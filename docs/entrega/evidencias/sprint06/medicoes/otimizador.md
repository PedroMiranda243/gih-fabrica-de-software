# Medição do otimizador serial — H48, H49

> Gerado por `scripts/medir_otimizador.py`. **Não edite à mão**: número escrito à mão não é evidência. Para atualizar, rode o comando abaixo de novo.

O genético (ADR-011) é comparado com o **melhor dos dois planos gulosos** — por razão ganho/custo e por ganho —, que é o que uma planilha faria. O tempo é o do baseline serial em Python puro: o denominador do *speedup* das versões em C++ e CUDA (RNF02).

## Ambiente

| Item | Valor |
|---|---|
| Data | 25/09/2026 21:24 |
| Massa | `scripts/gerar_dados_sinteticos.py`, 12 semanas, redes geradas com as sementes 42, 7, 2026 |
| Caminho | gerador → banco `gih_medicao` → segmentação → treino → `servico_otimizacao.montar` → busca |
| Genético | população 48, 150 gerações, 4 partidas, 1 mutação por filho |
| Sementes de busca | 1, 2, 3 |
| Python | 3.11.9, uma thread |
| Processador | AMD64 Family 25 Model 33 Stepping 2, AuthenticAMD |

## Como reproduzir

```bash
api/.venv/Scripts/python scripts/medir_otimizador.py --parceiros 500 2000 --redes 42 7 2026 --sementes 3
```

## 500 parceiros

3 redes geradas × 3 sementes de busca, com os parâmetros padrão do genético. Mediana, e entre parênteses a faixa do menor ao maior.

| Campanha | Elegíveis | Ações no plano | Ganho do genético | Sobre o melhor guloso | Abaixo do teto, no máximo | Tempo da busca |
|---|--:|--:|--:|--:|--:|--:|
| orçamento aperta | 469 | 31 | R$ 97.719 | **+3,2%** (0,0% a 5,4%) | 4,5% (3,0% a 17,7%) | 7,1 s (6,9 a 7,2 s) |
| máximo de ações aperta | 469 | 30 | R$ 161.718 | **+0,0%** (0,0% a 0,0%) | 0,0% (0,0% a 0,0%) | 7,3 s (7,1 a 7,9 s) |
| com cotas | 469 | 45 | R$ 167.294 | **+2,9%** (1,3% a 4,0%) | 3,4% (1,6% a 4,1%) | 7,5 s (7,0 a 7,8 s) |

- **Recortes de 8 parceiros da mesma base**, com orçamento curto e cota de cauda longa: o genético chegou ao ótimo da enumeração em **75 de 75**.
- O genético **empatou com o guloso** em 10 de 27 buscas; nas demais, ficou acima. Nunca abaixo: os dois planos gulosos estão na população inicial, e o elitismo não os perde (ADR-011).
- **Abaixo do teto, no máximo** é quanto o plano pode estar abaixo do ótimo: o ótimo fica entre o ganho do plano e um limite superior por relaxação lagrangiana, que relaxa o orçamento e o máximo de ações e ignora as cotas. Com cotas, o teto é mais folgado, e a distância real é menor que a mostrada.

<details><summary>Cada busca</summary>

