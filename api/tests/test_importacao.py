"""Testes da importação de relatório — histórias H21, H23 e H24.

Requisitos: RF09, RF10, RF11, RF13; regras RN03 e RN04; caso de uso UC03.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import select

from app.db import Sessao
from app.modelos import Metrica, Parceiro, Perfil

PERIODO = {"periodo_inicio": "2026-09-07", "periodo_fim": "2026-09-13"}

RELATORIO = """Parceiro;Faturamento;Pedidos
Comércio Alfa;12500,40;312
Comércio Beta;8940,00;201
Comércio Gama;1250,75;38
"""


@pytest.fixture
def analista(criar_usuario, autenticar, cliente):
    criar_usuario(login="analista", perfil=Perfil.ANALISTA)
    autenticar("analista")
    return cliente


def importar(cliente, texto=RELATORIO, **periodo):
    return cliente.post("/api/importacoes", json={**PERIODO, **periodo, "texto": texto})


# =========================================================== H23 · período
def test_sem_periodo_a_importacao_e_recusada(analista):
    """RN03 — sem o período as métricas ficam órfãs na linha do tempo e a
    segmentação por tendência classifica errado **sem emitir erro**."""
    r = analista.post("/api/importacoes", json={"texto": RELATORIO})

    assert r.status_code == 422
    campos = {c["campo"] for c in r.json()["campos"]}
    assert campos == {"periodo_inicio", "periodo_fim"}


def test_a_recusa_explica_por_que_o_periodo_e_necessario(analista):
    """"Campo obrigatório" faz o usuário preencher qualquer coisa. Dizer o que
    acontece sem o período faz ele preencher a coisa certa."""
    r = analista.post("/api/importacoes", json={"texto": RELATORIO})

    ajuda = r.json()["campos"][0]["ajuda"]
    assert "RN03" in ajuda
    assert "padrão" in ajuda  # explicita que não existe valor padrão


def test_periodo_invertido_e_recusado(analista):
    r = importar(analista, periodo_inicio="2026-09-13", periodo_fim="2026-09-07")

    assert r.status_code == 422
    assert "anterior" in r.text


def test_nao_existe_periodo_padrao(analista):
    """Se um dia alguém 'facilitar' preenchendo a semana atual, este teste cai."""
    r = analista.post("/api/importacoes", json={"texto": RELATORIO, "periodo_inicio": "2026-09-07"})

    assert r.status_code == 422
    assert {c["campo"] for c in r.json()["campos"]} == {"periodo_fim"}


# ============================================================= H24 · prévia
def test_previa_lista_reconhecidos_e_parceiros_novos(analista):
    r = analista.post("/api/importacoes/previa", json={**PERIODO, "texto": RELATORIO})

    assert r.status_code == 200
    corpo = r.json()
    assert corpo["total_reconhecido"] == 3
    assert corpo["total_rejeitado"] == 0
    assert corpo["parceiros_novos"] == ["Comércio Alfa", "Comércio Beta", "Comércio Gama"]
    assert corpo["reconhecidos"][0]["faturamento"] == "12500.40"


def test_previa_nao_grava_nada(analista):
    """A prévia é consulta e pode ser repetida. Se gravasse, conferir o que vai
    entrar já teria feito entrar."""
    analista.post("/api/importacoes/previa", json={**PERIODO, "texto": RELATORIO})
    analista.post("/api/importacoes/previa", json={**PERIODO, "texto": RELATORIO})

    s = Sessao()
    try:
        assert s.scalars(select(Parceiro)).all() == []
        assert s.scalars(select(Metrica)).all() == []
    finally:
        s.close()


def test_previa_traz_o_motivo_de_cada_rejeicao(analista):
    """"3 linhas rejeitadas" não permite corrigir nada."""
    texto = """Parceiro;Faturamento;Pedidos
