# Medição do painel com 5.000 parceiros — H40

> Gerado por `scripts/medir_painel.py`. **Não edite à mão**: número escrito à mão não é evidência. Para atualizar, rode o comando abaixo de novo.

O RNF03 fixa **2 s** como teto de resposta e a H40 cobra isso com 5.000 parceiros. Este arquivo é o registro da medição — a Sprint 12 não precisa medir de novo às pressas para pôr o número na apresentação.

## Ambiente

| Item | Valor |
|---|---|
| Data | 20/09/2026 02:07 |
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
| `indicadores` | 300 | 15.2 ms | 16.8 ms | 10% | 380 B | sim |
| `ranking-25` | 192 | 29.3 ms | 31.7 ms | 8% | 6 kB | sim |
| `ranking-200` | 181 | 34.0 ms | 36.7 ms | 8% | 47 kB | sim |
| `serie` | 300 | 21.0 ms | 22.6 ms | 8% | 2 kB | sim |
| `segmentos` | 300 | 8.7 ms | 9.5 ms | 9% | 278 B | sim |
| `mobilidade` | 241 | 20.8 ms | 23.3 ms | 12% | 351 B | sim |
| `busca` | 300 | 15.7 ms | 38.7 ms | 147% | 63 kB | sim |
| `lista-completa` | 44 | 140.0 ms | 178.9 ms | 28% | 1011 kB | sim |

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
  - tempo no banco: **0.04 ms** · varredura: `periodo`
- `SELECT coalesce(sum(metrica.faturamento), %(coalesce_2)s::INTEGER) AS coalesce_1, coalesce(sum(metrica.pedido…`
  - tempo no banco: **1.62 ms** · varredura: nenhuma
- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo WHERE periodo.data_inicio < %(data_inic…`
  - tempo no banco: **0.02 ms** · varredura: `periodo`
- `SELECT count(*) AS count_1, count(*) FILTER (WHERE historico_segmento.segmento = %(segmento_1)s) AS anon_1 FR…`
  - tempo no banco: **0.57 ms** · varredura: nenhuma

<details><summary>Plano completo</summary>

```
Limit  (cost=1.18..1.18 rows=1 width=12) (actual time=0.009..0.010 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.18..1.21 rows=12 width=12) (actual time=0.009..0.009 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.004..0.005 rows=12 loops=1)
              Buffers: shared hit=1
Planning Time: 0.035 ms
Execution Time: 0.039 ms
```

</details>

<details><summary>Plano completo</summary>

```
Aggregate  (cost=718.02..718.03 rows=1 width=48) (actual time=1.542..1.543 rows=1 loops=1)
  Buffers: shared hit=504
  ->  Bitmap Heap Scan on metrica  (cost=138.75..680.79 rows=4963 width=11) (actual time=0.322..1.022 rows=5000 loops=1)
        Recheck Cond: (periodo_id = 12)
        Heap Blocks: exact=480
        Buffers: shared hit=504
        ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..137.51 rows=4963 width=0) (actual time=0.250..0.250 rows=5000 loops=1)
              Index Cond: (periodo_id = 12)
              Buffers: shared hit=24
Planning Time: 0.049 ms
Execution Time: 1.617 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=1.20..1.21 rows=1 width=12) (actual time=0.007..0.007 rows=1 loops=1)
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
Planning Time: 0.062 ms
Execution Time: 0.016 ms
```

</details>

<details><summary>Plano completo</summary>

```
Aggregate  (cost=519.71..519.72 rows=1 width=16) (actual time=0.534..0.535 rows=1 loops=1)
  Buffers: shared hit=39
  ->  Bitmap Heap Scan on historico_segmento  (cost=58.39..482.84 rows=4916 width=4) (actual time=0.072..0.306 rows=5000 loops=1)
        Recheck Cond: (periodo_id = 12)
        Heap Blocks: exact=33
        Buffers: shared hit=39
        ->  Bitmap Index Scan on ix_segmento_periodo_segmento  (cost=0.00..57.16 rows=4916 width=0) (actual time=0.061..0.061 rows=5000 loops=1)
              Index Cond: (periodo_id = 12)
              Buffers: shared hit=6
Planning Time: 0.030 ms
Execution Time: 0.569 ms
```

</details>

### `ranking-25`

A consulta filtra `metrica`. Se o planejador varrer, a conferência abaixo diz se foi escolha dele ou falta de índice.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo ORDER BY periodo.data_inicio DESC, peri…`
  - tempo no banco: **0.03 ms** · varredura: `periodo`
- `SELECT count(*) AS count_1 FROM (SELECT metrica.parceiro_id AS parceiro_id, metrica.faturamento AS faturament…`
  - tempo no banco: **2.71 ms** · varredura: `parceiro`
- `SELECT atual.parceiro_id, atual.faturamento, atual.pedidos, atual.posicao, parceiro.nome, categoria.nome AS n…`
  - tempo no banco: **11.09 ms** · varredura: `categoria`, `parceiro`
- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo WHERE periodo.data_inicio < %(data_inic…`
  - tempo no banco: **0.04 ms** · varredura: `periodo`
- `SELECT anterior.parceiro_id, anterior.posicao, anterior.faturamento FROM (SELECT metrica.parceiro_id AS parce…`
  - tempo no banco: **5.84 ms** · varredura: `parceiro`

<details><summary>Plano completo</summary>

```
Limit  (cost=1.18..1.18 rows=1 width=12) (actual time=0.015..0.016 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.18..1.21 rows=12 width=12) (actual time=0.015..0.015 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.003..0.004 rows=12 loops=1)
              Buffers: shared hit=1
Planning Time: 0.034 ms
Execution Time: 0.032 ms
```

</details>

<details><summary>Plano completo</summary>

```
Aggregate  (cost=934.37..934.38 rows=1 width=8) (actual time=2.582..2.583 rows=1 loops=1)
  Buffers: shared hit=570
  ->  Hash Join  (cost=317.25..872.33 rows=4963 width=40) (actual time=1.193..2.417 rows=5000 loops=1)
        Hash Cond: (metrica.parceiro_id = parceiro.id)
        Buffers: shared hit=570
        ->  Bitmap Heap Scan on metrica  (cost=138.75..680.79 rows=4963 width=11) (actual time=0.258..0.811 rows=5000 loops=1)
              Recheck Cond: (periodo_id = 12)
              Heap Blocks: exact=480
              Buffers: shared hit=504
              ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..137.51 rows=4963 width=0) (actual time=0.217..0.217 rows=5000 loops=1)
                    Index Cond: (periodo_id = 12)
                    Buffers: shared hit=24
        ->  Hash  (cost=116.00..116.00 rows=5000 width=21) (actual time=0.888..0.888 rows=5000 loops=1)
              Buckets: 8192  Batches: 1  Memory Usage: 333kB
              Buffers: shared hit=66
              ->  Seq Scan on parceiro  (cost=0.00..116.00 rows=5000 width=21) (actual time=0.004..0.317 rows=5000 loops=1)
                    Buffers: shared hit=66
Planning:
  Buffers: shared hit=12
Planning Time: 0.329 ms
Execution Time: 2.715 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=2234.56..2234.63 rows=25 width=54) (actual time=10.647..10.651 rows=25 loops=1)
  Buffers: shared hit=676
  ->  Sort  (cost=2234.56..2246.97 rows=4963 width=54) (actual time=10.646..10.649 rows=25 loops=1)
        Sort Key: (row_number() OVER (?))
        Sort Method: top-N heapsort  Memory: 28kB
        Buffers: shared hit=676
        ->  Hash Left Join  (cost=1901.00..2094.51 rows=4963 width=54) (actual time=6.667..10.025 rows=5000 loops=1)
              Hash Cond: (metrica.parceiro_id = historico_segmento.parceiro_id)
              Buffers: shared hit=676
              ->  Hash Left Join  (cost=1356.71..1537.18 rows=4963 width=50) (actual time=5.523..8.202 rows=5000 loops=1)
                    Hash Cond: (parceiro.categoria_id = categoria.id)
                    Buffers: shared hit=637
                    ->  Hash Join  (cost=1355.48..1517.41 rows=4963 width=44) (actual time=5.497..7.646 rows=5000 loops=1)
                          Hash Cond: (metrica.parceiro_id = parceiro.id)
                          Buffers: shared hit=636
                          ->  WindowAgg  (cost=1176.98..1276.24 rows=4963 width=40) (actual time=4.264..5.635 rows=5000 loops=1)
                                Buffers: shared hit=570
                                ->  Sort  (cost=1176.98..1189.39 rows=4963 width=32) (actual time=4.255..4.522 rows=5000 loops=1)
                                      Sort Key: metrica.faturamento DESC, parceiro_1.nome
                                      Sort Method: quicksort  Memory: 488kB
                                      Buffers: shared hit=570
                                      ->  Hash Join  (cost=317.25..872.33 rows=4963 width=32) (actual time=1.466..2.767 rows=5000 loops=1)
                                            Hash Cond: (metrica.parceiro_id = parceiro_1.id)
                                            Buffers: shared hit=570
                                            ->  Bitmap Heap Scan on metrica  (cost=138.75..680.79 rows=4963 width=15) (actual time=0.303..0.904 rows=5000 loops=1)
                                                  Recheck Cond: (periodo_id = 12)
                                                  Heap Blocks: exact=480
                                                  Buffers: shared hit=504
                                                  ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..137.51 rows=4963 width=0) (actual time=0.265..0.265 rows=5000 loops=1)
                                                        Index Cond: (periodo_id = 12)
                                                        Buffers: shared hit=24
                                            ->  Hash  (cost=116.00..116.00 rows=5000 width=21) (actual time=1.124..1.124 rows=5000 loops=1)
                                                  Buckets: 8192  Batches: 1  Memory Usage: 333kB
                                                  Buffers: shared hit=66
                                                  ->  Seq Scan on parceiro parceiro_1  (cost=0.00..116.00 rows=5000 width=21) (actual time=0.003..0.276 rows=5000 loops=1)
                                                        Buffers: shared hit=66
                          ->  Hash  (cost=116.00..116.00 rows=5000 width=25) (actual time=1.195..1.195 rows=5000 loops=1)
                                Buckets: 8192  Batches: 1  Memory Usage: 352kB
                                Buffers: shared hit=66
                                ->  Seq Scan on parceiro  (cost=0.00..116.00 rows=5000 width=25) (actual time=0.003..0.390 rows=5000 loops=1)
                                      Buffers: shared hit=66
                    ->  Hash  (cost=1.10..1.10 rows=10 width=14) (actual time=0.017..0.017 rows=10 loops=1)
                          Buckets: 1024  Batches: 1  Memory Usage: 9kB
                          Buffers: shared hit=1
                          ->  Seq Scan on categoria  (cost=0.00..1.10 rows=10 width=14) (actual time=0.004..0.004 rows=10 loops=1)
                                Buffers: shared hit=1
              ->  Hash  (cost=482.84..482.84 rows=4916 width=8) (actual time=1.106..1.107 rows=5000 loops=1)
                    Buckets: 8192  Batches: 1  Memory Usage: 260kB
                    Buffers: shared hit=39
                    ->  Bitmap Heap Scan on historico_segmento  (cost=58.39..482.84 rows=4916 width=8) (actual time=0.274..0.593 rows=5000 loops=1)
                          Recheck Cond: (periodo_id = 12)
                          Heap Blocks: exact=33
                          Buffers: shared hit=39
                          ->  Bitmap Index Scan on ix_segmento_periodo_segmento  (cost=0.00..57.16 rows=4916 width=0) (actual time=0.268..0.268 rows=5000 loops=1)
                                Index Cond: (periodo_id = 12)
                                Buffers: shared hit=6
