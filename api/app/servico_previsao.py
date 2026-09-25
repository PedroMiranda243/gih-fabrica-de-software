"""Previsão de faturamento e risco — RF27, RF28, UC07, histórias H42 a H45.

A API orquestra; o pacote `gih_modelo` prevê (ADR-010). O que mora aqui é o que
é regra de negócio, e é por isso que não mora lá:

- **O rótulo de risco** (RN09): estar Em Risco no período seguinte, pelo
  critério da RN01. Sai de `criterio_em_risco`, a mesma função que classifica o
  segmento — modelo e segmentação nunca discordam sobre o que é queda, e mudar
  o limiar na configuração muda os dois juntos.
- **O histórico mínimo** (RN09): 8 períodos para treinar (UC07-E1); 4 para um
  parceiro receber previsão.
- **Quando uma versão entra em uso** (UC07-A1): só se superar as referências nas
  duas saídas. Senão fica a anterior — ou, sem anterior, a própria referência.
- **Quem recebe previsão**: quem tem janela completa e aparece no período mais
  recente, que é de onde a previsão parte.

**O treino roda fora da requisição** (`CLAUDE.md` §3). `iniciar` grava o treino
em andamento e devolve; `executar` roda em segundo plano, com sessão própria, e
grava o resultado na mesma linha. A tela só conhece o que está gravado — se um
dia o treino for para outro processo, a tela não muda.
"""
from __future__ import annotations

import logging
import sys
import uuid
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from gih_modelo import JANELA, PERIODOS_MINIMOS, Serie
from sqlalchemy import delete, exists, func, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import auditoria
from app.auditoria import Acao
from app.db import sessao
from app.modelos import (
    Categoria,
    Metrica,
    Parceiro,
    Periodo,
    Previsao,
    SituacaoTreino,
    TreinoModelo,
)
from app.servico_segmentacao import Limiares, criterio_em_risco, limiares_vigentes

log = logging.getLogger("gih")

# A semente do treino. Fixa, para que o mesmo histórico dê sempre a mesma
# versão (RNF16) — e gravada na linha, para que uma medição possa refazê-lo.
SEMENTE = 42

# O maior valor que `previsao.faturamento_previsto`, Numeric(12, 2), aceita.
# Previsão que passa disso é defeito, não previsão — mas estourar a coluna
# derrubaria o treino inteiro por causa de um parceiro.
_TETO_FATURAMENTO = Decimal("9999999999.99")

PREFIXO_REDE = "rede-"
PREFIXO_REFERENCIA = "referencia-"


# ------------------------------------------------------------ as recusas
class TreinoRecusado(Exception):
    """O treino não pode começar agora. Carrega o que a tela precisa dizer."""

    def __init__(self, erro: str, ajuda: str, **extra) -> None:
        super().__init__(erro)
        self.erro = erro
        self.ajuda = ajuda
        self.extra = extra


def recusa_por_historico(periodos: int) -> TreinoRecusado:
    faltam = PERIODOS_MINIMOS - periodos
    return TreinoRecusado(
        f"O treino precisa de {PERIODOS_MINIMOS} períodos importados, e a base tem {periodos}.",
        f"Faltam {faltam} período(s). Com menos, não há como separar treino, validação e teste "
        "no tempo, e o número sairia com cara de previsão e sem valor preditivo.",
        periodos=periodos,
        faltam=faltam,
    )


def _recusa_por_andamento(treino: TreinoModelo) -> TreinoRecusado:
    return TreinoRecusado(
        "Já existe um treino em andamento.",
        "Acompanhe o treino atual; quando ele terminar, você pode disparar outro.",
        em_andamento=treino.id,
    )


# ---------------------------------------------------- o histórico da rede
@dataclass(frozen=True)
class Historico:
    series: list[Serie]
    periodos: list[Periodo]  # em ordem; a posição na lista é o ordinal

    @property
    def base(self) -> Periodo | None:
        """O período mais recente com dados — de onde as previsões partem."""
        ultimo = max((s.periodos[-1] for s in self.series), default=None)
        return self.periodos[ultimo] if ultimo is not None else None


