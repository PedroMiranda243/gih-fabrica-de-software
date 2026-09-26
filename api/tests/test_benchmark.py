"""O benchmark — UC09, RF33, história H57.

Quase todos os testes fingem o executável do núcleo: os modos que ele diz ter, e
o tempo de cada busca. O plano de cada modo é o do genético em Python, que é o
mesmo (ADR-011) — o que se testa aqui é o que a API faz com as medidas: a
média, o desvio, os ganhos, a divergência, a explicação da GPU e o gráfico. O
Python roda num processo à parte só no teste que confere isso; nos outros, numa
thread, para o teste não pagar a subida de um interpretador.

Com o executável de verdade, um teste confere que cada modo desta instalação dá
o plano do Python.
"""
from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import replace
from datetime import date

import gih_nucleo
import pytest
from gih_nucleo import cenario, nativo
from sqlalchemy import select

from app import servico_benchmark
from app.db import Sessao
from app.modelos import (
    Auditoria,
    ExecucaoBenchmark,
    ExecucaoOtimizador,
    ModoExecucao,
    Perfil,
    Periodo,
    SituacaoExecucao,
)

CAPACIDADES_REAIS = nativo.capacidades  # antes de qualquer teste trocá-la
PROCESSO_REAL = servico_benchmark.processo_do_python
RTX = nativo.Dispositivo("NVIDIA GeForce RTX 4060", "8.9", 8187)
PEQUENO = {"parceiros": 100, "acoes": 2, "repeticoes": 2}


@pytest.fixture(autouse=True)
def busca_curta(monkeypatch):
    """Um genético de poucas gerações, e o Python numa thread: milissegundos."""
    monkeypatch.setattr(servico_benchmark, "PARAMETROS_DA_BUSCA", {"geracoes": 3})

    @contextmanager
    def na_mesma_maquina():
        with ThreadPoolExecutor(max_workers=1) as executor:
            yield executor

    monkeypatch.setattr(servico_benchmark, "processo_do_python", na_mesma_maquina)


@pytest.fixture(autouse=True)
def so_o_python(monkeypatch):
    """A instalação sem o núcleo em C++: só o Python."""

    def indisponivel(*_a, **_k):
        raise nativo.NucleoIndisponivel("fingido pelo teste")

    monkeypatch.setattr(nativo, "capacidades", indisponivel)


@pytest.fixture
def gestor(criar_usuario, autenticar):
    criar_usuario(login="gestora", perfil=Perfil.GESTOR, nome="Gestora")
    return autenticar("gestora")


def _fingir(monkeypatch, *modos, gpu=None, tempos=None, contexto=0.19, falha=None):
    """O executável tem estes modos, além do serial; cada busca leva `tempos[modo]`
    segundos — ou a função de parceiros que ele for —, com o plano do Python.

    `falha(modo, chamada)` pode levantar, para simular o executável que falha.
    """
    capacidades = nativo.Capacidades(
        ("serial", *modos),
        8,
        "g++ fingido",
        gpu,
        None if gpu else "texto do executável",
        None if gpu else "sem_cuda",
    )
    monkeypatch.setattr(nativo, "capacidades", lambda *_a, **_k: capacidades)
    monkeypatch.setattr(nativo, "nucleos_fisicos", lambda: 8)
    tempos = tempos or {"serial": 0.4, "openmp": 0.05, "cuda": 0.2}
    chamadas = []

    def otimizar(inst, *, modo, semente, threads=None, **parametros):
        chamadas.append(modo)
        if falha:
            falha(modo, chamadas.count(modo))
        r = gih_nucleo.otimizar(inst, semente=semente, **parametros)
        t = tempos[modo]
        segundos = t(len(inst.ganho)) if callable(t) else t
        return replace(
            r,
            segundos=segundos,
            threads=threads or 1,
            contexto_s=contexto if modo == "cuda" else 0.0,
        )

    monkeypatch.setattr(nativo, "otimizar", otimizar)
    return chamadas


def _rodar(cliente, **parametros):
    r = cliente.post("/api/benchmarks", json={**PEQUENO, **parametros})
    assert r.status_code == 202, r.text
    assert r.json()["situacao"] == "EM_ANDAMENTO"
    # O TestClient roda a tarefa de fundo antes de devolver: já terminou.
    return cliente.get(f"/api/benchmarks/{r.json()['id']}").json()


def _coluna(execucao, coluna):
    return next(c for c in execucao["colunas"] if c["coluna"] == coluna)


