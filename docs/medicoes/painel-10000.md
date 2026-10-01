# Medição do painel com 10.000 parceiros — H40, H82 e H83

> Gerado por `scripts/medir_painel.py`. **Não edite à mão**: número escrito à mão não é evidência. Para atualizar, rode o comando abaixo de novo.

O RNF03 fixa **2 s** como teto de resposta e a H40 cobra isso com 10.000 parceiros. Este arquivo é o registro da medição — a Sprint 12 não precisa medir de novo às pressas para pôr o número na apresentação.

## Ambiente

| Item | Valor |
|---|---|
| Data | 01/10/2026 06:47 |
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
| `indicadores` | 300 | 17.4 ms | 18.9 ms | 9% | 398 B | sim |
| `ranking-25` | 131 | 45.0 ms | 49.5 ms | 10% | 6 kB | sim |
| `ranking-200` | 127 | 48.3 ms | 51.2 ms | 6% | 47 kB | sim |
| `serie` | 187 | 31.2 ms | 33.6 ms | 8% | 2 kB | sim |
| `segmentos` | 300 | 8.3 ms | 9.2 ms | 11% | 297 B | sim |
| `mobilidade` | 184 | 32.1 ms | 34.2 ms | 7% | 517 B | sim |
| `indicadores-categoria` | 259 | 23.4 ms | 25.5 ms | 9% | 434 B | sim |
| `ranking-categoria` | 142 | 45.4 ms | 48.1 ms | 6% | 6 kB | sim |
| `serie-categoria` | 284 | 20.8 ms | 22.4 ms | 8% | 2 kB | sim |
| `segmentos-categoria` | 300 | 10.6 ms | 11.4 ms | 8% | 330 B | sim |
| `decisao` | 180 | 30.4 ms | 33.5 ms | 10% | 1 kB | sim |
| `busca` | 293 | 17.5 ms | 19.7 ms | 12% | 18 kB | sim |
| `lista-completa` | 300 | 18.4 ms | 20.2 ms | 10% | 17 kB | sim |

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
  - tempo no banco: **2.40 ms** · varredura: nenhuma
- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo WHERE periodo.data_inicio < %(data_inic…`
  - tempo no banco: **0.01 ms** · varredura: `periodo`
- `SELECT count(*) AS count_1, count(*) FILTER (WHERE historico_segmento.segmento = %(segmento_1)s) AS anon_1 FR…`
  - tempo no banco: **1.16 ms** · varredura: nenhuma

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
Planning Time: 0.032 ms
Execution Time: 0.013 ms
```

</details>

<details><summary>Plano completo</summary>

```
Aggregate  (cost=1423.21..1423.22 rows=1 width=48) (actual time=2.339..2.340 rows=1 loops=1)
  Buffers: shared hit=1005
  ->  Bitmap Heap Scan on metrica  (cost=270.65..1351.37 rows=9578 width=11) (actual time=0.474..1.521 rows=10000 loops=1)
        Recheck Cond: (periodo_id = 12)
        Heap Blocks: exact=961
        Buffers: shared hit=1005
        ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..268.25 rows=9578 width=0) (actual time=0.398..0.398 rows=10000 loops=1)
              Index Cond: (periodo_id = 12)
              Buffers: shared hit=44
Planning Time: 0.044 ms
Execution Time: 2.402 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=1.20..1.21 rows=1 width=12) (actual time=0.008..0.008 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.20..1.23 rows=11 width=12) (actual time=0.008..0.008 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.15 rows=11 width=12) (actual time=0.003..0.004 rows=11 loops=1)
              Filter: (data_inicio < '2026-09-21'::date)
              Rows Removed by Filter: 1
              Buffers: shared hit=1
Planning:
  Buffers: shared hit=2
Planning Time: 0.078 ms
Execution Time: 0.014 ms
```

</details>

<details><summary>Plano completo</summary>

```
Aggregate  (cost=1048.71..1048.72 rows=1 width=16) (actual time=1.109..1.109 rows=1 loops=1)
  Buffers: shared hit=77
  ->  Bitmap Heap Scan on historico_segmento  (cost=122.05..973.46 rows=10033 width=4) (actual time=0.130..0.610 rows=10000 loops=1)
        Recheck Cond: (periodo_id = 12)
        Heap Blocks: exact=65
        Buffers: shared hit=77
        ->  Bitmap Index Scan on ix_segmento_periodo_segmento  (cost=0.00..119.54 rows=10033 width=0) (actual time=0.114..0.115 rows=10000 loops=1)
              Index Cond: (periodo_id = 12)
              Buffers: shared hit=12
Planning Time: 0.034 ms
Execution Time: 1.163 ms
```

</details>

### `ranking-25`

A consulta filtra `metrica`. Se o planejador varrer, a conferência abaixo diz se foi escolha dele ou falta de índice.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo ORDER BY periodo.data_inicio DESC, peri…`
  - tempo no banco: **0.04 ms** · varredura: `periodo`
- `SELECT count(*) AS count_1 FROM (SELECT metrica.parceiro_id AS parceiro_id, metrica.faturamento AS faturament…`
  - tempo no banco: **6.10 ms** · varredura: `parceiro`
- `SELECT atual.parceiro_id, atual.faturamento, atual.pedidos, atual.posicao, parceiro.nome, categoria.nome AS n…`
  - tempo no banco: **21.57 ms** · varredura: `categoria`, `parceiro`
- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo WHERE periodo.data_inicio < %(data_inic…`
  - tempo no banco: **0.03 ms** · varredura: `periodo`
- `SELECT anterior.parceiro_id, anterior.posicao, anterior.faturamento FROM (SELECT metrica.parceiro_id AS parce…`
  - tempo no banco: **9.94 ms** · varredura: `parceiro`

<details><summary>Plano completo</summary>

```
Limit  (cost=1.18..1.18 rows=1 width=12) (actual time=0.018..0.019 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.18..1.21 rows=12 width=12) (actual time=0.018..0.018 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.005..0.006 rows=12 loops=1)
              Buffers: shared hit=1
Planning Time: 0.044 ms
Execution Time: 0.040 ms
```

</details>

<details><summary>Plano completo</summary>

```
Aggregate  (cost=1852.25..1852.26 rows=1 width=8) (actual time=5.870..5.871 rows=1 loops=1)
  Buffers: shared hit=1136
  ->  Hash Join  (cost=626.65..1732.53 rows=9578 width=40) (actual time=2.494..5.516 rows=10000 loops=1)
        Hash Cond: (metrica.parceiro_id = parceiro.id)
        Buffers: shared hit=1136
        ->  Bitmap Heap Scan on metrica  (cost=270.65..1351.37 rows=9578 width=11) (actual time=0.601..1.936 rows=10000 loops=1)
              Recheck Cond: (periodo_id = 12)
              Heap Blocks: exact=961
              Buffers: shared hit=1005
              ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..268.25 rows=9578 width=0) (actual time=0.503..0.503 rows=10000 loops=1)
                    Index Cond: (periodo_id = 12)
                    Buffers: shared hit=44
        ->  Hash  (cost=231.00..231.00 rows=10000 width=21) (actual time=1.826..1.826 rows=10000 loops=1)
              Buckets: 16384  Batches: 1  Memory Usage: 668kB
              Buffers: shared hit=131
              ->  Seq Scan on parceiro  (cost=0.00..231.00 rows=10000 width=21) (actual time=0.003..0.665 rows=10000 loops=1)
                    Buffers: shared hit=131
Planning:
  Buffers: shared hit=12
Planning Time: 0.228 ms
Execution Time: 6.101 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=4473.46..4473.52 rows=25 width=54) (actual time=20.802..20.807 rows=25 loops=1)
  Buffers: shared hit=1345
  ->  Sort  (cost=4473.46..4498.09 rows=9852 width=54) (actual time=20.801..20.804 rows=25 loops=1)
        Sort Key: (row_number() OVER (?))
        Sort Method: top-N heapsort  Memory: 28kB
        Buffers: shared hit=1345
        ->  Hash Left Join  (cost=3821.99..4195.44 rows=9852 width=54) (actual time=12.251..19.402 rows=10000 loops=1)
              Hash Cond: (metrica.parceiro_id = historico_segmento.parceiro_id)
              Buffers: shared hit=1345
              ->  Hash Left Join  (cost=2723.12..3071.41 rows=9578 width=50) (actual time=10.446..16.083 rows=10000 loops=1)
                    Hash Cond: (parceiro.categoria_id = categoria.id)
                    Buffers: shared hit=1268
                    ->  Hash Join  (cost=2721.89..3034.39 rows=9578 width=44) (actual time=10.421..14.863 rows=10000 loops=1)
                          Hash Cond: (metrica.parceiro_id = parceiro.id)
                          Buffers: shared hit=1267
                          ->  WindowAgg  (cost=2365.89..2557.45 rows=9578 width=40) (actual time=8.015..10.511 rows=10000 loops=1)
                                Buffers: shared hit=1136
                                ->  Sort  (cost=2365.89..2389.84 rows=9578 width=32) (actual time=8.007..8.717 rows=10000 loops=1)
                                      Sort Key: metrica.faturamento DESC, parceiro_1.nome
                                      Sort Method: quicksort  Memory: 978kB
                                      Buffers: shared hit=1136
                                      ->  Hash Join  (cost=626.65..1732.53 rows=9578 width=32) (actual time=2.832..5.518 rows=10000 loops=1)
                                            Hash Cond: (metrica.parceiro_id = parceiro_1.id)
                                            Buffers: shared hit=1136
                                            ->  Bitmap Heap Scan on metrica  (cost=270.65..1351.37 rows=9578 width=15) (actual time=0.534..1.777 rows=10000 loops=1)
                                                  Recheck Cond: (periodo_id = 12)
                                                  Heap Blocks: exact=961
                                                  Buffers: shared hit=1005
                                                  ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..268.25 rows=9578 width=0) (actual time=0.460..0.460 rows=10000 loops=1)
                                                        Index Cond: (periodo_id = 12)
                                                        Buffers: shared hit=44
                                            ->  Hash  (cost=231.00..231.00 rows=10000 width=21) (actual time=2.216..2.216 rows=10000 loops=1)
                                                  Buckets: 16384  Batches: 1  Memory Usage: 668kB
                                                  Buffers: shared hit=131
                                                  ->  Seq Scan on parceiro parceiro_1  (cost=0.00..231.00 rows=10000 width=21) (actual time=0.003..0.753 rows=10000 loops=1)
                                                        Buffers: shared hit=131
                          ->  Hash  (cost=231.00..231.00 rows=10000 width=25) (actual time=2.327..2.327 rows=10000 loops=1)
                                Buckets: 16384  Batches: 1  Memory Usage: 707kB
                                Buffers: shared hit=131
                                ->  Seq Scan on parceiro  (cost=0.00..231.00 rows=10000 width=25) (actual time=0.004..0.797 rows=10000 loops=1)
                                      Buffers: shared hit=131
                    ->  Hash  (cost=1.10..1.10 rows=10 width=14) (actual time=0.014..0.014 rows=10 loops=1)
                          Buckets: 1024  Batches: 1  Memory Usage: 9kB
                          Buffers: shared hit=1
                          ->  Seq Scan on categoria  (cost=0.00..1.10 rows=10 width=14) (actual time=0.003..0.004 rows=10 loops=1)
                                Buffers: shared hit=1
              ->  Hash  (cost=973.46..973.46 rows=10033 width=8) (actual time=1.727..1.728 rows=10000 loops=1)
                    Buckets: 16384  Batches: 1  Memory Usage: 519kB
                    Buffers: shared hit=77
                    ->  Bitmap Heap Scan on historico_segmento  (cost=122.05..973.46 rows=10033 width=8) (actual time=0.133..0.759 rows=10000 loops=1)
                          Recheck Cond: (periodo_id = 12)
                          Heap Blocks: exact=65
                          Buffers: shared hit=77
                          ->  Bitmap Index Scan on ix_segmento_periodo_segmento  (cost=0.00..119.54 rows=10033 width=0) (actual time=0.126..0.126 rows=10000 loops=1)
                                Index Cond: (periodo_id = 12)
                                Buffers: shared hit=12
Planning:
  Buffers: shared hit=30
Planning Time: 0.665 ms
Execution Time: 21.570 ms
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
              Filter: (data_inicio < '2026-09-21'::date)
              Rows Removed by Filter: 1
              Buffers: shared hit=1
Planning:
  Buffers: shared hit=2
Planning Time: 0.093 ms
Execution Time: 0.032 ms
```

</details>

<details><summary>Plano completo</summary>

```
Subquery Scan on anterior  (cost=2369.23..2705.65 rows=25 width=19) (actual time=7.438..9.662 rows=25 loops=1)
  Filter: (anterior.parceiro_id = ANY ('{4133,2118,4648,8156,1577,2384,2515,6266,1682,6144,4544,3134,4101,4155,3997,924,3103,246,5834,8777,4254,6210,3194,9809,460}'::integer[]))
  Rows Removed by Filter: 9791
  Buffers: shared hit=1145
  ->  WindowAgg  (cost=2369.17..2561.41 rows=9612 width=40) (actual time=7.435..9.151 rows=9816 loops=1)
        Buffers: shared hit=1145
        ->  Sort  (cost=2369.17..2393.20 rows=9612 width=28) (actual time=7.425..7.823 rows=9816 loops=1)
              Sort Key: metrica.faturamento DESC, parceiro.nome
              Sort Method: quicksort  Memory: 921kB
              Buffers: shared hit=1145
              ->  Hash Join  (cost=626.91..1733.30 rows=9612 width=28) (actual time=2.342..5.045 rows=9816 loops=1)
                    Hash Cond: (metrica.parceiro_id = parceiro.id)
                    Buffers: shared hit=1145
                    ->  Bitmap Heap Scan on metrica  (cost=270.91..1352.06 rows=9612 width=11) (actual time=0.522..1.862 rows=9816 loops=1)
                          Recheck Cond: (periodo_id = 11)
                          Heap Blocks: exact=961
                          Buffers: shared hit=1014
                          ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..268.51 rows=9612 width=0) (actual time=0.448..0.448 rows=9816 loops=1)
                                Index Cond: (periodo_id = 11)
                                Buffers: shared hit=53
                    ->  Hash  (cost=231.00..231.00 rows=10000 width=21) (actual time=1.757..1.757 rows=10000 loops=1)
                          Buckets: 16384  Batches: 1  Memory Usage: 668kB
                          Buffers: shared hit=131
                          ->  Seq Scan on parceiro  (cost=0.00..231.00 rows=10000 width=21) (actual time=0.003..0.607 rows=10000 loops=1)
                                Buffers: shared hit=131
Planning:
  Buffers: shared hit=12
Planning Time: 0.223 ms
Execution Time: 9.941 ms
```

</details>

### `ranking-200`

A consulta filtra `metrica`. Se o planejador varrer, a conferência abaixo diz se foi escolha dele ou falta de índice.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo ORDER BY periodo.data_inicio DESC, peri…`
  - tempo no banco: **0.03 ms** · varredura: `periodo`
- `SELECT count(*) AS count_1 FROM (SELECT metrica.parceiro_id AS parceiro_id, metrica.faturamento AS faturament…`
  - tempo no banco: **5.76 ms** · varredura: `parceiro`
- `SELECT atual.parceiro_id, atual.faturamento, atual.pedidos, atual.posicao, parceiro.nome, categoria.nome AS n…`
  - tempo no banco: **19.64 ms** · varredura: `categoria`, `parceiro`
- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo WHERE periodo.data_inicio < %(data_inic…`
  - tempo no banco: **0.04 ms** · varredura: `periodo`
- `SELECT anterior.parceiro_id, anterior.posicao, anterior.faturamento FROM (SELECT metrica.parceiro_id AS parce…`
  - tempo no banco: **11.55 ms** · varredura: `parceiro`

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
Planning Time: 0.035 ms
Execution Time: 0.034 ms
```

</details>

<details><summary>Plano completo</summary>

```
Aggregate  (cost=1852.25..1852.26 rows=1 width=8) (actual time=5.551..5.552 rows=1 loops=1)
  Buffers: shared hit=1136
  ->  Hash Join  (cost=626.65..1732.53 rows=9578 width=40) (actual time=2.467..5.220 rows=10000 loops=1)
        Hash Cond: (metrica.parceiro_id = parceiro.id)
        Buffers: shared hit=1136
        ->  Bitmap Heap Scan on metrica  (cost=270.65..1351.37 rows=9578 width=11) (actual time=0.625..1.895 rows=10000 loops=1)
              Recheck Cond: (periodo_id = 12)
              Heap Blocks: exact=961
              Buffers: shared hit=1005
              ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..268.25 rows=9578 width=0) (actual time=0.542..0.543 rows=10000 loops=1)
                    Index Cond: (periodo_id = 12)
                    Buffers: shared hit=44
        ->  Hash  (cost=231.00..231.00 rows=10000 width=21) (actual time=1.775..1.775 rows=10000 loops=1)
              Buckets: 16384  Batches: 1  Memory Usage: 668kB
              Buffers: shared hit=131
              ->  Seq Scan on parceiro  (cost=0.00..231.00 rows=10000 width=21) (actual time=0.003..0.632 rows=10000 loops=1)
                    Buffers: shared hit=131
Planning:
  Buffers: shared hit=12
Planning Time: 0.182 ms
Execution Time: 5.764 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=4621.24..4621.74 rows=200 width=54) (actual time=18.974..18.991 rows=200 loops=1)
  Buffers: shared hit=1345
  ->  Sort  (cost=4621.24..4645.87 rows=9852 width=54) (actual time=18.973..18.981 rows=200 loops=1)
        Sort Key: (row_number() OVER (?))
        Sort Method: top-N heapsort  Memory: 51kB
        Buffers: shared hit=1345
        ->  Hash Left Join  (cost=3821.99..4195.44 rows=9852 width=54) (actual time=11.420..17.737 rows=10000 loops=1)
              Hash Cond: (metrica.parceiro_id = historico_segmento.parceiro_id)
              Buffers: shared hit=1345
              ->  Hash Left Join  (cost=2723.12..3071.41 rows=9578 width=50) (actual time=9.580..14.534 rows=10000 loops=1)
                    Hash Cond: (parceiro.categoria_id = categoria.id)
                    Buffers: shared hit=1268
                    ->  Hash Join  (cost=2721.89..3034.39 rows=9578 width=44) (actual time=9.557..13.498 rows=10000 loops=1)
                          Hash Cond: (metrica.parceiro_id = parceiro.id)
                          Buffers: shared hit=1267
                          ->  WindowAgg  (cost=2365.89..2557.45 rows=9578 width=40) (actual time=7.583..9.733 rows=10000 loops=1)
                                Buffers: shared hit=1136
                                ->  Sort  (cost=2365.89..2389.84 rows=9578 width=32) (actual time=7.571..8.192 rows=10000 loops=1)
                                      Sort Key: metrica.faturamento DESC, parceiro_1.nome
                                      Sort Method: quicksort  Memory: 978kB
                                      Buffers: shared hit=1136
                                      ->  Hash Join  (cost=626.65..1732.53 rows=9578 width=32) (actual time=2.344..5.080 rows=10000 loops=1)
                                            Hash Cond: (metrica.parceiro_id = parceiro_1.id)
                                            Buffers: shared hit=1136
                                            ->  Bitmap Heap Scan on metrica  (cost=270.65..1351.37 rows=9578 width=15) (actual time=0.531..1.827 rows=10000 loops=1)
                                                  Recheck Cond: (periodo_id = 12)
                                                  Heap Blocks: exact=961
                                                  Buffers: shared hit=1005
                                                  ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..268.25 rows=9578 width=0) (actual time=0.448..0.448 rows=10000 loops=1)
                                                        Index Cond: (periodo_id = 12)
                                                        Buffers: shared hit=44
                                            ->  Hash  (cost=231.00..231.00 rows=10000 width=21) (actual time=1.745..1.746 rows=10000 loops=1)
                                                  Buckets: 16384  Batches: 1  Memory Usage: 668kB
                                                  Buffers: shared hit=131
                                                  ->  Seq Scan on parceiro parceiro_1  (cost=0.00..231.00 rows=10000 width=21) (actual time=0.003..0.582 rows=10000 loops=1)
                                                        Buffers: shared hit=131
                          ->  Hash  (cost=231.00..231.00 rows=10000 width=25) (actual time=1.908..1.908 rows=10000 loops=1)
                                Buckets: 16384  Batches: 1  Memory Usage: 707kB
                                Buffers: shared hit=131
                                ->  Seq Scan on parceiro  (cost=0.00..231.00 rows=10000 width=25) (actual time=0.004..0.641 rows=10000 loops=1)
                                      Buffers: shared hit=131
                    ->  Hash  (cost=1.10..1.10 rows=10 width=14) (actual time=0.015..0.015 rows=10 loops=1)
                          Buckets: 1024  Batches: 1  Memory Usage: 9kB
                          Buffers: shared hit=1
                          ->  Seq Scan on categoria  (cost=0.00..1.10 rows=10 width=14) (actual time=0.004..0.005 rows=10 loops=1)
                                Buffers: shared hit=1
              ->  Hash  (cost=973.46..973.46 rows=10033 width=8) (actual time=1.774..1.774 rows=10000 loops=1)
                    Buckets: 16384  Batches: 1  Memory Usage: 519kB
                    Buffers: shared hit=77
                    ->  Bitmap Heap Scan on historico_segmento  (cost=122.05..973.46 rows=10033 width=8) (actual time=0.141..0.769 rows=10000 loops=1)
                          Recheck Cond: (periodo_id = 12)
                          Heap Blocks: exact=65
                          Buffers: shared hit=77
                          ->  Bitmap Index Scan on ix_segmento_periodo_segmento  (cost=0.00..119.54 rows=10033 width=0) (actual time=0.135..0.135 rows=10000 loops=1)
                                Index Cond: (periodo_id = 12)
                                Buffers: shared hit=12
