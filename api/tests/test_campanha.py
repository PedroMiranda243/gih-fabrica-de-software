"""A campanha pela API — UC08, RF29 a RF32, RN07, RN10, RN11, histórias H48 a H52 e H55.

O otimizador em si é testado em `nucleo/tests`. Aqui se testa o que é da API:
o ganho da RN10 em centavos, quem entra e quem fica fora (RN11), as cotas em
contagem, a categoria confirmada, a cauda longa pelo ranking (e não pelo
segmento), a recusa com o que falta, uma execução por vez, a recuperação depois
de reinício, a auditoria, o catálogo e o modo de execução.

**Por padrão, a instalação dos testes só tem o modo serial**: o resultado não
depende de o executável em C++ estar compilado na máquina. Os testes dos outros
modos fingem o que o executável responde, ou pedem o de verdade (`nucleo_real`).

A base é a rede de `tests/rede.py`, gravada direto no banco, sem treinar de
verdade: o que importa aqui é controlar o faturamento previsto, o risco, o
ranking e a categoria de cada parceiro.
"""
from __future__ import annotations

import os
from decimal import Decimal

import gih_nucleo
import pytest
from gih_nucleo import nativo
from gih_nucleo.exaustivo import otimo
from sqlalchemy import select

from app import servico_otimizacao
from app.db import Sessao
from app.modelos import (
    Auditoria,
    ExecucaoOtimizador,
    ModoExecucao,
    OrigemCategoria,
    Perfil,
    Segmento,
    SituacaoExecucao,
    StatusComercial,
)
from app.servico_otimizacao import ganho_em_centavos, maximo_em_contagem, minimo_em_contagem
from tests.rede import VISITA, VITRINE
from tests.rede import parceiro as _parceiro

CAPACIDADES_REAIS = nativo.capacidades  # antes de qualquer teste trocá-la

@pytest.fixture(autouse=True)
def so_o_serial(monkeypatch):
    """A instalação sem o núcleo em C++: só o serial, em Python, na própria API."""

    def indisponivel(*_a, **_k):
        raise nativo.NucleoIndisponivel("fingido pelo teste")

    monkeypatch.setattr(nativo, "capacidades", indisponivel)


RTX = nativo.Dispositivo("NVIDIA GeForce RTX 4060", "8.9", 8187)


def _fingir(monkeypatch, *modos, gpu=None, ausencia="sem_cuda"):
    """O executável responde que tem estes modos, além do serial, e a GPU ou por que não."""
    capacidades = nativo.Capacidades(
        ("serial", *modos),
        8,
        "g++ fingido",
        gpu,
        None if gpu else "texto do executável, para quem investiga",
        None if gpu else ausencia,
    )
    monkeypatch.setattr(nativo, "capacidades", lambda *_a, **_k: capacidades)


@pytest.fixture
def nucleo_real(monkeypatch):
    """O executável de verdade, com OpenMP. Sem ele o teste pula — exceto na CI."""
    monkeypatch.setattr(nativo, "capacidades", CAPACIDADES_REAIS)
    obrigatorio = os.environ.get("GIH_NUCLEO_OBRIGATORIO") == "1"
    if nativo.localizar() is None or "openmp" not in CAPACIDADES_REAIS().modos:
        if obrigatorio:
            pytest.fail("O gih-nucleo com OpenMP é obrigatório aqui, e não foi encontrado.")
        pytest.skip("gih-nucleo com OpenMP não compilado — ver nucleo/README.md.")


@pytest.fixture
def gestor(criar_usuario, autenticar):
    criar_usuario(login="gestora", perfil=Perfil.GESTOR, nome="Gestora")
    return autenticar("gestora")


def _parametros(**mudancas):
    return {
        "orcamento": "500.00",
        "maximo_acoes": 3,
        "aplicacao_inicio": "2026-07-06",
        "aplicacao_fim": "2026-07-12",
        **mudancas,
    }


def _seis():
    """Seis parceiros com previsão, de tamanhos e riscos diferentes."""
    return [
        _parceiro("Alfa", "9000", previsto="9500", risco=0.10, categoria="Pizzaria"),
        _parceiro("Beta", "7000", previsto="6800", risco=0.60, categoria="Pizzaria"),
        _parceiro("Gama", "5000", previsto="5200", risco=0.30, categoria="Mercado"),
        _parceiro("Delta", "3000", previsto="2500", risco=0.80, categoria="Mercado"),
        _parceiro("Epsilon", "2000", previsto="2100", risco=0.05),
        _parceiro("Zeta", "1000", previsto="1200", risco=0.50, categoria="Mercado"),
    ]


def _calcular(cliente, **mudancas):
    r = cliente.post("/api/otimizacoes", json=_parametros(**mudancas))
    assert r.status_code == 202, r.text
    # O TestClient só devolve depois de a tarefa em segundo plano terminar.
    return cliente.get(f"/api/otimizacoes/{r.json()['id']}").json()


