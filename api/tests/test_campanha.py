"""A campanha pela API — UC08, RF29 a RF31, RN07, RN10, RN11, histórias H48 a H52.

O otimizador em si é testado em `nucleo/tests`. Aqui se testa o que é da API:
o ganho da RN10 em centavos, quem entra e quem fica fora (RN11), as cotas em
contagem, a categoria confirmada, a cauda longa pelo ranking (e não pelo
segmento), a recusa com o que falta, uma execução por vez, a recuperação depois
de reinício, a auditoria e o catálogo.

A base é gravada direto no banco — parceiros, métricas, um treino concluído e as
previsões dele —, sem treinar de verdade: o que importa aqui é controlar o
faturamento previsto, o risco, o ranking e a categoria de cada parceiro.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import gih_nucleo
import pytest
from gih_nucleo.exaustivo import otimo
from sqlalchemy import select

from app import servico_otimizacao
from app.db import Sessao
from app.modelos import (
    AcaoComercial,
    Auditoria,
    Categoria,
    ConfiguracaoSegmentacao,
    ExecucaoOtimizador,
    HistoricoSegmento,
    Importacao,
    Metrica,
    ModoExecucao,
    OrigemCategoria,
    OrigemImportacao,
    Parceiro,
    Perfil,
    Periodo,
    Previsao,
    Segmento,
    SituacaoExecucao,
    SituacaoTreino,
    StatusComercial,
    TreinoModelo,
)
from app.servico_otimizacao import ganho_em_centavos, maximo_em_contagem, minimo_em_contagem

PRIMEIRA_SEMANA = date(2026, 6, 1)
PERIODOS = 5
VISITA = ("Visita de relacionamento", "90.00", "0.06", "0.30")
VITRINE = ("Destaque na vitrine", "260.00", "0.14", "0.05")


def _parceiro(nome, faturamento, **extra):
    return {"nome": nome, "faturamento": Decimal(faturamento), **extra}


@pytest.fixture
def base(criar_usuario):
    """Grava a rede e devolve os ids. Cada parceiro é um dict:

    - `faturamento`: o do período-base, que decide o ranking;
    - `previsto` e `risco`: a previsão da versão em uso; sem `previsto`, não há;
    - `categoria` e `origem`: a categoria e se ela foi confirmada (RN05);
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
    assert registro.detalhes["parametros"]["maximo_acoes"] == 3
    assert registro.detalhes["tempo_ms"] == execucao["tempo_ms"]
    assert registro.detalhes["viavel"] is True


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
