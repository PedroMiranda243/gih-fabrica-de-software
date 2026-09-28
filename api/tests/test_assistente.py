"""O assistente analítico — UC12, RF41, história H65 (ADR-013).

O modelo de linguagem é sempre de mentira aqui (`ModeloFalso`): ele devolve a
extração que o teste mandar. O que se testa é o que a API faz com ela — a
resolução contra a base, a precisão e a abstenção, e as respostas, que precisam
trazer os números das telas e só números que estão nos fatos (RN08).

A rede é a da campanha (`tests/rede.py`): cinco semanas, de 01/06/2026 a
05/07/2026, com o segmento só na mais recente.
"""
from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app import redator
from app.assistente import resolucao
from app.assistente.catalogo import (
    CATALOGO,
    CAUSA,
    COMPARACAO,
    CONTA,
    DATA_ISO,
    Extracao,
    abstencao_pelo_codigo,
    instrucao,
)
from app.assistente.redacao import (
    LONGO,
    NUMEROS_SEM_ORIGEM,
    SENTIDO_TROCADO,
    UNIDADE_SEM_ORIGEM,
)
from app.assistente.servico import (
    FORA_DO_CATALOGO,
    NAO_ENTENDI,
    SEM_DADOS,
    SEM_PARCEIRO,
    SEM_SEGMENTO,
)
from app.db import Sessao
from app.esquemas import TipoPergunta
from app.formato import probabilidade
from app.guarda_numerica import numeros_sem_origem
from app.modelos import (
    Importacao,
    Metrica,
    OrigemImportacao,
    Parceiro,
    Perfil,
    Periodo,
    Segmento,
)
from app.redator import DEMOROU, FORA_DO_AR, ILEGIVEL, SEM_ENDERECO, Estado, FalhaDoRedator
from tests.rede import parceiro as _parceiro
from tests.test_campanha import _calcular

MODELO = "modelo-falso:1b"
PERGUNTAS = "/api/assistente/perguntas"
# O modelo escreve todo campo; o teste só diz os que não são nulos.
VAZIA = dict.fromkeys(Extracao.model_fields)


def _repete(pedido: str) -> str:
    """A redação que só repete a resposta do sistema: o texto sai igual, pelo modelo."""
    return next(
        linha.removeprefix("Resposta do sistema: ")
        for linha in pedido.splitlines()
        if linha.startswith("Resposta do sistema: ")
    )


class ModeloFalso:
    """Um modelo que devolve a extração e a redação que o teste mandar, e guarda o que
    recebeu. Sem redação dada, ele repete a resposta do sistema."""

    def __init__(
        self, extracao=None, *, disponivel=True, motivo=None, falha=None, redacao=_repete,
        falha_na_redacao=None,
    ):
        self.modelo = MODELO
        self.extracao = extracao or {"tipo": "fora_do_catalogo"}
        self.disponivel = disponivel
        self.motivo = motivo
        self.falha = falha
        self.redacao = redacao
        self.falha_na_redacao = falha_na_redacao
        self.pedidos: list[tuple[str, str]] = []
        self.redacoes: list[tuple[str, str]] = []

    def redigir(self, sistema, pedido):
        self.redacoes.append((sistema, pedido))
        if self.falha_na_redacao:
            raise FalhaDoRedator(self.falha_na_redacao)
        return self.redacao(pedido)

    def estado(self):
        return Estado(self.disponivel, MODELO, self.motivo)

    def extrair(self, sistema, pergunta, esquema):
        self.pedidos.append((sistema, pergunta))
        if self.falha:
            raise FalhaDoRedator(self.falha)
        return esquema.model_validate({**VAZIA, **self.extracao})


@pytest.fixture
def modelo(monkeypatch):
    """Troca o modelo de linguagem da aplicação pelo que o teste montar."""

    def trocar(falso: ModeloFalso) -> ModeloFalso:
        monkeypatch.setattr(redator, "atual", lambda: falso)
        return falso

    return trocar


@pytest.fixture
def gestor(criar_usuario, autenticar):
    criar_usuario(login="gestora", perfil=Perfil.GESTOR, nome="Gestora")
    return autenticar("gestora")


@pytest.fixture
def analista(criar_usuario, autenticar):
    criar_usuario(login="analista", perfil=Perfil.ANALISTA, nome="Analista")
    return autenticar("analista")


def _rede():
    return [
        _parceiro(
            "Esquina da Serra", "9000", previsto="9500", risco=0.125, categoria="Pizzaria",
            segmento=Segmento.TOP,
        ),
        _parceiro(
            "Cantina Central", "7000", previsto="6800", risco=0.6, categoria="Mercado",
            segmento=Segmento.EM_RISCO,
        ),
        _parceiro("Cantina Verde", "5000", categoria="Mercado", segmento=Segmento.EM_RISCO),
        # Chegou há duas semanas: a evolução dele começa na primeira medição.
        _parceiro("Forno do Vale", "3000", periodos=2, segmento=Segmento.ESTAVEL),
        # Faltou no relatório mais recente.
        _parceiro("Ponto Real", "2000", na_base=False),
    ]


@pytest.fixture
def rede(base):
    return base(_rede())


def _perguntar(cliente, texto, **extracao):
    r = cliente.post(PERGUNTAS, json={"texto": texto})
    assert r.status_code == 200, r.text
    return r.json()


def _fatos(corpo):
    return [{"fato": f["fato"], "valor": f["valor"]} for f in corpo["fatos"]]


def _respondida(corpo):
    """Respondida, e com todo número do texto nos fatos (RN08)."""
    assert corpo["situacao"] == "RESPONDIDA", corpo
    assert numeros_sem_origem(corpo["texto"], _fatos(corpo)) == [], corpo["texto"]
    return corpo["texto"]


# ======================================================================= puros
@pytest.mark.parametrize(
    ("valor", "texto"),
    [(0.004, "menos de 1%"), (0.125, "13%"), (0.6, "60%"), (0.995, "mais de 99%")],
)
def test_a_probabilidade_arredonda_como_a_tela(valor, texto):
    """12,5% é 13% na tela (`Math.round`); o `round` do Python daria 12%."""
    assert probabilidade(valor) == texto


@pytest.mark.parametrize(
    ("termo", "pergunta", "citado"),
    [
        ("Esquina da Serra", "Quanto a esquina da serra faturou?", True),
        ("Açaí do Porto", "e o acai do porto, como foi?", True),
        ("Serra Esquina", "Quanto a Esquina da Serra faturou?", True),
        ("catálogo_geográfico", "Qual a capital da França?", False),
        ("Esquina da Serra", "Quanto a Esquina faturou?", False),
        ("", "Quanto a Esquina faturou?", False),
    ],
)
def test_o_parceiro_precisa_estar_na_pergunta(termo, pergunta, citado):
    """A sonda da ADR-013 pegou o modelo inventando o parceiro "catálogo_geográfico"."""
    assert resolucao.citado(termo, pergunta) is citado


@pytest.mark.parametrize(
    ("pedido", "quantos"), [(None, 10), (0, 10), (-3, 10), (5, 5), (20, 20), (500, 20)]
)
def test_a_lista_cabe_numa_resposta(pedido, quantos):
    assert resolucao.quantos(pedido) == quantos


