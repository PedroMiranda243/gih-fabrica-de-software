// A avaliação de uma solução e a comparação por viabilidade — reproduz
// `gih_nucleo/problema.py` (`avaliar`, `melhor`, `acao_mais_barata`).
#include <algorithm>

#include "nucleo.hpp"

namespace gih {

int Instancia::acao_mais_barata() const {
    int barata = 0;
    for (int a = 1; a < acoes; ++a) {
        if (custo[a] < custo[barata]) barata = a;  // `<` estrito: no empate fica o menor índice
    }
    return barata;
}

Avaliacao avaliar(const Instancia& inst, const Gene* genes) {
    Avaliacao av;
    av.por_categoria.assign(static_cast<std::size_t>(inst.categorias), 0);
    for (int i = 0; i < inst.parceiros; ++i) {
        const int g = genes[i];
        if (g == 0) continue;
        av.ganho += inst.ganho_de(i, g - 1);
        av.custo += inst.custo[g - 1];
        av.acoes += 1;
        const int k = inst.categoria[i];
        if (k >= 0) av.por_categoria[k] += 1;
        if (inst.cauda[i]) av.cauda += 1;
    }

    av.violacao = std::max<std::int64_t>(0, av.acoes - inst.maximo_acoes)
                + std::max<std::int64_t>(0, inst.minimo_cauda - av.cauda);
    for (int k = 0; k < inst.categorias; ++k) {
        const std::int64_t n = av.por_categoria[k];
        av.violacao += std::max<std::int64_t>(0, inst.minimo_categoria[k] - n)
                     + std::max<std::int64_t>(0, n - inst.maximo_categoria[k]);
    }
    const std::int64_t excesso = av.custo - inst.orcamento;
    if (excesso > 0) {
        const std::int64_t barata = inst.custo[inst.acao_mais_barata()];
        av.violacao += (excesso + barata - 1) / barata;  // divisão para cima, os dois positivos
    }
    return av;
}

bool melhor(const Avaliacao& a, const Avaliacao& b) {
    if (a.viavel() != b.viavel()) return a.viavel();
    if (a.viavel()) return a.ganho > b.ganho;
    if (a.violacao != b.violacao) return a.violacao < b.violacao;
    return a.ganho > b.ganho;
}

}  // namespace gih
