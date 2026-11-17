"""O modelo de dados documentado é o banco que roda (H108).

O `docs/08` descreve as tabelas, as chaves e as contagens do catálogo; as
migrações criam o banco; os modelos em `app/modelos.py` são o que a API usa.
São três descrições do mesmo esquema, e cada uma pode mudar sem as outras —
foi assim que o documento ficou dizendo "dezenove entidades" com vinte tabelas
no banco, e desenhando como obrigatórias chaves que aceitam nulo. Este teste as
amarra:

- as migrações criam exatamente o que os modelos descrevem (o `compare_metadata`
  do Alembic, contra o banco de teste, que o `conftest` monta pelas migrações);
- toda tabela e toda coluna do modelo relacional do `docs/08` existem no banco,
  e o banco não tem nenhuma a mais; as colunas marcadas com `*` são as chaves
  estrangeiras, nem uma a mais, nem uma a menos;
- toda tabela tem a sua entidade, e a cardinalidade de cada diagrama é a da chave;
- as contagens do catálogo na seção 6 são as que o PostgreSQL dá.

Mudou o esquema? A migração, o modelo e o `docs/08` entram no mesmo Pull Request,
ou este teste reprova.
"""
from __future__ import annotations

import re
from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import text

from app.db import Base, engine

DOCUMENTO = Path(__file__).resolve().parents[2] / "docs" / "08-modelo-de-dados.md"
FORA = {"alembic_version"}
# A tentativa de login não se liga a nada, de propósito: ela registra até login
# que não existe, e por isso não tem chave para o usuário (RNF11).
SEM_LIGACAO = {"tentativa_login"}

# `A <lado de A>--<lado de B> B : verbo`. O lado de cada entidade diz quantas
# dela há para uma da outra: `||` exatamente uma, `|o`/`o|` zero ou uma,
# `}o`/`o{` zero ou mais, `}|`/`|{` uma ou mais.
RELACAO = re.compile(r"^\s*(\w+) ([|}][|o])--([o|][|{]) (\w+)", re.M)


def _texto() -> str:
    return DOCUMENTO.read_text(encoding="utf-8")


def _relacional() -> dict[str, list[str]]:
    """As tabelas do bloco do modelo relacional: `tabela(coluna, fk*, ...)`, em várias linhas."""
    secao = _texto()[_texto().index("## 2. Modelo relacional"):]
    inicio = secao.index("```") + 3
    bloco = secao[inicio: secao.index("```", inicio)]
    return {
        nome: [c.strip() for c in colunas.replace("\n", " ").split(",") if c.strip()]
        for nome, colunas in re.findall(r"(\w+)\(([^)]*)\)", bloco)
    }


def _diagramas() -> dict[str, str]:
    """Os blocos `erDiagram` do documento, pelo nome do marcador acima de cada um."""
    padrao = r"<!-- diagrama: ([\w-]+) -->\n```mermaid\nerDiagram\n(.*?)```"
    return dict(re.findall(padrao, _texto(), re.S))


def _consulta(sql: str) -> list:
    with engine.connect() as c:
        return c.execute(text(sql)).all()


def test_as_migracoes_criam_o_que_os_modelos_descrevem():
    """Coluna, tipo, nulo, índice e chave que um lado tem e o outro não, o Alembic acusa."""
    with engine.connect() as c:
        diferencas = compare_metadata(MigrationContext.configure(c), Base.metadata)
    assert diferencas == [], "Migrações e modelos divergem:\n" + "\n".join(map(str, diferencas))


def test_toda_tabela_e_coluna_do_documento_existe_no_banco_e_o_banco_nao_tem_mais():
    documento = {t: {c.rstrip("*") for c in cs} for t, cs in _relacional().items()}
    banco: dict[str, set[str]] = {}
    for tabela, coluna in _consulta(
        "SELECT table_name, column_name FROM information_schema.columns "
        "WHERE table_schema = 'public'"
    ):
        if tabela not in FORA:
            banco.setdefault(tabela, set()).add(coluna)

    assert sorted(documento) == sorted(banco), "as tabelas do docs/08 e as do banco divergem"
    divergentes = {
        t: {
            "só no documento": sorted(documento[t] - banco[t]),
            "só no banco": sorted(banco[t] - documento[t]),
        }
        for t in banco
        if documento[t] != banco[t]
    }
    assert not divergentes, divergentes


