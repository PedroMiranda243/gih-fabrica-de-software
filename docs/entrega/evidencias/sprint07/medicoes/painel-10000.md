# Medição do painel e dos relatórios com 10.000 parceiros — H40, H82 a H86

> Gerado por `scripts/medir_painel.py`. **Não edite à mão**: número escrito à mão não é evidência. Para atualizar, rode o comando abaixo de novo.

O RNF03 fixa **2 s** como teto de resposta e a H40 cobra isso com 10.000 parceiros. Este arquivo é o registro da medição — a Sprint 12 não precisa medir de novo às pressas para pôr o número na apresentação.

## Ambiente

| Item | Valor |
|---|---|
| Data | 01/10/2026 07:16 |
| Banco | `gih_medicao` — **separado do banco de trabalho** |
| PostgreSQL | PostgreSQL 16.14 on x86_64-pc-linux-musl |
| Python | 3.11.9 |
| Massa | 10.000 parceiros · 12 períodos · 113.929 métricas |
| Semente | 42 |

A medição chama a aplicação em processo, pelo `TestClient`: cobre roteamento, autorização, consulta e serialização — tudo que o navegador espera, menos a rede.

As consultas `-categoria` (H82) usam a categoria com mais parceiros, que é o recorte que mais custa. A `decisao` (H83) lê uma previsão por parceiro e um plano de 30 ações **postos à mão** pela medição, e não pelo modelo treinado: o que se mede é a consulta sobre uma tabela de previsões do tamanho da rede, e os valores dela não significam nada.

## Como reproduzir

```bash
api/.venv/Scripts/python scripts/medir_painel.py --parceiros 10000 --periodos 12 --semente 42 --relatorio docs/medicoes/painel-10000.md
```

## Resultado

| Consulta | Chamadas | Mediana | p95 | Dispersão | Resposta | Dentro de 2 s |
|---|--:|--:|--:|--:|--:|:--:|
| `indicadores` | 286 | 17.8 ms | 22.1 ms | 24% | 398 B | sim |
| `ranking-25` | 119 | 42.7 ms | 49.7 ms | 16% | 6 kB | sim |
| `ranking-200` | 124 | 45.8 ms | 52.6 ms | 15% | 47 kB | sim |
| `serie` | 202 | 30.5 ms | 32.0 ms | 5% | 2 kB | sim |
| `segmentos` | 300 | 8.0 ms | 8.9 ms | 11% | 297 B | sim |
| `mobilidade` | 188 | 31.5 ms | 36.9 ms | 17% | 517 B | sim |
| `indicadores-categoria` | 255 | 22.1 ms | 25.4 ms | 15% | 434 B | sim |
| `ranking-categoria` | 150 | 46.8 ms | 56.9 ms | 22% | 6 kB | sim |
| `serie-categoria` | 268 | 20.8 ms | 22.4 ms | 7% | 2 kB | sim |
| `segmentos-categoria` | 300 | 10.5 ms | 11.9 ms | 12% | 330 B | sim |
| `decisao` | 197 | 29.3 ms | 33.0 ms | 13% | 1 kB | sim |
| `relatorio-desempenho` | 125 | 46.7 ms | 52.2 ms | 12% | 3 kB | sim |
| `relatorio-risco` | 92 | 62.1 ms | 70.1 ms | 13% | 13 kB | sim |
| `relatorio-campanha` | 300 | 12.2 ms | 13.9 ms | 14% | 2 kB | sim |
| `busca` | 284 | 17.5 ms | 20.1 ms | 15% | 18 kB | sim |
| `lista-completa` | 300 | 18.3 ms | 20.4 ms | 11% | 17 kB | sim |

A dispersão é o quanto o p95 se afasta da mediana. Vai junto de propósito: um número só de tempo esconde a variação, e foi exatamente isso que enganou a equipe na validação do toolchain (H47).

## O que cada consulta faz

- **`indicadores`** — `GET /api/painel/indicadores` · Faturamento, pedidos, ticket e ativos do período, com variação (H30).
- **`ranking-25`** — `GET /api/painel/ranking?tamanho=25` · A página que o painel pede ao abrir (H31).
- **`ranking-200`** — `GET /api/painel/ranking?tamanho=200` · A maior página que a API aceita — o pior caso do ranking.
- **`serie`** — `GET /api/painel/series` · Série histórica da rede (H32).
- **`segmentos`** — `GET /api/painel/segmentos` · Distribuição por segmento do período (H33).
- **`mobilidade`** — `GET /api/painel/mobilidade` · Quem entrou e quem saiu do Top N (H35).
- **`indicadores-categoria`** — `GET /api/painel/indicadores?categoria_id=1` · Os indicadores no recorte de uma categoria (H82).
- **`ranking-categoria`** — `GET /api/painel/ranking?tamanho=25&categoria_id=1` · O ranking da categoria, com a posição da rede inteira (H82, RN02).
- **`serie-categoria`** — `GET /api/painel/series?categoria_id=1` · A série histórica da categoria (H82).
- **`segmentos-categoria`** — `GET /api/painel/segmentos?categoria_id=1` · A distribuição por segmento da categoria (H82).
- **`decisao`** — `GET /api/painel/decisao` · A previsão e a campanha no painel, com uma previsão por parceiro (H83).
- **`relatorio-desempenho`** — `GET /api/relatorios/desempenho` · O desempenho do período por categoria e por segmento (H84).
- **`relatorio-risco`** — `GET /api/relatorios/risco` · A primeira página do relatório de risco, com o resumo do recorte (H85).
- **`relatorio-campanha`** — `GET /api/relatorios/campanha` · O último plano por ação, por categoria e por segmento (H86).
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
  - tempo no banco: **3.19 ms** · varredura: nenhuma
- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo WHERE periodo.data_inicio < %(data_inic…`
  - tempo no banco: **0.02 ms** · varredura: `periodo`
- `SELECT count(*) AS count_1, count(*) FILTER (WHERE historico_segmento.segmento = %(segmento_1)s) AS anon_1 FR…`
  - tempo no banco: **0.94 ms** · varredura: nenhuma

<details><summary>Plano completo</summary>

```
Limit  (cost=1.18..1.18 rows=1 width=12) (actual time=0.016..0.017 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.18..1.21 rows=12 width=12) (actual time=0.015..0.015 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.007..0.008 rows=12 loops=1)
              Buffers: shared hit=1
Planning Time: 0.076 ms
Execution Time: 0.040 ms
```

</details>

<details><summary>Plano completo</summary>

```
Aggregate  (cost=1431.73..1431.74 rows=1 width=48) (actual time=3.124..3.125 rows=1 loops=1)
  Buffers: shared hit=1005
  ->  Bitmap Heap Scan on metrica  (cost=275.91..1358.67 rows=9741 width=11) (actual time=0.557..2.197 rows=10000 loops=1)
        Recheck Cond: (periodo_id = 12)
        Heap Blocks: exact=961
        Buffers: shared hit=1005
        ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..273.48 rows=9741 width=0) (actual time=0.475..0.476 rows=10000 loops=1)
              Index Cond: (periodo_id = 12)
              Buffers: shared hit=44
Planning Time: 0.078 ms
Execution Time: 3.192 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=1.20..1.21 rows=1 width=12) (actual time=0.010..0.010 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.20..1.23 rows=11 width=12) (actual time=0.009..0.009 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.15 rows=11 width=12) (actual time=0.004..0.005 rows=11 loops=1)
              Filter: (data_inicio < '2026-09-21'::date)
              Rows Removed by Filter: 1
              Buffers: shared hit=1
Planning:
  Buffers: shared hit=2
Planning Time: 0.089 ms
Execution Time: 0.022 ms
```

</details>

<details><summary>Plano completo</summary>

```
Aggregate  (cost=303.02..303.03 rows=1 width=16) (actual time=0.894..0.894 rows=1 loops=1)
  Buffers: shared hit=14
  ->  Index Only Scan using ix_segmento_periodo_segmento on historico_segmento  (cost=0.29..226.60 rows=10189 width=4) (actual time=0.053..0.507 rows=10000 loops=1)
        Index Cond: (periodo_id = 12)
        Heap Fetches: 104
        Buffers: shared hit=14
Planning Time: 0.054 ms
Execution Time: 0.941 ms
```

</details>

### `ranking-25`

A consulta filtra `metrica`. Se o planejador varrer, a conferência abaixo diz se foi escolha dele ou falta de índice.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo ORDER BY periodo.data_inicio DESC, peri…`
  - tempo no banco: **0.05 ms** · varredura: `periodo`
- `SELECT count(*) AS count_1 FROM (SELECT metrica.parceiro_id AS parceiro_id, metrica.faturamento AS faturament…`
  - tempo no banco: **5.87 ms** · varredura: `parceiro`
- `SELECT atual.parceiro_id, atual.faturamento, atual.pedidos, atual.posicao, parceiro.nome, categoria.nome AS n…`
  - tempo no banco: **18.26 ms** · varredura: `categoria`, `parceiro`
- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo WHERE periodo.data_inicio < %(data_inic…`
  - tempo no banco: **0.03 ms** · varredura: `periodo`
- `SELECT anterior.parceiro_id, anterior.posicao, anterior.faturamento FROM (SELECT metrica.parceiro_id AS parce…`
  - tempo no banco: **10.82 ms** · varredura: `parceiro`

<details><summary>Plano completo</summary>

```
Limit  (cost=1.18..1.18 rows=1 width=12) (actual time=0.026..0.027 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.18..1.21 rows=12 width=12) (actual time=0.026..0.026 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.004..0.005 rows=12 loops=1)
              Buffers: shared hit=1
Planning Time: 0.036 ms
Execution Time: 0.046 ms
```

</details>

<details><summary>Plano completo</summary>

```
Aggregate  (cost=1862.02..1862.03 rows=1 width=8) (actual time=5.629..5.630 rows=1 loops=1)
  Buffers: shared hit=1136
  ->  Hash Join  (cost=631.91..1740.25 rows=9741 width=40) (actual time=2.578..5.272 rows=10000 loops=1)
        Hash Cond: (metrica.parceiro_id = parceiro.id)
        Buffers: shared hit=1136
        ->  Bitmap Heap Scan on metrica  (cost=275.91..1358.67 rows=9741 width=11) (actual time=0.610..1.754 rows=10000 loops=1)
              Recheck Cond: (periodo_id = 12)
              Heap Blocks: exact=961
              Buffers: shared hit=1005
              ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..273.48 rows=9741 width=0) (actual time=0.527..0.527 rows=10000 loops=1)
                    Index Cond: (periodo_id = 12)
                    Buffers: shared hit=44
        ->  Hash  (cost=231.00..231.00 rows=10000 width=21) (actual time=1.907..1.907 rows=10000 loops=1)
              Buckets: 16384  Batches: 1  Memory Usage: 668kB
              Buffers: shared hit=131
              ->  Seq Scan on parceiro  (cost=0.00..231.00 rows=10000 width=21) (actual time=0.003..0.619 rows=10000 loops=1)
                    Buffers: shared hit=131
Planning:
  Buffers: shared hit=12
Planning Time: 0.239 ms
Execution Time: 5.867 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=4514.06..4514.13 rows=25 width=54) (actual time=17.629..17.633 rows=25 loops=1)
  Buffers: shared hit=1345
  ->  Sort  (cost=4514.06..4539.53 rows=10187 width=54) (actual time=17.628..17.631 rows=25 loops=1)
        Sort Key: (row_number() OVER (?))
        Sort Method: top-N heapsort  Memory: 28kB
        Buffers: shared hit=1345
        ->  Hash Left Join  (cost=3846.80..4226.59 rows=10187 width=54) (actual time=10.795..16.412 rows=10000 loops=1)
              Hash Cond: (metrica.parceiro_id = historico_segmento.parceiro_id)
              Buffers: shared hit=1345
              ->  Hash Left Join  (cost=2742.81..3097.03 rows=9741 width=50) (actual time=9.015..13.420 rows=10000 loops=1)
                    Hash Cond: (parceiro.categoria_id = categoria.id)
                    Buffers: shared hit=1268
                    ->  Hash Join  (cost=2741.59..3059.40 rows=9741 width=44) (actual time=8.987..12.362 rows=10000 loops=1)
                          Hash Cond: (metrica.parceiro_id = parceiro.id)
                          Buffers: shared hit=1267
                          ->  WindowAgg  (cost=2385.59..2580.41 rows=9741 width=40) (actual time=7.071..9.000 rows=10000 loops=1)
                                Buffers: shared hit=1136
                                ->  Sort  (cost=2385.59..2409.94 rows=9741 width=32) (actual time=7.063..7.461 rows=10000 loops=1)
                                      Sort Key: metrica.faturamento DESC, parceiro_1.nome
                                      Sort Method: quicksort  Memory: 978kB
                                      Buffers: shared hit=1136
                                      ->  Hash Join  (cost=631.91..1740.25 rows=9741 width=32) (actual time=2.251..4.612 rows=10000 loops=1)
                                            Hash Cond: (metrica.parceiro_id = parceiro_1.id)
                                            Buffers: shared hit=1136
                                            ->  Bitmap Heap Scan on metrica  (cost=275.91..1358.67 rows=9741 width=15) (actual time=0.489..1.540 rows=10000 loops=1)
                                                  Recheck Cond: (periodo_id = 12)
                                                  Heap Blocks: exact=961
                                                  Buffers: shared hit=1005
                                                  ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..273.48 rows=9741 width=0) (actual time=0.416..0.416 rows=10000 loops=1)
                                                        Index Cond: (periodo_id = 12)
                                                        Buffers: shared hit=44
                                            ->  Hash  (cost=231.00..231.00 rows=10000 width=21) (actual time=1.697..1.697 rows=10000 loops=1)
                                                  Buckets: 16384  Batches: 1  Memory Usage: 668kB
                                                  Buffers: shared hit=131
                                                  ->  Seq Scan on parceiro parceiro_1  (cost=0.00..231.00 rows=10000 width=21) (actual time=0.004..0.540 rows=10000 loops=1)
                                                        Buffers: shared hit=131
                          ->  Hash  (cost=231.00..231.00 rows=10000 width=25) (actual time=1.837..1.837 rows=10000 loops=1)
                                Buckets: 16384  Batches: 1  Memory Usage: 707kB
                                Buffers: shared hit=131
                                ->  Seq Scan on parceiro  (cost=0.00..231.00 rows=10000 width=25) (actual time=0.003..0.604 rows=10000 loops=1)
                                      Buffers: shared hit=131
                    ->  Hash  (cost=1.10..1.10 rows=10 width=14) (actual time=0.016..0.016 rows=10 loops=1)
                          Buckets: 1024  Batches: 1  Memory Usage: 9kB
                          Buffers: shared hit=1
                          ->  Seq Scan on categoria  (cost=0.00..1.10 rows=10 width=14) (actual time=0.004..0.005 rows=10 loops=1)
                                Buffers: shared hit=1
              ->  Hash  (cost=976.62..976.62 rows=10189 width=8) (actual time=1.715..1.715 rows=10000 loops=1)
                    Buckets: 16384  Batches: 1  Memory Usage: 519kB
                    Buffers: shared hit=77
                    ->  Bitmap Heap Scan on historico_segmento  (cost=123.26..976.62 rows=10189 width=8) (actual time=0.130..0.754 rows=10000 loops=1)
                          Recheck Cond: (periodo_id = 12)
                          Heap Blocks: exact=65
                          Buffers: shared hit=77
                          ->  Bitmap Index Scan on ix_segmento_periodo_segmento  (cost=0.00..120.71 rows=10189 width=0) (actual time=0.125..0.125 rows=10000 loops=1)
                                Index Cond: (periodo_id = 12)
                                Buffers: shared hit=12