Planning:
  Buffers: shared hit=28
Planning Time: 0.583 ms
Execution Time: 11.090 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=1.20..1.21 rows=1 width=12) (actual time=0.018..0.018 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.20..1.23 rows=11 width=12) (actual time=0.017..0.017 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.15 rows=11 width=12) (actual time=0.004..0.005 rows=11 loops=1)
              Filter: (data_inicio < '2026-09-07'::date)
              Rows Removed by Filter: 1
              Buffers: shared hit=1
Planning:
  Buffers: shared hit=2
Planning Time: 0.095 ms
Execution Time: 0.035 ms
```

</details>

<details><summary>Plano completo</summary>

```
Subquery Scan on anterior  (cost=1167.72..1337.86 rows=25 width=19) (actual time=4.337..5.656 rows=25 loops=1)
  Filter: (anterior.parceiro_id = ANY ('{2118,4133,4648,2515,1682,1577,2384,4544,3134,246,4155,3103,924,3997,3194,460,2744,2149,4254,4101,1563,1823,4982,4676,4468}'::integer[]))
  Rows Removed by Filter: 4870
  Buffers: shared hit=569
  ->  WindowAgg  (cost=1167.66..1264.88 rows=4861 width=40) (actual time=4.333..5.190 rows=4895 loops=1)
        Buffers: shared hit=569
        ->  Sort  (cost=1167.66..1179.81 rows=4861 width=28) (actual time=4.320..4.482 rows=4895 loops=1)
              Sort Key: metrica.faturamento DESC, parceiro.nome
              Sort Method: quicksort  Memory: 460kB
              Buffers: shared hit=569
              ->  Hash Join  (cost=316.46..870.00 rows=4861 width=28) (actual time=1.426..2.814 rows=4895 loops=1)
                    Hash Cond: (metrica.parceiro_id = parceiro.id)
                    Buffers: shared hit=569
                    ->  Bitmap Heap Scan on metrica  (cost=137.96..678.73 rows=4861 width=11) (actual time=0.337..1.000 rows=4895 loops=1)
                          Recheck Cond: (periodo_id = 11)
                          Heap Blocks: exact=480
                          Buffers: shared hit=503
                          ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..136.75 rows=4861 width=0) (actual time=0.288..0.288 rows=4895 loops=1)
                                Index Cond: (periodo_id = 11)
                                Buffers: shared hit=23
                    ->  Hash  (cost=116.00..116.00 rows=5000 width=21) (actual time=1.048..1.048 rows=5000 loops=1)
                          Buckets: 8192  Batches: 1  Memory Usage: 333kB
                          Buffers: shared hit=66
                          ->  Seq Scan on parceiro  (cost=0.00..116.00 rows=5000 width=21) (actual time=0.005..0.359 rows=5000 loops=1)
                                Buffers: shared hit=66
Planning:
  Buffers: shared hit=12
Planning Time: 0.262 ms
Execution Time: 5.843 ms
```

</details>

### `ranking-200`

A consulta filtra `metrica`. Se o planejador varrer, a conferência abaixo diz se foi escolha dele ou falta de índice.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo ORDER BY periodo.data_inicio DESC, peri…`
  - tempo no banco: **0.04 ms** · varredura: `periodo`
