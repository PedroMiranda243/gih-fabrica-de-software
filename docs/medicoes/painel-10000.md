# Medição do painel com 10.000 parceiros — H40

> Gerado por `scripts/medir_painel.py`. **Não edite à mão**: número escrito à mão não é evidência. Para atualizar, rode o comando abaixo de novo.

O RNF03 fixa **2 s** como teto de resposta e a H40 cobra isso com 10.000 parceiros. Este arquivo é o registro da medição — a Sprint 12 não precisa medir de novo às pressas para pôr o número na apresentação.

## Ambiente

| Item | Valor |
|---|---|
| Data | 20/09/2026 02:09 |
| Banco | `gih_medicao` — **separado do banco de trabalho** |
| PostgreSQL | PostgreSQL 16.14 on x86_64-pc-linux-musl |
| Python | 3.11.9 |
| Massa | 10.000 parceiros · 12 períodos · 113.929 métricas |
| Semente | 42 |

A medição chama a aplicação em processo, pelo `TestClient`: cobre roteamento, autorização, consulta e serialização — tudo que o navegador espera, menos a rede.

## Como reproduzir

```bash
api/.venv/Scripts/python scripts/medir_painel.py --parceiros 10000 --periodos 12 --semente 42 --relatorio docs/medicoes/painel-10000.md
```

## Resultado

| Consulta | Chamadas | Mediana | p95 | Dispersão | Resposta | Dentro de 2 s |
|---|--:|--:|--:|--:|--:|:--:|
| `indicadores` | 300 | 17.8 ms | 19.2 ms | 7% | 381 B | sim |
| `ranking-25` | 133 | 42.9 ms | 45.0 ms | 5% | 6 kB | sim |
| `ranking-200` | 127 | 47.4 ms | 50.7 ms | 7% | 47 kB | sim |
| `serie` | 190 | 31.9 ms | 34.2 ms | 7% | 2 kB | sim |
| `segmentos` | 300 | 8.3 ms | 9.0 ms | 9% | 279 B | sim |
| `mobilidade` | 189 | 30.6 ms | 32.9 ms | 7% | 514 B | sim |
| `busca` | 113 | 21.5 ms | 49.0 ms | 127% | 128 kB | sim |
| `lista-completa` | 21 | 299.3 ms | 353.0 ms | 18% | 2026 kB | sim |

A dispersão é o quanto o p95 se afasta da mediana. Vai junto de propósito: um número só de tempo esconde a variação, e foi exatamente isso que enganou a equipe na validação do toolchain (H47).

## O que cada consulta faz

- **`indicadores`** — `GET /api/painel/indicadores` · Faturamento, pedidos, ticket e ativos do período, com variação (H30).
- **`ranking-25`** — `GET /api/painel/ranking?tamanho=25` · A página que o painel pede ao abrir (H31).
- **`ranking-200`** — `GET /api/painel/ranking?tamanho=200` · A maior página que a API aceita — o pior caso do ranking.
- **`serie`** — `GET /api/painel/series` · Série histórica da rede (H32).
- **`segmentos`** — `GET /api/painel/segmentos` · Distribuição por segmento do período (H33).
- **`mobilidade`** — `GET /api/painel/mobilidade` · Quem entrou e quem saiu do Top N (H35).
- **`busca`** — `GET /api/parceiros?busca=praca` · Busca por nome, sem sensibilidade a acentuação (H37).
- **`lista-completa`** — `GET /api/parceiros` · Lista de parceiros sem filtro — hoje sem paginação.

## Planos de execução

Cada consulta abaixo foi **capturada do SQLAlchemy durante a chamada** e passada por `EXPLAIN (ANALYZE, BUFFERS)`. Nenhuma foi reescrita à mão para o relatório.

**Varredura sequencial não é sinônimo de índice faltando.** Numa tabela de poucas páginas o planejador varre porque varrer é mais barato, e está certo. O que precisa ser verdade é que exista índice capaz de atender o filtro quando a tabela crescer — e é isso que a conferência com `enable_seqscan = off` mostra. A conferência só roda onde a varredura apareceu.

### `indicadores`

