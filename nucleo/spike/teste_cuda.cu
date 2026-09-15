// Spike de CUDA compilado por nvcc — história H47, parte GPU.
//
// É o mesmo kernel que o spike em Python já validou por NVRTC. Reescrevê-lo
// aqui responde a outra pergunta: a cadeia nvcc + MSVC funciona nesta máquina,
// que é o que as histórias H54a a H54c vão exigir.
//
// A referência de corretude é o cálculo equivalente em CPU, no mesmo processo.

#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdint>
#include <vector>

#include <cuda_runtime.h>

#define CHECAR(chamada)                                                        \
    do {                                                                       \
        cudaError_t erro = (chamada);                                          \
        if (erro != cudaSuccess) {                                             \
            std::printf("CUDA falhou em %s:%d -> %s\n", __FILE__, __LINE__,    \
                        cudaGetErrorString(erro));                             \
            return 1;                                                          \
        }                                                                      \
    } while (0)

__global__ void avaliar_populacao(const float* __restrict__ uplift,
                                  const float* __restrict__ custo,
                                  const uint8_t* __restrict__ populacao,
                                  const float orcamento, const int n, const int p,
                                  float* __restrict__ aptidao,
                                  float* __restrict__ custo_total) {
    const int plano = blockIdx.x * blockDim.x + threadIdx.x;
    if (plano >= p) return;

    const uint8_t* selecao = populacao + static_cast<size_t>(plano) * n;

    float soma_uplift = 0.0f;
    float soma_custo = 0.0f;
    for (int i = 0; i < n; ++i) {
        if (selecao[i]) {
            soma_uplift += uplift[i];
            soma_custo += custo[i];
        }
    }

    custo_total[plano] = soma_custo;
    // Estourou o orçamento: plano inviável não compete (RN07).
    aptidao[plano] = (soma_custo <= orcamento) ? soma_uplift : 0.0f;
}

namespace {

uint32_t proximo(uint32_t& estado) {
    estado ^= estado << 13;
    estado ^= estado >> 17;
    estado ^= estado << 5;
    return estado;
}

float uniforme(uint32_t& estado, float a, float b) {
    return a + (b - a) * (proximo(estado) / 4294967296.0f);
}

// Tempo médio de uma execução de `acao`, com `finalizar` chamado uma vez ao fim
// para fechar o trabalho assíncrono antes de parar o cronômetro.
//
// Repetição fixa não serve: o kernel roda em fração de milissegundo e a medição
// viraria ruído de relógio. Calibra quantas repetições cabem no alvo e só então
// mede.
//
// `finalizar` fora do laço é deliberado: nas histórias H54a–H54c a população
// permanece na GPU entre gerações, então o que interessa é a vazão de lançamentos
// encadeados, não o custo de sincronizar a cada geração.
template <typename F, typename G>
double medir(F acao, G finalizar, double alvo_ms = 300.0) {
    acao();
    finalizar();

    auto inicio = std::chrono::steady_clock::now();
    acao();
    finalizar();
    auto fim = std::chrono::steady_clock::now();
    const double uma = std::chrono::duration<double, std::milli>(fim - inicio).count();

    int repeticoes = static_cast<int>(alvo_ms / (uma > 0.001 ? uma : 0.001));
    if (repeticoes < 3) repeticoes = 3;
    if (repeticoes > 20000) repeticoes = 20000;

    inicio = std::chrono::steady_clock::now();
    for (int r = 0; r < repeticoes; ++r) acao();
    finalizar();
    fim = std::chrono::steady_clock::now();
    return std::chrono::duration<double, std::milli>(fim - inicio).count() / repeticoes;
}

}  // namespace

