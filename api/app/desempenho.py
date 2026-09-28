"""O desempenho de cada parceiro — o do período mais recente e a série — num lugar só.

A lista de parceiros (H32, H37) e a geração de mensagens (H60) mostram **os mesmos
números**: faturamento, pedidos, ticket e variação do período mais recente, com o
segmento. Uma segunda consulta para a mesma pergunta divergiria na primeira
correção — e a mensagem diria ao parceiro um número que a tela não mostra.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import and_, func, literal, select
from sqlalchemy.orm import Session, selectinload

from app.calculos import ticket_medio
from app.esquemas import PeriodoResposta, PontoSerie
from app.modelos import HistoricoSegmento, Metrica, Parceiro, Periodo, Segmento

# Os rótulos do segmento, no CSV exportado e na descrição do público das
# mensagens. **Precisam bater com `web/src/formato.js`**: o usuário exporta o que
# está vendo, e ler "EM_RISCO" numa planilha onde a tela dizia "Em risco" faz
# parecer que são duas coisas diferentes. Não dá para compartilhar a fonte entre
# Python e JavaScript; dá para deixar o aviso aqui.
ROTULO_SEGMENTO = {
    Segmento.TOP: "Top 15",
    Segmento.EM_ASCENSAO: "Em ascensão",
    Segmento.EM_RISCO: "Em risco",
    Segmento.RECEM_CHEGADO: "Recém-chegado",
    Segmento.PROSPECCAO: "Prospecção",
    Segmento.ESTAVEL: "Estável",
}


def recorte(s: Session) -> tuple[Periodo | None, Periodo | None]:
    """O período mais recente e o anterior a ele.

    O desempenho que a lista mostra é sempre o do período mais recente: é a
    pergunta que o analista traz para esta tela — "quem está como, agora".
    Percorrer o histórico é trabalho do painel, que tem a série.
    """
    alvo = s.scalar(select(Periodo).order_by(Periodo.data_inicio.desc(), Periodo.id.desc()))
    if alvo is None:
        return None, None
    return alvo, periodo_anterior(s, alvo)


def periodo_anterior(s: Session, alvo: Periodo) -> Periodo | None:
    """O período imediatamente anterior, pela data de início, e não pelo id: o id
    segue a ordem da importação, e um período antigo importado depois de um
    recente ficaria "depois" dele."""
    return s.scalar(
        select(Periodo)
        .where(Periodo.data_inicio < alvo.data_inicio)
        .order_by(Periodo.data_inicio.desc(), Periodo.id.desc())
        .limit(1)
    )


def com_desempenho(s: Session, alvo: Periodo | None, anterior: Periodo | None):
    """A consulta da lista, com desempenho e segmento — tudo numa junção só.

    **Junções externas nas três.** Parceiro sem métrica no período continua
    sendo parceiro: sumir com ele faria a tela esconder justamente quem ainda
    não vendeu, que é quem mais precisa aparecer.

    Devolve também as colunas pelas quais dá para ordenar. O ticket e a variação
    entram como expressão SQL **para ordenar**, com `NULLIF` nos dois divisores:
    pedidos zerados e base anterior zerada tornam a divisão indefinida, e
    `NULLIF` devolve nulo em vez de estourar. Os valores que a resposta
    **mostra** vêm de `app.calculos`, a mesma fonte do painel.
    """
    nulo = literal(None)
    consulta = select(Parceiro).options(selectinload(Parceiro.categoria))
    colunas = {
        "faturamento": nulo,
        "pedidos": nulo,
        "anterior": nulo,
        "ticket_medio": nulo,
        "variacao": nulo,
        "segmento": nulo,
    }

    if alvo is None:
        return consulta, colunas

    atual = (
        select(Metrica.parceiro_id, Metrica.faturamento, Metrica.pedidos)
        .where(Metrica.periodo_id == alvo.id)
        .subquery("atual")
    )
    segmentado = (
        select(HistoricoSegmento.parceiro_id, HistoricoSegmento.segmento)
        .where(HistoricoSegmento.periodo_id == alvo.id)
        .subquery("segmentado")
    )
    consulta = consulta.outerjoin(atual, atual.c.parceiro_id == Parceiro.id).outerjoin(
        segmentado, segmentado.c.parceiro_id == Parceiro.id
    )
    colunas |= {
        "faturamento": atual.c.faturamento,
        "pedidos": atual.c.pedidos,
        "ticket_medio": atual.c.faturamento / func.nullif(atual.c.pedidos, 0),
        "segmento": segmentado.c.segmento,
    }

    if anterior is not None:
        passado = (
            select(Metrica.parceiro_id, Metrica.faturamento.label("antes"))
            .where(Metrica.periodo_id == anterior.id)
            .subquery("passado")
        )
        consulta = consulta.outerjoin(passado, passado.c.parceiro_id == Parceiro.id)
        colunas |= {
            "anterior": passado.c.antes,
            "variacao": (atual.c.faturamento - passado.c.antes)
            / func.nullif(passado.c.antes, 0),
        }

    return consulta, colunas


def serie_historica(
    s: Session,
    parceiro_id: int | None = None,
    *,
    de: date | None = None,
    ate: date | None = None,
) -> list[PontoSerie]:
    """A série por período, da rede ou de um parceiro (RF19, H32) — o painel e o portal
    do Parceiro (H39) leem a mesma.

    **A consulta parte dos períodos, não das métricas.** É o que faz a lacuna
    aparecer: período sem medição para aquele parceiro vem com os três valores
    nulos, em vez de sumir da lista. Omitir o ponto faria o gráfico ligar os
    vizinhos com uma reta e desenhar uma tendência onde não houve medição.
    """
    # O filtro do parceiro entra na **junção**, e não no `where`: no `where` ele
    # descartaria os períodos sem métrica dele, que são justamente as lacunas
    # que esta consulta existe para mostrar.
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

    return [
        PontoSerie(
            periodo=PeriodoResposta.model_validate(periodo),
            faturamento=faturamento,
            pedidos=pedidos,
            ticket_medio=ticket_medio(faturamento, pedidos),
        )
        for periodo, faturamento, pedidos in s.execute(consulta).all()
    ]
