"""O módulo de previsão pela API — UC07, RF27, RF28, RN09, histórias H42 a H45.

O modelo em si é testado em `modelo/tests`. Aqui se testa o que é da API: o
rótulo de risco igual ao segmento, o histórico mínimo (UC07-E1), quando uma
versão entra em uso (UC07-A1), versões que coexistem (A2), um treino por vez, a
recuperação depois de reinício, a trilha de auditoria e a previsão no cadastro
do parceiro — com o motivo quando não há.

A massa é gravada direto no banco, com o movimento do gerador sintético —
tendência, sazonalidade e ruído —, porque o treino precisa de algo para
aprender. Pequena (80 parceiros, 10 semanas) para o treino levar menos de um
segundo.
"""
from __future__ import annotations

import math
import random
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import event, insert, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from app import cli, servico_previsao
from app.db import Sessao
from app.modelos import (
    Auditoria,
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
    Segmento,
    SituacaoTreino,
    StatusComercial,
    TreinoModelo,
)
from app.servico_segmentacao import limiares_vigentes, reprocessar_tudo

PRIMEIRA_SEMANA = date(2026, 3, 2)


# ============================================================= a massa
@pytest.fixture
def rede(criar_usuario):
    """Grava uma rede com movimento e devolve os ids.

    `curtos` entram só nas 3 últimas semanas (histórico menor que a janela);
    `ausentes` faltam na última semana. São os dois casos da RN09 em que o
    parceiro não recebe previsão.
    """
    autor_id = criar_usuario(login="semeador", perfil=Perfil.ANALISTA)

    def montar(parceiros=80, periodos=10, semente=3, curtos=(), ausentes=()):
        rng = random.Random(semente)
        s = Sessao()
        try:
            categoria = Categoria(nome="Pizzaria")
            s.add(categoria)
            ids_periodo, ids_importacao = [], []
            for i in range(periodos):
                comeco = PRIMEIRA_SEMANA + timedelta(days=7 * i)
                periodo = Periodo(data_inicio=comeco, data_fim=comeco + timedelta(days=6))
                s.add(periodo)
                s.flush()
                importacao = Importacao(
                    periodo_id=periodo.id,
                    usuario_id=autor_id,
                    origem=OrigemImportacao.TEXTO,
                    total_gravado=0,
                    total_rejeitado=0,
                )
                s.add(importacao)
                s.flush()
                ids_periodo.append(periodo.id)
                ids_importacao.append(importacao.id)

            todos = [
                Parceiro(
                    nome=f"Parceiro {n:03d}",
                    categoria_id=categoria.id,
                    origem_categoria=OrigemCategoria.MANUAL,
                )
                for n in range(parceiros)
            ]
            s.add_all(todos)
            s.flush()

            linhas = []
            for n, parceiro in enumerate(todos):
                base = rng.lognormvariate(7.6, 1.0)
                tendencia = rng.choice([0.0, 0.0, 0.045, -0.04])
                fase = rng.uniform(0, 2 * math.pi)
                inicio = periodos - 3 if n in curtos else 0
                for i in range(inicio, periodos):
                    if n in ausentes and i == periodos - 1:
                        continue
                    sazonal = 1 + 0.08 * math.cos(2 * math.pi * i / 4 + fase)
                    valor = max(50.0, base * (1 + tendencia) ** i * sazonal * rng.gauss(1, 0.07))
                    linhas.append(
                        {
                            "parceiro_id": parceiro.id,
                            "periodo_id": ids_periodo[i],
                            "importacao_id": ids_importacao[i],
                            "faturamento": Decimal(f"{valor:.2f}"),
                            "pedidos": max(1, round(valor / 40)),
                        }
                    )
            s.execute(insert(Metrica), linhas)
            s.commit()
            reprocessar_tudo(s)
            s.commit()
            return SimpleNamespace(periodos=ids_periodo, parceiros=[p.id for p in todos])
        finally:
            s.close()

    return montar


@pytest.fixture
def gestor(criar_usuario, autenticar):
    criar_usuario(login="gestora", perfil=Perfil.GESTOR, nome="Gestora")
    return autenticar("gestora")


def _treinos() -> list[TreinoModelo]:
    s = Sessao()
    try:
        return list(s.scalars(select(TreinoModelo).order_by(TreinoModelo.id)))
    finally:
        s.close()


def _previsoes(versao: str | None = None) -> list[Previsao]:
    s = Sessao()
    try:
        consulta = select(Previsao)
        if versao is not None:
            consulta = consulta.where(Previsao.modelo_versao == versao)
        return list(s.scalars(consulta))
    finally:
        s.close()