def test_a_instrucao_traz_o_catalogo_as_categorias_e_as_datas():
    texto = instrucao(
        ["Mercado", "Pizzaria"],
        [(date(2026, 9, 7), date(2026, 9, 13)), (date(2026, 9, 14), date(2026, 9, 20))],
    )
    for entrada in CATALOGO.values():
        assert f"- {entrada.tipo}: " in texto and entrada.exemplo in texto
    assert "- fora_do_catalogo: " in texto
    assert "Mercado, Pizzaria" in texto
    assert '"nesta semana" e "na última semana" são 2026-09-14 e 2026-09-20' in texto
    assert '"na semana passada" e "no período anterior", 2026-09-07 e 2026-09-13' in texto
    assert '"em agosto", 2026-08-01 e 2026-08-31' in texto
    assert '"na semana de 10 de agosto", 2026-08-10 e 2026-08-10' in texto
    assert "Sem o ano, use 2026" in texto


def test_o_modelo_escreve_todo_campo_e_a_data_no_formato():
    """Com os campos opcionais, o modelo fechava o JSON depois do tipo, e nenhuma data
    chegava (sonda do H65). O padrão da data entra na gramática da saída."""
    esquema = Extracao.model_json_schema()
    assert set(esquema["required"]) == set(Extracao.model_fields)
    assert esquema["properties"]["inicio"]["anyOf"][0]["pattern"] == DATA_ISO
    with pytest.raises(ValidationError):
        Extracao.model_validate({**VAZIA, "tipo": "ranking", "inicio": "log(2026-09-07)"})


def test_com_um_periodo_so_nao_ha_periodo_anterior_na_instrucao():
    texto = instrucao(["Mercado"], [(date(2026, 9, 14), date(2026, 9, 20))])
    assert '"no período anterior"' not in texto
    assert "vão de 14/09/2026 a 20/09/2026" in texto


# ============================================================ a rota e o estado
def test_o_estado_diz_por_que_o_modelo_nao_esta_no_ar(analista):
    corpo = analista.get("/api/assistente").json()
    assert corpo["assistente"] == {
        "disponivel": False, "modelo": "qwen2.5:7b", "motivo": SEM_ENDERECO
    }
    assert [e["tipo"] for e in corpo["exemplos"]] == [t.value for t in CATALOGO]
    assert corpo["tamanho_maximo"] == 1000


def test_os_exemplos_da_tela_sao_os_que_o_modelo_ve(gestor, modelo):
    modelo(ModeloFalso())
    corpo = gestor.get("/api/assistente").json()
    assert corpo["assistente"]["disponivel"] is True
    assert {e["exemplo"] for e in corpo["exemplos"]} == {e.exemplo for e in CATALOGO.values()}


def test_a_pergunta_acima_do_limite_e_recusada_com_o_limite(analista):
    """UC12-E2, RNF15."""
    r = analista.post(PERGUNTAS, json={"texto": "a" * 1001})
    assert r.status_code == 422
    assert r.json()["campos"] == [
        {"campo": "texto", "mensagem": "Longo demais: use no máximo 1000 caracteres."}
    ]


def test_a_pergunta_em_branco_e_recusada(analista):
    r = analista.post(PERGUNTAS, json={"texto": "   "})
    assert r.status_code == 422
    assert r.json()["campos"][0]["mensagem"] == "Escreva a pergunta."


@pytest.mark.parametrize("perfil", [Perfil.ADMINISTRADOR, Perfil.PARCEIRO])
def test_so_gestor_e_analista_perguntam(rede, criar_usuario, autenticar, perfil):
    vinculo = rede.parceiros["Esquina da Serra"] if perfil is Perfil.PARCEIRO else None
    criar_usuario(login="outro", perfil=perfil, parceiro_id=vinculo)
    cliente = autenticar("outro")
    assert cliente.post(PERGUNTAS, json={"texto": "Como foi a rede?"}).status_code == 403
    assert cliente.get("/api/assistente").status_code == 403


def test_o_gestor_tem_a_tela_do_assistente(gestor):
    assert "assistente" in gestor.get("/api/sessao/atual").json()["telas"]


# ================================================ antes de perguntar ao modelo
def test_sem_dados_nem_pergunta_ao_modelo(analista, modelo):
    """Carregar o modelo custaria dezenas de segundos para dizer que não há dados."""
    falso = modelo(ModeloFalso())
    corpo = _perguntar(analista, "Como foi a rede na semana passada?")
    assert corpo["situacao"] == "ABSTENCAO" and corpo["texto"] == SEM_DADOS
    assert falso.pedidos == []


def test_sem_o_modelo_o_assistente_se_diz_indisponivel(rede, analista):
    """UC12-E1: o motivo, e o resto do sistema segue."""
    corpo = _perguntar(analista, "Como foi a rede na semana passada?")
    assert corpo["situacao"] == "INDISPONIVEL"
    assert corpo["tipo"] is None
    assert SEM_ENDERECO in corpo["texto"]
    assert "O painel e as outras telas seguem funcionando." in corpo["texto"]
    assert analista.get("/api/painel/indicadores").status_code == 200


def test_o_modelo_que_demora_deixa_o_assistente_indisponivel(rede, analista, modelo):
    modelo(ModeloFalso(falha=DEMOROU.format(s=120)))
    corpo = _perguntar(analista, "Como foi a rede?")
    assert corpo["situacao"] == "INDISPONIVEL" and "120 s" in corpo["texto"]


def test_a_resposta_ilegivel_do_modelo_pede_outra_pergunta(rede, analista, modelo):
    modelo(ModeloFalso(falha=ILEGIVEL))
    corpo = _perguntar(analista, "asdf qwer")
    assert corpo == {
        "situacao": "ABSTENCAO", "tipo": None, "texto": NAO_ENTENDI, "fonte": None,
        "redator": "MODELO_FIXO", "motivo": None, "fatos": [], "candidatos": [],
    }


def test_o_modelo_recebe_a_pergunta_e_o_contexto_da_base(rede, analista, modelo):
    falso = modelo(ModeloFalso())
    _perguntar(analista, "  Como foi a rede?  ")
    sistema, pergunta = falso.pedidos[0]
    assert pergunta == "Como foi a rede?"
    assert "Mercado, Pizzaria" in sistema
    assert '"nesta semana" e "na última semana" são 2026-06-29 e 2026-07-05' in sistema


# ======================================================== abstenção e precisão
def test_fora_do_catalogo_o_assistente_se_abstem(rede, analista, modelo):
    modelo(ModeloFalso({"tipo": "fora_do_catalogo"}))
    corpo = _perguntar(analista, "Qual a capital da França?")
    assert corpo["situacao"] == "ABSTENCAO"
    assert corpo["tipo"] == "fora_do_catalogo"
    assert corpo["texto"] == FORA_DO_CATALOGO


def test_parceiro_inventado_pelo_modelo_e_abstencao(rede, analista, modelo):
    """O caso da sonda: o parceiro não está na pergunta — a classificação inteira é suspeita."""
    modelo(ModeloFalso({"tipo": "segmento_do_parceiro", "parceiro": "Esquina da Serra"}))
    corpo = _perguntar(analista, "Qual a capital da França?")
    assert corpo["situacao"] == "ABSTENCAO"
    assert corpo["tipo"] == "fora_do_catalogo"


def test_sem_o_parceiro_pede_qual(rede, analista, modelo):
    modelo(ModeloFalso({"tipo": "desempenho_do_parceiro"}))
    corpo = _perguntar(analista, "Quanto ele faturou?")
    assert corpo["situacao"] == "PRECISAO" and corpo["texto"] == SEM_PARCEIRO


