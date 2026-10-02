"""A matriz de rastreabilidade confere com o que existe — história H98.

`docs/11-rastreabilidade.md` diz, para cada requisito, o caso de uso, a rota, a
tela e o teste. Um documento desses envelhece na primeira rota renomeada, e
ninguém percebe: a tabela continua bonita. Por isso estes testes leem o
documento e o comparam com a aplicação, com `docs/02`, com `docs/03` e com os
arquivos do repositório.

**O teste que mais importa é o dos perfis.** Ele cruza a coluna Perfis de cada
requisito com os perfis que as rotas dele aceitam — lidos do `exigir` de cada
rota, que é de onde a autorização sai de verdade. Na primeira execução ele
achou sete requisitos cuja coluna dizia uma coisa e a API fazia outra (as notas
4 e 6 do documento).

Nada aqui toca o banco: é leitura de arquivo e das rotas registradas.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.routing import APIRoute

from app.dependencias import perfis_da_rota
from app.main import app
from app.modelos import Perfil

RAIZ = Path(__file__).resolve().parents[2]
MATRIZ = RAIZ / "docs" / "11-rastreabilidade.md"
REQUISITOS = RAIZ / "docs" / "02-requisitos.md"
CASOS_DE_USO = RAIZ / "docs" / "03-casos-de-uso.md"
ROTAS_DA_INTERFACE = RAIZ / "web" / "src" / "App.jsx"

SIGLA = {
    "ADM": Perfil.ADMINISTRADOR,
    "GES": Perfil.GESTOR,
    "ANL": Perfil.ANALISTA,
    "PAR": Perfil.PARCEIRO,
}
# As rotas que o FastAPI cria sozinho não são superfície da aplicação.
IGNORADAS = {"/api/openapi.json", "/api/docs", "/api/docs/oauth2-redirect", "/api/redoc"}

ROTA = re.compile(r"^(GET|POST|PUT|PATCH|DELETE) (/api/\S+)$")
CRASE = re.compile(r"`([^`]+)`")


# ------------------------------------------------------------------ leitura
def _linhas(arquivo: Path, prefixo: str) -> dict[str, list[str]]:
    """As linhas de tabela que começam por `| **RF01** |`, com as células."""
    linhas = {}
    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        achado = re.match(rf"\| \*\*({prefixo}\d+)\*\* \|", linha)
        if achado:
            linhas[achado.group(1)] = [c.strip() for c in linha.strip().strip("|").split(" | ")]
    return linhas


def _perfis(celula: str) -> frozenset[Perfil]:
    if celula == "todos":
        return frozenset(Perfil)
    return frozenset(SIGLA[sigla.strip()] for sigla in celula.split(","))


def _rotas_da_aplicacao() -> dict[tuple[str, str], frozenset[Perfil]]:
    """Cada rota com os perfis que ela aceita; sem `exigir`, são os quatro."""
    rotas = {}
    for rota in app.routes:
        if not isinstance(rota, APIRoute) or rota.path in IGNORADAS:
            continue
        for metodo in rota.methods - {"HEAD", "OPTIONS"}:
            rotas[(metodo, rota.path)] = perfis_da_rota(rota) or frozenset(Perfil)
    return rotas


def _rotas_citadas(celula: str) -> list[tuple[str, str]]:
    return [
        (achado.group(1), achado.group(2))
        for texto in CRASE.findall(celula)
        if (achado := ROTA.match(texto))
    ]


def _casos_de_uso_por_requisito() -> dict[str, set[str]]:
    """O que `docs/03` associa a cada requisito, na visão geral e na cobertura."""
    por_requisito: dict[str, set[str]] = {}

    def somar(requisitos: str, casos: list[str]) -> None:
        requisitos = re.sub(
            r"RF(\d+) a RF(\d+)",
            lambda m: ", ".join(f"RF{n:02d}" for n in range(int(m.group(1)), int(m.group(2)) + 1)),
            requisitos,
        )
        for requisito in re.findall(r"RF\d+", requisitos):
            por_requisito.setdefault(requisito, set()).update(casos)

    for linha in CASOS_DE_USO.read_text(encoding="utf-8").splitlines():
        celulas = [c.strip() for c in linha.strip().strip("|").split(" | ")]
        # A visão geral: | **UC01** | nome | ator | RF01, RF02 |
        if re.fullmatch(r"\*\*UC\d+\*\*", celulas[0]) and len(celulas) == 4:
            somar(celulas[3], [celulas[0].strip("*")])
        # A cobertura: | RF09 a RF13 | UC03 |
        elif celulas[0].startswith("RF") and len(celulas) == 2:
            somar(celulas[0], re.findall(r"UC\d+", celulas[1]))
    return por_requisito


FUNCIONAIS = _linhas(MATRIZ, "RF")
NAO_FUNCIONAIS = _linhas(MATRIZ, "RNF")
# RF: ID, Perfis, Caso de uso, Rotas, Telas, Testes, Situação.
PERFIS, CASOS, ROTAS, TELAS, TESTES, SITUACAO = range(1, 7)


# ---------------------------------------------------------------- requisitos
def test_a_matriz_traz_todos_os_requisitos_funcionais_e_so_eles():
    assert sorted(FUNCIONAIS) == sorted(_linhas(REQUISITOS, "RF"))
    assert len(FUNCIONAIS) == 56


def test_a_matriz_traz_todos_os_requisitos_nao_funcionais_e_so_eles():
    assert sorted(NAO_FUNCIONAIS) == sorted(_linhas(REQUISITOS, "RNF"))


def test_a_coluna_de_perfis_e_a_do_documento_de_requisitos():
    """A matriz repete a coluna para ser lida sozinha; repetida, não pode divergir."""
    requisitos = _linhas(REQUISITOS, "RF")
    diferentes = {
        rf: (celulas[PERFIS], requisitos[rf][-1])
        for rf, celulas in FUNCIONAIS.items()
        if _perfis(celulas[PERFIS]) != _perfis(requisitos[rf][-1])
    }
    assert not diferentes


def test_o_caso_de_uso_citado_e_o_que_docs_03_associa_ao_requisito():
    associados = _casos_de_uso_por_requisito()
    errados = {}
    for rf, celulas in FUNCIONAIS.items():
        citados = set(re.findall(r"UC\d+", celulas[CASOS]))
        if not citados or not citados <= associados.get(rf, set()):
            errados[rf] = (sorted(citados), sorted(associados.get(rf, set())))
    assert not errados, f"caso de uso citado × o de docs/03: {errados}"


# --------------------------------------------------------------------- rotas
def test_toda_rota_citada_existe_na_aplicacao():
    existentes = _rotas_da_aplicacao()
    texto = MATRIZ.read_text(encoding="utf-8")
    citadas = {rota for trecho in CRASE.findall(texto) for rota in _rotas_citadas(f"`{trecho}`")}

    assert citadas, "nenhuma rota lida do documento: o formato mudou?"
    assert not citadas - set(existentes), (
        "A matriz cita rota que a aplicação não tem: "
        + ", ".join(f"{m} {c}" for m, c in sorted(citadas - set(existentes)))
    )


def test_toda_rota_da_aplicacao_esta_no_documento():
    """Rota nova sem requisito, ou sem a explicação de por que não tem, reprova."""
    texto = MATRIZ.read_text(encoding="utf-8")
    citadas = {rota for trecho in CRASE.findall(texto) for rota in _rotas_citadas(f"`{trecho}`")}
    faltando = set(_rotas_da_aplicacao()) - citadas

    assert not faltando, (
        "Rota da aplicação fora de docs/11-rastreabilidade.md: "
        + ", ".join(f"{m} {c}" for m, c in sorted(faltando))
    )


@pytest.mark.parametrize("rf", sorted(FUNCIONAIS))
def test_os_perfis_do_requisito_sao_os_das_rotas_dele(rf):
    """A união dos perfis das rotas citadas é exatamente a coluna Perfis de `docs/02`.

    Requisito que promete a um perfil o que nenhuma rota lhe dá, e rota que
    entrega a um perfil o que o requisito não previu, caem aqui.
    """
    rotas = _rotas_citadas(FUNCIONAIS[rf][ROTAS])
    if not rotas:
        # Só o RF06 e o RF16 podem não ter rota, e o documento diz por quê.
        assert rf in {"RF06", "RF16"}, f"{rf} sem rota citada"
        return

    existentes = _rotas_da_aplicacao()
    das_rotas = frozenset().union(*(existentes[rota] for rota in rotas if rota in existentes))
    do_requisito = _perfis(_linhas(REQUISITOS, "RF")[rf][-1])

    assert das_rotas == do_requisito, (
        f"{rf}: docs/02 diz {sorted(p.value for p in do_requisito)}, "
        f"e as rotas aceitam {sorted(p.value for p in das_rotas)}"
    )


# --------------------------------------------------------------------- telas
def test_toda_tela_citada_e_um_endereco_da_interface():
    enderecos = set(re.findall(r'path="([^"]+)"', ROTAS_DA_INTERFACE.read_text(encoding="utf-8")))
    enderecos.add("/")  # a rota inicial é declarada como `index`, sem `path`

    citadas = {
        tela
        for celulas in FUNCIONAIS.values()
        for tela in CRASE.findall(celulas[TELAS])
        if tela.startswith("/")
    }
    assert citadas, "nenhuma tela lida do documento: o formato mudou?"
    fora = sorted(citadas - enderecos)
    assert not fora, f"tela citada que a interface não tem: {fora}"


# -------------------------------------------------------------------- testes
def _arquivos_e_testes_citados() -> list[tuple[str, str, str | None]]:
    citados = []
    for requisito, celulas in {**FUNCIONAIS, **NAO_FUNCIONAIS}.items():
        for texto in CRASE.findall(" ".join(celulas[1:])):
            if ROTA.match(texto) or texto.startswith("/") or " " in texto:
                continue
            caminho, _, nome = texto.partition("::")
            citados.append((requisito, caminho, nome or None))
    return citados


def test_todo_arquivo_citado_existe_e_todo_teste_citado_esta_nele():
    citados = _arquivos_e_testes_citados()
    assert len(citados) > 150, "poucas citações lidas do documento: o formato mudou?"

    problemas = []
    for requisito, caminho, nome in citados:
        arquivo = RAIZ / caminho
        if not arquivo.is_file():
            problemas.append(f"{requisito}: {caminho} não existe")
        elif nome and not re.search(
            rf"^(async )?def {re.escape(nome)}\(", arquivo.read_text(encoding="utf-8"), re.M
        ):
            problemas.append(f"{requisito}: {caminho} não tem {nome}")
    assert not problemas, "\n".join(problemas)


def test_todo_requisito_tem_ao_menos_um_teste_ou_uma_medicao():
    sem_evidencia = [
        requisito
        for requisito, celulas in {**FUNCIONAIS, **NAO_FUNCIONAIS}.items()
        if not any(r == requisito for r, _, _ in _arquivos_e_testes_citados())
    ]
    assert not sem_evidencia


# ------------------------------------------------------------------ situação
def test_o_resumo_dos_nao_funcionais_conta_o_que_a_tabela_diz():
    """"23 atendidos, 5 em parte e 1 em aberto" não pode ser escrito à mão e esquecido."""
    situacoes = [celulas[-1] for celulas in NAO_FUNCIONAIS.values()]
    contagem = {
        "atendidos": sum(s.startswith("Atende") for s in situacoes),
        "em parte": sum(s.startswith("Parcial") for s in situacoes),
        "em aberto": sum(s.startswith("Em aberto") for s in situacoes),
    }
    assert sum(contagem.values()) == len(situacoes), "situação fora de Atende, Parcial e Em aberto"

    resumo = re.search(
        r"(\d+) requisitos não funcionais: (\d+) atendidos, (\d+) em parte .*? "
        r"e (\d+) em\s+>?\s*aberto",
        MATRIZ.read_text(encoding="utf-8"),
        re.S,
    )
    assert resumo, "o resumo dos requisitos não funcionais não foi achado"
    total, atendidos, em_parte, em_aberto = map(int, resumo.groups())
    assert (total, atendidos, em_parte, em_aberto) == (
        len(situacoes), contagem["atendidos"], contagem["em parte"], contagem["em aberto"],
    )


def test_todo_requisito_funcional_esta_implementado():
    """É o que a Sprint 08 afirma. Se um deixar de estar, a frase do documento cai junto."""
    fora = {
        rf: celulas[SITUACAO]
        for rf, celulas in FUNCIONAIS.items()
        if not celulas[SITUACAO].startswith("Implementado")
    }
    assert not fora
