"""O plano de campanha — RF29, RF30, RF31, UC08, histórias H48 a H52.

A API orquestra; o pacote `gih_nucleo` otimiza (ADR-011). O que mora aqui é o
que é regra de negócio, e é por isso que não mora lá:

- **O ganho de cada ação** (RN10): `F̂·crescimento + F̂·p·retenção`, com a
  previsão da versão em uso, calculado em centavos inteiros.
- **Quem é elegível** (RN11): ativo e com previsão. Quem fica fora é contado,
  por motivo.
- **As cotas em contagem** (RN11): fração do máximo de ações, o mínimo para
  cima e o máximo para baixo.
- **A categoria que conta** é só a confirmada (RN05); **a cauda longa** é quem
  está fora do Top N no ranking do período-base, e não no segmento (RN02).
- **O texto da recusa**, com o nome da categoria e o valor em reais: o núcleo
  só conhece índices e centavos.

**A busca roda fora da requisição** (`CLAUDE.md` §3), como o treino do modelo:
`iniciar` grava a execução em andamento, e `executar` roda em segundo plano, com
sessão própria, e grava o resultado na mesma linha. Uma por vez, pelo banco.
"""
from __future__ import annotations

import logging
import math
import time
import uuid
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction

import gih_nucleo
from gih_modelo import JANELA
from gih_nucleo import viabilidade as v
from gih_nucleo.guloso import GANHO, RAZAO
from sqlalchemy import func, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import auditoria, servico_previsao
from app.auditoria import Acao
from app.db import sessao
from app.esquemas import ParametrosCampanha
from app.modelos import (
    AcaoComercial,
    Categoria,
    ExecucaoOtimizador,
    ItemPlano,
    Metrica,
    ModoExecucao,
    OrigemCategoria,
    Parceiro,
    Periodo,
    PlanoCampanha,
    Previsao,
    SituacaoExecucao,
    StatusComercial,
)
from app.ranking import posicoes
from app.servico_segmentacao import limiares_vigentes

log = logging.getLogger("gih")

# A semente da busca. Fixa, para que a mesma campanha dê o mesmo plano (RNF16),
# e gravada na execução, para que o benchmark possa refazê-la (ADR-011).
SEMENTE = 42

# O limite de tempo da busca (UC08, E2): estourado, o plano é o melhor viável
# encontrado até ali, marcado como parcial. A versão serial em Python leva
# segundos na base de demonstração; o limite existe para a base grande.
LIMITE_S = 120

_UM = Decimal(1)


# ------------------------------------------------------------ as recusas
class OtimizacaoRecusada(Exception):
    """A campanha não pode ser calculada agora. Carrega o que a tela precisa dizer."""

    def __init__(self, erro: str, ajuda: str, *, status: int = 409, **extra) -> None:
        super().__init__(erro)
        self.erro = erro
        self.ajuda = ajuda
        self.status = status
        self.extra = extra


def _recusa_por_andamento(execucao: ExecucaoOtimizador) -> OtimizacaoRecusada:
    return OtimizacaoRecusada(
        "Já existe uma otimização em andamento.",
        "Acompanhe a atual; quando ela terminar, você pode calcular outra.",
        em_andamento=execucao.id,
    )


def em_andamento(s: Session) -> ExecucaoOtimizador | None:
    return s.scalar(
        select(ExecucaoOtimizador).where(
            ExecucaoOtimizador.situacao == SituacaoExecucao.EM_ANDAMENTO
        )
    )


def ultima_concluida(s: Session) -> ExecucaoOtimizador | None:
    return s.scalar(
        select(ExecucaoOtimizador)
        .where(ExecucaoOtimizador.situacao == SituacaoExecucao.CONCLUIDA)
        .order_by(ExecucaoOtimizador.id.desc())
    )


