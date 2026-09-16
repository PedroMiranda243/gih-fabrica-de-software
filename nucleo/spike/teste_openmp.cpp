// Spike de OpenMP — história H47, parte C++.
//
// Mesma carga do spike de GPU: avaliar uma população de planos candidatos,
// somando uplift e custo de cada um e zerando a aptidão dos inviáveis.
//
// Mede a versão serial contra a paralela no mesmo processo, para que o ganho
// reportado seja do paralelismo e não de diferença de linguagem.

#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdint>
#include <vector>

#include <omp.h>

namespace {

struct Cenario {
    std::vector<float> uplift;
    std::vector<float> custo;
    std::vector<uint8_t> populacao;  // [planos * parceiros]
    float orcamento{};
};

// Gerador próprio para o cenário ser idêntico entre as duas medições e entre
// execuções — depender de rand() tornaria a comparação ruidosa.
uint32_t proximo(uint32_t& estado) {
    estado ^= estado << 13;
    estado ^= estado >> 17;
    estado ^= estado << 5;
    return estado;
}

float uniforme(uint32_t& estado, float a, float b) {
    return a + (b - a) * (proximo(estado) / 4294967296.0f);
}

Cenario gerar(int parceiros, int planos, uint32_t semente) {
    uint32_t e = semente;
    Cenario c;
    c.uplift.reserve(parceiros);
    c.custo.reserve(parceiros);
    float soma_custo = 0.0f;
    for (int i = 0; i < parceiros; ++i) {
        c.uplift.push_back(uniforme(e, 50.0f, 5000.0f));
        const float custo = uniforme(e, 20.0f, 800.0f);
        c.custo.push_back(custo);
        soma_custo += custo;
    }
    c.populacao.resize(static_cast<size_t>(planos) * parceiros);
    for (auto& bit : c.populacao) {
        bit = uniforme(e, 0.0f, 1.0f) < 0.15f ? 1 : 0;
    }
    c.orcamento = soma_custo * 0.12f;
    return c;
}

void avaliar(const Cenario& c, int parceiros, int planos,
             std::vector<float>& aptidao, std::vector<float>& custo_total,
             bool paralelo) {
#pragma omp parallel for schedule(static) if (paralelo)
    for (int plano = 0; plano < planos; ++plano) {
        const uint8_t* selecao = c.populacao.data() + static_cast<size_t>(plano) * parceiros;
        float soma_uplift = 0.0f;
        float soma_custo = 0.0f;
        for (int i = 0; i < parceiros; ++i) {
            if (selecao[i]) {
                soma_uplift += c.uplift[i];
                soma_custo += c.custo[i];
            }
        }
        custo_total[plano] = soma_custo;
        // Estourou o orçamento: plano inviável não compete (RN07).
        aptidao[plano] = (soma_custo <= c.orcamento) ? soma_uplift : 0.0f;
    }
}

// Tempo medio de uma avaliacao da populacao.
//
// Repeticao fixa nao serve: nos tamanhos pequenos cada passada dura menos de um
// milissegundo e a medicao vira ruido de relogio — com cinco repeticoes, o ganho
// de 1024 planos oscilou entre 7,5x e 13,9x no mesmo cenario. Aqui se calibra
// quantas repeticoes cabem em ALVO_MS e so entao se mede.
double medir(const Cenario& c, int parceiros, int planos, bool paralelo,
             std::vector<float>& aptidao) {
    constexpr double ALVO_MS = 300.0;
    std::vector<float> custo_total(planos);

    // Aquecimento: a primeira passada paga o toque inicial das paginas de
    // memoria e a criacao do pool de threads do OpenMP.
    auto inicio = std::chrono::steady_clock::now();
    avaliar(c, parceiros, planos, aptidao, custo_total, paralelo);
    auto fim = std::chrono::steady_clock::now();
    const double uma = std::chrono::duration<double, std::milli>(fim - inicio).count();

    int repeticoes = static_cast<int>(ALVO_MS / (uma > 0.001 ? uma : 0.001));
    if (repeticoes < 3) repeticoes = 3;
    if (repeticoes > 20000) repeticoes = 20000;

    inicio = std::chrono::steady_clock::now();
    for (int r = 0; r < repeticoes; ++r) {
        avaliar(c, parceiros, planos, aptidao, custo_total, paralelo);
    }
    fim = std::chrono::steady_clock::now();
    return std::chrono::duration<double, std::milli>(fim - inicio).count() / repeticoes;
}

}  // namespace

int main() {
    const int parceiros = 2000;  // cenário de referência do RNF01

    std::printf("Threads disponiveis: %d\n\n", omp_get_max_threads());
    std::printf("%8s %12s %12s %10s  %s\n", "planos", "serial ms", "OpenMP ms", "ganho", "confere");
    std::printf("---------------------------------------------------------\n");

    for (int planos : {256, 1024, 4096, 16384, 65536}) {
        const Cenario c = gerar(parceiros, planos, 42u);

        std::vector<float> apt_serial(planos), apt_paralelo(planos);
        const double t_serial = medir(c, parceiros, planos, false, apt_serial);
        const double t_paralelo = medir(c, parceiros, planos, true, apt_paralelo);

        // Cada plano é somado pela mesma thread na mesma ordem, então aqui a
        // igualdade pode ser exata — diferente da comparação com a GPU.
        bool confere = true;
        for (int i = 0; i < planos && confere; ++i) {
            confere = apt_serial[i] == apt_paralelo[i];
        }

        std::printf("%8d %12.2f %12.2f %9.1fx  %s\n", planos, t_serial, t_paralelo,
                    t_serial / t_paralelo, confere ? "sim" : "NAO");
    }
    return 0;
}
