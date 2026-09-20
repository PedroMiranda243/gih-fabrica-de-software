# Medição do painel com 5.000 parceiros — H40

> Gerado por `scripts/medir_painel.py`. **Não edite à mão**: número escrito à mão não é evidência. Para atualizar, rode o comando abaixo de novo.

O RNF03 fixa **2 s** como teto de resposta e a H40 cobra isso com 5.000 parceiros. Este arquivo é o registro da medição — a Sprint 12 não precisa medir de novo às pressas para pôr o número na apresentação.

## Ambiente

| Item | Valor |
|---|---|
| Data | 20/09/2026 00:59 |
| Banco | `gih_medicao` — **separado do banco de trabalho** |
| PostgreSQL | PostgreSQL 16.14 on x86_64-pc-linux-musl |
| Python | 3.11.9 |
| Massa | 5.000 parceiros · 12 períodos · 56.874 métricas |
| Semente | 42 |

A medição chama a aplicação em processo, pelo `TestClient`: cobre roteamento, autorização, consulta e serialização — tudo que o navegador espera, menos a rede.

## Como reproduzir

```bash
api/.venv/Scripts/python scripts/medir_painel.py --parceiros 5000 --periodos 12 --semente 42
```

## Resultado

| Consulta | Chamadas | Mediana | p95 | Dispersão | Resposta | Dentro de 2 s |
|---|--:|--:|--:|--:|--:|:--:|
| `indicadores` | 300 | 11.3 ms | 12.9 ms | 14% | 344 B | sim |
| `ranking-25` | 232 | 25.4 ms | 28.8 ms | 13% | 6 kB | sim |
| `ranking-200` | 205 | 29.4 ms | 31.9 ms | 9% | 43 kB | sim |
| `serie` | 300 | 19.2 ms | 21.4 ms | 11% | 2 kB | sim |
| `busca` | 300 | 15.4 ms | 37.0 ms | 141% | 63 kB | sim |
| `lista-completa` | 46 | 140.6 ms | 182.6 ms | 30% | 1011 kB | sim |

A dispersão é o quanto o p95 se afasta da mediana. Vai junto de propósito: um número só de tempo esconde a variação, e foi exatamente isso que enganou a equipe na validação do toolchain (H47).

## O que cada consulta faz

- **`indicadores`** — `GET /api/painel/indicadores` · Faturamento, pedidos, ticket e ativos do período, com variação (H30).
- **`ranking-25`** — `GET /api/painel/ranking?tamanho=25` · A página que o painel pede ao abrir (H31).
- **`ranking-200`** — `GET /api/painel/ranking?tamanho=200` · A maior página que a API aceita — o pior caso do ranking.
- **`serie`** — `GET /api/painel/series` · Série histórica da rede (H32).
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
  - tempo no banco: **1.10 ms** · varredura: nenhuma
- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo WHERE periodo.data_inicio < %(data_inic…`
  - tempo no banco: **0.02 ms** · varredura: `periodo`

<details><summary>Plano completo</summary>

```
Limit  (cost=1.18..1.18 rows=1 width=12) (actual time=0.006..0.006 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.18..1.21 rows=12 width=12) (actual time=0.006..0.006 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.002..0.003 rows=12 loops=1)
              Buffers: shared hit=1
Planning Time: 0.042 ms
Execution Time: 0.011 ms
```

</details>

<details><summary>Plano completo</summary>

```
Aggregate  (cost=719.43..719.44 rows=1 width=48) (actual time=1.041..1.041 rows=1 loops=1)
  Buffers: shared hit=504
  ->  Bitmap Heap Scan on metrica  (cost=139.15..681.82 rows=5014 width=11) (actual time=0.232..0.647 rows=5000 loops=1)
        Recheck Cond: (periodo_id = 12)
        Heap Blocks: exact=480
        Buffers: shared hit=504
        ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..137.89 rows=5014 width=0) (actual time=0.168..0.168 rows=5000 loops=1)
              Index Cond: (periodo_id = 12)
              Buffers: shared hit=24