# ================================================================ a tela ao abrir
def test_sem_o_nucleo_so_o_python_esta_disponivel(gestor):
    estado = gestor.get("/api/benchmark").json()
    assert [c["coluna"] for c in estado["colunas"]] == ["PYTHON", "CPP_SERIAL", "OPENMP", "GPU"]
    assert [c["disponivel"] for c in estado["colunas"]] == [True, False, False, False]
    assert {c["motivo"] for c in estado["colunas"][1:]} == {
        "O núcleo em C++ não está nesta instalação."
    }
    assert estado["padrao"] == {"parceiros": 2000, "acoes": 5, "repeticoes": 3}
    assert estado["pode_executar"] is True and estado["ultima"] is None
    assert estado["python_s_por_parceiro"] is None


def test_com_o_nucleo_a_tela_diz_as_threads_e_a_gpu(gestor, monkeypatch):
    _fingir(monkeypatch, "openmp", "cuda", gpu=RTX)
    colunas = gestor.get("/api/benchmark").json()["colunas"]
    assert all(c["disponivel"] for c in colunas)
    assert [c["detalhe"] for c in colunas] == [None, None, "8 threads", RTX.nome]


def test_sem_gpu_ela_fica_de_fora_e_diz_por_que(gestor, monkeypatch):
    """UC09-A1: o comparativo vale para os modos que há."""
    _fingir(monkeypatch, "openmp")
    execucao = _rodar(gestor)
    gpu = _coluna(execucao, "GPU")
    assert gpu["situacao"] == "INDISPONIVEL"
    assert gpu["motivo"] == "Esta instalação foi montada sem suporte a GPU."
    assert [c["situacao"] for c in execucao["colunas"][:3]] == ["MEDIDA"] * 3
    assert execucao["explicacao_gpu"] is None


# ================================================================ a medição
def test_so_com_o_python_o_benchmark_mede_e_registra(gestor):
    execucao = _rodar(gestor)
    assert execucao["situacao"] == "CONCLUIDA" and execucao["progresso"] is None
    python = _coluna(execucao, "PYTHON")
    assert python["situacao"] == "MEDIDA" and len(python["tempos_s"]) == 2
    assert python["media_s"] > 0 and python["desvio_s"] is not None
    assert python["speedup_python"] == pytest.approx(1)
    assert python["diferenca_uplift"] == 0 and python["divergente"] is False
    esperado = gih_nucleo.otimizar(cenario.sintetico(100, 2), semente=42, geracoes=3)
    assert float(python["uplift"]) == esperado.avaliacao.ganho / 100
    assert execucao["autor"] == "Gestora" and execucao["disputada"] is False

    s = Sessao()
    try:
        registro = s.scalar(select(Auditoria).where(Auditoria.acao == "BENCHMARK_EXECUTADO"))
    finally:
        s.close()
    assert registro.detalhes["execucao"] == execucao["id"]
    assert registro.detalhes["parametros"] == PEQUENO
    assert set(registro.detalhes["medias_s"]) == {"PYTHON"}


def test_as_quatro_colunas_com_os_ganhos_contra_o_python_e_o_cpp(gestor, monkeypatch):
    """RF33: tempo, desvio, speedup e uplift. O OpenMP e a GPU se leem também contra o
    C++ serial (ADR-012)."""
    chamadas = _fingir(monkeypatch, "openmp", "cuda", gpu=RTX)
    execucao = _rodar(gestor, repeticoes=3)
    # Um aquecimento de cada modo do executável, depois três repetições de cada.
    assert chamadas == ["serial", "openmp", "cuda"] + ["serial", "openmp", "cuda"] * 3
    python, cpp, openmp, gpu = execucao["colunas"]
    assert cpp["media_s"] == pytest.approx(0.4) and cpp["desvio_s"] == 0
    assert openmp["speedup_cpp"] == pytest.approx(8) and gpu["speedup_cpp"] == pytest.approx(2)
    assert cpp["speedup_cpp"] is None and python["speedup_cpp"] is None
    assert gpu["speedup_python"] == pytest.approx(python["media_s"] / 0.2)
    assert gpu["contexto_s"] == pytest.approx(0.19) and openmp["contexto_s"] is None
    assert all(c["diferenca_uplift"] == 0 for c in execucao["colunas"])
    assert len({c["uplift"] for c in execucao["colunas"]}) == 1  # o mesmo plano
    assert execucao["ambiente"] == {"threads": 8, "gpu": RTX.nome, "compilador": "g++ fingido"}


