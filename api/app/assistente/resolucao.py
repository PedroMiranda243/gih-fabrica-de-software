"""Dos campos que o modelo extraiu às entidades da base.

O modelo copia da pergunta; aqui se confere se o que ele copiou existe. **O
nome que não está na base não vira resposta**, e o parceiro que nem está na
pergunta também não: foi o que a sonda da ADR-013 pegou — "Qual a capital da
França?" classificada como pergunta de segmento, com o parceiro
"catálogo_geográfico".

Cada função devolve a entidade, ou a `Resposta` que pede a precisão (UC12-A2)
ou declara que não há base para responder (A1).
"""
from __future__ import annotations

import re
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import formato
from app.assistente.catalogo import UsoDoPeriodo
from app.assistente.respostas import (
    MAXIMO_NA_LISTA,
    PERIODOS_NA_EVOLUCAO,
    QUANTOS_PADRAO,
    Resposta,
    abstencao,
    fato,
    precisao,
)
from app.modelos import Categoria, Parceiro, Periodo
from app.texto import normalizar, para_busca

# Quantas opções uma precisão oferece. Mais que isso, a pergunta precisa de mais
# do nome, e não de uma lista maior.
MAXIMO_DE_CANDIDATOS = 5
# O limiar padrão do `pg_trgm`: abaixo dele, "parecido" já é chute.
SEMELHANCA_MINIMA = 0.3
ARTIGOS = {"a", "o", "as", "os"}


def citado(termo: str, pergunta: str) -> bool:
    """Se o termo saiu da pergunta, e não da cabeça do modelo.

    Palavra a palavra, normalizadas: o modelo pode trocar a ordem ou deixar um
    "da" de fora, mas não pode trazer palavra que a pessoa não escreveu.
    """
    palavras = re.findall(r"\w+", normalizar(termo))
    texto = normalizar(pergunta)
    return bool(palavras) and all(p in texto for p in palavras)


def _sem_artigo(termo: str) -> str:
    palavras = termo.split()
    if len(palavras) > 1 and normalizar(palavras[0]) in ARTIGOS:
        return " ".join(palavras[1:])
    return termo


def parceiro(s: Session, termo: str) -> Parceiro | Resposta:
    """O parceiro pelo nome, pela busca normalizada da lista de parceiros (RF24).

    O nome exato vence; senão, o nome que contém o termo, se for um só. Vários:
    a pessoa escolhe. Nenhum: os de nome parecido, que é o erro de digitação.

    O modelo às vezes copia o artigo junto — "A Esquina da Serra" —, e com ele a
    busca parcial não acha nada. O nome com o artigo ainda vale, para o parceiro
    que se chama assim.
    """
    for candidato in dict.fromkeys((termo, _sem_artigo(termo))):
        exato = s.scalar(
            select(Parceiro).where(Parceiro.nome_normalizado == normalizar(candidato)).limit(1)
        )
        if exato is not None:
            return exato
    termo = _sem_artigo(termo)
    normalizado = normalizar(termo)

    contem = Parceiro.nome_normalizado.like(f"%{para_busca(termo)}%", escape="\\")
    total = s.scalar(select(func.count()).select_from(Parceiro).where(contem)) or 0
    if total == 1:
        return s.scalar(select(Parceiro).where(contem))
    if total > 1:
        nomes = s.scalars(
            select(Parceiro.nome).where(contem).order_by(Parceiro.nome).limit(MAXIMO_DE_CANDIDATOS)
        ).all()
        return precisao(
            f'Há {formato.inteiro(total)} parceiros com "{termo}" no nome. De qual deles?',
            list(nomes),
            [fato("Parceiros com o termo no nome", formato.inteiro(total))],
        )

    semelhanca = func.similarity(Parceiro.nome_normalizado, normalizado)
    parecidos = s.scalars(
        select(Parceiro.nome)
        .where(semelhanca >= SEMELHANCA_MINIMA)
        .order_by(semelhanca.desc(), Parceiro.nome)
        .limit(MAXIMO_DE_CANDIDATOS)
    ).all()
    if parecidos:
        return precisao(
            f'Não há parceiro chamado "{termo}". É algum destes?', list(parecidos)
        )
    return abstencao(f'Não há parceiro chamado "{termo}" na base.')


