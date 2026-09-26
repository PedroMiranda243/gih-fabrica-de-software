"""A GPU do núcleo: achar a placa, recusar sem ela, a ida e volta e o kernel (H54a, H54b, H56).

A ida e volta e o kernel só rodam com GPU; na CI, sem placa nem CUDA, eles pulam
— exceto com `GIH_GPU_OBRIGATORIA=1`, que reprova. **A recusa roda em qualquer máquina**:
onde há placa, ela é escondida (`CUDA_VISIBLE_DEVICES=-1`), e o executável
precisa responder como numa máquina sem ela — saída 1, com o motivo. É o sinal
que a API usa para cair para a CPU (RNF06).
"""
import os
import random
import subprocess

import pytest

from gih_nucleo import avaliar, nativo, verificar_viabilidade
from tests.conftest import sortear_instancia, sortear_viavel

ESCONDIDA = {**os.environ, "CUDA_VISIBLE_DEVICES": "-1"}


@pytest.fixture(scope="module")
def gpu(executavel):
    """O executável, desde que ache uma GPU."""
    if nativo.capacidades(executavel).gpu is None:
        if os.environ.get("GIH_GPU_OBRIGATORIA") == "1":
            pytest.fail("Sem GPU, e aqui ela é obrigatória.")
        pytest.skip("Sem GPU nesta máquina, ou gih-nucleo compilado sem CUDA.")
    return executavel


def test_a_versao_diz_a_gpu_ou_por_que_nao_ha(executavel):
    c = nativo.capacidades(executavel)
    assert (c.gpu is None) != (c.sem_gpu is None)
    assert (c.sem_gpu is None) == (c.ausencia_gpu is None)
    if c.gpu:
        assert c.gpu.nome and c.gpu.memoria_mib > 0
    else:
        assert c.ausencia_gpu in ("sem_cuda", "sem_placa", "erro")


def test_sem_placa_o_executavel_recusa_com_saida_1(executavel):
    r = subprocess.run([executavel, "gpu"], capture_output=True, text=True, env=ESCONDIDA)
    assert r.returncode == 1
    assert r.stderr.strip()  # o motivo, para quem investiga
    versao = subprocess.run([executavel, "versao"], capture_output=True, text=True, env=ESCONDIDA)
    linha = next(x for x in versao.stdout.splitlines() if x.startswith("gpu "))
    # Com CUDA, a placa escondida é "sem placa"; sem CUDA, como na CI, é "sem CUDA".
    assert linha.split()[:3] in (["gpu", "0", "sem_placa"], ["gpu", "0", "sem_cuda"])


def test_sem_placa_a_ida_e_volta_levanta_sem_gpu(executavel, monkeypatch):
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "-1")
    with pytest.raises(nativo.SemGpu):
        nativo.transferir(sortear_viavel(parceiros=20), executavel=executavel, repeticoes=1)


def test_a_ida_e_volta_recusa_campanha_inviavel_e_parametro_impossivel(executavel):
    inviavel = next(
        i for i in map(sortear_instancia, range(200)) if verificar_viabilidade(i)
    )
    with pytest.raises(ValueError):
        nativo.transferir(inviavel, executavel=executavel)
    with pytest.raises(ValueError):
        nativo.transferir(sortear_viavel(parceiros=20), executavel=executavel, repeticoes=0)


@pytest.mark.parametrize("parceiros", [1, 40, 300, 2000])
def test_a_instancia_e_a_populacao_vao_e_voltam_iguais(gpu, parceiros):
    """O executável confere byte a byte, e com uma conta feita na própria GPU; se não
    bater, ele sai como defeito, e a chamada levanta `NucleoFalhou`."""
    inst = sortear_viavel(parceiros=parceiros, acoes=5, categorias=3)
    t = nativo.transferir(inst, executavel=gpu, partidas=3, populacao=10, repeticoes=3)

    n, a, k = inst.parceiros, inst.acoes, inst.categorias
    assert t.bytes_populacao == 3 * 10 * n  # um byte por gene
    assert t.bytes_instancia == 8 * n * a + 8 * a + 4 * n + n + 2 * 8 * k
    assert len(t.envio_ms) == len(t.volta_ms) == len(t.volta_um_ms) == 3
    assert all(x > 0 for x in t.envio_ms + t.volta_ms + t.volta_um_ms)
    assert t.dispositivo.nome


