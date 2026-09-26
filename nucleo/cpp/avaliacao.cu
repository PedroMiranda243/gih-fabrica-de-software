// O kernel de avaliação da população — H54b.
//
// Um bloco por indivíduo (ver `gpu_avaliacao.cuh`). A saída é a avaliação de
// cada um e, para conferir, a contagem por categoria; o laço da H54c só vai
// precisar da primeira.
//
// Compilado só com CUDA (`GIH_COM_CUDA`); sem ele, `sem_gpu.cpp` responde.
#include <algorithm>
#include <stdexcept>

#include "gpu.cuh"
#include "gpu.hpp"
#include "gpu_avaliacao.cuh"

namespace gih::gpu {
namespace {

__global__ void avaliar_populacao(VisaoDaInstancia inst, const Gene* populacao, AvaliacaoNoDispositivo* saida,
                                  int* por_categoria) {
    extern __shared__ int contadores[];
    __shared__ long long parciais[WARPS_POR_BLOCO][4];
    const int j = blockIdx.x;
    const Gene* genes = populacao + static_cast<std::size_t>(j) * inst.parceiros;

    const AvaliacaoNoDispositivo av = avaliar_no_bloco(inst, genes, contadores, parciais);
    if (threadIdx.x == 0) saida[j] = av;
    for (int k = threadIdx.x; k < inst.categorias; k += blockDim.x) {
        por_categoria[static_cast<std::size_t>(j) * inst.categorias + k] = contadores[k];
    }
}

// Os contadores por categoria moram na memória compartilhada do bloco, que tem
// 48 KB por padrão. Um int por categoria: cabem 12 mil, muito acima de qualquer
// rede real — mas passar disso seria falha silenciosa no lançamento, e aqui vira
// recusa com motivo.
constexpr int CATEGORIAS_MAXIMAS = 10000;

}  // namespace

PopulacaoAvaliada avaliar_na_gpu(const Instancia& inst, const std::vector<Gene>& populacao, int individuos,
                                 int repeticoes) {
    Dispositivo d;
    Ausencia ausencia{};
    std::string motivo;
    if (!procurar(d, ausencia, motivo)) throw SemGpu(motivo);
    if (individuos < 1 || inst.parceiros < 1) {
        throw std::invalid_argument("A avaliação precisa de ao menos um indivíduo e um parceiro.");
    }
    if (populacao.size() != static_cast<std::size_t>(individuos) * inst.parceiros) {
        throw std::invalid_argument("A população não tem indivíduos × parceiros genes.");
    }
    if (inst.categorias > CATEGORIAS_MAXIMAS) {
        throw std::invalid_argument("A GPU conta até " + std::to_string(CATEGORIAS_MAXIMAS) + " categorias.");
    }
    GIH_CUDA(cudaFree(nullptr));  // o contexto da GPU, fora da medição

    InstanciaNaGpu na_gpu(inst);
    PopulacaoNaGpu pop(individuos, inst.parceiros);
    pop.enviar(populacao);
    Memoria<AvaliacaoNoDispositivo> saida(static_cast<std::size_t>(individuos));
    // Pelo menos um int, para o ponteiro existir mesmo sem categoria.
    Memoria<int> por_categoria(std::max<std::size_t>(1, static_cast<std::size_t>(individuos) * inst.categorias));
    const std::size_t compartilhada = std::max<std::size_t>(1, inst.categorias) * sizeof(int);

    auto lancar = [&] {
        avaliar_populacao<<<individuos, THREADS_POR_BLOCO, compartilhada>>>(na_gpu.visao(), pop.atual(),
                                                                          saida.dados(), por_categoria.dados());
        GIH_CUDA(cudaGetLastError());
    };
    aquecer(lancar);

    // **Mede-se o lote, e não o lançamento.** Um lançamento isolado, com a placa
    // esperando a CPU entre um e outro, mede a latência — e ela oscilou de 11 a
    // 88 µs com 500 parceiros, conforme o relógio da placa subia ou não. O laço
    // da H54c lança uma geração depois da outra, sem esperar a CPU no meio: é a
    // vazão desses lançamentos em sequência que importa, como no spike. O lote
    // tem lançamentos bastantes para durar uns 2 ms, e cada medida é a média
    // por lançamento dentro dele.
    cudaEvent_t comeco, fim;
    GIH_CUDA(cudaEventCreate(&comeco));
    GIH_CUDA(cudaEventCreate(&fim));
    auto medir_lote = [&](int lancamentos) {
        GIH_CUDA(cudaEventRecord(comeco));
        for (int i = 0; i < lancamentos; ++i) lancar();
        GIH_CUDA(cudaEventRecord(fim));
        GIH_CUDA(cudaEventSynchronize(fim));
        float ms = 0;
        GIH_CUDA(cudaEventElapsedTime(&ms, comeco, fim));
        return static_cast<double>(ms) / lancamentos;
    };
    const double um = medir_lote(1);
    const int por_lote = std::clamp(static_cast<int>(2.0 / std::max(um, 1e-3)), 1, 1000);

    PopulacaoAvaliada r;
    for (int rodada = 0; rodada < repeticoes; ++rodada) r.kernel_ms.push_back(medir_lote(por_lote));
    cudaEventDestroy(comeco);
    cudaEventDestroy(fim);

    const std::vector<AvaliacaoNoDispositivo> avs = saida.trazer();
    const std::vector<int> contagens = por_categoria.trazer();
    r.avaliacoes.reserve(static_cast<std::size_t>(individuos));
    for (int j = 0; j < individuos; ++j) {
        Avaliacao av;
        av.ganho = avs[j].ganho;
        av.custo = avs[j].custo;
        av.acoes = avs[j].acoes;
        av.cauda = avs[j].cauda;
        av.violacao = avs[j].violacao;
        av.por_categoria.assign(contagens.begin() + static_cast<std::ptrdiff_t>(j) * inst.categorias,
                                contagens.begin() + static_cast<std::ptrdiff_t>(j + 1) * inst.categorias);
        r.avaliacoes.push_back(std::move(av));
    }
    return r;
}

}  // namespace gih::gpu