def test_varios_parceiros_com_o_nome_pedem_qual(rede, analista, modelo):
    modelo(ModeloFalso({"tipo": "desempenho_do_parceiro", "parceiro": "Cantina"}))
    corpo = _perguntar(analista, "Quanto a Cantina faturou?")
    assert corpo["situacao"] == "PRECISAO"
    assert corpo["texto"] == 'Há 2 parceiros com "Cantina" no nome. De qual deles?'
    assert corpo["candidatos"] == ["Cantina Central", "Cantina Verde"]


def test_o_nome_exato_vence_o_parcial(base, analista, modelo):
    base([_parceiro("Casa Real", "1000"), _parceiro("Casa Real Lanches", "900")])
    modelo(ModeloFalso({"tipo": "desempenho_do_parceiro", "parceiro": "casa real"}))
    texto = _respondida(_perguntar(analista, "Quanto a casa real faturou?"))
    assert texto.startswith("Casa Real faturou R$ 1.000,00")


def test_o_artigo_copiado_com_o_nome_nao_atrapalha(rede, analista, modelo):
    """Na sonda do H65, o modelo devolveu "A Esquina da Serra"."""
    modelo(ModeloFalso({"tipo": "segmento_do_parceiro", "parceiro": "A Esquina da Serra"}))
    texto = _respondida(_perguntar(analista, "A Esquina da Serra está em risco?"))
    assert texto.startswith("Em 29/06/2026 a 05/07/2026, Esquina da Serra está no segmento Top 15.")


def test_o_parceiro_que_se_chama_com_o_artigo_e_achado_pelo_nome(base, analista, modelo):
    base([_parceiro("O Casarão", "1000"), _parceiro("Casarão Lanches", "900")])
    modelo(ModeloFalso({"tipo": "desempenho_do_parceiro", "parceiro": "o casarão"}))
    texto = _respondida(_perguntar(analista, "Quanto o casarão faturou?"))
    assert texto.startswith("O Casarão faturou R$ 1.000,00")


def test_um_so_parcial_e_o_parceiro(rede, analista, modelo):
    modelo(ModeloFalso({"tipo": "desempenho_do_parceiro", "parceiro": "Forno"}))
    assert _respondida(_perguntar(analista, "Quanto o Forno faturou?")).startswith("Forno do Vale")


def test_o_nome_com_erro_de_digitacao_sugere_os_parecidos(rede, analista, modelo):
    modelo(ModeloFalso({"tipo": "desempenho_do_parceiro", "parceiro": "Esquna da Sera"}))
    corpo = _perguntar(analista, "Quanto a Esquna da Sera faturou?")
    assert corpo["situacao"] == "PRECISAO"
    assert corpo["candidatos"][0] == "Esquina da Serra"


def test_o_parceiro_que_nao_existe_e_abstencao(rede, analista, modelo):
    modelo(ModeloFalso({"tipo": "desempenho_do_parceiro", "parceiro": "Xyzw Qwerty"}))
    corpo = _perguntar(analista, "Quanto a Xyzw Qwerty faturou?")
    assert corpo["situacao"] == "ABSTENCAO"
    assert corpo["texto"] == 'Não há parceiro chamado "Xyzw Qwerty" na base.'


def test_sem_o_segmento_pede_qual(rede, analista, modelo):
    modelo(ModeloFalso({"tipo": "parceiros_do_segmento"}))
    corpo = _perguntar(analista, "Quais parceiros estão nesse segmento?")
    assert corpo["situacao"] == "PRECISAO" and corpo["texto"] == SEM_SEGMENTO
    assert "Em risco" in corpo["candidatos"]


def test_a_categoria_no_plural_e_a_categoria(rede, analista, modelo):
    modelo(ModeloFalso({"tipo": "ranking", "categoria": "pizzarias"}))
    texto = _respondida(_perguntar(analista, "Quais pizzarias mais faturaram?"))
    assert texto.startswith("Os maiores faturamentos na categoria Pizzaria")


def test_a_categoria_que_nao_existe_pede_qual(rede, analista, modelo):
    modelo(ModeloFalso({"tipo": "ranking", "categoria": "Sushi"}))
    corpo = _perguntar(analista, "Quais os sushis que mais faturaram?")
    assert corpo["situacao"] == "PRECISAO"
    assert corpo["candidatos"] == ["Mercado", "Pizzaria"]


# ================================================================== o período
def test_sem_data_vale_o_periodo_mais_recente(rede, analista, modelo):
    modelo(ModeloFalso({"tipo": "resumo_do_periodo"}))
    assert "Em 29/06/2026 a 05/07/2026" in _respondida(_perguntar(analista, "Como foi a rede?"))


def test_uma_data_escolhe_a_semana_que_a_contem(rede, analista, modelo):
    modelo(ModeloFalso({"tipo": "resumo_do_periodo", "inicio": "2026-06-10"}))
    texto = _respondida(_perguntar(analista, "Como foi a rede no dia 10 de junho?"))
    assert texto.startswith("Em 08/06/2026 a 14/06/2026")


def test_um_mes_em_pergunta_de_uma_semana_pede_qual(rede, analista, modelo):
    """Somar as semanas seria conta que o catálogo não faz; escolher uma, outra pergunta."""
    extracao = {"tipo": "resumo_do_periodo", "inicio": "2026-06-01", "fim": "2026-06-30"}
    modelo(ModeloFalso(extracao))
    corpo = _perguntar(analista, "Como foi a rede em junho?")
    assert corpo["situacao"] == "PRECISAO"
    assert corpo["texto"] == (
        "Os dados são semanais, e de 01/06/2026 a 30/06/2026 há 5 períodos. De qual deles?"
    )
    assert corpo["candidatos"][0] == "01/06/2026 a 07/06/2026"
    assert len(corpo["candidatos"]) == 5
    assert numeros_sem_origem(corpo["texto"], _fatos(corpo)) == []


def test_data_sem_dados_e_abstencao_com_o_que_ha(rede, analista, modelo):
    modelo(ModeloFalso({"tipo": "resumo_do_periodo", "inicio": "2025-01-01"}))
    corpo = _perguntar(analista, "Como foi a rede em 1º de janeiro de 2025?")
    assert corpo["situacao"] == "ABSTENCAO"
    assert corpo["texto"] == (
        "Não há dados de 01/01/2025. Os períodos importados vão de 01/06/2026 a 05/07/2026."
    )


def test_data_impossivel_pede_a_semana(rede, analista, modelo):
    modelo(ModeloFalso({"tipo": "resumo_do_periodo", "inicio": "2026-02-30"}))
    corpo = _perguntar(analista, "Como foi a rede em 30 de fevereiro?")
    assert corpo["situacao"] == "PRECISAO"
    assert corpo["candidatos"][0] == "29/06/2026 a 05/07/2026"