# ================================================================ as regras, puras
def test_ganho_soma_crescimento_e_perda_evitada():
    """RN10, com o exemplo da decisão: F̂ = R$ 30.000, p = 40%."""
    vitrine = ganho_em_centavos(Decimal("30000.00"), 0.4, Decimal("0.14"), Decimal("0.05"))
    visita = ganho_em_centavos(Decimal("30000.00"), 0.4, Decimal("0.06"), Decimal("0.30"))
    assert (vitrine, visita) == (480_000, 540_000)  # R$ 4.800 e R$ 5.400


def test_risco_sem_ruido_de_float_no_centavo():
    """0.2355 como `float` é 0.23549999…; o ganho precisa sair do decimal curto."""
    assert ganho_em_centavos(Decimal("100.00"), 0.2355, Decimal("0"), Decimal("1")) == 2355


def test_cotas_viram_contagem_em_fracao_exata():
    """RN11: mínimo para cima, máximo para baixo — sem `float`, que erraria os dois."""
    assert minimo_em_contagem(Decimal("0.3"), 45) == 14
    assert maximo_em_contagem(Decimal("0.2"), 45) == 9
    assert minimo_em_contagem(Decimal("0.1"), 30) == 3  # float: ceil(3.0000000000000004) = 4
    assert maximo_em_contagem(Decimal("0.29"), 100) == 29  # float: floor(28.999999999999996) = 28


# ================================================================ o plano
def test_sem_modelo_treinado_recusa(base, gestor):
    """UC08-E1."""
    base(_seis(), treinado=False)
    r = gestor.post("/api/otimizacoes", json=_parametros())
    assert r.status_code == 409
    assert r.json()["detail"]["erro"] == "O modelo ainda não foi treinado."


def test_o_plano_respeita_as_restricoes_e_e_o_otimo(base, gestor):
    base(_seis())
    execucao = _calcular(gestor)

    assert execucao["situacao"] == "CONCLUIDA" and execucao["viavel"] is True
    assert execucao["modo"] == "SERIAL" and execucao["modelo_versao"] == "rede-1"
    itens = execucao["itens"]
    custo = sum(Decimal(i["custo"]) for i in itens)
    ganho = sum(Decimal(i["ganho"]) for i in itens)
    assert 0 < len(itens) <= 3
    assert len({i["parceiro_id"] for i in itens}) == len(itens)
    assert custo <= Decimal("500.00")
    assert (Decimal(execucao["custo_total"]), Decimal(execucao["uplift_total"])) == (custo, ganho)
    assert Decimal(execucao["folga_orcamento"]) == Decimal("500.00") - custo
    assert Decimal(execucao["ganho_guloso"]) <= ganho
    assert execucao["tempo_ms"] is not None and execucao["parcial"] is False

    # Com seis parceiros, a enumeração confere o ótimo sobre a mesma instância.
    s = Sessao()
    try:
        montagem = servico_otimizacao.montar(s, s.get(ExecucaoOtimizador, execucao["id"]))
    finally:
        s.close()
    assert ganho * 100 == otimo(montagem.instancia)[0]


def test_o_ganho_de_cada_item_e_o_da_rn10(base, gestor):
    base(_seis())
    execucao = _calcular(gestor)
    previsoes = {p["nome"]: p for p in _seis()}
    efeitos = {nome: (Decimal(c), Decimal(r)) for nome, _custo, c, r in (VISITA, VITRINE)}
    for item in execucao["itens"]:
        spec = previsoes[item["parceiro"]]
        c, r = efeitos[item["acao"]]
        esperado = ganho_em_centavos(Decimal(spec["previsto"]), spec["risco"], c, r)
        assert Decimal(item["ganho"]) * 100 == esperado


def test_a_mesma_campanha_da_o_mesmo_plano(base, gestor):
    """RNF16: mesma versão do modelo, mesmos parâmetros, mesma semente."""
    base(_seis())
    primeiro = _calcular(gestor, maximo_acoes=4, orcamento="700.00")
    segundo = _calcular(gestor, maximo_acoes=4, orcamento="700.00")
    par = [(i["parceiro_id"], i["acao_id"]) for i in primeiro["itens"]]
    assert par == [(i["parceiro_id"], i["acao_id"]) for i in segundo["itens"]]


