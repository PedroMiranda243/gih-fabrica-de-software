# Revisão das regras de negócio — RN01 a RN11

> **Gerado por `scripts/revisar_regras.py`. Não edite à mão:** rode o roteiro de novo.

Cada regra de `docs/02-requisitos.md`, parte IV, contra o que o sistema faz: o cenário, o que a regra manda e o que a aplicação devolveu. O esperado está escrito no roteiro, deduzido da regra — não vem do código que se revisa.

**Resultado: 79 de 79 conferências passaram, nas 11 regras.**

## Ambiente

| Item | Valor |
|---|---|
| Data | 02/10/2026 04:56 |
| Banco | `gih_regras` — **separado do banco de trabalho**, recriado a cada execução |
| PostgreSQL | PostgreSQL 16.14 on x86_64-pc-linux-musl |
| Python | 3.11.9 |
| Aplicação | em processo, pelo `TestClient`: as rotas, a sessão e os perfis de verdade |
| Otimizador | modo SERIAL |
| Modelo de linguagem | fora do ar: as mensagens saem do modelo fixo |

## Como reproduzir

```bash
api/.venv/Scripts/python scripts/revisar_regras.py
```

## O cenário

22 parceiros e 8 semanas, importados pela API. O faturamento das três últimas semanas decide a tendência, e o da última, o ranking:

| Parceiro | Antepenúltima | Penúltima | Última | Posição | Segmento esperado |
|---|--:|--:|--:|--:|---|
| Loja 01 | 20.050 | 20.000 | 20.050 | 1ª | TOP |
| Loja 02 | 19.000 | 18.500 | 18.000 | 3ª | EM_RISCO |
| Loja 03 | 18.000 | 18.200 | 18.400 | 2ª | TOP |
| Loja 04 | 17.050 | 17.000 | 17.050 | 4ª | TOP |
| Loja 05 | 16.050 | 16.000 | 16.050 | 5ª | TOP |
| Loja 06 | 15.050 | 15.000 | 15.050 | 6ª | TOP |
| Loja 07 | 14.050 | 14.000 | 14.050 | 7ª | TOP |
| Loja 08 | 13.050 | 13.000 | 13.050 | 8ª | TOP |
| Loja 09 | 12.050 | 12.000 | 12.050 | 9ª | TOP |
| Loja 10 | 11.050 | 11.000 | 11.050 | 10ª | TOP |
| Loja 11 | 10.050 | 10.000 | 10.050 | 11ª | TOP |
| Loja 12 | 9.050 | 9.000 | 9.050 | 12ª | TOP |
| Loja 13 | 8.050 | 8.000 | 8.050 | 13ª | TOP |
| Loja 14 | 7.000 | 6.900 | 6.800 | 14ª | PROSPECCAO |
| Loja 15 | 5.950 | 6.000 | 4.800 | 16ª | ESTAVEL |
| Loja 16 | 5.050 | 5.000 | 6.100 | 15ª | TOP |
| Loja 17 | 4.050 | 4.000 | 4.050 | 17ª | ESTAVEL |
| Loja 18 | 3.000 | 3.200 | 3.400 | 18ª | EM_ASCENSAO |
| Loja 19 | 2.000 | 1.900 | 1.800 | 19ª | EM_RISCO |
| Loja 20 | — | 1.000 | 900 | 20ª | RECEM_CHEGADO |
| Pizzaria Aurora | 550 | 500 | 550 | 21ª | ESTAVEL |
| Pizzaria e Padaria Sol | 450 | 400 | 450 | 22ª | ESTAVEL |

A Loja 14 está marcada como prospecção; as lojas 05 a 08 foram classificadas à mão como Padaria; a Loja 17 é desativada antes da campanha.

## Resumo

| Regra | Conferências | Resultado |
|---|--:|---|
| **RN01** — Segmentação com precedência explícita | 13 de 13 | ok |
| **RN02** — Mobilidade do Top N lê o ranking, não o segmento | 6 de 6 | ok |
| **RN03** — Período é obrigatório na importação | 4 de 4 | ok |
| **RN04** — Ticket médio é derivado, nunca importado | 5 de 5 | ok |
| **RN05** — Categoria sugerida não é categoria confirmada | 6 de 6 | ok |
| **RN06** — Nenhuma mensagem sai sem aprovação humana | 9 de 9 | ok |
| **RN07** — O plano de campanha respeita todas as restrições ou não existe | 4 de 4 | ok |
| **RN08** — O modelo de linguagem não produz número | 5 de 5 | ok |
| **RN09** — Queda prevista é entrar em risco, e o modelo exige histórico | 13 de 13 | ok |
| **RN10** — O ganho esperado de uma ação soma crescimento e perda evitada | 2 de 2 | ok |
| **RN11** — Quem recebe ação, e como as cotas contam | 12 de 12 | ok |