# ================================================================= as respostas
EXTRACOES = {
    TipoPergunta.DESEMPENHO_DO_PARCEIRO: {"parceiro": "Esquina da Serra"},
    TipoPergunta.EVOLUCAO_DO_PARCEIRO: {"parceiro": "Esquina da Serra"},
    TipoPergunta.POSICAO_DO_PARCEIRO: {"parceiro": "Esquina da Serra"},
    TipoPergunta.SEGMENTO_DO_PARCEIRO: {"parceiro": "Esquina da Serra"},
    TipoPergunta.PREVISAO_DO_PARCEIRO: {"parceiro": "Esquina da Serra"},
    TipoPergunta.RANKING: {"categoria": "Mercado"},
    TipoPergunta.PARCEIROS_DO_SEGMENTO: {"segmento": "EM_RISCO"},
    TipoPergunta.MOBILIDADE_DO_TOP: {},
    TipoPergunta.RESUMO_DO_PERIODO: {},
    TipoPergunta.DISTRIBUICAO_DOS_SEGMENTOS: {},
    TipoPergunta.ULTIMO_PLANO: {},
}


def test_todo_tipo_do_catalogo_tem_resposta():
    assert set(EXTRACOES) == set(CATALOGO)


@pytest.mark.parametrize("tipo", list(EXTRACOES))
def test_toda_resposta_so_tem_numero_dos_fatos(rede, gestor, modelo, tipo):
    """RN08: o modelo fixo de cada tipo é o que a guarda vai aceitar sem conferir."""
    if tipo is TipoPergunta.ULTIMO_PLANO:
        _calcular(gestor)
    modelo(ModeloFalso({"tipo": tipo, **EXTRACOES[tipo]}))
    corpo = _perguntar(gestor, "Pergunta sobre a Esquina da Serra")
    assert corpo["tipo"] == tipo
    _respondida(corpo)


def test_o_desempenho_com_a_variacao(rede, analista, modelo):
    with Sessao() as s:
        penultima = s.scalars(select(Periodo).order_by(Periodo.data_inicio.desc())).all()[1]
        metrica = s.scalar(
            select(Metrica).where(
                Metrica.parceiro_id == rede.parceiros["Esquina da Serra"],
                Metrica.periodo_id == penultima.id,
            )
        )
        metrica.faturamento = Decimal("8000.00")
        s.commit()
    modelo(ModeloFalso({"tipo": "desempenho_do_parceiro", "parceiro": "Esquina da Serra"}))
    texto = _respondida(_perguntar(analista, "Quanto a Esquina da Serra faturou?"))
    assert texto == (
        "Esquina da Serra faturou R$ 9.000,00 em 10 pedidos de 29/06/2026 a 05/07/2026, com "
        "ticket médio de R$ 900,00. No período anterior, de 22/06/2026 a 28/06/2026, tinha "
        "faturado R$ 8.000,00: uma variação de +12,50%."
    )


def test_o_desempenho_de_quem_faltou_no_relatorio_e_abstencao(rede, analista, modelo):
    modelo(ModeloFalso({"tipo": "desempenho_do_parceiro", "parceiro": "Ponto Real"}))
    corpo = _perguntar(analista, "Quanto o Ponto Real faturou?")
    assert corpo["situacao"] == "ABSTENCAO"
    assert corpo["texto"].startswith("O relatório de 29/06/2026 a 05/07/2026 não trouxe Ponto Real")


def test_o_desempenho_no_primeiro_periodo_nao_compara(rede, analista, modelo):
    extracao = {"tipo": "desempenho_do_parceiro", "parceiro": "Ponto Real", "inicio": "2026-06-01"}
    modelo(ModeloFalso(extracao))
    texto = _respondida(_perguntar(analista, "Quanto o Ponto Real faturou em 1º de junho?"))
    assert texto.endswith("É o primeiro período importado: não há com o que comparar.")


def test_a_evolucao_comeca_na_primeira_medicao(rede, analista, modelo):
    modelo(ModeloFalso({"tipo": "evolucao_do_parceiro", "parceiro": "Forno do Vale"}))
    texto = _respondida(_perguntar(analista, "Como evoluiu o Forno do Vale?"))
    assert texto == (
        "O faturamento de Forno do Vale, período a período:\n"
        "- 22/06/2026 a 28/06/2026: R$ 3.000,00 em 10 pedidos\n"
        "- 29/06/2026 a 05/07/2026: R$ 3.000,00 em 10 pedidos"
    )


def test_a_evolucao_num_intervalo_mostra_a_falta_como_lacuna(rede, analista, modelo):
    extracao = {
        "tipo": "evolucao_do_parceiro", "parceiro": "Ponto Real",
        "inicio": "2026-06-22", "fim": "2026-07-05",
    }
    modelo(ModeloFalso(extracao))
    texto = _respondida(_perguntar(analista, "Como evoluiu o Ponto Real no fim de junho?"))
    assert texto.endswith("- 29/06/2026 a 05/07/2026: sem dados")


def test_a_posicao_e_a_do_ranking_do_painel(rede, analista, modelo):
    modelo(ModeloFalso({"tipo": "posicao_do_parceiro", "parceiro": "Cantina Verde"}))
    texto = _respondida(_perguntar(analista, "Em que posição está a Cantina Verde?"))
    painel = analista.get("/api/painel/ranking").json()
    posicao = next(i["posicao"] for i in painel["itens"] if i["nome"] == "Cantina Verde")
    assert texto.startswith(
        f"Cantina Verde ficou em {posicao}º lugar no ranking de faturamento de 29/06/2026 a "
        f"05/07/2026, entre {painel['total']} parceiros com faturamento."
    )


def test_o_segmento_fora_do_periodo_segmentado_e_abstencao(rede, analista, modelo):
    extracao = {
        "tipo": "segmento_do_parceiro", "parceiro": "Esquina da Serra", "inicio": "2026-06-10"
    }
    modelo(ModeloFalso(extracao))
    corpo = _perguntar(analista, "A Esquina da Serra estava em risco em 10 de junho?")
    assert corpo["situacao"] == "ABSTENCAO"


def test_a_previsao_e_a_do_modelo_em_uso(rede, analista, modelo):
    modelo(ModeloFalso({"tipo": "previsao_do_parceiro", "parceiro": "Esquina da Serra"}))
    texto = _respondida(_perguntar(analista, "A Esquina da Serra vai cair?"))
    assert texto == (
        "Pelo modelo rede-1, treinado com os dados até 29/06/2026 a 05/07/2026, a probabilidade "
        "de Esquina da Serra estar em risco no período seguinte, de 06/07/2026 a 12/07/2026, é "
        "de 13%, e o faturamento previsto para ele é de R$ 9.500,00."
    )


def test_sem_previsao_diz_por_que(rede, analista, modelo):
    modelo(ModeloFalso({"tipo": "previsao_do_parceiro", "parceiro": "Cantina Verde"}))
    corpo = _perguntar(analista, "A Cantina Verde vai cair?")
    assert corpo["situacao"] == "ABSTENCAO"
    assert corpo["texto"].startswith("Não há previsão para Cantina Verde.")


def test_o_ranking_da_rede_e_o_do_painel(rede, analista, modelo):
    modelo(ModeloFalso({"tipo": "ranking", "quantos": 2}))
    texto = _respondida(_perguntar(analista, "Quem são os 2 maiores?"))
    assert texto == (
        "Os maiores faturamentos em 29/06/2026 a 05/07/2026:\n"
        "1º Esquina da Serra — R$ 9.000,00\n"
        "2º Cantina Central — R$ 7.000,00\n"
        "São 4 parceiros com faturamento; o ranking inteiro está no painel."
    )


