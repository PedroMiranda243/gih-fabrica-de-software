"""Treinar, avaliar e prever — histórias H42 e H43.

`treinar` devolve os pesos e as métricas no conjunto de teste, lado a lado com
as referências. **Não decide se a versão entra em uso**: isso é o UC07-A1, regra
de negócio, e fica na API. Aqui só se mede.

**Reprodutível** (RNF16). A mesma base com a mesma semente dá as mesmas
métricas, e há teste para isso. Três coisas garantem: a semente fixa em tudo que
sorteia (pesos iniciais e ordem dos lotes), algoritmos determinísticos e uma
thread só — somas em paralelo mudam de ordem entre execuções, e em ponto
flutuante a ordem muda o resultado.

**Os pesos saem como bytes** (ADR-010), com tudo o que é preciso para prever
depois: a normalização, o vocabulário de categorias e a temperatura. E são lidos
com `weights_only=True`: o formato de salvamento do PyTorch é pickle, e pickle
de fonte arbitrária executa código. Só tensores, números e textos voltam.
"""
from __future__ import annotations

import copy
import io
import time
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass

import numpy as np
import torch
from torch import nn

from gih_modelo.avaliacao import Faixa, brier, curva_calibracao, erro_calibracao, mape
from gih_modelo.baselines import BASELINES, ReferenciaRisco, prever_faturamento
from gih_modelo.rede import OCULTAS, RedePrevisao
from gih_modelo.variaveis import (
    NUMERICAS,
    PISO_FATURAMENTO,
    Amostras,
    Serie,
    atuais,
    montar,
    separar_no_tempo,
    vocabulario,
)

FORMATO = 1
EPOCAS_MAXIMAS = 300
PACIENCIA = 20  # épocas sem melhorar na validação antes de parar
LOTE = 256
TAXA = 1e-3
DECAIMENTO = 1e-4

# Onde procurar a temperatura da calibração: de 1/4 a 4, em escala logarítmica.
# Uma grade, e não otimização, porque é um parâmetro só — e grade é
# determinística sem esforço.
_TEMPERATURAS = np.exp(np.linspace(np.log(0.25), np.log(4.0), 61))


class HistoricoInsuficiente(ValueError):
    """Não há amostra para treinar, validar ou testar."""


@dataclass(frozen=True)
class Volume:
    parceiros: int
    periodos: int
    treino: int
    validacao: int
    teste: int


@dataclass(frozen=True)
class Metricas:
    mape_modelo: float
    mape_ultimo: float
    mape_media_movel: float
    brier_modelo: float
    brier_referencia: float
    calibracao_modelo: float
    calibracao_referencia: float
    curva: list[Faixa]

    @property
    def melhor_baseline(self) -> str:
        return "ultimo" if self.mape_ultimo <= self.mape_media_movel else "media_movel"


@dataclass(frozen=True)
class Resultado:
    pesos: bytes
    metricas: Metricas
    volume: Volume
    referencia_risco: ReferenciaRisco
    epocas: int
    temperatura: float
    segundos: float


@dataclass(frozen=True)
class Previsao:
    parceiro: int
    faturamento: float
    probabilidade: float


@contextmanager
def _deterministico(semente: int) -> Iterator[torch.Generator]:
    """Semente, uma thread e algoritmos determinísticos — e devolve o estado
    anterior ao sair, porque são configurações do processo inteiro."""
    threads = torch.get_num_threads()
    deterministico = torch.are_deterministic_algorithms_enabled()
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.manual_seed(semente)
    try:
        yield torch.Generator().manual_seed(semente)
    finally:
        torch.set_num_threads(threads)
        torch.use_deterministic_algorithms(deterministico)


def _normalizacao(treino: Amostras) -> tuple[np.ndarray, np.ndarray]:
    """Média e desvio das variáveis numéricas, medidos só no treino.

    As colunas de categoria ficam como estão (0 ou 1): centrá-las não ajuda a
    rede e tira a leitura direta de "é desta categoria".
    """
    d = treino.x.shape[1]
    media = np.zeros(d)
    desvio = np.ones(d)
    n = len(NUMERICAS)
    media[:n] = treino.x[:, :n].mean(axis=0)
    desvio[:n] = np.maximum(treino.x[:, :n].std(axis=0), 1e-6)
    return media, desvio


def _variacao(amostras: Amostras) -> np.ndarray:
    """O alvo da regressão: logaritmo do faturamento do alvo sobre o do último."""
    alvo = np.maximum(amostras.alvo, PISO_FATURAMENTO)
    return np.log(alvo) - np.log(amostras.ultimo)


