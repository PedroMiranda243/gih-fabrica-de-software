"""Mede as telas num navegador de verdade — a largura e a acessibilidade, H76.

Cada tela, aberta pelo perfil que a usa, a **768 e a 1440 px**:

- **sem rolagem horizontal da página** (RNF21), e **sem conteúdo cortado** por
  uma caixa que esconde o que passa dela. A tabela larga que rola na própria
  caixa passa — é o desenho do projeto (`componentes.css`, `.tabela-rolagem`) —,
  e o relatório lista onde isso acontece;
- **o axe-core com o layout de verdade** (RNF22). Nos testes da interface, o
  jsdom não desenha, e o contraste fica de fora; aqui ele entra, nos dois temas;
- **a captura de cada tela**, em `docs/medicoes/telas/`.

O contraste dos tokens, par a par, também sai no relatório: os mesmos pares que
`web/src/estilos/contraste.test.js` confere.

**Contra a aplicação no ar**, com os dados que ela tiver — a massa do gerador, na
base de trabalho. O script cria três usuários de medição (gestor, administrador e
parceiro) e calcula dois planos, porque a execução e a comparação precisam
deles. No fim, desativa os usuários e apaga os planos, pela mesma limpeza da
verificação de ponta a ponta.

**O navegador é o Edge da máquina**, pelo Playwright (Apache 2.0): nada de
baixar navegador. As dependências da medição estão em
`scripts/requisitos-medicao.txt`.

Uso, com o `docker compose up` rodando:

    api/.venv/Scripts/python -m pip install -r scripts/requisitos-medicao.txt
    GIH_ADMIN_SENHA=... api/.venv/Scripts/python scripts/medir_telas.py
"""
from __future__ import annotations

import argparse
import os
import platform
import re
import secrets
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import httpx

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "api"))

from e2e.limpeza import desativar_usuarios, limpar_execucao  # noqa: E402

LARGURAS = {768: 1024, 1440: 900}
AXE = RAIZ / "web" / "node_modules" / "axe-core" / "axe.min.js"
TOKENS = RAIZ / "web" / "src" / "estilos" / "tokens.css"
SENHA = f"medicao-{secrets.token_urlsafe(12)}"

# Os pares de `web/src/estilos/contraste.test.js`: a tinta e os fundos dela.
PARES_DE_TEXTO = {
    "--ink": ["--ground", "--surface", "--surface-2", "--acao-fraca"],
    "--ink-2": ["--ground", "--surface", "--surface-2", "--acao-fraca"],
    "--acao-ink": ["--ground", "--surface", "--surface-2", "--acao-fraca"],
    "--acao-sobre": ["--acao"],
}
PARES_DE_CONTORNO = {
    "--borda-controle": ["--ground", "--surface", "--surface-2"],
    "--acao-ink": ["--ground", "--surface", "--surface-2"],
}


@dataclass
class Tela:
    nome: str
    rota: str
    perfil: str | None  # None: sem sessão
    arquivo: str


@dataclass
class Medida:
    tela: Tela
    largura: int
    rola: bool  # a página rola na horizontal
    passam: list[str]  # o que passa da borda fora de caixa com rolagem própria
    rolam: list[str]  # as caixas que rolam por conta própria: a tabela, o menu
    captura: str

    @property
    def situacao(self) -> str:
        if self.rola:
            return "rola"
        return "corta" if self.passam else "ok"


@dataclass
class Auditoria:
    tela: Tela
    tema: str
    violacoes: list[str] = field(default_factory=list)


# ------------------------------------------------------------------ contraste
def _bloco(texto: str, seletor: str) -> dict[str, str]:
    inicio = texto.index("{", texto.index(seletor))
    corpo = texto[inicio + 1 : texto.index("}", inicio)]
    return dict(re.findall(r"(--[a-z0-9-]+)\s*:\s*([^;]+);", corpo))


