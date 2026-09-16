"""Ciclo de vida da sessão autenticada (RF01, RF02, RNF10).

O estado fica no servidor. Isso é exigência do RF02 — "invalidando-a no
servidor" — e é o que separa esta escolha de um token autocontido: um token
assinado só deixa de valer quando expira, e encerrar sessão em máquina
compartilhada precisa ter efeito imediato.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.config import config
from app.modelos import SessaoAcesso, Usuario
from app.seguranca import gerar_token, hash_token


class Motivo:
    """Por que uma sessão deixou de valer. Aparece na investigação da H18."""

    LOGOUT = "LOGOUT"
    NOVO_LOGIN = "NOVO_LOGIN"
    SENHA_ALTERADA = "SENHA_ALTERADA"
    USUARIO_DESATIVADO = "USUARIO_DESATIVADO"
    PERFIL_ALTERADO = "PERFIL_ALTERADO"


def agora() -> datetime:
    return datetime.now(UTC)


def criar(
    s: Session,
    usuario: Usuario,
    *,
    origem: str | None = None,
    agente: str | None = None,
) -> tuple[str, SessaoAcesso]:
    """Abre uma sessão e devolve `(token em claro, registro)`.

    O token em claro só existe aqui e no cookie: o banco fica com o hash. Quem
    perder o cookie perde a sessão, e nem o administrador consegue recuperá-la —
    que é o comportamento correto.
    """
    token = gerar_token()
    sessao = SessaoAcesso(
        token_hash=hash_token(token),
        usuario_id=usuario.id,
        expira_em=agora() + timedelta(hours=config.sessao_duracao_horas),
        origem=origem,
        agente=(agente or "")[:255] or None,
    )
    s.add(sessao)
    s.flush()
    return token, sessao


def validar(s: Session, token: str | None) -> SessaoAcesso | None:
    """Sessão viva correspondente ao token, ou `None`.

    Recusa por três motivos diferentes — inexistente, revogada, expirada — e
    devolve a mesma coisa nos três. Quem está do outro lado não precisa saber
    qual foi.
    """
    if not token:
        return None

    sessao = s.scalar(
        select(SessaoAcesso).where(SessaoAcesso.token_hash == hash_token(token))
    )
    if sessao is None or sessao.revogada_em is not None:
        return None

    # O banco devolve com fuso quando a coluna é `timestamptz`; a comparação
    # precisa dos dois lados cientes do fuso, senão levanta TypeError.
    if sessao.expira_em <= agora():
        return None

    return sessao


def revogar(s: Session, sessao: SessaoAcesso, motivo: str) -> None:
    if sessao.revogada_em is None:
        sessao.revogada_em = agora()
        sessao.motivo_revogacao = motivo


def revogar_do_usuario(
    s: Session, usuario_id: int, motivo: str, *, preservar_id: int | None = None
) -> int:
    """Derruba as sessões abertas de um usuário. Devolve quantas caíram.

    `preservar_id` existe para a troca de senha: quem acabou de trocar continua
    logado, todo o resto cai (H19). Uma única consulta — a alternativa com laço
    seria o N+1 que o CLAUDE.md manda evitar.
    """
    condicoes = [
        SessaoAcesso.usuario_id == usuario_id,
        SessaoAcesso.revogada_em.is_(None),
    ]
    if preservar_id is not None:
        condicoes.append(SessaoAcesso.id != preservar_id)

    resultado = s.execute(
        update(SessaoAcesso)
        .where(*condicoes)
        .values(revogada_em=agora(), motivo_revogacao=motivo)
    )
    return resultado.rowcount or 0
