"""Normalização de texto para comparação — uma regra, num lugar só.

Este módulo existe porque a mesma normalização passou a ser usada em três
lugares que não deviam depender um do outro: o interpretador do relatório casa o
nome do parceiro por ela, o modelo grava a forma normalizada em coluna, e a
busca compara contra essa coluna — a da lista de parceiros e a do assistente.

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


def para_busca(termo: str) -> str:
    """Termo digitado vira padrão de comparação seguro (RF24).

    Duas coisas acontecem aqui, e as duas importam:

    **Normaliza pela mesma regra da coluna.** `nome_normalizado` é gravado por
    `normalizar`; comparar contra um termo cru não encontraria nada com acento,
    que é justamente o defeito que a busca por nome corrige.

    **Escapa os curingas do LIKE.** Sem isso, quem digitasse `%` faria uma busca
    que casa com tudo, e `_` casaria com qualquer caractere — o usuário não pede
    curinga, ele digita um nome. A barra invertida é escapada primeiro, senão
    escaparia os escapes acrescentados depois. Quem usa passa `escape="\\"`.
    """
    normalizado = normalizar(termo)
    for caractere in ("\\", "%", "_"):
        normalizado = normalizado.replace(caractere, f"\\{caractere}")
    return normalizado