Planning Time: 0.045 ms
Execution Time: 1.097 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=1.20..1.21 rows=1 width=12) (actual time=0.007..0.008 rows=1 loops=1)
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
Planning Time: 0.066 ms
Execution Time: 0.017 ms
```

</details>

### `ranking-25`

A consulta filtra `metrica`. Se o planejador varrer, a conferência abaixo diz se foi escolha dele ou falta de índice.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo ORDER BY periodo.data_inicio DESC, peri…`
  - tempo no banco: **0.04 ms** · varredura: `periodo`
- `SELECT count(*) AS count_1 FROM (SELECT metrica.parceiro_id AS parceiro_id, metrica.faturamento AS faturament…`
  - tempo no banco: **2.65 ms** · varredura: `parceiro`
- `SELECT atual.parceiro_id, atual.faturamento, atual.pedidos, atual.posicao, parceiro.nome, categoria.nome AS n…`
  - tempo no banco: **7.89 ms** · varredura: `categoria`, `parceiro`
- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo WHERE periodo.data_inicio < %(data_inic…`
  - tempo no banco: **0.03 ms** · varredura: `periodo`
- `SELECT anterior.parceiro_id, anterior.posicao, anterior.faturamento FROM (SELECT metrica.parceiro_id AS parce…`
  - tempo no banco: **5.46 ms** · varredura: `parceiro`

<details><summary>Plano completo</summary>

```
Limit  (cost=1.18..1.18 rows=1 width=12) (actual time=0.015..0.016 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.18..1.21 rows=12 width=12) (actual time=0.015..0.015 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.004..0.004 rows=12 loops=1)
              Buffers: shared hit=1
Planning Time: 0.033 ms
Execution Time: 0.035 ms
```

</details>

<details><summary>Plano completo</summary>

```
Aggregate  (cost=936.17..936.18 rows=1 width=8) (actual time=2.520..2.521 rows=1 loops=1)
  Buffers: shared hit=570
  ->  Hash Join  (cost=317.65..873.50 rows=5014 width=40) (actual time=1.186..2.352 rows=5000 loops=1)
        Hash Cond: (metrica.parceiro_id = parceiro.id)
        Buffers: shared hit=570
        ->  Bitmap Heap Scan on metrica  (cost=139.15..681.82 rows=5014 width=11) (actual time=0.264..0.781 rows=5000 loops=1)
              Recheck Cond: (periodo_id = 12)
              Heap Blocks: exact=480
              Buffers: shared hit=504
              ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..137.89 rows=5014 width=0) (actual time=0.223..0.223 rows=5000 loops=1)
                    Index Cond: (periodo_id = 12)
                    Buffers: shared hit=24
        ->  Hash  (cost=116.00..116.00 rows=5000 width=21) (actual time=0.887..0.887 rows=5000 loops=1)
              Buckets: 8192  Batches: 1  Memory Usage: 333kB
              Buffers: shared hit=66
              ->  Seq Scan on parceiro  (cost=0.00..116.00 rows=5000 width=21) (actual time=0.003..0.308 rows=5000 loops=1)
                    Buffers: shared hit=66
Planning:
  Buffers: shared hit=12
Planning Time: 0.233 ms
Execution Time: 2.647 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=1685.20..1685.26 rows=25 width=50) (actual time=7.579..7.583 rows=25 loops=1)
  Buffers: shared hit=637
  ->  Sort  (cost=1685.20..1697.73 rows=5014 width=50) (actual time=7.579..7.581 rows=25 loops=1)
        Sort Key: (row_number() OVER (?))
        Sort Method: top-N heapsort  Memory: 28kB
        Buffers: shared hit=637
        ->  Hash Left Join  (cost=1361.38..1543.70 rows=5014 width=50) (actual time=4.789..6.971 rows=5000 loops=1)
              Hash Cond: (parceiro.categoria_id = categoria.id)
              Buffers: shared hit=637
              ->  Hash Join  (cost=1360.15..1523.74 rows=5014 width=44) (actual time=4.763..6.407 rows=5000 loops=1)
                    Hash Cond: (metrica.parceiro_id = parceiro.id)
                    Buffers: shared hit=636
                    ->  WindowAgg  (cost=1181.65..1281.93 rows=5014 width=40) (actual time=3.779..4.749 rows=5000 loops=1)
                          Buffers: shared hit=570
                          ->  Sort  (cost=1181.65..1194.19 rows=5014 width=32) (actual time=3.763..3.970 rows=5000 loops=1)
                                Sort Key: metrica.faturamento DESC, parceiro_1.nome
                                Sort Method: quicksort  Memory: 488kB
                                Buffers: shared hit=570
                                ->  Hash Join  (cost=317.65..873.50 rows=5014 width=32) (actual time=1.257..2.470 rows=5000 loops=1)
                                      Hash Cond: (metrica.parceiro_id = parceiro_1.id)
                                      Buffers: shared hit=570
                                      ->  Bitmap Heap Scan on metrica  (cost=139.15..681.82 rows=5014 width=15) (actual time=0.267..0.820 rows=5000 loops=1)
                                            Recheck Cond: (periodo_id = 12)
                                            Heap Blocks: exact=480
                                            Buffers: shared hit=504
                                            ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..137.89 rows=5014 width=0) (actual time=0.219..0.219 rows=5000 loops=1)
                                                  Index Cond: (periodo_id = 12)
                                                  Buffers: shared hit=24
                                      ->  Hash  (cost=116.00..116.00 rows=5000 width=21) (actual time=0.951..0.951 rows=5000 loops=1)
                                            Buckets: 8192  Batches: 1  Memory Usage: 333kB
                                            Buffers: shared hit=66
                                            ->  Seq Scan on parceiro parceiro_1  (cost=0.00..116.00 rows=5000 width=21) (actual time=0.004..0.315 rows=5000 loops=1)
                                                  Buffers: shared hit=66
                    ->  Hash  (cost=116.00..116.00 rows=5000 width=25) (actual time=0.949..0.949 rows=5000 loops=1)
                          Buckets: 8192  Batches: 1  Memory Usage: 352kB
                          Buffers: shared hit=66
                          ->  Seq Scan on parceiro  (cost=0.00..116.00 rows=5000 width=25) (actual time=0.003..0.323 rows=5000 loops=1)
                                Buffers: shared hit=66
              ->  Hash  (cost=1.10..1.10 rows=10 width=14) (actual time=0.015..0.015 rows=10 loops=1)
                    Buckets: 1024  Batches: 1  Memory Usage: 9kB
                    Buffers: shared hit=1
                    ->  Seq Scan on categoria  (cost=0.00..1.10 rows=10 width=14) (actual time=0.004..0.005 rows=10 loops=1)
                          Buffers: shared hit=1
