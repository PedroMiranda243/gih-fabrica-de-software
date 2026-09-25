"""Mostra que os dados sobrevivem a desligar e religar a aplicação.

A quarta entrega da disciplina pede evidência de persistência: o dado gravado
continua lá depois de fechar e reabrir o sistema. Este script faz isso de
verdade, e não por simulação:

1. um analista cadastra e altera um parceiro, e o estado é anotado — o
   parceiro, os totais da base, o painel, os limiares da segmentação, e, desde
   a Sprint 05, a versão do modelo em uso e a previsão de um parceiro;
2. `docker compose down` **remove** os contêineres — não os pausa — e o script
   confere que a API parou de responder;
3. `docker compose up -d` cria contêineres novos, e o script espera a API;
4. com **o mesmo cookie de antes**, sem novo login, tudo é lido de novo e
   comparado campo a campo.

**O modelo é parte da prova desde a Sprint 05.** Os pesos ficam na linha do
treino (ADR-010): se a versão em uso ou a previsão mudassem depois de religar, é
porque algo morava na memória do processo.

O cookie é parte da prova: a sessão tem estado no servidor (`sessao_acesso`),
então ela também é dado persistido, e não algo que só existia na memória do
processo que acabou de morrer.

**Nunca `down -v`.** O `-v` apaga o volume do banco — a base de demonstração
inteira. O comando é montado num lugar só, e esse lugar recusa a opção.

Como a transcrição, não deixa resíduo: no fim, o que o script gravou sai do
banco e o analista é desativado (ver `e2e/limpeza.py`).

Precisa do Docker Desktop aberto e da aplicação no ar. Uso, da pasta `api/`:
    GIH_ADMIN_SENHA=... python e2e/persistencia.py \
        > ../docs/entrega/evidencias/sprint05/persistencia.txt
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import subprocess
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from e2e.transcricao import LARGURA, desfazer, titulo, troca  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = Path(__file__).resolve().parents[2]
SENHA = "persistencia-de-evidencia"

# Quanto esperar a API voltar. O contêiner aplica as migrações antes de servir;
# numa máquina lenta, com o Postgres ainda conferindo o volume, isso passa de um
# minuto.
ESPERA_MAXIMA = 240
OPCOES_PROIBIDAS = {"-v", "--volumes", "--rmi"}


def compose(*argumentos: str) -> list[str]:
    """Roda `docker compose` na raiz do projeto e devolve as linhas da saída.

    O único lugar que monta o comando — e por isso o único que precisa recusar o
    `-v`. A saída vem em texto simples, sem cor nem barra de progresso, para
    poder entrar na evidência.
    """
    proibidas = OPCOES_PROIBIDAS.intersection(argumentos)
    if proibidas:
        raise ValueError(f"Opção recusada: {', '.join(sorted(proibidas))} apagaria dados.")
    r = subprocess.run(
        ["docker", "compose", "--ansi", "never", "--progress", "plain", *argumentos],
        cwd=RAIZ, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if r.returncode != 0:
        raise RuntimeError(f"docker compose {' '.join(argumentos)} falhou:\n{r.stderr.strip()}")
    return [linha for linha in (r.stdout + r.stderr).splitlines() if linha.strip()]


def conteineres() -> dict[str, str]:
    """Serviço → identificador do contêiner em execução."""
    linhas = compose("ps", "--format", "{{.Service}}\t{{.ID}}")
    return dict(linha.split("\t") for linha in linhas)


def volume_do_banco() -> str | None:
    """Nome e data de criação do volume do Postgres, se ele existir."""
    projeto = json.loads("\n".join(compose("config", "--format", "json")))["name"]
    r = subprocess.run(
        ["docker", "volume", "ls", "-q",
         "--filter", f"label=com.docker.compose.project={projeto}",
         "--filter", "label=com.docker.compose.volume=dados_postgres"],
        capture_output=True, text=True,
    )
    nome = r.stdout.strip()
    if not nome:
        return None
    criado = subprocess.run(
        ["docker", "volume", "inspect", nome, "--format", "{{.CreatedAt}}"],
        capture_output=True, text=True,
    ).stdout.strip()
    return f"{nome}, criado em {criado}"


def api_responde(url: str) -> bool:
    try:
        return httpx.get(f"{url}/api/health", timeout=3).status_code == 200
    except httpx.HTTPError:
        return False


def retrato(c: httpx.Client, admin: httpx.Client, alvo: int, maior: int) -> dict:
    """Tudo o que se compara depois: lido pela API, como a tela lê.

    Os limiares vêm pela sessão do administrador, que é o único perfil que os
    enxerga (RF21) — e que, assim, também atravessa o reinício.
    """
    return {
        "parceiro": c.get(f"/api/parceiros/{alvo}").json(),
        "total_de_parceiros": c.get("/api/parceiros?tamanho=1").json()["total"],
        "painel": c.get("/api/painel/indicadores").json(),
        "limiares": admin.get("/api/configuracao/segmentacao").json(),
        "modelo": _modelo(admin.get("/api/modelo").json()),
        "previsao": c.get(f"/api/parceiros/{maior}/previsao").json(),
    }


def _modelo(estado: dict) -> dict:
    """A versão em uso e as métricas do treino que a produziu."""
    treino = estado.get("treino_da_versao") or {}
    return {
        "versao_em_uso": estado.get("versao_em_uso"),
        "treino": treino.get("id"),
        "concluido_em": treino.get("concluido_em"),
        "metricas": treino.get("metricas"),
    }


def mostrar_retrato(r: dict) -> None:
    p, painel, limiares = r["parceiro"], r["painel"], r["limiares"]
    periodo = painel["periodo"]
    print(f"  parceiro           {p['nome']} · {p['status']} · {p['contato']}"
          f" · {p['categoria']['nome'] if p['categoria'] else 'sem categoria'}")
    print(f"  parceiros na base  {r['total_de_parceiros']}")
    if periodo:
        print(f"  painel             {periodo['data_inicio']} a {periodo['data_fim']}"
              f" · faturamento {painel['faturamento']} · {painel['pedidos']} pedidos")
    print(f"  limiares           Top {limiares['top_n']} · tendência em"
          f" {limiares['periodos_tendencia']} períodos · recém-chegado até"
          f" {limiares['periodos_novato']}")
    modelo, previsao = r["modelo"], r["previsao"]
    if modelo["versao_em_uso"]:
        metricas = modelo["metricas"]
        print(f"  modelo em uso      {modelo['versao_em_uso']} (treino {modelo['treino']})"
              f" · MAPE {metricas['mape_modelo']:.4f} · Brier {metricas['brier_modelo']:.4f}")
    else:
        print("  modelo em uso      nenhum — o modelo não foi treinado")
    if previsao.get("disponivel"):
        print(f"  previsão           R$ {previsao['faturamento_previsto']} · risco"
              f" {previsao['probabilidade_queda']:.4f} · {previsao['modelo_versao']}")


def mostrar_conteineres(ids: dict[str, str]) -> None:
    if not ids:
        print("  (nenhum contêiner)")
    for servico, ident in sorted(ids.items()):
        print(f"  {servico:<10} {ident}")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--url", default=os.environ.get("GIH_URL", "http://localhost:8000"))
    p.add_argument("--login", default=os.environ.get("GIH_ADMIN_LOGIN", "admin"))
    p.add_argument("--senha", default=os.environ.get("GIH_ADMIN_SENHA", ""))
    a = p.parse_args()

    if not a.senha:
        print("Informe a senha do administrador com --senha ou GIH_ADMIN_SENHA.", file=sys.stderr)
        return 2
    if not api_responde(a.url):
        print(f"A API não responde em {a.url}. Suba com: docker compose up -d", file=sys.stderr)
        return 2

    marca = f"t{secrets.randbelow(100000):05d}"
    print(f"Persistência: os dados sobrevivem a desligar e religar a aplicação · {a.url}")
    print("Dados sintéticos; nenhum nome real de empresa ou pessoa.")

    with httpx.Client(base_url=a.url, timeout=30) as admin:
        if admin.post("/api/sessao", json={"login": a.login, "senha": a.senha}).status_code != 201:
            print("Não consegui autenticar como administrador.", file=sys.stderr)
            return 2
        try:
            conferencias = demonstrar(a.url, admin, marca)
        finally:
            # A sessão do administrador também atravessou o reinício: se ela não
            # valesse mais, a limpeza falharia aqui, e a execução reprovaria.
            limpo = desfazer(admin, marca)

    passaram = sum(ok for _, ok in conferencias)
    print(f"\n{'=' * LARGURA}")
    print(f"Resultado: {passaram} de {len(conferencias)} conferências passaram.")
    return 0 if limpo and passaram == len(conferencias) else 1


def demonstrar(url: str, admin: httpx.Client, marca: str) -> list[tuple[str, bool]]:
    analista = f"{marca}.analista"
    titulo("Preparação — um analista, que é quem gerencia parceiros (UC04)")
    troca(admin, "POST", "/api/usuarios", {
        "login": analista, "nome": "Analista da Evidência", "senha": SENHA, "perfil": "ANALISTA",
    })

    with httpx.Client(base_url=url, timeout=30) as c:
        # ---------------------------------------------------------------- 1
        titulo("[1/4] Antes de desligar — o analista cadastra e altera um parceiro")
        troca(c, "POST", "/api/sessao", {"login": analista, "senha": SENHA})
        categoria = troca(c, "POST", "/api/categorias", {"nome": f"Categoria {marca}"}).json()
        alvo = troca(c, "POST", "/api/parceiros", {
            "nome": f"Comércio {marca}", "status": "PROSPECCAO",
        }).json()["id"]
        troca(c, "PATCH", f"/api/parceiros/{alvo}", {
            "status": "ATIVO", "categoria_id": categoria["id"], "contato": "contato@exemplo.test",
        })

        # O maior do período mais recente: está nele, então tem previsão.
        maior = c.get("/api/parceiros", params={
            "tamanho": 1, "ordenar_por": "faturamento", "descendente": True,
        }).json()["itens"][0]["id"]
        antes = retrato(c, admin, alvo, maior)
        print("\nO estado anotado para comparar depois:")
        mostrar_retrato(antes)
        ids_antes = conteineres()
        print("\nContêineres em execução:")
        mostrar_conteineres(ids_antes)
        volume_antes = volume_do_banco()
        print(f"\nVolume do banco: {volume_antes}")

        # ---------------------------------------------------------------- 2
        titulo("[2/4] Desligar — docker compose down")
        print("\n$ docker compose down")
        for linha in compose("down"):
            print(f"  {linha}")
        api_parou = not api_responde(url)
        print(f"\nA API responde? {'não' if api_parou else 'SIM — o down não derrubou a API'}")
        ids_desligado = conteineres()
        print("Contêineres depois do down:")
        mostrar_conteineres(ids_desligado)
        print(f"Volume do banco: {volume_do_banco()}")

        # ---------------------------------------------------------------- 3
        titulo("[3/4] Religar — docker compose up -d")
        print("\n$ docker compose up -d")
        for linha in compose("up", "-d"):
            print(f"  {linha}")
        inicio = time.monotonic()
        while not api_responde(url):
            if time.monotonic() - inicio > ESPERA_MAXIMA:
                raise RuntimeError(f"A API não voltou em {ESPERA_MAXIMA} s.")
            time.sleep(2)
        print(f"\nA API voltou a responder em {time.monotonic() - inicio:.0f} s.")
        ids_depois = conteineres()
        print("Contêineres novos:")
        mostrar_conteineres(ids_depois)

        # ---------------------------------------------------------------- 4
        titulo("[4/4] Depois de religar — o mesmo cookie de antes, sem novo login")
        sessao = troca(c, "GET", "/api/sessao/atual")
        troca(c, "GET", f"/api/parceiros/{alvo}")
        depois = retrato(c, admin, alvo, maior)
        print("\nO estado lido agora:")
        mostrar_retrato(depois)

    conferencias = [
        ("o down removeu os contêineres, e a API parou de responder",
         api_parou and not ids_desligado),
        ("o up criou contêineres novos — não é o mesmo processo de antes",
         bool(ids_depois) and not set(ids_antes.values()) & set(ids_depois.values())),
        ("o volume do banco é o mesmo, com a mesma data de criação",
         volume_antes is not None and volume_antes == volume_do_banco()),
        ("a sessão aberta antes de desligar continua valendo",
         sessao.status_code == 200 and sessao.json()["login"] == analista),
        ("o parceiro voltou com todos os campos iguais",
         depois["parceiro"] == antes["parceiro"]),
        ("a alteração feita antes de desligar continua lá",
         depois["parceiro"]["status"] == "ATIVO"
         and depois["parceiro"]["contato"] == "contato@exemplo.test"
         and (depois["parceiro"]["categoria"] or {}).get("id") == categoria["id"]),
        ("a base tem o mesmo número de parceiros",
         depois["total_de_parceiros"] == antes["total_de_parceiros"]),
        ("o painel mostra os mesmos indicadores",
         depois["painel"] == antes["painel"]),
        ("os limiares da segmentação são os mesmos",
         depois["limiares"] == antes["limiares"]),
        ("a versão do modelo em uso é a mesma, com as mesmas métricas",
         bool(antes["modelo"]["versao_em_uso"]) and depois["modelo"] == antes["modelo"]),
        ("a previsão do parceiro é a mesma, da mesma versão",
         antes["previsao"].get("disponivel") is True and depois["previsao"] == antes["previsao"]),
    ]
    print("\nConferências:")
    for texto, ok in conferencias:
        print(f"  {'ok   ' if ok else 'FALHA'} {texto}")
    return conferencias


if __name__ == "__main__":
    raise SystemExit(main())