int main() {
    const int parceiros = 2000;  // cenário de referência do RNF01

    cudaDeviceProp prop{};
    CHECAR(cudaGetDeviceProperties(&prop, 0));
    std::printf("GPU: %s | %d SMs | capacidade %d.%d\n\n", prop.name,
                prop.multiProcessorCount, prop.major, prop.minor);

    std::printf("%8s %10s %10s %10s %10s %10s  %s\n", "planos", "CPU ms", "envio",
                "kernel", "volta", "GPU total", "confere");
    std::printf("---------------------------------------------------------------------------\n");

    for (int planos : {256, 1024, 4096, 16384, 65536}) {
        uint32_t e = 42u;
        std::vector<float> uplift(parceiros), custo(parceiros);
        float soma_custo_total = 0.0f;
        for (int i = 0; i < parceiros; ++i) {
            uplift[i] = uniforme(e, 50.0f, 5000.0f);
            custo[i] = uniforme(e, 20.0f, 800.0f);
            soma_custo_total += custo[i];
        }
        const float orcamento = soma_custo_total * 0.12f;

        std::vector<uint8_t> populacao(static_cast<size_t>(planos) * parceiros);
        for (auto& bit : populacao) bit = uniforme(e, 0.0f, 1.0f) < 0.15f ? 1 : 0;

        // ------------------------------------------------------------- CPU
        std::vector<float> apt_cpu(planos), cst_cpu(planos);
        const double t_cpu = medir(
            [&] {
                for (int plano = 0; plano < planos; ++plano) {
                    const uint8_t* sel =
                        populacao.data() + static_cast<size_t>(plano) * parceiros;
                    float su = 0.0f, sc = 0.0f;
                    for (int i = 0; i < parceiros; ++i) {
                        if (sel[i]) { su += uplift[i]; sc += custo[i]; }
                    }
                    cst_cpu[plano] = sc;
                    apt_cpu[plano] = (sc <= orcamento) ? su : 0.0f;
                }
            },
            [] {});

        // ---------------------------------------------------- transferência
        float *d_uplift = nullptr, *d_custo = nullptr, *d_apt = nullptr, *d_cst = nullptr;
        uint8_t* d_pop = nullptr;
        CHECAR(cudaMalloc(&d_uplift, parceiros * sizeof(float)));
        CHECAR(cudaMalloc(&d_custo, parceiros * sizeof(float)));
        CHECAR(cudaMalloc(&d_pop, populacao.size()));
        CHECAR(cudaMalloc(&d_apt, planos * sizeof(float)));
        CHECAR(cudaMalloc(&d_cst, planos * sizeof(float)));

        auto sincronizar = [] { cudaDeviceSynchronize(); };

        const double t_envio = medir(
            [&] {
                cudaMemcpy(d_uplift, uplift.data(), parceiros * sizeof(float),
                           cudaMemcpyHostToDevice);
                cudaMemcpy(d_custo, custo.data(), parceiros * sizeof(float),
                           cudaMemcpyHostToDevice);
                cudaMemcpy(d_pop, populacao.data(), populacao.size(),
                           cudaMemcpyHostToDevice);
            },
            sincronizar);
        CHECAR(cudaGetLastError());

        // ---------------------------------------------------------- kernel
        const int threads = 256;
        const int blocos = (planos + threads - 1) / threads;
        const double t_kernel = medir(
            [&] {
                avaliar_populacao<<<blocos, threads>>>(d_uplift, d_custo, d_pop, orcamento,
                                                       parceiros, planos, d_apt, d_cst);
            },
            sincronizar);
        CHECAR(cudaGetLastError());

        // ---------------------------------------------------------- volta
        std::vector<float> apt_gpu(planos), cst_gpu(planos);
        const double t_volta = medir(
            [&] {
                cudaMemcpy(apt_gpu.data(), d_apt, planos * sizeof(float),
                           cudaMemcpyDeviceToHost);
                cudaMemcpy(cst_gpu.data(), d_cst, planos * sizeof(float),
                           cudaMemcpyDeviceToHost);
            },
            sincronizar);
        CHECAR(cudaGetLastError());

        // ------------------------------------------------------- corretude
        // Aqui CPU e GPU somam na mesma ordem sequencial, então a tolerância
        // pode ser apertada — ao contrário da comparação com o NumPy, que usa
        // BLAS e soma em outra ordem.
        double erro_max = 0.0;
        for (int i = 0; i < planos; ++i) {
            const double base = apt_cpu[i] > 1.0 ? apt_cpu[i] : 1.0;
            const double e_rel = std::fabs(apt_cpu[i] - apt_gpu[i]) / base;
            if (e_rel > erro_max) erro_max = e_rel;
        }

        const double t_gpu_total = t_kernel + t_envio + t_volta;
        std::printf("%8d %10.2f %10.2f %10.3f %10.2f %10.2f  %s (%.1e)\n", planos, t_cpu,
                    t_envio, t_kernel, t_volta, t_gpu_total,
                    erro_max < 1e-4 ? "sim" : "NAO", erro_max);

        cudaFree(d_uplift); cudaFree(d_custo); cudaFree(d_pop);
        cudaFree(d_apt); cudaFree(d_cst);
    }
    return 0;
}
