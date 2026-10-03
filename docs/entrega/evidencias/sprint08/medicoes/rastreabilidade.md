# 11 — Rastreabilidade

**Projeto:** Growth Intelligence Hub (GIH)
**Sprint:** 08 acadêmica — história **H98**
**Versão:** 1.0 — 02/10/2026

> **Para que serve.** "Todas as funcionalidades implementadas" é uma frase que qualquer documento escreve.
> Esta matriz a transforma em algo que se confere: para cada requisito, **onde** ele está — o caso de uso, a
> rota da API, a tela e um teste que o exercita. E quem confere não é quem escreveu:
> `api/tests/test_rastreabilidade.py` lê este arquivo a cada execução da suíte.

---

## 1. Como ler, e o que o teste cobra

Cada linha é um requisito de [02 — Requisitos](02-requisitos.md). As colunas:

- **Perfis** — os da coluna do próprio requisito: quem o acessa, para executar ou só para ler. Quem faz o
  quê em cada caso de uso está na matriz de permissões de [03 — Casos de uso](03-casos-de-uso.md).
- **Caso de uso** — o que o exercita, em `docs/03`.
- **Rotas** — as operações da API que o atendem.
- **Telas** — os endereços da interface em que ele aparece.
- **Testes** — um teste automatizado da API que o exercita, pelo nome, e o arquivo de testes da tela. Não é
  a lista de todos: é o fio que leva do requisito ao teste.

O teste reprova a suíte quando:

1. um requisito de `docs/02` não está nesta matriz, ou a matriz traz um que não existe;
2. o caso de uso citado não é um dos que `docs/03` associa ao requisito;
3. uma rota citada não existe na aplicação — ou **uma rota da aplicação não está neste documento**;
4. **os perfis do requisito não são os das rotas dele**: a união dos perfis que as rotas citadas aceitam
   precisa ser exatamente a coluna Perfis de `docs/02`. É a regra que pega o requisito que promete a um
   perfil o que a API nega, e a API que entrega a um perfil o que o requisito não previu;
5. uma tela citada não é um endereço da interface;
6. um arquivo de teste citado não existe, ou o teste citado pelo nome não está nele.

O que o teste **não** prova: que o teste citado é bom. Isso é da revisão de cada Pull Request e da cobertura
(RNF24).

---

## 2. Requisitos funcionais

### Módulo 1 — Autenticação, perfis e auditoria

| ID | Perfis | Caso de uso | Rotas | Telas | Testes | Situação |
|---|---|---|---|---|---|---|
| **RF01** | todos | UC01 | `POST /api/sessao`<br>`GET /api/sessao/atual` | `/entrar` | `api/tests/test_autenticacao.py::test_autentica_com_credenciais_validas`<br>`web/src/paginas/Login.test.jsx` | Implementado |
| **RF02** | todos | UC01 | `DELETE /api/sessao` | cabeçalho de toda tela | `api/tests/test_autenticacao.py::test_encerrar_invalida_a_sessao_no_servidor`<br>`web/src/App.teclado.test.jsx` | Implementado |
| **RF03** | ADM | UC02 | `GET /api/usuarios`<br>`POST /api/usuarios`<br>`GET /api/usuarios/{usuario_id}`<br>`PATCH /api/usuarios/{usuario_id}` | `/usuarios`<br>`/usuarios/novo`<br>`/usuarios/:id` | `api/tests/test_usuarios.py::test_desativar_derruba_as_sessoes_abertas`<br>`web/src/paginas/Usuarios.test.jsx`<br>`web/src/paginas/Usuario.test.jsx` | Implementado |
| **RF04** | ADM | UC02 | `POST /api/usuarios`<br>`PATCH /api/usuarios/{usuario_id}` | `/usuarios/novo`<br>`/usuarios/:id` | `api/tests/test_usuarios.py::test_troca_de_perfil_vale_na_requisicao_seguinte`<br>`web/src/paginas/Usuario.test.jsx` | Implementado |
| **RF05** | todos | UC02 | `GET /api/sessao/atual` | menu de toda tela; página "Sem acesso" | `api/tests/test_autorizacao.py::test_cada_endpoint_contra_cada_perfil`<br>`web/src/App.guarda.test.jsx` | Implementado (nota 1) |
| **RF06** | todos | UC14 | — | — | `api/tests/test_auditoria.py::test_alteracao_de_usuario_entra_na_trilha`<br>`api/tests/test_importacao.py::test_importacao_entra_na_auditoria`<br>`api/tests/test_campanha.py::test_a_execucao_fica_na_auditoria_com_parametros_modo_e_tempo`<br>`api/tests/test_aprovacao.py::test_aprovar_registra_quem_quando_e_o_conteudo_final` | Implementado (nota 2) |
| **RF07** | todos | UC01 | `POST /api/sessao/senha` | `/conta` | `api/tests/test_senha.py::test_exige_a_senha_atual`<br>`web/src/paginas/MinhaConta.test.jsx` | Implementado; a tela veio na Sprint 08 (H92) |
| **RF08** | ADM | UC14 | `GET /api/auditoria`<br>`GET /api/auditoria/acoes` | `/auditoria` | `api/tests/test_auditoria.py::test_filtra_por_intervalo_de_datas`<br>`web/src/paginas/Auditoria.test.jsx` | Implementado |