Planning:
  Buffers: shared hit=22
Planning Time: 0.375 ms
Execution Time: 7.889 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=1.20..1.21 rows=1 width=12) (actual time=0.016..0.017 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.20..1.23 rows=11 width=12) (actual time=0.016..0.016 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.15 rows=11 width=12) (actual time=0.003..0.004 rows=11 loops=1)
              Filter: (data_inicio < '2026-09-07'::date)
              Rows Removed by Filter: 1
              Buffers: shared hit=1
Planning:
  Buffers: shared hit=2
Planning Time: 0.079 ms
Execution Time: 0.033 ms
```

</details>

<details><summary>Plano completo</summary>

```
Subquery Scan on anterior  (cost=1172.38..1344.30 rows=25 width=19) (actual time=4.148..5.280 rows=25 loops=1)
  Filter: (anterior.parceiro_id = ANY ('{2118,4133,4648,2515,1682,1577,2384,4544,3134,246,4155,3103,924,3997,3194,460,2744,2149,4254,4101,1563,1823,4982,4676,4468}'::integer[]))
  Rows Removed by Filter: 4870
  Buffers: shared hit=569
  ->  WindowAgg  (cost=1172.32..1270.56 rows=4912 width=40) (actual time=4.145..5.021 rows=4895 loops=1)
        Buffers: shared hit=569
        ->  Sort  (cost=1172.32..1184.60 rows=4912 width=28) (actual time=4.133..4.305 rows=4895 loops=1)
              Sort Key: metrica.faturamento DESC, parceiro.nome
              Sort Method: quicksort  Memory: 460kB
              Buffers: shared hit=569
              ->  Hash Join  (cost=316.86..871.16 rows=4912 width=28) (actual time=1.274..2.643 rows=4895 loops=1)
                    Hash Cond: (metrica.parceiro_id = parceiro.id)
                    Buffers: shared hit=569
                    ->  Bitmap Heap Scan on metrica  (cost=138.36..679.76 rows=4912 width=11) (actual time=0.353..0.989 rows=4895 loops=1)
                          Recheck Cond: (periodo_id = 11)
                          Heap Blocks: exact=480
                          Buffers: shared hit=503
                          ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..137.13 rows=4912 width=0) (actual time=0.304..0.304 rows=4895 loops=1)
                                Index Cond: (periodo_id = 11)
                                Buffers: shared hit=23
                    ->  Hash  (cost=116.00..116.00 rows=5000 width=21) (actual time=0.883..0.883 rows=5000 loops=1)
                          Buckets: 8192  Batches: 1  Memory Usage: 333kB
                          Buffers: shared hit=66
                          ->  Seq Scan on parceiro  (cost=0.00..116.00 rows=5000 width=21) (actual time=0.004..0.304 rows=5000 loops=1)
                                Buffers: shared hit=66
