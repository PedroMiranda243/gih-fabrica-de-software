"""A guarda numérica: a RN08 como código (ADR-013).

O modelo de linguagem redige em volta de fatos que o código calculou, e é
instruído a não escrever número que não recebeu. Instrução não é garantia: um
modelo arredonda "12,8%" para "13%", troca o mês, ou diz que o faturamento
"dobrou" — e cada uma dessas é um número que o núcleo não produziu (RF43,
RNF16). Esta guarda lê o texto pronto e devolve **todo número que não veio dos
fatos**. Texto com algum deles não chega à tela: quem chama troca pelo modelo
fixo, que só tem os números dos fatos.

**O que conta como número**, em português do Brasil:

- inteiros e decimais (`412`, `1.234`, `12,8`), com `mil` e `milhões`;
- valores em reais (`R$ 12.345,67`);
- percentuais (`12,8%`, `12,8 por cento`), que só casam com percentual dos fatos;
- ordinais (`3º`, `terceiro`);
- datas (`08/2026`, `15/08/2026`, `15/08`, `de 05 a 11/10`, `agosto de 2026`,
  `agosto`, `14 de setembro`, `de 14 a 20 de setembro`), que só casam com data
  dos fatos, componente a componente;
- números por extenso (`três`, `vinte e cinco`, `doze mil`);
- **comparações** (`dobro`, `triplo`, `metade`): não há fato que as sustente,
  porque comparar é conta, e conta é do código (regra 2.3).

**A comparação é exata**, sem tolerância: `13%` não é `12,8%`. O sinal não
conta no valor — "caiu 12,8%" diz a variação de `-12,8%` com palavras —, e o
sentido é conferido à parte (`sentido_trocado`): "caiu 12,8%" onde o fato é
`+12,8%` é número trocado.

**O que fica de fora, de propósito:** "um" e "uma" sozinhos (são artigo, e não
quantidade), "primeiro" e "segundo" (são "antes de tudo" e "de acordo com"), e
"quarta", "quinta" e "sexta" (são dias da semana). Um falso positivo aqui custa
pouco — a mensagem sai do modelo fixo —, mas custa sempre: a guarda precisa
deixar passar o texto certo.

Função pura, sem banco nem rede.
"""

from __future__ import annotations

import datetime as dt
import re
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from decimal import Decimal, InvalidOperation
from enum import Enum

from app.texto import normalizar


class Tipo(str, Enum):
    NUMERO = "NUMERO"
    PERCENTUAL = "PERCENTUAL"
    DATA = "DATA"
    COMPARACAO = "COMPARACAO"


@dataclass(frozen=True)
class Numero:
    """Um número achado no texto: o trecho como está escrito, e o que ele vale."""

    trecho: str
    tipo: Tipo
    # NUMERO e PERCENTUAL: o valor absoluto. DATA: (dia, mês, ano), com None no
    # que o texto não disse. COMPARACAO: None.
    valor: Decimal | tuple[int | None, int | None, int | None] | None
    # Onde o trecho começa no texto, para ler as palavras em volta (`sentido_trocado`).
    inicio: int = field(default=0, compare=False)


# ------------------------------------------------------------------ vocabulário
# Os meses com acento, como o português os escreve: sem o acento, "março" vira
# "marco", que é outra palavra.
MESES = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "abril": 4, "maio": 5, "junho": 6,
    "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
}

