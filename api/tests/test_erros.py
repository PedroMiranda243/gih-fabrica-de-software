"""Testes das respostas de erro — RNF18, RNF19 e RNF20.

Duas promessas: o usuário lê o erro em português, dizendo o que fazer; e uma
falha inesperada não mostra nada do servidor além de um identificador que liga a
reclamação ao registro no log.
"""
from __future__ import annotations

import logging
import re

import pytest

from app.erros import GENERICA, mensagem_de
from app.modelos import Perfil

# As palavras das frases do Pydantic: "Input should be…", "Field required".
EM_INGLES = re.compile(r"\b(Input|should|Field|required|valid)\b")


@pytest.fixture
def analista(criar_usuario, autenticar, cliente):
    criar_usuario(login="analista", perfil=Perfil.ANALISTA)
    autenticar("analista")
    return cliente


def mensagens(resposta) -> dict[str, str]:
    assert resposta.status_code == 422, resposta.text
    return {c["campo"]: c["mensagem"] for c in resposta.json()["campos"]}


# ============================================================ RNF20 · idioma
def test_opcao_fora_da_lista_diz_quais_sao_as_opcoes(analista):
    """Respondia "Input should be 'ATIVO', 'PROSPECCAO' or 'INATIVO'"."""
    r = analista.post("/api/parceiros", json={"nome": "Nome Bom", "status": "XYZ"})

    assert mensagens(r)["status"] == "Escolha uma destas opções: ATIVO, PROSPECCAO ou INATIVO."


def test_ordenacao_desconhecida_responde_em_portugues(analista):
    """A ordenação vem da URL, e um link editado à mão chega aqui."""
    r = analista.get("/api/parceiros?ordenar_por=xyz")

    assert mensagens(r)["ordenar_por"].startswith("Escolha uma destas opções: nome, faturamento")


def test_filtro_de_situacao_invalido_responde_em_portugues(analista):
    """Respondia "Input should be a valid boolean, unable to interpret input"."""
    r = analista.get("/api/parceiros?ativo=talvez")

    assert mensagens(r)["ativo"] == "Informe verdadeiro ou falso."


def test_numero_com_casas_decimais_onde_se_espera_inteiro(analista):
    r = analista.post("/api/parceiros", json={"nome": "Nome Bom", "categoria_id": 1.5})

    assert mensagens(r)["categoria_id"] == "Informe um número inteiro, sem casas decimais."


@pytest.mark.parametrize(
    ("metodo", "caminho", "corpo"),
    [
        ("post", "/api/parceiros", {"nome": 12, "status": "XYZ", "contato": ["a"]}),
        ("post", "/api/parceiros", {}),
        ("patch", "/api/parceiros/1", {"ativo": "talvez", "categoria_id": 1.5}),
        ("get", "/api/parceiros?pagina=0&tamanho=abc&segmento=XYZ&descendente=talvez", None),
        ("post", "/api/importacoes", {"texto": 5, "periodo_inicio": "31/12/2026"}),
    ],
)
def test_nenhuma_mensagem_de_campo_sai_em_ingles(analista, metodo, caminho, corpo):
    """A varredura que teria achado o defeito: várias entradas ruins de uma vez,
    e nenhuma mensagem com a frase do Pydantic."""
    argumentos = {"json": corpo} if corpo is not None else {}
    r = getattr(analista, metodo)(caminho, **argumentos)

    for campo, mensagem in mensagens(r).items():
        assert not EM_INGLES.search(mensagem), (campo, mensagem)


def test_tipo_ainda_sem_traducao_nao_vaza_a_frase_em_ingles():
    erro = {"type": "tipo_que_ainda_nao_existe", "msg": "Input should be something", "loc": ()}

    assert mensagem_de(erro) == GENERICA



@pytest.mark.parametrize(
    ("erro", "esperada"),
    [
        ({"type": "greater_than", "ctx": {"gt": 0}}, "Use um valor maior que 0."),
        ({"type": "less_than", "ctx": {"lt": 1}}, "Use um valor menor que 1."),
        (
            {"type": "decimal_max_digits", "ctx": {"max_digits": 12}},
            "Número grande demais: use no máximo 12 dígitos.",
        ),
        (
            {"type": "decimal_max_places", "ctx": {"decimal_places": 2}},
            "Use no máximo 2 casas decimais.",
        ),
    ],
    ids=["maior-que", "menor-que", "digitos", "casas-decimais"],
)
def test_limite_estrito_e_decimal_dizem_o_limite(erro, esperada):
    """Achados ao transcrever as validações da campanha: caíam na frase genérica."""
    assert mensagem_de({"loc": (), "msg": "", **erro}) == esperada


def test_orcamento_zero_na_campanha_diz_o_minimo(criar_usuario, autenticar, cliente):
    """O caso que achou a lacuna: `orcamento` é `gt=0`, e respondia "Valor inválido"."""
    criar_usuario(login="gestora", perfil=Perfil.GESTOR)
    autenticar("gestora")

    r = cliente.post(
        "/api/otimizacoes",
        json={
            "orcamento": "0",
            "maximo_acoes": 10,
            "aplicacao_inicio": "2026-10-05",
            "aplicacao_fim": "2026-10-11",
        },
    )

    assert r.status_code == 422
    assert "Use um valor maior que 0." in r.text


# ============================================ RNF18 e RNF19 · falha inesperada
@pytest.fixture
def rota_que_falha():
    """Uma rota que quebra, registrada só durante o teste.

    Não há como provocar um 500 de verdade sem um defeito, e plantar um defeito
    no código de produção para testá-lo seria pior que o defeito.
    """
    from app.main import app

    async def falhar():
        raise RuntimeError("detalhe interno que não pode chegar ao cliente: senha=abc")

    app.add_api_route("/api/teste-de-falha", falhar, methods=["GET"])
    yield "/api/teste-de-falha"
    app.router.routes[:] = [
        r for r in app.router.routes if getattr(r, "path", None) != "/api/teste-de-falha"
    ]


def test_falha_inesperada_responde_generico_com_correlacao(cliente, rota_que_falha, caplog):
    with caplog.at_level(logging.ERROR, logger="gih"):
        r = cliente.get(rota_que_falha)

    assert r.status_code == 500
    corpo = r.json()
    assert set(corpo) == {"erro", "correlacao"}
    assert corpo["erro"] == "Não foi possível concluir a operação."
    assert re.fullmatch(r"[0-9a-f]{12}", corpo["correlacao"])

    # RNF18: nada do servidor na resposta — nem a pilha, nem a mensagem da exceção.
    assert "Traceback" not in r.text
    assert "detalhe interno" not in r.text and "RuntimeError" not in r.text

    # RNF19: o mesmo identificador no log, junto do detalhe que ficou de fora.
    registro = next(x for x in caplog.records if corpo["correlacao"] in x.getMessage())
    assert rota_que_falha in registro.getMessage()
    assert registro.exc_info and "detalhe interno" in str(registro.exc_info[1])
