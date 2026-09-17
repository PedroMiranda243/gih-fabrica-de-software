"""Cobertura sistemática da autorização — história H17, requisito RNF14.

Os testes das outras histórias verificam a permissão dos endpoints que elas
tocam. Este verifica **todos**, contra **todos** os perfis, a partir da matriz de
`docs/03-casos-de-uso.md` — e a propriedade que mais importa não é nenhuma
asserção individual:

    Endpoint novo sem permissão declarada **reprova** o teste.

Sem isso, a cobertura envelhece em silêncio: alguém acrescenta uma rota daqui a
seis semanas, esquece a dependência de perfil, e nenhum teste reclama porque
nenhum teste sabia que a rota existia. É o modo de falha que o RNF14 existe para
evitar, e ele não se resolve escrevendo mais asserções — se resolve fazendo o
conjunto de rotas ser *derivado da aplicação*, não escrito à mão.
"""
from __future__ import annotations

import pytest
from fastapi.routing import APIRoute

from app.main import app
from app.modelos import Perfil

TODOS = frozenset(Perfil)
NENHUM: frozenset[Perfil] = frozenset()

# ---------------------------------------------------------------------------
# A matriz. Transcrita da tabela de permissões de `docs/03-casos-de-uso.md`,
# **não** lida do código — copiar do código provaria apenas que o código é igual
# a si mesmo.
#
# `PUBLICO` é o conjunto vazio com significado próprio: não exige sessão alguma.
# ---------------------------------------------------------------------------
PUBLICO = "publico"

PERMISSOES: dict[tuple[str, str], object] = {
    # Sistema
    ("GET", "/api/health"): PUBLICO,
    # UC01 — Autenticar: todos os perfis
    ("POST", "/api/sessao"): PUBLICO,
    ("DELETE", "/api/sessao"): TODOS,
    ("GET", "/api/sessao/atual"): TODOS,
    ("POST", "/api/sessao/senha"): TODOS,
    # UC02 — Gerenciar usuários: só Administrador
    ("GET", "/api/usuarios"): {Perfil.ADMINISTRADOR},
    ("POST", "/api/usuarios"): {Perfil.ADMINISTRADOR},
    ("GET", "/api/usuarios/{usuario_id}"): {Perfil.ADMINISTRADOR},
    ("PATCH", "/api/usuarios/{usuario_id}"): {Perfil.ADMINISTRADOR},
    # UC04 — Gerenciar parceiros e categorias: Gestor e Analista
    ("GET", "/api/parceiros"): {Perfil.GESTOR, Perfil.ANALISTA},
    ("POST", "/api/parceiros"): {Perfil.GESTOR, Perfil.ANALISTA},
    ("GET", "/api/parceiros/{parceiro_id}"): {Perfil.GESTOR, Perfil.ANALISTA},
    ("PATCH", "/api/parceiros/{parceiro_id}"): {Perfil.GESTOR, Perfil.ANALISTA},
    ("DELETE", "/api/parceiros/{parceiro_id}"): {Perfil.GESTOR, Perfil.ANALISTA},
    ("GET", "/api/categorias"): {Perfil.GESTOR, Perfil.ANALISTA},
    ("POST", "/api/categorias"): {Perfil.GESTOR, Perfil.ANALISTA},
    # UC03 — Importar relatório: Gestor e Analista
    ("POST", "/api/importacoes"): {Perfil.GESTOR, Perfil.ANALISTA},
    ("POST", "/api/importacoes/previa"): {Perfil.GESTOR, Perfil.ANALISTA},
    ("GET", "/api/importacoes"): {Perfil.GESTOR, Perfil.ANALISTA},
    # UC14 — Auditar ações: só Administrador
    ("GET", "/api/auditoria"): {Perfil.ADMINISTRADOR},
    ("GET", "/api/auditoria/acoes"): {Perfil.ADMINISTRADOR},
}

# Rotas que o FastAPI cria sozinho e que não são superfície da aplicação.
IGNORADAS = {"/api/openapi.json", "/api/docs", "/api/docs/oauth2-redirect", "/api/redoc"}

# Valores de caminho para as rotas parametrizadas. O id não precisa existir: um
# 404 já prova que a autorização deixou passar, que é o que se está medindo.
PARAMETROS = {"usuario_id": "1", "parceiro_id": "1"}


def rotas_da_aplicacao() -> list[tuple[str, str]]:
    """Todo par (método, caminho) que a aplicação expõe, lido dela mesma."""
    pares = []
    for rota in app.routes:
        if not isinstance(rota, APIRoute) or rota.path in IGNORADAS:
            continue
        for metodo in sorted(rota.methods - {"HEAD", "OPTIONS"}):
            pares.append((metodo, rota.path))
    return sorted(pares)


