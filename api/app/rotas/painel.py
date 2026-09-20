"""Painel: indicadores, ranking e séries (UC05 · histórias H30, H31, H32).

Caso de uso de **consulta**: nenhuma rota daqui altera estado, e por isso nenhuma
delas audita. A trilha registra o que muda o sistema; enchê-la de leituras
esconderia o que ela existe para mostrar.

Perfis: Gestor e Analista executam; o Administrador tem **somente leitura** no
UC05, e como aqui tudo é leitura, ele entra. É diferente do UC03 e do UC04, onde
a matriz lhe nega acesso — a distinção está na tabela de
`docs/03-casos-de-uso.md` e é deliberada.

O contrato deste módulo é o que a interface vai consumir. As três convenções de
que o frontend depende — base vazia, período único, e variação nula não sendo
zero — estão documentadas em `app/esquemas.py`, na seção do painel.
"""
from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.dependencias import Banco, exigir
from app.esquemas import (
    ContagemSegmento,
    DistribuicaoSegmentos,
    FatiaSegmento,
    IndicadoresPainel,
    LinhaRanking,
    MobilidadeTopN,
    MovimentoTopN,
    PaginaRanking,
    PeriodoResposta,
    PontoSerie,
    SerieHistorica,
    VariacaoIndicadores,
)
from app.modelos import (
    Categoria,
    HistoricoSegmento,
    Metrica,
    Parceiro,
    Perfil,
    Periodo,
    Segmento,
)
from app.ranking import posicoes
from app.servico_segmentacao import PADRAO as LIMIARES

router = APIRouter(
    prefix="/api/painel",
    tags=["painel"],
    dependencies=[Depends(exigir(Perfil.ADMINISTRADOR, Perfil.GESTOR, Perfil.ANALISTA))],
)

TAMANHO_MAXIMO_PAGINA = 200
CENTAVOS = Decimal("0.01")


# --------------------------------------------------------------------- apoio
def _periodo_alvo(s: Session, periodo_id: int | None) -> Periodo | None:
    """O período consultado, ou o mais recente quando nenhum é informado.

    Devolve `None` só quando a base não tem período nenhum — o estado inicial do
    UC05, A1. Id informado que não existe é 404, e não silêncio: pedir um período
    específico e receber outro seria pior que receber erro.
    """
    if periodo_id is not None:
        periodo = s.get(Periodo, periodo_id)
        if periodo is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Não existe período com id {periodo_id}.",
            )
        return periodo

    return s.scalar(
        select(Periodo).order_by(Periodo.data_inicio.desc(), Periodo.id.desc()).limit(1)
    )


def _periodo_anterior(s: Session, alvo: Periodo) -> Periodo | None:
    """O período imediatamente anterior, pela data de início.

    Comparar por `data_inicio`, e não por id, é o que mantém a resposta correta
    quando um período antigo é importado depois de um recente — o id segue a
    ordem de digitação, não a do calendário.
    """
    return s.scalar(
        select(Periodo)
        .where(Periodo.data_inicio < alvo.data_inicio)
        .order_by(Periodo.data_inicio.desc(), Periodo.id.desc())
        .limit(1)
    )


def _ticket(faturamento: Decimal | None, pedidos: int | None) -> Decimal | None:
    """Ticket médio, derivado na consulta (RN04).

    Sem pedidos não há ticket: devolver zero afirmaria que cada pedido valeu
    nada, quando o que houve foi ausência de pedido.
    """
    if not pedidos or faturamento is None:
        return None
    return (Decimal(faturamento) / Decimal(pedidos)).quantize(CENTAVOS, ROUND_HALF_UP)


def _variacao(atual, anterior) -> Decimal | None:
    """Variação percentual, ou nulo quando ela não é definível.

    Nulo **não** é zero. Zero diz "não mudou"; nulo diz "não dá para dizer" — sem
    período anterior, ou com base anterior zerada, em que a divisão é indefinida.
    Devolver zero nesses casos desenharia estabilidade que ninguém mediu.
    """
    if atual is None or anterior is None or Decimal(anterior) == 0:
        return None
    variacao = (Decimal(atual) - Decimal(anterior)) / Decimal(anterior) * 100
    return variacao.quantize(CENTAVOS, ROUND_HALF_UP)


