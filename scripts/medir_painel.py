"""Mede o tempo de resposta do painel com base grande — história H40.

O RNF03 fixa 2 s e o RNF04 fixa 10.000 parceiros; a H40 cobra o painel
respondendo em até 2 s com 5.000. Este script produz o número, e produz de um
jeito que outra pessoa consegue repetir.

**Três cuidados que vieram de erro cometido antes neste projeto:**

1. **Banco separado.** A medição gera 5.000 parceiros com `--limpar`. Apontada
   para o banco de trabalho, apagaria a base de demonstração e o usuário de quem
   estiver testando a aplicação. Por isso cria e usa `gih_medicao`, na mesma
   instância — o banco de trabalho não é tocado em nenhum passo.

2. **Repetições calibradas, não fixas.** Na validação do toolchain (H47) o mesmo
   binário no mesmo cenário deu 7,5x numa execução e 13,9x na seguinte: cinco
   repetições de uma passada curta medem o relógio, não o trabalho. Aqui o número
   de chamadas sai de um alvo de tempo, e o relatório traz **mediana, p95 e
   dispersão** — número único esconde justamente o que interessa.

3. **Índice verificado, não presumido.** Cada consulta que o endpoint realmente
   executou é capturada do SQLAlchemy e passada por `EXPLAIN (ANALYZE, BUFFERS)`.
   O plano vai inteiro para o relatório. Comentário sem medição é hipótese.

**Por que `Seq Scan` não é reprovação automática.** A primeira versão deste
script reprovava a busca por varrer `parceiro` — e estava errada. Com 5.000
parceiros a tabela tem 528 kB e o índice de trigrama 1,9 MB: varrer é o plano
mais barato, e o planejador acertou. Reprovar ali seria instrumento quebrado
acusando falha que não existe, que é a armadilha registrada no CLAUDE.md.

O que de fato precisa ser verdade é que **exista índice capaz de atender o
filtro quando a tabela crescer**. Por isso, onde a varredura aparece numa
consulta que filtra, a mesma consulta roda de novo com `enable_seqscan = off`:
se o plano passa a usar um índice, era escolha do planejador; se continua
varrendo, aí sim falta índice, e a medição reprova.

Uso:

    api/.venv/Scripts/python scripts/medir_painel.py
    api/.venv/Scripts/python scripts/medir_painel.py --parceiros 10000 --reusar
"""
from __future__ import annotations

import argparse
import math
import os
import re
import secrets
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

RAIZ = Path(__file__).resolve().parent.parent
RAIZ_API = RAIZ / "api"
sys.path.insert(0, str(RAIZ_API))

# O console do Windows é cp1252 e estoura em qualquer caractere fora dele. O
# relatório sai em arquivo UTF-8; isto aqui só impede que a impressão do resumo
# derrube uma medição que já terminou.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LIMITE_MS = 2000  # RNF03

# O que vale explicar: o preâmbulo de autenticação toca só `usuario` e
# `sessao_acesso`, e não é o que a H40 mede. O casamento é por `FROM`/`JOIN`, e
# não por substring: `usuario.parceiro_id` contém "parceiro" e faria a consulta
# da sessão entrar no relatório como se fosse do painel.
TABELA_DO_DOMINIO = re.compile(
    r"\b(?:FROM|JOIN)\s+(?:metrica|parceiro|periodo|historico_segmento)\b", re.IGNORECASE
)


def _mil(n: int) -> str:
    """5000 vira 5.000. `:n` dependeria do locale do processo, que no console
    do Windows não é o daqui."""
    return f"{n:,}".replace(",", ".")


# --------------------------------------------------------------------- catálogo
@dataclass(frozen=True)
class Medicao:
    """Uma chamada do painel, com o que se espera do plano de execução."""

    nome: str
    caminho: str
    proposito: str
    # Tabelas que a consulta filtra. Se a varredura aparecer numa delas, a
    # medição confere se existe índice que atenda o filtro — ver `Confirmacao`.
    sem_seq_scan_em: tuple[str, ...] = ()
    # Quando a varredura é esperada, a razão fica registrada no relatório.
    varredura_esperada: str = ""