### Módulo 2 — Ingestão e gestão de dados

| ID | Perfis | Caso de uso | Rotas | Telas | Testes | Situação |
|---|---|---|---|---|---|---|
| **RF09** | GES, ANL | UC03 | `POST /api/importacoes`<br>`POST /api/importacoes/arquivo` | `/importacao` | `api/tests/test_importacao.py::test_importa_por_arquivo_csv`<br>`web/src/paginas/Importacao.test.jsx` | Implementado |
| **RF10** | GES, ANL | UC03 | `POST /api/importacoes`<br>`POST /api/importacoes/arquivo` | `/importacao` | `api/tests/test_importacao.py::test_sem_periodo_a_importacao_e_recusada` | Implementado |
| **RF11** | GES, ANL | UC03 | `POST /api/importacoes/previa`<br>`POST /api/importacoes/arquivo/previa` | `/importacao` | `api/tests/test_importacao.py::test_previa_traz_o_motivo_de_cada_rejeicao`<br>`web/src/paginas/Importacao.test.jsx` | Implementado |
| **RF12** | GES, ANL | UC03 | `POST /api/importacoes` | `/importacao` | `api/tests/test_importacao.py::test_substituir_troca_as_metricas_sem_duplicar` | Implementado |
| **RF13** | GES, ANL, ADM | UC03 | `GET /api/importacoes` | `/importacao` | `api/tests/test_importacao.py::test_historico_traz_o_autor` | Implementado |
| **RF14** | GES, ANL | UC04 | `GET /api/parceiros`<br>`POST /api/parceiros`<br>`GET /api/parceiros/{parceiro_id}`<br>`PATCH /api/parceiros/{parceiro_id}`<br>`DELETE /api/parceiros/{parceiro_id}`<br>`GET /api/categorias`<br>`POST /api/categorias` | `/parceiros`<br>`/parceiros/novo`<br>`/parceiros/:id` | `api/tests/test_parceiros.py::test_cadastra_parceiro`<br>`web/src/paginas/Parceiro.test.jsx` | Implementado |
| **RF15** | GES, ANL | UC04 | `GET /api/categorias/sugestao` | `/parceiros/novo`<br>`/parceiros/:id` | `api/tests/test_sugestao_categoria.py::test_a_rota_sugere_sem_gravar_nada`<br>`web/src/paginas/Parceiro.test.jsx` | Implementado |
| **RF16** | ADM | UC04 | — | — | `api/tests/test_cli.py::test_popular_demonstracao_gera_segmenta_e_treina` | Implementado, pelo terminal (nota 3) |

### Módulo 3 — Inteligência de negócio e segmentação