# Por extenso, comparados sem acento: "tres" e "três" são o mesmo número.
UNIDADES = {
    "um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5,
    "seis": 6, "sete": 7, "oito": 8, "nove": 9,
    "dez": 10, "onze": 11, "doze": 12, "treze": 13, "catorze": 14, "quatorze": 14,
    "quinze": 15, "dezesseis": 16, "dezessete": 17, "dezoito": 18, "dezenove": 19,
    "vinte": 20, "trinta": 30, "quarenta": 40, "cinquenta": 50, "sessenta": 60,
    "setenta": 70, "oitenta": 80, "noventa": 90,
    "cem": 100, "cento": 100, "duzentos": 200, "duzentas": 200, "trezentos": 300,
    "trezentas": 300, "quatrocentos": 400, "quatrocentas": 400, "quinhentos": 500,
    "quinhentas": 500, "seiscentos": 600, "seiscentas": 600, "setecentos": 700,
    "setecentas": 700, "oitocentos": 800, "oitocentas": 800, "novecentos": 900,
    "novecentas": 900,
}
MULTIPLICADORES = {
    "mil": 1_000,
    "milhao": 1_000_000, "milhoes": 1_000_000,
    "bilhao": 1_000_000_000, "bilhoes": 1_000_000_000,
}
ORDINAIS = {
    "terceiro": 3, "terceira": 3, "quarto": 4, "quinto": 5, "sexto": 6,
    "setimo": 7, "setima": 7, "oitavo": 8, "oitava": 8, "nono": 9, "nona": 9,
    "decimo": 10, "decima": 10,
}
COMPARACOES = {"dobro", "triplo", "quadruplo", "metade"}
# Sozinhas, não são quantidade: "uma campanha", "um cupom".
ARTIGOS = {"um", "uma"}

# ---------------------------------------------------------------- expressões
_MES = "|".join(MESES)
_DATAS = re.compile(
    r"(?P<iso>\b(?P<ia>\d{4})-(?P<im>\d{2})-(?P<id>\d{2})\b)"
    r"|(?P<dma>\b(?P<d>\d{1,2})/(?P<m>\d{1,2})/(?P<a>\d{4})\b)"
    r"|(?P<ma>\b(?P<m2>\d{1,2})/(?P<a2>\d{4})\b)"
    # "de 05 a 11/10": dois dias do mesmo mês, com o mês só no fim.
    r"|(?P<faixa2>\b(?P<gd1>[0-3]?\d)\s+(?:a|e)\s+(?P<gd2>[0-3]?\d)/(?P<gm>[01]?\d)"
    r"(?:/(?P<ga>\d{4}))?\b)"
    # "05/10", sem o ano: o modelo encurta assim o período da ação.
    r"|(?P<dm>\b(?P<d7>[0-3]?\d)/(?P<m7>[01]?\d)\b(?!/))"
    # "de 14 a 20 de setembro": dois dias do mesmo mês.
    rf"|(?P<faixa>\b(?P<fd1>\d{{1,2}})\s+(?:a|e)\s+(?P<fd2>\d{{1,2}})\s+de\s+(?P<fmes>{_MES})"
    r"(?:\s+de\s+(?P<fa>\d{4}))?\b)"
    rf"|(?P<dia>\b(?P<dd>\d{{1,2}})º?\s+de\s+(?P<dmes>{_MES})(?:\s+de\s+(?P<da>\d{{4}}))?\b)"
    rf"|(?P<nome>\b(?P<mes>{_MES})(?:\s+de\s+|\s*/\s*)(?P<a3>\d{{4}})\b)",
    re.IGNORECASE,
)
# O número em algarismos, com o que vem colado nele: "R$" antes; "mil", o
# percentual ou o sinal de ordinal depois.
_ALGARISMOS = re.compile(
    r"(?P<reais>R\$\s*)?"
    r"(?P<sinal>[-−+])?"
    r"(?P<num>\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?)"
    r"(?P<mult>\s*(?:mil|milh(?:ão|ao|ões|oes)|bilh(?:ão|ao|ões|oes))\b)?"
    r"(?P<pct>\s*(?:%|por\s+cento\b|pontos?\s+percentua(?:l|is)\b|p\.\s?p\.))?"
    r"(?P<ord>[ºª°])?",
    re.IGNORECASE,
)
_PALAVRA = re.compile(r"[^\W\d_]+", re.UNICODE)


def _decimal(texto: str) -> Decimal:
    """Um número em algarismos, lido como o pt-BR escreve: ponto de milhar, vírgula decimal.

    `1.234` é mil duzentos e trinta e quatro; `12.8`, que não tem três dígitos
    depois do ponto, é decimal escrito à inglesa — o modelo às vezes escreve assim.
    """
    if "," in texto:
        return Decimal(texto.replace(".", "").replace(",", "."))
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", texto):
        return Decimal(texto.replace(".", ""))
    return Decimal(texto)


def _multiplicador(texto: str | None) -> int:
    if not texto:
        return 1
    return MULTIPLICADORES[normalizar(texto)]


