"""Spike de GPU — história H47.

Objetivo: retirar o maior risco técnico do projeto oito semanas antes de ele
ser necessário, respondendo a três perguntas:

1. Conseguimos compilar e executar um kernel CUDA nesta máquina?
2. Conseguimos invocá-lo a partir do Python?
3. O resultado bate com o cálculo equivalente em CPU?

O kernel **não é um exemplo didático**. É o protótipo da avaliação de população
que a história H54b vai precisar: dada uma população de planos candidatos, cada
um selecionando um subconjunto de parceiros, calcular o uplift e o custo de cada
plano e zerar a aptidão dos que estouram o orçamento.

Executar:  nucleo/.venv/Scripts/python.exe nucleo/spike/spike_gpu.py
"""
from __future__ import annotations

import time

import cupy as cp
import numpy as np

# Código CUDA C de verdade, compilado em tempo de execução pelo NVRTC.
KERNEL = r"""
extern "C" __global__
void avaliar_populacao(
    const float* __restrict__ uplift,   // [n] uplift esperado por parceiro
    const float* __restrict__ custo,    // [n] custo da ação por parceiro
    const unsigned char* __restrict__ populacao,  // [p * n] seleção binária
    const float orcamento,
    const int n,
    const int p,
    float* __restrict__ aptidao,        // [p] saída
    float* __restrict__ custo_total)    // [p] saída
{
    int plano = blockIdx.x * blockDim.x + threadIdx.x;
    if (plano >= p) return;

    const unsigned char* selecao = populacao + (size_t)plano * n;

    float soma_uplift = 0.0f;
    float soma_custo  = 0.0f;
    for (int i = 0; i < n; ++i) {
        if (selecao[i]) {
            soma_uplift += uplift[i];
            soma_custo  += custo[i];
        }
    }

    custo_total[plano] = soma_custo;
    // Estourou o orçamento: plano inviável não compete (RN07).
    aptidao[plano] = (soma_custo <= orcamento) ? soma_uplift : 0.0f;
}
"""

avaliar_gpu = cp.RawKernel(KERNEL, "avaliar_populacao")


def avaliar_cpu(uplift, custo, populacao, orcamento):
    """Mesmo cálculo em NumPy — é a referência de corretude."""
    soma_uplift = populacao @ uplift
    soma_custo = populacao @ custo
    aptidao = np.where(soma_custo <= orcamento, soma_uplift, 0.0).astype(np.float32)
    return aptidao, soma_custo.astype(np.float32)


def gerar_cenario(n_parceiros: int, n_planos: int, semente: int = 42):
    """Instância sintética reproduzível — nenhum dado real (regra 2.1)."""
    rng = np.random.default_rng(semente)
    uplift = rng.uniform(50, 5000, n_parceiros).astype(np.float32)
    custo = rng.uniform(20, 800, n_parceiros).astype(np.float32)
    populacao = (rng.random((n_planos, n_parceiros)) < 0.15).astype(np.uint8)
    orcamento = np.float32(custo.sum() * 0.12)
    return uplift, custo, populacao, orcamento


def medir(n_parceiros: int, n_planos: int, repeticoes: int = 5):
    uplift, custo, populacao, orcamento = gerar_cenario(n_parceiros, n_planos)

    # ---------------------------------------------------------------- CPU
    inicio = time.perf_counter()
    for _ in range(repeticoes):
        apt_cpu, cst_cpu = avaliar_cpu(uplift, custo, populacao, orcamento)
    t_cpu = (time.perf_counter() - inicio) / repeticoes

    # ---------------------------------------------------------- transferência
    cp.cuda.Stream.null.synchronize()
    inicio = time.perf_counter()
    d_uplift = cp.asarray(uplift)
    d_custo = cp.asarray(custo)
    d_pop = cp.asarray(populacao)
    cp.cuda.Stream.null.synchronize()
    t_envio = time.perf_counter() - inicio

    d_apt = cp.empty(n_planos, dtype=cp.float32)
    d_cst = cp.empty(n_planos, dtype=cp.float32)

    threads = 256
    blocos = (n_planos + threads - 1) // threads
    args = (d_uplift, d_custo, d_pop, orcamento, n_parceiros, n_planos, d_apt, d_cst)

    avaliar_gpu((blocos,), (threads,), args)  # aquece: a 1ª execução compila
    cp.cuda.Stream.null.synchronize()

    # ---------------------------------------------------------------- kernel
    inicio = time.perf_counter()
    for _ in range(repeticoes):
        avaliar_gpu((blocos,), (threads,), args)
    cp.cuda.Stream.null.synchronize()
    t_kernel = (time.perf_counter() - inicio) / repeticoes

    # ------------------------------------------------------------- retorno
    inicio = time.perf_counter()
    apt_gpu = cp.asnumpy(d_apt)
    cst_gpu = cp.asnumpy(d_cst)
    t_retorno = time.perf_counter() - inicio

    # ----------------------------------------------------------- corretude
    # float32 somado em ordem diferente não dá bit a bit igual: a GPU soma
    # sequencialmente dentro da thread, o NumPy usa BLAS. A tolerância é o que
    # importa — RNF02 aceita 2% de diferença no uplift.
    erro_max = float(np.max(np.abs(apt_cpu - apt_gpu) / np.maximum(apt_cpu, 1.0)))
    confere = np.allclose(apt_cpu, apt_gpu, rtol=1e-3) and np.allclose(cst_cpu, cst_gpu, rtol=1e-3)

    total_gpu = t_kernel + t_envio + t_retorno
    return {
        "planos": n_planos,
        "cpu_ms": t_cpu * 1000,
        "envio_ms": t_envio * 1000,
        "kernel_ms": t_kernel * 1000,
        "retorno_ms": t_retorno * 1000,
        "total_gpu_ms": total_gpu * 1000,
        "speedup_kernel": t_cpu / t_kernel,
        "speedup_total": t_cpu / total_gpu,
        "confere": confere,
        "erro_relativo_max": erro_max,
    }


def main():
    props = cp.cuda.runtime.getDeviceProperties(0)
    print(f"GPU: {props['name'].decode()} | {props['multiProcessorCount']} SMs")
    print(f"Runtime CUDA: {cp.cuda.runtime.runtimeGetVersion()}")
    print(f"Capacidade: {props['major']}.{props['minor']}\n")

    n_parceiros = 2000  # cenário de referência do RNF01
    print(f"Cenário: {n_parceiros} parceiros, população variável\n")
    print(f"{'planos':>8} {'CPU ms':>9} {'envio':>8} {'kernel':>9} {'volta':>7} "
          f"{'GPU total':>10} {'ganho kernel':>13} {'ganho total':>12}  ok")
    print("-" * 95)

    for n_planos in (256, 1024, 4096, 16384, 65536):
        r = medir(n_parceiros, n_planos)
        print(f"{r['planos']:>8} {r['cpu_ms']:>9.2f} {r['envio_ms']:>8.2f} "
              f"{r['kernel_ms']:>9.2f} {r['retorno_ms']:>7.2f} {r['total_gpu_ms']:>10.2f} "
              f"{r['speedup_kernel']:>12.1f}x {r['speedup_total']:>11.1f}x  "
              f"{'sim' if r['confere'] else 'NAO'}")

    print("\nCorretude conferida contra o cálculo equivalente em NumPy.")
    print("Diferença esperada em float32: a GPU soma sequencialmente na thread,")
    print("o NumPy usa BLAS. Tolerância de 0,1%; o RNF02 aceita 2%.")


if __name__ == "__main__":
    main()
