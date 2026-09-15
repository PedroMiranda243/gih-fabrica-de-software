"""Gerador de dados sintéticos — história H28.

Produz uma rede de parceiros com histórico de faturamento, para três usos que
dependem dele: desenvolver o painel sem esperar dados, treinar o modelo
preditivo, e dar escala ao benchmark do otimizador.

**Nenhum dado real entra aqui** (CLAUDE.md, regra 2.1). Os nomes são compostos
a partir de listas genéricas e não correspondem a estabelecimentos existentes.

O que torna os dados úteis, e não apenas aleatórios:

- O faturamento segue distribuição de cauda longa. Sem isso não existiria um
  Top 15 destacado nem uma cauda esquecida — que é o problema que o produto
  resolve.
- Cada parceiro recebe um **perfil de trajetória** (em ascensão, em queda,
  estável, volátil, recém-chegado). É o que dá o que segmentar e o que prever;
  série puramente aleatória não tem tendência para o modelo aprender.
- Há sazonalidade semanal, porque o faturamento real de delivery tem.

Uso:
    python scripts/gerar_dados_sinteticos.py --parceiros 2000 --periodos 12
    python scripts/gerar_dados_sinteticos.py --parceiros 200 --periodos 8 --limpar
"""
from __future__ import annotations

import argparse
import random
import sys
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import insert, text

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "api"))

from app.db import Sessao, engine  # noqa: E402
from app.modelos import (  # noqa: E402
    AcaoComercial,
    Categoria,
    Importacao,
    Metrica,
    OrigemCategoria,
    OrigemImportacao,
    Parceiro,
    Perfil,
    Periodo,
    StatusComercial,
    Usuario,
)

# --------------------------------------------------------------------------- vocabulário
# Composição genérica. Qualquer semelhança com estabelecimento real seria
# coincidência de duas listas curtas — e é por isso que elas são curtas e banais.
PREFIXOS = [
    "Cantina", "Empório", "Casa", "Ponto", "Sabor", "Recanto", "Espaço",
    "Villa", "Quintal", "Celeiro", "Forno", "Parada", "Esquina", "Varanda",
]
NUCLEOS = [
    "do Chef", "da Serra", "Central", "Express", "Popular", "do Vale",
    "Real", "Dourado", "Verde", "do Norte", "Bom Prato", "da Praça",
    "Azul", "do Sol", "Mineiro", "Caseiro",
]

CATEGORIAS = {
    # categoria: (ticket médio típico, peso na rede)
    "Restaurante": (48.0, 22),
    "Lanchonete": (32.0, 20),
    "Pizzaria": (62.0, 12),
    "Padaria": (26.0, 10),
    "Mercado": (85.0, 9),
    "Açaí e sorvetes": (28.0, 8),
    "Farmácia": (54.0, 6),
    "Bebidas": (70.0, 5),
    "Gás e água": (95.0, 4),
    "Petshop": (58.0, 4),
}

ACOES = [
    ("Cupom de primeira compra", 120.00, 0.08),
    ("Destaque na vitrine", 260.00, 0.14),
    ("Campanha de categoria", 480.00, 0.22),
    ("Visita de relacionamento", 90.00, 0.06),
    ("Frete subsidiado", 350.00, 0.18),
]

# Perfis de trajetória: (rótulo, peso, tendência por período, volatilidade)
PERFIS = [
    ("estavel", 52, 0.000, 0.06),
    ("ascensao", 16, 0.045, 0.07),
    ("queda", 14, -0.040, 0.07),
    ("volatil", 12, 0.000, 0.22),
    ("recem_chegado", 6, 0.060, 0.10),
]


def nome_parceiro(rng: random.Random, usados: set[str]) -> str:
    for _ in range(200):
        nome = f"{rng.choice(PREFIXOS)} {rng.choice(NUCLEOS)}"
        if nome not in usados:
            usados.add(nome)
            return nome
    # Listas esgotadas: sufixo numérico mantém a unicidade sem inventar nome.
    n = 2
    while True:
        nome = f"{rng.choice(PREFIXOS)} {rng.choice(NUCLEOS)} {n}"
        if nome not in usados:
            usados.add(nome)
            return nome
        n += 1