| ID | Perfis | Caso de uso | Rotas | Telas | Testes | Situação |
|---|---|---|---|---|---|---|
| **RF17** | GES, ANL, ADM | UC05 | `GET /api/painel/indicadores`<br>`GET /api/painel/recortes` | `/` | `api/tests/test_painel.py::test_indicadores_consolidam_o_periodo_mais_recente`<br>`web/src/paginas/Painel.test.jsx` | Implementado; perfis ajustados (nota 4) |
| **RF18** | GES, ANL, ADM | UC05 | `GET /api/painel/ranking` | `/` | `api/tests/test_painel.py::test_ranking_traz_posicao_anterior_e_variacao`<br>`web/src/paginas/Painel.test.jsx` | Implementado; perfis ajustados (nota 4) |
| **RF19** | GES, ANL, ADM, PAR | UC05, UC13 | `GET /api/painel/series`<br>`GET /api/meu-desempenho` | `/`<br>`/parceiros/:id`<br>`/meu-desempenho` | `api/tests/test_painel.py::test_serie_do_parceiro_traz_so_o_dele`<br>`web/src/componentes/SerieHistorica.test.jsx` | Implementado; perfis ajustados (nota 4) |
| **RF20** | GES, ANL, ADM | UC05 | `GET /api/parceiros`<br>`GET /api/painel/segmentos` | `/parceiros`<br>`/` | `api/tests/test_segmentacao.py::test_top_em_queda_sai_como_em_risco`<br>`api/tests/test_segmentacao.py::test_a_ordem_do_enum_e_a_ordem_em_que_a_regra_decide` | Implementado; perfis ajustados (nota 4) |
| **RF21** | ADM | UC05, UC06 | `GET /api/configuracao/segmentacao`<br>`PUT /api/configuracao/segmentacao` | `/configuracao` | `api/tests/test_configuracao.py::test_alterar_reclassifica_o_periodo_mais_recente`<br>`web/src/paginas/Configuracao.test.jsx` | Implementado |
| **RF22** | GES, ANL, ADM | UC06 | `GET /api/painel/mobilidade` | `/` | `api/tests/test_painel.py::test_top_em_queda_nao_aparece_como_saida`<br>`web/src/paginas/Painel.test.jsx` | Implementado; perfis ajustados (nota 4) |
| **RF23** | GES, ANL | UC05 | `GET /api/parceiros` | `/parceiros` | `api/tests/test_parceiros_recorte.py::test_ordena_pelo_campo_pedido`<br>`api/tests/test_parceiros_risco.py::test_ordena_por_risco_com_quem_nao_tem_previsao_no_fim`<br>`web/src/paginas/Parceiros.test.jsx` | Implementado |
| **RF24** | GES, ANL | UC05 | `GET /api/parceiros` | `/parceiros` | `api/tests/test_parceiros.py::test_busca_por_trecho_do_nome`<br>`web/src/paginas/Parceiros.test.jsx` | Implementado |
| **RF25** | GES, ANL | UC05 | `GET /api/parceiros/exportacao.csv` | `/parceiros` | `api/tests/test_parceiros_recorte.py::test_o_arquivo_reflete_exatamente_os_filtros_da_tela` | Implementado |
| **RF26** | PAR | UC13 | `GET /api/meu-desempenho` | `/meu-desempenho` | `api/tests/test_meu_desempenho.py::test_o_parceiro_ve_so_o_proprio_historico`<br>`web/src/paginas/MeuDesempenho.test.jsx` | Implementado |

### Módulo 4 — Núcleo computacional: previsão e otimização

