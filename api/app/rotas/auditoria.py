"""Consulta da trilha de auditoria (RF06, RF08 · história H18)."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from app.auditoria import Acao
from app.dependencias import Banco, exigir
from app.esquemas import PaginaAuditoria, RegistroAuditoria
from app.modelos import Auditoria, Perfil

router = APIRouter(
    prefix="/api/auditoria",
    tags=["auditoria"],
    dependencies=[Depends(exigir(Perfil.ADMINISTRADOR))],
)

TAMANHO_MAXIMO = 200


@router.get("", response_model=PaginaAuditoria)
def consultar(
    s: Banco,
    autor: Annotated[int | None, Query(description="Id do usuário que executou a ação.")] = None,
    acao: Annotated[Acao | None, Query()] = None,
    de: Annotated[date | None, Query(description="Data inicial, inclusiva.")] = None,
    ate: Annotated[date | None, Query(description="Data final, inclusiva.")] = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamanho: Annotated[int, Query(ge=1, le=TAMANHO_MAXIMO)] = 50,
) -> PaginaAuditoria:
    """Trilha filtrada por autor, ação e intervalo de datas (RF08).

    Paginada porque esta tabela só cresce: a mais movimentada do sistema recebe
    uma linha por login, por importação e por decisão de mensagem. Devolver tudo
    funcionaria na demonstração e travaria depois.
    """
    condicoes = []
    if autor is not None:
        condicoes.append(Auditoria.usuario_id == autor)
    if acao is not None:
        condicoes.append(Auditoria.acao == str(acao))
    if de is not None:
        condicoes.append(Auditoria.ocorrido_em >= _inicio_do_dia(de))
    if ate is not None:
        # Fim do dia, não início: quem filtra "até 15/09" espera o dia 15
        # inteiro. Comparar com o início excluiria tudo o que aconteceu nele.
        condicoes.append(Auditoria.ocorrido_em < _inicio_do_dia(ate + timedelta(days=1)))

    total = s.scalar(select(func.count()).select_from(Auditoria).where(*condicoes)) or 0

    itens = s.scalars(
        select(Auditoria)
        .where(*condicoes)
        .order_by(Auditoria.ocorrido_em.desc(), Auditoria.id.desc())
        .offset((pagina - 1) * tamanho)
        .limit(tamanho)
    )

    return PaginaAuditoria(
        itens=[RegistroAuditoria.model_validate(i) for i in itens],
        total=total,
        pagina=pagina,
        tamanho=tamanho,
    )


def _inicio_do_dia(dia: date) -> datetime:
    """Meia-noite daquele dia **no fuso do servidor**.

    A coluna é `timestamptz`, então comparar com data ingênua levanta TypeError —
    mas o detalhe que importa é outro: usar UTC aqui faz o filtro "hoje" perder
    o que acabou de acontecer. Às 23h no horário de Brasília já é o dia seguinte
    em UTC, e o registro cai fora do intervalo que o usuário pediu. O dia é o do
    relógio de quem consulta, não o do meridiano de Greenwich.

    Isso torna o resultado dependente do `TZ` do servidor — que por isso está
    declarado no `docker-compose.yml` e no `.env.example`, e não deixado ao
    padrão do contêiner, que é UTC.
    """
    return datetime.combine(dia, time.min).astimezone()


@router.get("/acoes", response_model=list[str])
def acoes_possiveis() -> list[str]:
    """As ações que existem, para o filtro da interface.

    Vem do enum, não de um `SELECT DISTINCT`: a lista precisa ser a mesma ainda
    que uma ação nunca tenha ocorrido, senão o filtro some justo quando ninguém
    fez aquilo — que é o caso mais interessante de procurar.
    """
    return [str(a) for a in Acao]