def test_as_chaves_estrangeiras_do_documento_sao_as_do_banco():
    documento = {
        (t, c.rstrip("*")) for t, cs in _relacional().items() for c in cs if c.endswith("*")
    }
    banco = {
        tuple(linha)
        for linha in _consulta(
            """
            SELECT kcu.table_name, kcu.column_name
              FROM information_schema.table_constraints tc
              JOIN information_schema.key_column_usage kcu
                   USING (constraint_schema, constraint_name)
             WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public'
            """
        )
    }
    assert documento == banco, {
        "marcadas com * sem chave no banco": sorted(documento - banco),
        "chaves do banco sem o *": sorted(banco - documento),
    }


def test_cada_entidade_do_banco_esta_na_tabela_de_entidades_e_no_mer():
    secao = _texto()[_texto().index("### Entidades e atributos"):]
    secao = secao[: secao.index("\n\n###")]
    na_tabela = {
        re.sub(r"(?<!^)(?=[A-Z])", "_", nome).lower()
        for nome in re.findall(r"^\| \*\*(\w+)\*\* \|", secao, re.M)
    }
    no_mer = {
        nome.lower()
        for a, _, _, b in RELACAO.findall(_diagramas()["mer-conceitual"])
        for nome in (a, b)
    }
    tabelas = set(_relacional())

    assert na_tabela == tabelas, {
        "faltam na tabela": sorted(tabelas - na_tabela),
        "sobram": sorted(na_tabela - tabelas),
    }
    assert no_mer == tabelas - SEM_LIGACAO, sorted(tabelas - SEM_LIGACAO - no_mer)


def test_a_cardinalidade_dos_diagramas_e_a_da_chave_estrangeira():
    """A chave que aceita nulo aponta para "zero ou um"; a obrigatória, para "exatamente um".

    E nenhuma relação diz "um ou mais": nada no banco obriga um plano a ter item —
    o plano viável sem ação existe, quando nenhuma cabe no orçamento.
    """
    chaves: dict[tuple[str, str], list[bool]] = {}
    for tabela in Base.metadata.sorted_tables:
        for fk in tabela.foreign_keys:
            chaves.setdefault((tabela.name, fk.column.table.name), []).append(fk.parent.nullable)

    erradas = []
    for nome, corpo in _diagramas().items():
        for a, lado_a, lado_b, b in RELACAO.findall(corpo):
            a, b = a.lower(), b.lower()
            relacao = f"{nome}: {a} {lado_a}--{lado_b} {b}"
            if lado_b.endswith("{") and lado_b.startswith("|"):
                erradas.append(f"{relacao} diz 'um ou mais', e nada no banco obriga")
            # A chave mora em b e aponta para a (o lado de a diz quantos a há
            # para um b), ou mora em a e aponta para b.
            for filho, pai, lado in ((b, a, lado_a), (a, b, lado_b)):
                nulos = chaves.get((filho, pai))
                if nulos and len(nulos) == 1:
                    esperado = {"|o", "o|"} if nulos[0] else {"||"}
                    if lado not in esperado:
                        situacao = "aceita nulo" if nulos[0] else "é obrigatória"
                        erradas.append(f"{relacao} — a chave de {filho} para {pai} {situacao}")
    assert not erradas, "\n".join(erradas)


def test_a_contagem_do_catalogo_e_a_do_documento():
    """A tabela "Contagem por consulta ao catálogo", da seção 6."""
    secao = _texto()[_texto().index("**Contagem por consulta ao catálogo"):]
    tabela = secao[: secao.index("\n\n", secao.index("| Objeto"))]
    linhas = re.findall(r"^\| ([^|]+?) \| (\d+) \|$", tabela, re.M)
    documentado = {rotulo.strip(): int(n) for rotulo, n in linhas}

    def restricoes(tipo: str) -> int:
        return _consulta(
            "SELECT count(*) FROM pg_constraint k JOIN pg_class t ON t.oid = k.conrelid "
            "JOIN pg_namespace n ON n.oid = t.relnamespace "
            f"WHERE n.nspname = 'public' AND k.contype = '{tipo}' "
            "AND t.relname <> 'alembic_version'"
        )[0][0]

    medido = {
        "Tabelas de domínio": _consulta(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public' "
            "AND table_type = 'BASE TABLE' AND table_name <> 'alembic_version'"
        )[0][0],
        "Chaves primárias": restricoes("p"),
        "Chaves estrangeiras": restricoes("f"),
        "Restrições `UNIQUE`": restricoes("u"),
        "Restrições `CHECK` declaradas": restricoes("c"),
        "Índices": _consulta(
            "SELECT count(*) FROM pg_indexes "
            "WHERE schemaname = 'public' AND tablename <> 'alembic_version'"
        )[0][0],
        "Tipos `ENUM`": _consulta(
            "SELECT count(*) FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace "
            "WHERE n.nspname = 'public' AND t.typtype = 'e'"
        )[0][0],
    }
    assert documentado == medido
