"""A geração de mensagens — UC10, RF36, RF37, história H60 (ADR-013).

O modelo de linguagem é sempre de mentira aqui (`RedatorFalso`): o que se testa
é o que a API faz com ele — os fatos que entrega, a guarda que confere o texto,
o modelo fixo quando ele falha ou está fora do ar, o público, o lote em segundo
plano, a falha de um parceiro e a recuperação. O modelo de verdade é testado em
`test_redator.py`.

A rede é a da campanha (`tests/rede.py`): parceiros, cinco semanas de
métricas e o segmento na semana mais recente.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app import redator, servico_benchmark, servico_mensagens
from app.db import Sessao
from app.guarda_numerica import numeros_sem_origem
from app.modelos import (
    Auditoria,
    EstadoMensagem,
    ExecucaoBenchmark,
    ExecucaoOtimizador,
    LoteMensagens,
    Mensagem,
    ModoExecucao,
    OrigemCategoria,
    Perfil,
    Periodo,
    RedatorMensagem,
    Segmento,
    SituacaoExecucao,
)
from app.redator import FORA_DO_AR, ILEGIVEL, Estado, FalhaDoRedator
from app.servico_mensagens import (
    ACAO,
    FATURAMENTO,
    PARCEIRO,
    PEDIDOS,
    PERIODO,
    PERIODO_DA_ACAO,
    TICKET,
    VARIACAO,
    fatos_do_parceiro,
    modelo_fixo,
    redigir,
    termos_internos,
)
from tests.rede import parceiro as _parceiro
from tests.test_campanha import _calcular

MODELO = "modelo-falso:1b"


class RedatorFalso:
    """Um redator que responde o que o teste mandar, e guarda o que recebeu."""

    def __init__(self, resposta=None, *, disponivel=True, motivo=None, falha=None):
        self.modelo = MODELO
        self.resposta = resposta or (lambda parceiro: f"Olá, {parceiro}! Obrigado pela parceria.")
        self.disponivel = disponivel
        self.motivo = motivo
        self.falha = falha
        self.pedidos: list[tuple[str, str]] = []

    def estado(self):
        return Estado(self.disponivel, MODELO, self.motivo)

    def redigir(self, sistema, pedido):
        self.pedidos.append((sistema, pedido))
        if self.falha:
            raise FalhaDoRedator(self.falha)
        parceiro = next(
            linha.removeprefix(f"- {PARCEIRO}: ")
            for linha in pedido.splitlines()
            if linha.startswith(f"- {PARCEIRO}: ")
        )
        return self.resposta(parceiro)


@pytest.fixture
def modelo(monkeypatch):
    """Troca o modelo de linguagem da aplicação pelo que o teste montar."""

    def trocar(falso: RedatorFalso) -> RedatorFalso:
        monkeypatch.setattr(redator, "atual", lambda: falso)
        return falso

    return trocar


@pytest.fixture
def analista(criar_usuario, autenticar):
    criar_usuario(login="analista", perfil=Perfil.ANALISTA, nome="Analista")
    return autenticar("analista")


def _rede():
    """Seis parceiros, com segmento, categoria confirmada ou não, e um desativado."""
    return [
        _parceiro("Alfa", "9000", previsto="9500", categoria="Pizzaria", segmento=Segmento.TOP),
        _parceiro(
            "Beta", "7000", previsto="6800", risco=0.6, categoria="Mercado",
            segmento=Segmento.EM_RISCO,
        ),
        _parceiro(
            "Gama", "5000", previsto="5200", categoria="Mercado",
            origem=OrigemCategoria.INFERIDA, segmento=Segmento.EM_RISCO,
        ),
        _parceiro("Delta", "3000", previsto="2500", risco=0.8, segmento=Segmento.EM_RISCO),
        _parceiro(
            "Epsilon", "2000", previsto="2100", categoria="Mercado", segmento=Segmento.ESTAVEL,
        ),
        _parceiro(
            "Zeta", "1000", previsto="1200", segmento=Segmento.EM_RISCO, ativo=False,
        ),
    ]


def _previa(cliente, **publico):
    return cliente.post("/api/mensagens/publico", json=publico)


def _gerar(cliente, **publico):
    r = cliente.post("/api/mensagens/lotes", json=publico)
    assert r.status_code == 202, r.text
    # O TestClient só devolve depois de a tarefa em segundo plano terminar.
    return cliente.get(f"/api/mensagens/lotes/{r.json()['id']}").json()


# ================================================================ os fatos, puros
def test_os_fatos_saem_formatados_como_a_tela_os_mostra():
    fatos = fatos_do_parceiro(
        "Mercearia Boa Vista",
        periodo=(date(2026, 9, 14), date(2026, 9, 20)),
        faturamento=Decimal("12345.67"),
        pedidos=1234,
        anterior=Decimal("11000"),
        acao="Cupom de reativação",
        periodo_da_acao=(date(2026, 10, 1), date(2026, 10, 31)),
    )
    assert fatos == [
        {"fato": PARCEIRO, "valor": "Mercearia Boa Vista"},
        {"fato": PERIODO, "valor": "14/09/2026 a 20/09/2026"},
        {"fato": FATURAMENTO, "valor": "R$ 12.345,67"},
        {"fato": PEDIDOS, "valor": "1.234"},
        {"fato": TICKET, "valor": "R$ 10,00"},
        {"fato": VARIACAO, "valor": "+12,23%"},
        {"fato": ACAO, "valor": "Cupom de reativação"},
        {"fato": PERIODO_DA_ACAO, "valor": "01/10/2026 a 31/10/2026"},
    ]


def test_sem_desempenho_no_periodo_os_fatos_sao_so_o_nome():
    fatos = fatos_do_parceiro(
        "Nova Loja", periodo=None, faturamento=None, pedidos=None, anterior=None,
        acao=None, periodo_da_acao=None,
    )
    assert fatos == [{"fato": PARCEIRO, "valor": "Nova Loja"}]


def test_sem_periodo_anterior_nao_ha_variacao():
    fatos = fatos_do_parceiro(
        "Nova Loja", periodo=(date(2026, 9, 14), date(2026, 9, 20)),
        faturamento=Decimal("500"), pedidos=0, anterior=None, acao=None, periodo_da_acao=None,
    )
    assert [f["fato"] for f in fatos] == [PARCEIRO, PERIODO, FATURAMENTO, PEDIDOS]


# ============================================================ o modelo fixo, puro
FATOS_COMPLETOS = fatos_do_parceiro(
    "Mercearia Boa Vista",
    periodo=(date(2026, 9, 14), date(2026, 9, 20)),
    faturamento=Decimal("12345.67"),
    pedidos=1,
    anterior=Decimal("13000"),
    acao="Cupom de reativação",
    periodo_da_acao=(date(2026, 10, 1), date(2026, 10, 31)),
)


@pytest.mark.parametrize("segmento", [*Segmento, None])
@pytest.mark.parametrize(
    "fatos", [FATOS_COMPLETOS, FATOS_COMPLETOS[:1]], ids=["completos", "so-o-nome"]
)
def test_o_modelo_fixo_so_tem_os_numeros_dos_fatos_e_nada_da_rede(segmento, fatos):
    texto = modelo_fixo(segmento, fatos)
    assert texto.startswith("Olá, Mercearia Boa Vista!")
    assert numeros_sem_origem(texto, fatos) == []
    assert termos_internos(texto) == []


def test_o_modelo_fixo_diz_o_desempenho_e_a_acao():
    texto = modelo_fixo(Segmento.EM_RISCO, FATOS_COMPLETOS)
    assert "1 pedido e R$ 12.345,67" in texto
    assert "Cupom de reativação, de 01/10/2026 a 31/10/2026." in texto


# ================================================================ a redação, pura
def test_texto_do_modelo_com_os_fatos_passa():
    r = redigir(RedatorFalso(), None, Segmento.TOP, FATOS_COMPLETOS)
    assert r.redator == RedatorMensagem.MODELO
    assert r.modelo == MODELO
    assert r.texto == "Olá, Mercearia Boa Vista! Obrigado pela parceria."


def test_numero_inventado_troca_pelo_modelo_fixo_e_diz_qual():
    falso = RedatorFalso(lambda p: f"{p}, suas vendas caíram 13% em julho, o dobro de antes.")
    r = redigir(falso, None, Segmento.EM_RISCO, FATOS_COMPLETOS)
    assert r.redator == RedatorMensagem.MODELO_FIXO
    assert r.texto == modelo_fixo(Segmento.EM_RISCO, FATOS_COMPLETOS)
    assert "(13%, julho, dobro)" in r.motivo


@pytest.mark.parametrize(
    "texto", ["Vocês estão em risco.", "No nosso ranking, vocês...", "Seu SEGMENTO mudou."]
)
def test_o_que_e_da_rede_troca_pelo_modelo_fixo(texto):
    r = redigir(RedatorFalso(lambda _p: texto), None, Segmento.EM_RISCO, FATOS_COMPLETOS)
    assert r.redator == RedatorMensagem.MODELO_FIXO
    assert "classificação interna" in r.motivo


def test_termos_internos_sem_acento_e_por_palavra_inteira():
    achados = termos_internos("Vocês estão EM RISCO e na classificacao")
    assert achados == ["em risco", "classificação"]
    assert termos_internos("Sem riscos para vocês, segmentos e rankings à parte") == []


@pytest.mark.parametrize(
    ("do_modelo", "na_mensagem"),
    [
        (
            "Olá, Casa Real,\n\nVocês fazem parte da rede.",
            "Olá, Casa Real, vocês fazem parte da rede.",
        ),
        ("Olá, Casa Real! Obrigado.\n\nAtenciosamente,", "Olá, Casa Real! Obrigado."),
        ("Olá!  Seguimos   juntos. Atenciosamente.", "Olá! Seguimos juntos."),
        ("Olá!\nObrigado.", "Olá! Obrigado."),
    ],
)
def test_o_texto_do_modelo_vira_um_paragrafo_sem_despedida(do_modelo, na_mensagem):
    r = redigir(RedatorFalso(lambda _p: do_modelo), None, None, [{"fato": PARCEIRO, "valor": "x"}])
    assert r.texto == na_mensagem


def test_modelo_fora_do_ar_no_meio_avisa_que_caiu():
    r = redigir(RedatorFalso(falha=FORA_DO_AR), None, None, FATOS_COMPLETOS)
    assert (r.redator, r.motivo, r.modelo_caiu) == (RedatorMensagem.MODELO_FIXO, FORA_DO_AR, True)


def test_resposta_ilegivel_nao_derruba_o_modelo_para_o_resto():
    r = redigir(RedatorFalso(falha=ILEGIVEL), None, None, FATOS_COMPLETOS)
    assert (r.redator, r.modelo_caiu) == (RedatorMensagem.MODELO_FIXO, False)


def test_sem_modelo_o_motivo_e_o_do_estado():
    r = redigir(None, "O assistente não está configurado nesta instalação.", None, FATOS_COMPLETOS)
    assert r.redator == RedatorMensagem.MODELO_FIXO
    assert r.motivo == "O assistente não está configurado nesta instalação."


# ================================================================== o público
def test_por_segmento_so_os_ativos_e_o_desativado_contado(base, analista):
    base(_rede())
    r = _previa(analista, tipo="FILTRO", segmento="EM_RISCO")
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert corpo["descricao"] == "Em risco"
    assert [p["nome"] for p in corpo["parceiros"]] == ["Beta", "Delta", "Gama"]
    assert corpo["excluidos"] == {"desativado": 1}
    assert corpo["pode_gerar"] is True


def test_por_categoria_so_a_confirmada_rn05(base, analista):
    base(_rede())
    categorias = analista.get("/api/categorias").json()
    mercado = next(c["id"] for c in categorias if c["nome"] == "Mercado")
    corpo = _previa(analista, tipo="FILTRO", categoria_id=mercado).json()
    assert corpo["descricao"] == "Mercado"
    assert [p["nome"] for p in corpo["parceiros"]] == ["Beta", "Epsilon"]
    assert corpo["excluidos"] == {"categoria não confirmada": 1}
    assert all(p["categoria"] == "Mercado" for p in corpo["parceiros"])

    juntos = _previa(analista, tipo="FILTRO", segmento="EM_RISCO", categoria_id=mercado).json()
    assert juntos["descricao"] == "Em risco, em Mercado"
    assert [p["nome"] for p in juntos["parceiros"]] == ["Beta"]


def test_categoria_que_nao_existe(base, analista):
    base(_rede())
    r = _previa(analista, tipo="FILTRO", categoria_id=999)
    assert r.status_code == 404
    assert r.json()["detail"]["erro"] == "Categoria não encontrada."


def test_por_plano_os_parceiros_do_plano_com_a_acao(base, criar_usuario, autenticar):
    base(_rede())
    criar_usuario(login="gestora", perfil=Perfil.GESTOR)
    gestora = autenticar("gestora")
    execucao = _calcular(gestora)
    assert execucao["viavel"], execucao
    corpo = _previa(gestora, tipo="PLANO", execucao_id=execucao["id"]).json()
    no_plano = {i["parceiro"]: i["acao"] for i in execucao["itens"]}
    assert {p["nome"]: p["acao"] for p in corpo["parceiros"]} == no_plano
    assert corpo["descricao"] == "Plano de campanha de 06/07/2026 a 12/07/2026"


def test_plano_que_nao_existe_ou_sem_plano(base, analista):
    base(_rede())
    assert _previa(analista, tipo="PLANO", execucao_id=999).status_code == 404
    with Sessao() as s:
        falha = ExecucaoOtimizador(
            situacao=SituacaoExecucao.FALHOU, modo=ModoExecucao.SERIAL, parametros={},
            periodo_base_id=base_periodo(s), modelo_versao="rede-1", semente=42, motivo="x",
        )
        s.add(falha)
        s.commit()
        falha_id = falha.id
    r = _previa(analista, tipo="PLANO", execucao_id=falha_id)
    assert r.status_code == 422
    assert r.json()["detail"]["erro"] == "Esta execução não tem plano."


def base_periodo(s) -> int:
    return s.scalar(select(Periodo.id).order_by(Periodo.data_inicio.desc()))


def test_selecao_manual_sem_repetir_e_com_o_que_nao_existe(base, analista):
    rede = base(_rede())
    p = rede.parceiros
    corpo = _previa(
        analista, tipo="SELECAO", parceiros=[p["Alfa"], p["Alfa"], p["Zeta"], 9999]
    ).json()
    assert [x["nome"] for x in corpo["parceiros"]] == ["Alfa"]
    assert corpo["excluidos"] == {"desativado": 1, "não encontrado": 1}
    assert corpo["descricao"] == "Seleção de 1 parceiro"


@pytest.mark.parametrize(
    ("publico", "mensagem"),
    [
        ({"tipo": "FILTRO"}, "Escolha um segmento, uma categoria, ou os dois."),
        ({"tipo": "PLANO"}, "Escolha o plano de campanha."),
        ({"tipo": "PLANO", "execucao_id": 1, "segmento": "TOP"}, "sem outro critério"),
        ({"tipo": "SELECAO", "parceiros": []}, "Escolha ao menos um parceiro."),
        ({"tipo": "SELECAO", "parceiros": [1], "categoria_id": 1}, "não leva segmento"),
    ],
)
def test_o_criterio_precisa_ser_o_do_tipo(analista, publico, mensagem):
    r = analista.post("/api/mensagens/publico", json=publico)
    assert r.status_code == 422
    assert mensagem in r.text


# ================================================================== a geração
def test_sem_o_modelo_tudo_sai_do_modelo_fixo_e_pendente(base, analista, modelo):
    base(_rede())
    modelo(RedatorFalso(disponivel=False, motivo="O serviço do modelo de linguagem não respondeu."))
    lote = _gerar(analista, tipo="FILTRO", segmento="EM_RISCO")

    assert lote["situacao"] == "CONCLUIDA"
    assert (lote["total"], lote["geradas"], lote["pelo_modelo"]) == (3, 3, 0)
    assert lote["descricao"] == "Em risco"
    assert lote["modelo"] is None
    assert lote["falhas"] == []
    for m in lote["mensagens"]:
        assert m["estado"] == "PENDENTE"
        assert m["redator"] == "MODELO_FIXO"
        assert m["motivo_redator"] == "O serviço do modelo de linguagem não respondeu."
        assert m["segmento"] == "EM_RISCO"
        assert m["texto"].startswith(f"Olá, {m['parceiro']}!")
        assert numeros_sem_origem(m["texto"], m["fatos"]) == []


def test_com_o_modelo_o_texto_e_dele_e_os_fatos_vao_no_pedido(base, analista, modelo):
    rede = base(_rede())
    falso = modelo(RedatorFalso())
    lote = _gerar(analista, tipo="SELECAO", parceiros=[rede.parceiros["Beta"]])

    assert (lote["geradas"], lote["pelo_modelo"], lote["modelo"]) == (1, 1, MODELO)
    [m] = lote["mensagens"]
    assert m["redator"] == "MODELO"
    assert m["modelo"] == MODELO
    assert m["texto"] == "Olá, Beta! Obrigado pela parceria."

    [(sistema, pedido)] = falso.pedidos
    assert "não invente números" in sistema
    assert "- Faturamento no período: R$ 7.000,00" in pedido
    assert "- Pedidos no período: 10" in pedido
    # O segmento escolhe o tom, e não entra no texto que o modelo lê (RF26, ADR-013).
    assert "risco" not in pedido.lower()
    assert "EM_RISCO" not in pedido


def test_os_fatos_nao_levam_nada_da_rede(base, analista, modelo):
    base(_rede())
    modelo(RedatorFalso(disponivel=False, motivo="fora"))
    lote = _gerar(analista, tipo="FILTRO", segmento="EM_RISCO")
    permitidos = {PARCEIRO, PERIODO, FATURAMENTO, PEDIDOS, TICKET, VARIACAO, ACAO, PERIODO_DA_ACAO}
    for m in lote["mensagens"]:
        assert {f["fato"] for f in m["fatos"]} <= permitidos


def test_o_plano_leva_a_acao_e_o_periodo_dela_para_a_mensagem(
    base, criar_usuario, autenticar, modelo
):
    base(_rede())
    criar_usuario(login="gestora", perfil=Perfil.GESTOR)
    gestora = autenticar("gestora")
    execucao = _calcular(gestora)
    modelo(RedatorFalso(disponivel=False, motivo="fora"))
    lote = _gerar(gestora, tipo="PLANO", execucao_id=execucao["id"])
    acoes = {i["parceiro"]: i["acao"] for i in execucao["itens"]}
    assert lote["geradas"] == len(acoes)
    for m in lote["mensagens"]:
        assert m["acao"] == acoes[m["parceiro"]]
        fatos = {f["fato"]: f["valor"] for f in m["fatos"]}
        assert fatos[ACAO] == acoes[m["parceiro"]]
        assert fatos[PERIODO_DA_ACAO] == "06/07/2026 a 12/07/2026"
        assert f"{acoes[m['parceiro']]}, de 06/07/2026 a 12/07/2026." in m["texto"]


def test_texto_com_numero_inventado_vira_modelo_fixo_na_fila(base, analista, modelo):
    rede = base(_rede())
    modelo(RedatorFalso(lambda p: f"{p}, vocês cresceram 13%!"))
    lote = _gerar(analista, tipo="SELECAO", parceiros=[rede.parceiros["Alfa"]])
    [m] = lote["mensagens"]
    assert m["redator"] == "MODELO_FIXO"
    assert "(13%)" in m["motivo_redator"]
    assert lote["pelo_modelo"] == 0


def test_modelo_que_cai_no_meio_nao_e_chamado_de_novo(base, analista, modelo):
    base(_rede())
    falso = modelo(RedatorFalso(falha=FORA_DO_AR))
    lote = _gerar(analista, tipo="FILTRO", segmento="EM_RISCO")
    assert lote["geradas"] == 3
    assert len(falso.pedidos) == 1
    assert {m["motivo_redator"] for m in lote["mensagens"]} == {FORA_DO_AR}


def test_a_falha_de_um_parceiro_nao_para_o_lote_e_se_refaz(base, analista, modelo, monkeypatch):
    rede = base(_rede())
    modelo(RedatorFalso(disponivel=False, motivo="fora"))
    gravar = servico_mensagens._gravar

    def falhar_com_o_delta(lote_id, contexto, redacao):
        if contexto.nome == "Delta":
            raise RuntimeError("disco cheio")
        gravar(lote_id, contexto, redacao)

    monkeypatch.setattr(servico_mensagens, "_gravar", falhar_com_o_delta)
    lote = _gerar(analista, tipo="FILTRO", segmento="EM_RISCO")
    assert lote["situacao"] == "CONCLUIDA"
    assert lote["geradas"] == 2
    [falha] = lote["falhas"]
    assert falha["parceiro_id"] == rede.parceiros["Delta"]
    assert falha["parceiro"] == "Delta"
    assert "registro" in falha["motivo"]
    assert "disco cheio" not in falha["motivo"]  # o detalhe fica no log (RNF18)

    monkeypatch.setattr(servico_mensagens, "_gravar", gravar)
    r = analista.post(f"/api/mensagens/lotes/{lote['id']}/refazer")
    assert r.status_code == 202, r.text
    refeito = analista.get(f"/api/mensagens/lotes/{lote['id']}").json()
    assert (refeito["situacao"], refeito["geradas"], refeito["falhas"]) == ("CONCLUIDA", 3, [])
    # As que já existiam não se repetem.
    assert len({m["parceiro_id"] for m in refeito["mensagens"]}) == 3


def test_refazer_o_que_nao_falhou_ou_nao_existe(base, analista, modelo):
    base(_rede())
    modelo(RedatorFalso(disponivel=False, motivo="fora"))
    lote = _gerar(analista, tipo="FILTRO", segmento="EM_RISCO")
    r = analista.post(f"/api/mensagens/lotes/{lote['id']}/refazer")
    assert r.status_code == 422
    assert r.json()["detail"]["erro"] == "Todas as mensagens deste lote já foram geradas."
    assert analista.post("/api/mensagens/lotes/999/refazer").status_code == 404
    assert analista.get("/api/mensagens/lotes/999").status_code == 404


def test_publico_vazio_nao_cria_nada(base, analista):
    base(_rede())
    r = analista.post("/api/mensagens/lotes", json={"tipo": "FILTRO", "segmento": "RECEM_CHEGADO"})
    assert r.status_code == 422
    assert r.json()["detail"]["erro"] == "Nenhum parceiro ativo neste público: nada a gerar."
    with Sessao() as s:
        assert s.scalar(select(LoteMensagens.id)) is None
    previa = _previa(analista, tipo="FILTRO", segmento="RECEM_CHEGADO").json()
    assert (previa["total"], previa["pode_gerar"]) == (0, False)


def test_publico_grande_demais_e_recusado(base, analista, monkeypatch):
    base(_rede())
    monkeypatch.setattr(servico_mensagens, "MAXIMO_POR_LOTE", 2)
    r = analista.post("/api/mensagens/lotes", json={"tipo": "FILTRO", "segmento": "EM_RISCO"})
    assert r.status_code == 422
    assert "São 3 parceiros, e um lote gera até 2" in r.json()["detail"]["erro"]


def test_um_lote_por_vez(base, analista, criar_usuario):
    rede = base(_rede())
    with Sessao() as s:
        rodando = LoteMensagens(
            publico={"tipo": "SELECAO", "parceiros": [1], "descricao": "x"},
            alvos=[{"parceiro_id": rede.parceiros["Alfa"], "item_plano_id": None}],
            falhas=[],
        )
        s.add(rodando)
        s.commit()
        rodando_id = rodando.id
    r = analista.post("/api/mensagens/lotes", json={"tipo": "FILTRO", "segmento": "EM_RISCO"})
    assert r.status_code == 409
    assert r.json()["detail"]["lote_id"] == rodando_id
    estado = analista.get("/api/mensagens/geracao").json()
    assert estado["em_andamento"]["id"] == rodando_id


def test_a_subida_da_api_recupera_o_lote_interrompido(base, analista, modelo):
    rede = base(_rede())
    p = rede.parceiros
    with Sessao() as s:
        lote = LoteMensagens(
            publico={"tipo": "SELECAO", "parceiros": [p["Alfa"], p["Beta"]], "descricao": "x"},
            alvos=[
                {"parceiro_id": p["Alfa"], "item_plano_id": None},
                {"parceiro_id": p["Beta"], "item_plano_id": None},
            ],
            falhas=[],
        )
        s.add(lote)
        s.flush()
        s.add(
            Mensagem(
                parceiro_id=p["Alfa"], lote_id=lote.id, texto_gerado="Olá, Alfa!", fatos=[],
                redator=RedatorMensagem.MODELO_FIXO, motivo_redator="fora",
            )
        )
        s.commit()
        lote_id = lote.id
    with Sessao() as s:
        assert servico_mensagens.recuperar_interrompidos(s) == 1
        s.commit()

    recuperado = analista.get(f"/api/mensagens/lotes/{lote_id}").json()
    assert recuperado["situacao"] == "FALHOU"
    assert recuperado["motivo"] == servico_mensagens.INTERROMPIDO
    assert [f["parceiro"] for f in recuperado["falhas"]] == ["Beta"]
    assert recuperado["geradas"] == 1

    modelo(RedatorFalso(disponivel=False, motivo="fora"))
    assert analista.post(f"/api/mensagens/lotes/{lote_id}/refazer").status_code == 202
    refeito = analista.get(f"/api/mensagens/lotes/{lote_id}").json()
    assert (refeito["situacao"], refeito["geradas"], refeito["falhas"]) == ("CONCLUIDA", 2, [])


def test_a_geracao_fica_na_auditoria_com_quem_pediu(base, analista, modelo):
    base(_rede())
    modelo(RedatorFalso())
    lote = _gerar(analista, tipo="FILTRO", segmento="EM_RISCO")
    with Sessao() as s:
        registro = s.scalar(select(Auditoria).where(Auditoria.acao == "MENSAGENS_GERADAS"))
    assert registro.detalhes == {
        "lote": lote["id"],
        "publico": "Em risco",
        "total": 3,
        "geradas": 3,
        "pelo_modelo": 3,
        "falhas": 0,
        "modelo": MODELO,
        "tentativa_de_novo": False,
    }


def test_a_tela_abre_com_o_estado_do_assistente(base, analista, modelo):
    base(_rede())
    modelo(RedatorFalso(disponivel=False, motivo="O modelo x ainda não foi baixado."))
    estado = analista.get("/api/mensagens/geracao").json()
    assert estado["assistente"] == {
        "disponivel": False,
        "modelo": MODELO,
        "motivo": "O modelo x ainda não foi baixado.",
    }
    assert (estado["em_andamento"], estado["ultimo"]) == (None, None)
    assert estado["maximo"] == servico_mensagens.MAXIMO_POR_LOTE

    lote = _gerar(analista, tipo="FILTRO", segmento="EM_RISCO")
    assert analista.get("/api/mensagens/geracao").json()["ultimo"]["id"] == lote["id"]


def test_sem_configuracao_a_tela_diz_que_o_assistente_nao_esta_configurado(analista):
    estado = analista.get("/api/mensagens/geracao").json()
    assert estado["assistente"]["disponivel"] is False
    assert estado["assistente"]["motivo"] == redator.SEM_ENDERECO


def test_as_mensagens_nascem_pendentes_no_banco(base, analista, modelo):
    base(_rede())
    modelo(RedatorFalso())
    _gerar(analista, tipo="FILTRO", segmento="EM_RISCO")
    with Sessao() as s:
        estados = set(s.scalars(select(Mensagem.estado)))
        autores = set(s.scalars(select(Mensagem.decidida_por_id)))
    assert estados == {EstadoMensagem.PENDENTE}
    assert autores == {None}


# =========================================================== e o benchmark
def test_o_benchmark_durante_a_redacao_pelo_modelo_sai_disputado():
    # Sem a rede: o treino dela, sem data de fim, contaria como cálculo rodando junto.
    with Sessao() as s:
        execucao = ExecucaoBenchmark(parceiros=100, acoes=1, repeticoes=1, semente=42)
        s.add(execucao)
        s.flush()
        # Concluídos agora há pouco, sem data de fim: contam como rodando junto.
        concluido = SituacaoExecucao.CONCLUIDA
        s.add(LoteMensagens(situacao=concluido, publico={}, alvos=[], falhas=[], modelo=None))
        s.flush()
        assert servico_benchmark._disputada(s, execucao) is False
        s.add(LoteMensagens(situacao=concluido, publico={}, alvos=[], falhas=[], modelo=MODELO))
        s.flush()
        assert servico_benchmark._disputada(s, execucao) is True
        s.rollback()
