"""O otimizador serial contra a enumeração exata e contra o guloso (H48, H49).

O portão da H49: nas instâncias pequenas, o genético chega ao mesmo ganho que a
enumeração. E a razão de existir do genético: o guloso não chega.
"""
import pytest

from gih_nucleo import Instancia, Inviavel, avaliar, guloso, otimizar, verificar_plano
from gih_nucleo.exaustivo import otimo
from gih_nucleo.problema import SEM_CATEGORIA
from gih_nucleo.viabilidade import verificar_viabilidade
from tests.conftest import sortear_instancia, sortear_viavel

# As instâncias sorteadas que têm plano viável — as outras são testadas na
# viabilidade. Fixas pela semente: o teste é o mesmo a cada execução.
VIAVEIS = [s for s in range(120) if verificar_viabilidade(sortear_instancia(s)) is None][:40]


def test_o_guloso_erra_onde_o_genetico_acerta(mochila):
    """O contraexemplo da mochila: 115 pelo guloso, 195 pelo ótimo."""
    assert avaliar(mochila, guloso(mochila)).ganho == 115
    assert otimo(mochila)[0] == 195
    assert otimizar(mochila).avaliacao.ganho == 195


@pytest.mark.parametrize("semente", VIAVEIS)
def test_o_genetico_chega_ao_otimo_da_enumeracao(semente):
    inst = sortear_instancia(semente)
    resultado = otimizar(inst)
    assert resultado.avaliacao.ganho == otimo(inst)[0]
    assert verificar_plano(inst, resultado.genes) == []


def test_o_guloso_nao_basta_nas_instancias_sorteadas():
    """Em parte das instâncias pequenas o guloso fica abaixo do ótimo — sem isso,
    a metaheurística não se justificaria (`docs/07` §4.1)."""
    abaixo = sum(
        avaliar(sortear_instancia(s), guloso(sortear_instancia(s))).ganho
        < otimo(sortear_instancia(s))[0]
        for s in VIAVEIS
    )
    assert abaixo >= 3


def test_nunca_pior_que_o_guloso_em_instancia_maior():
    """Com 60 parceiros a enumeração não termina; a garantia que sobra é o piso."""
    inst = sortear_viavel(parceiros=60, acoes=4, categorias=3)
    resultado = otimizar(inst, geracoes=40)
    assert resultado.avaliacao.ganho >= avaliar(inst, guloso(inst)).ganho
    assert verificar_plano(inst, resultado.genes) == []


def test_a_mesma_semente_da_o_mesmo_plano():
    inst = sortear_viavel(parceiros=40, acoes=4)
    primeiro = otimizar(inst, semente=7, geracoes=30)
    segundo = otimizar(inst, semente=7, geracoes=30)
    assert primeiro.genes == segundo.genes
    assert primeiro.geracoes == segundo.geracoes == 30 * 4


def test_campanha_inviavel_e_recusada_antes_da_busca():
    inst = Instancia(
        ganho=((100,), (200,)),
        custo=(90,),
        orcamento=100,
        maximo_acoes=2,
        categoria=(0, 0),
        cauda=(False, False),
        minimo_categoria=(2,),
        maximo_categoria=(2,),
    )
    with pytest.raises(Inviavel) as erro:
        otimizar(inst)
    assert (erro.value.motivo.restricao, erro.value.motivo.falta) == ("orcamento", 80)


def test_o_limite_de_tempo_devolve_o_melhor_viavel_e_marca_parcial():
    """UC08-E2: com o relógio estourado, a busca para — e o plano continua viável."""
    inst = sortear_viavel(parceiros=30)
    instantes = iter(range(1000))
    resultado = otimizar(inst, limite_s=3, relogio=lambda: next(instantes))
    assert resultado.parcial
    assert resultado.geracoes < 150 * 4
    assert verificar_plano(inst, resultado.genes) == []


def test_sem_parceiros_elegiveis_o_plano_e_vazio():
    inst = Instancia(
        ganho=(),
        custo=(90,),
        orcamento=100,
        maximo_acoes=5,
        categoria=(),
        cauda=(),
        minimo_categoria=(),
        maximo_categoria=(),
    )
    resultado = otimizar(inst)
    assert resultado.genes == () and resultado.avaliacao.ganho == 0


def test_parametros_impossiveis_sao_recusados():
    inst = Instancia(
        ganho=((1,),),
        custo=(1,),
        orcamento=1,
        maximo_acoes=1,
        categoria=(SEM_CATEGORIA,),
        cauda=(False,),
        minimo_categoria=(),
        maximo_categoria=(),
    )
    with pytest.raises(ValueError):
        otimizar(inst, populacao=1)