def test_o_ranking_da_categoria_mostra_a_posicao_na_rede(rede, analista, modelo):
    modelo(ModeloFalso({"tipo": "ranking", "categoria": "Mercado"}))
    texto = _respondida(_perguntar(analista, "Quais mercados mais faturaram?"))
    assert texto == (
        "Os maiores faturamentos na categoria Mercado em 29/06/2026 a 05/07/2026:\n"
        "1º Cantina Central — R$ 7.000,00 (2º na rede)\n"
        "2º Cantina Verde — R$ 5.000,00 (3º na rede)"
    )


def test_os_parceiros_do_segmento_do_maior_para_o_menor(rede, analista, modelo):
    modelo(ModeloFalso({"tipo": "parceiros_do_segmento", "segmento": "EM_RISCO"}))
    texto = _respondida(_perguntar(analista, "Quem está em risco?"))
    assert texto == (
        "Em 29/06/2026 a 05/07/2026, 2 parceiros estão no segmento Em risco:\n"
        "- Cantina Central: R$ 7.000,00\n"
        "- Cantina Verde: R$ 5.000,00"
    )


def test_nenhum_parceiro_no_segmento_e_resposta_e_nao_abstencao(rede, analista, modelo):
    """Com a segmentação calculada, zero é a resposta."""
    extracao = {"tipo": "parceiros_do_segmento", "segmento": "EM_RISCO", "categoria": "Pizzaria"}
    modelo(ModeloFalso(extracao))
    texto = _respondida(_perguntar(analista, "Quais pizzarias estão em risco?"))
    assert texto == (
        "Em 29/06/2026 a 05/07/2026, nenhum parceiro da categoria Pizzaria está no segmento "
        "Em risco."
    )


def test_segmento_sem_segmentacao_calculada_e_abstencao(rede, analista, modelo):
    """Sem a segmentação, "nenhum" afirmaria uma distribuição que ninguém calculou."""
    extracao = {"tipo": "parceiros_do_segmento", "segmento": "EM_RISCO", "inicio": "2026-06-10"}
    modelo(ModeloFalso(extracao))
    corpo = _perguntar(analista, "Quem estava em risco em 10 de junho?")
    assert corpo["situacao"] == "ABSTENCAO"
    assert corpo["texto"] == (
        "O período de 08/06/2026 a 14/06/2026 ainda não tem segmentação calculada."
    )


def test_a_mobilidade_e_a_do_ranking(base, analista, modelo):
    """RN02: quem entrou e quem saiu, pela posição — a mesma função do painel."""
    base(
        [
            _parceiro("Esquina da Serra", "9000"),
            _parceiro("Cantina Central", "7000"),
            _parceiro("Novato Express", "9500", periodos=1),
        ],
        top_n=2,
    )
    modelo(ModeloFalso({"tipo": "mobilidade_do_top"}))
    texto = _respondida(_perguntar(analista, "Quem entrou no Top?"))
    assert texto == (
        "De 22/06/2026 a 28/06/2026 para 29/06/2026 a 05/07/2026, entrou no Top 2: Novato "
        "Express (1º); e saiu: Cantina Central (agora em 3º)."
    )


def test_quem_faltou_no_relatorio_sai_do_top_sem_faturamento(rede, analista, modelo):
    modelo(ModeloFalso({"tipo": "mobilidade_do_top"}))
    texto = _respondida(_perguntar(analista, "Quem saiu do Top?"))
    assert texto == (
        "De 22/06/2026 a 28/06/2026 para 29/06/2026 a 05/07/2026, saiu: Ponto Real (sem "
        "faturamento no período)."
    )


def test_sem_movimento_no_top_diz_que_ninguem_entrou(base, analista, modelo):
    base([_parceiro("Esquina da Serra", "9000"), _parceiro("Cantina Central", "7000")])
    modelo(ModeloFalso({"tipo": "mobilidade_do_top"}))
    texto = _respondida(_perguntar(analista, "Quem entrou no Top?"))
    assert texto.endswith("ninguém entrou nem saiu do Top 15.")


def test_a_mobilidade_no_primeiro_periodo_e_abstencao(rede, analista, modelo):
    modelo(ModeloFalso({"tipo": "mobilidade_do_top", "inicio": "2026-06-01"}))
    corpo = _perguntar(analista, "Quem entrou no Top em 1º de junho?")
    assert corpo["situacao"] == "ABSTENCAO"


def test_o_resumo_traz_os_numeros_do_painel(rede, analista, modelo):
    modelo(ModeloFalso({"tipo": "resumo_do_periodo"}))
    texto = _respondida(_perguntar(analista, "Como foi a rede?"))
    painel = analista.get("/api/painel/indicadores").json()
    assert painel["faturamento"] == "24000.00"
    assert texto == (
        "Em 29/06/2026 a 05/07/2026, a rede faturou R$ 24.000,00 em 40 pedidos, com ticket "
        "médio de R$ 600,00, e 4 parceiros tiveram movimento. Contra o período anterior, de "
        "22/06/2026 a 28/06/2026: faturamento -7,69%, pedidos -20,00%, ticket médio +15,38%. "
        "2 parceiros estão em risco."
    )


def test_a_distribuicao_dos_segmentos(rede, analista, modelo):
    modelo(ModeloFalso({"tipo": "distribuicao_dos_segmentos"}))
    texto = _respondida(_perguntar(analista, "Como os parceiros se dividem?"))
    assert texto == (
        "Os parceiros por segmento em 29/06/2026 a 05/07/2026, num total de 4:\n"
        "- Em risco: 2\n"
        "- Top 15: 1\n"
        "- Estável: 1"
    )


def test_sem_plano_calculado_e_abstencao(rede, analista, modelo):
    modelo(ModeloFalso({"tipo": "ultimo_plano"}))
    corpo = _perguntar(analista, "Qual o ganho do último plano?")
    assert corpo["situacao"] == "ABSTENCAO"
    assert corpo["texto"] == "Nenhum plano de campanha foi calculado ainda."


def test_o_ultimo_plano_traz_os_numeros_da_campanha(rede, gestor, modelo):
    plano = _calcular(gestor)
    modelo(ModeloFalso({"tipo": "ultimo_plano"}))
    texto = _respondida(_perguntar(gestor, "Qual o ganho do último plano?"))
    ganho = f"{Decimal(plano['uplift_total']):,.2f}".replace(",", "_").replace(".", ",")
    assert f"ganho esperado de R$ {ganho.replace('_', '.')}" in texto
    assert texto.startswith("O último plano calculado, para aplicar de 06/07/2026 a 12/07/2026")
    assert "do orçamento de R$ 500,00" in texto


def test_o_assistente_nao_grava_nada(rede, analista, modelo):
    """UC12: consulta, sem pós-condição."""
    modelo(ModeloFalso({"tipo": "resumo_do_periodo"}))
    with Sessao() as s:
        antes = (s.query(Parceiro).count(), s.query(Metrica).count())
    _perguntar(analista, "Como foi a rede?")
    with Sessao() as s:
        assert (s.query(Parceiro).count(), s.query(Metrica).count()) == antes



# ============================================================ a fonte (H66)
@pytest.mark.parametrize("tipo", list(EXTRACOES))
def test_toda_resposta_com_numeros_traz_a_fonte(rede, gestor, modelo, tipo):
    """RF42: o período e a origem, montados pelo código."""
    if tipo is TipoPergunta.ULTIMO_PLANO:
        _calcular(gestor)
    modelo(ModeloFalso({"tipo": tipo, **EXTRACOES[tipo]}))
    corpo = _perguntar(gestor, "Pergunta sobre a Esquina da Serra")
    assert corpo["situacao"] == "RESPONDIDA"
    fonte = corpo["fonte"]
    assert fonte["texto"] and fonte["relatorios"]
    for relatorio in fonte["relatorios"]:
        assert relatorio["importado_por"] == "Semeador"
        assert relatorio["origem"] == "TEXTO" and relatorio["importado_em"]


