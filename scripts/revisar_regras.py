"""Revisa as regras de negócio RN01 a RN11 contra o que o sistema faz — história H99.

A oitava entrega da disciplina pede a **revisão geral das regras de negócio**:
identificar o que está incoerente e ajustar. "Revisamos e está tudo certo" não é
evidência. Este roteiro monta um cenário pequeno, **desenhado à mão para cair em
cada ramo de cada regra**, passa-o pela aplicação de verdade e compara o que
voltou com o que a regra escrita manda. O relatório sai em
`docs/medicoes/regras.md`, regra a regra: o cenário, o esperado e o que voltou.

**O esperado está escrito aqui, e não calculado pelo código que se revisa.** A
rede tem 22 parceiros e 8 semanas, e o segmento, a posição no ranking e a
mobilidade de cada um foram deduzidos da regra, no papel, e estão nas tabelas
abaixo. Se o roteiro chamasse a função da segmentação para saber o esperado,
ele só provaria que a função concorda consigo mesma.

**Banco próprio.** O cenário precisa de histórico fabricado: um parceiro no Top
e em queda, um recém-chegado, um que sai do Top na última semana. Na base de
demonstração isso mexeria no "período mais recente" de quem estiver usando a
aplicação. Por isso o roteiro cria e usa `gih_regras`, na mesma instância, e o
recria a cada execução — o banco de trabalho não é tocado.

**Em processo, pela API.** As importações, o treino, a campanha e as mensagens
passam pelas rotas, com sessão e perfil, pelo `TestClient`: o que se revisa é o
que o usuário recebe, e não uma função isolada. Onde a regra é sobre uma função
pura — a guarda numérica da RN08 —, ela é chamada direto, e o relatório diz.

**Sem o modelo de linguagem.** As mensagens saem do modelo fixo, que é o que o
sistema faz quando o modelo não está no ar; a RN06 e a RN08 valem igual. O
assistente com o modelo de verdade é medido em `docs/medicoes/assistente.md`.

Uso:

    api/.venv/Scripts/python scripts/revisar_regras.py
"""
from __future__ import annotations

import argparse
import math
import os
import secrets
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

RAIZ = Path(__file__).resolve().parent.parent
RAIZ_API = RAIZ / "api"
sys.path.insert(0, str(RAIZ_API))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ESPERA_MAXIMA = 300

# ------------------------------------------------------------------ o cenário
SEMANAS = 8
PRIMEIRA_SEMANA = date(2026, 6, 1)


def _plana(base: int) -> list[int | None]:
    """Sobe 50 nas semanas pares e volta nas ímpares: nunca dois movimentos seguidos
    no mesmo sentido, que é o que a regra chama de tendência."""
    return [base + (50 if semana % 2 == 0 else 0) for semana in range(1, SEMANAS + 1)]


def _com_final(base: int, *finais: int) -> list[int | None]:
    serie = _plana(base)
    serie[-len(finais):] = finais
    return serie


# O faturamento de cada parceiro, semana a semana. As três últimas semanas é que
# decidem a tendência; a última, o ranking.
REDE: dict[str, list[int | None]] = {
    "Loja 01": _plana(20000),
    # No Top e em queda há duas semanas: o caso que a RN01 e a RN02 existem para tratar.
    "Loja 02": _com_final(19000, 19000, 18500, 18000),
    # No Top e subindo há duas semanas: Top vence Em Ascensão.
    "Loja 03": _com_final(18000, 18000, 18200, 18400),
    **{f"Loja {n:02d}": _plana(21000 - 1000 * n) for n in range(4, 14)},
    # Marcada como prospecção, no Top e em queda: Prospecção vence tudo.
    "Loja 14": _com_final(7000, 7000, 6900, 6800),
    # Era a 15ª e cai para a 16ª na última semana: sai do Top. Uma queda só não é risco.
    "Loja 15": _com_final(6000, 5950, 6000, 4800),
    # Era a 16ª e sobe para a 15ª: entra no Top.
    "Loja 16": _com_final(5000, 5050, 5000, 6100),
    "Loja 17": _plana(4000),
    # Fora do Top e subindo há duas semanas.
    "Loja 18": _com_final(3000, 3000, 3200, 3400),
    # Fora do Top e em queda há duas semanas.
    "Loja 19": _com_final(2000, 2000, 1900, 1800),
    # Só aparece nas duas últimas semanas.
    "Loja 20": [None] * 6 + [1000, 900],
    # O nome aponta uma categoria: a importação a sugere, e ninguém a confirma.
    "Pizzaria Aurora": _plana(500),
    # O nome aponta duas categorias: fica sem sugestão.
    "Pizzaria e Padaria Sol": _plana(400),
}
EM_PROSPECCAO = "Loja 14"
DESATIVADO = "Loja 17"
DA_PADARIA = ("Loja 05", "Loja 06", "Loja 07", "Loja 08")

# O que a RN01 manda para a última semana, com os limiares de fábrica — Top 15,
# 2 períodos de tendência, 3 de recém-chegado. Deduzido da regra, à mão.
SEGMENTO_ESPERADO = {
    "Loja 01": "TOP",
    "Loja 02": "EM_RISCO",
    "Loja 03": "TOP",
    **{f"Loja {n:02d}": "TOP" for n in range(4, 14)},
    "Loja 14": "PROSPECCAO",
    "Loja 15": "ESTAVEL",
    "Loja 16": "TOP",
    "Loja 17": "ESTAVEL",
    "Loja 18": "EM_ASCENSAO",
    "Loja 19": "EM_RISCO",
    "Loja 20": "RECEM_CHEGADO",
    "Pizzaria Aurora": "ESTAVEL",
    "Pizzaria e Padaria Sol": "ESTAVEL",
}
# O ranking da última semana, do maior faturamento para o menor.
RANKING_ESPERADO = [
    "Loja 01", "Loja 03", "Loja 02", *[f"Loja {n:02d}" for n in range(4, 14)],
    "Loja 14", "Loja 16", "Loja 15", "Loja 17", "Loja 18", "Loja 19", "Loja 20",
    "Pizzaria Aurora", "Pizzaria e Padaria Sol",
]
TOP_N, TENDENCIA, NOVATO = 15, 2, 3

VISITA = {"nome": "Visita de relacionamento", "custo_unitario": "90.00",
          "efeito_crescimento": "0.06", "efeito_retencao": "0.30", "ativa": True}
VITRINE = {"nome": "Destaque na vitrine", "custo_unitario": "260.00",
           "efeito_crescimento": "0.14", "efeito_retencao": "0.05", "ativa": True}
