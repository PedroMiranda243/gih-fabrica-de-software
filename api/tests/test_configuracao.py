"""Testes da configuração da segmentação — história H34, requisito RF21.

O que a história promete é que os limiares de RN01 mudem **sem alteração de
código**. Um teste que só confirmasse que a linha do banco mudou não provaria
isso: provaria que a tabela grava. Por isso os testes seguem o valor até onde
ele importa — a classificação gravada e o Top N que o painel conta.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.db import Sessao
from app.modelos import (
    Auditoria,
    ConfiguracaoSegmentacao,
    HistoricoSegmento,
    Importacao,
    Metrica,
    OrigemImportacao,
    Parceiro,
    Perfil,
    Periodo,
    Segmento,
)
from app.servico_segmentacao import reprocessar_tudo

PRIMEIRA_SEMANA = date(2026, 3, 2)
PADRAO_ESPERADO = {"top_n": 15, "periodos_tendencia": 2, "periodos_novato": 3}


@pytest.fixture
def administrador(criar_usuario, autenticar, cliente):
    criar_usuario(login="admin-teste", perfil=Perfil.ADMINISTRADOR)
    autenticar("admin-teste")
    return cliente


@pytest.fixture
def rede(criar_usuario):
    """Dezessete parceiros com faturamento distinto, em três semanas.

    Dezessete porque o Top padrão é 15: com menos, baixar o limiar não teria o
    que tirar de dentro, e o teste passaria sem provar nada.
    """
    autor_id = criar_usuario(login="semeador", perfil=Perfil.ANALISTA)

    def montar(semanas: int = 3) -> list[int]:
        ids = []
        s = Sessao()
        try:
            parceiros: dict[str, Parceiro] = {}
            for indice in range(semanas):
                comeco = PRIMEIRA_SEMANA + timedelta(days=7 * indice)
                periodo = Periodo(data_inicio=comeco, data_fim=comeco + timedelta(days=6))
                s.add(periodo)
                s.flush()
                importacao = Importacao(
                    periodo_id=periodo.id,
                    usuario_id=autor_id,
                    origem=OrigemImportacao.TEXTO,
                    total_gravado=17,
                    total_rejeitado=0,
                )
                s.add(importacao)
                s.flush()
                for i in range(17):
                    nome = f"P{i:02d}"
                    if nome not in parceiros:
                        parceiros[nome] = Parceiro(nome=nome)
                        s.add(parceiros[nome])
                        s.flush()
                    s.add(
                        Metrica(
                            parceiro_id=parceiros[nome].id,
                            periodo_id=periodo.id,
                            importacao_id=importacao.id,
                            faturamento=Decimal(1700 - 100 * i),
                            pedidos=10,
                        )
                    )
                ids.append(periodo.id)
            s.commit()
            return ids
        finally:
            s.close()

    return montar


def _segmentos(periodo_id: int) -> dict[str, Segmento]:
    s = Sessao()
    try:
        return {
            nome: segmento
            for nome, segmento in s.execute(
                select(Parceiro.nome, HistoricoSegmento.segmento)
                .join(HistoricoSegmento, HistoricoSegmento.parceiro_id == Parceiro.id)
                .where(HistoricoSegmento.periodo_id == periodo_id)
            )
        }
    finally:
        s.close()


# ===================================================================== leitura
def test_os_limiares_de_fabrica_sao_os_de_rn01(administrador):
    corpo = administrador.get("/api/configuracao/segmentacao").json()

    assert {c: corpo[c] for c in PADRAO_ESPERADO} == PADRAO_ESPERADO
    # Ninguém mudou ainda: dizer que foi o administrador atual seria inventar
    # um autor para um valor que veio com o sistema.
    assert corpo["atualizado_por"] is None


def test_a_configuracao_responde_com_a_tabela_vazia(administrador):
    """Tabela vazia devolve os padrões e grava a linha, em vez de estourar.

    A linha é semeada pela migração, mas isso **não dá para observar aqui**: o
    `conftest` trunca todas as tabelas entre os testes, e a linha semeada vai
    junto. O que este teste cobre é o caso real que sobra — um banco migrado de
    uma versão anterior, onde a rota de leitura não pode devolver 500 por causa
    de uma linha ausente que tem padrão conhecido.
    """
    s = Sessao()
    try:
        assert s.get(ConfiguracaoSegmentacao, 1) is None
    finally:
        s.close()

    corpo = administrador.get("/api/configuracao/segmentacao").json()

    assert {c: corpo[c] for c in PADRAO_ESPERADO} == PADRAO_ESPERADO
    s = Sessao()
    try:
        assert s.get(ConfiguracaoSegmentacao, 1) is not None
    finally:
        s.close()


# ==================================================================== alteração
def test_alterar_muda_o_que_o_painel_conta(administrador, rede):
    rede()

    administrador.put("/api/configuracao/segmentacao", json={**PADRAO_ESPERADO, "top_n": 5})

    corpo = administrador.get("/api/painel/mobilidade").json()
    assert corpo["top_n"] == 5


def test_alterar_reclassifica_o_periodo_mais_recente(administrador, rede):
    """Configuração que não se reflete na tela engana quem a mudou.

    Sem o reprocessamento, o administrador baixaria o Top de 15 para 5, abriria
    o painel e veria as mesmas quinze linhas marcadas como Top.
    """
    ids = rede()
    administrador.put("/api/configuracao/segmentacao", json=PADRAO_ESPERADO)
    assert sum(1 for s in _segmentos(ids[-1]).values() if s is Segmento.TOP) == 15

    resposta = administrador.put(
        "/api/configuracao/segmentacao", json={**PADRAO_ESPERADO, "top_n": 5}
    )

    assert resposta.json()["periodos_reprocessados"] == 1
    assert sum(1 for s in _segmentos(ids[-1]).values() if s is Segmento.TOP) == 5


def test_os_periodos_anteriores_ficam_como_estavam(administrador, rede):
    """E a resposta diz isso, em vez de deixar a diferença passar calada.

    Reprocessar doze períodos com 10.000 parceiros levaria segundos dentro da
    requisição, e o teto de 2 s do RNF03 vale para o sistema todo.
    """
    # Quatro semanas, e não três: o período anterior precisa ter **três**
    # períodos de histórico atrás dele, senão a regra o classifica inteiro como
    # recém-chegado e não sobra nenhum Top para comparar depois.
    ids = rede(semanas=4)
    # A base inteira classificada com o limiar antigo: é esse o estado que a
    # alteração **não** pode reescrever sozinha. Sem este passo, o período
    # anterior não teria segmento nenhum e o teste confundiria "ficou como
    # estava" com "nunca foi classificado".
    s = Sessao()
    try:
        reprocessar_tudo(s)
        s.commit()
    finally:
        s.close()
    assert sum(1 for seg in _segmentos(ids[-2]).values() if seg is Segmento.TOP) == 15

    resposta = administrador.put(
        "/api/configuracao/segmentacao", json={**PADRAO_ESPERADO, "top_n": 5}
    )

    assert resposta.json()["periodos_reprocessados"] == 1
    assert sum(1 for seg in _segmentos(ids[-1]).values() if seg is Segmento.TOP) == 5
    # O penúltimo continua com a classificação do limiar antigo.
    assert sum(1 for seg in _segmentos(ids[-2]).values() if seg is Segmento.TOP) == 15


def test_a_alteracao_registra_quem_mudou(administrador, rede):
    rede()

    corpo = administrador.put(
        "/api/configuracao/segmentacao", json={**PADRAO_ESPERADO, "top_n": 7}
    ).json()

    assert corpo["atualizado_por"] == "Admin-teste"
    assert corpo["top_n"] == 7


def test_a_trilha_guarda_o_valor_anterior(administrador, rede):
    """"Alterou a configuração" sem o que era antes não responde à pergunta que
    a auditoria existe para responder."""
    rede()

    administrador.put("/api/configuracao/segmentacao", json={**PADRAO_ESPERADO, "top_n": 7})

    s = Sessao()
    try:
        registro = s.scalars(
            select(Auditoria)
            .where(Auditoria.acao == "SEGMENTACAO_CONFIGURADA")
            .order_by(Auditoria.id.desc())
        ).first()
    finally:
        s.close()

    assert registro is not None
    assert registro.detalhes["anterior"]["top_n"] == 15
    assert registro.detalhes["novo"]["top_n"] == 7


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("top_n", 0),
        ("periodos_tendencia", 0),
        ("periodos_novato", 0),
        ("top_n", -1),
    ],
)
def test_limiar_sem_sentido_e_recusado(administrador, campo, valor):
    """Zero não é "mais permissivo", é sem sentido: Top 0 não tem ninguém
    dentro, e tendência de 0 períodos classificaria a rede inteira como em risco
    **e** em ascensão ao mesmo tempo."""
    resposta = administrador.put(
        "/api/configuracao/segmentacao", json={**PADRAO_ESPERADO, campo: valor}
    )

    assert resposta.status_code == 422


def test_o_limiar_de_novato_configurado_vale_na_classificacao(administrador, rede):
    """O caminho inteiro: muda o limiar, e a classificação gravada muda junto."""
    ids = rede(semanas=3)
    administrador.put("/api/configuracao/segmentacao", json=PADRAO_ESPERADO)
    assert Segmento.RECEM_CHEGADO not in _segmentos(ids[-1]).values()

    administrador.put(
        "/api/configuracao/segmentacao", json={**PADRAO_ESPERADO, "periodos_novato": 4}
    )

    # Três semanas de histórico agora são pouco: todos viram recém-chegados.
    assert set(_segmentos(ids[-1]).values()) == {Segmento.RECEM_CHEGADO}


def test_sem_periodo_importado_a_alteracao_nao_reprocessa_nada(administrador):
    corpo = administrador.put(
        "/api/configuracao/segmentacao", json={**PADRAO_ESPERADO, "top_n": 9}
    ).json()

    assert corpo["periodos_reprocessados"] == 0
    assert corpo["top_n"] == 9


def test_limiar_abaixo_do_minimo_diz_o_minimo(administrador):
    corpo = administrador.put(
        "/api/configuracao/segmentacao", json={**PADRAO_ESPERADO, "top_n": 0}
    ).json()

    assert corpo["campos"][0]["mensagem"] == "Use um valor a partir de 1."