def test_a_fonte_do_desempenho_sao_os_dois_relatorios(rede, analista, modelo):
    modelo(ModeloFalso({"tipo": "desempenho_do_parceiro", "parceiro": "Esquina da Serra"}))
    fonte = _perguntar(analista, "Quanto a Esquina da Serra faturou?")["fonte"]
    assert fonte["texto"] == "Relatórios de 22/06/2026 a 28/06/2026 e de 29/06/2026 a 05/07/2026."
    assert [r["periodo"]["data_inicio"] for r in fonte["relatorios"]] == [
        "2026-06-22", "2026-06-29"
    ]
    assert fonte["modelo_versao"] is None and fonte["execucao_id"] is None


def test_a_fonte_da_evolucao_conta_os_relatorios(rede, analista, modelo):
    modelo(ModeloFalso({"tipo": "evolucao_do_parceiro", "parceiro": "Esquina da Serra"}))
    fonte = _perguntar(analista, "Como evoluiu a Esquina da Serra?")["fonte"]
    assert fonte["texto"] == "5 relatórios semanais, de 01/06/2026 a 05/07/2026."


def test_a_fonte_da_previsao_traz_a_versao_do_modelo(rede, analista, modelo):
    modelo(ModeloFalso({"tipo": "previsao_do_parceiro", "parceiro": "Esquina da Serra"}))
    fonte = _perguntar(analista, "A Esquina da Serra vai cair?")["fonte"]
    assert fonte["texto"] == "Relatório de 29/06/2026 a 05/07/2026. Modelo preditivo rede-1."
    assert fonte["modelo_versao"] == "rede-1"


def test_a_fonte_do_plano_traz_o_calculo(rede, gestor, modelo):
    plano = _calcular(gestor)
    modelo(ModeloFalso({"tipo": "ultimo_plano"}))
    fonte = _perguntar(gestor, "Qual o ganho do último plano?")["fonte"]
    assert fonte["execucao_id"] == plano["id"]
    assert fonte["texto"].endswith(f"Cálculo de plano nº {plano['id']}.")


def test_a_fonte_e_a_importacao_mais_recente_do_periodo(rede, analista, modelo, criar_usuario):
    """Depois de uma substituição (H25), os dados são da importação nova."""
    outro = criar_usuario(login="substituta", perfil=Perfil.ANALISTA, nome="Substituta")
    with Sessao() as s:
        s.add(Importacao(periodo_id=rede.base_id, usuario_id=outro, origem=OrigemImportacao.CSV))
        s.commit()
    modelo(ModeloFalso({"tipo": "resumo_do_periodo"}))
    relatorios = _perguntar(analista, "Como foi a rede?")["fonte"]["relatorios"]
    assert (relatorios[-1]["importado_por"], relatorios[-1]["origem"]) == ("Substituta", "CSV")


def test_a_abstencao_por_falta_no_periodo_cita_o_periodo(rede, analista, modelo):
    modelo(ModeloFalso({"tipo": "desempenho_do_parceiro", "parceiro": "Ponto Real"}))
    corpo = _perguntar(analista, "Quanto o Ponto Real faturou?")
    assert corpo["situacao"] == "ABSTENCAO"
    assert corpo["fonte"]["texto"] == "Relatório de 29/06/2026 a 05/07/2026."


def test_o_modelo_nao_ve_a_fonte(rede, analista, modelo):
    falso = modelo(ModeloFalso({"tipo": "desempenho_do_parceiro", "parceiro": "Esquina da Serra"}))
    _perguntar(analista, "Quanto a Esquina da Serra faturou?")
    _, pedido = falso.redacoes[0]
    assert "Semeador" not in pedido and "Relatório" not in pedido


# ======================================================== a redação (H67)
def test_o_modelo_redige_e_a_guarda_aprova(rede, analista, modelo):
    texto = "Não: em 29/06/2026 a 05/07/2026, a Esquina da Serra está no segmento Top 15."
    modelo(
        ModeloFalso(
            {"tipo": "segmento_do_parceiro", "parceiro": "Esquina da Serra"},
            redacao=lambda _: texto,
        )
    )
    corpo = _perguntar(analista, "A Esquina da Serra está em risco?")
    assert (corpo["texto"], corpo["redator"], corpo["motivo"]) == (texto, "MODELO", None)


def test_o_modelo_recebe_a_pergunta_a_resposta_e_os_fatos(rede, analista, modelo):
    falso = modelo(ModeloFalso({"tipo": "resumo_do_periodo"}))
    corpo = _perguntar(analista, "Como foi a rede?")
    sistema, pedido = falso.redacoes[0]
    assert "exatamente como está nos fatos" in sistema
    assert pedido.startswith("Pergunta: Como foi a rede?\n\nResposta do sistema: Em 29/06/2026")
    assert "- Faturamento: R$ 24.000,00" in pedido
    assert corpo["redator"] == "MODELO"


def test_numero_inventado_nunca_chega_a_tela(rede, analista, modelo):
    """RF43: o texto com número que não veio dos fatos volta a ser o do código."""
    modelo(
        ModeloFalso(
            {"tipo": "resumo_do_periodo"},
            redacao=lambda _: "A rede faturou R$ 25.000,00, cerca de 5% a mais.",
        )
    )
    corpo = _perguntar(analista, "Como foi a rede?")
    assert corpo["redator"] == "MODELO_FIXO"
    assert corpo["texto"].startswith("Em 29/06/2026 a 05/07/2026, a rede faturou R$ 24.000,00")
    assert corpo["motivo"] == NUMEROS_SEM_ORIGEM.format(numeros="R$ 25.000,00, 5%")


def test_a_variacao_no_sentido_contrario_nunca_chega_a_tela(rede, analista, modelo):
    """O número certo com a notícia invertida: -7,69% dito como alta."""
    modelo(
        ModeloFalso(
            {"tipo": "resumo_do_periodo"},
            redacao=lambda _: "Em 29/06/2026 a 05/07/2026, o faturamento cresceu 7,69%.",
        )
    )
    corpo = _perguntar(analista, "Como foi a rede?")
    assert corpo["redator"] == "MODELO_FIXO"
    assert corpo["motivo"] == SENTIDO_TROCADO.format(numeros="7,69%")


def test_o_texto_longo_demais_volta_ao_do_codigo(rede, analista, modelo):
    modelo(ModeloFalso({"tipo": "resumo_do_periodo"}, redacao=lambda _: "A rede vai bem. " * 60))
    corpo = _perguntar(analista, "Como foi a rede?")
    assert (corpo["redator"], corpo["motivo"]) == ("MODELO_FIXO", LONGO)


def test_o_modelo_que_cai_na_redacao_deixa_a_resposta_do_codigo(rede, analista, modelo):
    modelo(ModeloFalso({"tipo": "resumo_do_periodo"}, falha_na_redacao=FORA_DO_AR))
    corpo = _perguntar(analista, "Como foi a rede?")
    assert corpo["situacao"] == "RESPONDIDA"
    assert (corpo["redator"], corpo["motivo"]) == ("MODELO_FIXO", FORA_DO_AR)