MAXIMO_ACOES = 9
COTA_CAUDA = "0.3"         # ⌈0,3 × 9⌉ = ⌈2,7⌉ = 3
COTA_PADARIA = ("0.25", "0.5")  # ⌈2,25⌉ = 3 e ⌊4,5⌋ = 4


def periodo(semana: int) -> tuple[date, date]:
    inicio = PRIMEIRA_SEMANA + timedelta(days=7 * (semana - 1))
    return inicio, inicio + timedelta(days=6)


def pedidos_de(nome: str, faturamento: int) -> int:
    """Um ticket diferente por parceiro: a média dos tickets não é o ticket da rede."""
    return max(1, round(faturamento / (40 + list(REDE).index(nome))))


def relatorio_da_semana(semana: int) -> str:
    linhas = ["Parceiro;Faturamento;Pedidos"]
    for nome, serie in REDE.items():
        faturamento = serie[semana - 1]
        if faturamento is not None:
            linhas.append(f"{nome};{faturamento},00;{pedidos_de(nome, faturamento)}")
    return "\n".join(linhas) + "\n"


# ---------------------------------------------------------------- o relatório
def _texto(valor: object) -> str:
    if isinstance(valor, bool):
        return "sim" if valor else "não"
    if isinstance(valor, (list, tuple)):
        return ", ".join(_texto(v) for v in valor) or "nenhum"
    if isinstance(valor, dict):
        return "; ".join(f"{k}: {_texto(v)}" for k, v in valor.items()) or "nenhum"
    return str(valor)


@dataclass
class Regra:
    codigo: str
    nome: str
    onde: tuple[str, ...]
    testes: tuple[str, ...]
    cenario: str
    linhas: list[tuple[str, str, str, bool]] = field(default_factory=list)
    notas: list[str] = field(default_factory=list)

    def confere(self, o_que: str, esperado: object, voltou: object) -> bool:
        ok = esperado == voltou
        self.linhas.append((o_que, _texto(esperado), _texto(voltou), ok))
        print(f"  {'ok   ' if ok else 'FALHA'} {self.codigo} · {o_que}")
        if not ok:
            print(f"        esperado: {_texto(esperado)}\n        voltou:   {_texto(voltou)}")
        return ok

    def nota(self, texto: str) -> None:
        self.notas.append(texto)


# ----------------------------------------------------------------- preparação
def _url_base() -> str:
    """De onde sai a URL do banco, na ordem que a aplicação usa (ver `medir_painel.py`)."""
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    for arquivo in (RAIZ / ".env", RAIZ_API / ".env"):
        if not arquivo.exists():
            continue
        for linha in arquivo.read_text(encoding="utf-8").splitlines():
            chave, _, valor = linha.partition("=")
            if chave.strip() == "DATABASE_URL" and valor.strip():
                return valor.strip().strip("\"'")
    return "postgresql+psycopg://gih:gih@localhost:5433/gih"


def _recriar_banco(url: str) -> None:
    """O banco da revisão começa vazio a cada execução: o cenário é o do roteiro, e só ele."""
    from sqlalchemy import create_engine, text

    partes = urlsplit(url)
    nome = partes.path.lstrip("/")
    manutencao = create_engine(
        urlunsplit(partes._replace(path="/postgres")), isolation_level="AUTOCOMMIT"
    )
    try:
        with manutencao.connect() as c:
            # Identificador não aceita bind. O nome vem da nossa configuração, e já
            # foi conferido que não é o do banco de trabalho.
            c.execute(text(f'DROP DATABASE IF EXISTS "{nome}" WITH (FORCE)'))
            c.execute(text(f'CREATE DATABASE "{nome}"'))
    finally:
        manutencao.dispose()

    r = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=RAIZ_API,
        env={**os.environ, "DATABASE_URL": url},
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if r.returncode != 0:
        raise SystemExit(f"As migrações falharam no banco da revisão:\n{r.stdout}\n{r.stderr}")


def criar_usuarios() -> dict[str, tuple[str, str]]:
    """Um usuário por perfil que as regras envolvem. A senha é sorteada e não é impressa."""
    from app.db import Sessao
    from app.modelos import Perfil, Usuario
    from app.seguranca import gerar_hash

    contas = {}
    s = Sessao()
    try:
        for perfil in (Perfil.ADMINISTRADOR, Perfil.GESTOR, Perfil.ANALISTA):
            login, senha = f"revisao.{perfil.value.lower()}", secrets.token_urlsafe(18)
            s.add(Usuario(login=login, nome=f"{perfil.value.title()} da Revisão",
                          perfil=perfil, senha_hash=gerar_hash(senha)))
            contas[perfil.value] = (login, senha)
        s.commit()
    finally:
        s.close()
    return contas


def aguardar(cliente, caminho: str, campo: str = "situacao") -> dict:
    """Consulta até a operação de fundo sair de EM_ANDAMENTO, como a tela faz."""
    inicio = time.monotonic()
    while True:
        corpo = cliente.get(caminho).json()
        if corpo[campo] != "EM_ANDAMENTO":
            return corpo
        if time.monotonic() - inicio > ESPERA_MAXIMA:
            raise SystemExit(f"{caminho} não terminou em {ESPERA_MAXIMA} s.")
        time.sleep(0.5)


def importar(analista, semana: int) -> None:
    inicio, fim = periodo(semana)
    r = analista.post("/api/importacoes", json={
        "periodo_inicio": inicio.isoformat(), "periodo_fim": fim.isoformat(),
        "texto": relatorio_da_semana(semana),
    })
    if r.status_code != 201:
        raise SystemExit(f"A importação da semana {semana} respondeu {r.status_code}: {r.text}")


def ids_dos_parceiros(analista) -> dict[str, int]:
    itens = analista.get("/api/parceiros?tamanho=100").json()["itens"]
    return {p["nome"]: p["id"] for p in itens}