def rotular(faturamentos: list[Decimal], limiares: Limiares) -> list[bool]:
    """Em cada ponto da série, se o critério de Em Risco da RN01 valia ali.

    O critério recebe a série do mais recente para o mais antigo — é assim que
    a segmentação o chama —, daí o fatiamento invertido.
    """
    return [criterio_em_risco(faturamentos[i::-1], limiares) for i in range(len(faturamentos))]


def historico(s: Session, limiares: Limiares | None = None) -> Historico:
    """Toda a base, em três consultas, qualquer que seja o tamanho da rede.

    Uma consulta por parceiro funciona com 100 e morre com 10.000 (RNF04,
    `CLAUDE.md` §7). Aqui são três: os períodos, as categorias e as métricas —
    e o agrupamento por parceiro é feito em memória.
    """
    limiares = limiares or limiares_vigentes(s)
    periodos = list(s.scalars(select(Periodo).order_by(Periodo.data_inicio, Periodo.id)))
    ordinal = {p.id: i for i, p in enumerate(periodos)}
    categorias = dict(
        s.execute(
            select(Parceiro.id, Categoria.nome).outerjoin(
                Categoria, Categoria.id == Parceiro.categoria_id
            )
        ).all()
    )

    pontos: dict[int, list[tuple[int, Decimal, int]]] = defaultdict(list)
    for parceiro_id, periodo_id, faturamento, pedidos in s.execute(
        select(Metrica.parceiro_id, Metrica.periodo_id, Metrica.faturamento, Metrica.pedidos)
    ):
        pontos[parceiro_id].append((ordinal[periodo_id], faturamento, pedidos))

    series = []
    for parceiro_id in sorted(pontos):
        linha = sorted(pontos[parceiro_id])
        faturamentos = [f for _, f, _ in linha]
        series.append(
            Serie(
                parceiro=parceiro_id,
                categoria=categorias.get(parceiro_id),
                periodos=tuple(o for o, _, _ in linha),
                faturamento=tuple(float(f) for f in faturamentos),
                pedidos=tuple(p for _, _, p in linha),
                em_risco=tuple(rotular(faturamentos, limiares)),
            )
        )
    return Historico(series=series, periodos=periodos)


def periodos_com_dados(s: Session) -> int:
    return s.scalar(select(func.count(func.distinct(Metrica.periodo_id)))) or 0


def periodo_mais_recente(s: Session) -> Periodo | None:
    """O período mais recente **com métrica** — um período sem dado não é base de nada."""
    return s.scalar(
        select(Periodo)
        .where(exists().where(Metrica.periodo_id == Periodo.id))
        .order_by(Periodo.data_inicio.desc(), Periodo.id.desc())
    )


# ------------------------------------------------------------ a versão em uso
def ultimo_concluido(s: Session) -> TreinoModelo | None:
    """O último treino concluído: ele diz qual versão está valendo."""
    return s.scalar(
        select(TreinoModelo)
        .where(TreinoModelo.situacao == SituacaoTreino.CONCLUIDO)
        .order_by(TreinoModelo.id.desc())
    )


def em_andamento(s: Session) -> TreinoModelo | None:
    return s.scalar(
        select(TreinoModelo).where(TreinoModelo.situacao == SituacaoTreino.EM_ANDAMENTO)
    )


def treino_da_versao(s: Session, versao: str | None) -> TreinoModelo | None:
    """O treino que produziu a versão — `rede-7` e `referencia-7` vêm do treino 7."""
    if not versao:
        return None
    for prefixo in (PREFIXO_REDE, PREFIXO_REFERENCIA):
        if versao.startswith(prefixo):
            return s.get(TreinoModelo, int(versao.removeprefix(prefixo)))
    return None


def e_referencia(versao: str | None) -> bool:
    return bool(versao) and versao.startswith(PREFIXO_REFERENCIA)