Planning:
  Buffers: shared hit=31
Planning Time: 0.644 ms
Execution Time: 18.256 ms
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
              Filter: (data_inicio < '2026-09-21'::date)
              Rows Removed by Filter: 1
              Buffers: shared hit=1
Planning:
  Buffers: shared hit=2
Planning Time: 0.083 ms
Execution Time: 0.032 ms
```

</details>

<details><summary>Plano completo</summary>

```
Subquery Scan on anterior  (cost=2406.52..2753.58 rows=26 width=19) (actual time=8.170..10.539 rows=25 loops=1)
  Filter: (anterior.parceiro_id = ANY ('{4133,2118,4648,8156,1577,2384,2515,6266,1682,6144,4544,3134,4101,4155,3997,924,3103,246,5834,8777,4254,6210,3194,9809,460}'::integer[]))
  Rows Removed by Filter: 9791
  Buffers: shared hit=1145
  ->  WindowAgg  (cost=2406.46..2604.78 rows=9916 width=40) (actual time=8.167..10.023 rows=9816 loops=1)
        Buffers: shared hit=1145
        ->  Sort  (cost=2406.46..2431.25 rows=9916 width=28) (actual time=8.156..8.547 rows=9816 loops=1)
              Sort Key: metrica.faturamento DESC, parceiro.nome
              Sort Method: quicksort  Memory: 921kB
              Buffers: shared hit=1145
              ->  Hash Join  (cost=637.27..1748.26 rows=9916 width=28) (actual time=2.953..5.646 rows=9816 loops=1)
                    Hash Cond: (metrica.parceiro_id = parceiro.id)
                    Buffers: shared hit=1145
                    ->  Bitmap Heap Scan on metrica  (cost=281.27..1366.22 rows=9916 width=11) (actual time=0.553..1.819 rows=9816 loops=1)
                          Recheck Cond: (periodo_id = 11)
                          Heap Blocks: exact=961
                          Buffers: shared hit=1014
                          ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..278.79 rows=9916 width=0) (actual time=0.475..0.476 rows=9816 loops=1)
                                Index Cond: (periodo_id = 11)
                                Buffers: shared hit=53
                    ->  Hash  (cost=231.00..231.00 rows=10000 width=21) (actual time=2.322..2.322 rows=10000 loops=1)
                          Buckets: 16384  Batches: 1  Memory Usage: 668kB
                          Buffers: shared hit=131
                          ->  Seq Scan on parceiro  (cost=0.00..231.00 rows=10000 width=21) (actual time=0.004..0.772 rows=10000 loops=1)
                                Buffers: shared hit=131
Planning:
  Buffers: shared hit=12
Planning Time: 0.275 ms
Execution Time: 10.819 ms
```

</details>

### `ranking-200`

A consulta filtra `metrica`. Se o planejador varrer, a conferência abaixo diz se foi escolha dele ou falta de índice.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo ORDER BY periodo.data_inicio DESC, peri…`
  - tempo no banco: **0.04 ms** · varredura: `periodo`
- `SELECT count(*) AS count_1 FROM (SELECT metrica.parceiro_id AS parceiro_id, metrica.faturamento AS faturament…`
  - tempo no banco: **6.19 ms** · varredura: `parceiro`
- `SELECT atual.parceiro_id, atual.faturamento, atual.pedidos, atual.posicao, parceiro.nome, categoria.nome AS n…`
  - tempo no banco: **19.27 ms** · varredura: `categoria`, `parceiro`
- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo WHERE periodo.data_inicio < %(data_inic…`
  - tempo no banco: **0.03 ms** · varredura: `periodo`
- `SELECT anterior.parceiro_id, anterior.posicao, anterior.faturamento FROM (SELECT metrica.parceiro_id AS parce…`
  - tempo no banco: **9.86 ms** · varredura: `parceiro`

<details><summary>Plano completo</summary>

```
Limit  (cost=1.18..1.18 rows=1 width=12) (actual time=0.021..0.021 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.18..1.21 rows=12 width=12) (actual time=0.020..0.020 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.005..0.006 rows=12 loops=1)
              Buffers: shared hit=1
Planning Time: 0.052 ms
Execution Time: 0.043 ms
```

</details>

<details><summary>Plano completo</summary>

```
Aggregate  (cost=1862.02..1862.03 rows=1 width=8) (actual time=5.772..5.773 rows=1 loops=1)
  Buffers: shared hit=1136
  ->  Hash Join  (cost=631.91..1740.25 rows=9741 width=40) (actual time=2.828..5.426 rows=10000 loops=1)
        Hash Cond: (metrica.parceiro_id = parceiro.id)
        Buffers: shared hit=1136
        ->  Bitmap Heap Scan on metrica  (cost=275.91..1358.67 rows=9741 width=11) (actual time=0.624..1.769 rows=10000 loops=1)
              Recheck Cond: (periodo_id = 12)
              Heap Blocks: exact=961
              Buffers: shared hit=1005
              ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..273.48 rows=9741 width=0) (actual time=0.539..0.539 rows=10000 loops=1)
                    Index Cond: (periodo_id = 12)
                    Buffers: shared hit=44
        ->  Hash  (cost=231.00..231.00 rows=10000 width=21) (actual time=2.123..2.123 rows=10000 loops=1)
              Buckets: 16384  Batches: 1  Memory Usage: 668kB
              Buffers: shared hit=131
              ->  Seq Scan on parceiro  (cost=0.00..231.00 rows=10000 width=21) (actual time=0.004..0.652 rows=10000 loops=1)
                    Buffers: shared hit=131
Planning:
  Buffers: shared hit=12
Planning Time: 0.241 ms
Execution Time: 6.190 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=4666.87..4667.37 rows=200 width=54) (actual time=18.598..18.616 rows=200 loops=1)
  Buffers: shared hit=1345
  ->  Sort  (cost=4666.87..4692.34 rows=10187 width=54) (actual time=18.597..18.605 rows=200 loops=1)
        Sort Key: (row_number() OVER (?))
        Sort Method: top-N heapsort  Memory: 51kB
        Buffers: shared hit=1345
        ->  Hash Left Join  (cost=3846.80..4226.59 rows=10187 width=54) (actual time=11.361..17.356 rows=10000 loops=1)
              Hash Cond: (metrica.parceiro_id = historico_segmento.parceiro_id)
              Buffers: shared hit=1345
              ->  Hash Left Join  (cost=2742.81..3097.03 rows=9741 width=50) (actual time=9.536..14.285 rows=10000 loops=1)
                    Hash Cond: (parceiro.categoria_id = categoria.id)
                    Buffers: shared hit=1268
                    ->  Hash Join  (cost=2741.59..3059.40 rows=9741 width=44) (actual time=9.511..13.182 rows=10000 loops=1)
                          Hash Cond: (metrica.parceiro_id = parceiro.id)
                          Buffers: shared hit=1267
                          ->  WindowAgg  (cost=2385.59..2580.41 rows=9741 width=40) (actual time=7.413..9.417 rows=10000 loops=1)
                                Buffers: shared hit=1136
                                ->  Sort  (cost=2385.59..2409.94 rows=9741 width=32) (actual time=7.406..7.773 rows=10000 loops=1)
                                      Sort Key: metrica.faturamento DESC, parceiro_1.nome
                                      Sort Method: quicksort  Memory: 978kB
                                      Buffers: shared hit=1136
                                      ->  Hash Join  (cost=631.91..1740.25 rows=9741 width=32) (actual time=2.298..4.944 rows=10000 loops=1)
                                            Hash Cond: (metrica.parceiro_id = parceiro_1.id)
                                            Buffers: shared hit=1136
                                            ->  Bitmap Heap Scan on metrica  (cost=275.91..1358.67 rows=9741 width=15) (actual time=0.565..1.818 rows=10000 loops=1)
                                                  Recheck Cond: (periodo_id = 12)
                                                  Heap Blocks: exact=961
                                                  Buffers: shared hit=1005
                                                  ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..273.48 rows=9741 width=0) (actual time=0.488..0.489 rows=10000 loops=1)
                                                        Index Cond: (periodo_id = 12)
                                                        Buffers: shared hit=44
                                            ->  Hash  (cost=231.00..231.00 rows=10000 width=21) (actual time=1.664..1.664 rows=10000 loops=1)
                                                  Buckets: 16384  Batches: 1  Memory Usage: 668kB
                                                  Buffers: shared hit=131
                                                  ->  Seq Scan on parceiro parceiro_1  (cost=0.00..231.00 rows=10000 width=21) (actual time=0.002..0.515 rows=10000 loops=1)
                                                        Buffers: shared hit=131
                          ->  Hash  (cost=231.00..231.00 rows=10000 width=25) (actual time=2.018..2.018 rows=10000 loops=1)
                                Buckets: 16384  Batches: 1  Memory Usage: 707kB
                                Buffers: shared hit=131
                                ->  Seq Scan on parceiro  (cost=0.00..231.00 rows=10000 width=25) (actual time=0.055..0.677 rows=10000 loops=1)
                                      Buffers: shared hit=131
                    ->  Hash  (cost=1.10..1.10 rows=10 width=14) (actual time=0.014..0.015 rows=10 loops=1)
                          Buckets: 1024  Batches: 1  Memory Usage: 9kB
                          Buffers: shared hit=1
                          ->  Seq Scan on categoria  (cost=0.00..1.10 rows=10 width=14) (actual time=0.004..0.005 rows=10 loops=1)
                                Buffers: shared hit=1
              ->  Hash  (cost=976.62..976.62 rows=10189 width=8) (actual time=1.756..1.757 rows=10000 loops=1)
                    Buckets: 16384  Batches: 1  Memory Usage: 519kB
                    Buffers: shared hit=77
                    ->  Bitmap Heap Scan on historico_segmento  (cost=123.26..976.62 rows=10189 width=8) (actual time=0.132..0.767 rows=10000 loops=1)
                          Recheck Cond: (periodo_id = 12)
                          Heap Blocks: exact=65
                          Buffers: shared hit=77
                          ->  Bitmap Index Scan on ix_segmento_periodo_segmento  (cost=0.00..120.71 rows=10189 width=0) (actual time=0.124..0.124 rows=10000 loops=1)
                                Index Cond: (periodo_id = 12)
                                Buffers: shared hit=12
Planning:
  Buffers: shared hit=31
Planning Time: 0.700 ms
Execution Time: 19.268 ms
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
        ->  Seq Scan on periodo  (cost=0.00..1.15 rows=11 width=12) (actual time=0.003..0.004 rows=11 loops=1)
              Filter: (data_inicio < '2026-09-21'::date)
              Rows Removed by Filter: 1
              Buffers: shared hit=1
Planning:
  Buffers: shared hit=2
Planning Time: 0.105 ms
Execution Time: 0.034 ms
```

</details>

<details><summary>Plano completo</summary>

```
Subquery Scan on anterior  (cost=2406.96..2754.02 rows=204 width=19) (actual time=7.263..9.588 rows=198 loops=1)
  Filter: (anterior.parceiro_id = ANY ('{4133,2118,4648,8156,1577,2384,2515,6266,1682,6144,4544,3134,4101,4155,3997,924,3103,246,5834,8777,4254,6210,3194,9809,460,2744,7117,6061,2272,1563,6700,8924,1823,2149,4982,5788,6772,5275,1917,4729,4468,9817,9927,1660,983,9656,2999,7128,2260,2864,4716,7651,9344,6952,4676,3721,7656,1936,5323,9527,9814,1307,7911,1242,9892,7384,3662,3453,8044,6606,3217,9490,5998,9104,3270,9386,5257,4885,7965,1395,9573,6999,7609,8553,7619,2311,6693,4654,2470,1793,3736,7033,9035,9142,7023,2314,600,8137,860,1019,181,8398,5022,9952,8365,5193,5315,4340,3133,2914,613,1348,6290,2666,3389,9534,9904,1393,2125,3621,2539,9030,8625,1382,2134,9094,2336,1067,1586,6956,7674,1265,6706,214,1896,7732,6511,9681,5609,6382,549,9248,9717,3415,484,381,6190,74,5690,3576,1754,6766,885,823,2044,2050,7320,7921,9332,9754,6518,5953,3090,6070,9481,1010,1825,9883,5897,2831,906,2980,2512,4890,2053,5946,6522,8519,4171,8839,1763,5865,6100,339,7794,8698,6222,7442,3461,9277,9949,2828,3384,6676,3273,9710,9165,3579,6677,2759}'::integer[]))
  Rows Removed by Filter: 9618
  Buffers: shared hit=1145
  ->  WindowAgg  (cost=2406.46..2604.78 rows=9916 width=40) (actual time=7.257..8.946 rows=9816 loops=1)
        Buffers: shared hit=1145
        ->  Sort  (cost=2406.46..2431.25 rows=9916 width=28) (actual time=7.249..7.580 rows=9816 loops=1)
              Sort Key: metrica.faturamento DESC, parceiro.nome
              Sort Method: quicksort  Memory: 921kB
              Buffers: shared hit=1145
              ->  Hash Join  (cost=637.27..1748.26 rows=9916 width=28) (actual time=2.329..4.931 rows=9816 loops=1)
                    Hash Cond: (metrica.parceiro_id = parceiro.id)
                    Buffers: shared hit=1145
                    ->  Bitmap Heap Scan on metrica  (cost=281.27..1366.22 rows=9916 width=11) (actual time=0.512..1.775 rows=9816 loops=1)
                          Recheck Cond: (periodo_id = 11)
                          Heap Blocks: exact=961
                          Buffers: shared hit=1014
                          ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..278.79 rows=9916 width=0) (actual time=0.437..0.437 rows=9816 loops=1)
                                Index Cond: (periodo_id = 11)
                                Buffers: shared hit=53
                    ->  Hash  (cost=231.00..231.00 rows=10000 width=21) (actual time=1.755..1.755 rows=10000 loops=1)
                          Buckets: 16384  Batches: 1  Memory Usage: 668kB
                          Buffers: shared hit=131
                          ->  Seq Scan on parceiro  (cost=0.00..231.00 rows=10000 width=21) (actual time=0.003..0.609 rows=10000 loops=1)
                                Buffers: shared hit=131