| ID | Perfis | Caso de uso | Rotas | Telas | Testes | Situação |
|---|---|---|---|---|---|---|
| **RF27** | ADM, GES | UC07 | `GET /api/modelo`<br>`POST /api/modelo/treinos`<br>`GET /api/modelo/treinos`<br>`GET /api/modelo/treinos/{treino_id}` | `/modelo` | `api/tests/test_previsao.py::test_treinar_registra_data_volume_e_metricas`<br>`web/src/paginas/Modelo.test.jsx` | Implementado |
| **RF28** | GES, ANL | UC07 | `GET /api/parceiros/{parceiro_id}/previsao`<br>`GET /api/painel/decisao` | `/parceiros/:id`<br>`/parceiros`<br>`/` | `api/tests/test_previsao.py::test_previsao_no_cadastro_e_estimativa_com_base_e_versao`<br>`web/src/paginas/Parceiro.test.jsx` | Implementado |
| **RF29** | GES | UC08 | `POST /api/otimizacoes`<br>`POST /api/acoes-comerciais`<br>`PATCH /api/acoes-comerciais/{acao_id}` | `/campanha` | `api/tests/test_campanha.py::test_catalogo_cria_edita_e_audita`<br>`web/src/paginas/Campanha.test.jsx` | Implementado |
| **RF30** | GES | UC08 | `POST /api/otimizacoes` | `/campanha` | `api/tests/test_campanha.py::test_o_plano_respeita_as_restricoes_e_e_o_otimo`<br>`web/src/componentes/PlanoDeCampanha.test.jsx` | Implementado |
| **RF31** | GES | UC08 | `POST /api/otimizacoes` | `/campanha` | `api/tests/test_campanha.py::test_campanha_inviavel_diz_quanto_falta`<br>`web/src/paginas/Campanha.test.jsx` | Implementado |
| **RF32** | GES, ADM | UC09 | `POST /api/otimizacoes`<br>`POST /api/benchmarks` | `/campanha`<br>`/benchmark` | `api/tests/test_campanha.py::test_sem_escolha_roda_o_primeiro_disponivel_e_o_indisponivel_vira_troca`<br>`web/src/paginas/Campanha.test.jsx` | Implementado (nota 5) |
| **RF33** | GES, ADM | UC09 | `GET /api/benchmark`<br>`GET /api/benchmarks`<br>`GET /api/benchmarks/{execucao_id}` | `/benchmark` | `api/tests/test_benchmark.py::test_as_quatro_colunas_com_os_ganhos_contra_o_python_e_o_cpp`<br>`web/src/paginas/Benchmark.test.jsx` | Implementado |
| **RF34** | GES, ANL, ADM | UC09 | `GET /api/otimizacoes`<br>`GET /api/otimizacoes/{execucao_id}` | `/execucoes`<br>`/execucoes/:id` | `api/tests/test_campanha.py::test_o_historico_traz_o_que_o_rf34_pede`<br>`api/tests/test_campanha.py::test_o_administrador_ve_o_historico_mas_nao_abre_o_plano`<br>`web/src/paginas/Execucoes.test.jsx` | Implementado; perfis ajustados (nota 6) |
| **RF35** | GES, ANL | UC08 | `GET /api/otimizacoes/comparacao` | `/execucoes/comparar` | `api/tests/test_campanha.py::test_dois_planos_lado_a_lado_com_o_que_mudou`<br>`api/tests/test_campanha.py::test_o_analista_compara_e_o_administrador_nao`<br>`web/src/paginas/Comparacao.test.jsx` | Implementado; perfis ajustados (nota 6) |

### Módulo 5 — Central de comunicação

| ID | Perfis | Caso de uso | Rotas | Telas | Testes | Situação |
|---|---|---|---|---|---|---|
| **RF36** | GES, ANL | UC10 | `GET /api/mensagens/geracao`<br>`POST /api/mensagens/publico`<br>`POST /api/mensagens/lotes`<br>`GET /api/mensagens/lotes/{lote_id}`<br>`POST /api/mensagens/lotes/{lote_id}/refazer` | `/mensagens` | `api/tests/test_mensagens.py::test_por_plano_os_parceiros_do_plano_com_a_acao`<br>`web/src/paginas/Mensagens.test.jsx` | Implementado |
| **RF37** | GES, ANL | UC10 | `GET /api/mensagens` | `/aprovacao` | `api/tests/test_mensagens.py::test_as_mensagens_nascem_pendentes_no_banco`<br>`web/src/paginas/Aprovacao.test.jsx` | Implementado |
| **RF38** | GES | UC11 | `POST /api/mensagens/{mensagem_id}/aprovacao`<br>`POST /api/mensagens/{mensagem_id}/edicao`<br>`POST /api/mensagens/{mensagem_id}/rejeicao`<br>`POST /api/mensagens/aprovacao-em-lote` | `/aprovacao` | `api/tests/test_aprovacao.py::test_editar_guarda_o_original_e_a_mensagem_continua_pendente`<br>`web/src/paginas/Aprovacao.test.jsx` | Implementado |
| **RF39** | GES | UC11 | `POST /api/mensagens/{mensagem_id}/aprovacao`<br>`POST /api/mensagens/aprovacao-em-lote` | `/aprovacao` | `api/tests/test_aprovacao.py::test_o_analista_ve_a_fila_mas_nao_decide_e_a_tentativa_fica_na_auditoria`<br>`api/tests/test_aprovacao.py::test_o_banco_recusa_mensagem_decidida_sem_autor` | Implementado |
| **RF40** | GES, ANL | UC11 | `GET /api/mensagens`<br>`GET /api/mensagens/exportacao.csv` | `/aprovacao` | `api/tests/test_aprovacao.py::test_o_historico_traz_quem_decidiu_o_final_o_redigido_e_o_motivo`<br>`web/src/paginas/Aprovacao.test.jsx` | Implementado |

