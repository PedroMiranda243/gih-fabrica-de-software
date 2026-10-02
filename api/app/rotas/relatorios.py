"""Relatórios: desempenho, risco, campanha e operações (UC15 · RF44 a RF48 · H84 a H88).

Caso de uso de **consulta**: nenhuma rota daqui altera estado, e por isso nenhuma
audita — como o painel. As consultas e as regras estão em `servico_relatorios`;
aqui ficam os filtros, o perfil de quem pode e o formato da resposta.

**Cada relatório tem o seu CSV, na mesma leitura** (RF48). A rota do arquivo
recebe os mesmos filtros e chama a mesma função do serviço: exportar um recorte
diferente do que está na tela é pior que não exportar. Todo texto que veio de
quem cadastra — o nome do parceiro, o da categoria, o da ação — passa por
`planilha.texto`, que impede a planilha de executá-lo como fórmula.

Perfis: os três relatórios da rede são do Gestor e do Analista; o de operações,
que resume a trilha de auditoria, é do Administrador (RF08).
"""
from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app import formato, planilha, servico_relatorios
from app.auditoria import Acao
from app.dependencias import Banco, exigir
from app.desempenho import ROTULO_SEGMENTO
from app.esquemas import (
    PlanoResumido,
    RelatorioCampanha,
    RelatorioDesempenho,
    RelatorioOperacoes,
    RelatorioRisco,
)
from app.modelos import Perfil, Segmento
from app.servico_previsao import SEM_TREINO
from app.servico_relatorios import RelatorioRecusado

router = APIRouter(prefix="/api/relatorios", tags=["relatórios"])

DA_REDE = [Depends(exigir(Perfil.GESTOR, Perfil.ANALISTA))]
DA_TRILHA = [Depends(exigir(Perfil.ADMINISTRADOR))]

TAMANHO_MAXIMO = 200

PeriodoId = Annotated[int | None, Query(description="Padrão: o período mais recente.")]
CategoriaId = Annotated[int | None, Query(description="Padrão: a rede inteira.")]
DoSegmento = Annotated[Segmento | None, Query(description="Padrão: todos os segmentos.")]
RiscoMinimo = Annotated[
    float | None,
    Query(ge=0, le=1, description="Só quem tem chance de queda a partir desta, de 0 a 1."),
]
ExecucaoId = Annotated[int | None, Query(description="Padrão: o último plano viável.")]
De = Annotated[date | None, Query(description="Data inicial, inclusiva.")]
Ate = Annotated[date | None, Query(description="Data final, inclusiva.")]
Autor = Annotated[int | None, Query(description="Id do usuário que executou a ação.")]
DaAcao = Annotated[Acao | None, Query()]


def _recusa(recusa: RelatorioRecusado) -> HTTPException:
    return HTTPException(
        status_code=recusa.status, detail={"erro": recusa.erro, "ajuda": recusa.ajuda}
    )


def _arquivo(nome: str, conteudo: Iterable[str]) -> StreamingResponse:
    return StreamingResponse(
        conteudo,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )


def _grupos(blocos: Iterable[tuple[str, list]], campos) -> list[tuple]:
    """As linhas de um relatório agregado: uma por grupo, com o agrupamento na frente."""
    return [
        (agrupamento, planilha.texto(linha.rotulo), *campos(linha))
        for agrupamento, linhas in blocos
        for linha in linhas
    ]


# ================================================== 1. desempenho (RF44, H84)
def _ler_desempenho(s, periodo_id, categoria_id, segmento) -> RelatorioDesempenho:
    try:
        return servico_relatorios.desempenho(
            s, periodo_id=periodo_id, categoria_id=categoria_id, segmento=segmento
        )
    except RelatorioRecusado as recusa:
        raise _recusa(recusa) from recusa


@router.get("/desempenho", response_model=RelatorioDesempenho, dependencies=DA_REDE)
def desempenho(
    s: Banco,
    periodo_id: PeriodoId = None,
    categoria_id: CategoriaId = None,
    segmento: DoSegmento = None,
) -> RelatorioDesempenho:
    """O desempenho de um período, por categoria e por segmento (RF44, H84)."""
    return _ler_desempenho(s, periodo_id, categoria_id, segmento)


CABECALHO_DESEMPENHO = (
    "Agrupamento", "Grupo", "Parceiros", "Faturamento", "Pedidos", "Ticket médio", "Variação %",
)


