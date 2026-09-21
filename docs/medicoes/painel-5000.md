# Medição do painel com 5.000 parceiros — H40

> Gerado por `scripts/medir_painel.py`. **Não edite à mão**: número escrito à mão não é evidência. Para atualizar, rode o comando abaixo de novo.

O RNF03 fixa **2 s** como teto de resposta e a H40 cobra isso com 5.000 parceiros. Este arquivo é o registro da medição — a Sprint 12 não precisa medir de novo às pressas para pôr o número na apresentação.

## Ambiente

| Item | Valor |
|---|---|
| Data | 21/09/2026 17:45 |
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
| `indicadores` | 300 | 14.1 ms | 17.0 ms | 21% | 381 B | sim |
| `ranking-25` | 210 | 28.2 ms | 32.5 ms | 15% | 6 kB | sim |
| `ranking-200` | 191 | 32.3 ms | 36.4 ms | 13% | 47 kB | sim |
| `serie` | 273 | 18.8 ms | 21.4 ms | 13% | 2 kB | sim |
| `segmentos` | 300 | 8.0 ms | 9.1 ms | 13% | 279 B | sim |
| `mobilidade` | 269 | 20.8 ms | 22.9 ms | 10% | 515 B | sim |
| `busca` | 300 | 14.7 ms | 16.4 ms | 12% | 17 kB | sim |
| `lista-completa` | 300 | 14.9 ms | 16.7 ms | 12% | 16 kB | sim |

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
  - tempo no banco: **0.02 ms** · varredura: `periodo`
- `SELECT coalesce(sum(metrica.faturamento), %(coalesce_2)s::INTEGER) AS coalesce_1, coalesce(sum(metrica.pedido…`
  - tempo no banco: **1.28 ms** · varredura: nenhuma
- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo WHERE periodo.data_inicio < %(data_inic…`
  - tempo no banco: **0.02 ms** · varredura: `periodo`
- `SELECT count(*) AS count_1, count(*) FILTER (WHERE historico_segmento.segmento = %(segmento_1)s) AS anon_1 FR…`
  - tempo no banco: **0.59 ms** · varredura: nenhuma

<details><summary>Plano completo</summary>

```
Limit  (cost=1.18..1.18 rows=1 width=12) (actual time=0.010..0.010 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.18..1.21 rows=12 width=12) (actual time=0.009..0.009 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.004..0.005 rows=12 loops=1)
              Buffers: shared hit=1
Planning Time: 0.050 ms
Execution Time: 0.018 ms
```

</details>

<details><summary>Plano completo</summary>

```
Aggregate  (cost=718.35..718.36 rows=1 width=48) (actual time=1.222..1.223 rows=1 loops=1)
  Buffers: shared hit=505
  ->  Bitmap Heap Scan on metrica  (cost=138.85..681.03 rows=4975 width=11) (actual time=0.226..0.797 rows=5000 loops=1)
        Recheck Cond: (periodo_id = 12)
        Heap Blocks: exact=480
        Buffers: shared hit=505
        ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..137.60 rows=4975 width=0) (actual time=0.189..0.190 rows=5000 loops=1)
              Index Cond: (periodo_id = 12)
              Buffers: shared hit=25
Planning Time: 0.046 ms
Execution Time: 1.276 ms
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
              Filter: (data_inicio < '2026-09-14'::date)
              Rows Removed by Filter: 1
              Buffers: shared hit=1
Planning:
  Buffers: shared hit=2
Planning Time: 0.077 ms
Execution Time: 0.017 ms
```

</details>

<details><summary>Plano completo</summary>

```
Aggregate  (cost=522.82..522.83 rows=1 width=16) (actual time=0.550..0.550 rows=1 loops=1)
  Buffers: shared hit=39
  ->  Bitmap Heap Scan on historico_segmento  (cost=59.26..485.11 rows=5028 width=4) (actual time=0.074..0.314 rows=5000 loops=1)
        Recheck Cond: (periodo_id = 12)
        Heap Blocks: exact=33
        Buffers: shared hit=39
        ->  Bitmap Index Scan on ix_segmento_periodo_segmento  (cost=0.00..58.00 rows=5028 width=0) (actual time=0.063..0.063 rows=5000 loops=1)
              Index Cond: (periodo_id = 12)
              Buffers: shared hit=6
Planning Time: 0.035 ms
Execution Time: 0.589 ms
```

</details>

### `ranking-25`

A consulta filtra `metrica`. Se o planejador varrer, a conferência abaixo diz se foi escolha dele ou falta de índice.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo ORDER BY periodo.data_inicio DESC, peri…`
  - tempo no banco: **0.04 ms** · varredura: `periodo`
- `SELECT count(*) AS count_1 FROM (SELECT metrica.parceiro_id AS parceiro_id, metrica.faturamento AS faturament…`
  - tempo no banco: **2.75 ms** · varredura: `parceiro`
- `SELECT atual.parceiro_id, atual.faturamento, atual.pedidos, atual.posicao, parceiro.nome, categoria.nome AS n…`
  - tempo no banco: **9.96 ms** · varredura: `categoria`, `parceiro`
- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo WHERE periodo.data_inicio < %(data_inic…`
  - tempo no banco: **0.03 ms** · varredura: `periodo`
- `SELECT anterior.parceiro_id, anterior.posicao, anterior.faturamento FROM (SELECT metrica.parceiro_id AS parce…`
  - tempo no banco: **4.75 ms** · varredura: `parceiro`

<details><summary>Plano completo</summary>

```
Limit  (cost=1.18..1.18 rows=1 width=12) (actual time=0.017..0.017 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.18..1.21 rows=12 width=12) (actual time=0.016..0.017 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.004..0.005 rows=12 loops=1)
              Buffers: shared hit=1
Planning Time: 0.046 ms
Execution Time: 0.035 ms
```

</details>

<details><summary>Plano completo</summary>

```
Aggregate  (cost=934.79..934.80 rows=1 width=8) (actual time=2.589..2.590 rows=1 loops=1)
  Buffers: shared hit=571
  ->  Hash Join  (cost=317.35..872.60 rows=4975 width=40) (actual time=1.143..2.425 rows=5000 loops=1)
        Hash Cond: (metrica.parceiro_id = parceiro.id)
        Buffers: shared hit=571
        ->  Bitmap Heap Scan on metrica  (cost=138.85..681.03 rows=4975 width=11) (actual time=0.266..0.864 rows=5000 loops=1)
              Recheck Cond: (periodo_id = 12)
              Heap Blocks: exact=480
              Buffers: shared hit=505
              ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..137.60 rows=4975 width=0) (actual time=0.225..0.225 rows=5000 loops=1)
                    Index Cond: (periodo_id = 12)
                    Buffers: shared hit=25
        ->  Hash  (cost=116.00..116.00 rows=5000 width=21) (actual time=0.838..0.838 rows=5000 loops=1)
              Buckets: 8192  Batches: 1  Memory Usage: 333kB
              Buffers: shared hit=66
              ->  Seq Scan on parceiro  (cost=0.00..116.00 rows=5000 width=21) (actual time=0.003..0.281 rows=5000 loops=1)
                    Buffers: shared hit=66
Planning:
  Buffers: shared hit=12
Planning Time: 0.236 ms
Execution Time: 2.746 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=2242.85..2242.92 rows=25 width=54) (actual time=9.544..9.548 rows=25 loops=1)
  Buffers: shared hit=677
  ->  Sort  (cost=2242.85..2255.53 rows=5071 width=54) (actual time=9.543..9.545 rows=25 loops=1)
        Sort Key: (row_number() OVER (?))
        Sort Method: top-N heapsort  Memory: 28kB
        Buffers: shared hit=677
        ->  Hash Left Join  (cost=1905.76..2099.75 rows=5071 width=54) (actual time=5.935..8.938 rows=5000 loops=1)
              Hash Cond: (metrica.parceiro_id = historico_segmento.parceiro_id)
              Buffers: shared hit=677
              ->  Hash Left Join  (cost=1357.81..1538.73 rows=4975 width=50) (actual time=5.036..7.418 rows=5000 loops=1)
                    Hash Cond: (parceiro.categoria_id = categoria.id)
                    Buffers: shared hit=638
                    ->  Hash Join  (cost=1356.58..1518.90 rows=4975 width=44) (actual time=5.014..6.848 rows=5000 loops=1)
                          Hash Cond: (metrica.parceiro_id = parceiro.id)
                          Buffers: shared hit=637
                          ->  WindowAgg  (cost=1178.08..1277.58 rows=4975 width=40) (actual time=3.847..4.869 rows=5000 loops=1)
                                Buffers: shared hit=571
                                ->  Sort  (cost=1178.08..1190.52 rows=4975 width=32) (actual time=3.840..4.053 rows=5000 loops=1)
                                      Sort Key: metrica.faturamento DESC, parceiro_1.nome
                                      Sort Method: quicksort  Memory: 488kB
                                      Buffers: shared hit=571
                                      ->  Hash Join  (cost=317.35..872.60 rows=4975 width=32) (actual time=1.257..2.590 rows=5000 loops=1)
                                            Hash Cond: (metrica.parceiro_id = parceiro_1.id)
                                            Buffers: shared hit=571
                                            ->  Bitmap Heap Scan on metrica  (cost=138.85..681.03 rows=4975 width=15) (actual time=0.259..0.913 rows=5000 loops=1)
                                                  Recheck Cond: (periodo_id = 12)
                                                  Heap Blocks: exact=480
                                                  Buffers: shared hit=505
                                                  ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..137.60 rows=4975 width=0) (actual time=0.222..0.222 rows=5000 loops=1)
                                                        Index Cond: (periodo_id = 12)
                                                        Buffers: shared hit=25
                                            ->  Hash  (cost=116.00..116.00 rows=5000 width=21) (actual time=0.956..0.956 rows=5000 loops=1)
                                                  Buckets: 8192  Batches: 1  Memory Usage: 333kB
                                                  Buffers: shared hit=66
                                                  ->  Seq Scan on parceiro parceiro_1  (cost=0.00..116.00 rows=5000 width=21) (actual time=0.003..0.305 rows=5000 loops=1)
                                                        Buffers: shared hit=66
                          ->  Hash  (cost=116.00..116.00 rows=5000 width=25) (actual time=1.122..1.122 rows=5000 loops=1)
                                Buckets: 8192  Batches: 1  Memory Usage: 352kB
                                Buffers: shared hit=66
                                ->  Seq Scan on parceiro  (cost=0.00..116.00 rows=5000 width=25) (actual time=0.006..0.362 rows=5000 loops=1)
                                      Buffers: shared hit=66
                    ->  Hash  (cost=1.10..1.10 rows=10 width=14) (actual time=0.014..0.014 rows=10 loops=1)
                          Buckets: 1024  Batches: 1  Memory Usage: 9kB
                          Buffers: shared hit=1
                          ->  Seq Scan on categoria  (cost=0.00..1.10 rows=10 width=14) (actual time=0.003..0.004 rows=10 loops=1)
                                Buffers: shared hit=1
              ->  Hash  (cost=485.11..485.11 rows=5028 width=8) (actual time=0.863..0.863 rows=5000 loops=1)
                    Buckets: 8192  Batches: 1  Memory Usage: 260kB
                    Buffers: shared hit=39
                    ->  Bitmap Heap Scan on historico_segmento  (cost=59.26..485.11 rows=5028 width=8) (actual time=0.075..0.394 rows=5000 loops=1)
                          Recheck Cond: (periodo_id = 12)
                          Heap Blocks: exact=33
                          Buffers: shared hit=39
                          ->  Bitmap Index Scan on ix_segmento_periodo_segmento  (cost=0.00..58.00 rows=5028 width=0) (actual time=0.069..0.069 rows=5000 loops=1)
                                Index Cond: (periodo_id = 12)
                                Buffers: shared hit=6
