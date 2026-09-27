"""O CSV que vai para a planilha — o formato e a proteção contra fórmula, num lugar só.

Duas exportações usam isto: a lista de parceiros (RF25, H38) e as mensagens
aprovadas (RF40, H64). Duas cópias da proteção contra fórmula divergiriam, e a
exportação que esquecesse de uma letra seria a porta aberta (H70).
"""
from __future__ import annotations

import csv
import io
from collections.abc import Callable, Iterator, Sequence

from app.db import Sessao

# Ponto e vírgula, e não vírgula: é o que o Excel em português espera, e é o
# mesmo separador que a importação aceita. Vírgula obrigaria o usuário a passar
# pelo assistente de importação de texto para abrir o próprio arquivo.
SEPARADOR_CSV = ";"

# O primeiro caractere que faz a planilha ler a célula como fórmula. O nome, a
# categoria e o contato vêm de quem cadastra ou importa, e o texto da mensagem
# vem do modelo de linguagem ou do gestor; um valor como `=HYPERLINK("http://...")`
# viraria um link — ou coisa pior — na planilha de quem exporta (injeção de CSV,
# OWASP). A tabulação e o retorno de carro estão aqui porque algumas planilhas os
# descartam antes de olhar o resto.
INICIO_DE_FORMULA = ("=", "+", "-", "@", "\t", "\r")


def texto(valor: str | None) -> str:
    """Texto do usuário numa célula: com um apóstrofo na frente, se começaria uma
    fórmula (RNF12). A planilha mostra o texto como foi digitado e não o executa.

    Só nas colunas de texto: nas de número, o sinal de menos da variação é número
    de verdade, e o apóstrofo o transformaria em texto que não se soma.
    """
    if not valor:
        return ""
    return f"'{valor}" if valor.startswith(INICIO_DE_FORMULA) else valor


def numero(valor) -> str:
    """Número com vírgula decimal e sem separador de milhar.

    É o que a planilha em português lê como número. Com ponto decimal ela trata
    a coluna inteira como texto, e o usuário exporta para não conseguir somar.
    """
    return "" if valor is None else str(valor).replace(".", ",")


def gerar(cabecalho: Sequence[str], consulta, linha: Callable[[object], Sequence]) -> Iterator[str]:
    """Gera o arquivo linha a linha, sem montar a lista inteira antes.

    **Abre a própria sessão**, em vez de reusar a da requisição. O corpo de uma
    resposta em fluxo é consumido **depois** que a função da rota retorna, e a
    essa altura o FastAPI já fechou as dependências: usar a sessão da requisição
    aqui pendura a resposta. Foi exatamente o que aconteceu — os testes de
    exportação travaram até o tempo limite, sem erro nenhum.

    O BOM na primeira linha é o que faz a planilha abrir o arquivo como UTF-8.
    Sem ele, "Praça" vira "PraÃ§a", e o usuário conclui que o sistema gravou o
    nome errado — não que o programa dele adivinhou a codificação.
    """
    buffer = io.StringIO()
    escritor = csv.writer(buffer, delimiter=SEPARADOR_CSV, lineterminator="\r\n")

    def despejar() -> str:
        conteudo = buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)
        return conteudo

    escritor.writerow(cabecalho)
    yield "﻿" + despejar()

    s = Sessao()
    try:
        for bruta in s.execute(consulta.execution_options(yield_per=500)):
            escritor.writerow(linha(bruta))
            yield despejar()
    finally:
        s.close()
