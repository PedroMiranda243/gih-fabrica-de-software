"""Exporta a documentação da API para o repositório (H107).

O Swagger (`/api/docs`) só existe com o sistema no ar. Para ler a API no GitHub,
ou na entrega, este script grava:

- `docs/api/openapi.json` — a especificação inteira, como a API a gera;
- `docs/13-api.md` — a referência legível, por área: para cada rota, quem pode
  chamar, os parâmetros, o corpo com exemplo e as respostas, com um exemplo de
  uso de ponta a ponta no começo.

Os dois saem do `app.openapi()` — o mesmo documento do Swagger —, e não são
escritos à mão: `api/tests/test_documentacao_api.py` reprova se a API mudar e os
arquivos não forem gerados de novo. Uso, da raiz do projeto:

    api/.venv/Scripts/python scripts/exportar_api.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO_JSON = RAIZ / "docs" / "api" / "openapi.json"
ARQUIVO_MD = RAIZ / "docs" / "13-api.md"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def especificacao() -> dict[str, Any]:
    """O OpenAPI da aplicação, gerado em memória: não abre conexão com o banco."""
    os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://gih:gih@localhost:5433/gih")
    sys.path.insert(0, str(RAIZ / "api"))
    from app.main import app

    return app.openapi()


def _tipo(esquema: dict[str, Any]) -> str:
    if "$ref" in esquema:
        return esquema["$ref"].rsplit("/", 1)[-1]
    if "anyOf" in esquema or "oneOf" in esquema:
        opcoes = [_tipo(e) for e in esquema.get("anyOf", esquema.get("oneOf", []))]
        return " ou ".join(dict.fromkeys(o for o in opcoes if o != "null")) + (
            " (opcional)" if "null" in opcoes else ""
        )
    if esquema.get("type") == "array":
        return f"lista de {_tipo(esquema.get('items', {}))}"
    return esquema.get("format") or esquema.get("type", "—")


def _celula(texto: str) -> str:
    return " ".join(str(texto).split()).replace("|", "\\|")


def _corpo(op: dict[str, Any]) -> list[str]:
    corpo = op.get("requestBody")
    if not corpo:
        return []
    linhas = []
    for tipo, conteudo in corpo["content"].items():
        nome = _tipo(conteudo.get("schema", {}))
        linhas.append(f"**Corpo** (`{tipo}`): `{nome}`.")
        if "example" in conteudo:
            exemplo = json.dumps(conteudo["example"], ensure_ascii=False, indent=2)
            linhas += ["", "```json", exemplo, "```"]
    return linhas + [""]


def markdown(spec: dict[str, Any]) -> str:
    info = spec["info"]
    saida = [
        "# 13 — Referência da API",
        "",
        "**Projeto:** Growth Intelligence Hub (GIH)",
        f"**Versão da API:** {info['version']} · **Gerado por** `scripts/exportar_api.py` — não edite à mão",
        "",
        "> **Este documento sai da própria API.** O `app.openapi()` — o mesmo documento do Swagger, em",
        "> `/api/docs` com o sistema no ar — é exportado para `docs/api/openapi.json` e convertido aqui,",
        "> rota por rota. Um teste reprova o Pull Request que mude a API sem gerar os dois de novo. Os",
        "> esquemas completos de cada corpo e de cada resposta estão no `openapi.json`.",
        "",
        "## Como usar",
        "",
        info["description"].replace("\n## ", "\n### "),
        "",
        "## Exemplo de uso, de ponta a ponta",
        "",
        "Com o sistema no ar (`docker compose up -d`), em Python, com o `httpx` — o cliente guarda o",
        "cookie da sessão entre as chamadas:",
        "",
        "```python",
        "import httpx",
        "",
        'api = httpx.Client(base_url="http://localhost:8000")',
        'r = api.post("/api/sessao", json={"login": "gestora", "senha": "uma frase longa de senha"})',
        "r.raise_for_status()                                  # 201, e o cookie gih_sessao",
        "",
        'emrisco = api.get("/api/parceiros", params={"segmento": "EM_RISCO", "tamanho": 5}).json()',
        'print(emrisco["total"], [p["nome"] for p in emrisco["itens"]])',
        "",
        'novo = api.post("/api/parceiros", json={"nome": "Ponto Azul 9", "status": "ATIVO"})',
        "print(novo.status_code, novo.json())                # 201, ou 409 se o nome já existe",
        "",
        'csv = api.get("/api/parceiros/exportacao.csv", params={"segmento": "EM_RISCO"})',
        'open("em-risco.csv", "wb").write(csv.content)        # o mesmo recorte, em CSV',
        "",
        'api.delete("/api/sessao")                            # 204: a sessão termina no servidor',
        "```",
        "",
        "O mesmo, com o `curl`, guardando o cookie num arquivo:",
        "",
        "```bash",
        "curl -c sessao.txt -H 'Content-Type: application/json' \\",
        "     -d '{\"login\":\"gestora\",\"senha\":\"uma frase longa de senha\"}' http://localhost:8000/api/sessao",
        "curl -b sessao.txt 'http://localhost:8000/api/parceiros?segmento=EM_RISCO&tamanho=5'",
        "curl -b sessao.txt -X DELETE http://localhost:8000/api/sessao",
        "```",
        "",
        "## As áreas",
        "",
        "| Área | O que tem | Rotas |",
        "|---|---|---|",
    ]
    por_area: dict[str, list[tuple[str, str, dict]]] = {t["name"]: [] for t in spec.get("tags", [])}
    for caminho, ops in spec["paths"].items():
        for metodo, op in ops.items():
            por_area.setdefault(op.get("tags", ["—"])[0], []).append((metodo.upper(), caminho, op))
    for tag in spec.get("tags", []):
        saida.append(f"| {tag['name'].capitalize()} | {tag['description']} | {len(por_area[tag['name']])} |")
    total = sum(len(v) for v in por_area.values())
    saida += ["", f"**{total} operações.**", ""]

    for tag in spec.get("tags", []):
        saida += [f"## {tag['name'].capitalize()}", "", tag["description"], ""]
        for metodo, caminho, op in por_area[tag["name"]]:
            saida += [f"### `{metodo} {caminho}` — {op['summary']}", "", op.get("description", ""), ""]
            parametros = op.get("parameters", [])
            if parametros:
                saida += ["| Parâmetro | Onde | Tipo | Obrigatório | Descrição |", "|---|---|---|---|---|"]
                for prm in parametros:
                    saida.append(
                        f"| `{prm['name']}` | {prm['in']} | {_celula(_tipo(prm.get('schema', {})))} | "
                        f"{'sim' if prm.get('required') else 'não'} | {_celula(prm.get('description', ''))} |"
                    )
                saida.append("")
            saida += _corpo(op)
            saida += ["| Resposta | Quando |", "|---|---|"]
            for codigo, resposta in op.get("responses", {}).items():
                esquemas = [
                    f"`{_tipo(c['schema'])}`" if c.get("schema", {}).get("type") != "string" else f"`{tipo}`"
                    for tipo, c in resposta.get("content", {}).items()
                    if c.get("schema")
                ]
                corpo = f" — {', '.join(esquemas)}" if esquemas else ""
                saida.append(f"| `{codigo}` | {_celula(resposta.get('description', ''))}{corpo} |")
            saida.append("")
    return "\n".join(saida).rstrip() + "\n"


def main() -> None:
    spec = especificacao()
    ARQUIVO_JSON.parent.mkdir(parents=True, exist_ok=True)
    ARQUIVO_JSON.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ARQUIVO_MD.write_text(markdown(spec), encoding="utf-8")
    operacoes = sum(len(v) for v in spec["paths"].values())
    print(f"{operacoes} operações — {ARQUIVO_JSON.relative_to(RAIZ)} e {ARQUIVO_MD.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
