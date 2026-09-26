// Os dois planos gulosos — reproduz `gih_nucleo/guloso.py` (`completar`, `guloso`).
#include <algorithm>
#include <utility>

#include "nucleo.hpp"

namespace gih {
namespace {

// O produto `a·b` em 128 bits, sem `__int128`: o MSVC não tem, e a razão
// ganho/custo é comparada por produto cruzado. Com ganho e custo em centavos, o
// produto passa de 64 bits a partir de ~R$ 30 milhões × R$ 30 milhões — longe
// do uso, mas o Python não estoura nunca, e o porte precisa responder igual.
struct U128 {
    std::uint64_t alto;
    std::uint64_t baixo;
};

U128 multiplicar(std::uint64_t a, std::uint64_t b) {
    const std::uint64_t a0 = a & 0xFFFFFFFFULL, a1 = a >> 32;
    const std::uint64_t b0 = b & 0xFFFFFFFFULL, b1 = b >> 32;
    const std::uint64_t p00 = a0 * b0, p01 = a0 * b1, p10 = a1 * b0, p11 = a1 * b1;
    const std::uint64_t meio = (p00 >> 32) + (p01 & 0xFFFFFFFFULL) + (p10 & 0xFFFFFFFFULL);
    return {p11 + (p01 >> 32) + (p10 >> 32) + (meio >> 32), (meio << 32) | (p00 & 0xFFFFFFFFULL)};
}

// -1, 0 ou 1, como `(a·b > c·d)`… ordenado do maior para o menor.
int decrescente_por_produto(std::int64_t a, std::int64_t b, std::int64_t c, std::int64_t d) {
    const U128 x = multiplicar(static_cast<std::uint64_t>(a), static_cast<std::uint64_t>(b));
    const U128 y = multiplicar(static_cast<std::uint64_t>(c), static_cast<std::uint64_t>(d));
    if (x.alto != y.alto) return x.alto > y.alto ? -1 : 1;
    if (x.baixo != y.baixo) return x.baixo > y.baixo ? -1 : 1;
    return 0;
}

int decrescente(std::int64_t x, std::int64_t y) {
    if (x == y) return 0;
    return x > y ? -1 : 1;
}

std::vector<Gene> completar(const Instancia& inst, std::vector<Gene> genes, Criterio criterio) {
    std::int64_t custo = 0, acoes = 0;
    std::vector<std::int64_t> por_categoria(static_cast<std::size_t>(inst.categorias), 0);
    for (int i = 0; i < inst.parceiros; ++i) {
        if (!genes[i]) continue;
        custo += inst.custo[genes[i] - 1];
        acoes += 1;
        if (inst.categoria[i] >= 0) por_categoria[inst.categoria[i]] += 1;
    }

    std::vector<std::pair<int, int>> pares;
    for (int i = 0; i < inst.parceiros; ++i) {
        if (genes[i]) continue;
        for (int a = 0; a < inst.acoes; ++a) {
            if (inst.ganho_de(i, a) > 0) pares.emplace_back(i, a);
        }
    }

    // Um critério desempata o outro; depois, menor parceiro e menor ação — a
    // ordem é total, e por isso o `sort` chega à mesma sequência do `sorted`.
    auto pela_razao = [&](const std::pair<int, int>& p, const std::pair<int, int>& q) {
        return decrescente_por_produto(inst.ganho_de(p.first, p.second), inst.custo[q.second],
                                       inst.ganho_de(q.first, q.second), inst.custo[p.second]);
    };
    auto pelo_ganho = [&](const std::pair<int, int>& p, const std::pair<int, int>& q) {
        return decrescente(inst.ganho_de(p.first, p.second), inst.ganho_de(q.first, q.second));
    };
    std::sort(pares.begin(), pares.end(), [&](const auto& p, const auto& q) {
        int r = criterio == Criterio::Razao ? pela_razao(p, q) : pelo_ganho(p, q);
        if (r == 0) r = criterio == Criterio::Razao ? pelo_ganho(p, q) : pela_razao(p, q);
        if (r != 0) return r < 0;
        return p < q;
    });

    for (const auto& [i, a] : pares) {
        if (genes[i] || acoes >= inst.maximo_acoes) continue;
        if (custo + inst.custo[a] > inst.orcamento) continue;
        const int k = inst.categoria[i];
        if (k >= 0 && por_categoria[k] >= inst.maximo_categoria[k]) continue;
        genes[i] = static_cast<Gene>(a + 1);
        custo += inst.custo[a];
        acoes += 1;
        if (k >= 0) por_categoria[k] += 1;
    }
    return genes;
}

}  // namespace

std::vector<Gene> guloso(const Instancia& inst, Criterio criterio) {
    std::vector<int> minimo;
    Inviabilidade motivo;
    diagnosticar(inst, minimo, motivo);  // quem chama já conferiu que cabe
    std::vector<Gene> genes(static_cast<std::size_t>(inst.parceiros), 0);
    const Gene barata = static_cast<Gene>(inst.acao_mais_barata() + 1);
    for (int i : minimo) genes[i] = barata;
    return completar(inst, std::move(genes), criterio);
}

}  // namespace gih
