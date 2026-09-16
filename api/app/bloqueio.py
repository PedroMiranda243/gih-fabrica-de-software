"""Bloqueio temporário por tentativas repetidas de login (RNF11, H14).

**O bloqueio é por origem, não por login** — é o que o RNF11 diz, e é a escolha
certa: contar falhas por login deixaria qualquer um travar a conta de um colega
só errando a senha dele cinco vezes. O custo aceito é que duas pessoas atrás do
mesmo endereço compartilham o contador.

As tentativas gravam em transação própria, pelo mesmo motivo da auditoria: a
falha de login termina em 401, e um `rollback` levaria junto o registro da
tentativa — a defesa apagaria as próprias evidências e nunca chegaria a cinco.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from sqlalchemy import func, select

from app.config import config
from app.db import Sessao
from app.modelos import TentativaLogin
from app.sessoes import agora

log = logging.getLogger("gih.bloqueio")


def registrar_tentativa(login: str, origem: str, sucesso: bool) -> None:
    s = Sessao()
    try:
        s.add(TentativaLogin(login=login[:60], origem=origem[:45], sucesso=sucesso))
        s.commit()
    except Exception:
        s.rollback()
        log.exception("Falha ao registrar tentativa de login")
    finally:
        s.close()


def esta_bloqueada(origem: str) -> bool:
    """Se a origem esgotou as tentativas dentro da janela.

    Conta apenas as falhas **posteriores ao último sucesso** da mesma origem:
    quem erra quatro vezes, acerta e erra de novo recomeça do zero. Sem isso, um
    usuário desastrado ficaria bloqueado ao longo do dia por falhas que ele
    mesmo já corrigiu.
    """
    limite = agora() - timedelta(minutes=config.login_janela_minutos)

    s = Sessao()
    try:
        ultimo_sucesso = s.scalar(
            select(func.max(TentativaLogin.ocorrido_em)).where(
                TentativaLogin.origem == origem,
                TentativaLogin.sucesso.is_(True),
                TentativaLogin.ocorrido_em >= limite,
            )
        )

        condicoes = [
            TentativaLogin.origem == origem,
            TentativaLogin.sucesso.is_(False),
            TentativaLogin.ocorrido_em >= limite,
        ]
        if ultimo_sucesso is not None:
            condicoes.append(TentativaLogin.ocorrido_em > ultimo_sucesso)

        falhas = s.scalar(select(func.count()).select_from(TentativaLogin).where(*condicoes))
        return (falhas or 0) >= config.login_falhas_para_bloquear
    finally:
        s.close()
