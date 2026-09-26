"""O núcleo em C++ contra o Python: o mesmo resultado, sorteio a sorteio (H53a, H53b).

O critério de aceite da H53a é **resultado idêntico** — mesmos genes, mesma
avaliação, mesmas gerações —, e não "qualidade parecida". É o que dá sentido ao
*speedup* das versões paralelas (RNF02): elas reproduzem esta. A versão OpenMP
(H53b) é conferida do mesmo jeito, e com vários números de threads: um defeito
de corrida costuma aparecer só com uma divisão de trabalho que ninguém testou.

Sem o executável compilado, os testes são pulados — quem mexe só no Python não
precisa do compilador. **Na CI não**: lá `GIH_NUCLEO_OBRIGATORIO=1`, e a falta do
executável, ou do modo OpenMP nele, reprova.
"""
import os
import subprocess

import pytest

from gih_nucleo import Instancia, Inviavel, nativo, otimizar, verificar_plano, verificar_viabilidade
from gih_nucleo.aleatorio import sorteio
from tests.conftest import sortear_instancia, sortear_viavel
from tests.test_otimizador import VIAVEIS

OBRIGATORIO = os.environ.get("GIH_NUCLEO_OBRIGATORIO") == "1"


@pytest.fixture(scope="module")
def executavel():
    caminho = nativo.localizar()
    if caminho is None:
        if OBRIGATORIO:
            pytest.fail("O executável gih-nucleo não foi encontrado, e aqui ele é obrigatório.")
        pytest.skip("gih-nucleo não compilado — ver nucleo/construir.bat ou o g++ do README.")
    return caminho


@pytest.fixture(scope="module")
def openmp(executavel):
    """O executável, desde que compilado com OpenMP."""
    if "openmp" not in nativo.capacidades(executavel).modos:
        if OBRIGATORIO:
            pytest.fail("O gih-nucleo foi compilado sem OpenMP, e aqui o modo é obrigatório.")
        pytest.skip("gih-nucleo compilado sem OpenMP — ver nucleo/construir.bat ou o README.")
    return executavel


@pytest.fixture(scope="module")
def grande():
    """300 parceiros, com cotas de categoria e de cauda: o caminho inteiro, milhares de sorteios."""
    inst = sortear_viavel(parceiros=300, acoes=5, categorias=3)
    parametros = {"semente": 7, "geracoes": 60, "partidas": 3}
    return inst, parametros, otimizar(inst, **parametros)


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


def test_identico_numa_instancia_grande(executavel, grande):
    inst, parametros, python = grande
    cpp = nativo.otimizar(inst, executavel=executavel, **parametros)
    _mesmo(python, cpp)
    assert verificar_plano(inst, cpp.genes) == []


def test_a_mochila(executavel, mochila):
    assert nativo.otimizar(mochila, executavel=executavel).avaliacao.ganho == 195


@pytest.mark.parametrize("modo", nativo.MODOS)
def test_a_recusa_e_a_mesma(executavel, modo):
    """A viabilidade decidida pelo C++ é a do Python: mesma restrição, exigido e disponível."""
    if modo == "openmp" and "openmp" not in nativo.capacidades(executavel).modos:
        pytest.skip("gih-nucleo compilado sem OpenMP.")
    inviaveis = 0
    for semente in range(150):
        inst = sortear_instancia(semente)
        esperado = verificar_viabilidade(inst)
        if esperado is None:
            continue
        inviaveis += 1
        with pytest.raises(Inviavel) as erro:
            nativo.otimizar(inst, executavel=executavel, geracoes=1, modo=modo)
        assert erro.value.motivo == esperado
    assert inviaveis > 20


def test_o_executavel_diz_seus_modos(executavel):
    capacidades = nativo.capacidades(executavel)
    assert capacidades.modos[0] == "serial"
    assert set(capacidades.modos) <= set(nativo.MODOS)
    assert ("openmp" in capacidades.modos) == (capacidades.threads > 0)


