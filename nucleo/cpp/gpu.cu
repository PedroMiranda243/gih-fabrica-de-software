// A GPU do núcleo — H54a: achar a placa, levar a instância e a população para
// ela, trazer de volta e conferir.
//
// Compilado só com CUDA (`GIH_COM_CUDA`); sem ele, `sem_gpu.cpp` responde.
#include <algorithm>
#include <chrono>

#include "gpu.cuh"
#include "gpu.hpp"

namespace gih::gpu {
namespace {

// A conta que prova que a GPU lê a instância e a população com o layout que o
// kernel da H54b vai ler: ações, custo, ganho e cauda longa de cada indivíduo.
// É a parte mais simples da avaliação; a completa, com as cotas por categoria e
// a violação, é da H54b. Uma thread por indivíduo, como no spike: o gene de cada
// parceiro é lido em sequência, e as somas são inteiras, então a ordem não muda
// o resultado.
__global__ void somar_por_individuo(VisaoDaInstancia inst, const Gene* populacao, int individuos,
                                    std::int64_t* acoes, std::int64_t* custo, std::int64_t* ganho,
                                    std::int64_t* cauda) {
    const int j = blockIdx.x * blockDim.x + threadIdx.x;
    if (j >= individuos) return;
    const Gene* genes = populacao + static_cast<std::size_t>(j) * inst.parceiros;
    std::int64_t a = 0, c = 0, g = 0, na_cauda = 0;
    for (int i = 0; i < inst.parceiros; ++i) {
        const int gene = genes[i];
        if (gene == 0) continue;
        a += 1;
        c += inst.custo[gene - 1];
        g += inst.ganho[static_cast<std::size_t>(i) * inst.acoes + gene - 1];
        na_cauda += inst.cauda[i] ? 1 : 0;
    }
    acoes[j] = a;
    custo[j] = c;
    ganho[j] = g;
    cauda[j] = na_cauda;
}

double milissegundos_desde(std::chrono::steady_clock::time_point inicio) {
    return std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - inicio).count();
}

bool conferir_no_dispositivo(const Instancia& inst, const InstanciaNaGpu& na_gpu, const PopulacaoNaGpu& pop,
                             const std::vector<Gene>& populacao) {
    const int individuos = pop.individuos();
    Memoria<std::int64_t> acoes(individuos), custo(individuos), ganho(individuos), cauda(individuos);
    const int por_bloco = 128;
    const int blocos = (individuos + por_bloco - 1) / por_bloco;
    somar_por_individuo<<<blocos, por_bloco>>>(na_gpu.visao(), pop.atual(), individuos, acoes.dados(),
                                               custo.dados(), ganho.dados(), cauda.dados());
    GIH_CUDA(cudaGetLastError());
    GIH_CUDA(cudaDeviceSynchronize());

    const auto a = acoes.trazer(), c = custo.trazer(), g = ganho.trazer(), n = cauda.trazer();
    for (int j = 0; j < individuos; ++j) {
        const Avaliacao av = avaliar(inst, populacao.data() + static_cast<std::size_t>(j) * inst.parceiros);
        if (a[j] != av.acoes || c[j] != av.custo || g[j] != av.ganho || n[j] != av.cauda) return false;
    }
    return true;
}

}  // namespace

bool procurar(Dispositivo& dispositivo, std::string& motivo) {
    int quantas = 0;
    const cudaError_t erro = cudaGetDeviceCount(&quantas);
    if (erro != cudaSuccess) {
        // Sem driver NVIDIA — um contêiner sem `--gpus`, uma máquina sem placa —
        // o runtime responde que o driver é insuficiente. A mensagem dele vai
        // junto, para quem for investigar.
        motivo = std::string("Nenhuma GPU NVIDIA disponível (CUDA: ") + cudaGetErrorString(erro) + ").";
        cudaGetLastError();  // limpa o erro, para não contaminar a próxima chamada
        return false;
    }
    if (quantas == 0) {
        motivo = "Nenhuma GPU NVIDIA disponível.";
        return false;
    }
    cudaDeviceProp p{};
    if (cudaGetDeviceProperties(&p, 0) != cudaSuccess) {
        motivo = "A GPU não respondeu às propriedades.";
        cudaGetLastError();
        return false;
    }
    dispositivo = {p.name, p.major, p.minor, p.totalGlobalMem};
    return true;
}

Transferencia ida_e_volta(const Instancia& inst, const std::vector<Gene>& populacao, int individuos,
                          int repeticoes) {
    Dispositivo d;
    std::string motivo;
    if (!procurar(d, motivo)) throw SemGpu(motivo);
    if (individuos < 1 || inst.parceiros < 1) {
        throw std::invalid_argument("A ida e volta precisa de ao menos um indivíduo e um parceiro.");
    }
    if (populacao.size() != static_cast<std::size_t>(individuos) * inst.parceiros) {
        throw std::invalid_argument("A população não tem indivíduos × parceiros genes.");
    }

    // A primeira chamada ao runtime cria o contexto da GPU, e leva centenas de
    // milissegundos. Pago aqui, fora da medição: ele acontece uma vez por
    // processo, e não uma vez por busca.
    GIH_CUDA(cudaFree(nullptr));

    Transferencia t;
    InstanciaNaGpu na_gpu(inst);
    PopulacaoNaGpu pop(individuos, inst.parceiros);
    t.bytes_instancia = na_gpu.bytes();
    t.bytes_populacao = pop.bytes();

    // Uma rodada de aquecimento, descartada, e as medidas: a primeira cópia de
    // cada tamanho paga a alocação dos buffers de passagem do driver.
    for (int r = 0; r <= repeticoes; ++r) {
        auto inicio = std::chrono::steady_clock::now();
        na_gpu.enviar();
        pop.enviar(populacao);
        GIH_CUDA(cudaDeviceSynchronize());
        const double envio = milissegundos_desde(inicio);

        inicio = std::chrono::steady_clock::now();
        static_cast<void>(pop.trazer());
        const double volta_ms = milissegundos_desde(inicio);

        inicio = std::chrono::steady_clock::now();
        static_cast<void>(pop.trazer_individuo(individuos - 1));
        const double volta_um = milissegundos_desde(inicio);

        if (r == 0) continue;
        t.envio_ms.push_back(envio);
        t.volta_ms.push_back(volta_ms);
        t.volta_um_ms.push_back(volta_um);
    }

    const std::vector<Gene> ultimo(populacao.end() - inst.parceiros, populacao.end());
    t.identica = na_gpu.identica() && pop.trazer() == populacao &&
                 pop.trazer_individuo(individuos - 1) == ultimo;
    t.conferida = conferir_no_dispositivo(inst, na_gpu, pop, populacao);
    return t;
}

}  // namespace gih::gpu