Planning:
  Buffers: shared hit=12
Planning Time: 0.235 ms
Execution Time: 5.462 ms
```

</details>

### `ranking-200`

A consulta filtra `metrica`. Se o planejador varrer, a conferência abaixo diz se foi escolha dele ou falta de índice.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo ORDER BY periodo.data_inicio DESC, peri…`
  - tempo no banco: **0.04 ms** · varredura: `periodo`
- `SELECT count(*) AS count_1 FROM (SELECT metrica.parceiro_id AS parceiro_id, metrica.faturamento AS faturament…`
  - tempo no banco: **2.65 ms** · varredura: `parceiro`
- `SELECT atual.parceiro_id, atual.faturamento, atual.pedidos, atual.posicao, parceiro.nome, categoria.nome AS n…`
  - tempo no banco: **8.24 ms** · varredura: `categoria`, `parceiro`
- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo WHERE periodo.data_inicio < %(data_inic…`
  - tempo no banco: **0.03 ms** · varredura: `periodo`
- `SELECT anterior.parceiro_id, anterior.posicao, anterior.faturamento FROM (SELECT metrica.parceiro_id AS parce…`
  - tempo no banco: **4.90 ms** · varredura: `parceiro`

<details><summary>Plano completo</summary>

```
Limit  (cost=1.18..1.18 rows=1 width=12) (actual time=0.017..0.018 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.18..1.21 rows=12 width=12) (actual time=0.017..0.017 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.004..0.005 rows=12 loops=1)
              Buffers: shared hit=1
Planning Time: 0.033 ms
Execution Time: 0.036 ms
```

</details>

<details><summary>Plano completo</summary>

```
Aggregate  (cost=936.17..936.18 rows=1 width=8) (actual time=2.487..2.487 rows=1 loops=1)
  Buffers: shared hit=570
  ->  Hash Join  (cost=317.65..873.50 rows=5014 width=40) (actual time=1.136..2.322 rows=5000 loops=1)
        Hash Cond: (metrica.parceiro_id = parceiro.id)
        Buffers: shared hit=570
        ->  Bitmap Heap Scan on metrica  (cost=139.15..681.82 rows=5014 width=11) (actual time=0.256..0.771 rows=5000 loops=1)
              Recheck Cond: (periodo_id = 12)
              Heap Blocks: exact=480
              Buffers: shared hit=504
              ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..137.89 rows=5014 width=0) (actual time=0.211..0.212 rows=5000 loops=1)
                    Index Cond: (periodo_id = 12)
                    Buffers: shared hit=24
        ->  Hash  (cost=116.00..116.00 rows=5000 width=21) (actual time=0.847..0.848 rows=5000 loops=1)
              Buckets: 8192  Batches: 1  Memory Usage: 333kB
              Buffers: shared hit=66
              ->  Seq Scan on parceiro  (cost=0.00..116.00 rows=5000 width=21) (actual time=0.005..0.291 rows=5000 loops=1)
                    Buffers: shared hit=66
Planning:
  Buffers: shared hit=12
Planning Time: 0.243 ms
Execution Time: 2.651 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=1760.41..1760.91 rows=200 width=50) (actual time=7.877..7.894 rows=200 loops=1)
  Buffers: shared hit=637
  ->  Sort  (cost=1760.41..1772.94 rows=5014 width=50) (actual time=7.877..7.883 rows=200 loops=1)
        Sort Key: (row_number() OVER (?))
        Sort Method: top-N heapsort  Memory: 51kB
        Buffers: shared hit=637
        ->  Hash Left Join  (cost=1361.38..1543.70 rows=5014 width=50) (actual time=5.018..7.223 rows=5000 loops=1)
              Hash Cond: (parceiro.categoria_id = categoria.id)
              Buffers: shared hit=637
              ->  Hash Join  (cost=1360.15..1523.74 rows=5014 width=44) (actual time=4.996..6.659 rows=5000 loops=1)
                    Hash Cond: (metrica.parceiro_id = parceiro.id)
                    Buffers: shared hit=636
                    ->  WindowAgg  (cost=1181.65..1281.93 rows=5014 width=40) (actual time=3.839..4.825 rows=5000 loops=1)
                          Buffers: shared hit=570
                          ->  Sort  (cost=1181.65..1194.19 rows=5014 width=32) (actual time=3.831..4.044 rows=5000 loops=1)
                                Sort Key: metrica.faturamento DESC, parceiro_1.nome
                                Sort Method: quicksort  Memory: 488kB
                                Buffers: shared hit=570
                                ->  Hash Join  (cost=317.65..873.50 rows=5014 width=32) (actual time=1.389..2.540 rows=5000 loops=1)
                                      Hash Cond: (metrica.parceiro_id = parceiro_1.id)
                                      Buffers: shared hit=570
                                      ->  Bitmap Heap Scan on metrica  (cost=139.15..681.82 rows=5014 width=15) (actual time=0.302..0.779 rows=5000 loops=1)
                                            Recheck Cond: (periodo_id = 12)
                                            Heap Blocks: exact=480
                                            Buffers: shared hit=504
                                            ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..137.89 rows=5014 width=0) (actual time=0.235..0.235 rows=5000 loops=1)
                                                  Index Cond: (periodo_id = 12)
                                                  Buffers: shared hit=24
                                      ->  Hash  (cost=116.00..116.00 rows=5000 width=21) (actual time=1.050..1.050 rows=5000 loops=1)
                                            Buckets: 8192  Batches: 1  Memory Usage: 333kB
                                            Buffers: shared hit=66
                                            ->  Seq Scan on parceiro parceiro_1  (cost=0.00..116.00 rows=5000 width=21) (actual time=0.003..0.345 rows=5000 loops=1)
                                                  Buffers: shared hit=66
                    ->  Hash  (cost=116.00..116.00 rows=5000 width=25) (actual time=1.117..1.117 rows=5000 loops=1)
                          Buckets: 8192  Batches: 1  Memory Usage: 352kB
                          Buffers: shared hit=66
                          ->  Seq Scan on parceiro  (cost=0.00..116.00 rows=5000 width=25) (actual time=0.004..0.370 rows=5000 loops=1)
                                Buffers: shared hit=66
              ->  Hash  (cost=1.10..1.10 rows=10 width=14) (actual time=0.014..0.014 rows=10 loops=1)
                    Buckets: 1024  Batches: 1  Memory Usage: 9kB
                    Buffers: shared hit=1
                    ->  Seq Scan on categoria  (cost=0.00..1.10 rows=10 width=14) (actual time=0.003..0.004 rows=10 loops=1)
                          Buffers: shared hit=1
