// O genético com OpenMP (H53b): o mesmo plano da versão serial, com os filhos
// calculados em paralelo.
//
// **O que se paraleliza são os filhos, de todas as partidas de uma vez.** Na
// versão serial as partidas rodam uma depois da outra. Aqui elas avançam juntas,
// uma geração por vez, e os filhos de todas elas formam um único laço paralelo.
// Com os parâmetros padrão são 4 × 47 = 188 filhos independentes por geração.
// As alternativas eram piores:
// - paralelizar só as partidas ocuparia no máximo 4 threads;
// - paralelizar só os filhos de uma partida daria 47 tarefas por laço, e quatro
//   vezes mais sincronizações.
//
// **Por que o plano é o mesmo.** Cada filho depende só da geração anterior da
// sua partida e do sorteio das suas coordenadas (ADR-011). Nenhum filho lê o que
// outro escreve na mesma geração: a leitura é de `pop` e `av`, a escrita é em
// `nova` e `novas`, cada filho na sua posição. A ordem em que as threads calculam
// não muda nada. No fim, as partidas são percorridas na ordem, com a mesma
// comparação estrita da serial; no empate, fica a de menor índice, como lá.
//
// **O limite de tempo é a única diferença visível.** Na serial, a busca
// interrompida encerra a partida em curso e não começa as seguintes. Aqui todas
// param na mesma geração. As duas devolvem o melhor plano viável encontrado e
// marcam `parcial`, e nenhuma busca interrompida se repete, em modo nenhum,
// porque depende do relógio.
#include <algorithm>

#ifdef _OPENMP
#include <omp.h>
#endif

#include "genetico.hpp"
#include "nucleo.hpp"

namespace gih {

using namespace genetico;

int threads_openmp() {
#ifdef _OPENMP
    return omp_get_max_threads();
#else
    return 0;
#endif
}

Resultado otimizar_openmp(const Instancia& inst, const Parametros& p) {
    conferir(p);
    if (p.threads < 0) throw std::invalid_argument("O número de threads não pode ser negativo.");
    if (threads_openmp() == 0) throw std::invalid_argument("Este executável foi compilado sem OpenMP.");
    const Cronometro relogio(p.limite_ms);
    const int n = inst.parceiros;
    Resultado r;
    r.threads = p.threads > 0 ? p.threads : threads_openmp();
    if (n == 0) {
        r.avaliacao = avaliar(inst, nullptr);
        r.segundos = relogio.segundos();
        return r;
    }

    Preparo prep = preparar(inst, p);
    const auto un = static_cast<std::uint64_t>(n);
    const int partidas = p.partidas;
    const int tamanho = p.populacao;
    const int n_iniciais = std::min<int>(2, tamanho);

    // Uma população por partida, e duas de cada, como na serial.
    std::vector<std::vector<Gene>> pop(static_cast<std::size_t>(partidas),
                                       std::vector<Gene>(static_cast<std::size_t>(tamanho) * n));
    std::vector<std::vector<Gene>> nova = pop;
    std::vector<std::vector<Avaliacao>> av(static_cast<std::size_t>(partidas),
                                           std::vector<Avaliacao>(static_cast<std::size_t>(tamanho)));
    std::vector<std::vector<Avaliacao>> novas = av;

    // A população inicial de todas as partidas. `t` percorre partida e indivíduo
    // num índice só: o laço paralelo do OpenMP 2.0, o do MSVC, aceita um índice só.
    //
    // **Escalonamento dinâmico, uma tarefa por vez**, nos dois laços. Os filhos
    // custam todos o mesmo, e a divisão estática pareceria a natural; medida no
    // contêiner, ela perdeu em todos os tamanhos (6,0x contra 5,1x com 2.000
    // parceiros e 8 threads, na mediana). Cada geração termina numa barreira,
    // e na divisão estática ela espera a thread mais atrasada: no WSL2, os
    // processadores virtuais são divididos com o Windows, e em 150 gerações
    // sempre há um que atrasa. No dinâmico, quem termina pega o próximo filho.
    // O custo é um incremento atômico por filho, contra ~10 µs de cálculo.
    const int inicial = partidas * tamanho;
#ifdef _OPENMP
#pragma omp parallel for schedule(dynamic, 1) num_threads(r.threads)
#endif
    for (int t = 0; t < inicial; ++t) {
        const int partida = t / tamanho, j = t % tamanho;
        Gene* genes = individuo(pop[partida], j, n);
        if (j < n_iniciais) {
            std::copy(prep.iniciais[j].begin(), prep.iniciais[j].end(), genes);
        } else {
            sorteado(inst, sorteio(p.semente, static_cast<std::uint64_t>(partida), 0, static_cast<std::uint64_t>(j)),
                     prep.densidade, genes);
        }
        av[partida][j] = avaliar(inst, genes);
    }
    r.partidas = partidas;

    const int filhos = tamanho - 1;
    const int por_geracao = partidas * filhos;
    for (int g = 1; g <= p.geracoes; ++g) {
        if (relogio.estourou()) {
            r.parcial = true;
            break;
        }
        // A elite de cada partida vai para a posição 0. São poucas cópias, e
        // fazê-las antes do laço deixa todas as tarefas dele do mesmo tamanho.
        for (int partida = 0; partida < partidas; ++partida) {
            const int elite = indice_do_melhor(av[partida]);
            const Gene* origem = individuo(pop[partida], elite, n);
            std::copy(origem, origem + n, individuo(nova[partida], 0, n));
            novas[partida][0] = av[partida][elite];
        }
#ifdef _OPENMP
#pragma omp parallel for schedule(dynamic, 1) num_threads(r.threads)
#endif
        for (int t = 0; t < por_geracao; ++t) {
            const int partida = t / filhos, j = 1 + t % filhos;
            const std::vector<Avaliacao>& anteriores = av[partida];
            const std::uint64_t base = sorteio(p.semente, static_cast<std::uint64_t>(partida),
                                               static_cast<std::uint64_t>(g), static_cast<std::uint64_t>(j));
            const int pai = torneio(anteriores, encadear(base, un), encadear(base, un + 1));
            const int mae = torneio(anteriores, encadear(base, un + 2), encadear(base, un + 3));
            Gene* saida = individuo(nova[partida], j, n);
            filho(individuo(pop[partida], pai, n), individuo(pop[partida], mae, n), n, base, prep.taxa_ppm,
                  prep.valores, saida);
            novas[partida][j] = avaliar(inst, saida);
        }
        std::swap(pop, nova);
        std::swap(av, novas);
        r.geracoes += partidas;
    }

    for (int partida = 0; partida < partidas; ++partida) {
        const int m = indice_do_melhor(av[partida]);
        if (melhor(av[partida][m], prep.av_vencedor)) {
            const Gene* genes = individuo(pop[partida], m, n);
            prep.vencedor.assign(genes, genes + n);
            prep.av_vencedor = av[partida][m];
        }
    }

    conferir_vencedor(prep.av_vencedor);
    r.genes = std::move(prep.vencedor);
    r.avaliacao = prep.av_vencedor;
    r.segundos = relogio.segundos();
    return r;
}

}  // namespace gih
