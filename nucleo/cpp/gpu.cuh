// As estruturas de dados na GPU — H54a, ADR-006, ADR-011.
//
// Só entra em `.cu`: é o lado do dispositivo, com o runtime do CUDA. O resto do
// núcleo conversa com a GPU por `gpu.hpp`.
//
// **O layout é o da CPU, de propósito.** O ganho é a mesma tabela achatada
// `[parceiro × ações]` em centavos inteiros; a população, os mesmos genes de um
// byte, indivíduo depois de indivíduo. Nada de reordenar para a GPU "por
// desempenho" antes de medir: o que a H54b precisa é ler exatamente o que a CPU
// lê, para dar exatamente o mesmo resultado (ADR-011).
//
// **A população mora na GPU a busca inteira** (ADR-006, H54c). No spike, mandar
// e trazer a população a cada geração foi 88% do tempo; por isso ela tem dois
// buffers — a geração atual e a seguinte, que o laço escreve — trocados por
// ponteiro, e só o melhor indivíduo volta no fim.
#pragma once

#include <cuda_runtime.h>

#include <cstdint>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "nucleo.hpp"

namespace gih::gpu {

inline void checar(cudaError_t erro, const char* chamada) {
    if (erro != cudaSuccess) {
        throw std::runtime_error(std::string("CUDA falhou em ") + chamada + ": " + cudaGetErrorString(erro));
    }
}

#define GIH_CUDA(chamada) ::gih::gpu::checar((chamada), #chamada)

// Memória da GPU com dono: liberada no destrutor, também quando uma exceção
// atravessa — sem isso, cada falha deixaria memória presa na placa até o
// processo acabar.
template <typename T>
class Memoria {
public:
    Memoria() = default;
    explicit Memoria(std::size_t n) : n_(n) {
        if (n_ > 0) GIH_CUDA(cudaMalloc(reinterpret_cast<void**>(&p_), bytes()));
    }
    ~Memoria() {
        if (p_ != nullptr) cudaFree(p_);
    }
    Memoria(const Memoria&) = delete;
    Memoria& operator=(const Memoria&) = delete;
    Memoria(Memoria&& outra) noexcept : p_(std::exchange(outra.p_, nullptr)), n_(std::exchange(outra.n_, 0)) {}
    Memoria& operator=(Memoria&& outra) noexcept {
        std::swap(p_, outra.p_);
        std::swap(n_, outra.n_);
        return *this;
    }

    T* dados() const { return p_; }
    std::size_t tamanho() const { return n_; }
    std::size_t bytes() const { return n_ * sizeof(T); }

    void enviar(const T* origem) {
        if (n_ > 0) GIH_CUDA(cudaMemcpy(p_, origem, bytes(), cudaMemcpyHostToDevice));
    }
    std::vector<T> trazer() const {
        std::vector<T> destino(n_);
        if (n_ > 0) GIH_CUDA(cudaMemcpy(destino.data(), p_, bytes(), cudaMemcpyDeviceToHost));
        return destino;
    }

private:
    T* p_ = nullptr;
    std::size_t n_ = 0;
};

// O que um kernel recebe da instância, por valor: ponteiros para a memória da
// GPU e os escalares. Só tipos simples, para caber nos parâmetros do kernel.
struct VisaoDaInstancia {
    const std::int64_t* ganho;  // [parceiro * acoes + acao], centavos
    const std::int64_t* custo;  // [acao]
    const int* categoria;  // [parceiro], SEM_CATEGORIA quando não confirmada
    const char* cauda;  // [parceiro]
    const std::int64_t* minimo_categoria;  // [categoria]
    const std::int64_t* maximo_categoria;
    int parceiros;
    int acoes;
    int categorias;
    std::int64_t orcamento;
    std::int64_t maximo_acoes;
    std::int64_t minimo_cauda;
    std::int64_t custo_mais_barato;  // a unidade da violação de orçamento (ADR-011)
};

// A instância na GPU: enviada uma vez, antes da busca, e só lida depois.
class InstanciaNaGpu {
public:
    explicit InstanciaNaGpu(const Instancia& inst)
        : inst_(inst),
          ganho_(inst.ganho.size()),
          custo_(inst.custo.size()),
          categoria_(inst.categoria.size()),
          cauda_(inst.cauda.size()),
          minimo_(inst.minimo_categoria.size()),
          maximo_(inst.maximo_categoria.size()) {
        enviar();
    }

