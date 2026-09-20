# Medição do painel com 10.000 parceiros — H40

> Gerado por `scripts/medir_painel.py`. **Não edite à mão**: número escrito à mão não é evidência. Para atualizar, rode o comando abaixo de novo.

O RNF03 fixa **2 s** como teto de resposta e a H40 cobra isso com 10.000 parceiros. Este arquivo é o registro da medição — a Sprint 12 não precisa medir de novo às pressas para pôr o número na apresentação.

## Ambiente

| Item | Valor |
|---|---|
| Data | 20/09/2026 01:02 |
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
| `indicadores` | 300 | 13.8 ms | 15.7 ms | 13% | 345 B | sim |
| `ranking-25` | 150 | 43.0 ms | 50.0 ms | 16% | 6 kB | sim |
| `ranking-200` | 122 | 46.5 ms | 53.2 ms | 14% | 43 kB | sim |
| `serie` | 184 | 31.4 ms | 34.5 ms | 10% | 2 kB | sim |
| `busca` | 300 | 21.3 ms | 47.6 ms | 123% | 128 kB | sim |
| `lista-completa` | 19 | 294.5 ms | 364.3 ms | 24% | 2026 kB | sim |

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
  - tempo no banco: **2.36 ms** · varredura: nenhuma
- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo WHERE periodo.data_inicio < %(data_inic…`
  - tempo no banco: **0.01 ms** · varredura: `periodo`

<details><summary>Plano completo</summary>

```
Limit  (cost=1.18..1.18 rows=1 width=12) (actual time=0.006..0.006 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.18..1.21 rows=12 width=12) (actual time=0.005..0.006 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.002..0.003 rows=12 loops=1)
              Buffers: shared hit=1
Planning Time: 0.040 ms
Execution Time: 0.010 ms
```

</details>

<details><summary>Plano completo</summary>

```
Aggregate  (cost=1452.70..1452.71 rows=1 width=48) (actual time=2.288..2.288 rows=1 loops=1)
  Buffers: shared hit=1011
  ->  Bitmap Heap Scan on metrica  (cost=290.41..1377.21 rows=10064 width=11) (actual time=0.494..1.467 rows=10000 loops=1)
        Recheck Cond: (periodo_id = 12)
        Heap Blocks: exact=961
        Buffers: shared hit=1011
        ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..287.90 rows=10064 width=0) (actual time=0.418..0.418 rows=10000 loops=1)
              Index Cond: (periodo_id = 12)
              Buffers: shared hit=50
Planning Time: 0.050 ms
Execution Time: 2.356 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=1.20..1.21 rows=1 width=12) (actual time=0.007..0.007 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.20..1.23 rows=11 width=12) (actual time=0.006..0.006 rows=1 loops=1)
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
Execution Time: 0.015 ms
```

</details>

### `ranking-25`

A consulta filtra `metrica`. Se o planejador varrer, a conferência abaixo diz se foi escolha dele ou falta de índice.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo ORDER BY periodo.data_inicio DESC, peri…`
  - tempo no banco: **0.04 ms** · varredura: `periodo`
- `SELECT count(*) AS count_1 FROM (SELECT metrica.parceiro_id AS parceiro_id, metrica.faturamento AS faturament…`
  - tempo no banco: **7.18 ms** · varredura: `parceiro`
- `SELECT atual.parceiro_id, atual.faturamento, atual.pedidos, atual.posicao, parceiro.nome, categoria.nome AS n…`
  - tempo no banco: **20.86 ms** · varredura: `categoria`, `parceiro`
- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo WHERE periodo.data_inicio < %(data_inic…`
  - tempo no banco: **0.05 ms** · varredura: `periodo`
- `SELECT anterior.parceiro_id, anterior.posicao, anterior.faturamento FROM (SELECT metrica.parceiro_id AS parce…`
  - tempo no banco: **10.11 ms** · varredura: `parceiro`

<details><summary>Plano completo</summary>

```
Limit  (cost=1.18..1.18 rows=1 width=12) (actual time=0.022..0.022 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.18..1.21 rows=12 width=12) (actual time=0.021..0.021 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.006..0.007 rows=12 loops=1)
              Buffers: shared hit=1
Planning Time: 0.054 ms
Execution Time: 0.044 ms
```

</details>

<details><summary>Plano completo</summary>

```
Aggregate  (cost=1885.44..1885.45 rows=1 width=8) (actual time=6.973..6.974 rows=1 loops=1)
  Buffers: shared hit=1142
  ->  Hash Join  (cost=646.41..1759.64 rows=10064 width=40) (actual time=3.150..6.571 rows=10000 loops=1)
        Hash Cond: (metrica.parceiro_id = parceiro.id)
        Buffers: shared hit=1142
        ->  Bitmap Heap Scan on metrica  (cost=290.41..1377.21 rows=10064 width=11) (actual time=0.606..2.227 rows=10000 loops=1)
              Recheck Cond: (periodo_id = 12)
              Heap Blocks: exact=961
              Buffers: shared hit=1011
              ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..287.90 rows=10064 width=0) (actual time=0.525..0.525 rows=10000 loops=1)
                    Index Cond: (periodo_id = 12)
                    Buffers: shared hit=50
        ->  Hash  (cost=231.00..231.00 rows=10000 width=21) (actual time=2.362..2.363 rows=10000 loops=1)
              Buckets: 16384  Batches: 1  Memory Usage: 668kB
              Buffers: shared hit=131
              ->  Seq Scan on parceiro  (cost=0.00..231.00 rows=10000 width=21) (actual time=0.005..0.890 rows=10000 loops=1)
                    Buffers: shared hit=131
Planning:
  Buffers: shared hit=12
Planning Time: 0.241 ms
Execution Time: 7.185 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=3435.93..3435.99 rows=25 width=50) (actual time=20.296..20.302 rows=25 loops=1)
  Buffers: shared hit=1274
  ->  Sort  (cost=3435.93..3461.09 rows=10064 width=50) (actual time=20.295..20.299 rows=25 loops=1)
        Sort Key: (row_number() OVER (?))
        Sort Method: top-N heapsort  Memory: 28kB
        Buffers: shared hit=1274
        ->  Hash Left Join  (cost=2785.97..3151.93 rows=10064 width=50) (actual time=12.837..19.103 rows=10000 loops=1)
              Hash Cond: (parceiro.categoria_id = categoria.id)
              Buffers: shared hit=1274
              ->  Hash Join  (cost=2784.74..3113.09 rows=10064 width=44) (actual time=12.799..17.904 rows=10000 loops=1)
                    Hash Cond: (metrica.parceiro_id = parceiro.id)
                    Buffers: shared hit=1273
                    ->  WindowAgg  (cost=2428.74..2630.02 rows=10064 width=40) (actual time=10.382..13.077 rows=10000 loops=1)
                          Buffers: shared hit=1142
                          ->  Sort  (cost=2428.74..2453.90 rows=10064 width=32) (actual time=10.314..10.918 rows=10000 loops=1)
                                Sort Key: metrica.faturamento DESC, parceiro_1.nome
                                Sort Method: quicksort  Memory: 978kB
                                Buffers: shared hit=1142
                                ->  Hash Join  (cost=646.41..1759.64 rows=10064 width=32) (actual time=3.401..6.856 rows=10000 loops=1)
                                      Hash Cond: (metrica.parceiro_id = parceiro_1.id)
                                      Buffers: shared hit=1142
                                      ->  Bitmap Heap Scan on metrica  (cost=290.41..1377.21 rows=10064 width=15) (actual time=0.758..2.493 rows=10000 loops=1)
                                            Recheck Cond: (periodo_id = 12)
                                            Heap Blocks: exact=961
                                            Buffers: shared hit=1011
                                            ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..287.90 rows=10064 width=0) (actual time=0.671..0.672 rows=10000 loops=1)
                                                  Index Cond: (periodo_id = 12)
                                                  Buffers: shared hit=50
                                      ->  Hash  (cost=231.00..231.00 rows=10000 width=21) (actual time=2.565..2.566 rows=10000 loops=1)
                                            Buckets: 16384  Batches: 1  Memory Usage: 668kB
                                            Buffers: shared hit=131
                                            ->  Seq Scan on parceiro parceiro_1  (cost=0.00..231.00 rows=10000 width=21) (actual time=0.003..0.986 rows=10000 loops=1)
                                                  Buffers: shared hit=131
                    ->  Hash  (cost=231.00..231.00 rows=10000 width=25) (actual time=2.272..2.273 rows=10000 loops=1)
                          Buckets: 16384  Batches: 1  Memory Usage: 707kB
                          Buffers: shared hit=131
                          ->  Seq Scan on parceiro  (cost=0.00..231.00 rows=10000 width=25) (actual time=0.029..0.902 rows=10000 loops=1)
                                Buffers: shared hit=131
              ->  Hash  (cost=1.10..1.10 rows=10 width=14) (actual time=0.019..0.019 rows=10 loops=1)
                    Buckets: 1024  Batches: 1  Memory Usage: 9kB
                    Buffers: shared hit=1
                    ->  Seq Scan on categoria  (cost=0.00..1.10 rows=10 width=14) (actual time=0.007..0.008 rows=10 loops=1)
                          Buffers: shared hit=1