Planning:
  Buffers: shared hit=12
Planning Time: 0.381 ms
Execution Time: 9.860 ms
```

</details>

### `serie`

A série agrega **todos** os períodos: a consulta lê a tabela inteira por definição, e varrer é o plano certo.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim, sum(metrica.faturamento) AS sum_1, sum(metrica.pedi…`
  - tempo no banco: **31.54 ms** · varredura: `metrica`, `periodo`

<details><summary>Plano completo</summary>

```
Sort  (cost=3361.08..3361.11 rows=12 width=52) (actual time=31.494..31.496 rows=12 loops=1)
  Sort Key: periodo.data_inicio, periodo.id
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=962
  ->  HashAggregate  (cost=3360.71..3360.86 rows=12 width=52) (actual time=31.487..31.490 rows=12 loops=1)
        Group Key: periodo.id
        Batches: 1  Memory Usage: 24kB
        Buffers: shared hit=962
        ->  Hash Right Join  (cost=1.27..2506.24 rows=113929 width=23) (actual time=0.057..18.278 rows=113929 loops=1)
              Hash Cond: (metrica.periodo_id = periodo.id)
              Buffers: shared hit=962
              ->  Seq Scan on metrica  (cost=0.00..2100.29 rows=113929 width=15) (actual time=0.003..4.349 rows=113929 loops=1)
                    Buffers: shared hit=961
              ->  Hash  (cost=1.12..1.12 rows=12 width=12) (actual time=0.045..0.045 rows=12 loops=1)
                    Buckets: 1024  Batches: 1  Memory Usage: 9kB
                    Buffers: shared hit=1
                    ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.002..0.004 rows=12 loops=1)
                          Buffers: shared hit=1
Planning:
  Buffers: shared hit=4
Planning Time: 0.143 ms
Execution Time: 31.538 ms
```

</details>

### `segmentos`

A consulta filtra `historico_segmento`. Se o planejador varrer, a conferência abaixo diz se foi escolha dele ou falta de índice.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo ORDER BY periodo.data_inicio DESC, peri…`
  - tempo no banco: **0.01 ms** · varredura: `periodo`
- `SELECT historico_segmento.segmento, count(*) AS count_1 FROM historico_segmento WHERE historico_segmento.peri…`
  - tempo no banco: **0.95 ms** · varredura: nenhuma

<details><summary>Plano completo</summary>

```
Limit  (cost=1.18..1.18 rows=1 width=12) (actual time=0.006..0.007 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.18..1.21 rows=12 width=12) (actual time=0.006..0.006 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.002..0.003 rows=12 loops=1)
              Buffers: shared hit=1
Planning Time: 0.043 ms
Execution Time: 0.012 ms
```

</details>

<details><summary>Plano completo</summary>

```
Sort  (cost=277.65..277.67 rows=5 width=12) (actual time=0.922..0.922 rows=5 loops=1)
  Sort Key: (count(*)) DESC, segmento
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=14
  ->  GroupAggregate  (cost=0.29..277.60 rows=5 width=12) (actual time=0.073..0.920 rows=5 loops=1)
        Group Key: segmento
        Buffers: shared hit=14
        ->  Index Only Scan using ix_segmento_periodo_segmento on historico_segmento  (cost=0.29..226.60 rows=10189 width=4) (actual time=0.033..0.482 rows=10000 loops=1)
              Index Cond: (periodo_id = 12)
              Heap Fetches: 104
              Buffers: shared hit=14
Planning Time: 0.043 ms
Execution Time: 0.949 ms
```

</details>

### `mobilidade`

A consulta filtra `metrica`. Se o planejador varrer, a conferência abaixo diz se foi escolha dele ou falta de índice.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo ORDER BY periodo.data_inicio DESC, peri…`
  - tempo no banco: **0.02 ms** · varredura: `periodo`
- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo WHERE periodo.data_inicio < %(data_inic…`
  - tempo no banco: **0.01 ms** · varredura: `periodo`
- `SELECT coalesce(atual.parceiro_id, passado.parceiro_id) AS parceiro_id, parceiro.nome, atual.posicao AS posic…`
  - tempo no banco: **26.01 ms** · varredura: `parceiro`

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
Planning Time: 0.049 ms
Execution Time: 0.016 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=1.20..1.21 rows=1 width=12) (actual time=0.006..0.006 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.20..1.23 rows=11 width=12) (actual time=0.006..0.006 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.15 rows=11 width=12) (actual time=0.003..0.003 rows=11 loops=1)
              Filter: (data_inicio < '2026-09-21'::date)
              Rows Removed by Filter: 1
              Buffers: shared hit=1
Planning:
  Buffers: shared hit=2
Planning Time: 0.074 ms
Execution Time: 0.012 ms
```

</details>

<details><summary>Plano completo</summary>

```
Sort  (cost=6242.74..6248.01 rows=2110 width=45) (actual time=25.113..25.118 rows=4 loops=1)
  Sort Key: (COALESCE(atual.posicao, (row_number() OVER (?))))
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=2412
  ->  Hash Join  (cost=5562.04..6126.23 rows=2110 width=45) (actual time=21.601..25.109 rows=4 loops=1)
        Hash Cond: (COALESCE(atual.parceiro_id, metrica.parceiro_id) = parceiro.id)
        Buffers: shared hit=2412
        ->  Hash Full Join  (cost=5206.04..5764.69 rows=2110 width=24) (actual time=19.100..22.605 rows=4 loops=1)
              Hash Cond: (metrica.parceiro_id = atual.parceiro_id)
              Filter: (((atual.posicao <= 15) AND (((row_number() OVER (?)) IS NULL) OR ((row_number() OVER (?)) > 15))) OR (((row_number() OVER (?)) <= 15) AND ((atual.posicao IS NULL) OR (atual.posicao > 15))))
              Rows Removed by Filter: 9996
              Buffers: shared hit=2281
              ->  WindowAgg  (cost=2406.46..2604.78 rows=9916 width=40) (actual time=7.430..9.330 rows=9816 loops=1)
                    Buffers: shared hit=1145
                    ->  Sort  (cost=2406.46..2431.25 rows=9916 width=28) (actual time=7.420..7.968 rows=9816 loops=1)
                          Sort Key: metrica.faturamento DESC, parceiro_1.nome
                          Sort Method: quicksort  Memory: 921kB
                          Buffers: shared hit=1145
                          ->  Hash Join  (cost=637.27..1748.26 rows=9916 width=28) (actual time=2.303..5.012 rows=9816 loops=1)
                                Hash Cond: (metrica.parceiro_id = parceiro_1.id)
                                Buffers: shared hit=1145
                                ->  Bitmap Heap Scan on metrica  (cost=281.27..1366.22 rows=9916 width=11) (actual time=0.501..1.793 rows=9816 loops=1)
                                      Recheck Cond: (periodo_id = 11)
                                      Heap Blocks: exact=961
                                      Buffers: shared hit=1014
                                      ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..278.79 rows=9916 width=0) (actual time=0.426..0.426 rows=9816 loops=1)
                                            Index Cond: (periodo_id = 11)
                                            Buffers: shared hit=53
                                ->  Hash  (cost=231.00..231.00 rows=10000 width=21) (actual time=1.732..1.733 rows=10000 loops=1)
                                      Buckets: 16384  Batches: 1  Memory Usage: 668kB
                                      Buffers: shared hit=131
                                      ->  Seq Scan on parceiro parceiro_1  (cost=0.00..231.00 rows=10000 width=21) (actual time=0.006..0.573 rows=10000 loops=1)
                                            Buffers: shared hit=131
              ->  Hash  (cost=2677.82..2677.82 rows=9741 width=12) (actual time=11.562..11.565 rows=10000 loops=1)
                    Buckets: 16384  Batches: 1  Memory Usage: 597kB
                    Buffers: shared hit=1136
                    ->  Subquery Scan on atual  (cost=2385.59..2677.82 rows=9741 width=12) (actual time=7.813..10.395 rows=10000 loops=1)
                          Buffers: shared hit=1136
                          ->  WindowAgg  (cost=2385.59..2580.41 rows=9741 width=40) (actual time=7.812..9.802 rows=10000 loops=1)
                                Buffers: shared hit=1136
                                ->  Sort  (cost=2385.59..2409.94 rows=9741 width=28) (actual time=7.795..8.264 rows=10000 loops=1)
                                      Sort Key: metrica_1.faturamento DESC, parceiro_2.nome
                                      Sort Method: quicksort  Memory: 932kB
                                      Buffers: shared hit=1136
                                      ->  Hash Join  (cost=631.91..1740.25 rows=9741 width=28) (actual time=2.543..5.295 rows=10000 loops=1)
                                            Hash Cond: (metrica_1.parceiro_id = parceiro_2.id)
                                            Buffers: shared hit=1136
                                            ->  Bitmap Heap Scan on metrica metrica_1  (cost=275.91..1358.67 rows=9741 width=11) (actual time=0.573..1.922 rows=10000 loops=1)
                                                  Recheck Cond: (periodo_id = 12)
                                                  Heap Blocks: exact=961
                                                  Buffers: shared hit=1005
                                                  ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..273.48 rows=9741 width=0) (actual time=0.495..0.495 rows=10000 loops=1)
                                                        Index Cond: (periodo_id = 12)
                                                        Buffers: shared hit=44
                                            ->  Hash  (cost=231.00..231.00 rows=10000 width=21) (actual time=1.852..1.853 rows=10000 loops=1)
                                                  Buckets: 16384  Batches: 1  Memory Usage: 668kB
                                                  Buffers: shared hit=131
                                                  ->  Seq Scan on parceiro parceiro_2  (cost=0.00..231.00 rows=10000 width=21) (actual time=0.008..0.595 rows=10000 loops=1)
                                                        Buffers: shared hit=131
        ->  Hash  (cost=231.00..231.00 rows=10000 width=21) (actual time=2.420..2.420 rows=10000 loops=1)
              Buckets: 16384  Batches: 1  Memory Usage: 668kB
              Buffers: shared hit=131
              ->  Seq Scan on parceiro  (cost=0.00..231.00 rows=10000 width=21) (actual time=0.004..0.744 rows=10000 loops=1)
                    Buffers: shared hit=131
Planning:
  Buffers: shared hit=24
Planning Time: 0.593 ms
Execution Time: 26.014 ms
```

</details>

### `indicadores-categoria`

A consulta filtra `metrica`. Se o planejador varrer, a conferência abaixo diz se foi escolha dele ou falta de índice.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo ORDER BY periodo.data_inicio DESC, peri…`
  - tempo no banco: **0.01 ms** · varredura: `periodo`
- `SELECT coalesce(sum(metrica.faturamento), %(coalesce_2)s::INTEGER) AS coalesce_1, coalesce(sum(metrica.pedido…`
  - tempo no banco: **3.07 ms** · varredura: `parceiro`
- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo WHERE periodo.data_inicio < %(data_inic…`
  - tempo no banco: **0.01 ms** · varredura: `periodo`
- `SELECT count(*) AS count_1, count(*) FILTER (WHERE historico_segmento.segmento = %(segmento_1)s AND historico…`
  - tempo no banco: **2.03 ms** · varredura: `parceiro`

<details><summary>Plano completo</summary>

```
Limit  (cost=1.18..1.18 rows=1 width=12) (actual time=0.008..0.008 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.18..1.21 rows=12 width=12) (actual time=0.008..0.008 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.003..0.004 rows=12 loops=1)
              Buffers: shared hit=1
Planning Time: 0.037 ms
Execution Time: 0.015 ms
```

</details>

<details><summary>Plano completo</summary>

```
Aggregate  (cost=1684.90..1684.91 rows=1 width=48) (actual time=2.985..2.986 rows=1 loops=1)
  Buffers: shared hit=1136
  ->  Hash Join  (cost=560.09..1668.43 rows=2196 width=11) (actual time=1.145..2.825 rows=2254 loops=1)
        Hash Cond: (metrica.parceiro_id = parceiro.id)
        Buffers: shared hit=1136
        ->  Bitmap Heap Scan on metrica  (cost=275.91..1358.67 rows=9741 width=15) (actual time=0.536..1.444 rows=10000 loops=1)
              Recheck Cond: (periodo_id = 12)
              Heap Blocks: exact=961
              Buffers: shared hit=1005
              ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..273.48 rows=9741 width=0) (actual time=0.448..0.448 rows=10000 loops=1)
                    Index Cond: (periodo_id = 12)
                    Buffers: shared hit=44
        ->  Hash  (cost=256.00..256.00 rows=2254 width=4) (actual time=0.588..0.589 rows=2254 loops=1)
              Buckets: 4096  Batches: 1  Memory Usage: 112kB
              Buffers: shared hit=131
              ->  Seq Scan on parceiro  (cost=0.00..256.00 rows=2254 width=4) (actual time=0.003..0.391 rows=2254 loops=1)
                    Filter: (categoria_id = 1)
                    Rows Removed by Filter: 7746
                    Buffers: shared hit=131
Planning:
  Buffers: shared hit=12
Planning Time: 0.200 ms
Execution Time: 3.071 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=1.20..1.21 rows=1 width=12) (actual time=0.006..0.006 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.20..1.23 rows=11 width=12) (actual time=0.005..0.006 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.15 rows=11 width=12) (actual time=0.002..0.003 rows=11 loops=1)
              Filter: (data_inicio < '2026-09-21'::date)
              Rows Removed by Filter: 1
              Buffers: shared hit=1
Planning:
  Buffers: shared hit=2
Planning Time: 0.056 ms
Execution Time: 0.011 ms
```

</details>

<details><summary>Plano completo</summary>

```
Aggregate  (cost=1340.14..1340.15 rows=1 width=16) (actual time=1.945..1.946 rows=1 loops=1)
  Buffers: shared hit=208
  ->  Bitmap Heap Scan on historico_segmento  (cost=123.26..976.62 rows=10189 width=8) (actual time=0.115..0.594 rows=10000 loops=1)
        Recheck Cond: (periodo_id = 12)
        Heap Blocks: exact=65
        Buffers: shared hit=77
        ->  Bitmap Index Scan on ix_segmento_periodo_segmento  (cost=0.00..120.71 rows=10189 width=0) (actual time=0.108..0.108 rows=10000 loops=1)
              Index Cond: (periodo_id = 12)
              Buffers: shared hit=12
  SubPlan 1
    ->  Seq Scan on parceiro  (cost=0.00..256.00 rows=2254 width=4) (actual time=0.002..0.417 rows=2254 loops=1)
          Filter: (categoria_id = 1)
          Rows Removed by Filter: 7746
          Buffers: shared hit=131
Planning Time: 0.045 ms
Execution Time: 2.034 ms
```

</details>

### `ranking-categoria`

A consulta filtra `metrica`. Se o planejador varrer, a conferência abaixo diz se foi escolha dele ou falta de índice.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo ORDER BY periodo.data_inicio DESC, peri…`
  - tempo no banco: **0.03 ms** · varredura: `periodo`
- `SELECT count(*) AS count_1 FROM (SELECT metrica.parceiro_id AS parceiro_id, metrica.faturamento AS faturament…`
  - tempo no banco: **7.04 ms** · varredura: `parceiro`
- `SELECT atual.parceiro_id, atual.faturamento, atual.pedidos, atual.posicao, parceiro.nome, categoria.nome AS n…`
  - tempo no banco: **14.73 ms** · varredura: `categoria`, `parceiro`
- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo WHERE periodo.data_inicio < %(data_inic…`
  - tempo no banco: **0.03 ms** · varredura: `periodo`
- `SELECT anterior.parceiro_id, anterior.posicao, anterior.faturamento FROM (SELECT metrica.parceiro_id AS parce…`
  - tempo no banco: **10.82 ms** · varredura: `parceiro`

<details><summary>Plano completo</summary>

```
Limit  (cost=1.18..1.18 rows=1 width=12) (actual time=0.016..0.016 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.18..1.21 rows=12 width=12) (actual time=0.016..0.016 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.004..0.005 rows=12 loops=1)
              Buffers: shared hit=1
Planning Time: 0.041 ms
Execution Time: 0.034 ms
```

</details>

<details><summary>Plano completo</summary>

```
Aggregate  (cost=2152.91..2152.92 rows=1 width=8) (actual time=6.795..6.796 rows=1 loops=1)
  Buffers: shared hit=1267
  ->  Hash Join  (cost=916.09..2147.42 rows=2196 width=0) (actual time=3.074..6.715 rows=2254 loops=1)
        Hash Cond: (metrica.parceiro_id = parceiro.id)
        Buffers: shared hit=1267
        ->  Hash Join  (cost=631.91..1740.25 rows=9741 width=40) (actual time=2.333..5.194 rows=10000 loops=1)
              Hash Cond: (metrica.parceiro_id = parceiro_1.id)
              Buffers: shared hit=1136
              ->  Bitmap Heap Scan on metrica  (cost=275.91..1358.67 rows=9741 width=11) (actual time=0.533..1.733 rows=10000 loops=1)
                    Recheck Cond: (periodo_id = 12)
                    Heap Blocks: exact=961
                    Buffers: shared hit=1005
                    ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..273.48 rows=9741 width=0) (actual time=0.453..0.454 rows=10000 loops=1)
                          Index Cond: (periodo_id = 12)
                          Buffers: shared hit=44
              ->  Hash  (cost=231.00..231.00 rows=10000 width=21) (actual time=1.734..1.734 rows=10000 loops=1)
                    Buckets: 16384  Batches: 1  Memory Usage: 668kB
                    Buffers: shared hit=131
                    ->  Seq Scan on parceiro parceiro_1  (cost=0.00..231.00 rows=10000 width=21) (actual time=0.002..0.510 rows=10000 loops=1)
                          Buffers: shared hit=131
        ->  Hash  (cost=256.00..256.00 rows=2254 width=4) (actual time=0.720..0.720 rows=2254 loops=1)
              Buckets: 4096  Batches: 1  Memory Usage: 112kB
              Buffers: shared hit=131
              ->  Seq Scan on parceiro  (cost=0.00..256.00 rows=2254 width=4) (actual time=0.004..0.471 rows=2254 loops=1)
                    Filter: (categoria_id = 1)
                    Rows Removed by Filter: 7746
                    Buffers: shared hit=131
Planning:
  Buffers: shared hit=18
Planning Time: 0.478 ms
Execution Time: 7.044 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=4445.39..4445.46 rows=25 width=54) (actual time=14.199..14.207 rows=25 loops=1)
  Buffers: shared hit=1476
  ->  Sort  (cost=4445.39..4451.13 rows=2296 width=54) (actual time=14.199..14.205 rows=25 loops=1)
        Sort Key: (row_number() OVER (?))
        Sort Method: top-N heapsort  Memory: 30kB
        Buffers: shared hit=1476
        ->  Hash Right Join  (cost=3466.06..4380.60 rows=2296 width=54) (actual time=12.635..13.927 rows=2254 loops=1)
              Hash Cond: (historico_segmento.parceiro_id = metrica.parceiro_id)
              Buffers: shared hit=1476
              ->  Bitmap Heap Scan on historico_segmento  (cost=123.26..976.62 rows=10189 width=8) (actual time=0.133..0.612 rows=10000 loops=1)
                    Recheck Cond: (periodo_id = 12)
                    Heap Blocks: exact=65
                    Buffers: shared hit=77
                    ->  Bitmap Index Scan on ix_segmento_periodo_segmento  (cost=0.00..120.71 rows=10189 width=0) (actual time=0.127..0.128 rows=10000 loops=1)
                          Index Cond: (periodo_id = 12)
                          Buffers: shared hit=12
              ->  Hash  (cost=3315.36..3315.36 rows=2196 width=50) (actual time=12.475..12.481 rows=2254 loops=1)
                    Buckets: 4096  Batches: 1  Memory Usage: 223kB
                    Buffers: shared hit=1399
                    ->  Hash Left Join  (cost=2956.42..3315.36 rows=2196 width=50) (actual time=9.160..12.067 rows=2254 loops=1)
                          Hash Cond: (parceiro.categoria_id = categoria.id)
                          Buffers: shared hit=1399
                          ->  Hash Join  (cost=2955.20..3305.92 rows=2196 width=44) (actual time=9.132..11.786 rows=2254 loops=1)
                                Hash Cond: (metrica.parceiro_id = parceiro.id)
                                Buffers: shared hit=1398
                                ->  WindowAgg  (cost=2385.59..2580.41 rows=9741 width=40) (actual time=7.069..8.914 rows=10000 loops=1)
                                      Buffers: shared hit=1136
                                      ->  Sort  (cost=2385.59..2409.94 rows=9741 width=32) (actual time=7.060..7.498 rows=10000 loops=1)
                                            Sort Key: metrica.faturamento DESC, parceiro_2.nome
                                            Sort Method: quicksort  Memory: 978kB
                                            Buffers: shared hit=1136
                                            ->  Hash Join  (cost=631.91..1740.25 rows=9741 width=32) (actual time=2.211..4.584 rows=10000 loops=1)
                                                  Hash Cond: (metrica.parceiro_id = parceiro_2.id)
                                                  Buffers: shared hit=1136
                                                  ->  Bitmap Heap Scan on metrica  (cost=275.91..1358.67 rows=9741 width=15) (actual time=0.502..1.549 rows=10000 loops=1)
                                                        Recheck Cond: (periodo_id = 12)
                                                        Heap Blocks: exact=961
                                                        Buffers: shared hit=1005
                                                        ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..273.48 rows=9741 width=0) (actual time=0.426..0.426 rows=10000 loops=1)
                                                              Index Cond: (periodo_id = 12)
                                                              Buffers: shared hit=44
                                                  ->  Hash  (cost=231.00..231.00 rows=10000 width=21) (actual time=1.641..1.641 rows=10000 loops=1)
                                                        Buckets: 16384  Batches: 1  Memory Usage: 668kB
                                                        Buffers: shared hit=131
                                                        ->  Seq Scan on parceiro parceiro_2  (cost=0.00..231.00 rows=10000 width=21) (actual time=0.004..0.502 rows=10000 loops=1)
                                                              Buffers: shared hit=131
                                ->  Hash  (cost=541.44..541.44 rows=2254 width=29) (actual time=2.041..2.042 rows=2254 loops=1)
                                      Buckets: 4096  Batches: 1  Memory Usage: 172kB
                                      Buffers: shared hit=262
                                      ->  Hash Join  (cost=284.18..541.44 rows=2254 width=29) (actual time=0.684..1.751 rows=2254 loops=1)
                                            Hash Cond: (parceiro.id = parceiro_1.id)
                                            Buffers: shared hit=262
                                            ->  Seq Scan on parceiro  (cost=0.00..231.00 rows=10000 width=25) (actual time=0.002..0.355 rows=10000 loops=1)
                                                  Buffers: shared hit=131
                                            ->  Hash  (cost=256.00..256.00 rows=2254 width=4) (actual time=0.661..0.661 rows=2254 loops=1)
                                                  Buckets: 4096  Batches: 1  Memory Usage: 112kB
                                                  Buffers: shared hit=131
                                                  ->  Seq Scan on parceiro parceiro_1  (cost=0.00..256.00 rows=2254 width=4) (actual time=0.002..0.424 rows=2254 loops=1)
                                                        Filter: (categoria_id = 1)
                                                        Rows Removed by Filter: 7746
                                                        Buffers: shared hit=131
                          ->  Hash  (cost=1.10..1.10 rows=10 width=14) (actual time=0.012..0.012 rows=10 loops=1)
                                Buckets: 1024  Batches: 1  Memory Usage: 9kB
                                Buffers: shared hit=1
                                ->  Seq Scan on categoria  (cost=0.00..1.10 rows=10 width=14) (actual time=0.004..0.004 rows=10 loops=1)
                                      Buffers: shared hit=1
Planning:
  Buffers: shared hit=49
Planning Time: 1.255 ms
Execution Time: 14.732 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=1.20..1.21 rows=1 width=12) (actual time=0.017..0.017 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.20..1.23 rows=11 width=12) (actual time=0.016..0.017 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.15 rows=11 width=12) (actual time=0.003..0.004 rows=11 loops=1)
              Filter: (data_inicio < '2026-09-21'::date)
              Rows Removed by Filter: 1
              Buffers: shared hit=1
Planning:
  Buffers: shared hit=2
Planning Time: 0.106 ms
Execution Time: 0.033 ms
```

</details>

<details><summary>Plano completo</summary>

```
Subquery Scan on anterior  (cost=2406.52..2753.58 rows=26 width=19) (actual time=8.331..10.524 rows=24 loops=1)
  Filter: (anterior.parceiro_id = ANY ('{4133,4648,8156,2515,3134,3997,9809,460,2744,7117,6772,7651,9344,4676,3721,9527,9814,3453,5998,5257,1395,9035,600,5022,3133}'::integer[]))
  Rows Removed by Filter: 9792
  Buffers: shared hit=1145
  ->  WindowAgg  (cost=2406.46..2604.78 rows=9916 width=40) (actual time=8.328..10.038 rows=9816 loops=1)
        Buffers: shared hit=1145
        ->  Sort  (cost=2406.46..2431.25 rows=9916 width=28) (actual time=8.319..8.660 rows=9816 loops=1)
              Sort Key: metrica.faturamento DESC, parceiro.nome
              Sort Method: quicksort  Memory: 921kB
              Buffers: shared hit=1145
              ->  Hash Join  (cost=637.27..1748.26 rows=9916 width=28) (actual time=2.805..5.685 rows=9816 loops=1)
                    Hash Cond: (metrica.parceiro_id = parceiro.id)
                    Buffers: shared hit=1145
                    ->  Bitmap Heap Scan on metrica  (cost=281.27..1366.22 rows=9916 width=11) (actual time=0.526..1.816 rows=9816 loops=1)
                          Recheck Cond: (periodo_id = 11)
                          Heap Blocks: exact=961
                          Buffers: shared hit=1014
                          ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..278.79 rows=9916 width=0) (actual time=0.443..0.443 rows=9816 loops=1)
                                Index Cond: (periodo_id = 11)
                                Buffers: shared hit=53
                    ->  Hash  (cost=231.00..231.00 rows=10000 width=21) (actual time=2.191..2.191 rows=10000 loops=1)
                          Buckets: 16384  Batches: 1  Memory Usage: 668kB
                          Buffers: shared hit=131
                          ->  Seq Scan on parceiro  (cost=0.00..231.00 rows=10000 width=21) (actual time=0.004..0.718 rows=10000 loops=1)
                                Buffers: shared hit=131
Planning:
  Buffers: shared hit=12
Planning Time: 0.483 ms
Execution Time: 10.823 ms
```

</details>

### `serie-categoria`

Como a da rede: a série agrega todos os períodos, e a categoria só escolhe de quais parceiros.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim, sum(metrica.faturamento) AS sum_1, sum(metrica.pedi…`
  - tempo no banco: **18.80 ms** · varredura: `metrica`, `parceiro`, `periodo`

<details><summary>Plano completo</summary>

```
Sort  (cost=2969.10..2969.13 rows=12 width=52) (actual time=18.689..18.696 rows=12 loops=1)
  Sort Key: periodo.data_inicio, periodo.id
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=1093
  ->  HashAggregate  (cost=2968.74..2968.89 rows=12 width=52) (actual time=18.681..18.690 rows=12 loops=1)
        Group Key: periodo.id
        Batches: 1  Memory Usage: 24kB
        Buffers: shared hit=1093
        ->  Hash Right Join  (cost=285.44..2776.14 rows=25680 width=23) (actual time=0.920..15.510 rows=25611 loops=1)
              Hash Cond: (metrica.periodo_id = periodo.id)
              Buffers: shared hit=1093
              ->  Hash Join  (cost=284.18..2683.65 rows=25680 width=15) (actual time=0.888..12.727 rows=25611 loops=1)
                    Hash Cond: (metrica.parceiro_id = parceiro.id)
                    Buffers: shared hit=1092
                    ->  Seq Scan on metrica  (cost=0.00..2100.29 rows=113929 width=19) (actual time=0.002..4.359 rows=113929 loops=1)
                          Buffers: shared hit=961
                    ->  Hash  (cost=256.00..256.00 rows=2254 width=4) (actual time=0.860..0.860 rows=2254 loops=1)
                          Buckets: 4096  Batches: 1  Memory Usage: 112kB
                          Buffers: shared hit=131
                          ->  Seq Scan on parceiro  (cost=0.00..256.00 rows=2254 width=4) (actual time=0.003..0.556 rows=2254 loops=1)
                                Filter: (categoria_id = 1)
                                Rows Removed by Filter: 7746
                                Buffers: shared hit=131
              ->  Hash  (cost=1.12..1.12 rows=12 width=12) (actual time=0.020..0.026 rows=12 loops=1)
                    Buckets: 1024  Batches: 1  Memory Usage: 9kB
                    Buffers: shared hit=1
                    ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.003..0.004 rows=12 loops=1)
                          Buffers: shared hit=1
Planning:
  Buffers: shared hit=16
Planning Time: 0.361 ms
Execution Time: 18.797 ms
```

</details>

### `segmentos-categoria`

A consulta filtra `historico_segmento`. Se o planejador varrer, a conferência abaixo diz se foi escolha dele ou falta de índice.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo ORDER BY periodo.data_inicio DESC, peri…`
  - tempo no banco: **0.01 ms** · varredura: `periodo`
- `SELECT historico_segmento.segmento, count(*) AS count_1 FROM historico_segmento WHERE historico_segmento.peri…`
  - tempo no banco: **2.32 ms** · varredura: `parceiro`

<details><summary>Plano completo</summary>

```
Limit  (cost=1.18..1.18 rows=1 width=12) (actual time=0.007..0.007 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.18..1.21 rows=12 width=12) (actual time=0.006..0.006 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.003..0.004 rows=12 loops=1)
              Buffers: shared hit=1
Planning Time: 0.059 ms
Execution Time: 0.013 ms
```

</details>

<details><summary>Plano completo</summary>

```
Sort  (cost=1299.15..1299.16 rows=5 width=12) (actual time=2.222..2.223 rows=5 loops=1)
  Sort Key: (count(*)) DESC, historico_segmento.segmento
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=208
  ->  HashAggregate  (cost=1299.04..1299.09 rows=5 width=12) (actual time=2.219..2.220 rows=5 loops=1)
        Group Key: historico_segmento.segmento
        Batches: 1  Memory Usage: 24kB
        Buffers: shared hit=208
        ->  Hash Join  (cost=407.43..1287.55 rows=2297 width=4) (actual time=0.824..2.046 rows=2254 loops=1)
              Hash Cond: (historico_segmento.parceiro_id = parceiro.id)
              Buffers: shared hit=208
              ->  Bitmap Heap Scan on historico_segmento  (cost=123.26..976.62 rows=10189 width=8) (actual time=0.136..0.604 rows=10000 loops=1)
                    Recheck Cond: (periodo_id = 12)
                    Heap Blocks: exact=65
                    Buffers: shared hit=77
                    ->  Bitmap Index Scan on ix_segmento_periodo_segmento  (cost=0.00..120.71 rows=10189 width=0) (actual time=0.131..0.131 rows=10000 loops=1)
                          Index Cond: (periodo_id = 12)
                          Buffers: shared hit=12
              ->  Hash  (cost=256.00..256.00 rows=2254 width=4) (actual time=0.659..0.659 rows=2254 loops=1)
                    Buckets: 4096  Batches: 1  Memory Usage: 112kB
                    Buffers: shared hit=131
                    ->  Seq Scan on parceiro  (cost=0.00..256.00 rows=2254 width=4) (actual time=0.003..0.436 rows=2254 loops=1)
                          Filter: (categoria_id = 1)
                          Rows Removed by Filter: 7746
                          Buffers: shared hit=131
Planning:
  Buffers: shared hit=15
Planning Time: 0.245 ms
Execution Time: 2.316 ms
```

</details>

### `decisao`

A consulta filtra `previsao`. Se o planejador varrer, a conferência abaixo diz se foi escolha dele ou falta de índice.

- `SELECT periodo.id AS periodo_id, periodo.data_inicio AS periodo_data_inicio, periodo.data_fim AS periodo_data…`
  - tempo no banco: **0.01 ms** · varredura: `periodo`
- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo WHERE EXISTS (SELECT * FROM metrica WHE…`
  - tempo no banco: **0.11 ms** · varredura: `periodo`
- `SELECT count(*) AS count_1, sum(com_medido.faturamento_previsto) AS sum_1, sum(com_medido.medido) AS sum_2 FR…`
  - tempo no banco: **5.82 ms** · varredura: `previsao`
  - a varredura em `previsao` é **escolha do planejador**: com `enable_seqscan = off` o mesmo filtro usa `ix_metrica_periodo_faturamento`, `ix_previsao_periodo_versao` e leva 5.48 ms. O índice cobre a consulta.
- `SELECT com_medido.parceiro_id, parceiro.nome, categoria.nome AS nome_1, com_medido.probabilidade_queda, com_m…`
  - tempo no banco: **12.21 ms** · varredura: `categoria`, `parceiro`, `previsao`
  - a varredura em `previsao` é **escolha do planejador**: com `enable_seqscan = off` o mesmo filtro usa `categoria_pkey`, `ix_metrica_periodo_faturamento`, `ix_previsao_periodo_versao`, `parceiro_pkey` e leva 12.09 ms. O índice cobre a consulta.

<details><summary>Plano completo</summary>

```
Seq Scan on periodo  (cost=0.00..1.15 rows=1 width=12) (actual time=0.005..0.005 rows=1 loops=1)
  Filter: (id = 12)
  Rows Removed by Filter: 11
  Buffers: shared hit=1
Planning Time: 0.037 ms
Execution Time: 0.009 ms
```

</details>

<details><summary>Plano completo</summary>

```
Sort  (cost=7.33..7.36 rows=12 width=12) (actual time=0.089..0.089 rows=12 loops=1)
  Sort Key: periodo.data_inicio DESC, periodo.id DESC
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=38
  ->  Nested Loop Semi Join  (cost=0.42..7.12 rows=12 width=12) (actual time=0.020..0.085 rows=12 loops=1)
        Buffers: shared hit=38
        ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.002..0.003 rows=12 loops=1)
              Buffers: shared hit=1
        ->  Index Only Scan using ix_metrica_periodo_faturamento on metrica  (cost=0.42..296.56 rows=9494 width=4) (actual time=0.007..0.007 rows=1 loops=12)
              Index Cond: (periodo_id = periodo.id)
              Heap Fetches: 0
              Buffers: shared hit=37
Planning:
  Buffers: shared hit=8
Planning Time: 0.160 ms
Execution Time: 0.106 ms
```

</details>

<details><summary>Plano completo</summary>

```
Aggregate  (cost=1826.32..1826.33 rows=1 width=72) (actual time=5.648..5.648 rows=1 loops=1)
  Buffers: shared hit=1099
  ->  Hash Join  (cost=644.91..1753.25 rows=9741 width=14) (actual time=2.523..4.825 rows=10000 loops=1)
        Hash Cond: (metrica.parceiro_id = previsao.parceiro_id)
        Buffers: shared hit=1099
        ->  Bitmap Heap Scan on metrica  (cost=275.91..1358.67 rows=9741 width=11) (actual time=0.488..1.509 rows=10000 loops=1)
              Recheck Cond: (periodo_id = 12)
              Heap Blocks: exact=961
              Buffers: shared hit=1005
              ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..273.48 rows=9741 width=0) (actual time=0.405..0.405 rows=10000 loops=1)
                    Index Cond: (periodo_id = 12)
                    Buffers: shared hit=44
        ->  Hash  (cost=244.00..244.00 rows=10000 width=11) (actual time=1.970..1.970 rows=10000 loops=1)
              Buckets: 16384  Batches: 1  Memory Usage: 562kB
              Buffers: shared hit=94
              ->  Seq Scan on previsao  (cost=0.00..244.00 rows=10000 width=11) (actual time=0.004..0.910 rows=10000 loops=1)
                    Filter: ((periodo_base_id = 12) AND ((modelo_versao)::text = 'rede-1'::text))
                    Buffers: shared hit=94
Planning:
  Buffers: shared hit=12
Planning Time: 0.190 ms
Execution Time: 5.824 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=2334.26..2334.27 rows=5 width=53) (actual time=11.773..11.776 rows=5 loops=1)
  Buffers: shared hit=1231
  ->  Sort  (cost=2334.26..2358.61 rows=9741 width=53) (actual time=11.773..11.774 rows=5 loops=1)
        Sort Key: previsao.probabilidade_queda DESC, parceiro.nome
        Sort Method: top-N heapsort  Memory: 26kB
        Buffers: shared hit=1231
        ->  Hash Left Join  (cost=1002.14..2172.47 rows=9741 width=53) (actual time=5.301..10.600 rows=10000 loops=1)
              Hash Cond: (parceiro.categoria_id = categoria.id)
              Buffers: shared hit=1231
              ->  Hash Join  (cost=1000.91..2134.84 rows=9741 width=47) (actual time=5.273..9.553 rows=10000 loops=1)
                    Hash Cond: (metrica.parceiro_id = parceiro.id)
                    Buffers: shared hit=1230
                    ->  Hash Join  (cost=644.91..1753.25 rows=9741 width=30) (actual time=3.067..6.066 rows=10000 loops=1)
                          Hash Cond: (metrica.parceiro_id = previsao.parceiro_id)
                          Buffers: shared hit=1099
                          ->  Bitmap Heap Scan on metrica  (cost=275.91..1358.67 rows=9741 width=11) (actual time=0.550..2.065 rows=10000 loops=1)
                                Recheck Cond: (periodo_id = 12)
                                Heap Blocks: exact=961
                                Buffers: shared hit=1005
                                ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..273.48 rows=9741 width=0) (actual time=0.465..0.465 rows=10000 loops=1)
                                      Index Cond: (periodo_id = 12)
                                      Buffers: shared hit=44
                          ->  Hash  (cost=244.00..244.00 rows=10000 width=19) (actual time=2.441..2.442 rows=10000 loops=1)
                                Buckets: 16384  Batches: 1  Memory Usage: 667kB
                                Buffers: shared hit=94
                                ->  Seq Scan on previsao  (cost=0.00..244.00 rows=10000 width=19) (actual time=0.007..1.012 rows=10000 loops=1)
                                      Filter: ((periodo_base_id = 12) AND ((modelo_versao)::text = 'rede-1'::text))
                                      Buffers: shared hit=94
                    ->  Hash  (cost=231.00..231.00 rows=10000 width=25) (actual time=2.085..2.085 rows=10000 loops=1)
                          Buckets: 16384  Batches: 1  Memory Usage: 707kB
                          Buffers: shared hit=131
                          ->  Seq Scan on parceiro  (cost=0.00..231.00 rows=10000 width=25) (actual time=0.006..0.678 rows=10000 loops=1)
                                Buffers: shared hit=131
              ->  Hash  (cost=1.10..1.10 rows=10 width=14) (actual time=0.015..0.016 rows=10 loops=1)
                    Buckets: 1024  Batches: 1  Memory Usage: 9kB
                    Buffers: shared hit=1
                    ->  Seq Scan on categoria  (cost=0.00..1.10 rows=10 width=14) (actual time=0.004..0.005 rows=10 loops=1)
                          Buffers: shared hit=1
Planning:
  Buffers: shared hit=40
Planning Time: 1.042 ms
Execution Time: 12.214 ms
```

</details>

### `relatorio-desempenho`

A consulta filtra `metrica`. Se o planejador varrer, a conferência abaixo diz se foi escolha dele ou falta de índice.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo ORDER BY periodo.data_inicio DESC, peri…`
  - tempo no banco: **0.03 ms** · varredura: `periodo`
- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo WHERE periodo.data_inicio < %(data_inic…`
  - tempo no banco: **0.01 ms** · varredura: `periodo`
- `SELECT parceiro.categoria_id, count(*) AS count_1, sum(metrica.faturamento) AS sum_1, sum(metrica.pedidos) AS…`
  - tempo no banco: **5.92 ms** · varredura: `parceiro`
- `SELECT historico_segmento.segmento, count(*) AS count_1, sum(metrica.faturamento) AS sum_1, sum(metrica.pedid…`
  - tempo no banco: **9.20 ms** · varredura: `parceiro`
- `SELECT EXISTS (SELECT * FROM historico_segmento WHERE historico_segmento.periodo_id = %(periodo_id_1)s::INTEG…`
  - tempo no banco: **3.88 ms** · varredura: `historico_segmento`
- `SELECT historico_segmento.segmento, sum(metrica.faturamento) AS sum_1, sum(passado.antes) AS sum_2 FROM metri…`
  - tempo no banco: **14.00 ms** · varredura: `parceiro`

<details><summary>Plano completo</summary>

```
Sort  (cost=1.34..1.37 rows=12 width=12) (actual time=0.010..0.010 rows=12 loops=1)
  Sort Key: data_inicio DESC, id DESC
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=1
  ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.004..0.004 rows=12 loops=1)
        Buffers: shared hit=1
Planning Time: 0.047 ms
Execution Time: 0.034 ms
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
              Filter: (data_inicio < '2026-09-21'::date)
              Rows Removed by Filter: 1
              Buffers: shared hit=1
Planning:
  Buffers: shared hit=2
Planning Time: 0.064 ms
Execution Time: 0.012 ms
```

</details>

<details><summary>Plano completo</summary>

```
HashAggregate  (cost=1837.66..1837.79 rows=10 width=52) (actual time=5.750..5.753 rows=10 loops=1)
  Group Key: parceiro.categoria_id
  Batches: 1  Memory Usage: 24kB
  Buffers: shared hit=1136
  ->  Hash Join  (cost=631.91..1740.25 rows=9741 width=15) (actual time=2.213..4.572 rows=10000 loops=1)
        Hash Cond: (metrica.parceiro_id = parceiro.id)
        Buffers: shared hit=1136
        ->  Bitmap Heap Scan on metrica  (cost=275.91..1358.67 rows=9741 width=19) (actual time=0.501..1.566 rows=10000 loops=1)
              Recheck Cond: (periodo_id = 12)
              Heap Blocks: exact=961
              Buffers: shared hit=1005
              ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..273.48 rows=9741 width=0) (actual time=0.420..0.421 rows=10000 loops=1)
                    Index Cond: (periodo_id = 12)
                    Buffers: shared hit=44
        ->  Hash  (cost=231.00..231.00 rows=10000 width=8) (actual time=1.642..1.643 rows=10000 loops=1)
              Buckets: 16384  Batches: 1  Memory Usage: 519kB
              Buffers: shared hit=131
              ->  Seq Scan on parceiro  (cost=0.00..231.00 rows=10000 width=8) (actual time=0.003..0.627 rows=10000 loops=1)
                    Buffers: shared hit=131
Planning:
  Buffers: shared hit=12
Planning Time: 0.201 ms
Execution Time: 5.922 ms
```

</details>

<details><summary>Plano completo</summary>

```
HashAggregate  (cost=2971.69..2971.75 rows=5 width=52) (actual time=8.860..8.862 rows=5 loops=1)
  Group Key: historico_segmento.segmento
  Batches: 1  Memory Usage: 24kB
  Buffers: shared hit=1213
  ->  Hash Left Join  (cost=1735.89..2869.82 rows=10187 width=15) (actual time=4.056..7.660 rows=10000 loops=1)
        Hash Cond: (metrica.parceiro_id = historico_segmento.parceiro_id)
        Buffers: shared hit=1213
        ->  Hash Join  (cost=631.91..1740.25 rows=9741 width=19) (actual time=1.976..4.502 rows=10000 loops=1)
              Hash Cond: (metrica.parceiro_id = parceiro.id)
              Buffers: shared hit=1136
              ->  Bitmap Heap Scan on metrica  (cost=275.91..1358.67 rows=9741 width=19) (actual time=0.447..1.567 rows=10000 loops=1)
                    Recheck Cond: (periodo_id = 12)
                    Heap Blocks: exact=961
                    Buffers: shared hit=1005
                    ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..273.48 rows=9741 width=0) (actual time=0.366..0.367 rows=10000 loops=1)
                          Index Cond: (periodo_id = 12)
                          Buffers: shared hit=44
              ->  Hash  (cost=231.00..231.00 rows=10000 width=4) (actual time=1.453..1.453 rows=10000 loops=1)
                    Buckets: 16384  Batches: 1  Memory Usage: 480kB
                    Buffers: shared hit=131
                    ->  Seq Scan on parceiro  (cost=0.00..231.00 rows=10000 width=4) (actual time=0.003..0.498 rows=10000 loops=1)
                          Buffers: shared hit=131
        ->  Hash  (cost=976.62..976.62 rows=10189 width=12) (actual time=2.015..2.016 rows=10000 loops=1)
              Buckets: 16384  Batches: 1  Memory Usage: 558kB
              Buffers: shared hit=77
              ->  Bitmap Heap Scan on historico_segmento  (cost=123.26..976.62 rows=10189 width=12) (actual time=0.118..0.955 rows=10000 loops=1)
                    Recheck Cond: (periodo_id = 12)
                    Heap Blocks: exact=65
                    Buffers: shared hit=77
                    ->  Bitmap Index Scan on ix_segmento_periodo_segmento  (cost=0.00..120.71 rows=10189 width=0) (actual time=0.111..0.111 rows=10000 loops=1)
                          Index Cond: (periodo_id = 12)
                          Buffers: shared hit=12
Planning:
  Buffers: shared hit=27
Planning Time: 0.551 ms
Execution Time: 9.202 ms
```

</details>

<details><summary>Plano completo</summary>

```
Result  (cost=0.21..0.22 rows=1 width=1) (actual time=3.875..3.876 rows=1 loops=1)
  Buffers: shared hit=662
  InitPlan 1 (returns $0)
    ->  Seq Scan on historico_segmento  (cost=0.00..2150.11 rows=10189 width=0) (actual time=3.874..3.874 rows=1 loops=1)
          Filter: (periodo_id = 12)
          Rows Removed by Filter: 103929
          Buffers: shared hit=662
Planning Time: 0.040 ms
Execution Time: 3.881 ms
```

</details>

<details><summary>Plano completo</summary>

```
HashAggregate  (cost=4459.84..4459.91 rows=5 width=68) (actual time=13.466..13.469 rows=5 loops=1)
  Group Key: historico_segmento.segmento
  Batches: 1  Memory Usage: 24kB
  Buffers: shared hit=2227
  ->  Hash Left Join  (cost=3221.68..4384.08 rows=10101 width=18) (actual time=7.407..12.224 rows=9816 loops=1)
        Hash Cond: (metrica.parceiro_id = historico_segmento.parceiro_id)
        Buffers: shared hit=2227
        ->  Hash Join  (cost=2117.70..3254.73 rows=9659 width=22) (actual time=5.459..8.900 rows=9816 loops=1)
              Hash Cond: (parceiro.id = metrica.parceiro_id)
              Buffers: shared hit=2150
              ->  Hash Join  (cost=637.27..1748.26 rows=9916 width=15) (actual time=2.240..4.514 rows=9816 loops=1)
                    Hash Cond: (metrica_1.parceiro_id = parceiro.id)
                    Buffers: shared hit=1145
                    ->  Bitmap Heap Scan on metrica metrica_1  (cost=281.27..1366.22 rows=9916 width=11) (actual time=0.480..1.413 rows=9816 loops=1)
                          Recheck Cond: (periodo_id = 11)
                          Heap Blocks: exact=961
                          Buffers: shared hit=1014
                          ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..278.79 rows=9916 width=0) (actual time=0.399..0.399 rows=9816 loops=1)
                                Index Cond: (periodo_id = 11)
                                Buffers: shared hit=53
                    ->  Hash  (cost=231.00..231.00 rows=10000 width=4) (actual time=1.696..1.696 rows=10000 loops=1)
                          Buckets: 16384  Batches: 1  Memory Usage: 480kB
                          Buffers: shared hit=131
                          ->  Seq Scan on parceiro  (cost=0.00..231.00 rows=10000 width=4) (actual time=0.003..0.613 rows=10000 loops=1)
                                Buffers: shared hit=131
              ->  Hash  (cost=1358.67..1358.67 rows=9741 width=15) (actual time=3.147..3.147 rows=10000 loops=1)
                    Buckets: 16384  Batches: 1  Memory Usage: 601kB
                    Buffers: shared hit=1005
                    ->  Bitmap Heap Scan on metrica  (cost=275.91..1358.67 rows=9741 width=15) (actual time=0.488..1.798 rows=10000 loops=1)
                          Recheck Cond: (periodo_id = 12)
                          Heap Blocks: exact=961
                          Buffers: shared hit=1005
                          ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..273.48 rows=9741 width=0) (actual time=0.412..0.412 rows=10000 loops=1)
                                Index Cond: (periodo_id = 12)
                                Buffers: shared hit=44
        ->  Hash  (cost=976.62..976.62 rows=10189 width=12) (actual time=1.877..1.877 rows=10000 loops=1)
              Buckets: 16384  Batches: 1  Memory Usage: 558kB
              Buffers: shared hit=77
              ->  Bitmap Heap Scan on historico_segmento  (cost=123.26..976.62 rows=10189 width=12) (actual time=0.116..0.808 rows=10000 loops=1)
                    Recheck Cond: (periodo_id = 12)
                    Heap Blocks: exact=65
                    Buffers: shared hit=77
                    ->  Bitmap Index Scan on ix_segmento_periodo_segmento  (cost=0.00..120.71 rows=10189 width=0) (actual time=0.111..0.111 rows=10000 loops=1)
                          Index Cond: (periodo_id = 12)
                          Buffers: shared hit=12
