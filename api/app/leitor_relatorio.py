"""Interpretador do relatório de desempenho colado ou enviado como CSV.

O formato é **tolerante e guiado por cabeçalho**, decidido pela equipe e
registrado na ADR-009:

    Parceiro;Faturamento;Pedidos
    Comércio Alfa;12500,40;312

O separador pode ser `;`, tabulação ou `,`; a ordem das colunas não importa; e
os nomes aceitam sinônimos. A razão é prática: colar de planilha produz
tabulação, exportar em CSV produz vírgula ou ponto-e-vírgula, e exigir que o
usuário arrume o texto antes de colar transformaria a ingestão num obstáculo.

Este módulo **não toca no banco**. É função pura de texto para resultado — é o
que permite a prévia da H24 usar exatamente o mesmo código da gravação da H21,
sem risco de a prévia mostrar uma coisa e a gravação fazer outra.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from app.texto import normalizar

# Sinônimos aceitos por coluna, já normalizados (minúsculo, sem acento).
COLUNAS = {
    "nome": {"parceiro", "nome", "estabelecimento", "loja", "comercio", "restaurante"},
    "faturamento": {"faturamento", "vendas", "valor", "receita", "total"},
    "pedidos": {"pedidos", "qtd", "quantidade", "numero de pedidos", "n de pedidos"},
}

# Separadores, em ordem de preferência. A vírgula vem por último de propósito:
# em português ela também é separador decimal, e "12.500,40" num arquivo
# separado por vírgula partiria o número ao meio.
SEPARADORES = [";", "\t", "|", ","]


@dataclass
class LinhaLida:
    linha: int
    nome: str
    faturamento: Decimal
    pedidos: int


@dataclass
class LinhaRejeitada:
    linha: int
    conteudo: str
    motivo: str


@dataclass
class Leitura:
    reconhecidos: list[LinhaLida] = field(default_factory=list)
    rejeitados: list[LinhaRejeitada] = field(default_factory=list)
    cabecalho_reconhecido: bool = False
    separador: str | None = None
    primeiras_linhas: list[str] = field(default_factory=list)


class FormatoNaoReconhecido(ValueError):
    """Nenhuma linha foi interpretável (UC03, fluxo A4).

    Carrega as primeiras linhas recebidas: a mensagem sozinha não ajuda ninguém
    a descobrir o que veio errado no que foi colado.
    """

    def __init__(self, mensagem: str, primeiras_linhas: list[str]):
        super().__init__(mensagem)
        self.primeiras_linhas = primeiras_linhas


def detectar_separador(cabecalho: str) -> str:
    """O separador que melhor divide o cabeçalho.

    Decide pelo **cabeçalho**, não pelo corpo: é a única linha em que se sabe o
    que esperar, e valores monetários no corpo estão cheios de pontos e vírgulas
    que confundiriam a contagem.
    """
    for sep in SEPARADORES:
        if cabecalho.count(sep) >= 1:
            return sep
    raise FormatoNaoReconhecido(
        "Não foi possível identificar o separador das colunas.", [cabecalho]
    )


def mapear_colunas(cabecalho: list[str]) -> dict[str, int]:
    """Posição de cada coluna esperada. Levanta se faltar alguma."""
    posicoes: dict[str, int] = {}
    for i, bruto in enumerate(cabecalho):
        rotulo = normalizar(bruto)
        for campo, sinonimos in COLUNAS.items():
            if campo not in posicoes and rotulo in sinonimos:
                posicoes[campo] = i

    faltando = [c for c in COLUNAS if c not in posicoes]
    if faltando:
        raise FormatoNaoReconhecido(
            "O cabeçalho não traz as colunas necessárias: " + ", ".join(faltando) + ".",
            [";".join(cabecalho)],
        )
    return posicoes


def ler_decimal(bruto: str) -> Decimal:
    """Converte valor monetário em português.

    Aceita `12.500,40`, `12500,40`, `12500.40` e `R$ 12.500,40`. A regra que
    resolve a ambiguidade é simples: **o último separador que aparecer é o
    decimal**, e o outro é de milhar.
    """
    limpo = re.sub(r"[^\d,.\-]", "", bruto).strip()
    if not limpo:
        raise InvalidOperation("vazio")

    if "," in limpo and "." in limpo:
        decimal = max(limpo.rfind(","), limpo.rfind("."))
        inteiro = re.sub(r"[,.]", "", limpo[:decimal])
        limpo = inteiro + "." + limpo[decimal + 1:]
    elif "," in limpo:
        limpo = limpo.replace(",", ".")

    return Decimal(limpo)


def ler_inteiro(bruto: str) -> int:
    limpo = re.sub(r"[^\d\-]", "", bruto).strip()
    if not limpo:
        raise ValueError("vazio")
    return int(limpo)


def interpretar(texto: str) -> Leitura:
    """Interpreta o relatório inteiro, sem tocar no banco.

    Linha ruim **não interrompe a leitura**: vira rejeição com motivo, e o
    usuário decide na prévia se segue com o resto (UC03, A5). Interromper no
    primeiro erro faria uma célula errada esconder as outras noventa e nove.
    """
    # `splitlines` ja trata a quebra de linha do Windows, que chega com dois
    # caracteres, e a do Mac antigo. Dividir na mao erraria os dois casos.
    linhas = texto.splitlines()
    primeiras = [x for x in linhas if x.strip()][:3]

    # Guarda o numero da linha **original**: o usuario procura no que colou,
    # onde as linhas em branco contam.
    uteis = [(i + 1, x) for i, x in enumerate(linhas) if x.strip()]
    if not uteis:
        raise FormatoNaoReconhecido("O conteúdo enviado está vazio.", [])

    numero_cabecalho, cabecalho_bruto = uteis[0]
    separador = detectar_separador(cabecalho_bruto)
    cabecalho = next(csv.reader([cabecalho_bruto], delimiter=separador))
    posicoes = mapear_colunas(cabecalho)

    leitura = Leitura(cabecalho_reconhecido=True, separador=separador, primeiras_linhas=primeiras)
    vistos: dict[str, int] = {}

    for numero, bruta in uteis[1:]:
        campos = next(csv.reader([bruta], delimiter=separador))
        maximo = max(posicoes.values())
        if len(campos) <= maximo:
            motivo = f"A linha tem {len(campos)} coluna(s); esperado ao menos {maximo + 1}."
            leitura.rejeitados.append(LinhaRejeitada(numero, bruta, motivo))
            continue

        nome = campos[posicoes["nome"]].strip()
        if not nome:
            leitura.rejeitados.append(LinhaRejeitada(numero, bruta, "Nome do parceiro em branco."))
            continue

        try:
            faturamento = ler_decimal(campos[posicoes["faturamento"]])
        except (InvalidOperation, ValueError):
            bruto = campos[posicoes["faturamento"]]
            leitura.rejeitados.append(
                LinhaRejeitada(numero, bruta, f"Faturamento não numérico: {bruto!r}.")
            )
            continue

        try:
            pedidos = ler_inteiro(campos[posicoes["pedidos"]])
        except ValueError:
            bruto = campos[posicoes["pedidos"]]
            leitura.rejeitados.append(
                LinhaRejeitada(numero, bruta, f"Número de pedidos inválido: {bruto!r}.")
            )
            continue

        if faturamento < 0 or pedidos < 0:
            leitura.rejeitados.append(
                LinhaRejeitada(numero, bruta, "Faturamento e pedidos não podem ser negativos.")
            )
            continue

        # Duas linhas do mesmo parceiro no mesmo período: gravar as duas
        # violaria a unicidade (parceiro, período) e perderia uma delas em
        # silêncio. Recusar a segunda e dizer qual é a primeira deixa o usuário
        # resolver — pode ser duplicata, pode ser nome repetido por engano.
        chave = normalizar(nome)
        if chave in vistos:
            motivo = f"Parceiro repetido — já aparece na linha {vistos[chave]}."
            leitura.rejeitados.append(LinhaRejeitada(numero, bruta, motivo))
            continue
        vistos[chave] = numero

        leitura.reconhecidos.append(LinhaLida(numero, nome, faturamento, pedidos))

    if not leitura.reconhecidos and not leitura.rejeitados:
        raise FormatoNaoReconhecido(
            f"O cabeçalho foi reconhecido na linha {numero_cabecalho}, "
            "mas não veio nenhuma linha de dados.",
            primeiras,
        )

    return leitura


def de_csv(conteudo: bytes) -> str:
    """Decodifica arquivo CSV, tentando UTF-8 e depois a codificação do Windows.

    Planilha exportada no Windows costuma sair em `cp1252`, e decodificar como
    UTF-8 estoura ou produz mojibake no nome do parceiro. O BOM do Excel é
    removido junto.
    """
    for codificacao in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return conteudo.decode(codificacao)
        except UnicodeDecodeError:
            continue
    return conteudo.decode("utf-8", errors="replace")
