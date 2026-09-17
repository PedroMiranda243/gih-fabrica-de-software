"""Trilha de auditoria (RF06).

**A auditoria grava em transação própria, separada da operação auditada.** Isso
não é descuido: se ela participasse da mesma transação, o `rollback` de uma
falha levaria junto o registro da falha — e são justamente as tentativas de
login recusadas e as ações negadas que alguém vai querer investigar depois.
Registrar só o que deu certo é uma trilha que mente por omissão.
"""
from __future__ import annotations

import enum
import logging

from fastapi import Request

from app.db import Sessao
from app.modelos import Auditoria

log = logging.getLogger("gih.auditoria")


class Acao(enum.StrEnum):
    """As ações sensíveis que o RF06 manda registrar.

    Vale como enum, e não como texto solto, porque o filtro da H18 lista os
    valores possíveis — e string livre vira três grafias da mesma coisa.
    """

    LOGIN_SUCESSO = "LOGIN_SUCESSO"
    LOGIN_FALHA = "LOGIN_FALHA"
    LOGIN_BLOQUEADO = "LOGIN_BLOQUEADO"
    LOGOUT = "LOGOUT"
    SENHA_ALTERADA = "SENHA_ALTERADA"
    IMPORTACAO_REALIZADA = "IMPORTACAO_REALIZADA"
    PARCEIRO_CRIADO = "PARCEIRO_CRIADO"
    PARCEIRO_EDITADO = "PARCEIRO_EDITADO"
    PARCEIRO_CLASSIFICADO = "PARCEIRO_CLASSIFICADO"
    PARCEIRO_DESATIVADO = "PARCEIRO_DESATIVADO"
    PARCEIRO_REATIVADO = "PARCEIRO_REATIVADO"
    PARCEIRO_EXCLUIDO = "PARCEIRO_EXCLUIDO"
    CATEGORIA_CRIADA = "CATEGORIA_CRIADA"
    USUARIO_CRIADO = "USUARIO_CRIADO"
    USUARIO_EDITADO = "USUARIO_EDITADO"
    USUARIO_DESATIVADO = "USUARIO_DESATIVADO"
    USUARIO_REATIVADO = "USUARIO_REATIVADO"
    PERFIL_ALTERADO = "PERFIL_ALTERADO"
    ACESSO_NEGADO = "ACESSO_NEGADO"


# Chaves que nunca podem entrar em `detalhes`. A trilha é consultável por
# administrador (RF08) e vazar senha ou identificador de sessão ali seria
# transformar o registro de segurança em brecha de segurança.
_PROIBIDAS = {"senha", "senha_atual", "senha_nova", "senha_hash", "token", "token_hash"}


def registrar(
    acao: Acao,
    *,
    usuario_id: int | None = None,
    detalhes: dict | None = None,
    origem: str | None = None,
) -> None:
    """Grava um evento e comita imediatamente.

    Nunca propaga exceção: falha ao auditar não pode derrubar a operação do
    usuário. Vai para o log, que é o lugar certo para o problema aparecer.
    """
    limpos = _sem_dados_sensiveis(detalhes) if detalhes else None

    s = Sessao()
    try:
        s.add(
            Auditoria(
                usuario_id=usuario_id,
                acao=str(acao),
                detalhes=limpos,
                origem=origem,
            )
        )
        s.commit()
    except Exception:
        s.rollback()
        log.exception("Falha ao registrar auditoria de %s", acao)
    finally:
        s.close()


def _sem_dados_sensiveis(detalhes: dict) -> dict:
    return {k: v for k, v in detalhes.items() if k.lower() not in _PROIBIDAS}


def origem_de(request: Request) -> str:
    """Endereço de origem da requisição.

    Atrás de proxy reverso isto passa a ser o endereço do proxy, e aí o
    `X-Forwarded-For` precisa entrar — **só depois** de o proxy ser confiável e
    estar configurado para reescrever o cabeçalho. Confiar nele agora deixaria
    qualquer cliente escolher a própria origem e escapar do bloqueio do RNF11.
    """
    return request.client.host if request.client else "desconhecida"
