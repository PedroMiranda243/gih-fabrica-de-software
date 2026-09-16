"""Testes da troca de senha — história H19, requisito RF07."""
from __future__ import annotations

import pytest

from app.config import config
from app.seguranca import SenhaFraca, validar_forca
from tests.conftest import SENHA_PADRAO

COOKIE = config.sessao_cookie
NOVA = "outra-senha-bem-comprida"


def test_troca_com_a_senha_atual_correta(cliente, criar_usuario, autenticar):
    criar_usuario(login="gestora")
    autenticar("gestora")

    r = cliente.post(
        "/api/sessao/senha", json={"senha_atual": SENHA_PADRAO, "senha_nova": NOVA}
    )

    assert r.status_code == 204
    cliente.delete("/api/sessao")
    assert cliente.post(
        "/api/sessao", json={"login": "gestora", "senha": NOVA}
    ).status_code == 201


def test_a_senha_antiga_deixa_de_valer(cliente, criar_usuario, autenticar):
    criar_usuario(login="gestora")
    autenticar("gestora")
    cliente.post("/api/sessao/senha", json={"senha_atual": SENHA_PADRAO, "senha_nova": NOVA})
    cliente.delete("/api/sessao")

    r = cliente.post("/api/sessao", json={"login": "gestora", "senha": SENHA_PADRAO})

    assert r.status_code == 401


def test_exige_a_senha_atual(cliente, criar_usuario, autenticar):
    """RF07 — sem isso, um cookie roubado vira conta roubada em um passo."""
    criar_usuario(login="gestora")
    autenticar("gestora")

    r = cliente.post(
        "/api/sessao/senha", json={"senha_atual": "chute-errado-1", "senha_nova": NOVA}
    )

    assert r.status_code == 400


def test_recusa_senha_fraca_explicando_a_regra(cliente, criar_usuario, autenticar):
    criar_usuario(login="gestora")
    autenticar("gestora")

    r = cliente.post("/api/sessao/senha", json={"senha_atual": SENHA_PADRAO, "senha_nova": "curta"})

    assert r.status_code == 400
    # A mensagem precisa dizer o que fazer. "Senha inválida" obriga o usuário a
    # adivinhar a regra tentativa por tentativa.
    assert str(config.senha_tamanho_minimo) in r.json()["detail"]


def test_troca_derruba_as_outras_sessoes_e_mantem_a_atual(cliente, criar_usuario, autenticar):
    """Se a troca foi por suspeita de acesso indevido, deixar as outras sessões
    abertas anula o motivo de ter trocado. A que trocou continua, senão o
    usuário se desconecta sozinho ao tentar se proteger."""
    criar_usuario(login="gestora")

    autenticar("gestora")
    outro_dispositivo = cliente.cookies.get(COOKIE)

    # Limpar a jar antes do segundo login é o que simula um **segundo
    # dispositivo**. Sem isso, o cookie da primeira sessão viajaria junto e ela
    # seria revogada pela renovação de identificador da H13 — o teste passaria
    # medindo a coisa errada.
    cliente.cookies.clear()
    autenticar("gestora")
    atual = cliente.cookies.get(COOKIE)
    assert atual != outro_dispositivo

    # As duas estão vivas antes da troca; esta é a linha que dá sentido ao resto.
    cliente.cookies.set(COOKIE, outro_dispositivo)
    assert cliente.get("/api/sessao/atual").status_code == 200

    cliente.cookies.set(COOKIE, atual)
    assert cliente.post(
        "/api/sessao/senha", json={"senha_atual": SENHA_PADRAO, "senha_nova": NOVA}
    ).status_code == 204

    assert cliente.get("/api/sessao/atual").status_code == 200

    cliente.cookies.set(COOKIE, outro_dispositivo)
    assert cliente.get("/api/sessao/atual").status_code == 401


def test_sem_sessao_nao_troca_senha(cliente):
    r = cliente.post("/api/sessao/senha", json={"senha_atual": "a", "senha_nova": NOVA})
    assert r.status_code == 401


# ------------------------------------------------------ regra de força, isolada
@pytest.mark.parametrize(
    "senha",
    [
        "curta",  # abaixo do mínimo
        "aaaaaaaaaaaaaaa",  # comprida, mas repetitiva
        "gestora-2026",  # contém o login
        "GESTORA-2026",  # contém o login, ignorando caixa
    ],
)
def test_senhas_recusadas(senha):
    with pytest.raises(SenhaFraca):
        validar_forca(senha, "gestora")


@pytest.mark.parametrize(
    "senha",
    [
        "cavalo-bateria-grampo",  # frase longa sem símbolo nenhum
        "P@ssw0rd-do-turno",
        "1234567890abcdef",
    ],
)
def test_senhas_aceitas(senha):
    """Comprimento vale mais que composição obrigatória.

    Exigir maiúscula, número e símbolo produz `Senha@123`, que um dicionário
    quebra antes de uma frase longa sem símbolo algum.
    """
    validar_forca(senha, "gestora")
