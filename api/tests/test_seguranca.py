"""Os vetores de ataque do RNF12, do RNF13 e do RNF14 — história H70.

**O que reprova o PR que abre um vetor** não é uma asserção sobre uma rota que
existe hoje: é o teste que olha a aplicação inteira. Por isso a maior parte
deste arquivo é **derivada** — das rotas que a aplicação expõe e do código-fonte
dela —, e não escrita rota a rota:

- **RNF13, injeção SQL.** Um teste lê o código de `app/` e recusa SQL montado
  com texto: f-string, concatenação ou `%` dentro de `text()`, `execute()` e
  afins. Outro manda cargas de injeção em **todo** parâmetro de consulta de
  **toda** rota de leitura, com um perfil que a abre, e confere que nenhuma
  responde 500 e que o banco continua inteiro. Rota nova entra nos dois sem
  ninguém lembrar dela.
- **RNF12, injeção de script.** A saída da API é JSON, nunca HTML, com
  `nosniff`: o mesmo fuzz confere o tipo e o cabeçalho de cada resposta, de
  sucesso ou de erro. O texto do usuário volta como foi gravado — quem o
  escapa é a tela, e `web/src/seguranca.test.js` recusa as formas de pular esse
  escape. E a exportação em CSV, que vai para a planilha, e não para o
  navegador, neutraliza a fórmula.
- **RNF14, autorização.** É do `test_autorizacao.py` (H17): toda rota, contra
  todo perfil, derivada da aplicação; rota sem permissão declarada reprova. A
  troca de perfil e a desativação valendo na requisição seguinte estão em
  `test_usuarios.py`. Aqui fica o que falta a eles: o cookie forjado.
"""
from __future__ import annotations

import ast
import csv
import io
from decimal import Decimal
from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db import Sessao
from app.main import app
from app.modelos import Categoria, Parceiro, Perfil, Usuario
from app.rotas.parceiros import _numero, _texto
from tests.conftest import SENHA_PADRAO
from tests.test_autorizacao import PERMISSOES, PUBLICO, concretizar, rotas_da_aplicacao

APP = Path(__file__).resolve().parent.parent / "app"

CARGAS_SQL = [
    "' OR '1'='1",
    "'; DROP TABLE parceiro; --",
    '" OR ""="',
    "1' UNION SELECT senha_hash FROM usuario --",
    "\\'; SELECT pg_sleep(3); --",
    "%' OR 1=1 --",
]
CARGAS_SCRIPT = [
    "<script>alert('gih')</script>",
    '"><img src=x onerror=alert(1)>',
    "javascript:alert(1)",
    "<svg onload=alert(1)>",
]
CARGAS = CARGAS_SQL + CARGAS_SCRIPT

# Perfis que abrem cada rota, na ordem de preferência para o fuzz: um basta.
PREFERENCIA = (Perfil.GESTOR, Perfil.ANALISTA, Perfil.ADMINISTRADOR, Perfil.PARCEIRO)


# ================================================================ RNF13: o código
# As funções que recebem SQL cru, e em qual argumento. O ORM monta o resto com
# parâmetro; só por estas o texto do usuário chegaria à consulta como código.
RECEBEM_SQL = {"text", "literal_column", "exec_driver_sql", "from_statement", "execute"}


def _montado_com_texto(no: ast.expr) -> bool:
    """f-string, `+`, `%` ou `.format()`: SQL que muda com o valor de uma variável."""
    if isinstance(no, ast.JoinedStr):
        return True
    if isinstance(no, ast.BinOp) and isinstance(no.op, ast.Add | ast.Mod):
        return True
    return (
        isinstance(no, ast.Call)
        and isinstance(no.func, ast.Attribute)
        and no.func.attr == "format"
    )


def test_nenhuma_consulta_e_montada_com_texto():
    """RNF13: toda consulta é parametrizada. `text()` só aceita texto fixo."""
    achados = []
    for arquivo in sorted(APP.rglob("*.py")):
        arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
        for no in ast.walk(arvore):
            if not isinstance(no, ast.Call) or not no.args:
                continue
            nome = getattr(no.func, "attr", None) or getattr(no.func, "id", None)
            if nome not in RECEBEM_SQL:
                continue
            sql = no.args[0]
            # `text()` e `literal_column()` recebem SQL cru: só aceitam texto fixo.
            # `execute()` recebe também consultas do ORM, que são seguras.
            cru = nome in ("text", "literal_column", "exec_driver_sql")
            if _montado_com_texto(sql) or (cru and not isinstance(sql, ast.Constant)):
                achados.append(f"{arquivo.relative_to(APP.parent)}:{no.lineno} {nome}(...)")
    assert achados == [], "SQL montado com texto — use parâmetros: " + ", ".join(achados)


