"""Testes da sugestão de categoria pelo nome — RN05, RF15, história H27.

A regra está em `docs/02-requisitos.md` (RN05), aprovada na issue #35.
"""
from __future__ import annotations

import pytest

from app.db import Sessao
from app.modelos import Categoria, OrigemCategoria, Parceiro, Perfil
from app.sugestao_categoria import PALAVRAS, categoria_da_regra, sugerir
from app.texto import normalizar


@pytest.fixture
def analista(criar_usuario, autenticar, cliente):
    criar_usuario(login="analista", perfil=Perfil.ANALISTA)
    autenticar("analista")
    return cliente


def categoria(nome: str, ativa: bool = True) -> Categoria:
    with Sessao() as s:
        c = Categoria(nome=nome, ativa=ativa)
        s.add(c)
        s.commit()
        s.refresh(c)
        return c


# =============================================================== a regra
@pytest.mark.parametrize(
    ("nome", "esperada"),
    [
        ("Pizzaria Bella", "Pizzaria"),
        ("Padaria do Bairro", "Padaria"),
        ("Hamburgueria Central", "Lanchonete"),
        ("Churrascaria Gaúcha", "Restaurante"),
        ("Açaí da Praia", "Açaí e sorvetes"),
        ("Mercadinho São Jorge", "Mercado"),
        ("Adega do Vale", "Bebidas"),
        ("Drogaria Popular", "Farmácia"),
        ("Pet Shop Amigo", "Petshop"),
        ("Botijão Express", "Gás e água"),
    ],
)
def test_cada_categoria_e_reconhecida_pelas_suas_palavras(nome, esperada):
    assert categoria_da_regra(nome) == normalizar(esperada)


def test_toda_categoria_da_tabela_tem_palavra_propria():
    """Uma palavra repetida em duas categorias tornaria as duas ambíguas para
    sempre — o nome casaria com as duas e nunca haveria sugestão."""
    todas = [normalizar(p) for palavras in PALAVRAS.values() for p in palavras]
    assert len(todas) == len(set(todas))


def test_acento_e_caixa_nao_importam():
    assert categoria_da_regra("PIZZARIA do vale") == "pizzaria"
    assert categoria_da_regra("Pao Quente") == "padaria"
    assert categoria_da_regra("Farmacia Sao Jose") == normalizar("Farmácia")


def test_so_palavra_inteira():
    """"Pet" casa com "Pet Shop", e não com "Carpete" nem com "Petiscaria"."""
    assert categoria_da_regra("Carpete Azul") is None
    assert categoria_da_regra("Petiscaria do Porto") is None


def test_nome_que_aponta_duas_categorias_nao_recebe_sugestao():
    """Adivinhar entre as duas seria gravar palpite com cara de decisão."""
    assert categoria_da_regra("Pizzaria e Lanchonete do Vale") is None


def test_nome_sem_palavra_de_categoria_fica_em_branco():
    """Os nomes da base sintética são assim — e branco é resultado aceitável."""
    assert categoria_da_regra("Cantina do Chef") is None
    assert categoria_da_regra("Forno Real") is None
    assert categoria_da_regra("Empório Dourado") is None


def test_agua_sozinha_nao_basta_mas_agua_mineral_sim():
    assert categoria_da_regra("Água Viva") is None
    assert categoria_da_regra("Água Mineral da Serra") == normalizar("Gás e água")


def test_so_sugere_categoria_que_existe_e_esta_ativa():
    categorias = {"pizzaria": Categoria(id=1, nome="Pizzaria", ativa=True)}

    assert sugerir("Pizzaria Bella", categorias).nome == "Pizzaria"
    # Padaria não está na base: a regra aponta, mas não há o que sugerir.
    assert sugerir("Padaria do Bairro", categorias) is None


# ============================================================ importação
def test_importacao_sugere_a_categoria_dos_parceiros_novos(analista):
    pizzaria = categoria("Pizzaria")
    categoria("Padaria", ativa=False)

    r = analista.post("/api/importacoes", json={
        "periodo_inicio": "2026-09-07",
        "periodo_fim": "2026-09-13",
        "texto": (
            "Parceiro;Faturamento;Pedidos\n"
            "Pizzaria Bella;1200,00;30\n"
            "Padaria do Bairro;800,00;40\n"
            "Cantina do Chef;900,00;20\n"
        ),
    })
    assert r.status_code == 201, r.text

    with Sessao() as s:
        por_nome = {p.nome: p for p in s.query(Parceiro)}
    assert por_nome["Pizzaria Bella"].categoria_id == pizzaria.id
    assert por_nome["Pizzaria Bella"].origem_categoria == OrigemCategoria.INFERIDA
    # Categoria inativa não é sugerida, e nome sem palavra fica em branco.
    assert por_nome["Padaria do Bairro"].categoria_id is None
    assert por_nome["Cantina do Chef"].origem_categoria is None


# ======================================================== cadastro manual
def test_a_rota_sugere_sem_gravar_nada(analista):
    pizzaria = categoria("Pizzaria")

    r = analista.get("/api/categorias/sugestao", params={"nome": "Pizzaria Bella"})

    assert r.status_code == 200
    assert r.json()["categoria"]["id"] == pizzaria.id
    with Sessao() as s:
        assert s.query(Parceiro).count() == 0


def test_sem_sugestao_a_resposta_diz_nula_e_nao_erro(analista):
    categoria("Pizzaria")

    r = analista.get("/api/categorias/sugestao", params={"nome": "Forno Real"})

    assert r.status_code == 200
    assert r.json() == {"categoria": None}


def test_categoria_so_sugerida_continua_pendente_de_classificacao(analista):
    """Pendente é quem não tem categoria **confirmada** (RN05). Sem isto, o
    parceiro importado sairia da fila de classificação justamente por ter
    recebido um palpite."""
    categoria("Pizzaria")
    analista.post("/api/importacoes", json={
        "periodo_inicio": "2026-09-07",
        "periodo_fim": "2026-09-13",
        "texto": "Parceiro;Faturamento;Pedidos\nPizzaria Bella;1200,00;30\n",
    })

    pendentes = analista.get("/api/parceiros", params={"sem_categoria": True}).json()["itens"]
    assert [p["nome"] for p in pendentes] == ["Pizzaria Bella"]

    # Salvar o cadastro com a categoria a confirma, e ele sai da fila.
    alvo = pendentes[0]
    analista.patch(f"/api/parceiros/{alvo['id']}", json={"categoria_id": alvo["categoria"]["id"]})
    assert analista.get("/api/parceiros", params={"sem_categoria": True}).json()["itens"] == []