def test_quem_fica_fora_e_contado_por_motivo(base, gestor):
    """RN11: fora do plano, e contado — cada um pelo seu motivo."""
    base(
        _seis()
        + [
            _parceiro("Curto", "800", periodos=2),
            _parceiro("Ausente", "800", na_base=False),
            _parceiro("Inativo", "800", previsto="900", status=StatusComercial.INATIVO),
            _parceiro("Desativado", "800", previsto="900", ativo=False),
            _parceiro("Prospecto", "800", status=StatusComercial.PROSPECCAO, periodos=0),
        ]
    )
    execucao = _calcular(gestor)
    assert execucao["elegiveis"] == 6
    assert execucao["excluidos"] == {
        "historico_curto": 1,
        "fora_do_periodo": 1,
        "sem_previsao": 0,
        "inativos": 2,
        "em_prospeccao": 1,
    }
    fora = {"Curto", "Ausente", "Inativo", "Desativado", "Prospecto"}
    assert not fora & {i["parceiro"] for i in execucao["itens"]}


def test_a_cauda_longa_vem_do_ranking_e_nao_do_segmento(base, gestor):
    """RN11 com a RN02: o maior parceiro está no Top 1 **e** em queda.

    Gravado como EM_RISCO (Em Risco vence Top, RN01), ele pareceria cauda longa
    para quem lesse o segmento. Com a cota de 100% na cauda, ele não pode entrar.
    """
    specs = _seis()
    specs[0]["segmento"] = Segmento.EM_RISCO
    base(specs, top_n=1)
    execucao = _calcular(gestor, maximo_acoes=2, cota_cauda_longa="1", orcamento="1000.00")
    assert execucao["viavel"] is True
    assert "Alfa" not in {i["parceiro"] for i in execucao["itens"]}
    assert all(i["cauda_longa"] for i in execucao["itens"])
    assert {"categoria_id": None, "nome": "Cauda longa", "acoes": 2, "minimo": 2, "maximo": 2} in (
        execucao["cotas"]
    )


def test_categoria_so_conta_quando_confirmada(base, gestor):
    """RN05 e RN11: a Pizzaria só tem um parceiro, com a categoria sugerida."""
    specs = _seis()
    for spec in specs:
        if spec.get("categoria") == "Pizzaria":
            spec["origem"] = OrigemCategoria.INFERIDA
    montada = base(specs)
    pizzaria = montada.categorias["Pizzaria"]
    execucao = _calcular(gestor, cotas_categoria=[{"categoria_id": pizzaria, "minimo": "0.34"}])
    assert execucao["viavel"] is False
    assert execucao["restricao_violada"] == "elegiveis_categoria"
    assert execucao["motivo"] == (
        "Pizzaria tem 0 parceiros elegíveis, e a cota mínima exige 2 ações: faltam 2."
    )
    assert execucao["itens"] == [] and execucao["uplift_total"] is None


def test_campanha_inviavel_diz_quanto_falta(base, gestor):
    """RN07 e UC08-A1: nada de plano parcial, e o valor que falta em reais."""
    base(_seis(), top_n=1)
    execucao = _calcular(gestor, maximo_acoes=3, cota_cauda_longa="1", orcamento="200.00")
    assert execucao["situacao"] == "CONCLUIDA" and execucao["viavel"] is False
    assert execucao["restricao_violada"] == "orcamento"
    assert execucao["motivo"] == (
        "As cotas mínimas exigem pelo menos R$ 270,00, acima do orçamento de R$ 200,00: "
        "faltam R$ 70,00."
    )
    assert "Aumente o orçamento" in execucao["ajuda"]
    assert execucao["itens"] == []


def test_cota_de_categoria_que_nao_existe(base, gestor):
    base(_seis())
    cotas = [{"categoria_id": 999, "minimo": "0.1"}]
    r = gestor.post("/api/otimizacoes", json=_parametros(cotas_categoria=cotas))
    assert r.status_code == 422
    assert r.json()["detail"]["categorias"] == [999]


@pytest.mark.parametrize(
    "mudanca",
    [
        {"orcamento": "0"},
        {"maximo_acoes": 0},
        {"cota_cauda_longa": "1.5"},
        {"aplicacao_fim": "2026-07-01"},
        {"cotas_categoria": [{"categoria_id": 1, "minimo": "0.5", "maximo": "0.2"}]},
        {"cotas_categoria": [{"categoria_id": 1}]},
    ],
)
def test_parametros_impossiveis_sao_recusados(base, gestor, mudanca):
    base(_seis())
    assert gestor.post("/api/otimizacoes", json=_parametros(**mudanca)).status_code == 422


# ================================================================ um por vez e falhas
def _em_andamento(base_id: int) -> int:
    s = Sessao()
    try:
        execucao = ExecucaoOtimizador(
            modo=ModoExecucao.SERIAL,
            parametros=_parametros(),
            periodo_base_id=base_id,
            modelo_versao="rede-1",
            semente=42,
        )
        s.add(execucao)
        s.commit()
        return execucao.id
    finally:
        s.close()