# ------------------------------------------------------------------ as regras
def rn03(analista) -> Regra:
    r = Regra(
        "RN03", "Período é obrigatório na importação",
        ("`api/app/esquemas.py`, `PedidoImportacao`: as duas datas sem valor padrão",
         "`api/app/erros.py`: a recusa explica por que o período é necessário"),
        ("api/tests/test_importacao.py::test_sem_periodo_a_importacao_e_recusada",
         "api/tests/test_importacao.py::test_nao_existe_periodo_padrao"),
        "Antes de qualquer importação, o relatório da primeira semana é enviado sem as datas, "
        "e depois com o fim antes do início.",
    )
    sem = analista.post("/api/importacoes", json={"texto": relatorio_da_semana(1)})
    r.confere("sem as datas, a importação é recusada", 422, sem.status_code)
    campos = sorted(c["campo"] for c in sem.json().get("campos", []))
    r.confere("a recusa aponta as duas datas", ["periodo_fim", "periodo_inicio"], campos)
    inicio, fim = periodo(1)
    invertido = analista.post("/api/importacoes", json={
        "periodo_inicio": fim.isoformat(), "periodo_fim": inicio.isoformat(),
        "texto": relatorio_da_semana(1),
    })
    r.confere("com o fim antes do início, também", 422, invertido.status_code)
    gravadas = analista.get("/api/importacoes").json()["total"]
    r.confere("nada foi gravado: o histórico de importações continua vazio", 0, gravadas)
    return r


def rn05(analista, ids: dict[str, int], categorias: dict[str, int]) -> Regra:
    r = Regra(
        "RN05", "Categoria sugerida não é categoria confirmada",
        ("`api/app/sugestao_categoria.py`: a regra das palavras do nome",
         "`api/app/servico_importacao.py`: a sugestão entra com origem `INFERIDA`",
         "`api/app/servico_otimizacao.py`: a cota de categoria só conta a confirmada"),
        ("api/tests/test_sugestao_categoria.py::"
         "test_nome_que_aponta_duas_categorias_nao_recebe_sugestao",
         "api/tests/test_sugestao_categoria.py::"
         "test_categoria_so_sugerida_continua_pendente_de_classificacao",
         "api/tests/test_campanha.py::test_categoria_so_conta_quando_confirmada"),
        'Com as categorias "Pizzaria" e "Padaria" cadastradas, a importação traz "Pizzaria '
        'Aurora", cujo nome aponta uma categoria, e "Pizzaria e Padaria Sol", que aponta duas. '
        "Quatro lojas são classificadas à mão como Padaria.",
    )
    aurora = analista.get(f"/api/parceiros/{ids['Pizzaria Aurora']}").json()
    sol = analista.get(f"/api/parceiros/{ids['Pizzaria e Padaria Sol']}").json()
    r.confere("o nome com uma categoria recebe a sugestão", "Pizzaria",
              (aurora.get("categoria") or {}).get("nome"))
    r.confere("e a origem dela é inferida, e não manual", "INFERIDA", aurora["origem_categoria"])
    r.confere("o nome com duas categorias fica sem sugestão", None, sol.get("categoria"))
    pendentes = analista.get("/api/parceiros?sem_categoria=true&tamanho=100").json()["itens"]
    nomes = {p["nome"] for p in pendentes}
    r.confere("a só sugerida continua entre os pendentes de classificação", True,
              "Pizzaria Aurora" in nomes)
    r.confere("a classificada à mão não está entre os pendentes", False, "Loja 05" in nomes)
    manual = analista.get(f"/api/parceiros/{ids['Loja 05']}").json()
    r.confere("classificar à mão marca a origem como manual", "MANUAL", manual["origem_categoria"])
    r.nota("A outra metade da regra — a cota de categoria só conta a categoria confirmada — "
           "é conferida no plano de campanha, na RN11.")
    return r


def rn01(gestor, ids: dict[str, int]) -> Regra:
    r = Regra(
        "RN01", "Segmentação com precedência explícita",
        ("`api/app/servico_segmentacao.py`, `classificar`: os seis ramos, na ordem da regra",
         "`api/app/servico_segmentacao.py`, `Limiares`: os três limiares de fábrica",
         "`api/app/modelos.py`, `Segmento`: o enum declarado na ordem de precedência"),
        ("api/tests/test_segmentacao.py::test_top_em_queda_sai_como_em_risco",
         "api/tests/test_segmentacao.py::test_a_ordem_do_enum_e_a_ordem_em_que_a_regra_decide",
         "api/tests/test_configuracao.py::test_os_limiares_de_fabrica_sao_os_de_rn01"),
        f"Os {len(REDE)} parceiros, depois das {SEMANAS} semanas, com os limiares de fábrica. "
        "Cada ramo da precedência tem pelo menos um parceiro desenhado para cair nele — e "
        "cinco deles satisfazem mais de um critério ao mesmo tempo.",
    )
    limiares = gestor.get("/api/ajuda/regras").json()
    r.confere("os limiares de fábrica: Top, tendência e recém-chegado",
              [TOP_N, TENDENCIA, NOVATO],
              [limiares["top_n"], limiares["periodos_tendencia"], limiares["periodos_novato"]])

    itens = gestor.get("/api/parceiros?tamanho=100").json()["itens"]
    voltou = {p["nome"]: (p.get("desempenho") or {}).get("segmento") for p in itens}
    casos = (
        ("Loja 14", "marcada como prospecção, no Top e em queda: Prospecção vence tudo"),
        ("Loja 20", "só duas semanas de histórico: Recém-chegado"),
        ("Loja 02", "no Top e em queda há duas semanas: Em Risco vence Top"),
        ("Loja 19", "fora do Top e em queda há duas semanas: Em Risco"),
        ("Loja 03", "no Top e subindo há duas semanas: Top vence Em Ascensão"),
        ("Loja 16", "acabou de entrar no Top, com uma alta só: Top"),
        ("Loja 18", "fora do Top e subindo há duas semanas: Em Ascensão"),
        ("Loja 15", "fora do Top, com uma queda só: Estável — uma queda não é tendência"),
        ("Loja 17", "fora do Top, sem tendência: Estável"),
    )
    for nome, o_que in casos:
        r.confere(o_que, SEGMENTO_ESPERADO[nome], voltou.get(nome))
    r.confere(f"os {len(REDE)} parceiros, um a um, no segmento que a regra manda",
              SEGMENTO_ESPERADO, {nome: voltou.get(nome) for nome in SEGMENTO_ESPERADO})

    fatias = gestor.get("/api/painel/segmentos").json()
    contagem = {f["segmento"]: f["total"] for f in fatias["itens"]}
    esperada = {}
    for segmento in SEGMENTO_ESPERADO.values():
        esperada[segmento] = esperada.get(segmento, 0) + 1
    r.confere("a distribuição do painel soma os mesmos segmentos",
              dict(sorted(esperada.items())), dict(sorted(contagem.items())))
    r.confere("cada parceiro tem exatamente um segmento: a distribuição soma a rede",
              len(REDE), fatias["total"])
    return r


