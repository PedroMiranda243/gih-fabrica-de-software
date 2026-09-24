"""As variáveis preditivas e a separação no tempo — história H41.

**O que entra** é uma `Serie` por parceiro: os números que a API leu do banco e
o rótulo de risco que a API calculou pela RN01. O rótulo chega pronto de
propósito: o que conta como queda é regra de negócio (RN09), e regra mora na
API. Este pacote só aprende a antecipá-lo.

**Cada amostra olha os 4 períodos do parceiro que antecedem o alvo.** "Período
do parceiro" no mesmo sentido da RN01: os períodos em que ele aparece, em
ordem. Quem faltou a um relatório não ganha um zero inventado no lugar — zero
seria uma queda de 100% que não aconteceu.

**Faturamento vai relativo ao último período da janela**, e não em reais. Na
rede sintética há parceiro de R$ 100 e de R$ 50.000 por semana; em reais, a
rede passaria o treino aprendendo a escala de cada um em vez do movimento, que
é o que se quer prever. A escala entra à parte, como uma variável só.

**A separação é por tempo, nunca por sorteio** (UC07, passo 3): o último
período da base testa, o penúltimo valida, e os anteriores treinam. Sorteando,
uma amostra de treino poderia ter como alvo a semana seguinte à de uma amostra
de teste, e a métrica sairia boa e falsa.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, fields

import numpy as np

# A janela de variáveis. É também o histórico mínimo para um parceiro receber
# previsão (RN09, item 3): com menos que isto não há janela para montar.
JANELA = 4

# O mínimo de períodos na base para treinar (RN09, item 2): a janela, dois
# períodos-alvo para treinar, um para validar e um para testar.
PERIODOS_MINIMOS = JANELA + 4

# Faturamento e pedidos podem ser zero no banco (as restrições são `>= 0`), e
# logaritmo de zero não existe. Um real e um pedido são o piso: abaixo disso a
# diferença não significa nada para a previsão.
PISO_FATURAMENTO = 1.0
PISO_PEDIDOS = 1.0

# As variáveis numéricas, na ordem das colunas. As de categoria vêm depois, uma
# por categoria do vocabulário e uma para "sem categoria ou desconhecida".
NUMERICAS = (
    "faturamento_t-4",  # relativo ao último período da janela, em logaritmo
    "faturamento_t-3",
    "faturamento_t-2",
    "pedidos_t-4",  # idem, para pedidos
    "pedidos_t-3",
    "pedidos_t-2",
    "escala",  # logaritmo do faturamento do último período
    "ticket_medio",  # logaritmo do faturamento por pedido no último período (RN04)
    "tendencia",  # inclinação do logaritmo do faturamento ao longo da janela
    "posicao",  # posição no ranking do último período, em percentil (1 = o maior)
    "tempo_de_casa",  # logaritmo de 1 + períodos do parceiro antes do alvo
)

# Abscissas centradas da janela: a inclinação por mínimos quadrados fica um
# produto escalar.
_T = np.arange(JANELA, dtype=float) - (JANELA - 1) / 2


@dataclass(frozen=True)
class Serie:
    """O histórico de um parceiro, do período mais antigo para o mais recente.

    `periodos` é o ordinal do período na base — 0 é o mais antigo — e é o que
    põe as amostras de parceiros diferentes na mesma linha do tempo. `em_risco`
    diz, em cada período, se o critério de Em Risco da RN01 valia ali.
    """

    parceiro: int
    categoria: str | None
    periodos: Sequence[int]
    faturamento: Sequence[float]
    pedidos: Sequence[int]
    em_risco: Sequence[bool]

    def __post_init__(self) -> None:
        n = len(self.periodos)
        if not (len(self.faturamento) == len(self.pedidos) == len(self.em_risco) == n):
            raise ValueError(f"Série do parceiro {self.parceiro} com tamanhos diferentes.")
        if any(b <= a for a, b in zip(self.periodos, self.periodos[1:], strict=False)):
            raise ValueError(f"Períodos do parceiro {self.parceiro} fora de ordem ou repetidos.")


@dataclass(frozen=True)
class Amostras:
    """Uma linha por par (parceiro, período-alvo), em colunas paralelas.

    `x` ainda não está normalizado: a normalização usa só o treino, e é por isso
    que ela acontece depois da separação, no treino — normalizar antes vazaria
    a média do teste para dentro do modelo.
    """

    x: np.ndarray  # (n, d) variáveis
    ultimo: np.ndarray  # faturamento do último período da janela
    media_movel: np.ndarray  # média do faturamento na janela
    caiu: np.ndarray  # o faturamento caiu no último período da janela
    alvo: np.ndarray  # faturamento real do período-alvo (NaN quando não há alvo)
    em_risco: np.ndarray  # o rótulo do alvo, 0 ou 1 (NaN quando não há alvo)
    periodo_alvo: np.ndarray  # ordinal do período-alvo (-1 quando não há alvo)
    parceiro: np.ndarray

    def __len__(self) -> int:
        return len(self.parceiro)

    def filtrar(self, mascara: np.ndarray) -> Amostras:
        return Amostras(**{f.name: getattr(self, f.name)[mascara] for f in fields(self)})


@dataclass(frozen=True)
class Separacao:
    treino: Amostras
    validacao: Amostras
    teste: Amostras


def vocabulario(series: Sequence[Serie]) -> tuple[str, ...]:
    """As categorias da base, em ordem fixa — a ordem é a das colunas."""
    return tuple(sorted({s.categoria for s in series if s.categoria}))


def colunas(vocab: Sequence[str]) -> tuple[str, ...]:
    """O nome de cada coluna de `x`, para documentar e para conferir."""
    return NUMERICAS + tuple(f"categoria:{c}" for c in vocab) + ("categoria:—",)


def _percentis(series: Sequence[Serie]) -> list[np.ndarray]:
    """A posição de cada ponto no ranking do seu período, em percentil.

    Calculada **dentro do período**, entre os parceiros que aparecem nele: é
    informação daquela semana, e não enxerga semana nenhuma à frente. Percentil,
    e não posição absoluta, para que "3º lugar" signifique o mesmo numa rede de
    500 e numa de 5.000.
    """
    periodos = np.concatenate([np.asarray(s.periodos, dtype=np.int64) for s in series])
    fat = np.concatenate([np.asarray(s.faturamento, dtype=float) for s in series])
    ordem = np.lexsort((-fat, periodos))
    grupo = periodos[ordem]
    inicio = np.r_[0, np.flatnonzero(np.diff(grupo)) + 1]
    tamanho = np.diff(np.r_[inicio, len(ordem)])
    posicao = np.arange(len(ordem)) - np.repeat(inicio, tamanho)
    n = np.repeat(tamanho, tamanho)
    em_ordem = np.where(n > 1, 1.0 - posicao / np.maximum(n - 1, 1), 1.0)
    percentil = np.empty_like(em_ordem)
    percentil[ordem] = em_ordem
    cortes = np.cumsum([len(s.periodos) for s in series])[:-1]
    return np.split(percentil, cortes)


def _janelas(serie: Serie, percentil: np.ndarray, fim: np.ndarray, vocab: Sequence[str]):
    """As variáveis das janelas que terminam logo antes de cada índice em `fim`.

    `fim[k]` é o índice do alvo na série; a janela são os `JANELA` pontos
    anteriores a ele.
    """
    fat = np.maximum(np.asarray(serie.faturamento, dtype=float), PISO_FATURAMENTO)
    ped = np.maximum(np.asarray(serie.pedidos, dtype=float), PISO_PEDIDOS)
    indices = fim[:, None] - JANELA + np.arange(JANELA)  # (k, JANELA)
    lf = np.log(fat[indices])
    lp = np.log(ped[indices])
    ultimo = indices[:, -1]

    categoria = np.zeros((len(fim), len(vocab) + 1))
    coluna = vocab.index(serie.categoria) if serie.categoria in vocab else len(vocab)
    categoria[:, coluna] = 1.0

    x = np.column_stack(
        [
            lf[:, :-1] - lf[:, -1:],
            lp[:, :-1] - lp[:, -1:],
            lf[:, -1],
            lf[:, -1] - lp[:, -1],
            lf @ _T / (_T @ _T),
            percentil[ultimo],
            np.log1p(fim),
            categoria,
        ]
    )
    return x, fat[ultimo], fat[indices].mean(axis=1), fat[ultimo] < fat[ultimo - 1]


def _vazias(d: int) -> Amostras:
    vazio = np.empty(0)
    return Amostras(
        x=np.empty((0, d)),
        ultimo=vazio,
        media_movel=vazio,
        caiu=np.empty(0, dtype=bool),
        alvo=vazio,
        em_risco=vazio,
        periodo_alvo=np.empty(0, dtype=np.int64),
        parceiro=np.empty(0, dtype=np.int64),
    )


def _juntar(partes: list[dict], d: int) -> Amostras:
    if not partes:
        return _vazias(d)
    return Amostras(**{k: np.concatenate([p[k] for p in partes]) for k in partes[0]})


def montar(series: Sequence[Serie], vocab: Sequence[str]) -> Amostras:
    """Todas as amostras de treino da base: cada período com janela completa antes dele."""
    percentis = _percentis(series) if series else []
    partes = []
    for serie, percentil in zip(series, percentis, strict=True):
        n = len(serie.periodos)
        if n <= JANELA:
            continue
        fim = np.arange(JANELA, n)
        x, ultimo, media, caiu = _janelas(serie, percentil, fim, vocab)
        partes.append(
            {
                "x": x,
                "ultimo": ultimo,
                "media_movel": media,
                "caiu": caiu,
                "alvo": np.asarray(serie.faturamento, dtype=float)[fim],
                "em_risco": np.asarray(serie.em_risco, dtype=float)[fim],
                "periodo_alvo": np.asarray(serie.periodos, dtype=np.int64)[fim],
                "parceiro": np.full(len(fim), serie.parceiro, dtype=np.int64),
            }
        )
    return _juntar(partes, len(colunas(vocab)))


def atuais(series: Sequence[Serie], vocab: Sequence[str]) -> Amostras:
    """Uma amostra por parceiro com histórico suficiente, com a janela terminando
    no período mais recente dele — é o que se usa para prever o próximo."""
    percentis = _percentis(series) if series else []
    partes = []
    for serie, percentil in zip(series, percentis, strict=True):
        n = len(serie.periodos)
        if n < JANELA:
            continue
        x, ultimo, media, caiu = _janelas(serie, percentil, np.array([n]), vocab)
        partes.append(
            {
                "x": x,
                "ultimo": ultimo,
                "media_movel": media,
                "caiu": caiu,
                "alvo": np.full(1, np.nan),
                "em_risco": np.full(1, np.nan),
                "periodo_alvo": np.full(1, -1, dtype=np.int64),
                "parceiro": np.full(1, serie.parceiro, dtype=np.int64),
            }
        )
    return _juntar(partes, len(colunas(vocab)))


def separar_no_tempo(amostras: Amostras) -> Separacao:
    """Teste no último período-alvo, validação no penúltimo, treino no resto."""
    if len(amostras) == 0:
        vazias = amostras
        return Separacao(vazias, vazias, vazias)
    ultimo = amostras.periodo_alvo.max()
    return Separacao(
        treino=amostras.filtrar(amostras.periodo_alvo <= ultimo - 2),
        validacao=amostras.filtrar(amostras.periodo_alvo == ultimo - 1),
        teste=amostras.filtrar(amostras.periodo_alvo == ultimo),
    )
