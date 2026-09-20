"""Testes do cadastro de parceiros — história H26, requisito RF14, caso de uso UC04.

O parceiro é a entidade central do produto, e é o CRUD que a terceira entrega da
disciplina avalia. Por isso as quatro operações têm teste, e a exclusão tem dois:
o caminho em que ela acontece e o caminho em que ela é recusada.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.db import Sessao
from app.modelos import (
    Categoria,
    Importacao,
    Metrica,
    OrigemCategoria,
    OrigemImportacao,
    Parceiro,
    Perfil,
    Periodo,
    StatusComercial,
)


def _itens(resposta) -> list[dict]:
    """A lista dentro da página.

    A H36 trocou a resposta de lista para página: `{itens, total, pagina,
    tamanho}`. Passar por aqui deixa o teste falar do que ele testa, em vez de
    repetir a forma do envelope em trinta lugares.
    """
    return resposta.json()["itens"]


@pytest.fixture
def analista(criar_usuario, autenticar, cliente):
    """Gestor e Analista são quem gerencia parceiros (UC04)."""
    criar_usuario(login="analista", perfil=Perfil.ANALISTA)
    autenticar("analista")
    return cliente


@pytest.fixture
def categoria() -> int:
    s = Sessao()
    try:
        c = Categoria(nome="Restaurante", ativa=True)
        s.add(c)
        s.commit()
        return c.id
    finally:
        s.close()


def novo(**campos) -> dict:
    return {"nome": "Comércio Alfa", **campos}


def criar_parceiro_no_banco(nome: str = "Comércio Alfa", **campos) -> int:
    """Cria direto no banco, sem passar pela API.

    Preparar o cenário pela própria API tornaria cada teste dependente do
    endpoint de criação — um defeito ali reprovaria testes que não têm nada a
    ver com isso.
    """
    s = Sessao()
    try:
        p = Parceiro(nome=nome, **campos)
        s.add(p)
        s.commit()
        return p.id
    finally:
        s.close()


def dar_historico(parceiro_id: int, usuario_id: int) -> None:
    """Amarra uma métrica ao parceiro, que é o que impede a exclusão."""
    s = Sessao()
    try:
        periodo = Periodo(data_inicio=date(2026, 9, 7), data_fim=date(2026, 9, 13))
        s.add(periodo)
        s.flush()
        importacao = Importacao(
            periodo_id=periodo.id,
            usuario_id=usuario_id,
            origem=OrigemImportacao.TEXTO,
            total_gravado=1,
            total_rejeitado=0,
        )
        s.add(importacao)
        s.flush()
        s.add(
            Metrica(
                parceiro_id=parceiro_id,
                periodo_id=periodo.id,
                importacao_id=importacao.id,
                faturamento=Decimal("1000.00"),
                pedidos=10,
            )
        )
        s.commit()
    finally:
        s.close()


# ========================================================== autorização
def test_sem_sessao_nao_lista(cliente):
    assert cliente.get("/api/parceiros").status_code == 401


@pytest.mark.parametrize("perfil", [Perfil.ADMINISTRADOR])
def test_perfil_sem_permissao_recebe_403(cliente, criar_usuario, autenticar, perfil):
    """UC04 não é do Administrador. A barreira é o servidor, não a interface."""
    criar_usuario(login="chefia", perfil=perfil)
    autenticar("chefia")

    assert cliente.get("/api/parceiros").status_code == 403
    assert cliente.post("/api/parceiros", json=novo()).status_code == 403


# =============================================================== criar
def test_cadastra_parceiro(analista):
    r = analista.post("/api/parceiros", json=novo(contato="contato@exemplo.test"))

    assert r.status_code == 201, r.text
    corpo = r.json()
    assert corpo["nome"] == "Comércio Alfa"
    assert corpo["ativo"] is True
    assert corpo["status"] == "ATIVO"
    assert corpo["categoria"] is None
    assert corpo["origem_categoria"] is None


def test_cadastro_com_categoria_marca_origem_manual(analista, categoria):
    """RN05 — categoria escolhida por uma pessoa é categoria confirmada.

    O cliente não informa a origem: quem cadastra pela API é alguém decidindo, e
    deixar o campo aberto permitiria marcar como confirmada uma classificação
    que ninguém confirmou.
    """
    r = analista.post("/api/parceiros", json=novo(categoria_id=categoria))

    assert r.status_code == 201
    assert r.json()["categoria"]["nome"] == "Restaurante"
    assert r.json()["origem_categoria"] == "MANUAL"


def test_nome_repetido_e_recusado(analista):
    analista.post("/api/parceiros", json=novo())

    r = analista.post("/api/parceiros", json=novo())

    assert r.status_code == 409
    assert "Comércio Alfa" in r.json()["detail"]


def test_nome_curto_demais_e_recusado(analista):
    assert analista.post("/api/parceiros", json={"nome": "A"}).status_code == 422


# ============================================================ consultar
def test_obtem_por_id(analista):
    alvo = analista.post("/api/parceiros", json=novo()).json()["id"]

    r = analista.get(f"/api/parceiros/{alvo}")

    assert r.status_code == 200
    assert r.json()["id"] == alvo


def test_inexistente_da_404(analista):
    assert analista.get("/api/parceiros/9999").status_code == 404


def test_lista_ordenada_por_nome(analista):
    for nome in ("Comércio Gama", "Comércio Alfa", "Comércio Beta"):
        analista.post("/api/parceiros", json={"nome": nome})

    nomes = [p["nome"] for p in _itens(analista.get("/api/parceiros"))]

    assert nomes == ["Comércio Alfa", "Comércio Beta", "Comércio Gama"]


def test_busca_por_trecho_do_nome(analista):
    analista.post("/api/parceiros", json={"nome": "Padaria do Centro"})
    analista.post("/api/parceiros", json={"nome": "Mercado do Bairro"})

    r = analista.get("/api/parceiros", params={"busca": "padaria"})

    assert [p["nome"] for p in _itens(r)] == ["Padaria do Centro"]


# ============================================= H37 · busca sem acentuação
@pytest.mark.parametrize(
    "termo",
    ["comercio", "Comércio", "COMERCIO", "cOmErCiO", "mércio", "mercio"],
)
def test_busca_ignora_acentuacao_e_caixa(analista, termo):
    """RF24 — buscar `comercio` precisa encontrar `Comércio`.

    A busca anterior usava `ILIKE`, que ignora maiúsculas e **não** ignora
    acento: a história parecia cumprida e metade do critério não estava.
    """
    analista.post("/api/parceiros", json={"nome": "Comércio Órion"})
    analista.post("/api/parceiros", json={"nome": "Mercado do Bairro"})

    r = analista.get("/api/parceiros", params={"busca": termo})

    assert [p["nome"] for p in _itens(r)] == ["Comércio Órion"]


def test_busca_encontra_por_trecho_no_meio_do_nome(analista):
    """Correspondência parcial em qualquer posição, não só por prefixo."""
    analista.post("/api/parceiros", json={"nome": "Restaurante Sabor Caseiro"})

    r = analista.get("/api/parceiros", params={"busca": "sabor"})

    assert len(_itens(r)) == 1


def test_renomear_mantem_a_busca_correta(analista):
    """A coluna normalizada não pode envelhecer em relação ao nome.

    Se ela ficasse presa ao valor do cadastro, o parceiro renomeado deixaria de
    ser encontrado pelo nome novo — **sem erro nenhum**, que é o modo de falha
    mais caro deste projeto.
    """
    alvo = analista.post("/api/parceiros", json={"nome": "Nome Antigo"}).json()["id"]

    analista.patch(f"/api/parceiros/{alvo}", json={"nome": "Café Renomeado"})

    assert len(_itens(analista.get("/api/parceiros", params={"busca": "cafe"}))) == 1
    assert _itens(analista.get("/api/parceiros", params={"busca": "antigo"})) == []


@pytest.mark.parametrize("curinga", ["%", "_", "%%", "a%"])
def test_curinga_digitado_e_texto_e_nao_padrao(analista, curinga):
    """Quem digita `%` está procurando um nome, não pedindo curinga.

    Sem escapar, `%` casaria com tudo e `_` com qualquer caractere — a busca
    devolveria a base inteira e pareceria estar funcionando.
    """
    analista.post("/api/parceiros", json={"nome": "Padaria do Centro"})
    analista.post("/api/parceiros", json={"nome": "Mercado do Bairro"})

    r = analista.get("/api/parceiros", params={"busca": curinga})

    assert _itens(r) == []


def test_parceiro_criado_pela_importacao_tambem_e_encontrado(analista):
    """A importação cria parceiro por outro caminho, e ele precisa ser buscável.

    Os dois caminhos usam a mesma normalização — se divergissem, só o parceiro
    cadastrado pela tela apareceria, e ninguém desconfiaria da busca.
    """
    analista.post(
        "/api/importacoes",
        json={
            "periodo_inicio": "2026-04-06",
            "periodo_fim": "2026-04-12",
            "texto": "Parceiro;Faturamento;Pedidos\nEmpório Água Verde;900,00;12\n",
        },
    )

    r = analista.get("/api/parceiros", params={"busca": "emporio agua"})

    assert [p["nome"] for p in _itens(r)] == ["Empório Água Verde"]


def test_filtra_por_situacao_e_por_categoria(analista, categoria):
    analista.post("/api/parceiros", json={"nome": "Com categoria", "categoria_id": categoria})
    inativo = analista.post("/api/parceiros", json={"nome": "Sem categoria"}).json()["id"]
    analista.patch(f"/api/parceiros/{inativo}", json={"ativo": False})

    ativos = _itens(analista.get("/api/parceiros", params={"ativo": True}))
    por_categoria = _itens(analista.get("/api/parceiros", params={"categoria_id": categoria}))

    assert [p["nome"] for p in ativos] == ["Com categoria"]
    assert [p["nome"] for p in por_categoria] == ["Com categoria"]


def test_filtra_os_pendentes_de_classificacao(analista, categoria):
    """Parceiro criado pela importação entra sem categoria (UC04, A1); este
    filtro é o que permite encontrá-los depois."""
    analista.post("/api/parceiros", json={"nome": "Classificado", "categoria_id": categoria})
    analista.post("/api/parceiros", json={"nome": "Pendente"})

    r = analista.get("/api/parceiros", params={"sem_categoria": True})

    assert [p["nome"] for p in _itens(r)] == ["Pendente"]


# ============================================================ atualizar
def test_edita_nome_e_contato(analista):
    alvo = analista.post("/api/parceiros", json=novo()).json()["id"]

    r = analista.patch(
        f"/api/parceiros/{alvo}",
        json={"nome": "Comércio Alfa Ltda", "contato": "novo@exemplo.test"},
    )

    assert r.status_code == 200
    assert r.json()["nome"] == "Comércio Alfa Ltda"
    assert r.json()["contato"] == "novo@exemplo.test"


def test_classificar_depois_tambem_marca_origem_manual(analista, categoria):
    alvo = analista.post("/api/parceiros", json=novo()).json()["id"]

    r = analista.patch(f"/api/parceiros/{alvo}", json={"categoria_id": categoria})

    assert r.json()["categoria"]["id"] == categoria
    assert r.json()["origem_categoria"] == "MANUAL"


def test_desclassificar_limpa_a_origem(analista, categoria):
    """O banco exige que categoria e origem sejam ambas nulas ou ambas
    preenchidas; limpar só uma estouraria a restrição."""
    alvo = analista.post("/api/parceiros", json=novo(categoria_id=categoria)).json()["id"]

    r = analista.patch(f"/api/parceiros/{alvo}", json={"categoria_id": None})

    assert r.status_code == 200, r.text
    assert r.json()["categoria"] is None
    assert r.json()["origem_categoria"] is None


def test_muda_status_comercial(analista):
    alvo = analista.post("/api/parceiros", json=novo()).json()["id"]

    r = analista.patch(f"/api/parceiros/{alvo}", json={"status": "PROSPECCAO"})

    assert r.json()["status"] == "PROSPECCAO"


def test_desativar_mantem_o_registro(analista):
    """Desativar tira de circulação sem destruir o histórico (UC04, A4)."""
    alvo = analista.post("/api/parceiros", json=novo()).json()["id"]

    assert analista.patch(f"/api/parceiros/{alvo}", json={"ativo": False}).json()["ativo"] is False

    s = Sessao()
    try:
        assert s.get(Parceiro, alvo) is not None
    finally:
        s.close()


def test_edicao_vazia_e_recusada(analista):
    alvo = analista.post("/api/parceiros", json=novo()).json()["id"]
    assert analista.patch(f"/api/parceiros/{alvo}", json={}).status_code == 422


def test_edicao_para_nome_ja_usado_e_recusada(analista):
    analista.post("/api/parceiros", json={"nome": "Comércio Beta"})
    alvo = analista.post("/api/parceiros", json=novo()).json()["id"]

    r = analista.patch(f"/api/parceiros/{alvo}", json={"nome": "Comércio Beta"})

    assert r.status_code == 409


# ============================================================== excluir
def test_exclui_parceiro_sem_historico(analista):
    alvo = analista.post("/api/parceiros", json=novo()).json()["id"]

    r = analista.delete(f"/api/parceiros/{alvo}")

    assert r.status_code == 204
    assert analista.get(f"/api/parceiros/{alvo}").status_code == 404

    s = Sessao()
    try:
        assert s.scalars(select(Parceiro)).all() == []
    finally:
        s.close()


def test_exclusao_com_historico_e_recusada_dizendo_o_que_impede(
    analista, criar_usuario, cliente
):
    """Apagar um parceiro com faturamento importado falsearia as séries dos
    períodos já fechados — o total da rede deixaria de bater com a soma das
    partes, e a tela continuaria parecendo correta."""
    dono = criar_usuario(login="quem.importou", perfil=Perfil.GESTOR)
    alvo = analista.post("/api/parceiros", json=novo()).json()["id"]
    dar_historico(alvo, dono)

    r = analista.delete(f"/api/parceiros/{alvo}")

    assert r.status_code == 409
    detalhe = r.json()["detail"]
    assert detalhe["vinculos"]["metricas"] == 1
    # A recusa precisa dizer o caminho: "não é possível excluir" sozinho obriga
    # o usuário a adivinhar o que fazer.
    assert "desative" in detalhe["ajuda"].lower()


def test_parceiro_com_historico_continua_apos_a_recusa(analista, criar_usuario):
    dono = criar_usuario(login="quem.importou", perfil=Perfil.GESTOR)
    alvo = analista.post("/api/parceiros", json=novo()).json()["id"]
    dar_historico(alvo, dono)

    analista.delete(f"/api/parceiros/{alvo}")

    assert analista.get(f"/api/parceiros/{alvo}").status_code == 200


def test_excluir_inexistente_da_404(analista):
    assert analista.delete("/api/parceiros/9999").status_code == 404


# ============================================================ auditoria
def test_operacoes_entram_na_trilha(analista, cliente, criar_usuario, autenticar, categoria):
    """RF06 — a alteração de parceiro é ação sensível."""
    alvo = analista.post("/api/parceiros", json=novo()).json()["id"]
    analista.patch(f"/api/parceiros/{alvo}", json={"categoria_id": categoria})
    analista.delete(f"/api/parceiros/{alvo}")

    criar_usuario(login="chefia", perfil=Perfil.ADMINISTRADOR)
    cliente.cookies.clear()
    autenticar("chefia")
    acoes = [i["acao"] for i in cliente.get("/api/auditoria").json()["itens"]]

    assert "PARCEIRO_CRIADO" in acoes
    assert "PARCEIRO_CLASSIFICADO" in acoes
    assert "PARCEIRO_EXCLUIDO" in acoes


# ============================================================ categorias
def test_lista_e_cria_categoria(analista):
    r = analista.post("/api/categorias", json={"nome": "Pizzaria"})

    assert r.status_code == 201
    assert r.json()["nome"] == "Pizzaria"
    assert [c["nome"] for c in analista.get("/api/categorias").json()] == ["Pizzaria"]


def test_categoria_repetida_e_recusada(analista):
    analista.post("/api/categorias", json={"nome": "Pizzaria"})

    assert analista.post("/api/categorias", json={"nome": "Pizzaria"}).status_code == 409


def test_parceiro_criado_pela_importacao_aparece_sem_categoria(analista, criar_usuario):
    """Fecha o ciclo com a ingestão: o que a importação cria é justamente o que o
    filtro de pendentes precisa encontrar."""
    criar_parceiro_no_banco("Veio da importação", status=StatusComercial.ATIVO)

    r = analista.get("/api/parceiros", params={"sem_categoria": True})

    assert [p["nome"] for p in _itens(r)] == ["Veio da importação"]
    assert _itens(r)[0]["origem_categoria"] is None


def test_origem_categoria_nao_e_aceita_do_cliente(analista, categoria):
    """Campo desconhecido é ignorado pelo Pydantic; o que importa é que a origem
    gravada seja a que a regra determina, não a que o cliente pediu."""
    r = analista.post(
        "/api/parceiros",
        json=novo(categoria_id=categoria, origem_categoria=OrigemCategoria.SUGERIDA_IA.value),
    )

    assert r.status_code == 201
    assert r.json()["origem_categoria"] == "MANUAL"