Planning:
  Buffers: shared hit=30
Planning Time: 0.550 ms
Execution Time: 19.639 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=1.20..1.21 rows=1 width=12) (actual time=0.019..0.020 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.20..1.23 rows=11 width=12) (actual time=0.019..0.019 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.15 rows=11 width=12) (actual time=0.004..0.005 rows=11 loops=1)
              Filter: (data_inicio < '2026-09-21'::date)
              Rows Removed by Filter: 1
              Buffers: shared hit=1
Planning:
  Buffers: shared hit=2
Planning Time: 0.094 ms
Execution Time: 0.036 ms
```

</details>

<details><summary>Plano completo</summary>

```
Subquery Scan on anterior  (cost=2369.67..2706.09 rows=198 width=19) (actual time=8.492..11.237 rows=198 loops=1)
  Filter: (anterior.parceiro_id = ANY ('{4133,2118,4648,8156,1577,2384,2515,6266,1682,6144,4544,3134,4101,4155,3997,924,3103,246,5834,8777,4254,6210,3194,9809,460,2744,7117,6061,2272,1563,6700,8924,1823,2149,4982,5788,6772,5275,1917,4729,4468,9817,9927,1660,983,9656,2999,7128,2260,2864,4716,7651,9344,6952,4676,3721,7656,1936,5323,9527,9814,1307,7911,1242,9892,7384,3662,3453,8044,6606,3217,9490,5998,9104,3270,9386,5257,4885,7965,1395,9573,6999,7609,8553,7619,2311,6693,4654,2470,1793,3736,7033,9035,9142,7023,2314,600,8137,860,1019,181,8398,5022,9952,8365,5193,5315,4340,3133,2914,613,1348,6290,2666,3389,9534,9904,1393,2125,3621,2539,9030,8625,1382,2134,9094,2336,1067,1586,6956,7674,1265,6706,214,1896,7732,6511,9681,5609,6382,549,9248,9717,3415,484,381,6190,74,5690,3576,1754,6766,885,823,2044,2050,7320,7921,9332,9754,6518,5953,3090,6070,9481,1010,1825,9883,5897,2831,906,2980,2512,4890,2053,5946,6522,8519,4171,8839,1763,5865,6100,339,7794,8698,6222,7442,3461,9277,9949,2828,3384,6676,3273,9710,9165,3579,6677,2759}'::integer[]))
  Rows Removed by Filter: 9618
  Buffers: shared hit=1145
  ->  WindowAgg  (cost=2369.17..2561.41 rows=9612 width=40) (actual time=8.485..10.466 rows=9816 loops=1)
        Buffers: shared hit=1145
        ->  Sort  (cost=2369.17..2393.20 rows=9612 width=28) (actual time=8.476..8.982 rows=9816 loops=1)
              Sort Key: metrica.faturamento DESC, parceiro.nome
              Sort Method: quicksort  Memory: 921kB
              Buffers: shared hit=1145
              ->  Hash Join  (cost=626.91..1733.30 rows=9612 width=28) (actual time=2.944..5.871 rows=9816 loops=1)
                    Hash Cond: (metrica.parceiro_id = parceiro.id)
                    Buffers: shared hit=1145
                    ->  Bitmap Heap Scan on metrica  (cost=270.91..1352.06 rows=9612 width=11) (actual time=0.548..1.880 rows=9816 loops=1)
                          Recheck Cond: (periodo_id = 11)
                          Heap Blocks: exact=961
                          Buffers: shared hit=1014
                          ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..268.51 rows=9612 width=0) (actual time=0.472..0.472 rows=9816 loops=1)
                                Index Cond: (periodo_id = 11)
                                Buffers: shared hit=53
                    ->  Hash  (cost=231.00..231.00 rows=10000 width=21) (actual time=2.316..2.317 rows=10000 loops=1)
                          Buckets: 16384  Batches: 1  Memory Usage: 668kB
                          Buffers: shared hit=131
                          ->  Seq Scan on parceiro  (cost=0.00..231.00 rows=10000 width=21) (actual time=0.004..0.706 rows=10000 loops=1)
                                Buffers: shared hit=131
Planning:
  Buffers: shared hit=12
Planning Time: 0.552 ms
Execution Time: 11.553 ms
```

</details>

### `serie`

A série agrega **todos** os períodos: a consulta lê a tabela inteira por definição, e varrer é o plano certo.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim, sum(metrica.faturamento) AS sum_1, sum(metrica.pedi…`
  - tempo no banco: **33.35 ms** · varredura: `metrica`, `periodo`

<details><summary>Plano completo</summary>

```
Sort  (cost=3361.08..3361.11 rows=12 width=52) (actual time=33.296..33.298 rows=12 loops=1)
  Sort Key: periodo.data_inicio, periodo.id
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=962
  ->  HashAggregate  (cost=3360.71..3360.86 rows=12 width=52) (actual time=33.285..33.289 rows=12 loops=1)
        Group Key: periodo.id
        Batches: 1  Memory Usage: 24kB
        Buffers: shared hit=962
        ->  Hash Right Join  (cost=1.27..2506.24 rows=113929 width=23) (actual time=0.051..19.411 rows=113929 loops=1)
              Hash Cond: (metrica.periodo_id = periodo.id)
              Buffers: shared hit=962
              ->  Seq Scan on metrica  (cost=0.00..2100.29 rows=113929 width=15) (actual time=0.003..5.115 rows=113929 loops=1)
                    Buffers: shared hit=961
              ->  Hash  (cost=1.12..1.12 rows=12 width=12) (actual time=0.037..0.037 rows=12 loops=1)
                    Buckets: 1024  Batches: 1  Memory Usage: 9kB
                    Buffers: shared hit=1
                    ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.021..0.022 rows=12 loops=1)
                          Buffers: shared hit=1
Planning:
  Buffers: shared hit=4
Planning Time: 0.170 ms
Execution Time: 33.355 ms
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
Limit  (cost=1.18..1.18 rows=1 width=12) (actual time=0.007..0.008 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.18..1.21 rows=12 width=12) (actual time=0.007..0.007 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.003..0.004 rows=12 loops=1)
              Buffers: shared hit=1
Planning Time: 0.031 ms
Execution Time: 0.012 ms
```

</details>

<details><summary>Plano completo</summary>

```
Sort  (cost=274.14..274.16 rows=5 width=12) (actual time=0.883..0.883 rows=5 loops=1)
  Sort Key: (count(*)) DESC, segmento
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=14
  ->  GroupAggregate  (cost=0.29..274.08 rows=5 width=12) (actual time=0.069..0.880 rows=5 loops=1)
        Group Key: segmento
        Buffers: shared hit=14
        ->  Index Only Scan using ix_segmento_periodo_segmento on historico_segmento  (cost=0.29..223.87 rows=10033 width=4) (actual time=0.029..0.442 rows=10000 loops=1)
              Index Cond: (periodo_id = 12)
              Heap Fetches: 104
              Buffers: shared hit=14
Planning Time: 0.037 ms
Execution Time: 0.909 ms
```