def _totais(s: Session, periodo_id: int) -> tuple[Decimal, int, int]:
    """Faturamento, pedidos e parceiros com movimento, numa consulta agregada.

    `count()` conta parceiros porque a métrica é única por (parceiro, período) —
    a restrição de unicidade do modelo é o que torna a contagem exata sem
    `DISTINCT`. "Parceiros ativos" aqui é quem teve movimento no período, e não
    a situação cadastral: é a única leitura em que a variação contra o período
    anterior, que o RF17 pede, significa alguma coisa.
    """
    faturamento, pedidos, parceiros = s.execute(
        select(
            func.coalesce(func.sum(Metrica.faturamento), 0),
            func.coalesce(func.sum(Metrica.pedidos), 0),
            func.count(),
        ).where(Metrica.periodo_id == periodo_id)
    ).one()
    return Decimal(faturamento), int(pedidos), int(parceiros)


def _contar_segmento(s: Session, periodo_id: int, segmento: Segmento) -> int | None:
    """Quantos parceiros naquele segmento — ou `None` se o período não tem segmentação.

    A distinção não é preciosismo. Zero afirma "ninguém em risco"; `None` diz
    "ainda não calculei". Num painel que existe para apontar risco, confundir os
    dois é a forma cara de errar: a tela fica tranquila justamente quando não
    sabe de nada.
    """
    total, no_segmento = s.execute(
        select(
            func.count(),
            func.count().filter(HistoricoSegmento.segmento == segmento),
        ).where(HistoricoSegmento.periodo_id == periodo_id)
    ).one()
    return int(no_segmento) if total else None


# ------------------------------------------------------- 1. indicadores (H30)
@router.get("/indicadores", response_model=IndicadoresPainel)
def indicadores(
    s: Banco,
    periodo_id: Annotated[int | None, Query(description="Padrão: o período mais recente.")] = None,
) -> IndicadoresPainel:
    """Indicadores consolidados do período, com variação (RF17, H30)."""
    alvo = _periodo_alvo(s, periodo_id)
    if alvo is None:
        # UC05, A1 — base vazia. Não é erro: é quem ainda não importou nada.
        return IndicadoresPainel(
            periodo=None,
            periodo_anterior=None,
            faturamento=Decimal("0.00"),
            pedidos=0,
            ticket_medio=None,
            parceiros_ativos=0,
            variacao=None,
        )

    faturamento, pedidos, parceiros = _totais(s, alvo.id)
    anterior = _periodo_anterior(s, alvo)

    em_risco = None
    risco_agora = _contar_segmento(s, alvo.id, Segmento.EM_RISCO)
    if risco_agora is not None:
        risco_antes = (
            _contar_segmento(s, anterior.id, Segmento.EM_RISCO) if anterior is not None else None
        )
        em_risco = ContagemSegmento(
            total=risco_agora,
            delta=None if risco_antes is None else risco_agora - risco_antes,
        )

    variacao = None
    if anterior is not None:
        fat_ant, ped_ant, par_ant = _totais(s, anterior.id)
        variacao = VariacaoIndicadores(
            faturamento=_variacao(faturamento, fat_ant),
            pedidos=_variacao(pedidos, ped_ant),
            ticket_medio=_variacao(_ticket(faturamento, pedidos), _ticket(fat_ant, ped_ant)),
            parceiros_ativos=_variacao(parceiros, par_ant),
        )

    return IndicadoresPainel(
        periodo=PeriodoResposta.model_validate(alvo),
        # UC05, A2 — período único: sem anterior, e toda variação vem nula junto.
        periodo_anterior=PeriodoResposta.model_validate(anterior) if anterior else None,
        faturamento=faturamento,
        pedidos=pedidos,
        ticket_medio=_ticket(faturamento, pedidos),
        parceiros_ativos=parceiros,
        variacao=variacao,
        em_risco=em_risco,
    )


