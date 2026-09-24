"""As referências — H46 — e as métricas de avaliação."""
from __future__ import annotations

import numpy as np
import pytest

from gih_modelo.avaliacao import brier, curva_calibracao, erro_calibracao, mape
from gih_modelo.baselines import ReferenciaRisco, prever_faturamento
from gih_modelo.variaveis import Amostras


def amostras(ultimo, media, caiu, em_risco) -> Amostras:
    n = len(ultimo)
    return Amostras(
        x=np.zeros((n, 1)),
        ultimo=np.asarray(ultimo, dtype=float),
        media_movel=np.asarray(media, dtype=float),
        caiu=np.asarray(caiu, dtype=bool),
        alvo=np.full(n, np.nan),
        em_risco=np.asarray(em_risco, dtype=float),
        periodo_alvo=np.zeros(n, dtype=np.int64),
        parceiro=np.arange(n),
    )


def test_as_duas_referencias_de_faturamento():
    a = amostras([100, 200], [150, 180], [False, True], [0, 0])
    assert list(prever_faturamento(a, "ultimo")) == [100, 200]
    assert list(prever_faturamento(a, "media_movel")) == [150, 180]
    with pytest.raises(ValueError):
        prever_faturamento(a, "palpite")


def test_a_referencia_de_risco_separa_quem_acabou_de_cair():
    treino = amostras([1] * 6, [1] * 6, [True, True, True, True, False, False], [1, 1, 1, 0, 0, 0])
    referencia = ReferenciaRisco.ajustar(treino)
    assert referencia.se_caiu == pytest.approx(0.75)
    assert referencia.se_nao_caiu == pytest.approx(0.0)
    assert list(referencia.prever(treino)) == [0.75] * 4 + [0.0] * 2


def test_grupo_sem_amostra_usa_a_taxa_geral_em_vez_de_zero():
    treino = amostras([1] * 4, [1] * 4, [False] * 4, [1, 0, 0, 0])
    referencia = ReferenciaRisco.ajustar(treino)
    assert referencia.se_caiu == pytest.approx(0.25)


def test_mape_em_fracao_e_sem_os_zeros():
    real = np.array([100.0, 200.0, 0.0])
    previsto = np.array([110.0, 180.0, 50.0])
    assert mape(previsto, real) == pytest.approx((0.10 + 0.10) / 2)


def test_brier():
    assert brier(np.array([1.0, 0.0]), np.array([1.0, 0.0])) == 0
    assert brier(np.array([0.5, 0.5]), np.array([1.0, 0.0])) == pytest.approx(0.25)


def test_calibracao_perfeita_tem_erro_zero_e_a_curva_diz_as_faixas():
    probabilidade = np.array([0.25] * 4 + [0.75] * 4)
    rotulo = np.array([1, 0, 0, 0, 1, 1, 1, 0], dtype=float)
    assert erro_calibracao(probabilidade, rotulo) == pytest.approx(0.0)
    curva = curva_calibracao(probabilidade, rotulo)
    assert [(f.inicio, f.observado, f.amostras) for f in curva] == [(0.2, 0.25, 4), (0.7, 0.75, 4)]


def test_confianca_demais_aparece_no_erro_de_calibracao():
    # Diz 90% para o que acontece metade das vezes.
    probabilidade = np.full(10, 0.9)
    rotulo = np.array([1, 0] * 5, dtype=float)
    assert erro_calibracao(probabilidade, rotulo) == pytest.approx(0.4)