# ------------------------------------------------------------ OpenMP (H53b)
@pytest.mark.parametrize("semente", VIAVEIS)
def test_openmp_identico_nas_instancias_pequenas(openmp, semente):
    inst = sortear_instancia(semente)
    _mesmo(otimizar(inst), nativo.otimizar(inst, executavel=openmp, modo="openmp"))


# O escalonamento é dinâmico: a thread que calcula cada filho muda de uma
# execução para outra, e 3 e 7 nem dividem os 3 × 47 filhos em partes iguais.
# Com 1, tudo sai na ordem da serial. Se a ordem de cálculo vazasse para o
# resultado, alguma destas execuções mudaria o plano.
@pytest.mark.parametrize("threads", [1, 2, 3, 7, None])
def test_openmp_identico_com_qualquer_numero_de_threads(openmp, grande, threads):
    inst, parametros, python = grande
    cpp = nativo.otimizar(inst, executavel=openmp, modo="openmp", threads=threads, **parametros)
    _mesmo(python, cpp)
    assert verificar_plano(inst, cpp.genes) == []
    assert cpp.threads == (threads or nativo.capacidades(openmp).threads)
    assert python.threads == 1


# Um processador de 2 núcleos com SMT: quatro threads lógicas, dois pares
# (processador físico, núcleo). Recortado de um /proc/cpuinfo de verdade.
CPUINFO = "\n\n".join(
    f"processor\t: {p}\nmodel name\t: Processador de teste\nphysical id\t: 0\n"
    f"siblings\t: 4\ncore id\t\t: {nucleo}\ncpu cores\t: 2"
    for p, nucleo in enumerate([0, 1, 0, 1])
)


@pytest.mark.parametrize(
    "cpuinfo, permitidos, esperado",
    [
        (CPUINFO, None, 2),
        (CPUINFO, {0, 1, 2, 3}, 2),
        (CPUINFO, {0, 2}, 1),  # o contêiner limitado às duas threads do núcleo 0
        (CPUINFO.replace("core id", "outro campo"), None, None),  # sem o campo: não se sabe
        ("", None, None),
    ],
)
def test_os_nucleos_fisicos_contam_os_pares_distintos(cpuinfo, permitidos, esperado):
    """A API pede uma thread por núcleo físico (adendo da ADR-011), e não por thread lógica."""
    assert nativo.contar_nucleos(cpuinfo, permitidos) == esperado


def test_openmp_na_mochila_e_sem_parceiros(openmp, mochila):
    assert nativo.otimizar(mochila, executavel=openmp, modo="openmp").avaliacao.ganho == 195
    vazia = Instancia((), (100,), 1000, 5, (), (), (), (), 0)
    _mesmo(otimizar(vazia), nativo.otimizar(vazia, executavel=openmp, modo="openmp"))


def test_openmp_com_limite_de_tempo_devolve_viavel_e_marca_parcial(openmp):
    inst = sortear_viavel(parceiros=300, acoes=5, categorias=3)
    r = nativo.otimizar(inst, executavel=openmp, modo="openmp", geracoes=1_000_000, limite_s=0.05)
    assert r.parcial
    assert verificar_plano(inst, r.genes) == []
    # Aqui as partidas avançam juntas e param juntas; na serial, a interrompida
    # é a última começada.
    assert r.partidas == 4
    assert r.geracoes % 4 == 0


@pytest.mark.parametrize(
    "pedido",
    [
        {"modo": "cuda"},  # ainda não existe (H54)
        {"modo": "serial", "threads": 4},  # aceitar e ignorar faria a medição mentir
        {"modo": "openmp", "threads": 0},
    ],
)
def test_modo_ou_threads_impossiveis_sao_recusados(executavel, mochila, pedido):
    with pytest.raises(ValueError):
        nativo.otimizar(mochila, executavel=executavel, **pedido)


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