# ----------------------------------------------------------- 2. ranking (H31)
@router.get("/ranking", response_model=PaginaRanking)
def ranking(
    s: Banco,
    periodo_id: Annotated[int | None, Query(description="Padrão: o período mais recente.")] = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamanho: Annotated[int, Query(ge=1, le=TAMANHO_MAXIMO_PAGINA)] = 50,
) -> PaginaRanking:
    """Ranking por faturamento, com posição anterior e variação (RF18, H31).

    **Esta rota é a fonte da posição.** A mobilidade do Top N (H35, RN02) vai ler
    daqui, e nunca do segmento armazenado: um parceiro entre os N maiores mas em
    queda fica gravado como EM_RISCO, e derivar a mobilidade do segmento faria o
    painel anunciar que ele saiu do Top N enquanto continua lá.

    Duas consultas, não N: a página, e as posições anteriores **apenas dos
    parceiros dela**. A posição anterior é calculada sobre o ranking inteiro do
    período anterior e só então filtrada — calculá-la sobre o recorte daria a
    posição dentro da página, que não significa nada.
    """
    alvo = _periodo_alvo(s, periodo_id)
    if alvo is None:
        return PaginaRanking(
            periodo=None, periodo_anterior=None, itens=[], total=0,
            pagina=pagina, tamanho=tamanho,
        )

    atual = posicoes(alvo.id).subquery("atual")
    total = s.scalar(select(func.count()).select_from(atual)) or 0

    linhas = s.execute(
        select(atual, Parceiro.nome, Categoria.nome, HistoricoSegmento.segmento)
        .join(Parceiro, Parceiro.id == atual.c.parceiro_id)
        .outerjoin(Categoria, Categoria.id == Parceiro.categoria_id)
        # `outerjoin`, e não `join`: período sem segmentação calculada ainda
        # precisa devolver o ranking. Faltar a coluna é aceitável; sumir com as
        # linhas do painel porque a classificação não rodou, não.
        .outerjoin(
            HistoricoSegmento,
            and_(
                HistoricoSegmento.parceiro_id == atual.c.parceiro_id,
                HistoricoSegmento.periodo_id == alvo.id,
            ),
        )
        .order_by(atual.c.posicao)
        .offset((pagina - 1) * tamanho)
        .limit(tamanho)
    ).all()

    anterior = _periodo_anterior(s, alvo)
    antes: dict[int, tuple[int, Decimal]] = {}
    if anterior is not None and linhas:
        passado = posicoes(anterior.id).subquery("anterior")
        antes = {
            pid: (posicao, faturamento)
            for pid, posicao, faturamento in s.execute(
                select(passado.c.parceiro_id, passado.c.posicao, passado.c.faturamento).where(
                    passado.c.parceiro_id.in_([linha.parceiro_id for linha in linhas])
                )
            ).all()
        }

    itens = []
    for linha in linhas:
        # Nome e categoria vêm posicionais porque as duas colunas se chamam
        # `nome`; desempacotar aqui deixa o resto do laço legível.
        nome, categoria, segmento = linha[-3], linha[-2], linha[-1]
        passada = antes.get(linha.parceiro_id)
        itens.append(
            LinhaRanking(
                parceiro_id=linha.parceiro_id,
                nome=nome,
                categoria=categoria,
                segmento=segmento,
                posicao=linha.posicao,
                posicao_anterior=passada[0] if passada else None,
                faturamento=linha.faturamento,
                pedidos=linha.pedidos,
                ticket_medio=_ticket(linha.faturamento, linha.pedidos),
                variacao_percentual=_variacao(linha.faturamento, passada[1]) if passada else None,
                # Estreante só faz sentido havendo período anterior: sem ele
                # ninguém estreou, todos são simplesmente os primeiros dados.
                estreante=anterior is not None and passada is None,
            )
        )

    return PaginaRanking(
        periodo=PeriodoResposta.model_validate(alvo),
        periodo_anterior=PeriodoResposta.model_validate(anterior) if anterior else None,
        itens=itens,
        total=total,
        pagina=pagina,
        tamanho=tamanho,
    )


