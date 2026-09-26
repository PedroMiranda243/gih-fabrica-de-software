// O genético inteiro na GPU — H54c, ADR-006, ADR-011.
//
// **A mesma sequência da versão OpenMP**, com a GPU no lugar das threads: as
// partidas avançam juntas, uma geração por vez, e cada geração é um kernel só,
// com um bloco por indivíduo da geração nova. O bloco 0 de cada partida copia
// a elite; cada um dos outros sorteia os pais no torneio, monta o filho gene a
// gene e o avalia (`avaliar_no_bloco`, H54b). Com os parâmetros padrão são
// 4 × 48 = 192 blocos por geração, e 150 gerações.
//
// **Por que o plano é o mesmo** da serial e da OpenMP:
// - o sorteio, o torneio, a elite e a fórmula de cada gene são as mesmas
//   funções da CPU (`genetico.hpp`), compiladas para os dois lados;
// - nenhum bloco lê o que outro escreve na mesma geração: a leitura é da
//   geração atual, a escrita é na seguinte, cada bloco na sua posição;
// - a avaliação soma inteiros, e a soma de inteiros não depende da ordem em que
//   as threads terminam (ADR-011);
// - no fim, as partidas são percorridas na ordem, com a mesma comparação
//   estrita, contra o melhor guloso.
//
// **A população nasce e fica na placa** (ADR-006). Vão para a GPU a instância e
// os dois gulosos; a geração 0 é sorteada lá, pelas coordenadas. Voltam as
// avaliações da última geração — 40 bytes por indivíduo — e os genes do plano
// vencedor. No spike, mandar e trazer a população a cada geração foi 88% do
// tempo.
//
// Compilado só com CUDA (`GIH_COM_CUDA`); sem ele, `sem_gpu.cpp` responde.
#include <algorithm>
#include <array>
#include <chrono>
#include <climits>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "genetico.hpp"
#include "gpu.cuh"
#include "gpu.hpp"
#include "gpu_avaliacao.cuh"
#include "nucleo.hpp"

