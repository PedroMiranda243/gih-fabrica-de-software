"""Painel: indicadores, ranking e séries (UC05 · histórias H30, H31, H32, H82, H83).

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

**O recorte (H82, UC05-A4).** Toda rota aceita `periodo_id`, e as que somam ou
listam parceiros aceitam `categoria_id`. A categoria **escolhe quem entra**, e
não renumera: a posição do ranking é sempre a da rede inteira (RN02), e a
mobilidade do Top N não se filtra por categoria — um "Top 15 das padarias" seria
outra regra, que ninguém escreveu. A resposta devolve a categoria do recorte,
para a tela dizer o que está mostrando sem deduzir do endereço.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.orm import Session

from app import servico_otimizacao, servico_previsao
from app.calculos import ticket_medio as _ticket
from app.calculos import variacao_percentual as _variacao
from app.dependencias import Banco, exigir
from app.desempenho import serie_historica
from app.esquemas import (
    CampanhaNoPainel,
    CategoriaResposta,
    ContagemSegmento,
    DecisaoPainel,
    DistribuicaoSegmentos,
    FatiaSegmento,
    IndicadoresPainel,
    LinhaRanking,
    MobilidadeTopN,
    MovimentoTopN,
    PaginaRanking,
    ParceiroEmRisco,
    PeriodoResposta,
    PlanoResumido,
    PrevisaoNoPainel,
    RecortesPainel,
    SerieHistorica,
    VariacaoIndicadores,
)
from app.modelos import (
    Categoria,
    HistoricoSegmento,
    ItemPlano,
    Metrica,
    Parceiro,
    Perfil,
    Periodo,
    Previsao,
    Segmento,
)
from app.ranking import posicoes
from app.servico_segmentacao import limiares_vigentes

router = APIRouter(
    prefix="/api/painel",
    tags=["painel"],
    dependencies=[Depends(exigir(Perfil.ADMINISTRADOR, Perfil.GESTOR, Perfil.ANALISTA))],
)

TAMANHO_MAXIMO_PAGINA = 200

# Quantos parceiros o bloco de previsão lista, do maior risco para o menor. É o
# tamanho de uma lista na tela, e não um limiar: ninguém é "de risco" por estar
# nela, e a lista inteira, ordenada, está a um clique (H80).
MAIOR_RISCO = 5

PeriodoDoPainel = Annotated[
    int | None, Query(description="Padrão: o período mais recente.")
]
CategoriaDoPainel = Annotated[
    int | None, Query(description="Padrão: a rede inteira.")
]


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


def _categoria_alvo(s: Session, categoria_id: int | None) -> Categoria | None:
    """A categoria do recorte, ou `None` para a rede inteira. Id que não existe é
    404, pelo mesmo motivo do período: pedir um recorte e receber a rede seria pior."""
    if categoria_id is None:
        return None
    categoria = s.get(Categoria, categoria_id)
    if categoria is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Não existe categoria com id {categoria_id}.",
        )
    return categoria


def _da_categoria(coluna, categoria: Categoria | None) -> list:
    """O filtro "o parceiro desta coluna é da categoria" — vazio para a rede inteira.

    Subconsulta, e não junção: serve igual para métrica, segmento, previsão e
    item de plano, sem cada consulta precisar juntar `parceiro` do seu jeito.
    """
    if categoria is None:
        return []
    return [coluna.in_(select(Parceiro.id).where(Parceiro.categoria_id == categoria.id))]


def _categoria_resposta(categoria: Categoria | None) -> CategoriaResposta | None:
    return CategoriaResposta.model_validate(categoria) if categoria else None


def _reais(valor) -> Decimal:
    """Uma soma em reais, sempre com os centavos. A soma de nada vem do banco
    como `0`, e sairia `"0"` ao lado de um `"1380.00"` — o recorte vazio existe
    desde que a categoria filtra (H82)."""
    return Decimal(valor).quantize(Decimal("0.01"))


def _totais(
    s: Session, periodo_id: int, categoria: Categoria | None = None
) -> tuple[Decimal, int, int]:
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
        ).where(Metrica.periodo_id == periodo_id, *_da_categoria(Metrica.parceiro_id, categoria))
    ).one()
    return _reais(faturamento), int(pedidos), int(parceiros)


def _contar_segmento(
    s: Session, periodo_id: int, segmento: Segmento, categoria: Categoria | None = None
) -> int | None:
    """Quantos parceiros naquele segmento — ou `None` se o período não tem segmentação.

    A distinção não é preciosismo. Zero afirma "ninguém em risco"; `None` diz
    "ainda não calculei". Num painel que existe para apontar risco, confundir os
    dois é a forma cara de errar: a tela fica tranquila justamente quando não
    sabe de nada.

    Com categoria, o "ainda não calculei" continua sendo o do **período**: a
    categoria entra só na contagem. Categoria sem ninguém em risco é zero, e não
    "segmentação por calcular".
    """
    total, no_segmento = s.execute(
        select(
            func.count(),
            func.count().filter(
                HistoricoSegmento.segmento == segmento,
                *_da_categoria(HistoricoSegmento.parceiro_id, categoria),
            ),
        ).where(HistoricoSegmento.periodo_id == periodo_id)
    ).one()
    return int(no_segmento) if total else None


# ------------------------------------------------- 0. o que dá para escolher (H82)
@router.get("/recortes", response_model=RecortesPainel)
def recortes(s: Banco) -> RecortesPainel:
    """Os períodos e as categorias que o painel oferece (H82, UC05-A4).

    Rota do painel, e não a de categorias: o Administrador lê o painel e não abre
    o cadastro de parceiros, de onde a lista de categorias viria. Só as
    categorias com parceiro — escolher uma vazia abriria um painel em branco.
    """
    periodos = s.scalars(
        select(Periodo).order_by(Periodo.data_inicio.desc(), Periodo.id.desc())
    ).all()
    categorias = s.scalars(
        select(Categoria)
        .where(exists().where(Parceiro.categoria_id == Categoria.id))
        .order_by(Categoria.nome)
    ).all()
    return RecortesPainel(
        periodos=[PeriodoResposta.model_validate(p) for p in periodos],
        categorias=[CategoriaResposta.model_validate(c) for c in categorias],
    )


# ------------------------------------------------------- 1. indicadores (H30)
@router.get("/indicadores", response_model=IndicadoresPainel)
def indicadores(
    s: Banco,
    periodo_id: PeriodoDoPainel = None,
    categoria_id: CategoriaDoPainel = None,
) -> IndicadoresPainel:
    """Indicadores consolidados do período, com variação (RF17, H30) — da rede ou
    de uma categoria (H82). A variação é contra o período anterior **no mesmo recorte**."""
    alvo = _periodo_alvo(s, periodo_id)
    categoria = _categoria_alvo(s, categoria_id)
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

    faturamento, pedidos, parceiros = _totais(s, alvo.id, categoria)
    anterior = _periodo_anterior(s, alvo)

    em_risco = None
    risco_agora = _contar_segmento(s, alvo.id, Segmento.EM_RISCO, categoria)
    if risco_agora is not None:
        risco_antes = (
            _contar_segmento(s, anterior.id, Segmento.EM_RISCO, categoria)
            if anterior is not None
            else None
        )
        em_risco = ContagemSegmento(
            total=risco_agora,
            delta=None if risco_antes is None else risco_agora - risco_antes,
        )

    variacao = None
    if anterior is not None:
        fat_ant, ped_ant, par_ant = _totais(s, anterior.id, categoria)
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
        categoria=_categoria_resposta(categoria),
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
    periodo_id: PeriodoDoPainel = None,
    categoria_id: CategoriaDoPainel = None,
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

    **Com categoria, a posição continua a da rede** (RN02, H82): a janela numera
    o ranking inteiro na subconsulta, e o filtro entra por fora dela. Filtrar
    antes renumeraria — a padaria que é a 40ª da rede viraria a 1ª, e a tabela
    discordaria do cadastro dela e da mobilidade do Top N.
    """
    alvo = _periodo_alvo(s, periodo_id)
    categoria = _categoria_alvo(s, categoria_id)
    if alvo is None:
        return PaginaRanking(
            periodo=None, periodo_anterior=None, itens=[], total=0,
            pagina=pagina, tamanho=tamanho,
        )

    atual = posicoes(alvo.id).subquery("atual")
    do_recorte = _da_categoria(atual.c.parceiro_id, categoria)
    total = s.scalar(select(func.count()).select_from(atual).where(*do_recorte)) or 0

    linhas = s.execute(
        select(atual, Parceiro.nome, Categoria.nome, HistoricoSegmento.segmento)
        .join(Parceiro, Parceiro.id == atual.c.parceiro_id)
        .where(*do_recorte)
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
        nome, da_categoria, segmento = linha[-3], linha[-2], linha[-1]
        passada = antes.get(linha.parceiro_id)
        itens.append(
            LinhaRanking(
                parceiro_id=linha.parceiro_id,
                nome=nome,
                categoria=da_categoria,
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
        categoria=_categoria_resposta(categoria),
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
    periodo_id: Annotated[
        int | None, Query(description="A série vai até este período. Padrão: até o mais recente.")
    ] = None,
    categoria_id: CategoriaDoPainel = None,
) -> SerieHistorica:
    """Série histórica da rede, de uma categoria ou de um parceiro (RF19, H32, H82),
    com a lacuna explícita onde não houve medição — ver `desempenho.serie_historica`.

    Não há paginação: a quantidade de períodos é limitada pelo que foi
    importado, e o RNF04 fixa o teto em 52. O recorte por data existe para quem
    quiser menos, não para conter volume.

    Com `periodo_id`, a série termina nele: quem escolhe um período no painel
    quer saber como a rede vinha **até ali**, e não o que aconteceu depois.
    """
    if parceiro_id is not None and categoria_id is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "erro": "A série é de um parceiro ou de uma categoria, e não dos dois.",
                "ajuda": "Informe só o parceiro, ou só a categoria.",
            },
        )
    categoria = _categoria_alvo(s, categoria_id)
    if periodo_id is not None and ate is None:
        ate = _periodo_alvo(s, periodo_id).data_fim

    parceiro = None
    if parceiro_id is not None:
        parceiro = s.get(Parceiro, parceiro_id)
        if parceiro is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Não existe parceiro com id {parceiro_id}.",
            )

    pontos = serie_historica(
        s, parceiro_id, de=de, ate=ate, categoria_id=categoria.id if categoria else None
    )

    return SerieHistorica(
        escopo="parceiro" if parceiro else "categoria" if categoria else "rede",
        parceiro_id=parceiro.id if parceiro else None,
        parceiro_nome=parceiro.nome if parceiro else None,
        categoria=_categoria_resposta(categoria),
        pontos=pontos,
    )


