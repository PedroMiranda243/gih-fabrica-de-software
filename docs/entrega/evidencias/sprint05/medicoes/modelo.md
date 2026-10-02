# Medição do modelo preditivo — H42, H43, H46

> Gerado por `scripts/medir_modelo.py`. **Não edite à mão**: número escrito à mão não é evidência. Para atualizar, rode o comando abaixo de novo.

A rede é comparada, **no mesmo conjunto de teste**, com as referências da `docs/07` §4.4: para o faturamento, repetir o último período e a média móvel dos últimos 4; para o risco (RN09), a taxa observada no treino, separada por "caiu no último período". O teste é o último período da base; o penúltimo valida; os anteriores treinam.

## Ambiente

| Item | Valor |
|---|---|
| Data | 24/09/2026 21:27 |
| Massa | `scripts/gerar_dados_sinteticos.py`, 12 semanas, redes geradas com as sementes 42, 7, 2026 |
| Sementes de treino | 1, 2, 3, 4, 5 |
| Caminho | gerador → banco `gih_medicao` → segmentação → `servico_previsao.historico` → treino |
| Python | 3.11.9 |
| PyTorch | 2.14.0+cpu (CPU, uma thread) |
| NumPy | 2.4.6 |
| Processador | AMD64 Family 25 Model 33 Stepping 2, AuthenticAMD |

## Como reproduzir

```bash
api/.venv/Scripts/python scripts/medir_modelo.py --parceiros 500 5000 --redes 42 7 2026 --sementes 5
```

## 500 parceiros

15 treinos: 3 redes geradas × 5 sementes de treino. Mediana, e entre parênteses a faixa do menor ao maior.

| Métrica | Rede | Repetir o último | Média móvel dos últimos 4 |
|---|--:|--:|--:|
| MAPE do faturamento | **9,8%** (9,1% a 10,1%) | 11,5% (11,5% a 11,9%) | 10,2% (10,0% a 10,4%) |

| Métrica | Rede | Taxa observada |
|---|--:|--:|
| Brier do risco | **0,105** (0,087 a 0,113) | 0,122 (0,114 a 0,125) |
| Erro de calibração | 0,042 (0,029 a 0,053) | 0,003 (0,002 a 0,005) |

- **Supera as referências nas duas saídas (UC07-A1): 15 de 15 treinos.**
- Vantagem no MAPE sobre a melhor referência de cada treino: mediana de 0,6 ponto percentual (0,2 a 0,9).
- O risco da rede **separa melhor** quem cai de quem não cai (Brier menor) e é **menos calibrado** que a referência: em média, 4,2 pontos percentuais entre o previsto e o observado, contra 0,3. A referência é calibrada por construção — é a própria taxa observada, em dois grupos —, e por isso não distingue ninguém dentro de cada grupo.
- Tempo de treino: mediana de 1,0 s (0,8 a 2,6 s), uma thread.
- Amostras de teste por treino: 469 (o último período da base).

<details><summary>Cada treino</summary>

| Rede | Semente | MAPE rede | Último | Média móvel | Brier rede | Referência | Épocas | Tempo | Supera |
|--:|--:|--:|--:|--:|--:|--:|--:|--:|:--:|
| 42 | 1 | 9,2% | 11,5% | 10,0% | 0,104 | 0,122 | 68 | 2,6 s | sim |
| 42 | 2 | 9,2% | 11,5% | 10,0% | 0,105 | 0,122 | 61 | 0,9 s | sim |
| 42 | 3 | 9,1% | 11,5% | 10,0% | 0,103 | 0,122 | 71 | 1,1 s | sim |
| 42 | 4 | 9,3% | 11,5% | 10,0% | 0,108 | 0,122 | 47 | 0,8 s | sim |
| 42 | 5 | 9,2% | 11,5% | 10,0% | 0,105 | 0,122 | 54 | 0,9 s | sim |
| 7 | 1 | 9,8% | 11,9% | 10,2% | 0,091 | 0,114 | 49 | 0,8 s | sim |
| 7 | 2 | 10,0% | 11,9% | 10,2% | 0,091 | 0,114 | 59 | 0,9 s | sim |
| 7 | 3 | 9,8% | 11,9% | 10,2% | 0,089 | 0,114 | 52 | 0,9 s | sim |
| 7 | 4 | 9,7% | 11,9% | 10,2% | 0,091 | 0,114 | 70 | 1,0 s | sim |
| 7 | 5 | 9,7% | 11,9% | 10,2% | 0,087 | 0,114 | 75 | 1,0 s | sim |
| 2026 | 1 | 9,9% | 11,5% | 10,4% | 0,111 | 0,125 | 72 | 1,1 s | sim |
| 2026 | 2 | 10,1% | 11,5% | 10,4% | 0,111 | 0,125 | 89 | 1,3 s | sim |
| 2026 | 3 | 9,8% | 11,5% | 10,4% | 0,113 | 0,125 | 73 | 1,1 s | sim |
| 2026 | 4 | 9,9% | 11,5% | 10,4% | 0,111 | 0,125 | 76 | 1,2 s | sim |
| 2026 | 5 | 9,9% | 11,5% | 10,4% | 0,109 | 0,125 | 90 | 1,3 s | sim |