def categoria(s: Session, termo: str) -> Categoria | Resposta:
    """A categoria pelo nome — com o plural e o nome dentro do que a pessoa escreveu:
    "pizzarias" é Pizzaria."""
    todas = s.scalars(select(Categoria).order_by(Categoria.nome)).all()
    chave = normalizar(termo)
    for c in todas:
        if normalizar(c.nome) == chave:
            return c
    contidas = [c for c in todas if normalizar(c.nome) in chave or chave in normalizar(c.nome)]
    if len(contidas) == 1:
        return contidas[0]
    return precisao(
        f'Não há categoria "{termo}". Qual destas?', [c.nome for c in contidas or todas]
    )


def _data(texto: str | None) -> date | None:
    try:
        return date.fromisoformat(texto.strip()) if texto else None
    except ValueError:
        return None


def periodos(
    s: Session, inicio: str | None, fim: str | None, uso: UsoDoPeriodo
) -> list[Periodo] | Resposta:
    """Os períodos de que a pergunta fala, do mais antigo ao mais recente.

    Sem data, o mais recente — ou os mais recentes, na evolução. Com data, os
    períodos que tocam o intervalo: **os dados são semanais**, e "agosto" são
    cinco semanas. Num tipo de um período só, somá-las seria conta que o
    catálogo não faz; escolher uma seria responder outra pergunta. A pessoa
    escolhe.
    """
    if uso is UsoDoPeriodo.NENHUM:
        return []

    de, ate = _data(inicio), _data(fim)
    if (inicio and de is None) or (fim and ate is None):
        recentes = _recentes(s, MAXIMO_DE_CANDIDATOS)
        return precisao(
            "Não entendi a data da pergunta. De qual semana?",
            [formato.intervalo(p.data_inicio, p.data_fim) for p in reversed(recentes)],
        )
    if de is None and ate is None:
        return _recentes(s, 1 if uso is UsoDoPeriodo.UM else PERIODOS_NA_EVOLUCAO)

    de, ate = de or ate, ate or de
    if de > ate:
        de, ate = ate, de
    achados = list(
        s.scalars(
            select(Periodo)
            .where(Periodo.data_inicio <= ate, Periodo.data_fim >= de)
            .order_by(Periodo.data_inicio, Periodo.id)
        )
    )
    pedido = formato.intervalo(de, ate) if de != ate else formato.data(de)
    if not achados:
        primeiro = s.scalar(select(func.min(Periodo.data_inicio)))
        ultimo = s.scalar(select(func.max(Periodo.data_fim)))
        return abstencao(
            f"Não há dados de {pedido}. Os períodos importados vão de {formato.data(primeiro)} "
            f"a {formato.data(ultimo)}.",
            [fato("Pedido", pedido), fato("Dados de", formato.intervalo(primeiro, ultimo))],
        )
    if uso is UsoDoPeriodo.UM and len(achados) > 1:
        return precisao(
            f"Os dados são semanais, e de {pedido} há {len(achados)} períodos. De qual deles?",
            [formato.intervalo(p.data_inicio, p.data_fim) for p in achados],
            [fato("Pedido", pedido), fato("Períodos", str(len(achados)))],
        )
    return achados


def _recentes(s: Session, quantos: int) -> list[Periodo]:
    recentes = s.scalars(
        select(Periodo).order_by(Periodo.data_inicio.desc(), Periodo.id.desc()).limit(quantos)
    ).all()
    return list(reversed(recentes))


def quantos(pedido: int | None) -> int:
    """O tamanho da lista: o pedido, dentro do que cabe numa resposta."""
    if pedido is None or pedido < 1:
        return QUANTOS_PADRAO
    return min(pedido, MAXIMO_NA_LISTA)
