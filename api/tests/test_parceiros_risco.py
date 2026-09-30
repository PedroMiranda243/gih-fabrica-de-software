"""O risco de queda na lista de parceiros — H80 (RF23, RF28).

A Parte V deixou como próximo passo "a coluna de risco na lista de parceiros, com
ordenação por ela": a pergunta "em quem investir?" feita à rede inteira de uma vez.
O que importa em cada teste é que o risco da lista seja **o mesmo** do cadastro do
parceiro — a versão em uso, a partir do período dela —, que a ordem por ele deixe
quem não tem previsão no fim, e que ele venha numa consulta só.
"""
from __future__ import annotations

import csv
import io
from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import event
from sqlalchemy.engine import Engine

from app.db import Sessao
from app.modelos import Importacao, Metrica, OrigemImportacao, Perfil, Periodo, Previsao
from tests.rede import parceiro


@pytest.fixture
def analista(criar_usuario, autenticar, cliente):
    criar_usuario(login="analista", perfil=Perfil.ANALISTA)
    autenticar("analista")
    return cliente


def _rede(base):
    return base(
        [
            parceiro("Alto Risco", "900.00", previsto="700.00", risco=0.81),
            parceiro("Baixo Risco", "1500.00", previsto="1600.00", risco=0.04),
            parceiro("Quase Nenhum", "400.00", previsto="410.00", risco=0.003),
            # Sem `previsto`: sem previsão na versão em uso, como o recém-chegado (RN09).
            parceiro("Sem Previsao", "300.00"),
        ]
    )


def _por_nome(resposta) -> dict[str, dict]:
    return {i["nome"]: i for i in resposta.json()["itens"]}


def test_a_lista_traz_o_risco_da_versao_em_uso_e_diz_de_onde_ele_vem(analista, base):
    rede = _rede(base)

    r = analista.get("/api/parceiros")

    assert r.status_code == 200
    itens = _por_nome(r)
    assert itens["Alto Risco"]["risco_queda"] == pytest.approx(0.81)
    assert itens["Baixo Risco"]["risco_queda"] == pytest.approx(0.04)
    origem = r.json()["risco"]
    assert origem["modelo_versao"] == "rede-1"
    assert origem["periodo_base"]["id"] == rede.base_id
    assert origem["desatualizada"] is False


def test_o_risco_fica_fora_do_desempenho_medido(analista, base):
    """Estimativa não se veste de medição: o risco não mora no bloco do que o parceiro fez."""
    _rede(base)

    item = _por_nome(analista.get("/api/parceiros"))["Alto Risco"]

    assert "risco_queda" not in item["desempenho"]


def test_sem_previsao_o_risco_vem_nulo_e_o_parceiro_continua_na_lista(analista, base):
    _rede(base)

    itens = _por_nome(analista.get("/api/parceiros"))

    assert "Sem Previsao" in itens
    assert itens["Sem Previsao"]["risco_queda"] is None


@pytest.mark.parametrize("descendente", [True, False])
def test_ordena_por_risco_com_quem_nao_tem_previsao_no_fim(analista, base, descendente):
    _rede(base)

    r = analista.get("/api/parceiros", params={"ordenar_por": "risco", "descendente": descendente})

    nomes = [i["nome"] for i in r.json()["itens"]]
    com_risco = ["Alto Risco", "Baixo Risco", "Quase Nenhum"]
    assert nomes == (com_risco if descendente else com_risco[::-1]) + ["Sem Previsao"]


def test_o_risco_da_lista_e_o_mesmo_do_cadastro_do_parceiro(analista, base):
    """Duas escolhas de versão fariam as duas telas mostrarem dois riscos para o mesmo parceiro."""
    rede = _rede(base)
    parceiro_id = rede.parceiros["Alto Risco"]

    da_lista = _por_nome(analista.get("/api/parceiros"))["Alto Risco"]["risco_queda"]
    previsao = analista.get(f"/api/parceiros/{parceiro_id}/previsao").json()
    do_cadastro = previsao["probabilidade_queda"]
    do_item = analista.get(f"/api/parceiros/{parceiro_id}").json()["risco_queda"]

    assert da_lista == pytest.approx(do_cadastro)
    assert do_item == pytest.approx(do_cadastro)