</details>

## 5.000 parceiros

15 treinos: 3 redes geradas × 5 sementes de treino. Mediana, e entre parênteses a faixa do menor ao maior.

| Métrica | Rede | Repetir o último | Média móvel dos últimos 4 |
|---|--:|--:|--:|
| MAPE do faturamento | **9,9%** (9,9% a 10,1%) | 12,2% (12,2% a 12,2%) | 10,6% (10,5% a 10,7%) |

| Métrica | Rede | Taxa observada |
|---|--:|--:|
| Brier do risco | **0,096** (0,095 a 0,097) | 0,122 (0,122 a 0,123) |
| Erro de calibração | 0,010 (0,005 a 0,017) | 0,001 (0,000 a 0,006) |

- **Supera as referências nas duas saídas (UC07-A1): 15 de 15 treinos.**
- Vantagem no MAPE sobre a melhor referência de cada treino: mediana de 0,6 ponto percentual (0,5 a 0,7).
- O risco da rede **separa melhor** quem cai de quem não cai (Brier menor) e é **menos calibrado** que a referência: em média, 1,0 ponto percentual entre o previsto e o observado, contra 0,1. A referência é calibrada por construção — é a própria taxa observada, em dois grupos —, e por isso não distingue ninguém dentro de cada grupo.
- Tempo de treino: mediana de 7,5 s (5,7 a 11,6 s), uma thread.
- Amostras de teste por treino: 4.689 (o último período da base).

<details><summary>Cada treino</summary>

| Rede | Semente | MAPE rede | Último | Média móvel | Brier rede | Referência | Épocas | Tempo | Supera |
|--:|--:|--:|--:|--:|--:|--:|--:|--:|:--:|
| 42 | 1 | 10,0% | 12,2% | 10,5% | 0,096 | 0,122 | 54 | 8,0 s | sim |
| 42 | 2 | 9,9% | 12,2% | 10,5% | 0,097 | 0,122 | 85 | 11,6 s | sim |
| 42 | 3 | 9,9% | 12,2% | 10,5% | 0,096 | 0,122 | 36 | 5,8 s | sim |
| 42 | 4 | 9,9% | 12,2% | 10,5% | 0,096 | 0,122 | 39 | 6,1 s | sim |
| 42 | 5 | 9,9% | 12,2% | 10,5% | 0,095 | 0,122 | 65 | 8,3 s | sim |
| 7 | 1 | 9,9% | 12,2% | 10,6% | 0,096 | 0,123 | 36 | 5,7 s | sim |
| 7 | 2 | 9,9% | 12,2% | 10,6% | 0,096 | 0,123 | 65 | 9,1 s | sim |
| 7 | 3 | 9,9% | 12,2% | 10,6% | 0,096 | 0,123 | 42 | 7,5 s | sim |
| 7 | 4 | 9,9% | 12,2% | 10,6% | 0,095 | 0,123 | 44 | 7,3 s | sim |
| 7 | 5 | 10,1% | 12,2% | 10,6% | 0,096 | 0,123 | 36 | 6,3 s | sim |
| 2026 | 1 | 10,1% | 12,2% | 10,7% | 0,095 | 0,122 | 40 | 6,6 s | sim |
| 2026 | 2 | 10,1% | 12,2% | 10,7% | 0,097 | 0,122 | 38 | 7,3 s | sim |
| 2026 | 3 | 10,1% | 12,2% | 10,7% | 0,096 | 0,122 | 57 | 8,1 s | sim |
| 2026 | 4 | 10,0% | 12,2% | 10,7% | 0,095 | 0,122 | 77 | 11,4 s | sim |
| 2026 | 5 | 10,1% | 12,2% | 10,7% | 0,096 | 0,122 | 58 | 8,7 s | sim |

</details>