# ------------------------------------------------------------ o kernel (H54b)
def _populacao(inst, semente, individuos=40):
    """Os extremos — ninguém com ação, todos com a última, todos com a primeira — e o
    resto sorteado, com densidade de ação de 0 a 100%."""
    rng = random.Random(semente)
    n, a = inst.parceiros, inst.acoes
    extremos = [(0,) * n, (a,) * n, (1,) * n]
    sorteados = [
        tuple(rng.randint(1, a) if rng.random() < densidade else 0 for _ in range(n))
        for densidade in (rng.random() for _ in range(individuos - len(extremos)))
    ]
    return extremos + sorteados


@pytest.mark.parametrize("parceiros", [1, 7, 300, 2000])
def test_o_kernel_avalia_como_o_python(gpu, parceiros):
    """Ganho, custo, ações, cauda, contagem por categoria e violação, indivíduo a
    indivíduo, contra o `avaliar` do Python — a referência de tudo (ADR-011)."""
    inst = sortear_viavel(parceiros=parceiros, acoes=5, categorias=3)
    populacao = _populacao(inst, parceiros)
    r = nativo.avaliar_na_gpu(inst, populacao, executavel=gpu, repeticoes=2)
    assert list(r.avaliacoes) == [avaliar(inst, genes) for genes in populacao]
    assert len(r.kernel_ms) == len(r.cpu_ms) == 2


def test_o_kernel_nas_campanhas_sorteadas_viaveis_ou_nao(gpu):
    """As 60 campanhas pequenas dos testes do Python, muitas inviáveis: cada termo da
    violação — máximo de ações, cauda, mínimo e máximo de categoria, orçamento —
    aparece em alguma, e precisa sair igual."""
    termos_vistos = set()
    for semente in range(60):
        inst = sortear_instancia(semente)
        populacao = _populacao(inst, semente, individuos=20)
        r = nativo.avaliar_na_gpu(inst, populacao, executavel=gpu, repeticoes=1)
        esperadas = [avaliar(inst, genes) for genes in populacao]
        assert list(r.avaliacoes) == esperadas, f"campanha {semente}"
        for av in esperadas:
            if av.acoes > inst.maximo_acoes:
                termos_vistos.add("máximo de ações")
            if av.cauda < inst.minimo_cauda:
                termos_vistos.add("cauda")
            if av.custo > inst.orcamento:
                termos_vistos.add("orçamento")
            for k, n in enumerate(av.por_categoria):
                if n < inst.minimo_categoria[k]:
                    termos_vistos.add("mínimo de categoria")
                if n > inst.maximo_categoria[k]:
                    termos_vistos.add("máximo de categoria")
    assert len(termos_vistos) == 5, termos_vistos


def test_o_kernel_sem_categoria(gpu):
    inst = sortear_viavel(parceiros=50, acoes=3, categorias=0)
    populacao = _populacao(inst, 3, individuos=10)
    r = nativo.avaliar_na_gpu(inst, populacao, executavel=gpu, repeticoes=1)
    assert list(r.avaliacoes) == [avaliar(inst, genes) for genes in populacao]
    assert all(av.por_categoria == () for av in r.avaliacoes)


def test_avaliar_recusa_gene_fora_do_catalogo(executavel):
    inst = sortear_viavel(parceiros=5, acoes=2)
    with pytest.raises(ValueError):
        nativo.avaliar_na_gpu(inst, [(0, 1, 2, 3, 0)], executavel=executavel)


def test_sem_placa_avaliar_levanta_sem_gpu(executavel, monkeypatch):
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "-1")
    inst = sortear_viavel(parceiros=5, acoes=2)
    with pytest.raises(nativo.SemGpu):
        nativo.avaliar_na_gpu(inst, [(0, 1, 2, 1, 0)], executavel=executavel)