Planning:
  Buffers: shared hit=28
Planning Time: 0.683 ms
Execution Time: 9.960 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=1.20..1.21 rows=1 width=12) (actual time=0.015..0.015 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.20..1.23 rows=11 width=12) (actual time=0.014..0.015 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.15 rows=11 width=12) (actual time=0.003..0.004 rows=11 loops=1)
              Filter: (data_inicio < '2026-09-14'::date)
              Rows Removed by Filter: 1
              Buffers: shared hit=1
Planning:
  Buffers: shared hit=2
Planning Time: 0.077 ms
Execution Time: 0.029 ms
```

</details>

<details><summary>Plano completo</summary>

```
Subquery Scan on anterior  (cost=1168.36..1338.74 rows=25 width=19) (actual time=3.535..4.574 rows=25 loops=1)
  Filter: (anterior.parceiro_id = ANY ('{2118,4133,4648,1577,2515,1682,2384,4544,3134,246,4155,3997,924,3103,4101,3194,460,2744,2149,4982,1823,4254,1563,1917,4468}'::integer[]))
  Rows Removed by Filter: 4870
  Buffers: shared hit=569
  ->  WindowAgg  (cost=1168.30..1265.66 rows=4868 width=40) (actual time=3.532..4.337 rows=4895 loops=1)
        Buffers: shared hit=569
        ->  Sort  (cost=1168.30..1180.47 rows=4868 width=28) (actual time=3.520..3.684 rows=4895 loops=1)
              Sort Key: metrica.faturamento DESC, parceiro.nome
              Sort Method: quicksort  Memory: 460kB
              Buffers: shared hit=569
              ->  Hash Join  (cost=316.52..870.16 rows=4868 width=28) (actual time=1.130..2.356 rows=4895 loops=1)
                    Hash Cond: (metrica.parceiro_id = parceiro.id)
                    Buffers: shared hit=569
                    ->  Bitmap Heap Scan on metrica  (cost=138.02..678.87 rows=4868 width=11) (actual time=0.259..0.856 rows=4895 loops=1)
                          Recheck Cond: (periodo_id = 11)
                          Heap Blocks: exact=480
                          Buffers: shared hit=503
                          ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..136.80 rows=4868 width=0) (actual time=0.222..0.222 rows=4895 loops=1)
                                Index Cond: (periodo_id = 11)
                                Buffers: shared hit=23
                    ->  Hash  (cost=116.00..116.00 rows=5000 width=21) (actual time=0.834..0.834 rows=5000 loops=1)
                          Buckets: 8192  Batches: 1  Memory Usage: 333kB
                          Buffers: shared hit=66
                          ->  Seq Scan on parceiro  (cost=0.00..116.00 rows=5000 width=21) (actual time=0.003..0.276 rows=5000 loops=1)
                                Buffers: shared hit=66
Planning:
  Buffers: shared hit=12
Planning Time: 0.204 ms
Execution Time: 4.754 ms
```

</details>

### `ranking-200`

A consulta filtra `metrica`. Se o planejador varrer, a conferência abaixo diz se foi escolha dele ou falta de índice.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo ORDER BY periodo.data_inicio DESC, peri…`
  - tempo no banco: **0.04 ms** · varredura: `periodo`
- `SELECT count(*) AS count_1 FROM (SELECT metrica.parceiro_id AS parceiro_id, metrica.faturamento AS faturament…`
  - tempo no banco: **3.39 ms** · varredura: `parceiro`
- `SELECT atual.parceiro_id, atual.faturamento, atual.pedidos, atual.posicao, parceiro.nome, categoria.nome AS n…`
  - tempo no banco: **10.02 ms** · varredura: `categoria`, `parceiro`
- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo WHERE periodo.data_inicio < %(data_inic…`
  - tempo no banco: **0.08 ms** · varredura: `periodo`
- `SELECT anterior.parceiro_id, anterior.posicao, anterior.faturamento FROM (SELECT metrica.parceiro_id AS parce…`
  - tempo no banco: **6.02 ms** · varredura: `parceiro`

<details><summary>Plano completo</summary>

```
Limit  (cost=1.18..1.18 rows=1 width=12) (actual time=0.017..0.018 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.18..1.21 rows=12 width=12) (actual time=0.017..0.017 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.005..0.005 rows=12 loops=1)
              Buffers: shared hit=1
Planning Time: 0.045 ms
Execution Time: 0.038 ms
```

</details>

<details><summary>Plano completo</summary>

```
Aggregate  (cost=934.79..934.80 rows=1 width=8) (actual time=3.233..3.234 rows=1 loops=1)
  Buffers: shared hit=571
  ->  Hash Join  (cost=317.35..872.60 rows=4975 width=40) (actual time=1.479..3.062 rows=5000 loops=1)
        Hash Cond: (metrica.parceiro_id = parceiro.id)
        Buffers: shared hit=571
        ->  Bitmap Heap Scan on metrica  (cost=138.85..681.03 rows=4975 width=11) (actual time=0.535..1.420 rows=5000 loops=1)
              Recheck Cond: (periodo_id = 12)
              Heap Blocks: exact=480
              Buffers: shared hit=505
              ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..137.60 rows=4975 width=0) (actual time=0.483..0.483 rows=5000 loops=1)
                    Index Cond: (periodo_id = 12)
                    Buffers: shared hit=25
        ->  Hash  (cost=116.00..116.00 rows=5000 width=21) (actual time=0.909..0.909 rows=5000 loops=1)
              Buckets: 8192  Batches: 1  Memory Usage: 333kB
              Buffers: shared hit=66
              ->  Seq Scan on parceiro  (cost=0.00..116.00 rows=5000 width=21) (actual time=0.003..0.327 rows=5000 loops=1)
                    Buffers: shared hit=66
Planning:
  Buffers: shared hit=12
Planning Time: 0.223 ms
Execution Time: 3.388 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=2318.92..2319.42 rows=200 width=54) (actual time=9.545..9.564 rows=200 loops=1)
  Buffers: shared hit=677
  ->  Sort  (cost=2318.92..2331.60 rows=5071 width=54) (actual time=9.544..9.553 rows=200 loops=1)
        Sort Key: (row_number() OVER (?))
        Sort Method: top-N heapsort  Memory: 51kB
        Buffers: shared hit=677
        ->  Hash Left Join  (cost=1905.76..2099.75 rows=5071 width=54) (actual time=5.751..8.881 rows=5000 loops=1)
              Hash Cond: (metrica.parceiro_id = historico_segmento.parceiro_id)
              Buffers: shared hit=677
              ->  Hash Left Join  (cost=1357.81..1538.73 rows=4975 width=50) (actual time=4.812..7.297 rows=5000 loops=1)
                    Hash Cond: (parceiro.categoria_id = categoria.id)
                    Buffers: shared hit=638
                    ->  Hash Join  (cost=1356.58..1518.90 rows=4975 width=44) (actual time=4.790..6.746 rows=5000 loops=1)
                          Hash Cond: (metrica.parceiro_id = parceiro.id)
                          Buffers: shared hit=637
                          ->  WindowAgg  (cost=1178.08..1277.58 rows=4975 width=40) (actual time=3.825..4.881 rows=5000 loops=1)
                                Buffers: shared hit=571
                                ->  Sort  (cost=1178.08..1190.52 rows=4975 width=32) (actual time=3.817..4.060 rows=5000 loops=1)
                                      Sort Key: metrica.faturamento DESC, parceiro_1.nome
                                      Sort Method: quicksort  Memory: 488kB
                                      Buffers: shared hit=571
                                      ->  Hash Join  (cost=317.35..872.60 rows=4975 width=32) (actual time=1.195..2.561 rows=5000 loops=1)
                                            Hash Cond: (metrica.parceiro_id = parceiro_1.id)
                                            Buffers: shared hit=571
                                            ->  Bitmap Heap Scan on metrica  (cost=138.85..681.03 rows=4975 width=15) (actual time=0.269..0.950 rows=5000 loops=1)
                                                  Recheck Cond: (periodo_id = 12)
                                                  Heap Blocks: exact=480
                                                  Buffers: shared hit=505
                                                  ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..137.60 rows=4975 width=0) (actual time=0.232..0.232 rows=5000 loops=1)
                                                        Index Cond: (periodo_id = 12)
                                                        Buffers: shared hit=25
                                            ->  Hash  (cost=116.00..116.00 rows=5000 width=21) (actual time=0.886..0.887 rows=5000 loops=1)
                                                  Buckets: 8192  Batches: 1  Memory Usage: 333kB
                                                  Buffers: shared hit=66
                                                  ->  Seq Scan on parceiro parceiro_1  (cost=0.00..116.00 rows=5000 width=21) (actual time=0.002..0.263 rows=5000 loops=1)
                                                        Buffers: shared hit=66
                          ->  Hash  (cost=116.00..116.00 rows=5000 width=25) (actual time=0.930..0.930 rows=5000 loops=1)
                                Buckets: 8192  Batches: 1  Memory Usage: 352kB
                                Buffers: shared hit=66
                                ->  Seq Scan on parceiro  (cost=0.00..116.00 rows=5000 width=25) (actual time=0.004..0.310 rows=5000 loops=1)
                                      Buffers: shared hit=66
                    ->  Hash  (cost=1.10..1.10 rows=10 width=14) (actual time=0.013..0.013 rows=10 loops=1)
                          Buckets: 1024  Batches: 1  Memory Usage: 9kB
                          Buffers: shared hit=1
                          ->  Seq Scan on categoria  (cost=0.00..1.10 rows=10 width=14) (actual time=0.004..0.005 rows=10 loops=1)
                                Buffers: shared hit=1
              ->  Hash  (cost=485.11..485.11 rows=5028 width=8) (actual time=0.902..0.902 rows=5000 loops=1)
                    Buckets: 8192  Batches: 1  Memory Usage: 260kB
                    Buffers: shared hit=39
                    ->  Bitmap Heap Scan on historico_segmento  (cost=59.26..485.11 rows=5028 width=8) (actual time=0.072..0.402 rows=5000 loops=1)
                          Recheck Cond: (periodo_id = 12)
                          Heap Blocks: exact=33
                          Buffers: shared hit=39
                          ->  Bitmap Index Scan on ix_segmento_periodo_segmento  (cost=0.00..58.00 rows=5028 width=0) (actual time=0.067..0.067 rows=5000 loops=1)
                                Index Cond: (periodo_id = 12)
                                Buffers: shared hit=6
Planning:
  Buffers: shared hit=28
Planning Time: 0.527 ms
Execution Time: 10.018 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=1.20..1.21 rows=1 width=12) (actual time=0.026..0.026 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.20..1.23 rows=11 width=12) (actual time=0.025..0.025 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.15 rows=11 width=12) (actual time=0.005..0.006 rows=11 loops=1)
              Filter: (data_inicio < '2026-09-14'::date)
              Rows Removed by Filter: 1
              Buffers: shared hit=1
Planning:
  Buffers: shared hit=2
