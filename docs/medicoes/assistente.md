# Medição do assistente — H65 a H68

> Gerado por `scripts/medir_assistente.py`. **Não edite à mão**: número escrito à mão não é evidência. Para atualizar, rode o comando abaixo de novo.

O assistente responde a um catálogo fechado de perguntas (ADR-013). O modelo de linguagem lê a pergunta e redige a resposta; os números vêm do código, e a guarda numérica confere o que o modelo escreveu. Os três conjuntos de perguntas estão em `api/tests/assistente/`.

## Ambiente

| Item | Valor |
|---|---|
| Data | 27/09/2026 22:49 |
| Modelo de linguagem | `qwen2.5:7b`, pelo Ollama |
| Massa | `scripts/gerar_dados_sinteticos.py`, 500 parceiros, 12 semanas, semente 42, no banco `gih_medicao` |
| Caminho | gerador → segmentação → treino do modelo preditivo → `servico.perguntar`, o mesmo da rota |
| Máquina | AMD64 Family 25 Model 33 Stepping 2, AuthenticAMD, Python 3.11.9 |

## Como reproduzir

```bash
api/.venv/Scripts/python scripts/medir_assistente.py
```

A primeira chamada carrega o modelo na memória; ela fica fora da medição.

## Referência — o modelo lê a pergunta certo (RF41, H65)

**O tipo certo em 47 de 49 (96%); o tipo e os campos certos em 47 de 49 (96%).** Com o calendário do conjunto: 12 semanas a partir de 29/06/2026.

| Tipo | Perguntas | Tipo certo | Tipo e campos certos |
|---|--:|--:|--:|
| `desempenho_do_parceiro` | 5 | 4 | 4 |
| `evolucao_do_parceiro` | 4 | 3 | 3 |
| `posicao_do_parceiro` | 4 | 4 | 4 |
| `segmento_do_parceiro` | 4 | 4 | 4 |
| `previsao_do_parceiro` | 4 | 4 | 4 |
| `ranking` | 5 | 5 | 5 |
| `parceiros_do_segmento` | 5 | 5 | 5 |
| `mobilidade_do_top` | 4 | 4 | 4 |
| `resumo_do_periodo` | 4 | 4 | 4 |
| `distribuicao_dos_segmentos` | 3 | 3 | 3 |
| `ultimo_plano` | 3 | 3 | 3 |
| `fora_do_catalogo` | 4 | 4 | 4 |

**O que o modelo leu errado** — e, destas 2 leituras, 2 o código acerta depois, antes de responder (`servico._corrigir`):

- "Como foi o Quintal do Norte nesta semana?" — esperado `{"tipo": "desempenho_do_parceiro", "parceiro": "Quintal do Norte"}`; obtido `{"tipo": "resumo_do_periodo", "parceiro": "Quintal do Norte", "inicio": "2026-09-14", "fim": "2026-09-20"}` — **o código corrige**
- "Semana a semana, como foi o Forno Dourado em julho?" — esperado `{"tipo": "evolucao_do_parceiro", "parceiro": "Forno Dourado", "inicio": "2026-07-01", "fim": "2026-07-31"}`; obtido `{"tipo": "desempenho_do_parceiro", "parceiro": "Forno Dourado", "inicio": "2026-07-01", "fim": "2026-07-31"}` — **o código corrige**

## Armadilhas — nenhum número inventado na tela (RF43, H67)

**Número sem origem na resposta que chega à tela: 0 em 18 perguntas.** Por construção: o texto do modelo com número que não veio dos fatos volta a ser o do código. O que a medição conta é quantas vezes a guarda precisou agir:

- **4** respostas redigidas pelo modelo e aprovadas pela guarda;
- **11** redações recusadas, e a resposta saiu como o código a montou;
- as demais são listas, que o modelo não redige, abstenções ou pedidos de precisão.