## RN01 — Segmentação com precedência explícita

**Cenário.** Os 22 parceiros, depois das 8 semanas, com os limiares de fábrica. Cada ramo da precedência tem pelo menos um parceiro desenhado para cair nele — e cinco deles satisfazem mais de um critério ao mesmo tempo.

**Onde está no código.**

- `api/app/servico_segmentacao.py`, `classificar`: os seis ramos, na ordem da regra
- `api/app/servico_segmentacao.py`, `Limiares`: os três limiares de fábrica
- `api/app/modelos.py`, `Segmento`: o enum declarado na ordem de precedência

**Testes automatizados que a cobram.**

- `api/tests/test_segmentacao.py::test_top_em_queda_sai_como_em_risco`
- `api/tests/test_segmentacao.py::test_a_ordem_do_enum_e_a_ordem_em_que_a_regra_decide`
- `api/tests/test_configuracao.py::test_os_limiares_de_fabrica_sao_os_de_rn01`

| O que se confere | Esperado | Voltou | |
|---|---|---|---|
| os limiares de fábrica: Top, tendência e recém-chegado | 15, 2, 3 | 15, 2, 3 | ok |
| marcada como prospecção, no Top e em queda: Prospecção vence tudo | PROSPECCAO | PROSPECCAO | ok |
| só duas semanas de histórico: Recém-chegado | RECEM_CHEGADO | RECEM_CHEGADO | ok |
| no Top e em queda há duas semanas: Em Risco vence Top | EM_RISCO | EM_RISCO | ok |
| fora do Top e em queda há duas semanas: Em Risco | EM_RISCO | EM_RISCO | ok |
| no Top e subindo há duas semanas: Top vence Em Ascensão | TOP | TOP | ok |
| acabou de entrar no Top, com uma alta só: Top | TOP | TOP | ok |
| fora do Top e subindo há duas semanas: Em Ascensão | EM_ASCENSAO | EM_ASCENSAO | ok |
| fora do Top, com uma queda só: Estável — uma queda não é tendência | ESTAVEL | ESTAVEL | ok |
| fora do Top, sem tendência: Estável | ESTAVEL | ESTAVEL | ok |
| os 22 parceiros, um a um, no segmento que a regra manda | Loja 01: TOP; Loja 02: EM_RISCO; Loja 03: TOP; Loja 04: TOP; Loja 05: TOP; Loja 06: TOP; Loja 07: TOP; Loja 08: TOP; Loja 09: TOP; Loja 10: TOP; Loja 11: TOP; Loja 12: TOP; Loja 13: TOP; Loja 14: PROSPECCAO; Loja 15: ESTAVEL; Loja 16: TOP; Loja 17: ESTAVEL; Loja 18: EM_ASCENSAO; Loja 19: EM_RISCO; Loja 20: RECEM_CHEGADO; Pizzaria Aurora: ESTAVEL; Pizzaria e Padaria Sol: ESTAVEL | Loja 01: TOP; Loja 02: EM_RISCO; Loja 03: TOP; Loja 04: TOP; Loja 05: TOP; Loja 06: TOP; Loja 07: TOP; Loja 08: TOP; Loja 09: TOP; Loja 10: TOP; Loja 11: TOP; Loja 12: TOP; Loja 13: TOP; Loja 14: PROSPECCAO; Loja 15: ESTAVEL; Loja 16: TOP; Loja 17: ESTAVEL; Loja 18: EM_ASCENSAO; Loja 19: EM_RISCO; Loja 20: RECEM_CHEGADO; Pizzaria Aurora: ESTAVEL; Pizzaria e Padaria Sol: ESTAVEL | ok |
| a distribuição do painel soma os mesmos segmentos | EM_ASCENSAO: 1; EM_RISCO: 2; ESTAVEL: 4; PROSPECCAO: 1; RECEM_CHEGADO: 1; TOP: 13 | EM_ASCENSAO: 1; EM_RISCO: 2; ESTAVEL: 4; PROSPECCAO: 1; RECEM_CHEGADO: 1; TOP: 13 | ok |
| cada parceiro tem exatamente um segmento: a distribuição soma a rede | 22 | 22 | ok |