Planning:
  Buffers: shared hit=22
Planning Time: 0.409 ms
Execution Time: 8.240 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=1.20..1.21 rows=1 width=12) (actual time=0.016..0.016 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.20..1.23 rows=11 width=12) (actual time=0.015..0.016 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.15 rows=11 width=12) (actual time=0.003..0.004 rows=11 loops=1)
              Filter: (data_inicio < '2026-09-07'::date)
              Rows Removed by Filter: 1
              Buffers: shared hit=1
Planning:
  Buffers: shared hit=2
Planning Time: 0.066 ms
Execution Time: 0.032 ms
```

</details>

<details><summary>Plano completo</summary>

```
Subquery Scan on anterior  (cost=1172.82..1344.74 rows=200 width=19) (actual time=3.583..4.675 rows=196 loops=1)
  Filter: (anterior.parceiro_id = ANY ('{2118,4133,4648,2515,1682,1577,2384,4544,3134,246,4155,3103,924,3997,3194,460,2744,2149,4254,4101,1563,1823,4982,4676,4468,1917,2272,4729,983,1242,1660,1307,2260,2864,3721,3217,2999,3270,2050,3662,152,4716,3453,1754,1936,1793,2044,4654,2470,4885,3621,2336,3133,4340,1395,3736,613,823,2311,600,2314,181,860,1265,2134,3415,381,1019,2666,3389,959,510,2539,1067,885,2074,1586,3049,4890,484,214,1896,74,4268,2125,1663,2085,3090,2296,3857,733,1825,4156,1348,906,3579,3758,1393,4171,3095,4179,630,1010,3461,3737,1596,2828,3629,3211,4695,2053,1382,1782,2520,1458,2512,524,1238,2232,549,4059,1503,3273,2108,3623,3517,4044,3097,1304,1763,572,3384,2914,2980,2759,1443,2073,1757,4670,339,2618,4920,1311,3343,2821,639,4793,2404,4980,2968,2127,263,4691,3619,3860,3667,4420,757,4580,3204,4115,4618,2880,1972,654,3754,1084,927,1417,1440,4574,3657,3221,2936,2267,2834,7,528,589,3813,1683,3094,4009,2231,3433,1377,2363,2831,3016,1148,1959,775,3576,4886,1533,1281,2036,3403,800,4304}'::integer[]))
  Rows Removed by Filter: 4699
  Buffers: shared hit=569
  ->  WindowAgg  (cost=1172.32..1270.56 rows=4912 width=40) (actual time=3.577..4.401 rows=4895 loops=1)
        Buffers: shared hit=569
        ->  Sort  (cost=1172.32..1184.60 rows=4912 width=28) (actual time=3.569..3.730 rows=4895 loops=1)
              Sort Key: metrica.faturamento DESC, parceiro.nome
              Sort Method: quicksort  Memory: 460kB
              Buffers: shared hit=569
              ->  Hash Join  (cost=316.86..871.16 rows=4912 width=28) (actual time=1.242..2.349 rows=4895 loops=1)
                    Hash Cond: (metrica.parceiro_id = parceiro.id)
                    Buffers: shared hit=569
                    ->  Bitmap Heap Scan on metrica  (cost=138.36..679.76 rows=4912 width=11) (actual time=0.274..0.746 rows=4895 loops=1)
                          Recheck Cond: (periodo_id = 11)
                          Heap Blocks: exact=480
                          Buffers: shared hit=503
                          ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..137.13 rows=4912 width=0) (actual time=0.238..0.238 rows=4895 loops=1)
                                Index Cond: (periodo_id = 11)
                                Buffers: shared hit=23
                    ->  Hash  (cost=116.00..116.00 rows=5000 width=21) (actual time=0.926..0.927 rows=5000 loops=1)
                          Buckets: 8192  Batches: 1  Memory Usage: 333kB
                          Buffers: shared hit=66
                          ->  Seq Scan on parceiro  (cost=0.00..116.00 rows=5000 width=21) (actual time=0.004..0.304 rows=5000 loops=1)
                                Buffers: shared hit=66