def _luminancia(cor: str) -> float:
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", cor.strip()):
        raise ValueError(f"cor que o script não sabe medir: {cor}")

    def canal(v: int) -> float:
        c = v / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (canal(int(cor.strip()[i : i + 2], 16)) for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def razao(a: str, b: str) -> float:
    claro, escuro = sorted((_luminancia(a), _luminancia(b)), reverse=True)
    return (claro + 0.05) / (escuro + 0.05)


def contraste() -> list[tuple[str, str, float, float, float]]:
    """(frente, fundo, mínimo, claro, escuro), de todos os pares."""
    assert abs(razao("#000000", "#ffffff") - 21) < 1e-9, "o instrumento não dá 21:1"
    texto = TOKENS.read_text(encoding="utf-8")
    claro = _bloco(texto, ":root {")
    escuro = {**claro, **_bloco(texto, ':root[data-tema="escuro"]')}
    linhas = []
    for pares, minimo in ((PARES_DE_TEXTO, 4.5), (PARES_DE_CONTORNO, 3.0)):
        for frente, fundos in pares.items():
            for fundo in fundos:
                linhas.append(
                    (
                        frente,
                        fundo,
                        minimo,
                        razao(claro[frente], claro[fundo]),
                        razao(escuro[frente], escuro[fundo]),
                    )
                )
    return linhas


# ------------------------------------------------------------ a preparação
def _cliente(url: str) -> httpx.Client:
    return httpx.Client(base_url=url, timeout=60)


def _entrar(url: str, login: str, senha: str) -> httpx.Client:
    c = _cliente(url)
    r = c.post("/api/sessao", json={"login": login, "senha": senha})
    r.raise_for_status()
    return c


def preparar(url: str, admin: httpx.Client, marca: str) -> tuple[dict[str, httpx.Client], dict]:
    """Os usuários de medição, com sessão aberta, e os ids das telas que precisam de um."""
    gestor_login = f"{marca}.gestor"
    admin.post(
        "/api/usuarios",
        json={"login": gestor_login, "nome": "Medição Gestor", "senha": SENHA, "perfil": "GESTOR"},
    ).raise_for_status()
    gestor = _entrar(url, gestor_login, SENHA)

    parceiros = gestor.get(
        "/api/parceiros", params={"ordenar_por": "faturamento", "descendente": "true", "tamanho": 1}
    ).json()["itens"]
    if not parceiros:
        raise SystemExit("A base não tem parceiros: importe dados antes de medir as telas.")
    parceiro_id = parceiros[0]["id"]

    admin_login = f"{marca}.admin"
    admin.post(
        "/api/usuarios",
        json={"login": admin_login, "nome": "Medição Administrador", "senha": SENHA,
              "perfil": "ADMINISTRADOR"},
    ).raise_for_status()
    parceiro_login = f"{marca}.parceiro"
    admin.post(
        "/api/usuarios",
        json={"login": parceiro_login, "nome": "Medição Parceiro", "senha": SENHA,
              "perfil": "PARCEIRO", "parceiro_id": parceiro_id},
    ).raise_for_status()
    sessoes = {
        "GESTOR": gestor,
        "ADMINISTRADOR": _entrar(url, admin_login, SENHA),
        "PARCEIRO": _entrar(url, parceiro_login, SENHA),
    }
    usuario_id = next(
        u["id"] for u in admin.get("/api/usuarios").json() if u["login"] == gestor_login
    )

    execucoes = []
    for orcamento in ("5000.00", "8000.00"):
        pedido = gestor.post(
            "/api/otimizacoes",
            json={
                "orcamento": orcamento,
                "maximo_acoes": 30,
                "aplicacao_inicio": "2026-10-05",
                "aplicacao_fim": "2026-10-11",
            },
        )
        if pedido.status_code != 202:
            print(f"  plano não calculado ({pedido.status_code}): sem execução e sem comparação")
            break
        execucao_id = pedido.json()["id"]
        limite = time.monotonic() + 300
        while gestor.get(f"/api/otimizacoes/{execucao_id}").json()["situacao"] == "EM_ANDAMENTO":
            if time.monotonic() > limite:
                raise SystemExit("O plano não terminou em 5 minutos.")
            time.sleep(1)
        execucoes.append(execucao_id)
    return sessoes, {"parceiro": parceiro_id, "usuario": usuario_id, "execucoes": execucoes}


def telas(ids: dict) -> list[Tela]:
    lista = [
        Tela("Entrar", "/entrar", None, "entrar"),
        Tela("Painel", "/", "GESTOR", "painel"),
        Tela("Importação", "/importacao", "GESTOR", "importacao"),
        Tela("Parceiros", "/parceiros", "GESTOR", "parceiros"),
        Tela("Novo parceiro", "/parceiros/novo", "GESTOR", "parceiro-novo"),
        Tela("Cadastro do parceiro", f"/parceiros/{ids['parceiro']}", "GESTOR", "parceiro"),
        Tela("Assistente", "/assistente", "GESTOR", "assistente"),
        Tela("Campanha", "/campanha", "GESTOR", "campanha"),
        Tela("Execuções", "/execucoes", "GESTOR", "execucoes"),
    ]
    if ids["execucoes"]:
        lista.append(Tela("Execução", f"/execucoes/{ids['execucoes'][0]}", "GESTOR", "execucao"))
    if len(ids["execucoes"]) == 2:
        a, b = ids["execucoes"]
        lista.append(Tela("Comparação", f"/execucoes/comparar?a={a}&b={b}", "GESTOR", "comparacao"))
    lista += [
        Tela("Mensagens", "/mensagens", "GESTOR", "mensagens"),
        Tela("Aprovação", "/aprovacao", "GESTOR", "aprovacao"),
        Tela("Benchmark", "/benchmark", "GESTOR", "benchmark"),
        Tela("Modelo", "/modelo", "GESTOR", "modelo"),
        Tela("Usuários", "/usuarios", "ADMINISTRADOR", "usuarios"),
        Tela("Novo usuário", "/usuarios/novo", "ADMINISTRADOR", "usuario-novo"),
        Tela("Conta do usuário", f"/usuarios/{ids['usuario']}", "ADMINISTRADOR", "usuario"),
        Tela("Auditoria", "/auditoria", "ADMINISTRADOR", "auditoria"),
        Tela("Limiares", "/configuracao", "ADMINISTRADOR", "configuracao"),
        Tela("Meu desempenho", "/meu-desempenho", "PARCEIRO", "meu-desempenho"),
    ]
    return lista


# ------------------------------------------------------------ o navegador
# O que passa da borda direita da página fora de caixa com rolagem própria. Se a
# página não rola e ainda assim há algo aqui, uma caixa com `overflow: hidden`
# está cortando conteúdo — que a pessoa não tem como ver. O texto só para leitor
# de tela (`.so-leitor`) fica de fora: ele é recortado de propósito.
NOME = """(e) => e.tagName.toLowerCase() + (e.id ? "#" + e.id : "") +
  (e.classList.length ? "." + [...e.classList].join(".") : "")"""
PASSAM_DA_BORDA = f"""() => {{
  const nome = {NOME};
  const largura = document.documentElement.clientWidth;
  const rolavel = (e) => {{
    for (let p = e.parentElement; p; p = p.parentElement) {{
      const s = getComputedStyle(p).overflowX;
      if (s === "auto" || s === "scroll") return true;
    }}
    return false;
  }};
  return [...document.querySelectorAll("body *")]
    .filter((e) => !e.closest(".so-leitor"))
    .filter((e) => e.getBoundingClientRect().right > largura + 1 && !rolavel(e))
    .slice(0, 5)
    .map(nome);
}}"""
# As caixas que rolam na horizontal por conta própria, e estão rolando.
ROLAM = f"""() => {{
  const nome = {NOME};
  return [...document.querySelectorAll("body *")]
    .filter((e) => ["auto", "scroll"].includes(getComputedStyle(e).overflowX))
    .filter((e) => e.scrollWidth > e.clientWidth + 1)
    .map(nome);
}}"""


def _abrir(pagina, url: str) -> None:
    pagina.goto(url, wait_until="networkidle")
    # A tela termina de carregar quando sai o "Carregando"; o gráfico, com ela.
    pagina.wait_for_function(
        "() => !document.querySelector('[aria-busy=\"true\"]')", timeout=30000
    )
    pagina.wait_for_timeout(400)


def medir(url_web: str, sessoes: dict[str, httpx.Client], lista: list[Tela], destino: Path):
    from playwright.sync_api import sync_playwright

    medidas: list[Medida] = []
    auditorias: list[Auditoria] = []
    destino.mkdir(parents=True, exist_ok=True)
    host = httpx.URL(url_web).host
    with sync_playwright() as p:
        navegador = p.chromium.launch(channel="msedge", headless=True)
        try:
            for tela in lista:
                for tema in ("light", "dark"):
                    contexto = navegador.new_context(
                        viewport={"width": 1440, "height": 900}, color_scheme=tema, locale="pt-BR"
                    )
                    if tela.perfil:
                        contexto.add_cookies(
                            [
                                {"name": nome, "value": valor, "domain": host, "path": "/"}
                                for nome, valor in sessoes[tela.perfil].cookies.items()
                            ]
                        )
                    pagina = contexto.new_page()
                    _abrir(pagina, url_web + tela.rota)

                    pagina.add_script_tag(path=str(AXE))
                    resultado = pagina.evaluate(
                        "async () => (await axe.run(document, { resultTypes: ['violations'] }))"
                        ".violations.map(v => v.id + ' (' + v.impact + '): ' + "
                        "v.nodes.slice(0, 3).map(n => n.target.join(' ')).join(' | '))"
                    )
                    nome_do_tema = "claro" if tema == "light" else "escuro"
                    auditorias.append(Auditoria(tela, nome_do_tema, resultado))

                    if tema == "light":
                        for largura, altura in LARGURAS.items():
                            pagina.set_viewport_size({"width": largura, "height": altura})
                            pagina.wait_for_timeout(300)
                            rola = pagina.evaluate(
                                "() => document.documentElement.scrollWidth > "
                                "document.documentElement.clientWidth"
                            )
                            passam = pagina.evaluate(PASSAM_DA_BORDA)
                            rolam = pagina.evaluate(ROLAM)
                            arquivo = f"{tela.arquivo}-{largura}.jpg"
                            pagina.screenshot(path=str(destino / arquivo), type="jpeg", quality=70)
                            medidas.append(Medida(tela, largura, rola, passam, rolam, arquivo))
                    contexto.close()
                situacoes = {m.situacao for m in medidas if m.tela is tela}
                marca = "ok" if situacoes == {"ok"} else "/".join(sorted(situacoes - {"ok"}))
                erros = sum(len(a.violacoes) for a in auditorias if a.tela is tela)
                print(f"  {marca:4} axe {erros}  {tela.nome}")
        finally:
            navegador.close()
    return medidas, auditorias


# ------------------------------------------------------------------ relatório
def _v(x: float) -> str:
    return f"{x:.2f}".replace(".", ",")


def montar_relatorio(ambiente, pares, medidas: list[Medida], auditorias: list[Auditoria]) -> str:
    lista = list(dict.fromkeys(m.tela.nome for m in medidas))
    falham = [m for m in medidas if m.situacao != "ok"]
    com_violacao = [a for a in auditorias if a.violacoes]
    reprovados = [p for p in pares if min(p[3], p[4]) < p[2]]
    linhas = [
        "# Acessibilidade e responsividade — H76",
        "",
        "> Gerado por `scripts/medir_telas.py`. **Não edite à mão**: número escrito à mão não é "
        "evidência. Para atualizar, rode o comando abaixo de novo.",
        "",
        "Três verificações, em três lugares:",
        "",
        "- **o contraste dos tokens**, par a par, nos dois temas — também conferido a cada PR por "
        "`web/src/estilos/contraste.test.js`;",
        "- **rótulos, papéis e nomes acessíveis** — conferidos pelo axe-core no fim de cada teste "
        "da interface (`web/src/testes/preparar.js`), e aqui de novo, no navegador, com o "
        "contraste real do que está desenhado;",
        "- **a largura**: cada tela a 768 e a 1440 px, sem rolagem horizontal da página e sem "
        "conteúdo cortado (RNF21). A tabela larga rola na própria caixa, e a página fica no lugar.",
        "",
        "## Ambiente",
        "",
        "| Item | Valor |",
        "|---|---|",
        f"| Data | {ambiente['data']} |",
        f"| Navegador | Microsoft Edge {ambiente['navegador']}, sem cabeça, pelo Playwright |",
        f"| axe-core | {ambiente['axe']} |",
        "| Dados | a base de trabalho, com a massa do gerador; dois planos calculados para a "
        "medição e apagados depois |",
        f"| Máquina | {ambiente['maquina']} |",
        "",
        "## Como reproduzir",
        "",
        "```bash",
        "api/.venv/Scripts/python -m pip install -r scripts/requisitos-medicao.txt",
        "api/.venv/Scripts/python scripts/medir_telas.py",
        "```",
        "",
        "## O contraste dos tokens (RNF22)",
        "",
        f"**{len(pares) - len(reprovados)} de {len(pares)} pares passam nos dois temas.** O texto "
        "pede 4,5:1; a borda de um campo e o anel de foco, 3:1 (WCAG 1.4.11).",
        "",
        "| Frente | Fundo | Mínimo | Claro | Escuro |",
        "|---|---|--:|--:|--:|",
    ]
    for frente, fundo, minimo, claro, escuro in pares:
        linhas.append(
            f"| `{frente}` | `{fundo}` | {_v(minimo)}:1 | {_v(claro)}:1 | {_v(escuro)}:1 |"
        )
    linhas += [
        "",
        "## As telas",
        "",
        f"**{len(lista)} telas. Com a página rolando na horizontal ou conteúdo cortado: "
        f"{len(falham)} das {len(medidas)} medidas. Com violação do axe no navegador: "
        f"{len(com_violacao)} das {len(auditorias)} auditorias** (cada tela, nos dois temas).",
        "",
        "| Tela | Rota | Perfil | 768 px | 1440 px | axe, claro | axe, escuro |",
        "|---|---|---|---|---|--:|--:|",
    ]
    for nome in lista:
        doze = {m.largura: m for m in medidas if m.tela.nome == nome}
        aud = {a.tema: a for a in auditorias if a.tela.nome == nome}
        tela = doze[768].tela
        situacao = {k: m.situacao for k, m in doze.items()}
        linhas.append(
            f"| {nome} | `{tela.rota}` | {(tela.perfil or 'sem sessão').lower()} | "
            f"{situacao[768]} | {situacao[1440]} | {len(aud['claro'].violacoes)} | "
            f"{len(aud['escuro'].violacoes)} |"
        )
    if falham:
        linhas += ["", "**O que passa da borda:**", ""]
        for m in falham:
            passam = ", ".join(f"`{p}`" for p in m.passam)
            linhas.append(f"- {m.tela.nome}, {m.largura} px ({m.situacao}): {passam}")
    com_rolagem = [m for m in medidas if m.rolam]
    if com_rolagem:
        linhas += [
            "",
            "**O que rola na própria caixa** — e a página fica no lugar: a tabela larga e, a 768 "
            "px, o menu, que vira uma faixa no topo.",
            "",
            "| Tela | Largura | Caixas |",
            "|---|--:|---|",
        ]
        for m in com_rolagem:
            caixas = ", ".join(f"`{c}`" for c in dict.fromkeys(m.rolam))
            linhas.append(f"| {m.tela.nome} | {m.largura} px | {caixas} |")
    if com_violacao:
        linhas += ["", "**O que o axe acusou:**", ""]
        for a in com_violacao:
            for v in a.violacoes:
                linhas.append(f"- {a.tela.nome}, tema {a.tema}: {v}")
    linhas += ["", "## As capturas", "", "Tema claro. À esquerda, 768 px; à direita, 1440 px.", ""]
    for nome in lista:
        doze = {m.largura: m for m in medidas if m.tela.nome == nome}
        linhas += [
            f"### {nome}",
            "",
            f'<img src="telas/{doze[768].captura}" width="280" alt="{nome} a 768 px"> '
            f'<img src="telas/{doze[1440].captura}" width="480" alt="{nome} a 1440 px">',
            "",
        ]
    return "\n".join(linhas)


def main() -> None:
    p = argparse.ArgumentParser(description="Mede as telas (H76).")
    p.add_argument("--api", default=os.environ.get("GIH_URL", "http://localhost:8000"))
    p.add_argument("--web", default="http://localhost:5173")
    p.add_argument("--senha", default=os.environ.get("GIH_ADMIN_SENHA", ""))
    p.add_argument("--relatorio", default=str(RAIZ / "docs" / "medicoes" / "acessibilidade.md"))
    args = p.parse_args()
    if not args.senha:
        raise SystemExit("Informe a senha do administrador em GIH_ADMIN_SENHA.")
    if not AXE.exists():
        raise SystemExit("Falta o axe-core: rode `npm install` em web/.")

    marca = f"t{secrets.randbelow(100000):05d}"
    admin = _entrar(args.api, "admin", args.senha)
    sessoes: dict[str, httpx.Client] = {}
    try:
        print("preparando os usuários e os planos da medição")
        sessoes, ids = preparar(args.api, admin, marca)
        print("medindo as telas")
        medidas, auditorias = medir(
            args.web, sessoes, telas(ids), Path(args.relatorio).parent / "telas"
        )
    finally:
        for c in sessoes.values():
            c.delete("/api/sessao")
            c.close()
        print("limpando: " + ", ".join(desativar_usuarios(admin, marca)))
        print(limpar_execucao(marca))
        admin.delete("/api/sessao")

    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        edge = pw.chromium.launch(channel="msedge", headless=True)
        versao = edge.version
        edge.close()
    axe_versao = re.search(r"axe v([\d.]+)", AXE.read_text(encoding="utf-8")[:300])
    ambiente = {
        "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "navegador": versao,
        "axe": axe_versao.group(1) if axe_versao else "?",
        "maquina": f"{platform.system()} {platform.release()}, Python {platform.python_version()}",
    }
    destino = Path(args.relatorio)
    relatorio = montar_relatorio(ambiente, contraste(), medidas, auditorias)
    destino.write_text(relatorio, encoding="utf-8")
    print(f"\nrelatório: {destino}")


if __name__ == "__main__":
    main()