namespace gih::gpu {
namespace {

using genetico::gene_do_filho;
using genetico::gene_sorteado;
using genetico::indice_do_melhor;
using genetico::sorteio;
using genetico::torneio;

// O que os kernels da busca recebem, por valor, além da instância: os números
// de `genetico::Preparo` e o tamanho de cada partida.
struct Busca {
    std::uint64_t semente;
    std::uint64_t taxa_ppm;
    std::uint64_t valores;
    std::int64_t densidade;
    int populacao;  // indivíduos por partida
    int iniciais;  // os gulosos, no começo de toda partida
};

// A geração 0 de todas as partidas, um bloco por indivíduo: os gulosos
// copiados, os demais sorteados pelas coordenadas, e todos avaliados.
__global__ void gerar_populacao_inicial(VisaoDaInstancia inst, Busca b, const Gene* gulosos, Gene* populacao,
                                        AvaliacaoNoDispositivo* avaliacoes) {
    extern __shared__ int contadores[];
    __shared__ long long parciais[WARPS_POR_BLOCO][4];
    const int partida = blockIdx.x / b.populacao, j = blockIdx.x % b.populacao;
    const int n = inst.parceiros;
    Gene* genes = populacao + static_cast<std::size_t>(blockIdx.x) * n;

    if (j < b.iniciais) {
        const Gene* guloso = gulosos + static_cast<std::size_t>(j) * n;
        for (int i = threadIdx.x; i < n; i += blockDim.x) genes[i] = guloso[i];
    } else {
        const std::uint64_t base =
            sorteio(b.semente, static_cast<std::uint64_t>(partida), 0, static_cast<std::uint64_t>(j));
        const auto un = static_cast<std::uint64_t>(n);
        const auto acoes = static_cast<std::uint64_t>(inst.acoes);
        for (int i = threadIdx.x; i < n; i += blockDim.x) genes[i] = gene_sorteado(base, i, un, acoes, b.densidade);
    }
    // Cada thread avalia os mesmos genes que escreveu: a mesma fatia, na mesma ordem.
    const AvaliacaoNoDispositivo av = avaliar_no_bloco(inst, genes, contadores, parciais);
    if (threadIdx.x == 0) avaliacoes[blockIdx.x] = av;
}

// Uma geração de todas as partidas: lê `atual` e `avaliacoes`, escreve
// `seguinte` e `novas`.
__global__ void gerar_geracao(VisaoDaInstancia inst, Busca b, std::uint64_t geracao, const Gene* atual,
                              const AvaliacaoNoDispositivo* avaliacoes, Gene* seguinte,
                              AvaliacaoNoDispositivo* novas) {
    extern __shared__ int contadores[];
    __shared__ long long parciais[WARPS_POR_BLOCO][4];
    __shared__ int escolhidos[2];
    const int partida = blockIdx.x / b.populacao, j = blockIdx.x % b.populacao;
    const int n = inst.parceiros;
    const std::size_t primeiro = static_cast<std::size_t>(partida) * b.populacao;
    const AvaliacaoNoDispositivo* anteriores = avaliacoes + primeiro;
    const Gene* da_partida = atual + primeiro * n;
    Gene* saida = seguinte + static_cast<std::size_t>(blockIdx.x) * n;

    if (j == 0) {
        // Elitismo: o melhor da geração anterior passa intacto, com a avaliação
        // que já tinha. `j` é o mesmo em todo o bloco, e a barreira aqui dentro
        // é alcançada por todas as threads.
        if (threadIdx.x == 0) escolhidos[0] = indice_do_melhor(anteriores, b.populacao);
        __syncthreads();
        const Gene* elite = da_partida + static_cast<std::size_t>(escolhidos[0]) * n;
        for (int i = threadIdx.x; i < n; i += blockDim.x) saida[i] = elite[i];
        if (threadIdx.x == 0) novas[blockIdx.x] = anteriores[escolhidos[0]];
        return;
    }

    const std::uint64_t base =
        sorteio(b.semente, static_cast<std::uint64_t>(partida), geracao, static_cast<std::uint64_t>(j));
    if (threadIdx.x == 0) {
        const auto un = static_cast<std::uint64_t>(n);
        escolhidos[0] = torneio(anteriores, b.populacao, encadear(base, un), encadear(base, un + 1));
        escolhidos[1] = torneio(anteriores, b.populacao, encadear(base, un + 2), encadear(base, un + 3));
    }
    __syncthreads();
    const Gene* pai = da_partida + static_cast<std::size_t>(escolhidos[0]) * n;
    const Gene* mae = da_partida + static_cast<std::size_t>(escolhidos[1]) * n;
    for (int i = threadIdx.x; i < n; i += blockDim.x) {
        saida[i] = gene_do_filho(pai, mae, i, base, b.taxa_ppm, b.valores);
    }
    const AvaliacaoNoDispositivo av = avaliar_no_bloco(inst, saida, contadores, parciais);
    if (threadIdx.x == 0) novas[blockIdx.x] = av;
}

// Quantas gerações a CPU deixa na fila da GPU antes de esperar.
//
// Os lançamentos são assíncronos: sem espera nenhuma, a CPU enfileiraria as 150
// gerações em um milissegundo e só então olharia o relógio — e o limite de
// tempo (UC08-E2) não pararia nada. Esperando cada geração terminar, a placa
// ficaria parada enquanto a CPU lança a próxima. Com quatro na fila, a CPU
// espera a geração g−4 antes de lançar a g: a placa sempre tem trabalho, e o
// relógio é olhado com no máximo quatro gerações de atraso.
constexpr int NA_FILA = 4;

// Um evento no fim de cada geração enfileirada, reaproveitados em rodízio.
class Marcos {
public:
    Marcos() {
        for (auto& e : eventos_) GIH_CUDA(cudaEventCreateWithFlags(&e, cudaEventDisableTiming));
    }
    ~Marcos() {
        for (auto e : eventos_) {
            if (e != nullptr) cudaEventDestroy(e);
        }
    }
    Marcos(const Marcos&) = delete;
    Marcos& operator=(const Marcos&) = delete;