def bloqueio(s: Session) -> OtimizacaoRecusada | None:
    """Por que não dá para calcular agora; `None` quando dá."""
    if servico_previsao.ultimo_concluido(s) is None:
        return OtimizacaoRecusada(
            "O modelo ainda não foi treinado.",
            "O ganho de cada ação sai da previsão do parceiro (RN10). Treine o modelo na tela "
            "Modelo e volte.",
        )
    if s.scalar(select(func.count()).where(AcaoComercial.ativa.is_(True))) == 0:
        return OtimizacaoRecusada(
            "O catálogo não tem nenhuma ação ativa.",
            "Cadastre ou reative uma ação no catálogo da campanha.",
        )
    rodando = em_andamento(s)
    if rodando is not None:
        return _recusa_por_andamento(rodando)
    return None


# ------------------------------------------------------------ quem entra
@dataclass(frozen=True)
class Elegivel:
    parceiro_id: int
    categoria_id: int | None  # só a confirmada (RN05)
    faturamento_previsto: Decimal
    probabilidade: float
    posicao: int | None  # no ranking do período-base


def _elegivel():
    """Ativo no status comercial e não desativado no cadastro (RN11)."""
    return (Parceiro.ativo.is_(True)) & (Parceiro.status == StatusComercial.ATIVO)


def elegiveis(s: Session, periodo_base_id: int, versao: str) -> list[Elegivel]:
    """Os parceiros que podem receber ação, numa consulta só (sem N+1)."""
    ranking = posicoes(periodo_base_id).subquery()
    linhas = s.execute(
        select(
            Parceiro.id,
            Parceiro.categoria_id,
            Parceiro.origem_categoria,
            Previsao.faturamento_previsto,
            Previsao.probabilidade_queda,
            ranking.c.posicao,
        )
        .join(Previsao, Previsao.parceiro_id == Parceiro.id)
        .outerjoin(ranking, ranking.c.parceiro_id == Parceiro.id)
        .where(
            Previsao.periodo_base_id == periodo_base_id,
            Previsao.modelo_versao == versao,
            _elegivel(),
        )
        .order_by(Parceiro.id)
    )
    return [
        Elegivel(
            parceiro_id=pid,
            categoria_id=cid if origem == OrigemCategoria.MANUAL else None,
            faturamento_previsto=previsto,
            probabilidade=prob,
            posicao=posicao,
        )
        for pid, cid, origem, previsto, prob, posicao in linhas
    ]


def excluidos(s: Session, periodo_base_id: int, versao: str) -> dict[str, int]:
    """Quem ficou fora do plano, por motivo (RN11) — os mesmos da tela do parceiro."""
    contagem = {
        "historico_curto": 0,
        "fora_do_periodo": 0,
        "sem_previsao": 0,
        "inativos": 0,
        "em_prospeccao": 0,
    }
    for status_comercial, ativo, n in s.execute(
        select(Parceiro.status, Parceiro.ativo, func.count()).group_by(
            Parceiro.status, Parceiro.ativo
        )
    ):
        if not ativo or status_comercial == StatusComercial.INATIVO:
            contagem["inativos"] += n
        elif status_comercial == StatusComercial.PROSPECCAO:
            contagem["em_prospeccao"] += n

    # Ativos sem previsão: o motivo segue a mesma ordem de `previsao_do_parceiro`.
    base = s.get(Periodo, periodo_base_id)
    com_previsao = select(Previsao.parceiro_id).where(
        Previsao.periodo_base_id == periodo_base_id, Previsao.modelo_versao == versao
    )
    ate_a_base = func.count(Metrica.id).filter(Periodo.data_inicio <= base.data_inicio)
    na_base = func.bool_or(Metrica.periodo_id == periodo_base_id)
    for _pid, periodos, presente in s.execute(
        select(Parceiro.id, ate_a_base, na_base)
        .select_from(Parceiro)
        .outerjoin(Metrica, Metrica.parceiro_id == Parceiro.id)
        .outerjoin(Periodo, Periodo.id == Metrica.periodo_id)
        .where(_elegivel(), Parceiro.id.not_in(com_previsao))
        .group_by(Parceiro.id)
    ):
        if periodos < JANELA:
            contagem["historico_curto"] += 1
        elif not presente:
            contagem["fora_do_periodo"] += 1
        else:
            contagem["sem_previsao"] += 1
    return contagem


