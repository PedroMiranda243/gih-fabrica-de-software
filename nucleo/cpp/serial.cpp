// O genético serial em C++ — reproduz `gih_nucleo/serial.py` (`otimizar`), sorteio
// a sorteio. É a base das versões OpenMP (H53b) e CUDA (H54): as três fazem a
// mesma sequência, e só o que muda é quem calcula cada filho. Os passos
// compartilhados estão em `genetico.hpp`.
#include <algorithm>

#include "genetico.hpp"
#include "nucleo.hpp"

namespace gih {

using namespace genetico;

Resultado otimizar_serial(const Instancia& inst, const Parametros& p) {
    conferir(p);
    const Cronometro relogio(p.limite_ms);
    const int n = inst.parceiros;
    Resultado r;
    if (n == 0) {
        r.avaliacao = avaliar(inst, nullptr);
        r.segundos = relogio.segundos();
        return r;
    }

    Preparo prep = preparar(inst, p);
    const auto un = static_cast<std::uint64_t>(n);
    const int tamanho = p.populacao;
    // Duas populações contíguas, que trocam de papel a cada geração: sem uma
    // alocação por filho, que em C++ custaria mais que o próprio cálculo.
    std::vector<Gene> pop(static_cast<std::size_t>(tamanho) * n), nova(pop.size());
    std::vector<Avaliacao> av(static_cast<std::size_t>(tamanho)), novas(av.size());

    for (int partida = 0; partida < p.partidas; ++partida) {
        r.partidas += 1;
        const int n_iniciais = std::min<int>(2, tamanho);
        for (int j = 0; j < n_iniciais; ++j) {
            std::copy(prep.iniciais[j].begin(), prep.iniciais[j].end(), individuo(pop, j, n));
        }
        for (int j = n_iniciais; j < tamanho; ++j) {
            sorteado(inst, sorteio(p.semente, static_cast<std::uint64_t>(partida), 0, static_cast<std::uint64_t>(j)),
                     prep.densidade, individuo(pop, j, n));
        }
        for (int j = 0; j < tamanho; ++j) av[j] = avaliar(inst, individuo(pop, j, n));

        for (int g = 1; g <= p.geracoes; ++g) {
            if (relogio.estourou()) {
                r.parcial = true;
                break;
            }
            const int elite = indice_do_melhor(av);
            std::copy(individuo(pop, elite, n), individuo(pop, elite, n) + n, individuo(nova, 0, n));
            novas[0] = av[elite];
            for (int j = 1; j < tamanho; ++j) {
                const std::uint64_t base = sorteio(p.semente, static_cast<std::uint64_t>(partida),
                                                   static_cast<std::uint64_t>(g), static_cast<std::uint64_t>(j));
                const int pai = torneio(av, encadear(base, un), encadear(base, un + 1));
                const int mae = torneio(av, encadear(base, un + 2), encadear(base, un + 3));
                filho(individuo(pop, pai, n), individuo(pop, mae, n), n, base, prep.taxa_ppm, prep.valores,
                      individuo(nova, j, n));
                novas[j] = avaliar(inst, individuo(nova, j, n));
            }
            std::swap(pop, nova);
            std::swap(av, novas);
            r.geracoes += 1;
        }

        const int melhor_da_partida = indice_do_melhor(av);
        if (melhor(av[melhor_da_partida], prep.av_vencedor)) {
            prep.vencedor.assign(individuo(pop, melhor_da_partida, n), individuo(pop, melhor_da_partida, n) + n);
            prep.av_vencedor = av[melhor_da_partida];
        }
        if (r.parcial) break;
    }

    conferir_vencedor(prep.av_vencedor);
    r.genes = std::move(prep.vencedor);
    r.avaliacao = prep.av_vencedor;
    r.segundos = relogio.segundos();
    return r;
}

}  // namespace gih