Planning:
  Buffers: shared hit=12
Planning Time: 0.384 ms
Execution Time: 4.904 ms
```

</details>

### `serie`

A série agrega **todos** os períodos: a consulta lê a tabela inteira por definição, e varrer é o plano certo.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim, sum(metrica.faturamento) AS sum_1, sum(metrica.pedi…`
  - tempo no banco: **18.30 ms** · varredura: `metrica`, `periodo`

<details><summary>Plano completo</summary>

```
Sort  (cost=1678.96..1678.99 rows=12 width=52) (actual time=18.266..18.267 rows=12 loops=1)
  Sort Key: periodo.data_inicio, periodo.id
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=481
  ->  HashAggregate  (cost=1678.59..1678.74 rows=12 width=52) (actual time=18.259..18.262 rows=12 loops=1)
        Group Key: periodo.id
        Batches: 1  Memory Usage: 24kB
        Buffers: shared hit=481
        ->  Hash Right Join  (cost=1.27..1252.04 rows=56874 width=23) (actual time=0.024..10.571 rows=56874 loops=1)
              Hash Cond: (metrica.periodo_id = periodo.id)
              Buffers: shared hit=481
              ->  Seq Scan on metrica  (cost=0.00..1048.74 rows=56874 width=15) (actual time=0.002..2.348 rows=56874 loops=1)
                    Buffers: shared hit=480
              ->  Hash  (cost=1.12..1.12 rows=12 width=12) (actual time=0.018..0.018 rows=12 loops=1)
                    Buckets: 1024  Batches: 1  Memory Usage: 9kB
                    Buffers: shared hit=1
                    ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.003..0.004 rows=12 loops=1)
                          Buffers: shared hit=1
Planning:
  Buffers: shared hit=4
Planning Time: 0.202 ms
Execution Time: 18.297 ms
```