### Módulo 6 — Assistente analítico

| ID | Perfis | Caso de uso | Rotas | Telas | Testes | Situação |
|---|---|---|---|---|---|---|
| **RF41** | GES, ANL | UC12 | `GET /api/assistente`<br>`POST /api/assistente/perguntas` | `/assistente` | `api/tests/test_assistente.py::test_o_resumo_traz_os_numeros_do_painel`<br>`web/src/paginas/Assistente.test.jsx` | Implementado |
| **RF42** | GES, ANL | UC12 | `POST /api/assistente/perguntas` | `/assistente` | `api/tests/test_assistente.py::test_toda_resposta_com_numeros_traz_a_fonte`<br>`api/tests/test_assistente.py::test_fora_do_catalogo_o_assistente_se_abstem`<br>`web/src/paginas/Assistente.test.jsx` | Implementado |
| **RF43** | GES, ANL | UC12 | `POST /api/assistente/perguntas` | `/assistente` | `api/tests/test_assistente.py::test_numero_inventado_nunca_chega_a_tela`<br>`api/tests/test_guarda_numerica.py::test_numero_que_nao_veio_dos_fatos_e_apontado` | Implementado |

### Módulo 7 — Relatórios, consulta e acompanhamento

| ID | Perfis | Caso de uso | Rotas | Telas | Testes | Situação |
|---|---|---|---|---|---|---|
| **RF44** | GES, ANL | UC15 | `GET /api/relatorios/desempenho` | `/relatorios`<br>`/relatorios/desempenho` | `api/tests/test_relatorios.py::test_os_filtros_do_desempenho_recortam_e_a_resposta_diz_o_recorte`<br>`web/src/paginas/Relatorios.test.jsx` | Implementado |
| **RF45** | GES, ANL | UC15 | `GET /api/relatorios/risco` | `/relatorios/risco` | `api/tests/test_relatorios.py::test_o_risco_do_relatorio_e_o_do_cadastro_e_diz_de_que_modelo`<br>`web/src/paginas/Relatorios.test.jsx` | Implementado |
| **RF46** | GES, ANL | UC15 | `GET /api/relatorios/campanha`<br>`GET /api/relatorios/campanha/planos` | `/relatorios/campanha` | `api/tests/test_relatorios.py::test_a_campanha_por_acao_por_categoria_e_por_segmento`<br>`web/src/paginas/Relatorios.test.jsx` | Implementado |
| **RF47** | ADM | UC15 | `GET /api/relatorios/operacoes` | `/relatorios/operacoes` | `api/tests/test_relatorios.py::test_as_operacoes_somam_a_trilha_no_mesmo_recorte`<br>`web/src/paginas/Relatorios.test.jsx` | Implementado |
| **RF48** | GES, ANL, ADM | UC15 | `GET /api/relatorios/desempenho/exportacao.csv`<br>`GET /api/relatorios/risco/exportacao.csv`<br>`GET /api/relatorios/campanha/exportacao.csv`<br>`GET /api/relatorios/operacoes/exportacao.csv` | `/relatorios/desempenho`<br>`/relatorios/risco`<br>`/relatorios/campanha`<br>`/relatorios/operacoes` | `api/tests/test_relatorios.py::test_o_csv_do_desempenho_leva_o_recorte_da_tela`<br>`api/tests/test_relatorios.py::test_o_csv_das_operacoes_traz_os_tres_agrupamentos_e_o_total`<br>`web/src/paginas/Relatorios.test.jsx` | Implementado |
| **RF49** | ADM | UC14 | `GET /api/auditoria`<br>`GET /api/auditoria/exportacao.csv` | `/auditoria` | `api/tests/test_auditoria.py::test_busca_no_que_foi_gravado_e_em_quem_fez`<br>`api/tests/test_auditoria.py::test_exporta_o_recorte_da_tela_em_csv`<br>`web/src/paginas/Auditoria.test.jsx` | Implementado |
| **RF50** | GES, ANL | UC04 | `GET /api/parceiros/{parceiro_id}/historico` | `/parceiros/:id` | `api/tests/test_parceiros_historico.py::test_o_historico_conta_o_que_mudou_quando_e_por_quem`<br>`web/src/paginas/Parceiro.test.jsx` | Implementado |
| **RF51** | GES, ANL, ADM | UC09 | `GET /api/otimizacoes` | `/execucoes` | `api/tests/test_campanha.py::test_os_filtros_do_historico_se_combinam_e_o_total_e_o_do_recorte`<br>`web/src/paginas/Execucoes.test.jsx` | Implementado |
| **RF52** | ADM | UC02 | `GET /api/usuarios` | `/usuarios` | `api/tests/test_usuarios.py::test_busca_por_trecho_do_nome_ou_do_login`<br>`web/src/paginas/Usuarios.test.jsx` | Implementado |
| **RF53** | GES, ANL | UC08 | `GET /api/otimizacoes/{execucao_id}/exportacao.csv` | `/execucoes/:id` | `api/tests/test_campanha.py::test_o_csv_do_plano_traz_os_itens_da_tela_e_o_total` | Implementado |

