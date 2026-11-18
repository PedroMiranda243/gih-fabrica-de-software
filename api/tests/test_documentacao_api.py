"""A documentação da API está completa, certa e em dia (H107).

`app/documentacao_api.py` completa o OpenAPI que o FastAPI gera; este teste é o
que impede uma rota nova de entrar sem documentação, e um exemplo de entrar
errado. Para cada uma das operações:

- resumo escrito à mão (o FastAPI geraria "Listar" a partir do nome da função) e
  descrição, que começa por quem pode chamar;
- o cadeado da sessão e o 401 em toda rota que exige sessão, e o 403 em toda que
  exige um perfil — lidos da própria rota, e não de uma lista copiada;
- o 422 no formato que a API devolve (`{erro, campos}`), e não no do FastAPI;
- descrição em todo parâmetro, exemplo em todo corpo JSON — e o exemplo passa no
  próprio esquema da rota;
- o `text/csv` nas exportações.

E os arquivos exportados — `docs/api/openapi.json` e `docs/13-api.md` — são os
que a API gera agora. Mudou uma rota? `python scripts/exportar_api.py`.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from fastapi.routing import APIRoute

from app.dependencias import perfis_da_rota
from app.documentacao_api import DESCRICOES, ERROS, EXEMPLOS, PUBLICAS, RESUMOS
from app.main import app
from tests.conftest import SENHA_PADRAO

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))

import exportar_api  # noqa: E402

ESPEC = app.openapi()
OPERACOES = [
    (metodo, rota.path, rota)
    for rota in app.routes
    if isinstance(rota, APIRoute)
    for metodo in sorted(rota.methods - {"HEAD"})
]
IDS = [f"{m} {p}" for m, p, _ in OPERACOES]


def _op(metodo: str, caminho: str) -> dict:
    return ESPEC["paths"][caminho][metodo.lower()]


def test_toda_operacao_tem_o_seu_resumo_e_nenhum_resumo_sobra():
    rotas = {(m, p) for m, p, _ in OPERACOES}
    assert set(RESUMOS) == rotas, {
        "rotas sem resumo": sorted(rotas - set(RESUMOS)),
        "resumos sem rota": sorted(set(RESUMOS) - rotas),
    }
    for tabela in (DESCRICOES, ERROS, EXEMPLOS):
        assert set(tabela) <= rotas, sorted(set(tabela) - rotas)


@pytest.mark.parametrize(("metodo", "caminho", "rota"), OPERACOES, ids=IDS)
def test_cada_operacao_diz_o_que_faz_e_quem_pode(metodo, caminho, rota):
    op = _op(metodo, caminho)
    assert op["summary"] == RESUMOS[(metodo, caminho)]
    quem, _, resto = op["description"].partition("\n\n")
    assert quem.startswith("**Quem pode:**")
    assert resto.strip(), "sem descrição além de quem pode"


@pytest.mark.parametrize(("metodo", "caminho", "rota"), OPERACOES, ids=IDS)
def test_a_sessao_e_o_perfil_estao_no_documento(metodo, caminho, rota):
    op = _op(metodo, caminho)
    respostas = op["responses"]
    if (metodo, caminho) in PUBLICAS:
        assert "security" not in op
        return
    assert op["security"] == [{"sessao": []}]
    assert "401" in respostas
    if perfis_da_rota(rota):
        assert "403" in respostas


@pytest.mark.parametrize(("metodo", "caminho", "rota"), OPERACOES, ids=IDS)
def test_parametros_corpo_e_respostas_estao_documentados(metodo, caminho, rota):
    op = _op(metodo, caminho)
    sem_descricao = [p["name"] for p in op.get("parameters", []) if not p.get("description")]
    assert not sem_descricao, f"parâmetros sem descrição: {sem_descricao}"
    assert all(p["in"] != "cookie" for p in op.get("parameters", []))

    json_do_corpo = op.get("requestBody", {}).get("content", {}).get("application/json")
    if json_do_corpo is not None:
        assert "example" in json_do_corpo, "corpo JSON sem exemplo"
        # O exemplo passa no próprio esquema da rota: exemplo errado é pior que nenhum.
        rota.body_field.type_.model_validate(json_do_corpo["example"])

    respostas = op["responses"]
    if "422" in respostas:
        esquema = respostas["422"]["content"]["application/json"]["schema"]
        assert esquema == {"$ref": "#/components/schemas/ErroDeCampos"}
    for codigo in ERROS.get((metodo, caminho), ()):
        assert str(codigo) in respostas
    if caminho.endswith("exportacao.csv"):
        sucesso = [r for c, r in respostas.items() if c.startswith("2")]
        assert all("text/csv" in r["content"] for r in sucesso)


def test_o_documento_nao_anuncia_o_422_do_fastapi():
    esquemas = ESPEC["components"]["schemas"]
    assert "HTTPValidationError" not in esquemas
    assert {"ErroDeCampos", "ErroSimples", "ErroComAjuda", "ErroInterno"} <= set(esquemas)
    assert ESPEC["components"]["securitySchemes"]["sessao"]["in"] == "cookie"


def _exemplo(metodo: str, caminho: str, codigo: int) -> str:
    return _op(metodo, caminho)["responses"][str(codigo)]["content"]["application/json"]["example"][
        "detail"
    ]


def test_o_exemplo_de_cada_erro_e_o_que_a_api_responde(cliente, criar_usuario):
    """O 401, o 403 e o 429 têm o mesmo esquema; o exemplo de cada um é a resposta dele.

    O 401 mostrava "Seu perfil não permite esta operação." — o texto do 403.
    """
    from app.config import config
    from app.modelos import Perfil

    sem_sessao = cliente.get("/api/parceiros")
    assert sem_sessao.json()["detail"] == _exemplo("GET", "/api/parceiros", 401)

    criar_usuario(login="analista", perfil=Perfil.ANALISTA)
    errada = cliente.post("/api/sessao", json={"login": "analista", "senha": "errada-mesmo"})
    assert errada.json()["detail"] == _exemplo("POST", "/api/sessao", 401)
    entrou = cliente.post("/api/sessao", json={"login": "analista", "senha": SENHA_PADRAO})
    assert entrou.status_code == 201
    sem_perfil = cliente.get("/api/usuarios")
    assert sem_perfil.status_code == 403
    assert sem_perfil.json()["detail"] == _exemplo("GET", "/api/usuarios", 403)
    cliente.delete("/api/sessao")

    for _ in range(config.login_falhas_para_bloquear):
        cliente.post("/api/sessao", json={"login": "analista", "senha": "errada-mesmo"})
    bloqueada = cliente.post("/api/sessao", json={"login": "analista", "senha": SENHA_PADRAO})
    assert bloqueada.status_code == 429
    assert bloqueada.json()["detail"] == _exemplo("POST", "/api/sessao", 429)


def test_os_enderecos_da_documentacao_que_o_readme_da_respondem(cliente):
    """O README dá `/api/docs` e `/api/redoc`; o ReDoc ficou em `/redoc` até o #286."""
    for caminho in ("/api/docs", "/api/redoc"):
        r = cliente.get(caminho)
        assert r.status_code == 200 and "text/html" in r.headers["content-type"], caminho
        assert "/api/openapi.json" in r.text, f"{caminho} não lê o documento da API"
    assert cliente.get("/api/openapi.json").status_code == 200
    # Fora de /api, a borda remota entrega a interface: documentação ali escaparia do bloqueio.
    assert cliente.get("/redoc").status_code == 404
    assert cliente.get("/docs").status_code == 404


def test_os_arquivos_exportados_sao_os_que_a_api_gera_agora():
    """`docs/api/openapi.json` e `docs/13-api.md`: rode `scripts/exportar_api.py` se falhar."""
    exportado = json.loads((RAIZ / "docs" / "api" / "openapi.json").read_text(encoding="utf-8"))
    assert exportado == ESPEC, "docs/api/openapi.json está velho: rode scripts/exportar_api.py"
    referencia = (RAIZ / "docs" / "13-api.md").read_text(encoding="utf-8").replace("\r\n", "\n")
    assert referencia == exportar_api.markdown(ESPEC), "docs/13-api.md está velho"