def escolher_ponderado(rng: random.Random, itens: list, pesos: list[int]):
    return rng.choices(itens, weights=pesos, k=1)[0]


def gerar(n_parceiros: int, n_periodos: int, semente: int, limpar: bool) -> None:
    rng = random.Random(semente)

    with Sessao() as s:
        if limpar:
            print("Limpando dados existentes...")
            s.execute(
                text(
                    "TRUNCATE metrica, importacao, historico_segmento, previsao,"
                    " item_plano, mensagem, plano_campanha, execucao_otimizador,"
                    " periodo, parceiro, categoria, acao_comercial RESTART IDENTITY CASCADE"
                )
            )
            s.commit()

        # ------------------------------------------------------------ catálogos
        categorias = {}
        for nome in CATEGORIAS:
            c = Categoria(nome=nome)
            s.add(c)
            categorias[nome] = c
        for nome, custo, uplift in ACOES:
            s.add(
                AcaoComercial(
                    nome=nome, custo_unitario=Decimal(str(custo)), uplift_esperado_pct=uplift
                )
            )
        s.flush()

        # Um usuário para constar como autor das importações — a FK exige.
        autor = s.query(Usuario).filter_by(login="gerador").one_or_none()
        if autor is None:
            autor = Usuario(
                login="gerador",
                nome="Gerador de dados",
                senha_hash="!sem-acesso",  # não é credencial válida
                perfil=Perfil.ADMINISTRADOR,
                ativo=False,
            )
            s.add(autor)
            s.flush()

        # ------------------------------------------------------------ parceiros
        print(f"Gerando {n_parceiros} parceiros...")
        nomes_cat = list(CATEGORIAS)
        pesos_cat = [CATEGORIAS[c][1] for c in nomes_cat]
        rotulos_perfil = [p[0] for p in PERFIS]
        pesos_perfil = [p[1] for p in PERFIS]

        usados: set[str] = set()
        parceiros = []
        for _ in range(n_parceiros):
            cat = escolher_ponderado(rng, nomes_cat, pesos_cat)
            perfil = escolher_ponderado(rng, rotulos_perfil, pesos_perfil)

            # Cauda longa: lognormal concentra a maior parte da rede embaixo e
            # deixa poucos no topo — que é a forma do problema.
            #
            # sigma calibrado para o Top 15 ficar por volta de um terço do
            # faturamento. Com 0,85 a concentração cai para ~22%, e aí a rede
            # não ilustra a premissa do produto: o topo precisa pesar o
            # bastante para que ignorar a cauda pareça racional.
            base = rng.lognormvariate(mu=7.6, sigma=1.15)

            p = Parceiro(
                nome=nome_parceiro(rng, usados),
                categoria_id=categorias[cat].id,
                origem_categoria=OrigemCategoria.MANUAL,
                status=StatusComercial.ATIVO,
                ativo=True,
            )
            parceiros.append((p, cat, perfil, base))
            s.add(p)
        s.flush()

        # ------------------------------------------------------------- períodos
        print(f"Gerando {n_periodos} períodos semanais...")
        fim = date.today() - timedelta(days=date.today().weekday() + 1)
        periodos = []
        for i in range(n_periodos - 1, -1, -1):
            f = fim - timedelta(weeks=i)
            periodos.append(Periodo(data_inicio=f - timedelta(days=6), data_fim=f))
        s.add_all(periodos)
        s.flush()

        importacoes = []
        for per in periodos:
            imp = Importacao(
                periodo_id=per.id,
                usuario_id=autor.id,
                origem=OrigemImportacao.CSV,
                total_gravado=0,
                total_rejeitado=0,
            )
            importacoes.append(imp)
            s.add(imp)
        s.flush()

        # -------------------------------------------------------------- métricas
        print("Gerando séries de faturamento...")
        tendencia = {p[0]: p[2] for p in PERFIS}
        volatilidade = {p[0]: p[3] for p in PERFIS}
        linhas = []

        for parceiro, cat, perfil, base in parceiros:
            ticket = CATEGORIAS[cat][0] * rng.uniform(0.8, 1.25)
            # Recém-chegado só aparece nos períodos finais.
            entra_em = (
                rng.randint(max(0, n_periodos - 3), n_periodos - 1)
                if perfil == "recem_chegado"
                else 0
            )

            for i, (per, imp) in enumerate(zip(periodos, importacoes)):
                if i < entra_em:
                    continue
                passos = i - entra_em
                fator_tendencia = (1 + tendencia[perfil]) ** passos
                sazonal = 1 + 0.08 * ((i % 4) - 1.5) / 1.5
                ruido = rng.gauss(1.0, volatilidade[perfil])
                faturamento = max(50.0, base * fator_tendencia * sazonal * ruido)
                pedidos = max(1, round(faturamento / ticket))

                linhas.append(
                    {
                        "parceiro_id": parceiro.id,
                        "periodo_id": per.id,
                        "importacao_id": imp.id,
                        "faturamento": Decimal(f"{faturamento:.2f}"),
                        "pedidos": pedidos,
                        "projecao": Decimal(f"{faturamento * rng.uniform(1.02, 1.18):.2f}"),
                    }
                )

        s.execute(insert(Metrica), linhas)

        # Contar com uma varredura por importação seria O(n²) — com 10.000
        # parceiros e 52 períodos são 520 mil linhas, e isso trava.
        por_importacao = Counter(m["importacao_id"] for m in linhas)
        for imp in importacoes:
            imp.total_gravado = por_importacao[imp.id]

        s.commit()

    resumo(n_parceiros, n_periodos, len(linhas), semente)


