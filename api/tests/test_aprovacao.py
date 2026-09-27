"""A fila e a decisão das mensagens — UC11, RF37 a RF39, RN06, histórias H61 a H63.

As mensagens são gravadas direto no banco, como a geração as deixa: o que se
testa aqui é a fila, a decisão de cada perfil, a edição que guarda o original,
a recusa da decisão que chegou tarde e a auditoria.
"""
from __future__ import annotations

import csv
import io
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db import Sessao
from app.modelos import (
    AcaoComercial,
    Auditoria,
    Categoria,
    EstadoMensagem,
    ExecucaoOtimizador,
    ItemPlano,
    Mensagem,
    ModoExecucao,
    OrigemCategoria,
    Parceiro,
    Perfil,
    Periodo,
    PlanoCampanha,
    RedatorMensagem,
    Segmento,
    SituacaoExecucao,
    Usuario,
)

FATOS = [
    {"fato": "Parceiro", "valor": "Beta"},
    {"fato": "Faturamento no período", "valor": "R$ 7.000,00"},
]


@pytest.fixture
def gestor(criar_usuario, autenticar):
    criar_usuario(login="gestora", perfil=Perfil.GESTOR, nome="Gestora")
    return autenticar("gestora")


@pytest.fixture
def analista(criar_usuario, autenticar):
    criar_usuario(login="analista", perfil=Perfil.ANALISTA, nome="Analista")
    return autenticar("analista")


@pytest.fixture
def fila():
    """Quatro mensagens pendentes, de dois segmentos; a primeira com a ação de um plano."""
    s = Sessao()
    try:
        mercado = Categoria(nome="Mercado")
        pizzaria = Categoria(nome="Pizzaria")
        s.add_all([mercado, pizzaria])
        s.flush()
        beta = Parceiro(
            nome="Beta", categoria_id=mercado.id, origem_categoria=OrigemCategoria.MANUAL
        )
        gama = Parceiro(
            nome="Gama", categoria_id=pizzaria.id, origem_categoria=OrigemCategoria.INFERIDA
        )
        delta = Parceiro(nome="Delta")
        s.add_all([beta, gama, delta])
        s.flush()
        periodo = Periodo(data_inicio=_data("2026-09-14"), data_fim=_data("2026-09-20"))
        acao = AcaoComercial(
            nome="Cupom de reativação",
            custo_unitario=Decimal("90"),
            efeito_crescimento=Decimal("0.06"),
            efeito_retencao=Decimal("0.3"),
        )
        s.add_all([periodo, acao])
        s.flush()
        execucao = ExecucaoOtimizador(
            situacao=SituacaoExecucao.CONCLUIDA,
            modo=ModoExecucao.SERIAL,
            parametros={},
            periodo_base_id=periodo.id,
            modelo_versao="rede-1",
            semente=42,
            viavel=True,
            tempo_ms=10,
        )
        s.add(execucao)
        s.flush()
        plano = PlanoCampanha(
            execucao_id=execucao.id,
            aplicacao_inicio=_data("2026-10-05"),
            aplicacao_fim=_data("2026-10-11"),
        )
        s.add(plano)
        s.flush()
        item = ItemPlano(
            plano_id=plano.id,
            parceiro_id=beta.id,
            acao_id=acao.id,
            uplift_esperado=Decimal("100"),
            custo=Decimal("90"),
        )
        s.add(item)
        s.flush()
        mensagens = [
            _mensagem(beta.id, Segmento.EM_RISCO, "Olá, Beta!", item_plano_id=item.id),
            _mensagem(gama.id, Segmento.EM_RISCO, "Olá, Gama!"),
            _mensagem(delta.id, Segmento.TOP, "Olá, Delta!"),
            _mensagem(beta.id, Segmento.EM_RISCO, "Olá de novo, Beta!"),
        ]
        s.add_all(mensagens)
        s.commit()
        return [m.id for m in mensagens]
    finally:
        s.close()


def _data(iso):
    from datetime import date

    return date.fromisoformat(iso)


def _mensagem(parceiro_id, segmento, texto, **extra):
    return Mensagem(
        parceiro_id=parceiro_id,
        segmento=segmento,
        texto_gerado=texto,
        fatos=FATOS,
        redator=RedatorMensagem.MODELO,
        modelo="qwen2.5:7b",
        **extra,
    )