Planning:
  Buffers: shared hit=51
Planning Time: 0.863 ms
Execution Time: 13.996 ms
```

</details>

### `relatorio-risco`

A consulta filtra `previsao`. Se o planejador varrer, a conferência abaixo diz se foi escolha dele ou falta de índice.

- `SELECT periodo.id AS periodo_id, periodo.data_inicio AS periodo_data_inicio, periodo.data_fim AS periodo_data…`
  - tempo no banco: **0.01 ms** · varredura: `periodo`
- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo WHERE EXISTS (SELECT * FROM metrica WHE…`
  - tempo no banco: **0.12 ms** · varredura: `periodo`
- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo WHERE periodo.data_inicio < %(data_inic…`
  - tempo no banco: **0.01 ms** · varredura: `periodo`
- `SELECT count(*) AS count_1, count(*) FILTER (WHERE recorte.probabilidade_queda IS NOT NULL) AS anon_1, sum(re…`
  - tempo no banco: **11.09 ms** · varredura: `acao_comercial`, `item_plano`, `parceiro`, `previsao`
  - a varredura em `previsao` é **escolha do planejador**: com `enable_seqscan = off` o mesmo filtro usa `acao_comercial_pkey`, `ix_metrica_periodo_faturamento`, `ix_previsao_periodo_versao`, `parceiro_pkey`, `uq_item_plano_parceiro` e leva 11.10 ms. O índice cobre a consulta.
- `SELECT parceiro.id, parceiro.nome, categoria.nome AS categoria, segmentado.segmento, metrica.faturamento, pas…`
  - tempo no banco: **52.10 ms** · varredura: `acao_comercial`, `categoria`, `item_plano`, `metrica`, `parceiro`, `periodo`, `previsao`
  - a varredura em `previsao` é **escolha do planejador**: com `enable_seqscan = off` o mesmo filtro usa `acao_comercial_pkey`, `categoria_pkey`, `ix_metrica_periodo_faturamento`, `ix_previsao_periodo_versao`, `ix_segmento_periodo_segmento`, `parceiro_pkey`, `periodo_pkey`, `uq_item_plano_parceiro`, `uq_metrica_parceiro_periodo` e leva 60.29 ms. O índice cobre a consulta.

<details><summary>Plano completo</summary>

```
Seq Scan on periodo  (cost=0.00..1.15 rows=1 width=12) (actual time=0.005..0.006 rows=1 loops=1)
  Filter: (id = 12)
  Rows Removed by Filter: 11
  Buffers: shared hit=1
Planning Time: 0.049 ms
Execution Time: 0.011 ms
```

</details>

<details><summary>Plano completo</summary>

```
Sort  (cost=7.33..7.36 rows=12 width=12) (actual time=0.099..0.100 rows=12 loops=1)
  Sort Key: periodo.data_inicio DESC, periodo.id DESC
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=38
  ->  Nested Loop Semi Join  (cost=0.42..7.12 rows=12 width=12) (actual time=0.022..0.091 rows=12 loops=1)
        Buffers: shared hit=38
        ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.002..0.003 rows=12 loops=1)
              Buffers: shared hit=1
        ->  Index Only Scan using ix_metrica_periodo_faturamento on metrica  (cost=0.42..296.56 rows=9494 width=4) (actual time=0.007..0.007 rows=1 loops=12)
              Index Cond: (periodo_id = periodo.id)
              Heap Fetches: 0
              Buffers: shared hit=37
Planning:
  Buffers: shared hit=8
Planning Time: 0.197 ms
Execution Time: 0.121 ms
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
        ->  Seq Scan on periodo  (cost=0.00..1.15 rows=11 width=12) (actual time=0.003..0.003 rows=11 loops=1)
              Filter: (data_inicio < '2026-09-21'::date)
              Rows Removed by Filter: 1
              Buffers: shared hit=1
Planning:
  Buffers: shared hit=2
Planning Time: 0.069 ms
Execution Time: 0.013 ms
```

</details>

<details><summary>Plano completo</summary>

```
Aggregate  (cost=2296.43..2296.44 rows=1 width=88) (actual time=10.682..10.684 rows=1 loops=1)
  Buffers: shared hit=1232
  ->  Hash Left Join  (cost=1003.92..2174.66 rows=9741 width=43) (actual time=4.913..9.677 rows=10000 loops=1)
        Hash Cond: (parceiro.id = item_plano.parceiro_id)
        Buffers: shared hit=1232
        ->  Hash Left Join  (cost=1000.91..2134.84 rows=9741 width=26) (actual time=4.869..8.761 rows=10000 loops=1)
              Hash Cond: (parceiro.id = previsao.parceiro_id)
              Buffers: shared hit=1230
              ->  Hash Join  (cost=631.91..1740.25 rows=9741 width=11) (actual time=2.421..5.110 rows=10000 loops=1)
                    Hash Cond: (metrica.parceiro_id = parceiro.id)
                    Buffers: shared hit=1136
                    ->  Bitmap Heap Scan on metrica  (cost=275.91..1358.67 rows=9741 width=11) (actual time=0.622..1.941 rows=10000 loops=1)
                          Recheck Cond: (periodo_id = 12)
                          Heap Blocks: exact=961
                          Buffers: shared hit=1005
                          ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..273.48 rows=9741 width=0) (actual time=0.545..0.545 rows=10000 loops=1)
                                Index Cond: (periodo_id = 12)
                                Buffers: shared hit=44
                    ->  Hash  (cost=231.00..231.00 rows=10000 width=8) (actual time=1.721..1.722 rows=10000 loops=1)
                          Buckets: 16384  Batches: 1  Memory Usage: 519kB
                          Buffers: shared hit=131
                          ->  Seq Scan on parceiro  (cost=0.00..231.00 rows=10000 width=8) (actual time=0.004..0.624 rows=10000 loops=1)
                                Buffers: shared hit=131
              ->  Hash  (cost=244.00..244.00 rows=10000 width=19) (actual time=2.346..2.346 rows=10000 loops=1)
                    Buckets: 16384  Batches: 1  Memory Usage: 640kB
                    Buffers: shared hit=94
                    ->  Seq Scan on previsao  (cost=0.00..244.00 rows=10000 width=19) (actual time=0.005..1.021 rows=10000 loops=1)
                          Filter: ((periodo_base_id = 12) AND ((modelo_versao)::text = 'rede-1'::text))
                          Buffers: shared hit=94
        ->  Hash  (cost=2.63..2.63 rows=30 width=25) (actual time=0.035..0.036 rows=30 loops=1)
              Buckets: 1024  Batches: 1  Memory Usage: 10kB
              Buffers: shared hit=2
              ->  Hash Join  (cost=1.11..2.63 rows=30 width=25) (actual time=0.023..0.028 rows=30 loops=1)
                    Hash Cond: (item_plano.acao_id = acao_comercial.id)
                    Buffers: shared hit=2
                    ->  Seq Scan on item_plano  (cost=0.00..1.38 rows=30 width=8) (actual time=0.003..0.005 rows=30 loops=1)
                          Filter: (plano_id = 1)
                          Buffers: shared hit=1
                    ->  Hash  (cost=1.05..1.05 rows=5 width=25) (actual time=0.008..0.009 rows=5 loops=1)
                          Buckets: 1024  Batches: 1  Memory Usage: 9kB
                          Buffers: shared hit=1
                          ->  Seq Scan on acao_comercial  (cost=0.00..1.05 rows=5 width=25) (actual time=0.002..0.002 rows=5 loops=1)
                                Buffers: shared hit=1