## RN02 — Mobilidade do Top N lê o ranking, não o segmento

**Cenário.** Na última semana a Loja 16 passa a Loja 15 e entra no Top 15. A Loja 02 continua em 3º, mas está gravada como Em Risco: lida do segmento, ela apareceria como saída.

**Onde está no código.**

- `api/app/ranking.py`: as posições por faturamento, numa consulta só
- `api/app/rotas/painel.py`, `mobilidade`: compara as posições de dois períodos

**Testes automatizados que a cobram.**

- `api/tests/test_painel.py::test_top_em_queda_nao_aparece_como_saida`
- `api/tests/test_painel.py::test_mobilidade_lista_quem_entrou_e_quem_saiu`

| O que se confere | Esperado | Voltou | |
|---|---|---|---|
| o ranking da última semana, do maior faturamento para o menor | Loja 01, Loja 03, Loja 02, Loja 04, Loja 05, Loja 06, Loja 07, Loja 08, Loja 09, Loja 10, Loja 11, Loja 12, Loja 13, Loja 14, Loja 16, Loja 15, Loja 17, Loja 18, Loja 19, Loja 20, Pizzaria Aurora, Pizzaria e Padaria Sol | Loja 01, Loja 03, Loja 02, Loja 04, Loja 05, Loja 06, Loja 07, Loja 08, Loja 09, Loja 10, Loja 11, Loja 12, Loja 13, Loja 14, Loja 16, Loja 15, Loja 17, Loja 18, Loja 19, Loja 20, Pizzaria Aurora, Pizzaria e Padaria Sol | ok |
| a Loja 02 está em 3º no ranking | 3 | 3 | ok |
| e o segmento dela é Em Risco | EM_RISCO | EM_RISCO | ok |
| quem entrou no Top 15 | Loja 16 | Loja 16 | ok |
| quem saiu do Top 15 | Loja 15 | Loja 15 | ok |
| a Loja 02, no Top e em risco, não aparece como saída | não | não | ok |

## RN03 — Período é obrigatório na importação

**Cenário.** Antes de qualquer importação, o relatório da primeira semana é enviado sem as datas, e depois com o fim antes do início.

**Onde está no código.**

- `api/app/esquemas.py`, `PedidoImportacao`: as duas datas sem valor padrão
- `api/app/erros.py`: a recusa explica por que o período é necessário

**Testes automatizados que a cobram.**

- `api/tests/test_importacao.py::test_sem_periodo_a_importacao_e_recusada`
- `api/tests/test_importacao.py::test_nao_existe_periodo_padrao`

| O que se confere | Esperado | Voltou | |
|---|---|---|---|
| sem as datas, a importação é recusada | 422 | 422 | ok |
| a recusa aponta as duas datas | periodo_fim, periodo_inicio | periodo_fim, periodo_inicio | ok |
| com o fim antes do início, também | 422 | 422 | ok |
| nada foi gravado: o histórico de importações continua vazio | 0 | 0 | ok |

## RN04 — Ticket médio é derivado, nunca importado

**Cenário.** Cada parceiro foi importado com um ticket diferente. O ticket da rede, na última semana, é o faturamento somado dividido pelos pedidos somados.

**Onde está no código.**

- `api/app/calculos.py`, `ticket_medio`: a única conta, usada por todas as telas
- `api/app/modelos.py`, `Metrica`: só faturamento e pedidos

**Testes automatizados que a cobram.**

- `api/tests/test_importacao.py::test_ticket_medio_nao_e_gravado`
- `api/tests/test_painel.py::test_ticket_medio_e_a_razao_dos_totais_e_nao_a_media_das_medias`

| O que se confere | Esperado | Voltou | |
|---|---|---|---|
| a tabela de métricas não tem coluna de ticket | não | não | ok |
| o faturamento da rede é a soma do que foi importado | 210800.00 | 210800.00 | ok |
| os pedidos também | 4589 | 4589 | ok |
| o ticket é a razão dos totais | 45.94 | 45.94 | ok |
| e não a média dos tickets dos parceiros, que daria outro número | sim | sim | ok |

As colunas da tabela `metrica`: id, parceiro_id, periodo_id, importacao_id, faturamento, pedidos, projecao.

A média dos tickets dos parceiros daria 50.74; a razão dos totais é 45.94.

## RN05 — Categoria sugerida não é categoria confirmada