- `SELECT count(*) AS count_1 FROM (SELECT metrica.parceiro_id AS parceiro_id, metrica.faturamento AS faturament…`
  - tempo no banco: **3.29 ms** · varredura: `parceiro`
- `SELECT atual.parceiro_id, atual.faturamento, atual.pedidos, atual.posicao, parceiro.nome, categoria.nome AS n…`
  - tempo no banco: **9.56 ms** · varredura: `categoria`, `parceiro`
- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo WHERE periodo.data_inicio < %(data_inic…`
  - tempo no banco: **0.03 ms** · varredura: `periodo`
- `SELECT anterior.parceiro_id, anterior.posicao, anterior.faturamento FROM (SELECT metrica.parceiro_id AS parce…`
  - tempo no banco: **5.79 ms** · varredura: `parceiro`

<details><summary>Plano completo</summary>

```
Limit  (cost=1.18..1.18 rows=1 width=12) (actual time=0.019..0.019 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.18..1.21 rows=12 width=12) (actual time=0.018..0.019 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.004..0.005 rows=12 loops=1)
              Buffers: shared hit=1
Planning Time: 0.042 ms
Execution Time: 0.040 ms
```

</details>

<details><summary>Plano completo</summary>

```
Aggregate  (cost=934.37..934.38 rows=1 width=8) (actual time=3.141..3.142 rows=1 loops=1)
  Buffers: shared hit=570
  ->  Hash Join  (cost=317.25..872.33 rows=4963 width=40) (actual time=1.461..2.935 rows=5000 loops=1)
        Hash Cond: (metrica.parceiro_id = parceiro.id)
        Buffers: shared hit=570
        ->  Bitmap Heap Scan on metrica  (cost=138.75..680.79 rows=4963 width=11) (actual time=0.342..1.005 rows=5000 loops=1)
              Recheck Cond: (periodo_id = 12)
              Heap Blocks: exact=480
              Buffers: shared hit=504
              ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..137.51 rows=4963 width=0) (actual time=0.285..0.285 rows=5000 loops=1)
                    Index Cond: (periodo_id = 12)
                    Buffers: shared hit=24
        ->  Hash  (cost=116.00..116.00 rows=5000 width=21) (actual time=1.071..1.071 rows=5000 loops=1)
              Buckets: 8192  Batches: 1  Memory Usage: 333kB
              Buffers: shared hit=66
              ->  Seq Scan on parceiro  (cost=0.00..116.00 rows=5000 width=21) (actual time=0.004..0.382 rows=5000 loops=1)
                    Buffers: shared hit=66
Planning:
  Buffers: shared hit=12
Planning Time: 0.259 ms
Execution Time: 3.294 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=2309.01..2309.51 rows=200 width=54) (actual time=9.122..9.139 rows=200 loops=1)
  Buffers: shared hit=676
  ->  Sort  (cost=2309.01..2321.42 rows=4963 width=54) (actual time=9.122..9.129 rows=200 loops=1)
        Sort Key: (row_number() OVER (?))
        Sort Method: top-N heapsort  Memory: 51kB
        Buffers: shared hit=676
        ->  Hash Left Join  (cost=1901.00..2094.51 rows=4963 width=54) (actual time=5.654..8.473 rows=5000 loops=1)
              Hash Cond: (metrica.parceiro_id = historico_segmento.parceiro_id)
              Buffers: shared hit=676
              ->  Hash Left Join  (cost=1356.71..1537.18 rows=4963 width=50) (actual time=4.732..6.958 rows=5000 loops=1)
                    Hash Cond: (parceiro.categoria_id = categoria.id)
                    Buffers: shared hit=637
                    ->  Hash Join  (cost=1355.48..1517.41 rows=4963 width=44) (actual time=4.712..6.415 rows=5000 loops=1)
                          Hash Cond: (metrica.parceiro_id = parceiro.id)
                          Buffers: shared hit=636
                          ->  WindowAgg  (cost=1176.98..1276.24 rows=4963 width=40) (actual time=3.732..4.701 rows=5000 loops=1)
                                Buffers: shared hit=570
                                ->  Sort  (cost=1176.98..1189.39 rows=4963 width=32) (actual time=3.724..3.908 rows=5000 loops=1)
                                      Sort Key: metrica.faturamento DESC, parceiro_1.nome
                                      Sort Method: quicksort  Memory: 488kB
                                      Buffers: shared hit=570
                                      ->  Hash Join  (cost=317.25..872.33 rows=4963 width=32) (actual time=1.135..2.465 rows=5000 loops=1)
                                            Hash Cond: (metrica.parceiro_id = parceiro_1.id)
                                            Buffers: shared hit=570
                                            ->  Bitmap Heap Scan on metrica  (cost=138.75..680.79 rows=4963 width=15) (actual time=0.269..0.926 rows=5000 loops=1)
                                                  Recheck Cond: (periodo_id = 12)
                                                  Heap Blocks: exact=480
                                                  Buffers: shared hit=504
                                                  ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..137.51 rows=4963 width=0) (actual time=0.233..0.233 rows=5000 loops=1)
                                                        Index Cond: (periodo_id = 12)
                                                        Buffers: shared hit=24
                                            ->  Hash  (cost=116.00..116.00 rows=5000 width=21) (actual time=0.827..0.827 rows=5000 loops=1)
                                                  Buckets: 8192  Batches: 1  Memory Usage: 333kB
                                                  Buffers: shared hit=66
                                                  ->  Seq Scan on parceiro parceiro_1  (cost=0.00..116.00 rows=5000 width=21) (actual time=0.003..0.270 rows=5000 loops=1)
                                                        Buffers: shared hit=66
                          ->  Hash  (cost=116.00..116.00 rows=5000 width=25) (actual time=0.933..0.933 rows=5000 loops=1)
                                Buckets: 8192  Batches: 1  Memory Usage: 352kB
                                Buffers: shared hit=66
                                ->  Seq Scan on parceiro  (cost=0.00..116.00 rows=5000 width=25) (actual time=0.005..0.339 rows=5000 loops=1)
                                      Buffers: shared hit=66
                    ->  Hash  (cost=1.10..1.10 rows=10 width=14) (actual time=0.012..0.012 rows=10 loops=1)
                          Buckets: 1024  Batches: 1  Memory Usage: 9kB
                          Buffers: shared hit=1
                          ->  Seq Scan on categoria  (cost=0.00..1.10 rows=10 width=14) (actual time=0.003..0.004 rows=10 loops=1)
                                Buffers: shared hit=1
              ->  Hash  (cost=482.84..482.84 rows=4916 width=8) (actual time=0.885..0.885 rows=5000 loops=1)
                    Buckets: 8192  Batches: 1  Memory Usage: 260kB
                    Buffers: shared hit=39
                    ->  Bitmap Heap Scan on historico_segmento  (cost=58.39..482.84 rows=4916 width=8) (actual time=0.078..0.392 rows=5000 loops=1)
                          Recheck Cond: (periodo_id = 12)
                          Heap Blocks: exact=33
                          Buffers: shared hit=39
                          ->  Bitmap Index Scan on ix_segmento_periodo_segmento  (cost=0.00..57.16 rows=4916 width=0) (actual time=0.072..0.072 rows=5000 loops=1)
                                Index Cond: (periodo_id = 12)
                                Buffers: shared hit=6
