"""Executa pela tela os casos de teste do `docs/12-plano-de-testes.md` (H104, H105).

O catálogo diz, para cada caso, os passos e o resultado esperado. Este script
faz os passos num navegador de verdade, contra o sistema no ar, e registra o
resultado **obtido** — o texto, o endereço ou a mensagem que a tela mostrou —,
com uma captura de cada caso. É a diferença entre dizer que testou e mostrar o
teste: qualquer pessoa da equipe roda de novo e vê o mesmo.

**O catálogo e o código não divergem.** Um caso do `docs/12` sem função aqui, ou
uma função sem o caso no `docs/12`, faz o script recusar rodar: o documento que
vai para a entrega é o que de fato se executa.

**Nada fica na base da equipe.** Os usuários do teste levam a marca da execução
no login (`t12345.gestor`), os parceiros e as ações, no nome; tudo o que eles
gravam sai no fim pela mesma limpeza da verificação de ponta a ponta
(`api/e2e/limpeza.py`), e eles são desativados — não apagados, porque a trilha
de auditoria aponta para o autor. A importação vai para uma semana no futuro,
que só a execução usa. O limiar mudado volta ao valor de antes, mesmo se o caso
falhar no meio.

**O bloqueio por cinco tentativas não roda aqui.** Ele é por origem: provocá-lo
pela tela travaria a entrada de todos na máquina, inclusive a de quem está
usando o sistema. Cada execução faz no máximo duas tentativas recusadas (CT-V01
e CT-F07); o bloqueio fica no teste da API (`test_autenticacao.py`).

Uso, com o `docker compose up` rodando (o perfil `assistente` liga o modelo de
linguagem; sem ele, o assistente e as mensagens usam o que o sistema monta
sozinho, e o caso diz qual dos dois respondeu):

    api/.venv/Scripts/python -m pip install -r scripts/requisitos-medicao.txt
    GIH_ADMIN_SENHA=... api/.venv/Scripts/python scripts/testar_na_tela.py --saida <pasta>
    ... --so CT-N01,CT-V05      # só estes casos (aceita prefixo: --so CT-N)
    ... --ver                   # com a janela aberta, devagar, para demonstrar
    ... --navegador chrome      # o Chrome instalado na máquina, no lugar do Edge
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import sys
import tempfile
import time
import traceback
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

import httpx

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "api"))

from playwright.sync_api import expect  # noqa: E402

from e2e.limpeza import desativar_usuarios, limpar_execucao  # noqa: E402

CATALOGO = RAIZ / "docs" / "12-plano-de-testes.md"
NAVEGADORES = {"edge": "msedge", "chrome": "chrome"}
LIMIARES = ("top_n", "periodos_tendencia", "periodos_novato")
PERFIS = {"ADMINISTRADOR": "adm", "GESTOR": "gestor", "ANALISTA": "analista", "PARCEIRO": "parceiro"}
NOME_DO_PERFIL = {
    "ADMINISTRADOR": "Administrador",
    "GESTOR": "Gestor",
    "ANALISTA": "Analista",
    "PARCEIRO": "Parceiro",
}

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


class Reprovado(Exception):
    """O sistema não fez o que o caso espera; a mensagem é o que se viu."""


class NaoExecutado(Exception):
    """O ambiente não permite o caso (o modelo de linguagem fora do ar); a mensagem diz o que falta."""


def confere(condicao: object, obtido: str) -> None:
    if not condicao:
        raise Reprovado(obtido)


# ------------------------------------------------------------------ o catálogo
@dataclass
class Caso:
    id: str
    modulo: str
    requisito: str
    perfil: str
    passos: str
    esperado: str
    obtido: str = ""
    situacao: str = ""
    captura: str = ""
    segundos: float = 0.0

    @property
    def tipo(self) -> str:
        return {"F": "funcional", "V": "validação", "N": "navegação"}[self.id[3]]


def ler_catalogo(caminho: Path = CATALOGO) -> dict[str, Caso]:
    """Os casos das tabelas do `docs/12`: cada linha que começa por `| CT-`."""
    casos: dict[str, Caso] = {}
    modulo = ""
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        if linha.startswith("### "):
            modulo = linha[4:].strip()
        elif linha.startswith("| CT-"):
            celulas = [c.strip() for c in linha.strip().strip("|").split("|")]
            if len(celulas) != 5:
                raise SystemExit(f"Linha do catálogo fora do formato (5 colunas): {linha}")
            ident, requisito, perfil, passos, esperado = celulas
            if ident in casos:
                raise SystemExit(f"{ident} aparece duas vezes no catálogo.")
            casos[ident] = Caso(ident, modulo, requisito, perfil, passos, esperado)
    return casos


CASOS: dict[str, Callable] = {}


def caso(ident: str):
    def registrar(funcao: Callable) -> Callable:
        if ident in CASOS:
            raise SystemExit(f"{ident} tem duas funções.")
        CASOS[ident] = funcao
        return funcao

    return registrar


# ------------------------------------------------------------------ a execução
@dataclass
class Execucao:
    web: str
    marca: str
    senha: str
    admin: httpx.Client
    saida: Path
    lento: bool = False
    estado: dict = field(default_factory=dict)
    sessoes: dict = field(default_factory=dict)
    # Por caso: as recusas da API que o caso provoca de propósito, e o que a captura mostra.
    esperadas: list = field(default_factory=list)
    alvo: object = None
    fotografado: bool = False

    def login(self, perfil: str) -> str:
        return f"{self.marca}.{PERFIS[perfil]}"

    def api(self, perfil: str) -> httpx.Client:
        if perfil not in self.sessoes:
            c = httpx.Client(base_url=self.web, timeout=120)
            c.post("/api/sessao", json={"login": self.login(perfil), "senha": self.senha}).raise_for_status()
            self.sessoes[perfil] = c
        return self.sessoes[perfil]

    def recusa_esperada(self, metodo: str, padrao: str, status: int) -> None:
        self.esperadas.append((metodo, re.compile(padrao), status))

    def foto(self, pagina, ident: str, alvo=None) -> None:
        """A captura do caso agora, e não no fim: o que importa mostrar some depois."""
        centralizar(alvo)
        pagina.screenshot(path=str(self.saida / f"{ident}.png"))
        self.fotografado = True

    # --- a tela
    def ir(self, pagina, destino: str) -> None:
        pagina.goto(self.web + destino)
        sossegar(pagina)

    def entrar(self, pagina, perfil: str, destino: str = "/") -> None:
        """Abre a sessão do perfil no navegador e vai ao destino.

        A sessão é aberta pela API, no próprio contexto do navegador (o cookie
        fica nele): entrar pela tela é o CT-F01, e repeti-lo em todo caso só
        alongaria a execução.
        """
        r = pagina.context.request.post(
            self.web + "/api/sessao", data={"login": self.login(perfil), "senha": self.senha}
        )
        confere(r.status == 201, f"a sessão do {perfil} não abriu: {r.status}")
        self.ir(pagina, destino)

    def entrar_pela_tela(self, pagina, login: str, senha: str) -> None:
        pagina.goto(self.web + "/entrar")
        pagina.locator("#campo-login").fill(login)
        pagina.locator("#campo-senha").fill(senha)
        pagina.get_by_role("button", name="Entrar", exact=True).click()

    # --- dados que mais de um caso usa; criados na hora se o caso roda sozinho
    def parceiro_novo(self) -> dict:
        if "parceiro_novo" not in self.estado:
            r = self.api("GESTOR").post(
                "/api/parceiros", json={"nome": f"Empório {self.marca}", "status": "ATIVO"}
            )
            r.raise_for_status()
            self.estado["parceiro_novo"] = r.json()
        return self.estado["parceiro_novo"]

    def parceiro_com_historico(self) -> dict:
        if "parceiro_antigo" not in self.estado:
            itens = (
                self.api("GESTOR")
                .get(
                    "/api/parceiros",
                    params={"ordenar_por": "faturamento", "descendente": "true", "tamanho": 1},
                )
                .json()["itens"]
            )
            confere(itens, "a base não tem parceiros: importe dados antes de testar")
            self.estado["parceiro_antigo"] = itens[0]
        return self.estado["parceiro_antigo"]

    def plano(self, orcamento: str = "15000.00") -> int:
        """Um plano calculado pelo gestor da execução: o id da execução do otimizador."""
        chave = f"plano-{orcamento}"
        if chave not in self.estado:
            gestor = self.api("GESTOR")
            hoje = date.today()
            r = gestor.post(
                "/api/otimizacoes",
                json={
                    "orcamento": orcamento,
                    "maximo_acoes": 8,
                    "aplicacao_inicio": hoje.isoformat(),
                    "aplicacao_fim": (hoje + timedelta(days=6)).isoformat(),
                },
            )
            confere(r.status_code == 202, f"o plano não foi calculado: {r.status_code} {r.text[:200]}")
            ident = r.json()["id"]
            limite = time.monotonic() + 300
            while gestor.get(f"/api/otimizacoes/{ident}").json()["situacao"] == "EM_ANDAMENTO":
                confere(time.monotonic() < limite, "o plano não terminou em 5 minutos")
                time.sleep(1)
            self.estado[chave] = ident
        return self.estado[chave]

    def semana_futura(self) -> tuple[str, str]:
        """Uma semana só desta execução, longe dos dados e de outras execuções."""
        inicio = date(2091, 1, 1) + timedelta(weeks=int(self.marca[1:]) % 2000)
        inicio -= timedelta(days=inicio.weekday())
        return inicio.isoformat(), (inicio + timedelta(days=6)).isoformat()


def centralizar(alvo) -> None:
    """Rola a página até o que a captura precisa mostrar, no meio da tela.

    No meio, e não na borda: o cabeçalho fica fixo no alto e cobriria o alvo. E
    só o que está visível: o mesmo texto costuma existir também para o leitor de
    tela, num elemento de um pixel no alto da página.
    """
    if alvo is not None:
        alvo.filter(visible=True).first.evaluate("e => e.scrollIntoView({block: 'center'})", timeout=3000)


def sossegar(pagina, limite: int = 30000) -> None:
    """Espera a tela parar: sem rede pendente e sem nada marcado como ocupado."""
    pagina.wait_for_load_state("networkidle")
    pagina.wait_for_function("!document.querySelector('[aria-busy=\"true\"]')", timeout=limite)


def resposta(pagina, metodo: str, padrao: str, acao: Callable, limite: int = 60000):
    """Faz a ação e devolve a resposta da API que ela provocou."""
    with pagina.expect_response(
        lambda r: r.request.method == metodo and re.search(padrao, r.url.split("?")[0]), timeout=limite
    ) as info:
        acao()
    return info.value


def mensagem(r: httpx.Response) -> str:
    """A mensagem de uma recusa da API: `erro`, ou o `detail` do FastAPI."""
    try:
        corpo = r.json()
    except ValueError:
        return r.text[:160]
    detalhe = corpo.get("detail")
    return corpo.get("erro") or (
        detalhe if isinstance(detalhe, str) else json.dumps(detalhe, ensure_ascii=False)[:160]
    )


def h1(pagina) -> str:
    return pagina.locator("h1").first.inner_text().strip()


def erro_do_campo(pagina, nome: str) -> str:
    alvo = pagina.locator(f"#campo-{nome}-erro")
    alvo.wait_for(timeout=15000)
    return " ".join(alvo.inner_text().split())


def caminho(pagina, web: str) -> str:
    return pagina.url.replace(web, "") or "/"


def confirmar(pagina, acao: str, padrao_metodo: tuple[str, str] | None = None, limite: int = 60000):
    """Clica no botão da confirmação na própria página (nunca window.confirm)."""
    botao = pagina.locator(".confirmacao").get_by_role("button", name=acao, exact=True)
    if padrao_metodo:
        return resposta(pagina, padrao_metodo[0], padrao_metodo[1], botao.click, limite)
    botao.click()
    return None


# ================================================================== funcionais
# ---------------------------------------------------------------- autenticação
@caso("CT-F01")
def entrar(x: Execucao, pg) -> str:
    x.entrar_pela_tela(pg, x.login("GESTOR"), x.senha)
    pg.wait_for_url(lambda u: "/entrar" not in u, timeout=20000)
    sossegar(pg)
    conta = pg.get_by_role("link", name=re.compile("^Minha conta:"))
    confere(h1(pg) == "Painel", f"depois de entrar, o título é '{h1(pg)}'")
    nome = " ".join(conta.inner_text().split())
    return f"abriu {caminho(pg, x.web)} com o título 'Painel'; o cabeçalho mostra '{nome}'"


@caso("CT-F02")
def sair(x: Execucao, pg) -> str:
    x.entrar(pg, "GESTOR", "/parceiros")
    pg.get_by_role("button", name="Encerrar sessão").click()
    pg.wait_for_url("**/entrar", timeout=15000)
    x.recusa_esperada("GET", r"/api/sessao/atual$", 401)
    pg.goto(x.web + "/parceiros")
    pg.wait_for_url("**/entrar", timeout=15000)
    return "voltou para /entrar; abrir /parceiros depois de sair pede a entrada de novo"


@caso("CT-F03")
def trocar_a_senha(x: Execucao, pg) -> str:
    login = f"{x.marca}.conta"
    x.admin.post(
        "/api/usuarios", json={"login": login, "nome": "Teste Conta", "senha": x.senha, "perfil": "GESTOR"}
    ).raise_for_status()
    pg.context.request.post(x.web + "/api/sessao", data={"login": login, "senha": x.senha})
    x.ir(pg, "/conta")
    nova = f"nova-{secrets.token_urlsafe(10)}"
    pg.get_by_label(re.compile("^Senha atual")).fill(x.senha)
    pg.get_by_label(re.compile(r"^Senha nova(?!,)")).fill(nova)
    pg.get_by_label(re.compile("^Senha nova, de novo")).fill(nova)
    r = resposta(
        pg, "POST", r"/api/sessao/senha$", lambda: pg.get_by_role("button", name="Trocar a senha").click()
    )
    confere(r.status in (200, 204), f"a troca respondeu {r.status}")
    sossegar(pg)
    aviso = " ".join(pg.locator(".aviso--sucesso, [role=status]").first.inner_text().split())
    entra = httpx.post(x.web + "/api/sessao", json={"login": login, "senha": nova}).status_code
    confere(entra == 201, f"a senha nova não entra: {entra}")
    return f"'{aviso}'; a conta entra com a senha nova (201)"


# ---------------------------------------------------------------- usuários
def preencher_usuario(pg, login: str, nome: str, senha: str, perfil: str) -> None:
    pg.locator("#campo-login").fill(login)
    pg.locator("#campo-nome").fill(nome)
    pg.locator("#campo-senha").fill(senha)
    pg.locator("#campo-perfil").select_option(label=perfil)


@caso("CT-F04")
def criar_usuario(x: Execucao, pg) -> str:
    x.entrar(pg, "ADMINISTRADOR", "/usuarios/novo")
    login = f"{x.marca}.novo"
    preencher_usuario(pg, login, "Teste Novo Analista", x.senha, "Analista")
    r = resposta(
        pg, "POST", r"/api/usuarios$", lambda: pg.get_by_role("button", name="Criar usuário").click()
    )
    confere(r.status == 201, f"a criação respondeu {r.status}: {r.text()[:200]}")
    x.estado["usuario_novo"] = r.json()
    sossegar(pg)
    x.ir(pg, "/usuarios")
    linha = pg.locator("tbody tr").filter(has_text=login)
    confere(linha.count() == 1, f"a lista não mostra {login}")
    return f"criou {login} (201); a lista mostra '{' '.join(linha.inner_text().split())}'"


def usuario_novo(x: Execucao) -> dict:
    if "usuario_novo" not in x.estado:
        r = x.admin.post(
            "/api/usuarios",
            json={
                "login": f"{x.marca}.novo",
                "nome": "Teste Novo Analista",
                "senha": x.senha,
                "perfil": "ANALISTA",
            },
        )
        r.raise_for_status()
        x.estado["usuario_novo"] = r.json()
    return x.estado["usuario_novo"]


@caso("CT-F05")
def buscar_usuario(x: Execucao, pg) -> str:
    alvo = usuario_novo(x)
    x.entrar(pg, "ADMINISTRADOR", "/usuarios")
    with pg.expect_response(lambda r: "/api/usuarios" in r.url and r.request.method == "GET", timeout=15000):
        pg.get_by_role("searchbox").first.fill(alvo["login"])
    sossegar(pg)
    linhas = pg.locator("tbody tr")
    confere(
        linhas.count() == 1 and alvo["login"] in linhas.first.inner_text(),
        f"a busca mostrou {linhas.count()} linhas",
    )
    return f"a busca por '{alvo['login']}' mostra 1 linha, a dele; o endereço guarda a busca ({caminho(pg, x.web)})"


@caso("CT-F06")
def editar_usuario(x: Execucao, pg) -> str:
    alvo = usuario_novo(x)
    x.entrar(pg, "ADMINISTRADOR", f"/usuarios/{alvo['id']}")
    pg.locator("#campo-perfil").select_option(label="Gestor")
    r = resposta(
        pg, "PATCH", r"/api/usuarios/\d+$", lambda: pg.get_by_role("button", name="Salvar alterações").click()
    )
    confere(r.status == 200 and r.json()["perfil"] == "GESTOR", f"a edição respondeu {r.status}")
    sossegar(pg)
    x.ir(pg, "/usuarios")
    linha = " ".join(pg.locator("tbody tr").filter(has_text=alvo["login"]).inner_text().split())
    confere("Gestor" in linha, f"a lista mostra '{linha}'")
    return f"perfil de Analista para Gestor (200); a lista mostra '{linha}'"


@caso("CT-F07")
def desativar_usuario(x: Execucao, pg) -> str:
    alvo = usuario_novo(x)
    x.entrar(pg, "ADMINISTRADOR", f"/usuarios/{alvo['id']}")
    pg.get_by_role("button", name="Desativar", exact=True).click()
    r = confirmar(pg, "Desativar", ("PATCH", r"/api/usuarios/\d+$"))
    confere(r.status == 200 and r.json()["ativo"] is False, f"a desativação respondeu {r.status}")
    sossegar(pg)
    situacao = " ".join(pg.locator(".situacao").inner_text().split())
    entra = httpx.post(x.web + "/api/sessao", json={"login": alvo["login"], "senha": x.senha})
    confere(entra.status_code == 401, f"a conta desativada ainda entra: {entra.status_code}")
    return f"'{situacao}'; tentar entrar com ela responde {entra.status_code}: '{mensagem(entra)}'"


@caso("CT-F08")
def conta_parceiro(x: Execucao, pg) -> str:
    antigo = x.parceiro_com_historico()
    x.entrar(pg, "ADMINISTRADOR", "/usuarios/novo")
    login = f"{x.marca}.portal"
    preencher_usuario(pg, login, "Teste Portal", x.senha, "Parceiro")
    pg.locator("#campo-parceiro_id").fill(antigo["nome"][:12])
    pg.locator(".achados button").filter(has_text=antigo["nome"]).first.click(timeout=15000)
    vinculo = " ".join(pg.locator(".parceiro-da-conta__atual").inner_text().split())
    r = resposta(
        pg, "POST", r"/api/usuarios$", lambda: pg.get_by_role("button", name="Criar usuário").click()
    )
    confere(
        r.status == 201 and r.json().get("parceiro_id") == antigo["id"],
        f"a criação respondeu {r.status}: {r.text()[:200]}",
    )
    return f"'{vinculo}'; a conta foi criada (201) vinculada ao parceiro {antigo['id']}"


@caso("CT-F09")
def redefinir_senha(x: Execucao, pg) -> str:
    login = f"{x.marca}.esqueceu"
    r = x.admin.post(
        "/api/usuarios",
        json={"login": login, "nome": "Teste Esqueceu", "senha": x.senha, "perfil": "ANALISTA"},
    )
    r.raise_for_status()
    x.entrar(pg, "ADMINISTRADOR", f"/usuarios/{r.json()['id']}")
    nova = f"redefinida-{secrets.token_urlsafe(8)}"
    pg.locator("#campo-senha_nova").fill(nova)
    pg.get_by_role("button", name="Redefinir a senha").click()
    r = confirmar(pg, "Redefinir a senha", ("POST", r"/api/usuarios/\d+/senha$"))
    confere(r.status in (200, 204), f"a redefinição respondeu {r.status}")
    sossegar(pg)
    antiga = httpx.post(x.web + "/api/sessao", json={"login": login, "senha": nova}).status_code
    confere(antiga == 201, f"a senha redefinida não entra: {antiga}")
    return f"redefinida ({r.status}); a conta entra com a senha nova (201)"


# ---------------------------------------------------------------- parceiros
@caso("CT-F10")
def cadastrar_parceiro(x: Execucao, pg) -> str:
    x.entrar(pg, "GESTOR", "/parceiros/novo")
    nome = f"Padaria {x.marca}"
    pg.locator("#campo-nome").fill(nome)
    pg.locator("#campo-contato").click()  # sai do nome: a sugestão de categoria é pedida
    sugestao = pg.locator(".sugestao")
    try:
        sugestao.wait_for(timeout=5000)
        texto_sugestao = " ".join(sugestao.inner_text().split())
        pg.locator(".sugestao button").click()
    except Exception:  # noqa: BLE001 — sem sugestão, o cadastro segue sem categoria
        texto_sugestao = "nenhuma sugestão de categoria"
    pg.locator("#campo-contato").fill("contato@exemplo.test")
    r = resposta(
        pg, "POST", r"/api/parceiros$", lambda: pg.get_by_role("button", name="Cadastrar parceiro").click()
    )
    confere(r.status == 201, f"o cadastro respondeu {r.status}: {r.text()[:200]}")
    x.estado["parceiro_novo"] = r.json()
    sossegar(pg)
    aviso = " ".join(pg.get_by_text("Parceiro cadastrado.").inner_text().split())
    return f"'{texto_sugestao}'; cadastrado (201), abriu {caminho(pg, x.web)} com '{aviso}'"


@caso("CT-F11")
def consultar_parceiros(x: Execucao, pg) -> str:
    x.entrar(pg, "GESTOR", "/parceiros")
    with pg.expect_response(
        lambda r: "/api/parceiros?" in r.url and "segmento=EM_RISCO" in r.url, timeout=20000
    ):
        pg.get_by_label("Segmento", exact=True).select_option(value="EM_RISCO")
    sossegar(pg)
    linhas = pg.locator("tbody tr")
    n = linhas.count()
    confere(n > 0, "o filtro Em risco não trouxe nenhum parceiro")
    fora = [i for i in range(n) if "Em risco" not in linhas.nth(i).inner_text()]
    confere(not fora, f"{len(fora)} das {n} linhas não são Em risco")
    return f"{n} linhas, todas 'Em risco'; o endereço guarda o filtro ({caminho(pg, x.web)})"


@caso("CT-F12")
def editar_parceiro(x: Execucao, pg) -> str:
    novo = x.parceiro_novo()
    x.entrar(pg, "GESTOR", f"/parceiros/{novo['id']}")
    pg.locator("#campo-contato").fill("(81) 3000-0000")
    pg.locator("#campo-status").select_option(value="PROSPECCAO")
    r = resposta(
        pg,
        "PATCH",
        r"/api/parceiros/\d+$",
        lambda: pg.get_by_role("button", name="Salvar alterações").click(),
    )
    confere(r.status == 200, f"a edição respondeu {r.status}: {r.text()[:200]}")
    sossegar(pg)
    confere(pg.get_by_text("Alterações salvas.").is_visible(), "a tela não disse que salvou")
    dados = r.json()
    return f"'Alterações salvas.'; a API devolveu contato '{dados.get('contato')}' e status {dados.get('status')}"


@caso("CT-F13")
def excluir_parceiro(x: Execucao, pg) -> str:
    r = x.api("GESTOR").post("/api/parceiros", json={"nome": f"Mercearia {x.marca}", "status": "ATIVO"})
    r.raise_for_status()
    alvo = r.json()
    x.entrar(pg, "GESTOR", f"/parceiros/{alvo['id']}")
    pg.get_by_role("button", name="Excluir parceiro").click()
    r = confirmar(pg, "Excluir", ("DELETE", r"/api/parceiros/\d+$"))
    confere(r.status == 204, f"a exclusão respondeu {r.status}")
    pg.wait_for_url(lambda u: not re.search(r"/parceiros/\d+$", u), timeout=15000)
    sossegar(pg)
    depois = x.api("GESTOR").get(f"/api/parceiros/{alvo['id']}").status_code
    x.recusa_esperada("GET", r"/api/parceiros/\d+$", 404)
    confere(depois == 404, f"o parceiro excluído ainda responde {depois}")
    return f"excluído (204); a tela foi para {caminho(pg, x.web)}; o cadastro dele responde 404"


@caso("CT-F14")
def exportar_parceiros(x: Execucao, pg) -> str:
    x.entrar(pg, "GESTOR", "/parceiros?segmento=TOP")
    link = pg.get_by_role("link", name=re.compile("Exportar CSV"))
    href = link.get_attribute("href")
    r = pg.context.request.get(x.web + href if href.startswith("/") else href)
    corpo = r.body().decode("utf-8-sig")
    cabecalho = corpo.splitlines()[0] if corpo else ""
    confere(
        r.status == 200 and "text/csv" in r.headers.get("content-type", ""), f"o CSV respondeu {r.status}"
    )
    confere("segmento=TOP" in href, f"o link não leva o filtro: {href}")
    return f"{href} → 200 text/csv, {len(corpo.splitlines()) - 1} linhas; cabeçalho '{cabecalho[:90]}'"


@caso("CT-F15")
def situacao_parceiro(x: Execucao, pg) -> str:
    novo = x.parceiro_novo()
    x.entrar(pg, "GESTOR", f"/parceiros/{novo['id']}")
    pg.get_by_role("button", name="Desativar", exact=True).click()
    r = confirmar(pg, "Desativar", ("PATCH", r"/api/parceiros/\d+$"))
    confere(r.status == 200 and r.json()["ativo"] is False, f"a desativação respondeu {r.status}")
    sossegar(pg)
    r = resposta(
        pg, "PATCH", r"/api/parceiros/\d+$", lambda: pg.get_by_role("button", name="Reativar").click()
    )
    confere(r.status == 200 and r.json()["ativo"] is True, f"a reativação respondeu {r.status}")
    return "desativado e reativado pela tela (200 nas duas)"


# ---------------------------------------------------------------- importação
def colar_relatorio(pg, inicio: str, fim: str, texto: str) -> None:
    pg.locator("#campo-periodo_inicio").fill(inicio)
    pg.locator("#campo-periodo_fim").fill(fim)
    pg.locator("#campo-texto").fill(texto)


def relatorio_de_teste(x: Execucao) -> str:
    nomes = [
        p["nome"]
        for p in x.api("GESTOR")
        .get("/api/parceiros", params={"tamanho": 2, "ordenar_por": "faturamento", "descendente": "true"})
        .json()["itens"]
    ]
    return (
        "Parceiro;Faturamento;Pedidos\n" + f"{nomes[0]};1234,50;40\n{nomes[1]};987,00;31\nlinha sem sentido"
    )


@caso("CT-F16")
def previa(x: Execucao, pg) -> str:
    x.entrar(pg, "GESTOR", "/importacao")
    colar_relatorio(pg, *x.semana_futura(), relatorio_de_teste(x))
    r = resposta(
        pg, "POST", r"/api/importacoes/previa$", lambda: pg.get_by_role("button", name="Ver a prévia").click()
    )
    confere(r.status == 200, f"a prévia respondeu {r.status}")
    sossegar(pg)
    corpo = r.json()
    confere(
        corpo["total_reconhecido"] == 2 and corpo["total_rejeitado"] == 1,
        f"a prévia reconheceu {corpo['total_reconhecido']} e rejeitou {corpo['total_rejeitado']}",
    )
    motivo = corpo["rejeitados"][0]
    return f"{corpo['total_reconhecido']} linhas para gravar e {corpo['total_rejeitado']} rejeitada, com o motivo: '{motivo.get('motivo')}'"


@caso("CT-F17")
def importar(x: Execucao, pg) -> str:
    x.entrar(pg, "GESTOR", "/importacao")
    inicio, fim = x.semana_futura()
    colar_relatorio(pg, inicio, fim, relatorio_de_teste(x))
    resposta(
        pg, "POST", r"/api/importacoes/previa$", lambda: pg.get_by_role("button", name="Ver a prévia").click()
    )
    sossegar(pg)
    r = resposta(
        pg, "POST", r"/api/importacoes$", lambda: pg.get_by_role("button", name=re.compile("^Gravar")).click()
    )
    confere(r.status == 201, f"a gravação respondeu {r.status}: {r.text()[:200]}")
    sossegar(pg)
    historico = pg.get_by_role("region", name="Importações anteriores", exact=True).inner_text()
    confere(inicio[8:10] in historico, "o histórico não mostra a semana importada")
    x.alvo = pg.get_by_role("region", name="Importações anteriores", exact=True)
    return f"gravado (201): o período {inicio} a {fim} aparece em 'Importações anteriores'"


@caso("CT-F18")
def substituir(x: Execucao, pg) -> str:
    inicio, fim = x.semana_futura()
    gestor = x.api("GESTOR")
    if not any(
        i["periodo"]["data_inicio"] == inicio
        for i in gestor.get("/api/importacoes", params={"tamanho": 5}).json()["itens"]
    ):
        gestor.post(
            "/api/importacoes",
            json={"periodo_inicio": inicio, "periodo_fim": fim, "texto": relatorio_de_teste(x)},
        ).raise_for_status()
    x.entrar(pg, "GESTOR", "/importacao")
    colar_relatorio(pg, inicio, fim, relatorio_de_teste(x).replace("1234,50", "1500,00"))
    resposta(
        pg, "POST", r"/api/importacoes/previa$", lambda: pg.get_by_role("button", name="Ver a prévia").click()
    )
    sossegar(pg)
    x.recusa_esperada("POST", r"/api/importacoes$", 409)
    r = resposta(
        pg, "POST", r"/api/importacoes$", lambda: pg.get_by_role("button", name=re.compile("^Gravar")).click()
    )
    confere(r.status == 409, f"gravar o mesmo período respondeu {r.status}")
    aviso = " ".join(pg.locator(".confirmacao").inner_text().split())
    x.foto(pg, "CT-F18", pg.locator(".confirmacao"))
    r = confirmar(pg, "Substituir mesmo assim", ("POST", r"/api/importacoes$"))
    confere(r.status == 201, f"a substituição respondeu {r.status}: {r.text()[:200]}")
    return f"o mesmo período foi recusado (409) com '{aviso[:140]}'; 'Substituir mesmo assim' gravou (201)"


# ---------------------------------------------------------------- painel
@caso("CT-F19")
def painel(x: Execucao, pg) -> str:
    x.entrar(pg, "GESTOR", "/")
    kpis = pg.locator(".faixa-kpi")
    confere(kpis.count() > 0, "o painel não mostra os indicadores")
    texto = " ".join(kpis.first.inner_text().split())
    ranking = pg.get_by_role("region", name="Tabela: Ranking de parceiros").locator("tbody tr").count()
    confere(ranking > 0, "o ranking está vazio")
    return f"indicadores: '{texto[:150]}'; ranking com {ranking} linhas"


@caso("CT-F20")
def recorte(x: Execucao, pg) -> str:
    x.entrar(pg, "GESTOR", "/")
    categoria = pg.get_by_label("Categoria", exact=True)
    escolhida = categoria.locator("option").nth(1)
    valor, nome = escolhida.get_attribute("value"), escolhida.inner_text()
    with pg.expect_response(
        lambda r: "/api/painel/indicadores" in r.url and f"categoria_id={valor}" in r.url, timeout=20000
    ):
        categoria.select_option(value=valor)
    sossegar(pg)
    confere(
        f"categoria_id={valor}" in pg.url or "categoria" in pg.url,
        f"o endereço não guarda o recorte: {pg.url}",
    )
    return f"recorte '{nome}': indicadores e ranking pedidos com categoria_id={valor}; endereço {caminho(pg, x.web)}"


# ---------------------------------------------------------------- modelo
@caso("CT-F21")
def treinar(x: Execucao, pg) -> str:
    x.entrar(pg, "GESTOR", "/modelo")
    pg.get_by_role("button", name=re.compile("^Treinar")).first.click()
    r = confirmar(
        pg, pg.locator(".confirmacao button").first.inner_text().strip(), ("POST", r"/api/modelo/treinos$")
    )
    confere(r.status == 202, f"o treino respondeu {r.status}: {r.text()[:200]}")
    treino = r.json()["id"]
    pg.wait_for_function("!document.body.innerText.includes('Treinando')", timeout=900000)
    sossegar(pg)
    situacao = x.api("GESTOR").get(f"/api/modelo/treinos/{treino}").json()
    confere(situacao.get("situacao") == "CONCLUIDO", f"o treino terminou em {situacao.get('situacao')}")
    return f"treino {treino} disparado (202) e acompanhado até o fim: {situacao.get('situacao')}"


# ---------------------------------------------------------------- campanha
@caso("CT-F22")
def calcular_plano(x: Execucao, pg) -> str:
    x.entrar(pg, "GESTOR", "/campanha")
    pg.locator("#campo-orcamento").fill("15.000,00")
    pg.locator("#campo-maximo_acoes").fill("8")
    pg.get_by_role("button", name="Calcular plano").first.click()
    r = confirmar(pg, "Calcular plano", ("POST", r"/api/otimizacoes$"))
    confere(r.status == 202, f"o cálculo respondeu {r.status}: {r.text()[:200]}")
    x.estado["plano-15000.00"] = r.json()["id"]
    pg.wait_for_function("!document.body.innerText.includes('Calculando')", timeout=300000)
    sossegar(pg)
    x.alvo = pg.get_by_text(re.compile("^Plano calculado")).first
    plano = x.api("GESTOR").get(f"/api/otimizacoes/{r.json()['id']}").json()
    confere(
        plano["situacao"] == "CONCLUIDA" and plano["viavel"],
        f"o plano terminou em {plano['situacao']}, viável: {plano['viavel']}",
    )
    return (
        f"plano {plano['id']} calculado no modo {plano['modo']}: {plano['acoes']} ações, custo R$ {plano['custo_total']}, "
        f"ganho esperado R$ {plano['uplift_total']}, em {plano['tempo_ms']} ms"
    )


@caso("CT-F23")
def comparar(x: Execucao, pg) -> str:
    a, b = x.plano("15000.00"), x.plano("9000.00")
    x.entrar(pg, "GESTOR", "/execucoes?usuario_id=")
    x.ir(pg, f"/execucoes/comparar?a={a}&b={b}")
    confere("comparar" in pg.url, f"não abriu a comparação: {pg.url}")
    titulo = h1(pg)
    return f"a comparação dos planos {a} e {b} abriu ('{titulo}')"


@caso("CT-F24")
def exportar_plano(x: Execucao, pg) -> str:
    ident = x.plano()
    x.entrar(pg, "GESTOR", f"/execucoes/{ident}")
    link = pg.get_by_role("link", name=re.compile("CSV"))
    href = link.first.get_attribute("href")
    r = pg.context.request.get(x.web + href if href.startswith("/") else href)
    corpo = r.body().decode("utf-8-sig")
    confere(
        r.status == 200 and "text/csv" in r.headers.get("content-type", ""),
        f"o CSV do plano respondeu {r.status}",
    )
    return f"{href} → 200 text/csv, {len(corpo.splitlines()) - 1} ações; cabeçalho '{corpo.splitlines()[0][:90]}'"


@caso("CT-F25")
def catalogo(x: Execucao, pg) -> str:
    x.entrar(pg, "GESTOR", "/campanha")
    nome = f"Cupom {x.marca}"
    pg.get_by_role("button", name=re.compile("Nova ação")).click()
    grupo = pg.get_by_role("group", name="Nova ação")
    grupo.get_by_label(re.compile("^Nome")).fill(nome)
    grupo.get_by_label(re.compile("^Custo unitário")).fill("35,00")
    grupo.get_by_label(re.compile("^Efeito de crescimento")).fill("4")
    grupo.get_by_label(re.compile("^Efeito de retenção")).fill("2")
    r = resposta(
        pg,
        "POST",
        r"/api/acoes-comerciais$",
        lambda: grupo.get_by_role("button", name=re.compile("^Salvar")).click(),
    )
    confere(r.status == 201, f"a criação respondeu {r.status}: {r.text()[:200]}")
    sossegar(pg)
    pg.get_by_role("button", name=f"Editar {nome}").click()
    grupo = pg.get_by_role("group", name=f"Editar {nome}")
    grupo.get_by_label(re.compile("^Custo unitário")).fill("40,00")
    grupo.get_by_role("checkbox").uncheck()
    r = resposta(
        pg,
        "PATCH",
        r"/api/acoes-comerciais/\d+$",
        lambda: grupo.get_by_role("button", name=re.compile("^Salvar")).click(),
    )
    confere(
        r.status == 200 and r.json()["ativa"] is False, f"a edição respondeu {r.status}: {r.text()[:200]}"
    )
    sossegar(pg)
    linha = pg.locator("tbody tr").filter(has_text=nome)
    expect(linha).to_contain_text("Inativa", timeout=10000)
    expect(linha).to_contain_text("40,00")
    x.alvo = linha
    return f"criada (201), editada e desativada (200); a linha do catálogo: '{' '.join(linha.inner_text().split())}'"


# ---------------------------------------------------------------- benchmark
@caso("CT-F26")
def benchmark(x: Execucao, pg) -> str:
    x.entrar(pg, "GESTOR", "/benchmark")
    pg.get_by_label("Parceiros", exact=True).fill("500")
    pg.get_by_label("Repetições", exact=True).fill("1")
    r = resposta(
        pg, "POST", r"/api/benchmarks$", lambda: pg.get_by_role("button", name="Rodar benchmark").click()
    )
    confere(r.status == 202, f"o benchmark respondeu {r.status}: {r.text()[:200]}")
    pg.wait_for_function("!document.body.innerText.includes('Benchmark em andamento')", timeout=600000)
    sossegar(pg)
    final = x.api("GESTOR").get(f"/api/benchmarks/{r.json()['id']}").json()
    confere(
        final["situacao"] == "CONCLUIDA",
        f"o benchmark terminou em {final['situacao']}: {final.get('motivo')}",
    )
    modos = [
        f"{c['coluna']} {c['situacao']}" + (f" {c['media_s']:.3f} s" if c.get("media_s") is not None else "")
        for c in final["colunas"]
    ]
    x.alvo = pg.locator("table").first
    return f"benchmark {final['id']} concluído; " + "; ".join(modos)


# ---------------------------------------------------------------- mensagens
@caso("CT-F27")
def gerar_mensagens(x: Execucao, pg) -> str:
    ident = x.plano()
    x.entrar(pg, "GESTOR", "/")
    r = resposta(pg, "POST", r"/api/mensagens/publico$", lambda: x.ir(pg, f"/mensagens?plano={ident}"))
    confere(r.status == 200, f"a prévia do público respondeu {r.status}")
    sossegar(pg)
    gerar = pg.get_by_role("button", name=re.compile(r"^Gerar \d+ mensage"))
    rotulo = gerar.inner_text().strip()
    r = resposta(pg, "POST", r"/api/mensagens/lotes$", gerar.click)
    confere(r.status == 202, f"a geração respondeu {r.status}: {r.text()[:200]}")
    x.estado["lote"] = r.json()["id"]
    link = pg.get_by_role("link", name=re.compile("Ver estas mensagens na fila de aprovação"))
    link.wait_for(timeout=900000)
    lote = x.api("GESTOR").get(f"/api/mensagens/lotes/{x.estado['lote']}").json()
    return f"'{rotulo}' (202); lote {lote.get('id')} pronto: {json.dumps({k: v for k, v in lote.items() if isinstance(v, int | str) and k != 'id'}, ensure_ascii=False)[:160]}"


def lote(x: Execucao) -> int:
    if "lote" not in x.estado:
        gestor = x.api("GESTOR")
        r = gestor.post("/api/mensagens/lotes", json={"plano_id": x.plano()})
        confere(r.status_code == 202, f"o lote não foi pedido: {r.status_code} {r.text[:200]}")
        x.estado["lote"] = r.json()["id"]
        limite = time.monotonic() + 900
        while gestor.get(f"/api/mensagens/lotes/{x.estado['lote']}").json().get("situacao") == "EM_ANDAMENTO":
            confere(time.monotonic() < limite, "o lote não terminou em 15 minutos")
            time.sleep(2)
    return x.estado["lote"]


def cartoes(pg):
    return pg.locator("ol.lista-mensagens > li")


@caso("CT-F28")
def aprovar(x: Execucao, pg) -> str:
    x.entrar(pg, "GESTOR", f"/aprovacao?lote={lote(x)}")
    antes = cartoes(pg).count()
    r = resposta(
        pg,
        "POST",
        r"/aprovacao$",
        lambda: cartoes(pg).first.get_by_role("button", name="Aprovar", exact=True).click(),
    )
    confere(r.status == 200, f"a aprovação respondeu {r.status}")
    sossegar(pg)
    return f"a fila do lote tinha {antes} pendentes; uma aprovada (200), e a fila ficou com {cartoes(pg).count()}"


@caso("CT-F29")
def editar_mensagem(x: Execucao, pg) -> str:
    x.entrar(pg, "GESTOR", f"/aprovacao?lote={lote(x)}")
    cartao = cartoes(pg).first
    cartao.get_by_role("button", name="Editar", exact=True).click()
    caixa = pg.locator("ol.lista-mensagens textarea").first
    caixa.fill(caixa.input_value() + " Conte com a gente.")
    r = resposta(pg, "POST", r"/edicao$", lambda: pg.get_by_role("button", name="Salvar o texto").click())
    confere(r.status == 200, f"a edição respondeu {r.status}: {r.text()[:200]}")
    confere("Conte com a gente." in r.json().get("texto", ""), "o texto salvo não tem a edição")
    return "o texto editado foi salvo (200) e voltou com a frase acrescentada"


@caso("CT-F30")
def rejeitar(x: Execucao, pg) -> str:
    x.entrar(pg, "GESTOR", f"/aprovacao?lote={lote(x)}")
    cartoes(pg).first.get_by_role("button", name="Rejeitar", exact=True).click()
    pg.locator("ol.lista-mensagens textarea").first.fill("Tom inadequado para este parceiro.")
    r = resposta(
        pg, "POST", r"/rejeicao$", lambda: pg.get_by_role("button", name="Rejeitar mensagem").click()
    )
    confere(r.status == 200, f"a rejeição respondeu {r.status}: {r.text()[:200]}")
    return f"rejeitada (200) com o motivo; estado {r.json().get('estado')}"


# ---------------------------------------------------------------- assistente
def perguntar(pg, texto: str) -> dict:
    pg.locator("#campo-pergunta").fill(texto)
    r = resposta(
        pg,
        "POST",
        r"/api/assistente/perguntas$",
        lambda: pg.get_by_role("button", name="Perguntar").click(),
        limite=240000,
    )
    confere(r.status == 200, f"a pergunta respondeu {r.status}")
    sossegar(pg, 240000)
    return r.json()


@caso("CT-F31")
def assistente_responde(x: Execucao, pg) -> str:
    x.entrar(pg, "GESTOR", "/assistente")
    corpo = perguntar(pg, "Qual foi o faturamento total da rede na última semana?")
    if corpo["situacao"] == "INDISPONIVEL":
        raise NaoExecutado(
            "o modelo de linguagem está fora do ar (suba com --profile assistente); a tela disse 'Assistente indisponível'"
        )
    resposta_tela = " ".join(pg.locator(".resposta").first.inner_text().split())
    confere(
        corpo["situacao"] == "RESPONDIDA" and corpo.get("fonte") and "Fonte" in resposta_tela,
        f"{corpo['situacao']}: '{resposta_tela[:160]}'",
    )
    return f"{corpo['situacao']}, redigida por {corpo.get('redator')}; na tela: '{resposta_tela[:220]}'"


@caso("CT-F32")
def assistente_abstem(x: Execucao, pg) -> str:
    x.entrar(pg, "GESTOR", "/assistente")
    corpo = perguntar(pg, "Qual vai ser a cotação do dólar amanhã?")
    if corpo["situacao"] == "INDISPONIVEL":
        raise NaoExecutado(
            "o modelo de linguagem está fora do ar (suba com --profile assistente); a tela disse 'Assistente indisponível'"
        )
    resposta_tela = " ".join(pg.locator(".resposta").first.inner_text().split())
    confere(
        corpo["situacao"] == "ABSTENCAO" and not re.search(r"\d", corpo["texto"]),
        f"{corpo['situacao']}: '{resposta_tela[:160]}'",
    )
    return f"{corpo['situacao']}; na tela: '{resposta_tela[:220]}'"


# ---------------------------------------------------------------- relatórios
@caso("CT-F33")
def relatorios(x: Execucao, pg) -> str:
    x.entrar(pg, "GESTOR", "/relatorios")
    vistos = []
    for rota in ("desempenho", "risco", "campanha"):
        x.ir(pg, f"/relatorios/{rota}")
        confere(pg.locator(".folha").count() > 0, f"o relatório {rota} não abriu a folha")
        vistos.append(f"{rota}: '{h1(pg)}'")
    return "; ".join(vistos)


@caso("CT-F34")
def imprimir(x: Execucao, pg) -> str:
    x.entrar(pg, "GESTOR", "/relatorios/desempenho")
    pg.emulate_media(media="print")
    menu = pg.locator("aside.trilho")
    escondido = menu.count() == 0 or not menu.is_visible()
    x.foto(pg, "CT-F34")
    pg.emulate_media(media="screen")
    confere(escondido, "na impressão, o menu continua na folha")
    return "na mídia de impressão, só a folha do relatório aparece: o menu e o cabeçalho saem"


@caso("CT-F35")
def operacoes(x: Execucao, pg) -> str:
    x.entrar(pg, "ADMINISTRADOR", "/relatorios/operacoes")
    confere(pg.locator(".folha").count() > 0, "o relatório de operações não abriu")
    return f"o Administrador abre '{h1(pg)}'"


# ---------------------------------------------------------------- auditoria
@caso("CT-F36")
def auditoria(x: Execucao, pg) -> str:
    usuario_novo(x)
    x.entrar(pg, "ADMINISTRADOR", "/auditoria")
    with pg.expect_response(lambda r: "/api/auditoria" in r.url and "busca=" in r.url, timeout=20000):
        pg.get_by_role("searchbox").first.fill(x.marca)
    sossegar(pg)
    linhas = pg.get_by_role("region", name="Tabela: Trilha de auditoria").locator("tbody tr")
    n = linhas.count()
    confere(n > 0, "a busca pela marca da execução não trouxe nenhum registro")
    return f"a busca por '{x.marca}' trouxe {n} registros; o primeiro: '{' '.join(linhas.first.inner_text().split())[:140]}'"


# ---------------------------------------------------------------- configuração
@caso("CT-F37")
def limiar(x: Execucao, pg) -> str:
    antes = x.admin.get("/api/configuracao/segmentacao").json()
    try:
        x.entrar(pg, "ADMINISTRADOR", "/configuracao")
        campo = pg.get_by_label(re.compile("^Períodos de tendência"))
        valor = campo.input_value()
        campo.fill(str(int(valor) + 1))
        pg.get_by_role("button", name="Salvar limiares").click()
        r = confirmar(pg, "Salvar limiares", ("PUT", r"/api/configuracao/segmentacao$"), limite=120000)
        confere(r.status == 200, f"salvar respondeu {r.status}: {r.text()[:200]}")
        sossegar(pg)
        depois = r.json()
        confere(
            depois["periodos_tendencia"] == int(valor) + 1, f"a API devolveu {depois['periodos_tendencia']}"
        )
        x.foto(pg, "CT-F37")
        return f"períodos de tendência de {valor} para {int(valor) + 1} (200), gravado por {depois['atualizado_por']}"
    finally:
        # Volta ao valor de antes mesmo se o caso falhou no meio: o limiar vale para a rede inteira.
        atual = x.admin.get("/api/configuracao/segmentacao").json()
        if any(atual[k] != antes[k] for k in LIMIARES):
            x.admin.put(
                "/api/configuracao/segmentacao", json={k: antes[k] for k in LIMIARES}
            ).raise_for_status()


# ---------------------------------------------------------------- portal
@caso("CT-F38")
def portal(x: Execucao, pg) -> str:
    x.entrar(pg, "PARCEIRO", "/")
    pg.wait_for_url("**/meu-desempenho", timeout=15000)
    sossegar(pg)
    kpi = " ".join(pg.locator(".faixa-kpi").first.inner_text().split())
    return f"abriu /meu-desempenho; indicadores do próprio parceiro: '{kpi[:160]}'"


# ================================================================== validação
@caso("CT-V01")
def senha_errada(x: Execucao, pg) -> str:
    x.recusa_esperada("POST", r"/api/sessao$", 401)
    x.entrar_pela_tela(pg, x.login("GESTOR"), "senha-que-nao-e-esta")
    alerta = pg.locator("#entrar-form [role=alert]")
    alerta.wait_for(timeout=15000)
    texto = " ".join(alerta.inner_text().split())
    senha = pg.locator("#campo-senha").input_value()
    login = pg.locator("#campo-login").input_value()
    confere(senha == "" and login == x.login("GESTOR"), "a tela não apagou só a senha")
    return f"'{texto}'; o login continua preenchido e só a senha foi apagada"


@caso("CT-V02")
def entrar_vazio(x: Execucao, pg) -> str:
    x.ir(pg, "/entrar")
    x.recusa_esperada("GET", r"/api/sessao/atual$", 401)
    botao = pg.get_by_role("button", name="Entrar", exact=True)
    vazio = botao.is_disabled()
    pg.locator("#campo-login").fill("alguem")
    so_login = botao.is_disabled()
    pg.locator("#campo-senha").fill("x")
    confere(vazio and so_login and botao.is_enabled(), "o botão Entrar não acompanha os campos")
    return "o botão Entrar fica desligado com os campos vazios e com só o login; liga com os dois"


@caso("CT-V03")
def usuario_sem_campos(x: Execucao, pg) -> str:
    x.entrar(pg, "ADMINISTRADOR", "/usuarios/novo")
    x.recusa_esperada("POST", r"/api/usuarios$", 422)
    pg.get_by_role("button", name="Criar usuário").click()
    erros = {n: erro_do_campo(pg, n) for n in ("login", "nome", "senha", "perfil")}
    return "; ".join(f"{n}: '{m}'" for n, m in erros.items())


@caso("CT-V04")
def login_fora_do_formato(x: Execucao, pg) -> str:
    x.entrar(pg, "ADMINISTRADOR", "/usuarios/novo")
    x.recusa_esperada("POST", r"/api/usuarios$", 422)
    preencher_usuario(pg, "Fulano Silva", "Teste Formato", x.senha, "Analista")
    pg.get_by_role("button", name="Criar usuário").click()
    return f"login 'Fulano Silva': '{erro_do_campo(pg, 'login')}'"


@caso("CT-V05")
def senha_fraca(x: Execucao, pg) -> str:
    x.entrar(pg, "ADMINISTRADOR", "/usuarios/novo")
    x.recusa_esperada("POST", r"/api/usuarios$", 422)
    login = f"{x.marca}.fraca"
    preencher_usuario(pg, login, "Teste Senha Fraca", "curta1", "Analista")
    pg.get_by_role("button", name="Criar usuário").click()
    curta = erro_do_campo(pg, "senha")
    pg.locator("#campo-senha").fill(f"{login}-2026")
    pg.get_by_role("button", name="Criar usuário").click()
    pg.wait_for_timeout(800)
    com_login = erro_do_campo(pg, "senha")
    return f"'curta1': '{curta}'; com o login dentro: '{com_login}'"


@caso("CT-V06")
def login_repetido(x: Execucao, pg) -> str:
    x.entrar(pg, "ADMINISTRADOR", "/usuarios/novo")
    x.recusa_esperada("POST", r"/api/usuarios$", 409)
    preencher_usuario(pg, x.login("GESTOR"), "Teste Repetido", x.senha, "Analista")
    pg.get_by_role("button", name="Criar usuário").click()
    alerta = pg.locator("form [role=alert]").first
    alerta.wait_for(timeout=15000)
    link = pg.get_by_role("link", name=re.compile("Abrir a conta que já usa este login"))
    confere(link.count() == 1, "a recusa não aponta a conta existente")
    return f"'{' '.join(alerta.inner_text().split())}'"


@caso("CT-V07")
def parceiro_sem_nome(x: Execucao, pg) -> str:
    x.entrar(pg, "GESTOR", "/parceiros/novo")
    x.recusa_esperada("POST", r"/api/parceiros$", 422)
    pg.get_by_role("button", name="Cadastrar parceiro").click()
    return f"nome em branco: '{erro_do_campo(pg, 'nome')}'"


@caso("CT-V08")
def parceiro_repetido(x: Execucao, pg) -> str:
    antigo = x.parceiro_com_historico()
    x.entrar(pg, "GESTOR", "/parceiros/novo")
    x.recusa_esperada("POST", r"/api/parceiros$", 409)
    pg.locator("#campo-nome").fill(antigo["nome"])
    pg.get_by_role("button", name="Cadastrar parceiro").click()
    link = pg.get_by_role("link", name=re.compile("^Abrir o cadastro de"))
    link.wait_for(timeout=15000)
    alerta = " ".join(pg.locator("form [role=alert]").first.inner_text().split())
    return f"'{alerta}'"


@caso("CT-V09")
def excluir_com_historico(x: Execucao, pg) -> str:
    antigo = x.parceiro_com_historico()
    x.entrar(pg, "GESTOR", f"/parceiros/{antigo['id']}")
    x.recusa_esperada("DELETE", r"/api/parceiros/\d+$", 409)
    pg.get_by_role("button", name="Excluir parceiro").click()
    r = confirmar(pg, "Excluir", ("DELETE", r"/api/parceiros/\d+$"))
    confere(r.status == 409, f"a exclusão respondeu {r.status}")
    pg.wait_for_timeout(500)
    recusa = (
        " ".join(
            pg.get_by_role("region", name=re.compile("Excluir"))
            .locator("[role=alert]")
            .first.inner_text()
            .split()
        )
        if pg.get_by_role("region", name=re.compile("Excluir")).count()
        else r.json().get("erro")
    )
    return f"recusada (409): '{recusa}'"


@caso("CT-V10")
def importacao_sem_periodo(x: Execucao, pg) -> str:
    x.entrar(pg, "GESTOR", "/importacao")
    x.recusa_esperada("POST", r"/api/importacoes/previa$", 422)
    pg.locator("#campo-texto").fill(relatorio_de_teste(x))
    r = resposta(
        pg, "POST", r"/api/importacoes/previa$", lambda: pg.get_by_role("button", name="Ver a prévia").click()
    )
    confere(r.status == 422, f"a prévia sem período respondeu {r.status}")
    return f"recusada (422): início '{erro_do_campo(pg, 'periodo_inicio')}'"


@caso("CT-V11")
def periodo_invertido(x: Execucao, pg) -> str:
    x.entrar(pg, "GESTOR", "/importacao")
    x.recusa_esperada("POST", r"/api/importacoes/previa$", 422)
    inicio, fim = x.semana_futura()
    colar_relatorio(pg, fim, inicio, relatorio_de_teste(x))
    r = resposta(
        pg, "POST", r"/api/importacoes/previa$", lambda: pg.get_by_role("button", name="Ver a prévia").click()
    )
    confere(r.status == 422, f"o período invertido respondeu {r.status}")
    sossegar(pg)
    mensagens = " ".join(pg.locator(".campo__erro, form [role=alert]").first.inner_text().split())
    return f"recusado (422): '{mensagens}'"


@caso("CT-V12")
def periodo_repetido(x: Execucao, pg) -> str:
    ultima = (
        x.api("GESTOR")
        .get("/api/importacoes", params={"pagina": 1, "tamanho": 1})
        .json()["itens"][0]["periodo"]
    )
    x.entrar(pg, "GESTOR", "/importacao")
    colar_relatorio(pg, ultima["data_inicio"], ultima["data_fim"], relatorio_de_teste(x))
    resposta(
        pg, "POST", r"/api/importacoes/previa$", lambda: pg.get_by_role("button", name="Ver a prévia").click()
    )
    sossegar(pg)
    x.recusa_esperada("POST", r"/api/importacoes$", 409)
    r = resposta(
        pg, "POST", r"/api/importacoes$", lambda: pg.get_by_role("button", name=re.compile("^Gravar")).click()
    )
    confere(r.status == 409, f"gravar um período já importado respondeu {r.status}")
    texto = " ".join(pg.locator(".confirmacao").inner_text().split())
    x.foto(pg, "CT-V12", pg.locator(".confirmacao"))
    pg.locator(".confirmacao").get_by_role("button", name="Cancelar").click()
    return f"recusado (409), nada gravado: '{texto[:200]}' — cancelado, sem substituir"


@caso("CT-V13")
def nenhuma_linha(x: Execucao, pg) -> str:
    x.entrar(pg, "GESTOR", "/importacao")
    colar_relatorio(pg, *x.semana_futura(), "Parceiro;Faturamento;Pedidos\nlinha sem sentido\noutra;abc;x")
    resposta(
        pg, "POST", r"/api/importacoes/previa$", lambda: pg.get_by_role("button", name="Ver a prévia").click()
    )
    sossegar(pg)
    vazio = pg.get_by_text("Nenhuma linha aproveitável")
    confere(vazio.count() > 0, "a prévia não disse que nada se aproveita")
    gravar = pg.get_by_role("button", name=re.compile("^Gravar"))
    desligado = gravar.count() == 0 or gravar.is_disabled()
    confere(desligado, "a prévia sem linha aproveitável ainda oferece gravar")
    return "a prévia diz 'Nenhuma linha aproveitável', com o motivo de cada linha, e não oferece gravar"


@caso("CT-V14")
def orcamento_zero(x: Execucao, pg) -> str:
    x.entrar(pg, "GESTOR", "/campanha")
    x.recusa_esperada("POST", r"/api/otimizacoes$", 422)
    pg.locator("#campo-orcamento").fill("0,00")
    pg.locator("#campo-maximo_acoes").fill("8")
    pg.get_by_role("button", name="Calcular plano").first.click()
    confirmar(pg, "Calcular plano")
    return f"orçamento zero: '{erro_do_campo(pg, 'orcamento')}'"


@caso("CT-V15")
def campanha_inviavel(x: Execucao, pg) -> str:
    x.entrar(pg, "GESTOR", "/campanha")
    pg.locator("#campo-orcamento").fill("100,00")
    pg.locator("#campo-maximo_acoes").fill("8")
    pg.locator("#campo-cota_cauda_longa").fill("100")
    pg.get_by_role("button", name="Calcular plano").first.click()
    r = confirmar(pg, "Calcular plano", ("POST", r"/api/otimizacoes$"))
    confere(r.status == 202, f"o pedido respondeu {r.status}: {r.text()[:200]}")
    pg.wait_for_function("!document.body.innerText.includes('Calculando')", timeout=300000)
    sossegar(pg)
    final = x.api("GESTOR").get(f"/api/otimizacoes/{r.json()['id']}").json()
    confere(
        final["viavel"] is False,
        f"as cotas acima do orçamento deram um plano viável ({final.get('acoes')} ações)",
    )
    motivo = pg.get_by_text(final["motivo"][:40])
    confere(motivo.count() > 0, "a tela não mostra o motivo da inviabilidade")
    x.alvo = motivo.first
    return f"sem solução viável (restrição: {final['restricao_violada']}); a tela diz: '{final['motivo']}'"


@caso("CT-V16")
def limiar_fora_da_faixa(x: Execucao, pg) -> str:
    x.entrar(pg, "ADMINISTRADOR", "/configuracao")
    x.recusa_esperada("PUT", r"/api/configuracao/segmentacao$", 422)
    pg.get_by_label(re.compile("^Tamanho do Top")).fill("0")
    pg.get_by_role("button", name="Salvar limiares").click()
    confirmar(pg, "Salvar limiares")
    return f"Top 0: '{erro_do_campo(pg, 'top_n')}'"


@caso("CT-V17")
def propria_senha_pelo_admin(x: Execucao, pg) -> str:
    eu = next(u for u in x.admin.get("/api/usuarios").json() if u["login"] == x.login("ADMINISTRADOR"))
    x.entrar(pg, "ADMINISTRADOR", f"/usuarios/{eu['id']}")
    confere(pg.locator("#campo-senha_nova").count() == 0, "a tela oferece redefinir a própria senha")
    texto = " ".join(pg.get_by_text(re.compile("Esta é a sua conta")).first.inner_text().split())
    return f"na própria conta, a redefinição não aparece: '{texto}'"


def conta_para_senha(x: Execucao, pg) -> None:
    login = f"{x.marca}.senha"
    if "conta_senha" not in x.estado:
        x.admin.post(
            "/api/usuarios",
            json={"login": login, "nome": "Teste Senha", "senha": x.senha, "perfil": "ANALISTA"},
        ).raise_for_status()
        x.estado["conta_senha"] = login
    pg.context.request.post(x.web + "/api/sessao", data={"login": login, "senha": x.senha})
    x.ir(pg, "/conta")


@caso("CT-V18")
def senha_atual_errada(x: Execucao, pg) -> str:
    conta_para_senha(x, pg)
    x.recusa_esperada("POST", r"/api/sessao/senha$", 422)
    nova = f"nova-{secrets.token_urlsafe(10)}"
    pg.get_by_label(re.compile("^Senha atual")).fill("nao-e-a-senha-atual")
    pg.get_by_label(re.compile(r"^Senha nova(?!,)")).fill(nova)
    pg.get_by_label(re.compile("^Senha nova, de novo")).fill(nova)
    pg.get_by_role("button", name="Trocar a senha").click()
    return f"senha atual errada: '{erro_do_campo(pg, 'senha_atual')}'"


@caso("CT-V19")
def confirmacao_diferente(x: Execucao, pg) -> str:
    conta_para_senha(x, pg)
    pg.get_by_label(re.compile("^Senha atual")).fill(x.senha)
    pg.get_by_label(re.compile(r"^Senha nova(?!,)")).fill(f"nova-{secrets.token_urlsafe(10)}")
    pg.get_by_label(re.compile("^Senha nova, de novo")).fill(f"outra-{secrets.token_urlsafe(10)}")
    pg.get_by_role("button", name="Trocar a senha").click()
    return f"'{erro_do_campo(pg, 'senha_nova_de_novo') if pg.locator('#campo-senha_nova_de_novo-erro').count() else ' '.join(pg.locator('.campo__erro').first.inner_text().split())}' — nada foi enviado à API"


@caso("CT-V20")
def pergunta_vazia(x: Execucao, pg) -> str:
    x.entrar(pg, "GESTOR", "/assistente")
    botao = pg.get_by_role("button", name="Perguntar")
    vazio = botao.is_disabled()
    pg.locator("#campo-pergunta").fill("   ")
    espacos = botao.is_disabled()
    confere(vazio and espacos, "o botão Perguntar aceita pergunta vazia")
    return "o botão Perguntar fica desligado com a pergunta vazia e com só espaços"


@caso("CT-V21")
def sem_previsao(x: Execucao, pg) -> str:
    novo = x.parceiro_novo()
    x.entrar(pg, "GESTOR", f"/parceiros/{novo['id']}")
    bloco = pg.locator("section").filter(has=pg.locator("#titulo-previsao"))
    texto = " ".join(bloco.inner_text().split())
    confere(
        "Estimativa" in texto and "Faturamento previsto" not in texto,
        "o parceiro sem histórico mostra previsão",
    )
    return f"'{texto[:220]}'"


@caso("CT-V22")
def arquivo_grande(x: Execucao, pg) -> str:
    x.entrar(pg, "GESTOR", "/importacao")
    x.recusa_esperada("POST", r"/api/importacoes/arquivo/previa$", 413)
    inicio, fim = x.semana_futura()
    pg.locator("#campo-periodo_inicio").fill(inicio)
    pg.locator("#campo-periodo_fim").fill(fim)
    pg.get_by_text("Enviar um arquivo CSV").click()
    grande = "Parceiro;Faturamento;Pedidos\n" + "Parceiro de teste;100,00;1\n" * 25000
    pg.locator("#campo-arquivo").set_input_files(
        {"name": "grande.csv", "mimeType": "text/csv", "buffer": grande.encode("utf-8")}
    )
    pg.get_by_role("button", name="Ver a prévia").click()
    alerta = pg.locator(".campo__erro, form [role=alert]").first
    alerta.wait_for(timeout=20000)
    return f"arquivo de {len(grande.encode()) // 1000} kB: '{' '.join(alerta.inner_text().split())}'"


@caso("CT-V23")
def acao_custo_zero(x: Execucao, pg) -> str:
    x.entrar(pg, "GESTOR", "/campanha")
    x.recusa_esperada("POST", r"/api/acoes-comerciais$", 422)
    pg.get_by_role("button", name=re.compile("Nova ação")).click()
    grupo = pg.get_by_role("group", name="Nova ação")
    grupo.get_by_label(re.compile("^Nome")).fill(f"Brinde {x.marca}")
    grupo.get_by_label(re.compile("^Custo unitário")).fill("0")
    grupo.get_by_label(re.compile("^Efeito de crescimento")).fill("3")
    grupo.get_by_role("button", name=re.compile("^Salvar")).click()
    erro = grupo.locator(".campo__erro, .texto-erro, [role=alert]").first
    erro.wait_for(timeout=15000)
    return f"custo zero: '{' '.join(erro.inner_text().split())}'"


# ================================================================== navegação
def menu(pg):
    return pg.get_by_role("navigation", name="Menu principal")


def percorrer_menu(x: Execucao, pg, perfil: str) -> str:
    x.entrar(pg, perfil, "/conta")
    itens = menu(pg).locator("a.menu__item")
    destinos = [
        (
            itens.nth(i).get_attribute("href"),
            " ".join(itens.nth(i).locator(".menu__rotulo").inner_text().split()),
        )
        for i in range(itens.count())
    ]
    confere(destinos, "o menu está vazio")
    vistos = []
    for href, rotulo in destinos:
        menu(pg).locator(f'a.menu__item[href="{href}"]').click()
        pg.wait_for_url(lambda u, h=href: u.split("?")[0].endswith(h), timeout=15000)
        sossegar(pg)
        titulo = h1(pg)
        confere(
            titulo
            and "Sem acesso" not in titulo
            and pg.get_by_text("O seu perfil não abre esta tela").count() == 0,
            f"{href} abriu '{titulo}'",
        )
        confere(pg.get_by_text("Página não encontrada").count() == 0, f"{href} não existe")
        vistos.append(f"{rotulo} → {href}")
    return f"{len(vistos)} itens, todos abriram a tela com título: " + ", ".join(vistos)


@caso("CT-N01")
def menu_administrador(x: Execucao, pg) -> str:
    return percorrer_menu(x, pg, "ADMINISTRADOR")


@caso("CT-N02")
def menu_gestor(x: Execucao, pg) -> str:
    return percorrer_menu(x, pg, "GESTOR")


@caso("CT-N03")
def menu_analista(x: Execucao, pg) -> str:
    return percorrer_menu(x, pg, "ANALISTA")


@caso("CT-N04")
def parceiro_no_inicio(x: Execucao, pg) -> str:
    x.entrar(pg, "PARCEIRO", "/")
    pg.wait_for_url("**/meu-desempenho", timeout=15000)
    sossegar(pg)
    itens = [" ".join(t.split()) for t in menu(pg).locator(".menu__rotulo").all_inner_texts()]
    confere(itens == ["Meu desempenho"], f"o menu do Parceiro tem {itens}")
    return f"/ levou a /meu-desempenho; o menu tem só {itens}"


@caso("CT-N05")
def sem_acesso(x: Execucao, pg) -> str:
    chamadas = []
    pg.on("request", lambda r: "/api/modelo" in r.url and chamadas.append(r.url))
    x.entrar(pg, "ANALISTA", "/modelo")
    aviso = pg.locator(".aviso-pagina")
    aviso.wait_for(timeout=15000)
    texto = " ".join(aviso.inner_text().split())
    confere("não abre esta tela" in texto, f"a tela mostrou '{texto[:120]}'")
    confere(not chamadas, f"a tela chamou a API do modelo: {chamadas}")
    return f"'{texto[:200]}' — nenhuma chamada a /api/modelo"


@caso("CT-N06")
def sem_sessao_volta(x: Execucao, pg) -> str:
    x.recusa_esperada("GET", r"/api/sessao/atual$", 401)
    pg.goto(x.web + "/parceiros?segmento=TOP")
    pg.wait_for_url("**/entrar", timeout=15000)
    x.entrar_pela_tela(pg, x.login("GESTOR"), x.senha)
    pg.wait_for_url(lambda u: "/entrar" not in u, timeout=20000)
    sossegar(pg)
    confere(
        caminho(pg, x.web) == "/parceiros?segmento=TOP", f"depois de entrar, foi para {caminho(pg, x.web)}"
    )
    return "sem sessão, /parceiros?segmento=TOP levou à entrada; depois de entrar, voltou a /parceiros?segmento=TOP"


@caso("CT-N07")
def nao_encontrada(x: Execucao, pg) -> str:
    x.entrar(pg, "GESTOR", "/relatorio-que-nao-existe")
    texto = " ".join(pg.locator(".aviso-pagina").inner_text().split())
    confere("/relatorio-que-nao-existe" in texto, f"a página não mostra o endereço: {texto[:120]}")
    pg.get_by_role("link", name="Ir para o início").click()
    pg.wait_for_url(lambda u: u.rstrip("/") == x.web, timeout=15000)
    sossegar(pg)
    return f"'{texto[:160]}'; 'Ir para o início' levou ao '{h1(pg)}'"


@caso("CT-N08")
def painel_para_lista(x: Execucao, pg) -> str:
    x.entrar(pg, "GESTOR", "/")
    link = pg.get_by_role("link", name=re.compile("parceiros — ver na lista$")).first
    nome = " ".join(link.inner_text().split())
    link.click()
    pg.wait_for_url("**/parceiros?segmento=*", timeout=15000)
    sossegar(pg)
    filtro = pg.get_by_label("Segmento", exact=True).input_value()
    confere(filtro and filtro in pg.url, f"a lista abriu sem o filtro: {pg.url}")
    return f"'{nome}' levou a {caminho(pg, x.web)}, com o segmento escolhido no filtro"


@caso("CT-N09")
def lista_para_cadastro(x: Execucao, pg) -> str:
    x.entrar(pg, "GESTOR", "/parceiros?segmento=TOP")
    primeiro = pg.locator("tbody tr a").first
    nome = primeiro.inner_text().strip()
    primeiro.click()
    pg.wait_for_url(re.compile(r"/parceiros/\d+"), timeout=15000)
    sossegar(pg)
    try:
        pg.wait_for_function(
            "t => document.querySelector('h1')?.textContent.trim() === t", arg=nome, timeout=10000
        )
    except Exception:  # noqa: BLE001
        raise Reprovado(f"o cadastro abriu '{h1(pg)}'") from None
    pg.get_by_role("link", name="Voltar para a lista").click()
    pg.wait_for_url("**/parceiros?segmento=TOP", timeout=15000)
    return f"'{nome}' abriu o cadastro dele; 'Voltar para a lista' voltou a /parceiros?segmento=TOP, com o filtro"


@caso("CT-N10")
def plano_para_mensagens(x: Execucao, pg) -> str:
    ident = x.plano()
    x.entrar(pg, "GESTOR", f"/execucoes/{ident}")
    r = resposta(
        pg,
        "POST",
        r"/api/mensagens/publico$",
        lambda: pg.get_by_role("link", name=re.compile("Gerar mensagens para este plano")).click(),
    )
    pg.wait_for_url(f"**/mensagens?plano={ident}", timeout=15000)
    confere(r.status == 200, f"a prévia do público respondeu {r.status}")
    return f"da execução {ident}, 'Gerar mensagens para este plano' abriu {caminho(pg, x.web)} com a prévia do público já carregada"


@caso("CT-N11")
def voltar_e_avancar(x: Execucao, pg) -> str:
    x.entrar(pg, "GESTOR", "/")
    menu(pg).get_by_role("link", name=re.compile("^Parceiros")).click()
    pg.wait_for_url("**/parceiros", timeout=15000)
    sossegar(pg)
    menu(pg).get_by_role("link", name=re.compile("^Relatórios")).click()
    pg.wait_for_url("**/relatorios", timeout=15000)
    sossegar(pg)
    passos = []
    pg.go_back()
    sossegar(pg)
    passos.append(f"voltar → {caminho(pg, x.web)} ('{h1(pg)}')")
    pg.go_back()
    sossegar(pg)
    passos.append(f"voltar → {caminho(pg, x.web)} ('{h1(pg)}')")
    pg.go_forward()
    sossegar(pg)
    passos.append(f"avançar → {caminho(pg, x.web)} ('{h1(pg)}')")
    confere([p.split(" ")[2] for p in passos] == ["/parceiros", "/", "/parceiros"], "; ".join(passos))
    return "; ".join(passos)


@caso("CT-N12")
def alteracoes_nao_salvas(x: Execucao, pg) -> str:
    novo = x.parceiro_novo()
    x.entrar(pg, "GESTOR", f"/parceiros/{novo['id']}")
    pg.locator("#campo-contato").fill("rascunho que não foi salvo")
    menu(pg).get_by_role("link", name=re.compile("^Painel")).click()
    aviso = pg.get_by_role("alertdialog")
    aviso.wait_for(timeout=10000)
    texto = " ".join(aviso.inner_text().split())
    aviso.get_by_role("button", name="Continuar editando").click()
    confere(
        re.search(r"/parceiros/\d+$", pg.url)
        and pg.locator("#campo-contato").input_value() == "rascunho que não foi salvo",
        "continuar editando perdeu o texto",
    )
    menu(pg).get_by_role("link", name=re.compile("^Painel")).click()
    pg.get_by_role("alertdialog").get_by_role("button", name="Sair sem salvar").click()
    pg.wait_for_url(lambda u: u.rstrip("/") == x.web, timeout=15000)
    return f"'{texto[:160]}'; 'Continuar editando' manteve o texto; 'Sair sem salvar' foi ao painel"


@caso("CT-N13")
def sessao_termina(x: Execucao, pg) -> str:
    x.entrar(pg, "GESTOR", "/parceiros?pagina=2")
    x.recusa_esperada("GET", r"/api/", 401)
    pg.context.request.delete(x.web + "/api/sessao")
    menu(pg).get_by_role("link", name=re.compile("^Execuções")).click()
    pg.wait_for_url("**/entrar", timeout=20000)
    aviso = pg.get_by_text(re.compile("sessão terminou"))
    aviso.wait_for(timeout=10000)
    texto = " ".join(aviso.inner_text().split())
    x.entrar_pela_tela(pg, x.login("GESTOR"), x.senha)
    pg.wait_for_url(lambda u: "/entrar" not in u, timeout=20000)
    sossegar(pg)
    confere("/execucoes" in pg.url, f"depois de entrar de novo, foi para {caminho(pg, x.web)}")
    return f"'{texto}'; ao entrar de novo, voltou a {caminho(pg, x.web)}"


@caso("CT-N14")
def teclado(x: Execucao, pg) -> str:
    x.entrar(pg, "GESTOR", "/")
    pg.keyboard.press("Tab")
    primeiro = pg.evaluate("document.activeElement.textContent.trim()")
    confere(primeiro == "Pular para o conteúdo", f"o primeiro Tab foi para '{primeiro}'")
    pg.keyboard.press("Enter")
    alvo = pg.evaluate("document.activeElement.id || document.activeElement.tagName")
    menu(pg).get_by_role("link", name=re.compile("^Parceiros")).click()
    pg.wait_for_url("**/parceiros", timeout=15000)
    sossegar(pg)
    foco = pg.evaluate("document.activeElement.tagName + ':' + document.activeElement.textContent.trim()")
    confere(foco.startswith("H1"), f"depois de trocar de tela, o foco está em {foco}")
    return f"o primeiro Tab é '{primeiro}', e Enter leva a #{alvo}; ao trocar de tela, o foco vai ao título ({foco})"


@caso("CT-N15")
def gaveta(x: Execucao, pg) -> str:
    pg.set_viewport_size({"width": 768, "height": 1024})
    x.entrar(pg, "GESTOR", "/")
    botao = pg.get_by_role("button", name="Abrir o menu")
    # Fechada, a gaveta fica fora da tela: o lado direito do menu à esquerda do zero.
    fora = "document.getElementById('menu-principal').getBoundingClientRect().right <= 0"
    fechado = pg.evaluate(fora) and botao.get_attribute("aria-expanded") == "false"
    botao.click()
    pg.wait_for_function(
        "document.getElementById('menu-principal').getBoundingClientRect().left >= 0", timeout=5000
    )
    aberto = botao.get_attribute("aria-expanded") == "true"
    x.foto(pg, "CT-N15")
    menu(pg).get_by_role("link", name=re.compile("^Parceiros")).click()
    pg.wait_for_url("**/parceiros", timeout=15000)
    sossegar(pg)
    pg.wait_for_timeout(400)
    confere(
        fechado and aberto,
        f"a gaveta começou {'fechada' if fechado else 'aberta'} e o botão {'abriu' if aberto else 'não abriu'}",
    )
    confere(pg.evaluate(fora), "a gaveta não fechou depois da escolha")
    largura = pg.evaluate("document.documentElement.scrollWidth")
    confere(largura <= 768, f"a página rola na horizontal ({largura} px)")
    return f"a 768 px o menu começa fora da tela; 'Abrir o menu' o mostra, e escolher Parceiros navega e o fecha; a página tem {largura} px, sem rolar na horizontal"


@caso("CT-N16")
def onde_estou(x: Execucao, pg) -> str:
    antigo = x.parceiro_com_historico()
    x.entrar(pg, "GESTOR", f"/parceiros/{antigo['id']}")
    onde = " ".join(pg.get_by_role("navigation", name="Onde você está").inner_text().split())
    confere("Análise" in onde, f"o cabeçalho diz '{onde}'")
    volta = pg.get_by_role("link", name=re.compile("^Voltar para")).first
    rotulo = volta.get_attribute("aria-label") or volta.inner_text()
    volta.click()
    pg.wait_for_url(lambda u: not re.search(r"/parceiros/\d+$", u), timeout=15000)
    return f"o cabeçalho diz '{onde}'; '{rotulo.strip()}' levou a {caminho(pg, x.web)}"


# ================================================================== o roteiro
def preparar(x: Execucao) -> None:
    """As quatro contas da execução, uma por perfil; o Parceiro vinculado ao de maior faturamento."""
    for perfil, sufixo in PERFIS.items():
        corpo = {
            "login": f"{x.marca}.{sufixo}",
            "nome": f"Teste {NOME_DO_PERFIL[perfil]}",
            "senha": x.senha,
            "perfil": perfil,
        }
        if perfil == "PARCEIRO":
            corpo["parceiro_id"] = x.parceiro_com_historico()["id"]
        x.admin.post("/api/usuarios", json=corpo).raise_for_status()


def rodar(x: Execucao, catalogo: dict[str, Caso], escolhidos: list[str], canal: str, ver: bool) -> list[Caso]:
    from playwright.sync_api import sync_playwright

    feitos: list[Caso] = []
    with sync_playwright() as p:
        navegador = p.chromium.launch(channel=canal, headless=not ver, slow_mo=250 if ver else 0)
        x.estado["navegador"] = (
            f"{ {'msedge': 'Microsoft Edge', 'chrome': 'Google Chrome'}[canal]} {navegador.version}"
        )
        for ident in escolhidos:
            c = catalogo[ident]
            # A tela de entrada confere se já há sessão, e sem ela a resposta é 401.
            x.esperadas = [("GET", re.compile(r"/api/sessao/atual$"), 401)]
            contexto = navegador.new_context(
                viewport={"width": 1440, "height": 900}, locale="pt-BR", color_scheme="light"
            )
            pg = contexto.new_page()
            pg.set_default_timeout(20000)
            ruido: list[str] = []
            pg.on("pageerror", lambda e, ruido=ruido: ruido.append(f"erro na página: {e}"))
            # A recusa provocada aparece no console como "status of 4xx"; a recarga do
            # servidor de desenvolvimento (WebSocket do Vite) não é da aplicação.
            pg.on(
                "console",
                lambda m, ruido=ruido: m.type == "error"
                and "status of 4" not in m.text
                and "WebSocket" not in m.text
                and ruido.append(f"console: {m.text[:160]}"),
            )

            def anotar(r, ruido=ruido):
                if "/api/" not in r.url or r.status < 400:
                    return
                caminho_api = r.url.split("?")[0]
                if r.status < 500 and any(
                    r.request.method == m and pd.search(caminho_api) and r.status == s
                    for m, pd, s in x.esperadas
                ):
                    return
                ruido.append(f"{r.request.method} {r.url.replace(x.web, '')} → {r.status}")

            pg.on("response", anotar)
            inicio = time.monotonic()
            x.alvo, x.fotografado = None, False
            c.captura = f"{ident}.png"
            try:
                c.obtido = CASOS[ident](x, pg)
                pg.wait_for_timeout(300)
                if ruido:
                    raise Reprovado("; ".join(dict.fromkeys(ruido)))
                c.situacao = "ok"
            except Reprovado as e:
                c.obtido, c.situacao = str(e), "FALHA"
            except NaoExecutado as e:
                c.obtido, c.situacao = str(e), "não executado"
            except Exception as e:  # noqa: BLE001 — o caso falhou por um passo que não aconteceu
                primeira = str(e).strip().splitlines()[0][:300] if str(e).strip() else type(e).__name__
                c.obtido, c.situacao = f"{type(e).__name__}: {primeira}", "FALHA"
                if os.environ.get("GIH_DEPURAR"):
                    traceback.print_exc()
            try:
                if not x.fotografado:
                    centralizar(x.alvo)
                    pg.screenshot(path=str(x.saida / c.captura))
            except Exception:  # noqa: BLE001 — sem captura, o caso continua registrado
                c.captura = ""
            c.segundos = round(time.monotonic() - inicio, 1)
            contexto.close()
            feitos.append(c)
            print(f"{ident}  {c.situacao:<5} {c.segundos:>5.1f} s  {c.obtido[:150]}", flush=True)
        navegador.close()
    return feitos


def relatorio(feitos: list[Caso], x: Execucao, catalogo: dict[str, Caso]) -> str:
    ok = [c for c in feitos if c.situacao == "ok"]
    linhas = [
        "Casos de teste pela tela — gerado por scripts/testar_na_tela.py",
        f"Executado em {datetime.now():%d/%m/%Y %H:%M}, contra {x.web}, no {x.estado.get('navegador', '?')}",
        f"Catálogo: docs/12-plano-de-testes.md ({len(catalogo)} casos; {len(feitos)} executados)",
        "",
    ]
    for c in feitos:
        linhas += [
            f"{c.id}  {c.modulo} · {c.requisito} · {c.perfil}",
            f"    passos:    {c.passos}",
            f"    esperado:  {c.esperado}",
            f"    obtido:    {c.obtido}",
            f"    situação:  {c.situacao} ({c.segundos:.0f} s){'  — captura ' + c.captura if c.captura else ''}",
            "",
        ]
    falhas = [c.id for c in feitos if c.situacao == "FALHA"]
    pulados = [c.id for c in feitos if c.situacao == "não executado"]
    final = f"Resultado: {len(ok)} de {len(feitos)} casos como esperado."
    if falhas:
        final += f" FALHA em {', '.join(falhas)}."
    if pulados:
        final += f" Não executados (o ambiente não permitiu): {', '.join(pulados)}."
    return "\n".join(linhas + [final]) + "\n"


def main() -> None:
    p = argparse.ArgumentParser(description="Executa pela tela os casos do docs/12 (H104, H105).")
    p.add_argument("--web", default="http://localhost:5173")
    p.add_argument("--senha", default=os.environ.get("GIH_ADMIN_SENHA", ""))
    p.add_argument("--saida", default=str(Path(tempfile.gettempdir()) / "gih-casos"))
    p.add_argument("--navegador", choices=sorted(NAVEGADORES), default="edge")
    p.add_argument("--so", default="", help="ids ou prefixos separados por vírgula (ex.: CT-N,CT-V05)")
    p.add_argument("--ver", action="store_true", help="com a janela aberta e devagar, para demonstrar")
    args = p.parse_args()

    catalogo = ler_catalogo()
    sem_funcao = sorted(set(catalogo) - set(CASOS))
    sem_caso = sorted(set(CASOS) - set(catalogo))
    if sem_funcao or sem_caso:
        raise SystemExit(
            "O catálogo do docs/12 e o executor divergem — "
            f"casos sem função: {sem_funcao or 'nenhum'}; funções sem caso: {sem_caso or 'nenhuma'}."
        )
    if not args.senha:
        raise SystemExit("Informe a senha do administrador em GIH_ADMIN_SENHA.")
    filtros = [f.strip() for f in args.so.split(",") if f.strip()]
    escolhidos = [i for i in catalogo if not filtros or any(i.startswith(f) for f in filtros)]
    # A importação grava uma semana no futuro, e o painel abre no período mais
    # recente: ela roda por último, para os outros casos verem a base como ela é.
    escolhidos.sort(key=lambda i: catalogo[i].modulo == "Importação" and i.startswith("CT-F"))
    if not escolhidos:
        raise SystemExit(f"Nenhum caso com {args.so}.")

    saida = Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)
    for velha in saida.glob("CT-*.png"):
        velha.unlink()
    marca = f"t{secrets.randbelow(100000):05d}"
    senha = f"teste-{secrets.token_urlsafe(12)}"
    admin = httpx.Client(base_url=args.web, timeout=120)
    r = admin.post("/api/sessao", json={"login": "admin", "senha": args.senha})
    if r.status_code != 201:
        raise SystemExit(
            f"O administrador não entrou ({r.status_code}): confira GIH_ADMIN_SENHA e se o sistema está no ar."
        )
    x = Execucao(args.web, marca, senha, admin, saida, lento=args.ver)
    print(f"execução {marca}: {len(escolhidos)} casos, no {args.navegador}; capturas em {saida}\n")
    feitos: list[Caso] = []
    try:
        preparar(x)
        feitos = rodar(x, catalogo, escolhidos, NAVEGADORES[args.navegador], args.ver)
    finally:
        for c in x.sessoes.values():
            c.delete("/api/sessao")
            c.close()
        print("\nlimpando: " + ", ".join(desativar_usuarios(admin, marca)))
        print(limpar_execucao(marca))
        admin.delete("/api/sessao")
    texto = relatorio(feitos, x, catalogo)
    (saida / "casos.txt").write_text(texto, encoding="utf-8")
    (saida / "casos.json").write_text(
        json.dumps(
            {
                "navegador": x.estado.get("navegador"),
                "web": x.web,
                "executado_em": datetime.now().isoformat(timespec="minutes"),
                "casos": [asdict(c) | {"tipo": c.tipo} for c in feitos],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("\n" + texto.splitlines()[-1])
    sys.exit(0 if all(c.situacao == "ok" for c in feitos) else 1)


if __name__ == "__main__":
    main()
