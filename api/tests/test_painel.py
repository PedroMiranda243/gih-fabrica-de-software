"""Testes do painel — histórias H30 (indicadores), H31 (ranking) e H32 (séries).

Requisitos: RF17, RF18, RF19; regra RN04; caso de uso UC05, com os fluxos
alternativos A1 (base vazia) e A2 (período único).

O cenário é montado direto no banco, e não pela API de importação: um defeito na
ingestão reprovaria testes que não têm nada a ver com ela.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import event
from sqlalchemy.engine import Engine

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
)

PRIMEIRA_SEMANA = date(2026, 3, 2)


@pytest.fixture
def gestor(criar_usuario, autenticar, cliente):
    """O ator do UC05."""
    criar_usuario(login="gestora", perfil=Perfil.GESTOR)
    autenticar("gestora")
    return cliente


@pytest.fixture
def semear(criar_usuario):
    """Monta períodos, parceiros e métricas.

    Cada semana é um dicionário `{nome do parceiro: (faturamento, pedidos)}`.
    Parceiro ausente numa semana simplesmente não recebe métrica ali — é assim
    que se produz a lacuna que a H32 precisa mostrar.

    Devolve os ids dos períodos, na ordem em que foram passados.
    """
    autor_id = criar_usuario(login="semeador", perfil=Perfil.ANALISTA)

    def montar(*semanas: dict[str, tuple[str, int]], inicio: date = PRIMEIRA_SEMANA) -> list[int]:
        ids = []
        s = Sessao()
        try:
            # Parceiro já existente é reaproveitado, como a importação real faz:
            # o nome é único no banco, e chamar esta fábrica duas vezes no mesmo
            # teste tentaria recriá-lo.
            parceiros: dict[str, Parceiro] = {p.nome: p for p in s.query(Parceiro)}
            for indice, semana in enumerate(semanas):
                comeco = inicio + timedelta(days=7 * indice)
                periodo = Periodo(data_inicio=comeco, data_fim=comeco + timedelta(days=6))
                s.add(periodo)
                s.flush()

                # A métrica exige a importação que a trouxe: é o que amarra o
                # dado à sua origem, e o modelo não deixa gravar sem ela.
                importacao = Importacao(
                    periodo_id=periodo.id,
                    usuario_id=autor_id,
                    origem=OrigemImportacao.TEXTO,
                    total_gravado=len(semana),
                    total_rejeitado=0,
                )
                s.add(importacao)
                s.flush()

                for nome, (faturamento, pedidos) in semana.items():
                    if nome not in parceiros:
                        parceiros[nome] = Parceiro(nome=nome)
                        s.add(parceiros[nome])
                        s.flush()
                    s.add(
                        Metrica(
                            parceiro_id=parceiros[nome].id,
                            periodo_id=periodo.id,
                            importacao_id=importacao.id,
                            faturamento=Decimal(faturamento),
                            pedidos=pedidos,
                        )
                    )
                ids.append(periodo.id)
            s.commit()
            return ids
        finally:
            s.close()

    return montar


# ====================================================== H30 · indicadores
def test_base_vazia_devolve_estado_inicial(gestor):
    """UC05, A1 — quem ainda não importou nada não recebe erro, recebe vazio."""
    r = gestor.get("/api/painel/indicadores")

    assert r.status_code == 200
    corpo = r.json()
    assert corpo["periodo"] is None
    assert corpo["faturamento"] == "0.00"
    assert corpo["parceiros_ativos"] == 0
    assert corpo["variacao"] is None


def test_indicadores_consolidam_o_periodo_mais_recente(gestor, semear):
    semear(
        {"Alfa": ("1000.00", 10), "Beta": ("500.00", 5)},
        {"Alfa": ("2000.00", 20), "Beta": ("1000.00", 5)},
    )

    corpo = gestor.get("/api/painel/indicadores").json()

    assert corpo["faturamento"] == "3000.00"
    assert corpo["pedidos"] == 25
    assert corpo["parceiros_ativos"] == 2


def test_ticket_medio_e_a_razao_dos_totais_e_nao_a_media_das_medias(gestor, semear):
    """RN04, e uma armadilha de estatística.

    A média dos tickets daria peso igual a quem fez 20 pedidos e a quem fez 5.
    O que responde "quanto vale um pedido nesta rede" é a razão dos totais.
    """
    semear({"Alfa": ("2000.00", 20), "Beta": ("1000.00", 5)})

    corpo = gestor.get("/api/painel/indicadores").json()

    # 3000 / 25 = 120,00 — e não a média de 100,00 e 200,00, que seria 150,00.
    assert corpo["ticket_medio"] == "120.00"


def test_periodo_unico_nao_tem_com_que_comparar(gestor, semear):
    """UC05, A2 — sem histórico não há variação, e isso não é zero."""
    semear({"Alfa": ("1000.00", 10)})

    corpo = gestor.get("/api/painel/indicadores").json()

    assert corpo["periodo_anterior"] is None
    assert corpo["variacao"] is None


def test_variacao_compara_com_o_periodo_anterior(gestor, semear):
    semear(
        {"Alfa": ("1000.00", 10)},
        {"Alfa": ("1500.00", 12)},
    )

    variacao = gestor.get("/api/painel/indicadores").json()["variacao"]

    assert variacao["faturamento"] == "50.00"
    assert variacao["pedidos"] == "20.00"


def test_sem_pedidos_o_ticket_e_nulo_e_nao_zero(gestor, semear):
    """Zero afirmaria que cada pedido valeu nada; o que houve foi nenhum pedido."""
    semear({"Alfa": ("0.00", 0)})

    assert gestor.get("/api/painel/indicadores").json()["ticket_medio"] is None


def test_variacao_sobre_base_zero_e_nula_e_nao_zero(gestor, semear):
    """Crescer a partir de zero não tem percentual definido.

    Devolver zero diria "não mudou" sobre a única mudança que houve.
    """
    semear(
        {"Alfa": ("0.00", 0)},
        {"Alfa": ("1000.00", 10)},
    )

    variacao = gestor.get("/api/painel/indicadores").json()["variacao"]

    assert variacao["faturamento"] is None
    assert variacao["parceiros_ativos"] == "0.00"  # um parceiro nos dois: não mudou


def test_periodo_inexistente_e_404(gestor, semear):
    """Pedir um período e receber outro seria pior que receber erro."""
    semear({"Alfa": ("1000.00", 10)})

    assert gestor.get("/api/painel/indicadores", params={"periodo_id": 999999}).status_code == 404


def test_periodo_anterior_segue_o_calendario_e_nao_a_ordem_de_digitacao(gestor, semear):
    """Importar um período antigo depois de um recente não pode inverter a comparação.

    O id segue a ordem em que se digitou; o anterior é o anterior no calendário.
    """
    recentes = semear({"Alfa": ("2000.00", 20)}, inicio=date(2026, 6, 1))
    semear({"Alfa": ("1000.00", 10)}, inicio=date(2026, 5, 4))  # mais antigo, id maior

    corpo = gestor.get("/api/painel/indicadores", params={"periodo_id": recentes[0]}).json()

    assert corpo["periodo_anterior"]["data_inicio"] == "2026-05-04"
    assert corpo["variacao"]["faturamento"] == "100.00"


# ========================================================== H31 · ranking
def test_ranking_ordena_por_faturamento(gestor, semear):
    semear({"Alfa": ("100.00", 1), "Beta": ("300.00", 3), "Gama": ("200.00", 2)})

    itens = gestor.get("/api/painel/ranking").json()["itens"]

    assert [i["nome"] for i in itens] == ["Beta", "Gama", "Alfa"]
    assert [i["posicao"] for i in itens] == [1, 2, 3]


def test_ranking_traz_posicao_anterior_e_variacao(gestor, semear):
    """RF18 — posição atual, posição no período anterior e variação percentual."""
    semear(
        {"Alfa": ("300.00", 3), "Beta": ("100.00", 1)},
        {"Alfa": ("100.00", 1), "Beta": ("400.00", 4)},
    )

    itens = {i["nome"]: i for i in gestor.get("/api/painel/ranking").json()["itens"]}

    assert itens["Beta"]["posicao"] == 1 and itens["Beta"]["posicao_anterior"] == 2
    assert itens["Alfa"]["posicao"] == 2 and itens["Alfa"]["posicao_anterior"] == 1
    assert itens["Alfa"]["variacao_percentual"] == "-66.67"


def test_estreante_nao_e_queda(gestor, semear):
    """Posição anterior nula, sozinha, seria lida como "despencou".

    Quem não existia no período anterior não caiu de lugar nenhum.
    """
    semear(
        {"Alfa": ("300.00", 3)},
        {"Alfa": ("300.00", 3), "Novo": ("100.00", 1)},
    )

    itens = {i["nome"]: i for i in gestor.get("/api/painel/ranking").json()["itens"]}

    assert itens["Novo"]["posicao_anterior"] is None
    assert itens["Novo"]["estreante"] is True
    assert itens["Alfa"]["estreante"] is False


def test_no_primeiro_periodo_ninguem_e_estreante(gestor, semear):
    """Sem período anterior ninguém estreou — são simplesmente os primeiros dados."""
    semear({"Alfa": ("300.00", 3), "Beta": ("100.00", 1)})

    itens = gestor.get("/api/painel/ranking").json()["itens"]

    assert all(i["estreante"] is False for i in itens)


def test_empate_e_desempatado_pelo_nome_e_nao_oscila(gestor, semear):
    """Sem critério de desempate explícito, o banco devolve os empatados em
    qualquer ordem — e a mesma base produziria posições diferentes entre duas
    execuções, fazendo o painel anunciar subida e queda que não aconteceram."""
    semear({"Zeta": ("100.00", 1), "Alfa": ("100.00", 1), "Meta": ("100.00", 1)})

    primeira = [i["nome"] for i in gestor.get("/api/painel/ranking").json()["itens"]]
    segunda = [i["nome"] for i in gestor.get("/api/painel/ranking").json()["itens"]]

    assert primeira == ["Alfa", "Meta", "Zeta"]
    assert primeira == segunda


def test_ranking_e_paginado(gestor, semear):
    semear({f"Parceiro {i:02d}": (f"{100 - i}.00", 1) for i in range(10)})

    pagina = gestor.get("/api/painel/ranking", params={"tamanho": 4, "pagina": 2}).json()

    assert pagina["total"] == 10
    assert len(pagina["itens"]) == 4
    assert [i["posicao"] for i in pagina["itens"]] == [5, 6, 7, 8]


def test_posicao_anterior_vem_do_ranking_inteiro_e_nao_da_pagina(gestor, semear):
    """A armadilha desta rota.

    Calcular a posição anterior sobre o recorte devolveria a posição *dentro da
    página*, que não significa nada — e ninguém perceberia, porque os números
    continuariam parecendo plausíveis.
    """
    semana = {f"P{i:02d}": (f"{100 - i}.00", 1) for i in range(10)}
    semear(semana, semana)

    pagina = gestor.get("/api/painel/ranking", params={"tamanho": 3, "pagina": 3}).json()

    # Terceira página: posições 7, 8 e 9 — e, como nada mudou entre os períodos,
    # a posição anterior de cada um é a própria.
    assert [i["posicao"] for i in pagina["itens"]] == [7, 8, 9]
    assert [i["posicao_anterior"] for i in pagina["itens"]] == [7, 8, 9]


def test_ranking_de_base_vazia_nao_quebra(gestor):
    corpo = gestor.get("/api/painel/ranking").json()

    assert corpo["periodo"] is None and corpo["itens"] == [] and corpo["total"] == 0


def test_ranking_traz_a_categoria_quando_ha(gestor, semear):
    semear({"Alfa": ("100.00", 1)})
    s = Sessao()
    try:
        categoria = Categoria(nome="Lanches")
        s.add(categoria)
        s.flush()
        parceiro = s.query(Parceiro).filter_by(nome="Alfa").one()
        parceiro.categoria_id = categoria.id
        parceiro.origem_categoria = OrigemCategoria.MANUAL
        s.commit()
    finally:
        s.close()

    assert gestor.get("/api/painel/ranking").json()["itens"][0]["categoria"] == "Lanches"


# =========================================================== H32 · séries
def test_serie_da_rede_soma_por_periodo(gestor, semear):
    semear(
        {"Alfa": ("100.00", 1), "Beta": ("200.00", 2)},
        {"Alfa": ("300.00", 3)},
    )

    corpo = gestor.get("/api/painel/series").json()

    assert corpo["escopo"] == "rede"
    assert [p["faturamento"] for p in corpo["pontos"]] == ["300.00", "300.00"]


def test_serie_do_parceiro_traz_so_o_dele(gestor, semear):
    ids = semear({"Alfa": ("100.00", 1), "Beta": ("900.00", 9)})
    alvo = _id_do_parceiro("Alfa")

    corpo = gestor.get("/api/painel/series", params={"parceiro_id": alvo}).json()

    assert corpo["escopo"] == "parceiro"
    assert corpo["parceiro_nome"] == "Alfa"
    assert corpo["pontos"][0]["faturamento"] == "100.00"
    assert len(corpo["pontos"]) == len(ids)


def test_lacuna_no_meio_da_serie_aparece_como_buraco(gestor, semear):
    """O ponto que falta **precisa** aparecer.

    Omiti-lo faria o gráfico ligar os vizinhos com uma reta e desenhar uma
    tendência onde não houve medição nenhuma.
    """
    semear(
        {"Alfa": ("100.00", 1), "Beta": ("100.00", 1)},
        {"Beta": ("100.00", 1)},  # Alfa não aparece nesta semana
        {"Alfa": ("300.00", 3), "Beta": ("100.00", 1)},
    )

    pontos = gestor.get(
        "/api/painel/series", params={"parceiro_id": _id_do_parceiro("Alfa")}
    ).json()["pontos"]

    assert len(pontos) == 3
    assert pontos[1]["faturamento"] is None
    assert pontos[1]["pedidos"] is None
    assert pontos[1]["ticket_medio"] is None
    # E o período da lacuna continua identificado: o buraco tem data.
    assert pontos[1]["periodo"]["data_inicio"] == "2026-03-09"


def test_serie_sai_em_ordem_cronologica(gestor, semear):
    """A ordenação é da consulta, não do cliente."""
    semear({"Alfa": ("300.00", 3)}, inicio=date(2026, 6, 1))
    semear({"Alfa": ("100.00", 1)}, inicio=date(2026, 5, 4))

    datas = [p["periodo"]["data_inicio"] for p in gestor.get("/api/painel/series").json()["pontos"]]

    assert datas == sorted(datas)


def test_serie_respeita_o_recorte_por_data(gestor, semear):
    semear(
        {"Alfa": ("100.00", 1)},
        {"Alfa": ("200.00", 2)},
        {"Alfa": ("300.00", 3)},
    )

    corpo = gestor.get("/api/painel/series", params={"de": "2026-03-09"}).json()

    assert len(corpo["pontos"]) == 2
    assert corpo["pontos"][0]["periodo"]["data_inicio"] == "2026-03-09"


def test_serie_de_parceiro_inexistente_e_404(gestor, semear):
    semear({"Alfa": ("100.00", 1)})

    assert gestor.get("/api/painel/series", params={"parceiro_id": 999999}).status_code == 404


def test_serie_de_base_vazia_e_lista_vazia(gestor):
    corpo = gestor.get("/api/painel/series").json()

    assert corpo["escopo"] == "rede" and corpo["pontos"] == []


# ================================================ desempenho: o N+1 medido
@pytest.mark.parametrize("quantos", [5, 40])
def test_o_ranking_nao_faz_uma_consulta_por_linha(gestor, semear, quantos):
    """A afirmação "duas consultas, não N" medida, e não escrita no comentário.

    O N+1 é o defeito que passa na demonstração e morre com a base cheia: com
    10.000 parceiros (RNF04) e 2 s de teto (RNF03), uma consulta por linha não
    tem como caber. Medir o número de consultas contra dois tamanhos de página é
    o que impede alguém de reintroduzi-lo sem perceber — com poucos dados o
    tempo continuaria aceitável e nenhum outro teste reclamaria.

    Medido em 17/09/2026 com 5, 20, 40 e 80 linhas: **5 consultas em todos os
    casos** — período alvo, contagem, página, período anterior e as posições
    anteriores. O limiar abaixo é 6, deliberadamente colado no valor real: com
    folga larga o teste passaria mesmo com o defeito de volta.
    """
    semana = {f"P{i:03d}": (f"{1000 - i}.00", 1) for i in range(quantos)}
    semear(semana, semana)

    consultas: list[str] = []

    def anotar(conn, cursor, texto, parametros, contexto, muitos):  # noqa: ANN001
        consultas.append(texto)

    event.listen(Engine, "before_cursor_execute", anotar)
    try:
        r = gestor.get("/api/painel/ranking", params={"tamanho": quantos})
    finally:
        # Remover no `finally`: um ouvinte vazado ficaria acumulando consultas
        # dos testes seguintes e este passaria a reprovar por causa deles.
        event.remove(Engine, "before_cursor_execute", anotar)

    assert r.status_code == 200
    assert len(r.json()["itens"]) == quantos

    # As da própria rota são poucas e fixas; as demais são da sessão autenticada.
    # O que importa é não crescer com o número de linhas.
    do_painel = [c for c in consultas if "metrica" in c.lower() or "periodo" in c.lower()]
    assert len(do_painel) <= 6, (
        f"{len(do_painel)} consultas para {quantos} linhas — "
        "o número precisa ser fixo, não proporcional à página"
    )


# ========================================================== apoio dos testes
def _id_do_parceiro(nome: str) -> int:
    s = Sessao()
    try:
        return s.query(Parceiro).filter_by(nome=nome).one().id
    finally:
        s.close()