</details>

### `mobilidade`

A consulta filtra `metrica`. Se o planejador varrer, a conferência abaixo diz se foi escolha dele ou falta de índice.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo ORDER BY periodo.data_inicio DESC, peri…`
  - tempo no banco: **0.04 ms** · varredura: `periodo`
- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo WHERE periodo.data_inicio < %(data_inic…`
  - tempo no banco: **0.01 ms** · varredura: `periodo`
- `SELECT coalesce(atual.parceiro_id, passado.parceiro_id) AS parceiro_id, parceiro.nome, atual.posicao AS posic…`
  - tempo no banco: **26.51 ms** · varredura: `parceiro`

<details><summary>Plano completo</summary>

```
Limit  (cost=1.18..1.18 rows=1 width=12) (actual time=0.018..0.019 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.18..1.21 rows=12 width=12) (actual time=0.017..0.018 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.004..0.005 rows=12 loops=1)
              Buffers: shared hit=1
Planning Time: 0.044 ms
Execution Time: 0.036 ms
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
              Filter: (data_inicio < '2026-09-21'::date)
              Rows Removed by Filter: 1
              Buffers: shared hit=1
Planning:
  Buffers: shared hit=2
Planning Time: 0.073 ms
Execution Time: 0.013 ms
```

</details>

<details><summary>Plano completo</summary>

```
Sort  (cost=6153.56..6158.65 rows=2036 width=45) (actual time=25.744..25.748 rows=4 loops=1)
  Sort Key: (COALESCE(atual.posicao, (row_number() OVER (?))))
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=2412
  ->  Hash Join  (cost=5498.13..6041.67 rows=2036 width=45) (actual time=22.367..25.738 rows=4 loops=1)
        Hash Cond: (COALESCE(atual.parceiro_id, metrica.parceiro_id) = parceiro.id)
        Buffers: shared hit=2412
        ->  Hash Full Join  (cost=5142.13..5680.32 rows=2036 width=24) (actual time=20.457..23.825 rows=4 loops=1)
              Hash Cond: (metrica.parceiro_id = atual.parceiro_id)
              Filter: (((atual.posicao <= 15) AND (((row_number() OVER (?)) IS NULL) OR ((row_number() OVER (?)) > 15))) OR (((row_number() OVER (?)) <= 15) AND ((atual.posicao IS NULL) OR (atual.posicao > 15))))
              Rows Removed by Filter: 9996
              Buffers: shared hit=2281
              ->  WindowAgg  (cost=2369.17..2561.41 rows=9612 width=40) (actual time=8.060..9.923 rows=9816 loops=1)
                    Buffers: shared hit=1145
                    ->  Sort  (cost=2369.17..2393.20 rows=9612 width=28) (actual time=8.054..8.568 rows=9816 loops=1)
                          Sort Key: metrica.faturamento DESC, parceiro_1.nome
                          Sort Method: quicksort  Memory: 921kB
                          Buffers: shared hit=1145
                          ->  Hash Join  (cost=626.91..1733.30 rows=9612 width=28) (actual time=2.851..5.614 rows=9816 loops=1)
                                Hash Cond: (metrica.parceiro_id = parceiro_1.id)
                                Buffers: shared hit=1145
                                ->  Bitmap Heap Scan on metrica  (cost=270.91..1352.06 rows=9612 width=11) (actual time=0.667..1.984 rows=9816 loops=1)
                                      Recheck Cond: (periodo_id = 11)
                                      Heap Blocks: exact=961
                                      Buffers: shared hit=1014
                                      ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..268.51 rows=9612 width=0) (actual time=0.571..0.571 rows=9816 loops=1)
                                            Index Cond: (periodo_id = 11)
                                            Buffers: shared hit=53
                                ->  Hash  (cost=231.00..231.00 rows=10000 width=21) (actual time=2.118..2.118 rows=10000 loops=1)
                                      Buckets: 16384  Batches: 1  Memory Usage: 668kB
                                      Buffers: shared hit=131
                                      ->  Seq Scan on parceiro parceiro_1  (cost=0.00..231.00 rows=10000 width=21) (actual time=0.005..0.660 rows=10000 loops=1)
                                            Buffers: shared hit=131
              ->  Hash  (cost=2653.23..2653.23 rows=9578 width=12) (actual time=12.322..12.324 rows=10000 loops=1)
                    Buckets: 16384  Batches: 1  Memory Usage: 597kB
                    Buffers: shared hit=1136
                    ->  Subquery Scan on atual  (cost=2365.89..2653.23 rows=9578 width=12) (actual time=8.341..11.009 rows=10000 loops=1)
                          Buffers: shared hit=1136
                          ->  WindowAgg  (cost=2365.89..2557.45 rows=9578 width=40) (actual time=8.340..10.468 rows=10000 loops=1)
                                Buffers: shared hit=1136
                                ->  Sort  (cost=2365.89..2389.84 rows=9578 width=28) (actual time=8.324..8.818 rows=10000 loops=1)
                                      Sort Key: metrica_1.faturamento DESC, parceiro_2.nome
                                      Sort Method: quicksort  Memory: 932kB
                                      Buffers: shared hit=1136
                                      ->  Hash Join  (cost=626.65..1732.53 rows=9578 width=28) (actual time=2.783..5.669 rows=10000 loops=1)
                                            Hash Cond: (metrica_1.parceiro_id = parceiro_2.id)
                                            Buffers: shared hit=1136
                                            ->  Bitmap Heap Scan on metrica metrica_1  (cost=270.65..1351.37 rows=9578 width=11) (actual time=0.578..1.937 rows=10000 loops=1)
                                                  Recheck Cond: (periodo_id = 12)
                                                  Heap Blocks: exact=961
                                                  Buffers: shared hit=1005
                                                  ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..268.25 rows=9578 width=0) (actual time=0.502..0.502 rows=10000 loops=1)
                                                        Index Cond: (periodo_id = 12)
                                                        Buffers: shared hit=44
                                            ->  Hash  (cost=231.00..231.00 rows=10000 width=21) (actual time=2.138..2.139 rows=10000 loops=1)
                                                  Buckets: 16384  Batches: 1  Memory Usage: 668kB
                                                  Buffers: shared hit=131
                                                  ->  Seq Scan on parceiro parceiro_2  (cost=0.00..231.00 rows=10000 width=21) (actual time=0.003..0.566 rows=10000 loops=1)
                                                        Buffers: shared hit=131
        ->  Hash  (cost=231.00..231.00 rows=10000 width=21) (actual time=1.843..1.844 rows=10000 loops=1)
              Buckets: 16384  Batches: 1  Memory Usage: 668kB
              Buffers: shared hit=131
              ->  Seq Scan on parceiro  (cost=0.00..231.00 rows=10000 width=21) (actual time=0.003..0.623 rows=10000 loops=1)
                    Buffers: shared hit=131
Planning:
  Buffers: shared hit=24
Planning Time: 0.476 ms
Execution Time: 26.513 ms
```

</details>

### `indicadores-categoria`