A consulta filtra `metrica`. Se o planejador varrer, a conferência abaixo diz se foi escolha dele ou falta de índice.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo ORDER BY periodo.data_inicio DESC, peri…`
  - tempo no banco: **0.01 ms** · varredura: `periodo`
- `SELECT coalesce(sum(metrica.faturamento), %(coalesce_2)s::INTEGER) AS coalesce_1, coalesce(sum(metrica.pedido…`
  - tempo no banco: **2.26 ms** · varredura: nenhuma
- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo WHERE periodo.data_inicio < %(data_inic…`
  - tempo no banco: **0.02 ms** · varredura: `periodo`
- `SELECT count(*) AS count_1, count(*) FILTER (WHERE historico_segmento.segmento = %(segmento_1)s) AS anon_1 FR…`
  - tempo no banco: **1.09 ms** · varredura: nenhuma

<details><summary>Plano completo</summary>

```
Limit  (cost=1.18..1.18 rows=1 width=12) (actual time=0.009..0.009 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.18..1.21 rows=12 width=12) (actual time=0.008..0.008 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.004..0.004 rows=12 loops=1)
              Buffers: shared hit=1
Planning Time: 0.036 ms
Execution Time: 0.015 ms
```

</details>

<details><summary>Plano completo</summary>

```
Aggregate  (cost=1453.75..1453.76 rows=1 width=48) (actual time=2.209..2.210 rows=1 loops=1)
  Buffers: shared hit=1011
  ->  Bitmap Heap Scan on metrica  (cost=290.71..1377.98 rows=10102 width=11) (actual time=0.469..1.400 rows=10000 loops=1)
        Recheck Cond: (periodo_id = 12)
        Heap Blocks: exact=961
        Buffers: shared hit=1011
        ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..288.18 rows=10102 width=0) (actual time=0.394..0.394 rows=10000 loops=1)
              Index Cond: (periodo_id = 12)
              Buffers: shared hit=50
Planning Time: 0.038 ms
Execution Time: 2.263 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=1.20..1.21 rows=1 width=12) (actual time=0.008..0.008 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.20..1.23 rows=11 width=12) (actual time=0.007..0.007 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.15 rows=11 width=12) (actual time=0.003..0.004 rows=11 loops=1)
              Filter: (data_inicio < '2026-09-07'::date)
              Rows Removed by Filter: 1
              Buffers: shared hit=1
Planning:
  Buffers: shared hit=2
Planning Time: 0.073 ms
Execution Time: 0.017 ms
```

</details>

<details><summary>Plano completo</summary>

```
Aggregate  (cost=1043.24..1043.25 rows=1 width=16) (actual time=1.042..1.042 rows=1 loops=1)
  Buffers: shared hit=75
  ->  Bitmap Heap Scan on historico_segmento  (cost=117.64..968.39 rows=9980 width=4) (actual time=0.121..0.587 rows=10000 loops=1)
        Recheck Cond: (periodo_id = 12)
        Heap Blocks: exact=65
        Buffers: shared hit=75
        ->  Bitmap Index Scan on ix_segmento_periodo_segmento  (cost=0.00..115.14 rows=9980 width=0) (actual time=0.109..0.109 rows=10000 loops=1)
              Index Cond: (periodo_id = 12)
              Buffers: shared hit=10
Planning Time: 0.035 ms
Execution Time: 1.087 ms
```

</details>

### `ranking-25`

A consulta filtra `metrica`. Se o planejador varrer, a conferência abaixo diz se foi escolha dele ou falta de índice.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo ORDER BY periodo.data_inicio DESC, peri…`
  - tempo no banco: **0.04 ms** · varredura: `periodo`
- `SELECT count(*) AS count_1 FROM (SELECT metrica.parceiro_id AS parceiro_id, metrica.faturamento AS faturament…`
  - tempo no banco: **5.72 ms** · varredura: `parceiro`
- `SELECT atual.parceiro_id, atual.faturamento, atual.pedidos, atual.posicao, parceiro.nome, categoria.nome AS n…`
  - tempo no banco: **19.04 ms** · varredura: `categoria`, `parceiro`
- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo WHERE periodo.data_inicio < %(data_inic…`
  - tempo no banco: **0.04 ms** · varredura: `periodo`
- `SELECT anterior.parceiro_id, anterior.posicao, anterior.faturamento FROM (SELECT metrica.parceiro_id AS parce…`
  - tempo no banco: **10.26 ms** · varredura: `parceiro`

<details><summary>Plano completo</summary>

```
Limit  (cost=1.18..1.18 rows=1 width=12) (actual time=0.021..0.022 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.18..1.21 rows=12 width=12) (actual time=0.020..0.021 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.005..0.006 rows=12 loops=1)
              Buffers: shared hit=1
Planning Time: 0.047 ms
Execution Time: 0.041 ms
```

</details>

<details><summary>Plano completo</summary>

```
Aggregate  (cost=1886.79..1886.80 rows=1 width=8) (actual time=5.527..5.528 rows=1 loops=1)
  Buffers: shared hit=1142
  ->  Hash Join  (cost=646.71..1760.51 rows=10102 width=40) (actual time=2.602..5.147 rows=10000 loops=1)
        Hash Cond: (metrica.parceiro_id = parceiro.id)
        Buffers: shared hit=1142
        ->  Bitmap Heap Scan on metrica  (cost=290.71..1377.98 rows=10102 width=11) (actual time=0.530..1.762 rows=10000 loops=1)
              Recheck Cond: (periodo_id = 12)
              Heap Blocks: exact=961
              Buffers: shared hit=1011
              ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..288.18 rows=10102 width=0) (actual time=0.449..0.449 rows=10000 loops=1)
                    Index Cond: (periodo_id = 12)
                    Buffers: shared hit=50
        ->  Hash  (cost=231.00..231.00 rows=10000 width=21) (actual time=1.990..1.990 rows=10000 loops=1)
              Buckets: 16384  Batches: 1  Memory Usage: 668kB
              Buffers: shared hit=131
              ->  Seq Scan on parceiro  (cost=0.00..231.00 rows=10000 width=21) (actual time=0.004..0.663 rows=10000 loops=1)
                    Buffers: shared hit=131
Planning:
  Buffers: shared hit=12
Planning Time: 0.262 ms
Execution Time: 5.725 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=4569.85..4569.91 rows=25 width=54) (actual time=18.354..18.359 rows=25 loops=1)
  Buffers: shared hit=1349
  ->  Sort  (cost=4569.85..4595.82 rows=10390 width=54) (actual time=18.353..18.356 rows=25 loops=1)
        Sort Key: (row_number() OVER (?))
        Sort Method: top-N heapsort  Memory: 28kB
        Buffers: shared hit=1349
        ->  Hash Left Join  (cost=3882.78..4276.65 rows=10390 width=54) (actual time=11.269..17.186 rows=10000 loops=1)
              Hash Cond: (metrica.parceiro_id = historico_segmento.parceiro_id)
              Buffers: shared hit=1349
              ->  Hash Left Join  (cost=2789.64..3156.98 rows=10102 width=50) (actual time=9.474..14.262 rows=10000 loops=1)
                    Hash Cond: (parceiro.categoria_id = categoria.id)
                    Buffers: shared hit=1274
                    ->  Hash Join  (cost=2788.41..3118.00 rows=10102 width=44) (actual time=9.446..13.226 rows=10000 loops=1)
                          Hash Cond: (metrica.parceiro_id = parceiro.id)
                          Buffers: shared hit=1273
                          ->  WindowAgg  (cost=2432.41..2634.45 rows=10102 width=40) (actual time=7.428..9.511 rows=10000 loops=1)
                                Buffers: shared hit=1142
                                ->  Sort  (cost=2432.41..2457.67 rows=10102 width=32) (actual time=7.415..7.977 rows=10000 loops=1)
                                      Sort Key: metrica.faturamento DESC, parceiro_1.nome
                                      Sort Method: quicksort  Memory: 978kB
                                      Buffers: shared hit=1142
                                      ->  Hash Join  (cost=646.71..1760.51 rows=10102 width=32) (actual time=2.297..4.912 rows=10000 loops=1)
                                            Hash Cond: (metrica.parceiro_id = parceiro_1.id)
                                            Buffers: shared hit=1142
                                            ->  Bitmap Heap Scan on metrica  (cost=290.71..1377.98 rows=10102 width=15) (actual time=0.516..1.767 rows=10000 loops=1)
                                                  Recheck Cond: (periodo_id = 12)
                                                  Heap Blocks: exact=961
                                                  Buffers: shared hit=1011
                                                  ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..288.18 rows=10102 width=0) (actual time=0.441..0.441 rows=10000 loops=1)
                                                        Index Cond: (periodo_id = 12)
                                                        Buffers: shared hit=50
                                            ->  Hash  (cost=231.00..231.00 rows=10000 width=21) (actual time=1.712..1.712 rows=10000 loops=1)
                                                  Buckets: 16384  Batches: 1  Memory Usage: 668kB
                                                  Buffers: shared hit=131
                                                  ->  Seq Scan on parceiro parceiro_1  (cost=0.00..231.00 rows=10000 width=21) (actual time=0.004..0.519 rows=10000 loops=1)
                                                        Buffers: shared hit=131
                          ->  Hash  (cost=231.00..231.00 rows=10000 width=25) (actual time=1.949..1.950 rows=10000 loops=1)
                                Buckets: 16384  Batches: 1  Memory Usage: 707kB
                                Buffers: shared hit=131
                                ->  Seq Scan on parceiro  (cost=0.00..231.00 rows=10000 width=25) (actual time=0.003..0.662 rows=10000 loops=1)
                                      Buffers: shared hit=131
                    ->  Hash  (cost=1.10..1.10 rows=10 width=14) (actual time=0.017..0.017 rows=10 loops=1)
                          Buckets: 1024  Batches: 1  Memory Usage: 9kB
                          Buffers: shared hit=1
                          ->  Seq Scan on categoria  (cost=0.00..1.10 rows=10 width=14) (actual time=0.004..0.005 rows=10 loops=1)
                                Buffers: shared hit=1
              ->  Hash  (cost=968.39..968.39 rows=9980 width=8) (actual time=1.726..1.726 rows=10000 loops=1)
                    Buckets: 16384  Batches: 1  Memory Usage: 519kB
                    Buffers: shared hit=75
                    ->  Bitmap Heap Scan on historico_segmento  (cost=117.64..968.39 rows=9980 width=8) (actual time=0.125..0.765 rows=10000 loops=1)
                          Recheck Cond: (periodo_id = 12)
                          Heap Blocks: exact=65
                          Buffers: shared hit=75
                          ->  Bitmap Index Scan on ix_segmento_periodo_segmento  (cost=0.00..115.14 rows=9980 width=0) (actual time=0.119..0.119 rows=10000 loops=1)
                                Index Cond: (periodo_id = 12)
                                Buffers: shared hit=10
Planning:
  Buffers: shared hit=30
Planning Time: 0.567 ms
Execution Time: 19.040 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=1.20..1.21 rows=1 width=12) (actual time=0.022..0.023 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.20..1.23 rows=11 width=12) (actual time=0.022..0.022 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.15 rows=11 width=12) (actual time=0.004..0.006 rows=11 loops=1)
              Filter: (data_inicio < '2026-09-07'::date)
              Rows Removed by Filter: 1
              Buffers: shared hit=1
Planning:
  Buffers: shared hit=2
Planning Time: 0.089 ms
Execution Time: 0.042 ms
```

</details>

<details><summary>Plano completo</summary>

```
Subquery Scan on anterior  (cost=2388.59..2729.14 rows=25 width=19) (actual time=7.693..9.906 rows=25 loops=1)
  Filter: (anterior.parceiro_id = ANY ('{4133,2118,8156,4648,2384,2515,1577,1682,6266,6144,4544,3134,3103,4155,924,246,4101,8777,3997,4254,5834,6210,3194,460,9809}'::integer[]))
  Rows Removed by Filter: 9791
  Buffers: shared hit=1146
  ->  WindowAgg  (cost=2388.53..2583.13 rows=9730 width=40) (actual time=7.691..9.415 rows=9816 loops=1)
        Buffers: shared hit=1146
        ->  Sort  (cost=2388.53..2412.85 rows=9730 width=28) (actual time=7.674..8.028 rows=9816 loops=1)
              Sort Key: metrica.faturamento DESC, parceiro.nome
              Sort Method: quicksort  Memory: 922kB
              Buffers: shared hit=1146
              ->  Hash Join  (cost=635.83..1744.00 rows=9730 width=28) (actual time=2.474..5.234 rows=9816 loops=1)
                    Hash Cond: (metrica.parceiro_id = parceiro.id)
                    Buffers: shared hit=1146
                    ->  Bitmap Heap Scan on metrica  (cost=279.83..1362.45 rows=9730 width=11) (actual time=0.579..1.959 rows=9816 loops=1)
                          Recheck Cond: (periodo_id = 11)
                          Heap Blocks: exact=961
                          Buffers: shared hit=1015
                          ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..277.39 rows=9730 width=0) (actual time=0.501..0.501 rows=9816 loops=1)
                                Index Cond: (periodo_id = 11)
                                Buffers: shared hit=54
                    ->  Hash  (cost=231.00..231.00 rows=10000 width=21) (actual time=1.829..1.829 rows=10000 loops=1)
                          Buckets: 16384  Batches: 1  Memory Usage: 668kB
                          Buffers: shared hit=131
                          ->  Seq Scan on parceiro  (cost=0.00..231.00 rows=10000 width=21) (actual time=0.003..0.621 rows=10000 loops=1)
                                Buffers: shared hit=131
Planning:
  Buffers: shared hit=12
Planning Time: 0.239 ms
Execution Time: 10.258 ms
```

</details>

### `ranking-200`

A consulta filtra `metrica`. Se o planejador varrer, a conferência abaixo diz se foi escolha dele ou falta de índice.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo ORDER BY periodo.data_inicio DESC, peri…`
  - tempo no banco: **0.05 ms** · varredura: `periodo`
- `SELECT count(*) AS count_1 FROM (SELECT metrica.parceiro_id AS parceiro_id, metrica.faturamento AS faturament…`
  - tempo no banco: **6.36 ms** · varredura: `parceiro`
- `SELECT atual.parceiro_id, atual.faturamento, atual.pedidos, atual.posicao, parceiro.nome, categoria.nome AS n…`
  - tempo no banco: **20.92 ms** · varredura: `categoria`, `parceiro`
- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo WHERE periodo.data_inicio < %(data_inic…`
  - tempo no banco: **0.04 ms** · varredura: `periodo`
- `SELECT anterior.parceiro_id, anterior.posicao, anterior.faturamento FROM (SELECT metrica.parceiro_id AS parce…`
  - tempo no banco: **11.82 ms** · varredura: `parceiro`

<details><summary>Plano completo</summary>

```
Limit  (cost=1.18..1.18 rows=1 width=12) (actual time=0.027..0.027 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.18..1.21 rows=12 width=12) (actual time=0.026..0.026 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.006..0.007 rows=12 loops=1)
              Buffers: shared hit=1
Planning Time: 0.064 ms
Execution Time: 0.050 ms
```

</details>

<details><summary>Plano completo</summary>

```
Aggregate  (cost=1886.79..1886.80 rows=1 width=8) (actual time=6.077..6.079 rows=1 loops=1)
  Buffers: shared hit=1142
  ->  Hash Join  (cost=646.71..1760.51 rows=10102 width=40) (actual time=2.854..5.739 rows=10000 loops=1)
        Hash Cond: (metrica.parceiro_id = parceiro.id)
        Buffers: shared hit=1142
        ->  Bitmap Heap Scan on metrica  (cost=290.71..1377.98 rows=10102 width=11) (actual time=0.605..1.882 rows=10000 loops=1)
              Recheck Cond: (periodo_id = 12)
              Heap Blocks: exact=961
              Buffers: shared hit=1011
              ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..288.18 rows=10102 width=0) (actual time=0.520..0.520 rows=10000 loops=1)
                    Index Cond: (periodo_id = 12)
                    Buffers: shared hit=50
        ->  Hash  (cost=231.00..231.00 rows=10000 width=21) (actual time=2.180..2.180 rows=10000 loops=1)
              Buckets: 16384  Batches: 1  Memory Usage: 668kB
              Buffers: shared hit=131
              ->  Seq Scan on parceiro  (cost=0.00..231.00 rows=10000 width=21) (actual time=0.004..0.938 rows=10000 loops=1)
                    Buffers: shared hit=131
Planning:
  Buffers: shared hit=12
Planning Time: 0.317 ms
Execution Time: 6.357 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=4725.70..4726.20 rows=200 width=54) (actual time=20.027..20.045 rows=200 loops=1)
  Buffers: shared hit=1349
  ->  Sort  (cost=4725.70..4751.67 rows=10390 width=54) (actual time=20.026..20.034 rows=200 loops=1)
        Sort Key: (row_number() OVER (?))
        Sort Method: top-N heapsort  Memory: 51kB
        Buffers: shared hit=1349
        ->  Hash Left Join  (cost=3882.78..4276.65 rows=10390 width=54) (actual time=12.589..18.676 rows=10000 loops=1)
              Hash Cond: (metrica.parceiro_id = historico_segmento.parceiro_id)
              Buffers: shared hit=1349
              ->  Hash Left Join  (cost=2789.64..3156.98 rows=10102 width=50) (actual time=10.388..15.145 rows=10000 loops=1)
                    Hash Cond: (parceiro.categoria_id = categoria.id)
                    Buffers: shared hit=1274
                    ->  Hash Join  (cost=2788.41..3118.00 rows=10102 width=44) (actual time=10.363..14.110 rows=10000 loops=1)
                          Hash Cond: (metrica.parceiro_id = parceiro.id)
                          Buffers: shared hit=1273
                          ->  WindowAgg  (cost=2432.41..2634.45 rows=10102 width=40) (actual time=8.148..10.088 rows=10000 loops=1)
                                Buffers: shared hit=1142
                                ->  Sort  (cost=2432.41..2457.67 rows=10102 width=32) (actual time=8.136..8.593 rows=10000 loops=1)
                                      Sort Key: metrica.faturamento DESC, parceiro_1.nome
                                      Sort Method: quicksort  Memory: 978kB
                                      Buffers: shared hit=1142
                                      ->  Hash Join  (cost=646.71..1760.51 rows=10102 width=32) (actual time=2.679..5.482 rows=10000 loops=1)
                                            Hash Cond: (metrica.parceiro_id = parceiro_1.id)
                                            Buffers: shared hit=1142
                                            ->  Bitmap Heap Scan on metrica  (cost=290.71..1377.98 rows=10102 width=15) (actual time=0.540..1.803 rows=10000 loops=1)
                                                  Recheck Cond: (periodo_id = 12)
                                                  Heap Blocks: exact=961
                                                  Buffers: shared hit=1011
                                                  ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..288.18 rows=10102 width=0) (actual time=0.460..0.460 rows=10000 loops=1)
                                                        Index Cond: (periodo_id = 12)
                                                        Buffers: shared hit=50
                                            ->  Hash  (cost=231.00..231.00 rows=10000 width=21) (actual time=2.057..2.058 rows=10000 loops=1)
                                                  Buckets: 16384  Batches: 1  Memory Usage: 668kB
                                                  Buffers: shared hit=131
                                                  ->  Seq Scan on parceiro parceiro_1  (cost=0.00..231.00 rows=10000 width=21) (actual time=0.003..0.534 rows=10000 loops=1)
                                                        Buffers: shared hit=131
                          ->  Hash  (cost=231.00..231.00 rows=10000 width=25) (actual time=2.146..2.147 rows=10000 loops=1)
                                Buckets: 16384  Batches: 1  Memory Usage: 707kB
                                Buffers: shared hit=131
                                ->  Seq Scan on parceiro  (cost=0.00..231.00 rows=10000 width=25) (actual time=0.004..0.767 rows=10000 loops=1)
                                      Buffers: shared hit=131
                    ->  Hash  (cost=1.10..1.10 rows=10 width=14) (actual time=0.016..0.016 rows=10 loops=1)
                          Buckets: 1024  Batches: 1  Memory Usage: 9kB
                          Buffers: shared hit=1
                          ->  Seq Scan on categoria  (cost=0.00..1.10 rows=10 width=14) (actual time=0.004..0.005 rows=10 loops=1)
                                Buffers: shared hit=1
              ->  Hash  (cost=968.39..968.39 rows=9980 width=8) (actual time=2.135..2.135 rows=10000 loops=1)
                    Buckets: 16384  Batches: 1  Memory Usage: 519kB
                    Buffers: shared hit=75
                    ->  Bitmap Heap Scan on historico_segmento  (cost=117.64..968.39 rows=9980 width=8) (actual time=0.124..1.104 rows=10000 loops=1)
                          Recheck Cond: (periodo_id = 12)
                          Heap Blocks: exact=65
                          Buffers: shared hit=75
                          ->  Bitmap Index Scan on ix_segmento_periodo_segmento  (cost=0.00..115.14 rows=9980 width=0) (actual time=0.118..0.118 rows=10000 loops=1)
                                Index Cond: (periodo_id = 12)
                                Buffers: shared hit=10
Planning:
  Buffers: shared hit=30
Planning Time: 0.542 ms
Execution Time: 20.920 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=1.20..1.21 rows=1 width=12) (actual time=0.017..0.018 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.20..1.23 rows=11 width=12) (actual time=0.017..0.017 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.15 rows=11 width=12) (actual time=0.003..0.004 rows=11 loops=1)
              Filter: (data_inicio < '2026-09-07'::date)
              Rows Removed by Filter: 1
              Buffers: shared hit=1
Planning:
  Buffers: shared hit=2
Planning Time: 0.100 ms
Execution Time: 0.035 ms
```

</details>

<details><summary>Plano completo</summary>

```
Subquery Scan on anterior  (cost=2389.03..2729.58 rows=200 width=19) (actual time=8.822..11.279 rows=199 loops=1)
  Filter: (anterior.parceiro_id = ANY ('{4133,2118,8156,4648,2384,2515,1577,1682,6266,6144,4544,3134,3103,4155,924,246,4101,8777,3997,4254,5834,6210,3194,460,9809,7117,2744,1563,2272,2149,6700,8924,6061,5275,1823,4982,4468,5788,9656,9927,6772,1917,2260,4729,3721,2999,4676,983,9817,5323,7651,1660,6952,1242,1307,4716,7128,8044,7384,9527,2864,1936,9344,3217,7656,9814,9490,9892,3270,9104,6606,7911,3662,3453,5257,7609,7619,7033,9142,5998,2470,1395,3736,8553,7965,9573,9386,4885,9035,3133,6999,1793,2311,4340,6693,8137,4654,6290,3621,8365,9904,9534,613,9094,9030,1586,181,7732,9952,2134,1348,600,7674,7023,1265,5022,1019,2336,8625,2314,860,1754,484,8398,9248,5690,5315,5193,2666,6518,2914,9681,2050,1067,6956,5609,214,6190,2125,1010,2044,1393,2831,3389,2539,74,5897,7921,1825,7320,8519,1896,6522,9481,381,1382,9717,6382,5865,6706,6222,6070,7794,6511,3415,4890,2053,549,9754,6676,6773,885,6677,8839,6766,3090,3576,6704,8130,823,906,2074,9332,8698,510,5953,5166,8311,9883,7731,4268,2512,2980,9165,6100,8177,2520,3273,9249,9170}'::integer[]))
  Rows Removed by Filter: 9617
  Buffers: shared hit=1146
  ->  WindowAgg  (cost=2388.53..2583.13 rows=9730 width=40) (actual time=8.813..10.625 rows=9816 loops=1)
        Buffers: shared hit=1146
        ->  Sort  (cost=2388.53..2412.85 rows=9730 width=28) (actual time=8.804..9.186 rows=9816 loops=1)
              Sort Key: metrica.faturamento DESC, parceiro.nome
              Sort Method: quicksort  Memory: 922kB
              Buffers: shared hit=1146
              ->  Hash Join  (cost=635.83..1744.00 rows=9730 width=28) (actual time=2.541..5.643 rows=9816 loops=1)
                    Hash Cond: (metrica.parceiro_id = parceiro.id)
                    Buffers: shared hit=1146
                    ->  Bitmap Heap Scan on metrica  (cost=279.83..1362.45 rows=9730 width=11) (actual time=0.558..2.037 rows=9816 loops=1)
                          Recheck Cond: (periodo_id = 11)
                          Heap Blocks: exact=961
                          Buffers: shared hit=1015
                          ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..277.39 rows=9730 width=0) (actual time=0.481..0.481 rows=9816 loops=1)
                                Index Cond: (periodo_id = 11)
                                Buffers: shared hit=54
                    ->  Hash  (cost=231.00..231.00 rows=10000 width=21) (actual time=1.900..1.901 rows=10000 loops=1)
                          Buckets: 16384  Batches: 1  Memory Usage: 668kB
                          Buffers: shared hit=131
                          ->  Seq Scan on parceiro  (cost=0.00..231.00 rows=10000 width=21) (actual time=0.005..0.693 rows=10000 loops=1)
                                Buffers: shared hit=131
Planning:
  Buffers: shared hit=12
Planning Time: 0.673 ms
Execution Time: 11.821 ms
```

</details>

### `serie`

A série agrega **todos** os períodos: a consulta lê a tabela inteira por definição, e varrer é o plano certo.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim, sum(metrica.faturamento) AS sum_1, sum(metrica.pedi…`
  - tempo no banco: **34.35 ms** · varredura: `metrica`, `periodo`

<details><summary>Plano completo</summary>

```
Sort  (cost=3361.08..3361.11 rows=12 width=52) (actual time=34.298..34.300 rows=12 loops=1)
  Sort Key: periodo.data_inicio, periodo.id
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=962
  ->  HashAggregate  (cost=3360.71..3360.86 rows=12 width=52) (actual time=34.289..34.292 rows=12 loops=1)
        Group Key: periodo.id
        Batches: 1  Memory Usage: 24kB
        Buffers: shared hit=962
        ->  Hash Right Join  (cost=1.27..2506.24 rows=113929 width=23) (actual time=0.025..19.910 rows=113929 loops=1)
              Hash Cond: (metrica.periodo_id = periodo.id)
              Buffers: shared hit=962
              ->  Seq Scan on metrica  (cost=0.00..2100.29 rows=113929 width=15) (actual time=0.002..4.819 rows=113929 loops=1)
                    Buffers: shared hit=961
              ->  Hash  (cost=1.12..1.12 rows=12 width=12) (actual time=0.018..0.019 rows=12 loops=1)
                    Buckets: 1024  Batches: 1  Memory Usage: 9kB
                    Buffers: shared hit=1
                    ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.003..0.004 rows=12 loops=1)
                          Buffers: shared hit=1
Planning:
  Buffers: shared hit=4
Planning Time: 0.169 ms
Execution Time: 34.349 ms
```

</details>

### `segmentos`

A consulta filtra `historico_segmento`. Se o planejador varrer, a conferência abaixo diz se foi escolha dele ou falta de índice.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo ORDER BY periodo.data_inicio DESC, peri…`
  - tempo no banco: **0.01 ms** · varredura: `periodo`
- `SELECT historico_segmento.segmento, count(*) AS count_1 FROM historico_segmento WHERE historico_segmento.peri…`
  - tempo no banco: **0.91 ms** · varredura: nenhuma

<details><summary>Plano completo</summary>

```
Limit  (cost=1.18..1.18 rows=1 width=12) (actual time=0.006..0.007 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.18..1.21 rows=12 width=12) (actual time=0.006..0.006 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.003..0.003 rows=12 loops=1)
              Buffers: shared hit=1
Planning Time: 0.044 ms
Execution Time: 0.011 ms
```

</details>

<details><summary>Plano completo</summary>

```
Sort  (cost=264.95..264.96 rows=5 width=12) (actual time=0.895..0.895 rows=5 loops=1)
  Sort Key: (count(*)) DESC, segmento
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=11
  ->  GroupAggregate  (cost=0.29..264.89 rows=5 width=12) (actual time=0.068..0.891 rows=5 loops=1)
        Group Key: segmento
        Buffers: shared hit=11
        ->  Index Only Scan using ix_segmento_periodo_segmento on historico_segmento  (cost=0.29..214.94 rows=9980 width=4) (actual time=0.032..0.439 rows=10000 loops=1)
              Index Cond: (periodo_id = 12)
              Heap Fetches: 0
              Buffers: shared hit=11
Planning Time: 0.047 ms
Execution Time: 0.913 ms
```

</details>

### `mobilidade`

A consulta filtra `metrica`. Se o planejador varrer, a conferência abaixo diz se foi escolha dele ou falta de índice.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo ORDER BY periodo.data_inicio DESC, peri…`
  - tempo no banco: **0.02 ms** · varredura: `periodo`
- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo WHERE periodo.data_inicio < %(data_inic…`
  - tempo no banco: **0.01 ms** · varredura: `periodo`
- `SELECT coalesce(atual.parceiro_id, passado.parceiro_id) AS parceiro_id, parceiro.nome, atual.posicao AS posic…`
  - tempo no banco: **23.89 ms** · varredura: `parceiro`

<details><summary>Plano completo</summary>

```
Limit  (cost=1.18..1.18 rows=1 width=12) (actual time=0.011..0.011 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.18..1.21 rows=12 width=12) (actual time=0.010..0.010 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.004..0.005 rows=12 loops=1)
              Buffers: shared hit=1
Planning Time: 0.051 ms
Execution Time: 0.018 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=1.20..1.21 rows=1 width=12) (actual time=0.008..0.009 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.20..1.23 rows=11 width=12) (actual time=0.008..0.008 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.15 rows=11 width=12) (actual time=0.003..0.004 rows=11 loops=1)
              Filter: (data_inicio < '2026-09-07'::date)
              Rows Removed by Filter: 1
              Buffers: shared hit=1
Planning:
  Buffers: shared hit=2
Planning Time: 0.091 ms
Execution Time: 0.015 ms
```

</details>

<details><summary>Plano completo</summary>

```
Sort  (cost=6284.75..6290.13 rows=2153 width=45) (actual time=23.034..23.038 rows=4 loops=1)
  Sort Key: (COALESCE((row_number() OVER (?)), passado.posicao))
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=2419
  ->  Hash Join  (cost=5590.47..6165.56 rows=2153 width=45) (actual time=19.650..23.032 rows=4 loops=1)
        Hash Cond: (COALESCE(metrica.parceiro_id, passado.parceiro_id) = parceiro.id)
        Buffers: shared hit=2419
        ->  Hash Full Join  (cost=5234.47..5803.90 rows=2153 width=24) (actual time=17.804..21.183 rows=4 loops=1)
              Hash Cond: (metrica.parceiro_id = passado.parceiro_id)
              Filter: ((((row_number() OVER (?)) <= 15) AND ((passado.posicao IS NULL) OR (passado.posicao > 15))) OR ((passado.posicao <= 15) AND (((row_number() OVER (?)) IS NULL) OR ((row_number() OVER (?)) > 15))))
              Rows Removed by Filter: 9996
              Buffers: shared hit=2288
              ->  WindowAgg  (cost=2432.41..2634.45 rows=10102 width=40) (actual time=7.078..8.963 rows=10000 loops=1)
                    Buffers: shared hit=1142
                    ->  Sort  (cost=2432.41..2457.67 rows=10102 width=28) (actual time=7.064..7.487 rows=10000 loops=1)
                          Sort Key: metrica.faturamento DESC, parceiro_1.nome
                          Sort Method: quicksort  Memory: 932kB
                          Buffers: shared hit=1142
                          ->  Hash Join  (cost=646.71..1760.51 rows=10102 width=28) (actual time=2.290..4.719 rows=10000 loops=1)
                                Hash Cond: (metrica.parceiro_id = parceiro_1.id)
                                Buffers: shared hit=1142
                                ->  Bitmap Heap Scan on metrica  (cost=290.71..1377.98 rows=10102 width=11) (actual time=0.556..1.682 rows=10000 loops=1)
                                      Recheck Cond: (periodo_id = 12)
                                      Heap Blocks: exact=961
                                      Buffers: shared hit=1011
                                      ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..288.18 rows=10102 width=0) (actual time=0.480..0.480 rows=10000 loops=1)
                                            Index Cond: (periodo_id = 12)
                                            Buffers: shared hit=50
                                ->  Hash  (cost=231.00..231.00 rows=10000 width=21) (actual time=1.664..1.664 rows=10000 loops=1)
                                      Buckets: 16384  Batches: 1  Memory Usage: 668kB
                                      Buffers: shared hit=131
                                      ->  Seq Scan on parceiro parceiro_1  (cost=0.00..231.00 rows=10000 width=21) (actual time=0.005..0.534 rows=10000 loops=1)
                                            Buffers: shared hit=131
              ->  Hash  (cost=2680.43..2680.43 rows=9730 width=12) (actual time=10.651..10.653 rows=9816 loops=1)
                    Buckets: 16384  Batches: 1  Memory Usage: 589kB
                    Buffers: shared hit=1146
                    ->  Subquery Scan on passado  (cost=2388.53..2680.43 rows=9730 width=12) (actual time=7.272..9.588 rows=9816 loops=1)
                          Buffers: shared hit=1146
                          ->  WindowAgg  (cost=2388.53..2583.13 rows=9730 width=40) (actual time=7.271..9.043 rows=9816 loops=1)
                                Buffers: shared hit=1146
                                ->  Sort  (cost=2388.53..2412.85 rows=9730 width=28) (actual time=7.261..7.639 rows=9816 loops=1)
                                      Sort Key: metrica_1.faturamento DESC, parceiro_2.nome
                                      Sort Method: quicksort  Memory: 922kB
                                      Buffers: shared hit=1146
                                      ->  Hash Join  (cost=635.83..1744.00 rows=9730 width=28) (actual time=2.261..4.913 rows=9816 loops=1)
                                            Hash Cond: (metrica_1.parceiro_id = parceiro_2.id)
                                            Buffers: shared hit=1146
                                            ->  Bitmap Heap Scan on metrica metrica_1  (cost=279.83..1362.45 rows=9730 width=11) (actual time=0.527..1.828 rows=9816 loops=1)
                                                  Recheck Cond: (periodo_id = 11)
                                                  Heap Blocks: exact=961
                                                  Buffers: shared hit=1015
                                                  ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..277.39 rows=9730 width=0) (actual time=0.437..0.438 rows=9816 loops=1)
                                                        Index Cond: (periodo_id = 11)
                                                        Buffers: shared hit=54
                                            ->  Hash  (cost=231.00..231.00 rows=10000 width=21) (actual time=1.665..1.665 rows=10000 loops=1)
                                                  Buckets: 16384  Batches: 1  Memory Usage: 668kB
                                                  Buffers: shared hit=131
                                                  ->  Seq Scan on parceiro parceiro_2  (cost=0.00..231.00 rows=10000 width=21) (actual time=0.003..0.518 rows=10000 loops=1)
                                                        Buffers: shared hit=131
        ->  Hash  (cost=231.00..231.00 rows=10000 width=21) (actual time=1.776..1.777 rows=10000 loops=1)
              Buckets: 16384  Batches: 1  Memory Usage: 668kB
              Buffers: shared hit=131
              ->  Seq Scan on parceiro  (cost=0.00..231.00 rows=10000 width=21) (actual time=0.003..0.573 rows=10000 loops=1)
                    Buffers: shared hit=131
Planning:
  Buffers: shared hit=24
Planning Time: 0.578 ms
Execution Time: 23.892 ms
```

</details>

### `busca`

A consulta filtra `parceiro`. Se o planejador varrer, a conferência abaixo diz se foi escolha dele ou falta de índice.

- `SELECT parceiro.id, parceiro.nome, parceiro.nome_normalizado, parceiro.categoria_id, parceiro.origem_categori…`
  - tempo no banco: **0.81 ms** · varredura: nenhuma

<details><summary>Plano completo</summary>

```
Sort  (cost=207.14..208.91 rows=707 width=317) (actual time=0.730..0.755 rows=625 loops=1)
  Sort Key: nome
  Sort Method: quicksort  Memory: 87kB
  Buffers: shared hit=137
  ->  Bitmap Heap Scan on parceiro  (cost=33.84..173.68 rows=707 width=317) (actual time=0.077..0.288 rows=625 loops=1)
        Recheck Cond: ((nome_normalizado)::text ~~ '%praca%'::text)
        Heap Blocks: exact=130
        Buffers: shared hit=137
        ->  Bitmap Index Scan on ix_parceiro_nome_normalizado_trgm  (cost=0.00..33.66 rows=707 width=0) (actual time=0.065..0.065 rows=625 loops=1)
              Index Cond: ((nome_normalizado)::text ~~ '%praca%'::text)
              Buffers: shared hit=7
Planning:
  Buffers: shared hit=1
Planning Time: 0.079 ms
Execution Time: 0.810 ms
```

</details>

### `lista-completa`

Sem filtro, a resposta é a tabela inteira; o custo está no volume, não no plano. É o caso que a paginação da H36 precisa resolver.

- `SELECT parceiro.id, parceiro.nome, parceiro.nome_normalizado, parceiro.categoria_id, parceiro.origem_categori…`
  - tempo no banco: **9.98 ms** · varredura: `parceiro`

<details><summary>Plano completo</summary>

```
Sort  (cost=895.39..920.39 rows=10000 width=317) (actual time=9.185..9.523 rows=10000 loops=1)
  Sort Key: nome
  Sort Method: quicksort  Memory: 1350kB
  Buffers: shared hit=131
  ->  Seq Scan on parceiro  (cost=0.00..231.00 rows=10000 width=317) (actual time=0.008..1.017 rows=10000 loops=1)
        Buffers: shared hit=131
Planning Time: 0.080 ms
Execution Time: 9.985 ms
```

</details>

## Índices em uso

- `ix_metrica_periodo_faturamento`
- `ix_parceiro_nome_normalizado_trgm`
- `ix_segmento_periodo_segmento`