def rn02(gestor) -> Regra:
    r = Regra(
        "RN02", "Mobilidade do Top N lê o ranking, não o segmento",
        ("`api/app/ranking.py`: as posições por faturamento, numa consulta só",
         "`api/app/rotas/painel.py`, `mobilidade`: compara as posições de dois períodos"),
        ("api/tests/test_painel.py::test_top_em_queda_nao_aparece_como_saida",
         "api/tests/test_painel.py::test_mobilidade_lista_quem_entrou_e_quem_saiu"),
        "Na última semana a Loja 16 passa a Loja 15 e entra no Top 15. A Loja 02 continua em "
        "3º, mas está gravada como Em Risco: lida do segmento, ela apareceria como saída.",
    )
    ranking = gestor.get("/api/painel/ranking?tamanho=100").json()["itens"]
    r.confere("o ranking da última semana, do maior faturamento para o menor",
              RANKING_ESPERADO, [linha["nome"] for linha in ranking])
    da_02 = next(linha for linha in ranking if linha["nome"] == "Loja 02")
    r.confere("a Loja 02 está em 3º no ranking", 3, da_02["posicao"])
    r.confere("e o segmento dela é Em Risco", "EM_RISCO", da_02["segmento"])

    mobilidade = gestor.get("/api/painel/mobilidade").json()
    r.confere("quem entrou no Top 15", ["Loja 16"], [m["nome"] for m in mobilidade["entradas"]])
    r.confere("quem saiu do Top 15", ["Loja 15"], [m["nome"] for m in mobilidade["saidas"]])
    r.confere("a Loja 02, no Top e em risco, não aparece como saída", False,
              "Loja 02" in [m["nome"] for m in mobilidade["saidas"]])
    return r


def rn04(gestor) -> Regra:
    from app.db import Sessao
    from sqlalchemy import text

    r = Regra(
        "RN04", "Ticket médio é derivado, nunca importado",
        ("`api/app/calculos.py`, `ticket_medio`: a única conta, usada por todas as telas",
         "`api/app/modelos.py`, `Metrica`: só faturamento e pedidos"),
        ("api/tests/test_importacao.py::test_ticket_medio_nao_e_gravado",
         "api/tests/test_painel.py::"
         "test_ticket_medio_e_a_razao_dos_totais_e_nao_a_media_das_medias"),
        "Cada parceiro foi importado com um ticket diferente. O ticket da rede, na última "
        "semana, é o faturamento somado dividido pelos pedidos somados.",
    )
    s = Sessao()
    try:
        colunas = s.scalars(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'metrica' ORDER BY ordinal_position"
        )).all()
    finally:
        s.close()
    r.confere("a tabela de métricas não tem coluna de ticket", False,
              any("ticket" in coluna for coluna in colunas))
    r.nota(f"As colunas da tabela `metrica`: {', '.join(colunas)}.")

    ultima = [(nome, serie[-1]) for nome, serie in REDE.items() if serie[-1] is not None]
    faturamento = sum(valor for _, valor in ultima)
    pedidos = sum(pedidos_de(nome, valor) for nome, valor in ultima)
    centavos = Decimal("0.01")
    esperado = (Decimal(faturamento) / Decimal(pedidos)).quantize(centavos, ROUND_HALF_UP)
    media_das_medias = (
        sum(Decimal(valor) / Decimal(pedidos_de(nome, valor)) for nome, valor in ultima)
        / len(ultima)
    ).quantize(centavos, ROUND_HALF_UP)

    painel = gestor.get("/api/painel/indicadores").json()
    r.confere("o faturamento da rede é a soma do que foi importado",
              f"{faturamento}.00", painel["faturamento"])
    r.confere("os pedidos também", pedidos, painel["pedidos"])
    r.confere("o ticket é a razão dos totais", str(esperado), painel["ticket_medio"])
    r.confere("e não a média dos tickets dos parceiros, que daria outro número", True,
              str(media_das_medias) != painel["ticket_medio"])
    r.nota(f"A média dos tickets dos parceiros daria {media_das_medias}; a razão dos totais "
           f"é {esperado}.")
    return r


def rn09_recusa(gestor) -> tuple[int, dict]:
    """Com sete semanas importadas, o treino é recusado. Devolve a resposta, para a RN09."""
    r = gestor.post("/api/modelo/treinos")
    return r.status_code, r.json()


def rn09(gestor, analista, ids: dict[str, int], recusa: tuple[int, dict], treino: dict) -> Regra:
    from gih_modelo import JANELA, PERIODOS_MINIMOS

    from app.servico_segmentacao import Limiares, criterio_em_risco

    r = Regra(
        "RN09", "Queda prevista é entrar em risco, e o modelo exige histórico",
        ("`api/app/servico_segmentacao.py`, `criterio_em_risco`: o rótulo do treino é a regra "
         "do segmento",
         "`modelo/gih_modelo/variaveis.py`: os mínimos de 8 períodos e de 4 de janela",
         "`api/app/servico_previsao.py`: a recusa, a versão em uso e quem recebe previsão"),
        ("api/tests/test_previsao.py::test_o_rotulo_de_risco_e_o_segmento_em_risco",
         "api/tests/test_previsao.py::test_historico_curto_recusa_dizendo_quantos_faltam",
         "api/tests/test_previsao.py::test_versao_que_nao_supera_nao_entra_e_as_versoes_coexistem",
         "modelo/tests/test_variaveis.py::test_os_minimos_sao_os_da_rn09"),
        "O treino é pedido com sete semanas importadas, e de novo com as oito. Depois, a "
        "previsão de três parceiros: um com histórico, um com duas semanas e um em prospecção.",
    )
    r.confere("os mínimos do modelo: períodos para treinar e janela do parceiro",
              [8, 4], [PERIODOS_MINIMOS, JANELA])
    status, corpo = recusa
    r.confere("com sete semanas, o treino é recusado", 409, status)
    detalhe = corpo.get("detail", {})
    r.confere("a recusa diz quantos períodos faltam", True,
              "8" in str(detalhe.get("erro", "")) and "7" in str(detalhe.get("erro", "")))
    r.nota(f"A recusa: \"{detalhe.get('erro')}\"")

    r.confere("com as oito, o treino conclui", "CONCLUIDO", treino["situacao"])
    estado = gestor.get("/api/modelo").json()
    versao = estado["versao_em_uso"]
    promovido = treino.get("promovido")
    r.confere("a versão em uso é da rede só se ela superou a referência; senão, é a referência",
              "MODELO" if promovido else "REFERENCIA", estado["origem"])
    r.nota(f"Neste cenário o treino {'superou' if promovido else 'não superou'} as referências, "
           f"e a versão em uso ficou sendo `{versao}`."
           + (f" O motivo registrado: \"{treino.get('motivo')}\"" if treino.get("motivo") else ""))

    queda = [Decimal(v) for v in reversed(REDE["Loja 02"][-3:])]
    alta = [Decimal(v) for v in reversed(REDE["Loja 03"][-3:])]
    r.confere("o rótulo de risco do treino é o critério do segmento: duas quedas seguidas",
              [True, False], [criterio_em_risco(queda), criterio_em_risco(alta)])
    r.confere("mudar o limiar muda o rótulo junto: com três períodos, as duas quedas não bastam",
              False, criterio_em_risco(queda, Limiares(periodos_tendencia=3)))

    com = analista.get(f"/api/parceiros/{ids['Loja 01']}/previsao").json()
    r.confere("quem tem histórico recebe previsão", True, com["disponivel"])
    r.confere("a previsão diz a versão que a produziu", versao, com["modelo_versao"])
    inicio, fim = periodo(SEMANAS)
    r.confere("e o período de onde parte, que é a última semana",
              [inicio.isoformat(), fim.isoformat()],
              [com["periodo_base"]["data_inicio"], com["periodo_base"]["data_fim"]])
    r.confere("a chance de queda é uma probabilidade", True,
              0.0 <= com["probabilidade_queda"] <= 1.0)

    curto = analista.get(f"/api/parceiros/{ids['Loja 20']}/previsao").json()
    r.confere("quem tem duas semanas de histórico não recebe previsão", False,
              curto["disponivel"])
    r.confere("e a resposta diz por quê", True, bool(curto.get("motivo")))
    r.nota(f"O motivo para a Loja 20: \"{curto.get('motivo')}\"")
    return r


