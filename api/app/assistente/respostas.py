"""As respostas do catálogo: cada tipo de pergunta, respondido pelo código.

**Os números saem das funções das telas** — o painel, o ranking, a previsão, a
campanha. O assistente não tem consulta própria para o que uma tela já mostra:
uma segunda consulta para a mesma pergunta divergiria na primeira correção, e a
resposta diria um número que o painel não diz.

**Cada resposta traz os fatos que a sustentam**, já formatados como a tela os
mostra. Todo número do texto está neles — os testes conferem com a guarda
numérica —, e é contra eles que a guarda vai conferir o texto que o modelo
redigir (RN08, H67). O texto daqui é o **modelo fixo**: o que sai quando o
modelo não redige, ou quando redige com número sem origem.

Toda resposta diz de que período são os dados (RF42).
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import formato, servico_otimizacao, servico_previsao
from app.calculos import ticket_medio, variacao_percentual
from app.desempenho import ROTULO_SEGMENTO, periodo_anterior, serie_historica
from app.esquemas import ParametrosCampanha, SituacaoResposta, TipoPergunta
from app.modelos import (
    Categoria,
    HistoricoSegmento,
    ItemPlano,
    Metrica,
    Parceiro,
    Periodo,
    PlanoCampanha,
    Segmento,
)
from app.ranking import posicoes
from app.rotas import painel

# O tamanho de uma lista na resposta. Mais que isso é tela, e não resposta: o
# painel e a lista de parceiros têm a paginação e o filtro.
QUANTOS_PADRAO = 10
MAXIMO_NA_LISTA = 20
# A evolução sem data: dois meses de semanas.
PERIODOS_NA_EVOLUCAO = 8


@dataclass
class Resposta:
    situacao: SituacaoResposta
    texto: str
    fatos: list[dict] = field(default_factory=list)
    candidatos: list[str] = field(default_factory=list)


def respondida(texto: str, fatos: list[dict]) -> Resposta:
    return Resposta(SituacaoResposta.RESPONDIDA, texto, fatos)


def abstencao(texto: str, fatos: list[dict] | None = None) -> Resposta:
    """Não há base para responder (UC12-A1): dizer isso é a resposta certa."""
    return Resposta(SituacaoResposta.ABSTENCAO, texto, fatos or [])


def precisao(texto: str, candidatos: list[str] | None = None, fatos=None) -> Resposta:
    """Falta dizer qual — o parceiro, o período, o segmento (UC12-A2). Escolher sozinho
    seria responder com confiança sobre a interpretação errada."""
    return Resposta(SituacaoResposta.PRECISAO, texto, fatos or [], candidatos or [])


def fato(nome: str, valor: str) -> dict:
    return {"fato": nome, "valor": valor}


@dataclass
class Contexto:
    """A pergunta resolvida: as entidades da base, e não mais o texto do modelo."""

    s: Session
    parceiro: Parceiro | None = None
    categoria: Categoria | None = None
    segmento: Segmento | None = None
    # Do mais antigo ao mais recente. Nos tipos de um período só, é um.
    periodos: list[Periodo] = field(default_factory=list)
    quantos: int = QUANTOS_PADRAO

    @property
    def periodo(self) -> Periodo:
        return self.periodos[-1]


# ------------------------------------------------------------------- apoio
PARCEIRO = "Parceiro"
PERIODO = "Período"
PERIODO_ANTERIOR = "Período anterior"
FATURAMENTO = "Faturamento"
FATURAMENTO_ANTERIOR = "Faturamento no período anterior"
PEDIDOS = "Pedidos"
TICKET = "Ticket médio"
VARIACAO = "Variação do faturamento"
POSICAO = "Posição no ranking"
POSICAO_ANTERIOR = "Posição no período anterior"
COM_FATURAMENTO = "Parceiros com faturamento"
SEGMENTO = "Segmento"
SEGMENTO_ANTERIOR = "Segmento no período anterior"
CATEGORIA = "Categoria"
TOTAL = "Total"
MOTIVO = "Motivo"


def _intervalo(p) -> str:
    return formato.intervalo(p.data_inicio, p.data_fim)


def _contagem(n: int, singular: str, plural: str) -> str:
    return f"{formato.inteiro(n)} {singular if n == 1 else plural}"


def _metrica(s: Session, parceiro_id: int, periodo_id: int) -> Metrica | None:
    return s.scalar(
        select(Metrica).where(Metrica.parceiro_id == parceiro_id, Metrica.periodo_id == periodo_id)
    )


def _posicao(s: Session, parceiro_id: int, periodo_id: int) -> tuple[int | None, int]:
    """A posição do parceiro e quantos entraram no ranking — o mesmo cálculo do painel."""
    ranking = posicoes(periodo_id).subquery("ranking")
    posicao = s.scalar(select(ranking.c.posicao).where(ranking.c.parceiro_id == parceiro_id))
    total = s.scalar(select(func.count()).select_from(ranking)) or 0
    return posicao, total


def _segmento(s: Session, parceiro_id: int, periodo_id: int) -> Segmento | None:
    return s.scalar(
        select(HistoricoSegmento.segmento).where(
            HistoricoSegmento.parceiro_id == parceiro_id,
            HistoricoSegmento.periodo_id == periodo_id,
        )
    )


def _segmentado(s: Session, periodo_id: int) -> bool:
    return bool(
        s.scalar(
            select(func.count())
            .select_from(HistoricoSegmento)
            .where(HistoricoSegmento.periodo_id == periodo_id)
        )
    )


def _sem_segmentacao(periodo: Periodo, fatos: list[dict]) -> Resposta:
    # "Ninguém" afirmaria uma distribuição que ninguém calculou.
    return abstencao(
        f"O período de {_intervalo(periodo)} ainda não tem segmentação calculada.", fatos
    )


# ------------------------------------------------------------ do parceiro
def desempenho_do_parceiro(c: Contexto) -> Resposta:
    p, periodo = c.parceiro, c.periodo
    fatos = [fato(PARCEIRO, p.nome), fato(PERIODO, _intervalo(periodo))]
    atual = _metrica(c.s, p.id, periodo.id)
    if atual is None:
        return abstencao(
            f"O relatório de {_intervalo(periodo)} não trouxe {p.nome}: não há faturamento "
            "dele nesse período.",
            fatos,
        )

    fatos += [
        fato(FATURAMENTO, formato.reais(atual.faturamento)),
        fato(PEDIDOS, formato.inteiro(atual.pedidos)),
    ]
    texto = (
        f"{p.nome} faturou {formato.reais(atual.faturamento)} em "
        f"{_contagem(atual.pedidos, 'pedido', 'pedidos')} de {_intervalo(periodo)}"
    )
    ticket = ticket_medio(atual.faturamento, atual.pedidos)
    if ticket is not None:
        fatos.append(fato(TICKET, formato.reais(ticket)))
        texto += f", com ticket médio de {formato.reais(ticket)}"
    texto += "."

    anterior = periodo_anterior(c.s, periodo)
    if anterior is None:
        texto += " É o primeiro período importado: não há com o que comparar."
        return respondida(texto, fatos)
    fatos.append(fato(PERIODO_ANTERIOR, _intervalo(anterior)))
    antes = _metrica(c.s, p.id, anterior.id)
    if antes is None:
        texto += f" No período anterior, de {_intervalo(anterior)}, não há dados dele."
        return respondida(texto, fatos)
    fatos.append(fato(FATURAMENTO_ANTERIOR, formato.reais(antes.faturamento)))
    texto += (
        f" No período anterior, de {_intervalo(anterior)}, tinha faturado "
        f"{formato.reais(antes.faturamento)}"
    )
    variacao = variacao_percentual(atual.faturamento, antes.faturamento)
    if variacao is not None:
        fatos.append(fato(VARIACAO, formato.percentual(variacao)))
        texto += f": uma variação de {formato.percentual(variacao)}"
    return respondida(texto + ".", fatos)


def evolucao_do_parceiro(c: Contexto) -> Resposta:
    p = c.parceiro
    inicio, fim = c.periodos[0].data_inicio, c.periodos[-1].data_fim
    fatos = [fato(PARCEIRO, p.nome)]
    pontos = serie_historica(c.s, p.id, de=inicio, ate=fim)
    # Antes da primeira medição dele não havia o que medir: listar esses períodos
    # como "sem dados" diria que ele deixou de vender (como no portal, H39).
    primeiro = next((i for i, ponto in enumerate(pontos) if ponto.faturamento is not None), None)
    if primeiro is None:
        fatos.append(fato(PERIODO, formato.intervalo(inicio, fim)))
        return abstencao(
            f"Não há dados de {p.nome} de {formato.data(inicio)} a {formato.data(fim)}.", fatos
        )

    linhas = []
    for ponto in pontos[primeiro:]:
        quando = _intervalo(ponto.periodo)
        if ponto.faturamento is None:
            valor = "sem dados"
        else:
            valor = (
                f"{formato.reais(ponto.faturamento)} em "
                f"{_contagem(ponto.pedidos, 'pedido', 'pedidos')}"
            )
        fatos.append(fato(quando, valor))
        linhas.append(f"- {quando}: {valor}")
    return respondida(f"O faturamento de {p.nome}, período a período:\n" + "\n".join(linhas), fatos)


def posicao_do_parceiro(c: Contexto) -> Resposta:
    p, periodo = c.parceiro, c.periodo
    fatos = [fato(PARCEIRO, p.nome), fato(PERIODO, _intervalo(periodo))]
    posicao, total = _posicao(c.s, p.id, periodo.id)
    if posicao is None:
        return abstencao(
            f"{p.nome} não teve faturamento em {_intervalo(periodo)}, e fica fora do ranking "
            "desse período.",
            fatos,
        )

    fatos += [
        fato(POSICAO, formato.ordinal(posicao)),
        fato(COM_FATURAMENTO, formato.inteiro(total)),
    ]
    texto = (
        f"{p.nome} ficou em {formato.ordinal(posicao)} lugar no ranking de faturamento de "
        f"{_intervalo(periodo)}, entre {_contagem(total, 'parceiro', 'parceiros')} com "
        "faturamento."
    )
    anterior = periodo_anterior(c.s, periodo)
    if anterior is not None:
        fatos.append(fato(PERIODO_ANTERIOR, _intervalo(anterior)))
        antes, _ = _posicao(c.s, p.id, anterior.id)
        if antes is None:
            texto += f" No período anterior, de {_intervalo(anterior)}, não teve faturamento."
        else:
            fatos.append(fato(POSICAO_ANTERIOR, formato.ordinal(antes)))
            texto += (
                f" No período anterior, de {_intervalo(anterior)}, estava em "
                f"{formato.ordinal(antes)}."
            )
    return respondida(texto, fatos)


def segmento_do_parceiro(c: Contexto) -> Resposta:
    p, periodo = c.parceiro, c.periodo
    fatos = [fato(PARCEIRO, p.nome), fato(PERIODO, _intervalo(periodo))]
    segmento = _segmento(c.s, p.id, periodo.id)
    if segmento is None:
        return abstencao(
            f"Não há segmento calculado para {p.nome} em {_intervalo(periodo)}.", fatos
        )

    rotulo = ROTULO_SEGMENTO[segmento]
    fatos.append(fato(SEGMENTO, rotulo))
    texto = f"Em {_intervalo(periodo)}, {p.nome} está no segmento {rotulo}."
    anterior = periodo_anterior(c.s, periodo)
    antes = _segmento(c.s, p.id, anterior.id) if anterior is not None else None
    if antes is not None:
        fatos.append(fato(PERIODO_ANTERIOR, _intervalo(anterior)))
        if antes == segmento:
            texto += f" No período anterior, de {_intervalo(anterior)}, estava no mesmo."
        else:
            fatos.append(fato(SEGMENTO_ANTERIOR, ROTULO_SEGMENTO[antes]))
            texto += (
                f" No período anterior, de {_intervalo(anterior)}, estava em "
                f"{ROTULO_SEGMENTO[antes]}."
            )
    return respondida(texto, fatos)


def previsao_do_parceiro(c: Contexto) -> Resposta:
    p = c.parceiro
    fatos = [fato(PARCEIRO, p.nome)]
    lida = servico_previsao.previsao_do_parceiro(c.s, p.id)
    if lida.previsao is None:
        motivo = " ".join(t for t in (lida.motivo, lida.ajuda) if t)
        fatos.append(fato(MOTIVO, motivo))
        return abstencao(f"Não há previsão para {p.nome}. {motivo}", fatos)

    previsao = lida.previsao
    chance = formato.probabilidade(previsao.probabilidade_queda)
    previsto = formato.reais(previsao.faturamento_previsto)
    fatos += [
        fato("Versão do modelo", lida.versao),
        fato("Dados do treino até", _intervalo(lida.periodo_base)),
        fato("Probabilidade de entrar em risco", chance),
        fato("Faturamento previsto", previsto),
    ]
    texto = (
        f"Pelo modelo {lida.versao}, treinado com os dados até {_intervalo(lida.periodo_base)}, "
        f"a probabilidade de {p.nome} estar em risco no período seguinte é de {chance}, e o "
        f"faturamento previsto é de {previsto}."
    )
    if lida.desatualizada:
        texto += (
            " Já há dados mais recentes que os do treino: a previsão só os considera depois "
            "de um novo treino."
        )
    return respondida(texto, fatos)


# -------------------------------------------------------------- da rede
def ranking(c: Contexto) -> Resposta:
    periodo = c.periodo
    fatos = [fato(PERIODO, _intervalo(periodo))]
    onde = ""
    if c.categoria is None:
        pagina = painel.ranking(c.s, periodo_id=periodo.id, pagina=1, tamanho=c.quantos)
        itens = [(i.posicao, i.nome, i.faturamento, None) for i in pagina.itens]
        total = pagina.total
    else:
        onde = f" na categoria {c.categoria.nome}"
        fatos.append(fato(CATEGORIA, c.categoria.nome))
        geral = posicoes(periodo.id).subquery("geral")
        consulta = (
            select(geral.c.posicao, Parceiro.nome, geral.c.faturamento)
            .join(Parceiro, Parceiro.id == geral.c.parceiro_id)
            .where(Parceiro.categoria_id == c.categoria.id)
        )
        total = c.s.scalar(select(func.count()).select_from(consulta.subquery())) or 0
        linhas = c.s.execute(consulta.order_by(geral.c.posicao).limit(c.quantos)).all()
        # A posição na categoria é a ordem do ranking geral filtrado: a mesma
        # regra, com o mesmo desempate, e a posição na rede ao lado.
        itens = [
            (i, nome, faturamento, na_rede)
            for i, (na_rede, nome, faturamento) in enumerate(linhas, start=1)
        ]

    if not itens:
        return abstencao(
            f"Nenhum parceiro{onde} teve faturamento em {_intervalo(periodo)}.", fatos
        )

    linhas_do_texto = []
    for posicao, nome, faturamento, na_rede in itens:
        valor = f"{nome} — {formato.reais(faturamento)}"
        if na_rede is not None:
            valor += f" ({formato.ordinal(na_rede)} na rede)"
        fatos.append(fato(formato.ordinal(posicao), valor))
        linhas_do_texto.append(f"{formato.ordinal(posicao)} {valor}")
    texto = f"Os maiores faturamentos{onde} em {_intervalo(periodo)}:\n" + "\n".join(
        linhas_do_texto
    )
    if total > len(itens):
        fatos.append(fato(COM_FATURAMENTO, formato.inteiro(total)))
        texto += (
            f"\nSão {_contagem(total, 'parceiro', 'parceiros')} com faturamento{onde}; o "
            "ranking inteiro está no painel."
        )
    return respondida(texto, fatos)


def parceiros_do_segmento(c: Contexto) -> Resposta:
    periodo, rotulo = c.periodo, ROTULO_SEGMENTO[c.segmento]
    fatos = [fato(PERIODO, _intervalo(periodo)), fato(SEGMENTO, rotulo)]
    if not _segmentado(c.s, periodo.id):
        return _sem_segmentacao(periodo, fatos)

    geral = posicoes(periodo.id).subquery("geral")
    consulta = (
        select(Parceiro.nome, geral.c.faturamento)
        .select_from(HistoricoSegmento)
        .join(Parceiro, Parceiro.id == HistoricoSegmento.parceiro_id)
        .outerjoin(geral, geral.c.parceiro_id == HistoricoSegmento.parceiro_id)
        .where(
            HistoricoSegmento.periodo_id == periodo.id,
            HistoricoSegmento.segmento == c.segmento,
        )
    )
    onde = ""
    if c.categoria is not None:
        onde = f" da categoria {c.categoria.nome}"
        fatos.append(fato(CATEGORIA, c.categoria.nome))
        consulta = consulta.where(Parceiro.categoria_id == c.categoria.id)
    total = c.s.scalar(select(func.count()).select_from(consulta.subquery())) or 0
    fatos.append(fato(TOTAL, formato.inteiro(total)))
    if not total:
        return respondida(
            f"Em {_intervalo(periodo)}, nenhum parceiro{onde} está no segmento {rotulo}.", fatos
        )

    linhas = c.s.execute(
        consulta.order_by(geral.c.posicao.asc().nulls_last(), Parceiro.nome).limit(c.quantos)
    ).all()
    verbo = "está" if total == 1 else "estão"
    texto = (
        f"Em {_intervalo(periodo)}, {_contagem(total, 'parceiro', 'parceiros')}{onde} {verbo} "
        f"no segmento {rotulo}"
    )
    texto += ":" if total == len(linhas) else ". Os de maior faturamento:"
    for nome, faturamento in linhas:
        valor = formato.reais(faturamento) if faturamento is not None else "sem faturamento"
        fatos.append(fato(nome, valor))
        texto += f"\n- {nome}: {valor}"
    if total > len(linhas):
        texto += "\nA lista inteira está na tela Parceiros, com o filtro do segmento."
    return respondida(texto, fatos)


def mobilidade_do_top(c: Contexto) -> Resposta:
    """Lida do ranking, e não do segmento (RN02): é a mesma função do painel."""
    periodo = c.periodo
    mobilidade = painel.mobilidade(c.s, periodo_id=periodo.id)
    top = f"Top {mobilidade.top_n}"
    fatos = [fato(PERIODO, _intervalo(periodo)), fato("Top", top)]
    if mobilidade.periodo_anterior is None:
        return abstencao(
            f"{_intervalo(periodo)} é o primeiro período importado: não há período anterior de "
            f"onde entrar ou sair do {top}.",
            fatos,
        )

    anterior = _intervalo(mobilidade.periodo_anterior)
    fatos.append(fato(PERIODO_ANTERIOR, anterior))
    partes = []
    if mobilidade.entradas:
        nomes = [f"{e.nome} ({formato.ordinal(e.posicao)})" for e in mobilidade.entradas]
        fatos += [fato("Entrou", n) for n in nomes]
        verbo = "entrou" if len(nomes) == 1 else "entraram"
        partes.append(f"{verbo} no {top}: {', '.join(nomes)}")
    if mobilidade.saidas:
        nomes = [
            f"{m.nome} (agora em {formato.ordinal(m.posicao)})"
            if m.posicao is not None
            else f"{m.nome} (sem faturamento no período)"
            for m in mobilidade.saidas
        ]
        fatos += [fato("Saiu", n) for n in nomes]
        verbo = "saiu" if len(nomes) == 1 else "saíram"
        partes.append(f"{verbo}: {', '.join(nomes)}")
    if not partes:
        texto = f"De {anterior} para {_intervalo(periodo)}, ninguém entrou nem saiu do {top}."
    else:
        texto = f"De {anterior} para {_intervalo(periodo)}, " + "; e ".join(partes) + "."
    return respondida(texto, fatos)


def resumo_do_periodo(c: Contexto) -> Resposta:
    periodo = c.periodo
    indicadores = painel.indicadores(c.s, periodo_id=periodo.id)
    fatos = [
        fato(PERIODO, _intervalo(periodo)),
        fato(FATURAMENTO, formato.reais(indicadores.faturamento)),
        fato(PEDIDOS, formato.inteiro(indicadores.pedidos)),
        fato("Parceiros com movimento", formato.inteiro(indicadores.parceiros_ativos)),
    ]
    texto = (
        f"Em {_intervalo(periodo)}, a rede faturou {formato.reais(indicadores.faturamento)} em "
        f"{_contagem(indicadores.pedidos, 'pedido', 'pedidos')}"
    )
    if indicadores.ticket_medio is not None:
        fatos.append(fato(TICKET, formato.reais(indicadores.ticket_medio)))
        texto += f", com ticket médio de {formato.reais(indicadores.ticket_medio)}"
    texto += (
        f", e {_contagem(indicadores.parceiros_ativos, 'parceiro teve', 'parceiros tiveram')} "
        "movimento."
    )

    if indicadores.variacao is not None and indicadores.periodo_anterior is not None:
        anterior = _intervalo(indicadores.periodo_anterior)
        comparacoes = []
        for nome, valor in (
            ("faturamento", indicadores.variacao.faturamento),
            ("pedidos", indicadores.variacao.pedidos),
            ("ticket médio", indicadores.variacao.ticket_medio),
        ):
            if valor is not None:
                fatos.append(fato(f"Variação de {nome}", formato.percentual(valor)))
                comparacoes.append(f"{nome} {formato.percentual(valor)}")
        if comparacoes:
            fatos.append(fato(PERIODO_ANTERIOR, anterior))
            texto += f" Contra o período anterior, de {anterior}: {', '.join(comparacoes)}."

    if indicadores.em_risco is not None:
        risco = indicadores.em_risco.total
        fatos.append(fato("Em risco", formato.inteiro(risco)))
        texto += f" {_contagem(risco, 'parceiro está', 'parceiros estão')} em risco."
    return respondida(texto, fatos)


def distribuicao_dos_segmentos(c: Contexto) -> Resposta:
    periodo = c.periodo
    distribuicao = painel.segmentos(c.s, periodo_id=periodo.id)
    fatos = [fato(PERIODO, _intervalo(periodo))]
    if not distribuicao.itens:
        return _sem_segmentacao(periodo, fatos)

    fatos.append(fato(TOTAL, formato.inteiro(distribuicao.total)))
    texto = (
        f"Os parceiros por segmento em {_intervalo(periodo)}, num total de "
        f"{formato.inteiro(distribuicao.total)}:"
    )
    for fatia in distribuicao.itens:
        rotulo = ROTULO_SEGMENTO[fatia.segmento]
        fatos.append(fato(rotulo, formato.inteiro(fatia.total)))
        texto += f"\n- {rotulo}: {formato.inteiro(fatia.total)}"
    return respondida(texto, fatos)


def ultimo_plano(c: Contexto) -> Resposta:
    execucao = servico_otimizacao.ultima_concluida(c.s)
    if execucao is None:
        return abstencao("Nenhum plano de campanha foi calculado ainda.")

    base = c.s.get(Periodo, execucao.periodo_base_id)
    fatos = [fato("Dados de", _intervalo(base))]
    if not execucao.viavel:
        motivo = execucao.motivo or execucao.restricao_violada or "sem motivo registrado"
        fatos.append(fato(MOTIVO, motivo))
        return respondida(
            f"O último cálculo, com os dados de {_intervalo(base)}, não encontrou plano viável: "
            f"{motivo}",
            fatos,
        )

    parametros = ParametrosCampanha.model_validate(execucao.parametros)
    acoes = (
        c.s.scalar(
            select(func.count())
            .select_from(ItemPlano)
            .join(PlanoCampanha, PlanoCampanha.id == ItemPlano.plano_id)
            .where(PlanoCampanha.execucao_id == execucao.id)
        )
        or 0
    )
    custo = execucao.custo_total or Decimal("0")
    ganho = execucao.uplift_total or Decimal("0")
    aplicacao = formato.intervalo(parametros.aplicacao_inicio, parametros.aplicacao_fim)
    fatos += [
        fato("Aplicação", aplicacao),
        fato("Ações", formato.inteiro(acoes)),
        fato("Custo", formato.reais(custo)),
        fato("Orçamento", formato.reais(parametros.orcamento)),
        fato("Ganho esperado", formato.reais(ganho)),
    ]
    texto = (
        f"O último plano calculado, para aplicar de {aplicacao}, tem "
        f"{_contagem(acoes, 'ação', 'ações')}, com custo de {formato.reais(custo)} do orçamento "
        f"de {formato.reais(parametros.orcamento)} e ganho esperado de {formato.reais(ganho)}. "
        f"Ele partiu dos dados de {_intervalo(base)}."
    )
    return respondida(texto, fatos)


RESPONDER: dict[TipoPergunta, Callable[[Contexto], Resposta]] = {
    TipoPergunta.DESEMPENHO_DO_PARCEIRO: desempenho_do_parceiro,
    TipoPergunta.EVOLUCAO_DO_PARCEIRO: evolucao_do_parceiro,
    TipoPergunta.POSICAO_DO_PARCEIRO: posicao_do_parceiro,
    TipoPergunta.SEGMENTO_DO_PARCEIRO: segmento_do_parceiro,
    TipoPergunta.PREVISAO_DO_PARCEIRO: previsao_do_parceiro,
    TipoPergunta.RANKING: ranking,
    TipoPergunta.PARCEIROS_DO_SEGMENTO: parceiros_do_segmento,
    TipoPergunta.MOBILIDADE_DO_TOP: mobilidade_do_top,
    TipoPergunta.RESUMO_DO_PERIODO: resumo_do_periodo,
    TipoPergunta.DISTRIBUICAO_DOS_SEGMENTOS: distribuicao_dos_segmentos,
    TipoPergunta.ULTIMO_PLANO: ultimo_plano,
}