def test_com_uma_otimizacao_rodando_a_segunda_e_recusada(base, gestor):
    montada = base(_seis())
    rodando = _em_andamento(montada.base_id)
    r = gestor.post("/api/otimizacoes", json=_parametros())
    assert r.status_code == 409
    assert r.json()["detail"]["em_andamento"] == rodando
    estado = gestor.get("/api/campanha").json()
    assert estado["pode_executar"] is False
    assert estado["motivo_bloqueio"] == "Já existe uma otimização em andamento."
    assert estado["em_andamento"]["id"] == rodando


def test_a_subida_da_api_libera_a_otimizacao_interrompida(base):
    from fastapi.testclient import TestClient

    from app.main import app

    montada = base(_seis())
    execucao_id = _em_andamento(montada.base_id)
    with TestClient(app):  # a subida roda o ciclo de vida da aplicação
        pass
    s = Sessao()
    try:
        execucao = s.get(ExecucaoOtimizador, execucao_id)
        assert execucao.situacao is SituacaoExecucao.FALHOU
        assert "reiniciou" in execucao.motivo
    finally:
        s.close()


def test_falha_vira_falhou_com_motivo_e_libera_a_trava(base, gestor, monkeypatch):
    base(_seis())

    def quebrar(*_a, **_k):
        raise RuntimeError("defeito de teste")

    monkeypatch.setattr(gih_nucleo, "otimizar", quebrar)
    execucao = _calcular(gestor)
    assert execucao["situacao"] == "FALHOU"
    assert "erro interno" in execucao["motivo"]
    assert "defeito de teste" not in execucao["motivo"]  # detalhe técnico só no log
    monkeypatch.undo()
    assert _calcular(gestor)["situacao"] == "CONCLUIDA"


def test_a_execucao_fica_na_auditoria_com_parametros_modo_e_tempo(base, gestor):
    """UC08, passo 10, e RF34."""
    base(_seis())
    execucao = _calcular(gestor)
    s = Sessao()
    try:
        registro = s.scalar(select(Auditoria).where(Auditoria.acao == "OTIMIZACAO_EXECUTADA"))
    finally:
        s.close()
    assert registro.usuario_id is not None
    assert registro.detalhes["execucao"] == execucao["id"]
    assert registro.detalhes["modo"] == "SERIAL"
    assert registro.detalhes["substituicao"] is None
    assert registro.detalhes["parametros"]["maximo_acoes"] == 3
    assert registro.detalhes["tempo_ms"] == execucao["tempo_ms"]
    assert registro.detalhes["viavel"] is True


# ================================================================ o modo (RF32, H55)
SERIAL, CPU, GPU = ModoExecucao.SERIAL, ModoExecucao.CPU_PARALELO, ModoExecucao.GPU


@pytest.mark.parametrize(
    "pedido, livres, esperado, troca",
    [
        (None, {SERIAL}, SERIAL, False),
        (None, {SERIAL, CPU}, CPU, False),
        (None, {SERIAL, CPU, GPU}, GPU, False),
        (SERIAL, {SERIAL, CPU}, SERIAL, False),  # forçar o baseline, para comparar
        (GPU, {SERIAL, CPU}, CPU, True),  # UC08-A4
        (CPU, {SERIAL}, SERIAL, True),
    ],
)
def test_sem_escolha_roda_o_primeiro_disponivel_e_o_indisponivel_vira_troca(
    pedido, livres, esperado, troca
):
    disponiveis = [
        servico_otimizacao.Disponibilidade(m, m in livres, None if m in livres else "Motivo.")
        for m in servico_otimizacao.ORDEM
    ]
    modo, substituicao = servico_otimizacao.escolher(pedido, disponiveis)
    assert modo == esperado
    assert (substituicao is not None) == troca


def test_os_modos_sao_perguntados_ao_executavel(base, gestor, monkeypatch):
    base(_seis())
    estado = gestor.get("/api/campanha").json()
    assert [m["modo"] for m in estado["modos"]] == ["GPU", "CPU_PARALELO", "SERIAL"]
    assert [m["disponivel"] for m in estado["modos"]] == [False, False, True]
    assert estado["modos"][1]["motivo"] == "O núcleo em C++ não está nesta instalação."
    assert estado["modo_automatico"] == "SERIAL"

    _fingir(monkeypatch, "openmp")
    estado = gestor.get("/api/campanha").json()
    assert [m["disponivel"] for m in estado["modos"]] == [False, True, True]
    assert estado["modos"][0]["motivo"] == "Esta instalação foi montada sem suporte a GPU."
    assert estado["modo_automatico"] == "CPU_PARALELO"


