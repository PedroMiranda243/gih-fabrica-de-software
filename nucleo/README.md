# `nucleo/` — o otimizador do plano de campanha

Pacote `gih_nucleo`: dado o ganho esperado de cada ação em cada parceiro, escolhe o plano de maior ganho que
respeita o orçamento, o máximo de ações e as cotas (H48, H49, H52). **Otimiza; não decide.** Recebe da API
uma instância já em números inteiros e devolve o plano. Não conhece banco, FastAPI nem regra de negócio:
o que é ganho (RN10), quem é elegível e o que é cauda longa (RN11) são decididos pela API.

O problema está formalizado em [`docs/07`](../docs/07-arquitetura-preliminar.md) §4.1. O algoritmo, e o que
deixa as três versões no mesmo plano, estão na ADR-011.

| Arquivo | O que faz |
|---|---|
| `problema.py` | A instância, em centavos e contagens. A avaliação de uma solução, com a violação em unidades de ação. O verificador independente das restrições (RN07) |
| `viabilidade.py` | Decide **com exatidão**, antes da busca, se as cotas cabem; se não, diz qual restrição falha e quanto falta (H52) |
| `guloso.py` | Os planos gulosos, por razão ganho/custo e por ganho: soluções iniciais do genético e referência de qualidade |
| `serial.py` | O genético com partidas independentes, em Python puro: o baseline de corretude e de tempo (H49, RNF02) |
| `aleatorio.py` | O gerador sem estado (SplitMix64 por coordenadas), igual em Python, C++ e CUDA |
| `exaustivo.py` | O ótimo por enumeração, para instâncias pequenas: a régua dos testes |
| `nativo.py` | Chama o executável em C++ com o mesmo contrato de `serial.otimizar`, e confere a avaliação que ele devolve (ADR-012) |

**O mesmo algoritmo em C++** (`cpp/`, H53a): o executável `gih-nucleo` lê a instância em texto e devolve o
plano **idêntico** ao do Python — mesmos genes, mesma avaliação, mesmas gerações —, porque o sorteio é por
coordenadas e a aritmética é inteira (ADR-011). No contêiner, com 2.000 parceiros, leva 0,34 s contra 25,5 s
do Python: 76x. É dele que as versões OpenMP (H53b) e CUDA (H54) partem.

**O pacote Python não tem dependência.** O baseline serial é o denominador do *speedup*, e vetorizá-lo com NumPy
deixaria o ganho medido menos honesto. As versões em C++ com OpenMP (Sprint 10) e em CUDA (Sprint 11) vão
morar aqui, seguindo o mesmo algoritmo sorteio a sorteio. `spike/` guarda a validação do toolchain de GPU
(H47), e o `requirements.txt` desta pasta é dele, não do pacote.

## Rodando os testes

No mesmo ambiente virtual da API, de dentro de `nucleo/`:

```bash
pip install --no-deps -e .
construir.bat                                                    # Windows: compila bin\gih-nucleo.exe
g++ -O2 -std=c++17 -Wall -Wextra cpp/*.cpp -o bin/gih-nucleo     # Linux
pytest
```

Sem o executável compilado, os testes que comparam o C++ com o Python são pulados; na CI, reprovam.

Os testes conferem o genético contra a enumeração exata em 40 instâncias pequenas sorteadas e a
verificação de viabilidade contra a enumeração em 150. Também mostram onde o guloso fica abaixo do ótimo e
fixam os valores do gerador que o C++ e o CUDA vão precisar reproduzir.
