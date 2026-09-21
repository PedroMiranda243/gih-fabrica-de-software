"""Limpa e repovoa o banco — história H77.

Anda junto com o gerador de dados. Num projeto anterior no mesmo domínio, seed
e reset foram usados centenas de vezes, e a conclusão registrada foi direta:
quando testar dói, a equipe testa menos.

Uso:
    python scripts/resetar_banco.py                          # confirma, recria e popula
    python scripts/resetar_banco.py --parceiros 2000         # tamanho da rede
    python scripts/resetar_banco.py --vazio                  # recria sem popular
    python scripts/resetar_banco.py --sim                    # sem perguntar
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
API = RAIZ / "api"
sys.path.insert(0, str(API))

from app.config import config  # noqa: E402


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
    print(f"Isto vai APAGAR todos os dados de: {destino}")

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


if __name__ == "__main__":
    main()
