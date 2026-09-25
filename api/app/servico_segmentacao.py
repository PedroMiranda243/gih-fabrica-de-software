"""Segmentação determinística dos parceiros — RN01, história H33.

Cada parceiro recebe **exatamente um** segmento em cada período, pela ordem de
precedência de RN01. A regra é código, nunca modelo de linguagem: dois usuários
que rodarem a mesma análise sobre os mesmos dados têm que obter o mesmo
resultado.

**Em Risco vence Top de propósito.** É o que deixa o painel responder *quem está
prestes a sair do Top 15?*. Um parceiro entre os maiores, mas em queda
consecutiva, precisa aparecer como risco — não diluído entre os campeões. A
consequência disso é RN02: a mobilidade do Top N lê o **ranking**, nunca este
segmento, porque quem está no topo e caindo está gravado aqui como EM_RISCO.

**O recálculo é uma consulta agregada, não uma por parceiro.** Uma consulta por
parceiro funciona com 100 e morre com 10.000, que é a carga do RNF04 — e o
teste `test_segmentacao.py::test_numero_de_consultas_nao_cresce_com_a_base`
existe para impedir que o N+1 volte sem ninguém perceber.

Quem é classificado: **os parceiros com métrica no período**. Quem não aparece
no relatório daquele período não tem desempenho para classificar, e inventar um
segmento para ele encheria a distribuição de linhas que o relatório não
sustenta.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import Select, delete, func, insert, select
from sqlalchemy.dialects.postgresql import aggregate_order_by
from sqlalchemy.orm import Session

from app.modelos import (
    ConfiguracaoSegmentacao,
    HistoricoSegmento,
    Metrica,
    Parceiro,
    Periodo,
    Segmento,
    StatusComercial,
)
from app.ranking import posicoes


@dataclass(frozen=True)
class Limiares:
    """Os três números que a regra usa. A H34 os torna configuráveis (RF21)."""

    # "Top 15" está em `docs/01-visao-do-produto.md`, no problema e no glossário,
    # e é o que o protótipo aprovado mostra.
    top_n: int = 15

    # RN01 escreve "2 ou mais períodos consecutivos" para queda **e** para
    # crescimento. A RF21 só nomeia o da queda como configurável; enquanto os
    # dois forem o mesmo número, um limiar só evita a ilusão de que dá para
    # afrouxar um sem o outro. Separá-los é conversa da H34.
    periodos_tendencia: int = 2

    # **Este não está em `docs/`** — RN01 diz apenas "menos períodos de histórico
    # que o limiar configurado". O 3 vem da premissa registrada em
    # `docs/01-visao-do-produto.md` §6: "existe histórico de ao menos 3 períodos
    # para que a segmentação por tendência e a previsão façam sentido". A lacuna
    # está aberta na issue #59, com o PO.
    periodos_novato: int = 3

    @property
    def janela(self) -> int:
        """Quantos faturamentos a regra precisa olhar.

        N quedas consecutivas exigem N+1 pontos: com dois valores dá para ver
        uma queda, não duas.
        """
        return self.periodos_tendencia + 1


PADRAO = Limiares()


def limiares_vigentes(s: Session) -> Limiares:
    """Os limiares configurados (RF21, H34), ou o padrão se a linha não existir.

    A ausência da linha não é erro: um banco migrado a partir de uma versão
    anterior ainda não a tem, e recusar a segmentação por causa disso pararia o
    painel inteiro por uma configuração que tem padrão conhecido.

    Quem chama em laço — `reprocessar_tudo` — lê **uma vez** e passa adiante.
    Resolver por período faria uma consulta por período para ler a mesma linha.
    """
    configuracao = s.get(ConfiguracaoSegmentacao, 1)
    if configuracao is None:
        return PADRAO
    return Limiares(
        top_n=configuracao.top_n,
        periodos_tendencia=configuracao.periodos_tendencia,
        periodos_novato=configuracao.periodos_novato,
    )


# ------------------------------------------------------------- a regra, pura
def _consecutivos(faturamentos: Sequence[Decimal], *, subindo: bool) -> int:
    """Quantos períodos seguidos o faturamento subiu (ou caiu), do mais recente.

    A sequência chega **do mais recente para o mais antigo**, e a contagem para
    no primeiro período que quebra a sequência: a regra é sobre o que está
    acontecendo agora, não sobre o melhor trecho do histórico.
    """
    seguidos = 0
    for atual, anterior in zip(faturamentos, faturamentos[1:], strict=False):
        subiu = atual > anterior
        caiu = atual < anterior
        if (subiu if subindo else caiu):
            seguidos += 1
        else:
            break
    return seguidos


def criterio_em_risco(faturamentos: Sequence[Decimal], limiares: Limiares = PADRAO) -> bool:
    """O critério de Em Risco da RN01, sozinho: quedas seguidas até o limiar.

    Separado de `classificar` porque o modelo preditivo rotula o treino com ele
    (RN09). Modelo e segmentação não podem discordar sobre o que é queda — e,
    usando a mesma função, mudar o limiar na configuração muda os dois juntos.
    """
    return _consecutivos(faturamentos, subindo=False) >= limiares.periodos_tendencia


def classificar(
    *,
    status: StatusComercial,
    periodos: int,
    faturamentos: Sequence[Decimal],
    posicao: int | None,
    limiares: Limiares = PADRAO,
) -> Segmento:
    """O segmento de um parceiro, pela precedência de RN01.

    Pura de propósito: recebe números, devolve segmento, não toca no banco. É o
    que permite cobrir os seis ramos da precedência com teste de mesa, sem massa
    de dados — e é onde um erro de regra dói mais barato.

    `faturamentos` vem do mais recente para o mais antigo, e `posicao` é a do
    ranking do período, que é `None` quando o parceiro não faturou nele.
    """
    # 1. Prospecção — marcado à mão, ainda não converteu. Vem primeiro porque é
    #    estado comercial declarado, e não algo que o histórico contradiga.
    if status is StatusComercial.PROSPECCAO:
        return Segmento.PROSPECCAO

    # 2. Recém-chegado — histórico curto demais para a tendência significar algo.
    if periodos < limiares.periodos_novato:
        return Segmento.RECEM_CHEGADO

    # 3. Em Risco — **antes de Top, deliberadamente** (RN01).
    if criterio_em_risco(faturamentos, limiares):
        return Segmento.EM_RISCO

    # 4. Top — entre os N maiores do período mais recente.
    if posicao is not None and posicao <= limiares.top_n:
        return Segmento.TOP

    # 5. Em Ascensão — crescendo, e fora do Top N. O "fora do Top N" de RN01 sai
    #    de graça da precedência: quem está no topo já saiu no passo anterior.
    if _consecutivos(faturamentos, subindo=True) >= limiares.periodos_tendencia:
        return Segmento.EM_ASCENSAO

    # 6. Estável — nenhum critério anterior se aplica.
    return Segmento.ESTAVEL


# -------------------------------------------------------- a consulta agregada
def _consulta(periodo: Periodo, limiares: Limiares) -> Select:
    """Tudo que a regra precisa, para todos os parceiros, numa consulta só.

    A função de janela numera os períodos de cada parceiro do mais recente para
    o mais antigo; o agregado então devolve, por parceiro, **quantos períodos de
    histórico ele tem** e **os últimos faturamentos na ordem certa**. O `FILTER`
    limita o vetor à janela da regra sem perder a contagem total, que é o que o
    critério de recém-chegado usa.

    O `JOIN` com as posições é interno e não decorativo: é ele que restringe o
    resultado aos parceiros com métrica no período.
    """
    recencia = (
        select(
            Metrica.parceiro_id.label("parceiro_id"),
            Metrica.faturamento.label("faturamento"),
            func.row_number()
            .over(
                partition_by=Metrica.parceiro_id,
                # `id` desempata: dois períodos podem começar no mesmo dia, e
                # sem critério estável a janela mudaria entre execuções.
                order_by=(Periodo.data_inicio.desc(), Periodo.id.desc()),
            )
            .label("recencia"),
        )
        .join(Periodo, Periodo.id == Metrica.periodo_id)
        .where(Periodo.data_inicio <= periodo.data_inicio)
        .subquery("recencia")
    )

    historico = (
        select(
            recencia.c.parceiro_id.label("parceiro_id"),
            func.count().label("periodos"),
            func.array_agg(
                aggregate_order_by(recencia.c.faturamento, recencia.c.recencia)
            )
            .filter(recencia.c.recencia <= limiares.janela)
            .label("ultimos"),
        )
        .group_by(recencia.c.parceiro_id)
        .subquery("historico")
    )

    atual = posicoes(periodo.id).subquery("atual")

    return (
        select(
            Parceiro.id,
            Parceiro.status,
            historico.c.periodos,
            historico.c.ultimos,
            atual.c.posicao,
        )
        .join(historico, historico.c.parceiro_id == Parceiro.id)
        .join(atual, atual.c.parceiro_id == Parceiro.id)
    )


# ----------------------------------------------------------- o reprocessamento
def reprocessar(
    s: Session, periodo_id: int, limiares: Limiares | None = None
) -> Counter[Segmento]:
    """Recalcula e grava o segmento de todos os parceiros de um período.

    **Idempotente**: apaga o que havia para o período e grava de novo. Rodar
    duas vezes produz o mesmo resultado, que é o que a H33 cobra — e apagar
    antes é mais simples de manter correto que um `UPSERT` que precisa lembrar
    de remover quem deixou de ser classificado.

    Devolve a distribuição por segmento, que é o que o comando de terminal
    imprime e o que o teste confere.
    """
    limiares = limiares or limiares_vigentes(s)
    periodo = s.get(Periodo, periodo_id)
    if periodo is None:
        raise ValueError(f"Período {periodo_id} não existe.")

    registros = []
    distribuicao: Counter[Segmento] = Counter()
    for parceiro_id, status, periodos, ultimos, posicao in s.execute(
        _consulta(periodo, limiares)
    ):
        segmento = classificar(
            status=status,
            periodos=periodos,
            faturamentos=ultimos or [],
            posicao=posicao,
            limiares=limiares,
        )
        distribuicao[segmento] += 1
        registros.append(
            {"parceiro_id": parceiro_id, "periodo_id": periodo.id, "segmento": segmento}
        )

    s.execute(delete(HistoricoSegmento).where(HistoricoSegmento.periodo_id == periodo.id))
    if registros:
        s.execute(insert(HistoricoSegmento), registros)
    s.flush()
    return distribuicao


def reprocessar_desde(s: Session, periodo_id: int, limiares: Limiares | None = None) -> int:
    """Reprocessa o período e **todos os posteriores**, devolvendo quantos foram.

    Importar um período antigo muda o histórico de todos os que vieram depois:
    um parceiro deixa de ser recém-chegado, uma queda passa a ser a segunda
    seguida. Recalcular só o período importado deixaria o painel mostrando
    classificação de um histórico que não existe mais — e, pior, sem avisar.
    """
    limiares = limiares or limiares_vigentes(s)
    base = s.get(Periodo, periodo_id)
    if base is None:
        raise ValueError(f"Período {periodo_id} não existe.")

    posteriores = s.scalars(
        select(Periodo.id)
        .where(Periodo.data_inicio >= base.data_inicio)
        .order_by(Periodo.data_inicio)
    ).all()
    for pid in posteriores:
        reprocessar(s, pid, limiares)
    return len(posteriores)


def reprocessar_tudo(s: Session, limiares: Limiares | None = None) -> int:
    """Reprocessa a base inteira. É o que o comando de terminal usa."""
    limiares = limiares or limiares_vigentes(s)
    periodos = s.scalars(select(Periodo.id).order_by(Periodo.data_inicio)).all()
    for periodo_id in periodos:
        reprocessar(s, periodo_id, limiares)
    return len(periodos)