Planning:
  Buffers: shared hit=22
Planning Time: 0.761 ms
Execution Time: 20.861 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=1.20..1.21 rows=1 width=12) (actual time=0.028..0.029 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.20..1.23 rows=11 width=12) (actual time=0.028..0.028 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.15 rows=11 width=12) (actual time=0.005..0.007 rows=11 loops=1)
              Filter: (data_inicio < '2026-09-07'::date)
              Rows Removed by Filter: 1
              Buffers: shared hit=1
Planning:
  Buffers: shared hit=2
Planning Time: 0.095 ms
Execution Time: 0.046 ms
```

</details>

<details><summary>Plano completo</summary>

```
Subquery Scan on anterior  (cost=2398.37..2741.02 rows=25 width=19) (actual time=7.609..9.813 rows=25 loops=1)
  Filter: (anterior.parceiro_id = ANY ('{4133,2118,8156,4648,2384,2515,1577,1682,6266,6144,4544,3134,3103,4155,924,246,4101,8777,3997,4254,5834,6210,3194,460,9809}'::integer[]))
  Rows Removed by Filter: 9791
  Buffers: shared hit=1146
  ->  WindowAgg  (cost=2398.31..2594.11 rows=9790 width=40) (actual time=7.605..9.333 rows=9816 loops=1)
        Buffers: shared hit=1146
        ->  Sort  (cost=2398.31..2422.78 rows=9790 width=28) (actual time=7.593..8.022 rows=9816 loops=1)
              Sort Key: metrica.faturamento DESC, parceiro.nome
              Sort Method: quicksort  Memory: 922kB
              Buffers: shared hit=1146
              ->  Hash Join  (cost=640.29..1749.37 rows=9790 width=28) (actual time=2.378..5.127 rows=9816 loops=1)
                    Hash Cond: (metrica.parceiro_id = parceiro.id)
                    Buffers: shared hit=1146
                    ->  Bitmap Heap Scan on metrica  (cost=284.29..1367.66 rows=9790 width=11) (actual time=0.531..1.897 rows=9816 loops=1)
                          Recheck Cond: (periodo_id = 11)
                          Heap Blocks: exact=961
                          Buffers: shared hit=1015
                          ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..281.84 rows=9790 width=0) (actual time=0.456..0.456 rows=9816 loops=1)
                                Index Cond: (periodo_id = 11)
                                Buffers: shared hit=54
                    ->  Hash  (cost=231.00..231.00 rows=10000 width=21) (actual time=1.779..1.779 rows=10000 loops=1)
                          Buckets: 16384  Batches: 1  Memory Usage: 668kB
                          Buffers: shared hit=131
                          ->  Seq Scan on parceiro  (cost=0.00..231.00 rows=10000 width=21) (actual time=0.003..0.625 rows=10000 loops=1)
                                Buffers: shared hit=131
Planning:
  Buffers: shared hit=12
Planning Time: 0.234 ms
Execution Time: 10.114 ms
```

</details>

### `ranking-200`

A consulta filtra `metrica`. Se o planejador varrer, a conferência abaixo diz se foi escolha dele ou falta de índice.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo ORDER BY periodo.data_inicio DESC, peri…`
  - tempo no banco: **0.04 ms** · varredura: `periodo`
- `SELECT count(*) AS count_1 FROM (SELECT metrica.parceiro_id AS parceiro_id, metrica.faturamento AS faturament…`
  - tempo no banco: **5.60 ms** · varredura: `parceiro`
- `SELECT atual.parceiro_id, atual.faturamento, atual.pedidos, atual.posicao, parceiro.nome, categoria.nome AS n…`
  - tempo no banco: **16.14 ms** · varredura: `categoria`, `parceiro`
- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo WHERE periodo.data_inicio < %(data_inic…`
  - tempo no banco: **0.03 ms** · varredura: `periodo`
- `SELECT anterior.parceiro_id, anterior.posicao, anterior.faturamento FROM (SELECT metrica.parceiro_id AS parce…`
  - tempo no banco: **9.81 ms** · varredura: `parceiro`

<details><summary>Plano completo</summary>

```
Limit  (cost=1.18..1.18 rows=1 width=12) (actual time=0.018..0.019 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.18..1.21 rows=12 width=12) (actual time=0.018..0.018 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.004..0.005 rows=12 loops=1)
              Buffers: shared hit=1
Planning Time: 0.037 ms
Execution Time: 0.037 ms
```

</details>

<details><summary>Plano completo</summary>

```
Aggregate  (cost=1885.44..1885.45 rows=1 width=8) (actual time=5.323..5.324 rows=1 loops=1)
  Buffers: shared hit=1142
  ->  Hash Join  (cost=646.41..1759.64 rows=10064 width=40) (actual time=2.487..4.971 rows=10000 loops=1)
        Hash Cond: (metrica.parceiro_id = parceiro.id)
        Buffers: shared hit=1142
        ->  Bitmap Heap Scan on metrica  (cost=290.41..1377.21 rows=10064 width=11) (actual time=0.551..1.724 rows=10000 loops=1)
              Recheck Cond: (periodo_id = 12)
              Heap Blocks: exact=961
              Buffers: shared hit=1011
              ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..287.90 rows=10064 width=0) (actual time=0.466..0.466 rows=10000 loops=1)
                    Index Cond: (periodo_id = 12)
                    Buffers: shared hit=50
        ->  Hash  (cost=231.00..231.00 rows=10000 width=21) (actual time=1.868..1.868 rows=10000 loops=1)
              Buckets: 16384  Batches: 1  Memory Usage: 668kB
              Buffers: shared hit=131
              ->  Seq Scan on parceiro  (cost=0.00..231.00 rows=10000 width=21) (actual time=0.003..0.620 rows=10000 loops=1)
                    Buffers: shared hit=131
Planning:
  Buffers: shared hit=12
Planning Time: 0.210 ms
Execution Time: 5.596 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=3586.89..3587.39 rows=200 width=50) (actual time=15.539..15.556 rows=200 loops=1)
  Buffers: shared hit=1274
  ->  Sort  (cost=3586.89..3612.05 rows=10064 width=50) (actual time=15.539..15.546 rows=200 loops=1)
        Sort Key: (row_number() OVER (?))
        Sort Method: top-N heapsort  Memory: 51kB
        Buffers: shared hit=1274
        ->  Hash Left Join  (cost=2785.97..3151.93 rows=10064 width=50) (actual time=9.846..14.386 rows=10000 loops=1)
              Hash Cond: (parceiro.categoria_id = categoria.id)
              Buffers: shared hit=1274
              ->  Hash Join  (cost=2784.74..3113.09 rows=10064 width=44) (actual time=9.818..13.365 rows=10000 loops=1)
                    Hash Cond: (metrica.parceiro_id = parceiro.id)
                    Buffers: shared hit=1273
                    ->  WindowAgg  (cost=2428.74..2630.02 rows=10064 width=40) (actual time=7.716..9.617 rows=10000 loops=1)
                          Buffers: shared hit=1142
                          ->  Sort  (cost=2428.74..2453.90 rows=10064 width=32) (actual time=7.700..8.119 rows=10000 loops=1)
                                Sort Key: metrica.faturamento DESC, parceiro_1.nome
                                Sort Method: quicksort  Memory: 978kB
                                Buffers: shared hit=1142
                                ->  Hash Join  (cost=646.41..1759.64 rows=10064 width=32) (actual time=2.334..5.120 rows=10000 loops=1)
                                      Hash Cond: (metrica.parceiro_id = parceiro_1.id)
                                      Buffers: shared hit=1142
                                      ->  Bitmap Heap Scan on metrica  (cost=290.41..1377.21 rows=10064 width=15) (actual time=0.563..1.859 rows=10000 loops=1)
                                            Recheck Cond: (periodo_id = 12)
                                            Heap Blocks: exact=961
                                            Buffers: shared hit=1011
                                            ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..287.90 rows=10064 width=0) (actual time=0.477..0.477 rows=10000 loops=1)
                                                  Index Cond: (periodo_id = 12)
                                                  Buffers: shared hit=50
                                      ->  Hash  (cost=231.00..231.00 rows=10000 width=21) (actual time=1.698..1.698 rows=10000 loops=1)
                                            Buckets: 16384  Batches: 1  Memory Usage: 668kB
                                            Buffers: shared hit=131
                                            ->  Seq Scan on parceiro parceiro_1  (cost=0.00..231.00 rows=10000 width=21) (actual time=0.003..0.535 rows=10000 loops=1)
                                                  Buffers: shared hit=131
                    ->  Hash  (cost=231.00..231.00 rows=10000 width=25) (actual time=2.022..2.022 rows=10000 loops=1)
                          Buckets: 16384  Batches: 1  Memory Usage: 707kB
                          Buffers: shared hit=131
                          ->  Seq Scan on parceiro  (cost=0.00..231.00 rows=10000 width=25) (actual time=0.003..0.660 rows=10000 loops=1)
                                Buffers: shared hit=131
              ->  Hash  (cost=1.10..1.10 rows=10 width=14) (actual time=0.018..0.018 rows=10 loops=1)
                    Buckets: 1024  Batches: 1  Memory Usage: 9kB
                    Buffers: shared hit=1
                    ->  Seq Scan on categoria  (cost=0.00..1.10 rows=10 width=14) (actual time=0.005..0.006 rows=10 loops=1)
                          Buffers: shared hit=1
