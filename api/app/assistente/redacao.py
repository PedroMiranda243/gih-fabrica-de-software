"""A redação da resposta pelo modelo, com a guarda — RF43, RN08, história H67.

O código já respondeu: o texto de `respostas` tem os números certos, e os fatos
que o sustentam. O modelo reescreve esse texto para responder direto ao que foi
perguntado — "a Esquina da Serra está em risco?" pede um "não" antes do
segmento. **A guarda confere o que ele escreveu** contra os fatos: número que
não veio deles, variação no sentido contrário ou unidade que os fatos não têm
("por mês", "em dólares"), e a resposta volta a ser a do código, com o motivo.
Número inventado não chega à tela.

**Só os tipos em prosa passam pelo modelo.** O ranking, a lista de um segmento,
a evolução, a distribuição e a mobilidade são listas, e uma lista reescrita
pode perder um item sem que número nenhum fique errado — omissão que a guarda
não pega. A lista do código já é a resposta mais clara.

A abstenção e o pedido de precisão também não passam: são do código, e dizem
exatamente o que falta.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.assistente.respostas import Resposta
from app.esquemas import SituacaoResposta, TipoPergunta
from app.guarda_numerica import numeros_sem_origem, sentido_trocado
from app.modelos import RedatorMensagem
from app.redator import FalhaDoRedator, Redator
from app.texto import normalizar

REDIGIDOS = frozenset(
    {
        TipoPergunta.DESEMPENHO_DO_PARCEIRO,
        TipoPergunta.POSICAO_DO_PARCEIRO,
        TipoPergunta.SEGMENTO_DO_PARCEIRO,
        TipoPergunta.PREVISAO_DO_PARCEIRO,
        TipoPergunta.RESUMO_DO_PERIODO,
        TipoPergunta.ULTIMO_PLANO,
    }
)

SISTEMA = (
    "Você responde, em português do Brasil, à pergunta de um gestor de uma rede de comércios "
    "parceiros de delivery. Você recebe a pergunta, a resposta que o sistema montou e os fatos "
    "dela. Reescreva a resposta começando pelo que a pergunta quer saber, num parágrafo de no "
    "máximo 3 frases. Todo número, valor, data e porcentagem precisa aparecer exatamente como "
    "está nos fatos: não calcule, não arredonde, não compare e não acrescente número. Variação "
    "negativa é queda, e positiva é alta. Não afirme nada que os fatos não digam, e não diga de "
    "onde vêm os dados: o sistema mostra a fonte à parte. Sem listas e sem títulos."
)
# Uma resposta em prosa tem poucas frases; muito mais que isso é o modelo desandando.
MAXIMO = 800

NUMEROS_SEM_ORIGEM = (
    "O texto do modelo trazia números que não vieram dos dados ({numeros}): a resposta é a "
    "que o sistema montou."
)
SENTIDO_TROCADO = (
    "O texto do modelo invertia o sentido de uma variação ({numeros}): a resposta é a que o "
    "sistema montou."
)
LONGO = "O texto do modelo passou do tamanho de uma resposta: a resposta é a que o sistema montou."
UNIDADE_SEM_ORIGEM = (
    "O texto do modelo punha nos números uma unidade que os dados não têm ({unidades}): a "
    "resposta é a que o sistema montou."
)

# A unidade que muda o sentido de um número certo. Na medição, o modelo escreveu
# "o faturamento previsto para o mês" onde a previsão é de uma semana, e "o
# ticket médio em dólares foi de R$ 91,25". O número era o dos fatos, e a guarda
# numérica deixou passar; a palavra é que não era. Comparadas sem acento.
UNIDADES = {
    "dia", "dias", "diario", "diaria", "diarios", "diarias", "diariamente",
    "mes", "meses", "mensal", "mensais", "mensalmente",
    "ano", "anos", "anual", "anuais", "anualmente", "trimestre", "semestre",
    "dolar", "dolares", "euro", "euros",
}
_PALAVRA = re.compile(r"[^\W\d_]+")
_MOEDA_ESTRANGEIRA = re.compile(r"\b(?:US|U)\$")


def unidades_sem_origem(texto: str, fatos: list[dict]) -> list[str]:
    """As unidades de tempo e de moeda do texto que nenhum fato traz."""
    nos_fatos = {
        normalizar(palavra)
        for f in fatos
        for valor in f.values()
        for palavra in _PALAVRA.findall(str(valor))
    }
    achadas = [
        palavra
        for palavra in _PALAVRA.findall(texto)
        if normalizar(palavra) in UNIDADES and normalizar(palavra) not in nos_fatos
    ]
    achadas += _MOEDA_ESTRANGEIRA.findall(texto)
    return list(dict.fromkeys(achadas))


@dataclass(frozen=True)
class Redacao:
    texto: str
    redator: RedatorMensagem
    # Por que o texto é o do código, quando o modelo tentou e não passou.
    motivo: str | None = None


def _pedido(pergunta: str, resposta: Resposta) -> str:
    linhas = [
        f"Pergunta: {pergunta}",
        "",
        f"Resposta do sistema: {resposta.texto}",
        "",
        "Fatos:",
    ]
    linhas += [f"- {f['fato']}: {f['valor']}" for f in resposta.fatos]
    return "\n".join(linhas)


def redigir(r: Redator, pergunta: str, tipo: TipoPergunta | None, resposta: Resposta) -> Redacao:
    """O texto da resposta: do modelo, se ele redigir e passar pela guarda; senão, do código."""
    do_codigo = Redacao(resposta.texto, RedatorMensagem.MODELO_FIXO)
    if resposta.situacao is not SituacaoResposta.RESPONDIDA or tipo not in REDIGIDOS:
        return do_codigo
    try:
        texto = " ".join(r.redigir(SISTEMA, _pedido(pergunta, resposta)).split())
    except FalhaDoRedator as falha:
        return Redacao(resposta.texto, RedatorMensagem.MODELO_FIXO, str(falha))
    if len(texto) > MAXIMO:
        return Redacao(resposta.texto, RedatorMensagem.MODELO_FIXO, LONGO)
    sem_origem = numeros_sem_origem(texto, resposta.fatos)
    if sem_origem:
        motivo = NUMEROS_SEM_ORIGEM.format(numeros=", ".join(dict.fromkeys(sem_origem)))
        return Redacao(resposta.texto, RedatorMensagem.MODELO_FIXO, motivo)
    trocados = sentido_trocado(texto, resposta.fatos)
    if trocados:
        motivo = SENTIDO_TROCADO.format(numeros=", ".join(dict.fromkeys(trocados)))
        return Redacao(resposta.texto, RedatorMensagem.MODELO_FIXO, motivo)
    unidades = unidades_sem_origem(texto, resposta.fatos)
    if unidades:
        motivo = UNIDADE_SEM_ORIGEM.format(unidades=", ".join(unidades))
        return Redacao(resposta.texto, RedatorMensagem.MODELO_FIXO, motivo)
    return Redacao(texto, RedatorMensagem.MODELO)