**Cenário.** Com as categorias "Pizzaria" e "Padaria" cadastradas, a importação traz "Pizzaria Aurora", cujo nome aponta uma categoria, e "Pizzaria e Padaria Sol", que aponta duas. Quatro lojas são classificadas à mão como Padaria.

**Onde está no código.**

- `api/app/sugestao_categoria.py`: a regra das palavras do nome
- `api/app/servico_importacao.py`: a sugestão entra com origem `INFERIDA`
- `api/app/servico_otimizacao.py`: a cota de categoria só conta a confirmada

**Testes automatizados que a cobram.**

- `api/tests/test_sugestao_categoria.py::test_nome_que_aponta_duas_categorias_nao_recebe_sugestao`
- `api/tests/test_sugestao_categoria.py::test_categoria_so_sugerida_continua_pendente_de_classificacao`
- `api/tests/test_campanha.py::test_categoria_so_conta_quando_confirmada`

| O que se confere | Esperado | Voltou | |
|---|---|---|---|
| o nome com uma categoria recebe a sugestão | Pizzaria | Pizzaria | ok |
| e a origem dela é inferida, e não manual | INFERIDA | INFERIDA | ok |
| o nome com duas categorias fica sem sugestão | None | None | ok |
| a só sugerida continua entre os pendentes de classificação | sim | sim | ok |
| a classificada à mão não está entre os pendentes | não | não | ok |
| classificar à mão marca a origem como manual | MANUAL | MANUAL | ok |

A outra metade da regra — a cota de categoria só conta a categoria confirmada — é conferida no plano de campanha, na RN11.

## RN06 — Nenhuma mensagem sai sem aprovação humana

**Cenário.** As mensagens do plano calculado são geradas pelo analista. Ele tenta aprovar uma; depois o gestor aprova uma e rejeita outra.

**Onde está no código.**

- `api/app/rotas/mensagens.py`: aprovar, editar e rejeitar só com o perfil Gestor
- `api/app/servico_aprovacao.py`: a decisão grava quem decidiu e quando
- `api/migrations/`: o banco recusa mensagem decidida sem autor

**Testes automatizados que a cobram.**

- `api/tests/test_aprovacao.py::test_o_analista_ve_a_fila_mas_nao_decide_e_a_tentativa_fica_na_auditoria`
- `api/tests/test_aprovacao.py::test_o_banco_recusa_mensagem_decidida_sem_autor`
- `api/tests/test_aprovacao.py::test_a_exportacao_traz_so_as_aprovadas_prontas_para_envio`

| O que se confere | Esperado | Voltou | |
|---|---|---|---|
| uma mensagem para cada ação do plano | 9 | 9 | ok |
| todas nascem pendentes | PENDENTE | PENDENTE | ok |
| com tudo pendente, o arquivo para envio não tem mensagem nenhuma | 1 | 1 | ok |
| o analista, que gerou, não aprova | 403 | 403 | ok |
| e a mensagem continua na fila | 9 | 9 | ok |
| o gestor aprova, e a decisão registra quem decidiu | APROVADA, Gestor da Revisão | APROVADA, Gestor da Revisão | ok |
| o gestor rejeita, com o motivo | REJEITADA, Tom errado | REJEITADA, Tom errado | ok |
| o arquivo para envio passa a ter só a aprovada | 2 | 2 | ok |
| a mensagem já decidida não é decidida de novo | 409 | 409 | ok |

## RN07 — O plano de campanha respeita todas as restrições ou não existe

**Cenário.** A mesma campanha, agora exigindo 90% das 9 ações para a Padaria — nove ações —, que tem quatro parceiros.

**Onde está no código.**

- `nucleo/gih_nucleo/viabilidade.py`: a viabilidade exata, antes da busca
- `api/app/servico_otimizacao.py`: a recusa com a restrição e quanto falta

**Testes automatizados que a cobram.**

- `api/tests/test_campanha.py::test_campanha_inviavel_diz_quanto_falta`
- `api/tests/test_campanha.py::test_o_plano_respeita_as_restricoes_e_e_o_otimo`
- `nucleo/tests/test_viabilidade.py::test_a_verificacao_e_exata`

| O que se confere | Esperado | Voltou | |
|---|---|---|---|
| o cálculo conclui dizendo que a campanha é inviável | CONCLUIDA, não | CONCLUIDA, não | ok |
| não há plano parcial: nenhuma ação | sim | sim | ok |
| a recusa nomeia a restrição violada | sim | sim | ok |
| e diz quanto falta | sim | sim | ok |