def resumo(n_parceiros: int, n_periodos: int, n_metricas: int, semente: int) -> None:
    with engine.connect() as c:
        top = c.execute(
            text(
                "SELECT p.nome, m.faturamento FROM metrica m"
                " JOIN parceiro p ON p.id = m.parceiro_id"
                " WHERE m.periodo_id = (SELECT max(id) FROM periodo)"
                " ORDER BY m.faturamento DESC LIMIT 5"
            )
        ).all()
        total, mediana = c.execute(
            text(
                "SELECT sum(faturamento), percentile_cont(0.5) WITHIN GROUP (ORDER BY faturamento)"
                " FROM metrica WHERE periodo_id = (SELECT max(id) FROM periodo)"
            )
        ).one()
        top15 = c.execute(
            text(
                "SELECT sum(faturamento) FROM (SELECT faturamento FROM metrica"
                " WHERE periodo_id = (SELECT max(id) FROM periodo)"
                " ORDER BY faturamento DESC LIMIT 15) t"
            )
        ).scalar()

    print(f"\n{n_parceiros} parceiros · {n_periodos} períodos · {n_metricas} métricas · semente {semente}")
    print(f"\nÚltimo período: faturamento total R$ {total:,.2f} · mediana R$ {mediana:,.2f}")
    print(f"Concentração do Top 15: {100 * float(top15) / float(total):.1f}% do faturamento")
    print("\nTop 5 do último período:")
    for nome, valor in top:
        print(f"  {nome:<28} R$ {valor:>12,.2f}")


def main() -> None:
    p = argparse.ArgumentParser(description="Gera dados sintéticos para o GIH.")
    p.add_argument("--parceiros", type=int, default=500, help="100 a 10.000 (padrão: 500)")
    p.add_argument("--periodos", type=int, default=12, help="semanas de histórico (padrão: 12)")
    p.add_argument("--semente", type=int, default=42, help="semente aleatória (padrão: 42)")
    p.add_argument("--limpar", action="store_true", help="apaga os dados existentes antes")
    a = p.parse_args()

    if not 100 <= a.parceiros <= 10_000:
        p.error("--parceiros deve estar entre 100 e 10.000 (RF16)")
    if a.periodos < 1:
        p.error("--periodos deve ser no mínimo 1")

    gerar(a.parceiros, a.periodos, a.semente, a.limpar)


if __name__ == "__main__":
    main()
