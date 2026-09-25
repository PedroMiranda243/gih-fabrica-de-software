"""Gera o registro de bugs de uma entrega a partir das issues `fix` do GitHub.

O enunciado da Sprint 05 pede o registro dos principais bugs, das correções
aplicadas e das pendências. **O registro sai das issues, e não é escrito à
mão**: cada defeito é uma issue com o rótulo `fix`, com o que apareceu, a causa,
a correção e como foi encontrado — e a issue fechada aponta o PR que corrigiu.
Pendência é a issue ainda aberta.

Escrever a lista à mão no documento teria o defeito de sempre: ela diverge do
que aconteceu no primeiro bug que alguém esquecer de copiar.

Precisa do `gh` autenticado. Uso, da raiz do projeto:

    python scripts/registrar_bugs.py --desde 2026-09-22 --saida docs/entrega/evidencias/sprint05
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
REPOSITORIO = "PedroMiranda243/gih-fabrica-de-software"

# As seções do corpo da issue, na ordem em que o registro as mostra.
SECOES = {
    "O que apareceu": "apareceu",
    "Causa": "causa",
    "Correção": "correcao",
    "O que fazer": "correcao",
    "Como foi encontrado": "encontrado",
}

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def issues(desde: str) -> list[dict]:
    r = subprocess.run(
        [
            "gh", "issue", "list", "-R", REPOSITORIO, "--label", "fix", "--state", "all",
            "--limit", "500", "--json",
            "number,title,state,body,createdAt,closedAt,comments,url,closedByPullRequestsReferences",
        ],
        capture_output=True, text=True, encoding="utf-8",
    )
    if r.returncode:
        raise SystemExit(f"O gh falhou: {r.stderr.strip()}")
    todas = json.loads(r.stdout)
    return sorted((i for i in todas if i["createdAt"][:10] >= desde), key=lambda i: i["number"])


def secoes(corpo: str) -> dict[str, str]:
    """O texto de cada seção `## Título` do corpo, sem a nota de rodapé."""
    achadas: dict[str, str] = {}
    # O GitHub devolve o corpo com `\r\n`; sem normalizar, a nota de rodapé não
    # se separava e entrava colada na última seção.
    corpo = corpo.replace("\r\n", "\n").split("\n---\n")[0]
    for bloco in re.split(r"^## ", corpo, flags=re.MULTILINE)[1:]:
        titulo, _, texto = bloco.partition("\n")
        chave = SECOES.get(titulo.strip())
        if chave:
            achadas[chave] = " ".join(texto.split())
    return achadas


def prs_da_correcao(issue: dict) -> list[int]:
    """Os PRs que corrigiram: os que fecharam a issue com "Fixes #N", ou os citados
    no comentário de fechamento ("Corrigido em #79, #80.") quando a issue foi
    registrada depois da correção."""
    fecharam = [pr["number"] for pr in issue.get("closedByPullRequestsReferences") or []]
    if fecharam:
        return sorted(fecharam)
    for comentario in reversed(issue.get("comments", [])):
        corpo = comentario.get("body", "")
        if corpo.startswith("Corrigido em"):
            return [int(n) for n in re.findall(r"#(\d+)", corpo)]
    return []


def registro(desde: str) -> list[dict]:
    itens = []
    for issue in issues(desde):
        partes = secoes(issue["body"])
        faltando = {"apareceu", "causa", "correcao", "encontrado"} - partes.keys()
        if faltando:
            raise SystemExit(
                f"A issue #{issue['number']} não tem as seções {sorted(faltando)} — o registro "
                "sai do corpo dela, e sem elas ficaria incompleto."
            )
        fechada = issue["state"] == "CLOSED"
        itens.append(
            {
                "numero": issue["number"],
                "titulo": issue["title"],
                "situacao": "corrigido" if fechada else "pendente",
                "prs": prs_da_correcao(issue) if fechada else [],
                **partes,
            }
        )
    return itens


def _quantos(n: int, um: str, varios: str) -> str:
    return f"{n} {um if n == 1 else varios}"


def texto(itens: list[dict], desde: str) -> str:
    corrigidos = [i for i in itens if i["situacao"] == "corrigido"]
    pendentes = [i for i in itens if i["situacao"] == "pendente"]
    linhas = [
        "Registro de bugs — gerado das issues com o rótulo `fix`",
        f"Abertas desde {desde[8:10]}/{desde[5:7]}/{desde[:4]}; gerado em "
        f"{datetime.now():%d/%m/%Y %H:%M} por scripts/registrar_bugs.py",
        "",
    ]
    for item in itens:
        prs = ", ".join(f"#{p}" for p in item["prs"])
        marca = f"corrigido em {prs}" if item["situacao"] == "corrigido" else "PENDENTE"
        rotulo_correcao = "correção:" if item["situacao"] == "corrigido" else "a fazer:"
        linhas += [
            f"#{item['numero']}  {item['titulo']}",
            f"    {'situação:':<12} {marca}",
            f"    {'apareceu:':<12} {item['apareceu']}",
            f"    {'causa:':<12} {item['causa']}",
            f"    {rotulo_correcao:<12} {item['correcao']}",
            f"    {'encontrado:':<12} {item['encontrado']}",
            "",
        ]
    linhas.append(
        f"Resultado: {_quantos(len(itens), 'defeito registrado', 'defeitos registrados')} — "
        f"{_quantos(len(corrigidos), 'corrigido', 'corrigidos')}, "
        f"{_quantos(len(pendentes), 'pendente', 'pendentes')}."
    )
    return "\n".join(linhas) + "\n"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--desde", required=True, help="data de abertura mínima, AAAA-MM-DD")
    p.add_argument("--saida", required=True, help="pasta das evidências da entrega")
    a = p.parse_args()

    itens = registro(a.desde)
    destino = RAIZ / a.saida
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "bugs.json").write_text(
        json.dumps(itens, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (destino / "bugs.txt").write_text(texto(itens, a.desde), encoding="utf-8")
    print(texto(itens, a.desde).splitlines()[-1])


if __name__ == "__main__":
    main()