# ------------------------------------------------------------ a instância
def ganho_em_centavos(
    previsto: Decimal, probabilidade: float, crescimento: Decimal, retencao: Decimal
) -> int:
    """RN10: `F̂·c + F̂·p·r`, em centavos, arredondado meio para cima."""
    # `repr` dá o decimal mais curto que volta ao mesmo `float`: 0.2355, e não
    # 0.23549999999999998712… — que mudaria o arredondamento de um centavo.
    p = Decimal(repr(probabilidade))
    valor = previsto * (crescimento + p * retencao) * 100
    return max(0, int(valor.quantize(_UM, rounding=ROUND_HALF_UP)))


def minimo_em_contagem(fracao: Decimal, maximo_acoes: int) -> int:
    """RN11: o mínimo arredonda para cima. Em fração exata, sem `float`."""
    return math.ceil(Fraction(str(fracao)) * maximo_acoes)


def maximo_em_contagem(fracao: Decimal, maximo_acoes: int) -> int:
    """RN11: o máximo arredonda para baixo."""
    return math.floor(Fraction(str(fracao)) * maximo_acoes)


def centavos(valor: Decimal) -> int:
    return int((valor * 100).quantize(_UM, rounding=ROUND_HALF_UP))


def reais(valor_em_centavos: int) -> Decimal:
    return Decimal(valor_em_centavos) / 100


@dataclass(frozen=True)
class Montagem:
    instancia: gih_nucleo.Instancia
    parametros: ParametrosCampanha
    parceiros: list[Elegivel]  # na ordem dos genes
    acoes: list[AcaoComercial]  # na ordem das ações da instância
    categorias: list[Categoria]  # na ordem dos índices de categoria
    top_n: int


def montar(s: Session, execucao: ExecucaoOtimizador) -> Montagem:
    """Traduz a campanha para a instância do núcleo: centavos, índices e contagens."""
    parametros = ParametrosCampanha.model_validate(execucao.parametros)
    k = parametros.maximo_acoes
    acoes = list(
        s.scalars(
            select(AcaoComercial).where(AcaoComercial.ativa.is_(True)).order_by(AcaoComercial.id)
        )
    )
    parceiros = elegiveis(s, execucao.periodo_base_id, execucao.modelo_versao)
    top_n = limiares_vigentes(s).top_n

    cotas = {c.categoria_id: c for c in parametros.cotas_categoria}
    ids = sorted({p.categoria_id for p in parceiros if p.categoria_id is not None} | set(cotas))
    por_id = {c.id: c for c in s.scalars(select(Categoria).where(Categoria.id.in_(ids)))}
    categorias = [por_id[i] for i in ids]
    indice = {c.id: k_ for k_, c in enumerate(categorias)}

    minimos, maximos = [], []
    for c in categorias:
        cota = cotas.get(c.id)
        minimos.append(minimo_em_contagem(cota.minimo, k) if cota and cota.minimo else 0)
        maximos.append(
            maximo_em_contagem(cota.maximo, k) if cota and cota.maximo is not None else k
        )

    instancia = gih_nucleo.Instancia(
        ganho=tuple(
            tuple(
                ganho_em_centavos(
                    p.faturamento_previsto, p.probabilidade, a.efeito_crescimento, a.efeito_retencao
                )
                for a in acoes
            )
            for p in parceiros
        ),
        custo=tuple(centavos(a.custo_unitario) for a in acoes),
        orcamento=centavos(parametros.orcamento),
        maximo_acoes=k,
        categoria=tuple(
            indice[p.categoria_id] if p.categoria_id is not None else gih_nucleo.SEM_CATEGORIA
            for p in parceiros
        ),
        cauda=tuple(p.posicao is None or p.posicao > top_n for p in parceiros),
        minimo_categoria=tuple(minimos),
        maximo_categoria=tuple(maximos),
        minimo_cauda=(
            minimo_em_contagem(parametros.cota_cauda_longa, k)
            if parametros.cota_cauda_longa
            else 0
        ),
    )
    return Montagem(instancia, parametros, parceiros, acoes, categorias, top_n)


