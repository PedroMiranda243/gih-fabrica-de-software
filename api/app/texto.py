"""Normalização de texto para comparação — uma regra, num lugar só.

Este módulo existe porque a mesma normalização passou a ser usada em três
lugares que não deviam depender um do outro: o interpretador do relatório casa o
nome do parceiro por ela, o modelo grava a forma normalizada em coluna, e a
busca compara contra essa coluna.

**Duas normalizações parecidas divergem**, e a que divergir será a que ninguém
testa: a base ficaria com convenções misturadas e a busca passaria a falhar só
para alguns nomes — o defeito que ninguém acha, porque funciona em 95% dos casos.

Não depende de nada da aplicação, de propósito: é função pura de texto, e é o
que permite `app/modelos.py` usá-la sem inverter o sentido das dependências.
"""
from __future__ import annotations

import unicodedata


def normalizar(texto: str) -> str:
    """Minúsculo, sem acento, sem espaço nas pontas.

    `casefold` em vez de `lower` porque ele trata os casos que `lower` deixa
    passar em outras escritas — é a operação que o Python oferece justamente
    para comparação, e não para exibição.

    A decomposição NFKD separa a letra do acento, e o filtro remove os
    combinantes: é como "Comércio" e "comercio" viram a mesma chave.
    """
    sem_acento = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in sem_acento if not unicodedata.combining(c)).strip().casefold()
