"""Limpa e repovoa o banco — história H77.

Anda junto com o gerador de dados. Num projeto anterior no mesmo domínio, seed
e reset foram usados centenas de vezes, e a conclusão registrada foi direta:
quando testar dói, a equipe testa menos.

Uso:
    python scripts/resetar_banco.py                          # confirma, recria e popula
    python scripts/resetar_banco.py --parceiros 2000         # tamanho da rede
    python scripts/resetar_banco.py --vazio                  # recria sem popular
    python scripts/resetar_banco.py --sim                    # sem perguntar

Os usuários vão junto com o resto. No fim, o reset recria o administrador e
reinicia a API — ver `reabrir_acesso`.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
API = RAIZ / "api"
SAUDE = "http://localhost:8000/api/health"
sys.path.insert(0, str(API))

from app.config import config  # noqa: E402
from gih_modelo import PERIODOS_MINIMOS  # noqa: E402


def python_do_ambiente() -> str:
    """Prefere o venv da API; cai para o interpretador atual."""
    for candidato in (API / ".venv" / "Scripts" / "python.exe", API / ".venv" / "bin" / "python"):
        if candidato.exists():
            return str(candidato)
    return sys.executable


def rodar(comando: list[str], cwd: Path) -> None:
    r = subprocess.run(comando, cwd=cwd)
    if r.returncode != 0:
        print(f"\nFalhou: {' '.join(comando)}")
        sys.exit(r.returncode)


def api_no_compose() -> bool | None:
    """Se a API roda pelo Docker Compose; `None` quando não há Docker para perguntar."""
    try:
        r = subprocess.run(
            ["docker", "compose", "ps", "--status", "running", "--services"],
            cwd=RAIZ,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return None
    return r.returncode == 0 and "api" in r.stdout.split()


def esperar_api(limite_s: float = 60) -> bool:
    fim = time.monotonic() + limite_s
    while time.monotonic() < fim:
        try:
            with urllib.request.urlopen(SAUDE, timeout=2) as r:
                if r.status == 200:
                    return True
        except OSError:
            pass
        time.sleep(1)
    return False


def reabrir_acesso(py: str) -> None:
    """Deixa a base em condição de uso: com administrador, e a API enxergando as
    tabelas novas (#115).

    **O administrador.** O reset recria também a tabela de usuários, e ela volta
    vazia. O `criar-admin` só rodava na subida do contêiner: até alguém
    reiniciar a API, ninguém entrava. Rodado aqui, e antes de reiniciar, a senha
    sorteada (quando `ADMIN_SENHA` não está definida) sai nesta saída, onde quem
    rodou o reset vai lê-la — e não só no log do contêiner.

    **A API.** O psycopg prepara no servidor as consultas que se repetem numa
    conexão, e as conexões que a API mantém guardam planos dos tipos que o reset
    acabou de recriar. Cada uma respondia "erro interno" uma vez antes de se
    renovar ("cached plan must not change result type"). Reiniciar abre
    conexões novas.
    """
    print("\nConferindo o administrador...")
    rodar([py, "-m", "app.cli", "criar-admin"], cwd=API)
    print(
        "Só o administrador entra agora. Logins pessoais se recriam com "
        "`python -m app.cli criar-usuario` — a senha é digitada no terminal."
    )

    if not api_no_compose():
        print(
            "\nA API não está rodando pelo Docker Compose. Se ela estiver no ar por outro "
            "caminho, reinicie-a: as conexões abertas guardam consultas das tabelas antigas."
        )
        return

    print("\nReiniciando a API...")
    rodar(["docker", "compose", "restart", "api"], cwd=RAIZ)
    if esperar_api():
        print("API no ar.")
    else:
        print(f"A API não respondeu em {SAUDE} — veja `docker compose logs api`.")


def main() -> None:
    p = argparse.ArgumentParser(description="Limpa e repovoa o banco do GIH.")
    p.add_argument("--parceiros", type=int, default=500)
    p.add_argument("--periodos", type=int, default=12)
    p.add_argument("--semente", type=int, default=42)
    p.add_argument("--vazio", action="store_true", help="recria o esquema sem popular")
    p.add_argument("--sim", action="store_true", help="não pedir confirmação")
    a = p.parse_args()

    # Mostrar o destino antes de apagar não é formalidade: a porta 5432 costuma
    # ter outro Postgres, e apagar o banco errado é irreversível.
    destino = config.database_url.split("@")[-1]
    print(f"Isto vai APAGAR todos os dados, inclusive os usuários, de: {destino}")

    if not a.sim:
        if input("Digite 'apagar' para confirmar: ").strip().lower() != "apagar":
            print("Cancelado.")
            return

    py = python_do_ambiente()

    print("\nRevertendo as migrações...")
    rodar([py, "-m", "alembic", "downgrade", "base"], cwd=API)

    print("Aplicando as migrações...")
    rodar([py, "-m", "alembic", "upgrade", "head"], cwd=API)

    if a.vazio:
        print("\nEsquema recriado, sem dados.")
        reabrir_acesso(py)
        return

    print("\nPopulando...")
    rodar(
        [
            py,
            str(RAIZ / "scripts" / "gerar_dados_sinteticos.py"),
            "--parceiros", str(a.parceiros),
            "--periodos", str(a.periodos),
            "--semente", str(a.semente),
        ],
        cwd=RAIZ,
    )

    # O gerador grava métrica, não segmento: a segmentação só roda quando a
    # importação acontece, e o gerador não passa por ela. Sem este passo, todo
    # reset deixava o painel abrindo com a distribuição vazia e "segmentação
    # ainda não calculada" — correto, mas não é o que se quer demonstrar.
    print("\nSegmentando...")
    rodar([py, "-m", "app.cli", "reprocessar-segmentos"], cwd=API)

    # Pelo mesmo motivo, o modelo: sem treino, o cadastro do parceiro abriria
    # com "o modelo ainda não foi treinado" — correto, e não o que se demonstra.
    # Com menos de 8 períodos o treino é recusado (RN09); o reset não pula o
    # passo em silêncio, mas também não falha por isso — a base pequena
    # continua útil para o resto.
    if a.periodos >= PERIODOS_MINIMOS:
        print("\nTreinando o modelo preditivo...")
        rodar([py, "-m", "app.cli", "treinar-modelo"], cwd=API)
    else:
        print(
            f"\nModelo não treinado: {a.periodos} períodos, e o treino exige "
            f"{PERIODOS_MINIMOS} (RN09)."
        )

    reabrir_acesso(py)


if __name__ == "__main__":
    main()