def test_so_a_versao_em_uso_entra_na_lista(analista, base):
    """A previsão da referência do mesmo treino, ou de uma versão antiga, não aparece."""
    rede = _rede(base)
    s = Sessao()
    try:
        s.add(
            Previsao(
                parceiro_id=rede.parceiros["Baixo Risco"],
                periodo_base_id=rede.base_id,
                faturamento_previsto=Decimal("100.00"),
                probabilidade_queda=0.99,
                modelo_versao="referencia-1",
            )
        )
        s.commit()
    finally:
        s.close()

    item = _por_nome(analista.get("/api/parceiros"))["Baixo Risco"]

    assert item["risco_queda"] == pytest.approx(0.04)


def test_sem_modelo_treinado_o_risco_vem_nulo_e_sem_origem(analista, base):
    base([parceiro("Alguem", "500.00", previsto="500.00")], treinado=False)

    r = analista.get("/api/parceiros")

    assert r.json()["risco"] is None
    assert _por_nome(r)["Alguem"]["risco_queda"] is None


def test_periodo_mais_novo_que_o_treino_marca_o_risco_desatualizado(
    analista, base, criar_usuario
):
    rede = _rede(base)
    autor = criar_usuario(login="importador", perfil=Perfil.GESTOR)
    s = Sessao()
    try:
        antigo = s.get(Periodo, rede.base_id)
        novo = Periodo(
            data_inicio=antigo.data_inicio + timedelta(days=7),
            data_fim=antigo.data_fim + timedelta(days=7),
        )
        s.add(novo)
        s.flush()
        imp = Importacao(
            periodo_id=novo.id,
            usuario_id=autor,
            origem=OrigemImportacao.TEXTO,
            total_gravado=1,
            total_rejeitado=0,
        )
        s.add(imp)
        s.flush()
        s.add(
            Metrica(
                parceiro_id=rede.parceiros["Alto Risco"],
                periodo_id=novo.id,
                importacao_id=imp.id,
                faturamento=Decimal("800.00"),
                pedidos=9,
            )
        )
        s.commit()
    finally:
        s.close()

    r = analista.get("/api/parceiros")

    assert r.json()["risco"]["desatualizada"] is True
    assert _por_nome(r)["Alto Risco"]["risco_queda"] == pytest.approx(0.81)


def test_a_exportacao_traz_o_risco_com_o_texto_da_tela(analista, base):
    _rede(base)

    r = analista.get(
        "/api/parceiros/exportacao.csv", params={"ordenar_por": "risco", "descendente": True}
    )

    linhas = list(csv.DictReader(io.StringIO(r.content.decode("utf-8-sig")), delimiter=";"))
    riscos = {linha["Parceiro"]: linha["Risco de queda"] for linha in linhas}
    assert riscos == {
        "Alto Risco": "81%",
        "Baixo Risco": "4%",
        "Quase Nenhum": "menos de 1%",
        "Sem Previsao": "",
    }
    assert [linha["Parceiro"] for linha in linhas][-1] == "Sem Previsao"


def test_o_risco_nao_custa_uma_consulta_por_linha(analista, base):
    """A junção externa, e não a previsão parceiro a parceiro (RNF03, RNF04)."""
    base([parceiro(f"Parceiro {n:02d}", "500.00", previsto="500.00", risco=0.5) for n in range(30)])
    consultas: list[str] = []

    def anotar(_conexao, _cursor, sql, *_):
        consultas.append(sql)

    event.listen(Engine, "before_cursor_execute", anotar)
    try:
        r = analista.get("/api/parceiros", params={"tamanho": 30, "ordenar_por": "risco"})
    finally:
        # No `finally`: um ouvinte vazado contaria as consultas dos testes seguintes.
        event.remove(Engine, "before_cursor_execute", anotar)

    assert r.status_code == 200
    assert len(r.json()["itens"]) == 30
    com_previsao = [c for c in consultas if "previsao" in c.lower()]
    assert len(com_previsao) <= 2, f"{len(com_previsao)} consultas com a previsão para 30 linhas"