</details>

### `busca`

A consulta filtra `parceiro`. Se o planejador varrer, a conferência abaixo diz se foi escolha dele ou falta de índice.

- `SELECT parceiro.id, parceiro.nome, parceiro.nome_normalizado, parceiro.categoria_id, parceiro.origem_categori…`
  - tempo no banco: **0.47 ms** · varredura: nenhuma

<details><summary>Plano completo</summary>

```
Sort  (cost=113.99..114.75 rows=303 width=317) (actual time=0.405..0.418 rows=307 loops=1)
  Sort Key: nome
  Sort Method: quicksort  Memory: 55kB
  Buffers: shared hit=72
  ->  Bitmap Heap Scan on parceiro  (cost=31.72..101.51 rows=303 width=317) (actual time=0.085..0.198 rows=307 loops=1)
        Recheck Cond: ((nome_normalizado)::text ~~ '%praca%'::text)
        Heap Blocks: exact=65
        Buffers: shared hit=72
        ->  Bitmap Index Scan on ix_parceiro_nome_normalizado_trgm  (cost=0.00..31.64 rows=303 width=0) (actual time=0.073..0.073 rows=307 loops=1)
              Index Cond: ((nome_normalizado)::text ~~ '%praca%'::text)
              Buffers: shared hit=7
Planning:
  Buffers: shared hit=1
Planning Time: 0.085 ms
Execution Time: 0.471 ms
```

</details>

### `lista-completa`

Sem filtro, a resposta é a tabela inteira; o custo está no volume, não no plano. É o caso que a paginação da H36 precisa resolver.

- `SELECT parceiro.id, parceiro.nome, parceiro.nome_normalizado, parceiro.categoria_id, parceiro.origem_categori…`
  - tempo no banco: **4.73 ms** · varredura: `parceiro`

<details><summary>Plano completo</summary>

```
Sort  (cost=423.19..435.69 rows=5000 width=317) (actual time=4.366..4.523 rows=5000 loops=1)
  Sort Key: nome
  Sort Method: quicksort  Memory: 672kB
  Buffers: shared hit=66
  ->  Seq Scan on parceiro  (cost=0.00..116.00 rows=5000 width=317) (actual time=0.009..0.481 rows=5000 loops=1)
        Buffers: shared hit=66
Planning Time: 0.071 ms
Execution Time: 4.732 ms
```

</details>

## Índices em uso

- `ix_metrica_periodo_faturamento`
- `ix_parceiro_nome_normalizado_trgm`