Planning Time: 0.110 ms
Execution Time: 0.080 ms
```

</details>

<details><summary>Plano completo</summary>

```
Subquery Scan on anterior  (cost=1168.80..1339.18 rows=198 width=19) (actual time=4.140..5.479 rows=196 loops=1)
  Filter: (anterior.parceiro_id = ANY ('{2118,4133,4648,1577,2515,1682,2384,4544,3134,246,4155,3997,924,3103,4101,3194,460,2744,2149,4982,1823,4254,1563,1917,4468,4729,4676,1660,983,2272,2864,1242,1307,2260,3721,2999,3662,3453,3217,4716,4654,1936,4885,2050,3270,1793,152,1395,2044,823,2314,2470,1754,860,2311,600,2336,181,4340,3621,3736,613,3133,3415,3389,1019,959,381,2666,2539,885,1265,2134,1067,510,1663,1896,214,2125,2074,3090,4890,4171,1393,74,1586,3049,2828,906,484,3461,3211,3579,1382,1348,1782,1238,2085,630,524,4059,4268,733,2512,549,4156,1825,2296,3857,3737,2232,4044,3629,1763,2914,3758,3095,572,2053,2759,4179,1596,3384,3273,4695,1458,2073,1010,2980,2618,1757,339,1503,1443,2520,3619,263,3623,2108,3860,2127,4580,2821,2404,757,4115,4618,3097,927,3517,639,4691,4574,3204,1304,3657,3221,4920,654,4670,1084,4420,3343,1440,3813,2968,7,2834,2231,4793,2267,1377,1311,4980,3576,2880,1959,4886,4009,589,3016,2936,3667,3433,1566,800,2049,1972,1533,1417,3754,4432,2036,1303,2241,3094,2363,3403,1281,80}'::integer[]))
  Rows Removed by Filter: 4699
  Buffers: shared hit=569
  ->  WindowAgg  (cost=1168.30..1265.66 rows=4868 width=40) (actual time=4.133..5.209 rows=4895 loops=1)
        Buffers: shared hit=569
        ->  Sort  (cost=1168.30..1180.47 rows=4868 width=28) (actual time=4.124..4.306 rows=4895 loops=1)
              Sort Key: metrica.faturamento DESC, parceiro.nome
              Sort Method: quicksort  Memory: 460kB
              Buffers: shared hit=569
              ->  Hash Join  (cost=316.52..870.16 rows=4868 width=28) (actual time=1.384..2.907 rows=4895 loops=1)
                    Hash Cond: (metrica.parceiro_id = parceiro.id)
                    Buffers: shared hit=569
                    ->  Bitmap Heap Scan on metrica  (cost=138.02..678.87 rows=4868 width=11) (actual time=0.271..0.964 rows=4895 loops=1)
                          Recheck Cond: (periodo_id = 11)
                          Heap Blocks: exact=480
                          Buffers: shared hit=503
                          ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..136.80 rows=4868 width=0) (actual time=0.235..0.235 rows=4895 loops=1)
                                Index Cond: (periodo_id = 11)
                                Buffers: shared hit=23
                    ->  Hash  (cost=116.00..116.00 rows=5000 width=21) (actual time=1.074..1.074 rows=5000 loops=1)
                          Buckets: 8192  Batches: 1  Memory Usage: 333kB
                          Buffers: shared hit=66
                          ->  Seq Scan on parceiro  (cost=0.00..116.00 rows=5000 width=21) (actual time=0.004..0.471 rows=5000 loops=1)
                                Buffers: shared hit=66
Planning:
  Buffers: shared hit=12
Planning Time: 0.544 ms
Execution Time: 6.020 ms
```

</details>

### `serie`

A série agrega **todos** os períodos: a consulta lê a tabela inteira por definição, e varrer é o plano certo.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim, sum(metrica.faturamento) AS sum_1, sum(metrica.pedi…`
  - tempo no banco: **15.91 ms** · varredura: `metrica`, `periodo`

<details><summary>Plano completo</summary>

```
Sort  (cost=1678.96..1678.99 rows=12 width=52) (actual time=15.868..15.870 rows=12 loops=1)
  Sort Key: periodo.data_inicio, periodo.id
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=481
  ->  HashAggregate  (cost=1678.59..1678.74 rows=12 width=52) (actual time=15.859..15.863 rows=12 loops=1)
        Group Key: periodo.id
        Batches: 1  Memory Usage: 24kB
        Buffers: shared hit=481
        ->  Hash Right Join  (cost=1.27..1252.04 rows=56874 width=23) (actual time=0.021..9.223 rows=56874 loops=1)
              Hash Cond: (metrica.periodo_id = periodo.id)
              Buffers: shared hit=481
              ->  Seq Scan on metrica  (cost=0.00..1048.74 rows=56874 width=15) (actual time=0.002..2.173 rows=56874 loops=1)
                    Buffers: shared hit=480
              ->  Hash  (cost=1.12..1.12 rows=12 width=12) (actual time=0.014..0.015 rows=12 loops=1)
                    Buckets: 1024  Batches: 1  Memory Usage: 9kB
                    Buffers: shared hit=1
                    ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.004..0.004 rows=12 loops=1)
                          Buffers: shared hit=1
Planning:
  Buffers: shared hit=4
Planning Time: 0.148 ms
Execution Time: 15.908 ms
```

</details>

### `segmentos`

A consulta filtra `historico_segmento`. Se o planejador varrer, a conferência abaixo diz se foi escolha dele ou falta de índice.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo ORDER BY periodo.data_inicio DESC, peri…`
  - tempo no banco: **0.01 ms** · varredura: `periodo`
- `SELECT historico_segmento.segmento, count(*) AS count_1 FROM historico_segmento WHERE historico_segmento.peri…`
  - tempo no banco: **0.94 ms** · varredura: nenhuma

<details><summary>Plano completo</summary>

```
Limit  (cost=1.18..1.18 rows=1 width=12) (actual time=0.007..0.008 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.18..1.21 rows=12 width=12) (actual time=0.007..0.007 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.003..0.004 rows=12 loops=1)
              Buffers: shared hit=1
Planning Time: 0.043 ms
Execution Time: 0.012 ms
```

</details>

<details><summary>Plano completo</summary>

```
Sort  (cost=510.36..510.37 rows=5 width=12) (actual time=0.898..0.899 rows=5 loops=1)
  Sort Key: (count(*)) DESC, segmento
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=39
  ->  HashAggregate  (cost=510.25..510.30 rows=5 width=12) (actual time=0.895..0.896 rows=5 loops=1)
        Group Key: segmento
        Batches: 1  Memory Usage: 24kB
        Buffers: shared hit=39
        ->  Bitmap Heap Scan on historico_segmento  (cost=59.26..485.11 rows=5028 width=4) (actual time=0.076..0.374 rows=5000 loops=1)
              Recheck Cond: (periodo_id = 12)
              Heap Blocks: exact=33
              Buffers: shared hit=39
              ->  Bitmap Index Scan on ix_segmento_periodo_segmento  (cost=0.00..58.00 rows=5028 width=0) (actual time=0.070..0.070 rows=5000 loops=1)
                    Index Cond: (periodo_id = 12)
                    Buffers: shared hit=6
