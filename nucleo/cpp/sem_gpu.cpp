// O núcleo compilado sem CUDA: não há GPU, e ele diz por quê (RNF06, H56).
//
// Compilado sempre, e vazio quando há CUDA: assim `cpp/*.cpp` continua sendo a
// lista inteira de fontes da CI e do `g++` do README, sem exceção a lembrar.
#ifndef GIH_COM_CUDA

#include "gpu.hpp"

namespace gih::gpu {

bool procurar(Dispositivo&, Ausencia& ausencia, std::string& motivo) {
    ausencia = Ausencia::SemCuda;
    motivo = "Este executável foi compilado sem CUDA.";
    return false;
}

Transferencia ida_e_volta(const Instancia&, const std::vector<Gene>&, int, int) {
    throw SemGpu("Este executável foi compilado sem CUDA.");
}

PopulacaoAvaliada avaliar_na_gpu(const Instancia&, const std::vector<Gene>&, int, int) {
    throw SemGpu("Este executável foi compilado sem CUDA.");
}

Resultado otimizar_na_gpu(const Instancia&, const Parametros&) {
    throw SemGpu("Este executável foi compilado sem CUDA.");
}

}  // namespace gih::gpu

#endif