Planning:
  Buffers: shared hit=22
Planning Time: 0.360 ms
Execution Time: 16.138 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=1.20..1.21 rows=1 width=12) (actual time=0.015..0.015 rows=1 loops=1)
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
Planning Time: 0.093 ms
Execution Time: 0.029 ms
```

</details>

<details><summary>Plano completo</summary>

```
Subquery Scan on anterior  (cost=2398.81..2741.46 rows=202 width=19) (actual time=7.221..9.489 rows=199 loops=1)
  Filter: (anterior.parceiro_id = ANY ('{4133,2118,8156,4648,2384,2515,1577,1682,6266,6144,4544,3134,3103,4155,924,246,4101,8777,3997,4254,5834,6210,3194,460,9809,7117,2744,1563,2272,2149,6700,8924,6061,5275,1823,4982,4468,5788,9656,9927,6772,1917,2260,4729,3721,2999,4676,983,9817,5323,7651,1660,6952,1242,1307,4716,7128,8044,7384,9527,2864,1936,9344,3217,7656,9814,9490,9892,3270,9104,6606,7911,3662,3453,5257,7609,7619,7033,9142,5998,2470,1395,3736,8553,7965,9573,9386,4885,9035,3133,6999,1793,2311,4340,6693,8137,4654,6290,3621,8365,9904,9534,613,9094,9030,1586,181,7732,9952,2134,1348,600,7674,7023,1265,5022,1019,2336,8625,2314,860,1754,484,8398,9248,5690,5315,5193,2666,6518,2914,9681,2050,1067,6956,5609,214,6190,2125,1010,2044,1393,2831,3389,2539,74,5897,7921,1825,7320,8519,1896,6522,9481,381,1382,9717,6382,5865,6706,6222,6070,7794,6511,3415,4890,2053,549,9754,6676,6773,885,6677,8839,6766,3090,3576,6704,8130,823,906,2074,9332,8698,510,5953,5166,8311,9883,7731,4268,2512,2980,9165,6100,8177,2520,3273,9249,9170}'::integer[]))
  Rows Removed by Filter: 9617
  Buffers: shared hit=1146
  ->  WindowAgg  (cost=2398.31..2594.11 rows=9790 width=40) (actual time=7.211..8.951 rows=9816 loops=1)
        Buffers: shared hit=1146
        ->  Sort  (cost=2398.31..2422.78 rows=9790 width=28) (actual time=7.202..7.611 rows=9816 loops=1)
              Sort Key: metrica.faturamento DESC, parceiro.nome
              Sort Method: quicksort  Memory: 922kB
              Buffers: shared hit=1146
              ->  Hash Join  (cost=640.29..1749.37 rows=9790 width=28) (actual time=2.444..4.914 rows=9816 loops=1)
                    Hash Cond: (metrica.parceiro_id = parceiro.id)
                    Buffers: shared hit=1146
                    ->  Bitmap Heap Scan on metrica  (cost=284.29..1367.66 rows=9790 width=11) (actual time=0.534..1.708 rows=9816 loops=1)
                          Recheck Cond: (periodo_id = 11)
                          Heap Blocks: exact=961
                          Buffers: shared hit=1015
                          ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..281.84 rows=9790 width=0) (actual time=0.459..0.459 rows=9816 loops=1)
                                Index Cond: (periodo_id = 11)
                                Buffers: shared hit=54
                    ->  Hash  (cost=231.00..231.00 rows=10000 width=21) (actual time=1.832..1.832 rows=10000 loops=1)
                          Buckets: 16384  Batches: 1  Memory Usage: 668kB
                          Buffers: shared hit=131
                          ->  Seq Scan on parceiro  (cost=0.00..231.00 rows=10000 width=21) (actual time=0.003..0.595 rows=10000 loops=1)
                                Buffers: shared hit=131