Planning Time: 0.052 ms
Execution Time: 0.942 ms
```

</details>

### `mobilidade`

A consulta filtra `metrica`. Se o planejador varrer, a conferência abaixo diz se foi escolha dele ou falta de índice.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo ORDER BY periodo.data_inicio DESC, peri…`
  - tempo no banco: **0.01 ms** · varredura: `periodo`
- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo WHERE periodo.data_inicio < %(data_inic…`
  - tempo no banco: **0.01 ms** · varredura: `periodo`
- `SELECT coalesce(atual.parceiro_id, passado.parceiro_id) AS parceiro_id, parceiro.nome, atual.posicao AS posic…`
  - tempo no banco: **12.02 ms** · varredura: `parceiro`

<details><summary>Plano completo</summary>

```
Limit  (cost=1.18..1.18 rows=1 width=12) (actual time=0.008..0.008 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.18..1.21 rows=12 width=12) (actual time=0.007..0.008 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.003..0.004 rows=12 loops=1)
              Buffers: shared hit=1
Planning Time: 0.045 ms
Execution Time: 0.013 ms
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
        ->  Seq Scan on periodo  (cost=0.00..1.15 rows=11 width=12) (actual time=0.003..0.004 rows=11 loops=1)
              Filter: (data_inicio < '2026-09-14'::date)
              Rows Removed by Filter: 1
              Buffers: shared hit=1
Planning:
  Buffers: shared hit=2
Planning Time: 0.084 ms
Execution Time: 0.013 ms
```

</details>

<details><summary>Plano completo</summary>

```
Sort  (cost=3059.96..3062.60 rows=1054 width=45) (actual time=11.432..11.435 rows=4 loops=1)
  Sort Key: (COALESCE((row_number() OVER (?)), passado.posicao))
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=1206
  ->  Hash Join  (cost=2731.77..3007.04 rows=1054 width=45) (actual time=9.776..11.430 rows=4 loops=1)
        Hash Cond: (COALESCE(metrica.parceiro_id, passado.parceiro_id) = parceiro.id)
        Buffers: shared hit=1206
        ->  Hash Full Join  (cost=2553.27..2825.78 rows=1054 width=24) (actual time=8.839..10.491 rows=4 loops=1)
              Hash Cond: (metrica.parceiro_id = passado.parceiro_id)
              Filter: ((((row_number() OVER (?)) <= 15) AND ((passado.posicao IS NULL) OR (passado.posicao > 15))) OR ((passado.posicao <= 15) AND (((row_number() OVER (?)) IS NULL) OR ((row_number() OVER (?)) > 15))))
              Rows Removed by Filter: 4996
              Buffers: shared hit=1140
              ->  WindowAgg  (cost=1178.08..1277.58 rows=4975 width=40) (actual time=3.485..4.427 rows=5000 loops=1)
                    Buffers: shared hit=571
                    ->  Sort  (cost=1178.08..1190.52 rows=4975 width=28) (actual time=3.471..3.669 rows=5000 loops=1)
                          Sort Key: metrica.faturamento DESC, parceiro_1.nome
                          Sort Method: quicksort  Memory: 465kB
                          Buffers: shared hit=571
                          ->  Hash Join  (cost=317.35..872.60 rows=4975 width=28) (actual time=1.072..2.257 rows=5000 loops=1)
                                Hash Cond: (metrica.parceiro_id = parceiro_1.id)
                                Buffers: shared hit=571
                                ->  Bitmap Heap Scan on metrica  (cost=138.85..681.03 rows=4975 width=11) (actual time=0.225..0.757 rows=5000 loops=1)
                                      Recheck Cond: (periodo_id = 12)
                                      Heap Blocks: exact=480
                                      Buffers: shared hit=505
                                      ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..137.60 rows=4975 width=0) (actual time=0.190..0.190 rows=5000 loops=1)
                                            Index Cond: (periodo_id = 12)
                                            Buffers: shared hit=25
                                ->  Hash  (cost=116.00..116.00 rows=5000 width=21) (actual time=0.813..0.813 rows=5000 loops=1)
                                      Buckets: 8192  Batches: 1  Memory Usage: 333kB
                                      Buffers: shared hit=66
                                      ->  Seq Scan on parceiro parceiro_1  (cost=0.00..116.00 rows=5000 width=21) (actual time=0.003..0.253 rows=5000 loops=1)
                                            Buffers: shared hit=66
              ->  Hash  (cost=1314.34..1314.34 rows=4868 width=12) (actual time=5.309..5.310 rows=4895 loops=1)
                    Buckets: 8192  Batches: 1  Memory Usage: 294kB
                    Buffers: shared hit=569
                    ->  Subquery Scan on passado  (cost=1168.30..1314.34 rows=4868 width=12) (actual time=3.489..4.708 rows=4895 loops=1)
                          Buffers: shared hit=569
                          ->  WindowAgg  (cost=1168.30..1265.66 rows=4868 width=40) (actual time=3.488..4.433 rows=4895 loops=1)
                                Buffers: shared hit=569
                                ->  Sort  (cost=1168.30..1180.47 rows=4868 width=28) (actual time=3.480..3.691 rows=4895 loops=1)
                                      Sort Key: metrica_1.faturamento DESC, parceiro_2.nome
                                      Sort Method: quicksort  Memory: 460kB
                                      Buffers: shared hit=569
                                      ->  Hash Join  (cost=316.52..870.16 rows=4868 width=28) (actual time=1.096..2.282 rows=4895 loops=1)
                                            Hash Cond: (metrica_1.parceiro_id = parceiro_2.id)
                                            Buffers: shared hit=569
                                            ->  Bitmap Heap Scan on metrica metrica_1  (cost=138.02..678.87 rows=4868 width=11) (actual time=0.230..0.778 rows=4895 loops=1)
                                                  Recheck Cond: (periodo_id = 11)
                                                  Heap Blocks: exact=480
                                                  Buffers: shared hit=503
                                                  ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..136.80 rows=4868 width=0) (actual time=0.195..0.195 rows=4895 loops=1)
                                                        Index Cond: (periodo_id = 11)
                                                        Buffers: shared hit=23
                                            ->  Hash  (cost=116.00..116.00 rows=5000 width=21) (actual time=0.829..0.829 rows=5000 loops=1)
                                                  Buckets: 8192  Batches: 1  Memory Usage: 333kB
                                                  Buffers: shared hit=66
                                                  ->  Seq Scan on parceiro parceiro_2  (cost=0.00..116.00 rows=5000 width=21) (actual time=0.002..0.252 rows=5000 loops=1)
                                                        Buffers: shared hit=66
        ->  Hash  (cost=116.00..116.00 rows=5000 width=21) (actual time=0.899..0.900 rows=5000 loops=1)
              Buckets: 8192  Batches: 1  Memory Usage: 333kB
              Buffers: shared hit=66
              ->  Seq Scan on parceiro  (cost=0.00..116.00 rows=5000 width=21) (actual time=0.003..0.316 rows=5000 loops=1)
                    Buffers: shared hit=66