def rn10_e_rn11(gestor, analista, ids: dict[str, int], categorias: dict[str, int]):
    from app.db import Sessao
    from app.modelos import AcaoComercial

    rn10 = Regra(
        "RN10", "O ganho esperado de uma ação soma crescimento e perda evitada",
        ("`api/app/servico_otimizacao.py`, `ganho_em_centavos`: a conta, em centavos inteiros",
         "`nucleo/`: recebe o ganho pronto, e não faz conta de dinheiro"),
        ("api/tests/test_campanha.py::test_ganho_soma_crescimento_e_perda_evitada",
         "api/tests/test_campanha.py::test_o_ganho_de_cada_item_e_o_da_rn10"),
        "Para cada ação do plano calculado, o ganho é refeito aqui, a partir da previsão do "
        "parceiro e dos efeitos da ação no catálogo, e comparado com o que o plano traz.",
    )
    rn11 = Regra(
        "RN11", "Quem recebe ação, e como as cotas contam",
        ("`api/app/servico_otimizacao.py`: a elegibilidade, as cotas em contagem e a cauda "
         "longa pelo ranking",
         "`nucleo/gih_nucleo/viabilidade.py`: a viabilidade decidida antes da busca"),
        ("api/tests/test_campanha.py::test_quem_fica_fora_e_contado_por_motivo",
         "api/tests/test_campanha.py::test_cotas_viram_contagem_em_fracao_exata",
         "api/tests/test_campanha.py::test_a_cauda_longa_vem_do_ranking_e_nao_do_segmento",
         "api/tests/test_campanha.py::test_categoria_so_conta_quando_confirmada"),
        f"Uma campanha de até {MAXIMO_ACOES} ações, com pelo menos 30% para a cauda longa e de "
        "25% a 50% para a categoria Padaria. A Loja 17 foi desativada antes do cálculo.",
    )

    parametros = {
        "orcamento": "2000.00",
        "maximo_acoes": MAXIMO_ACOES,
        "cota_cauda_longa": COTA_CAUDA,
        "cotas_categoria": [{"categoria_id": categorias["Padaria"],
                             "minimo": COTA_PADARIA[0], "maximo": COTA_PADARIA[1]}],
        "aplicacao_inicio": "2026-08-03",
        "aplicacao_fim": "2026-08-09",
        "modo": "SERIAL",
    }
    pedido = gestor.post("/api/otimizacoes", json=parametros)
    if pedido.status_code != 202:
        raise SystemExit(f"O cálculo da campanha respondeu {pedido.status_code}: {pedido.text}")
    execucao = aguardar(gestor, f"/api/otimizacoes/{pedido.json()['id']}")
    itens = execucao.get("itens") or []

    # ---- RN11
    rn11.confere("o cálculo conclui com um plano viável", ["CONCLUIDA", True],
                 [execucao["situacao"], execucao["viavel"]])
    # 22 parceiros: a Loja 20 tem histórico curto, a Loja 14 está em prospecção e a
    # Loja 17 foi desativada.
    rn11.confere("são elegíveis os ativos com previsão", len(REDE) - 3, execucao["elegiveis"])
    excluidos = execucao["excluidos"] or {}
    rn11.confere("e quem ficou de fora é contado por motivo",
                 {"historico_curto": 1, "fora_do_periodo": 0, "sem_previsao": 0,
                  "inativos": 1, "em_prospeccao": 1},
                 {chave: excluidos.get(chave) for chave in
                  ("historico_curto", "fora_do_periodo", "sem_previsao", "inativos",
                   "em_prospeccao")})

    cotas = {c["nome"]: c for c in execucao["cotas"]}
    da_cauda = next((c for c in execucao["cotas"] if c["categoria_id"] is None), {})
    minimo_cauda = math.ceil(Fraction(COTA_CAUDA) * MAXIMO_ACOES)
    rn11.confere(f"30% de {MAXIMO_ACOES} ações vira contagem, para cima: ⌈2,7⌉",
                 3, da_cauda.get("minimo"))
    padaria = cotas.get("Padaria", {})
    rn11.confere(f"25% a 50% de {MAXIMO_ACOES} viram ⌈2,25⌉ e ⌊4,5⌋",
                 [3, 4], [padaria.get("minimo"), padaria.get("maximo")])

    posicao = {nome: i + 1 for i, nome in enumerate(RANKING_ESPERADO)}
    na_cauda = [i["parceiro"] for i in itens if i["cauda_longa"]]
    rn11.confere("a cauda longa de cada item é a posição no ranking: fora das 15 primeiras",
                 {i["parceiro"]: posicao[i["parceiro"]] > TOP_N for i in itens},
                 {i["parceiro"]: i["cauda_longa"] for i in itens})
    rn11.confere("o plano cumpre a cota mínima da cauda longa", True,
                 len(na_cauda) >= minimo_cauda)
    da_padaria = [i["parceiro"] for i in itens if i["categoria"] == "Padaria"]
    rn11.confere("as ações da Padaria ficam entre o mínimo e o máximo", True,
                 3 <= len(da_padaria) <= 4)
    rn11.confere("e são todas de parceiros classificados à mão", True,
                 set(da_padaria) <= set(DA_PADARIA))
    da_02 = next((i for i in itens if i["parceiro"] == "Loja 02"), None)
    if da_02 is not None:
        rn11.confere("a Loja 02, Em Risco no segmento e 3ª no ranking, não conta como cauda "
                     "longa", False, da_02["cauda_longa"])
    else:
        rn11.nota("A Loja 02 não entrou no plano; a leitura pelo ranking está conferida nos "
                  "itens que entraram.")
    da_aurora = next((i for i in itens if i["parceiro"] == "Pizzaria Aurora"), None)
    if da_aurora is not None:
        rn11.confere("a Pizzaria Aurora, com a categoria só sugerida, recebe ação e conta na "
                     "cauda longa, sem categoria", [None, True],
                     [da_aurora["categoria"], da_aurora["cauda_longa"]])
    else:
        rn11.nota("A Pizzaria Aurora não entrou no plano.")
    fora = [i["parceiro"] for i in itens if i["parceiro"] in ("Loja 14", "Loja 17", "Loja 20")]
    rn11.confere("nenhuma ação para quem não é elegível", [], fora)
    rn11.confere("o plano respeita o máximo de ações e o orçamento", True,
                 len(itens) <= MAXIMO_ACOES
                 and Decimal(execucao["custo_total"]) <= Decimal(parametros["orcamento"]))
    rn11.nota(f"O plano: {len(itens)} ações, {len(na_cauda)} para a cauda longa "
              f"({', '.join(na_cauda)}) e {len(da_padaria)} para a Padaria "
              f"({', '.join(da_padaria)}); custo de R$ {execucao['custo_total']} e ganho "
              f"esperado de R$ {execucao['uplift_total']}.")

    # ---- RN10
    s = Sessao()
    try:
        efeitos = {a.id: (a.efeito_crescimento, a.efeito_retencao)
                   for a in s.query(AcaoComercial).all()}
    finally:
        s.close()
    diferentes = {}
    exemplo, maior_chance = None, Decimal(-1)
    for item in itens:
        previsao = analista.get(f"/api/parceiros/{item['parceiro_id']}/previsao").json()
        previsto = Decimal(previsao["faturamento_previsto"])
        p = Decimal(repr(previsao["probabilidade_queda"]))
        crescimento, retencao = efeitos[item["acao_id"]]
        refeito = (previsto * crescimento + previsto * p * retencao).quantize(
            Decimal("0.01"), ROUND_HALF_UP
        )
        if refeito != Decimal(item["ganho"]):
            diferentes[item["parceiro"]] = f"refeito {refeito}, no plano {item['ganho']}"
        # O exemplo do relatório é o item de maior chance de queda: é onde a
        # segunda parcela da conta aparece.
        if p > maior_chance:
            maior_chance = p
            exemplo = (f"{item['parceiro']}, {item['acao']}: {previsto} × {crescimento} + "
                       f"{previsto} × {p} × {retencao} = {refeito}")
    rn10.confere(f"o ganho das {len(itens)} ações do plano, refeito pela fórmula, ao centavo",
                 {}, diferentes)
    soma = sum(Decimal(i["ganho"]) for i in itens)
    rn10.confere("o ganho do plano é a soma dos ganhos das ações",
                 str(soma), execucao["uplift_total"])
    if exemplo:
        rn10.nota(f"Um exemplo: {exemplo}.")
    return rn10, rn11, execucao