def _auditorias(acao: str) -> list[dict]:
    with Sessao() as s:
        return [
            a.detalhes
            for a in s.scalars(
                select(Auditoria).where(Auditoria.acao == acao).order_by(Auditoria.id)
            )
        ]


# ================================================================= a fila
def test_a_fila_traz_as_pendentes_da_mais_antiga_com_o_que_o_gestor_precisa_ver(fila, analista):
    corpo = analista.get("/api/mensagens").json()
    assert corpo["total"] == 4
    primeira = corpo["itens"][0]
    assert [m["id"] for m in corpo["itens"]] == fila
    assert (primeira["parceiro"], primeira["segmento"], primeira["acao"]) == (
        "Beta",
        "EM_RISCO",
        "Cupom de reativação",
    )
    assert primeira["categoria"] == "Mercado"
    # A categoria só sugerida não aparece como se fosse a do parceiro (RN05).
    assert corpo["itens"][1]["categoria"] is None
    assert all(m["estado"] == "PENDENTE" and m["decidida_por"] is None for m in corpo["itens"])


def test_a_fila_filtra_por_segmento_e_pagina(fila, analista):
    corpo = analista.get("/api/mensagens", params={"segmento": "TOP"}).json()
    assert [m["parceiro"] for m in corpo["itens"]] == ["Delta"]
    pagina = analista.get("/api/mensagens", params={"tamanho": 2, "pagina": 2}).json()
    assert (pagina["total"], [m["id"] for m in pagina["itens"]]) == (4, fila[2:])


def test_a_fila_filtra_pelo_lote(fila, analista):
    from app.modelos import LoteMensagens

    with Sessao() as s:
        lote = LoteMensagens(
            situacao=SituacaoExecucao.CONCLUIDA, publico={}, alvos=[], falhas=[]
        )
        s.add(lote)
        s.flush()
        s.get(Mensagem, fila[2]).lote_id = lote.id
        s.commit()
        lote_id = lote.id
    corpo = analista.get("/api/mensagens", params={"lote_id": lote_id}).json()
    assert [m["id"] for m in corpo["itens"]] == [fila[2]]


# ============================================================== quem decide
@pytest.mark.parametrize(
    ("metodo", "caminho", "corpo"),
    [
        ("post", "/api/mensagens/{id}/aprovacao", None),
        ("post", "/api/mensagens/{id}/edicao", {"texto": "Outro texto."}),
        ("post", "/api/mensagens/{id}/rejeicao", {"motivo": "Não gostei."}),
        ("post", "/api/mensagens/aprovacao-em-lote", "lote"),
    ],
)
def test_o_analista_ve_a_fila_mas_nao_decide_e_a_tentativa_fica_na_auditoria(
    fila, analista, metodo, caminho, corpo
):
    """RN06 e UC11-A4: negado no servidor, qualquer que seja a tela."""
    json = {"ids": fila} if corpo == "lote" else corpo
    r = getattr(analista, metodo)(caminho.format(id=fila[0]), json=json)
    assert r.status_code == 403
    with Sessao() as s:
        estados = set(s.scalars(select(Mensagem.estado)))
    assert estados == {EstadoMensagem.PENDENTE}
    negados = _auditorias("ACESSO_NEGADO")
    assert negados and negados[-1]["caminho"] == caminho.format(id=fila[0])


def test_o_gestor_ganha_a_capacidade_de_decidir_e_o_analista_nao(gestor, criar_usuario, cliente):
    telas = gestor.get("/api/sessao/atual").json()["telas"]
    assert {"aprovacao", "decidir_mensagens"} <= set(telas)
    criar_usuario(login="analista2", perfil=Perfil.ANALISTA)
    cliente.post("/api/sessao", json={"login": "analista2", "senha": "senha-de-teste-123"})
    telas = cliente.get("/api/sessao/atual").json()["telas"]
    assert "aprovacao" in telas and "decidir_mensagens" not in telas