Planning:
  Buffers: shared hit=12
Planning Time: 0.518 ms
Execution Time: 9.809 ms
```

</details>

### `serie`

A série agrega **todos** os períodos: a consulta lê a tabela inteira por definição, e varrer é o plano certo.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim, sum(metrica.faturamento) AS sum_1, sum(metrica.pedi…`
  - tempo no banco: **36.62 ms** · varredura: `metrica`, `periodo`

<details><summary>Plano completo</summary>

```
Sort  (cost=3361.08..3361.11 rows=12 width=52) (actual time=36.564..36.566 rows=12 loops=1)
  Sort Key: periodo.data_inicio, periodo.id
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=962
  ->  HashAggregate  (cost=3360.71..3360.86 rows=12 width=52) (actual time=36.556..36.559 rows=12 loops=1)
        Group Key: periodo.id
        Batches: 1  Memory Usage: 24kB
        Buffers: shared hit=962
        ->  Hash Right Join  (cost=1.27..2506.24 rows=113929 width=23) (actual time=0.027..20.771 rows=113929 loops=1)
              Hash Cond: (metrica.periodo_id = periodo.id)
              Buffers: shared hit=962
              ->  Seq Scan on metrica  (cost=0.00..2100.29 rows=113929 width=15) (actual time=0.002..4.699 rows=113929 loops=1)
                    Buffers: shared hit=961
              ->  Hash  (cost=1.12..1.12 rows=12 width=12) (actual time=0.014..0.015 rows=12 loops=1)
                    Buckets: 1024  Batches: 1  Memory Usage: 9kB
                    Buffers: shared hit=1
                    ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.003..0.004 rows=12 loops=1)
                          Buffers: shared hit=1
Planning:
  Buffers: shared hit=4
Planning Time: 0.182 ms
Execution Time: 36.622 ms
```

</details>

### `busca`

A consulta filtra `parceiro`. Se o planejador varrer, a conferência abaixo diz se foi escolha dele ou falta de índice.

- `SELECT parceiro.id, parceiro.nome, parceiro.nome_normalizado, parceiro.categoria_id, parceiro.origem_categori…`
  - tempo no banco: **0.95 ms** · varredura: nenhuma

<details><summary>Plano completo</summary>

```
Sort  (cost=207.14..208.91 rows=707 width=317) (actual time=0.864..0.885 rows=625 loops=1)
  Sort Key: nome
  Sort Method: quicksort  Memory: 87kB
  Buffers: shared hit=137
  ->  Bitmap Heap Scan on parceiro  (cost=33.84..173.68 rows=707 width=317) (actual time=0.105..0.390 rows=625 loops=1)
        Recheck Cond: ((nome_normalizado)::text ~~ '%praca%'::text)
        Heap Blocks: exact=130
        Buffers: shared hit=137
        ->  Bitmap Index Scan on ix_parceiro_nome_normalizado_trgm  (cost=0.00..33.66 rows=707 width=0) (actual time=0.091..0.091 rows=625 loops=1)
              Index Cond: ((nome_normalizado)::text ~~ '%praca%'::text)
              Buffers: shared hit=7
Planning:
  Buffers: shared hit=1
Planning Time: 0.088 ms
Execution Time: 0.950 ms
```

</details>

### `lista-completa`

Sem filtro, a resposta é a tabela inteira; o custo está no volume, não no plano. É o caso que a paginação da H36 precisa resolver.

- `SELECT parceiro.id, parceiro.nome, parceiro.nome_normalizado, parceiro.categoria_id, parceiro.origem_categori…`
  - tempo no banco: **10.17 ms** · varredura: `parceiro`

<details><summary>Plano completo</summary>

```
Sort  (cost=895.39..920.39 rows=10000 width=317) (actual time=9.436..9.806 rows=10000 loops=1)
  Sort Key: nome
  Sort Method: quicksort  Memory: 1350kB
  Buffers: shared hit=131
  ->  Seq Scan on parceiro  (cost=0.00..231.00 rows=10000 width=317) (actual time=0.007..1.021 rows=10000 loops=1)
        Buffers: shared hit=131
Planning Time: 0.083 ms
Execution Time: 10.174 ms
```

</details>

## Índices em uso

- `ix_metrica_periodo_faturamento`
- `ix_parceiro_nome_normalizado_trgm`

