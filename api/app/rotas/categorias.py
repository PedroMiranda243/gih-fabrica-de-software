"""Categorias de parceiro (RF14 · caso de uso UC04).

O UC04 se chama "Gerenciar parceiros **e categorias**". O cadastro de parceiro
precisa de uma lista de categorias para escolher, e é isso que estas duas rotas
entregam — o mínimo que o CRUD principal exige, sem antecipar a gestão completa,
que ninguém pediu ainda.

Mesmos perfis do cadastro de parceiros: Gestor e Analista.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app import auditoria
from app.auditoria import Acao
from app.dependencias import Banco, UsuarioAtual, exigir
from app.esquemas import CategoriaResposta, NovaCategoria, SugestaoCategoria
from app.modelos import Categoria, Perfil
from app.sugestao_categoria import categorias_ativas, sugerir

router = APIRouter(
    prefix="/api/categorias",
    tags=["parceiros"],
    dependencies=[Depends(exigir(Perfil.GESTOR, Perfil.ANALISTA))],
)


@router.get("/sugestao", response_model=SugestaoCategoria)
def sugestao(
    s: Banco,
    nome: Annotated[str, Query(min_length=1, max_length=160, description="Nome do parceiro.")],
) -> SugestaoCategoria:
    """A categoria que a regra da RN05 sugere para um nome (RF15, H27).

    Não grava nada: é o que o cadastro manual mostra enquanto a pessoa digita,
    para ela usar, trocar ou ignorar. `categoria` nula quer dizer que o nome não
    aponta uma categoria só — resultado aceitável, e não erro.
    """
    return SugestaoCategoria(categoria=sugerir(nome, categorias_ativas(s)))


@router.get("", response_model=list[CategoriaResposta])
def listar(
    s: Banco,
    ativa: Annotated[bool | None, Query(description="Filtra por situação.")] = None,
) -> list[Categoria]:
    consulta = select(Categoria).order_by(Categoria.nome)
    if ativa is not None:
        consulta = consulta.where(Categoria.ativa.is_(ativa))
    return list(s.scalars(consulta))


@router.post("", response_model=CategoriaResposta, status_code=status.HTTP_201_CREATED)
def criar(
    dados: NovaCategoria,
    request: Request,
    s: Banco,
    autor: UsuarioAtual,
) -> Categoria:
    categoria = Categoria(nome=dados.nome, ativa=True)
    s.add(categoria)

    try:
        s.flush()
    except IntegrityError as e:
        # Mesmo raciocínio do cadastro de parceiro: o nome é único no banco, e
        # deixar o banco recusar é o único jeito sem janela de corrida.
        s.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Já existe uma categoria com o nome {dados.nome!r}.",
        ) from e

    auditoria.registrar(
        Acao.CATEGORIA_CRIADA,
        usuario_id=autor.id,
        detalhes={"alvo": categoria.id, "nome": categoria.nome},
        origem=auditoria.origem_de(request),
    )
    return categoria
