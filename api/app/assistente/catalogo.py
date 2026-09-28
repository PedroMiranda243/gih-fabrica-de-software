"""O catálogo de perguntas: os tipos, o que cada um precisa e a instrução ao modelo.

**Fechado de propósito** (ADR-013). Cada tipo é uma pergunta que o código sabe
responder com uma consulta que já existe numa tela. Uma pergunta livre pediria
ao modelo que decidisse o que buscar e como juntar — e juntar é somar, contar e
comparar, que é justamente o que ele não faz (RN08, regra 2.3). O que não cabe
num tipo é `fora_do_catalogo`, e a resposta é a abstenção (H68).

O modelo vê a descrição e o exemplo de cada tipo, e a tela mostra os mesmos
exemplos para a pessoa clicar: o que o assistente sabe responder é um só.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import date, timedelta

from pydantic import BaseModel, Field

from app import formato
from app.esquemas import TipoPergunta
from app.modelos import Segmento


class UsoDoPeriodo(enum.Enum):
    NENHUM = "nenhum"
    UM = "um"  # sem data, o mais recente
    VARIOS = "varios"  # sem data, os mais recentes


@dataclass(frozen=True)
class Entrada:
    tipo: TipoPergunta
    descricao: str
    exemplo: str
    parceiro: bool = False  # precisa de um
    segmento: bool = False  # precisa de um
    categoria: bool = False  # aceita uma, para filtrar
    periodo: UsoDoPeriodo = UsoDoPeriodo.UM


CATALOGO: dict[TipoPergunta, Entrada] = {
    e.tipo: e
    for e in (
        Entrada(
            TipoPergunta.DESEMPENHO_DO_PARCEIRO,
            "O faturamento, os pedidos e o ticket médio de um parceiro num período, contra o "
            "período anterior.",
            "Quanto a Esquina da Serra faturou na semana passada?",
            parceiro=True,
        ),
        Entrada(
            TipoPergunta.EVOLUCAO_DO_PARCEIRO,
            "O faturamento de um parceiro período a período, num intervalo ou nas últimas "
            "semanas.",
            "Como evoluiu o faturamento da Esquina da Serra em agosto?",
            parceiro=True,
            periodo=UsoDoPeriodo.VARIOS,
        ),
        Entrada(
            TipoPergunta.POSICAO_DO_PARCEIRO,
            "A posição de um parceiro no ranking de faturamento de um período.",
            "Em que posição do ranking está a Esquina da Serra?",
            parceiro=True,
        ),
        Entrada(
            TipoPergunta.SEGMENTO_DO_PARCEIRO,
            "O segmento de um parceiro num período: Top, em ascensão, em risco, recém-chegado, "
            "em prospecção ou estável.",
            "A Esquina da Serra está em risco?",
            parceiro=True,
        ),
        Entrada(
            TipoPergunta.PREVISAO_DO_PARCEIRO,
            "A previsão do modelo para um parceiro: a chance de ele entrar em risco no próximo "
            "período e o faturamento previsto.",
            "Qual a chance de a Esquina da Serra cair no próximo período?",
            parceiro=True,
            periodo=UsoDoPeriodo.NENHUM,
        ),
        Entrada(
            TipoPergunta.RANKING,
            "Os parceiros de maior faturamento num período, na rede inteira ou numa categoria.",
            "Quais pizzarias mais faturaram na semana passada?",
            categoria=True,
        ),
        Entrada(
            TipoPergunta.PARCEIROS_DO_SEGMENTO,
            "Quantos e quais parceiros estão num segmento num período, na rede ou numa "
            "categoria.",
            "Quais farmácias estão em risco?",
            segmento=True,
            categoria=True,
        ),
        Entrada(
            TipoPergunta.MOBILIDADE_DO_TOP,
            "Quem entrou e quem saiu do Top do ranking, de um período para o seguinte.",
            "Quem saiu do Top nesta semana?",
        ),
        Entrada(
            TipoPergunta.RESUMO_DO_PERIODO,
            "O faturamento, os pedidos, o ticket médio e os parceiros com movimento da rede "
            "inteira num período.",
            "Como foi a rede na semana passada?",
        ),
        Entrada(
            TipoPergunta.DISTRIBUICAO_DOS_SEGMENTOS,
            "Quantos parceiros há em cada segmento num período.",
            "Como os parceiros se dividem entre os segmentos?",
        ),
        Entrada(
            TipoPergunta.ULTIMO_PLANO,
            "O último plano de campanha calculado: as ações, o custo e o ganho esperado.",
            "Qual é o ganho esperado do último plano?",
            periodo=UsoDoPeriodo.NENHUM,
        ),
    )
}


DATA_ISO = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$"


class Extracao(BaseModel):
    """O que o modelo devolve: o tipo e os campos, como estão na pergunta.

    **Todo campo é obrigatório, ainda que nulo.** Com os campos opcionais, o
    modelo fechava o JSON logo depois do tipo, e nenhuma data chegava: na sonda
    do H65, zero das seis perguntas com data. Obrigado a escrever cada campo, ele
    precisa decidir sobre cada um.

    Os campos são texto, e não tipos estritos, de propósito: uma data impossível
    ou um número fora da faixa derrubariam a validação inteira, e a pessoa leria
    "o modelo falhou" onde o certo é pedir a precisão. Quem valida é a resolução.
    """

    tipo: TipoPergunta
    parceiro: str | None
    categoria: str | None
    segmento: Segmento | None
    # O padrão entra na gramática da saída: sem ele, uma data saiu "log(2026-09-07)".
    inicio: str | None = Field(pattern=DATA_ISO)
    fim: str | None = Field(pattern=DATA_ISO)
    quantos: int | None


# Como a pessoa chama cada segmento — para o modelo reconhecer, e não para a tela.
NOMES_DO_SEGMENTO = {
    Segmento.TOP: "Top, os maiores do ranking",
    Segmento.EM_ASCENSAO: "em ascensão, crescendo",
    Segmento.EM_RISCO: "em risco, em queda, caindo",
    Segmento.RECEM_CHEGADO: "recém-chegados, novos na rede",
    Segmento.PROSPECCAO: "em prospecção, sem vendas ainda",
    Segmento.ESTAVEL: "estáveis",
}

MESES = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)

# Cada regra responde a um erro medido na sonda do H65: a pergunta sobre a rede
# classificada como de um parceiro, "quais farmácias estão em risco" como o
# segmento de um parceiro, e a média e a soma respondidas como desempenho.
REGRAS = (
    "- Os tipos terminados em _do_parceiro são sobre um parceiro só, citado pelo nome na "
    "pergunta. Pergunta sobre a rede inteira, sobre uma categoria ou sobre um segmento nunca é "
    "_do_parceiro.",
    '- "Quais" ou "quantos" parceiros estão num segmento é parceiros_do_segmento, com ou sem '
    "categoria.",
    '- "Top 3" ou "os 5 maiores", com número, é ranking, e o número vai em quantos. O segmento '
    "TOP é quando a pergunta fala do segmento, sem pedir uma lista de tamanho certo.",
    '- Toda expressão de tempo — "semana passada", "nesta semana", um mês, um dia — preenche '
    "inicio e fim.",
    "- Soma, média, total de mais de uma semana ou comparação entre parceiros é "
    f"{TipoPergunta.FORA_DO_CATALOGO}, mesmo que a pergunta fale de faturamento: essas contas o "
    "sistema não faz.",
    "- Você não responde à pergunta e não inventa campo: o que a pergunta não traz fica nulo.",
)


def _exemplos_de_data(periodos: list[tuple[date, date]]) -> str:
    """As expressões de tempo mais comuns, com as datas desta base.

    Sem exemplo, o modelo não preenchia data nenhuma; "semana passada" depende de
    qual é a semana mais recente, e só a base sabe.
    """
    inicio, fim = periodos[-1]
    exemplos = [f'"nesta semana" e "na última semana" são {inicio} e {fim}']
    if len(periodos) > 1:
        antes, depois = periodos[-2]
        exemplos.append(f'"na semana passada" e "no período anterior", {antes} e {depois}')
    fim_do_mes = fim.replace(day=1) - timedelta(days=1)
    mes = MESES[fim_do_mes.month - 1]
    exemplos += [
        f'"em {mes}", {fim_do_mes.replace(day=1)} e {fim_do_mes}',
        f'"na semana de 10 de {mes}", {fim_do_mes.replace(day=10)} e {fim_do_mes.replace(day=10)}',
    ]
    return "; ".join(exemplos)


def instrucao(categorias: list[str], periodos: list[tuple[date, date]]) -> str:
    """A instrução ao modelo, com o que ele precisa da base para ler as datas e as categorias.

    `periodos` vai do mais antigo ao mais recente, e não pode vir vazio: sem
    período, o assistente nem pergunta ao modelo.
    """
    tipos = "\n".join(
        f'- {e.tipo}: {e.descricao} Exemplo: "{e.exemplo}"' for e in CATALOGO.values()
    )
    segmentos = "; ".join(f"{s} ({nome})" for s, nome in NOMES_DO_SEGMENTO.items())
    primeiro, ultimo = periodos[0], periodos[-1]
    campos = [
        "- parceiro: o nome do parceiro exatamente como está escrito na pergunta. Nulo se a "
        "pergunta não cita um parceiro.",
        "- categoria: se a pergunta cita uma categoria, qual destas: "
        + ", ".join(categorias)
        + ". Nula se não cita.",
        f"- segmento: se a pergunta cita um segmento, o código dele: {segmentos}. Nulo se não "
        "cita.",
        "- inicio e fim: o primeiro e o último dia do intervalo de que a pergunta fala, no "
        f"formato AAAA-MM-DD. Os dados são semanais, e vão de {formato.data(primeiro[0])} a "
        f"{formato.data(ultimo[1])}. Nesta base, {_exemplos_de_data(periodos)}. Sem o ano, use "
        f"{ultimo[1].year}. Nulos só se a pergunta não fala de tempo nenhum.",
        '- quantos: o tamanho da lista que a pergunta pede, como em "os 5 maiores". Nulo se ela '
        "não diz.",
    ]
    return "\n".join(
        [
            "Você lê perguntas sobre uma rede de comércios parceiros de delivery e diz de que "
            "tipo cada uma é, com os campos dela, num JSON.",
            "",
            "Os tipos:",
            tipos,
            f"- {TipoPergunta.FORA_DO_CATALOGO}: todo o resto, e as perguntas que não são sobre "
            "a rede.",
            "",
            "Os campos:",
            *campos,
            "",
            "Regras:",
            *REGRAS,
        ]
    )