def test_o_teste_do_codigo_acharia_uma_consulta_montada():
    """O teste de cima só vale se reconhecer o que procura."""
    exemplos = {
        'text(f"SELECT * FROM parceiro WHERE nome = \'{nome}\'")': True,
        'text("SELECT * FROM parceiro WHERE nome = \'" + nome + "\'")': True,
        's.execute("SELECT %s" % nome)': True,
        'text("... {}".format(nome))': True,
        'text(consulta)': True,  # texto que veio de algum lugar: não dá para saber
        'text("SELECT 1")': False,
        "s.execute(select(Parceiro).where(Parceiro.nome == nome))": False,
    }
    for codigo, esperado in exemplos.items():
        chamada = ast.parse(codigo).body[0].value
        nome = getattr(chamada.func, "attr", None) or getattr(chamada.func, "id", None)
        sql = chamada.args[0]
        cru = nome in ("text", "literal_column", "exec_driver_sql")
        achou = _montado_com_texto(sql) or (cru and not isinstance(sql, ast.Constant))
        assert achou is esperado, codigo


# ================================================================ o fuzz das rotas
@pytest.fixture
def clientes(criar_usuario):
    """Um cliente autenticado por perfil, e alguns dados para as consultas acharem."""
    s = Sessao()
    try:
        categoria = Categoria(nome="Padaria")
        s.add(categoria)
        s.flush()
        s.add_all([Parceiro(nome="Padaria D'Ávila"), Parceiro(nome="Mercado Sol")])
        vinculado = Parceiro(nome="Parceiro vinculado")
        s.add(vinculado)
        s.commit()
        vinculado_id = vinculado.id
    finally:
        s.close()

    abertos = {}
    for perfil in PREFERENCIA:
        login = f"seguranca.{perfil.value.lower()}"
        criar_usuario(
            login=login,
            perfil=perfil,
            parceiro_id=vinculado_id if perfil == Perfil.PARCEIRO else None,
        )
        c = TestClient(app, raise_server_exceptions=False)
        entrada = c.post("/api/sessao", json={"login": login, "senha": SENHA_PADRAO})
        assert entrada.status_code == 201, entrada.text
        abertos[perfil] = c
    abertos[None] = TestClient(app, raise_server_exceptions=False)
    yield abertos
    for c in abertos.values():
        c.close()


def _quem_abre(metodo: str, caminho: str):
    permitidos = PERMISSOES[(metodo, caminho)]
    if permitidos is PUBLICO:
        return None
    return next(p for p in PREFERENCIA if p in permitidos)


def _parametros_de_consulta(caminho: str) -> list[str]:
    operacao = app.openapi()["paths"][caminho].get("get", {})
    return [p["name"] for p in operacao.get("parameters", []) if p["in"] == "query"]


def _contagens() -> dict[str, int]:
    s = Sessao()
    try:
        return {
            "usuario": s.scalar(select(func.count()).select_from(Usuario)),
            "parceiro": s.scalar(select(func.count()).select_from(Parceiro)),
            "categoria": s.scalar(select(func.count()).select_from(Categoria)),
        }
    finally:
        s.close()


def _conferir_resposta(r, onde: str, problemas: list[str]) -> None:
    """Nenhum 500, e a saída nunca é HTML: JSON ou o CSV da exportação, com `nosniff`."""
    tipo = r.headers.get("content-type", "")
    if r.status_code >= 500:
        problemas.append(f"{onde}: {r.status_code}")
    if not tipo.startswith(("application/json", "text/csv")):
        problemas.append(f"{onde}: devolveu {tipo or 'sem tipo'}")
    if r.headers.get("x-content-type-options") != "nosniff":
        problemas.append(f"{onde}: sem nosniff")


def test_carga_de_injecao_em_todo_parametro_de_toda_rota_de_leitura(clientes):
    """RNF12 e RNF13, derivado da aplicação: cada parâmetro de consulta e cada parte
    variável do caminho de cada rota de leitura recebe cada carga, com um perfil que
    a abre. Nenhuma responde 500, toda resposta é JSON ou CSV com `nosniff`, e o
    banco continua com as mesmas linhas."""
    antes = _contagens()
    problemas: list[str] = []
    for metodo, caminho in rotas_da_aplicacao():
        if metodo != "GET":
            continue
        c = clientes[_quem_abre(metodo, caminho)]
        base = concretizar(caminho)
        for parametro in _parametros_de_consulta(caminho):
            for carga in CARGAS:
                r = c.get(base, params={parametro: carga})
                _conferir_resposta(r, f"GET {caminho}?{parametro}={carga!r}", problemas)
        # A parte variável do caminho: o id vira a carga, e o 422 também é JSON.
        if "{" in caminho:
            for carga in CARGAS:
                com_carga = caminho
                for nome in ("usuario_id", "parceiro_id", "treino_id", "execucao_id", "acao_id"):
                    com_carga = com_carga.replace("{" + nome + "}", quote(carga, safe=""))
                r = c.get(com_carga)
                _conferir_resposta(r, f"GET {com_carga}", problemas)
    assert problemas == []
    assert _contagens() == antes


