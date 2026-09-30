"""Gera o registro das revisões dos Pull Requests de uma entrega, a partir do GitHub.

A devolutiva da Sprint 04 cobrou revisão cruzada de verdade nos Pull Requests.
**Revisão se mostra com o registro do GitHub, e não com uma frase**: para cada
PR incorporado na janela, quem abriu, quem foi convidado a revisar (o
CODEOWNERS convida o dono de cada área tocada), quem revisou e com que
resultado, e quem mesclou. Gerado, nunca escrito à mão — um PR mesclado sem
aprovação aparece como tal, e o documento diz isso em vez de omitir.

A janela começa depois de um PR — o do PDF da entrega anterior —, como a do
registro de commits (`docs/entrega/registrar_commits.js`): no mesmo dia do PDF
entraram PRs que já são da entrega seguinte.

Precisa do `gh` autenticado. Uso, da raiz do projeto:

    python scripts/registrar_revisoes.py --depois-do-pr 112 --saida docs/entrega/evidencias/sprint06
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
REPOSITORIO = "PedroMiranda243/gih-fabrica-de-software"

# O horário da equipe. Fixo, e não pelo nome do fuso: o Brasil não tem horário
# de verão desde 2019, e o `zoneinfo` no Windows depende de um pacote à parte.
HORARIO_LOCAL = timezone(timedelta(hours=-3))

ESTADOS = {
    "APPROVED": "aprovou",
    "CHANGES_REQUESTED": "pediu mudanças",
    "COMMENTED": "comentou",
    "DISMISSED": "revisão descartada",
}

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _local(instante: str) -> datetime:
    return datetime.fromisoformat(instante.replace("Z", "+00:00")).astimezone(HORARIO_LOCAL)


def prs_incorporados() -> list[dict]:
    r = subprocess.run(
        [
            "gh", "pr", "list", "-R", REPOSITORIO, "--state", "merged", "--limit", "500",
            "--json", "number,title,author,mergedAt,mergedBy,reviews,reviewRequests,comments",
        ],
        capture_output=True, text=True, encoding="utf-8",
    )
    if r.returncode:
        raise SystemExit(f"O gh falhou: {r.stderr.strip()}")
    return sorted(json.loads(r.stdout), key=lambda p: p["mergedAt"])


def registro(depois_do_pr: int) -> list[dict]:
    todos = prs_incorporados()
    marco = next((p for p in todos if p["number"] == depois_do_pr), None)
    if marco is None:
        raise SystemExit(f"O PR #{depois_do_pr} não está entre os incorporados.")
    itens = []
    for pr in (p for p in todos if p["mergedAt"] > marco["mergedAt"]):
        autor = pr["author"]["login"]
        revisoes = [
            {
                "revisor": r["author"]["login"],
                "estado": r["state"],
                "em": _local(r["submittedAt"]).isoformat(timespec="minutes"),
            }
            for r in pr["reviews"]
            if r["author"]["login"] != autor
        ]
        # Quem já revisou sai da lista de convidados; os dois juntos são todos os chamados.
        convidados = sorted(
            {r.get("login") or r.get("name", "") for r in pr["reviewRequests"]}
            | {r["revisor"] for r in revisoes}
        )
        itens.append(
            {
                "numero": pr["number"],
                "titulo": pr["title"],
                "mesclado_em": _local(pr["mergedAt"]).isoformat(timespec="minutes"),
                "autor": autor,
                "mesclado_por": (pr.get("mergedBy") or {}).get("login"),
                "convidados": convidados,
                "revisoes": revisoes,
                "aprovado": any(r["estado"] == "APPROVED" for r in revisoes),
                "comentarios_de_colegas": sum(
                    1 for c in pr["comments"] if c["author"]["login"] != autor
                ),
            }
        )
    return itens


def _cortar(texto: str, largura: int) -> str:
    if len(texto) <= largura:
        return texto
    corte = texto[: largura - 1]
    return corte[: corte.rfind(" ")].rstrip(" ,—-") + "…"


def texto(itens: list[dict], depois_do_pr: int) -> str:
    linhas = [
        "Registro das revisões dos Pull Requests — gerado do GitHub",
        f"https://github.com/{REPOSITORIO}",
        f"PRs incorporados depois do #{depois_do_pr}; gerado em "
        f"{datetime.now():%d/%m/%Y %H:%M} por scripts/registrar_revisoes.py",
        "",
    ]
    for item in itens:
        em = datetime.fromisoformat(item["mesclado_em"])
        linhas.append(f"#{item['numero']:<4} {em:%d/%m}  {_cortar(item['titulo'], 80)}")
        linhas.append(f"      aberto por {item['autor']} · mesclado por {item['mesclado_por']}")
        linhas.append(f"      convidados: {', '.join(item['convidados']) or 'ninguém'}")
        if item["revisoes"]:
            for i, r in enumerate(item["revisoes"]):
                quando = datetime.fromisoformat(r["em"])
                rotulo = "revisões:  " if i == 0 else " " * 11
                linhas.append(f"      {rotulo} {r['revisor']} "
                              f"{ESTADOS.get(r['estado'], r['estado'])} em {quando:%d/%m %H:%M}")
        else:
            linhas.append("      revisões:   nenhuma registrada no GitHub")
        if item["comentarios_de_colegas"]:
            linhas.append(f"      comentários de colegas na conversa: {item['comentarios_de_colegas']}")
        linhas.append("")

    aprovados = sum(item["aprovado"] for item in itens)
    so_revisados = sum(1 for item in itens if item["revisoes"] and not item["aprovado"])
    sem_revisao = sum(1 for item in itens if not item["revisoes"])
    linhas += [
        "Resumo",
        f"  PRs incorporados                               {len(itens):>4}",
        f"  com aprovação de um colega                     {aprovados:>4}",
        f"  com revisão de um colega, sem aprovação        {so_revisados:>4}",
        f"  sem revisão registrada no GitHub               {sem_revisao:>4}",
    ]

    convites = Counter(login for item in itens for login in item["convidados"])
    estados: dict[str, Counter] = {}
    for item in itens:
        for r in item["revisoes"]:
            estados.setdefault(r["revisor"], Counter())[r["estado"]] += 1
    if convites:
        linhas += ["", "Por colega convidado"]
        for login, n in sorted(convites.items(), key=lambda par: (-par[1], par[0])):
            c = estados.get(login, Counter())
            linhas.append(
                f"  {login:<24} convidado em {n:>3} · aprovou {c['APPROVED']:>3}"
                f" · pediu mudanças {c['CHANGES_REQUESTED']:>2} · comentou {c['COMMENTED']:>2}"
            )

    linhas += [
        "",
        f"Resultado: {len(itens)} PRs incorporados, {aprovados} com aprovação registrada de um "
        f"colega, {sem_revisao} sem revisão registrada.",
    ]
    return "\n".join(linhas) + "\n"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--depois-do-pr", type=int, required=True,
                   help="o PR que fecha a entrega anterior; a janela começa depois dele")
    p.add_argument("--saida", required=True, help="pasta das evidências da entrega")
    a = p.parse_args()

    itens = registro(a.depois_do_pr)
    destino = RAIZ / a.saida
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "revisoes.json").write_text(
        json.dumps(itens, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (destino / "revisoes.txt").write_text(texto(itens, a.depois_do_pr), encoding="utf-8")
    print(texto(itens, a.depois_do_pr).splitlines()[-1])


if __name__ == "__main__":
    main()