# =================================================== o rótulo (RN09)
def test_o_rotulo_de_risco_e_o_segmento_em_risco(rede):
    """RN09, item 1: modelo e segmentação não discordam sobre o que é queda.

    Compara o rótulo de cada ponto com o segmento gravado pela segmentação. Só
    entram os pontos em que o critério de risco decide o segmento — fora dos
    recém-chegados, que a precedência da RN01 põe antes.
    """
    rede(parceiros=40, periodos=8)
    s = Sessao()
    try:
        limiares = limiares_vigentes(s)
        historico = servico_previsao.historico(s, limiares)
        segmento = {
            (h.parceiro_id, h.periodo_id): h.segmento for h in s.scalars(select(HistoricoSegmento))
        }
        comparados = 0
        for serie in historico.series:
            for i, (ordinal, em_risco) in enumerate(
                zip(serie.periodos, serie.em_risco, strict=True)
            ):
                if i + 1 < limiares.periodos_novato:
                    continue
                gravado = segmento[(serie.parceiro, historico.periodos[ordinal].id)]
                assert em_risco == (gravado is Segmento.EM_RISCO), (serie.parceiro, ordinal)
                comparados += 1
        assert comparados > 200
        assert any(e for serie in historico.series for e in serie.em_risco)
    finally:
        s.close()


def test_mudar_o_limiar_muda_o_rotulo_junto(rede):
    """O limiar da configuração (RF21) vale para os dois — é a mesma função."""
    rede(parceiros=40, periodos=8)
    s = Sessao()
    try:
        com_dois = sum(sum(x.em_risco) for x in servico_previsao.historico(s).series)
        # A limpeza entre testes apaga a linha da configuração; sem ela vale o
        # padrão, 2. Gravá-la com 3 é o que a tela de limiares faria.
        s.add(
            ConfiguracaoSegmentacao(id=1, top_n=15, periodos_tendencia=3, periodos_novato=3)
        )
        s.flush()
        com_tres = sum(sum(x.em_risco) for x in servico_previsao.historico(s).series)
        assert 0 < com_tres < com_dois
    finally:
        s.rollback()
        s.close()


@pytest.mark.parametrize("parceiros", [20, 60])
def test_ler_o_historico_nao_faz_uma_consulta_por_parceiro(rede, parceiros):
    rede(parceiros=parceiros, periodos=8)
    consultas: list[str] = []

    def anotar(conn, cursor, texto, parametros, contexto, muitos):  # noqa: ANN001
        consultas.append(texto)

    s = Sessao()
    event.listen(Engine, "before_cursor_execute", anotar)
    try:
        historico = servico_previsao.historico(s)
    finally:
        event.remove(Engine, "before_cursor_execute", anotar)
        s.close()

    assert len(historico.series) == parceiros
    assert len(consultas) <= 4, f"{len(consultas)} consultas para {parceiros} parceiros"


# =================================================== o treino pela tela
def test_historico_curto_recusa_dizendo_quantos_faltam(rede, gestor):
    """UC07-E1: abaixo de 8 períodos, recusa e diz quantos faltam."""
    rede(parceiros=20, periodos=6)
    r = gestor.post("/api/modelo/treinos")
    assert r.status_code == 409
    corpo = r.json()["detail"]
    assert "8 períodos" in corpo["erro"]
    assert corpo["faltam"] == 2
    assert "Faltam 2 períodos" in corpo["ajuda"]
    assert _treinos() == []


def test_treinar_registra_data_volume_e_metricas(rede, gestor):
    """RF27 e H45: o treino fica gravado com o que o requisito pede."""
    ids = rede()
    r = gestor.post("/api/modelo/treinos")
    assert r.status_code == 202, r.text
    assert r.json()["situacao"] == "EM_ANDAMENTO"
    treino_id = r.json()["id"]

    # O TestClient só devolve depois de a tarefa em segundo plano terminar.
    treino = gestor.get(f"/api/modelo/treinos/{treino_id}").json()
    assert treino["situacao"] == "CONCLUIDO"
    assert treino["autor"] == "Gestora"
    assert treino["concluido_em"] is not None
    assert treino["periodo_base"]["id"] == ids.periodos[-1]
    assert treino["volume"]["parceiros"] == 80
    assert treino["volume"]["periodos"] == 10
    assert treino["volume"]["amostras_teste"] > 0
    for chave in ("mape_modelo", "mape_ultimo", "mape_media_movel", "brier_modelo"):
        assert treino["metricas"][chave] is not None
    assert sum(f["amostras"] for f in treino["curva"]) == treino["volume"]["amostras_teste"]
    assert treino["versao_em_uso"] in (treino["versao"], f"referencia-{treino_id}")