MEDICOES = (
    Medicao(
        nome="indicadores",
        caminho="/api/painel/indicadores",
        proposito="Faturamento, pedidos, ticket e ativos do período, com variação (H30).",
        sem_seq_scan_em=("metrica",),
    ),
    Medicao(
        nome="ranking-25",
        caminho="/api/painel/ranking?tamanho=25",
        proposito="A página que o painel pede ao abrir (H31).",
        sem_seq_scan_em=("metrica",),
    ),
    Medicao(
        nome="ranking-200",
        caminho="/api/painel/ranking?tamanho=200",
        proposito="A maior página que a API aceita — o pior caso do ranking.",
        sem_seq_scan_em=("metrica",),
    ),
    Medicao(
        nome="serie",
        caminho="/api/painel/series",
        proposito="Série histórica da rede (H32).",
        varredura_esperada=(
            "A série agrega **todos** os períodos: a consulta lê a tabela inteira por "
            "definição, e varrer é o plano certo."
        ),
    ),
    Medicao(
        nome="segmentos",
        caminho="/api/painel/segmentos",
        proposito="Distribuição por segmento do período (H33).",
        sem_seq_scan_em=("historico_segmento",),
    ),
    Medicao(
        nome="mobilidade",
        caminho="/api/painel/mobilidade",
        proposito="Quem entrou e quem saiu do Top N (H35).",
        sem_seq_scan_em=("metrica",),
    ),
    Medicao(
        nome="busca",
        caminho="/api/parceiros?busca=praca",
        proposito="Busca por nome, sem sensibilidade a acentuação (H37).",
        sem_seq_scan_em=("parceiro",),
    ),
    Medicao(
        nome="lista-completa",
        caminho="/api/parceiros",
        proposito="Lista de parceiros sem filtro — hoje sem paginação.",
        varredura_esperada=(
            "Sem filtro, a resposta é a tabela inteira; o custo está no volume, não no "
            "plano. É o caso que a paginação da H36 precisa resolver."
        ),
    ),
)


# ------------------------------------------------------------------ preparação
def _url_base() -> str:
    """De onde sai a URL do banco, na mesma ordem que a aplicação usa.

    Lê o `.env` à mão pelo mesmo motivo do `conftest`: importar `app.config`
    aqui criaria a engine apontando para o banco de trabalho **antes** de a
    variável de medição existir.
    """
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]

    for arquivo in (RAIZ / ".env", RAIZ_API / ".env"):
        if not arquivo.exists():
            continue
        for linha in arquivo.read_text(encoding="utf-8").splitlines():
            chave, _, valor = linha.partition("=")
            if chave.strip() == "DATABASE_URL" and valor.strip():
                return valor.strip().strip("\"'")

    return "postgresql+psycopg://gih:gih@localhost:5433/gih"


def _url_medicao(nome_banco: str) -> str:
    partes = urlsplit(_url_base())
    return urlunsplit(partes._replace(path=f"/{nome_banco}"))


