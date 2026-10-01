"""A base dos testes do painel e dos relatórios: períodos, parceiros e métricas à escolha.

Diferente de `tests/rede.py`, que grava cinco semanas iguais com previsão e plano
para os testes da campanha, aqui **cada semana é escrita no teste**: é o que
deixa conferir uma variação, uma posição no ranking ou uma lacuna na série.

Montada direto no banco, e não pela API de importação: um defeito na ingestão
reprovaria testes que não têm nada a ver com ela. A fixture `semear` é registrada
na `conftest.py`.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.db import Sessao
from app.modelos import (
    Categoria,
    Importacao,
    Metrica,
    OrigemCategoria,
    OrigemImportacao,
    Parceiro,
    Perfil,
    Periodo,
)

PRIMEIRA_SEMANA = date(2026, 3, 2)


@pytest.fixture
def semear(criar_usuario):
    """Monta períodos, parceiros e métricas.

    Cada semana é um dicionário `{nome do parceiro: (faturamento, pedidos)}`.
    Parceiro ausente numa semana simplesmente não recebe métrica ali — é assim
    que se produz a lacuna que a H32 precisa mostrar.

    Devolve os ids dos períodos, na ordem em que foram passados.
    """
    autor_id = criar_usuario(login="semeador", perfil=Perfil.ANALISTA)

    def montar(*semanas: dict[str, tuple[str, int]], inicio: date = PRIMEIRA_SEMANA) -> list[int]:
        ids = []
        s = Sessao()
        try:
            # Parceiro já existente é reaproveitado, como a importação real faz:
            # o nome é único no banco, e chamar esta fábrica duas vezes no mesmo
            # teste tentaria recriá-lo.
            parceiros: dict[str, Parceiro] = {p.nome: p for p in s.query(Parceiro)}
            for indice, semana in enumerate(semanas):
                comeco = inicio + timedelta(days=7 * indice)
                periodo = Periodo(data_inicio=comeco, data_fim=comeco + timedelta(days=6))
                s.add(periodo)
                s.flush()

                # A métrica exige a importação que a trouxe: é o que amarra o
                # dado à sua origem, e o modelo não deixa gravar sem ela.
                importacao = Importacao(
                    periodo_id=periodo.id,
                    usuario_id=autor_id,
                    origem=OrigemImportacao.TEXTO,
                    total_gravado=len(semana),
                    total_rejeitado=0,
                )
                s.add(importacao)
                s.flush()

                for nome, (faturamento, pedidos) in semana.items():
                    if nome not in parceiros:
                        parceiros[nome] = Parceiro(nome=nome)
                        s.add(parceiros[nome])
                        s.flush()
                    s.add(
                        Metrica(
                            parceiro_id=parceiros[nome].id,
                            periodo_id=periodo.id,
                            importacao_id=importacao.id,
                            faturamento=Decimal(faturamento),
                            pedidos=pedidos,
                        )
                    )
                ids.append(periodo.id)
            s.commit()
            return ids
        finally:
            s.close()

    return montar


def segmentar(limiares=None):
    """Roda a segmentação sobre tudo que `semear` colocou no banco.

    `semear` escreve direto no banco, sem passar pela importação — que é o que
    torna os testes independentes da ingestão, mas também o que deixa os
    períodos sem segmento até isto rodar.
    """
    from app.servico_segmentacao import PADRAO, reprocessar_tudo

    s = Sessao()
    try:
        reprocessar_tudo(s, limiares or PADRAO)
        s.commit()
    finally:
        s.close()


def categorizar(**categorias: list[str]) -> dict[str, int]:
    """Cria as categorias e põe cada parceiro na sua. Devolve o id de cada uma."""
    s = Sessao()
    try:
        ids = {}
        for nome, parceiros in categorias.items():
            categoria = Categoria(nome=nome)
            s.add(categoria)
            s.flush()
            ids[nome] = categoria.id
            for parceiro in s.query(Parceiro).filter(Parceiro.nome.in_(parceiros)):
                parceiro.categoria_id = categoria.id
                parceiro.origem_categoria = OrigemCategoria.MANUAL
        s.commit()
        return ids
    finally:
        s.close()
