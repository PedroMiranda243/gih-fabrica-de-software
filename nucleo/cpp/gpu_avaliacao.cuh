// A avaliação de um indivíduo na GPU — H54b, ADR-011.
//
// Reproduz `avaliar` (problema.cpp), conta a conta: ações, custo, ganho, cauda
// longa, contagem por categoria e a violação em unidades de ação. Tudo em
// inteiros, e é por isso que o resultado é **o mesmo** da CPU: a soma de
// inteiros não depende da ordem, e aqui cada bloco soma na ordem que as
// threads terminarem.
//
// **Um bloco por indivíduo**, e não uma thread por indivíduo como no spike. A
// população inteira tem 4 × 48 = 192 indivíduos: uma thread para cada ocuparia
// uma fração da placa. Com um bloco, as threads leem genes vizinhos — leitura
// coalescida — e cada uma soma uma fatia dos parceiros.
//
// Fica num cabeçalho, com funções `__device__` inline, porque o laço completo
// da H54c avalia cada filho do mesmo jeito, dentro do kernel dele.
#pragma once

#include "gpu.cuh"

namespace gih::gpu {

// O que a busca precisa de cada indivíduo. A contagem por categoria fica na
// memória compartilhada do bloco; quem a quer, copia (`avaliar_populacao`).
struct AvaliacaoNoDispositivo {
    long long ganho;
    long long custo;
    long long acoes;
    long long cauda;
    long long violacao;
};

// A mesma avaliação, na CPU: a contagem por categoria fica de fora, e quem a
// quer avalia de novo lá (`avaliar`).
inline Avaliacao como_avaliacao(const AvaliacaoNoDispositivo& d) {
    Avaliacao av;
    av.ganho = d.ganho;
    av.custo = d.custo;
    av.acoes = d.acoes;
    av.cauda = d.cauda;
    av.violacao = d.violacao;
    return av;
}

// Threads por bloco. Múltiplo de 32, que é o tamanho do warp: a soma do bloco
// conta com isso.
constexpr int THREADS_POR_BLOCO = 256;
constexpr int WARPS_POR_BLOCO = THREADS_POR_BLOCO / 32;

// Os contadores por categoria moram na memória compartilhada do bloco, que tem
// 48 KB por padrão. Um int por categoria: cabem 12 mil, muito acima de qualquer
// rede real — mas passar disso seria falha silenciosa no lançamento, e quem
// lança recusa antes, com motivo.
constexpr int CATEGORIAS_MAXIMAS = 10000;

// A memória compartilhada que cada bloco pede no lançamento: os contadores, e
// pelo menos um, para o ponteiro existir mesmo sem categoria.
inline std::size_t compartilhada_por_bloco(int categorias) {
    return static_cast<std::size_t>(categorias > 0 ? categorias : 1) * sizeof(int);
}

__device__ inline long long maior(long long a, long long b) { return a > b ? a : b; }

__device__ inline long long somar_no_warp(long long v) {
    for (int d = 16; d > 0; d /= 2) v += __shfl_down_sync(0xffffffffu, v, d);
    return v;
}

// Soma quatro valores de todas as threads do bloco. O resultado vale na thread 0.
__device__ inline void somar_no_bloco(long long v[4], long long (*parciais)[4]) {
    const int faixa = threadIdx.x % 32;
    const int warp = threadIdx.x / 32;
    for (int c = 0; c < 4; ++c) v[c] = somar_no_warp(v[c]);
    if (faixa == 0) {
        for (int c = 0; c < 4; ++c) parciais[warp][c] = v[c];
    }
    __syncthreads();
    if (warp == 0) {
        for (int c = 0; c < 4; ++c) v[c] = faixa < WARPS_POR_BLOCO ? parciais[faixa][c] : 0;
        for (int c = 0; c < 4; ++c) v[c] = somar_no_warp(v[c]);
    }
}

// Avalia os genes de um indivíduo com o bloco inteiro. `contadores` é memória
// compartilhada com um inteiro por categoria, e sai com a contagem; `parciais`,
// memória compartilhada para a soma. O resultado vale na thread 0.
//
// Todas as threads do bloco precisam chamar: há `__syncthreads` aqui dentro.
__device__ inline AvaliacaoNoDispositivo avaliar_no_bloco(const VisaoDaInstancia& inst, const Gene* genes,
                                                         int* contadores, long long (*parciais)[4]) {
    for (int k = threadIdx.x; k < inst.categorias; k += blockDim.x) contadores[k] = 0;
    __syncthreads();

    long long v[4] = {0, 0, 0, 0};  // ações, custo, ganho, cauda
    for (int i = threadIdx.x; i < inst.parceiros; i += blockDim.x) {
        const int g = genes[i];
        if (g == 0) continue;
        v[0] += 1;
        v[1] += inst.custo[g - 1];
        v[2] += inst.ganho[static_cast<std::size_t>(i) * inst.acoes + g - 1];
        v[3] += inst.cauda[i] ? 1 : 0;
        const int k = inst.categoria[i];
        if (k >= 0) atomicAdd(&contadores[k], 1);
    }
    somar_no_bloco(v, parciais);
    __syncthreads();  // os contadores de todas as threads chegaram

    AvaliacaoNoDispositivo av{v[2], v[1], v[0], v[3], 0};
    if (threadIdx.x == 0) {
        // A violação de `avaliar`, termo a termo (ADR-011).
        long long violacao = maior(0, av.acoes - inst.maximo_acoes) + maior(0, inst.minimo_cauda - av.cauda);
        for (int k = 0; k < inst.categorias; ++k) {
            const long long n = contadores[k];
            violacao += maior(0, inst.minimo_categoria[k] - n) + maior(0, n - inst.maximo_categoria[k]);
        }
        const long long excesso = av.custo - inst.orcamento;
        if (excesso > 0) violacao += (excesso + inst.custo_mais_barato - 1) / inst.custo_mais_barato;
        av.violacao = violacao;
    }
    return av;
}

}  // namespace gih::gpu
