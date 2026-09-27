"""A rede de parceiros dos testes da campanha e das mensagens.

Gravada direto no banco — parceiros, cinco semanas de métricas, o segmento na
semana mais recente, um treino concluído e as previsões dele —, sem treinar de
verdade: o que importa é controlar o faturamento, o risco, o ranking, o segmento
e a categoria de cada parceiro. A fixture `base` é registrada na `conftest.py`.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.db import Sessao
from app.modelos import (
    AcaoComercial,
    Categoria,
    ConfiguracaoSegmentacao,
    HistoricoSegmento,
    Importacao,
    Metrica,
    OrigemCategoria,
    OrigemImportacao,
    Parceiro,
    Perfil,
    Periodo,
    Previsao,
    SituacaoTreino,
    StatusComercial,
    TreinoModelo,
)

PRIMEIRA_SEMANA = date(2026, 6, 1)
PERIODOS = 5
VISITA = ("Visita de relacionamento", "90.00", "0.06", "0.30")
VITRINE = ("Destaque na vitrine", "260.00", "0.14", "0.05")


def parceiro(nome, faturamento, **extra):
    return {"nome": nome, "faturamento": Decimal(faturamento), **extra}


@pytest.fixture
def base(criar_usuario):
    """Grava a rede e devolve os ids. Cada parceiro é um dict:

    - `faturamento`: o do período-base, que decide o ranking;
    - `previsto` e `risco`: a previsão da versão em uso; sem `previsto`, não há;
    - `categoria` e `origem`: a categoria e se ela foi confirmada (RN05);
    - `segmento`: o da semana mais recente, gravado como a segmentação gravaria;
    - `status`, `ativo`, `periodos` (quantos até a base) e `na_base`.
    """
    autor = criar_usuario(login="semeador", perfil=Perfil.ANALISTA)

    def montar(parceiros, *, top_n=15, acoes=(VISITA, VITRINE), treinado=True):
        s = Sessao()
        try:
            s.add(
                ConfiguracaoSegmentacao(id=1, top_n=top_n, periodos_tendencia=2, periodos_novato=3)
            )
            periodos = []
            for i in range(PERIODOS):
                comeco = PRIMEIRA_SEMANA + timedelta(days=7 * i)
                p = Periodo(data_inicio=comeco, data_fim=comeco + timedelta(days=6))
                s.add(p)
                s.flush()
                imp = Importacao(
                    periodo_id=p.id,
                    usuario_id=autor,
                    origem=OrigemImportacao.TEXTO,
                    total_gravado=0,
                    total_rejeitado=0,
                )
                s.add(imp)
                s.flush()
                periodos.append((p.id, imp.id))
            base_id = periodos[-1][0]

            categorias = {}
            for spec in parceiros:
                nome = spec.get("categoria")
                if nome and nome not in categorias:
                    c = Categoria(nome=nome)
                    s.add(c)
                    s.flush()
                    categorias[nome] = c.id

            treino = None
            if treinado:
                treino = TreinoModelo(
                    situacao=SituacaoTreino.CONCLUIDO,
                    periodo_base_id=base_id,
                    semente=42,
                    promovido=True,
                    versao_em_uso="rede-1",
                )
                s.add(treino)

            ids = {}
            for spec in parceiros:
                cat = categorias.get(spec.get("categoria"))
                parceiro = Parceiro(
                    nome=spec["nome"],
                    categoria_id=cat,
                    origem_categoria=spec.get("origem", OrigemCategoria.MANUAL) if cat else None,
                    status=spec.get("status", StatusComercial.ATIVO),
                    ativo=spec.get("ativo", True),
                )
                s.add(parceiro)
                s.flush()
                ids[spec["nome"]] = parceiro.id
                # Os últimos `quantos` períodos até a base; ou, fora dela, os
                # anteriores. `[-0:]` seria a lista inteira, daí o caso do zero.
                quantos = spec.get("periodos", PERIODOS)
                candidatos = periodos if spec.get("na_base", True) else periodos[:-1]
                escolhidos = candidatos[-quantos:] if quantos else []
                for periodo_id, importacao_id in escolhidos:
                    s.add(
                        Metrica(
                            parceiro_id=parceiro.id,
                            periodo_id=periodo_id,
                            importacao_id=importacao_id,
                            faturamento=spec["faturamento"],
                            pedidos=10,
                        )
                    )
                if "segmento" in spec:
                    s.add(
                        HistoricoSegmento(
                            parceiro_id=parceiro.id, periodo_id=base_id, segmento=spec["segmento"]
                        )
                    )
                if treinado and "previsto" in spec:
                    s.add(
                        Previsao(
                            parceiro_id=parceiro.id,
                            periodo_base_id=base_id,
                            faturamento_previsto=Decimal(spec["previsto"]),
                            probabilidade_queda=spec.get("risco", 0.2),
                            modelo_versao="rede-1",
                        )
                    )
            for nome, custo, crescimento, retencao in acoes:
                s.add(
                    AcaoComercial(
                        nome=nome,
                        custo_unitario=Decimal(custo),
                        efeito_crescimento=Decimal(crescimento),
                        efeito_retencao=Decimal(retencao),
                    )
                )
            s.commit()
            return SimpleNamespace(base_id=base_id, parceiros=ids, categorias=categorias)
        finally:
            s.close()

    return montar