# =============================================================== aprovar
def test_aprovar_registra_quem_quando_e_o_conteudo_final(fila, gestor):
    r = gestor.post(f"/api/mensagens/{fila[0]}/aprovacao")
    assert r.status_code == 200, r.text
    m = r.json()
    assert (m["estado"], m["decidida_por"], m["editada"]) == ("APROVADA", "Gestora", False)
    assert m["decidida_em"] is not None
    with Sessao() as s:
        gravada = s.get(Mensagem, fila[0])
        assert gravada.texto_final == gravada.texto_gerado == "Olá, Beta!"
    [registro] = _auditorias("MENSAGEM_APROVADA")
    assert registro["mensagem"] == fila[0] and registro["editada"] is False


def test_aprovada_sai_da_fila_e_a_proxima_e_a_seguinte(fila, gestor):
    gestor.post(f"/api/mensagens/{fila[0]}/aprovacao")
    corpo = gestor.get("/api/mensagens").json()
    assert corpo["total"] == 3
    assert corpo["itens"][0]["id"] == fila[1]
    aprovadas = gestor.get("/api/mensagens", params={"estado": "APROVADA"}).json()
    assert [m["id"] for m in aprovadas["itens"]] == [fila[0]]


# ================================================================= editar
def test_editar_guarda_o_original_e_a_mensagem_continua_pendente(fila, gestor):
    """UC11-A1: a edição não aprova; o texto redigido fica para a auditoria."""
    r = gestor.post(
        f"/api/mensagens/{fila[0]}/edicao",
        json={"texto": "  Olá, Beta! Faturamento de R$ 7.000,00 e 20% de desconto.  "},
    )
    assert r.status_code == 200, r.text
    m = r.json()
    assert m["estado"] == "PENDENTE"
    assert m["editada"] is True
    assert m["texto"] == "Olá, Beta! Faturamento de R$ 7.000,00 e 20% de desconto."
    assert m["texto_gerado"] == "Olá, Beta!"
    # O gestor pode escrever número; a tela mostra qual não veio dos dados.
    assert m["numeros_fora_dos_fatos"] == ["20%"]
    [registro] = _auditorias("MENSAGEM_EDITADA")
    assert registro["numeros_fora_dos_fatos"] == ["20%"]

    aprovada = gestor.post(f"/api/mensagens/{fila[0]}/aprovacao").json()
    assert aprovada["texto"] == "Olá, Beta! Faturamento de R$ 7.000,00 e 20% de desconto."
    assert aprovada["editada"] is True
    assert _auditorias("MENSAGEM_APROVADA")[0]["editada"] is True


def test_editar_de_volta_para_o_texto_redigido_desfaz_a_edicao(fila, gestor):
    gestor.post(f"/api/mensagens/{fila[0]}/edicao", json={"texto": "Outro texto."})
    m = gestor.post(f"/api/mensagens/{fila[0]}/edicao", json={"texto": "Olá, Beta!"}).json()
    assert (m["editada"], m["texto"]) == (False, "Olá, Beta!")
    with Sessao() as s:
        assert s.get(Mensagem, fila[0]).texto_final is None


@pytest.mark.parametrize("texto", ["", "   ", "x" * 2001])
def test_texto_vazio_ou_grande_demais_e_recusado(fila, gestor, texto):
    r = gestor.post(f"/api/mensagens/{fila[0]}/edicao", json={"texto": texto})
    assert r.status_code == 422


# ================================================================ rejeitar
def test_rejeitar_com_motivo(fila, gestor):
    m = gestor.post(
        f"/api/mensagens/{fila[1]}/rejeicao", json={"motivo": "  Tom errado para o parceiro. "}
    ).json()
    assert (m["estado"], m["motivo_rejeicao"], m["decidida_por"]) == (
        "REJEITADA",
        "Tom errado para o parceiro.",
        "Gestora",
    )
    [registro] = _auditorias("MENSAGEM_REJEITADA")
    assert registro == {
        "mensagem": fila[1],
        "parceiro": m["parceiro_id"],
        "motivo": m["motivo_rejeicao"],
    }


def test_rejeitar_sem_motivo_e_permitido_e_motivo_longo_nao(fila, gestor):
    """O motivo é opcional (UC11-A2: "pode registrar")."""
    sem_motivo = gestor.post(f"/api/mensagens/{fila[1]}/rejeicao", json={}).json()
    assert sem_motivo["motivo_rejeicao"] is None
    r = gestor.post(f"/api/mensagens/{fila[2]}/rejeicao", json={"motivo": "x" * 241})
    assert r.status_code == 422