@router.get("/desempenho/exportacao.csv", response_class=StreamingResponse, dependencies=DA_REDE)
def exportar_desempenho(
    s: Banco,
    periodo_id: PeriodoId = None,
    categoria_id: CategoriaId = None,
    segmento: DoSegmento = None,
) -> StreamingResponse:
    """O mesmo relatório, em CSV (RF48): as categorias, os segmentos e o total."""
    relatorio = _ler_desempenho(s, periodo_id, categoria_id, segmento)
    linhas = _grupos(
        (
            ("Categoria", relatorio.por_categoria),
            ("Segmento", relatorio.por_segmento),
            ("Total", [relatorio.total] if relatorio.total else []),
        ),
        lambda linha: (
            linha.parceiros,
            planilha.numero(linha.faturamento),
            linha.pedidos,
            planilha.numero(linha.ticket_medio),
            planilha.numero(linha.variacao_percentual),
        ),
    )
    quando = relatorio.periodo.data_fim.isoformat() if relatorio.periodo else "sem-periodo"
    return _arquivo(
        f"relatorio-desempenho-{quando}.csv", planilha.de_linhas(CABECALHO_DESEMPENHO, linhas)
    )


# ======================================================= 2. risco (RF45, H85)
@router.get("/risco", response_model=RelatorioRisco, dependencies=DA_REDE)
def risco(
    s: Banco,
    categoria_id: CategoriaId = None,
    segmento: DoSegmento = None,
    risco_minimo: RiscoMinimo = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamanho: Annotated[int, Query(ge=1, le=TAMANHO_MAXIMO)] = 50,
) -> RelatorioRisco:
    """Quem está em risco e quem o modelo prevê que caia (RF45, H85).

    `risco_minimo` é um filtro de quem consulta, e não um limiar do sistema:
    ninguém é "de risco" por passar dele, e sem ele o relatório traz todos.
    """
    try:
        return servico_relatorios.risco(
            s,
            categoria_id=categoria_id,
            segmento=segmento,
            risco_minimo=risco_minimo,
            pagina=pagina,
            tamanho=tamanho,
        )
    except RelatorioRecusado as recusa:
        raise _recusa(recusa) from recusa


CABECALHO_RISCO = (
    "Parceiro", "Categoria", "Segmento", "Faturamento", "Variação %", "Faturamento previsto",
    "Risco de queda", "Sem previsão", "Ação no último plano", "Custo da ação",
)


def _linha_de_risco_csv(bruta) -> tuple:
    """Uma linha do arquivo, pela mesma montagem da tela (`linha_de_risco`)."""
    linha = servico_relatorios.linha_de_risco(bruta)
    return (
        planilha.texto(linha.nome),
        planilha.texto(linha.categoria),
        ROTULO_SEGMENTO.get(linha.segmento, ""),
        planilha.numero(linha.faturamento),
        planilha.numero(linha.variacao_percentual),
        planilha.numero(linha.faturamento_previsto),
        # O mesmo texto da tela — "24%", "menos de 1%" —, e não a fração crua: a
        # estimativa não finge no arquivo a certeza que não finge na tela.
        (
            ""
            if linha.probabilidade_queda is None
            else formato.probabilidade(linha.probabilidade_queda)
        ),
        linha.sem_previsao or "",
        planilha.texto(linha.acao),
        planilha.numero(linha.custo),
    )


@router.get("/risco/exportacao.csv", response_class=StreamingResponse, dependencies=DA_REDE)
def exportar_risco(
    s: Banco,
    categoria_id: CategoriaId = None,
    segmento: DoSegmento = None,
    risco_minimo: RiscoMinimo = None,
) -> StreamingResponse:
    """O recorte inteiro, sem paginação, em fluxo (RF48) — uma linha por parceiro."""
    try:
        categoria = servico_relatorios.categoria_do_recorte(s, categoria_id)
    except RelatorioRecusado as recusa:
        raise _recusa(recusa) from recusa
    lida = servico_relatorios.consulta_de_risco(
        s, categoria=categoria, segmento=segmento, risco_minimo=risco_minimo
    )
    if lida is None:
        motivo, ajuda = SEM_TREINO
        raise HTTPException(status_code=409, detail={"erro": motivo, "ajuda": ajuda})
    return _arquivo(
        f"relatorio-risco-{lida.base.data_fim.isoformat()}.csv",
        planilha.gerar(CABECALHO_RISCO, lida.consulta, _linha_de_risco_csv),
    )