### Módulo 8 — Conta, ajuda e vínculo do parceiro

| ID | Perfis | Caso de uso | Rotas | Telas | Testes | Situação |
|---|---|---|---|---|---|---|
| **RF54** | ADM | UC02 | `POST /api/usuarios/{usuario_id}/senha` | `/usuarios/:id` | `api/tests/test_usuarios_senha_e_vinculo.py::test_a_redefinicao_derruba_todas_as_sessoes_da_conta`<br>`web/src/paginas/Usuario.test.jsx` | Implementado na Sprint 08 (H93) |
| **RF55** | todos | UC16 | `GET /api/ajuda/regras`<br>`GET /api/sessao/atual` | `/ajuda` | `api/tests/test_ajuda.py::test_mudar_o_limiar_na_configuracao_muda_o_que_a_ajuda_diz`<br>`web/src/paginas/Ajuda.test.jsx` | Implementado na Sprint 08 (H95; nota 7) |
| **RF56** | ADM | UC02 | `GET /api/usuarios/parceiros` | `/usuarios/novo`<br>`/usuarios/:id` | `api/tests/test_usuarios_senha_e_vinculo.py::test_a_busca_devolve_so_o_nome_e_a_situacao`<br>`web/src/paginas/Usuario.test.jsx` | Implementado na Sprint 08 (H101) |

> **56 de 56 requisitos funcionais implementados**, cada um com rota, tela e teste — menos o RF06 e o RF16,
> que não têm rota nem tela próprias, pelos motivos das notas 2 e 3.

### Notas

1. **RF05 é transversal.** A restrição por perfil não tem uma rota: está em todas. A rota citada é a que diz à
   interface o que o perfil abre; o teste citado tenta cada rota da aplicação com cada perfil, e é o que
   sustenta o RNF14.
2. **RF06 também.** O registro na trilha acontece dentro de cada operação sensível, e por isso o requisito
   não tem rota nem tela: tem um teste por tipo de operação que o texto dele enumera. A consulta à trilha é o
   RF08.
3. **RF16 é do terminal.** O gerador de dados sintéticos é o `scripts/gerar_dados_sinteticos.py`, e a massa
   de demonstração entra pelo comando `popular-demonstracao`. Não há tela, de propósito: gerar a base inteira
   é operação de quem instala o sistema.
4. **O Administrador lê o painel.** A coluna Perfis de RF17, RF18, RF19, RF20 e RF22 dizia "GES, ANL". A
   matriz de permissões de `docs/03` dá ao Administrador a leitura do painel e da mobilidade desde a Sprint 1
   (UC05 e UC06, "somente leitura"), e a API sempre a entregou. A coluna foi corrigida em 02/10/2026 para
   dizer o que a matriz diz; nenhuma permissão mudou.
5. **RF32 e o Administrador.** O Administrador não calcula campanha. O modo de execução que ele escolhe é o
   do benchmark, que roda cada modo no mesmo problema (UC09); na campanha, quem escolhe é o Gestor.