# ------------------------------------------------------------ 3. séries (H32)
@router.get("/series", response_model=SerieHistorica)
def series(
    s: Banco,
    parceiro_id: Annotated[int | None, Query(description="Padrão: a rede inteira.")] = None,
    de: Annotated[date | None, Query(description="Períodos a partir deste dia.")] = None,
    ate: Annotated[date | None, Query(description="Períodos que terminam até este dia.")] = None,
) -> SerieHistorica:
    """Série histórica da rede ou de um parceiro (RF19, H32).

    **A consulta parte dos períodos, não das métricas.** É o que faz a lacuna
    aparecer: período sem medição para aquele parceiro vem com os três valores
    nulos, em vez de sumir da lista. Omitir o ponto faria o gráfico ligar os
    vizinhos com uma reta e desenhar uma tendência onde não houve medição.

    Não há paginação: a quantidade de períodos é limitada pelo que foi
    importado, e o RNF04 fixa o teto em 52. O recorte por data existe para quem
    quiser menos, não para conter volume.
    """
    parceiro = None
    if parceiro_id is not None:
        parceiro = s.get(Parceiro, parceiro_id)
        if parceiro is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Não existe parceiro com id {parceiro_id}.",
            )

    # O filtro do parceiro entra na **junção**, e não no `where`: no `where` ele
    # descartaria os períodos sem métrica dele, que são justamente as lacunas
    # que esta rota existe para mostrar.
    juncao = [Metrica.periodo_id == Periodo.id]
    if parceiro_id is not None:
        juncao.append(Metrica.parceiro_id == parceiro_id)

    consulta = (
        select(
            Periodo,
            func.sum(Metrica.faturamento),
            func.sum(Metrica.pedidos),
        )
        .outerjoin(Metrica, and_(*juncao))
        .group_by(Periodo.id)
        .order_by(Periodo.data_inicio, Periodo.id)
    )
    if de is not None:
        consulta = consulta.where(Periodo.data_inicio >= de)
    if ate is not None:
        consulta = consulta.where(Periodo.data_fim <= ate)

    pontos = [
        PontoSerie(
            periodo=PeriodoResposta.model_validate(periodo),
            faturamento=faturamento,
            pedidos=pedidos,
            ticket_medio=_ticket(faturamento, pedidos),
        )
        for periodo, faturamento, pedidos in s.execute(consulta).all()
    ]

    return SerieHistorica(
        escopo="parceiro" if parceiro else "rede",
        parceiro_id=parceiro.id if parceiro else None,
        parceiro_nome=parceiro.nome if parceiro else None,
        pontos=pontos,
    )


# --------------------------------------------- 4. distribuição por segmento (H33)
@router.get("/segmentos", response_model=DistribuicaoSegmentos)
def segmentos(
    s: Banco,
    periodo_id: Annotated[int | None, Query(description="Padrão: o período mais recente.")] = None,
) -> DistribuicaoSegmentos:
    """Quantos parceiros em cada segmento no período (RF20, H33).

    Devolve **só os segmentos com parceiros**, ordenados do maior para o menor.
    Preencher os seis com zero desenharia barras vazias que não dizem nada e
    roubariam espaço das que dizem.

    Período sem segmentação calculada devolve a lista vazia, e não seis zeros:
    seis zeros afirmam uma distribuição plana que ninguém mediu.
    """
    alvo = _periodo_alvo(s, periodo_id)
    if alvo is None:
        return DistribuicaoSegmentos(periodo=None, total=0, itens=[])

    linhas = s.execute(
        select(HistoricoSegmento.segmento, func.count())
        .where(HistoricoSegmento.periodo_id == alvo.id)
        .group_by(HistoricoSegmento.segmento)
        # O desempate por nome do segmento não é enfeite: sem ele, dois
        # segmentos com a mesma contagem trocariam de lugar entre recargas, e o
        # gráfico pareceria mudar sem nada ter mudado.
        .order_by(func.count().desc(), HistoricoSegmento.segmento)
    ).all()

    return DistribuicaoSegmentos(
        periodo=PeriodoResposta.model_validate(alvo),
        total=sum(quantos for _, quantos in linhas),
        itens=[FatiaSegmento(segmento=segmento, total=quantos) for segmento, quantos in linhas],
    )