@pytest.mark.parametrize(
    "modos, ausencia, motivo",
    [
        (("openmp",), "sem_cuda", "Esta instalação foi montada sem suporte a GPU."),
        # Com CUDA e sem placa: a imagem da GPU num contêiner sem a reserva dela.
        (("openmp", "cuda"), "sem_placa", "Nenhuma GPU NVIDIA disponível nesta máquina."),
        (("openmp", "cuda"), "erro", "A GPU desta máquina não respondeu."),
    ],
)
def test_a_tela_diz_por_que_nao_ha_gpu(base, gestor, monkeypatch, modos, ausencia, motivo):
    """RNF06: sem GPU, o sistema funciona em CPU paralelo e diz por quê — com uma frase
    para o gestor, e não a mensagem do runtime do CUDA. O modo `cuda` no executável
    não basta: sem a placa, a GPU segue indisponível."""
    _fingir(monkeypatch, *modos, ausencia=ausencia)
    base(_seis())
    estado = gestor.get("/api/campanha").json()
    assert estado["modos"][0] == {"modo": "GPU", "disponivel": False, "motivo": motivo}
    assert estado["modo_automatico"] == "CPU_PARALELO"


def test_com_a_placa_e_o_modo_cuda_o_automatico_e_a_gpu(base, gestor, monkeypatch):
    """H54c: o executável com CUDA, numa máquina com placa, tem os três modos."""
    _fingir(monkeypatch, "openmp", "cuda", gpu=RTX)
    base(_seis())
    estado = gestor.get("/api/campanha").json()
    assert [m["disponivel"] for m in estado["modos"]] == [True, True, True]
    assert all(m["motivo"] is None for m in estado["modos"])
    assert estado["modo_automatico"] == "GPU"


def _gpu_que_falha(monkeypatch):
    """A GPU responde à pergunta dos modos e falha no cálculo: o executável sai com 1.

    Os outros modos respondem com o plano do serial em Python, que é o mesmo
    (ADR-011): o teste não depende do executável compilado.
    """
    _fingir(monkeypatch, "openmp", "cuda", gpu=RTX)
    chamados = []

    def otimizar(inst, *, modo, semente, limite_s, **_k):
        chamados.append(modo)
        if modo == "cuda":
            raise nativo.SemGpu("fingido: a placa sumiu")
        return gih_nucleo.otimizar(inst, semente=semente, limite_s=limite_s)

    monkeypatch.setattr(nativo, "otimizar", otimizar)
    return chamados


@pytest.mark.parametrize(
    "pedido, como",
    [(None, "Sem escolha, rodaria em GPU"), ("GPU", "Pedido em GPU")],
)
def test_a_gpu_que_falha_no_calculo_cai_para_a_cpu(base, gestor, monkeypatch, pedido, como):
    """RNF06 e UC08-A4 (H56): a execução termina, no primeiro modo que sobrou, e diz a troca."""
    base(_seis())
    serial = _calcular(gestor, modo="SERIAL")
    chamados = _gpu_que_falha(monkeypatch)

    execucao = _calcular(gestor, **({"modo": pedido} if pedido else {}))
    assert chamados == ["cuda", "openmp"]
    assert execucao["situacao"] == "CONCLUIDA" and execucao["viavel"] is True
    assert execucao["modo"] == "CPU_PARALELO"
    assert execucao["substituicao"] == (
        f"{como}; calculado em CPU paralelo: a GPU não respondeu no início do cálculo."
    )
    assert [(i["parceiro_id"], i["acao_id"]) for i in execucao["itens"]] == [
        (i["parceiro_id"], i["acao_id"]) for i in serial["itens"]
    ]

    s = Sessao()
    try:
        registro = s.scalars(
            select(Auditoria).where(Auditoria.acao == "OTIMIZACAO_EXECUTADA")
        ).all()[-1]
    finally:
        s.close()
    assert registro.detalhes["modo"] == "CPU_PARALELO"
    assert registro.detalhes["substituicao"] == execucao["substituicao"]


def test_nucleo_que_nao_responde_deixa_so_o_serial(base, gestor, monkeypatch):
    def quebrado(*_a, **_k):
        raise nativo.NucleoFalhou("fingido pelo teste")

    monkeypatch.setattr(nativo, "capacidades", quebrado)
    base(_seis())
    estado = gestor.get("/api/campanha").json()
    assert estado["modo_automatico"] == "SERIAL"
    assert estado["modos"][1]["motivo"] == "O núcleo em C++ não respondeu."


def test_modo_indisponivel_roda_no_primeiro_disponivel_e_diz_a_troca(base, gestor):
    """UC08-A4: a campanha é calculada, e a execução diz o que foi pedido e o que rodou."""
    base(_seis())
    execucao = _calcular(gestor, modo="CPU_PARALELO")
    assert execucao["situacao"] == "CONCLUIDA" and execucao["viavel"] is True
    assert execucao["modo"] == "SERIAL" and execucao["parametros"]["modo"] == "CPU_PARALELO"
    assert execucao["substituicao"] == (
        "Pedido em CPU paralelo, calculado em serial: o núcleo em C++ não está nesta instalação."
    )
    assert execucao["threads"] is None