def _tensor(a: np.ndarray) -> torch.Tensor:
    return torch.as_tensor(np.ascontiguousarray(a), dtype=torch.float32)


def _sigmoide(z: np.ndarray) -> np.ndarray:
    # Pela tangente hiperbólica: `1 / (1 + exp(-z))` estoura para logito muito
    # negativo, e o aviso do NumPy vira ruído no log da API.
    return 0.5 * (1.0 + np.tanh(z / 2.0))


class _Preditor:
    """A rede com a normalização e a temperatura — o que se reconstrói dos pesos."""

    def __init__(self, rede, media, desvio, alvo_media, alvo_desvio, temperatura, vocab):
        self.rede = rede
        self.media = media
        self.desvio = desvio
        self.alvo_media = alvo_media
        self.alvo_desvio = alvo_desvio
        self.temperatura = temperatura
        self.vocab = tuple(vocab)

    def saidas(self, amostras: Amostras) -> tuple[np.ndarray, np.ndarray]:
        """A variação prevista (já desnormalizada) e o logito do risco."""
        self.rede.eval()
        with torch.no_grad():
            variacao, logito = self.rede(_tensor((amostras.x - self.media) / self.desvio))
        return (
            variacao.numpy().astype(float) * self.alvo_desvio + self.alvo_media,
            logito.numpy().astype(float),
        )

    def prever(self, amostras: Amostras) -> tuple[np.ndarray, np.ndarray]:
        variacao, logito = self.saidas(amostras)
        faturamento = amostras.ultimo * np.exp(variacao)
        probabilidade = _sigmoide(logito / self.temperatura)
        return faturamento, probabilidade

    def serializar(self) -> bytes:
        buffer = io.BytesIO()
        torch.save(
            {
                "formato": FORMATO,
                "entradas": int(self.media.shape[0]),
                "ocultas": OCULTAS,
                "estado": self.rede.state_dict(),
                "media": torch.as_tensor(self.media),
                "desvio": torch.as_tensor(self.desvio),
                "alvo_media": float(self.alvo_media),
                "alvo_desvio": float(self.alvo_desvio),
                "temperatura": float(self.temperatura),
                "vocabulario": list(self.vocab),
            },
            buffer,
        )
        return buffer.getvalue()

    @classmethod
    def carregar(cls, pesos: bytes) -> _Preditor:
        dados = torch.load(io.BytesIO(pesos), weights_only=True)
        if dados.get("formato") != FORMATO:
            raise ValueError(f"Formato de pesos desconhecido: {dados.get('formato')}")
        rede = RedePrevisao(dados["entradas"], dados["ocultas"])
        rede.load_state_dict(dados["estado"])
        return cls(
            rede,
            dados["media"].numpy(),
            dados["desvio"].numpy(),
            dados["alvo_media"],
            dados["alvo_desvio"],
            dados["temperatura"],
            dados["vocabulario"],
        )


def _perda(rede, x, variacao, risco) -> torch.Tensor:
    """Erro absoluto na variação mais entropia cruzada no risco.

    Absoluto, e não quadrático, porque o que se mede depois é o MAPE — erro em
    módulo. O quadrático gastaria a rede corrigindo as poucas semanas de ruído
    grande em vez de acertar as comuns.
    """
    prevista, logito = rede(x)
    return nn.functional.l1_loss(prevista, variacao) + (
        nn.functional.binary_cross_entropy_with_logits(logito, risco)
    )


def _temperatura(logito: np.ndarray, rotulo: np.ndarray) -> float:
    """A temperatura que minimiza a entropia cruzada na validação (H43).

    Dividir o logito por um número só muda o quanto a rede confia, nunca a
    ordem dos parceiros: quem tinha mais risco continua tendo.
    """
    melhor, menor = 1.0, float("inf")
    for t in _TEMPERATURAS:
        p = np.clip(_sigmoide(logito / t), 1e-7, 1 - 1e-7)
        perda = -np.mean(rotulo * np.log(p) + (1 - rotulo) * np.log(1 - p))
        if perda < menor:
            melhor, menor = float(t), perda
    return melhor