def test_a_gpu_que_nao_ganha_e_explicada(gestor, monkeypatch):
    """UC09-A2: o resultado negativo é informação, e não erro — com o custo fixo."""
    _fingir(monkeypatch, "openmp", "cuda", gpu=RTX)
    texto = _rodar(gestor)["explicacao_gpu"]
    assert texto.startswith("Com 100 parceiros, a GPU não ganha do CPU paralelo")
    assert "gasta 190 ms para começar" in texto
    assert "A busca em si leva 10,0 ms, 5,0x mais rápida que a do CPU paralelo" in texto
    assert texto.endswith("É um resultado legítimo, e não um defeito.")


def test_a_gpu_que_ganha_nao_precisa_de_explicacao(gestor, monkeypatch):
    _fingir(
        monkeypatch, "openmp", "cuda", gpu=RTX, tempos={"serial": 1, "openmp": 0.2, "cuda": 0.1}
    )
    assert _rodar(gestor)["explicacao_gpu"] is None


def test_o_uplift_diferente_do_python_e_destacado(gestor, monkeypatch):
    """UC09-A3: acima de 2% do Python, é possível defeito de implementação."""
    _fingir(monkeypatch, "openmp")
    original = nativo.otimizar

    def com_defeito(inst, *, modo, **k):
        r = original(inst, modo=modo, **k)
        if modo != "openmp":
            return r
        return replace(r, avaliacao=replace(r.avaliacao, ganho=round(r.avaliacao.ganho * 0.95)))

    monkeypatch.setattr(nativo, "otimizar", com_defeito)
    openmp = _coluna(_rodar(gestor), "OPENMP")
    assert openmp["divergente"] is True
    assert openmp["diferenca_uplift"] == pytest.approx(0.05, abs=0.001)


def test_a_gpu_que_falha_no_meio_sai_e_o_resto_segue(gestor, monkeypatch):
    """UC09-E1: a GPU fica de fora desta execução, com o motivo, e os outros terminam."""

    def falha(modo, chamada):
        if modo == "cuda" and chamada == 2:
            raise nativo.SemGpu("fingido: a placa sumiu")

    chamadas = _fingir(monkeypatch, "openmp", "cuda", gpu=RTX, falha=falha)
    execucao = _rodar(gestor, repeticoes=3)
    assert execucao["situacao"] == "CONCLUIDA"
    gpu = _coluna(execucao, "GPU")
    assert gpu["situacao"] == "FALHOU" and gpu["tempos_s"] == []
    assert gpu["motivo"].startswith("A GPU não respondeu durante a medição")
    assert chamadas.count("cuda") == 2  # o aquecimento e a que falhou; depois, nenhuma
    assert len(_coluna(execucao, "OPENMP")["tempos_s"]) == 3


def test_o_erro_do_nucleo_vira_falha_e_solta_a_trava(gestor, monkeypatch):
    def falha(_modo, _chamada):
        raise nativo.NucleoFalhou("fingido: defeito do porte")

    _fingir(monkeypatch, falha=falha)
    execucao = _rodar(gestor)
    assert execucao["situacao"] == "FALHOU"
    assert execucao["motivo"].startswith("O benchmark falhou por um erro interno (registro ")
    assert execucao["progresso"] is None
    s = Sessao()
    try:
        assert s.scalar(select(Auditoria).where(Auditoria.acao == "BENCHMARK_FALHOU"))
    finally:
        s.close()
    _fingir(monkeypatch)
    assert _rodar(gestor)["situacao"] == "CONCLUIDA"


def test_o_python_roda_num_processo_a_parte(gestor, monkeypatch):
    """O baseline não divide o interpretador com as requisições da tela."""
    monkeypatch.setattr(servico_benchmark, "processo_do_python", PROCESSO_REAL)
    python = _coluna(_rodar(gestor, repeticoes=1), "PYTHON")
    assert python["situacao"] == "MEDIDA" and python["media_s"] > 0


# ================================================================ um por vez, e a disputa
def _em_andamento() -> int:
    s = Sessao()
    try:
        e = ExecucaoBenchmark(parceiros=100, acoes=2, repeticoes=1, semente=42)
        s.add(e)
        s.commit()
        return e.id
    finally:
        s.close()


def test_um_benchmark_por_vez(gestor):
    rodando = _em_andamento()
    r = gestor.post("/api/benchmarks", json=PEQUENO)
    assert r.status_code == 409
    assert r.json()["detail"]["em_andamento"] == rodando
    estado = gestor.get("/api/benchmark").json()
    assert estado["pode_executar"] is False and estado["em_andamento"]["id"] == rodando


