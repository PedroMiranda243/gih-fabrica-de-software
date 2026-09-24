"""Sugestão de categoria pelo nome do parceiro — RN05, história H27.

A regra está em `docs/02-requisitos.md` (RN05) e foi aprovada na issue #35:
palavra inteira, sem acento e sem caixa; sugere só quando o nome aponta para
**exatamente uma** categoria, e só se ela existe e está ativa.

**Determinística, e não por modelo de linguagem.** Classificar é decisão do
código (regra 2.3), e o assistente só existe na Sprint 13. Uma tabela de
palavras erra de um jeito que dá para ler e corrigir; um modelo erraria de um
jeito que ninguém consegue explicar ao gestor.

**Sugestão não é confirmação.** O que sai daqui entra como `INFERIDA`, e ação
comercial por categoria só considera `MANUAL`. Por isso errar para o lado do
branco é barato: nome ambíguo não recebe sugestão, e "água" sozinha fica de
fora porque "Água Viva" pode ser qualquer coisa.
"""
from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modelos import Categoria
from app.texto import normalizar

# Escritas como as pessoas escrevem; a comparação normaliza os dois lados.
PALAVRAS: dict[str, tuple[str, ...]] = {
    "Pizzaria": ("pizza", "pizzas", "pizzaria"),
    "Padaria": ("padaria", "panificadora", "pão", "pães"),
    "Lanchonete": ("lanche", "lanches", "lanchonete", "burger", "hambúrguer", "hamburgueria"),
    "Restaurante": ("restaurante", "marmita", "marmitaria", "churrascaria"),
    "Açaí e sorvetes": ("açaí", "sorvete", "sorvetes", "sorveteria"),
    "Mercado": ("mercado", "mercadinho", "minimercado", "supermercado", "mercearia"),
    "Bebidas": ("bebidas", "adega"),
    "Farmácia": ("farmácia", "drogaria"),
    "Petshop": ("pet", "petshop"),
    "Gás e água": ("gás", "botijão", "água mineral"),
}

_INDICE: dict[str, tuple[str, ...]] = {
    normalizar(categoria): tuple(normalizar(p) for p in palavras)
    for categoria, palavras in PALAVRAS.items()
}


def _palavras(texto: str) -> str:
    """O texto como sequência de palavras separadas por um espaço, com as bordas.

    As bordas são o que faz a comparação ser por palavra inteira: " pet " não
    está dentro de " carpete ". E expressões de duas palavras, como "agua
    mineral", casam do mesmo jeito que as de uma.
    """
    return " " + " ".join(re.findall(r"[a-z0-9]+", normalizar(texto))) + " "


def categoria_da_regra(nome: str) -> str | None:
    """A categoria que as palavras do nome apontam — normalizada —, ou `None`.

    `None` quando nenhuma aponta **ou quando mais de uma aponta**: "Pizzaria e
    Lanchonete do Vale" não diz qual das duas é, e adivinhar seria gravar
    palpite com cara de decisão.
    """
    texto = _palavras(nome)
    candidatas = {
        categoria
        for categoria, palavras in _INDICE.items()
        if any(f" {palavra} " in texto for palavra in palavras)
    }
    return candidatas.pop() if len(candidatas) == 1 else None


def categorias_ativas(s: Session) -> dict[str, Categoria]:
    """As categorias ativas da base, pelo nome normalizado.

    Lidas uma vez e passadas adiante: a importação sugere para cada parceiro
    novo, e uma consulta por parceiro é o N+1 que funciona com dez e morre com
    dez mil.
    """
    return {
        normalizar(c.nome): c
        for c in s.scalars(select(Categoria).where(Categoria.ativa.is_(True)))
    }


def sugerir(nome: str, categorias: dict[str, Categoria]) -> Categoria | None:
    """A categoria sugerida para o nome, se a regra apontar uma e ela existir ativa."""
    alvo = categoria_da_regra(nome)
    return categorias.get(alvo) if alvo else None
