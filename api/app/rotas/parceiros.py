"""Gestão de parceiros (RF14 · história H26 · caso de uso UC04).

O parceiro é a entidade central do produto: tudo o mais — métrica, segmento,
previsão, plano de campanha e mensagem — pendura nele.

Perfis Gestor e Analista, conforme a matriz de `docs/03-casos-de-uso.md`. A
restrição está declarada na rota, não como `if` no corpo da função, onde
esquecer um é silencioso (regra 2.5).
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app import auditoria
from app.auditoria import Acao
from app.dependencias import Banco, UsuarioAtual, exigir
from app.esquemas import EdicaoParceiro, NovoParceiro, ParceiroResposta, VinculoParceiro
from app.modelos import (
    HistoricoSegmento,
    ItemPlano,
    Mensagem,
    Metrica,
    OrigemCategoria,
    Parceiro,
    Perfil,
    Previsao,
    StatusComercial,
    Usuario,
)

router = APIRouter(
    prefix="/api/parceiros",
    tags=["parceiros"],
    dependencies=[Depends(exigir(Perfil.GESTOR, Perfil.ANALISTA))],
)


@router.get("", response_model=list[ParceiroResposta])
def listar(
    s: Banco,
    busca: Annotated[
        str | None, Query(description="Trecho do nome, sem diferenciar maiúsculas.")
    ] = None,
    categoria_id: Annotated[int | None, Query()] = None,
    status_comercial: Annotated[StatusComercial | None, Query(alias="status")] = None,
    ativo: Annotated[bool | None, Query(description="Filtra por situação.")] = None,
    sem_categoria: Annotated[
        bool | None, Query(description="Só os pendentes de classificação.")
    ] = None,
) -> list[Parceiro]:
    """Lista com busca por nome e filtros (RF14, RF24).

    `selectinload` na categoria não é detalhe: sem ele, montar a resposta faria
    uma consulta por linha para buscar o nome da categoria — o N+1 que funciona
    com 100 parceiros e morre com 10.000, que é a carga do RNF04.
    """
    consulta = (
        select(Parceiro).options(selectinload(Parceiro.categoria)).order_by(Parceiro.nome)
    )

    if busca:
        consulta = consulta.where(Parceiro.nome.ilike(f"%{busca}%"))
    if categoria_id is not None:
        consulta = consulta.where(Parceiro.categoria_id == categoria_id)
    if status_comercial is not None:
        consulta = consulta.where(Parceiro.status == status_comercial)
    if ativo is not None:
        consulta = consulta.where(Parceiro.ativo.is_(ativo))
    if sem_categoria:
        # Parceiro criado pela importação entra sem categoria (UC04, A1); este
        # filtro é o que permite encontrá-los para classificar.
        consulta = consulta.where(Parceiro.categoria_id.is_(None))

    return list(s.scalars(consulta))


@router.get("/{parceiro_id}", response_model=ParceiroResposta)
def obter(parceiro_id: int, s: Banco) -> Parceiro:
    return _buscar(s, parceiro_id)


@router.post("", response_model=ParceiroResposta, status_code=status.HTTP_201_CREATED)
def criar(
    dados: NovoParceiro,
    request: Request,
    s: Banco,
    autor: UsuarioAtual,
) -> Parceiro:
    parceiro = Parceiro(
        nome=dados.nome,
        categoria_id=dados.categoria_id,
        # Categoria escolhida por uma pessoa é categoria confirmada (RN05). O
        # cliente não informa a origem — ver o docstring de `NovoParceiro`.
        origem_categoria=OrigemCategoria.MANUAL if dados.categoria_id else None,
        status=dados.status,
        contato=dados.contato,
        ativo=True,
    )
    s.add(parceiro)

    try:
        s.flush()
    except IntegrityError as e:
        # O nome é único no banco. Conferir antes com um SELECT deixaria uma
        # janela entre a conferência e a gravação — deixar o banco recusar é o
        # único jeito sem corrida (UC04, E1).
        s.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Já existe um parceiro com o nome {dados.nome!r}.",
        ) from e

    auditoria.registrar(
        Acao.PARCEIRO_CRIADO,
        usuario_id=autor.id,
        detalhes={"alvo": parceiro.id, "nome": parceiro.nome},
        origem=auditoria.origem_de(request),
    )
    return parceiro


@router.patch("/{parceiro_id}", response_model=ParceiroResposta)
def editar(
    parceiro_id: int,
    dados: EdicaoParceiro,
    request: Request,
    s: Banco,
    autor: UsuarioAtual,
) -> Parceiro:
    """Altera nome, categoria, status comercial, contato e situação (RF14)."""
    parceiro = _buscar(s, parceiro_id)
    origem = auditoria.origem_de(request)
    informados = dados.campos_informados
    anterior = {
        "nome": parceiro.nome,
        "categoria_id": parceiro.categoria_id,
        "status": str(parceiro.status),
        "contato": parceiro.contato,
        "ativo": parceiro.ativo,
    }

    if dados.nome is not None:
        parceiro.nome = dados.nome
    if dados.status is not None:
        parceiro.status = dados.status
    if "contato" in informados:
        parceiro.contato = dados.contato
    if dados.ativo is not None:
        parceiro.ativo = dados.ativo

    # `categoria_id` é o único campo em que o nulo tem significado próprio:
    # ausente quer dizer "não mexa", nulo quer dizer "desclassifique".
    if "categoria_id" in informados:
        parceiro.categoria_id = dados.categoria_id
        parceiro.origem_categoria = (
            OrigemCategoria.MANUAL if dados.categoria_id is not None else None
        )

    try:
        s.flush()
    except IntegrityError as e:
        s.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um parceiro com este nome.",
        ) from e

    _auditar_edicao(parceiro, anterior, autor_id=autor.id, origem=origem)
    return parceiro


@router.delete("/{parceiro_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(
    parceiro_id: int,
    request: Request,
    s: Banco,
    autor: UsuarioAtual,
) -> Response:
    """Exclui o parceiro — **quando ele não tem histórico**.

    Apagar um parceiro que já tem faturamento importado falsearia as séries dos
    períodos fechados: o total da rede deixaria de bater com a soma das partes,
    e ninguém perceberia, porque a tela continuaria parecendo correta.

    Por isso a exclusão é condicional. Com vínculos, a resposta recusa dizendo
    **quantos registros de cada tipo** impedem, e aponta a desativação — que
    resolve o problema real, que é tirar o parceiro de circulação, sem destruir
    o histórico (UC04, A4).
    """
    parceiro = _buscar(s, parceiro_id)
    vinculos = _contar_vinculos(s, parceiro_id)

    if vinculos.total:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "erro": f"O parceiro {parceiro.nome!r} tem histórico e não pode ser excluído.",
                "ajuda": (
                    "Excluir apagaria registros que outros períodos já contabilizam. "
                    "Para tirá-lo de circulação sem perder o histórico, desative-o: "
                    "PATCH neste mesmo endereço com {\"ativo\": false}."
                ),
                "vinculos": vinculos.model_dump(),
            },
        )

    nome = parceiro.nome
    s.delete(parceiro)
    s.flush()

    auditoria.registrar(
        Acao.PARCEIRO_EXCLUIDO,
        usuario_id=autor.id,
        detalhes={"alvo": parceiro_id, "nome": nome},
        origem=auditoria.origem_de(request),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --------------------------------------------------------------------- apoio
def _buscar(s: Session, parceiro_id: int) -> Parceiro:
    parceiro = s.get(Parceiro, parceiro_id)
    if parceiro is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Parceiro não encontrado."
        )
    return parceiro


def _contar_vinculos(s: Session, parceiro_id: int) -> VinculoParceiro:
    """Quantos registros de cada tipo dependem deste parceiro.

    Uma consulta por tipo, e não uma por registro: são seis consultas de
    contagem, todas por índice de chave estrangeira.
    """

    def quantos(modelo, coluna) -> int:
        return s.scalar(
            select(func.count()).select_from(modelo).where(coluna == parceiro_id)
        ) or 0

    return VinculoParceiro(
        metricas=quantos(Metrica, Metrica.parceiro_id),
        segmentos=quantos(HistoricoSegmento, HistoricoSegmento.parceiro_id),
        previsoes=quantos(Previsao, Previsao.parceiro_id),
        itens_de_plano=quantos(ItemPlano, ItemPlano.parceiro_id),
        mensagens=quantos(Mensagem, Mensagem.parceiro_id),
        usuarios=quantos(Usuario, Usuario.parceiro_id),
    )


def _auditar_edicao(parceiro: Parceiro, anterior: dict, *, autor_id: int, origem: str) -> None:
    """Uma ação por tipo de mudança, para o filtro da trilha ser útil.

    Registrar tudo como "parceiro editado" faria a consulta por classificação
    devolver toda correção de contato junto.
    """
    alvo = {"alvo": parceiro.id, "nome": parceiro.nome}

    if parceiro.categoria_id != anterior["categoria_id"]:
        auditoria.registrar(
            Acao.PARCEIRO_CLASSIFICADO,
            usuario_id=autor_id,
            detalhes={**alvo, "de": anterior["categoria_id"], "para": parceiro.categoria_id},
            origem=origem,
        )

    if parceiro.ativo != anterior["ativo"]:
        acao = Acao.PARCEIRO_REATIVADO if parceiro.ativo else Acao.PARCEIRO_DESATIVADO
        auditoria.registrar(acao, usuario_id=autor_id, detalhes=alvo, origem=origem)

    mudou_cadastro = (
        parceiro.nome != anterior["nome"]
        or str(parceiro.status) != anterior["status"]
        or parceiro.contato != anterior["contato"]
    )
    if mudou_cadastro:
        auditoria.registrar(
            Acao.PARCEIRO_EDITADO,
            usuario_id=autor_id,
            detalhes={
                **alvo,
                "nome_de": anterior["nome"],
                "status_de": anterior["status"],
                "status_para": str(parceiro.status),
            },
            origem=origem,
        )
