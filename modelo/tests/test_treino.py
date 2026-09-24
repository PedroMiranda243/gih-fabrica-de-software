"""Treino, avaliação e previsão — H42 e H43."""
from __future__ import annotations

import io
import math

import pytest
import torch
from conftest import rede_sintetica

from gih_modelo import (
    JANELA,
    HistoricoInsuficiente,
    ReferenciaRisco,
    prever,
    prever_referencia,
    treinar,
)
from gih_modelo.treino import _deterministico


@pytest.fixture(scope="module")
def resultado(rede):
    return treinar(rede, semente=42)


def test_o_volume_registrado_e_o_da_base(rede, resultado):
    volume = resultado.volume
    assert volume.parceiros == len(rede)
    assert volume.periodos == 10
    assert volume.treino > volume.validacao > 0
    assert volume.teste > 0
    assert resultado.epocas > 0
    assert resultado.segundos > 0


def test_mesma_base_e_mesma_semente_dao_as_mesmas_metricas(rede, resultado):
    """RNF16. Sem isto, a métrica que a tela mostra não se reproduz na frente
    de quem avalia."""
    de_novo = treinar(rede, semente=42)
    assert de_novo.metricas == resultado.metricas
    assert de_novo.epocas == resultado.epocas
    assert de_novo.temperatura == resultado.temperatura
    assert prever(de_novo.pesos, rede) == prever(resultado.pesos, rede)


def test_na_rede_sintetica_a_rede_supera_as_referencias(resultado):
    """O critério da H42 e o da H43, na massa de teste.

    Treino determinístico: este teste não oscila. Se ele quebrar, algo mudou
    no modelo ou nas variáveis — e a medição de `docs/medicoes/modelo.md`
    precisa ser refeita antes de confiar no número novo.
    """
    m = resultado.metricas
    assert m.mape_modelo < min(m.mape_ultimo, m.mape_media_movel)
    assert m.brier_modelo < m.brier_referencia


def test_a_curva_de_calibracao_cobre_o_teste(resultado):
    assert sum(f.amostras for f in resultado.metricas.curva) == resultado.volume.teste
    assert 0 <= resultado.metricas.calibracao_modelo <= 1


def test_historico_curto_demais_e_recusado():
    # Seis períodos: janela de 4, um alvo de validação e um de teste — nenhum
    # para treinar.
    with pytest.raises(HistoricoInsuficiente):
        treinar(rede_sintetica(50, 6))


def test_prever_devolve_o_proximo_periodo_de_quem_tem_janela(rede, resultado):
    previsoes = prever(resultado.pesos, rede)
    com_janela = {s.parceiro for s in rede if len(s.periodos) >= JANELA}
    assert {p.parceiro for p in previsoes} == com_janela
    for p in previsoes:
        assert p.faturamento > 0
        assert 0 <= p.probabilidade <= 1
        assert math.isfinite(p.faturamento)


def test_a_referencia_preve_com_as_contas_simples(rede):
    referencia = ReferenciaRisco(se_caiu=0.4, se_nao_caiu=0.1)
    previsoes = prever_referencia(rede, baseline="ultimo", referencia=referencia)
    por_parceiro = {p.parceiro: p for p in previsoes}
    for s in rede:
        if len(s.periodos) < JANELA:
            assert s.parceiro not in por_parceiro
            continue
        p = por_parceiro[s.parceiro]
        assert p.faturamento == pytest.approx(s.faturamento[-1])
        caiu = s.faturamento[-1] < s.faturamento[-2]
        assert p.probabilidade == (0.4 if caiu else 0.1)


class _Armadilha:
    """Um objeto que executaria código ao ser lido por pickle comum."""

    executou = False

    def __reduce__(self):
        return (_disparar, ())


def _disparar():
    _Armadilha.executou = True
    return None


def test_pesos_sao_lidos_sem_executar_codigo(rede):
    """O formato do PyTorch é pickle. Lido sem `weights_only`, pesos adulterados
    no banco rodariam código dentro da API."""
    buffer = io.BytesIO()
    torch.save({"formato": 1, "estado": _Armadilha()}, buffer)
    with pytest.raises(Exception):  # noqa: B017 — o tipo exato é do PyTorch
        prever(buffer.getvalue(), rede)
    assert not _Armadilha.executou


def test_formato_de_pesos_desconhecido_e_recusado(rede):
    buffer = io.BytesIO()
    torch.save({"formato": 99}, buffer)
    with pytest.raises(ValueError, match="Formato"):
        prever(buffer.getvalue(), rede)


def test_o_modo_deterministico_devolve_a_configuracao_do_processo():
    threads = torch.get_num_threads()
    antes = torch.are_deterministic_algorithms_enabled()
    with _deterministico(1):
        assert torch.get_num_threads() == 1
        assert torch.are_deterministic_algorithms_enabled()
    assert torch.get_num_threads() == threads
    assert torch.are_deterministic_algorithms_enabled() == antes