def treinar(series: Sequence[Serie], *, semente: int = 42) -> Resultado:
    """Treina a rede com o histórico e a avalia contra as referências."""
    inicio = time.perf_counter()
    vocab = vocabulario(series)
    separacao = separar_no_tempo(montar(series, vocab))
    treino, validacao, teste = separacao.treino, separacao.validacao, separacao.teste
    if not (len(treino) and len(validacao) and len(teste)):
        raise HistoricoInsuficiente(
            "Histórico sem amostra para treinar, validar e testar: "
            f"{len(treino)}, {len(validacao)} e {len(teste)}."
        )

    media, desvio = _normalizacao(treino)
    variacao_treino = _variacao(treino)
    alvo_media = float(variacao_treino.mean())
    alvo_desvio = float(max(variacao_treino.std(), 1e-6))

    def tensores(a: Amostras):
        return (
            _tensor((a.x - media) / desvio),
            _tensor((_variacao(a) - alvo_media) / alvo_desvio),
            _tensor(a.em_risco),
        )

    x, v, r = tensores(treino)
    xv, vv, rv = tensores(validacao)

    with _deterministico(semente) as gerador:
        rede = RedePrevisao(x.shape[1])
        otimizador = torch.optim.Adam(rede.parameters(), lr=TAXA, weight_decay=DECAIMENTO)
        melhor_perda, melhor_estado, melhor_epoca = float("inf"), None, 0
        epoca = 0
        for epoca in range(1, EPOCAS_MAXIMAS + 1):
            rede.train()
            for lote in torch.randperm(len(x), generator=gerador).split(LOTE):
                otimizador.zero_grad()
                _perda(rede, x[lote], v[lote], r[lote]).backward()
                otimizador.step()
            rede.eval()
            with torch.no_grad():
                perda = float(_perda(rede, xv, vv, rv))
            if perda < melhor_perda - 1e-6:
                melhor_perda, melhor_epoca = perda, epoca
                melhor_estado = copy.deepcopy(rede.state_dict())
            elif epoca - melhor_epoca >= PACIENCIA:
                break
        rede.load_state_dict(melhor_estado)

        preditor = _Preditor(rede, media, desvio, alvo_media, alvo_desvio, 1.0, vocab)
        _, logito_validacao = preditor.saidas(validacao)
        preditor.temperatura = _temperatura(logito_validacao, validacao.em_risco)

        faturamento, probabilidade = preditor.prever(teste)
        pesos = preditor.serializar()

    referencia = ReferenciaRisco.ajustar(treino)
    risco_referencia = referencia.prever(teste)
    metricas = Metricas(
        mape_modelo=mape(faturamento, teste.alvo),
        mape_ultimo=mape(prever_faturamento(teste, "ultimo"), teste.alvo),
        mape_media_movel=mape(prever_faturamento(teste, "media_movel"), teste.alvo),
        brier_modelo=brier(probabilidade, teste.em_risco),
        brier_referencia=brier(risco_referencia, teste.em_risco),
        calibracao_modelo=erro_calibracao(probabilidade, teste.em_risco),
        calibracao_referencia=erro_calibracao(risco_referencia, teste.em_risco),
        curva=curva_calibracao(probabilidade, teste.em_risco),
    )
    return Resultado(
        pesos=pesos,
        metricas=metricas,
        volume=Volume(
            parceiros=len(series),
            periodos=len({p for s in series for p in s.periodos}),
            treino=len(treino),
            validacao=len(validacao),
            teste=len(teste),
        ),
        referencia_risco=referencia,
        epocas=melhor_epoca,
        temperatura=preditor.temperatura,
        segundos=time.perf_counter() - inicio,
    )


def prever(pesos: bytes, series: Sequence[Serie]) -> list[Previsao]:
    """O próximo período de cada parceiro com histórico suficiente, pela rede."""
    preditor = _Preditor.carregar(pesos)
    amostras = atuais(series, preditor.vocab)
    if not len(amostras):
        return []
    with _deterministico(0):
        faturamento, probabilidade = preditor.prever(amostras)
    return _previsoes(amostras, faturamento, probabilidade)


def prever_referencia(
    series: Sequence[Serie], *, baseline: str, referencia: ReferenciaRisco
) -> list[Previsao]:
    """O próximo período pela referência — o que vale enquanto nenhuma versão da
    rede superou as contas simples (RN09, item 4)."""
    if baseline not in BASELINES:
        raise ValueError(f"Referência desconhecida: {baseline}")
    amostras = atuais(series, vocabulario(series))
    if not len(amostras):
        return []
    return _previsoes(
        amostras, prever_faturamento(amostras, baseline), referencia.prever(amostras)
    )


def _previsoes(amostras: Amostras, faturamento, probabilidade) -> list[Previsao]:
    return [
        Previsao(parceiro=int(p), faturamento=float(f), probabilidade=float(r))
        for p, f, r in zip(amostras.parceiro, faturamento, probabilidade, strict=True)
    ]

