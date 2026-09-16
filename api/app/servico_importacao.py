"""Regras da importação de relatório (UC03 · histórias H21, H23, H24).

A prévia e a gravação usam **o mesmo** caminho de leitura e a **mesma** função
de casamento de parceiro. Se fossem dois códigos parecidos, a prévia acabaria
mostrando uma coisa e a gravação fazendo outra — e a prévia existe justamente
para o usuário confiar no que vai acontecer.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.leitor_relatorio import Leitura, LinhaLida, interpretar, normalizar
from app.modelos import (
    Importacao,
    Metrica,
    OrigemImportacao,
    Parceiro,
    Periodo,
    Usuario,
)


@dataclass
class Analise:
    leitura: Leitura
    parceiros_novos: list[str]
    periodo_ja_importado: bool


class PeriodoJaImportado(Exception):
    """RF12 — reimportar um período exige decisão explícita.

    A opção de substituir é a H25, na Sprint 6. Até lá a resposta é recusar: o
    padrão do RF12 é cancelar, e gravar por cima sem perguntar é exatamente o
    que a regra proíbe.
    """


def _indice_de_parceiros(s: Session) -> dict[str, Parceiro]:
    """Todos os parceiros, indexados pelo nome normalizado, **em uma consulta**.

    Buscar parceiro por parceiro funcionaria com 100 e morreria com 10.000, que
    é a carga do RNF04 — a armadilha do N+1 já está registrada no CLAUDE.md
    para a segmentação, e vale igual aqui.
    """
    return {normalizar(p.nome): p for p in s.scalars(select(Parceiro))}


def analisar(s: Session, texto: str, inicio: date, fim: date) -> Analise:
    """Lê o relatório e confronta com a base, **sem gravar nada** (H24).

    Pode ser repetida à vontade: é consulta.
    """
    leitura = interpretar(texto)
    existentes = _indice_de_parceiros(s)

    novos: list[str] = []
    vistos: set[str] = set()
    for linha in leitura.reconhecidos:
        chave = normalizar(linha.nome)
        if chave not in existentes and chave not in vistos:
            vistos.add(chave)
            novos.append(linha.nome)

    periodo = s.scalar(
        select(Periodo).where(Periodo.data_inicio == inicio, Periodo.data_fim == fim)
    )
    ja_importado = False
    if periodo is not None:
        ja_importado = (
            s.scalar(select(Importacao.id).where(Importacao.periodo_id == periodo.id).limit(1))
            is not None
        )

    return Analise(leitura=leitura, parceiros_novos=novos, periodo_ja_importado=ja_importado)


def gravar(
    s: Session,
    texto: str,
    inicio: date,
    fim: date,
    autor: Usuario,
    origem: OrigemImportacao = OrigemImportacao.TEXTO,
) -> tuple[Importacao, Analise]:
    """Grava as métricas do período e cadastra os parceiros novos (H21).

    Tudo dentro da transação da requisição: ou o período inteiro entra, ou nada
    entra (UC03, E2). As linhas rejeitadas não impedem a gravação das válidas —
    o usuário já decidiu isso na prévia (UC03, A5).
    """
    analise = analisar(s, texto, inicio, fim)
    if analise.periodo_ja_importado:
        raise PeriodoJaImportado

    periodo = s.scalar(
        select(Periodo).where(Periodo.data_inicio == inicio, Periodo.data_fim == fim)
    )
    if periodo is None:
        periodo = Periodo(data_inicio=inicio, data_fim=fim)
        s.add(periodo)
        s.flush()

    importacao = Importacao(
        periodo_id=periodo.id,
        usuario_id=autor.id,
        origem=origem,
        total_gravado=0,
        total_rejeitado=len(analise.leitura.rejeitados),
    )
    s.add(importacao)
    s.flush()

    parceiros = _indice_de_parceiros(s)
    for nome in analise.parceiros_novos:
        # Categoria fica em branco: a sugestão a partir do nome é a H27, e
        # categoria inferida só vale como sugestão até alguém confirmar (RN05).
        # Melhor vazio que palpite gravado como se fosse decisão.
        novo = Parceiro(nome=nome)
        s.add(novo)
        parceiros[normalizar(nome)] = novo
    s.flush()

    for linha in analise.leitura.reconhecidos:
        _gravar_metrica(s, linha, parceiros, periodo.id, importacao.id)

    importacao.total_gravado = len(analise.leitura.reconhecidos)
    s.flush()
    return importacao, analise


def _gravar_metrica(
    s: Session,
    linha: LinhaLida,
    parceiros: dict[str, Parceiro],
    periodo_id: int,
    importacao_id: int,
) -> None:
    # Ticket médio **não** é gravado: é faturamento dividido por pedidos,
    # calculado na consulta (RN04). Guardá-lo faria o valor divergir das
    # parcelas que o originam na primeira correção de dado.
    s.add(
        Metrica(
            parceiro_id=parceiros[normalizar(linha.nome)].id,
            periodo_id=periodo_id,
            importacao_id=importacao_id,
            faturamento=linha.faturamento,
            pedidos=linha.pedidos,
        )
    )
