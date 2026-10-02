"""Testes da trilha de auditoria — histórias H18 e H89, requisitos RF06, RF08 e RF49."""
from __future__ import annotations

import csv
import io
from datetime import date, timedelta

import pytest
from sqlalchemy import event
from sqlalchemy.engine import Engine

from app import servico_auditoria
from app.auditoria import Acao
from app.modelos import Perfil
from tests.conftest import SENHA_PADRAO


@pytest.fixture
def admin(criar_usuario, autenticar, cliente):
    criar_usuario(login="chefia", perfil=Perfil.ADMINISTRADOR)
    autenticar("chefia")
    return cliente


def _acoes(resposta) -> list[str]:
    return [i["acao"] for i in resposta.json()["itens"]]


# ------------------------------------------------------------- autorização
def test_apenas_administrador_consulta(cliente, criar_usuario, autenticar):
    criar_usuario(login="comum", perfil=Perfil.GESTOR)
    autenticar("comum")

    assert cliente.get("/api/auditoria").status_code == 403


def test_sem_sessao_nao_consulta(cliente):
    assert cliente.get("/api/auditoria").status_code == 401


# ------------------------------------------------------------- o que registra
def test_login_bem_sucedido_entra_na_trilha(admin):
    r = admin.get("/api/auditoria", params={"acao": "LOGIN_SUCESSO"})

    assert r.status_code == 200
    assert r.json()["total"] >= 1


def test_login_recusado_entra_na_trilha(cliente, criar_usuario, autenticar):
    """**O caso que mais importa.**

    A auditoria grava em transação própria justamente por isto: a falha de login
    termina em 401, e se o registro participasse da mesma transação o
    `rollback` o levaria junto — a trilha só teria sucessos.
    """
    criar_usuario(login="chefia", perfil=Perfil.ADMINISTRADOR)
    cliente.post("/api/sessao", json={"login": "chefia", "senha": "senha-errada-aqui"})

    autenticar("chefia")
    r = cliente.get("/api/auditoria", params={"acao": "LOGIN_FALHA"})

    assert r.json()["total"] == 1


def test_tentativa_com_login_inexistente_tambem_e_registrada(cliente, criar_usuario, autenticar):
    criar_usuario(login="chefia", perfil=Perfil.ADMINISTRADOR)
    cliente.post("/api/sessao", json={"login": "ninguem", "senha": "chute-qualquer-1"})

    autenticar("chefia")
    r = cliente.get("/api/auditoria", params={"acao": "LOGIN_FALHA"})

    registro = r.json()["itens"][0]
    assert registro["usuario_id"] is None  # não existe usuário para apontar
    assert registro["detalhes"]["login"] == "ninguem"


def test_acesso_negado_entra_na_trilha(cliente, criar_usuario, autenticar):
    criar_usuario(login="comum", perfil=Perfil.GESTOR)
    criar_usuario(login="chefia", perfil=Perfil.ADMINISTRADOR)

    autenticar("comum")
    cliente.get("/api/usuarios")  # 403

    cliente.cookies.clear()
    autenticar("chefia")
    r = cliente.get("/api/auditoria", params={"acao": "ACESSO_NEGADO"})

    assert r.json()["total"] == 1
    assert r.json()["itens"][0]["detalhes"]["caminho"] == "/api/usuarios"


def test_alteracao_de_usuario_entra_na_trilha(admin, criar_usuario):
    alvo = criar_usuario(login="alguem", perfil=Perfil.ANALISTA)
    admin.patch(f"/api/usuarios/{alvo}", json={"perfil": "GESTOR"})

    r = admin.get("/api/auditoria", params={"acao": "PERFIL_ALTERADO"})

    detalhes = r.json()["itens"][0]["detalhes"]
    assert detalhes["de"] == "ANALISTA"
    assert detalhes["para"] == "GESTOR"


def test_trilha_nunca_guarda_senha(admin, criar_usuario):
    """RF08 deixa a trilha visível ao administrador; gravar segredo aqui seria
    transformar o registro de segurança em brecha de segurança."""
    admin.post(
        "/api/usuarios",
        json={"login": "novo", "nome": "Novo", "senha": SENHA_PADRAO, "perfil": "GESTOR"},
    )

    corpo = admin.get("/api/auditoria", params={"tamanho": 200}).text

    assert SENHA_PADRAO not in corpo
    assert "senha_hash" not in corpo
    assert "token" not in corpo