def rn07(gestor, categorias: dict[str, int]) -> Regra:
    r = Regra(
        "RN07", "O plano de campanha respeita todas as restrições ou não existe",
        ("`nucleo/gih_nucleo/viabilidade.py`: a viabilidade exata, antes da busca",
         "`api/app/servico_otimizacao.py`: a recusa com a restrição e quanto falta"),
        ("api/tests/test_campanha.py::test_campanha_inviavel_diz_quanto_falta",
         "api/tests/test_campanha.py::test_o_plano_respeita_as_restricoes_e_e_o_otimo",
         "nucleo/tests/test_viabilidade.py::test_a_verificacao_e_exata"),
        f"A mesma campanha, agora exigindo 90% das {MAXIMO_ACOES} ações para a Padaria — nove "
        "ações —, que tem quatro parceiros.",
    )
    parametros = {
        "orcamento": "2000.00",
        "maximo_acoes": MAXIMO_ACOES,
        "cotas_categoria": [{"categoria_id": categorias["Padaria"], "minimo": "0.9"}],
        "aplicacao_inicio": "2026-08-03",
        "aplicacao_fim": "2026-08-09",
        "modo": "SERIAL",
    }
    pedido = gestor.post("/api/otimizacoes", json=parametros)
    if pedido.status_code == 202:
        execucao = aguardar(gestor, f"/api/otimizacoes/{pedido.json()['id']}")
        r.confere("o cálculo conclui dizendo que a campanha é inviável", ["CONCLUIDA", False],
                  [execucao["situacao"], execucao["viavel"]])
        r.confere("não há plano parcial: nenhuma ação", True, not execucao.get("itens"))
        r.confere("a recusa nomeia a restrição violada", True,
                  bool(execucao.get("restricao_violada")))
        r.confere("e diz quanto falta", True, bool(execucao.get("motivo")))
        r.nota(f"A restrição: `{execucao.get('restricao_violada')}`. O motivo: "
               f"\"{execucao.get('motivo')}\"")
    else:
        detalhe = pedido.json().get("detail", {})
        r.confere("a campanha inviável é recusada", 409, pedido.status_code)
        r.confere("a recusa nomeia a restrição e diz quanto falta", True,
                  bool(detalhe.get("erro")))
        r.nota(f"A recusa: \"{detalhe.get('erro')}\"")
    return r


