"""Os relatórios: desempenho, risco, campanha e operações (UC15 · RF44 a RF47 · H84 a H87).

**Os relatórios não calculam regra nova.** Eles leem o que os outros módulos
gravam, pelas mesmas escolhas do painel, da previsão e do plano: o período
anterior é o do painel, a versão da previsão é a do cadastro do parceiro, o
"último plano" é o da campanha, e o recorte da trilha é o da tela de auditoria.
Uma escolha diferente aqui faria o relatório discordar da tela que ele resume —
e por isso os testes conferem um contra o outro.

**Tudo agregado no banco** (RNF03): cada relatório são poucas consultas com
`GROUP BY`, com 500 ou com 10.000 parceiros. O ticket médio e a variação saem de
`app.calculos`, das somas — nunca de uma coluna, e nunca da média das médias
(RN04).

O módulo devolve os esquemas prontos; as rotas só leem os filtros e escolhem o
formato — a tela ou o CSV, que saem da mesma leitura.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import Select, and_, exists, func, nullslast, select
from sqlalchemy.orm import Session

from app import servico_auditoria, servico_otimizacao, servico_previsao
from app.auditoria import Acao
from app.calculos import ticket_medio, variacao_percentual
from app.desempenho import ROTULO_SEGMENTO, periodo_anterior
from app.esquemas import (
    CategoriaResposta,
    ContagemOperacao,
    LinhaCampanha,
    LinhaDesempenho,
    LinhaRisco,
    PeriodoResposta,
    PlanoResumido,
    RelatorioCampanha,
    RelatorioDesempenho,
    RelatorioOperacoes,
    RelatorioRisco,
)
from app.modelos import (
    AcaoComercial,
    Auditoria,
    Categoria,
    ExecucaoOtimizador,
    HistoricoSegmento,
    ItemPlano,
    Metrica,
    Parceiro,
    Periodo,
    PlanoCampanha,
    Previsao,
    Segmento,
    SituacaoExecucao,
    Usuario,
)

SEM_CATEGORIA = "Sem categoria"
SEM_SEGMENTO = "Sem segmento"
SEM_USUARIO = "sem usuário"

# O intervalo do relatório de operações quando ninguém escolhe as datas (RF47).
DIAS_PADRAO = 30


class RelatorioRecusado(Exception):
    """O relatório não sai, e a mensagem diz por quê e o que fazer."""

    def __init__(self, erro: str, ajuda: str, *, status: int) -> None:
        super().__init__(erro)
        self.erro = erro
        self.ajuda = ajuda
        self.status = status


def _reais(valor) -> Decimal:
    """Uma soma em reais, sempre com os centavos — a soma de nada vem do banco como `0`."""
    return Decimal(valor or 0).quantize(Decimal("0.01"))


def _periodo(s: Session, periodo_id: int | None) -> Periodo | None:
    """O período pedido, ou o mais recente. Id que não existe é recusa, e não o mais recente."""
    if periodo_id is None:
        return s.scalar(select(Periodo).order_by(Periodo.data_inicio.desc(), Periodo.id.desc()))
    periodo = s.get(Periodo, periodo_id)
    if periodo is None:
        raise RelatorioRecusado(
            f"Não existe período com id {periodo_id}.",
            "Escolha um dos períodos importados.",
            status=404,
        )
    return periodo


def categoria_do_recorte(s: Session, categoria_id: int | None) -> Categoria | None:
    if categoria_id is None:
        return None
    categoria = s.get(Categoria, categoria_id)
    if categoria is None:
        raise RelatorioRecusado(
            f"Não existe categoria com id {categoria_id}.",
            "Escolha uma das categorias cadastradas.",
            status=404,
        )
    return categoria


def _nomes_das_categorias(s: Session) -> dict[int, str]:
    return dict(s.execute(select(Categoria.id, Categoria.nome)).all())


def _rotulo_do_segmento(segmento: str | None) -> str:
    return ROTULO_SEGMENTO.get(Segmento(segmento), segmento) if segmento else SEM_SEGMENTO


# ================================================== 1. desempenho (RF44, H84)
def _desempenho_agrupado(
    s: Session,
    periodo: Periodo,
    grupo,
    *,
    categoria: Categoria | None,
    segmento: Segmento | None,
) -> dict[object, tuple[int, Decimal, int]]:
    """Parceiros, faturamento e pedidos de cada grupo num período — uma consulta.

    O segmento é o **daquele período**: a junção com o histórico usa o período da
    própria métrica, e por isso a mesma função serve ao período do relatório e
    ao anterior, cada um com a classificação que tinha.
    """
    consulta = (
        select(grupo, func.count(), func.sum(Metrica.faturamento), func.sum(Metrica.pedidos))
        .select_from(Metrica)
        .join(Parceiro, Parceiro.id == Metrica.parceiro_id)
        .outerjoin(
            HistoricoSegmento,
            and_(
                HistoricoSegmento.parceiro_id == Metrica.parceiro_id,
                HistoricoSegmento.periodo_id == Metrica.periodo_id,
            ),
        )
        .where(Metrica.periodo_id == periodo.id)
        .group_by(grupo)
    )
    if categoria is not None:
        consulta = consulta.where(Parceiro.categoria_id == categoria.id)
    if segmento is not None:
        consulta = consulta.where(HistoricoSegmento.segmento == segmento)
    return {
        chave: (int(parceiros), _reais(faturamento), int(pedidos or 0))
        for chave, parceiros, faturamento, pedidos in s.execute(consulta).all()
    }


def _dos_mesmos_parceiros(
    s: Session,
    periodo: Periodo,
    anterior: Periodo,
    grupo,
    *,
    categoria: Categoria | None,
    segmento: Segmento | None,
) -> dict[object, tuple[Decimal, Decimal]]:
    """O faturamento de agora e o de antes de **quem vendeu nos dois períodos**, por grupo.

    É a variação que faz sentido quando o grupo é um segmento. O segmento muda de
    um período para o outro: comparar "Em risco agora" com "Em risco antes"
    mediria quem entrou e quem saiu do segmento — na base de demonstração, o Em
    risco aparecia **crescendo 47%**, porque mais parceiros caíram nele. Aqui o
    grupo é o de agora, e a pergunta é como esses mesmos parceiros foram.

    Junção interna com o período anterior: o estreante não tem de onde variar, e
    fica fora das duas somas — como no ranking, em que a variação dele é nula.
    """
    passado = (
        select(Metrica.parceiro_id, Metrica.faturamento.label("antes"))
        .where(Metrica.periodo_id == anterior.id)
        .subquery("passado")
    )
    consulta = (
        select(grupo, func.sum(Metrica.faturamento), func.sum(passado.c.antes))
        .select_from(Metrica)
        .join(Parceiro, Parceiro.id == Metrica.parceiro_id)
        .join(passado, passado.c.parceiro_id == Metrica.parceiro_id)
        .outerjoin(
            HistoricoSegmento,
            and_(
                HistoricoSegmento.parceiro_id == Metrica.parceiro_id,
                HistoricoSegmento.periodo_id == Metrica.periodo_id,
            ),
        )
        .where(Metrica.periodo_id == periodo.id)
        .group_by(grupo)
    )
    if categoria is not None:
        consulta = consulta.where(Parceiro.categoria_id == categoria.id)
    if segmento is not None:
        consulta = consulta.where(HistoricoSegmento.segmento == segmento)
    return {chave: (_reais(agora), _reais(antes)) for chave, agora, antes in s.execute(consulta)}


def _variacoes(pares: dict[object, tuple[Decimal, Decimal]]) -> dict[object, Decimal | None]:
    return {chave: variacao_percentual(agora, antes) for chave, (agora, antes) in pares.items()}


def _linhas_de_desempenho(agora: dict, variacoes: dict, rotulo) -> list[LinhaDesempenho]:
    linhas = [
        LinhaDesempenho(
            chave=None if chave is None else str(chave),
            rotulo=rotulo(chave),
            parceiros=parceiros,
            faturamento=faturamento,
            pedidos=pedidos,
            ticket_medio=ticket_medio(faturamento, pedidos),
            # Grupo sem com o que comparar não tem variação — nula, e não zero.
            variacao_percentual=variacoes.get(chave),
        )
        for chave, (parceiros, faturamento, pedidos) in agora.items()
    ]
    # O maior primeiro, e o rótulo desempata: a ordem não muda entre recargas.
    return sorted(linhas, key=lambda linha: (-linha.faturamento, linha.rotulo))


def desempenho(
    s: Session,
    *,
    periodo_id: int | None = None,
    categoria_id: int | None = None,
    segmento: Segmento | None = None,
) -> RelatorioDesempenho:
    """O desempenho de um período, por categoria e por segmento (RF44, H84).

    **Duas variações, e a resposta diz qual vale.** Por categoria e no total, é a
    do painel: o grupo contra ele mesmo no período anterior — o total daqui é o
    indicador de lá, e a linha de uma categoria é o painel filtrado por ela
    (H82). Por segmento, e em tudo quando há filtro de segmento
    (`mesmos_parceiros`), é a dos mesmos parceiros — ver `_dos_mesmos_parceiros`.
    """
    periodo = _periodo(s, periodo_id)
    categoria = categoria_do_recorte(s, categoria_id)
    vazio = RelatorioDesempenho(
        periodo=None,
        periodo_anterior=None,
        categoria=CategoriaResposta.model_validate(categoria) if categoria else None,
        segmento=segmento,
        mesmos_parceiros=segmento is not None,
        segmentado=False,
        total=None,
        por_categoria=[],
        por_segmento=[],
    )
    if periodo is None:
        return vazio

    anterior = periodo_anterior(s, periodo)
    recorte = {"categoria": categoria, "segmento": segmento}
    grupos = (Parceiro.categoria_id, HistoricoSegmento.segmento)
    por_categoria, por_segmento = (
        _desempenho_agrupado(s, periodo, grupo, **recorte) for grupo in grupos
    )
    segmentado = bool(
        s.scalar(select(exists().where(HistoricoSegmento.periodo_id == periodo.id)))
    )

    # O total é a soma das categorias: cada parceiro está em uma só, ou em nenhuma.
    zero = Decimal("0.00")
    parceiros = sum(g[0] for g in por_categoria.values())
    faturamento = sum((g[1] for g in por_categoria.values()), zero)
    pedidos = sum(g[2] for g in por_categoria.values())

    variacao_total = None
    variacao_por_categoria: dict = {}
    variacao_por_segmento: dict = {}
    if anterior is not None:
        variacao_por_segmento = _variacoes(
            _dos_mesmos_parceiros(s, periodo, anterior, HistoricoSegmento.segmento, **recorte)
        )
        if segmento is not None:
            mesmos = _dos_mesmos_parceiros(s, periodo, anterior, Parceiro.categoria_id, **recorte)
            variacao_por_categoria = _variacoes(mesmos)
            variacao_total = variacao_percentual(
                sum((par[0] for par in mesmos.values()), zero),
                sum((par[1] for par in mesmos.values()), zero),
            )
        else:
            antes = _desempenho_agrupado(s, anterior, Parceiro.categoria_id, **recorte)
            variacao_por_categoria = {
                chave: variacao_percentual(grupo[1], antes[chave][1])
                for chave, grupo in por_categoria.items()
                if chave in antes
            }
            variacao_total = variacao_percentual(
                faturamento, sum((g[1] for g in antes.values()), zero)
            )
    nomes = _nomes_das_categorias(s)

    return vazio.model_copy(
        update={
            "periodo": PeriodoResposta.model_validate(periodo),
            "periodo_anterior": PeriodoResposta.model_validate(anterior) if anterior else None,
            "segmentado": segmentado,
            "total": LinhaDesempenho(
                chave=None,
                rotulo="Total",
                parceiros=parceiros,
                faturamento=faturamento,
                pedidos=pedidos,
                ticket_medio=ticket_medio(faturamento, pedidos),
                variacao_percentual=variacao_total,
            ),
            "por_categoria": _linhas_de_desempenho(
                por_categoria, variacao_por_categoria, lambda c: nomes.get(c, SEM_CATEGORIA)
            ),
            # Período sem segmentação não tem "por segmento": uma linha "Sem
            # segmento" com a rede inteira diria que ela foi classificada.
            "por_segmento": (
                _linhas_de_desempenho(por_segmento, variacao_por_segmento, _rotulo_do_segmento)
                if segmentado
                else []
            ),
        }
    )


# ======================================================= 2. risco (RF45, H85)
@dataclass(frozen=True)
class ConsultaDeRisco:
    """A consulta do relatório de risco e de onde a previsão vem.

    A tela pagina a consulta, e o CSV a percorre inteira — a mesma, e é isso que
    garante que o arquivo traz o recorte que está na tela.
    """

    consulta: Select
    base: Periodo
    versao: str
    desatualizada: bool
    plano: PlanoResumido | None


def consulta_de_risco(
    s: Session,
    *,
    categoria: Categoria | None,
    segmento: Segmento | None,
    risco_minimo: float | None,
) -> ConsultaDeRisco | None:
    """Parceiro a parceiro: o medido, o previsto, o risco e a ação no último plano.

    `None` quando o modelo ainda não foi treinado. Entram os parceiros com
    movimento no período de onde a previsão parte; **junção externa com a
    previsão**, para quem não tem previsão continuar na lista, com o motivo — e
    não com zero (RN09). Uma consulta só: a previsão, o segmento, o período
    anterior, o histórico e o plano entram por junção, e não por parceiro.
    """
    concluido = servico_previsao.ultimo_concluido(s)
    if concluido is None:
        return None
    base = s.get(Periodo, concluido.periodo_base_id)
    versao = concluido.versao_em_uso
    recente = servico_previsao.periodo_mais_recente(s)
    anterior = periodo_anterior(s, base)

    previsao = (
        select(Previsao.parceiro_id, Previsao.faturamento_previsto, Previsao.probabilidade_queda)
        .where(Previsao.periodo_base_id == base.id, Previsao.modelo_versao == versao)
        .subquery("previsao_em_uso")
    )
    segmentado = (
        select(HistoricoSegmento.parceiro_id, HistoricoSegmento.segmento)
        .where(HistoricoSegmento.periodo_id == base.id)
        .subquery("segmentado")
    )
    passado = (
        select(Metrica.parceiro_id, Metrica.faturamento.label("antes"))
        .where(Metrica.periodo_id == (anterior.id if anterior else None))
        .subquery("passado")
    )
    # Quantos períodos de histórico até a base: é o que diz por que não há previsão.
    historico = (
        select(Metrica.parceiro_id, func.count().label("periodos"))
        .join(Periodo, Periodo.id == Metrica.periodo_id)
        .where(Periodo.data_inicio <= base.data_inicio)
        .group_by(Metrica.parceiro_id)
        .subquery("historico")
    )

    ultimo = servico_otimizacao.ultimo_plano(s)
    plano = None
    plano_id = None
    if ultimo is not None:
        execucao, gravado = ultimo
        plano_id = gravado.id
        plano = PlanoResumido(
            execucao_id=execucao.id,
            concluida_em=execucao.concluida_em,
            aplicacao_inicio=gravado.aplicacao_inicio,
            aplicacao_fim=gravado.aplicacao_fim,
            modelo_versao=execucao.modelo_versao,
        )
    no_plano = (
        select(ItemPlano.parceiro_id, AcaoComercial.nome.label("acao"), ItemPlano.custo)
        .join(AcaoComercial, AcaoComercial.id == ItemPlano.acao_id)
        .where(ItemPlano.plano_id == plano_id)
        .subquery("no_plano")
    )

    consulta = (
        select(
            Parceiro.id,
            Parceiro.nome,
            Categoria.nome.label("categoria"),
            segmentado.c.segmento,
            Metrica.faturamento,
            passado.c.antes,
            previsao.c.faturamento_previsto,
            previsao.c.probabilidade_queda,
            historico.c.periodos,
            no_plano.c.acao,
            no_plano.c.custo,
        )
        .select_from(Metrica)
        .join(Parceiro, Parceiro.id == Metrica.parceiro_id)
        .outerjoin(Categoria, Categoria.id == Parceiro.categoria_id)
        .outerjoin(previsao, previsao.c.parceiro_id == Parceiro.id)
        .outerjoin(segmentado, segmentado.c.parceiro_id == Parceiro.id)
        .outerjoin(passado, passado.c.parceiro_id == Parceiro.id)
        .outerjoin(historico, historico.c.parceiro_id == Parceiro.id)
        .outerjoin(no_plano, no_plano.c.parceiro_id == Parceiro.id)
        .where(Metrica.periodo_id == base.id)
        # O maior risco primeiro; quem não tem previsão no fim, que nulo não é o
        # maior nem o menor. O nome desempata.
        .order_by(nullslast(previsao.c.probabilidade_queda.desc()), Parceiro.nome)
    )
    if categoria is not None:
        consulta = consulta.where(Parceiro.categoria_id == categoria.id)
    if segmento is not None:
        consulta = consulta.where(segmentado.c.segmento == segmento)
    if risco_minimo is not None:
        consulta = consulta.where(previsao.c.probabilidade_queda >= risco_minimo)

    return ConsultaDeRisco(
        consulta=consulta,
        base=base,
        versao=versao,
        desatualizada=recente is not None and recente.id != base.id,
        plano=plano,
    )


def linha_de_risco(bruta) -> LinhaRisco:
    """Uma linha do relatório — a mesma para a tela e para o CSV."""
    (parceiro_id, nome, categoria, segmento, faturamento, antes, previsto, chance, periodos,
     acao, custo) = bruta
    sem_previsao = None
    if chance is None:
        # Está na base, porque a consulta parte das métricas dela.
        sem_previsao, _ = servico_previsao.motivo_sem_previsao(int(periodos or 0), na_base=True)
    return LinhaRisco(
        parceiro_id=parceiro_id,
        nome=nome,
        categoria=categoria,
        segmento=segmento,
        faturamento=faturamento,
        variacao_percentual=variacao_percentual(faturamento, antes),
        faturamento_previsto=previsto,
        probabilidade_queda=chance,
        sem_previsao=sem_previsao,
        acao=acao,
        custo=custo,
    )


def risco(
    s: Session,
    *,
    categoria_id: int | None = None,
    segmento: Segmento | None = None,
    risco_minimo: float | None = None,
    pagina: int = 1,
    tamanho: int = 50,
) -> RelatorioRisco:
    """Quem está em risco e quem o modelo prevê que caia (RF45, H85).

    O resumo soma o recorte inteiro, e não a página: o previsto e o medido de
    quem **tem** previsão — os mesmos parceiros nas duas somas, como no painel.
    """
    categoria = categoria_do_recorte(s, categoria_id)
    recorte = {
        "categoria": CategoriaResposta.model_validate(categoria) if categoria else None,
        "segmento": segmento,
        "risco_minimo": risco_minimo,
        "pagina": pagina,
        "tamanho": tamanho,
    }
    lida = consulta_de_risco(s, categoria=categoria, segmento=segmento, risco_minimo=risco_minimo)
    if lida is None:
        motivo, ajuda = servico_previsao.SEM_TREINO
        return RelatorioRisco(motivo=motivo, ajuda=ajuda, **recorte)

    tudo = lida.consulta.order_by(None).subquery("recorte")
    tem_previsao = tudo.c.probabilidade_queda.is_not(None)
    total, com_previsao, medido, previsto, no_plano = s.execute(
        select(
            func.count(),
            func.count().filter(tem_previsao),
            func.sum(tudo.c.faturamento).filter(tem_previsao),
            func.sum(tudo.c.faturamento_previsto),
            func.count().filter(tudo.c.acao.is_not(None)),
        )
    ).one()
    linhas = s.execute(lida.consulta.offset((pagina - 1) * tamanho).limit(tamanho)).all()

    return RelatorioRisco(
        disponivel=True,
        periodo_base=PeriodoResposta.model_validate(lida.base),
        modelo_versao=lida.versao,
        origem="REFERENCIA" if servico_previsao.e_referencia(lida.versao) else "MODELO",
        desatualizada=lida.desatualizada,
        plano=lida.plano,
        total=int(total),
        com_previsao=int(com_previsao),
        faturamento_medido=_reais(medido) if com_previsao else None,
        faturamento_previsto=_reais(previsto) if com_previsao else None,
        no_plano=int(no_plano),
        itens=[linha_de_risco(linha) for linha in linhas],
        **recorte,
    )


# ==================================================== 3. campanha (RF46, H86)
def _plano_do_relatorio(
    s: Session, execucao_id: int | None
) -> tuple[ExecucaoOtimizador, PlanoCampanha] | None:
    """O plano pedido, ou o último viável. Execução sem plano é recusa com o porquê."""
    if execucao_id is None:
        return servico_otimizacao.ultimo_plano(s)

    execucao = s.get(ExecucaoOtimizador, execucao_id)
    if execucao is None:
        raise RelatorioRecusado(
            f"Não existe execução com id {execucao_id}.",
            "Escolha uma das execuções do histórico.",
            status=404,
        )
    plano = s.scalar(select(PlanoCampanha).where(PlanoCampanha.execucao_id == execucao.id))
    if plano is None:
        # Em andamento, falhou ou inviável: nenhuma delas tem plano (RN07).
        situacao = (
            "terminou sem plano viável"
            if execucao.situacao == SituacaoExecucao.CONCLUIDA
            else "não foi concluída"
        )
        raise RelatorioRecusado(
            f"A execução {execucao_id} não tem plano: {situacao}.",
            "O relatório é de um plano calculado. Escolha uma execução viável.",
            status=409,
        )
    return execucao, plano


def _campanha_agrupada(s: Session, plano: PlanoCampanha, base_id: int, grupo) -> list:
    return s.execute(
        select(
            grupo,
            func.count(),
            func.sum(ItemPlano.custo),
            func.sum(ItemPlano.uplift_esperado),
        )
        .select_from(ItemPlano)
        .join(Parceiro, Parceiro.id == ItemPlano.parceiro_id)
        .join(AcaoComercial, AcaoComercial.id == ItemPlano.acao_id)
        .outerjoin(
            HistoricoSegmento,
            and_(
                HistoricoSegmento.parceiro_id == ItemPlano.parceiro_id,
                HistoricoSegmento.periodo_id == base_id,
            ),
        )
        .where(ItemPlano.plano_id == plano.id)
        .group_by(grupo)
    ).all()


def _linhas_de_campanha(grupos: list, rotulo) -> list[LinhaCampanha]:
    linhas = [
        LinhaCampanha(
            chave=None if chave is None else str(chave),
            rotulo=rotulo(chave),
            parceiros=int(parceiros),
            custo=_reais(custo),
            ganho_esperado=_reais(ganho),
        )
        for chave, parceiros, custo, ganho in grupos
    ]
    return sorted(linhas, key=lambda linha: (-linha.ganho_esperado, linha.rotulo))


def campanha(s: Session, *, execucao_id: int | None = None) -> RelatorioCampanha:
    """Onde a verba de um plano foi, por ação, por categoria e por segmento (RF46, H86).

    O segmento é o do período de onde o plano partiu (`periodo_base_id`): é a
    classificação que o otimizador viu ao escolher, e não a de hoje.
    """
    achado = _plano_do_relatorio(s, execucao_id)
    if achado is None:
        return RelatorioCampanha()
    execucao, plano = achado
    base = s.get(Periodo, execucao.periodo_base_id)

    por_acao, por_categoria, por_segmento = (
        _campanha_agrupada(s, plano, base.id, grupo)
        for grupo in (AcaoComercial.nome, Parceiro.categoria_id, HistoricoSegmento.segmento)
    )
    nomes = _nomes_das_categorias(s)
    orcamento = (execucao.parametros or {}).get("orcamento")

    return RelatorioCampanha(
        plano=PlanoResumido(
            execucao_id=execucao.id,
            concluida_em=execucao.concluida_em,
            aplicacao_inicio=plano.aplicacao_inicio,
            aplicacao_fim=plano.aplicacao_fim,
            modelo_versao=execucao.modelo_versao,
        ),
        periodo_base=PeriodoResposta.model_validate(base),
        orcamento=_reais(orcamento) if orcamento is not None else None,
        total=LinhaCampanha(
            chave=None,
            rotulo="Total",
            parceiros=sum(int(g[1]) for g in por_acao),
            custo=_reais(sum((g[2] for g in por_acao), Decimal(0))),
            ganho_esperado=_reais(sum((g[3] for g in por_acao), Decimal(0))),
        ),
        por_acao=_linhas_de_campanha(por_acao, lambda nome: nome),
        por_categoria=_linhas_de_campanha(
            por_categoria, lambda c: nomes.get(c, SEM_CATEGORIA)
        ),
        por_segmento=_linhas_de_campanha(por_segmento, _rotulo_do_segmento),
    )


# =================================================== 4. operações (RF47, H87)
def intervalo(de: date | None, ate: date | None) -> tuple[date, date]:
    """As datas do relatório. Sem nenhuma, os últimos trinta dias, com hoje dentro.

    Uma só informada puxa a outra: "até 15/09" são os trinta dias que terminam
    ali, e "desde 01/09" vai até hoje. Datas invertidas são recusa, e não um
    relatório vazio que a pessoa leria como "nada aconteceu".
    """
    hoje = datetime.now().astimezone().date()
    if de is not None and ate is not None and de > ate:
        raise RelatorioRecusado(
            "A data inicial é depois da final.",
            "Troque as datas, ou deixe uma delas em branco.",
            status=422,
        )
    if ate is None:
        ate = hoje
    if de is None:
        de = ate - timedelta(days=DIAS_PADRAO - 1)
    return de, ate


def _rotulo_do_usuario(nome: str | None, login: str | None) -> str:
    return f"{nome} ({login})" if nome else SEM_USUARIO


def operacoes(
    s: Session,
    *,
    de: date | None = None,
    ate: date | None = None,
    autor: int | None = None,
    acao: Acao | None = None,
) -> RelatorioOperacoes:
    """O que foi feito no sistema, por tipo de ação, por usuário e por dia (RF47, H87).

    Os filtros são os da trilha (`servico_auditoria.condicoes`), e o total é o
    que a tela de auditoria mostra no mesmo recorte.

    **O dia é o do relógio do servidor**, como nos filtros da trilha: a coluna é
    `timestamptz`, e agrupar pelo dia em UTC poria no dia seguinte o que
    aconteceu às 22h em Brasília. O deslocamento usado é o de agora — num fuso
    com horário de verão, um registro da outra metade do ano perto da meia-noite
    cairia no dia vizinho; o fuso do projeto (`TZ` no `docker-compose.yml`) não
    tem.
    """
    de, ate = intervalo(de, ate)
    filtros = servico_auditoria.condicoes(autor=autor, acao=acao, de=de, ate=ate)

    por_acao = s.execute(
        select(Auditoria.acao, func.count())
        .where(*filtros)
        .group_by(Auditoria.acao)
        .order_by(func.count().desc(), Auditoria.acao)
    ).all()
    por_usuario = s.execute(
        select(Auditoria.usuario_id, Usuario.nome, Usuario.login, func.count())
        .outerjoin(Usuario, Usuario.id == Auditoria.usuario_id)
        .where(*filtros)
        .group_by(Auditoria.usuario_id, Usuario.nome, Usuario.login)
        .order_by(func.count().desc(), Usuario.nome)
    ).all()
    deslocamento = datetime.now().astimezone().utcoffset()
    dia = func.date(func.timezone("UTC", Auditoria.ocorrido_em) + deslocamento)
    por_dia = s.execute(
        select(dia, func.count()).where(*filtros).group_by(dia).order_by(dia)
    ).all()

    return RelatorioOperacoes(
        de=de,
        ate=ate,
        autor=autor,
        acao=str(acao) if acao else None,
        total=sum(total for _, total in por_acao),
        por_acao=[
            ContagemOperacao(chave=codigo, rotulo=servico_auditoria.rotulo(codigo), total=total)
            for codigo, total in por_acao
        ],
        por_usuario=[
            ContagemOperacao(
                chave=None if usuario_id is None else str(usuario_id),
                rotulo=_rotulo_do_usuario(nome, login),
                total=total,
            )
            for usuario_id, nome, login, total in por_usuario
        ],
        por_dia=[
            ContagemOperacao(chave=quando.isoformat(), rotulo=quando.isoformat(), total=total)
            for quando, total in por_dia
        ],
    )