def test_o_que_a_api_interrompeu_vira_falha_na_subida(gestor):
    rodando = _em_andamento()
    s = Sessao()
    try:
        assert servico_benchmark.recuperar_interrompidos(s) == 1
        s.commit()
        e = s.get(ExecucaoBenchmark, rodando)
        assert e.situacao == SituacaoExecucao.FALHOU and e.motivo.startswith("Interrompido")
    finally:
        s.close()


def test_uma_otimizacao_junto_marca_a_medicao_como_disputada(gestor):
    s = Sessao()
    try:
        periodo = Periodo(data_inicio=date(2026, 9, 1), data_fim=date(2026, 9, 7))
        s.add(periodo)
        s.flush()
        s.add(
            ExecucaoOtimizador(
                modo=ModoExecucao.SERIAL,
                parametros={},
                periodo_base_id=periodo.id,
                modelo_versao="rede-1",
                semente=42,
            )
        )
        s.commit()
    finally:
        s.close()
    assert _rodar(gestor)["disputada"] is True


@pytest.mark.parametrize(
    "mudanca",
    [
        {"parceiros": 99},
        {"parceiros": 10_001},
        {"acoes": 0},
        {"acoes": 11},
        {"repeticoes": 0},
        {"repeticoes": 11},
    ],
)
def test_cenario_fora_da_faixa_e_recusado(gestor, mudanca):
    assert gestor.post("/api/benchmarks", json={**PEQUENO, **mudanca}).status_code == 422


# ================================================================ o gráfico e o histórico
def test_a_escalabilidade_junta_os_tamanhos_do_mesmo_numero_de_acoes(gestor, monkeypatch):
    """UC09, passo 7: de cada tamanho, a mais recente; outro número de ações fica de fora.
    E a explicação da GPU diz o tamanho em que ela passa a ganhar, se já foi medido."""
    _fingir(
        monkeypatch,
        "openmp",
        "cuda",
        gpu=RTX,
        # O OpenMP cresce com os parceiros; a GPU quase não.
        tempos={"serial": 1, "openmp": lambda n: n / 1000, "cuda": lambda n: 0.19 + n / 20000},
    )
    grande = _rodar(gestor, parceiros=400)
    _rodar(gestor, parceiros=100, acoes=3)  # outro número de ações
    antiga = _rodar(gestor, parceiros=100)
    recente = _rodar(gestor, parceiros=100)

    series = {s["coluna"]: s["pontos"] for s in recente["escalabilidade"]["series"]}
    assert recente["escalabilidade"]["acoes"] == 2
    assert [p["parceiros"] for p in series["GPU"]] == [100, 400]
    assert [p["execucao_id"] for p in series["GPU"]] == [recente["id"], grande["id"]]
    assert antiga["id"] not in {p["execucao_id"] for p in series["OPENMP"]}
    assert "ela passa a ganhar com 400 parceiros" in recente["explicacao_gpu"]

    estado = gestor.get("/api/benchmark").json()
    assert estado["ultima"]["id"] == recente["id"]
    assert estado["python_s_por_parceiro"] == pytest.approx(
        _coluna(recente, "PYTHON")["media_s"] / 100
    )
    pagina = gestor.get("/api/benchmarks").json()
    assert [e["id"] for e in pagina["itens"]] == [recente["id"], antiga["id"], 2, grande["id"]]
    assert pagina["total"] == 4 and pagina["itens"][0]["escalabilidade"] is None


def test_benchmark_inexistente_e_404(gestor):
    assert gestor.get("/api/benchmarks/999").status_code == 404


# ================================================================ o núcleo de verdade
@pytest.fixture
def nucleo_real(monkeypatch):
    """O executável de verdade. Sem ele o teste pula — exceto na CI."""
    monkeypatch.setattr(nativo, "capacidades", CAPACIDADES_REAIS)
    if nativo.localizar() is None:
        if os.environ.get("GIH_NUCLEO_OBRIGATORIO") == "1":
            pytest.fail("O gih-nucleo é obrigatório aqui, e não foi encontrado.")
        pytest.skip("gih-nucleo não compilado — ver nucleo/README.md.")


def test_cada_modo_desta_instalacao_da_o_plano_do_python(gestor, nucleo_real):
    """ADR-011, com o executável que houver: na CI, o C++ serial e o OpenMP; aqui, a
    GPU também, se houver placa."""
    execucao = _rodar(gestor, repeticoes=1)
    medidas = [c for c in execucao["colunas"] if c["situacao"] == "MEDIDA"]
    assert {c["coluna"] for c in medidas} >= {"PYTHON", "CPP_SERIAL", "OPENMP"}
    assert all(c["diferenca_uplift"] == 0 for c in medidas)
    assert len({c["uplift"] for c in medidas}) == 1