# ------------------------------------------------------------------ filtros
def test_filtra_por_autor(admin, cliente, criar_usuario, autenticar):
    outro = criar_usuario(login="segunda", perfil=Perfil.ADMINISTRADOR)
    cliente.cookies.clear()
    autenticar("segunda")

    r = cliente.get("/api/auditoria", params={"autor": outro})

    assert r.json()["total"] >= 1
    assert all(i["usuario_id"] == outro for i in r.json()["itens"])


def test_filtra_por_intervalo_de_datas(admin):
    hoje = date.today()

    de_hoje = admin.get("/api/auditoria", params={"de": hoje.isoformat(), "ate": hoje.isoformat()})
    de_ontem = admin.get(
        "/api/auditoria",
        params={
            "de": (hoje - timedelta(days=2)).isoformat(),
            "ate": (hoje - timedelta(days=1)).isoformat(),
        },
    )

    # "até hoje" precisa incluir o dia de hoje inteiro. Comparar com o início do
    # dia excluiria tudo o que acabou de acontecer — que é o erro fácil aqui.
    assert de_hoje.json()["total"] >= 1
    assert de_ontem.json()["total"] == 0


def test_pagina_os_resultados(admin, criar_usuario):
    for i in range(6):
        criar_usuario(login=f"pessoa{i}", perfil=Perfil.ANALISTA)
        admin.patch(f"/api/usuarios/{i + 2}", json={"nome": f"Nome {i}"})

    primeira = admin.get("/api/auditoria", params={"pagina": 1, "tamanho": 3})
    segunda = admin.get("/api/auditoria", params={"pagina": 2, "tamanho": 3})

    assert len(primeira.json()["itens"]) == 3
    assert primeira.json()["total"] > 3
    ids_primeira = {i["id"] for i in primeira.json()["itens"]}
    ids_segunda = {i["id"] for i in segunda.json()["itens"]}
    assert not (ids_primeira & ids_segunda)


def test_tamanho_de_pagina_tem_teto(admin):
    """Sem teto, `?tamanho=999999` devolve a tabela inteira e derruba a API."""
    assert admin.get("/api/auditoria", params={"tamanho": 10_000}).status_code == 422


def test_ordena_do_mais_recente_para_o_mais_antigo(admin, criar_usuario):
    alvo = criar_usuario(login="alguem")
    admin.patch(f"/api/usuarios/{alvo}", json={"nome": "Depois"})

    acoes = _acoes(admin.get("/api/auditoria"))

    # A investigação começa pelo que acabou de acontecer.
    assert acoes[0] == Acao.USUARIO_EDITADO
    assert acoes[-1] == Acao.LOGIN_SUCESSO


def test_lista_as_acoes_possiveis_para_o_filtro(admin):
    """Vem do enum, não de um SELECT DISTINCT: a opção precisa existir mesmo que
    nunca tenha ocorrido — que é o caso mais interessante de procurar."""
    r = admin.get("/api/auditoria/acoes")

    assert r.status_code == 200
    assert {"acao": "USUARIO_DESATIVADO", "rotulo": "Usuário desativado"} in r.json()
    assert len(r.json()) == len(Acao)


# ------------------------------------------------- a trilha como se lê (H89)
def test_toda_acao_tem_rotulo():
    """Ação nova sem frase apareceria na tela como `MENSAGENS_FALHARAM`."""
    sem_rotulo = [str(a) for a in Acao if servico_auditoria.rotulo(str(a)) == str(a)]
    assert sem_rotulo == []


def test_o_registro_traz_o_autor_o_rotulo_e_o_resumo(admin, criar_usuario):
    alvo = criar_usuario(login="alguem", perfil=Perfil.ANALISTA)
    admin.patch(f"/api/usuarios/{alvo}", json={"perfil": "GESTOR"})

    item = admin.get("/api/auditoria", params={"acao": "PERFIL_ALTERADO"}).json()["itens"][0]

    assert (item["autor"], item["autor_login"]) == ("Chefia", "chefia")
    assert item["rotulo"] == "Perfil de usuário alterado"
    assert item["resumo"] == "alguem: de ANALISTA para GESTOR"
    # O código e os parâmetros crus continuam ali, para investigar.
    assert item["acao"] == "PERFIL_ALTERADO" and item["detalhes"]["para"] == "GESTOR"