# ------------------------------------------------ 5. mobilidade do Top N (H35)
@router.get("/mobilidade", response_model=MobilidadeTopN)
def mobilidade(
    s: Banco,
    periodo_id: Annotated[int | None, Query(description="Padrão: o período mais recente.")] = None,
) -> MobilidadeTopN:
    """Quem entrou e quem saiu do Top N entre dois períodos (RF22, H35).

    **RN02: isto lê o ranking, nunca o segmento armazenado.** Como Em Risco
    vence Top na precedência de RN01, um parceiro entre os N maiores mas em
    queda fica gravado como EM_RISCO. Derivar a mobilidade dali faria o painel
    anunciar que ele saiu do Top N enquanto continua lá — e o erro passaria
    despercebido, porque a tela continuaria plausível.

    Uma consulta só, com junção externa completa dos dois rankings: quem está em
    um lado e não no outro. Comparar as duas listas em Python exigiria trazer os
    dois rankings inteiros para a aplicação.
    """
    alvo = _periodo_alvo(s, periodo_id)
    if alvo is None:
        return MobilidadeTopN(
            periodo=None,
            periodo_anterior=None,
            top_n=LIMIARES.top_n,
            entradas=[],
            saidas=[],
        )

    anterior = _periodo_anterior(s, alvo)
    if anterior is None:
        # UC05, A2 — período único. Ninguém entrou nem saiu de lugar nenhum
        # quando não há de onde sair; listar o Top N inteiro como "entradas"
        # seria inventar movimento.
        return MobilidadeTopN(
            periodo=PeriodoResposta.model_validate(alvo),
            periodo_anterior=None,
            top_n=LIMIARES.top_n,
            entradas=[],
            saidas=[],
        )

    n = LIMIARES.top_n
    atual = posicoes(alvo.id).subquery("atual")
    passado = posicoes(anterior.id).subquery("passado")
    parceiro_id = func.coalesce(atual.c.parceiro_id, passado.c.parceiro_id)

    entrou = and_(
        atual.c.posicao <= n,
        or_(passado.c.posicao.is_(None), passado.c.posicao > n),
    )
    saiu = and_(
        passado.c.posicao <= n,
        or_(atual.c.posicao.is_(None), atual.c.posicao > n),
    )

    linhas = s.execute(
        select(
            parceiro_id.label("parceiro_id"),
            Parceiro.nome,
            atual.c.posicao.label("posicao"),
            passado.c.posicao.label("posicao_anterior"),
        )
        .select_from(
            atual.outerjoin(
                passado, atual.c.parceiro_id == passado.c.parceiro_id, full=True
            ).join(Parceiro, Parceiro.id == parceiro_id)
        )
        .where(or_(entrou, saiu))
        # Quem entrou mais alto primeiro; entre as saídas, quem ocupava a
        # posição mais alta — é a ordem em que a notícia importa.
        .order_by(func.coalesce(atual.c.posicao, passado.c.posicao))
    ).all()

    entradas, saidas = [], []
    for linha in linhas:
        movimento = MovimentoTopN(
            parceiro_id=linha.parceiro_id,
            nome=linha.nome,
            posicao=linha.posicao,
            posicao_anterior=linha.posicao_anterior,
        )
        destino = entradas if linha.posicao is not None and linha.posicao <= n else saidas
        destino.append(movimento)

    return MobilidadeTopN(
        periodo=PeriodoResposta.model_validate(alvo),
        periodo_anterior=PeriodoResposta.model_validate(anterior),
        top_n=n,
        entradas=entradas,
        saidas=saidas,
    )
