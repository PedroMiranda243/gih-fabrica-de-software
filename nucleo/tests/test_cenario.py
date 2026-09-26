"""O cenário sintético do benchmark (UC09, H57): o tamanho escolhido dá sempre o mesmo
problema, viável, com a forma de uma campanha de verdade."""
import ast
from decimal import Decimal
from pathlib import Path

import pytest

from gih_nucleo import SEM_CATEGORIA, verificar_viabilidade
from gih_nucleo.cenario import CATALOGO, SEMENTE, TOP_N, sintetico

GERADOR = Path(__file__).resolve().parents[2] / "scripts" / "gerar_dados_sinteticos.py"


# Todo tamanho de 100 a 199, onde K é pequeno e o arredondamento das cotas aperta,
# e alguns maiores; com cada número de ações.
@pytest.mark.parametrize("acoes", range(1, 11))
def test_todo_cenario_da_faixa_e_viavel(acoes):
    tamanhos = [*range(100, 200), 250, 999, 2000, 4321, 10_000]
    inviaveis = [n for n in tamanhos if verificar_viabilidade(sintetico(n, acoes)) is not None]
    assert inviaveis == []


def test_o_mesmo_tamanho_da_o_mesmo_problema():
    assert sintetico(500, 5) == sintetico(500, 5)
    assert sintetico(500, 5) != sintetico(500, 5, semente=SEMENTE + 1)
    assert sintetico(500, 5) != sintetico(501, 5)


def test_mais_acoes_nao_mudam_os_parceiros():
    """As ações além do catálogo saem de outro gerador: os parceiros sorteados são os
    mesmos, e o ganho das cinco primeiras ações também."""
    cinco, dez = sintetico(700, 5), sintetico(700, 10)
    assert dez.custo[:5] == cinco.custo
    assert [g[:5] for g in dez.ganho] == list(cinco.ganho)
    assert (dez.categoria, dez.cauda) == (cinco.categoria, cinco.cauda)
    assert len(set(dez.custo)) > 5  # as sorteadas não repetem as do catálogo


def test_a_forma_de_uma_campanha():
    inst = sintetico(2000, 5)
    k = 2000 // 40
    assert (inst.maximo_acoes, inst.orcamento) == (k, k * 20_000)  # R$ 200 por ação
    assert sum(inst.cauda) == 2000 - TOP_N
    assert inst.minimo_categoria == (5, 5, 0, 0, 0) and inst.maximo_categoria == (20,) * 5
    assert inst.minimo_cauda == 15
    sem_categoria = sum(k == SEM_CATEGORIA for k in inst.categoria) / 2000
    assert 0.07 < sem_categoria < 0.13  # 1 em cada 10, sorteado
    assert inst.custo == tuple(c for c, _, _ in CATALOGO)


@pytest.mark.parametrize("parceiros, acoes", [(99, 5), (10_001, 5), (500, 0), (500, 11)])
def test_fora_da_faixa_e_recusado(parceiros, acoes):
    with pytest.raises(ValueError):
        sintetico(parceiros, acoes)


def test_o_catalogo_e_o_do_gerador():
    """O benchmark e o gerador de dados sintéticos falam das mesmas ações."""
    if not GERADOR.is_file():
        pytest.skip("scripts/ não está nesta cópia (a imagem do núcleo só leva nucleo/).")
    arvore = ast.parse(GERADOR.read_text(encoding="utf-8"))
    no = next(
        n
        for n in arvore.body
        if isinstance(n, ast.Assign) and any(getattr(a, "id", None) == "ACOES" for a in n.targets)
    )
    do_gerador = tuple(
        (int(Decimal(custo) * 100), float(crescimento), float(retencao))
        for _nome, custo, crescimento, retencao in ast.literal_eval(no.value)
    )
    assert CATALOGO == do_gerador
