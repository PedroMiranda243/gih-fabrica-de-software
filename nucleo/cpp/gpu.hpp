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

// O executável foi compilado com CUDA? É o que põe o modo `cuda` na lista de
// `gih-nucleo versao` (H54c). Se há placa nesta máquina, quem diz é `procurar`.
#ifdef GIH_COM_CUDA
constexpr bool COM_CUDA = true;
#else
constexpr bool COM_CUDA = false;
#endif

struct Dispositivo {
    std::string nome;
    int capacidade_maior = 0;  // a "compute capability", 8.9 na RTX 4060
    int capacidade_menor = 0;
    std::size_t memoria = 0;  // bytes
};

// Por que não há GPU, num código que a API traduz para quem está na tela (H56):
// a mensagem do runtime do CUDA serve a quem investiga, e não ao gestor.
enum class Ausencia {
    SemCuda,  // o executável foi compilado sem CUDA
    SemPlaca,  // nenhuma placa NVIDIA visível: sem placa, sem driver, contêiner sem `--gpus`
    Erro,  // a placa existe, e o runtime falhou ao falar com ela
};

inline const char* codigo(Ausencia ausencia) {
    switch (ausencia) {
        case Ausencia::SemCuda: return "sem_cuda";
        case Ausencia::SemPlaca: return "sem_placa";
        case Ausencia::Erro: return "erro";
    }
    return "erro";
}

// A GPU que o otimizador usaria, ou por que não há uma. Nunca lança: é o que
// `gih-nucleo versao` pergunta toda vez que a API quer saber os modos (ADR-012).
bool procurar(Dispositivo& dispositivo, Ausencia& ausencia, std::string& motivo);

// Sem GPU, as operações que precisam dela recusam com esta exceção — e o
// executável, com a saída 1, que é o sinal para a API cair para a CPU (H56).
// Vale também para a placa que some ou fica sem memória no meio da busca
// (`checar`, em `gpu.cuh`): para quem pediu, é a mesma falta de GPU.
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

// A avaliação da população inteira na GPU (H54b): as mesmas contas de
// `avaliar`, em inteiros, e por isso o mesmo resultado (ADR-011). O tempo é só o
// do kernel, medido pela própria GPU; a transferência é a da H54a.
struct PopulacaoAvaliada {
    std::vector<Avaliacao> avaliacoes;  // uma por indivíduo, na ordem da população
    std::vector<double> kernel_ms;  // uma por repetição
};

PopulacaoAvaliada avaliar_na_gpu(const Instancia& inst, const std::vector<Gene>& populacao, int individuos,
                                 int repeticoes);

// O genético inteiro na GPU (H54c): o mesmo plano, a mesma avaliação e as
// mesmas gerações da versão OpenMP, e da serial sem limite de tempo. A
// população nasce e fica na placa a busca inteira (ADR-006); só as avaliações
// da última geração e o plano vencedor voltam. Sem GPU, `SemGpu`.
Resultado otimizar_na_gpu(const Instancia& inst, const Parametros& p);

}  // namespace gih::gpu