def numeros(texto: str) -> list[Numero]:
    """Todo número do texto, na ordem em que aparece."""
    texto = unicodedata.normalize("NFC", texto)
    achados: list[tuple[int, Numero]] = []
    ocupado = [False] * len(texto)

    def marcar(inicio: int, fim: int) -> None:
        for i in range(inicio, fim):
            ocupado[i] = True

    # Datas primeiro: "08/2026" é uma data, e não o 8 e o 2026.
    for m in _DATAS.finditer(texto):
        if m.group("iso"):
            valores = [(int(m.group("id")), int(m.group("im")), int(m.group("ia")))]
        elif m.group("dma"):
            valores = [(int(m.group("d")), int(m.group("m")), int(m.group("a")))]
        elif m.group("ma"):
            valores = [(None, int(m.group("m2")), int(m.group("a2")))]
        elif m.group("faixa2"):
            mes = int(m.group("gm"))
            ano = int(m.group("ga")) if m.group("ga") else None
            valores = [(int(m.group("gd1")), mes, ano), (int(m.group("gd2")), mes, ano)]
        elif m.group("dm"):
            dia, mes = int(m.group("d7")), int(m.group("m7"))
            if not (1 <= dia <= 31 and 1 <= mes <= 12):
                continue  # "40/50" não é data: os números seguem para a leitura comum
            valores = [(dia, mes, None)]
        elif m.group("faixa"):
            mes = MESES[m.group("fmes").lower()]
            ano = int(m.group("fa")) if m.group("fa") else None
            valores = [(int(m.group("fd1")), mes, ano), (int(m.group("fd2")), mes, ano)]
        elif m.group("dia"):
            ano = int(m.group("da")) if m.group("da") else None
            valores = [(int(m.group("dd")), MESES[m.group("dmes").lower()], ano)]
        else:
            valores = [(None, MESES[m.group("mes").lower()], int(m.group("a3")))]
        for valor in valores:
            achados.append((m.start(), Numero(m.group(0), Tipo.DATA, valor)))
        marcar(m.start(), m.end())

    for m in _ALGARISMOS.finditer(texto):
        if any(ocupado[m.start() : m.end()]):
            continue
        # Um número colado numa palavra ("qwen2") não é quantidade no texto.
        if m.start() > 0 and texto[m.start() - 1].isalpha() and not m.group("reais"):
            continue
        try:
            valor = _decimal(m.group("num")) * _multiplicador(
                (m.group("mult") or "").strip() or None
            )
        except (InvalidOperation, KeyError):
            continue
        tipo = Tipo.PERCENTUAL if m.group("pct") else Tipo.NUMERO
        achados.append((m.start(), Numero(m.group(0).strip(), tipo, abs(valor))))
        marcar(m.start(), m.end())

    achados += _por_extenso(texto, ocupado)
    achados.sort(key=lambda par: par[0])
    return [replace(numero, inicio=posicao) for posicao, numero in achados]


