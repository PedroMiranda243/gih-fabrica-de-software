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
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.dependencias import Banco, exigir
from app.esquemas import (
    IndicadoresPainel,
    LinhaRanking,
    PaginaRanking,
    PeriodoResposta,
    PontoSerie,
    SerieHistorica,
    VariacaoIndicadores,
)
from app.modelos import Categoria, Metrica, Parceiro, Perfil, Periodo

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


def _posicoes(periodo_id: int):
    """Ranking do período, com a posição calculada por função de janela.

    **O desempate é explícito e estável**: faturamento decrescente e, em caso de
    empate, nome crescente. Sem o segundo critério o banco fica livre para
    devolver os empatados em qualquer ordem, e a mesma base produziria posições
    diferentes entre duas execuções — o painel anunciaria subida e queda que não
    aconteceram.

    `row_number` em vez de `rank`: posições distintas, sem buracos. A mobilidade
    do Top N (H35) vai comparar posição com posição, e posição repetida tornaria
    "entrou" e "saiu" ambíguos.
    """
    return (
        select(
            Metrica.parceiro_id.label("parceiro_id"),
            Metrica.faturamento.label("faturamento"),
            Metrica.pedidos.label("pedidos"),
            func.row_number()
            .over(order_by=(Metrica.faturamento.desc(), Parceiro.nome.asc()))
            .label("posicao"),
        )
        .join(Parceiro, Parceiro.id == Metrica.parceiro_id)
        .where(Metrica.periodo_id == periodo_id)
    )


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

    atual = _posicoes(alvo.id).subquery("atual")
    total = s.scalar(select(func.count()).select_from(atual)) or 0

    linhas = s.execute(
        select(atual, Parceiro.nome, Categoria.nome)
        .join(Parceiro, Parceiro.id == atual.c.parceiro_id)
        .outerjoin(Categoria, Categoria.id == Parceiro.categoria_id)
        .order_by(atual.c.posicao)
        .offset((pagina - 1) * tamanho)
        .limit(tamanho)
    ).all()

    anterior = _periodo_anterior(s, alvo)
    antes: dict[int, tuple[int, Decimal]] = {}
    if anterior is not None and linhas:
        passado = _posicoes(anterior.id).subquery("anterior")
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
        nome, categoria = linha[-2], linha[-1]
        passada = antes.get(linha.parceiro_id)
        itens.append(
            LinhaRanking(
                parceiro_id=linha.parceiro_id,
                nome=nome,
                categoria=categoria,
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