def test_a_conclusao_vem_depois_do_tempo_que_o_treino_levou(rede, gestor):
    """#113: gravada com `now()`, a conclusão saía com a hora em que o treino
    começou — no PostgreSQL, `now()` é o início da transação, e a do treino
    começa antes de treinar. O treino 1 da base de demonstração mediu 1,87 s
    e ficou com 25 ms entre início e conclusão."""
    rede()
    gestor.post("/api/modelo/treinos")
    (treino,) = _treinos()
    assert treino.concluido_em - treino.iniciado_em >= timedelta(
        seconds=treino.detalhes["segundos"]
    )


def test_o_treino_fica_na_auditoria_com_autor_e_metricas(rede, gestor):
    rede()
    treino_id = gestor.post("/api/modelo/treinos").json()["id"]
    s = Sessao()
    try:
        registro = s.scalar(select(Auditoria).where(Auditoria.acao == "MODELO_TREINADO"))
    finally:
        s.close()
    assert registro is not None
    assert registro.usuario_id is not None
    assert registro.detalhes["treino"] == treino_id
    assert registro.detalhes["parceiros"] == 80
    assert "mape_modelo" in registro.detalhes


def test_so_recebe_previsao_quem_tem_janela_e_esta_no_periodo_mais_recente(rede, gestor):
    """RN09, item 3."""
    ids = rede(curtos={0, 1}, ausentes={2})
    gestor.post("/api/modelo/treinos")
    previstos = {p.parceiro_id for p in _previsoes()}
    assert previstos == set(ids.parceiros) - {ids.parceiros[0], ids.parceiros[1], ids.parceiros[2]}
    assert all(p.periodo_base_id == ids.periodos[-1] for p in _previsoes())
    assert all(0 <= p.probabilidade_queda <= 1 for p in _previsoes())


# ============================================ quando uma versão entra em uso
def test_versao_que_nao_supera_nao_entra_e_as_versoes_coexistem(rede, gestor, monkeypatch):
    """UC07-A1 e A2, na sequência que acontece de verdade.

    1. Primeiro treino não supera, sem versão anterior: vale a referência.
    2. O segundo supera: a rede dele entra em uso.
    3. O terceiro não supera: fica a rede do segundo, e as previsões dela são
       regravadas sem colidir com as que já existiam.
    """
    ids = rede()
    decisoes = iter([False, True, False])
    monkeypatch.setattr(servico_previsao, "supera_referencias", lambda _m: next(decisoes))

    for _ in range(3):
        assert gestor.post("/api/modelo/treinos").status_code == 202

    primeiro, segundo, terceiro = _treinos()
    assert (primeiro.promovido, primeiro.versao_em_uso) == (False, "referencia-1")
    assert "Não superou a referência" in primeiro.motivo
    assert "as previsões saem da referência" in primeiro.motivo
    assert (segundo.promovido, segundo.versao_em_uso, segundo.motivo) == (True, "rede-2", None)
    assert (terceiro.promovido, terceiro.versao_em_uso) == (False, "rede-2")
    assert "Mantida a versão em uso, rede-2" in terceiro.motivo

    # A2: as duas versões têm previsão sobre o mesmo período-base.
    assert {p.modelo_versao for p in _previsoes()} == {"referencia-1", "rede-2"}
    assert len(_previsoes("rede-2")) == len(_previsoes("referencia-1"))

    estado = gestor.get("/api/modelo").json()
    assert estado["versao_em_uso"] == "rede-2"
    assert estado["origem"] == "MODELO"
    assert estado["treino_da_versao"]["id"] == 2
    assert estado["ultimo_treino"]["id"] == 3
    assert ids.periodos[-1] == estado["periodo_mais_recente"]["id"]
    # As previsões em uso partem do período do último treino concluído — o 3º,
    # que manteve a rede-2 —, e não do treino que a produziu.
    assert estado["periodo_das_previsoes"]["id"] == terceiro.periodo_base_id