Planning:
  Buffers: shared hit=28
Planning Time: 0.512 ms
Execution Time: 9.561 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=1.20..1.21 rows=1 width=12) (actual time=0.014..0.014 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.20..1.23 rows=11 width=12) (actual time=0.014..0.014 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.15 rows=11 width=12) (actual time=0.003..0.004 rows=11 loops=1)
              Filter: (data_inicio < '2026-09-07'::date)
              Rows Removed by Filter: 1
              Buffers: shared hit=1
Planning:
  Buffers: shared hit=2
Planning Time: 0.098 ms
Execution Time: 0.028 ms
```

</details>

<details><summary>Plano completo</summary>

```
Subquery Scan on anterior  (cost=1168.16..1338.30 rows=197 width=19) (actual time=4.228..5.402 rows=196 loops=1)
  Filter: (anterior.parceiro_id = ANY ('{2118,4133,4648,2515,1682,1577,2384,4544,3134,246,4155,3103,924,3997,3194,460,2744,2149,4254,4101,1563,1823,4982,4676,4468,1917,2272,4729,983,1242,1660,1307,2260,2864,3721,3217,2999,3270,2050,3662,152,4716,3453,1754,1936,1793,2044,4654,2470,4885,3621,2336,3133,4340,1395,3736,613,823,2311,600,2314,181,860,1265,2134,3415,381,1019,2666,3389,959,510,2539,1067,885,2074,1586,3049,4890,484,214,1896,74,4268,2125,1663,2085,3090,2296,3857,733,1825,4156,1348,906,3579,3758,1393,4171,3095,4179,630,1010,3461,3737,1596,2828,3629,3211,4695,2053,1382,1782,2520,1458,2512,524,1238,2232,549,4059,1503,3273,2108,3623,3517,4044,3097,1304,1763,572,3384,2914,2980,2759,1443,2073,1757,4670,339,2618,4920,1311,3343,2821,639,4793,2404,4980,2968,2127,263,4691,3619,3860,3667,4420,757,4580,3204,4115,4618,2880,1972,654,3754,1084,927,1417,1440,4574,3657,3221,2936,2267,2834,7,528,589,3813,1683,3094,4009,2231,3433,1377,2363,2831,3016,1148,1959,775,3576,4886,1533,1281,2036,3403,800,4304}'::integer[]))
  Rows Removed by Filter: 4699
  Buffers: shared hit=569
  ->  WindowAgg  (cost=1167.66..1264.88 rows=4861 width=40) (actual time=4.221..5.062 rows=4895 loops=1)
        Buffers: shared hit=569
        ->  Sort  (cost=1167.66..1179.81 rows=4861 width=28) (actual time=4.215..4.375 rows=4895 loops=1)
              Sort Key: metrica.faturamento DESC, parceiro.nome
              Sort Method: quicksort  Memory: 460kB
              Buffers: shared hit=569
              ->  Hash Join  (cost=316.46..870.00 rows=4861 width=28) (actual time=1.503..2.810 rows=4895 loops=1)
                    Hash Cond: (metrica.parceiro_id = parceiro.id)
                    Buffers: shared hit=569
                    ->  Bitmap Heap Scan on metrica  (cost=137.96..678.73 rows=4861 width=11) (actual time=0.489..1.106 rows=4895 loops=1)
                          Recheck Cond: (periodo_id = 11)
                          Heap Blocks: exact=480
                          Buffers: shared hit=503
                          ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..136.75 rows=4861 width=0) (actual time=0.257..0.257 rows=4895 loops=1)
                                Index Cond: (periodo_id = 11)
                                Buffers: shared hit=23
                    ->  Hash  (cost=116.00..116.00 rows=5000 width=21) (actual time=0.980..0.980 rows=5000 loops=1)
                          Buckets: 8192  Batches: 1  Memory Usage: 333kB
                          Buffers: shared hit=66
                          ->  Seq Scan on parceiro  (cost=0.00..116.00 rows=5000 width=21) (actual time=0.003..0.312 rows=5000 loops=1)
                                Buffers: shared hit=66