A restrição: `elegiveis_categoria`. O motivo: "Padaria tem 4 parceiros elegíveis, e a cota mínima exige 9 ações: faltam 5."

## RN08 — O modelo de linguagem não produz número

**Cenário.** A guarda é chamada com os fatos de uma mensagem gerada: uma vez com o texto dela, outra com o mesmo texto e um número acrescentado. Depois, o gestor edita uma mensagem e escreve um desconto que não está nos fatos.

**Onde está no código.**

- `api/app/guarda_numerica.py`: o texto com número que não veio dos fatos é reprovado
- `api/app/servico_mensagens.py`: texto reprovado vira modelo fixo
- `api/app/assistente/`: a resposta é montada dos fatos, e o modelo só redige

**Testes automatizados que a cobram.**

- `api/tests/test_guarda_numerica.py::test_numero_que_nao_veio_dos_fatos_e_apontado`
- `api/tests/test_mensagens.py::test_numero_inventado_troca_pelo_modelo_fixo_e_diz_qual`
- `api/tests/test_assistente.py::test_numero_inventado_nunca_chega_a_tela`

| O que se confere | Esperado | Voltou | |
|---|---|---|---|
| o texto gerado só tem números dos fatos | nenhum | nenhum | ok |
| o mesmo texto com um número acrescentado é reprovado, e a guarda diz qual | 37% | 37% | ok |
| nenhuma mensagem do lote chegou à fila com número fora dos fatos | nenhum | nenhum | ok |
| o número que o gestor escreveu fica apontado na fila, para ele conferir | 37% | 37% | ok |
| e a mensagem editada continua pendente: editar não aprova | PENDENTE | PENDENTE | ok |

As mensagens deste roteiro saíram do redator `MODELO_FIXO`: o modelo de linguagem não está no ar aqui, e o sistema funciona igual sem ele. O assistente com o modelo de verdade, com as perguntas sem resposta possível, está medido em `docs/medicoes/assistente.md`.

## RN09 — Queda prevista é entrar em risco, e o modelo exige histórico

**Cenário.** O treino é pedido com sete semanas importadas, e de novo com as oito. Depois, a previsão de três parceiros: um com histórico, um com duas semanas e um em prospecção.

**Onde está no código.**

- `api/app/servico_segmentacao.py`, `criterio_em_risco`: o rótulo do treino é a regra do segmento
- `modelo/gih_modelo/variaveis.py`: os mínimos de 8 períodos e de 4 de janela
- `api/app/servico_previsao.py`: a recusa, a versão em uso e quem recebe previsão

**Testes automatizados que a cobram.**

- `api/tests/test_previsao.py::test_o_rotulo_de_risco_e_o_segmento_em_risco`
- `api/tests/test_previsao.py::test_historico_curto_recusa_dizendo_quantos_faltam`
- `api/tests/test_previsao.py::test_versao_que_nao_supera_nao_entra_e_as_versoes_coexistem`
- `modelo/tests/test_variaveis.py::test_os_minimos_sao_os_da_rn09`

| O que se confere | Esperado | Voltou | |
|---|---|---|---|
| os mínimos do modelo: períodos para treinar e janela do parceiro | 8, 4 | 8, 4 | ok |
| com sete semanas, o treino é recusado | 409 | 409 | ok |
| a recusa diz quantos períodos faltam | sim | sim | ok |
| com as oito, o treino conclui | CONCLUIDO | CONCLUIDO | ok |
| a versão em uso é da rede só se ela superou a referência; senão, é a referência | REFERENCIA | REFERENCIA | ok |
| o rótulo de risco do treino é o critério do segmento: duas quedas seguidas | sim, não | sim, não | ok |
| mudar o limiar muda o rótulo junto: com três períodos, as duas quedas não bastam | não | não | ok |
| quem tem histórico recebe previsão | sim | sim | ok |
| a previsão diz a versão que a produziu | referencia-1 | referencia-1 | ok |
| e o período de onde parte, que é a última semana | 2026-07-20, 2026-07-26 | 2026-07-20, 2026-07-26 | ok |
| a chance de queda é uma probabilidade | sim | sim | ok |
| quem tem duas semanas de histórico não recebe previsão | não | não | ok |
| e a resposta diz por quê | sim | sim | ok |

A recusa: "O treino precisa de 8 períodos importados, e a base tem 7."

Neste cenário o treino não superou as referências, e a versão em uso ficou sendo `referencia-1`. O motivo registrado: "Não superou a referência: no faturamento, errou 655289243980,0% contra 4,1% de média móvel; no risco, teve Brier 0,287 contra 0,131 da taxa observada. Como nenhuma versão da rede superou as referências ainda, as previsões saem da referência."

