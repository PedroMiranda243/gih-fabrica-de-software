"""A instalação do zero, como o README a ensina, num clone novo — H110.

A Release Candidate precisa de evidência de que o sistema **se instala**, e não
só de que funciona na máquina de quem o escreveu. Este script faz o que o README
manda, numa pasta temporária, e transcreve cada passo:

1. clona o repositório (o GitHub, na referência pedida — a tag da versão);
2. copia o `.env.example` para `.env`, sem mudar nada;
3. `docker compose up -d`, que constrói as imagens e sobe os três serviços;
4. confere a saúde da API, a interface e a linha "Senha sorteada" no log, e
   entra como administrador com ela — **a senha nunca é impressa**;
5. `popular-demonstracao`, e o banco pelo `psql`;
6. a documentação da API nos endereços do README;
7. a verificação de ponta a ponta e a persistência, as do próprio clone;
8. desmonta o projeto do ensaio, com o volume e as imagens dele.

**O ensaio é um projeto à parte do Docker**, `gih-rc`, e nunca o da equipe. O
`down -v` do fim só roda depois de conferir que o Compose fala com o projeto
`gih-rc` — o volume do sistema principal, com a base de demonstração, não entra
nisso (CLAUDE.md: nunca `down -v` no projeto principal).

**As portas são as do README** (5173, 8000 e 5433), e por isso o sistema
principal precisa estar parado: o script recusa começar com alguma delas ocupada.

Não substitui a H72: quem roda este script, em geral, escreveu o código. A
validação do README por quem não o escreveu segue o `docs/validacao-do-readme.md`.

Uso, da raiz do projeto, com o sistema principal parado (`docker compose stop`):

    api/.venv/Scripts/python scripts/instalar_do_zero.py --ref v1.0.0-rc.1 \\
        > docs/entrega/evidencias/sprint10/instalacao.txt
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ORIGEM = "https://github.com/PedroMiranda243/gih-fabrica-de-software.git"
PROJETO = "gih-rc"
API = "http://localhost:8000"
WEB = "http://localhost:5173"
PORTAS = {5173: "a interface", 8000: "a API", 5433: "o banco"}
ESPERA_MAXIMA = 300
LARGURA = 78
# O Compose narra cada passo duas vezes, no gerúndio e no fim; a transcrição fica com o fim.
EM_ANDAMENTO = re.compile(r"\s(Building|Creating|Starting|Waiting|Stopping|Removing|Recreate)\s*$")


def titulo(texto: str) -> None:
    print(f"\n{'=' * LARGURA}\n{texto}\n{'=' * LARGURA}", flush=True)


def ocupadas() -> list[str]:
    livres = []
    for porta, quem in PORTAS.items():
        with socket.socket() as s:
            s.settimeout(0.5)
            if s.connect_ex(("127.0.0.1", porta)) == 0:
                livres.append(f"{porta} ({quem})")
    return livres


class Ensaio:
    """O clone, o Compose do projeto `gih-rc` e as conferências do caminho."""

    def __init__(self, pasta: Path) -> None:
        self.pasta = pasta
        self.conferencias: list[tuple[str, bool]] = []
        self.ambiente = {**os.environ, "COMPOSE_PROJECT_NAME": PROJETO}
        # O DATABASE_URL da máquina apontaria os roteiros para outro banco; o do
        # clone vem do .env dele, como para quem segue o README.
        self.ambiente.pop("DATABASE_URL", None)

    def conferir(self, texto: str, ok: bool) -> bool:
        self.conferencias.append((texto, ok))
        print(f"  {'ok   ' if ok else 'FALHA'} {texto}", flush=True)
        return ok

    def rodar(
        self, comando: list[str], *, mostrar: bool = True, onde: Path | None = None,
        filtro=None, tempo: int = 1800, como: str | None = None,
    ) -> subprocess.CompletedProcess:
        if mostrar:
            print(f"\n$ {como or ' '.join(comando)}", flush=True)
        r = subprocess.run(
            comando, cwd=onde or self.pasta, env=self.ambiente, capture_output=True,
            text=True, encoding="utf-8", errors="replace", timeout=tempo,
        )
        if mostrar:
            for linha in (r.stdout + r.stderr).splitlines():
                # Nada que fale de senha vai para a transcrição: o anexo sai do repositório.
                if (
                    not linha.strip() or "senha" in linha.lower() or EM_ANDAMENTO.search(linha)
                    or (filtro and not filtro(linha))
                ):
                    continue
                print(f"  {linha}")
        return r

    def compose(self, *argumentos: str, como: str | None = None, **opcoes) -> subprocess.CompletedProcess:
        # Na transcrição, o comando como o README o escreve, sem as opções de saída.
        return self.rodar(
            ["docker", "compose", "--ansi", "never", *argumentos],
            como=como or "docker compose " + " ".join(argumentos), **opcoes,
        )

    def projeto_do_compose(self) -> str:
        r = self.compose("config", "--format", "json", mostrar=False)
        return json.loads(r.stdout)["name"] if r.returncode == 0 else ""

    def esperar_api(self) -> float | None:
        inicio = time.monotonic()
        while time.monotonic() - inicio < ESPERA_MAXIMA:
            try:
                if httpx.get(f"{API}/api/health", timeout=3).status_code == 200:
                    return time.monotonic() - inicio
            except httpx.HTTPError:
                pass
            time.sleep(2)
        return None

    def senha_sorteada(self) -> tuple[int, str | None]:
        """Quantas linhas "Senha sorteada" o log tem, e a senha — que não é impressa."""
        r = self.compose("logs", "--no-log-prefix", "api", mostrar=False)
        linhas = [x for x in r.stdout.splitlines() if "Senha sorteada:" in x]
        senha = linhas[-1].split("Senha sorteada:", 1)[1].strip() if linhas else None
        return len(linhas), senha

    def roteiro(self, nome: str, senha: str, rotulo_resultado: str) -> tuple[bool, str]:
        """Roda um roteiro de `api/e2e/` do clone, e devolve se passou e a linha do resultado."""
        ambiente = {**self.ambiente, "GIH_ADMIN_SENHA": senha, "PYTHONIOENCODING": "utf-8"}
        print(f"\n$ python e2e/{nome}", flush=True)
        r = subprocess.run(
            [sys.executable, f"e2e/{nome}"], cwd=self.pasta / "api", env=ambiente,
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800,
        )
        resultado = next(
            (x.strip() for x in reversed(r.stdout.splitlines()) if rotulo_resultado in x), ""
        )
        print(f"  {resultado or '(sem a linha do resultado)'}")
        if r.returncode:
            for linha in (r.stdout + r.stderr).splitlines()[-15:]:
                if "senha" not in linha.lower():
                    print(f"  | {linha}")
        return r.returncode == 0 and bool(resultado), resultado


def principal(ref: str, origem: str, manter: bool, sem_cache: bool) -> int:
    print("Instalação do zero — o README seguido num clone novo (H110)")
    # O platform.release() diz "10" também no Windows 11; a versão traz o número da compilação.
    print(f"{datetime.now():%d/%m/%Y %H:%M} · {platform.system()} {platform.version()}")
    docker = subprocess.run(
        ["docker", "version", "--format", "{{.Server.Version}}"],
        capture_output=True, text=True, encoding="utf-8",
    ).stdout.strip()
    compose = subprocess.run(
        ["docker", "compose", "version", "--short"], capture_output=True, text=True, encoding="utf-8"
    ).stdout.strip()
    print(f"Docker {docker or '?'} · Compose {compose or '?'} · projeto do ensaio: {PROJETO}")

    if presas := ocupadas():
        print(
            f"\nPortas ocupadas: {', '.join(presas)}. O ensaio usa as portas do README; pare o "
            "sistema principal (docker compose stop) e rode de novo.",
            file=sys.stderr,
        )
        return 2

    raiz = Path(tempfile.mkdtemp(prefix="gih-rc-"))
    pasta = raiz / "gih-fabrica-de-software"
    ensaio = Ensaio(pasta)
    try:
        titulo("[1/7] O clone e o .env — os dois primeiros comandos do README")
        clone = ensaio.rodar(
            ["git", "clone", "--quiet", "--depth", "1", "--branch", ref, origem, str(pasta)],
            onde=raiz, como=f"git clone --depth 1 --branch {ref} {origem}",
        )
        if not ensaio.conferir(f"o clone de {ref} veio", clone.returncode == 0):
            return 1
        commit = ensaio.rodar(["git", "log", "-1", "--format=%h %s"], mostrar=False).stdout.strip()
        print(f"  commit: {commit}")
        shutil.copyfile(pasta / ".env.example", pasta / ".env")
        print("\n$ cp .env.example .env")
        ensaio.conferir("o .env é a cópia do .env.example, sem mudança", True)

        titulo("[2/7] docker compose up -d — constrói as imagens e sobe os serviços")
        inicio = time.monotonic()
        if sem_cache:
            # As imagens construídas de novo, camada por camada, e não lidas do cache do Docker.
            construcao = ensaio.compose(
                "build", "--no-cache", filtro=lambda x: not x.strip().startswith(("#", "=>")),
                tempo=5400,
            )
            if not ensaio.conferir("as imagens foram construídas sem o cache", construcao.returncode == 0):
                return 1
        subida = ensaio.compose(
            "up", "-d", filtro=lambda x: not x.strip().startswith(("#", "=>")), tempo=3600
        )
        print(f"\n  em {time.monotonic() - inicio:.0f} s")
        if not ensaio.conferir("o docker compose up -d terminou sem erro", subida.returncode == 0):
            return 1
        ensaio.conferir(
            f"o Compose fala com o projeto do ensaio ({PROJETO})",
            ensaio.projeto_do_compose() == PROJETO,
        )

        titulo("[3/7] A saúde, a interface e o primeiro acesso")
        demora = ensaio.esperar_api()
        saude = httpx.get(f"{API}/api/health", timeout=5).json() if demora is not None else {}
        print(f"\n$ GET {API}/api/health\n  {json.dumps(saude, ensure_ascii=False)}")
        ensaio.conferir(
            "a API responde, com o banco ok" + (f" ({demora:.0f} s depois do up)" if demora else ""),
            saude.get("banco") == "ok",
        )
        print(f"  versão: {saude.get('versao', '?')}")
        interface = httpx.get(WEB, timeout=10)
        print(f"\n$ GET {WEB}\n  {interface.status_code}")
        ensaio.conferir("a interface responde", interface.status_code == 200)
        linhas, senha = ensaio.senha_sorteada()
        print('\n$ docker compose logs api | grep "Senha sorteada"')
        print(f"  {linhas} linha — a senha não vai para este registro")
        ensaio.conferir("o log tem uma linha \"Senha sorteada\"", linhas == 1 and bool(senha))
        admin = httpx.Client(base_url=API, timeout=30)
        entrada = admin.post("/api/sessao", json={"login": "admin", "senha": senha or ""})
        print(f"\n$ POST {API}/api/sessao  (admin, com a senha do log)\n  {entrada.status_code}")
        if not ensaio.conferir("o administrador entra com a senha do log", entrada.status_code == 201):
            return 1

        titulo("[4/7] A base de demonstração, e o banco pelo psql")
        inicio = time.monotonic()
        demo = ensaio.compose(
            "exec", "-T", "api", "python", "-m", "app.cli", "popular-demonstracao",
            como="docker compose exec api python -m app.cli popular-demonstracao",
        )
        print(f"\n  em {time.monotonic() - inicio:.0f} s")
        ensaio.conferir("o popular-demonstracao terminou sem erro", demo.returncode == 0)
        ensaio.conferir("o modelo foi treinado e entrou em uso", "Versão em uso" in demo.stdout)
        contagem = ensaio.compose(
            "exec", "-T", "postgres", "psql", "-U", "gih", "-d", "gih", "-tAc",
            "select count(*) from parceiro",
            como='docker compose exec postgres psql -U gih -d gih -tAc "select count(*) from parceiro"',
        )
        ensaio.conferir(
            "o psql do README responde, com os parceiros gerados",
            contagem.returncode == 0 and contagem.stdout.strip() not in ("", "0"),
        )

        titulo("[5/7] A documentação da API, nos endereços do README")
        for caminho in ("/api/docs", "/api/redoc", "/api/openapi.json"):
            r = httpx.get(f"{API}{caminho}", timeout=10)
            print(f"\n$ GET {API}{caminho}\n  {r.status_code}")
            ensaio.conferir(f"{caminho} responde", r.status_code == 200)

        titulo("[6/7] A verificação de ponta a ponta e a persistência, as do clone")
        passou, _ = ensaio.roteiro("verificacao.py", senha, "verificações passaram")
        ensaio.conferir("a verificação de ponta a ponta passou inteira", passou)
        passou, _ = ensaio.roteiro("persistencia.py", senha, "Resultado:")
        ensaio.conferir("a persistência passou inteira (derrubar, subir, conferir)", passou)
    finally:
        if not manter:
            titulo("[7/7] Desmontar o ensaio — só o projeto gih-rc")
            if ensaio.projeto_do_compose() == PROJETO:
                ensaio.compose("down", "-v", "--rmi", "local")
                print(f"\n  o projeto {PROJETO}, o volume e as imagens dele saíram")
            else:
                print(f"\n  o Compose não fala com {PROJETO}: nada foi desmontado", file=sys.stderr)
            shutil.rmtree(raiz, ignore_errors=True)
        else:
            print(f"\nO ensaio ficou no ar, em {pasta} (projeto {PROJETO}).")

    print("\nConferências:")
    for texto, ok in ensaio.conferencias:
        print(f"  {'ok   ' if ok else 'FALHA'} {texto}")
    passaram = sum(ok for _, ok in ensaio.conferencias)
    print(f"\nResultado: {passaram} de {len(ensaio.conferencias)} conferências passaram.")
    return 0 if passaram == len(ensaio.conferencias) else 1


def main() -> int:
    p = argparse.ArgumentParser(description="A instalação do zero, como o README a ensina (H110).")
    p.add_argument("--ref", default="main", help="a tag ou o ramo a clonar (padrão: main)")
    p.add_argument("--origem", default=ORIGEM, help="o repositório a clonar (padrão: o do README)")
    p.add_argument("--manter", action="store_true", help="não desmonta o ensaio no fim")
    p.add_argument("--sem-cache", action="store_true", help="constrói as imagens sem o cache do Docker")
    a = p.parse_args()
    if not re.fullmatch(r"[\w./-]+", a.ref):
        raise SystemExit("Referência inválida.")
    return principal(a.ref, a.origem, a.manter, a.sem_cache)


if __name__ == "__main__":
    raise SystemExit(main())
