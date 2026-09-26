// O executável `gih-nucleo` — como a API chama o núcleo em C++ (ADR-012).
//
//   gih-nucleo otimizar [--semente N] [--partidas N] [--populacao N]
//                       [--geracoes N] [--mutacoes N] [--limite-ms N]
//       Lê a instância pela entrada padrão e escreve o resultado na saída.
//   gih-nucleo sorteio C1 C2 ...
//       O sorteio das coordenadas: o contrato do gerador com o Python.
//   gih-nucleo versao
//
// **Tudo em texto, tudo inteiro.** A instância chega em centavos e contagens, já
// traduzida pela API (ADR-011), e é lida com a biblioteca padrão: nenhuma
// dependência. O formato está em `gih_nucleo/nativo.py`, que o escreve e o lê.
//
// Saída 0: resultado (viável ou inviável — as duas são respostas). Saída 2:
// instância ou argumento inválido, com a mensagem no erro padrão. Saída 3:
// defeito interno.
#include <cstdlib>
#include <cstring>
#include <exception>
#include <stdexcept>
#include <iostream>
#include <sstream>
#include <string>

#include "nucleo.hpp"

namespace {

constexpr const char* FORMATO = "GIH-NUCLEO 1";

struct Invalida : std::runtime_error {
    using std::runtime_error::runtime_error;
};

std::int64_t ler(std::istream& entrada, const char* o_que) {
    std::int64_t valor;
    if (!(entrada >> valor)) throw Invalida(std::string("Faltou ou não é número: ") + o_que + ".");
    return valor;
}

// Reproduz as recusas de `problema.Instancia.__post_init__`, com as mesmas frases.
gih::Instancia ler_instancia(std::istream& entrada) {
    std::string cabecalho;
    std::getline(entrada >> std::ws, cabecalho);
    if (!cabecalho.empty() && cabecalho.back() == '\r') cabecalho.pop_back();
    if (cabecalho != FORMATO) throw Invalida("A entrada não começa com o cabeçalho " + std::string(FORMATO) + ".");

    gih::Instancia inst;
    inst.parceiros = static_cast<int>(ler(entrada, "número de parceiros"));
    inst.acoes = static_cast<int>(ler(entrada, "número de ações"));
    inst.categorias = static_cast<int>(ler(entrada, "número de categorias"));
    if (inst.parceiros < 0 || inst.categorias < 0) throw Invalida("Tamanho negativo.");
    if (inst.acoes == 0) throw Invalida("O catálogo não tem nenhuma ação.");
    if (inst.acoes < 0 || inst.acoes > gih::ACOES_MAXIMAS) {
        throw Invalida("O catálogo cabe em até " + std::to_string(gih::ACOES_MAXIMAS) + " ações.");
    }

    inst.orcamento = ler(entrada, "orçamento");
    inst.maximo_acoes = ler(entrada, "máximo de ações");
    inst.minimo_cauda = ler(entrada, "cota da cauda longa");
    if (inst.orcamento < 0 || inst.maximo_acoes < 0 || inst.minimo_cauda < 0) {
        throw Invalida("Orçamento, máximo de ações e cotas não podem ser negativos.");
    }

    inst.custo.resize(static_cast<std::size_t>(inst.acoes));
    for (auto& c : inst.custo) {
        c = ler(entrada, "custo");
        if (c <= 0) throw Invalida("Toda ação precisa custar mais que zero.");
    }
    inst.minimo_categoria.resize(static_cast<std::size_t>(inst.categorias));
    inst.maximo_categoria.resize(static_cast<std::size_t>(inst.categorias));
    for (auto& m : inst.minimo_categoria) m = ler(entrada, "mínimo da categoria");
    for (auto& m : inst.maximo_categoria) m = ler(entrada, "máximo da categoria");
    for (int k = 0; k < inst.categorias; ++k) {
        if (inst.minimo_categoria[k] < 0 || inst.maximo_categoria[k] < 0) throw Invalida("Cota negativa.");
    }

    inst.categoria.resize(static_cast<std::size_t>(inst.parceiros));
    inst.cauda.resize(static_cast<std::size_t>(inst.parceiros));
    inst.ganho.resize(static_cast<std::size_t>(inst.parceiros) * inst.acoes);
    for (int i = 0; i < inst.parceiros; ++i) {
        const std::int64_t k = ler(entrada, "categoria do parceiro");
        if (k != gih::SEM_CATEGORIA && (k < 0 || k >= inst.categorias)) {
            throw Invalida("Parceiro numa categoria que não tem cota definida.");
        }
        inst.categoria[i] = static_cast<int>(k);
        const std::int64_t cauda = ler(entrada, "cauda longa do parceiro");
        if (cauda != 0 && cauda != 1) throw Invalida("Cauda longa é 0 ou 1.");
        inst.cauda[i] = static_cast<char>(cauda);
        for (int a = 0; a < inst.acoes; ++a) {
            const std::int64_t g = ler(entrada, "ganho");
            if (g < 0) throw Invalida("Ganho negativo.");
            inst.ganho[static_cast<std::size_t>(i) * inst.acoes + a] = g;
        }
    }
    return inst;
}

gih::Parametros ler_parametros(int argc, char** argv) {
    gih::Parametros p;
    for (int i = 2; i < argc; i += 2) {
        if (i + 1 >= argc) throw Invalida(std::string("Falta o valor de ") + argv[i] + ".");
        const std::string nome = argv[i];
        char* fim = nullptr;
        const long long valor = std::strtoll(argv[i + 1], &fim, 10);
        if (*fim != '\0') throw Invalida("Valor não inteiro em " + nome + ".");
        if (nome == "--semente") {
            if (valor < 0) throw Invalida("A semente não pode ser negativa.");
            p.semente = static_cast<std::uint64_t>(valor);
        } else if (nome == "--partidas") {
            p.partidas = static_cast<int>(valor);
        } else if (nome == "--populacao") {
            p.populacao = static_cast<int>(valor);
        } else if (nome == "--geracoes") {
            p.geracoes = static_cast<int>(valor);
        } else if (nome == "--mutacoes") {
            p.mutacoes_por_filho = static_cast<int>(valor);
        } else if (nome == "--limite-ms") {
            p.limite_ms = valor;
        } else {
            throw Invalida("Parâmetro desconhecido: " + nome + ".");
        }
    }
    return p;
}

int otimizar(int argc, char** argv) {
    const gih::Parametros p = ler_parametros(argc, argv);
    // Conferidos antes da viabilidade, na mesma ordem do Python: com parâmetro
    // impossível e campanha inviável, as duas versões recusam pelo parâmetro.
    if (p.populacao < 2 || p.partidas < 1 || p.geracoes < 0) {
        throw Invalida("A busca precisa de ao menos 2 indivíduos, 1 partida e 0 gerações.");
    }
    std::ios::sync_with_stdio(false);
    const gih::Instancia inst = ler_instancia(std::cin);

    std::ostringstream saida;
    saida << FORMATO << '\n';
    std::vector<int> minimo;
    gih::Inviabilidade motivo;
    if (!gih::diagnosticar(inst, minimo, motivo)) {
        saida << "inviavel " << motivo.restricao << ' ' << motivo.exigido << ' ' << motivo.disponivel << ' '
              << motivo.categoria << '\n';
        std::cout << saida.str();
        return 0;
    }

    const gih::Resultado r = gih::otimizar_serial(inst, p);
    const auto& av = r.avaliacao;
    saida << "viavel\n"
          << "avaliacao " << av.ganho << ' ' << av.custo << ' ' << av.acoes << ' ' << av.cauda << ' '
          << av.violacao << '\n'
          << "busca " << r.partidas << ' ' << r.geracoes << ' ' << (r.parcial ? 1 : 0) << ' '
          << static_cast<long long>(r.segundos * 1e6) << '\n'
          << "genes";
    for (gih::Gene g : r.genes) saida << ' ' << static_cast<int>(g);
    saida << '\n';
    std::cout << saida.str();
    return 0;
}

int sorteio(int argc, char** argv) {
    std::uint64_t h = 0;
    for (int i = 2; i < argc; ++i) {
        char* fim = nullptr;
        const unsigned long long c = std::strtoull(argv[i], &fim, 10);
        if (*fim != '\0') throw Invalida(std::string("Coordenada não inteira: ") + argv[i] + ".");
        h = gih::encadear(h, c);
    }
    std::cout << h << '\n';
    return 0;
}

}  // namespace

int main(int argc, char** argv) {
    const std::string comando = argc > 1 ? argv[1] : "";
    try {
        if (comando == "otimizar") return otimizar(argc, argv);
        if (comando == "sorteio") return sorteio(argc, argv);
        if (comando == "versao") {
            std::cout << FORMATO << " serial\n";
            return 0;
        }
        std::cerr << "Uso: gih-nucleo otimizar|sorteio|versao — ver o cabeçalho de main.cpp.\n";
        return 2;
    } catch (const Invalida& e) {
        std::cerr << e.what() << '\n';
        return 2;
    } catch (const std::invalid_argument& e) {
        std::cerr << e.what() << '\n';
        return 2;
    } catch (const std::exception& e) {
        std::cerr << "Defeito interno: " << e.what() << '\n';
        return 3;
    }
}