Planning:
  Buffers: shared hit=34
Planning Time: 0.823 ms
Execution Time: 11.091 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=8604.00..8604.13 rows=50 width=98) (actual time=50.956..50.969 rows=50 loops=1)
  Buffers: shared hit=3286
  ->  Sort  (cost=8604.00..8628.81 rows=9925 width=98) (actual time=50.955..50.965 rows=50 loops=1)
        Sort Key: previsao.probabilidade_queda DESC NULLS LAST, parceiro.nome
        Sort Method: top-N heapsort  Memory: 38kB
        Buffers: shared hit=3286
        ->  Hash Left Join  (cost=6986.38..8274.30 rows=9925 width=98) (actual time=37.921..49.243 rows=10000 loops=1)
              Hash Cond: (parceiro.id = item_plano.parceiro_id)
              Buffers: shared hit=3286
              ->  Hash Left Join  (cost=6983.37..8233.77 rows=9925 width=72) (actual time=37.869..48.218 rows=10000 loops=1)
                    Hash Cond: (parceiro.id = historico_segmento.parceiro_id)
                    Buffers: shared hit=3284
                    ->  Hash Left Join  (cost=5879.39..7104.21 rows=9741 width=68) (actual time=36.073..45.081 rows=10000 loops=1)
                          Hash Cond: (parceiro.id = historico.parceiro_id)
                          Buffers: shared hit=3207
                          ->  Hash Left Join  (cost=2487.93..3687.17 rows=9741 width=60) (actual time=8.099..15.534 rows=10000 loops=1)
                                Hash Cond: (parceiro.id = previsao.parceiro_id)
                                Buffers: shared hit=2245
                                ->  Hash Left Join  (cost=2118.93..3292.58 rows=9741 width=45) (actual time=5.944..11.807 rows=10000 loops=1)
                                      Hash Cond: (parceiro.categoria_id = categoria.id)
                                      Buffers: shared hit=2151
                                      ->  Hash Join  (cost=2117.70..3254.95 rows=9741 width=39) (actual time=5.921..10.679 rows=10000 loops=1)
                                            Hash Cond: (parceiro.id = metrica.parceiro_id)
                                            Buffers: shared hit=2150
                                            ->  Hash Right Join  (cost=637.27..1748.26 rows=10000 width=32) (actual time=2.695..5.902 rows=10000 loops=1)
                                                  Hash Cond: (metrica_1.parceiro_id = parceiro.id)
                                                  Buffers: shared hit=1145
                                                  ->  Bitmap Heap Scan on metrica metrica_1  (cost=281.27..1366.22 rows=9916 width=11) (actual time=0.545..1.861 rows=9816 loops=1)
                                                        Recheck Cond: (periodo_id = 11)
                                                        Heap Blocks: exact=961
                                                        Buffers: shared hit=1014
                                                        ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..278.79 rows=9916 width=0) (actual time=0.466..0.467 rows=9816 loops=1)
                                                              Index Cond: (periodo_id = 11)
                                                              Buffers: shared hit=53
                                                  ->  Hash  (cost=231.00..231.00 rows=10000 width=25) (actual time=2.084..2.084 rows=10000 loops=1)
                                                        Buckets: 16384  Batches: 1  Memory Usage: 707kB
                                                        Buffers: shared hit=131
                                                        ->  Seq Scan on parceiro  (cost=0.00..231.00 rows=10000 width=25) (actual time=0.004..0.657 rows=10000 loops=1)
                                                              Buffers: shared hit=131
                                            ->  Hash  (cost=1358.67..1358.67 rows=9741 width=11) (actual time=3.159..3.160 rows=10000 loops=1)
                                                  Buckets: 16384  Batches: 1  Memory Usage: 562kB
                                                  Buffers: shared hit=1005
                                                  ->  Bitmap Heap Scan on metrica  (cost=275.91..1358.67 rows=9741 width=11) (actual time=0.528..1.988 rows=10000 loops=1)
                                                        Recheck Cond: (periodo_id = 12)
                                                        Heap Blocks: exact=961
                                                        Buffers: shared hit=1005
                                                        ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..273.48 rows=9741 width=0) (actual time=0.454..0.455 rows=10000 loops=1)
                                                              Index Cond: (periodo_id = 12)
                                                              Buffers: shared hit=44
                                      ->  Hash  (cost=1.10..1.10 rows=10 width=14) (actual time=0.014..0.014 rows=10 loops=1)
                                            Buckets: 1024  Batches: 1  Memory Usage: 9kB
                                            Buffers: shared hit=1
                                            ->  Seq Scan on categoria  (cost=0.00..1.10 rows=10 width=14) (actual time=0.003..0.004 rows=10 loops=1)
                                                  Buffers: shared hit=1
                                ->  Hash  (cost=244.00..244.00 rows=10000 width=19) (actual time=2.090..2.090 rows=10000 loops=1)
                                      Buckets: 16384  Batches: 1  Memory Usage: 643kB
                                      Buffers: shared hit=94
                                      ->  Seq Scan on previsao  (cost=0.00..244.00 rows=10000 width=19) (actual time=0.004..0.955 rows=10000 loops=1)
                                            Filter: ((periodo_base_id = 12) AND ((modelo_versao)::text = 'rede-1'::text))
                                            Buffers: shared hit=94
                          ->  Hash  (cost=3270.10..3270.10 rows=9709 width=12) (actual time=27.904..27.906 rows=10000 loops=1)
                                Buckets: 16384  Batches: 1  Memory Usage: 558kB
                                Buffers: shared hit=962
                                ->  Subquery Scan on historico  (cost=3075.92..3270.10 rows=9709 width=12) (actual time=25.540..26.840 rows=10000 loops=1)
                                      Buffers: shared hit=962
                                      ->  HashAggregate  (cost=3075.92..3173.01 rows=9709 width=12) (actual time=25.539..26.290 rows=10000 loops=1)
                                            Group Key: metrica_2.parceiro_id
                                            Batches: 1  Memory Usage: 1169kB
                                            Buffers: shared hit=962
                                            ->  Hash Join  (cost=1.30..2506.27 rows=113929 width=4) (actual time=0.022..15.745 rows=113929 loops=1)
                                                  Hash Cond: (metrica_2.periodo_id = periodo.id)
                                                  Buffers: shared hit=962
                                                  ->  Seq Scan on metrica metrica_2  (cost=0.00..2100.29 rows=113929 width=8) (actual time=0.002..4.334 rows=113929 loops=1)
                                                        Buffers: shared hit=961
                                                  ->  Hash  (cost=1.15..1.15 rows=12 width=4) (actual time=0.009..0.009 rows=12 loops=1)
                                                        Buckets: 1024  Batches: 1  Memory Usage: 9kB
                                                        Buffers: shared hit=1
                                                        ->  Seq Scan on periodo  (cost=0.00..1.15 rows=12 width=4) (actual time=0.003..0.004 rows=12 loops=1)
                                                              Filter: (data_inicio <= '2026-09-21'::date)
                                                              Buffers: shared hit=1
                    ->  Hash  (cost=976.62..976.62 rows=10189 width=8) (actual time=1.725..1.726 rows=10000 loops=1)
                          Buckets: 16384  Batches: 1  Memory Usage: 519kB
                          Buffers: shared hit=77
                          ->  Bitmap Heap Scan on historico_segmento  (cost=123.26..976.62 rows=10189 width=8) (actual time=0.122..0.780 rows=10000 loops=1)
                                Recheck Cond: (periodo_id = 12)
                                Heap Blocks: exact=65
                                Buffers: shared hit=77
                                ->  Bitmap Index Scan on ix_segmento_periodo_segmento  (cost=0.00..120.71 rows=10189 width=0) (actual time=0.114..0.114 rows=10000 loops=1)
                                      Index Cond: (periodo_id = 12)
                                      Buffers: shared hit=12
              ->  Hash  (cost=2.63..2.63 rows=30 width=30) (actual time=0.040..0.042 rows=30 loops=1)
                    Buckets: 1024  Batches: 1  Memory Usage: 11kB
                    Buffers: shared hit=2
                    ->  Hash Join  (cost=1.11..2.63 rows=30 width=30) (actual time=0.026..0.033 rows=30 loops=1)
                          Hash Cond: (item_plano.acao_id = acao_comercial.id)
                          Buffers: shared hit=2
                          ->  Seq Scan on item_plano  (cost=0.00..1.38 rows=30 width=13) (actual time=0.004..0.005 rows=30 loops=1)
                                Filter: (plano_id = 1)
                                Buffers: shared hit=1
                          ->  Hash  (cost=1.05..1.05 rows=5 width=25) (actual time=0.010..0.010 rows=5 loops=1)
                                Buckets: 1024  Batches: 1  Memory Usage: 9kB
                                Buffers: shared hit=1
                                ->  Seq Scan on acao_comercial  (cost=0.00..1.05 rows=5 width=25) (actual time=0.003..0.003 rows=5 loops=1)
                                      Buffers: shared hit=1
