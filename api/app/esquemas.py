"""Contrato da API: o que entra e o que sai.

Estes modelos **são** o contrato entre `api/` e `web/` (ver CLAUDE.md, seção 5).
O frontend codifica contra eles, não contra a implementação — e é daqui que sai
a especificação publicada em `/api/docs`.

Regra que vale para o arquivo inteiro: nenhuma resposta carrega `senha_hash`,
`token_hash` ou qualquer coisa parecida. Por isso as respostas são declaradas
campo a campo, em vez de serializarem a entidade inteira.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modelos import Perfil

# Senha longa demais é trabalho de hash caro sem ganho nenhum — o Argon2 leva o
# tempo que for pedido dele. O teto é proteção de recurso (RNF15).
SENHA_MAXIMA = 200

LOGIN = Field(
    min_length=3,
    max_length=60,
    pattern=r"^[a-z0-9._-]+$",
    description="Minúsculas, dígitos, ponto, hífen e sublinhado.",
)


# --------------------------------------------------------------------- sessão
class Credenciais(BaseModel):
    login: str = Field(min_length=1, max_length=60)
    senha: str = Field(min_length=1, max_length=SENHA_MAXIMA)


class UsuarioResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    login: str
    nome: str
    perfil: Perfil
    ativo: bool
    parceiro_id: int | None
    criado_em: datetime


class SessaoResposta(BaseModel):
    usuario: UsuarioResposta
    expira_em: datetime


# -------------------------------------------------------------------- usuários
class _PerfilComParceiro(BaseModel):
    """Regra compartilhada: só o perfil Parceiro se vincula a um parceiro.

    O banco já garante isso por CHECK, mas violar lá vira erro 500 genérico.
    Validar aqui devolve a mensagem que explica o que fazer.
    """

    @model_validator(mode="after")
    def conferir_vinculo(self):
        perfil = getattr(self, "perfil", None)
        if perfil is None:
            return self

        parceiro_id = getattr(self, "parceiro_id", None)
        if perfil == Perfil.PARCEIRO and parceiro_id is None:
            raise ValueError("O perfil Parceiro exige um parceiro vinculado.")
        if perfil != Perfil.PARCEIRO and parceiro_id is not None:
            raise ValueError("Somente o perfil Parceiro pode ter parceiro vinculado.")
        return self


class NovoUsuario(_PerfilComParceiro):
    login: str = LOGIN
    nome: str = Field(min_length=2, max_length=120)
    senha: str = Field(min_length=1, max_length=SENHA_MAXIMA)
    perfil: Perfil
    parceiro_id: int | None = None

    @field_validator("nome")
    @classmethod
    def sem_espaco_sobrando(cls, v: str) -> str:
        return v.strip()


class EdicaoUsuario(_PerfilComParceiro):
    """Tudo opcional: o que não vier fica como está.

    `senha` não está aqui de propósito. Administrador trocar senha alheia é
    outra operação, com outra consequência para a auditoria, e não foi pedida em
    nenhuma história — a troca de senha é sempre a própria (RF07, H19).
    """

    nome: str | None = Field(default=None, min_length=2, max_length=120)
    perfil: Perfil | None = None
    parceiro_id: int | None = None
    ativo: bool | None = None

    @model_validator(mode="after")
    def algo_para_mudar(self):
        if all(
            getattr(self, campo) is None
            for campo in ("nome", "perfil", "parceiro_id", "ativo")
        ):
            raise ValueError("Informe ao menos um campo para alterar.")
        return self


class TrocaSenha(BaseModel):
    senha_atual: str = Field(min_length=1, max_length=SENHA_MAXIMA)
    senha_nova: str = Field(min_length=1, max_length=SENHA_MAXIMA)


# ------------------------------------------------------------------- auditoria
class RegistroAuditoria(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    usuario_id: int | None
    acao: str
    detalhes: dict | None
    origem: str | None
    ocorrido_em: datetime


class PaginaAuditoria(BaseModel):
    """Paginada porque a tabela cresce sem teto e a consulta não pode varrer tudo."""

    itens: list[RegistroAuditoria]
    total: int
    pagina: int
    tamanho: int