6. **O Analista consulta os planos.** A coluna Perfis do RF34 dizia "GES, ADM", e a do RF35, "GES". O UC08 dá
   ao Analista a consulta dos planos desde a Sprint 1, e as histórias H58 e H59 a implementaram: ele vê o
   histórico das execuções, abre cada plano e compara dois. O Administrador vê o histórico e não abre o
   plano. A coluna foi corrigida em 02/10/2026.
7. **RF55 e o Parceiro.** A rota das regras é do Administrador, do Gestor e do Analista. O Parceiro abre a
   mesma tela, e ela lhe mostra só a ajuda do portal dele, sem pedir as regras (RF26); o que ele pode fazer
   sai da sessão.

---

## 3. Rotas de apoio

Rotas que não são de um requisito só: sustentam telas que juntam vários, ou a operação do sistema.

| Rota | Para que serve |
|---|---|
| `GET /api/health` | A verificação de saúde da aplicação e do banco, usada pelo Compose e pelo README (RNF07) |
| `GET /api/campanha` | O estado da tela da Campanha: o catálogo, o último plano e o que o perfil de quem pergunta pode fazer nela. É por ela que o Analista consulta o que o Gestor calculou (UC08) |
| `GET /api/acoes-comerciais` | O catálogo de ações, para a consulta do Gestor e do Analista (RF29) |
| `GET /api/parceiros/{parceiro_id}/campanha` | A ação do parceiro no último plano, no cadastro dele (H81) |

---

## 4. Requisitos não funcionais

Para cada um, onde a métrica de aceitação é conferida — por teste, por medição registrada ou por
configuração do repositório — e o que a conferência diz hoje.

