"""O gerador sem estado (ADR-011).

Os valores fixados aqui são o contrato entre as três versões do otimizador: o
C++ e o CUDA precisam reproduzi-los antes de qualquer outra coisa.
"""
from gih_nucleo.aleatorio import MASCARA, encadear, mistura, sorteio

OURO = 0x9E3779B97F4A7C15


def test_mistura_e_o_splitmix64_publicado():
    """As três primeiras saídas do SplitMix64 com semente 0, como publicadas.

    Confere a implementação contra uma fonte externa, e não contra ela mesma.
    """
    saidas = [mistura((k * OURO) & MASCARA) for k in range(3)]
    assert saidas == [0xE220A8397B1DCDAF, 0x6E789E6AA1B965F4, 0x06C45D188009454F]


def test_sorteio_encadeia_as_coordenadas():
    esperado = 0
    for c in (42, 0, 1, 2, 3):
        esperado = encadear(esperado, c)
    assert sorteio(42, 0, 1, 2, 3) == esperado


def test_valores_de_referencia_para_o_cpp_e_o_cuda():
    assert sorteio(42) == 0xBDD732262FEB6E95
    assert sorteio(42, 0, 1, 2, 3) == 0xEBE899E363E9817A
    assert sorteio(2**64 - 1, 7) == 0x19F20A9BB46150B6


def test_coordenada_maior_que_64_bits_e_truncada_como_no_cpp():
    """Em C++ e CUDA a coordenada é `uint64_t`: o que passa de 64 bits some."""
    assert sorteio(2**64 + 5) == sorteio(5)


def test_coordenadas_vizinhas_dao_numeros_sem_relacao():
    vizinhos = {sorteio(42, 0, 1, j) for j in range(1000)}
    assert len(vizinhos) == 1000
    assert all(0 <= v <= MASCARA for v in vizinhos)
