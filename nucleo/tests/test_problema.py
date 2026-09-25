"""A instância, a avaliação e o verificador independente (RN07)."""
import random

import pytest

from gih_nucleo import SEM_CATEGORIA, Instancia, InstanciaInvalida, avaliar, verificar_plano
from gih_nucleo.problema import melhor
from tests.conftest import sortear_instancia


def _instancia(**mudancas):
    base = {
        "ganho": ((100, 300), (200, 250), (50, 400)),
        "custo": (10, 30),
        "orcamento": 60,
        "maximo_acoes": 2,
        "categoria": (0, 0, SEM_CATEGORIA),
        "cauda": (False, True, True),
        "minimo_categoria": (1,),
        "maximo_categoria": (1,),
        "minimo_cauda": 1,
    }
    return Instancia(**{**base, **mudancas})


@pytest.mark.parametrize(
    "mudanca",
    [
        {"custo": (0, 30)},
        {"custo": ()},
        {"ganho": ((100,), (200, 250), (50, 400))},
        {"ganho": ((-1, 300), (200, 250), (50, 400))},
        {"categoria": (0, 1, SEM_CATEGORIA)},
        {"cauda": (False, True)},
        {"orcamento": -1},
        {"maximo_categoria": (1, 2)},
    ],
)
def test_instancia_impossivel_e_recusada(mudanca):
    with pytest.raises(InstanciaInvalida):
        _instancia(**mudanca)


def test_avaliar_soma_e_conta():
    inst = _instancia()
    av = avaliar(inst, [0, 2, 1])  # parceiro 1 na ação 1, parceiro 2 na ação 0
    assert (av.ganho, av.custo, av.acoes, av.por_categoria, av.cauda) == (300, 40, 2, (1,), 2)
    assert av.viavel


def test_excesso_de_orcamento_conta_em_acoes_da_mais_barata_arredondado_para_cima():
    """ADR-011: a violação é inteira e em unidades de ação."""
    inst = _instancia(orcamento=55, minimo_categoria=(0,), minimo_cauda=0)
    av = avaliar(inst, [0, 2, 2])  # custo 60: passa 5 do orçamento, e a mais barata custa 10
    assert av.custo == 60
    assert av.violacao == 1


def test_cada_restricao_soma_na_violacao():
    inst = _instancia()
    # 3 ações (1 acima de K), 2 na categoria 0 (1 acima do máximo), custo 70 (1 ação acima)
    assert avaliar(inst, [2, 1, 2]).violacao == 3


def test_viavel_vence_inviavel_e_entre_viaveis_vence_o_maior_ganho():
    inst = _instancia()
    viavel = avaliar(inst, [0, 2, 1])
    pior = avaliar(inst, [1, 0, 1])
    inviavel = avaliar(inst, [2, 2, 2])
    assert melhor(viavel, inviavel) and not melhor(inviavel, viavel)
    assert melhor(viavel, pior) and not melhor(pior, viavel)
    assert not melhor(viavel, viavel)  # empate não é "melhor": fica o de menor índice


def test_verificador_nomeia_cada_restricao_violada():
    inst = _instancia()
    problemas = verificar_plano(inst, [2, 1, 2])
    assert any(p.startswith("orçamento") for p in problemas)
    assert any(p.startswith("máximo de ações") for p in problemas)
    assert any(p.startswith("categoria 0") for p in problemas)
    assert verificar_plano(inst, [0, 2, 1]) == []
    assert verificar_plano(inst, [0, 0, 0]) == [
        "categoria 0: 0 ações, o mínimo é 1",
        "cauda longa: 0 ações, o mínimo é 1",
    ]


def test_verificador_recusa_plano_malformado():
    inst = _instancia()
    assert verificar_plano(inst, [0, 0]) != []
    assert verificar_plano(inst, [0, 0, 3]) != []


def test_verificador_e_avaliacao_concordam_em_planos_sorteados():
    """Duas implementações independentes: onde uma vê plano viável, a outra também."""
    rng = random.Random(7)
    for semente in range(40):
        inst = sortear_instancia(semente)
        for _ in range(50):
            genes = [
                rng.randint(0, inst.acoes) if rng.random() < 0.4 else 0
                for _ in range(inst.parceiros)
            ]
            assert avaliar(inst, genes).viavel == (verificar_plano(inst, genes) == [])
