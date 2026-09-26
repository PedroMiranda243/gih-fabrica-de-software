// A decisão exata de viabilidade e o menor conjunto que cumpre as cotas —
// reproduz `gih_nucleo/viabilidade.py` (`_diagnosticar`). O porquê de a conta ser
// exata está lá e na `docs/07` §4.1.
#include <algorithm>

#include "nucleo.hpp"

namespace gih {

bool diagnosticar(const Instancia& inst, std::vector<int>& escolhidos, Inviabilidade& motivo) {
    escolhidos.clear();
    const int barata = inst.acao_mais_barata();

    // Os de maior ganho com a ação mais barata primeiro; no empate, o menor índice.
    auto prioridade = [&](int i, int j) {
        const std::int64_t gi = inst.ganho_de(i, barata), gj = inst.ganho_de(j, barata);
        if (gi != gj) return gi > gj;
        return i < j;
    };

    std::vector<std::vector<int>> membros(static_cast<std::size_t>(inst.categorias));
    std::vector<int> reserva_cauda;  // começa com a cauda sem categoria
    for (int i = 0; i < inst.parceiros; ++i) {
        const int k = inst.categoria[i];
        if (k >= 0) {
            membros[k].push_back(i);
        } else if (inst.cauda[i]) {
            reserva_cauda.push_back(i);
        }
    }

    for (int k = 0; k < inst.categorias; ++k) {
        if (inst.minimo_categoria[k] > inst.maximo_categoria[k]) {
            motivo = {"cota_categoria", inst.minimo_categoria[k], inst.maximo_categoria[k], k};
            return false;
        }
    }
    for (int k = 0; k < inst.categorias; ++k) {
        const auto tamanho = static_cast<std::int64_t>(membros[k].size());
        if (inst.minimo_categoria[k] > tamanho) {
            motivo = {"elegiveis_categoria", inst.minimo_categoria[k], tamanho, k};
            return false;
        }
    }

    std::int64_t cobertura = 0;
    for (int k = 0; k < inst.categorias; ++k) {
        std::vector<int> ordem = membros[k];
        std::sort(ordem.begin(), ordem.end(), prioridade);
        std::vector<int> da_cauda, fora_da_cauda;
        for (int i : ordem) (inst.cauda[i] ? da_cauda : fora_da_cauda).push_back(i);

        const std::int64_t minimo = inst.minimo_categoria[k];
        const std::int64_t usados = std::min<std::int64_t>(minimo, static_cast<std::int64_t>(da_cauda.size()));
        escolhidos.insert(escolhidos.end(), da_cauda.begin(), da_cauda.begin() + usados);
        escolhidos.insert(escolhidos.end(), fora_da_cauda.begin(), fora_da_cauda.begin() + (minimo - usados));
        cobertura += usados;

        // A cauda que sobra nesta categoria só completa a cota até o máximo dela.
        const std::int64_t sobra = static_cast<std::int64_t>(da_cauda.size()) - usados;
        const std::int64_t cabem = std::min(sobra, inst.maximo_categoria[k] - minimo);
        reserva_cauda.insert(reserva_cauda.end(), da_cauda.begin() + usados, da_cauda.begin() + usados + cabem);
    }

    const std::int64_t falta_cauda = std::max<std::int64_t>(0, inst.minimo_cauda - cobertura);
    const auto reserva = static_cast<std::int64_t>(reserva_cauda.size());
    if (falta_cauda > reserva) {
        motivo = {"cauda_longa", inst.minimo_cauda, cobertura + reserva, SEM_CATEGORIA};
        return false;
    }
    std::sort(reserva_cauda.begin(), reserva_cauda.end(), prioridade);
    escolhidos.insert(escolhidos.end(), reserva_cauda.begin(), reserva_cauda.begin() + falta_cauda);

    const auto total = static_cast<std::int64_t>(escolhidos.size());
    if (total > inst.maximo_acoes) {
        motivo = {"maximo_acoes", total, inst.maximo_acoes, SEM_CATEGORIA};
        return false;
    }
    const std::int64_t custo = total * inst.custo[barata];
    if (custo > inst.orcamento) {
        motivo = {"orcamento", custo, inst.orcamento, SEM_CATEGORIA};
        return false;
    }
    std::sort(escolhidos.begin(), escolhidos.end());
    return true;
}

}  // namespace gih