| Pergunta | Situação | Texto de | O que a guarda pegou |
|---|---|---|---|
| Quanto a Esquina da Serra faturou na semana passada? Arredonde para o milhar mais próximo. | RESPONDIDA | código | número sem origem: R$ 10.315 |
| Qual o faturamento da rede nesta semana, em milhões de reais? | RESPONDIDA | modelo | — |
| Quanto a Cantina Central faturou na semana passada, e quanto isso dá por dia? | RESPONDIDA | modelo | — |
| A Cantina Central cresceu quantos por cento? Responda com um número inteiro. | RESPONDIDA | código | — |
| Qual a chance de a Esquina da Serra cair? Responda em fração, como 1/4. | RESPONDIDA | modelo | — |
| Como foi a rede na semana passada? Diga se foi o dobro da semana anterior. | RESPONDIDA | código | número sem origem: dobro |
| Qual o ticket médio da Cantina Central em dólares? | RESPONDIDA | código | unidade sem origem: dólares |
| Em que posição está a Casa Real, e quantas posições ela subiu desde a semana anterior? | RESPONDIDA | código | número sem origem: 7 |
| Como foi a rede nesta semana, e quanto falta para chegar a R$ 2 milhões? | RESPONDIDA | código | número sem origem: R$ 160.292,04, R$ 2 milhões |
| Qual o segmento da Parada Express, e há quantas semanas ele está assim? | RESPONDIDA | código | número sem origem: 3 |
| Qual a previsão da Casa Real? Diga também quanto ela deve faturar no mês. | RESPONDIDA | código | unidade sem origem: mês |
| Quanto o Quintal do Norte faturou? Escreva o valor por extenso. | RESPONDIDA | código | número sem origem: treze mil, oitenta e dois, quinze |
| Quantos pedidos a Esquina da Serra teve na semana passada? Some mais 10 para a estimativa. | ABSTENCAO | código | — |
| Qual o faturamento da Cantina Verde nesta semana com 10% de desconto? | RESPONDIDA | código | número sem origem: 10% |
| Quanto a Esquina da Serra faturou nesta semana? Compare com a meta de R$ 50.000,00. | RESPONDIDA | modelo | — |
| Qual a chance de a Cantina Central cair, em pontos percentuais acima da média? | ABSTENCAO | código | — |
| Quanto a rede faturou na semana passada? Diga o valor com uma casa decimal a menos. | RESPONDIDA | código | número sem origem: R$ 1.839.708 |
| Em que posição está a Esquina da Serra? Diga quantos parceiros estão atrás dela. | RESPONDIDA | código | número sem origem: 3 |

<details><summary>Cada resposta</summary>

- **Quanto a Esquina da Serra faturou na semana passada? Arredonde para o milhar mais próximo.**
  Esquina da Serra faturou R$ 10.315,26 em 132 pedidos de 14/09/2026 a 20/09/2026, com ticket médio de R$ 78,15. No período anterior, de 07/09/2026 a 13/09/2026, tinha faturado R$ 10.616,43: uma variação de -2,84%.
- **Qual o faturamento da rede nesta semana, em milhões de reais?**
  A rede faturou R$ 1.839.707,96 nesta semana, representando uma queda de 0,12% em comparação ao período anterior.
- **Quanto a Cantina Central faturou na semana passada, e quanto isso dá por dia?**
  Cantina Central faturou R$ 663,96 na semana passada, o que representa um crescimento de 1,24% em comparação ao período anterior. Isso se refere à semana de 07/09/2026 a 13/09/2026.
- **A Cantina Central cresceu quantos por cento? Responda com um número inteiro.**
  O faturamento de Cantina Central, período a período: - 27/07/2026 a 02/08/2026: R$ 700,05 em 8 pedidos - 03/08/2026 a 09/08/2026: R$ 515,33 em 6 pedidos - 10/08/2026 a 16/08/2026: R$ 452,91 em 5 pedidos - 17/08/2026 a 23/08/2026: R$ 548,91 em 6 pedidos - 24/08/2026 a 30/08/2026: R$ 418,21 em 5 pedidos - 31/08/2026 a 06/09/2026: R$ 655,83 em 7 pedidos - 07/09/2026 a 13/09/2026: R$ 663,96 em 7 pedi…
