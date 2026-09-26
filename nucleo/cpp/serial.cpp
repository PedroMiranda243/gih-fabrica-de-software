// O genético serial em C++ — reproduz `gih_nucleo/serial.py` (`otimizar`), sorteio
// a sorteio. É a base das versões OpenMP (H53b) e CUDA (H54): as três fazem a
// mesma sequência, e só o que muda é quem calcula cada filho.
#include <algorithm>
#include <chrono>
#include <stdexcept>

#include "nucleo.hpp"

namespace gih {
namespace {

std::uint64_t sorteio(std::uint64_t semente, std::uint64_t partida, std::uint64_t geracao,
                      std::uint64_t individuo) {
    return encadear(encadear(encadear(encadear(0, semente), partida), geracao), individuo);
}

int torneio(const std::vector<Avaliacao>& av, std::uint64_t h1, std::uint64_t h2) {
    const auto p = static_cast<std::uint64_t>(av.size());
    const auto r1 = static_cast<int>(h1 % p), r2 = static_cast<int>(h2 % p);
    return melhor(av[r2], av[r1]) ? r2 : r1;  // no empate, o primeiro sorteado
}

int indice_do_melhor(const std::vector<Avaliacao>& av) {
    int escolhido = 0;
    for (int j = 1; j < static_cast<int>(av.size()); ++j) {
        if (melhor(av[j], av[escolhido])) escolhido = j;
    }
    return escolhido;
}

void sorteado(const Instancia& inst, std::uint64_t base, std::int64_t densidade, Gene* genes) {
    const auto n = static_cast<std::uint64_t>(inst.parceiros);
    const auto a = static_cast<std::uint64_t>(inst.acoes);
    for (int i = 0; i < inst.parceiros; ++i) {
        const std::uint64_t h = encadear(base, static_cast<std::uint64_t>(i));
        genes[i] = (h % n) < static_cast<std::uint64_t>(densidade) ? static_cast<Gene>(1 + (h >> 32) % a) : 0;
    }
}

void filho(const Gene* pai, const Gene* mae, int n, std::uint64_t base, std::uint64_t taxa_ppm,
           std::uint64_t valores, Gene* saida) {
    for (int i = 0; i < n; ++i) {
        const std::uint64_t h = encadear(base, static_cast<std::uint64_t>(i));
        Gene gene = (h & 1) ? mae[i] : pai[i];
        if ((h >> 1) % MILHAO < taxa_ppm) gene = static_cast<Gene>((h >> 21) % valores);
        saida[i] = gene;
    }
}

}  // namespace

Resultado otimizar_serial(const Instancia& inst, const Parametros& p) {
    if (p.populacao < 2 || p.partidas < 1 || p.geracoes < 0) {
        throw std::invalid_argument("A busca precisa de ao menos 2 indivíduos, 1 partida e 0 gerações.");
    }
    using Relogio = std::chrono::steady_clock;
    const auto inicio = Relogio::now();
    auto passou_do_limite = [&] {
        if (p.limite_ms < 0) return false;
        const auto decorrido = std::chrono::duration_cast<std::chrono::milliseconds>(Relogio::now() - inicio);
        return decorrido.count() > p.limite_ms;
    };

    const int n = inst.parceiros;
    const std::vector<std::vector<Gene>> iniciais = {guloso(inst, Criterio::Razao), guloso(inst, Criterio::Ganho)};
    Resultado r;
    if (n == 0) {
        r.avaliacao = avaliar(inst, nullptr);
        r.segundos = std::chrono::duration<double>(Relogio::now() - inicio).count();
        return r;
    }

    const std::uint64_t taxa_ppm =
        std::max<std::uint64_t>(1, static_cast<std::uint64_t>(p.mutacoes_por_filho) * MILHAO / static_cast<std::uint64_t>(n));
    std::int64_t soma_custos = 0;
    for (auto c : inst.custo) soma_custos += c;
    const std::int64_t densidade = std::min<std::int64_t>(inst.maximo_acoes, inst.orcamento * inst.acoes / soma_custos);
    const auto valores = static_cast<std::uint64_t>(inst.acoes + 1);
    const auto un = static_cast<std::uint64_t>(n);

    std::vector<Avaliacao> av_iniciais = {avaliar(inst, iniciais[0].data()), avaliar(inst, iniciais[1].data())};
    const int primeiro = indice_do_melhor(av_iniciais);
    std::vector<Gene> vencedor = iniciais[primeiro];
    Avaliacao av_vencedor = av_iniciais[primeiro];

    const int tamanho = p.populacao;
    // Duas populações contíguas, que trocam de papel a cada geração: sem uma
    // alocação por filho, que em C++ custaria mais que o próprio cálculo.
    std::vector<Gene> pop(static_cast<std::size_t>(tamanho) * n), nova(pop.size());
    std::vector<Avaliacao> av(static_cast<std::size_t>(tamanho)), novas(av.size());
    auto individuo = [n](std::vector<Gene>& v, int j) { return v.data() + static_cast<std::size_t>(j) * n; };

    for (int partida = 0; partida < p.partidas; ++partida) {
        r.partidas += 1;
        const int n_iniciais = std::min<int>(2, tamanho);
        for (int j = 0; j < n_iniciais; ++j) std::copy(iniciais[j].begin(), iniciais[j].end(), individuo(pop, j));
        for (int j = n_iniciais; j < tamanho; ++j) {
            sorteado(inst, sorteio(p.semente, static_cast<std::uint64_t>(partida), 0, static_cast<std::uint64_t>(j)),
                     densidade, individuo(pop, j));
        }
        for (int j = 0; j < tamanho; ++j) av[j] = avaliar(inst, individuo(pop, j));

        for (int g = 1; g <= p.geracoes; ++g) {
            if (passou_do_limite()) {
                r.parcial = true;
                break;
            }
            const int elite = indice_do_melhor(av);
            std::copy(individuo(pop, elite), individuo(pop, elite) + n, individuo(nova, 0));
            novas[0] = av[elite];
            for (int j = 1; j < tamanho; ++j) {
                const std::uint64_t base = sorteio(p.semente, static_cast<std::uint64_t>(partida),
                                                   static_cast<std::uint64_t>(g), static_cast<std::uint64_t>(j));
                const int pai = torneio(av, encadear(base, un), encadear(base, un + 1));
                const int mae = torneio(av, encadear(base, un + 2), encadear(base, un + 3));
                filho(individuo(pop, pai), individuo(pop, mae), n, base, taxa_ppm, valores, individuo(nova, j));
                novas[j] = avaliar(inst, individuo(nova, j));
            }
            std::swap(pop, nova);
            std::swap(av, novas);
            r.geracoes += 1;
        }

        const int melhor_da_partida = indice_do_melhor(av);
        if (melhor(av[melhor_da_partida], av_vencedor)) {
            vencedor.assign(individuo(pop, melhor_da_partida), individuo(pop, melhor_da_partida) + n);
            av_vencedor = av[melhor_da_partida];
        }
        if (r.parcial) break;
    }

    // Os gulosos são viáveis e o elitismo nunca perde o melhor deles: chegar
    // aqui com um vencedor inviável seria defeito do algoritmo.
    if (!av_vencedor.viavel()) throw std::logic_error("O genético terminou com um plano inviável.");
    r.genes = std::move(vencedor);
    r.avaliacao = av_vencedor;
    r.segundos = std::chrono::duration<double>(Relogio::now() - inicio).count();
    return r;
}

}  // namespace gih
