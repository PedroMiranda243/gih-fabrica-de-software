"""Importação de relatório de desempenho (UC03 · histórias H21, H23, H24).

Perfis Gestor e Analista, conforme a matriz de `docs/03-casos-de-uso.md`.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select

from app import auditoria, servico_importacao
from app.auditoria import Acao
from app.dependencias import Banco, UsuarioAtual, exigir
from app.esquemas import (
    ImportacaoResposta,
    LinhaReconhecida,
    LinhaRejeitadaResposta,
    PedidoImportacao,
    PeriodoResposta,
    PreviaImportacao,
)
from app.leitor_relatorio import FormatoNaoReconhecido
from app.modelos import Importacao, Perfil
from app.servico_importacao import PeriodoJaImportado

router = APIRouter(
    prefix="/api/importacoes",
    tags=["importação"],
    dependencies=[Depends(exigir(Perfil.GESTOR, Perfil.ANALISTA))],
)


def _formato_nao_reconhecido(e: FormatoNaoReconhecido) -> HTTPException:
    """UC03, A4 — devolve as primeiras linhas junto com a recusa.

    "Formato não reconhecido" sozinho não deixa ninguém descobrir o que veio
    errado. Mostrar o que o servidor de fato recebeu resolve o caso mais comum,
    que é ter colado a célula errada ou o texto de outra aba.
    """
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={
            "erro": str(e),
            "ajuda": (
                "O relatório precisa de uma linha de cabeçalho nomeando as colunas de parceiro, "
                "faturamento e pedidos. O separador pode ser ponto-e-vírgula, tabulação ou vírgula."
            ),
            "primeiras_linhas_recebidas": e.primeiras_linhas,
        },
    )


@router.post("/previa", response_model=PreviaImportacao)
def previa(pedido: PedidoImportacao, s: Banco) -> PreviaImportacao:
    """Mostra o que será gravado, sem gravar (RF11, H24)."""
    try:
        analise = servico_importacao.analisar(
            s, pedido.texto, pedido.periodo_inicio, pedido.periodo_fim
        )
    except FormatoNaoReconhecido as e:
        raise _formato_nao_reconhecido(e) from e

    return PreviaImportacao(
        periodo=PeriodoResposta(data_inicio=pedido.periodo_inicio, data_fim=pedido.periodo_fim),
        reconhecidos=[
            LinhaReconhecida(
                linha=x.linha, nome=x.nome, faturamento=x.faturamento, pedidos=x.pedidos
            )
            for x in analise.leitura.reconhecidos
        ],
        rejeitados=[
            LinhaRejeitadaResposta(linha=r.linha, conteudo=r.conteudo, motivo=r.motivo)
            for r in analise.leitura.rejeitados
        ],
        parceiros_novos=analise.parceiros_novos,
        total_reconhecido=len(analise.leitura.reconhecidos),
        total_rejeitado=len(analise.leitura.rejeitados),
        periodo_ja_importado=analise.periodo_ja_importado,
    )


@router.post("", response_model=ImportacaoResposta, status_code=status.HTTP_201_CREATED)
def importar(
    pedido: PedidoImportacao,
    request: Request,
    s: Banco,
    autor: UsuarioAtual,
) -> Importacao:
    """Grava as métricas do período (RF09, RF13, H21).

    A transação é a da requisição: qualquer falha reverte tudo, e o período
    inteiro entra ou nada entra (UC03, E2).
    """
    try:
        importacao, analise = servico_importacao.gravar(
            s, pedido.texto, pedido.periodo_inicio, pedido.periodo_fim, autor
        )
    except FormatoNaoReconhecido as e:
        raise _formato_nao_reconhecido(e) from e
    except PeriodoJaImportado as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Este período já foi importado. Substituir os dados existentes exige uma "
                "decisão explícita, que ainda não está disponível — por ora, cancele ou "
                "informe outro período."
            ),
        ) from e

    if not analise.leitura.reconhecidos:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Nenhuma linha válida no relatório — nada foi gravado.",
        )

    auditoria.registrar(
        Acao.IMPORTACAO_REALIZADA,
        usuario_id=autor.id,
        detalhes={
            "importacao": importacao.id,
            "periodo": f"{pedido.periodo_inicio} a {pedido.periodo_fim}",
            "gravados": importacao.total_gravado,
            "rejeitados": importacao.total_rejeitado,
            "parceiros_criados": len(analise.parceiros_novos),
        },
        origem=auditoria.origem_de(request),
    )
    return importacao


@router.get("", response_model=list[ImportacaoResposta])
def historico(s: Banco) -> list[Importacao]:
    """Histórico das importações, da mais recente para a mais antiga (RF13)."""
    return list(
        s.scalars(select(Importacao).order_by(Importacao.enviado_em.desc(), Importacao.id.desc()))
    )