def _por_extenso(texto: str, ocupado: list[bool]) -> list[tuple[int, Numero]]:
    """Os números escritos com palavras, os meses sozinhos e as comparações."""
    palavras = [
        (m.start(), m.end(), m.group(0))
        for m in _PALAVRA.finditer(texto)
        if not any(ocupado[m.start() : m.end()])
    ]
    achados: list[tuple[int, Numero]] = []
    i = 0
    while i < len(palavras):
        inicio, fim, palavra = palavras[i]
        chave = normalizar(palavra)
        if palavra.lower() in MESES:
            mes = MESES[palavra.lower()]
            achados.append((inicio, Numero(palavra, Tipo.DATA, (None, mes, None))))
            i += 1
            continue
        if chave in COMPARACOES:
            achados.append((inicio, Numero(palavra, Tipo.COMPARACAO, None)))
            i += 1
            continue
        if chave in ORDINAIS:
            achados.append((inicio, Numero(palavra, Tipo.NUMERO, Decimal(ORDINAIS[chave]))))
            i += 1
            continue
        if chave not in UNIDADES and chave not in MULTIPLICADORES:
            i += 1
            continue
        # Uma expressão: "cento e vinte e três", "dois mil trezentos". O "e" só
        # junta quando a parte seguinte é menor que a anterior: "cinco e seis"
        # são dois números, e não onze.
        j, total, parcial, usadas = i, 0, 0, []
        ultimo: int | None = None
        aceita_unidade = True
        while j < len(palavras):
            chave_j = normalizar(palavras[j][2])
            if chave_j in MULTIPLICADORES:
                # "mil mil" não é um número: o multiplicador só cresce da esquerda.
                if ultimo is not None and ultimo >= 1000 and MULTIPLICADORES[chave_j] >= ultimo:
                    break
                total += (parcial or 1) * MULTIPLICADORES[chave_j]
                parcial = 0
                ultimo = MULTIPLICADORES[chave_j]
                aceita_unidade = True
            elif chave_j in UNIDADES:
                valor = UNIDADES[chave_j]
                if not aceita_unidade or (ultimo is not None and valor >= ultimo):
                    break
                parcial += valor
                ultimo = valor
                aceita_unidade = False
            elif (
                chave_j == "e"
                and usadas
                and j + 1 < len(palavras)
                and normalizar(palavras[j + 1][2]) in UNIDADES
                and UNIDADES[normalizar(palavras[j + 1][2])] < ultimo
            ):
                aceita_unidade = True
                j += 1
                continue
            else:
                break
            usadas.append(chave_j)
            j += 1
        fim = palavras[j - 1][1]
        # "por cento" depois da expressão faz dela percentual.
        percentual = (
            j + 1 < len(palavras)
            and normalizar(palavras[j][2]) == "por"
            and normalizar(palavras[j + 1][2]) == "cento"
        )
        # "cento" de "por cento" sozinho, ou "um"/"uma" sozinhos, não são número.
        sozinho = len(usadas) == 1
        if sozinho and (usadas[0] in ARTIGOS and not percentual):
            i = j
            continue
        if sozinho and usadas[0] == "cento" and i > 0 and normalizar(palavras[i - 1][2]) == "por":
            i = j
            continue
        if percentual:
            fim = palavras[j + 1][1]
            j += 2
        valor = Decimal(total + parcial)
        tipo = Tipo.PERCENTUAL if percentual else Tipo.NUMERO
        achados.append((inicio, Numero(texto[inicio:fim], tipo, valor)))
        i = j
    return achados


# ------------------------------------------------------------------- os fatos
@dataclass
class Permitidos:
    """Os números que os fatos sustentam, por tipo."""

    numeros: set[Decimal]
    percentuais: set[Decimal]
    datas: list[tuple[int | None, int | None, int | None]]

    def sustenta(self, numero: Numero) -> bool:
        if numero.tipo is Tipo.COMPARACAO:
            return False
        if numero.tipo is Tipo.PERCENTUAL:
            return numero.valor in self.percentuais
        if numero.tipo is Tipo.DATA:
            return any(_data_compativel(numero.valor, data) for data in self.datas)
        # O ano de uma data dos fatos pode aparecer sozinho: "em 2026".
        anos = {Decimal(ano) for _, _, ano in self.datas if ano is not None}
        return numero.valor in self.numeros or numero.valor in anos


def _data_compativel(do_texto, do_fato) -> bool:
    """O texto pode dizer menos que o fato ("agosto" de 08/2026), nunca outra coisa."""
    return all(t is None or t == f for t, f in zip(do_texto, do_fato, strict=True))


def permitidos(fatos: Mapping | Iterable | object) -> Permitidos:
    """Os números de um conjunto de fatos, lidos como o texto seria lido."""
    p = Permitidos(set(), set(), [])

    def visitar(valor) -> None:
        if valor is None or isinstance(valor, bool):
            return
        if isinstance(valor, Mapping):
            for v in valor.values():
                visitar(v)
        elif isinstance(valor, str):
            for n in numeros(valor):
                if n.tipo is Tipo.DATA:
                    p.datas.append(n.valor)
                elif n.tipo is Tipo.PERCENTUAL:
                    p.percentuais.add(n.valor)
                elif n.tipo is Tipo.NUMERO:
                    p.numeros.add(n.valor)
        elif isinstance(valor, dt.datetime | dt.date):
            p.datas.append((valor.day, valor.month, valor.year))
        elif isinstance(valor, int | float | Decimal):
            p.numeros.add(abs(Decimal(str(valor))))
        elif isinstance(valor, Iterable):
            for v in valor:
                visitar(v)

    visitar(fatos)
    return p