# ------------------------------------------------------------ o treino
def iniciar(s: Session, *, usuario_id: int | None) -> TreinoModelo:
    """Grava um treino em andamento, ou recusa dizendo por quê.

    A checagem do "um por vez" é feita duas vezes de propósito: a consulta dá a
    recusa com o treino que está rodando; o índice único parcial fecha a
    corrida entre duas requisições que passam pela consulta ao mesmo tempo.
    """
    periodos = periodos_com_dados(s)
    if periodos < PERIODOS_MINIMOS:
        raise recusa_por_historico(periodos)

    rodando = em_andamento(s)
    if rodando is not None:
        raise _recusa_por_andamento(rodando)

    treino = TreinoModelo(
        usuario_id=usuario_id,
        periodo_base_id=periodo_mais_recente(s).id,
        semente=SEMENTE,
    )
    try:
        with s.begin_nested():
            s.add(treino)
            s.flush()
    except IntegrityError:
        rodando = em_andamento(s)
        raise _recusa_por_andamento(rodando) from None
    return treino


def _porcento(valor: float) -> str:
    return f"{valor * 100:.1f}%".replace(".", ",")


def _decimal3(valor: float) -> str:
    return f"{valor:.3f}".replace(".", ",")


def _nao_superou(metricas) -> str:
    """Por que a versão não entrou em uso, com os números que decidiram."""
    melhor = min(metricas.mape_ultimo, metricas.mape_media_movel)
    nome = "repetir o último período" if metricas.melhor_baseline == "ultimo" else "média móvel"
    partes = []
    if not metricas.mape_modelo < melhor:
        partes.append(
            f"no faturamento, errou {_porcento(metricas.mape_modelo)} contra "
            f"{_porcento(melhor)} de {nome}"
        )
    if not metricas.brier_modelo < metricas.brier_referencia:
        partes.append(
            f"no risco, teve Brier {_decimal3(metricas.brier_modelo)} contra "
            f"{_decimal3(metricas.brier_referencia)} da taxa observada"
        )
    return "Não superou a referência: " + "; ".join(partes) + "."


def supera_referencias(metricas) -> bool:
    """UC07-A1: a versão entra em uso só se ganhar nas duas saídas."""
    return (
        metricas.mape_modelo < min(metricas.mape_ultimo, metricas.mape_media_movel)
        and metricas.brier_modelo < metricas.brier_referencia
    )