def rn06_e_rn08(gestor, analista, execucao: dict):
    from app.guarda_numerica import numeros_sem_origem

    rn06 = Regra(
        "RN06", "Nenhuma mensagem sai sem aprovação humana",
        ("`api/app/rotas/mensagens.py`: aprovar, editar e rejeitar só com o perfil Gestor",
         "`api/app/servico_aprovacao.py`: a decisão grava quem decidiu e quando",
         "`api/migrations/`: o banco recusa mensagem decidida sem autor"),
        ("api/tests/test_aprovacao.py::"
         "test_o_analista_ve_a_fila_mas_nao_decide_e_a_tentativa_fica_na_auditoria",
         "api/tests/test_aprovacao.py::test_o_banco_recusa_mensagem_decidida_sem_autor",
         "api/tests/test_aprovacao.py::test_a_exportacao_traz_so_as_aprovadas_prontas_para_envio"),
        "As mensagens do plano calculado são geradas pelo analista. Ele tenta aprovar uma; "
        "depois o gestor aprova uma e rejeita outra.",
    )
    rn08 = Regra(
        "RN08", "O modelo de linguagem não produz número",
        ("`api/app/guarda_numerica.py`: o texto com número que não veio dos fatos é reprovado",
         "`api/app/servico_mensagens.py`: texto reprovado vira modelo fixo",
         "`api/app/assistente/`: a resposta é montada dos fatos, e o modelo só redige"),
        ("api/tests/test_guarda_numerica.py::test_numero_que_nao_veio_dos_fatos_e_apontado",
         "api/tests/test_mensagens.py::test_numero_inventado_troca_pelo_modelo_fixo_e_diz_qual",
         "api/tests/test_assistente.py::test_numero_inventado_nunca_chega_a_tela"),
        "A guarda é chamada com os fatos de uma mensagem gerada: uma vez com o texto dela, "
        "outra com o mesmo texto e um número acrescentado. Depois, o gestor edita uma "
        "mensagem e escreve um desconto que não está nos fatos.",
    )

    pedido = analista.post("/api/mensagens/lotes",
                           json={"tipo": "PLANO", "execucao_id": execucao["id"]})
    if pedido.status_code != 202:
        raise SystemExit(f"A geração das mensagens respondeu {pedido.status_code}: {pedido.text}")
    lote = aguardar(analista, f"/api/mensagens/lotes/{pedido.json()['id']}")
    mensagens = lote["mensagens"] or []
    rn06.confere("uma mensagem para cada ação do plano", len(execucao["itens"]), len(mensagens))
    rn06.confere("todas nascem pendentes", ["PENDENTE"],
                 sorted({m["estado"] for m in mensagens}))
    exportadas = gestor.get("/api/mensagens/exportacao.csv").content.decode("utf-8-sig")
    rn06.confere("com tudo pendente, o arquivo para envio não tem mensagem nenhuma", 1,
                 len(exportadas.strip().splitlines()))

    primeira, segunda, terceira = mensagens[0], mensagens[1], mensagens[2]
    do_analista = analista.post(f"/api/mensagens/{primeira['id']}/aprovacao")
    rn06.confere("o analista, que gerou, não aprova", 403, do_analista.status_code)
    ainda = gestor.get("/api/mensagens?tamanho=100").json()["total"]
    rn06.confere("e a mensagem continua na fila", len(mensagens), ainda)
    aprovada = gestor.post(f"/api/mensagens/{primeira['id']}/aprovacao").json()
    rn06.confere("o gestor aprova, e a decisão registra quem decidiu",
                 ["APROVADA", "Gestor da Revisão"],
                 [aprovada["estado"], aprovada["decidida_por"]])
    rejeitada = gestor.post(f"/api/mensagens/{segunda['id']}/rejeicao",
                            json={"motivo": "Tom errado"}).json()
    rn06.confere("o gestor rejeita, com o motivo", ["REJEITADA", "Tom errado"],
                 [rejeitada["estado"], rejeitada["motivo_rejeicao"]])
    exportadas = gestor.get("/api/mensagens/exportacao.csv").content.decode("utf-8-sig")
    rn06.confere("o arquivo para envio passa a ter só a aprovada", 2,
                 len(exportadas.strip().splitlines()))
    de_novo = gestor.post(f"/api/mensagens/{primeira['id']}/rejeicao", json={})
    rn06.confere("a mensagem já decidida não é decidida de novo", 409, de_novo.status_code)

    # ---- RN08
    fatos = terceira["fatos"]
    rn08.confere("o texto gerado só tem números dos fatos", [],
                 numeros_sem_origem(terceira["texto"], fatos))
    inventado = terceira["texto"] + " Aproveite 37% de desconto."
    rn08.confere("o mesmo texto com um número acrescentado é reprovado, e a guarda diz qual",
                 ["37%"], numeros_sem_origem(inventado, fatos))
    rn08.confere("nenhuma mensagem do lote chegou à fila com número fora dos fatos", [],
                 sorted({n for m in mensagens for n in m["numeros_fora_dos_fatos"]}))
    editada = gestor.post(f"/api/mensagens/{terceira['id']}/edicao",
                          json={"texto": inventado}).json()
    rn08.confere("o número que o gestor escreveu fica apontado na fila, para ele conferir",
                 ["37%"], editada["numeros_fora_dos_fatos"])
    rn08.confere("e a mensagem editada continua pendente: editar não aprova", "PENDENTE",
                 editada["estado"])
    rn08.nota(f"As mensagens deste roteiro saíram do redator `{terceira['redator']}`: o modelo "
              "de linguagem não está no ar aqui, e o sistema funciona igual sem ele. O "
              "assistente com o modelo de verdade, com as perguntas sem resposta possível, "
              "está medido em `docs/medicoes/assistente.md`.")
    return rn06, rn08


