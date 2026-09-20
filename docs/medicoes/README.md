# Medições

Resultados de desempenho medidos contra o sistema em execução. **Os arquivos deste diretório são
gerados por script** — não os edite à mão. Número escrito à mão não é evidência, e a diferença só
aparece na frente da banca.

| Arquivo | O que mede | História |
|---|---|---|
| [`painel-5000.md`](painel-5000.md) | Tempo de resposta do painel com 5.000 parceiros | H40 (RNF03, RNF05) |
| [`painel-10000.md`](painel-10000.md) | O mesmo no teto de carga do RNF04 | H40 |

## Como refazer

```bash
api/.venv/Scripts/python scripts/medir_painel.py
```

O script cria o banco `gih_medicao` na mesma instância do Postgres e gera a massa lá. **O banco de
trabalho não é tocado**: quem estiver com a aplicação aberta não perde os dados nem o usuário.

O comando exato de cada medição está dentro do próprio relatório, com a semente usada.

## O que torna estes números confiáveis

- **Repetições calibradas por alvo de tempo**, não fixas. Cinco repetições de uma passada curta medem o
  relógio, não o trabalho — foi o que enganou a equipe na validação do toolchain (H47), onde o mesmo
  binário deu 7,5x numa execução e 13,9x na seguinte.
- **Mediana, p95 e dispersão**, nunca um número só. Um valor isolado esconde justamente a variação.
- **`EXPLAIN (ANALYZE, BUFFERS)` de cada consulta que o endpoint realmente executou**, capturada do
  SQLAlchemy durante a chamada. Nenhuma foi reescrita à mão para o relatório.
- **`ANALYZE` antes de medir.** O gerador insere em massa e o autovacuum não teve tempo de rodar; sem
  atualizar as estatísticas, o planejador escolhe plano de um banco que não existe. Na primeira execução
  isso custou 46 ms no ranking contra 25 ms depois do `ANALYZE` — e fez a busca varrer a tabela em vez de
  usar o índice de trigrama.

## Varredura sequencial não é índice faltando

A primeira versão do script reprovava a busca por varrer `parceiro`. Estava errada: numa tabela de poucas
páginas, varrer é mais barato que ler o índice, e o planejador acerta ao escolher isso.

O que precisa ser verdade é outra coisa — que **exista índice capaz de atender o filtro quando a tabela
crescer**. Por isso, onde a varredura aparece numa consulta que filtra, a mesma consulta roda de novo com
`enable_seqscan = off`: se o plano passa a usar índice, era escolha do planejador; se continua varrendo,
falta índice, e a medição reprova.