def test_evento_sem_autor_continua_na_lista(cliente, criar_usuario, autenticar):
    """UC14-A1: a entrada recusada com login que não existe não tem usuário para
    apontar. Uma junção interna com `usuario` a tiraria da trilha."""
    cliente.post("/api/sessao", json={"login": "fantasma", "senha": SENHA_PADRAO})
    criar_usuario(login="chefia", perfil=Perfil.ADMINISTRADOR)
    autenticar("chefia")

    item = cliente.get("/api/auditoria", params={"acao": "LOGIN_FALHA"}).json()["itens"][0]

    assert item["autor"] is None and item["autor_login"] is None
    assert item["resumo"] == "login tentado: fantasma"


def test_busca_no_que_foi_gravado_e_em_quem_fez(admin, criar_usuario):
    alvo = criar_usuario(login="alguem", perfil=Perfil.ANALISTA)
    admin.patch(f"/api/usuarios/{alvo}", json={"perfil": "GESTOR"})

    pelo_alvo = admin.get("/api/auditoria", params={"busca": "ALGUEM"}).json()
    assert pelo_alvo["total"] == 1 and pelo_alvo["itens"][0]["acao"] == "PERFIL_ALTERADO"

    # Pelo autor: tudo o que a chefia fez, da entrada à alteração.
    pelo_autor = admin.get("/api/auditoria", params={"busca": "chefia"}).json()
    assert {i["acao"] for i in pelo_autor["itens"]} == {"LOGIN_SUCESSO", "PERFIL_ALTERADO"}


def test_busca_trata_curinga_como_texto(admin):
    """`%` digitado é o caractere, e não "qualquer coisa": sem o escape, a busca
    devolveria a trilha inteira."""
    assert admin.get("/api/auditoria", params={"busca": "%"}).json()["total"] == 0
    assert admin.get("/api/auditoria", params={"busca": "_"}).json()["total"] == 0


def test_a_busca_combina_com_os_outros_filtros(admin, criar_usuario):
    alvo = criar_usuario(login="alguem", perfil=Perfil.ANALISTA)
    admin.patch(f"/api/usuarios/{alvo}", json={"perfil": "GESTOR"})
    admin.patch(f"/api/usuarios/{alvo}", json={"ativo": False})

    r = admin.get("/api/auditoria", params={"busca": "alguem", "acao": "USUARIO_DESATIVADO"})

    assert _acoes(r) == ["USUARIO_DESATIVADO"]


def test_o_autor_nao_custa_uma_consulta_por_linha(admin, criar_usuario):
    for n in range(20):
        pessoa = criar_usuario(login=f"pessoa{n:02d}")
        admin.patch(f"/api/usuarios/{pessoa}", json={"nome": f"Pessoa {n}"})
    consultas: list[str] = []

    def anotar(_conexao, _cursor, sql, *_):
        consultas.append(sql)

    event.listen(Engine, "before_cursor_execute", anotar)
    try:
        r = admin.get("/api/auditoria", params={"tamanho": 50})
    finally:
        # No `finally`: um ouvinte vazado contaria as consultas dos testes seguintes.
        event.remove(Engine, "before_cursor_execute", anotar)

    assert len(r.json()["itens"]) >= 20
    na_trilha = [c for c in consultas if "auditoria" in c.lower()]
    assert len(na_trilha) == 2, f"{len(na_trilha)} consultas na trilha: a contagem e a página"