def test_modo_desconhecido_e_recusado(base, gestor):
    base(_seis())
    r = gestor.post("/api/otimizacoes", json=_parametros(modo="QUANTICO"))
    assert r.status_code == 422


def test_os_modos_do_executavel_dao_o_mesmo_plano_do_serial(base, gestor, nucleo_real):
    """RF32 e ADR-011: o modo muda o tempo, e não o plano — em cada modo que esta
    instalação tem. Na CI e na imagem padrão, o CPU paralelo; com a GPU (H54c), ela
    também, e é ela que o automático escolhe."""
    base(_seis())
    serial = _calcular(gestor, modo="SERIAL")
    assert serial["modo"] == "SERIAL" and serial["threads"] is None
    livres = [d.modo.value for d in servico_otimizacao.modos() if d.disponivel]
    assert "CPU_PARALELO" in livres

    def plano(e):
        return [(i["parceiro_id"], i["acao_id"], i["ganho"]) for i in e["itens"]]

    automatico = _calcular(gestor)
    assert automatico["modo"] == livres[0]
    assert automatico["parametros"]["modo"] is None and automatico["substituicao"] is None
    for modo in livres:
        if modo == "SERIAL":
            continue
        execucao = automatico if modo == livres[0] else _calcular(gestor, modo=modo)
        assert execucao["modo"] == modo and execucao["substituicao"] is None
        # As threads só dizem algo no CPU paralelo; as da GPU são dezenas de milhares.
        assert (execucao["threads"] is not None) == (modo == "CPU_PARALELO")
        assert plano(execucao) == plano(serial), modo
        assert (execucao["uplift_total"], execucao["custo_total"]) == (
            serial["uplift_total"],
            serial["custo_total"],
        )


# ================================================================ a tela e o catálogo
def test_estado_da_campanha(base, gestor):
    specs = _seis()
    specs[1]["origem"] = OrigemCategoria.INFERIDA  # Beta: Pizzaria só sugerida
    base(specs + [_parceiro("Curto", "800", periodos=2)])
    estado = gestor.get("/api/campanha").json()
    assert estado["modelo_versao"] == "rede-1"
    assert estado["elegiveis"] == 6
    assert estado["excluidos"]["historico_curto"] == 1
    assert estado["sem_categoria"] == 2  # Epsilon, sem categoria, e Beta, só sugerida
    assert {c["nome"]: c["elegiveis"] for c in estado["categorias"]} == {
        "Mercado": 3,
        "Pizzaria": 1,
    }
    assert [a["nome"] for a in estado["acoes"]] == [VISITA[0], VITRINE[0]]
    assert estado["pode_executar"] is True and estado["ultima"] is None


def test_o_historico_lista_da_mais_recente_para_a_mais_antiga(base, gestor):
    base(_seis())
    primeira = _calcular(gestor)
    segunda = _calcular(gestor, orcamento="300.00")
    pagina = gestor.get("/api/otimizacoes").json()
    assert pagina["total"] == 2
    assert [e["id"] for e in pagina["itens"]] == [segunda["id"], primeira["id"]]
    assert pagina["itens"][0]["itens"] is None  # o plano só vem na consulta de uma


def test_o_historico_traz_o_que_o_rf34_pede(base, gestor):
    """Autor, data, parâmetros, modo, tempo e resultado de cada execução (H58)."""
    base(_seis())
    viavel = _calcular(gestor, modo="SERIAL")
    inviavel = _calcular(gestor, orcamento="10.00", cota_cauda_longa="1")
    por_id = {e["id"]: e for e in gestor.get("/api/otimizacoes").json()["itens"]}

    e = por_id[viavel["id"]]
    assert e["autor"] == "Gestora" and e["iniciada_em"] and e["concluida_em"]
    assert e["parametros"]["orcamento"] == "500.00" and e["parametros"]["modo"] == "SERIAL"
    assert e["modo"] == "SERIAL" and e["tempo_ms"] is not None
    assert e["viavel"] is True and e["acoes"] == viavel["acoes"]
    assert e["uplift_total"] == viavel["uplift_total"]

    r = por_id[inviavel["id"]]
    assert r["viavel"] is False and r["restricao_violada"] and r["motivo"]


def test_o_administrador_ve_o_historico_mas_nao_abre_o_plano(
    base, gestor, criar_usuario, autenticar
):
    """RF34 e UC08: o histórico é dele também; o plano, parceiro a parceiro, não."""
    base(_seis())
    execucao = _calcular(gestor)
    criar_usuario(login="admin2", perfil=Perfil.ADMINISTRADOR)
    admin = autenticar("admin2")

    pagina = admin.get("/api/otimizacoes")
    assert pagina.status_code == 200
    assert [e["id"] for e in pagina.json()["itens"]] == [execucao["id"]]
    assert pagina.json()["itens"][0]["itens"] is None
    assert admin.get(f"/api/otimizacoes/{execucao['id']}").status_code == 403