Planning:
  Buffers: shared hit=24
Planning Time: 0.567 ms
Execution Time: 12.020 ms
```

</details>

### `busca`

A consulta filtra `parceiro`. Se o planejador varrer, a conferência abaixo diz se foi escolha dele ou falta de índice.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo ORDER BY periodo.data_inicio DESC, peri…`
  - tempo no banco: **0.01 ms** · varredura: `periodo`
- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo WHERE periodo.data_inicio < %(data_inic…`
  - tempo no banco: **0.01 ms** · varredura: `periodo`
- `SELECT count(*) AS count_1 FROM (SELECT parceiro.id AS id, parceiro.nome AS nome, parceiro.nome_normalizado A…`
  - tempo no banco: **0.21 ms** · varredura: nenhuma
- `SELECT parceiro.id, parceiro.nome, parceiro.nome_normalizado, parceiro.categoria_id, parceiro.origem_categori…`
  - tempo no banco: **0.62 ms** · varredura: nenhuma

<details><summary>Plano completo</summary>

```
Sort  (cost=1.34..1.37 rows=12 width=12) (actual time=0.008..0.008 rows=12 loops=1)
  Sort Key: data_inicio DESC, id DESC
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=1
  ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.003..0.004 rows=12 loops=1)
        Buffers: shared hit=1
Planning Time: 0.043 ms
Execution Time: 0.014 ms
```

</details>

<details><summary>Plano completo</summary>

```
Sort  (cost=1.34..1.37 rows=11 width=12) (actual time=0.007..0.008 rows=11 loops=1)
  Sort Key: data_inicio DESC, id DESC
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=1
  ->  Seq Scan on periodo  (cost=0.00..1.15 rows=11 width=12) (actual time=0.003..0.004 rows=11 loops=1)
        Filter: (data_inicio < '2026-09-14'::date)
        Rows Removed by Filter: 1
        Buffers: shared hit=1
Planning:
  Buffers: shared hit=2
Planning Time: 0.085 ms
Execution Time: 0.014 ms
```

</details>

<details><summary>Plano completo</summary>

```
Aggregate  (cost=102.26..102.27 rows=1 width=8) (actual time=0.164..0.164 rows=1 loops=1)
  Buffers: shared hit=72
  ->  Bitmap Heap Scan on parceiro  (cost=31.72..101.51 rows=303 width=0) (actual time=0.077..0.152 rows=307 loops=1)
        Recheck Cond: ((nome_normalizado)::text ~~ '%praca%'::text)
        Heap Blocks: exact=65
        Buffers: shared hit=72
        ->  Bitmap Index Scan on ix_parceiro_nome_normalizado_trgm  (cost=0.00..31.64 rows=303 width=0) (actual time=0.071..0.071 rows=307 loops=1)
              Index Cond: ((nome_normalizado)::text ~~ '%praca%'::text)
              Buffers: shared hit=7
Planning:
  Buffers: shared hit=1
Planning Time: 0.125 ms
Execution Time: 0.211 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=19.12..910.28 rows=50 width=339) (actual time=0.359..0.531 rows=50 loops=1)
  Buffers: shared hit=1370
  ->  Incremental Sort  (cost=19.12..5455.23 rows=305 width=339) (actual time=0.359..0.528 rows=50 loops=1)
        Sort Key: parceiro.nome, parceiro.id
        Presorted Key: parceiro.nome
        Full-sort Groups: 2  Sort Method: quicksort  Average Memory: 29kB  Peak Memory: 29kB
        Buffers: shared hit=1370
        ->  Nested Loop Left Join  (cost=1.15..5441.57 rows=305 width=339) (actual time=0.108..0.509 rows=51 loops=1)
              Buffers: shared hit=1370
              ->  Nested Loop Left Join  (cost=0.86..3787.64 rows=303 width=335) (actual time=0.097..0.408 rows=51 loops=1)
                    Buffers: shared hit=1217
                    ->  Nested Loop Left Join  (cost=0.57..2145.71 rows=303 width=328) (actual time=0.089..0.357 rows=51 loops=1)
                          Buffers: shared hit=1064
                          ->  Index Scan using ix_parceiro_nome on parceiro  (cost=0.28..503.78 rows=303 width=317) (actual time=0.077..0.251 rows=51 loops=1)
                                Filter: ((nome_normalizado)::text ~~ '%praca%'::text)
                                Rows Removed by Filter: 896
                                Buffers: shared hit=911
                          ->  Index Scan using uq_metrica_parceiro_periodo on metrica  (cost=0.29..5.42 rows=1 width=15) (actual time=0.002..0.002 rows=1 loops=51)
                                Index Cond: ((parceiro_id = parceiro.id) AND (periodo_id = 12))
                                Buffers: shared hit=153
                    ->  Index Scan using uq_metrica_parceiro_periodo on metrica metrica_1  (cost=0.29..5.42 rows=1 width=11) (actual time=0.001..0.001 rows=1 loops=51)
                          Index Cond: ((parceiro_id = parceiro.id) AND (periodo_id = 11))
                          Buffers: shared hit=153
              ->  Index Scan using uq_segmento_parceiro_periodo on historico_segmento  (cost=0.29..5.46 rows=1 width=8) (actual time=0.002..0.002 rows=1 loops=51)
                    Index Cond: ((parceiro_id = parceiro.id) AND (periodo_id = 12))
                    Buffers: shared hit=153
