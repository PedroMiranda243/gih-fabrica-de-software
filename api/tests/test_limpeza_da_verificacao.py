"""A limpeza da verificação de ponta a ponta (`e2e/limpeza.py`).

Ela apaga direto no banco, por fora das regras da API. Por isso o que mais
precisa de teste não é o que ela apaga, e sim o que ela **não** apaga: uma
limpeza que acerta quase sempre é pior que nenhuma, porque ninguém desconfia
dela até faltar o dado de alguém.

A limpeza abre a própria conexão a partir do `DATABASE_URL`, que o `conftest`
aponta para o banco de teste. Se apontasse para outro, ela não acharia os
usuários da execução e recusaria — a mesma guarda que a protege do banco errado
na verificação de verdade.
"""
from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import func, select

from app.db import Sessao
from app.modelos import (
    Categoria,
    Importacao,
    Metrica,
    OrigemCategoria,
    Parceiro,
    Perfil,
    Periodo,
    Usuario,
)
from app.servico_importacao import gravar
from e2e.limpeza import Contagem, LimpezaRecusada, limpar_execucao

MARCA = "e2e00001"
ANALISTA_DA_EXECUCAO = f"{MARCA}.analista"
SEMANA_DA_EXECUCAO = (date(2027, 9, 20), date(2027, 9, 26))
SEMANA_REAL = (date(2026, 9, 7), date(2026, 9, 13))
CABECALHO = "Parceiro;Faturamento;Pedidos\n"


def _importar(
    login: str, linhas: str, semana: tuple[date, date], substituir: bool = False
) -> None:
    s = Sessao()
    try:
        autor = s.scalar(select(Usuario).where(Usuario.login == login))
        gravar(s, CABECALHO + linhas, *semana, autor, substituir=substituir)
        s.commit()
    finally:
        s.close()


def _gravar(*objetos) -> None:
    s = Sessao()
    try:
        s.add_all(objetos)
        s.commit()
    finally:
        s.close()


def _contar(modelo, *condicoes) -> int:
    s = Sessao()
    try:
        return s.scalar(select(func.count()).select_from(modelo).where(*condicoes)) or 0
    finally:
        s.close()


@pytest.fixture
def execucao(criar_usuario):
    """Uma execução da verificação ao lado de dado que não é dela.

    Reproduz o que a verificação de fato deixa: uma importação substituída por
    outra no mesmo período, e um parceiro cadastrado à mão com a categoria da
    execução — que precisa sair antes da categoria, por causa da chave.
    """
    criar_usuario(login=ANALISTA_DA_EXECUCAO, perfil=Perfil.ANALISTA)
    criar_usuario(login="analista.real", perfil=Perfil.ANALISTA)

    _importar("analista.real", "Loja do Centro;1000,00;10\n", SEMANA_REAL)

    _importar(
        ANALISTA_DA_EXECUCAO,
        f"Alfa {MARCA};12500,40;312\nBeta {MARCA};8940,00;201\n",
        SEMANA_DA_EXECUCAO,
    )
    _importar(ANALISTA_DA_EXECUCAO, f"Alfa {MARCA};777,00;7\n", SEMANA_DA_EXECUCAO, True)

    categoria = Categoria(nome=f"Categoria {MARCA}")
    _gravar(categoria)
    _gravar(
        Parceiro(
            nome=f"Comércio {MARCA} Ltda",
            categoria_id=categoria.id,
            origem_categoria=OrigemCategoria.MANUAL,
        )
    )


def test_remove_o_que_a_execucao_gravou(execucao):
    removidos = limpar_execucao(MARCA)

    assert removidos == Contagem(
        periodos=1, importacoes=2, metricas=1, parceiros=3, categorias=1
    )
    assert _contar(Periodo, Periodo.data_inicio == SEMANA_DA_EXECUCAO[0]) == 0
    assert _contar(Parceiro, Parceiro.nome.contains(MARCA)) == 0
    assert _contar(Categoria, Categoria.nome.contains(MARCA)) == 0


def test_o_que_nao_e_da_execucao_fica(execucao):
    limpar_execucao(MARCA)

    assert _contar(Periodo) == 1
    assert _contar(Importacao) == 1
    assert _contar(Metrica) == 1
    assert _contar(Parceiro, Parceiro.nome == "Loja do Centro") == 1


def test_o_usuario_da_execucao_fica(execucao):
    """A trilha de auditoria aponta para ele: é desativado pela API, nunca apagado."""
    limpar_execucao(MARCA)

    assert _contar(Usuario, Usuario.login == ANALISTA_DA_EXECUCAO) == 1


def test_a_marca_casa_so_como_palavra_inteira(execucao):
    """`t12345` não pode levar junto um parceiro cujo nome só contém esses caracteres."""
    _gravar(Parceiro(nome=f"Quiosque x{MARCA}"), Parceiro(nome=f"Quiosque {MARCA}9"))

    limpar_execucao(MARCA)

    assert _contar(Parceiro, Parceiro.nome.like("Quiosque %")) == 2


def test_recusa_periodo_em_que_mais_alguem_importou(execucao):
    """Métrica sai por período; num período compartilhado, sairia a de outra pessoa."""
    _importar("analista.real", "Loja do Centro;50,00;1\n", SEMANA_DA_EXECUCAO, True)

    with pytest.raises(LimpezaRecusada, match="também tem importação de fora"):
        limpar_execucao(MARCA)

    assert _contar(Periodo) == 2
    assert _contar(Parceiro, Parceiro.nome.contains(MARCA)) == 3


def test_recusa_parceiro_da_execucao_com_historico_de_fora(execucao):
    """Alguém importou um relatório real contendo o parceiro da execução."""
    _importar("analista.real", f"Alfa {MARCA};300,00;3\n", (date(2026, 9, 14), date(2026, 9, 20)))

    with pytest.raises(LimpezaRecusada, match="depende do que ela gravou"):
        limpar_execucao(MARCA)

    # A transação volta inteira: nem o período da execução, que não tinha
    # impedimento, foi removido.
    assert _contar(Periodo, Periodo.data_inicio == SEMANA_DA_EXECUCAO[0]) == 1
    assert _contar(Importacao) == 4


def test_recusa_banco_sem_os_usuarios_da_execucao():
    """É o sintoma de `DATABASE_URL` apontando para um banco que não é o da API.

    Responder "nada a remover" daria a limpeza por feita sem ter olhado o banco
    certo.
    """
    with pytest.raises(LimpezaRecusada, match="outro banco"):
        limpar_execucao(MARCA)


@pytest.mark.parametrize("marca", ["", "e2e", "e2e0001", "%", "e2e00001.*"])
def test_recusa_marca_fora_do_formato(marca):
    """Marca vazia faria o padrão de palavra inteira casar com a base toda."""
    with pytest.raises(ValueError, match="formato"):
        limpar_execucao(marca)