Comércio Alfa;12500,40;312
;900,00;10
Comércio Beta;abacaxi;20
Comércio Gama;100,00;muitos
Comércio Alfa;300,00;5
"""
    r = analista.post("/api/importacoes/previa", json={**PERIODO, "texto": texto})

    corpo = r.json()
    assert corpo["total_reconhecido"] == 1
    motivos = [x["motivo"] for x in corpo["rejeitados"]]
    assert any("branco" in m for m in motivos)
    assert any("Faturamento" in m for m in motivos)
    assert any("pedidos" in m for m in motivos)
    assert any("repetido" in m and "linha 2" in m for m in motivos)
    # O conteúdo da linha volta junto: sem ele o usuário não acha a linha 4 de
    # um relatório de duzentas.
    assert all(x["conteudo"] for x in corpo["rejeitados"])


def test_previa_avisa_que_o_periodo_ja_foi_importado(analista):
    importar(analista)

    r = analista.post("/api/importacoes/previa", json={**PERIODO, "texto": RELATORIO})

    assert r.json()["periodo_ja_importado"] is True


# ========================================================== H21 · gravação
def test_importa_e_grava_as_metricas(analista):
    r = importar(analista)

    assert r.status_code == 201, r.text
    assert r.json()["total_gravado"] == 3
    assert r.json()["origem"] == "TEXTO"

    s = Sessao()
    try:
        # Junção explícita: `Metrica` não tem relação com `Parceiro` no modelo, e
        # criar uma só para o teste ler mais bonito seria mexer no domínio por
        # conveniência de teste.
        linhas = dict(
            s.execute(
                select(Parceiro.nome, Metrica).join(Metrica, Metrica.parceiro_id == Parceiro.id)
            ).all()
        )
        assert linhas["Comércio Alfa"].faturamento == Decimal("12500.40")
        assert linhas["Comércio Alfa"].pedidos == 312
    finally:
        s.close()


def test_cadastra_os_parceiros_novos_sem_categoria(analista):
    """RN05 — categoria inferida vale como sugestão até alguém confirmar.
    Deixar em branco é melhor que gravar palpite com cara de decisão."""
    importar(analista)

    s = Sessao()
    try:
        parceiros = s.scalars(select(Parceiro)).all()
        assert len(parceiros) == 3
        assert all(p.categoria_id is None and p.origem_categoria is None for p in parceiros)
    finally:
        s.close()


def test_segunda_importacao_reaproveita_o_parceiro(analista):
    importar(analista)
    importar(analista, periodo_inicio="2026-09-14", periodo_fim="2026-09-20")

    s = Sessao()
    try:
        # Três parceiros, seis métricas: os mesmos parceiros em dois períodos.
        assert len(s.scalars(select(Parceiro)).all()) == 3
        assert len(s.scalars(select(Metrica)).all()) == 6
    finally:
        s.close()


def test_ticket_medio_nao_e_gravado(analista):
    """RN04 — é derivado na consulta. Como coluna, divergiria das parcelas que
    o originam na primeira correção de dado."""
    importar(analista)

    assert not hasattr(Metrica, "ticket_medio")
    assert "ticket" not in analista.get("/api/importacoes").text.lower()


def test_periodo_ja_importado_e_recusado(analista):
    """RF12 — o padrão é cancelar. Substituir exige decisão explícita, que é a
    H25, na Sprint 6."""
    importar(analista)

    r = importar(analista)

    assert r.status_code == 409
    assert "já foi importado" in r.json()["detail"]


def test_rejeicao_parcial_nao_impede_as_validas(analista):
    """UC03, A5 — uma célula errada não pode esconder as outras noventa e nove."""
    texto = """Parceiro;Faturamento;Pedidos
Comércio Alfa;12500,40;312
Comércio Beta;abacaxi;201
"""
    r = importar(analista, texto=texto)

    assert r.status_code == 201
    assert r.json()["total_gravado"] == 1
    assert r.json()["total_rejeitado"] == 1


def test_relatorio_sem_nenhuma_linha_valida_nao_grava(analista):
    texto = """Parceiro;Faturamento;Pedidos
Comércio Alfa;abacaxi;312
"""
    r = importar(analista, texto=texto)

    assert r.status_code == 422
    s = Sessao()
    try:
        assert s.scalars(select(Metrica)).all() == []
        # Nem o parceiro entra: a gravação é tudo-ou-nada (UC03, E2).
        assert s.scalars(select(Parceiro)).all() == []
    finally:
        s.close()


def test_formato_nao_reconhecido_mostra_o_que_chegou(analista):
    """UC03, A4 — "formato não reconhecido" sozinho não deixa ninguém descobrir
    o que veio errado."""
    r = importar(analista, texto="isto aqui não é um relatório\nnem de longe\n")

    assert r.status_code == 422
    detalhe = r.json()["detail"]
    assert detalhe["primeiras_linhas_recebidas"][0] == "isto aqui não é um relatório"
    assert "cabeçalho" in detalhe["ajuda"]


def test_entrada_grande_demais_e_recusada(analista):
    """RNF15 — limite explícito para não consumir recurso à toa."""
    from app.config import config

    r = importar(analista, texto="x" * (config.tamanho_maximo_relatorio + 1))

    assert r.status_code == 422


def test_importacao_entra_na_auditoria(cliente, criar_usuario, autenticar, analista):
    """RF06 lista a importação entre as ações sensíveis."""
    importar(analista)

    criar_usuario(login="chefia", perfil=Perfil.ADMINISTRADOR)
    cliente.cookies.clear()
    autenticar("chefia")
    r = cliente.get("/api/auditoria", params={"acao": "IMPORTACAO_REALIZADA"})

    assert r.json()["total"] == 1
    detalhes = r.json()["itens"][0]["detalhes"]
    assert detalhes["gravados"] == 3
    assert detalhes["periodo"] == "2026-09-07 a 2026-09-13"


def test_historico_lista_as_importacoes(analista):
    """RF13 — autor, data de envio, período coberto e total de registros."""
    importar(analista)
    importar(analista, periodo_inicio="2026-09-14", periodo_fim="2026-09-20")

    r = analista.get("/api/importacoes")

    assert r.status_code == 200
    assert len(r.json()) == 2
    # Mais recente primeiro: o histórico serve para conferir o último envio.
    assert r.json()[0]["periodo"]["data_inicio"] == "2026-09-14"
