"""Descreve a estrutura do banco no ar, lida do catálogo do PostgreSQL (H108).

A entrega da Sprint 10 pede a "descrição da estrutura final do banco de dados".
O `docs/08` a descreve à mão, e o `api/tests/test_modelo_de_dados.py` confere o
documento contra o banco a cada Pull Request. Este script é o terceiro lado:
lê o banco que está rodando e escreve, tabela por tabela, as colunas, as chaves,
as restrições, os índices e quantas linhas cada uma tem agora. Nada é escrito à
mão: o que vai para a entrega é o que o catálogo responde.

Só lê. Usa o banco da API do `docker compose`, pelo mesmo `DATABASE_URL` da
verificação de ponta a ponta. Uso, da raiz do projeto:

    api/.venv/Scripts/python scripts/descrever_banco.py --saida docs/entrega/evidencias/sprint10/banco.txt
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "api"))

from sqlalchemy import create_engine, text  # noqa: E402

from e2e.limpeza import url_do_banco  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FORA = "alembic_version"

COLUNAS = """
SELECT c.relname, a.attname, format_type(a.atttypid, a.atttypmod), a.attnotnull
  FROM pg_attribute a
  JOIN pg_class c ON c.oid = a.attrelid
  JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE n.nspname = 'public' AND c.relkind = 'r' AND a.attnum > 0 AND NOT a.attisdropped
   AND c.relname <> :fora
 ORDER BY c.relname, a.attnum
"""

RESTRICOES = """
SELECT c.relname, k.conname, k.contype, pg_get_constraintdef(k.oid)
  FROM pg_constraint k
  JOIN pg_class c ON c.oid = k.conrelid
  JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE n.nspname = 'public' AND c.relname <> :fora
 ORDER BY c.relname, k.contype, k.conname
"""

INDICES = """
SELECT tablename, indexname, indexdef
  FROM pg_indexes
 WHERE schemaname = 'public' AND tablename <> :fora
 ORDER BY tablename, indexname
"""

ENUMS = """
SELECT t.typname, string_agg(e.enumlabel, ', ' ORDER BY e.enumsortorder)
  FROM pg_type t
  JOIN pg_enum e ON e.enumtypid = t.oid
  JOIN pg_namespace n ON n.oid = t.typnamespace
 WHERE n.nspname = 'public'
 GROUP BY t.typname
 ORDER BY t.typname
"""

TIPO = {"p": "PK", "f": "FK", "u": "UNIQUE", "c": "CHECK"}


def descrever(url: str) -> str:
    engine = create_engine(url)
    try:
        with engine.connect() as c:
            colunas = c.execute(text(COLUNAS), {"fora": FORA}).all()
            restricoes = c.execute(text(RESTRICOES), {"fora": FORA}).all()
            indices = c.execute(text(INDICES), {"fora": FORA}).all()
            enums = c.execute(text(ENUMS)).all()
            revisao = c.execute(text("SELECT version_num FROM alembic_version")).scalar()
            extensoes = [e for (e,) in c.execute(text("SELECT extname FROM pg_extension ORDER BY 1"))]
            versao = c.execute(text("SHOW server_version")).scalar()
            tabelas = sorted({t for t, *_ in colunas})
            linhas = {
                t: c.execute(text(f'SELECT count(*) FROM "{t}"')).scalar() for t in tabelas
            }
    finally:
        engine.dispose()

    contagem = {tipo: sum(1 for r in restricoes if r[2] == tipo) for tipo in TIPO}
    saida = [
        "Estrutura do banco de dados — gerada por scripts/descrever_banco.py",
        f"Lida do catálogo em {datetime.now():%d/%m/%Y %H:%M}; PostgreSQL {versao.split()[0]}; "
        f"migração aplicada: {revisao}",
        f"Extensões: {', '.join(extensoes)}",
        "",
        "Resumo",
        f"  {len(tabelas)} tabelas de domínio, {contagem['p']} chaves primárias, "
        f"{contagem['f']} chaves estrangeiras, {contagem['u']} restrições UNIQUE, "
        f"{contagem['c']} restrições CHECK, {len(indices)} índices, {len(enums)} tipos ENUM",
        "",
    ]
    for t in tabelas:
        saida.append(f"{t}  ({linhas[t]} linhas)")
        for _, nome, tipo, obrigatoria in (r for r in colunas if r[0] == t):
            saida.append(f"    {nome:<28} {tipo:<32} {'NOT NULL' if obrigatoria else 'nulo'}")
        for _, nome, tipo, definicao in (r for r in restricoes if r[0] == t):
            saida.append(f"    {TIPO.get(tipo, tipo):<7} {nome}: {definicao}")
        for _, nome, definicao in (r for r in indices if r[0] == t):
            saida.append(f"    índice  {nome}: {definicao.split(' USING ', 1)[-1]}")
        saida.append("")
    saida.append("Tipos ENUM")
    saida += [f"    {nome}: {valores}" for nome, valores in enums]
    return "\n".join(saida) + "\n"


def main() -> None:
    p = argparse.ArgumentParser(description="Descreve a estrutura do banco no ar (H108).")
    p.add_argument("--url", default=None, help="o banco; padrão: o da API do docker compose")
    p.add_argument("--saida", default=None, help="arquivo de saída; padrão: a tela")
    args = p.parse_args()
    texto = descrever(args.url or url_do_banco())
    if args.saida:
        Path(args.saida).parent.mkdir(parents=True, exist_ok=True)
        Path(args.saida).write_text(texto, encoding="utf-8")
        print(f"gravado em {args.saida}")
    else:
        print(texto, end="")


if __name__ == "__main__":
    main()