def _criar_banco_se_faltar(url: str) -> None:
    from sqlalchemy import create_engine, text

    partes = urlsplit(url)
    nome = partes.path.lstrip("/")
    manutencao = create_engine(
        urlunsplit(partes._replace(path="/postgres")), isolation_level="AUTOCOMMIT"
    )
    try:
        with manutencao.connect() as c:
            existe = c.scalar(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": nome})
            if not existe:
                # Identificador não aceita bind. O nome vem da nossa própria
                # configuração, nunca de entrada de usuário.
                c.execute(text(f'CREATE DATABASE "{nome}"'))
                print(f"  banco {nome} criado")
    finally:
        manutencao.dispose()


def _rodar(comando: list[str], cwd: Path, url: str) -> None:
    r = subprocess.run(
        comando,
        cwd=cwd,
        env={**os.environ, "DATABASE_URL": url},
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if r.returncode != 0:
        raise SystemExit(f"Falhou: {' '.join(comando)}\n{r.stdout}\n{r.stderr}")


def _segmentar() -> None:
    """Classifica a base recém-gerada (H33).

    O gerador grava métrica, não segmento. Sem este passo o painel mediria uma
    base sem classificação: a distribuição viria vazia e o `EXPLAIN` da consulta
    de segmentos explicaria uma tabela sem linhas — que é medir outra coisa.

    Importado aqui dentro, e não no topo: `app` só pode ser importado depois de
    `DATABASE_URL` apontar para o banco de medição.
    """
    from app.db import Sessao
    from app.servico_segmentacao import reprocessar_tudo

    s = Sessao()
    try:
        periodos = reprocessar_tudo(s)
        s.commit()
        print(f"  segmentação calculada em {periodos} período(s)")
    finally:
        s.close()


def _analisar(url: str) -> None:
    from sqlalchemy import create_engine, text

    motor = create_engine(url, isolation_level="AUTOCOMMIT")
    try:
        with motor.connect() as c:
            c.execute(text("ANALYZE"))
    finally:
        motor.dispose()


def preparar(url: str, parceiros: int, periodos: int, semente: int) -> None:
    print("preparando o banco de medição")
    _criar_banco_se_faltar(url)
    _rodar([sys.executable, "-m", "alembic", "upgrade", "head"], RAIZ_API, url)
    print("  migrações aplicadas")
    _rodar(
        [
            sys.executable,
            str(RAIZ / "scripts" / "gerar_dados_sinteticos.py"),
            "--parceiros",
            str(parceiros),
            "--periodos",
            str(periodos),
            "--semente",
            str(semente),
            "--limpar",
        ],
        RAIZ,
        url,
    )
    print(f"  {parceiros} parceiros e {periodos} períodos gerados (semente {semente})")

    # **Sem isto a medição mente.** O gerador insere em massa e o autovacuum não
    # teve tempo de rodar: o planejador estimaria uma linha onde há cinco mil e
    # escolheria planos que não são os de um banco em regime. Medir plano
    # escolhido a partir de estatística velha é medir outro sistema.
    _segmentar()
    _analisar(url)
    print("  estatísticas atualizadas (ANALYZE)")


def criar_gestor() -> tuple[str, str]:
    """Usuário descartável, só para a sessão desta medição.

    A senha é sorteada e não é impressa nem gravada: o relatório vai para o
    repositório, que é público.
    """
    from app.db import Sessao
    from app.modelos import Perfil, Usuario
    from app.seguranca import gerar_hash

    login = "medicao"
    senha = secrets.token_urlsafe(18)
    s = Sessao()
    try:
        u = s.query(Usuario).filter_by(login=login).one_or_none()
        if u is None:
            u = Usuario(login=login, nome="Medição", perfil=Perfil.GESTOR)
            s.add(u)
        u.senha_hash = gerar_hash(senha)
        u.ativo = True
        s.commit()
    finally:
        s.close()
    return login, senha


# --------------------------------------------------------------------- medição
@dataclass
class Confirmacao:
    """O que acontece com o filtro quando a varredura é proibida.

    Varredura sequencial **não** é sinônimo de índice faltando. Numa tabela de
    poucas páginas o planejador varre porque varrer é mais barato, e isso é
    decisão certa. O que precisa ser verdade é outra coisa: que exista um índice
    capaz de atender o filtro quando a tabela crescer. Por isso a mesma consulta
    roda de novo com `enable_seqscan = off` — se o índice existe, o plano passa
    a usá-lo; se não existe, o Postgres varre assim mesmo, e aí é defeito.
    """

    tabela: str
    indices: tuple[str, ...]
    tempo_ms: float
    texto: str

    @property
    def coberta(self) -> bool:
        return f"Seq Scan on {self.tabela}" not in self.texto


@dataclass
class Plano:
    sql: str
    texto: str
    seq_scans: tuple[str, ...]
    tempo_ms: float
    confirmacoes: list[Confirmacao] = field(default_factory=list)


@dataclass
class Resultado:
    medicao: Medicao
    chamadas: list[float] = field(default_factory=list)
    planos: list[Plano] = field(default_factory=list)
    bytes_resposta: int = 0

    @property
    def mediana(self) -> float:
        return statistics.median(self.chamadas)

    @property
    def p95(self) -> float:
        ordenado = sorted(self.chamadas)
        return ordenado[min(len(ordenado) - 1, math.ceil(0.95 * len(ordenado)) - 1)]

    @property
    def dispersao(self) -> float:
        """Quanto o p95 se afasta da mediana, em %.

        Um número só de tempo esconde variação, e a medição paralela oscila mais
        que a serial — a dispersão é parte do resultado, não enfeite.
        """
        return (self.p95 - self.mediana) / self.mediana * 100 if self.mediana else 0.0

    @property
    def dentro_do_limite(self) -> bool:
        return self.p95 <= LIMITE_MS

    @property
    def confirmacoes(self) -> list[Confirmacao]:
        return [c for p in self.planos for c in p.confirmacoes]

    @property
    def sem_indice(self) -> list[str]:
        """Tabelas em que o filtro não tem índice que o atenda — isso é defeito."""
        return sorted({c.tabela for c in self.confirmacoes if not c.coberta})


def _chamar(cliente, caminho: str) -> int:
    r = cliente.get(caminho)
    if r.status_code != 200:
        raise SystemExit(f"{caminho} respondeu {r.status_code}: {r.text[:200]}")
    return len(r.content)


def medir(cliente, medicao: Medicao, alvo_ms: int) -> Resultado:
    resultado = Resultado(medicao=medicao)

    # Aquecimento: a primeira chamada paga import tardio, plano do banco e
    # conexão do pool. Medi-la mediria a partida, não o regime.
    for _ in range(2):
        resultado.bytes_resposta = _chamar(cliente, medicao.caminho)

    inicio = time.perf_counter()
    _chamar(cliente, medicao.caminho)
    uma_ms = (time.perf_counter() - inicio) * 1000

    # Quantas chamadas cabem no alvo de tempo. Mínimo de 5 para haver mediana,
    # teto de 300 para uma consulta rápida não fazer a medição levar minutos.
    chamadas = max(5, min(300, round(alvo_ms / max(uma_ms, 0.1))))

    for _ in range(chamadas):
        inicio = time.perf_counter()
        _chamar(cliente, medicao.caminho)
        resultado.chamadas.append((time.perf_counter() - inicio) * 1000)

    return resultado


# -------------------------------------------------------------------- EXPLAIN
def capturar_sql(engine, chamar) -> list[tuple[str, object]]:
    """As consultas que o endpoint **de fato** executou.

    Reescrever o SQL à mão para explicar seria explicar outra coisa: bastaria a
    consulta mudar no código para o relatório passar a descrever um plano que
    ninguém executa.
    """
    from sqlalchemy import event

    capturadas: list[tuple[str, object]] = []

    def ouvinte(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT") and not executemany:
            capturadas.append((statement, parameters))

    event.listen(engine, "before_cursor_execute", ouvinte)
    try:
        chamar()
    finally:
        event.remove(engine, "before_cursor_execute", ouvinte)
    return capturadas


def explicar(engine, sql: str, parametros) -> Plano:
    comando = f"EXPLAIN (ANALYZE, BUFFERS) {sql}"
    with engine.connect() as c:
        linhas = c.exec_driver_sql(comando, parametros) if parametros else c.exec_driver_sql(comando)
        texto = "\n".join(linha[0] for linha in linhas)

    tempo = re.search(r"Execution Time: ([\d.]+) ms", texto)
    return Plano(
        sql=sql,
        texto=texto,
        seq_scans=tuple(sorted(set(re.findall(r"Seq Scan on (\w+)", texto)))),
        tempo_ms=float(tempo.group(1)) if tempo else 0.0,
    )


def _indices_em(texto: str) -> tuple[str, ...]:
    """Os índices que o plano usou. `EXPLAIN` escreve as duas formas."""
    achados = re.findall(r"Index (?:Only )?Scan using (\w+)|Bitmap Index Scan on (\w+)", texto)
    return tuple(sorted({nome for par in achados for nome in par if nome}))


def confirmar_indice(engine, sql: str, parametros, tabela: str) -> Confirmacao:
    from sqlalchemy import text

    comando = f"EXPLAIN (ANALYZE, BUFFERS) {sql}"
    with engine.begin() as c:
        # `SET LOCAL` morre com a transação: nenhuma outra medição herda isto.
        c.execute(text("SET LOCAL enable_seqscan = off"))
        linhas = c.exec_driver_sql(comando, parametros) if parametros else c.exec_driver_sql(comando)
        plano = "\n".join(linha[0] for linha in linhas)

    tempo = re.search(r"Execution Time: ([\d.]+) ms", plano)
    return Confirmacao(
        tabela=tabela,
        indices=_indices_em(plano),
        tempo_ms=float(tempo.group(1)) if tempo else 0.0,
        texto=plano,
    )


def planos_de(engine, cliente, medicao: Medicao) -> list[Plano]:
    capturadas = capturar_sql(engine, lambda: _chamar(cliente, medicao.caminho))

    planos: list[Plano] = []
    vistas: set[str] = set()
    for sql, parametros in capturadas:
        if sql in vistas:
            continue
        vistas.add(sql)
        # A conferência da sessão roda em toda requisição, custa microssegundos
        # e não diz nada sobre o painel. Fica de fora para o relatório mostrar
        # o que está sendo medido, e não o mesmo preâmbulo seis vezes.
        if not TABELA_DO_DOMINIO.search(sql):
            continue
        plano = explicar(engine, sql, parametros)
        for tabela in medicao.sem_seq_scan_em:
            if tabela in plano.seq_scans:
                plano.confirmacoes.append(confirmar_indice(engine, sql, parametros, tabela))
        planos.append(plano)
    return planos


# ------------------------------------------------------------------ relatório
def _uma_linha(sql: str, limite: int = 110) -> str:
    compacto = re.sub(r"\s+", " ", sql).strip()
    return compacto if len(compacto) <= limite else compacto[: limite - 1] + "…"


def _tamanho(n: int) -> str:
    return f"{n / 1024:.0f} kB" if n >= 1024 else f"{n} B"


def _tabelas_varridas(plano: Plano) -> str:
    return ", ".join(f"`{t}`" for t in plano.seq_scans) if plano.seq_scans else "nenhuma"


def montar_relatorio(
    resultados: list[Resultado],
    *,
    parceiros: int,
    periodos: int,
    semente: int,
    metricas: int,
    versao_pg: str,
    banco: str,
    comando: str,
) -> str:
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    linhas: list[str] = []
    a = linhas.append

    a(f"# Medição do painel com {_mil(parceiros)} parceiros — H40")
    a("")
    a(
        "> Gerado por `scripts/medir_painel.py`. **Não edite à mão**: número escrito à mão não "
        "é evidência. Para atualizar, rode o comando abaixo de novo."
    )
    a("")
    a(
        f"O RNF03 fixa **2 s** como teto de resposta e a H40 cobra isso com "
        f"{_mil(parceiros)} parceiros. Este arquivo é o registro da medição — a Sprint 12 "
        f"não precisa medir de novo às pressas para pôr o número na apresentação."
    )
    a("")

    a("## Ambiente")
    a("")
    a("| Item | Valor |")
    a("|---|---|")
    a(f"| Data | {agora} |")
    a(f"| Banco | `{banco}` — **separado do banco de trabalho** |")
    a(f"| PostgreSQL | {versao_pg} |")
    a(f"| Python | {sys.version.split()[0]} |")
    a(f"| Massa | {_mil(parceiros)} parceiros · {periodos} períodos · {_mil(metricas)} métricas |")
    a(f"| Semente | {semente} |")
    a("")
    a(
        "A medição chama a aplicação em processo, pelo `TestClient`: cobre roteamento, "
        "autorização, consulta e serialização — tudo que o navegador espera, menos a rede."
    )
    a("")

    a("## Como reproduzir")
    a("")
    a("```bash")
    a(comando)
    a("```")
    a("")

    a("## Resultado")
    a("")
    a("| Consulta | Chamadas | Mediana | p95 | Dispersão | Resposta | Dentro de 2 s |")
    a("|---|--:|--:|--:|--:|--:|:--:|")
    for r in resultados:
        a(
            f"| `{r.medicao.nome}` | {len(r.chamadas)} | {r.mediana:.1f} ms | {r.p95:.1f} ms "
            f"| {r.dispersao:.0f}% | {_tamanho(r.bytes_resposta)} "
            f"| {'sim' if r.dentro_do_limite else '**NÃO**'} |"
        )
    a("")
    a(
        "A dispersão é o quanto o p95 se afasta da mediana. Vai junto de propósito: "
        "um número só de tempo esconde a variação, e foi exatamente isso que enganou a "
        "equipe na validação do toolchain (H47)."
    )
    a("")

    a("## O que cada consulta faz")
    a("")
    for r in resultados:
        a(f"- **`{r.medicao.nome}`** — `GET {r.medicao.caminho}` · {r.medicao.proposito}")
    a("")

    a("## Planos de execução")
    a("")
    a(
        "Cada consulta abaixo foi **capturada do SQLAlchemy durante a chamada** e passada por "
        "`EXPLAIN (ANALYZE, BUFFERS)`. Nenhuma foi reescrita à mão para o relatório."
    )
    a("")
    a(
        "**Varredura sequencial não é sinônimo de índice faltando.** Numa tabela de poucas "
        "páginas o planejador varre porque varrer é mais barato, e está certo. O que precisa "
        "ser verdade é que exista índice capaz de atender o filtro quando a tabela crescer — "
        "e é isso que a conferência com `enable_seqscan = off` mostra. A conferência só roda "
        "onde a varredura apareceu."
    )
    a("")
    for r in resultados:
        a(f"### `{r.medicao.nome}`")
        a("")
        if r.medicao.sem_seq_scan_em:
            alvo = ", ".join(f"`{t}`" for t in r.medicao.sem_seq_scan_em)
            a(
                f"A consulta filtra {alvo}. Se o planejador varrer, a conferência abaixo diz "
                f"se foi escolha dele ou falta de índice."
            )
        if r.medicao.varredura_esperada:
            a(r.medicao.varredura_esperada)
        a("")
        for plano in r.planos:
            a(f"- `{_uma_linha(plano.sql)}`")
            a(
                f"  - tempo no banco: **{plano.tempo_ms:.2f} ms** · "
                f"varredura: {_tabelas_varridas(plano)}"
            )
            for c in plano.confirmacoes:
                if c.coberta:
                    indices = ", ".join(f"`{i}`" for i in c.indices) or "um índice"
                    a(
                        f"  - a varredura em `{c.tabela}` é **escolha do planejador**: com "
                        f"`enable_seqscan = off` o mesmo filtro usa {indices} e leva "
                        f"{c.tempo_ms:.2f} ms. O índice cobre a consulta."
                    )
                else:
                    a(
                        f"  - **não há índice que atenda o filtro em `{c.tabela}`**: a varredura "
                        f"continua mesmo com `enable_seqscan = off`."
                    )
        a("")
        for plano in r.planos:
            a("<details><summary>Plano completo</summary>")
            a("")
            a("```")
            a(plano.texto)
            a("```")
            a("")
            a("</details>")
            a("")

    a("## Índices em uso")
    a("")
    usados = sorted(
        {
            indice
            for r in resultados
            for plano in r.planos
            # "Index Scan using X on" e "Bitmap Index Scan on X" — as duas
            # formas que o EXPLAIN usa; procurar só uma esconderia metade.
            for indice in re.findall(r"using (\w+)|Bitmap Index Scan on (\w+)", plano.texto)
            for indice in indice
            if indice
        }
    )
    for indice in usados:
        a(f"- `{indice}`")
    a("")

    return "\n".join(linhas) + "\n"


# -------------------------------------------------------------------- execução
def main() -> None:
    p = argparse.ArgumentParser(description="Mede o tempo de resposta do painel (H40).")
    p.add_argument("--parceiros", type=int, default=5000, help="padrão: 5000 (H40)")
    p.add_argument("--periodos", type=int, default=12, help="padrão: 12 semanas")
    p.add_argument("--semente", type=int, default=42, help="padrão: 42")
    p.add_argument("--banco", default="gih_medicao", help="nome do banco de medição")
    p.add_argument(
        "--alvo-ms", type=int, default=6000, help="tempo de medição por consulta (padrão: 6000)"
    )
    p.add_argument(
        "--reusar",
        action="store_true",
        help="não regera a massa; usa o que já está no banco de medição",
    )
    p.add_argument(
        "--relatorio",
        default=str(RAIZ / "docs" / "medicoes" / "painel-5000.md"),
        help="arquivo markdown de saída",
    )
    args = p.parse_args()

    url = _url_medicao(args.banco)
    if urlsplit(url).path.lstrip("/") == urlsplit(_url_base()).path.lstrip("/"):
        raise SystemExit("O banco de medição não pode ser o banco de trabalho.")

    # Precisa valer **antes** de qualquer import de `app`: a engine nasce no
    # import do módulo, lendo a configuração uma única vez.
    os.environ["DATABASE_URL"] = url

    if args.reusar:
        print("reusando a massa já existente no banco de medição")
    else:
        preparar(url, args.parceiros, args.periodos, args.semente)

    from fastapi.testclient import TestClient
    from sqlalchemy import func, select

    from app.db import Sessao, engine
    from app.main import app
    from app.modelos import Metrica, Parceiro, Periodo

    login, senha = criar_gestor()

    s = Sessao()
    try:
        parceiros = s.scalar(select(func.count()).select_from(Parceiro))
        periodos = s.scalar(select(func.count()).select_from(Periodo))
        metricas = s.scalar(select(func.count()).select_from(Metrica))
        versao_pg = s.scalar(select(func.version())).split(",")[0]
    finally:
        s.close()

    print(f"massa: {parceiros} parceiros, {periodos} períodos, {metricas} métricas")
    print(f"banco: {versao_pg}")
    print()

    resultados: list[Resultado] = []
    with TestClient(app) as cliente:
        r = cliente.post("/api/sessao", json={"login": login, "senha": senha})
        if r.status_code != 201:
            raise SystemExit(f"A autenticação respondeu {r.status_code}.")

        for medicao in MEDICOES:
            print(f"medindo {medicao.nome} ... ", end="", flush=True)
            resultado = medir(cliente, medicao, args.alvo_ms)
            resultado.planos = planos_de(engine, cliente, medicao)
            resultados.append(resultado)
            print(
                f"mediana {resultado.mediana:7.1f} ms | p95 {resultado.p95:7.1f} ms "
                f"| {len(resultado.chamadas):3d} chamadas"
            )

        cliente.delete("/api/sessao")

    comando = (
        f"api/.venv/Scripts/python scripts/medir_painel.py --parceiros {args.parceiros} "
        f"--periodos {args.periodos} --semente {args.semente}"
    )
    # Sem isto, o comando impresso num relatório fora do padrão sobrescreveria o
    # outro ao ser repetido — e quem reproduz confia no comando que está escrito.
    if Path(args.relatorio) != Path(p.get_default("relatorio")):
        comando += f" --relatorio {os.path.relpath(args.relatorio, RAIZ).replace(os.sep, '/')}"
    relatorio = montar_relatorio(
        resultados,
        parceiros=parceiros,
        periodos=periodos,
        semente=args.semente,
        metricas=metricas,
        versao_pg=versao_pg,
        banco=args.banco,
        comando=comando,
    )
    destino = Path(args.relatorio)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(relatorio, encoding="utf-8")
    # `relative_to` estoura quando o destino está fora do repositório, e isso
    # derrubaria uma medição que já terminou, depois do arquivo gravado.
    print(f"\nrelatório em {os.path.relpath(destino, RAIZ)}")

    print()
    problemas: list[str] = []
    for r in resultados:
        if not r.dentro_do_limite:
            problemas.append(f"{r.medicao.nome}: p95 de {r.p95:.0f} ms passa de {LIMITE_MS} ms")
        for tabela in r.sem_indice:
            problemas.append(
                f"{r.medicao.nome}: nenhum índice atende o filtro em {tabela} "
                f"(a varredura continua mesmo com enable_seqscan=off)"
            )

    if problemas:
        print("REPROVADO")
        for problema in problemas:
            print(f"  - {problema}")
        raise SystemExit(1)

    print(f"APROVADO: as {len(resultados)} consultas respondem dentro de {LIMITE_MS} ms")


if __name__ == "__main__":
    main()
