// O núcleo do otimizador em C++ — H53a, ADR-011, ADR-012.
//
// É o mesmo algoritmo de `gih_nucleo` (Python), passo a passo: a mesma
// instância em inteiros, o mesmo gerador sem estado, os mesmos desempates. O
// critério de aceite da H53a é **resultado idêntico** — mesmos genes, mesmo
// ganho, mesmas gerações —, e é ele que torna honesto o *speedup* das versões
// paralelas: elas vão reproduzir esta, que reproduz o Python.
//
// Por isso o código segue a forma do Python, e não a forma mais idiomática de
// C++: quem conferir um contra o outro precisa achar a mesma linha no mesmo
// lugar. Os comentários de cada função dizem qual função do pacote Python ela
// reproduz.
#pragma once

#include <cstdint>
#include <string>
#include <vector>

// O que a CPU e a GPU calculam com **a mesma função**, e não com duas cópias
// (H54c, ADR-011): o gerador, a comparação e a fórmula de cada gene. No `.cu`,
// o nvcc compila essas funções para os dois lados; no `.cpp`, a marca some.
#if defined(__CUDACC__)
#define GIH_CPU_E_GPU __host__ __device__
#else
#define GIH_CPU_E_GPU
#endif

namespace gih {

// ------------------------------------------------------------ o gerador
// SplitMix64 (Steele, Lea e Flood, 2014), aplicado em cadeia às coordenadas do
// sorteio. Reproduz `gih_nucleo/aleatorio.py`; os valores de referência estão
// em `nucleo/tests/test_aleatorio.py` e são conferidos contra este código.
GIH_CPU_E_GPU constexpr std::uint64_t mistura(std::uint64_t z) {
    z += 0x9E3779B97F4A7C15ULL;
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    return z ^ (z >> 31);
}

GIH_CPU_E_GPU constexpr std::uint64_t encadear(std::uint64_t base, std::uint64_t chave) {
    return mistura(base ^ chave);
}

// Probabilidades inteiras, em partes por milhão, como no Python.
constexpr std::uint64_t MILHAO = 1000000;

// ------------------------------------------------------------ o problema
constexpr int SEM_CATEGORIA = -1;

// Genes em um byte: 0 é "sem ação", de 1 a A é a ação. Com isso o catálogo
// cabe em 254 ações, e a população ocupa um quarto da memória de `int` — o que
// importa quando ela passar a morar na GPU (H54a).
using Gene = std::uint8_t;
constexpr int ACOES_MAXIMAS = 254;

struct Instancia {
    int parceiros = 0;
    int acoes = 0;
    int categorias = 0;
    std::vector<std::int64_t> ganho;  // [parceiro * acoes + acao], centavos
    std::vector<std::int64_t> custo;  // [acao], centavos, > 0
    std::int64_t orcamento = 0;
    std::int64_t maximo_acoes = 0;
    std::vector<int> categoria;  // [parceiro], SEM_CATEGORIA quando não confirmada
    std::vector<char> cauda;  // [parceiro]
    std::vector<std::int64_t> minimo_categoria;  // [categoria], contagem
    std::vector<std::int64_t> maximo_categoria;
    std::int64_t minimo_cauda = 0;

    std::int64_t ganho_de(int i, int a) const { return ganho[static_cast<std::size_t>(i) * acoes + a]; }
    int acao_mais_barata() const;  // no empate, a de menor índice
};

struct Avaliacao {
    std::int64_t ganho = 0;
    std::int64_t custo = 0;
    std::int64_t acoes = 0;
    std::int64_t cauda = 0;
    std::int64_t violacao = 0;
    std::vector<std::int64_t> por_categoria;

    bool viavel() const { return violacao == 0; }
};

// `problema.avaliar`.
Avaliacao avaliar(const Instancia& inst, const Gene* genes);

// `problema.melhor`: o viável ganha do inviável; entre viáveis, o de maior
// ganho; entre inviáveis, o de menor violação, e depois o de maior ganho.
// Estrita: no empate, nenhuma é melhor, e quem chama fica com a que já tinha.
// Vale para qualquer avaliação com `violacao` e `ganho` — a da CPU e a da GPU
// (H54c) —, e é uma função só: o desempate é o mesmo nas duas por construção.
template <typename A>
GIH_CPU_E_GPU bool melhor(const A& a, const A& b) {
    const bool a_viavel = a.violacao == 0, b_viavel = b.violacao == 0;
    if (a_viavel != b_viavel) return a_viavel;
    if (a_viavel) return a.ganho > b.ganho;
    if (a.violacao != b.violacao) return a.violacao < b.violacao;
    return a.ganho > b.ganho;
}

// ------------------------------------------------------------ a viabilidade
struct Inviabilidade {
    std::string restricao;  // os mesmos códigos de `viabilidade.py`
    std::int64_t exigido = 0;
    std::int64_t disponivel = 0;
    int categoria = SEM_CATEGORIA;
};

// `viabilidade._diagnosticar`: `true` e o conjunto mínimo quando cabe; `false` e
// o motivo quando não.
bool diagnosticar(const Instancia& inst, std::vector<int>& escolhidos, Inviabilidade& motivo);

// ------------------------------------------------------------ os gulosos
enum class Criterio { Razao, Ganho };

// `guloso.guloso`. Só é chamada depois de `diagnosticar` dizer que cabe.
std::vector<Gene> guloso(const Instancia& inst, Criterio criterio);

// ------------------------------------------------------------ o genético
struct Parametros {
    std::uint64_t semente = 42;
    int partidas = 4;
    int populacao = 48;
    int geracoes = 150;
    int mutacoes_por_filho = 1;
    std::int64_t limite_ms = -1;  // negativo: sem limite
    int threads = 0;  // só o modo OpenMP lê; 0: o padrão do OpenMP (OMP_NUM_THREADS ou os núcleos)
};

struct Resultado {
    std::vector<Gene> genes;
    Avaliacao avaliacao;
    int partidas = 0;
    std::int64_t geracoes = 0;
    bool parcial = false;
    double segundos = 0;
    int threads = 1;  // as que calcularam os filhos; no modo cuda, as da GPU em cada geração
    // Só no modo cuda: quanto de `segundos` foi criar o contexto da GPU, que
    // cada processo paga uma vez, antes de a placa fazer qualquer conta (H54c).
    double contexto_segundos = 0;
};

// `serial.otimizar`, depois de a viabilidade ter sido conferida.
Resultado otimizar_serial(const Instancia& inst, const Parametros& p);

// A versão OpenMP (H53b): sem limite de tempo, o mesmo plano, a mesma avaliação
// e as mesmas gerações da serial, com qualquer número de threads.
Resultado otimizar_openmp(const Instancia& inst, const Parametros& p);

// As threads que a versão OpenMP usa por padrão; 0 quando o executável foi
// compilado sem OpenMP, e só o modo serial existe.
int threads_openmp();

}  // namespace gih