def _executar(s: Session, treino: TreinoModelo) -> None:
    import gih_modelo  # o PyTorch só entra no processo quando se treina

    base = historico(s)
    periodo_base = base.base
    resultado = gih_modelo.treinar(base.series, semente=treino.semente)
    metricas = resultado.metricas
    anterior = ultimo_concluido(s)
    versao_anterior = anterior.versao_em_uso if anterior else None

    if supera_referencias(metricas):
        versao, motivo = treino.versao, None
        previsoes = gih_modelo.prever(resultado.pesos, base.series)
    elif versao_anterior and versao_anterior.startswith(PREFIXO_REDE):
        versao = versao_anterior
        motivo = f"{_nao_superou(metricas)} Mantida a versão em uso, {versao_anterior}."
        previsoes = gih_modelo.prever(treino_da_versao(s, versao_anterior).pesos, base.series)
    else:
        versao = f"{PREFIXO_REFERENCIA}{treino.id}"
        motivo = (
            f"{_nao_superou(metricas)} Como nenhuma versão da rede superou as referências "
            "ainda, as previsões saem da referência."
        )
        previsoes = gih_modelo.prever_referencia(
            base.series,
            baseline=metricas.melhor_baseline,
            referencia=resultado.referencia_risco,
        )

    # Só quem aparece no período mais recente: a previsão parte dele (RN09).
    ultimo = base.periodos.index(periodo_base)
    presentes = {serie.parceiro for serie in base.series if serie.periodos[-1] == ultimo}
    linhas = [
        {
            "parceiro_id": p.parceiro,
            "periodo_base_id": periodo_base.id,
            "faturamento_previsto": min(Decimal(f"{p.faturamento:.2f}"), _TETO_FATURAMENTO),
            "probabilidade_queda": min(max(p.probabilidade, 0.0), 1.0),
            "modelo_versao": versao,
        }
        for p in previsoes
        if p.parceiro in presentes
    ]
    # Idempotente, como a segmentação: retreinar sem período novo mantendo a
    # mesma versão regrava as mesmas previsões em vez de colidir com elas.
    s.execute(
        delete(Previsao).where(
            Previsao.periodo_base_id == periodo_base.id, Previsao.modelo_versao == versao
        )
    )
    if linhas:
        s.execute(insert(Previsao), linhas)

    volume = resultado.volume
    treino.situacao = SituacaoTreino.CONCLUIDO
    treino.concluido_em = s.scalar(select(func.now()))
    treino.periodo_base_id = periodo_base.id
    treino.parceiros = volume.parceiros
    treino.periodos = volume.periodos
    treino.amostras_treino = volume.treino
    treino.amostras_validacao = volume.validacao
    treino.amostras_teste = volume.teste
    treino.mape_modelo = metricas.mape_modelo
    treino.mape_ultimo = metricas.mape_ultimo
    treino.mape_media_movel = metricas.mape_media_movel
    treino.brier_modelo = metricas.brier_modelo
    treino.brier_referencia = metricas.brier_referencia
    treino.calibracao_modelo = metricas.calibracao_modelo
    treino.calibracao_referencia = metricas.calibracao_referencia
    treino.detalhes = {
        "epocas": resultado.epocas,
        "temperatura": resultado.temperatura,
        "segundos": round(resultado.segundos, 2),
        "melhor_baseline": metricas.melhor_baseline,
        "referencia_risco": {
            "se_caiu": resultado.referencia_risco.se_caiu,
            "se_nao_caiu": resultado.referencia_risco.se_nao_caiu,
        },
        "curva": [
            {
                "inicio": f.inicio,
                "fim": f.fim,
                "previsto": f.previsto,
                "observado": f.observado,
                "amostras": f.amostras,
            }
            for f in metricas.curva
        ],
        "previsoes": len(linhas),
    }
    treino.promovido = versao == treino.versao
    treino.versao_em_uso = versao
    treino.motivo = motivo
    treino.pesos = resultado.pesos
    s.flush()


def executar(treino_id: int, *, origem: str | None = None) -> None:
    """Roda o treino gravado por `iniciar`. É o que vai para segundo plano.

    **Nunca propaga exceção**: em segundo plano não há quem a receba, e o treino
    ficaria em andamento para sempre, prendendo a trava do um por vez. Falha
    vira `FALHOU` com o motivo, e o detalhe técnico vai para o log com um
    identificador de correlação — o mesmo contrato das rotas (RNF18, RNF19).
    """
    usuario_id = None
    try:
        with sessao() as s:
            treino = s.get(TreinoModelo, treino_id)
            usuario_id = treino.usuario_id
            _executar(s, treino)
            detalhes = {
                "treino": treino.id,
                "versao_em_uso": treino.versao_em_uso,
                "promovido": treino.promovido,
                "parceiros": treino.parceiros,
                "periodos": treino.periodos,
                "mape_modelo": treino.mape_modelo,
                "brier_modelo": treino.brier_modelo,
            }
        auditoria.registrar(
            Acao.MODELO_TREINADO, usuario_id=usuario_id, detalhes=detalhes, origem=origem
        )
    except Exception as erro:
        correlacao = uuid.uuid4().hex[:12]
        log.exception("[%s] Treino %s falhou", correlacao, treino_id)
        # Lido do módulo já carregado, sem importar de novo: se a falha foi
        # justamente importar o PyTorch, importar aqui estouraria de novo, fora
        # de qualquer `try`, e o treino ficaria em andamento para sempre.
        insuficiente = getattr(sys.modules.get("gih_modelo.treino"), "HistoricoInsuficiente", None)
        if insuficiente is not None and isinstance(erro, insuficiente):
            motivo = (
                "O histórico não tem amostra para treinar, validar e testar: há períodos "
                "suficientes, mas poucos parceiros com a janela completa de "
                f"{JANELA} períodos."
            )
        else:
            motivo = f"O treino falhou por um erro interno (registro {correlacao})."
        _marcar_falha(treino_id, motivo)
        auditoria.registrar(
            Acao.MODELO_TREINO_FALHOU,
            usuario_id=usuario_id,
            detalhes={"treino": treino_id, "motivo": motivo},
            origem=origem,
        )


