"""A recusa de campanha inviável (H52, RF31, RN07)."""
import pytest

from gih_nucleo import SEM_CATEGORIA, Instancia, Inviavel, verificar_viabilidade
from gih_nucleo import viabilidade as v
from gih_nucleo.exaustivo import otimo
from gih_nucleo.viabilidade import conjunto_minimo
from tests.conftest import sortear_instancia


def _instancia(**mudancas):
    """Duas categorias; cauda longa nos parceiros 1, 3 e 4; ações de 260 e 90 centavos."""
    base = {
        "ganho": tuple((100 + i, 400 + i) for i in range(6)),
        "custo": (260, 90),
        "orcamento": 10_000,
        "maximo_acoes": 6,
        "categoria": (0, 0, 1, 1, SEM_CATEGORIA, 0),
        "cauda": (False, True, False, True, True, False),
        "minimo_categoria": (0, 0),
        "maximo_categoria": (6, 6),
        "minimo_cauda": 0,
    }
    return Instancia(**{**base, **mudancas})


def test_campanha_sem_cotas_e_viavel():
    assert verificar_viabilidade(_instancia()) is None


def test_minimo_maior_que_o_maximo_da_categoria():
    motivo = verificar_viabilidade(_instancia(minimo_categoria=(3, 0), maximo_categoria=(2, 6)))
    assert (motivo.restricao, motivo.categoria, motivo.exigido, motivo.disponivel) == (
        v.COTA_CATEGORIA,
        0,
        3,
        2,
    )


def test_categoria_com_menos_elegiveis_que_o_minimo():
    motivo = verificar_viabilidade(_instancia(minimo_categoria=(0, 3)))
    assert (motivo.restricao, motivo.categoria, motivo.exigido, motivo.disponivel) == (
        v.ELEGIVEIS_CATEGORIA,
        1,
        3,
        2,
    )
    assert motivo.falta == 1


def test_cauda_longa_que_nao_cabe_nas_cotas():
    """Três parceiros de cauda longa, mas as categorias 0 e 1 não admitem nenhum: sobra um."""
    motivo = verificar_viabilidade(_instancia(minimo_cauda=3, maximo_categoria=(0, 0)))
    assert (motivo.restricao, motivo.exigido, motivo.disponivel) == (v.CAUDA_LONGA, 3, 1)


def test_minimos_que_somam_mais_que_o_maximo_de_acoes():
    motivo = verificar_viabilidade(_instancia(minimo_categoria=(2, 2), maximo_acoes=3))
    assert (motivo.restricao, motivo.exigido, motivo.disponivel) == (v.MAXIMO_ACOES, 4, 3)


def test_minimos_que_o_orcamento_nao_paga_nem_com_a_acao_mais_barata():
    """Quatro ações obrigatórias a 90 centavos são 360; o orçamento é 300."""
    motivo = verificar_viabilidade(_instancia(minimo_categoria=(2, 2), orcamento=300))
    assert (motivo.restricao, motivo.exigido, motivo.disponivel) == (v.ORCAMENTO, 360, 300)
    assert motivo.falta == 60


def test_a_cauda_longa_cobre_o_minimo_da_categoria_e_conta_duas_vezes():
    """Mínimo de 1 na categoria 1 e de 1 na cauda: o parceiro 3 cumpre os dois sozinho."""
    assert conjunto_minimo(_instancia(minimo_categoria=(0, 1), minimo_cauda=1)) == [3]


def test_conjunto_minimo_levanta_inviavel_com_o_motivo():
    with pytest.raises(Inviavel) as erro:
        conjunto_minimo(_instancia(minimo_categoria=(2, 2), orcamento=300))
    assert erro.value.motivo.restricao == v.ORCAMENTO


def test_a_verificacao_e_exata():
    """Viável pela verificação se, e somente se, a enumeração acha um plano viável.

    Nas instâncias sorteadas há dos dois casos: sem os dois lados, o teste não
    provaria nada.
    """
    viaveis = inviaveis = 0
    for semente in range(150):
        inst = sortear_instancia(semente)
        tem_plano = otimo(inst) is not None
        assert (verificar_viabilidade(inst) is None) == tem_plano, semente
        viaveis += tem_plano
        inviaveis += not tem_plano
    assert viaveis > 20 and inviaveis > 20