def concretizar(caminho: str) -> str:
    for nome, valor in PARAMETROS.items():
        caminho = caminho.replace("{" + nome + "}", valor)
    return caminho


# ---------------------------------------------------------------------------
# O teste que impede a cobertura de envelhecer
# ---------------------------------------------------------------------------
def test_toda_rota_tem_permissao_declarada():
    """Este é o teste que sustenta todos os outros deste arquivo.

    Se ele falhar, **não declare a permissão só para passar**: pergunte qual é o
    perfil certo, confira a matriz de `docs/03-casos-de-uso.md`, e só então
    acrescente a linha aqui **e** a dependência na rota.
    """
    declaradas = set(PERMISSOES)
    existentes = set(rotas_da_aplicacao())

    faltando = existentes - declaradas
    sobrando = declaradas - existentes

    assert not faltando, (
        "Rota sem permissão declarada em PERMISSOES: "
        + ", ".join(f"{m} {c}" for m, c in sorted(faltando))
    )
    assert not sobrando, (
        "PERMISSOES declara rota que não existe mais: "
        + ", ".join(f"{m} {c}" for m, c in sorted(sobrando))
    )


# ---------------------------------------------------------------------------
# Sem sessão
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(("metodo", "caminho"), rotas_da_aplicacao())
def test_sem_sessao_o_protegido_responde_401(cliente, metodo, caminho):
    permitidos = PERMISSOES.get((metodo, caminho))
    if permitidos is None:
        pytest.skip("rota sem permissão declarada — ver test_toda_rota_tem_permissao_declarada")

    r = cliente.request(metodo, concretizar(caminho), json={})

    if permitidos is PUBLICO:
        assert r.status_code != 401, f"{metodo} {caminho} deveria ser público"
    else:
        assert r.status_code == 401, (
            f"{metodo} {caminho} respondeu {r.status_code} sem sessão — "
            "endpoint protegido precisa recusar antes de qualquer outra validação"
        )


# ---------------------------------------------------------------------------
# Com sessão, perfil a perfil
# ---------------------------------------------------------------------------
def _casos():
    for metodo, caminho in rotas_da_aplicacao():
        # Rota sem declaração é pulada aqui de propósito: quem reclama dela é
        # `test_toda_rota_tem_permissao_declarada`, com a mensagem que diz o que
        # fazer. Buscar direto no dicionário estouraria um KeyError na **coleta**
        # e derrubaria o arquivo inteiro, escondendo o diagnóstico.
        permitidos = PERMISSOES.get((metodo, caminho))
        if permitidos is None or permitidos is PUBLICO:
            continue
        for perfil in Perfil:
            yield metodo, caminho, perfil, perfil in permitidos


@pytest.mark.parametrize(
    ("metodo", "caminho", "perfil", "permitido"),
    [pytest.param(*c, id=f"{c[0]}-{c[1]}-{c[2]}") for c in _casos()],
)
def test_cada_endpoint_contra_cada_perfil(
    cliente, criar_usuario, autenticar, metodo, caminho, perfil, permitido
):
    """A negação esperada, endpoint por endpoint, perfil por perfil (RNF14).

    Para o permitido não se exige 200: o corpo vazio de um POST dá 422 e um id
    inexistente dá 404. O que se mede é **só** se a autorização deixou passar —
    e é exatamente isso que 403 responderia em caso contrário.
    """
    # O perfil Parceiro exige vínculo, garantido por CHECK no banco.
    parceiro_id = None
    if perfil == Perfil.PARCEIRO:
        parceiro_id = _parceiro_de_teste()

    criar_usuario(login="sujeito", perfil=perfil, parceiro_id=parceiro_id)
    autenticar("sujeito")

    r = cliente.request(metodo, concretizar(caminho), json={})

    if permitido:
        assert r.status_code != 403, (
            f"{metodo} {caminho} negou o perfil {perfil}, que a matriz permite"
        )
    else:
        assert r.status_code == 403, (
            f"{metodo} {caminho} respondeu {r.status_code} para o perfil {perfil}, "
            "que a matriz não permite"
        )


def _parceiro_de_teste() -> int:
    from app.db import Sessao
    from app.modelos import Parceiro

    s = Sessao()
    try:
        p = Parceiro(nome="Parceiro de teste")
        s.add(p)
        s.commit()
        return p.id
    finally:
        s.close()
