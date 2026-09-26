// A GPU vista do resto do núcleo — H54a, H56, ADR-006, ADR-012.
//
// Este cabeçalho não inclui nada do CUDA: `main.cpp` o usa do mesmo jeito com
// e sem o toolkit. Quem implementa é `gpu.cu`, compilado só quando há CUDA
// (`GIH_COM_CUDA`); sem ele, `sem_gpu.cpp` responde que não há GPU. É isso que
// deixa o núcleo compilar e rodar em qualquer máquina (RNF06): a CI e quem não
// tem placa NVIDIA compilam só os `.cpp`.
#pragma once

#include <cstddef>
#include <stdexcept>
#include <string>
#include <vector>

#include "nucleo.hpp"

namespace gih::gpu {

struct Dispositivo {
    std::string nome;
    int capacidade_maior = 0;  // a "compute capability", 8.9 na RTX 4060
    int capacidade_menor = 0;
    std::size_t memoria = 0;  // bytes
};

// A GPU que o otimizador usaria, ou por que não há uma: executável compilado sem
// CUDA, nenhuma placa NVIDIA visível, driver antigo demais para o runtime. Nunca
// lança: é o que `gih-nucleo versao` pergunta toda vez que a API quer saber os
// modos (ADR-012).
bool procurar(Dispositivo& dispositivo, std::string& motivo);

// Sem GPU, as operações que precisam dela recusam com esta exceção — e o
// executável, com a saída 1, que é o sinal para a API cair para a CPU (H56).
class SemGpu : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

// A ida e volta da H54a: a instância e a população vão para a GPU, voltam, e
// são conferidas contra as originais — byte a byte, e por uma conta feita no
// próprio dispositivo com o layout que o kernel da H54b vai ler.
struct Transferencia {
    std::size_t bytes_instancia = 0;
    std::size_t bytes_populacao = 0;
    std::vector<double> envio_ms;  // instância e população, host → GPU, uma por repetição
    std::vector<double> volta_ms;  // a população inteira, GPU → host
    std::vector<double> volta_um_ms;  // um indivíduo: o que o laço na GPU devolve (H54c)
    bool identica = false;  // o que voltou é o que foi, byte a byte
    bool conferida = false;  // a conta feita na GPU bate com `avaliar` na CPU
};

// `populacao` tem `individuos × parceiros` genes, indivíduo depois de indivíduo.
Transferencia ida_e_volta(const Instancia& inst, const std::vector<Gene>& populacao, int individuos,
                          int repeticoes);

}  // namespace gih::gpu