def _marcar_falha(treino_id: int, motivo: str) -> None:
    try:
        with sessao() as s:
            treino = s.get(TreinoModelo, treino_id)
            if treino is not None and treino.situacao == SituacaoTreino.EM_ANDAMENTO:
                treino.situacao = SituacaoTreino.FALHOU
                treino.concluido_em = s.scalar(select(func.now()))
                treino.motivo = motivo
    except Exception:
        log.exception("Não foi possível marcar o treino %s como falho", treino_id)


def recuperar_interrompidos(s: Session) -> int:
    """Marca como falhos os treinos que ficaram em andamento — chamada na subida.

    Se a API reinicia no meio de um treino, a linha fica `EM_ANDAMENTO` sem
    ninguém rodando. Sem isto, a trava do um por vez ficaria fechada para
    sempre, e a tela recusaria todo treino novo dizendo que já há um rodando.

    Vale porque a API roda num processo só (`entrypoint.sh`: `uvicorn` sem
    `--workers`). Com vários, a subida de um marcaria como falho o treino que
    outro está rodando — e aí a recuperação precisaria saber de quem é cada um.
    """
    interrompidos = list(
        s.scalars(select(TreinoModelo).where(TreinoModelo.situacao == SituacaoTreino.EM_ANDAMENTO))
    )
    agora = s.scalar(select(func.now()))
    for treino in interrompidos:
        treino.situacao = SituacaoTreino.FALHOU
        treino.concluido_em = agora
        treino.motivo = "Interrompido: a API reiniciou durante o treino. Dispare um novo."
    return len(interrompidos)


# ------------------------------------------------------------ a leitura
@dataclass(frozen=True)
class PrevisaoLida:
    """A previsão de um parceiro, ou o porquê de não haver (RN09, H44)."""

    previsao: Previsao | None
    periodo_base: Periodo | None
    versao: str | None
    motivo: str | None = None
    ajuda: str | None = None
    desatualizada: bool = False


def previsao_do_parceiro(s: Session, parceiro_id: int) -> PrevisaoLida:
    concluido = ultimo_concluido(s)
    if concluido is None:
        return PrevisaoLida(
            None,
            None,
            None,
            motivo="O modelo ainda não foi treinado.",
            ajuda="Um administrador ou gestor treina o modelo na tela Modelo.",
        )

    base = s.get(Periodo, concluido.periodo_base_id)
    versao = concluido.versao_em_uso
    recente = periodo_mais_recente(s)
    desatualizada = recente is not None and recente.id != base.id

    previsao = s.scalar(
        select(Previsao).where(
            Previsao.parceiro_id == parceiro_id,
            Previsao.periodo_base_id == base.id,
            Previsao.modelo_versao == versao,
        )
    )
    if previsao is not None:
        return PrevisaoLida(previsao, base, versao, desatualizada=desatualizada)

    periodos = s.scalar(
        select(func.count())
        .select_from(Metrica)
        .join(Periodo, Periodo.id == Metrica.periodo_id)
        .where(Metrica.parceiro_id == parceiro_id, Periodo.data_inicio <= base.data_inicio)
    )
    no_periodo = s.scalar(
        select(exists().where(Metrica.parceiro_id == parceiro_id, Metrica.periodo_id == base.id))
    )
    if periodos < JANELA:
        motivo = (
            f"Com {periodos} período(s) de histórico, ainda não há previsão: "
            f"são necessários {JANELA}."
        )
        ajuda = "A previsão aparece no primeiro treino depois que o parceiro completar a janela."
    elif not no_periodo:
        motivo = "O parceiro não aparece no período mais recente do último treino."
        ajuda = "A previsão parte do período mais recente; sem dado nele, não há de onde partir."
    else:
        motivo = "O parceiro entrou na base depois do último treino."
        ajuda = "Um novo treino inclui o parceiro."
    return PrevisaoLida(
        None, base, versao, motivo=motivo, ajuda=ajuda, desatualizada=desatualizada
    )