O motivo para a Loja 20: "Com 2 períodos de histórico, ainda não há previsão: são necessários 4."

## RN10 — O ganho esperado de uma ação soma crescimento e perda evitada

**Cenário.** Para cada ação do plano calculado, o ganho é refeito aqui, a partir da previsão do parceiro e dos efeitos da ação no catálogo, e comparado com o que o plano traz.

**Onde está no código.**

- `api/app/servico_otimizacao.py`, `ganho_em_centavos`: a conta, em centavos inteiros
- `nucleo/`: recebe o ganho pronto, e não faz conta de dinheiro

**Testes automatizados que a cobram.**

- `api/tests/test_campanha.py::test_ganho_soma_crescimento_e_perda_evitada`
- `api/tests/test_campanha.py::test_o_ganho_de_cada_item_e_o_da_rn10`

| O que se confere | Esperado | Voltou | |
|---|---|---|---|
| o ganho das 9 ações do plano, refeito pela fórmula, ao centavo | nenhum | nenhum | ok |
| o ganho do plano é a soma dos ganhos das ações | 15448.64 | 15448.64 | ok |

Um exemplo: Loja 02, Destaque na vitrine: 18625.00 × 0.1400 + 18625.00 × 0.047619047619047616 × 0.0500 = 2651.85.

## RN11 — Quem recebe ação, e como as cotas contam

**Cenário.** Uma campanha de até 9 ações, com pelo menos 30% para a cauda longa e de 25% a 50% para a categoria Padaria. A Loja 17 foi desativada antes do cálculo.

**Onde está no código.**

- `api/app/servico_otimizacao.py`: a elegibilidade, as cotas em contagem e a cauda longa pelo ranking
- `nucleo/gih_nucleo/viabilidade.py`: a viabilidade decidida antes da busca

**Testes automatizados que a cobram.**

- `api/tests/test_campanha.py::test_quem_fica_fora_e_contado_por_motivo`
- `api/tests/test_campanha.py::test_cotas_viram_contagem_em_fracao_exata`
- `api/tests/test_campanha.py::test_a_cauda_longa_vem_do_ranking_e_nao_do_segmento`
- `api/tests/test_campanha.py::test_categoria_so_conta_quando_confirmada`

| O que se confere | Esperado | Voltou | |
|---|---|---|---|
| o cálculo conclui com um plano viável | CONCLUIDA, sim | CONCLUIDA, sim | ok |
| são elegíveis os ativos com previsão | 19 | 19 | ok |
| e quem ficou de fora é contado por motivo | historico_curto: 1; fora_do_periodo: 0; sem_previsao: 0; inativos: 1; em_prospeccao: 1 | historico_curto: 1; fora_do_periodo: 0; sem_previsao: 0; inativos: 1; em_prospeccao: 1 | ok |
| 30% de 9 ações vira contagem, para cima: ⌈2,7⌉ | 3 | 3 | ok |
| 25% a 50% de 9 viram ⌈2,25⌉ e ⌊4,5⌋ | 3, 4 | 3, 4 | ok |
| a cauda longa de cada item é a posição no ranking: fora das 15 primeiras | Loja 01: não; Loja 02: não; Loja 03: não; Loja 05: não; Loja 06: não; Loja 07: não; Loja 15: sim; Loja 18: sim; Loja 19: sim | Loja 01: não; Loja 02: não; Loja 03: não; Loja 05: não; Loja 06: não; Loja 07: não; Loja 15: sim; Loja 18: sim; Loja 19: sim | ok |
| o plano cumpre a cota mínima da cauda longa | sim | sim | ok |
| as ações da Padaria ficam entre o mínimo e o máximo | sim | sim | ok |
| e são todas de parceiros classificados à mão | sim | sim | ok |
| a Loja 02, Em Risco no segmento e 3ª no ranking, não conta como cauda longa | não | não | ok |
| nenhuma ação para quem não é elegível | nenhum | nenhum | ok |
| o plano respeita o máximo de ações e o orçamento | sim | sim | ok |

A Pizzaria Aurora não entrou no plano.

O plano: 9 ações, 3 para a cauda longa (Loja 15, Loja 18, Loja 19) e 3 para a Padaria (Loja 05, Loja 06, Loja 07); custo de R$ 2000.00 e ganho esperado de R$ 15448.64.