Planning:
  Buffers: shared hit=12
Planning Time: 0.527 ms
Execution Time: 5.791 ms
```

</details>

### `serie`

A série agrega **todos** os períodos: a consulta lê a tabela inteira por definição, e varrer é o plano certo.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim, sum(metrica.faturamento) AS sum_1, sum(metrica.pedi…`
  - tempo no banco: **17.57 ms** · varredura: `metrica`, `periodo`

<details><summary>Plano completo</summary>

```
Sort  (cost=1678.96..1678.99 rows=12 width=52) (actual time=17.515..17.516 rows=12 loops=1)
  Sort Key: periodo.data_inicio, periodo.id
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=481
  ->  HashAggregate  (cost=1678.59..1678.74 rows=12 width=52) (actual time=17.506..17.510 rows=12 loops=1)
        Group Key: periodo.id
        Batches: 1  Memory Usage: 24kB
        Buffers: shared hit=481
        ->  Hash Right Join  (cost=1.27..1252.04 rows=56874 width=23) (actual time=0.028..10.259 rows=56874 loops=1)
              Hash Cond: (metrica.periodo_id = periodo.id)
              Buffers: shared hit=481
              ->  Seq Scan on metrica  (cost=0.00..1048.74 rows=56874 width=15) (actual time=0.003..2.637 rows=56874 loops=1)
                    Buffers: shared hit=480
              ->  Hash  (cost=1.12..1.12 rows=12 width=12) (actual time=0.015..0.015 rows=12 loops=1)
                    Buckets: 1024  Batches: 1  Memory Usage: 9kB
                    Buffers: shared hit=1
                    ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.003..0.004 rows=12 loops=1)
                          Buffers: shared hit=1
Planning:
  Buffers: shared hit=4
Planning Time: 0.178 ms
Execution Time: 17.567 ms
```

</details>

### `segmentos`

A consulta filtra `historico_segmento`. Se o planejador varrer, a conferência abaixo diz se foi escolha dele ou falta de índice.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo ORDER BY periodo.data_inicio DESC, peri…`
  - tempo no banco: **0.02 ms** · varredura: `periodo`
- `SELECT historico_segmento.segmento, count(*) AS count_1 FROM historico_segmento WHERE historico_segmento.peri…`
  - tempo no banco: **0.95 ms** · varredura: nenhuma

<details><summary>Plano completo</summary>

```
Limit  (cost=1.18..1.18 rows=1 width=12) (actual time=0.011..0.011 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.18..1.21 rows=12 width=12) (actual time=0.010..0.010 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.005..0.005 rows=12 loops=1)
              Buffers: shared hit=1
Planning Time: 0.042 ms
Execution Time: 0.018 ms
```

</details>

<details><summary>Plano completo</summary>

```
Sort  (cost=507.53..507.54 rows=5 width=12) (actual time=0.893..0.893 rows=5 loops=1)
  Sort Key: (count(*)) DESC, segmento
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=39
  ->  HashAggregate  (cost=507.42..507.47 rows=5 width=12) (actual time=0.888..0.890 rows=5 loops=1)
        Group Key: segmento
        Batches: 1  Memory Usage: 24kB
        Buffers: shared hit=39
        ->  Bitmap Heap Scan on historico_segmento  (cost=58.39..482.84 rows=4916 width=4) (actual time=0.075..0.308 rows=5000 loops=1)
              Recheck Cond: (periodo_id = 12)
              Heap Blocks: exact=33
              Buffers: shared hit=39
              ->  Bitmap Index Scan on ix_segmento_periodo_segmento  (cost=0.00..57.16 rows=4916 width=0) (actual time=0.070..0.070 rows=5000 loops=1)
                    Index Cond: (periodo_id = 12)
                    Buffers: shared hit=6
