"""Dependências do FastAPI: transação, usuário da sessão e autorização por perfil.

A regra 2.5 do CLAUDE.md e o RNF14 dizem a mesma coisa: **autorização é
verificada no servidor, em todos os endpoints**. Esconder botão não é controle
de acesso. Por isso a checagem de perfil mora aqui, como dependência declarada
na rota — e não espalhada em `if` dentro de cada função, onde esquecer um é
silencioso.

A cobertura sistemática disso — cada endpoint contra cada perfil — é a H17, na
Sprint 5. O que existe aqui é o mecanismo que ela vai exercitar.
"""
from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Request, status
from fastapi.routing import APIRoute
from sqlalchemy.orm import Session

from app import auditoria, sessoes
from app.auditoria import Acao
from app.config import config
from app.db import sessao as transacao
from app.modelos import Perfil, SessaoAcesso, Usuario

NAO_AUTENTICADO = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Sessão inválida ou expirada.",
)


def banco() -> Iterator[Session]:
    """Uma transação por requisição: comita no fim, reverte se algo estourar."""
    with transacao() as s:
        yield s


Banco = Annotated[Session, Depends(banco)]


def sessao_atual(
    s: Banco,
    gih_sessao: Annotated[str | None, Cookie(alias=config.sessao_cookie)] = None,
) -> SessaoAcesso:
    sessao = sessoes.validar(s, gih_sessao)
    if sessao is None:
        raise NAO_AUTENTICADO
    return sessao


SessaoAtual = Annotated[SessaoAcesso, Depends(sessao_atual)]


def usuario_atual(sessao: SessaoAtual) -> Usuario:
    """O usuário dono da sessão.

    Reconfere `ativo` a cada requisição em vez de confiar no que valia no login:
    desativar alguém precisa ter efeito agora, não na próxima vez que ele
    entrar. A H15 já derruba as sessões ao desativar — isto é a segunda barreira,
    para o caso de alguém desativar um usuário por outro caminho.
    """
    usuario = sessao.usuario
    if usuario is None or not usuario.ativo:
        raise NAO_AUTENTICADO
    return usuario


UsuarioAtual = Annotated[Usuario, Depends(usuario_atual)]


def exigir(*perfis: Perfil):
    """Dependência que restringe a rota aos perfis informados.

    Uso: `@router.get(..., dependencies=[Depends(exigir(Perfil.ADMINISTRADOR))])`

    A negação entra na auditoria: tentativa de acesso fora do perfil é
    exatamente o tipo de evento que se procura depois (RF06).
    """
    permitidos = set(perfis)

    def verificar(request: Request, usuario: UsuarioAtual) -> Usuario:
        if usuario.perfil not in permitidos:
            auditoria.registrar(
                Acao.ACESSO_NEGADO,
                usuario_id=usuario.id,
                detalhes={
                    "caminho": request.url.path,
                    "metodo": request.method,
                    "perfil": str(usuario.perfil),
                },
                origem=auditoria.origem_de(request),
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Seu perfil não permite esta operação.",
            )
        return usuario

    # Os perfis ficam presos à própria dependência, e não numa tabela à parte:
    # é daqui que `telas_de` lê, e assim o menu não tem como divergir do que a
    # rota cobra.
    verificar.perfis = frozenset(permitidos)
    return verificar


# As áreas que a interface desenha, cada uma com a rota que a sustenta. **Os
# perfis de cada área não estão aqui**: vêm do `exigir` da própria rota. Mudar a
# permissão da rota muda o menu junto — a interface não reescreve a matriz de
# autorização, só pergunta a ela (regras 2.4 e 2.5).
TELAS: dict[str, tuple[str, str]] = {
    "painel": ("GET", "/api/painel/indicadores"),
    "importar": ("POST", "/api/importacoes"),
    "historico_importacoes": ("GET", "/api/importacoes"),
    "parceiros": ("GET", "/api/parceiros"),
    "usuarios": ("GET", "/api/usuarios"),
    "configuracao": ("GET", "/api/configuracao/segmentacao"),
    "modelo": ("GET", "/api/modelo"),
    "campanha": ("GET", "/api/campanha"),
}


def perfis_da_rota(rota: APIRoute) -> frozenset[Perfil] | None:
    """Os perfis que a rota aceita; `None` quando basta estar autenticado.

    Rota com mais de um `exigir` — o do roteador e o da própria rota — só deixa
    passar quem está em todos, então os conjuntos se cruzam.
    """
    conjuntos = [
        d.dependency.perfis for d in rota.dependencies if hasattr(d.dependency, "perfis")
    ]
    return frozenset.intersection(*conjuntos) if conjuntos else None


def telas_de(rotas: Iterable, perfil: Perfil) -> list[str]:
    """As áreas que o perfil abre, na ordem de `TELAS`."""
    indice = {
        (metodo, rota.path): rota
        for rota in rotas
        if isinstance(rota, APIRoute)
        for metodo in rota.methods
    }
    telas = []
    for nome, chave in TELAS.items():
        rota = indice.get(chave)
        if rota is None:
            # Falhar alto: uma tela apontando para rota que sumiu desapareceria
            # do menu em silêncio, e ninguém saberia por quê.
            raise RuntimeError(f"A tela {nome!r} aponta para {chave}, que não existe mais.")
        perfis = perfis_da_rota(rota)
        if perfis is None or perfil in perfis:
            telas.append(nome)
    return telas