# ---------------------------------------------------------------- o documento
def montar(regras: list[Regra], ambiente: dict[str, str]) -> str:
    total = sum(len(r.linhas) for r in regras)
    passaram = sum(ok for r in regras for *_, ok in r.linhas)
    saida = [
        "# Revisão das regras de negócio — RN01 a RN11",
        "",
        "> **Gerado por `scripts/revisar_regras.py`. Não edite à mão:** rode o roteiro de novo.",
        "",
        "Cada regra de `docs/02-requisitos.md`, parte IV, contra o que o sistema faz: o cenário, "
        "o que a regra manda e o que a aplicação devolveu. O esperado está escrito no roteiro, "
        "deduzido da regra — não vem do código que se revisa.",
        "",
        f"**Resultado: {passaram} de {total} conferências passaram, nas {len(regras)} regras.**",
        "",
        "## Ambiente",
        "",
        "| Item | Valor |",
        "|---|---|",
        *[f"| {chave} | {valor} |" for chave, valor in ambiente.items()],
        "",
        "## Como reproduzir",
        "",
        "```bash",
        "api/.venv/Scripts/python scripts/revisar_regras.py",
        "```",
        "",
        "## O cenário",
        "",
        f"{len(REDE)} parceiros e {SEMANAS} semanas, importados pela API. O faturamento das três "
        "últimas semanas decide a tendência, e o da última, o ranking:",
        "",
        "| Parceiro | Antepenúltima | Penúltima | Última | Posição | Segmento esperado |",
        "|---|--:|--:|--:|--:|---|",
    ]
    posicao = {nome: i + 1 for i, nome in enumerate(RANKING_ESPERADO)}
    for nome, serie in REDE.items():
        tres = [("—" if v is None else f"{v:,}".replace(",", ".")) for v in serie[-3:]]
        saida.append(f"| {nome} | {tres[0]} | {tres[1]} | {tres[2]} | {posicao[nome]}ª | "
                     f"{SEGMENTO_ESPERADO[nome]} |")
    saida += [
        "",
        f"A {EM_PROSPECCAO} está marcada como prospecção; as lojas 05 a 08 foram classificadas à "
        f"mão como Padaria; a {DESATIVADO} é desativada antes da campanha.",
        "",
        "## Resumo",
        "",
        "| Regra | Conferências | Resultado |",
        "|---|--:|---|",
    ]
    for r in regras:
        certas = sum(ok for *_, ok in r.linhas)
        saida.append(f"| **{r.codigo}** — {r.nome} | {certas} de {len(r.linhas)} | "
                     f"{'ok' if certas == len(r.linhas) else 'FALHA'} |")
    for r in regras:
        saida += ["", f"## {r.codigo} — {r.nome}", "", f"**Cenário.** {r.cenario}", "",
                  "**Onde está no código.**", "", *[f"- {onde}" for onde in r.onde], "",
                  "**Testes automatizados que a cobram.**", "",
                  *[f"- `{teste}`" for teste in r.testes], "",
                  "| O que se confere | Esperado | Voltou | |", "|---|---|---|---|"]
        for o_que, esperado, voltou, ok in r.linhas:
            saida.append(f"| {o_que} | {esperado} | {voltou} | {'ok' if ok else 'FALHA'} |")
        for nota in r.notas:
            saida += ["", nota]
    return "\n".join(saida) + "\n"


def main() -> int:
    p = argparse.ArgumentParser(description="Revisa as regras RN01 a RN11 (H99).")
    p.add_argument("--banco", default="gih_regras", help="nome do banco da revisão")
    p.add_argument("--relatorio", default=str(RAIZ / "docs" / "medicoes" / "regras.md"))
    args = p.parse_args()

    base = urlsplit(_url_base())
    if args.banco == base.path.lstrip("/"):
        raise SystemExit("O banco da revisão não pode ser o banco de trabalho.")
    url = urlunsplit(base._replace(path=f"/{args.banco}"))
    # Antes de qualquer import de `app`: a engine nasce no import, lendo a configuração.
    os.environ["DATABASE_URL"] = url

    print(f"recriando o banco {args.banco} ...")
    _recriar_banco(url)

    from fastapi.testclient import TestClient
    from sqlalchemy import func, select

    from app.db import Sessao
    from app.main import app

    contas = criar_usuarios()
    regras: list[Regra] = []
    with TestClient(app) as gestor:
        analista, administrador = TestClient(app), TestClient(app)
        for cliente, perfil in ((gestor, "GESTOR"), (analista, "ANALISTA"),
                                (administrador, "ADMINISTRADOR")):
            login, senha = contas[perfil]
            if cliente.post("/api/sessao", json={"login": login, "senha": senha}).status_code != 201:
                raise SystemExit(f"A conta {login} não entrou.")

        print("\nRN03 — antes de qualquer importação")
        regras.append(rn03(analista))

        print("\npreparando: categorias, a primeira semana, a prospecção e as padarias")
        categorias = {
            nome: analista.post("/api/categorias", json={"nome": nome}).json()["id"]
            for nome in ("Pizzaria", "Padaria")
        }
        importar(analista, 1)
        ids = ids_dos_parceiros(analista)
        analista.patch(f"/api/parceiros/{ids[EM_PROSPECCAO]}", json={"status": "PROSPECCAO"})
        for nome in DA_PADARIA:
            analista.patch(f"/api/parceiros/{ids[nome]}",
                           json={"categoria_id": categorias["Padaria"]})
        for semana in range(2, SEMANAS):
            importar(analista, semana)
        recusa = rn09_recusa(gestor)
        importar(analista, SEMANAS)
        ids = ids_dos_parceiros(analista)

        print("\nRN01, RN02, RN04 e RN05 — depois das oito semanas")
        da_rn01 = rn01(gestor, ids)
        da_rn02 = rn02(gestor)
        da_rn04 = rn04(gestor)
        da_rn05 = rn05(analista, ids, categorias)

        print("\nRN09 — o treino e as previsões")
        pedido = gestor.post("/api/modelo/treinos")
        if pedido.status_code != 202:
            raise SystemExit(f"O treino respondeu {pedido.status_code}: {pedido.text}")
        treino = aguardar(gestor, f"/api/modelo/treinos/{pedido.json()['id']}")
        da_rn09 = rn09(gestor, analista, ids, recusa, treino)

        print("\nRN10 e RN11 — a campanha")
        for acao in (VISITA, VITRINE):
            gestor.post("/api/acoes-comerciais", json=acao)
        analista.patch(f"/api/parceiros/{ids[DESATIVADO]}", json={"ativo": False})
        da_rn10, da_rn11, execucao = rn10_e_rn11(gestor, analista, ids, categorias)

        print("\nRN07 — a campanha inviável")
        da_rn07 = rn07(gestor, categorias)

        print("\nRN06 e RN08 — as mensagens")
        da_rn06, da_rn08 = rn06_e_rn08(gestor, analista, execucao)

        regras = [da_rn01, da_rn02, regras[0], da_rn04, da_rn05, da_rn06, da_rn07, da_rn08,
                  da_rn09, da_rn10, da_rn11]

    s = Sessao()
    try:
        versao_pg = s.scalar(select(func.version())).split(",")[0]
    finally:
        s.close()
    ambiente = {
        "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "Banco": f"`{args.banco}` — **separado do banco de trabalho**, recriado a cada execução",
        "PostgreSQL": versao_pg,
        "Python": sys.version.split()[0],
        "Aplicação": "em processo, pelo `TestClient`: as rotas, a sessão e os perfis de verdade",
        "Otimizador": f"modo {execucao['modo']}",
        "Modelo de linguagem": "fora do ar: as mensagens saem do modelo fixo",
    }
    Path(args.relatorio).write_text(montar(regras, ambiente), encoding="utf-8", newline="\n")

    total = sum(len(r.linhas) for r in regras)
    passaram = sum(ok for r in regras for *_, ok in r.linhas)
    print(f"\nResultado: {passaram} de {total} conferências passaram.")
    print(f"relatório: {args.relatorio}")
    return 0 if passaram == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
