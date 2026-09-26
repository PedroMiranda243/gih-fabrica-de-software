"""O núcleo em C++ contra o Python: o mesmo resultado, sorteio a sorteio (H53a).

O critério de aceite da H53a é **resultado idêntico** — mesmos genes, mesma
avaliação, mesmas gerações —, e não "qualidade parecida". É o que dá sentido ao
*speedup* das versões paralelas (RNF02): elas vão reproduzir esta.

Sem o executável compilado, os testes são pulados — quem mexe só no Python não
precisa do compilador. **Na CI não**: lá `GIH_NUCLEO_OBRIGATORIO=1`, e a falta do
executável reprova.
"""
import os
import subprocess

import pytest

from gih_nucleo import Inviavel, nativo, otimizar, verificar_plano, verificar_viabilidade
from gih_nucleo.aleatorio import sorteio
from tests.conftest import sortear_instancia, sortear_viavel
from tests.test_otimizador import VIAVEIS


@pytest.fixture(scope="module")
def executavel():
    caminho = nativo.localizar()
    if caminho is None:
        if os.environ.get("GIH_NUCLEO_OBRIGATORIO") == "1":
            pytest.fail("O executável gih-nucleo não foi encontrado, e aqui ele é obrigatório.")
        pytest.skip("gih-nucleo não compilado — ver nucleo/construir.bat ou o g++ do README.")
    return caminho


def _mesmo(python, cpp):
    assert cpp.genes == python.genes
    assert cpp.avaliacao == python.avaliacao
    assert (cpp.partidas, cpp.geracoes, cpp.parcial) == (
        python.partidas,
        python.geracoes,
        python.parcial,
    )


@pytest.mark.parametrize(
    "coordenadas",
    [(42,), (42, 0, 1, 2, 3), (2**64 - 1, 7), (0,), (7, 3, 150, 47, 2003)],
)
def test_o_gerador_do_cpp_e_o_do_python(executavel, coordenadas):
    r = subprocess.run(
        [executavel, "sorteio", *map(str, coordenadas)], capture_output=True, text=True, check=True
    )
    assert int(r.stdout) == sorteio(*coordenadas)


@pytest.mark.parametrize("semente", VIAVEIS)
def test_identico_nas_instancias_pequenas(executavel, semente):
    inst = sortear_instancia(semente)
    _mesmo(otimizar(inst), nativo.otimizar(inst, executavel=executavel))


def test_identico_numa_instancia_grande(executavel):
    """300 parceiros, com cotas de categoria e de cauda: o caminho inteiro, milhares de sorteios."""
    inst = sortear_viavel(parceiros=300, acoes=5, categorias=3)
    parametros = {"semente": 7, "geracoes": 60, "partidas": 3}
    python = otimizar(inst, **parametros)
    cpp = nativo.otimizar(inst, executavel=executavel, **parametros)
    _mesmo(python, cpp)
    assert verificar_plano(inst, cpp.genes) == []


def test_a_mochila(executavel, mochila):
    assert nativo.otimizar(mochila, executavel=executavel).avaliacao.ganho == 195


def test_a_recusa_e_a_mesma(executavel):
    """A viabilidade decidida pelo C++ é a do Python: mesma restrição, exigido e disponível."""
    inviaveis = 0
    for semente in range(150):
        inst = sortear_instancia(semente)
        esperado = verificar_viabilidade(inst)
        if esperado is None:
            continue
        inviaveis += 1
        with pytest.raises(Inviavel) as erro:
            nativo.otimizar(inst, executavel=executavel, geracoes=1)
        assert erro.value.motivo == esperado
    assert inviaveis > 20


def test_parametro_impossivel_e_recusado_como_no_python(executavel, mochila):
    with pytest.raises(ValueError):
        nativo.otimizar(mochila, executavel=executavel, populacao=1)


def test_o_limite_de_tempo_devolve_viavel_e_marca_parcial(executavel):
    inst = sortear_viavel(parceiros=300, acoes=5, categorias=3)
    r = nativo.otimizar(inst, executavel=executavel, geracoes=1_000_000, limite_s=0.05)
    assert r.parcial
    assert verificar_plano(inst, r.genes) == []


def test_sem_executavel_a_chamada_diz_por_que(mochila, monkeypatch):
    monkeypatch.delenv("GIH_NUCLEO", raising=False)
    monkeypatch.setattr(nativo, "localizar", lambda: None)
    with pytest.raises(nativo.NucleoIndisponivel):
        nativo.otimizar(mochila)