A consulta filtra `metrica`. Se o planejador varrer, a conferência abaixo diz se foi escolha dele ou falta de índice.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo ORDER BY periodo.data_inicio DESC, peri…`
  - tempo no banco: **0.04 ms** · varredura: `periodo`
- `SELECT coalesce(sum(metrica.faturamento), %(coalesce_2)s::INTEGER) AS coalesce_1, coalesce(sum(metrica.pedido…`
  - tempo no banco: **3.79 ms** · varredura: `parceiro`
- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo WHERE periodo.data_inicio < %(data_inic…`
  - tempo no banco: **0.02 ms** · varredura: `periodo`
- `SELECT count(*) AS count_1, count(*) FILTER (WHERE historico_segmento.segmento = %(segmento_1)s AND historico…`
  - tempo no banco: **2.68 ms** · varredura: `parceiro`

<details><summary>Plano completo</summary>

```
Limit  (cost=1.18..1.18 rows=1 width=12) (actual time=0.025..0.025 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.18..1.21 rows=12 width=12) (actual time=0.024..0.024 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.005..0.006 rows=12 loops=1)
              Buffers: shared hit=1
Planning Time: 0.043 ms
Execution Time: 0.045 ms
```

</details>

<details><summary>Plano completo</summary>

```
Aggregate  (cost=1676.90..1676.91 rows=1 width=48) (actual time=3.696..3.697 rows=1 loops=1)
  Buffers: shared hit=1136
  ->  Hash Join  (cost=554.82..1660.70 rows=2159 width=11) (actual time=1.214..3.190 rows=2254 loops=1)
        Hash Cond: (metrica.parceiro_id = parceiro.id)
        Buffers: shared hit=1136
        ->  Bitmap Heap Scan on metrica  (cost=270.65..1351.37 rows=9578 width=15) (actual time=0.554..1.714 rows=10000 loops=1)
              Recheck Cond: (periodo_id = 12)
              Heap Blocks: exact=961
              Buffers: shared hit=1005
              ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..268.25 rows=9578 width=0) (actual time=0.452..0.452 rows=10000 loops=1)
                    Index Cond: (periodo_id = 12)
                    Buffers: shared hit=44
        ->  Hash  (cost=256.00..256.00 rows=2254 width=4) (actual time=0.639..0.639 rows=2254 loops=1)
              Buckets: 4096  Batches: 1  Memory Usage: 112kB
              Buffers: shared hit=131
              ->  Seq Scan on parceiro  (cost=0.00..256.00 rows=2254 width=4) (actual time=0.004..0.439 rows=2254 loops=1)
                    Filter: (categoria_id = 1)
                    Rows Removed by Filter: 7746
                    Buffers: shared hit=131
Planning:
  Buffers: shared hit=12
Planning Time: 0.205 ms
Execution Time: 3.793 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=1.20..1.21 rows=1 width=12) (actual time=0.016..0.016 rows=1 loops=1)
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
Planning Time: 0.073 ms
Execution Time: 0.022 ms
```

</details>

<details><summary>Plano completo</summary>

```
Aggregate  (cost=1335.43..1335.44 rows=1 width=16) (actual time=2.563..2.563 rows=1 loops=1)
  Buffers: shared hit=208
  ->  Bitmap Heap Scan on historico_segmento  (cost=122.05..973.46 rows=10033 width=8) (actual time=0.149..0.752 rows=10000 loops=1)
        Recheck Cond: (periodo_id = 12)
        Heap Blocks: exact=65
        Buffers: shared hit=77
        ->  Bitmap Index Scan on ix_segmento_periodo_segmento  (cost=0.00..119.54 rows=10033 width=0) (actual time=0.140..0.141 rows=10000 loops=1)
              Index Cond: (periodo_id = 12)
              Buffers: shared hit=12
  SubPlan 1
    ->  Seq Scan on parceiro  (cost=0.00..256.00 rows=2254 width=4) (actual time=0.004..0.537 rows=2254 loops=1)
          Filter: (categoria_id = 1)
          Rows Removed by Filter: 7746
          Buffers: shared hit=131
Planning Time: 0.061 ms
Execution Time: 2.683 ms
```

</details>

### `ranking-categoria`

A consulta filtra `metrica`. Se o planejador varrer, a conferência abaixo diz se foi escolha dele ou falta de índice.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo ORDER BY periodo.data_inicio DESC, peri…`
  - tempo no banco: **0.05 ms** · varredura: `periodo`
- `SELECT count(*) AS count_1 FROM (SELECT metrica.parceiro_id AS parceiro_id, metrica.faturamento AS faturament…`
  - tempo no banco: **7.98 ms** · varredura: `parceiro`
- `SELECT atual.parceiro_id, atual.faturamento, atual.pedidos, atual.posicao, parceiro.nome, categoria.nome AS n…`
  - tempo no banco: **15.61 ms** · varredura: `categoria`, `parceiro`
- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo WHERE periodo.data_inicio < %(data_inic…`
  - tempo no banco: **0.04 ms** · varredura: `periodo`
- `SELECT anterior.parceiro_id, anterior.posicao, anterior.faturamento FROM (SELECT metrica.parceiro_id AS parce…`
  - tempo no banco: **10.94 ms** · varredura: `parceiro`

<details><summary>Plano completo</summary>

```
Limit  (cost=1.18..1.18 rows=1 width=12) (actual time=0.024..0.024 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.18..1.21 rows=12 width=12) (actual time=0.023..0.023 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.007..0.008 rows=12 loops=1)
              Buffers: shared hit=1
Planning Time: 0.053 ms
Execution Time: 0.050 ms
```

</details>

<details><summary>Plano completo</summary>

```
Aggregate  (cost=2143.03..2143.04 rows=1 width=8) (actual time=7.710..7.712 rows=1 loops=1)
  Buffers: shared hit=1267
  ->  Hash Join  (cost=910.82..2137.63 rows=2159 width=0) (actual time=3.728..7.628 rows=2254 loops=1)
        Hash Cond: (metrica.parceiro_id = parceiro.id)
        Buffers: shared hit=1267
        ->  Hash Join  (cost=626.65..1732.53 rows=9578 width=40) (actual time=2.859..5.957 rows=10000 loops=1)
              Hash Cond: (metrica.parceiro_id = parceiro_1.id)
              Buffers: shared hit=1136
              ->  Bitmap Heap Scan on metrica  (cost=270.65..1351.37 rows=9578 width=11) (actual time=0.557..1.989 rows=10000 loops=1)
                    Recheck Cond: (periodo_id = 12)
                    Heap Blocks: exact=961
                    Buffers: shared hit=1005
                    ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..268.25 rows=9578 width=0) (actual time=0.482..0.482 rows=10000 loops=1)
                          Index Cond: (periodo_id = 12)
                          Buffers: shared hit=44
              ->  Hash  (cost=231.00..231.00 rows=10000 width=21) (actual time=2.204..2.205 rows=10000 loops=1)
                    Buckets: 16384  Batches: 1  Memory Usage: 668kB
                    Buffers: shared hit=131
                    ->  Seq Scan on parceiro parceiro_1  (cost=0.00..231.00 rows=10000 width=21) (actual time=0.005..0.722 rows=10000 loops=1)
                          Buffers: shared hit=131
        ->  Hash  (cost=256.00..256.00 rows=2254 width=4) (actual time=0.836..0.836 rows=2254 loops=1)
              Buckets: 4096  Batches: 1  Memory Usage: 112kB
              Buffers: shared hit=131
              ->  Seq Scan on parceiro  (cost=0.00..256.00 rows=2254 width=4) (actual time=0.005..0.586 rows=2254 loops=1)
                    Filter: (categoria_id = 1)
                    Rows Removed by Filter: 7746
                    Buffers: shared hit=131
Planning:
  Buffers: shared hit=18
Planning Time: 0.378 ms
Execution Time: 7.978 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=4412.61..4412.67 rows=25 width=54) (actual time=15.024..15.034 rows=25 loops=1)
  Buffers: shared hit=1476
  ->  Sort  (cost=4412.61..4418.16 rows=2221 width=54) (actual time=15.023..15.031 rows=25 loops=1)
        Sort Key: (row_number() OVER (?))
        Sort Method: top-N heapsort  Memory: 30kB
        Buffers: shared hit=1476
        ->  Hash Right Join  (cost=3438.68..4349.93 rows=2221 width=54) (actual time=13.310..14.745 rows=2254 loops=1)
              Hash Cond: (historico_segmento.parceiro_id = metrica.parceiro_id)
              Buffers: shared hit=1476
              ->  Bitmap Heap Scan on historico_segmento  (cost=122.05..973.46 rows=10033 width=8) (actual time=0.147..0.641 rows=10000 loops=1)
                    Recheck Cond: (periodo_id = 12)
                    Heap Blocks: exact=65
                    Buffers: shared hit=77
                    ->  Bitmap Index Scan on ix_segmento_periodo_segmento  (cost=0.00..119.54 rows=10033 width=0) (actual time=0.141..0.141 rows=10000 loops=1)
                          Index Cond: (periodo_id = 12)
                          Buffers: shared hit=12
              ->  Hash  (cost=3289.65..3289.65 rows=2159 width=50) (actual time=13.140..13.147 rows=2254 loops=1)
                    Buckets: 4096  Batches: 1  Memory Usage: 223kB
                    Buffers: shared hit=1399
                    ->  Hash Left Join  (cost=2936.73..3289.65 rows=2159 width=50) (actual time=9.659..12.721 rows=2254 loops=1)
                          Hash Cond: (parceiro.categoria_id = categoria.id)
                          Buffers: shared hit=1399
                          ->  Hash Join  (cost=2935.51..3280.35 rows=2159 width=44) (actual time=9.632..12.449 rows=2254 loops=1)
                                Hash Cond: (metrica.parceiro_id = parceiro.id)
                                Buffers: shared hit=1398
                                ->  WindowAgg  (cost=2365.89..2557.45 rows=9578 width=40) (actual time=7.472..9.435 rows=10000 loops=1)
                                      Buffers: shared hit=1136
                                      ->  Sort  (cost=2365.89..2389.84 rows=9578 width=32) (actual time=7.465..8.019 rows=10000 loops=1)
                                            Sort Key: metrica.faturamento DESC, parceiro_2.nome
                                            Sort Method: quicksort  Memory: 978kB
                                            Buffers: shared hit=1136
                                            ->  Hash Join  (cost=626.65..1732.53 rows=9578 width=32) (actual time=2.292..5.005 rows=10000 loops=1)
                                                  Hash Cond: (metrica.parceiro_id = parceiro_2.id)
                                                  Buffers: shared hit=1136
                                                  ->  Bitmap Heap Scan on metrica  (cost=270.65..1351.37 rows=9578 width=15) (actual time=0.544..1.827 rows=10000 loops=1)
                                                        Recheck Cond: (periodo_id = 12)
                                                        Heap Blocks: exact=961
                                                        Buffers: shared hit=1005
                                                        ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..268.25 rows=9578 width=0) (actual time=0.466..0.466 rows=10000 loops=1)
                                                              Index Cond: (periodo_id = 12)
                                                              Buffers: shared hit=44
                                                  ->  Hash  (cost=231.00..231.00 rows=10000 width=21) (actual time=1.667..1.667 rows=10000 loops=1)
                                                        Buckets: 16384  Batches: 1  Memory Usage: 668kB
                                                        Buffers: shared hit=131
                                                        ->  Seq Scan on parceiro parceiro_2  (cost=0.00..231.00 rows=10000 width=21) (actual time=0.004..0.528 rows=10000 loops=1)
                                                              Buffers: shared hit=131
                                ->  Hash  (cost=541.44..541.44 rows=2254 width=29) (actual time=2.140..2.140 rows=2254 loops=1)
                                      Buckets: 4096  Batches: 1  Memory Usage: 172kB
                                      Buffers: shared hit=262
                                      ->  Hash Join  (cost=284.18..541.44 rows=2254 width=29) (actual time=0.710..1.832 rows=2254 loops=1)
                                            Hash Cond: (parceiro.id = parceiro_1.id)
                                            Buffers: shared hit=262
                                            ->  Seq Scan on parceiro  (cost=0.00..231.00 rows=10000 width=25) (actual time=0.003..0.372 rows=10000 loops=1)
                                                  Buffers: shared hit=131
                                            ->  Hash  (cost=256.00..256.00 rows=2254 width=4) (actual time=0.684..0.684 rows=2254 loops=1)
                                                  Buckets: 4096  Batches: 1  Memory Usage: 112kB
                                                  Buffers: shared hit=131
                                                  ->  Seq Scan on parceiro parceiro_1  (cost=0.00..256.00 rows=2254 width=4) (actual time=0.003..0.464 rows=2254 loops=1)
                                                        Filter: (categoria_id = 1)
                                                        Rows Removed by Filter: 7746
                                                        Buffers: shared hit=131
                          ->  Hash  (cost=1.10..1.10 rows=10 width=14) (actual time=0.011..0.012 rows=10 loops=1)
                                Buckets: 1024  Batches: 1  Memory Usage: 9kB
                                Buffers: shared hit=1
                                ->  Seq Scan on categoria  (cost=0.00..1.10 rows=10 width=14) (actual time=0.003..0.004 rows=10 loops=1)
                                      Buffers: shared hit=1
Planning:
  Buffers: shared hit=49
Planning Time: 1.238 ms
Execution Time: 15.610 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=1.20..1.21 rows=1 width=12) (actual time=0.018..0.019 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.20..1.23 rows=11 width=12) (actual time=0.018..0.018 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.15 rows=11 width=12) (actual time=0.004..0.005 rows=11 loops=1)
              Filter: (data_inicio < '2026-09-21'::date)
              Rows Removed by Filter: 1
              Buffers: shared hit=1
Planning:
  Buffers: shared hit=2
Planning Time: 0.111 ms
Execution Time: 0.035 ms
```

</details>

<details><summary>Plano completo</summary>

```
Subquery Scan on anterior  (cost=2369.23..2705.65 rows=25 width=19) (actual time=8.197..10.663 rows=24 loops=1)
  Filter: (anterior.parceiro_id = ANY ('{4133,4648,8156,2515,3134,3997,9809,460,2744,7117,6772,7651,9344,4676,3721,9527,9814,3453,5998,5257,1395,9035,600,5022,3133}'::integer[]))
  Rows Removed by Filter: 9792
  Buffers: shared hit=1145
  ->  WindowAgg  (cost=2369.17..2561.41 rows=9612 width=40) (actual time=8.192..10.157 rows=9816 loops=1)
        Buffers: shared hit=1145
        ->  Sort  (cost=2369.17..2393.20 rows=9612 width=28) (actual time=8.183..8.758 rows=9816 loops=1)
              Sort Key: metrica.faturamento DESC, parceiro.nome
              Sort Method: quicksort  Memory: 921kB
              Buffers: shared hit=1145
              ->  Hash Join  (cost=626.91..1733.30 rows=9612 width=28) (actual time=2.448..5.326 rows=9816 loops=1)
                    Hash Cond: (metrica.parceiro_id = parceiro.id)
                    Buffers: shared hit=1145
                    ->  Bitmap Heap Scan on metrica  (cost=270.91..1352.06 rows=9612 width=11) (actual time=0.666..2.010 rows=9816 loops=1)
                          Recheck Cond: (periodo_id = 11)
                          Heap Blocks: exact=961
                          Buffers: shared hit=1014
                          ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..268.51 rows=9612 width=0) (actual time=0.435..0.436 rows=9816 loops=1)
                                Index Cond: (periodo_id = 11)
                                Buffers: shared hit=53
                    ->  Hash  (cost=231.00..231.00 rows=10000 width=21) (actual time=1.719..1.719 rows=10000 loops=1)
                          Buckets: 16384  Batches: 1  Memory Usage: 668kB
                          Buffers: shared hit=131
                          ->  Seq Scan on parceiro  (cost=0.00..231.00 rows=10000 width=21) (actual time=0.004..0.558 rows=10000 loops=1)
                                Buffers: shared hit=131
Planning:
  Buffers: shared hit=12
Planning Time: 0.228 ms
Execution Time: 10.944 ms
```

</details>

### `serie-categoria`

Como a da rede: a série agrega todos os períodos, e a categoria só escolhe de quais parceiros.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim, sum(metrica.faturamento) AS sum_1, sum(metrica.pedi…`
  - tempo no banco: **19.07 ms** · varredura: `metrica`, `parceiro`, `periodo`

<details><summary>Plano completo</summary>

```
Sort  (cost=2969.10..2969.13 rows=12 width=52) (actual time=18.985..18.987 rows=12 loops=1)
  Sort Key: periodo.data_inicio, periodo.id
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=1093
  ->  HashAggregate  (cost=2968.74..2968.89 rows=12 width=52) (actual time=18.977..18.981 rows=12 loops=1)
        Group Key: periodo.id
        Batches: 1  Memory Usage: 24kB
        Buffers: shared hit=1093
        ->  Hash Right Join  (cost=285.44..2776.14 rows=25680 width=23) (actual time=0.816..15.808 rows=25611 loops=1)
              Hash Cond: (metrica.periodo_id = periodo.id)
              Buffers: shared hit=1093
              ->  Hash Join  (cost=284.18..2683.65 rows=25680 width=15) (actual time=0.796..12.989 rows=25611 loops=1)
                    Hash Cond: (metrica.parceiro_id = parceiro.id)
                    Buffers: shared hit=1092
                    ->  Seq Scan on metrica  (cost=0.00..2100.29 rows=113929 width=19) (actual time=0.002..4.514 rows=113929 loops=1)
                          Buffers: shared hit=961
                    ->  Hash  (cost=256.00..256.00 rows=2254 width=4) (actual time=0.767..0.767 rows=2254 loops=1)
                          Buckets: 4096  Batches: 1  Memory Usage: 112kB
                          Buffers: shared hit=131
                          ->  Seq Scan on parceiro  (cost=0.00..256.00 rows=2254 width=4) (actual time=0.004..0.535 rows=2254 loops=1)
                                Filter: (categoria_id = 1)
                                Rows Removed by Filter: 7746
                                Buffers: shared hit=131
              ->  Hash  (cost=1.12..1.12 rows=12 width=12) (actual time=0.013..0.013 rows=12 loops=1)
                    Buckets: 1024  Batches: 1  Memory Usage: 9kB
                    Buffers: shared hit=1
                    ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.003..0.003 rows=12 loops=1)
                          Buffers: shared hit=1
Planning:
  Buffers: shared hit=16
Planning Time: 0.304 ms
Execution Time: 19.075 ms
```

</details>

### `segmentos-categoria`

A consulta filtra `historico_segmento`. Se o planejador varrer, a conferência abaixo diz se foi escolha dele ou falta de índice.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo ORDER BY periodo.data_inicio DESC, peri…`
  - tempo no banco: **0.01 ms** · varredura: `periodo`
- `SELECT historico_segmento.segmento, count(*) AS count_1 FROM historico_segmento WHERE historico_segmento.peri…`
  - tempo no banco: **2.77 ms** · varredura: `parceiro`

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
Planning Time: 0.032 ms
Execution Time: 0.013 ms
```

</details>

<details><summary>Plano completo</summary>

```
Sort  (cost=1295.40..1295.41 rows=5 width=12) (actual time=2.632..2.633 rows=5 loops=1)
  Sort Key: (count(*)) DESC, historico_segmento.segmento
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=208
  ->  HashAggregate  (cost=1295.29..1295.34 rows=5 width=12) (actual time=2.628..2.629 rows=5 loops=1)
        Group Key: historico_segmento.segmento
        Batches: 1  Memory Usage: 24kB
        Buffers: shared hit=208
        ->  Hash Join  (cost=406.22..1283.98 rows=2261 width=4) (actual time=1.039..2.432 rows=2254 loops=1)
              Hash Cond: (historico_segmento.parceiro_id = parceiro.id)
              Buffers: shared hit=208
              ->  Bitmap Heap Scan on historico_segmento  (cost=122.05..973.46 rows=10033 width=8) (actual time=0.154..0.713 rows=10000 loops=1)
                    Recheck Cond: (periodo_id = 12)
                    Heap Blocks: exact=65
                    Buffers: shared hit=77
                    ->  Bitmap Index Scan on ix_segmento_periodo_segmento  (cost=0.00..119.54 rows=10033 width=0) (actual time=0.147..0.148 rows=10000 loops=1)
                          Index Cond: (periodo_id = 12)
                          Buffers: shared hit=12
              ->  Hash  (cost=256.00..256.00 rows=2254 width=4) (actual time=0.853..0.854 rows=2254 loops=1)
                    Buckets: 4096  Batches: 1  Memory Usage: 112kB
                    Buffers: shared hit=131
                    ->  Seq Scan on parceiro  (cost=0.00..256.00 rows=2254 width=4) (actual time=0.004..0.601 rows=2254 loops=1)
                          Filter: (categoria_id = 1)
                          Rows Removed by Filter: 7746
                          Buffers: shared hit=131
Planning:
  Buffers: shared hit=15
Planning Time: 0.236 ms
Execution Time: 2.768 ms
```

</details>

### `decisao`

A consulta filtra `previsao`. Se o planejador varrer, a conferência abaixo diz se foi escolha dele ou falta de índice.

- `SELECT periodo.id AS periodo_id, periodo.data_inicio AS periodo_data_inicio, periodo.data_fim AS periodo_data…`
  - tempo no banco: **0.01 ms** · varredura: `periodo`
- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo WHERE EXISTS (SELECT * FROM metrica WHE…`
  - tempo no banco: **0.11 ms** · varredura: `periodo`
- `SELECT count(*) AS count_1, sum(com_medido.faturamento_previsto) AS sum_1, sum(com_medido.medido) AS sum_2 FR…`
  - tempo no banco: **6.66 ms** · varredura: `previsao`
  - a varredura em `previsao` é **escolha do planejador**: com `enable_seqscan = off` o mesmo filtro usa `ix_metrica_periodo_faturamento`, `ix_previsao_periodo_versao` e leva 6.28 ms. O índice cobre a consulta.
- `SELECT com_medido.parceiro_id, parceiro.nome, categoria.nome AS nome_1, com_medido.probabilidade_queda, com_m…`
  - tempo no banco: **11.17 ms** · varredura: `categoria`, `parceiro`, `previsao`
  - a varredura em `previsao` é **escolha do planejador**: com `enable_seqscan = off` o mesmo filtro usa `categoria_pkey`, `ix_metrica_periodo_faturamento`, `ix_previsao_periodo_versao`, `parceiro_pkey` e leva 12.19 ms. O índice cobre a consulta.

<details><summary>Plano completo</summary>

```
Seq Scan on periodo  (cost=0.00..1.15 rows=1 width=12) (actual time=0.004..0.005 rows=1 loops=1)
  Filter: (id = 12)
  Rows Removed by Filter: 11
  Buffers: shared hit=1
Planning Time: 0.037 ms
Execution Time: 0.008 ms
```

</details>

<details><summary>Plano completo</summary>

```
Sort  (cost=7.33..7.36 rows=12 width=12) (actual time=0.094..0.094 rows=12 loops=1)
  Sort Key: periodo.data_inicio DESC, periodo.id DESC
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=38
  ->  Nested Loop Semi Join  (cost=0.42..7.12 rows=12 width=12) (actual time=0.023..0.090 rows=12 loops=1)
        Buffers: shared hit=38
        ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.002..0.003 rows=12 loops=1)
              Buffers: shared hit=1
        ->  Index Only Scan using ix_metrica_periodo_faturamento on metrica  (cost=0.42..296.56 rows=9494 width=4) (actual time=0.007..0.007 rows=1 loops=12)
              Index Cond: (periodo_id = periodo.id)
              Heap Fetches: 0
              Buffers: shared hit=37
Planning:
  Buffers: shared hit=8
Planning Time: 0.164 ms
Execution Time: 0.111 ms
```

</details>

<details><summary>Plano completo</summary>

```
Aggregate  (cost=1817.37..1817.38 rows=1 width=72) (actual time=6.449..6.450 rows=1 loops=1)
  Buffers: shared hit=1099
  ->  Hash Join  (cost=639.65..1745.53 rows=9578 width=14) (actual time=2.789..5.462 rows=10000 loops=1)
        Hash Cond: (metrica.parceiro_id = previsao.parceiro_id)
        Buffers: shared hit=1099
        ->  Bitmap Heap Scan on metrica  (cost=270.65..1351.37 rows=9578 width=11) (actual time=0.588..1.913 rows=10000 loops=1)
              Recheck Cond: (periodo_id = 12)
              Heap Blocks: exact=961
              Buffers: shared hit=1005
              ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..268.25 rows=9578 width=0) (actual time=0.502..0.502 rows=10000 loops=1)
                    Index Cond: (periodo_id = 12)
                    Buffers: shared hit=44
        ->  Hash  (cost=244.00..244.00 rows=10000 width=11) (actual time=2.132..2.133 rows=10000 loops=1)
              Buckets: 16384  Batches: 1  Memory Usage: 562kB
              Buffers: shared hit=94
              ->  Seq Scan on previsao  (cost=0.00..244.00 rows=10000 width=11) (actual time=0.004..1.031 rows=10000 loops=1)
                    Filter: ((periodo_base_id = 12) AND ((modelo_versao)::text = 'rede-1'::text))
                    Buffers: shared hit=94
Planning:
  Buffers: shared hit=12
Planning Time: 0.193 ms
Execution Time: 6.657 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=2322.79..2322.80 rows=5 width=53) (actual time=10.747..10.750 rows=5 loops=1)
  Buffers: shared hit=1231
  ->  Sort  (cost=2322.79..2346.74 rows=9578 width=53) (actual time=10.746..10.748 rows=5 loops=1)
        Sort Key: previsao.probabilidade_queda DESC, parceiro.nome
        Sort Method: top-N heapsort  Memory: 26kB
        Buffers: shared hit=1231
        ->  Hash Left Join  (cost=996.87..2163.70 rows=9578 width=53) (actual time=4.616..9.613 rows=10000 loops=1)
              Hash Cond: (parceiro.categoria_id = categoria.id)
              Buffers: shared hit=1231
              ->  Hash Join  (cost=995.65..2126.68 rows=9578 width=47) (actual time=4.595..8.584 rows=10000 loops=1)
                    Hash Cond: (metrica.parceiro_id = parceiro.id)
                    Buffers: shared hit=1230
                    ->  Hash Join  (cost=639.65..1745.53 rows=9578 width=30) (actual time=2.635..5.365 rows=10000 loops=1)
                          Hash Cond: (metrica.parceiro_id = previsao.parceiro_id)
                          Buffers: shared hit=1099
                          ->  Bitmap Heap Scan on metrica  (cost=270.65..1351.37 rows=9578 width=11) (actual time=0.502..1.685 rows=10000 loops=1)
                                Recheck Cond: (periodo_id = 12)
                                Heap Blocks: exact=961
                                Buffers: shared hit=1005
                                ->  Bitmap Index Scan on ix_metrica_periodo_faturamento  (cost=0.00..268.25 rows=9578 width=0) (actual time=0.422..0.422 rows=10000 loops=1)
                                      Index Cond: (periodo_id = 12)
                                      Buffers: shared hit=44
                          ->  Hash  (cost=244.00..244.00 rows=10000 width=19) (actual time=2.064..2.064 rows=10000 loops=1)
                                Buckets: 16384  Batches: 1  Memory Usage: 667kB
                                Buffers: shared hit=94
                                ->  Seq Scan on previsao  (cost=0.00..244.00 rows=10000 width=19) (actual time=0.004..0.930 rows=10000 loops=1)
                                      Filter: ((periodo_base_id = 12) AND ((modelo_versao)::text = 'rede-1'::text))
                                      Buffers: shared hit=94
                    ->  Hash  (cost=231.00..231.00 rows=10000 width=25) (actual time=1.893..1.893 rows=10000 loops=1)
                          Buckets: 16384  Batches: 1  Memory Usage: 707kB
                          Buffers: shared hit=131
                          ->  Seq Scan on parceiro  (cost=0.00..231.00 rows=10000 width=25) (actual time=0.006..0.654 rows=10000 loops=1)
                                Buffers: shared hit=131
              ->  Hash  (cost=1.10..1.10 rows=10 width=14) (actual time=0.010..0.010 rows=10 loops=1)
                    Buckets: 1024  Batches: 1  Memory Usage: 9kB
                    Buffers: shared hit=1
                    ->  Seq Scan on categoria  (cost=0.00..1.10 rows=10 width=14) (actual time=0.003..0.003 rows=10 loops=1)
                          Buffers: shared hit=1
Planning:
  Buffers: shared hit=40
Planning Time: 1.034 ms
Execution Time: 11.169 ms
```

</details>

### `busca`

A consulta filtra `parceiro`. Se o planejador varrer, a conferência abaixo diz se foi escolha dele ou falta de índice.

- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo ORDER BY periodo.data_inicio DESC, peri…`
  - tempo no banco: **0.01 ms** · varredura: `periodo`
- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo WHERE periodo.data_inicio < %(data_inic…`
  - tempo no banco: **0.01 ms** · varredura: `periodo`
- `SELECT periodo.id, periodo.data_inicio, periodo.data_fim FROM periodo WHERE EXISTS (SELECT * FROM metrica WHE…`
  - tempo no banco: **0.12 ms** · varredura: `periodo`
- `SELECT count(*) AS count_1 FROM (SELECT parceiro.id AS id, parceiro.nome AS nome, parceiro.nome_normalizado A…`
  - tempo no banco: **0.32 ms** · varredura: nenhuma
- `SELECT parceiro.id, parceiro.nome, parceiro.nome_normalizado, parceiro.categoria_id, parceiro.origem_categori…`
  - tempo no banco: **0.92 ms** · varredura: nenhuma

<details><summary>Plano completo</summary>

```
Sort  (cost=1.34..1.37 rows=12 width=12) (actual time=0.009..0.009 rows=12 loops=1)
  Sort Key: data_inicio DESC, id DESC
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=1
  ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.003..0.004 rows=12 loops=1)
        Buffers: shared hit=1
Planning Time: 0.043 ms
Execution Time: 0.015 ms
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
              Filter: (data_inicio < '2026-09-21'::date)
              Rows Removed by Filter: 1
              Buffers: shared hit=1
Planning:
  Buffers: shared hit=2
Planning Time: 0.071 ms
Execution Time: 0.013 ms
```

</details>

<details><summary>Plano completo</summary>

```
Sort  (cost=7.33..7.36 rows=12 width=12) (actual time=0.101..0.102 rows=12 loops=1)
  Sort Key: periodo.data_inicio DESC, periodo.id DESC
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=38
  ->  Nested Loop Semi Join  (cost=0.42..7.12 rows=12 width=12) (actual time=0.030..0.096 rows=12 loops=1)
        Buffers: shared hit=38
        ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.003..0.004 rows=12 loops=1)
              Buffers: shared hit=1
        ->  Index Only Scan using ix_metrica_periodo_faturamento on metrica  (cost=0.42..296.56 rows=9494 width=4) (actual time=0.007..0.007 rows=1 loops=12)
              Index Cond: (periodo_id = periodo.id)
              Heap Fetches: 0
              Buffers: shared hit=37
Planning:
  Buffers: shared hit=8
Planning Time: 0.233 ms
Execution Time: 0.124 ms
```

</details>

<details><summary>Plano completo</summary>

```
Aggregate  (cost=175.44..175.45 rows=1 width=8) (actual time=0.284..0.285 rows=1 loops=1)
  Buffers: shared hit=137
  ->  Bitmap Heap Scan on parceiro  (cost=33.84..173.68 rows=707 width=0) (actual time=0.099..0.261 rows=625 loops=1)
        Recheck Cond: ((nome_normalizado)::text ~~ '%praca%'::text)
        Heap Blocks: exact=130
        Buffers: shared hit=137
        ->  Bitmap Index Scan on ix_parceiro_nome_normalizado_trgm  (cost=0.00..33.66 rows=707 width=0) (actual time=0.087..0.087 rows=625 loops=1)
              Index Cond: ((nome_normalizado)::text ~~ '%praca%'::text)
              Buffers: shared hit=7
Planning:
  Buffers: shared hit=1
Planning Time: 0.162 ms
Execution Time: 0.323 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=19.54..915.74 rows=50 width=347) (actual time=0.501..0.831 rows=50 loops=1)
  Buffers: shared hit=1773
  ->  Incremental Sort  (cost=19.54..12727.71 rows=709 width=347) (actual time=0.501..0.828 rows=50 loops=1)
        Sort Key: parceiro.nome, parceiro.id
        Presorted Key: parceiro.nome
        Full-sort Groups: 2  Sort Method: quicksort  Average Memory: 29kB  Peak Memory: 29kB
        Buffers: shared hit=1773
        ->  Nested Loop Left Join  (cost=1.57..12695.88 rows=709 width=347) (actual time=0.204..0.807 rows=51 loops=1)
              Buffers: shared hit=1773
              ->  Nested Loop Left Join  (cost=1.16..8854.56 rows=707 width=343) (actual time=0.193..0.677 rows=51 loops=1)
                    Buffers: shared hit=1569
                    ->  Nested Loop Left Join  (cost=0.87..8097.16 rows=707 width=335) (actual time=0.183..0.572 rows=51 loops=1)
                          Buffers: shared hit=1416
                          ->  Nested Loop Left Join  (cost=0.58..4544.22 rows=707 width=328) (actual time=0.174..0.502 rows=51 loops=1)
                                Buffers: shared hit=1265
                                ->  Index Scan using ix_parceiro_nome on parceiro  (cost=0.29..991.28 rows=707 width=317) (actual time=0.161..0.368 rows=51 loops=1)
                                      Filter: ((nome_normalizado)::text ~~ '%praca%'::text)
                                      Rows Removed by Filter: 1113
                                      Buffers: shared hit=1112
                                ->  Index Scan using uq_metrica_parceiro_periodo on metrica  (cost=0.29..5.03 rows=1 width=15) (actual time=0.002..0.002 rows=1 loops=51)
                                      Index Cond: ((parceiro_id = parceiro.id) AND (periodo_id = 12))
                                      Buffers: shared hit=153
                          ->  Index Scan using uq_metrica_parceiro_periodo on metrica metrica_1  (cost=0.29..5.03 rows=1 width=11) (actual time=0.001..0.001 rows=1 loops=51)
                                Index Cond: ((parceiro_id = parceiro.id) AND (periodo_id = 11))
                                Buffers: shared hit=151
                    ->  Index Scan using uq_previsao_parceiro_periodo_modelo on previsao  (cost=0.29..1.07 rows=1 width=12) (actual time=0.002..0.002 rows=1 loops=51)
                          Index Cond: ((parceiro_id = parceiro.id) AND (periodo_base_id = 12) AND ((modelo_versao)::text = 'rede-1'::text))
                          Buffers: shared hit=153
              ->  Index Scan using uq_segmento_parceiro_periodo on historico_segmento  (cost=0.42..5.43 rows=1 width=8) (actual time=0.002..0.002 rows=1 loops=51)
                    Index Cond: ((parceiro_id = parceiro.id) AND (periodo_id = 12))
                    Buffers: shared hit=204
Planning:
  Buffers: shared hit=52
Planning Time: 1.116 ms
Execution Time: 0.917 ms
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
  - tempo no banco: **0.75 ms** · varredura: `parceiro`
- `SELECT parceiro.id, parceiro.nome, parceiro.nome_normalizado, parceiro.categoria_id, parceiro.origem_categori…`
  - tempo no banco: **0.78 ms** · varredura: nenhuma

<details><summary>Plano completo</summary>

```
Sort  (cost=1.34..1.37 rows=12 width=12) (actual time=0.008..0.009 rows=12 loops=1)
  Sort Key: data_inicio DESC, id DESC
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=1
  ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.003..0.004 rows=12 loops=1)
        Buffers: shared hit=1
Planning Time: 0.046 ms
Execution Time: 0.014 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=1.20..1.21 rows=1 width=12) (actual time=0.007..0.007 rows=1 loops=1)
  Buffers: shared hit=1
  ->  Sort  (cost=1.20..1.23 rows=11 width=12) (actual time=0.006..0.007 rows=1 loops=1)
        Sort Key: data_inicio DESC, id DESC
        Sort Method: top-N heapsort  Memory: 25kB
        Buffers: shared hit=1
        ->  Seq Scan on periodo  (cost=0.00..1.15 rows=11 width=12) (actual time=0.003..0.003 rows=11 loops=1)
              Filter: (data_inicio < '2026-09-21'::date)
              Rows Removed by Filter: 1
              Buffers: shared hit=1
Planning:
  Buffers: shared hit=2
Planning Time: 0.060 ms
Execution Time: 0.013 ms
```

</details>

<details><summary>Plano completo</summary>

```
Sort  (cost=7.33..7.36 rows=12 width=12) (actual time=0.096..0.096 rows=12 loops=1)
  Sort Key: periodo.data_inicio DESC, periodo.id DESC
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=38
  ->  Nested Loop Semi Join  (cost=0.42..7.12 rows=12 width=12) (actual time=0.022..0.092 rows=12 loops=1)
        Buffers: shared hit=38
        ->  Seq Scan on periodo  (cost=0.00..1.12 rows=12 width=12) (actual time=0.002..0.003 rows=12 loops=1)
              Buffers: shared hit=1
        ->  Index Only Scan using ix_metrica_periodo_faturamento on metrica  (cost=0.42..296.56 rows=9494 width=4) (actual time=0.007..0.007 rows=1 loops=12)
              Index Cond: (periodo_id = periodo.id)
              Heap Fetches: 0
              Buffers: shared hit=37
Planning:
  Buffers: shared hit=8
Planning Time: 0.350 ms
Execution Time: 0.114 ms
```

</details>

<details><summary>Plano completo</summary>

```
Aggregate  (cost=256.00..256.01 rows=1 width=8) (actual time=0.739..0.739 rows=1 loops=1)
  Buffers: shared hit=131
  ->  Seq Scan on parceiro  (cost=0.00..231.00 rows=10000 width=0) (actual time=0.003..0.420 rows=10000 loops=1)
        Buffers: shared hit=131
Planning Time: 0.127 ms
Execution Time: 0.748 ms
```

</details>

<details><summary>Plano completo</summary>

```
Limit  (cost=4.61..157.53 rows=50 width=347) (actual time=0.343..0.689 rows=50 loops=1)
  Buffers: shared hit=711
  ->  Incremental Sort  (cost=4.61..30690.97 rows=10033 width=347) (actual time=0.343..0.686 rows=50 loops=1)
        Sort Key: parceiro.nome, parceiro.id
        Presorted Key: parceiro.nome
        Full-sort Groups: 2  Sort Method: quicksort  Average Memory: 29kB  Peak Memory: 29kB
        Buffers: shared hit=711
        ->  Nested Loop Left Join  (cost=1.57..30240.64 rows=10033 width=347) (actual time=0.060..0.664 rows=51 loops=1)
              Buffers: shared hit=711
              ->  Nested Loop Left Join  (cost=1.16..21046.15 rows=10000 width=343) (actual time=0.047..0.526 rows=51 loops=1)
                    Buffers: shared hit=507
                    ->  Nested Loop Left Join  (cost=0.87..17431.22 rows=10000 width=335) (actual time=0.037..0.424 rows=51 loops=1)
                          Buffers: shared hit=354
                          ->  Nested Loop Left Join  (cost=0.58..9198.75 rows=10000 width=328) (actual time=0.027..0.186 rows=51 loops=1)
                                Buffers: shared hit=201
                                ->  Index Scan using ix_parceiro_nome on parceiro  (cost=0.29..966.28 rows=10000 width=317) (actual time=0.016..0.040 rows=51 loops=1)
                                      Buffers: shared hit=48
                                ->  Index Scan using uq_metrica_parceiro_periodo on metrica  (cost=0.29..0.82 rows=1 width=15) (actual time=0.002..0.002 rows=1 loops=51)
                                      Index Cond: ((parceiro_id = parceiro.id) AND (periodo_id = 12))
                                      Buffers: shared hit=153
                          ->  Index Scan using uq_metrica_parceiro_periodo on metrica metrica_1  (cost=0.29..0.82 rows=1 width=11) (actual time=0.004..0.004 rows=1 loops=51)
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
Planning Time: 1.092 ms
Execution Time: 0.776 ms
```

</details>

## Índices em uso

- `ix_metrica_periodo_faturamento`
- `ix_parceiro_nome`
- `ix_parceiro_nome_normalizado_trgm`
- `ix_segmento_periodo_segmento`
- `uq_metrica_parceiro_periodo`
- `uq_previsao_parceiro_periodo_modelo`
- `uq_segmento_parceiro_periodo`