@pytest.mark.parametrize(
    "tipo",
    [
        TipoPergunta.EVOLUCAO_DO_PARCEIRO,
        TipoPergunta.RANKING,
        TipoPergunta.PARCEIROS_DO_SEGMENTO,
        TipoPergunta.MOBILIDADE_DO_TOP,
        TipoPergunta.DISTRIBUICAO_DOS_SEGMENTOS,
    ],
)
def test_as_listas_nao_passam_pelo_modelo(rede, analista, modelo, tipo):
    """Uma lista reescrita pode perder um item sem que número nenhum fique errado."""
    falso = modelo(ModeloFalso({"tipo": tipo, **EXTRACOES[tipo]}))
    corpo = _perguntar(analista, "Pergunta sobre a Esquina da Serra")
    assert falso.redacoes == []
    assert (corpo["redator"], corpo["motivo"]) == ("MODELO_FIXO", None)


def test_a_abstencao_e_a_precisao_nao_passam_pelo_modelo(rede, analista, modelo):
    falso = modelo(ModeloFalso({"tipo": "desempenho_do_parceiro", "parceiro": "Cantina"}))
    assert _perguntar(analista, "Quanto a Cantina faturou?")["situacao"] == "PRECISAO"
    assert falso.redacoes == []


# ======================================================= a abstenção (H68)
@pytest.mark.parametrize(
    "pergunta",
    [
        "Qual a média de faturamento das pizzarias em agosto?",
        "Qual o faturamento médio da rede?",
        "Quanto a rede faturou em média na semana passada?",
        "Some o faturamento da Esquina da Serra e da Cantina Central",
        "Qual a soma dos pedidos de junho?",
        "Qual a diferença entre a Esquina da Serra e a Cantina Central?",
        "Qual o faturamento acumulado da Esquina da Serra?",
        "Qual a participação da Esquina da Serra no faturamento da rede?",
    ],
)
def test_a_pergunta_que_pede_conta_e_abstencao_sem_o_modelo(rede, analista, modelo, pergunta):
    """A instrução não bastou (ADR-013, adendo H65): o código reconhece a conta."""
    falso = modelo(ModeloFalso({"tipo": "desempenho_do_parceiro"}))
    corpo = _perguntar(analista, pergunta)
    assert (corpo["situacao"], corpo["tipo"], corpo["texto"]) == (
        "ABSTENCAO", "fora_do_catalogo", CONTA
    )
    assert falso.pedidos == []


@pytest.mark.parametrize(
    "pergunta", ["Por que a Esquina da Serra caiu?", "Qual foi o motivo da queda da rede?"]
)
def test_a_pergunta_pela_causa_e_abstencao(rede, analista, modelo, pergunta):
    falso = modelo(ModeloFalso())
    corpo = _perguntar(analista, pergunta)
    assert (corpo["situacao"], corpo["texto"]) == ("ABSTENCAO", CAUSA)
    assert falso.pedidos == []


def test_o_ticket_medio_nao_e_conta(rede, analista, modelo):
    """O ticket médio é indicador que o sistema calcula, e não uma média pedida."""
    modelo(ModeloFalso({"tipo": "desempenho_do_parceiro", "parceiro": "Esquina da Serra"}))
    _respondida(_perguntar(analista, "Qual o ticket médio da Esquina da Serra?"))


def test_dois_parceiros_na_pergunta_e_comparacao(rede, analista, modelo):
    extracao = {
        "tipo": "desempenho_do_parceiro", "parceiro": "Esquina da Serra",
        "outro_parceiro": "Cantina Central",
    }
    modelo(ModeloFalso(extracao))
    corpo = _perguntar(analista, "A Esquina da Serra faturou mais que a Cantina Central?")
    assert (corpo["situacao"], corpo["tipo"], corpo["texto"]) == (
        "ABSTENCAO", "fora_do_catalogo", COMPARACAO
    )


def test_o_segundo_parceiro_inventado_ou_repetido_nao_e_comparacao(rede, analista, modelo):
    for outro in ("Cantina Central", "Esquina da Serra"):
        extracao = {
            "tipo": "desempenho_do_parceiro", "parceiro": "Esquina da Serra",
            "outro_parceiro": outro,
        }
        modelo(ModeloFalso(extracao))
        _respondida(_perguntar(analista, "A Esquina da Serra faturou mais que na semana anterior?"))


def test_o_total_de_um_mes_e_abstencao_e_nao_precisao(rede, analista, modelo):
    extracao = {"tipo": "resumo_do_periodo", "inicio": "2026-06-01", "fim": "2026-06-30"}
    modelo(ModeloFalso(extracao))
    corpo = _perguntar(analista, "Qual o faturamento total da rede em junho?")
    assert (corpo["situacao"], corpo["texto"]) == ("ABSTENCAO", CONTA)


def test_a_previsao_de_outro_periodo_e_abstencao(rede, analista, modelo):
    """"Quanto vai faturar em dezembro?": a previsão existe, mas é de outra semana."""
    extracao = {
        "tipo": "previsao_do_parceiro", "parceiro": "Esquina da Serra", "inicio": "2026-12-01",
        "fim": "2026-12-31",
    }
    modelo(ModeloFalso(extracao))
    corpo = _perguntar(analista, "Quanto a Esquina da Serra vai faturar em dezembro?")
    assert corpo["situacao"] == "ABSTENCAO"
    assert corpo["texto"] == (
        "O modelo prevê só o período seguinte aos dados do treino, de 06/07/2026 a 12/07/2026: "
        "para 01/12/2026 a 31/12/2026, não há previsão."
    )
    assert numeros_sem_origem(corpo["texto"], _fatos(corpo)) == []


def test_a_previsao_do_periodo_previsto_e_respondida(rede, analista, modelo):
    extracao = {
        "tipo": "previsao_do_parceiro", "parceiro": "Esquina da Serra", "inicio": "2026-07-08",
        "fim": "2026-07-08",
    }
    modelo(ModeloFalso(extracao))
    _respondida(_perguntar(analista, "Quanto a Esquina da Serra vai faturar em 8 de julho?"))



# ============================================= o que o código acerta sobre o modelo
@pytest.mark.parametrize(
    ("pergunta", "futuro", "intervalo"),
    [
        ("Quanto faturou em 2019?", False, ("2019-01-01", "2019-12-31")),
        ("Como foi em agosto?", False, ("2026-08-01", "2026-08-31")),
        ("Como foi em dezembro?", False, ("2025-12-01", "2025-12-31")),
        ("Quanto vai faturar em dezembro?", True, ("2026-12-01", "2026-12-31")),
        ("E em março de 2025?", False, ("2025-03-01", "2025-03-31")),
        ("Entre junho e julho", False, ("2026-06-01", "2026-07-31")),
        ("Como foi no mês passado?", False, ("2026-08-01", "2026-08-31")),
        ("E no mês que vem?", True, ("2026-10-01", "2026-10-31")),
        ("E no ano que vem?", True, ("2027-01-01", "2027-12-31")),
        ("Como foi em 14/09/2026?", False, None),
        ("Como foi a rede?", False, None),
    ],
)
def test_o_codigo_le_o_mes_e_o_ano_da_pergunta(pergunta, futuro, intervalo):
    """Só quando o modelo não trouxe a data: "em 2019" e "em dezembro" chegaram sem."""
    lido = resolucao.datas_da_pergunta(pergunta, date(2026, 9, 20), futuro=futuro)
    esperado = tuple(date.fromisoformat(d) for d in intervalo) if intervalo else None
    assert lido == esperado