# ==================================================== 3. campanha (RF46, H86)
def _ler_campanha(s, execucao_id) -> RelatorioCampanha:
    try:
        return servico_relatorios.campanha(s, execucao_id=execucao_id)
    except RelatorioRecusado as recusa:
        raise _recusa(recusa) from recusa


@router.get("/campanha", response_model=RelatorioCampanha, dependencies=DA_REDE)
def campanha(s: Banco, execucao_id: ExecucaoId = None) -> RelatorioCampanha:
    """Onde a verba de um plano foi, por ação, por categoria e por segmento (RF46, H86)."""
    return _ler_campanha(s, execucao_id)


@router.get("/campanha/planos", response_model=list[PlanoResumido], dependencies=DA_REDE)
def planos_da_campanha(s: Banco) -> list[PlanoResumido]:
    """Os planos que o relatório oferece para escolher, do mais recente ao mais antigo.

    Quem decide que execução tem plano é a API, e não a tela: a lista traz só as
    concluídas e viáveis (RN07).
    """
    return servico_relatorios.planos(s)


CABECALHO_CAMPANHA = ("Agrupamento", "Grupo", "Parceiros", "Custo", "Ganho esperado")


@router.get("/campanha/exportacao.csv", response_class=StreamingResponse, dependencies=DA_REDE)
def exportar_campanha(s: Banco, execucao_id: ExecucaoId = None) -> StreamingResponse:
    """O mesmo relatório, em CSV (RF48). Sem plano não há arquivo, e a resposta diz por quê."""
    relatorio = _ler_campanha(s, execucao_id)
    if relatorio.plano is None:
        raise HTTPException(
            status_code=409,
            detail={
                "erro": "Nenhum plano de campanha foi calculado ainda.",
                "ajuda": (
                    "O plano sai da tela Campanha, com o orçamento, o máximo de ações e as cotas."
                ),
            },
        )
    linhas = _grupos(
        (
            ("Ação", relatorio.por_acao),
            ("Categoria", relatorio.por_categoria),
            ("Segmento", relatorio.por_segmento),
            ("Total", [relatorio.total]),
        ),
        lambda linha: (
            linha.parceiros,
            planilha.numero(linha.custo),
            planilha.numero(linha.ganho_esperado),
        ),
    )
    return _arquivo(
        f"relatorio-campanha-execucao-{relatorio.plano.execucao_id}.csv",
        planilha.de_linhas(CABECALHO_CAMPANHA, linhas),
    )


# =================================================== 4. operações (RF47, H87)
def _ler_operacoes(s, de, ate, autor, acao) -> RelatorioOperacoes:
    try:
        return servico_relatorios.operacoes(s, de=de, ate=ate, autor=autor, acao=acao)
    except RelatorioRecusado as recusa:
        raise _recusa(recusa) from recusa


@router.get("/operacoes", response_model=RelatorioOperacoes, dependencies=DA_TRILHA)
def operacoes(
    s: Banco, de: De = None, ate: Ate = None, autor: Autor = None, acao: DaAcao = None
) -> RelatorioOperacoes:
    """O que foi feito no sistema, por tipo de ação, por usuário e por dia (RF47, H87)."""
    return _ler_operacoes(s, de, ate, autor, acao)


CABECALHO_OPERACOES = ("Agrupamento", "Grupo", "Operações")


@router.get("/operacoes/exportacao.csv", response_class=StreamingResponse, dependencies=DA_TRILHA)
def exportar_operacoes(
    s: Banco, de: De = None, ate: Ate = None, autor: Autor = None, acao: DaAcao = None
) -> StreamingResponse:
    """O mesmo relatório, em CSV (RF48)."""
    relatorio = _ler_operacoes(s, de, ate, autor, acao)
    linhas = _grupos(
        (
            ("Ação", relatorio.por_acao),
            ("Usuário", relatorio.por_usuario),
            ("Dia", relatorio.por_dia),
        ),
        lambda linha: (linha.total,),
    )
    linhas.append(("Total", "", relatorio.total))
    return _arquivo(
        f"relatorio-operacoes-{relatorio.de.isoformat()}-a-{relatorio.ate.isoformat()}.csv",
        planilha.de_linhas(CABECALHO_OPERACOES, linhas),
    )