# ================================================================ a comparação (RF35, H59)
def _comparar(cliente, a, b):
    return cliente.get("/api/otimizacoes/comparacao", params={"a": a["id"], "b": b["id"]})


def test_dois_planos_lado_a_lado_com_o_que_mudou(base, gestor):
    """UC08-A3: um segundo plano com outros parâmetros, comparado ao primeiro — os
    parâmetros que mudaram, a diferença no resultado e parceiro a parceiro."""
    base(_seis())
    menor = _calcular(gestor, maximo_acoes=2)
    maior = _calcular(gestor, maximo_acoes=3, orcamento="800.00")
    r = _comparar(gestor, menor, maior)
    assert r.status_code == 200, r.text
    c = r.json()
    assert (c["a"]["id"], c["b"]["id"]) == (menor["id"], maior["id"])
    assert c["a"]["itens"] is None and c["b"]["itens"] is None  # os itens vêm juntos, uma vez
    assert c["parametros_diferentes"] == ["orcamento", "maximo_acoes"]
    assert c["mesmas_previsoes"] is True
    assert Decimal(c["diferenca_uplift"]) == Decimal(maior["uplift_total"]) - Decimal(
        menor["uplift_total"]
    )
    assert Decimal(c["diferenca_custo"]) == Decimal(maior["custo_total"]) - Decimal(
        menor["custo_total"]
    )
    assert c["diferenca_acoes"] == maior["acoes"] - menor["acoes"]

    # Cada parceiro de cada plano está na comparação, uma vez, com a ação de cada lado.
    acao_a = {i["parceiro_id"]: i["acao"] for i in menor["itens"]}
    acao_b = {i["parceiro_id"]: i["acao"] for i in maior["itens"]}
    itens = c["itens"]
    assert {i["parceiro_id"] for i in itens} == acao_a.keys() | acao_b.keys()
    for i in itens:
        parceiro = i["parceiro_id"]
        assert (i["acao_a"], i["acao_b"]) == (acao_a.get(parceiro), acao_b.get(parceiro))
    resumo = c["resumo"]
    assert resumo["mudaram"] + resumo["so_a"] + resumo["iguais"] == len(acao_a)
    assert resumo["mudaram"] + resumo["so_b"] + resumo["iguais"] == len(acao_b)
    # Primeiro o que mudou de ação, depois o que só está num deles, e os iguais no fim.
    ordem = ["MUDOU", "SO_A", "SO_B", "IGUAL"]
    posicoes = [ordem.index(i["situacao"]) for i in itens]
    assert posicoes == sorted(posicoes)


def test_o_analista_compara_e_o_administrador_nao(base, gestor, criar_usuario, autenticar):
    """Comparar é abrir os dois planos: de quem abre um plano (UC08)."""
    base(_seis())
    a, b = _calcular(gestor, maximo_acoes=2), _calcular(gestor)
    criar_usuario(login="analista2", perfil=Perfil.ANALISTA)
    assert _comparar(autenticar("analista2"), a, b).status_code == 200
    criar_usuario(login="admin3", perfil=Perfil.ADMINISTRADOR)
    assert _comparar(autenticar("admin3"), a, b).status_code == 403


def test_so_se_comparam_dois_planos_viaveis_e_diferentes(base, gestor):
    base(_seis())
    viavel = _calcular(gestor)
    inviavel = _calcular(gestor, orcamento="10.00", cota_cauda_longa="1")
    mesmo = _comparar(gestor, viavel, viavel)
    assert mesmo.status_code == 422
    assert mesmo.json()["detail"]["erro"] == "Escolha dois planos diferentes."
    sem_plano = _comparar(gestor, viavel, inviavel)
    assert sem_plano.status_code == 422
    assert sem_plano.json()["detail"]["execucao"] == inviavel["id"]
    assert _comparar(gestor, viavel, {"id": 999}).status_code == 404


def test_previsoes_diferentes_sao_ditas(base, gestor):
    """O modelo treinado de novo entre um plano e outro muda o ganho de cada parceiro:
    a comparação não recusa, mas diz, para a tela avisar."""
    base(_seis())
    a, b = _calcular(gestor, maximo_acoes=2), _calcular(gestor)
    s = Sessao()
    try:
        s.get(ExecucaoOtimizador, b["id"]).modelo_versao = "rede-9"
        s.commit()
    finally:
        s.close()
    assert _comparar(gestor, a, b).json()["mesmas_previsoes"] is False