| Campanha | Rede | Semente | Ganho | Guloso | Teto | Melhora | Abaixo do teto | Tempo |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| orçamento aperta | 42 | 1 | R$ 97.759 | R$ 97.624 | R$ 100.785 | 0,1% | 3,0% | 7,2 s |
| orçamento aperta | 42 | 2 | R$ 97.624 | R$ 97.624 | R$ 100.785 | 0,0% | 3,1% | 7,0 s |
| orçamento aperta | 42 | 3 | R$ 97.719 | R$ 97.624 | R$ 100.785 | 0,1% | 3,0% | 6,9 s |
| máximo de ações aperta | 42 | 1 | R$ 147.139 | R$ 147.139 | R$ 147.139 | 0,0% | 0,0% | 7,3 s |
| máximo de ações aperta | 42 | 2 | R$ 147.139 | R$ 147.139 | R$ 147.139 | 0,0% | 0,0% | 7,9 s |
| máximo de ações aperta | 42 | 3 | R$ 147.139 | R$ 147.139 | R$ 147.139 | 0,0% | 0,0% | 7,7 s |
| com cotas | 42 | 1 | R$ 164.306 | R$ 159.499 | R$ 170.878 | 3,0% | 3,8% | 7,7 s |
| com cotas | 42 | 2 | R$ 165.841 | R$ 159.499 | R$ 170.878 | 4,0% | 2,9% | 7,8 s |
| com cotas | 42 | 3 | R$ 164.467 | R$ 159.499 | R$ 170.878 | 3,1% | 3,8% | 7,8 s |
| orçamento aperta | 7 | 1 | R$ 82.645 | R$ 80.098 | R$ 87.427 | 3,2% | 5,5% | 7,1 s |
| orçamento aperta | 7 | 2 | R$ 83.734 | R$ 80.098 | R$ 87.427 | 4,5% | 4,2% | 7,1 s |
| orçamento aperta | 7 | 3 | R$ 83.504 | R$ 80.098 | R$ 87.427 | 4,3% | 4,5% | 7,2 s |
| máximo de ações aperta | 7 | 1 | R$ 161.718 | R$ 161.718 | R$ 161.718 | 0,0% | 0,0% | 7,2 s |
| máximo de ações aperta | 7 | 2 | R$ 161.718 | R$ 161.718 | R$ 161.718 | 0,0% | 0,0% | 7,5 s |
| máximo de ações aperta | 7 | 3 | R$ 161.718 | R$ 161.718 | R$ 161.718 | 0,0% | 0,0% | 7,1 s |
| com cotas | 7 | 1 | R$ 166.591 | R$ 162.635 | R$ 173.672 | 2,4% | 4,1% | 7,0 s |
| com cotas | 7 | 2 | R$ 167.294 | R$ 162.635 | R$ 173.672 | 2,9% | 3,7% | 7,1 s |
| com cotas | 7 | 3 | R$ 167.757 | R$ 162.635 | R$ 173.672 | 3,1% | 3,4% | 7,0 s |
| orçamento aperta | 2026 | 1 | R$ 102.085 | R$ 98.089 | R$ 119.424 | 4,1% | 14,5% | 7,1 s |
| orçamento aperta | 2026 | 2 | R$ 103.379 | R$ 98.089 | R$ 119.424 | 5,4% | 13,4% | 7,2 s |
| orçamento aperta | 2026 | 3 | R$ 98.335 | R$ 98.089 | R$ 119.424 | 0,3% | 17,7% | 7,1 s |
| máximo de ações aperta | 2026 | 1 | R$ 193.395 | R$ 193.395 | R$ 193.395 | 0,0% | 0,0% | 7,2 s |
| máximo de ações aperta | 2026 | 2 | R$ 193.395 | R$ 193.395 | R$ 193.395 | 0,0% | 0,0% | 7,3 s |
| máximo de ações aperta | 2026 | 3 | R$ 193.395 | R$ 193.395 | R$ 193.395 | 0,0% | 0,0% | 7,1 s |
| com cotas | 2026 | 1 | R$ 202.352 | R$ 199.733 | R$ 208.034 | 1,3% | 2,7% | 7,5 s |
| com cotas | 2026 | 2 | R$ 204.607 | R$ 199.733 | R$ 208.034 | 2,4% | 1,6% | 7,5 s |
| com cotas | 2026 | 3 | R$ 202.336 | R$ 199.733 | R$ 208.034 | 1,3% | 2,7% | 7,2 s |

</details>

## 2.000 parceiros

3 redes geradas × 3 sementes de busca, com os parâmetros padrão do genético. Mediana, e entre parênteses a faixa do menor ao maior.

| Campanha | Elegíveis | Ações no plano | Ganho do genético | Sobre o melhor guloso | Abaixo do teto, no máximo | Tempo da busca |
|---|--:|--:|--:|--:|--:|--:|
| orçamento aperta | 1.876 | 33 | R$ 180.004 | **+0,5%** (0,0% a 0,8%) | 0,8% (0,0% a 2,1%) | 27,2 s (26,7 a 28,3 s) |
| máximo de ações aperta | 1.876 | 30 | R$ 304.857 | **+0,0%** (0,0% a 0,0%) | 0,0% (0,0% a 0,0%) | 27,0 s (26,7 a 28,1 s) |
| com cotas | 1.876 | 42 | R$ 330.271 | **+0,8%** (0,0% a 2,4%) | 5,0% (4,6% a 7,8%) | 26,6 s (26,5 a 27,3 s) |

- **Recortes de 8 parceiros da mesma base**, com orçamento curto e cota de cauda longa: o genético chegou ao ótimo da enumeração em **75 de 75**.
- O genético **empatou com o guloso** em 15 de 27 buscas; nas demais, ficou acima. Nunca abaixo: os dois planos gulosos estão na população inicial, e o elitismo não os perde (ADR-011).
- **Abaixo do teto, no máximo** é quanto o plano pode estar abaixo do ótimo: o ótimo fica entre o ganho do plano e um limite superior por relaxação lagrangiana, que relaxa o orçamento e o máximo de ações e ignora as cotas. Com cotas, o teto é mais folgado, e a distância real é menor que a mostrada.