@pytest.mark.parametrize(
    ("acao", "detalhes", "esperado"),
    [
        (Acao.LOGIN_SUCESSO, None, ""),
        (Acao.PARCEIRO_CRIADO, {"alvo": 7, "nome": "Padaria Sol"}, "Padaria Sol"),
        (
            Acao.PARCEIRO_EDITADO,
            {"alvo": 7, "nome": "Padaria Sol", "nome_de": "Padaria Lua",
             "status_de": "ATIVO", "status_para": "ATIVO"},
            "Padaria Sol: nome de Padaria Lua para Padaria Sol",
        ),
        (
            Acao.PARCEIRO_EDITADO,
            {"alvo": 7, "nome": "Padaria Sol", "nome_de": "Padaria Sol",
             "status_de": "ATIVO", "status_para": "SUSPENSO", "contato_alterado": True},
            "Padaria Sol: status de ATIVO para SUSPENSO; contato alterado",
        ),
        (
            Acao.PARCEIRO_CLASSIFICADO,
            {"alvo": 7, "nome": "Padaria Sol", "de": 2, "para": 5,
             "de_nome": None, "para_nome": "Padaria"},
            "Padaria Sol: categoria de sem categoria para Padaria",
        ),
        # Registro de antes da H90: só os identificadores, que não se leem.
        (Acao.PARCEIRO_CLASSIFICADO, {"alvo": 7, "nome": "Padaria Sol", "de": 2, "para": 5},
         "Padaria Sol"),
        (
            Acao.SEGMENTACAO_CONFIGURADA,
            {"anterior": {"top_n": 15, "periodos_tendencia": 2}, "novo": {"top_n": 20,
             "periodos_tendencia": 2}},
            "Top N de 15 para 20",
        ),
        (
            Acao.IMPORTACAO_REALIZADA,
            {"periodo": "2026-09-14 a 2026-09-20", "gravados": 500, "rejeitados": 3,
             "parceiros_criados": 11},
            "período 2026-09-14 a 2026-09-20: 500 registro(s) gravado(s), 3 rejeitado(s), "
            "11 parceiro(s) novo(s)",
        ),
        (
            Acao.OTIMIZACAO_EXECUTADA,
            {"execucao": 9, "modo": "GPU", "viavel": True, "custo_total": "5000.00"},
            "execução 9, modo GPU, plano com custo de R$ 5000.00",
        ),
        (
            Acao.OTIMIZACAO_EXECUTADA,
            {"execucao": 10, "modo": "SERIAL", "viavel": False, "restricao_violada": "orcamento"},
            "execução 10, modo SERIAL, sem plano viável (orcamento)",
        ),
        (Acao.MENSAGEM_REJEITADA, {"mensagem": 4, "motivo": "tom frio"}, "mensagem 4: tom frio"),
        (Acao.ACESSO_NEGADO, {"metodo": "GET", "caminho": "/api/usuarios", "perfil": "GESTOR"},
         "GET /api/usuarios, perfil GESTOR"),
    ],
    ids=["sem-detalhes", "criado", "editado", "status-e-contato", "classificado",
         "classificado-antigo", "limiares", "importacao", "plano", "inviavel", "rejeitada",
         "negado"],
)
def test_o_resumo_so_reescreve_o_que_foi_gravado(acao, detalhes, esperado):
    assert servico_auditoria.resumo(str(acao), detalhes) == esperado


def test_resumo_de_registro_antigo_ou_desconhecido_nao_quebra():
    """Registro de antes de um campo existir, ou de ação que saiu do enum: a
    frase some, e o detalhe cru continua na tela."""
    assert servico_auditoria.resumo("ACAO_QUE_NAO_EXISTE_MAIS", {"x": 1}) == ""
    assert servico_auditoria.rotulo("ACAO_QUE_NAO_EXISTE_MAIS") == "ACAO_QUE_NAO_EXISTE_MAIS"
    assert servico_auditoria.resumo("USUARIO_CRIADO", {}) == ""


# ----------------------------------------------------------- exportação (RF49)
def test_exporta_o_recorte_da_tela_em_csv(admin, criar_usuario):
    alvo = criar_usuario(login="alguem", perfil=Perfil.ANALISTA)
    admin.patch(f"/api/usuarios/{alvo}", json={"perfil": "GESTOR"})

    r = admin.get("/api/auditoria/exportacao.csv", params={"acao": "PERFIL_ALTERADO"})

    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    linhas = list(csv.reader(io.StringIO(r.text.lstrip("﻿")), delimiter=";"))
    assert linhas[0] == ["Quando", "Autor", "Login", "Ação", "O que aconteceu", "Origem"]
    assert len(linhas) == 2  # o cabeçalho e a única alteração de perfil
    assert linhas[1][1:5] == [
        "Chefia", "chefia", "Perfil de usuário alterado", "alguem: de ANALISTA para GESTOR",
    ]


def test_a_exportacao_e_so_do_administrador(cliente, criar_usuario, autenticar):
    criar_usuario(login="comum", perfil=Perfil.GESTOR)
    autenticar("comum")

    assert cliente.get("/api/auditoria/exportacao.csv").status_code == 403