def test_o_ano_sem_dados_que_o_modelo_nao_leu_e_abstencao(rede, analista, modelo):
    """Na medição, "em 2019" foi respondido com a semana mais recente."""
    modelo(ModeloFalso({"tipo": "desempenho_do_parceiro", "parceiro": "Esquina da Serra"}))
    corpo = _perguntar(analista, "Quanto a Esquina da Serra faturou em 2019?")
    assert corpo["situacao"] == "ABSTENCAO"
    assert corpo["texto"].startswith("Não há dados de 01/01/2019 a 31/12/2019.")


def test_a_previsao_de_um_mes_que_o_modelo_nao_leu_e_abstencao(rede, analista, modelo):
    modelo(ModeloFalso({"tipo": "previsao_do_parceiro", "parceiro": "Esquina da Serra"}))
    corpo = _perguntar(analista, "Quanto a Esquina da Serra vai faturar em dezembro?")
    assert corpo["situacao"] == "ABSTENCAO"
    assert "não há previsão" in corpo["texto"]


def test_o_resumo_da_rede_com_um_parceiro_e_o_desempenho_dele(rede, analista, modelo):
    """ "Como foi o Quintal do Norte nesta semana?" saiu como o resumo da rede."""
    modelo(ModeloFalso({"tipo": "resumo_do_periodo", "parceiro": "Esquina da Serra"}))
    corpo = _perguntar(analista, "Como foi a Esquina da Serra nesta semana?")
    assert corpo["tipo"] == "desempenho_do_parceiro"
    assert _respondida(corpo).startswith("Esquina da Serra faturou R$ 9.000,00")


def test_o_desempenho_de_varias_semanas_e_a_evolucao(rede, analista, modelo):
    """Os números do intervalo pedido, semana a semana — sem somar e sem escolher."""
    extracao = {
        "tipo": "desempenho_do_parceiro", "parceiro": "Esquina da Serra",
        "inicio": "2026-06-22", "fim": "2026-07-05",
    }
    modelo(ModeloFalso(extracao))
    corpo = _perguntar(analista, "Quanto a Esquina da Serra faturou no fim de junho?")
    assert corpo["tipo"] == "evolucao_do_parceiro"
    assert _respondida(corpo) == (
        "O faturamento de Esquina da Serra, período a período:\n"
        "- 22/06/2026 a 28/06/2026: R$ 9.000,00 em 10 pedidos\n"
        "- 29/06/2026 a 05/07/2026: R$ 9.000,00 em 10 pedidos"
    )


def test_o_total_de_varias_semanas_de_um_parceiro_e_abstencao(rede, analista, modelo):
    extracao = {
        "tipo": "desempenho_do_parceiro", "parceiro": "Esquina da Serra",
        "inicio": "2026-06-01", "fim": "2026-06-30",
    }
    modelo(ModeloFalso(extracao))
    corpo = _perguntar(analista, "Qual o faturamento total da Esquina da Serra em junho?")
    assert (corpo["situacao"], corpo["texto"]) == ("ABSTENCAO", CONTA)


@pytest.mark.parametrize(
    ("redacao", "unidades"),
    [
        ("O faturamento previsto para o mês é de R$ 9.500,00.", "mês"),
        ("A chance é de 13%, e o faturamento previsto é de US$ 9.500,00.", "US$"),
        ("Por dia, são R$ 9.500,00 previstos.", "dia"),
    ],
)
def test_a_unidade_que_os_fatos_nao_tem_volta_ao_texto_do_codigo(
    rede, analista, modelo, redacao, unidades
):
    """O número é o dos fatos; a unidade, não. A previsão é de uma semana."""
    modelo(
        ModeloFalso(
            {"tipo": "previsao_do_parceiro", "parceiro": "Esquina da Serra"},
            redacao=lambda _: redacao,
        )
    )
    corpo = _perguntar(analista, "Quanto a Esquina da Serra deve faturar?")
    assert corpo["redator"] == "MODELO_FIXO"
    assert corpo["motivo"] == UNIDADE_SEM_ORIGEM.format(unidades=unidades)


def test_a_semana_dos_fatos_nao_e_unidade_sem_origem(rede, analista, modelo):
    texto = "Para o período de 06/07/2026 a 12/07/2026, o previsto é de R$ 9.500,00."
    modelo(
        ModeloFalso(
            {"tipo": "previsao_do_parceiro", "parceiro": "Esquina da Serra"},
            redacao=lambda _: texto,
        )
    )
    corpo = _perguntar(analista, "Quanto a Esquina da Serra deve faturar?")
    assert (corpo["redator"], corpo["texto"]) == ("MODELO", texto)


# ================================================= os conjuntos da medição
# Os três conjuntos de `tests/assistente/` são medidos contra o modelo de verdade
# por `scripts/medir_assistente.py`. Aqui, sem o modelo, confere-se que eles
# dizem o que precisam dizer.
CONJUNTOS = Path(__file__).parent / "assistente"


def _conjunto(nome):
    return json.loads((CONJUNTOS / nome).read_text(encoding="utf-8"))


def test_a_referencia_cobre_o_catalogo_com_campos_que_existem():
    perguntas = _conjunto("referencia.json")["perguntas"]
    textos = [p["pergunta"] for p in perguntas]
    assert len(textos) == len(set(textos))
    for p in perguntas:
        assert TipoPergunta(p["tipo"])
        assert set(p["campos"]) <= set(Extracao.model_fields) - {"tipo"}, p
    por_tipo = {t: sum(p["tipo"] == t for p in perguntas) for t in TipoPergunta}
    assert min(por_tipo.values()) >= 3, por_tipo


def test_as_armadilhas_sao_perguntas_distintas():
    perguntas = _conjunto("armadilhas.json")["perguntas"]
    assert len(perguntas) >= 15 and len(perguntas) == len(set(perguntas))


def test_o_que_o_conjunto_diz_que_o_codigo_pega_o_codigo_pega():
    """E o contrário: a pergunta marcada para o modelo não é pega antes dele, senão a
    medição mediria o código achando que mede o modelo."""
    for p in _conjunto("sem_resposta.json")["perguntas"]:
        assert (abstencao_pelo_codigo(p["pergunta"]) is not None) is p["pelo_codigo"], p


# ======================================================== o modelo de verdade
@pytest.mark.parametrize(
    ("pergunta", "tipo", "situacao"),
    [
        (
            "Quanto a Esquina da Serra faturou na semana passada?",
            "desempenho_do_parceiro",
            "RESPONDIDA",
        ),
        ("Quais mercados estão em risco?", "parceiros_do_segmento", "RESPONDIDA"),
        ("Qual a capital da França?", "fora_do_catalogo", "ABSTENCAO"),
    ],
)
def test_o_modelo_de_verdade_le_o_catalogo(
    rede, analista, monkeypatch, modelo_real, pergunta, tipo, situacao
):
    """Uma pergunta com parceiro e data, uma de segmento com categoria e uma fora do
    catálogo."""
    monkeypatch.setattr(redator, "atual", lambda: modelo_real)
    corpo = _perguntar(analista, pergunta)
    assert (corpo["tipo"], corpo["situacao"]) == (tipo, situacao), corpo
    if situacao == "RESPONDIDA":
        _respondida(corpo)