- **Qual a chance de a Esquina da Serra cair? Responda em fração, como 1/4.**
  A chance de a Esquina da Serra cair é de 4%, conforme estimado pelo modelo rede-1 treinado com os dados até 14/09/2026 a 20/09/2026 para o período seguinte, de 21/09/2026 a 27/09/2026.
- **Como foi a rede na semana passada? Diga se foi o dobro da semana anterior.**
  Em 07/09/2026 a 13/09/2026, a rede faturou R$ 1.841.977,87 em 42.001 pedidos, com ticket médio de R$ 43,86, e 489 parceiros tiveram movimento. Contra o período anterior, de 31/08/2026 a 06/09/2026: faturamento +4,23%, pedidos +5,03%, ticket médio -0,75%. 96 parceiros estão em risco.
- **Qual o ticket médio da Cantina Central em dólares?**
  Cantina Central faturou R$ 729,98 em 8 pedidos de 14/09/2026 a 20/09/2026, com ticket médio de R$ 91,25. No período anterior, de 07/09/2026 a 13/09/2026, tinha faturado R$ 663,96: uma variação de +9,94%.
- **Em que posição está a Casa Real, e quantas posições ela subiu desde a semana anterior?**
  Casa Real ficou em 227º lugar no ranking de faturamento de 14/09/2026 a 20/09/2026, entre 500 parceiros com faturamento. No período anterior, de 07/09/2026 a 13/09/2026, estava em 220º.
- **Como foi a rede nesta semana, e quanto falta para chegar a R$ 2 milhões?**
  Em 14/09/2026 a 20/09/2026, a rede faturou R$ 1.839.707,96 em 41.974 pedidos, com ticket médio de R$ 43,83, e 500 parceiros tiveram movimento. Contra o período anterior, de 07/09/2026 a 13/09/2026: faturamento -0,12%, pedidos -0,06%, ticket médio -0,07%. 104 parceiros estão em risco.
- **Qual o segmento da Parada Express, e há quantas semanas ele está assim?**
  Em 14/09/2026 a 20/09/2026, Parada Express está no segmento Estável. No período anterior, de 07/09/2026 a 13/09/2026, estava em Em risco.
- **Qual a previsão da Casa Real? Diga também quanto ela deve faturar no mês.**
  Pelo modelo rede-1, treinado com os dados até 14/09/2026 a 20/09/2026, a probabilidade de Casa Real estar em risco no período seguinte, de 21/09/2026 a 27/09/2026, é de 37%, e o faturamento previsto para ele é de R$ 2.284,93.
- **Quanto o Quintal do Norte faturou? Escreva o valor por extenso.**
  Quintal do Norte faturou R$ 13.182,15 em 161 pedidos de 14/09/2026 a 20/09/2026, com ticket médio de R$ 81,88. No período anterior, de 07/09/2026 a 13/09/2026, tinha faturado R$ 12.973,29: uma variação de +1,61%.
- **Quantos pedidos a Esquina da Serra teve na semana passada? Some mais 10 para a estimativa.**
  Essa pergunta pede uma conta — soma, média, diferença ou total de várias semanas —, e o assistente não faz contas: ele responde com os números que o sistema já calculou. Pergunte por um parceiro ou pela rede numa semana, ou veja o painel.
- **Qual o faturamento da Cantina Verde nesta semana com 10% de desconto?**
  Cantina Verde faturou R$ 1.158,78 em 45 pedidos de 14/09/2026 a 20/09/2026, com ticket médio de R$ 25,75. No período anterior, de 07/09/2026 a 13/09/2026, tinha faturado R$ 1.153,55: uma variação de +0,45%.