# ------------------------------------------------------------ o texto da recusa
def _formatar_reais(valor_em_centavos: int) -> str:
    texto = f"{reais(valor_em_centavos):,.2f}"
    return "R$ " + texto.replace(",", "_").replace(".", ",").replace("_", ".")


def _acoes(n: int) -> str:
    return f"{n} ação" if n == 1 else f"{n} ações"


def _parceiros(n: int) -> str:
    return f"{n} parceiro elegível" if n == 1 else f"{n} parceiros elegíveis"


def texto_da_recusa(motivo: v.Inviabilidade, m: Montagem) -> tuple[str, str]:
    """O que dizer a quem configurou a campanha: qual restrição e quanto falta (docs/09)."""
    nome = m.categorias[motivo.categoria].nome if motivo.categoria is not None else ""
    k = m.instancia.maximo_acoes
    if motivo.restricao == v.COTA_CATEGORIA:
        return (
            f"A cota mínima de {nome} ({_acoes(motivo.exigido)}) passa da máxima "
            f"({_acoes(motivo.disponivel)}).",
            f"Com o máximo de {_acoes(k)}, as cotas viram contagem: o mínimo arredonda para cima "
            f"e o máximo para baixo. Afaste as duas cotas de {nome}.",
        )
    if motivo.restricao == v.ELEGIVEIS_CATEGORIA:
        return (
            f"{nome} tem {_parceiros(motivo.disponivel)}, e a cota mínima exige "
            f"{_acoes(motivo.exigido)}: faltam {motivo.falta}.",
            f"Reduza a cota mínima de {nome}. Entra na campanha quem está ativo, tem previsão e "
            "tem a categoria confirmada (RN11).",
        )
    if motivo.restricao == v.CAUDA_LONGA:
        return (
            f"A cota da cauda longa exige {_acoes(motivo.exigido)}, e só "
            f"{motivo.disponivel} da cauda longa cabem nas cotas: faltam {motivo.falta}.",
            "Reduza a cota da cauda longa, ou aumente o máximo das categorias que a limitam.",
        )
    if motivo.restricao == v.MAXIMO_ACOES:
        return (
            f"As cotas mínimas somam {_acoes(motivo.exigido)}, acima do máximo de "
            f"{motivo.disponivel}: faltam {motivo.falta}.",
            "Aumente o máximo de ações ou reduza as cotas mínimas.",
        )
    return (
        f"As cotas mínimas exigem pelo menos {_formatar_reais(motivo.exigido)}, acima do "
        f"orçamento de {_formatar_reais(motivo.disponivel)}: faltam "
        f"{_formatar_reais(motivo.falta)}.",
        "Mesmo com a ação mais barata para cada parceiro que as cotas exigem, o orçamento não "
        "paga. Aumente o orçamento ou reduza as cotas mínimas.",
    )


# ------------------------------------------------------------ a execução
def iniciar(
    s: Session, parametros: ParametrosCampanha, *, usuario_id: int | None
) -> ExecucaoOtimizador:
    """Grava uma execução em andamento, ou recusa dizendo por quê.

    O "uma por vez" é conferido duas vezes, como no treino: a consulta dá a
    recusa com a execução que está rodando, e o índice único parcial fecha a
    corrida entre duas requisições que passem pela consulta ao mesmo tempo.
    """
    recusa = bloqueio(s)
    if recusa is not None:
        raise recusa
    ids = {c.categoria_id for c in parametros.cotas_categoria}
    existentes = set(s.scalars(select(Categoria.id).where(Categoria.id.in_(ids))))
    if ids - existentes:
        raise OtimizacaoRecusada(
            "Há cota para uma categoria que não existe.",
            "Escolha as categorias da lista.",
            status=422,
            categorias=sorted(ids - existentes),
        )

    concluido = servico_previsao.ultimo_concluido(s)
    execucao = ExecucaoOtimizador(
        usuario_id=usuario_id,
        modo=ModoExecucao.SERIAL,
        parametros=parametros.model_dump(mode="json"),
        periodo_base_id=concluido.periodo_base_id,
        modelo_versao=concluido.versao_em_uso,
        semente=SEMENTE,
    )
    try:
        with s.begin_nested():
            s.add(execucao)
            s.flush()
    except IntegrityError:
        raise _recusa_por_andamento(em_andamento(s)) from None
    return execucao