def numeros_sem_origem(texto: str, fatos) -> list[str]:
    """Os números do texto que os fatos não sustentam, como estão escritos no texto.

    Lista vazia: o texto só tem número que o código calculou.
    """
    p = permitidos(fatos)
    return [n.trecho for n in numeros(texto) if not p.sustenta(n)]


# ------------------------------------------------------------------ o sentido
# A variação dita com palavras: "caiu 12,8%" é -12,8%. Comparadas sem acento.
SOBE = {
    "sobe", "subiu", "subiram", "subir", "subindo", "alta", "cresce", "cresceu", "cresceram",
    "crescer", "crescendo", "crescimento", "aumento", "aumentou", "aumentaram", "aumentar",
    "avanco", "avancou", "melhora", "melhorou", "expansao",
}
DESCE = {
    "cai", "caiu", "cairam", "caem", "cair", "caindo", "queda", "recuo", "recuou", "recuaram",
    "recuar", "reducao", "reduziu", "reduzir", "baixa", "diminuiu", "diminuiram", "diminuicao",
    "diminuir", "perda", "perdeu", "piora", "piorou", "retracao", "encolheu",
}
# Até onde a palavra pode estar do percentual: "caiu 12,8%", "uma queda de
# 12,8%", "12,8% de queda". A mais próxima vale: numa frase com duas variações,
# cada uma tem o seu verbo.
ANTES = 40
DEPOIS = 15


def _sinal(numero: Numero) -> int:
    """O sinal escrito no trecho: 1, -1, ou 0 quando não há."""
    if numero.trecho[:1] in "-−":
        return -1
    return 1 if numero.trecho[:1] == "+" else 0


def _sentido_da_palavra(texto: str, numero: Numero) -> int:
    antes = texto[max(0, numero.inicio - ANTES) : numero.inicio]
    for palavra in reversed(_PALAVRA.findall(antes)):
        chave = normalizar(palavra)
        if chave in SOBE or chave in DESCE:
            return 1 if chave in SOBE else -1
    fim = numero.inicio + len(numero.trecho)
    for palavra in _PALAVRA.findall(texto[fim : fim + DEPOIS]):
        chave = normalizar(palavra)
        if chave in SOBE or chave in DESCE:
            return 1 if chave in SOBE else -1
    return 0


def _textos(valor) -> Iterable[str]:
    if isinstance(valor, str):
        yield valor
    elif isinstance(valor, Mapping):
        for v in valor.values():
            yield from _textos(v)
    elif isinstance(valor, Iterable):
        for v in valor:
            yield from _textos(v)


def sentido_trocado(texto: str, fatos) -> list[str]:
    """Os percentuais do texto ditos no sentido contrário ao dos fatos.

    A guarda compara o valor sem o sinal, porque "caiu 12,8%" é o jeito certo de
    escrever -12,8%. O preço é que "caiu 12,8%" também passaria onde o fato é
    +12,8% — o número certo, e a notícia invertida. Isto confere o sentido: o
    sinal escrito no texto, ou, sem ele, a palavra mais próxima do número.

    Só vale para o percentual que tem sinal nos fatos. A probabilidade de 13%
    não sobe nem desce; a variação de +12,8%, sim.
    """
    sinais: dict[Decimal, set[int]] = {}
    for valor in _textos(fatos):
        for n in numeros(valor):
            if n.tipo is Tipo.PERCENTUAL and _sinal(n):
                sinais.setdefault(n.valor, set()).add(_sinal(n))

    texto = unicodedata.normalize("NFC", texto)
    trocados = []
    for n in numeros(texto):
        esperado = sinais.get(n.valor) if n.tipo is Tipo.PERCENTUAL else None
        # Com os dois sinais nos fatos para o mesmo valor, não há como saber qual o
        # texto quis dizer — e a dúvida não reprova.
        if not esperado or len(esperado) > 1:
            continue
        escrito = _sinal(n) or _sentido_da_palavra(texto, n)
        if escrito and escrito not in esperado:
            trocados.append(n.trecho)
    return trocados