# ================================================================ RNF13: onde o texto entra
@pytest.mark.parametrize("carga", CARGAS_SQL)
def test_o_login_com_carga_de_injecao_so_recusa(clientes, carga):
    c = TestClient(app, raise_server_exceptions=False)
    r = c.post("/api/sessao", json={"login": carga, "senha": carga})
    assert r.status_code in (401, 422)
    assert "gih_sessao" not in r.cookies


def test_a_busca_de_parceiros_trata_a_carga_como_texto(clientes):
    """A carga não casa com nada, e o apóstrofo de um nome de verdade continua achando
    o parceiro: a busca é um parâmetro, e não pedaço da consulta."""
    analista = clientes[Perfil.ANALISTA]
    for carga in CARGAS_SQL:
        r = analista.get("/api/parceiros", params={"busca": carga})
        assert r.status_code == 200 and r.json()["total"] == 0, carga
    achados = analista.get("/api/parceiros", params={"busca": "d'ávila"}).json()["itens"]
    assert [p["nome"] for p in achados] == ["Padaria D'Ávila"]


@pytest.mark.parametrize("carga", CARGAS)
def test_o_texto_do_usuario_e_gravado_e_devolvido_como_foi(clientes, carga):
    """RNF12 e RNF13 no cadastro: a carga vira o nome, e só o nome — gravado e
    devolvido letra por letra, em JSON. Escapá-la é trabalho da tela."""
    gestor = clientes[Perfil.GESTOR]
    antes = _contagens()
    criado = gestor.post("/api/parceiros", json={"nome": carga, "contato": carga})
    assert criado.status_code == 201, criado.text
    lido = gestor.get(f"/api/parceiros/{criado.json()['id']}")
    assert lido.json()["nome"] == carga and lido.json()["contato"] == carga
    assert lido.headers["content-type"].startswith("application/json")
    assert lido.headers["x-content-type-options"] == "nosniff"
    categoria = gestor.post("/api/categorias", json={"nome": carga})
    assert categoria.status_code == 201 and categoria.json()["nome"] == carga
    depois = _contagens()
    assert depois["parceiro"] == antes["parceiro"] + 1
    assert depois["categoria"] == antes["categoria"] + 1
    assert depois["usuario"] == antes["usuario"]


def test_o_cookie_forjado_nao_abre_nada(clientes):
    """A sessão é conferida no banco a cada requisição: um token inventado, ou o de
    outra aplicação, não passa (RNF14)."""
    for token in ("inventado", CARGAS_SQL[0], "a" * 43):
        c = TestClient(app, raise_server_exceptions=False, cookies={"gih_sessao": token})
        assert c.get("/api/sessao/atual").status_code == 401
        assert c.get("/api/parceiros").status_code == 401


# ================================================================ RNF12: a planilha
def _ler_csv(resposta) -> list[dict]:
    texto = resposta.content.decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(texto), delimiter=";"))


@pytest.mark.parametrize(
    "nome",
    [
        '=HYPERLINK("http://exemplo.invalido","clique")',
        "+1+1",
        "-2+3",
        "@SOMA(A1:A2)",
    ],
)
def test_a_exportacao_neutraliza_a_formula(clientes, nome):
    """Injeção de CSV (OWASP): o texto que começaria uma fórmula sai com um apóstrofo
    na frente, e a planilha o mostra como texto, sem executar."""
    gestor = clientes[Perfil.GESTOR]
    assert gestor.post("/api/parceiros", json={"nome": nome, "contato": nome}).status_code == 201
    linhas = _ler_csv(gestor.get("/api/parceiros/exportacao.csv"))
    linha = next(li for li in linhas if li["Parceiro"].lstrip("'") == nome)
    assert linha["Parceiro"] == f"'{nome}"
    assert linha["Contato"] == f"'{nome}"


def test_a_exportacao_nao_mexe_no_texto_comum_nem_no_numero(clientes):
    assert _texto("Padaria D'Ávila") == "Padaria D'Ávila"
    assert _texto(None) == "" and _texto("") == ""
    # A tabulação e o retorno de carro na frente: o cadastro já tira os espaços das
    # pontas, mas o texto pode chegar à exportação por outro caminho.
    assert _texto("\t=1+1") == "'\t=1+1" and _texto("\r=1+1") == "'\r=1+1"
    # A variação negativa é número de verdade: com apóstrofo, a planilha não a somaria.
    assert _numero(Decimal("-12.5")) == "-12,5"