def _concluir(s: Session, execucao: ExecucaoOtimizador, inicio: float, detalhes: dict) -> None:
    execucao.detalhes = detalhes
    execucao.tempo_ms = round((time.perf_counter() - inicio) * 1000)
    execucao.situacao = SituacaoExecucao.CONCLUIDA
    # `clock_timestamp()`, e não `now()`: `now()` é o início da transação (#113).
    execucao.concluida_em = s.scalar(select(func.clock_timestamp()))
    s.flush()


def _cotas(m: Montagem, genes: tuple[int, ...] | None) -> list[dict]:
    """As cotas em contagem, com quantas ações o plano deu a cada uma."""
    inst = m.instancia
    por_categoria = [0] * inst.categorias
    na_cauda = 0
    for i, g in enumerate(genes or ()):
        if g:
            if inst.categoria[i] >= 0:
                por_categoria[inst.categoria[i]] += 1
            na_cauda += inst.cauda[i]
    cotas = [
        {
            "categoria_id": c.id,
            "nome": c.nome,
            "acoes": por_categoria[k] if genes is not None else None,
            "minimo": inst.minimo_categoria[k],
            "maximo": inst.maximo_categoria[k],
        }
        for k, c in enumerate(m.categorias)
        if inst.minimo_categoria[k] > 0 or inst.maximo_categoria[k] < inst.maximo_acoes
    ]
    if inst.minimo_cauda:
        cotas.append(
            {
                "categoria_id": None,
                "nome": "Cauda longa",
                "acoes": na_cauda if genes is not None else None,
                "minimo": inst.minimo_cauda,
                "maximo": inst.maximo_acoes,
            }
        )
    return cotas


def _executar(s: Session, execucao: ExecucaoOtimizador) -> None:
    inicio = time.perf_counter()
    m = montar(s, execucao)
    inst = m.instancia
    detalhes = {
        "elegiveis": inst.parceiros,
        "excluidos": excluidos(s, execucao.periodo_base_id, execucao.modelo_versao),
        "top_n": m.top_n,
    }

    motivo = gih_nucleo.verificar_viabilidade(inst)
    if motivo is not None:
        erro, ajuda = texto_da_recusa(motivo, m)
        execucao.viavel = False
        execucao.restricao_violada = motivo.restricao
        execucao.motivo = erro
        _concluir(s, execucao, inicio, {**detalhes, "ajuda": ajuda, "cotas": _cotas(m, None)})
        return

    resultado = gih_nucleo.otimizar(inst, semente=execucao.semente, limite_s=LIMITE_S)
    # A segunda chave da RN07: o verificador não reaproveita a avaliação que a
    # busca usou. Plano que não passa aqui é defeito, e vira falha — nunca plano.
    problemas = gih_nucleo.verificar_plano(inst, resultado.genes)
    if problemas:
        raise RuntimeError(f"O otimizador devolveu um plano fora das restrições: {problemas}")

    plano = PlanoCampanha(
        execucao_id=execucao.id,
        aplicacao_inicio=m.parametros.aplicacao_inicio,
        aplicacao_fim=m.parametros.aplicacao_fim,
    )
    s.add(plano)
    s.flush()
    linhas = [
        {
            "plano_id": plano.id,
            "parceiro_id": m.parceiros[i].parceiro_id,
            "acao_id": m.acoes[g - 1].id,
            "uplift_esperado": reais(inst.ganho[i][g - 1]),
            "custo": m.acoes[g - 1].custo_unitario,
        }
        for i, g in enumerate(resultado.genes)
        if g
    ]
    if linhas:
        s.execute(insert(ItemPlano), linhas)

    avaliacao = resultado.avaliacao
    guloso = max(
        gih_nucleo.avaliar(inst, gih_nucleo.guloso(inst, criterio)).ganho
        for criterio in (RAZAO, GANHO)
    )
    execucao.viavel = True
    execucao.uplift_total = reais(avaliacao.ganho)
    execucao.custo_total = reais(avaliacao.custo)
    execucao.parcial = resultado.parcial
    _concluir(
        s,
        execucao,
        inicio,
        {
            **detalhes,
            "acoes": avaliacao.acoes,
            "cotas": _cotas(m, resultado.genes),
            "folga_orcamento": str(reais(inst.orcamento - avaliacao.custo)),
            "folga_acoes": inst.maximo_acoes - avaliacao.acoes,
            "ganho_guloso": str(reais(guloso)),
            "na_cauda": [
                m.parceiros[i].parceiro_id
                for i, g in enumerate(resultado.genes)
                if g and inst.cauda[i]
            ],
            "busca": {
                "partidas": resultado.partidas,
                "geracoes": resultado.geracoes,
                "segundos": round(resultado.segundos, 2),
            },
        },
    )