# --------------------------------------------- 4. distribuição por segmento (H33)
@router.get("/segmentos", response_model=DistribuicaoSegmentos)
def segmentos(
    s: Banco,
    periodo_id: PeriodoDoPainel = None,
    categoria_id: CategoriaDoPainel = None,
) -> DistribuicaoSegmentos:
    """Quantos parceiros em cada segmento no período (RF20, H33).

    Devolve **só os segmentos com parceiros**, ordenados do maior para o menor.
    Preencher os seis com zero desenharia barras vazias que não dizem nada e
    roubariam espaço das que dizem.

    Período sem segmentação calculada devolve a lista vazia, e não seis zeros:
    seis zeros afirmam uma distribuição plana que ninguém mediu.
    """
    alvo = _periodo_alvo(s, periodo_id)
    categoria = _categoria_alvo(s, categoria_id)
    if alvo is None:
        return DistribuicaoSegmentos(periodo=None, total=0, itens=[])

    linhas = s.execute(
        select(HistoricoSegmento.segmento, func.count())
        .where(
            HistoricoSegmento.periodo_id == alvo.id,
            *_da_categoria(HistoricoSegmento.parceiro_id, categoria),
        )
        .group_by(HistoricoSegmento.segmento)
        # O desempate por nome do segmento não é enfeite: sem ele, dois
        # segmentos com a mesma contagem trocariam de lugar entre recargas, e o
        # gráfico pareceria mudar sem nada ter mudado.
        .order_by(func.count().desc(), HistoricoSegmento.segmento)
    ).all()

    return DistribuicaoSegmentos(
        periodo=PeriodoResposta.model_validate(alvo),
        categoria=_categoria_resposta(categoria),
        total=sum(quantos for _, quantos in linhas),
        itens=[FatiaSegmento(segmento=segmento, total=quantos) for segmento, quantos in linhas],
    )