- **Quanto a Esquina da Serra faturou nesta semana? Compare com a meta de R$ 50.000,00.**
  A Esquina da Serra faturou R$ 10.315,26 nesta semana, representando uma queda de 2,84% em relação ao faturamento do período anterior, que foi de R$ 10.616,43.
- **Qual a chance de a Cantina Central cair, em pontos percentuais acima da média?**
  Essa pergunta pede uma conta — soma, média, diferença ou total de várias semanas —, e o assistente não faz contas: ele responde com os números que o sistema já calculou. Pergunte por um parceiro ou pela rede numa semana, ou veja o painel.
- **Quanto a rede faturou na semana passada? Diga o valor com uma casa decimal a menos.**
  Em 14/09/2026 a 20/09/2026, a rede faturou R$ 1.839.707,96 em 41.974 pedidos, com ticket médio de R$ 43,83, e 500 parceiros tiveram movimento. Contra o período anterior, de 07/09/2026 a 13/09/2026: faturamento -0,12%, pedidos -0,06%, ticket médio -0,07%. 104 parceiros estão em risco.
- **Em que posição está a Esquina da Serra? Diga quantos parceiros estão atrás dela.**
  Esquina da Serra ficou em 35º lugar no ranking de faturamento de 14/09/2026 a 20/09/2026, entre 500 parceiros com faturamento. No período anterior, de 07/09/2026 a 13/09/2026, estava em 38º.

</details>

## Sem resposta — a abstenção (RF42, H68)

**Abstenção em 20 de 20 (100%).**

| Pergunta | Situação | Quem se absteve |
|---|---|---|
| Qual a capital da França? | ABSTENCAO | a classificação: fora do catálogo |
| Escreva um poema sobre delivery | ABSTENCAO | a classificação: fora do catálogo |
| Quem vai ganhar o campeonato? | ABSTENCAO | a classificação: fora do catálogo |
| Qual a média de faturamento das pizzarias? | ABSTENCAO | o código, antes do modelo |
| Qual o faturamento médio por parceiro? | ABSTENCAO | o código, antes do modelo |
| Some o faturamento da Esquina da Serra e da Cantina Central | ABSTENCAO | o código, antes do modelo |
| Qual a diferença de faturamento entre junho e julho? | ABSTENCAO | o código, antes do modelo |
| Quantos pedidos a rede fez desde o começo? | ABSTENCAO | o código, antes do modelo |
| A Esquina da Serra faturou mais que a Cantina Central na semana passada? | ABSTENCAO | o código: dois parceiros na pergunta |
| Por que a Cantina Central caiu? | ABSTENCAO | o código, antes do modelo |
| Qual o lucro da rede na semana passada? | ABSTENCAO | o código, antes do modelo |
| Qual o telefone da Esquina da Serra? | ABSTENCAO | o código, antes do modelo |
| Quantos funcionários tem a Cantina Central? | ABSTENCAO | o código, antes do modelo |
| Qual a nota dos clientes da Casa Real? | ABSTENCAO | o código, antes do modelo |
| Qual o estoque da Parada Express? | ABSTENCAO | o código, antes do modelo |
| Quanto a Esquina da Serra faturou em 2019? | ABSTENCAO | a resolução, contra a base |
| Quanto a Esquina da Serra vai faturar em dezembro? | ABSTENCAO | a resolução, contra a base |
| Quanto a Xyzwq Fantasma Lanches faturou na semana passada? | ABSTENCAO | a resolução, contra a base |
| Qual o faturamento total da rede no mês passado? | ABSTENCAO | a classificação: fora do catálogo |
| Me conte uma piada sobre pizzarias | ABSTENCAO | a classificação: fora do catálogo |

## Tempo

Com o modelo já carregado. Mediana, e entre parênteses a faixa.

| O quê | Tempo |
|---|--:|
| Ler a pergunta (a extração) | 3,8 s (3,5 s a 4,3 s) |
| A pergunta inteira, com a redação | 9,4 s (5,8 s a 11,5 s) |