def executar(execucao_id: int, *, origem: str | None = None) -> None:
    """Roda a execução gravada por `iniciar`. É o que vai para segundo plano.

    **Nunca propaga exceção**, pelo mesmo motivo do treino: em segundo plano
    não há quem a receba, e a execução ficaria em andamento para sempre,
    prendendo a trava. Falha vira `FALHOU` com o motivo, e o detalhe técnico
    vai para o log com um identificador de correlação (RNF18, RNF19).
    """
    usuario_id = None
    try:
        with sessao() as s:
            execucao = s.get(ExecucaoOtimizador, execucao_id)
            usuario_id = execucao.usuario_id
            _executar(s, execucao)
            detalhes = {
                "execucao": execucao.id,
                "modo": str(execucao.modo),
                "parametros": execucao.parametros,
                "viavel": execucao.viavel,
                "restricao_violada": execucao.restricao_violada,
                "uplift_total": str(execucao.uplift_total) if execucao.uplift_total else None,
                "custo_total": str(execucao.custo_total) if execucao.custo_total else None,
                "tempo_ms": execucao.tempo_ms,
            }
        auditoria.registrar(
            Acao.OTIMIZACAO_EXECUTADA, usuario_id=usuario_id, detalhes=detalhes, origem=origem
        )
    except Exception:
        correlacao = uuid.uuid4().hex[:12]
        log.exception("[%s] Otimização %s falhou", correlacao, execucao_id)
        motivo = f"A otimização falhou por um erro interno (registro {correlacao})."
        _marcar_falha(execucao_id, motivo)
        auditoria.registrar(
            Acao.OTIMIZACAO_FALHOU,
            usuario_id=usuario_id,
            detalhes={"execucao": execucao_id, "motivo": motivo},
            origem=origem,
        )


def _marcar_falha(execucao_id: int, motivo: str) -> None:
    try:
        with sessao() as s:
            execucao = s.get(ExecucaoOtimizador, execucao_id)
            if execucao is not None and execucao.situacao == SituacaoExecucao.EM_ANDAMENTO:
                execucao.situacao = SituacaoExecucao.FALHOU
                execucao.concluida_em = s.scalar(select(func.clock_timestamp()))
                execucao.motivo = motivo
    except Exception:
        log.exception("Não foi possível marcar a otimização %s como falha", execucao_id)


def recuperar_interrompidas(s: Session) -> int:
    """Marca como falhas as execuções que ficaram em andamento — chamada na subida.

    Mesma razão e mesma premissa do treino: sem isto a trava ficaria fechada
    para sempre, e vale porque a API roda num processo só.
    """
    interrompidas = list(
        s.scalars(
            select(ExecucaoOtimizador).where(
                ExecucaoOtimizador.situacao == SituacaoExecucao.EM_ANDAMENTO
            )
        )
    )
    agora = s.scalar(select(func.now()))
    for execucao in interrompidas:
        execucao.situacao = SituacaoExecucao.FALHOU
        execucao.concluida_em = agora
        execucao.motivo = "Interrompida: a API reiniciou durante a otimização. Calcule de novo."
    return len(interrompidas)
