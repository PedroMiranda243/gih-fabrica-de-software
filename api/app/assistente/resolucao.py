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

import calendar
import re
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import formato
from app.assistente.catalogo import CONTA, UsoDoPeriodo
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


def sem_artigo(termo: str) -> str:
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
    for candidato in dict.fromkeys((termo, sem_artigo(termo))):
        exato = s.scalar(
            select(Parceiro).where(Parceiro.nome_normalizado == normalizar(candidato)).limit(1)
        )
        if exato is not None:
            return exato
    termo = sem_artigo(termo)
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


def pedido(inicio: str | None, fim: str | None) -> tuple[date, date] | None:
    """O intervalo que a pergunta trouxe, quando as datas se leem — para o tipo que não
    escolhe período por elas, mas precisa conferi-las (a previsão)."""
    de, ate = _data(inicio), _data(fim)
    if de is None and ate is None:
        return None
    de, ate = de or ate, ate or de
    return (de, ate) if de <= ate else (ate, de)


def periodos(
    s: Session, inicio: str | None, fim: str | None, uso: UsoDoPeriodo, *, total: bool = False
) -> list[Periodo] | Resposta:
    """Os períodos de que a pergunta fala, do mais antigo ao mais recente.

    Sem data, o mais recente — ou os mais recentes, na evolução. Com data, os
    períodos que tocam o intervalo: **os dados são semanais**, e "agosto" são
    cinco semanas. Num tipo de um período só, somá-las seria conta que o
    catálogo não faz; escolher uma seria responder outra pergunta. A pessoa
    escolhe — a menos que a pergunta peça o `total`, e aí é a abstenção.
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
    if uso is UsoDoPeriodo.UM and len(achados) > 1 and total:
        return abstencao(CONTA, [fato("Pedido", pedido)])
    if uso is UsoDoPeriodo.UM and len(achados) > 1:
        return precisao(
            f"Os dados são semanais, e de {pedido} há {len(achados)} períodos. De qual deles?",
            [formato.intervalo(p.data_inicio, p.data_fim) for p in achados],
            [fato("Pedido", pedido), fato("Períodos", str(len(achados)))],
        )
    return achados


def semanas(s: Session, inicio: str | None, fim: str | None) -> int:
    """Quantos períodos o intervalo toca; zero sem data."""
    intervalo = pedido(inicio, fim)
    if intervalo is None:
        return 0
    return s.scalar(
        select(func.count())
        .select_from(Periodo)
        .where(Periodo.data_inicio <= intervalo[1], Periodo.data_fim >= intervalo[0])
    ) or 0


# ------------------------------------------------ as datas escritas na pergunta
MESES = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4, "maio": 5, "junho": 6, "julho": 7,
    "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
}
_MES = re.compile(rf"\b({'|'.join(MESES)})\b(?:\s+de\s+((?:19|20)\d{{2}}))?")
_ANO = re.compile(r"\b((?:19|20)\d{2})\b")
_DATA_ESCRITA = re.compile(r"\d{1,2}/\d{1,2}(?:/\d{2,4})?")
RELATIVOS = {
    "mes que vem": ("mes", 1),
    "proximo mes": ("mes", 1),
    "mes passado": ("mes", -1),
    "ano que vem": ("ano", 1),
    "proximo ano": ("ano", 1),
    "ano passado": ("ano", -1),
}


def _o_mes(ano: int, mes: int) -> tuple[date, date]:
    return date(ano, mes, 1), date(ano, mes, calendar.monthrange(ano, mes)[1])


def datas_da_pergunta(
    pergunta: str, referencia: date, *, futuro: bool = False
) -> tuple[date, date] | None:
    """O intervalo que a pergunta cita por mês ou por ano, lido pelo código.

    Só vale quando o modelo não trouxe data nenhuma. Na medição, "em 2019" e "em
    dezembro" chegaram sem data, e a resposta saiu da semana mais recente — a de
    outra pergunta. Aqui "2019" é o ano, e "dezembro" é o mês.

    `referencia` é o fim dos dados. O mês sem o ano é o mais recente até ela;
    na previsão (`futuro`), o próximo a partir dela.
    """
    texto = _DATA_ESCRITA.sub(" ", normalizar(pergunta))
    for expressao, (unidade, passo) in RELATIVOS.items():
        if expressao in texto:
            if unidade == "ano":
                ano = referencia.year + passo
                return date(ano, 1, 1), date(ano, 12, 31)
            indice = referencia.year * 12 + referencia.month - 1 + passo
            return _o_mes(indice // 12, indice % 12 + 1)

    intervalos = []
    for m in _MES.finditer(texto):
        mes = MESES[m.group(1)]
        ano = int(m.group(2)) if m.group(2) else referencia.year
        if not m.group(2) and futuro and mes < referencia.month:
            ano += 1
        if not m.group(2) and not futuro and mes > referencia.month:
            ano -= 1
        intervalos.append(_o_mes(ano, mes))
    if not intervalos:
        intervalos = [(date(int(a), 1, 1), date(int(a), 12, 31)) for a in _ANO.findall(texto)]
    if not intervalos:
        return None
    return min(i[0] for i in intervalos), max(i[1] for i in intervalos)


# A semana que a pergunta diz pelo nome, contada da mais recente: 0 é ela, 1 a
# anterior. "Período anterior" e "semana anterior" ficam de fora: costumam ser a
# comparação ("em relação ao período anterior"), e não a semana perguntada.
_SEMANAS = {
    re.compile(r"\b(?:n?esta|n?essa|ultima|atual) semana\b|\bsemana (?:atual|mais recente)\b"): 0,
    re.compile(r"\bsemana passada\b|\bpenultima semana\b"): 1,
}


def semana_dita(s: Session, pergunta: str) -> tuple[date, date] | None:
    """A semana que a pergunta diz pelo nome — "na última semana", "na semana
    passada" —, lida das datas da base.

    Vale mesmo quando o modelo trouxe outra data. Na evidência da Sprint 08 (#235),
    "Como foi a rede na última semana?" saiu com a semana anterior à mais recente:
    a instrução traz o exemplo com as datas, e o modelo às vezes troca as duas. O
    código sabe qual é qual.

    Não vale se a pergunta cita mês, ano ou data — "a última semana de agosto" é
    outra semana. Com as duas expressões, vale a mais recente: "nesta semana, em
    relação à semana passada" pergunta desta.
    """
    texto = normalizar(pergunta)
    if (
        _DATA_ESCRITA.search(texto)
        or _MES.search(texto)
        or _ANO.search(texto)
        or any(expressao in texto for expressao in RELATIVOS)
    ):
        return None
    citadas = [atras for expressao, atras in _SEMANAS.items() if expressao.search(texto)]
    if not citadas:
        return None
    atras = min(citadas)
    recentes = _recentes(s, atras + 1)
    if len(recentes) <= atras:
        return None
    semana = recentes[0]
    return semana.data_inicio, semana.data_fim


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