Planning:
  Buffers: shared hit=71
Planning Time: 5.037 ms
Execution Time: 52.101 ms
```

</details>

### `relatorio-campanha`

A consulta filtra `item_plano`. Se o planejador varrer, a conferência abaixo diz se foi escolha dele ou falta de índice.

- `SELECT periodo.id AS periodo_id, periodo.data_inicio AS periodo_data_inicio, periodo.data_fim AS periodo_data…`
  - tempo no banco: **0.01 ms** · varredura: `periodo`
- `SELECT acao_comercial.nome, count(*) AS count_1, sum(item_plano.custo) AS sum_1, sum(item_plano.uplift_espera…`
  - tempo no banco: **0.14 ms** · varredura: `acao_comercial`, `item_plano`
  - a varredura em `item_plano` é **escolha do planejador**: com `enable_seqscan = off` o mesmo filtro usa `acao_comercial_pkey`, `parceiro_pkey`, `uq_item_plano_parceiro` e leva 0.19 ms. O índice cobre a consulta.
- `SELECT parceiro.categoria_id, count(*) AS count_1, sum(item_plano.custo) AS sum_1, sum(item_plano.uplift_espe…`
  - tempo no banco: **0.36 ms** · varredura: `acao_comercial`, `item_plano`
  - a varredura em `item_plano` é **escolha do planejador**: com `enable_seqscan = off` o mesmo filtro usa `acao_comercial_pkey`, `parceiro_pkey`, `uq_item_plano_parceiro` e leva 0.21 ms. O índice cobre a consulta.
- `SELECT historico_segmento.segmento, count(*) AS count_1, sum(item_plano.custo) AS sum_1, sum(item_plano.uplif…`
  - tempo no banco: **0.19 ms** · varredura: `acao_comercial`, `item_plano`
  - a varredura em `item_plano` é **escolha do planejador**: com `enable_seqscan = off` o mesmo filtro usa `acao_comercial_pkey`, `parceiro_pkey`, `uq_item_plano_parceiro`, `uq_segmento_parceiro_periodo` e leva 0.21 ms. O índice cobre a consulta.

<details><summary>Plano completo</summary>

```
Seq Scan on periodo  (cost=0.00..1.15 rows=1 width=12) (actual time=0.003..0.004 rows=1 loops=1)
  Filter: (id = 12)
  Rows Removed by Filter: 11
  Buffers: shared hit=1
Planning Time: 0.039 ms
Execution Time: 0.007 ms
```

</details>

<details><summary>Plano completo</summary>

```
HashAggregate  (cost=5.29..5.36 rows=5 width=93) (actual time=0.077..0.078 rows=1 loops=1)
  Group Key: acao_comercial.nome
  Batches: 1  Memory Usage: 24kB
  Buffers: shared hit=5
  ->  Hash Join  (cost=3.51..4.99 rows=30 width=31) (actual time=0.057..0.069 rows=30 loops=1)
        Hash Cond: (item_plano.acao_id = acao_comercial.id)
        Buffers: shared hit=5
        ->  Merge Join  (cost=2.40..3.73 rows=30 width=14) (actual time=0.039..0.047 rows=30 loops=1)
              Merge Cond: (parceiro.id = item_plano.parceiro_id)
              Buffers: shared hit=4
              ->  Index Only Scan using parceiro_pkey on parceiro  (cost=0.29..270.29 rows=10000 width=4) (actual time=0.022..0.023 rows=31 loops=1)
                    Heap Fetches: 0
                    Buffers: shared hit=3
              ->  Sort  (cost=2.11..2.19 rows=30 width=18) (actual time=0.016..0.017 rows=30 loops=1)
                    Sort Key: item_plano.parceiro_id
                    Sort Method: quicksort  Memory: 26kB
                    Buffers: shared hit=1
                    ->  Seq Scan on item_plano  (cost=0.00..1.38 rows=30 width=18) (actual time=0.002..0.005 rows=30 loops=1)
                          Filter: (plano_id = 1)
                          Buffers: shared hit=1
        ->  Hash  (cost=1.05..1.05 rows=5 width=25) (actual time=0.011..0.011 rows=5 loops=1)
              Buckets: 1024  Batches: 1  Memory Usage: 9kB
              Buffers: shared hit=1
              ->  Seq Scan on acao_comercial  (cost=0.00..1.05 rows=5 width=25) (actual time=0.003..0.003 rows=5 loops=1)
                    Buffers: shared hit=1
Planning:
  Buffers: shared hit=10
Planning Time: 0.291 ms
Execution Time: 0.143 ms
```

</details>

<details><summary>Plano completo</summary>

```
HashAggregate  (cost=5.69..5.84 rows=10 width=76) (actual time=0.247..0.251 rows=9 loops=1)
  Group Key: parceiro.categoria_id
  Batches: 1  Memory Usage: 24kB
  Buffers: shared hit=5
  ->  Hash Join  (cost=3.51..5.39 rows=30 width=14) (actual time=0.215..0.236 rows=30 loops=1)
        Hash Cond: (item_plano.acao_id = acao_comercial.id)
        Buffers: shared hit=5
        ->  Merge Join  (cost=2.40..4.13 rows=30 width=18) (actual time=0.023..0.039 rows=30 loops=1)
              Merge Cond: (parceiro.id = item_plano.parceiro_id)
              Buffers: shared hit=4
              ->  Index Scan using parceiro_pkey on parceiro  (cost=0.29..404.29 rows=10000 width=8) (actual time=0.012..0.017 rows=31 loops=1)
                    Buffers: shared hit=3
              ->  Sort  (cost=2.11..2.19 rows=30 width=18) (actual time=0.010..0.011 rows=30 loops=1)
                    Sort Key: item_plano.parceiro_id
                    Sort Method: quicksort  Memory: 26kB
                    Buffers: shared hit=1
                    ->  Seq Scan on item_plano  (cost=0.00..1.38 rows=30 width=18) (actual time=0.003..0.005 rows=30 loops=1)
                          Filter: (plano_id = 1)
                          Buffers: shared hit=1
        ->  Hash  (cost=1.05..1.05 rows=5 width=4) (actual time=0.012..0.012 rows=5 loops=1)
              Buckets: 1024  Batches: 1  Memory Usage: 9kB
              Buffers: shared hit=1
              ->  Seq Scan on acao_comercial  (cost=0.00..1.05 rows=5 width=4) (actual time=0.003..0.004 rows=5 loops=1)
                    Buffers: shared hit=1
Planning:
  Buffers: shared hit=10
Planning Time: 0.304 ms
Execution Time: 0.362 ms
```

</details>

<details><summary>Plano completo</summary>

```
HashAggregate  (cost=24.87..24.95 rows=5 width=76) (actual time=0.098..0.100 rows=4 loops=1)
  Group Key: historico_segmento.segmento
  Batches: 1  Memory Usage: 24kB
  Buffers: shared hit=11
  ->  Hash Join  (cost=3.93..24.56 rows=31 width=14) (actual time=0.066..0.090 rows=30 loops=1)
        Hash Cond: (item_plano.acao_id = acao_comercial.id)
        Buffers: shared hit=11
        ->  Merge Left Join  (cost=2.81..23.30 rows=31 width=18) (actual time=0.047..0.068 rows=30 loops=1)
              Merge Cond: (item_plano.parceiro_id = historico_segmento.parceiro_id)
              Buffers: shared hit=10
              ->  Merge Join  (cost=2.40..3.73 rows=30 width=18) (actual time=0.031..0.040 rows=30 loops=1)
                    Merge Cond: (parceiro.id = item_plano.parceiro_id)
                    Buffers: shared hit=4
                    ->  Index Only Scan using parceiro_pkey on parceiro  (cost=0.29..270.29 rows=10000 width=4) (actual time=0.019..0.020 rows=31 loops=1)
                          Heap Fetches: 0
                          Buffers: shared hit=3
                    ->  Sort  (cost=2.11..2.19 rows=30 width=18) (actual time=0.011..0.013 rows=30 loops=1)
                          Sort Key: item_plano.parceiro_id
                          Sort Method: quicksort  Memory: 26kB
                          Buffers: shared hit=1
                          ->  Seq Scan on item_plano  (cost=0.00..1.38 rows=30 width=18) (actual time=0.003..0.005 rows=30 loops=1)
                                Filter: (plano_id = 1)
                                Buffers: shared hit=1
              ->  Index Scan using uq_segmento_parceiro_periodo on historico_segmento  (cost=0.42..5769.61 rows=10189 width=8) (actual time=0.016..0.021 rows=30 loops=1)
                    Index Cond: (periodo_id = 12)
                    Buffers: shared hit=6
        ->  Hash  (cost=1.05..1.05 rows=5 width=4) (actual time=0.010..0.011 rows=5 loops=1)
              Buckets: 1024  Batches: 1  Memory Usage: 9kB
              Buffers: shared hit=1
              ->  Seq Scan on acao_comercial  (cost=0.00..1.05 rows=5 width=4) (actual time=0.003..0.003 rows=5 loops=1)
                    Buffers: shared hit=1
Planning:
  Buffers: shared hit=18
Planning Time: 0.448 ms
Execution Time: 0.191 ms
```

</details>

### `busca`

A consulta filtra `parceiro`. Se o planejador varrer, a conferência abaixo diz se foi escolha dele ou falta de índice.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo ORDER BY periodo.data_inicio DESC, peri…`
  - tempo no banco: **0.01 ms** · varredura: `periodo`
- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo WHERE periodo.data_inicio < %(data_inic…`
  - tempo no banco: **0.01 ms** · varredura: `periodo`
- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo WHERE EXISTS (SELECT * FROM metrica WHE…`
  - tempo no banco: **0.15 ms** · varredura: `periodo`
- `SELECT count(*) AS count_1 FROM (SELECT parceiro.id AS id, parceiro.nome AS nome, parceiro.nome_normalizado A…`
  - tempo no banco: **0.31 ms** · varredura: nenhuma
- `SELECT parceiro.id, parceiro.nome, parceiro.nome_normalizado, parceiro.categoria_id, parceiro.origem_categori…`
  - tempo no banco: **0.86 ms** · varredura: nenhuma

<details><summary>Plano completo</summary>

```
Sort  (cost=1.34..1.37 rows=12 width=12) (actual time=0.007..0.008 rows=12 loops=1)
  Sort Key: data_inicio DESC, id DESC
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=1
  ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.003..0.004 rows=12 loops=1)
        Buffers: shared hit=1
Planning Time: 0.045 ms
Execution Time: 0.014 ms
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
              Filter: (data_inicio < '2026-09-21'::date)
              Rows Removed by Filter: 1
              Buffers: shared hit=1
Planning:
  Buffers: shared hit=2
Planning Time: 0.068 ms
Execution Time: 0.012 ms
```

</details>

<details><summary>Plano completo</summary>

```
Sort  (cost=7.33..7.36 rows=12 width=12) (actual time=0.134..0.135 rows=12 loops=1)
  Sort Key: periodo.data_inicio DESC, periodo.id DESC
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=38
  ->  Nested Loop Semi Join  (cost=0.42..7.12 rows=12 width=12) (actual time=0.021..0.130 rows=12 loops=1)
        Buffers: shared hit=38
        ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.002..0.003 rows=12 loops=1)
              Buffers: shared hit=1
        ->  Index Only Scan using ix_metrica_periodo_faturamento on metrica  (cost=0.42..296.56 rows=9494 width=4) (actual time=0.010..0.010 rows=1 loops=12)
              Index Cond: (periodo_id = periodo.id)
              Heap Fetches: 0
              Buffers: shared hit=37
Planning:
  Buffers: shared hit=8
Planning Time: 0.205 ms
Execution Time: 0.154 ms
```

</details>

<details><summary>Plano completo</summary>

```
Aggregate  (cost=175.44..175.45 rows=1 width=8) (actual time=0.277..0.277 rows=1 loops=1)
  Buffers: shared hit=137
  ->  Bitmap Heap Scan on parceiro  (cost=33.84..173.68 rows=707 width=0) (actual time=0.096..0.251 rows=625 loops=1)
        Recheck Cond: ((nome_normalizado)::text ~~ '%praca%'::text)
        Heap Blocks: exact=130
        Buffers: shared hit=137
        ->  Bitmap Index Scan on ix_parceiro_nome_normalizado_trgm  (cost=0.00..33.66 rows=707 width=0) (actual time=0.082..0.082 rows=625 loops=1)
              Index Cond: ((nome_normalizado)::text ~~ '%praca%'::text)
              Buffers: shared hit=7
Planning:
  Buffers: shared hit=1
Planning Time: 0.125 ms
Execution Time: 0.311 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=19.54..902.06 rows=50 width=347) (actual time=0.455..0.778 rows=50 loops=1)
  Buffers: shared hit=1773
  ->  Incremental Sort  (cost=19.54..12727.82 rows=720 width=347) (actual time=0.455..0.775 rows=50 loops=1)
        Sort Key: parceiro.nome, parceiro.id
        Presorted Key: parceiro.nome
        Full-sort Groups: 2  Sort Method: quicksort  Average Memory: 29kB  Peak Memory: 29kB
        Buffers: shared hit=1773
        ->  Nested Loop Left Join  (cost=1.57..12695.88 rows=720 width=347) (actual time=0.218..0.752 rows=51 loops=1)
              Buffers: shared hit=1773
              ->  Nested Loop Left Join  (cost=1.16..8854.56 rows=707 width=343) (actual time=0.208..0.645 rows=51 loops=1)
                    Buffers: shared hit=1569
                    ->  Nested Loop Left Join  (cost=0.87..8097.16 rows=707 width=335) (actual time=0.198..0.559 rows=51 loops=1)
                          Buffers: shared hit=1416
                          ->  Nested Loop Left Join  (cost=0.58..4544.22 rows=707 width=328) (actual time=0.186..0.501 rows=51 loops=1)
                                Buffers: shared hit=1265
                                ->  Index Scan using ix_parceiro_nome on parceiro  (cost=0.29..991.28 rows=707 width=317) (actual time=0.169..0.381 rows=51 loops=1)
                                      Filter: ((nome_normalizado)::text ~~ '%praca%'::text)
                                      Rows Removed by Filter: 1113
                                      Buffers: shared hit=1112
                                ->  Index Scan using uq_metrica_parceiro_periodo on metrica  (cost=0.29..5.03 rows=1 width=15) (actual time=0.002..0.002 rows=1 loops=51)
                                      Index Cond: ((parceiro_id = parceiro.id) AND (periodo_id = 12))
                                      Buffers: shared hit=153
                          ->  Index Scan using uq_metrica_parceiro_periodo on metrica metrica_1  (cost=0.29..5.03 rows=1 width=11) (actual time=0.001..0.001 rows=1 loops=51)
                                Index Cond: ((parceiro_id = parceiro.id) AND (periodo_id = 11))
                                Buffers: shared hit=151
                    ->  Index Scan using uq_previsao_parceiro_periodo_modelo on previsao  (cost=0.29..1.07 rows=1 width=12) (actual time=0.001..0.001 rows=1 loops=51)
                          Index Cond: ((parceiro_id = parceiro.id) AND (periodo_base_id = 12) AND ((modelo_versao)::text = 'rede-1'::text))
                          Buffers: shared hit=153
              ->  Index Scan using uq_segmento_parceiro_periodo on historico_segmento  (cost=0.42..5.43 rows=1 width=8) (actual time=0.002..0.002 rows=1 loops=51)
                    Index Cond: ((parceiro_id = parceiro.id) AND (periodo_id = 12))
                    Buffers: shared hit=204
Planning:
  Buffers: shared hit=52
Planning Time: 1.260 ms
Execution Time: 0.862 ms
```

</details>

### `lista-completa`

Sem filtro, a resposta é a tabela inteira; o custo está no volume, não no plano. É o caso que a paginação da H36 precisa resolver.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo ORDER BY periodo.data_inicio DESC, peri…`
  - tempo no banco: **0.01 ms** · varredura: `periodo`
- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo WHERE periodo.data_inicio < %(data_inic…`
  - tempo no banco: **0.01 ms** · varredura: `periodo`
- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo WHERE EXISTS (SELECT * FROM metrica WHE…`
  - tempo no banco: **0.11 ms** · varredura: `periodo`
- `SELECT count(*) AS count_1 FROM (SELECT parceiro.id AS id, parceiro.nome AS nome, parceiro.nome_normalizado A…`
  - tempo no banco: **0.76 ms** · varredura: `parceiro`
- `SELECT parceiro.id, parceiro.nome, parceiro.nome_normalizado, parceiro.categoria_id, parceiro.origem_categori…`
  - tempo no banco: **0.57 ms** · varredura: nenhuma

<details><summary>Plano completo</summary>

```
Sort  (cost=1.34..1.37 rows=12 width=12) (actual time=0.008..0.009 rows=12 loops=1)
  Sort Key: data_inicio DESC, id DESC
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=1
  ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.003..0.004 rows=12 loops=1)
        Buffers: shared hit=1
Planning Time: 0.045 ms
Execution Time: 0.014 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=1.20..1.21 rows=1 width=12) (actual time=0.006..0.006 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.20..1.23 rows=11 width=12) (actual time=0.006..0.006 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.15 rows=11 width=12) (actual time=0.003..0.003 rows=11 loops=1)
              Filter: (data_inicio < '2026-09-21'::date)
              Rows Removed by Filter: 1
              Buffers: shared hit=1
Planning:
  Buffers: shared hit=2
Planning Time: 0.063 ms
Execution Time: 0.012 ms
```

</details>

<details><summary>Plano completo</summary>

```
Sort  (cost=7.33..7.36 rows=12 width=12) (actual time=0.089..0.090 rows=12 loops=1)
  Sort Key: periodo.data_inicio DESC, periodo.id DESC
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=38
  ->  Nested Loop Semi Join  (cost=0.42..7.12 rows=12 width=12) (actual time=0.022..0.086 rows=12 loops=1)
        Buffers: shared hit=38
        ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.002..0.003 rows=12 loops=1)
              Buffers: shared hit=1
        ->  Index Only Scan using ix_metrica_periodo_faturamento on metrica  (cost=0.42..296.56 rows=9494 width=4) (actual time=0.007..0.007 rows=1 loops=12)
              Index Cond: (periodo_id = periodo.id)
              Heap Fetches: 0
              Buffers: shared hit=37
Planning:
  Buffers: shared hit=8
Planning Time: 0.166 ms
Execution Time: 0.107 ms
```

</details>

<details><summary>Plano completo</summary>

```
Aggregate  (cost=256.00..256.01 rows=1 width=8) (actual time=0.750..0.750 rows=1 loops=1)
  Buffers: shared hit=131
  ->  Seq Scan on parceiro  (cost=0.00..231.00 rows=10000 width=0) (actual time=0.003..0.431 rows=10000 loops=1)
        Buffers: shared hit=131
Planning Time: 0.123 ms
Execution Time: 0.759 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=4.61..155.20 rows=50 width=347) (actual time=0.298..0.481 rows=50 loops=1)
  Buffers: shared hit=711
  ->  Incremental Sort  (cost=4.61..30692.53 rows=10189 width=347) (actual time=0.297..0.478 rows=50 loops=1)
        Sort Key: parceiro.nome, parceiro.id
        Presorted Key: parceiro.nome
        Full-sort Groups: 2  Sort Method: quicksort  Average Memory: 29kB  Peak Memory: 29kB
        Buffers: shared hit=711
        ->  Nested Loop Left Join  (cost=1.57..30240.64 rows=10189 width=347) (actual time=0.056..0.458 rows=51 loops=1)
              Buffers: shared hit=711
              ->  Nested Loop Left Join  (cost=1.16..21046.15 rows=10000 width=343) (actual time=0.043..0.339 rows=51 loops=1)
                    Buffers: shared hit=507
                    ->  Nested Loop Left Join  (cost=0.87..17431.22 rows=10000 width=335) (actual time=0.033..0.202 rows=51 loops=1)
                          Buffers: shared hit=354
                          ->  Nested Loop Left Join  (cost=0.58..9198.75 rows=10000 width=328) (actual time=0.023..0.147 rows=51 loops=1)
                                Buffers: shared hit=201
                                ->  Index Scan using ix_parceiro_nome on parceiro  (cost=0.29..966.28 rows=10000 width=317) (actual time=0.011..0.029 rows=51 loops=1)
                                      Buffers: shared hit=48
                                ->  Index Scan using uq_metrica_parceiro_periodo on metrica  (cost=0.29..0.82 rows=1 width=15) (actual time=0.002..0.002 rows=1 loops=51)
                                      Index Cond: ((parceiro_id = parceiro.id) AND (periodo_id = 12))
                                      Buffers: shared hit=153
                          ->  Index Scan using uq_metrica_parceiro_periodo on metrica metrica_1  (cost=0.29..0.82 rows=1 width=11) (actual time=0.001..0.001 rows=1 loops=51)
                                Index Cond: ((parceiro_id = parceiro.id) AND (periodo_id = 11))
                                Buffers: shared hit=153
                    ->  Index Scan using uq_previsao_parceiro_periodo_modelo on previsao  (cost=0.29..0.36 rows=1 width=12) (actual time=0.002..0.002 rows=1 loops=51)
                          Index Cond: ((parceiro_id = parceiro.id) AND (periodo_base_id = 12) AND ((modelo_versao)::text = 'rede-1'::text))
                          Buffers: shared hit=153
              ->  Index Scan using uq_segmento_parceiro_periodo on historico_segmento  (cost=0.42..0.92 rows=1 width=8) (actual time=0.002..0.002 rows=1 loops=51)
                    Index Cond: ((parceiro_id = parceiro.id) AND (periodo_id = 12))
                    Buffers: shared hit=204
Planning:
  Buffers: shared hit=51
Planning Time: 1.039 ms
Execution Time: 0.567 ms
```

</details>

## Índices em uso

- `ix_metrica_periodo_faturamento`
- `ix_parceiro_nome`
- `ix_parceiro_nome_normalizado_trgm`
- `ix_segmento_periodo_segmento`
- `parceiro_pkey`
- `uq_metrica_parceiro_periodo`
- `uq_previsao_parceiro_periodo_modelo`
- `uq_segmento_parceiro_periodo`