def test_os_pesos_gravados_refazem_as_previsoes(rede, gestor, monkeypatch):
    """ADR-010: a versão em uso sobrevive a reinício porque os pesos estão no
    banco — lidos de lá, produzem as mesmas previsões que foram gravadas."""
    import gih_modelo

    rede()
    monkeypatch.setattr(servico_previsao, "supera_referencias", lambda _m: True)
    gestor.post("/api/modelo/treinos")
    (treino,) = _treinos()
    assert treino.pesos

    s = Sessao()
    try:
        series = servico_previsao.historico(s).series
    finally:
        s.close()
    refeitas = {p.parceiro: p for p in gih_modelo.prever(treino.pesos, series)}
    for gravada in _previsoes("rede-1"):
        refeita = refeitas[gravada.parceiro_id]
        assert gravada.faturamento_previsto == Decimal(f"{refeita.faturamento:.2f}")
        assert gravada.probabilidade_queda == pytest.approx(refeita.probabilidade)


# ================================================== um treino por vez
def _em_andamento(periodo_id: int) -> int:
    s = Sessao()
    try:
        treino = TreinoModelo(periodo_base_id=periodo_id, semente=1)
        s.add(treino)
        s.commit()
        return treino.id
    finally:
        s.close()


def test_com_um_treino_rodando_o_segundo_e_recusado(rede, gestor):
    ids = rede()
    rodando = _em_andamento(ids.periodos[-1])
    r = gestor.post("/api/modelo/treinos")
    assert r.status_code == 409
    assert r.json()["detail"]["em_andamento"] == rodando
    estado = gestor.get("/api/modelo").json()
    assert estado["pode_treinar"] is False
    assert estado["motivo_bloqueio"] == "Há um treino em andamento."


def test_o_banco_nao_aceita_dois_treinos_em_andamento(rede):
    """A trava é do banco, não da memória do processo (ADR-010)."""
    ids = rede(parceiros=5, periodos=8)
    _em_andamento(ids.periodos[-1])
    with pytest.raises(IntegrityError):
        _em_andamento(ids.periodos[-1])


def test_a_subida_da_api_libera_o_treino_interrompido(rede):
    """Reinício no meio do treino: a subida seguinte marca como falho — senão a
    trava do um por vez ficaria fechada para sempre."""
    from fastapi.testclient import TestClient

    from app.main import app

    ids = rede(parceiros=5, periodos=8)
    treino_id = _em_andamento(ids.periodos[-1])
    with TestClient(app):  # a subida roda o ciclo de vida da aplicação
        pass

    s = Sessao()
    try:
        treino = s.get(TreinoModelo, treino_id)
        assert treino.situacao is SituacaoTreino.FALHOU
        assert "reiniciou" in treino.motivo
    finally:
        s.close()


def test_falha_no_treino_vira_falhou_com_motivo_e_libera_a_trava(rede, gestor, monkeypatch):
    import gih_modelo.treino

    rede()

    def quebrar(*_a, **_k):
        raise RuntimeError("defeito de teste")

    monkeypatch.setattr(gih_modelo.treino, "treinar", quebrar)
    treino_id = gestor.post("/api/modelo/treinos").json()["id"]
    treino = gestor.get(f"/api/modelo/treinos/{treino_id}").json()
    assert treino["situacao"] == "FALHOU"
    assert "erro interno" in treino["motivo"]
    assert "defeito de teste" not in treino["motivo"]  # detalhe técnico só no log

    s = Sessao()
    try:
        assert s.scalar(select(Auditoria).where(Auditoria.acao == "MODELO_TREINO_FALHOU"))
    finally:
        s.close()

    monkeypatch.undo()
    assert gestor.post("/api/modelo/treinos").status_code == 202


# ================================================ a tela do modelo
def test_estado_antes_do_primeiro_treino(rede, gestor):
    rede(parceiros=10, periodos=5)
    estado = gestor.get("/api/modelo").json()
    assert estado["versao_em_uso"] is None
    assert estado["ultimo_treino"] is None
    assert estado["periodos_na_base"] == 5
    assert estado["periodos_minimos"] == 8
    assert estado["pode_treinar"] is False
    assert "8 períodos" in estado["motivo_bloqueio"]


def test_historico_de_treinos_do_mais_recente_para_o_mais_antigo(rede, gestor):
    rede()
    for _ in range(3):
        gestor.post("/api/modelo/treinos")
    pagina = gestor.get("/api/modelo/treinos", params={"tamanho": 2}).json()
    assert pagina["total"] == 3
    assert [t["id"] for t in pagina["itens"]] == [3, 2]
    assert gestor.get("/api/modelo/treinos/99").status_code == 404


# ================================================ o cadastro do parceiro
def test_previsao_antes_de_qualquer_treino_diz_por_que(rede, gestor):
    ids = rede(parceiros=5, periodos=8)
    r = gestor.get(f"/api/parceiros/{ids.parceiros[0]}/previsao").json()
    assert r["disponivel"] is False
    assert r["motivo"] == "O modelo ainda não foi treinado."
    assert "tela Modelo" in r["ajuda"]


