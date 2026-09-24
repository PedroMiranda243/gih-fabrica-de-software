"""As variáveis e a separação no tempo — H41."""
from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from gih_modelo import JANELA, PERIODOS_MINIMOS, Serie, colunas
from gih_modelo.variaveis import NUMERICAS, atuais, montar, separar_no_tempo, vocabulario


def serie(parceiro=1, faturamento=(100, 100, 100, 100, 100), inicio=0, categoria="Pizzaria"):
    n = len(faturamento)
    return Serie(
        parceiro=parceiro,
        categoria=categoria,
        periodos=tuple(range(inicio, inicio + n)),
        faturamento=tuple(float(f) for f in faturamento),
        pedidos=tuple(10 for _ in range(n)),
        em_risco=tuple(False for _ in range(n)),
    )


def coluna(nome: str) -> int:
    return NUMERICAS.index(nome)


def test_os_minimos_sao_os_da_rn09():
    # Quatro de janela; dois de treino, um de validação e um de teste.
    assert JANELA == 4
    assert PERIODOS_MINIMOS == 8


def test_uma_amostra_por_periodo_com_janela_completa_antes(rede):
    amostras = montar(rede, vocabulario(rede))
    esperado = sum(max(0, len(s.periodos) - JANELA) for s in rede)
    assert len(amostras) == esperado
    assert amostras.x.shape == (esperado, len(colunas(vocabulario(rede))))


def test_faturamento_constante_nao_tem_variacao_nem_tendencia():
    amostras = montar([serie()], ("Pizzaria",))
    assert len(amostras) == 1
    x = amostras.x[0]
    for nome in ("faturamento_t-4", "faturamento_t-3", "faturamento_t-2", "tendencia"):
        assert x[coluna(nome)] == pytest.approx(0.0)
    assert amostras.ultimo[0] == 100
    assert amostras.media_movel[0] == 100
    assert not amostras.caiu[0]


def test_a_janela_e_relativa_ao_ultimo_periodo_e_a_tendencia_tem_sinal():
    subindo = montar([serie(faturamento=(100, 200, 400, 800, 900))], ("Pizzaria",)).x[0]
    assert subindo[coluna("faturamento_t-4")] == pytest.approx(np.log(100 / 800))
    assert subindo[coluna("tendencia")] > 0

    caindo = montar([serie(faturamento=(800, 400, 200, 100, 50))], ("Pizzaria",))
    assert caindo.x[0, coluna("tendencia")] < 0
    assert caindo.caiu[0]


def test_posicao_e_o_percentil_dentro_do_proprio_periodo():
    series = [serie(1, (100,) * 5), serie(2, (300,) * 5), serie(3, (200,) * 5)]
    amostras = montar(series, ("Pizzaria",))
    posicao = dict(zip(amostras.parceiro, amostras.x[:, coluna("posicao")], strict=True))
    assert posicao == {1: 0.0, 2: 1.0, 3: 0.5}


def test_faturamento_zero_nao_quebra_o_logaritmo():
    amostras = montar([serie(faturamento=(0, 0, 100, 0, 50))], ("Pizzaria",))
    assert np.isfinite(amostras.x).all()


def test_categoria_fora_do_vocabulario_cai_na_ultima_coluna():
    vocab = ("Padaria", "Pizzaria")
    conhecida = montar([serie(categoria="Pizzaria")], vocab).x[0]
    nova = montar([serie(categoria="Açaí")], vocab).x[0]
    sem = montar([serie(categoria=None)], vocab).x[0]
    n = len(NUMERICAS)
    assert list(conhecida[n:]) == [0, 1, 0]
    assert list(nova[n:]) == [0, 0, 1]
    assert list(sem[n:]) == [0, 0, 1]


def test_a_separacao_e_por_tempo(rede):
    separacao = separar_no_tempo(montar(rede, vocabulario(rede)))
    ultimo = max(p for s in rede for p in s.periodos)
    assert set(separacao.teste.periodo_alvo) == {ultimo}
    assert set(separacao.validacao.periodo_alvo) == {ultimo - 1}
    assert separacao.treino.periodo_alvo.max() == ultimo - 2


def _embaralhar_periodo(series: list[Serie], periodo: int) -> list[Serie]:
    """A mesma rede com os números de um período trocados por outros."""
    rng = np.random.default_rng(7)
    novas = []
    for s in series:
        fat = list(s.faturamento)
        risco = list(s.em_risco)
        if periodo in s.periodos:
            i = s.periodos.index(periodo)
            fat[i] = float(rng.uniform(50, 90_000))
            risco[i] = not risco[i]
        novas.append(replace(s, faturamento=tuple(fat), em_risco=tuple(risco)))
    return novas


@pytest.mark.parametrize("parte", ["teste", "validacao"])
def test_nenhuma_amostra_anterior_enxerga_o_periodo_seguinte(rede, parte):
    """O critério da H41: mudar o que acontece no período de teste (ou no de
    validação) não pode mudar nada do que vem antes dele."""
    ultimo = max(p for s in rede for p in s.periodos)
    periodo = ultimo if parte == "teste" else ultimo - 1
    vocab = vocabulario(rede)
    antes = separar_no_tempo(montar(rede, vocab))
    depois = separar_no_tempo(montar(_embaralhar_periodo(rede, periodo), vocab))

    anteriores = ["treino", "validacao"] if parte == "teste" else ["treino"]
    for nome in anteriores:
        a, b = getattr(antes, nome), getattr(depois, nome)
        np.testing.assert_array_equal(a.x, b.x)
        np.testing.assert_array_equal(a.alvo, b.alvo)
        np.testing.assert_array_equal(a.em_risco, b.em_risco)
    # E a mudança chegou de fato ao período mexido — senão o teste não prova nada.
    assert not np.array_equal(getattr(antes, parte).alvo, getattr(depois, parte).alvo)


def test_a_extracao_e_reproduzivel(rede):
    vocab = vocabulario(rede)
    np.testing.assert_array_equal(montar(rede, vocab).x, montar(rede, vocab).x)


def test_as_janelas_atuais_terminam_no_ultimo_periodo_do_parceiro():
    curta = serie(1, (100, 100, 100))  # 3 períodos: menos que a janela
    exata = serie(2, (100, 200, 300, 400))
    longa = serie(3, (400, 300, 200, 100, 50, 60))
    amostras = atuais([curta, exata, longa], ("Pizzaria",))
    assert list(amostras.parceiro) == [2, 3]
    assert list(amostras.ultimo) == [400, 60]
    assert amostras.media_movel[1] == pytest.approx((200 + 100 + 50 + 60) / 4)
    assert (amostras.periodo_alvo == -1).all()


def test_serie_recusa_tamanhos_diferentes_e_periodos_fora_de_ordem():
    with pytest.raises(ValueError, match="tamanhos"):
        Serie(1, None, (0, 1), (1.0,), (1, 1), (False, False))
    with pytest.raises(ValueError, match="ordem"):
        Serie(1, None, (1, 0), (1.0, 2.0), (1, 1), (False, False))


def test_importar_o_pacote_nao_carrega_o_pytorch():
    """A API importa o pacote a cada subida; o PyTorch só pode vir quando se
    treina ou prevê."""
    import subprocess
    import sys

    codigo = "import sys, gih_modelo; print('torch' in sys.modules)"
    saida = subprocess.run([sys.executable, "-c", codigo], capture_output=True, text=True)
    assert saida.stdout.strip() == "False", saida.stderr
