"""Confere o acesso remoto contra o que está no ar — RNF30, ADR-014, história H102.

O RNF30 diz que o ambiente não fica alcançável pela internet nem pela rede
local, e que de fora da máquina só se chega por rede privada autenticada. "Está
configurado assim" não é evidência: um `ports: "5173:5173"` sem o `127.0.0.1`, ou
um `AllowFunnel: true`, e o sistema está na rua sem que nenhum teste reprove.
Este roteiro lê o que o Compose declara e pergunta ao que está rodando.

Três partes:

1. **As portas.** Toda porta publicada, de todo serviço e de todo perfil, está
   presa a `127.0.0.1`; a borda e o nó da rede privada não publicam nenhuma.
2. **A borda**, de dentro da rede do Compose, que é por onde o nó chega nela:
   a interface é a empacotada, e não o servidor de desenvolvimento; uma rota
   funda devolve a página; o `/api` passa; a documentação interativa da API não
   passa; os cabeçalhos de segurança saem uma vez só; e o cookie da sessão sai
   com `Secure`, `HttpOnly` e `SameSite`.
3. **O nó da rede privada.** O que ele serve vai para a borda, por HTTPS, e
   **sem Funnel** — que é o que separa a rede privada de um link público.

Uso, da raiz do repositório, com `docker compose --profile remoto up -d`:

    GIH_ADMIN_SENHA=... api/.venv/Scripts/python scripts/conferir_acesso_remoto.py

Só a biblioteca padrão e o `docker` da máquina. Sem a senha, a conferência do
cookie é pulada, e o roteiro diz; antes de o nó ser autorizado na conta, a do
que ele serve de fato também. Pulada não é aprovada: o resultado conta à parte.
A sessão aberta para ler o cookie é encerrada no fim.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
BORDA = "http://borda:8080"
SO_A_MAQUINA = "127.0.0.1"

# Roda dentro do contêiner da API, que está na mesma rede da borda e tem Python.
# Devolve um JSON só: quem decide o que é certo é este roteiro, e não a sonda.
SONDA = r'''
import json, os, urllib.error, urllib.request

BASE = os.environ["GIH_BORDA"]

def pedir(caminho, metodo="GET", corpo=None, cabecalhos=None):
    req = urllib.request.Request(BASE + caminho, data=corpo, method=metodo, headers=cabecalhos or {})
    try:
        r = urllib.request.urlopen(req, timeout=30)
    except urllib.error.HTTPError as e:
        r = e
    texto = r.read().decode("utf-8", "replace")
    return {
        "status": r.status if hasattr(r, "status") else r.code,
        "tipo": r.headers.get("Content-Type", ""),
        "cabecalhos": [[k, v] for k, v in r.headers.items()],
        "empacotada": "/assets/" in texto,
        "desenvolvimento": "/@vite/client" in texto or "/src/main.jsx" in texto,
        "openapi": '"openapi"' in texto or "swagger" in texto.lower(),
    }

saida = {c: pedir(c) for c in ("/", "/parceiros/12", "/docs", "/openapi.json", "/api/sessao/atual")}

senha = os.environ.get("GIH_ADMIN_SENHA")
if senha:
    corpo = json.dumps({"login": os.environ.get("GIH_ADMIN_LOGIN", "admin"), "senha": senha}).encode()
    entrada = pedir("/api/sessao", "POST", corpo, {"Content-Type": "application/json"})
    cookies = [v for k, v in entrada["cabecalhos"] if k.lower() == "set-cookie"]
    saida["login"] = {"status": entrada["status"], "marcas": []}
    if cookies:
        nome_valor, *marcas = [p.strip() for p in cookies[0].split(";")]
        # Só as marcas saem daqui: o valor do cookie é a sessão, e não vai para o relatório.
        saida["login"] = {"status": entrada["status"], "nome": nome_valor.split("=")[0],
                          "marcas": [m.lower() for m in marcas]}
        saida["saida"] = pedir("/api/sessao", "DELETE", None, {"Cookie": nome_valor})["status"]

print(json.dumps(saida))
'''


class Conferencias:
    def __init__(self) -> None:
        self.passaram = self.falharam = self.puladas = 0

    def confere(self, o_que: str, certo: bool, voltou: object = "") -> None:
        self.passaram += certo
        self.falharam += not certo
        detalhe = f"  — {voltou}" if voltou != "" and not certo else ""
        print(f"  {'ok   ' if certo else 'FALHA'} {o_que}{detalhe}")

    def pula(self, o_que: str, por_que: str) -> None:
        self.puladas += 1
        print(f"  pulou {o_que} — {por_que}")


def docker(*argumentos: str, entrada: str | None = None, ambiente: dict | None = None):
    return subprocess.run(
        ["docker", "compose", *argumentos], cwd=RAIZ, input=entrada, capture_output=True,
        text=True, encoding="utf-8", errors="replace", env={**os.environ, **(ambiente or {})},
    )


def titulo(texto: str) -> None:
    print(f"\n{texto}\n{'-' * len(texto)}")


# ------------------------------------------------------------------ 1. portas
def portas(c: Conferencias) -> dict:
    titulo("1. As portas — nada publicado fora da própria máquina")
    # Todos os perfis: uma porta aberta num perfil opcional é uma porta aberta.
    lido = docker("--profile", "*", "config", "--format", "json")
    if lido.returncode:
        c.confere("o Compose é lido", False, lido.stderr.strip()[:200])
        return {}
    compose = json.loads(lido.stdout)
    declaradas = {
        nome: [(p.get("host_ip", ""), p.get("published"), p.get("target")) for p in s.get("ports", [])]
        for nome, s in compose["services"].items()
    }
    for nome, lista in sorted(declaradas.items()):
        for ip, publicada, alvo in lista:
            print(f"  {nome:<10} {ip or '(todas as interfaces)'}:{publicada} → {alvo}")
    fora = [f"{n} {ip or '0.0.0.0'}:{pub}" for n, lista in declaradas.items()
            for ip, pub, _ in lista if ip != SO_A_MAQUINA]
    c.confere(f"toda porta declarada está presa a {SO_A_MAQUINA}", not fora, ", ".join(fora))
    for nome in ("borda", "tailscale"):
        c.confere(f"o serviço `{nome}` não publica porta nenhuma",
                  nome in declaradas and not declaradas[nome], declaradas.get(nome, "não existe"))

    # E o que está rodando de fato: o contêiner pode ter subido de outro arquivo.
    no_ar = [json.loads(linha) for linha in docker("ps", "--format", "json").stdout.splitlines()
             if linha.strip().startswith("{")]
    abertas = [f"{s['Service']} {p['URL']}:{p['PublishedPort']}" for s in no_ar
               for p in s.get("Publishers") or [] if p.get("PublishedPort") and p.get("URL") != SO_A_MAQUINA]
    c.confere(f"nenhum contêiner no ar publica porta fora de {SO_A_MAQUINA}", not abertas,
              ", ".join(abertas))
    return {"compose": compose, "no_ar": {s["Service"] for s in no_ar if s.get("State") == "running"}}


# ------------------------------------------------------------------- 2. borda
def _unico(resposta: dict, cabecalho: str) -> list[str]:
    return [v for k, v in resposta["cabecalhos"] if k.lower() == cabecalho.lower()]


def borda(c: Conferencias, no_ar: set[str]) -> None:
    titulo("2. A borda — o que quem chega de fora recebe")
    if not {"api", "borda"} <= no_ar:
        c.confere("a borda está no ar", False,
                  "suba com `docker compose --profile remoto up -d`")
        return
    passar = [v for v in ("GIH_ADMIN_SENHA", "GIH_ADMIN_LOGIN") if os.environ.get(v)]
    argumentos = [a for v in passar for a in ("-e", v)]
    lido = docker("exec", "-T", "-e", "GIH_BORDA", *argumentos, "api", "python", "-",
                  entrada=SONDA, ambiente={"GIH_BORDA": BORDA})
    if lido.returncode:
        c.confere("a borda responde pela rede do Compose", False, lido.stderr.strip()[-300:])
        return
    r = json.loads(lido.stdout.strip().splitlines()[-1])

    raiz, funda = r["/"], r["/parceiros/12"]
    c.confere("a página é a interface empacotada, e não o servidor de desenvolvimento",
              raiz["status"] == 200 and raiz["empacotada"] and not raiz["desenvolvimento"], raiz)
    c.confere("uma rota funda devolve a página, que abre a tela",
              funda["status"] == 200 and funda["empacotada"], funda["status"])
    api = r["/api/sessao/atual"]
    c.confere("o `/api` chega à API: sem sessão, a resposta é o 401 dela",
              api["status"] == 401 and "json" in api["tipo"], (api["status"], api["tipo"]))
    for caminho in ("/docs", "/openapi.json"):
        c.confere(f"a documentação interativa da API não passa pela borda ({caminho})",
                  not r[caminho]["openapi"], r[caminho]["tipo"])
    for resposta, de in ((raiz, "na página"), (api, "no `/api`")):
        c.confere(f"`nosniff` e `X-Frame-Options: DENY` saem uma vez só {de}",
                  _unico(resposta, "X-Content-Type-Options") == ["nosniff"]
                  and _unico(resposta, "X-Frame-Options") == ["DENY"],
                  (_unico(resposta, "X-Content-Type-Options"), _unico(resposta, "X-Frame-Options")))

    if "login" not in r:
        c.pula("o cookie de sessão sai com `Secure`, `HttpOnly` e `SameSite`",
               "sem `GIH_ADMIN_SENHA`, o roteiro não abre sessão")
        return
    login = r["login"]
    marcas = set(login["marcas"])
    print(f"  o login pela borda respondeu {login['status']}; o cookie `{login.get('nome', '?')}` "
          f"saiu com: {', '.join(sorted(marcas)) or 'nenhuma marca'}")
    c.confere("o cookie de sessão sai com `Secure`, posto pela borda",
              login["status"] == 201 and "secure" in marcas, sorted(marcas))
    c.confere("e continua `HttpOnly` e `SameSite=Lax`, como a API o manda (RNF10)",
              {"httponly", "samesite=lax"} <= marcas, sorted(marcas))
    c.confere("a sessão aberta para a conferência foi encerrada", r.get("saida") == 204, r.get("saida"))


# ---------------------------------------------------------------------- 3. nó
def _funnel_ligado(serve: dict) -> list[str]:
    return [onde for onde, ligado in (serve.get("AllowFunnel") or {}).items() if ligado]


def _destinos(serve: dict) -> set[str]:
    return {h.get("Proxy", "") for web in (serve.get("Web") or {}).values()
            for h in (web.get("Handlers") or {}).values()}


def no_da_rede(c: Conferencias, compose: dict, no_ar: set[str]) -> None:
    titulo("3. O nó da rede privada — o que ele serve, e para quem")
    declarado = json.loads(compose["configs"]["tailscale_serve"]["content"].replace("$$", "$"))
    c.confere("o que o Compose manda servir vai para a borda, por HTTPS na 443",
              _destinos(declarado) == {BORDA} and declarado["TCP"] == {"443": {"HTTPS": True}},
              (_destinos(declarado), declarado.get("TCP")))
    c.confere("e sem Funnel: o endereço só existe dentro da rede privada",
              bool(declarado.get("AllowFunnel")) and not _funnel_ligado(declarado),
              declarado.get("AllowFunnel"))

    if "tailscale" not in no_ar:
        c.pula("o que o nó serve de fato", "o serviço `tailscale` não está no ar")
        return
    estado = json.loads(docker("exec", "-T", "tailscale", "tailscale", "status", "--json").stdout)
    if estado.get("BackendState") != "Running":
        c.pula("o que o nó serve de fato",
               f"o nó ainda não foi autorizado na conta (estado: {estado.get('BackendState')}); "
               "o endereço está em `docker compose --profile remoto logs tailscale`")
        return
    nome = (estado.get("Self") or {}).get("DNSName", "").rstrip(".")
    print(f"  o nó está na rede privada como https://{nome}")
    servindo = json.loads(
        docker("exec", "-T", "tailscale", "tailscale", "serve", "status", "--json").stdout or "{}"
    )
    c.confere("o nó serve a borda, e só ela", _destinos(servindo) == {BORDA}, _destinos(servindo))
    c.confere("e o Funnel está desligado no que está rodando",
              not _funnel_ligado(servindo), _funnel_ligado(servindo))


def principal() -> int:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    print("Conferência do acesso remoto — RNF30, ADR-014")
    c = Conferencias()
    lido = portas(c)
    if lido:
        borda(c, lido["no_ar"])
        no_da_rede(c, lido["compose"], lido["no_ar"])
    total = c.passaram + c.falharam
    pulou = f"; {c.puladas} pulada(s), que não contam como aprovadas" if c.puladas else ""
    print(f"\nResultado: {c.passaram} de {total} conferências passaram{pulou}.")
    return 1 if c.falharam else 0


if __name__ == "__main__":
    raise SystemExit(principal())
