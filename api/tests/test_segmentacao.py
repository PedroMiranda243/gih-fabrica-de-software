"""Testes da segmentação — história H33, regra RN01.

A regra está partida em duas de propósito, e os testes acompanham: `classificar`
é pura e recebe números, e é onde os seis ramos da precedência são cobertos sem
massa de dados; `reprocessar` toca o banco, e é onde se testa idempotência,
alcance e número de consultas.

O teste que mais importa é `test_top_em_queda_sai_como_em_risco`. Ele é o
contraexemplo que RN01 e RN02 existem para tratar, e foi listado no CLAUDE.md
como o caso que o teste precisa incluir.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import event, select
from sqlalchemy.engine import Engine

from app.db import Sessao
from app.modelos import (
    HistoricoSegmento,
    Importacao,
    Metrica,
    OrigemImportacao,
    Parceiro,
    Perfil,
    Periodo,
    Segmento,
    StatusComercial,
)
from app.servico_segmentacao import (
    PADRAO,
    Limiares,
    classificar,
    reprocessar,
    reprocessar_desde,
    reprocessar_tudo,
)

PRIMEIRA_SEMANA = date(2026, 3, 2)


def _v(*valores: str) -> list[Decimal]:
    """Faturamentos do mais recente para o mais antigo, como a consulta entrega."""
    return [Decimal(v) for v in valores]


# ===================================================== a regra pura (RN01)
def test_prospeccao_vence_tudo():
    """Estado comercial declarado não é contradito pelo histórico."""
    assert (
        classificar(
            status=StatusComercial.PROSPECCAO,
            periodos=12,
            faturamentos=_v("100", "200", "300"),  # duas quedas seguidas
            posicao=1,  # e no topo do ranking
        )
        is Segmento.PROSPECCAO
    )


def test_recem_chegado_vence_tendencia_e_top():
    """Histórico curto demais para a tendência significar alguma coisa."""
    assert (
        classificar(
            status=StatusComercial.ATIVO,
            periodos=2,
            faturamentos=_v("100", "200", "300"),
            posicao=1,
        )
        is Segmento.RECEM_CHEGADO
    )


def test_top_em_queda_sai_como_em_risco():
    """**O caso que RN01 existe para tratar.**

    Um parceiro entre os N maiores, mas em queda consecutiva, é risco — não
    campeão. Se este teste reprovar porque alguém "consertou" a precedência
    colocando Top antes, o painel deixa de responder *quem está prestes a sair
    do Top 15?*, que é a pergunta que o produto promete.

    É também a razão de RN02: este parceiro fica gravado como EM_RISCO, então a
    mobilidade do Top N não pode ser derivada do segmento — ela leria uma saída
    que não aconteceu.
    """
    segmento = classificar(
        status=StatusComercial.ATIVO,
        periodos=12,
        faturamentos=_v("800", "900", "1000"),
        posicao=3,
    )

    assert segmento is Segmento.EM_RISCO
    assert segmento is not Segmento.TOP


def test_top_sem_queda_e_top():
    assert (
        classificar(
            status=StatusComercial.ATIVO,
            periodos=12,
            faturamentos=_v("1000", "900", "950"),
            posicao=15,
        )
        is Segmento.TOP
    )


def test_fora_do_top_com_duas_altas_e_ascensao():
    """RN01 pede "fora do Top N", e isso sai da precedência: Top vem antes."""
    assert (
        classificar(
            status=StatusComercial.ATIVO,
            periodos=12,
            faturamentos=_v("1200", "1000", "800"),
            posicao=42,
        )
        is Segmento.EM_ASCENSAO
    )


def test_sem_criterio_e_estavel():
    assert (
        classificar(
            status=StatusComercial.ATIVO,
            periodos=12,
            faturamentos=_v("1000", "1000", "1000"),
            posicao=300,
        )
        is Segmento.ESTAVEL
    )


def test_uma_queda_so_nao_e_risco():
    """O limiar é 2 períodos consecutivos, não "caiu"."""
    assert (
        classificar(
            status=StatusComercial.ATIVO,
            periodos=12,
            faturamentos=_v("900", "1000", "900"),
            posicao=300,
        )
        is Segmento.ESTAVEL
    )


def test_empate_quebra_a_sequencia():
    """Faturamento igual não é queda nem alta.

    Sem isso, uma rede parada viraria metade em risco e metade em ascensão, por
    uma comparação frouxa.
    """
    assert (
        classificar(
            status=StatusComercial.ATIVO,
            periodos=12,
            faturamentos=_v("900", "900", "1000"),
            posicao=300,
        )
        is Segmento.ESTAVEL
    )


def test_limiares_configuraveis_mudam_a_resposta():
    """Antecipa a H34: a regra lê os limiares, não os embute."""
    dados = {
        "status": StatusComercial.ATIVO,
        "periodos": 12,
        "faturamentos": _v("1000", "900", "950"),
        "posicao": 20,
    }

    assert classificar(**dados) is Segmento.ESTAVEL
    assert classificar(**dados, limiares=Limiares(top_n=25)) is Segmento.TOP


def test_sem_posicao_nao_e_top():
    """Parceiro sem métrica no período não tem posição — e não entra no Top."""
    assert (
        classificar(
            status=StatusComercial.ATIVO,
            periodos=12,
            faturamentos=_v("1000", "900", "950"),
            posicao=None,
        )
        is Segmento.ESTAVEL
    )


# ================================================= o reprocessamento (banco)
@pytest.fixture
def semear(criar_usuario):
    """Períodos, parceiros e métricas, no mesmo molde de `test_painel.py`.

    Cada semana é `{nome: faturamento}`; parceiro ausente numa semana não recebe
    métrica ali, que é como se produz histórico curto e lacuna.
    """
    autor_id = criar_usuario(login="semeador", perfil=Perfil.ANALISTA)

    def montar(*semanas: dict[str, str]) -> list[int]:
        ids = []
        s = Sessao()
        try:
            parceiros: dict[str, Parceiro] = {p.nome: p for p in s.query(Parceiro)}
            for indice, semana in enumerate(semanas):
                comeco = PRIMEIRA_SEMANA + timedelta(days=7 * indice)
                periodo = Periodo(data_inicio=comeco, data_fim=comeco + timedelta(days=6))
                s.add(periodo)
                s.flush()
                importacao = Importacao(
                    periodo_id=periodo.id,
                    usuario_id=autor_id,
                    origem=OrigemImportacao.TEXTO,
                    total_gravado=len(semana),
                    total_rejeitado=0,
                )
                s.add(importacao)
                s.flush()
                for nome, faturamento in semana.items():
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
                            pedidos=10,
                        )
                    )
                ids.append(periodo.id)
            s.commit()
            return ids
        finally:
            s.close()

    return montar


def _segmentos(periodo_id: int) -> dict[str, Segmento]:
    s = Sessao()
    try:
        return {
            nome: segmento
            for nome, segmento in s.execute(
                select(Parceiro.nome, HistoricoSegmento.segmento)
                .join(HistoricoSegmento, HistoricoSegmento.parceiro_id == Parceiro.id)
                .where(HistoricoSegmento.periodo_id == periodo_id)
            )
        }
    finally:
        s.close()


def test_reprocessar_grava_o_segmento_de_cada_parceiro(semear):
    """Três trajetórias, três segmentos — e a precedência no meio do caminho.

    O Top é 1 aqui, e não o 15 padrão, porque com três parceiros todos caberiam
    no Top 15 e o teste sairia com três TOP sem provar nada. Com Top N = 1, o
    maior faturamento do período é o "Caindo" — que mesmo assim sai EM_RISCO,
    porque risco vence topo (RN01).
    """
    ids = semear(
        {"Subindo": "100", "Caindo": "1000", "Parado": "500"},
        {"Subindo": "200", "Caindo": "900", "Parado": "500"},
        {"Subindo": "300", "Caindo": "800", "Parado": "500"},
    )

    s = Sessao()
    try:
        reprocessar(s, ids[-1], Limiares(top_n=1))
        s.commit()
    finally:
        s.close()

    gravados = _segmentos(ids[-1])
    assert gravados["Caindo"] is Segmento.EM_RISCO  # é o #1 do ranking, e ainda assim
    assert gravados["Subindo"] is Segmento.EM_ASCENSAO
    assert gravados["Parado"] is Segmento.ESTAVEL


def test_reprocessar_e_idempotente(semear):
    ids = semear({"Alfa": "100"}, {"Alfa": "200"}, {"Alfa": "300"})

    s = Sessao()
    try:
        primeira = reprocessar(s, ids[-1])
        s.commit()
        segunda = reprocessar(s, ids[-1])
        s.commit()
        total = s.scalar(
            select(Metrica.parceiro_id).where(Metrica.periodo_id == ids[-1])
        )
        assert total is not None
        linhas = s.scalars(
            select(HistoricoSegmento.id).where(HistoricoSegmento.periodo_id == ids[-1])
        ).all()
    finally:
        s.close()

    assert primeira == segunda
    # Não basta o resultado bater: gravar de novo não pode duplicar a linha.
    assert len(linhas) == 1


def test_so_classifica_quem_tem_metrica_no_periodo(semear):
    """Quem não aparece no relatório do período não tem o que classificar."""
    ids = semear(
        {"Presente": "100", "Sumido": "100"},
        {"Presente": "200", "Sumido": "100"},
        {"Presente": "300"},  # "Sumido" não veio nesta semana
    )

    s = Sessao()
    try:
        reprocessar(s, ids[-1])
        s.commit()
    finally:
        s.close()

    assert set(_segmentos(ids[-1])) == {"Presente"}


def test_historico_curto_e_recem_chegado(semear):
    ids = semear({"Novo": "100"}, {"Novo": "200"})

    s = Sessao()
    try:
        reprocessar(s, ids[-1])
        s.commit()
    finally:
        s.close()

    assert _segmentos(ids[-1])["Novo"] is Segmento.RECEM_CHEGADO


def test_prospeccao_vem_do_cadastro(semear):
    ids = semear({"Futuro": "100"}, {"Futuro": "200"}, {"Futuro": "300"})

    s = Sessao()
    try:
        parceiro = s.scalar(select(Parceiro).where(Parceiro.nome == "Futuro"))
        parceiro.status = StatusComercial.PROSPECCAO
        s.commit()
        reprocessar(s, ids[-1])
        s.commit()
    finally:
        s.close()

    assert _segmentos(ids[-1])["Futuro"] is Segmento.PROSPECCAO


def test_reprocessar_desde_alcanca_os_periodos_posteriores(semear):
    """Importar um período antigo muda a classificação dos que vieram depois."""
    ids = semear({"Alfa": "100"}, {"Alfa": "200"}, {"Alfa": "300"})

    s = Sessao()
    try:
        alcancados = reprocessar_desde(s, ids[0])
        s.commit()
    finally:
        s.close()

    assert alcancados == 3
    # O primeiro e o segundo período têm histórico curto; o terceiro, não.
    assert _segmentos(ids[0])["Alfa"] is Segmento.RECEM_CHEGADO
    assert _segmentos(ids[2])["Alfa"] is Segmento.TOP


def test_reprocessar_tudo_cobre_a_base_inteira(semear):
    ids = semear({"Alfa": "100"}, {"Alfa": "200"})

    s = Sessao()
    try:
        assert reprocessar_tudo(s) == 2
        s.commit()
    finally:
        s.close()

    assert _segmentos(ids[0]) and _segmentos(ids[1])


@pytest.mark.parametrize("funcao", [reprocessar, reprocessar_desde])
def test_periodo_inexistente_falha_alto(funcao):
    """Recusar explicando é melhor que seguir com dado parcial e calar."""
    s = Sessao()
    try:
        with pytest.raises(ValueError, match="não existe"):
            funcao(s, 999_999)
    finally:
        s.close()


@pytest.mark.parametrize("quantos", [5, 40])
def test_numero_de_consultas_nao_cresce_com_a_base(semear, quantos):
    """Anti-N+1, medido — o CLAUDE.md manda que esteja certo na primeira versão.

    Uma consulta por parceiro funciona com 100 e morre com 10.000 (RNF04), e o
    defeito não apareceria em nenhum outro teste: o resultado sairia correto, só
    lento. O limiar é colado no valor real (3: a agregada, o `DELETE` e o
    `INSERT`) porque folga larga deixaria o N+1 voltar sem reprovar.
    """
    semana = {f"P{i:03d}": f"{1000 + i}.00" for i in range(quantos)}
    ids = semear(semana, semana, semana)

    consultas: list[str] = []

    def anotar(conn, cursor, texto, parametros, contexto, muitos):  # noqa: ANN001
        consultas.append(texto)

    s = Sessao()
    event.listen(Engine, "before_cursor_execute", anotar)
    try:
        distribuicao = reprocessar(s, ids[-1])
        s.commit()
    finally:
        # Remover no `finally`: ouvinte vazado acumula consultas dos testes
        # seguintes, e este passa a reprovar por causa deles.
        event.remove(Engine, "before_cursor_execute", anotar)
        s.close()

    assert sum(distribuicao.values()) == quantos
    do_servico = [
        c for c in consultas if "metrica" in c.lower() or "historico_segmento" in c.lower()
    ]
    assert len(do_servico) <= 4, (
        f"{len(do_servico)} consultas para {quantos} parceiros — "
        "o número precisa ser fixo, não proporcional à base"
    )


# ============================================ o elo com a importação (H21+H33)
def test_importar_ja_deixa_o_periodo_segmentado(criar_usuario, autenticar, cliente):
    """Período gravado sem segmento é o pior dos mundos.

    O painel abriria com a distribuição faltando justamente a semana que o
    usuário acabou de importar — e sem erro nenhum na tela, que é a forma cara
    de errar neste domínio.
    """
    criar_usuario(login="analista", perfil=Perfil.ANALISTA)
    autenticar("analista")

    r = cliente.post(
        "/api/importacoes",
        json={
            "periodo_inicio": "2026-09-07",
            "periodo_fim": "2026-09-13",
            "texto": "Parceiro;Faturamento;Pedidos\nCasa Azul;1000,00;20",
        },
    )
    assert r.status_code == 201, r.text

    s = Sessao()
    try:
        periodo_id = s.scalar(select(Periodo.id).order_by(Periodo.id.desc()))
    finally:
        s.close()

    # Uma semana só de histórico: recém-chegado é a classificação certa.
    assert _segmentos(periodo_id) == {"Casa Azul": Segmento.RECEM_CHEGADO}


def test_substituir_um_periodo_reclassifica_o_que_ficou(criar_usuario, autenticar, cliente):
    """H25 + H33: trocar a métrica sem trocar o segmento deixaria a tela
    afirmando uma classificação apoiada em número que não existe mais."""
    criar_usuario(login="analista", perfil=Perfil.ANALISTA)
    autenticar("analista")
    periodo = {"periodo_inicio": "2026-09-07", "periodo_fim": "2026-09-13"}
    cabecalho = "Parceiro;Faturamento;Pedidos\n"

    cliente.post(
        "/api/importacoes",
        json={**periodo, "texto": cabecalho + "Casa Azul;1000,00;20"},
    )
    r = cliente.post(
        "/api/importacoes",
        json={**periodo, "texto": cabecalho + "Outro Nome;500,00;10", "substituir": True},
    )
    assert r.status_code == 201, r.text

    s = Sessao()
    try:
        periodo_id = s.scalar(select(Periodo.id).order_by(Periodo.id.desc()))
    finally:
        s.close()

    # O parceiro que saiu do período sai também da distribuição.
    assert set(_segmentos(periodo_id)) == {"Outro Nome"}


def test_janela_acompanha_o_limiar():
    """Três quedas exigem quatro pontos; a janela não pode ficar para trás."""
    assert PADRAO.janela == PADRAO.periodos_tendencia + 1
    assert Limiares(periodos_tendencia=3).janela == 4