| ID | Métrica de aceitação | Onde é conferido | Situação |
|---|---|---|---|
| **RNF01** | Até 5 s no cenário de referência | `docs/medicoes/nucleo.md` | Atende: 248 ms |
| **RNF02** | Speedup de 5x e uplift dentro de 2% | `docs/medicoes/nucleo.md`<br>`nucleo/tests/test_gpu.py::test_a_busca_na_gpu_e_a_do_python_numa_instancia_grande` | Atende: 106x, com o mesmo plano |
| **RNF03** | Painel em até 2 s com 5.000 parceiros | `docs/medicoes/painel-5000.md` | Atende |
| **RNF04** | 10.000 parceiros e 52 períodos | `docs/medicoes/painel-10000.md` | Parcial: medido com 10.000 parceiros e 12 períodos; os 52 períodos não foram medidos |
| **RNF05** | Consultas do painel sem varredura da tabela de métricas | `docs/medicoes/painel-5000.md`<br>`api/tests/test_painel.py::test_o_ranking_nao_faz_uma_consulta_por_linha` | Atende |
| **RNF06** | Fluxo completo sem GPU, com aviso | `api/tests/test_campanha.py::test_a_gpu_que_falha_no_calculo_cai_para_a_cpu`<br>`api/tests/test_campanha.py::test_a_tela_diz_por_que_nao_ha_gpu`<br>`nucleo/tests/test_gpu.py::test_sem_placa_o_executavel_recusa_com_saida_1` | Atende |
| **RNF07** | `docker compose up` de um clone limpo | `docker-compose.yml`<br>`docs/validacao-do-readme.md` | Parcial: sobe com um comando na máquina de desenvolvimento; a validação em máquina limpa é a H72, em aberto |
| **RNF08** | Chrome, Edge e Firefox | `scripts/medir_telas.py` | Parcial: medido no Edge; Chrome e Firefox não têm conferência automatizada |
| **RNF09** | Senha só como hash lento | `api/tests/test_autenticacao.py::test_senha_e_guardada_como_hash_lento`<br>`api/tests/test_auditoria.py::test_trilha_nunca_guarda_senha` | Atende |
| **RNF10** | Cookie HttpOnly e SameSite; identificador renovado | `api/tests/test_autenticacao.py::test_cookie_de_sessao_tem_as_marcacoes_do_rnf10`<br>`api/tests/test_autenticacao.py::test_novo_login_invalida_o_identificador_anterior` | Atende |
| **RNF11** | Bloqueio após 5 falhas; resposta igual | `api/tests/test_autenticacao.py::test_bloqueia_apos_cinco_falhas`<br>`api/tests/test_autenticacao.py::test_usuario_inexistente_e_senha_errada_respondem_igual` | Atende |
| **RNF12** | Saída escapada, com carga de script | `web/src/seguranca.test.jsx`<br>`api/tests/test_seguranca.py::test_a_exportacao_neutraliza_a_formula` | Atende |
| **RNF13** | Consultas parametrizadas, com carga de SQL | `api/tests/test_seguranca.py::test_nenhuma_consulta_e_montada_com_texto`<br>`api/tests/test_seguranca.py::test_carga_de_injecao_em_todo_parametro_de_toda_rota_de_leitura` | Atende |
| **RNF14** | Cada endpoint com cada perfil | `api/tests/test_autorizacao.py::test_cada_endpoint_contra_cada_perfil`<br>`api/tests/test_autorizacao.py::test_toda_rota_tem_permissao_declarada` | Atende |
| **RNF15** | Limite para o relatório e para a pergunta | `api/tests/test_importacao.py::test_entrada_grande_demais_e_recusada`<br>`api/tests/test_assistente.py::test_a_pergunta_acima_do_limite_e_recusada_com_o_limite` | Atende |
| **RNF16** | Reprocessar dá resultado idêntico | `api/tests/test_segmentacao.py::test_reprocessar_e_idempotente`<br>`api/tests/test_campanha.py::test_a_mesma_campanha_da_o_mesmo_plano`<br>`api/tests/test_assistente.py::test_toda_resposta_so_tem_numero_dos_fatos` | Atende |
| **RNF17** | Fonte ou insuficiência, com perguntas sem resposta | `api/tests/assistente/sem_resposta.json`<br>`api/tests/test_assistente.py::test_toda_resposta_com_numeros_traz_a_fonte`<br>`docs/medicoes/assistente.md` | Atende |
| **RNF18** | Nenhum rastreamento de pilha na resposta | `api/tests/test_erros.py::test_falha_inesperada_responde_generico_com_correlacao` | Atende |
| **RNF19** | Identificador de correlação na resposta e no log | `api/tests/test_erros.py::test_falha_inesperada_responde_generico_com_correlacao` | Atende |
| **RNF20** | Em português; operável sem treinamento | `api/tests/test_erros.py::test_nenhuma_mensagem_de_campo_sai_em_ingles`<br>`web/src/paginas/Ajuda.test.jsx` | Parcial: a interface está em português e tem ajuda; o fluxo com um usuário novo não foi observado |
| **RNF21** | Funcional a partir de 768 px | `docs/medicoes/acessibilidade.md`<br>`scripts/medir_telas.py` | Atende: 0 medidas com rolagem ou corte |
| **RNF22** | Contraste de 4,5:1 | `web/src/estilos/contraste.test.js`<br>`docs/medicoes/acessibilidade.md` | Atende |
| **RNF23** | Progresso em operações longas | `web/src/paginas/Campanha.test.jsx`<br>`web/src/paginas/Importacao.test.jsx`<br>`web/src/paginas/Modelo.test.jsx` | Atende |
| **RNF24** | Cobertura de 70% no núcleo de regras | `.github/workflows/ci.yml` | Atende: a CI reprova abaixo de 70% |
| **RNF25** | Pull Request revisado; nenhum push direto | `CONTRIBUTING.md` | Parcial: o ramo principal só recebe por Pull Request com a CI verde; a aprovação registrada no GitHub por outro integrante é pendência declarada |
| **RNF26** | CI com análise estática e testes | `.github/workflows/ci.yml` | Atende |
| **RNF27** | Um terceiro sobe o sistema só com o README | `docs/validacao-do-readme.md`<br>`README.md` | Em aberto: o roteiro está escrito, e a validação por quem não escreveu o código é a H72 |
| **RNF28** | Sem entidade de consumidor final | `docs/08-modelo-de-dados.md` | Atende |
| **RNF29** | Nenhum dado real no repositório | `.gitignore`<br>`.github/workflows/ci.yml` | Atende: a CI reprova arquivo de dados versionado |

> **29 requisitos não funcionais: 23 atendidos, 5 em parte (RNF04, RNF07, RNF08, RNF20, RNF25) e 1 em
> aberto (RNF27).** O que falta em cada um está dito na linha dele, e nenhum depende de código novo: são
> medições e validações.