# ============================================================ a decisão tardia
@pytest.mark.parametrize(
    ("caminho", "corpo"),
    [
        ("/api/mensagens/{id}/aprovacao", None),
        ("/api/mensagens/{id}/rejeicao", {"motivo": "tarde"}),
        ("/api/mensagens/{id}/edicao", {"texto": "tarde"}),
    ],
)
def test_mensagem_ja_decidida_nao_e_sobrescrita_e_diz_a_decisao(
    fila, gestor, criar_usuario, autenticar, caminho, corpo
):
    """UC11-E1: quem chegou depois recebe a decisão registrada, e nada muda."""
    criar_usuario(login="outra", perfil=Perfil.GESTOR, nome="Outra Gestora")
    with Sessao() as s:
        outra = s.scalar(select(Usuario.id).where(Usuario.login == "outra"))
    gestor.post(f"/api/mensagens/{fila[0]}/rejeicao", json={"motivo": "primeiro"})

    autenticar("outra")
    r = gestor.post(caminho.format(id=fila[0]), json=corpo)
    assert r.status_code == 409
    detalhe = r.json()["detail"]
    assert detalhe["erro"] == "Esta mensagem já foi decidida."
    assert (detalhe["estado"], detalhe["decidida_por"]) == ("REJEITADA", "Gestora")
    assert "rejeitada por Gestora" in detalhe["ajuda"]
    with Sessao() as s:
        m = s.get(Mensagem, fila[0])
        assert (m.estado, m.motivo_rejeicao, m.texto_final) == (
            EstadoMensagem.REJEITADA,
            "primeiro",
            None,
        )
        assert m.decidida_por_id != outra


def test_mensagem_que_nao_existe(gestor):
    r = gestor.post("/api/mensagens/999/aprovacao")
    assert r.status_code == 404
    assert r.json()["detail"]["erro"] == "Mensagem não encontrada."


# ============================================================ em lote
def test_aprovacao_em_lote_registra_cada_decisao_e_diz_o_que_ficou(fila, gestor):
    """UC11-A3: ação humana explícita, e cada mensagem com a própria decisão."""
    gestor.post(f"/api/mensagens/{fila[1]}/rejeicao", json={"motivo": "não"})
    r = gestor.post(
        "/api/mensagens/aprovacao-em-lote", json={"ids": [fila[0], fila[1], fila[3], fila[0], 999]}
    )
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert corpo["aprovadas"] == [fila[0], fila[3]]
    assert [(d["mensagem_id"], d["estado"]) for d in corpo["ja_decididas"]] == [
        (fila[1], "REJEITADA")
    ]
    assert corpo["nao_encontradas"] == [999]
    registros = _auditorias("MENSAGEM_APROVADA")
    assert [(r["mensagem"], r["em_lote"]) for r in registros] == [(fila[0], True), (fila[3], True)]
    with Sessao() as s:
        for mensagem_id in (fila[0], fila[3]):
            m = s.get(Mensagem, mensagem_id)
            assert m.decidida_por_id is not None and m.decidida_em is not None
            assert m.texto_final == m.texto_gerado


@pytest.mark.parametrize("ids", [[], list(range(1, 202))])
def test_lote_vazio_ou_grande_demais(gestor, ids):
    assert gestor.post("/api/mensagens/aprovacao-em-lote", json={"ids": ids}).status_code == 422


# ========================================================= o banco também
def test_o_banco_recusa_mensagem_decidida_sem_autor(fila):
    """RN06 no banco: mesmo um código que pulasse a rota não aprova sozinho."""
    with Sessao() as s:
        s.get(Mensagem, fila[0]).estado = EstadoMensagem.APROVADA
        with pytest.raises(IntegrityError, match="ck_mensagem_decisao_tem_autor"):
            s.commit()