Planning Time: 0.083 ms
Execution Time: 0.955 ms
```

</details>

### `mobilidade`

A consulta filtra `metrica`. Se o planejador varrer, a conferência abaixo diz se foi escolha dele ou falta de índice.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo ORDER BY periodo.data_inicio DESC, peri…`
  - tempo no banco: **0.02 ms** · varredura: `periodo`
- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo WHERE periodo.data_inicio < %(data_inic…`
  - tempo no banco: **0.01 ms** · varredura: `periodo`
- `SELECT coalesce(atual.parceiro_id, passado.parceiro_id) AS parceiro_id, parceiro.nome, atual.posicao AS posic…`
  - tempo no banco: **11.86 ms** · varredura: `parceiro`

<details><summary>Plano completo</summary>

```
Limit  (cost=1.18..1.18 rows=1 width=12) (actual time=0.010..0.011 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.18..1.21 rows=12 width=12) (actual time=0.010..0.010 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.005..0.005 rows=12 loops=1)
              Buffers: shared hit=1
Planning Time: 0.234 ms
Execution Time: 0.017 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=1.20..1.21 rows=1 width=12) (actual time=0.006..0.007 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.20..1.23 rows=11 width=12) (actual time=0.006..0.006 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.15 rows=11 width=12) (actual time=0.002..0.003 rows=11 loops=1)
              Filter: (data_inicio < '2026-09-07'::date)
              Rows Removed by Filter: 1
              Buffers: shared hit=1
Planning:
  Buffers: shared hit=2
Planning Time: 0.077 ms
Execution Time: 0.012 ms
```

</details>

<details><summary>Plano completo</summary>

```
Sort  (cost=3056.83..3059.46 rows=1051 width=45) (actual time=11.228..11.230 rows=2 loops=1)
  Sort Key: (COALESCE((row_number() OVER (?)), passado.posicao))
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=1205
  ->  Hash Join  (cost=2729.74..3004.08 rows=1051 width=45) (actual time=9.748..11.222 rows=2 loops=1)
        Hash Cond: (COALESCE(metrica.parceiro_id, passado.parceiro_id) = parceiro.id)
        Buffers: shared hit=1205
        ->  Hash Full Join  (cost=2551.24..2822.82 rows=1051 width=24) (actual time=8.827..10.301 rows=2 loops=1)
              Hash Cond: (metrica.parceiro_id = passado.parceiro_id)
              Filter: ((((row_number() OVER (?)) <= 15) AND ((passado.posicao IS NULL) OR (passado.posicao > 15))) OR ((passado.posicao <= 15) AND (((row_number() OVER (?)) IS NULL) OR ((row_number() OVER (?)) > 15))))
              Rows Removed by Filter: 4998
              Buffers: shared hit=1139
              ->  WindowAgg  (cost=1176.98..1276.24 rows=4963 width=40) (actual time=3.505..4.400 rows=5000 loops=1)
                    Buffers: shared hit=570
                    ->  Sort  (cost=1176.98..1189.39 rows=4963 width=28) (actual time=3.497..3.673 rows=5000 loops=1)
                          Sort Key: metrica.faturamento DESC, parceiro_1.nome
                          Sort Method: quicksort  Memory: 465kB
                          Buffers: shared hit=570
                          ->  Hash Join  (cost=317.25..872.33 rows=4963 width=28) (actual time=1.117..2.268 rows=5000 loops=1)
                                Hash Cond: (metrica.parceiro_id = parceiro_1.id)
                                Buffers: shared hit=570
                                ->  Bitmap Heap Scan on metrica  (cost=138.75..680.79 rows=4963 width=11) (actual time=0.229..0.736 rows=5000 loops=1)
                                      Recheck Cond: (periodo_id = 12)
                                      Heap Blocks: exact=480
                                      Buffers: shared hit=504
                                      ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..137.51 rows=4963 width=0) (actual time=0.195..0.195 rows=5000 loops=1)
                                            Index Cond: (periodo_id = 12)
                                            Buffers: shared hit=24
                                ->  Hash  (cost=116.00..116.00 rows=5000 width=21) (actual time=0.850..0.850 rows=5000 loops=1)
                                      Buckets: 8192  Batches: 1  Memory Usage: 333kB
                                      Buffers: shared hit=66
                                      ->  Seq Scan on parceiro parceiro_1  (cost=0.00..116.00 rows=5000 width=21) (actual time=0.004..0.273 rows=5000 loops=1)
                                            Buffers: shared hit=66
              ->  Hash  (cost=1313.49..1313.49 rows=4861 width=12) (actual time=5.277..5.278 rows=4895 loops=1)
                    Buckets: 8192  Batches: 1  Memory Usage: 294kB
                    Buffers: shared hit=569
                    ->  Subquery Scan on passado  (cost=1167.66..1313.49 rows=4861 width=12) (actual time=3.604..4.758 rows=4895 loops=1)
                          Buffers: shared hit=569
                          ->  WindowAgg  (cost=1167.66..1264.88 rows=4861 width=40) (actual time=3.604..4.483 rows=4895 loops=1)
                                Buffers: shared hit=569
                                ->  Sort  (cost=1167.66..1179.81 rows=4861 width=28) (actual time=3.598..3.769 rows=4895 loops=1)
                                      Sort Key: metrica_1.faturamento DESC, parceiro_2.nome
                                      Sort Method: quicksort  Memory: 460kB
                                      Buffers: shared hit=569
                                      ->  Hash Join  (cost=316.46..870.00 rows=4861 width=28) (actual time=1.100..2.363 rows=4895 loops=1)
                                            Hash Cond: (metrica_1.parceiro_id = parceiro_2.id)
                                            Buffers: shared hit=569
                                            ->  Bitmap Heap Scan on metrica metrica_1  (cost=137.96..678.73 rows=4861 width=11) (actual time=0.233..0.856 rows=4895 loops=1)
                                                  Recheck Cond: (periodo_id = 11)
                                                  Heap Blocks: exact=480
                                                  Buffers: shared hit=503
                                                  ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..136.75 rows=4861 width=0) (actual time=0.197..0.197 rows=4895 loops=1)
                                                        Index Cond: (periodo_id = 11)
                                                        Buffers: shared hit=23
                                            ->  Hash  (cost=116.00..116.00 rows=5000 width=21) (actual time=0.829..0.829 rows=5000 loops=1)
                                                  Buckets: 8192  Batches: 1  Memory Usage: 333kB
                                                  Buffers: shared hit=66
                                                  ->  Seq Scan on parceiro parceiro_2  (cost=0.00..116.00 rows=5000 width=21) (actual time=0.004..0.269 rows=5000 loops=1)
                                                        Buffers: shared hit=66
        ->  Hash  (cost=116.00..116.00 rows=5000 width=21) (actual time=0.885..0.885 rows=5000 loops=1)
              Buckets: 8192  Batches: 1  Memory Usage: 333kB
              Buffers: shared hit=66
              ->  Seq Scan on parceiro  (cost=0.00..116.00 rows=5000 width=21) (actual time=0.003..0.314 rows=5000 loops=1)
                    Buffers: shared hit=66