    // De novo, de propósito: é o que a medição da H54a repete.
    void enviar() {
        ganho_.enviar(inst_.ganho.data());
        custo_.enviar(inst_.custo.data());
        categoria_.enviar(inst_.categoria.data());
        cauda_.enviar(inst_.cauda.data());
        minimo_.enviar(inst_.minimo_categoria.data());
        maximo_.enviar(inst_.maximo_categoria.data());
    }

    // O que voltou é o que foi? Cada vetor trazido de volta e comparado.
    bool identica() const {
        return ganho_.trazer() == inst_.ganho && custo_.trazer() == inst_.custo &&
               categoria_.trazer() == inst_.categoria && cauda_.trazer() == inst_.cauda &&
               minimo_.trazer() == inst_.minimo_categoria && maximo_.trazer() == inst_.maximo_categoria;
    }

    std::size_t bytes() const {
        return ganho_.bytes() + custo_.bytes() + categoria_.bytes() + cauda_.bytes() + minimo_.bytes() +
               maximo_.bytes();
    }

    VisaoDaInstancia visao() const {
        return {ganho_.dados(),
                custo_.dados(),
                categoria_.dados(),
                cauda_.dados(),
                minimo_.dados(),
                maximo_.dados(),
                inst_.parceiros,
                inst_.acoes,
                inst_.categorias,
                inst_.orcamento,
                inst_.maximo_acoes,
                inst_.minimo_cauda,
                inst_.custo[inst_.acao_mais_barata()]};
    }

private:
    const Instancia& inst_;
    Memoria<std::int64_t> ganho_;
    Memoria<std::int64_t> custo_;
    Memoria<int> categoria_;
    Memoria<char> cauda_;
    Memoria<std::int64_t> minimo_;
    Memoria<std::int64_t> maximo_;
};

// A população de todas as partidas, contígua — partida, indivíduo, gene —, em
// dois buffers: a geração atual e a seguinte, que o laço escreve (H54c).
class PopulacaoNaGpu {
public:
    PopulacaoNaGpu(int individuos, int parceiros)
        : individuos_(individuos),
          parceiros_(parceiros),
          atual_(static_cast<std::size_t>(individuos) * parceiros),
          seguinte_(atual_.tamanho()) {}

    Gene* atual() const { return atual_.dados(); }
    Gene* seguinte() const { return seguinte_.dados(); }
    // Fim de geração: a seguinte vira a atual, sem copiar um byte.
    void trocar() { std::swap(atual_, seguinte_); }

    void enviar(const std::vector<Gene>& populacao) { atual_.enviar(populacao.data()); }
    std::vector<Gene> trazer() const { return atual_.trazer(); }

    // Um indivíduo só: no laço completo, é o único que volta (H54c).
    std::vector<Gene> trazer_individuo(int j) const {
        std::vector<Gene> genes(static_cast<std::size_t>(parceiros_));
        if (parceiros_ > 0) {
            GIH_CUDA(cudaMemcpy(genes.data(), atual_.dados() + static_cast<std::size_t>(j) * parceiros_,
                                genes.size(), cudaMemcpyDeviceToHost));
        }
        return genes;
    }

    int individuos() const { return individuos_; }
    int parceiros() const { return parceiros_; }
    std::size_t bytes() const { return atual_.bytes(); }  // de uma geração

private:
    int individuos_;
    int parceiros_;
    Memoria<Gene> atual_;
    Memoria<Gene> seguinte_;
};

}  // namespace gih::gpu