# ================================================== o histórico (RF40, H64)
def test_o_historico_traz_quem_decidiu_o_final_o_redigido_e_o_motivo(fila, gestor):
    gestor.post(f"/api/mensagens/{fila[0]}/edicao", json={"texto": "Olá, Beta! Texto do gestor."})
    gestor.post(f"/api/mensagens/{fila[0]}/aprovacao")
    gestor.post(f"/api/mensagens/{fila[1]}/rejeicao", json={"motivo": "Tom errado"})

    [aprovada] = gestor.get("/api/mensagens", params={"estado": "APROVADA"}).json()["itens"]
    assert (aprovada["texto"], aprovada["texto_gerado"], aprovada["editada"]) == (
        "Olá, Beta! Texto do gestor.",
        "Olá, Beta!",
        True,
    )
    assert aprovada["decidida_por"] == "Gestora" and aprovada["decidida_em"]
    [rejeitada] = gestor.get("/api/mensagens", params={"estado": "REJEITADA"}).json()["itens"]
    assert (rejeitada["motivo_rejeicao"], rejeitada["decidida_por"]) == ("Tom errado", "Gestora")


def test_o_historico_filtra_pelo_dia_da_decisao(fila, gestor):
    for mensagem_id in fila[:2]:
        gestor.post(f"/api/mensagens/{mensagem_id}/aprovacao")
    with Sessao() as s:
        antiga = s.get(Mensagem, fila[0])
        antiga.decidida_em = antiga.decidida_em - timedelta(days=10)
        s.commit()
        dia_antigo = antiga.decidida_em.astimezone().date()
    hoje = date.today()

    def ids(**filtro):
        corpo = gestor.get("/api/mensagens", params={"estado": "APROVADA", **filtro}).json()
        return [m["id"] for m in corpo["itens"]]

    assert ids() == [fila[1], fila[0]]  # a decisão mais recente primeiro
    assert ids(de=hoje.isoformat()) == [fila[1]]
    assert ids(ate=dia_antigo.isoformat()) == [fila[0]]
    assert ids(de=dia_antigo.isoformat(), ate=dia_antigo.isoformat()) == [fila[0]]


def _csv(cliente, **filtro):
    r = cliente.get("/api/mensagens/exportacao.csv", params=filtro)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/csv")
    assert r.text.startswith("﻿")
    return list(csv.reader(io.StringIO(r.text.lstrip("﻿")), delimiter=";"))


def test_a_exportacao_traz_so_as_aprovadas_prontas_para_envio(fila, gestor):
    with Sessao() as s:
        beta = s.get(Mensagem, fila[0]).parceiro_id
        s.get(Parceiro, beta).contato = "(81) 99999-0000"
        s.commit()
    gestor.post(f"/api/mensagens/{fila[0]}/edicao", json={"texto": "Olá, Beta! Até breve."})
    gestor.post(f"/api/mensagens/{fila[0]}/aprovacao")
    gestor.post(f"/api/mensagens/{fila[1]}/rejeicao", json={})

    cabecalho, *linhas = _csv(gestor)
    assert cabecalho == [
        "Parceiro",
        "Contato",
        "Segmento",
        "Categoria",
        "Acao",
        "Mensagem",
        "Editada",
        "Aprovada por",
        "Aprovada em",
    ]
    [linha] = linhas
    assert linha[:8] == [
        "Beta",
        "(81) 99999-0000",
        "Em risco",
        "Mercado",
        "Cupom de reativação",
        "Olá, Beta! Até breve.",
        "Sim",
        "Gestora",
    ]
    assert len(linha[8]) == len("27/09/2026 14:05")


def test_a_exportacao_neutraliza_formula_no_texto_da_mensagem(fila, gestor):
    """O texto vem do modelo ou do gestor, e vai para a planilha: passa pela mesma
    proteção dos parceiros (H70)."""
    gestor.post(f"/api/mensagens/{fila[2]}/edicao", json={"texto": '=HYPERLINK("http://x","clique")'})
    gestor.post(f"/api/mensagens/{fila[2]}/aprovacao")
    [_, linha] = _csv(gestor)
    assert linha[5] == "'=HYPERLINK(\"http://x\",\"clique\")"


def test_a_exportacao_segue_os_filtros_do_historico(fila, gestor):
    for mensagem_id in fila:
        gestor.post(f"/api/mensagens/{mensagem_id}/aprovacao")
    assert [linha[0] for linha in _csv(gestor, segmento="TOP")[1:]] == ["Delta"]
    amanha = (date.today() + timedelta(days=1)).isoformat()
    assert _csv(gestor, de=amanha)[1:] == []