# ------------------------------------------------ 5. mobilidade do Top N (H35)
@router.get("/mobilidade", response_model=MobilidadeTopN)
def mobilidade(
    s: Banco,
    periodo_id: PeriodoDoPainel = None,
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
    # O Top N vem da configuração, não de uma constante (RF21, H34): baixar o
    # Top de 15 para 10 e ver o painel continuar contando quinze faria o
    # administrador achar que a mudança não pegou.
    n = limiares_vigentes(s).top_n

    alvo = _periodo_alvo(s, periodo_id)
    if alvo is None:
        return MobilidadeTopN(
            periodo=None, periodo_anterior=None, top_n=n, entradas=[], saidas=[]
        )

    anterior = _periodo_anterior(s, alvo)
    if anterior is None:
        # UC05, A2 — período único. Ninguém entrou nem saiu de lugar nenhum
        # quando não há de onde sair; listar o Top N inteiro como "entradas"
        # seria inventar movimento.
        return MobilidadeTopN(
            periodo=PeriodoResposta.model_validate(alvo),
            periodo_anterior=None,
            top_n=n,
            entradas=[],
            saidas=[],
        )

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


# --------------------------------------- 6. a previsão e a campanha no painel (H83)
def _previsao_no_painel(s: Session, categoria: Categoria | None) -> PrevisaoNoPainel:
    """A previsão da versão em uso, somada no recorte, e quem tem o maior risco.

    A mesma escolha do cadastro e da lista (`servico_previsao.ultimo_concluido`):
    o último treino concluído diz a versão e o período de onde ela parte. Outra
    escolha aqui faria o painel e o cadastro mostrarem dois riscos para o mesmo
    parceiro.
    """
    concluido = servico_previsao.ultimo_concluido(s)
    if concluido is None:
        motivo, ajuda = servico_previsao.SEM_TREINO
        return PrevisaoNoPainel(motivo=motivo, ajuda=ajuda)

    base = s.get(Periodo, concluido.periodo_base_id)
    versao = concluido.versao_em_uso
    recente = servico_previsao.periodo_mais_recente(s)
    origem = {
        "periodo_base": PeriodoResposta.model_validate(base),
        "modelo_versao": versao,
        "origem": "REFERENCIA" if servico_previsao.e_referencia(versao) else "MODELO",
        "desatualizada": recente is not None and recente.id != base.id,
    }

    # Previsão e métrica do **mesmo parceiro no período base**, juntas: as duas
    # somas saem do mesmo conjunto, que é o que deixa compará-las.
    com_medido = (
        select(Previsao, Metrica.faturamento.label("medido"))
        .join(
            Metrica,
            and_(Metrica.parceiro_id == Previsao.parceiro_id, Metrica.periodo_id == base.id),
        )
        .where(
            Previsao.periodo_base_id == base.id,
            Previsao.modelo_versao == versao,
            *_da_categoria(Previsao.parceiro_id, categoria),
        )
        .subquery("com_medido")
    )
    parceiros, previsto, medido = s.execute(
        select(
            func.count(),
            func.sum(com_medido.c.faturamento_previsto),
            func.sum(com_medido.c.medido),
        )
    ).one()
    if not parceiros:
        return PrevisaoNoPainel(
            motivo="Nenhum parceiro deste recorte tem previsão.",
            ajuda=(
                f"A previsão exige {servico_previsao.JANELA} períodos de histórico e "
                "movimento no período em que o modelo foi treinado."
            ),
            **origem,
        )

    maior_risco = s.execute(
        select(
            com_medido.c.parceiro_id,
            Parceiro.nome,
            Categoria.nome,
            com_medido.c.probabilidade_queda,
            com_medido.c.medido,
            com_medido.c.faturamento_previsto,
        )
        .join(Parceiro, Parceiro.id == com_medido.c.parceiro_id)
        .outerjoin(Categoria, Categoria.id == Parceiro.categoria_id)
        # O nome desempata: sem ele, dois parceiros com a mesma chance trocariam
        # de lugar entre recargas.
        .order_by(com_medido.c.probabilidade_queda.desc(), Parceiro.nome)
        .limit(MAIOR_RISCO)
    ).all()

    return PrevisaoNoPainel(
        disponivel=True,
        parceiros=int(parceiros),
        faturamento_previsto=previsto,
        faturamento_medido=medido,
        variacao_percentual=_variacao(previsto, medido),
        maior_risco=[
            ParceiroEmRisco(
                parceiro_id=parceiro_id,
                nome=nome,
                categoria=da_categoria,
                probabilidade_queda=chance,
                faturamento=faturamento,
                faturamento_previsto=faturamento_previsto,
            )
            for parceiro_id, nome, da_categoria, chance, faturamento, faturamento_previsto
            in maior_risco
        ],
        **origem,
    )


def _campanha_no_painel(s: Session, categoria: Categoria | None) -> CampanhaNoPainel:
    """O último plano viável, somado no recorte — o mesmo "último" do cadastro do parceiro."""
    ultimo = servico_otimizacao.ultimo_plano(s)
    if ultimo is None:
        return CampanhaNoPainel()
    execucao, plano = ultimo

    acoes, custo, ganho = s.execute(
        select(
            func.count(),
            func.coalesce(func.sum(ItemPlano.custo), 0),
            func.coalesce(func.sum(ItemPlano.uplift_esperado), 0),
        ).where(ItemPlano.plano_id == plano.id, *_da_categoria(ItemPlano.parceiro_id, categoria))
    ).one()

    return CampanhaNoPainel(
        plano=PlanoResumido(
            execucao_id=execucao.id,
            concluida_em=execucao.concluida_em,
            aplicacao_inicio=plano.aplicacao_inicio,
            aplicacao_fim=plano.aplicacao_fim,
            modelo_versao=execucao.modelo_versao,
        ),
        acoes=int(acoes),
        custo=_reais(custo),
        ganho_esperado=_reais(ganho),
    )


@router.get(
    "/decisao",
    response_model=DecisaoPainel,
    # Além do `exigir` do roteador: o Administrador lê o painel, mas não abre a
    # previsão por parceiro nem a campanha, e o bloco é a soma das duas.
    dependencies=[Depends(exigir(Perfil.GESTOR, Perfil.ANALISTA))],
)
def decisao(s: Banco, categoria_id: CategoriaDoPainel = None) -> DecisaoPainel:
    """O que a previsão e a campanha dizem, dentro do painel (RF28, RF30 · H83, UC05-A5).

    **Não tem `periodo_id`, de propósito.** A previsão parte do período em que o
    modelo foi treinado, e o plano é o último calculado: nenhum dos dois muda com
    o período que a pessoa escolhe olhar. A resposta diz de quando cada um é.

    Quatro consultas agregadas, com 500 ou com 10.000 parceiros (RNF03).
    """
    categoria = _categoria_alvo(s, categoria_id)
    return DecisaoPainel(
        categoria=_categoria_resposta(categoria),
        previsao=_previsao_no_painel(s, categoria),
        campanha=_campanha_no_painel(s, categoria),
    )
