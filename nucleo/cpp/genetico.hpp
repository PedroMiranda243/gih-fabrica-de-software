// Os passos do genético que as versões serial e OpenMP fazem igual (ADR-011).
//
// Nenhum destes passos guarda estado. O sorteio vem das coordenadas (semente,
// partida, geração, indivíduo), e o filho só lê a geração anterior. É por isso
// que a versão OpenMP pode calcular os filhos em qualquer ordem, em qualquer
// thread, e chegar ao mesmo plano da serial. Um gerador com estado, como o
// `std::mt19937`, tornaria o resultado dependente da ordem de execução.
#pragma once

#include <algorithm>
#include <chrono>
#include <stdexcept>
#include <vector>

#include "nucleo.hpp"

namespace gih::genetico {

inline std::uint64_t sorteio(std::uint64_t semente, std::uint64_t partida, std::uint64_t geracao,
                             std::uint64_t individuo) {
    return encadear(encadear(encadear(encadear(0, semente), partida), geracao), individuo);
}

inline int torneio(const std::vector<Avaliacao>& av, std::uint64_t h1, std::uint64_t h2) {
    const auto p = static_cast<std::uint64_t>(av.size());
    const auto r1 = static_cast<int>(h1 % p), r2 = static_cast<int>(h2 % p);
    return melhor(av[r2], av[r1]) ? r2 : r1;  // no empate, o primeiro sorteado
}

inline int indice_do_melhor(const std::vector<Avaliacao>& av) {
    int escolhido = 0;
    for (int j = 1; j < static_cast<int>(av.size()); ++j) {
        if (melhor(av[j], av[escolhido])) escolhido = j;
    }
    return escolhido;
}

inline void sorteado(const Instancia& inst, std::uint64_t base, std::int64_t densidade, Gene* genes) {
    const auto n = static_cast<std::uint64_t>(inst.parceiros);
    const auto a = static_cast<std::uint64_t>(inst.acoes);
    for (int i = 0; i < inst.parceiros; ++i) {
        const std::uint64_t h = encadear(base, static_cast<std::uint64_t>(i));
        genes[i] = (h % n) < static_cast<std::uint64_t>(densidade) ? static_cast<Gene>(1 + (h >> 32) % a) : 0;
    }
}

inline void filho(const Gene* pai, const Gene* mae, int n, std::uint64_t base, std::uint64_t taxa_ppm,
                  std::uint64_t valores, Gene* saida) {
    for (int i = 0; i < n; ++i) {
        const std::uint64_t h = encadear(base, static_cast<std::uint64_t>(i));
        Gene gene = (h & 1) ? mae[i] : pai[i];
        if ((h >> 1) % MILHAO < taxa_ppm) gene = static_cast<Gene>((h >> 21) % valores);
        saida[i] = gene;
    }
}

inline Gene* individuo(std::vector<Gene>& populacao, int j, int n) {
    return populacao.data() + static_cast<std::size_t>(j) * n;
}

inline void conferir(const Parametros& p) {
    if (p.populacao < 2 || p.partidas < 1 || p.geracoes < 0) {
        throw std::invalid_argument("A busca precisa de ao menos 2 indivíduos, 1 partida e 0 gerações.");
    }
}

// O relógio da busca: o tempo que ela informa e o limite do UC08-E2.
class Cronometro {
public:
    explicit Cronometro(std::int64_t limite_ms) : limite_ms_(limite_ms), inicio_(Relogio::now()) {}

    bool estourou() const {
        if (limite_ms_ < 0) return false;
        const auto decorrido = std::chrono::duration_cast<std::chrono::milliseconds>(Relogio::now() - inicio_);
        return decorrido.count() > limite_ms_;
    }

    double segundos() const { return std::chrono::duration<double>(Relogio::now() - inicio_).count(); }

private:
    using Relogio = std::chrono::steady_clock;
    std::int64_t limite_ms_;
    Relogio::time_point inicio_;
};

// O que as duas versões calculam uma vez, antes da primeira geração.
struct Preparo {
    std::vector<std::vector<Gene>> iniciais;  // os dois gulosos, viáveis
    std::vector<Gene> vencedor;  // o melhor deles, que o genético só pode superar
    Avaliacao av_vencedor;
    std::uint64_t taxa_ppm = 0;
    std::int64_t densidade = 0;
    std::uint64_t valores = 0;
};

// Só é chamada com parceiros > 0: sem parceiro não há o que sortear.
inline Preparo preparar(const Instancia& inst, const Parametros& p) {
    Preparo r;
    r.iniciais = {guloso(inst, Criterio::Razao), guloso(inst, Criterio::Ganho)};
    const auto n = static_cast<std::uint64_t>(inst.parceiros);
    r.taxa_ppm = std::max<std::uint64_t>(1, static_cast<std::uint64_t>(p.mutacoes_por_filho) * MILHAO / n);
    std::int64_t soma_custos = 0;
    for (auto c : inst.custo) soma_custos += c;
    r.densidade = std::min<std::int64_t>(inst.maximo_acoes, inst.orcamento * inst.acoes / soma_custos);
    r.valores = static_cast<std::uint64_t>(inst.acoes + 1);

    const std::vector<Avaliacao> av = {avaliar(inst, r.iniciais[0].data()), avaliar(inst, r.iniciais[1].data())};
    const int primeiro = indice_do_melhor(av);
    r.vencedor = r.iniciais[primeiro];
    r.av_vencedor = av[primeiro];
    return r;
}

// Os gulosos são viáveis e o elitismo nunca perde o melhor deles: chegar ao fim
// com um vencedor inviável seria defeito do algoritmo.
inline void conferir_vencedor(const Avaliacao& av) {
    if (!av.viavel()) throw std::logic_error("O genético terminou com um plano inviável.");
}

}  // namespace gih::genetico
