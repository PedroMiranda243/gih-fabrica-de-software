"""Consulta da trilha de auditoria (RF06, RF08, RF49 · histórias H18 e H89)."""
from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select

from app import planilha, servico_auditoria
from app.auditoria import Acao
from app.dependencias import Banco, exigir
from app.esquemas import AcaoAuditavel, PaginaAuditoria, RegistroAuditoria
from app.modelos import Auditoria, Perfil, Usuario

router = APIRouter(
    prefix="/api/auditoria",
    tags=["auditoria"],
    dependencies=[Depends(exigir(Perfil.ADMINISTRADOR))],
)

TAMANHO_MAXIMO = 200

Autor = Annotated[int | None, Query(description="Id do usuário que executou a ação.")]
De = Annotated[date | None, Query(description="Data inicial, inclusiva.")]
Ate = Annotated[date | None, Query(description="Data final, inclusiva.")]
Busca = Annotated[
    str | None,
    Query(max_length=120, description="Texto no que foi gravado ou em quem fez."),
]


def _registro(evento: Auditoria, nome: str | None, login: str | None) -> RegistroAuditoria:
    return RegistroAuditoria(
        id=evento.id,
        usuario_id=evento.usuario_id,
        autor=nome,
        autor_login=login,
        acao=evento.acao,
        rotulo=servico_auditoria.rotulo(evento.acao),
        resumo=servico_auditoria.resumo(evento.acao, evento.detalhes),
        detalhes=evento.detalhes,
        origem=evento.origem,
        ocorrido_em=evento.ocorrido_em,
    )


@router.get("", response_model=PaginaAuditoria)
def consultar(
    s: Banco,
    autor: Autor = None,
    acao: Annotated[Acao | None, Query()] = None,
    de: De = None,
    ate: Ate = None,
    busca: Busca = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamanho: Annotated[int, Query(ge=1, le=TAMANHO_MAXIMO)] = 50,
) -> PaginaAuditoria:
    """Trilha filtrada por autor, ação, intervalo de datas e texto (RF08, RF49).

    Paginada porque esta tabela só cresce: a mais movimentada do sistema recebe
    uma linha por login, por importação e por decisão de mensagem. Devolver tudo
    funcionaria na demonstração e travaria depois.

    **O autor vem na mesma consulta**, pela junção — e não por uma busca a cada
    linha. Ela é externa: a tentativa de entrada com login que não existe não tem
    autor (UC14-A1), e precisa continuar na lista.
    """
    filtros = servico_auditoria.condicoes(autor=autor, acao=acao, de=de, ate=ate, busca=busca)
    total = (
        s.scalar(
            select(func.count())
            .select_from(Auditoria)
            .outerjoin(Usuario, Usuario.id == Auditoria.usuario_id)
            .where(*filtros)
        )
        or 0
    )
    linhas = s.execute(
        servico_auditoria.consulta(filtros).offset((pagina - 1) * tamanho).limit(tamanho)
    )
    return PaginaAuditoria(
        itens=[_registro(evento, nome, login) for evento, nome, login in linhas],
        total=total,
        pagina=pagina,
        tamanho=tamanho,
    )


@router.get("/exportacao.csv", response_class=StreamingResponse)
def exportar(
    autor: Autor = None,
    acao: Annotated[Acao | None, Query()] = None,
    de: De = None,
    ate: Ate = None,
    busca: Busca = None,
) -> StreamingResponse:
    """A trilha em CSV, com **exatamente** o recorte da tela (RF49).

    Os mesmos filtros, pela mesma função da lista: exportar um recorte diferente
    do que está na tela é pior que não exportar. Sem paginação — é o arquivo
    inteiro do recorte —, e as linhas saem em lotes, sem montar a lista antes.

    O resumo e o login passam pela proteção contra fórmula: os dois trazem texto
    que alguém digitou — um nome de parceiro, um login tentado.
    """
    filtros = servico_auditoria.condicoes(autor=autor, acao=acao, de=de, ate=ate, busca=busca)

    def linha(bruta) -> list[str]:
        evento, nome, login = bruta
        return [
            evento.ocorrido_em.astimezone().strftime("%d/%m/%Y %H:%M:%S"),
            planilha.texto(nome),
            planilha.texto(login),
            servico_auditoria.rotulo(evento.acao),
            planilha.texto(servico_auditoria.resumo(evento.acao, evento.detalhes)),
            planilha.texto(evento.origem),
        ]

    nome = f"auditoria-{date.today().isoformat()}.csv"
    return StreamingResponse(
        planilha.gerar(
            ["Quando", "Autor", "Login", "Ação", "O que aconteceu", "Origem"],
            servico_auditoria.consulta(filtros),
            linha,
        ),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )


@router.get("/acoes", response_model=list[AcaoAuditavel])
def acoes_possiveis() -> list[AcaoAuditavel]:
    """As ações que existem, com o rótulo, para o filtro da interface.

    Vem do enum, não de um `SELECT DISTINCT`: a lista precisa ser a mesma ainda
    que uma ação nunca tenha ocorrido, senão o filtro some justo quando ninguém
    fez aquilo — que é o caso mais interessante de procurar.
    """
    return [AcaoAuditavel(acao=str(a), rotulo=servico_auditoria.rotulo(str(a))) for a in Acao]