Planning:
  Buffers: shared hit=24
Planning Time: 0.627 ms
Execution Time: 11.859 ms
```

</details>

### `busca`

A consulta filtra `parceiro`. Se o planejador varrer, a conferência abaixo diz se foi escolha dele ou falta de índice.

- `SELECT parceiro.id, parceiro.nome, parceiro.nome_normalizado, parceiro.categoria_id, parceiro.origem_categori…`
  - tempo no banco: **0.69 ms** · varredura: `parceiro`
  - a varredura em `parceiro` é **escolha do planejador**: com `enable_seqscan = off` o mesmo filtro usa `ix_parceiro_nome` e leva 1.47 ms. O índice cobre a consulta.

<details><summary>Plano completo</summary>

```
Sort  (cost=140.99..141.75 rows=303 width=317) (actual time=0.672..0.680 rows=307 loops=1)
  Sort Key: nome
  Sort Method: quicksort  Memory: 55kB
  Buffers: shared hit=66
  ->  Seq Scan on parceiro  (cost=0.00..128.50 rows=303 width=317) (actual time=0.008..0.514 rows=307 loops=1)
        Filter: ((nome_normalizado)::text ~~ '%praca%'::text)
        Rows Removed by Filter: 4693
        Buffers: shared hit=66
Planning:
  Buffers: shared hit=1
Planning Time: 0.078 ms
Execution Time: 0.694 ms
```

</details>

### `lista-completa`

Sem filtro, a resposta é a tabela inteira; o custo está no volume, não no plano. É o caso que a paginação da H36 precisa resolver.

- `SELECT parceiro.id, parceiro.nome, parceiro.nome_normalizado, parceiro.categoria_id, parceiro.origem_categori…`
  - tempo no banco: **4.83 ms** · varredura: `parceiro`

<details><summary>Plano completo</summary>

```
Sort  (cost=423.19..435.69 rows=5000 width=317) (actual time=4.453..4.610 rows=5000 loops=1)
  Sort Key: nome
  Sort Method: quicksort  Memory: 672kB
  Buffers: shared hit=66
  ->  Seq Scan on parceiro  (cost=0.00..116.00 rows=5000 width=317) (actual time=0.007..0.469 rows=5000 loops=1)
        Buffers: shared hit=66
Planning Time: 0.059 ms
Execution Time: 4.826 ms
```

</details>

## Índices em uso

- `ix_metrica_periodo_faturamento`
- `ix_segmento_periodo_segmento`