def test_cada_parceiro_cai_num_dos_quatro_casos_na_ordem_da_tela():
    """Mudou de ação, só no primeiro, só no segundo, igual — e, dentro de cada um, o de
    maior diferença (ou maior ganho) primeiro."""
    from app.esquemas import ItemPlanoResposta
    from app.servico_comparacao import comparar_itens

    def item(parceiro_id, acao_id, ganho):
        return ItemPlanoResposta(
            parceiro_id=parceiro_id,
            parceiro=f"P{parceiro_id}",
            segmento=None,
            categoria=None,
            cauda_longa=False,
            acao_id=acao_id,
            acao=f"Ação {acao_id}",
            custo=Decimal("100"),
            ganho=Decimal(ganho),
        )

    a = [item(1, 1, "50"), item(2, 1, "80"), item(3, 2, "30"), item(4, 1, "10"), item(5, 1, "90")]
    b = [item(1, 2, "70"), item(2, 2, "81"), item(4, 1, "10"), item(6, 1, "40"), item(5, 1, "90")]
    comparados = comparar_itens(a, b)
    assert [(c.parceiro_id, c.situacao) for c in comparados] == [
        (1, "MUDOU"),  # a diferença de 20 vem antes da de 1
        (2, "MUDOU"),
        (3, "SO_A"),
        (6, "SO_B"),
        (5, "IGUAL"),  # o de maior ganho primeiro
        (4, "IGUAL"),
    ]
    assert (comparados[0].acao_a, comparados[0].acao_b) == ("Ação 1", "Ação 2")
    assert comparados[2].acao_b is None and comparados[3].acao_a is None


def test_os_parametros_se_comparam_pelo_valor():
    """12.000 e 12.000,00 são o mesmo orçamento; as cotas, em qualquer ordem, as mesmas."""
    from app.esquemas import ParametrosCampanha
    from app.servico_comparacao import parametros_diferentes

    base_ = {
        "maximo_acoes": 3,
        "aplicacao_inicio": "2026-07-06",
        "aplicacao_fim": "2026-07-12",
        "cotas_categoria": [
            {"categoria_id": 1, "minimo": "0.1"},
            {"categoria_id": 2, "maximo": "0.5"},
        ],
    }
    a = ParametrosCampanha(orcamento="12000", **base_)
    b = ParametrosCampanha(
        orcamento="12000.00", **{**base_, "cotas_categoria": base_["cotas_categoria"][::-1]}
    )
    assert parametros_diferentes(a, b) == []
    mudancas = {"cota_cauda_longa": "0.3", "modo": "SERIAL"}
    c = ParametrosCampanha(orcamento="12000", **{**base_, **mudancas})
    assert parametros_diferentes(a, c) == ["cota_cauda_longa", "modo"]


def test_catalogo_cria_edita_e_audita(base, gestor):
    base(_seis())
    nova = {
        "nome": "Cupom de primeira compra",
        "custo_unitario": "120.00",
        "efeito_crescimento": "0.08",
        "efeito_retencao": "0.03",
    }
    r = gestor.post("/api/acoes-comerciais", json=nova)
    assert r.status_code == 201, r.text
    acao_id = r.json()["id"]
    assert gestor.post("/api/acoes-comerciais", json=nova).status_code == 409

    r = gestor.patch(f"/api/acoes-comerciais/{acao_id}", json={"efeito_retencao": "0.1"})
    assert r.status_code == 200 and Decimal(r.json()["efeito_retencao"]) == Decimal("0.1")

    s = Sessao()
    try:
        editada = s.scalar(select(Auditoria).where(Auditoria.acao == "ACAO_COMERCIAL_EDITADA"))
    finally:
        s.close()
    assert Decimal(editada.detalhes["antes"]["efeito_retencao"]) == Decimal("0.03")
    assert Decimal(editada.detalhes["depois"]["efeito_retencao"]) == Decimal("0.1")


@pytest.mark.parametrize(
    "mudanca",
    [{"custo_unitario": "0"}, {"efeito_crescimento": "1.5"}, {"efeito_retencao": "-0.1"}],
)
def test_catalogo_recusa_valor_impossivel(base, gestor, mudanca):
    base(_seis())
    acao = {
        "nome": "Ação de teste",
        "custo_unitario": "100.00",
        "efeito_crescimento": "0.1",
        "efeito_retencao": "0.1",
        **mudanca,
    }
    assert gestor.post("/api/acoes-comerciais", json=acao).status_code == 422


def test_catalogo_sem_acao_ativa_bloqueia_a_campanha(base, gestor):
    base(_seis(), acoes=())
    r = gestor.post("/api/otimizacoes", json=_parametros())
    assert r.status_code == 409
    assert r.json()["detail"]["erro"] == "O catálogo não tem nenhuma ação ativa."