<details><summary>Cada busca</summary>

| Campanha | Rede | Semente | Ganho | Guloso | Teto | Melhora | Abaixo do teto | Tempo |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| orçamento aperta | 42 | 1 | R$ 180.004 | R$ 180.004 | R$ 183.886 | 0,0% | 2,1% | 27,9 s |
| orçamento aperta | 42 | 2 | R$ 180.004 | R$ 180.004 | R$ 183.886 | 0,0% | 2,1% | 27,5 s |
| orçamento aperta | 42 | 3 | R$ 180.004 | R$ 180.004 | R$ 183.886 | 0,0% | 2,1% | 27,0 s |
| máximo de ações aperta | 42 | 1 | R$ 290.882 | R$ 290.882 | R$ 290.882 | 0,0% | 0,0% | 27,3 s |
| máximo de ações aperta | 42 | 2 | R$ 290.882 | R$ 290.882 | R$ 290.882 | 0,0% | 0,0% | 26,7 s |
| máximo de ações aperta | 42 | 3 | R$ 290.882 | R$ 290.882 | R$ 290.882 | 0,0% | 0,0% | 27,0 s |
| com cotas | 42 | 1 | R$ 325.961 | R$ 320.299 | R$ 342.988 | 1,8% | 5,0% | 27,0 s |
| com cotas | 42 | 2 | R$ 327.256 | R$ 320.299 | R$ 342.988 | 2,2% | 4,6% | 26,9 s |
| com cotas | 42 | 3 | R$ 321.434 | R$ 320.299 | R$ 342.988 | 0,4% | 6,3% | 26,8 s |
| orçamento aperta | 7 | 1 | R$ 219.142 | R$ 217.803 | R$ 219.328 | 0,6% | 0,1% | 27,2 s |
| orçamento aperta | 7 | 2 | R$ 219.289 | R$ 217.803 | R$ 219.328 | 0,7% | 0,0% | 26,8 s |
| orçamento aperta | 7 | 3 | R$ 217.803 | R$ 217.803 | R$ 219.328 | 0,0% | 0,7% | 26,7 s |
| máximo de ações aperta | 7 | 1 | R$ 318.254 | R$ 318.254 | R$ 318.254 | 0,0% | 0,0% | 26,7 s |
| máximo de ações aperta | 7 | 2 | R$ 318.254 | R$ 318.254 | R$ 318.254 | 0,0% | 0,0% | 26,9 s |
| máximo de ações aperta | 7 | 3 | R$ 318.254 | R$ 318.254 | R$ 318.254 | 0,0% | 0,0% | 26,8 s |
| com cotas | 7 | 1 | R$ 359.941 | R$ 351.501 | R$ 384.155 | 2,4% | 6,3% | 26,6 s |
| com cotas | 7 | 2 | R$ 358.764 | R$ 351.501 | R$ 384.155 | 2,1% | 6,6% | 26,6 s |
| com cotas | 7 | 3 | R$ 354.370 | R$ 351.501 | R$ 384.155 | 0,8% | 7,8% | 26,6 s |
| orçamento aperta | 2026 | 1 | R$ 175.301 | R$ 174.124 | R$ 176.684 | 0,7% | 0,8% | 26,9 s |
| orçamento aperta | 2026 | 2 | R$ 174.974 | R$ 174.124 | R$ 176.684 | 0,5% | 1,0% | 28,3 s |
| orçamento aperta | 2026 | 3 | R$ 175.507 | R$ 174.124 | R$ 176.684 | 0,8% | 0,7% | 27,4 s |
| máximo de ações aperta | 2026 | 1 | R$ 304.857 | R$ 304.857 | R$ 304.857 | 0,0% | 0,0% | 27,3 s |
| máximo de ações aperta | 2026 | 2 | R$ 304.857 | R$ 304.857 | R$ 304.857 | 0,0% | 0,0% | 27,7 s |
| máximo de ações aperta | 2026 | 3 | R$ 304.857 | R$ 304.857 | R$ 304.857 | 0,0% | 0,0% | 28,1 s |
| com cotas | 2026 | 1 | R$ 330.271 | R$ 330.271 | R$ 347.348 | 0,0% | 4,9% | 27,3 s |
| com cotas | 2026 | 2 | R$ 330.546 | R$ 330.271 | R$ 347.348 | 0,1% | 4,8% | 26,5 s |
| com cotas | 2026 | 3 | R$ 330.271 | R$ 330.271 | R$ 347.348 | 0,0% | 4,9% | 26,5 s |

</details>