Planning:
  Buffers: shared hit=37
Planning Time: 0.758 ms
Execution Time: 0.619 ms
```

</details>

### `lista-completa`

Sem filtro, a resposta é a tabela inteira; o custo está no volume, não no plano. É o caso que a paginação da H36 precisa resolver.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo ORDER BY periodo.data_inicio DESC, peri…`
  - tempo no banco: **0.01 ms** · varredura: `periodo`
- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo WHERE periodo.data_inicio < %(data_inic…`
  - tempo no banco: **0.01 ms** · varredura: `periodo`
- `SELECT count(*) AS count_1 FROM (SELECT parceiro.id AS id, parceiro.nome AS nome, parceiro.nome_normalizado A…`
  - tempo no banco: **0.41 ms** · varredura: `parceiro`
- `SELECT parceiro.id, parceiro.nome, parceiro.nome_normalizado, parceiro.categoria_id, parceiro.origem_categori…`
  - tempo no banco: **0.40 ms** · varredura: nenhuma

<details><summary>Plano completo</summary>

```
Sort  (cost=1.34..1.37 rows=12 width=12) (actual time=0.007..0.007 rows=12 loops=1)
  Sort Key: data_inicio DESC, id DESC
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=1
  ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.003..0.004 rows=12 loops=1)
        Buffers: shared hit=1
Planning Time: 0.027 ms
Execution Time: 0.012 ms
```

</details>

<details><summary>Plano completo</summary>

```
Sort  (cost=1.34..1.37 rows=11 width=12) (actual time=0.006..0.007 rows=11 loops=1)
  Sort Key: data_inicio DESC, id DESC
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=1
  ->  Seq Scan on periodo  (cost=0.00..1.15 rows=11 width=12) (actual time=0.003..0.004 rows=11 loops=1)
        Filter: (data_inicio < '2026-09-14'::date)
        Rows Removed by Filter: 1
        Buffers: shared hit=1
Planning:
  Buffers: shared hit=2
Planning Time: 0.057 ms
Execution Time: 0.012 ms
```

</details>

<details><summary>Plano completo</summary>

```
Aggregate  (cost=128.50..128.51 rows=1 width=8) (actual time=0.380..0.380 rows=1 loops=1)
  Buffers: shared hit=66
  ->  Seq Scan on parceiro  (cost=0.00..116.00 rows=5000 width=0) (actual time=0.003..0.209 rows=5000 loops=1)
        Buffers: shared hit=66
Planning Time: 0.088 ms
Execution Time: 0.408 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=3.67..130.57 rows=50 width=339) (actual time=0.227..0.321 rows=50 loops=1)
  Buffers: shared hit=509
  ->  Incremental Sort  (cost=3.67..12765.02 rows=5028 width=339) (actual time=0.227..0.318 rows=50 loops=1)
        Sort Key: parceiro.nome, parceiro.id
        Presorted Key: parceiro.nome
        Full-sort Groups: 2  Sort Method: quicksort  Average Memory: 29kB  Peak Memory: 29kB
        Buffers: shared hit=509
        ->  Nested Loop Left Join  (cost=1.15..12539.74 rows=5028 width=339) (actual time=0.047..0.299 rows=51 loops=1)
              Buffers: shared hit=509
              ->  Nested Loop Left Join  (cost=0.86..8702.22 rows=5000 width=335) (actual time=0.036..0.195 rows=51 loops=1)
                    Buffers: shared hit=356
                    ->  Nested Loop Left Join  (cost=0.57..4596.75 rows=5000 width=328) (actual time=0.026..0.143 rows=51 loops=1)
                          Buffers: shared hit=204
                          ->  Index Scan using ix_parceiro_nome on parceiro  (cost=0.28..491.28 rows=5000 width=317) (actual time=0.012..0.028 rows=51 loops=1)
                                Buffers: shared hit=51
                          ->  Index Scan using uq_metrica_parceiro_periodo on metrica  (cost=0.29..0.82 rows=1 width=15) (actual time=0.002..0.002 rows=1 loops=51)
                                Index Cond: ((parceiro_id = parceiro.id) AND (periodo_id = 12))
                                Buffers: shared hit=153
                    ->  Index Scan using uq_metrica_parceiro_periodo on metrica metrica_1  (cost=0.29..0.82 rows=1 width=11) (actual time=0.001..0.001 rows=1 loops=51)
                          Index Cond: ((parceiro_id = parceiro.id) AND (periodo_id = 11))
                          Buffers: shared hit=152
              ->  Index Scan using uq_segmento_parceiro_periodo on historico_segmento  (cost=0.29..0.77 rows=1 width=8) (actual time=0.002..0.002 rows=1 loops=51)
                    Index Cond: ((parceiro_id = parceiro.id) AND (periodo_id = 12))
                    Buffers: shared hit=153
Planning:
  Buffers: shared hit=36
Planning Time: 0.759 ms
Execution Time: 0.404 ms
```

</details>

## Índices em uso

- `ix_metrica_periodo_faturamento`
- `ix_parceiro_nome`
- `ix_parceiro_nome_normalizado_trgm`
- `ix_segmento_periodo_segmento`
- `uq_metrica_parceiro_periodo`
- `uq_segmento_parceiro_periodo`