    void marcar(int geracao) { GIH_CUDA(cudaEventRecord(eventos_[geracao % NA_FILA])); }
    // Espera a geração `geracao − NA_FILA`, que marcou o mesmo evento.
    void esperar_vaga(int geracao) {
        if (geracao > NA_FILA) GIH_CUDA(cudaEventSynchronize(eventos_[geracao % NA_FILA]));
    }

private:
    std::array<cudaEvent_t, NA_FILA> eventos_{};
};

double segundos_desde(std::chrono::steady_clock::time_point inicio) {
    return std::chrono::duration<double>(std::chrono::steady_clock::now() - inicio).count();
}

bool iguais(const Avaliacao& a, const Avaliacao& b) {
    return a.ganho == b.ganho && a.custo == b.custo && a.acoes == b.acoes && a.cauda == b.cauda &&
           a.violacao == b.violacao;
}

}  // namespace

Resultado otimizar_na_gpu(const Instancia& inst, const Parametros& p) {
    genetico::conferir(p);
    const genetico::Cronometro relogio(p.limite_ms);
    const int n = inst.parceiros;
    const int partidas = p.partidas, tamanho = p.populacao;
    const long long individuos_por_geracao = static_cast<long long>(partidas) * tamanho;
    if (individuos_por_geracao > INT_MAX) {
        throw std::invalid_argument("A GPU calcula até " + std::to_string(INT_MAX) + " indivíduos por geração.");
    }
    if (inst.categorias > CATEGORIAS_MAXIMAS) {
        throw std::invalid_argument("A GPU conta até " + std::to_string(CATEGORIAS_MAXIMAS) + " categorias.");
    }

    // O custo fixo do modo, antes de qualquer conta: achar a placa inicia o
    // driver, e a primeira chamada ao runtime cria o contexto da GPU. No
    // contêiner, as duas somam centenas de milissegundos, que cada processo
    // paga uma vez. Entram no tempo da busca, porque o gestor espera por elas,
    // e saem também à parte, para a medição mostrar onde o tempo foi.
    Resultado r;
    const auto antes_do_contexto = std::chrono::steady_clock::now();
    Dispositivo d;
    Ausencia ausencia{};
    std::string motivo;
    if (!procurar(d, ausencia, motivo)) throw SemGpu(motivo);
    GIH_CUDA(cudaFree(nullptr));
    r.contexto_segundos = segundos_desde(antes_do_contexto);
    r.threads = static_cast<int>(std::min<long long>(INT_MAX, individuos_por_geracao * THREADS_POR_BLOCO));
    if (n == 0) {
        r.avaliacao = avaliar(inst, nullptr);
        r.segundos = relogio.segundos();
        return r;
    }

    genetico::Preparo prep = genetico::preparar(inst, p);
    const int individuos = static_cast<int>(individuos_por_geracao);
    const int iniciais = std::min<int>(2, tamanho);
    const Busca b{p.semente, prep.taxa_ppm, prep.valores, prep.densidade, tamanho, iniciais};

    // Primeiro a população, que é o que pode não caber: sem memória na placa, a
    // busca recusa antes de enviar qualquer coisa (`checar`, `SemGpu`).
    PopulacaoNaGpu pop(individuos, n);
    Memoria<AvaliacaoNoDispositivo> avaliacoes(static_cast<std::size_t>(individuos));
    Memoria<AvaliacaoNoDispositivo> novas(static_cast<std::size_t>(individuos));
    const InstanciaNaGpu na_gpu(inst);
    std::vector<Gene> gulosos;
    for (int j = 0; j < iniciais; ++j) gulosos.insert(gulosos.end(), prep.iniciais[j].begin(), prep.iniciais[j].end());
    Memoria<Gene> gulosos_na_gpu(gulosos.size());
    gulosos_na_gpu.enviar(gulosos.data());

    const VisaoDaInstancia visao = na_gpu.visao();
    const std::size_t compartilhada = compartilhada_por_bloco(inst.categorias);
    gerar_populacao_inicial<<<individuos, THREADS_POR_BLOCO, compartilhada>>>(visao, b, gulosos_na_gpu.dados(),
                                                                              pop.atual(), avaliacoes.dados());
    GIH_CUDA(cudaGetLastError());
    r.partidas = partidas;

    Marcos marcos;
    for (int g = 1; g <= p.geracoes; ++g) {
        marcos.esperar_vaga(g);
        if (relogio.estourou()) {
            r.parcial = true;
            break;
        }
        gerar_geracao<<<individuos, THREADS_POR_BLOCO, compartilhada>>>(
            visao, b, static_cast<std::uint64_t>(g), pop.atual(), avaliacoes.dados(), pop.seguinte(), novas.dados());
        GIH_CUDA(cudaGetLastError());
        marcos.marcar(g);
        pop.trocar();
        std::swap(avaliacoes, novas);
        r.geracoes += partidas;
    }

    // A cópia espera a fila inteira terminar. Voltam só as avaliações da última
    // geração; os genes, só os do vencedor, se ele não for um dos gulosos.
    const std::vector<AvaliacaoNoDispositivo> finais = avaliacoes.trazer();
    int vencedor = -1;
    for (int partida = 0; partida < partidas; ++partida) {
        const AvaliacaoNoDispositivo* da_partida = finais.data() + static_cast<std::size_t>(partida) * tamanho;
        const int m = indice_do_melhor(da_partida, tamanho);
        const Avaliacao av = como_avaliacao(da_partida[m]);
        if (melhor(av, prep.av_vencedor)) {
            vencedor = partida * tamanho + m;
            prep.av_vencedor = av;
        }
    }
    if (vencedor >= 0) {
        prep.vencedor = pop.trazer_individuo(vencedor);
        // O plano que volta é avaliado de novo na CPU. Diferente da GPU não é
        // resposta: é defeito do kernel, e sai como defeito.
        const Avaliacao na_cpu = avaliar(inst, prep.vencedor.data());
        if (!iguais(na_cpu, prep.av_vencedor)) {
            throw std::logic_error("A GPU avaliou o plano vencedor diferente da CPU.");
        }
        prep.av_vencedor = na_cpu;
    }

    genetico::conferir_vencedor(prep.av_vencedor);
    r.genes = std::move(prep.vencedor);
    r.avaliacao = prep.av_vencedor;
    r.segundos = relogio.segundos();
    return r;
}

}  // namespace gih::gpu