def test_previsao_no_cadastro_e_estimativa_com_base_e_versao(rede, gestor, monkeypatch):
    ids = rede()
    monkeypatch.setattr(servico_previsao, "supera_referencias", lambda _m: True)
    gestor.post("/api/modelo/treinos")
    r = gestor.get(f"/api/parceiros/{ids.parceiros[10]}/previsao").json()
    assert r["disponivel"] is True
    assert Decimal(r["faturamento_previsto"]) > 0
    assert 0 <= r["probabilidade_queda"] <= 1
    assert r["periodo_base"]["id"] == ids.periodos[-1]
    assert r["modelo_versao"] == "rede-1"
    assert r["origem"] == "MODELO"
    assert r["desatualizada"] is False


def test_sem_previsao_o_cadastro_diz_o_motivo_da_rn09(rede, gestor):
    ids = rede(curtos={0}, ausentes={1})
    gestor.post("/api/modelo/treinos")
    curto = gestor.get(f"/api/parceiros/{ids.parceiros[0]}/previsao").json()
    assert curto["disponivel"] is False
    assert curto["motivo"].startswith("Com 3 períodos de histórico")
    ausente = gestor.get(f"/api/parceiros/{ids.parceiros[1]}/previsao").json()
    assert ausente["disponivel"] is False
    assert "não aparece no período mais recente" in ausente["motivo"]


def test_periodo_novo_deixa_a_previsao_desatualizada(rede, gestor):
    ids = rede()
    gestor.post("/api/modelo/treinos")
    s = Sessao()
    try:
        ultimo = s.get(Periodo, ids.periodos[-1])
        novo = Periodo(
            data_inicio=ultimo.data_inicio + timedelta(days=7),
            data_fim=ultimo.data_fim + timedelta(days=7),
        )
        s.add(novo)
        s.flush()
        importacao = Importacao(
            periodo_id=novo.id,
            usuario_id=s.scalar(select(TreinoModelo.usuario_id)),
            origem=OrigemImportacao.TEXTO,
            total_gravado=1,
            total_rejeitado=0,
        )
        s.add(importacao)
        s.flush()
        s.add(
            Metrica(
                parceiro_id=ids.parceiros[5],
                periodo_id=novo.id,
                importacao_id=importacao.id,
                faturamento=Decimal("1000.00"),
                pedidos=20,
            )
        )
        s.commit()
    finally:
        s.close()

    r = gestor.get(f"/api/parceiros/{ids.parceiros[10]}/previsao").json()
    assert r["disponivel"] is True
    assert r["desatualizada"] is True
    assert gestor.get("/api/modelo").json()["desatualizado"] is True


def test_analista_le_a_previsao_mas_nao_treina(rede, criar_usuario, autenticar):
    ids = rede(parceiros=5, periodos=8)
    criar_usuario(login="analista", perfil=Perfil.ANALISTA)
    analista = autenticar("analista")
    assert analista.get(f"/api/parceiros/{ids.parceiros[0]}/previsao").status_code == 200
    assert analista.post("/api/modelo/treinos").status_code == 403


# ================================================ o terminal
def test_treinar_pelo_terminal(rede, capsys):
    rede()
    assert cli.treinar_modelo([]) == 0
    saida = capsys.readouterr().out
    assert "Concluído: 80 parceiros, 10 períodos" in saida
    assert "Versão em uso:" in saida
    (treino,) = _treinos()
    assert treino.usuario_id is None
    assert treino.situacao is SituacaoTreino.CONCLUIDO


def test_terminal_recusa_historico_curto(rede, capsys):
    rede(parceiros=5, periodos=7)
    assert cli.treinar_modelo([]) == 1
    assert "Faltam 1 período." in capsys.readouterr().err


def test_prospeccao_nao_quebra_o_treino(rede, gestor):
    """Parceiro marcado como prospecção continua com histórico; a segmentação
    o põe antes de tudo, mas o treino só precisa dos números."""
    ids = rede()
    s = Sessao()
    try:
        s.get(Parceiro, ids.parceiros[3]).status = StatusComercial.PROSPECCAO
        s.commit()
    finally:
        s.close()
    treino_id = gestor.post("/api/modelo/treinos").json()["id"]
    assert gestor.get(f"/api/modelo/treinos/{treino_id}").json()["situacao"] == "CONCLUIDO"
