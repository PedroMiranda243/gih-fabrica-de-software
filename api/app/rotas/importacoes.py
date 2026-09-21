"""Importação de relatório de desempenho (UC03 · H21, H22, H23, H24, H25, H29).

Perfis Gestor e Analista, conforme a matriz de `docs/03-casos-de-uso.md`.

Texto colado e arquivo enviado passam **pelo mesmo caminho**: a rota de arquivo
decodifica os bytes e entrega texto para as mesmas funções. Duas implementações
paralelas divergiriam, e a que divergisse seria a menos usada — ou seja, a que
ninguém testaria.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app import auditoria, servico_importacao
from app.auditoria import Acao
from app.config import config
from app.dependencias import Banco, UsuarioAtual, exigir
from app.esquemas import (
    ImportacaoResposta,
    LinhaReconhecida,
    LinhaRejeitadaResposta,
    PaginaImportacoes,
    PedidoImportacao,
    PeriodoResposta,
    PreviaImportacao,
)
from app.leitor_relatorio import FormatoNaoReconhecido
from app.modelos import Importacao, Metrica, OrigemImportacao, Perfil
from app.servico_importacao import PeriodoExistente, PeriodoJaImportado

router = APIRouter(
    prefix="/api/importacoes",
    tags=["importação"],
    dependencies=[Depends(exigir(Perfil.GESTOR, Perfil.ANALISTA))],
)

TAMANHO_MAXIMO_PAGINA = 200


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


def _conflito_de_periodo(existente: PeriodoExistente) -> HTTPException:
    """RF12 — recusa a reimportação dizendo o que está em jogo (H25).

    A alternativa oferecida apaga dados. Por isso a recusa vem com o número na
    frente: quem decide precisa saber quantos registros desaparecem, quem os
    trouxe e quando — e não descobrir isso depois.

    A `ajuda` aparece na tela de importação, e por isso fala da ação, não do
    campo: `"substituir": true` é instrução para quem escreve cliente de API, e
    esse está documentado no esquema, em `/docs`.
    """
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "erro": "Este período já foi importado.",
            "ajuda": (
                "O padrão é cancelar, para não duplicar nem apagar dados sem querer. "
                "Para trocar o conteúdo do período, substitua a importação anterior: "
                "as métricas atuais deste período serão apagadas antes da gravação."
            ),
            "ja_existe": {
                "importacao": existente.importacao_id,
                "autor": existente.autor,
                "enviado_em": existente.enviado_em.isoformat(),
                "metricas_que_serao_apagadas": existente.total_metricas,
            },
        },
    )


def _texto_do_arquivo(arquivo: UploadFile) -> str:
    """Bytes enviados viram texto, ou a recusa explica por quê (H22).

    A ordem de decodificação não é arbitrária. `utf-8-sig` vem primeiro porque
    exportação de planilha no Windows costuma sair com BOM, e o BOM lido como
    caractere gruda no nome da primeira coluna — o cabeçalho deixa de casar e o
    erro aparece como "formato não reconhecido", mandando o usuário procurar
    defeito no lugar errado. Latin-1 fecha a lista porque **nunca falha**: é
    reserva, e é justamente por não falhar que o arquivo binário precisa ser
    barrado antes, senão viraria texto ilegível em vez de erro.
    """
    limite = config.tamanho_maximo_relatorio
    bruto = arquivo.file.read(limite + 1)

    if len(bruto) > limite:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "erro": f"O arquivo passa do limite de {limite:,} bytes.".replace(",", "."),
                "ajuda": "Envie o relatório de um período por vez.",
            },
        )
    if not bruto:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"erro": "O arquivo está vazio.", "ajuda": "Confira se a exportação concluiu."},
        )
    if b"\x00" in bruto:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "erro": f"{arquivo.filename!r} não é um arquivo de texto.",
                "ajuda": (
                    "O relatório precisa ser CSV ou texto. Planilha em .xlsx é arquivo compactado "
                    "e não pode ser lida assim: exporte como CSV antes de enviar."
                ),
            },
        )

    for codec in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return bruto.decode(codec)
        except UnicodeDecodeError:
            continue
    raise AssertionError("inalcançável: latin-1 decodifica qualquer byte")


def _pedido_validado(**campos) -> PedidoImportacao:
    """Monta o pedido a partir do formulário, com **as mesmas** regras do JSON.

    Reaproveitar o modelo é o que garante que a coerência do período (fim não
    anterior ao início) valha nos dois caminhos. Converter para
    `RequestValidationError` faz o erro sair traduzido pelo mesmo tratador de
    `app/erros.py`, em vez de virar 500.
    """
    try:
        return PedidoImportacao(**campos)
    except ValidationError as e:
        raise RequestValidationError(e.errors()) from e


def _montar_previa(s: Banco, pedido: PedidoImportacao) -> PreviaImportacao:
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


def _executar_importacao(
    s: Banco,
    pedido: PedidoImportacao,
    autor,
    origem: OrigemImportacao,
    request: Request,
) -> Importacao:
    try:
        importacao, analise = servico_importacao.gravar(
            s,
            pedido.texto,
            pedido.periodo_inicio,
            pedido.periodo_fim,
            autor,
            origem=origem,
            substituir=pedido.substituir,
        )
    except FormatoNaoReconhecido as e:
        raise _formato_nao_reconhecido(e) from e
    except PeriodoJaImportado as e:
        raise _conflito_de_periodo(e.existente) from e

    if not analise.leitura.reconhecidos:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Nenhuma linha válida no relatório — nada foi gravado.",
        )

    substituiu = analise.existente is not None
    detalhes = {
        "importacao": importacao.id,
        "periodo": f"{pedido.periodo_inicio} a {pedido.periodo_fim}",
        "origem": str(origem),
        "gravados": importacao.total_gravado,
        "rejeitados": importacao.total_rejeitado,
        "parceiros_criados": len(analise.parceiros_novos),
    }
    if substituiu:
        # Sem este número, a trilha registra que houve substituição mas não
        # quanto se perdeu — e é exatamente isso que se pergunta depois.
        detalhes["metricas_apagadas"] = analise.existente.total_metricas
        detalhes["importacao_substituida"] = analise.existente.importacao_id

    auditoria.registrar(
        Acao.IMPORTACAO_SUBSTITUIDA if substituiu else Acao.IMPORTACAO_REALIZADA,
        usuario_id=autor.id,
        detalhes=detalhes,
        origem=auditoria.origem_de(request),
    )
    return importacao


# --------------------------------------------------------------- texto colado
@router.post("/previa", response_model=PreviaImportacao)
def previa(pedido: PedidoImportacao, s: Banco) -> PreviaImportacao:
    """Mostra o que será gravado, sem gravar (RF11, H24)."""
    return _montar_previa(s, pedido)


@router.post("", response_model=ImportacaoResposta, status_code=status.HTTP_201_CREATED)
def importar(
    pedido: PedidoImportacao,
    request: Request,
    s: Banco,
    autor: UsuarioAtual,
) -> Importacao:
    """Grava as métricas do período (RF09, RF12, RF13, H21, H25).

    A transação é a da requisição: qualquer falha reverte tudo, e o período
    inteiro entra ou nada entra (UC03, E2). Isso vale também para a
    substituição — apagar e gravar acontecem juntos ou não acontecem.
    """
    return _executar_importacao(s, pedido, autor, OrigemImportacao.TEXTO, request)


# ------------------------------------------------------------ arquivo enviado
@router.post("/arquivo/previa", response_model=PreviaImportacao)
def previa_de_arquivo(
    s: Banco,
    arquivo: Annotated[UploadFile, File(description="CSV ou texto, com cabeçalho.")],
    periodo_inicio: Annotated[date, Form()],
    periodo_fim: Annotated[date, Form()],
) -> PreviaImportacao:
    """Prévia do arquivo, antes de gravar (RF11, H22, H24)."""
    return _montar_previa(
        s,
        _pedido_validado(
            periodo_inicio=periodo_inicio,
            periodo_fim=periodo_fim,
            texto=_texto_do_arquivo(arquivo),
        ),
    )


@router.post("/arquivo", response_model=ImportacaoResposta, status_code=status.HTTP_201_CREATED)
def importar_arquivo(
    request: Request,
    s: Banco,
    autor: UsuarioAtual,
    arquivo: Annotated[UploadFile, File(description="CSV ou texto, com cabeçalho.")],
    periodo_inicio: Annotated[date, Form()],
    periodo_fim: Annotated[date, Form()],
    substituir: Annotated[bool, Form()] = False,
) -> Importacao:
    """Importa a partir de arquivo (RF09, H22).

    O período continua obrigatório, e pelo mesmo motivo de sempre: o relatório
    não traz data, e importar sem ela corrompe a linha do tempo em silêncio
    (RN03). Vir num arquivo não muda isso.
    """
    return _executar_importacao(
        s,
        _pedido_validado(
            periodo_inicio=periodo_inicio,
            periodo_fim=periodo_fim,
            texto=_texto_do_arquivo(arquivo),
            substituir=substituir,
        ),
        autor,
        OrigemImportacao.CSV,
        request,
    )


# ------------------------------------------------------------------ histórico
@router.get("", response_model=PaginaImportacoes)
def historico(
    s: Banco,
    autor: Annotated[int | None, Query(description="Id de quem importou.")] = None,
    de: Annotated[date | None, Query(description="Enviadas a partir deste dia.")] = None,
    ate: Annotated[date | None, Query(description="Enviadas até este dia, inclusive.")] = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamanho: Annotated[int, Query(ge=1, le=TAMANHO_MAXIMO_PAGINA)] = 50,
) -> PaginaImportacoes:
    """Histórico das importações, da mais recente para a mais antiga (RF13, H29).

    `metricas_vigentes` é contado no banco, e não lido de `total_gravado`. Os
    dois divergem de propósito depois de uma substituição: o total gravado
    continua verdadeiro sobre o que aquela importação fez, enquanto o vigente
    responde o que restou dela. Zero vigente é o rastro de um período trocado.
    """
    condicoes = []
    if autor is not None:
        condicoes.append(Importacao.usuario_id == autor)
    if de is not None:
        condicoes.append(Importacao.enviado_em >= _inicio_do_dia(de))
    if ate is not None:
        # Fim do dia, não início — mesmo raciocínio da auditoria: quem filtra
        # "até 15/09" espera o dia 15 inteiro.
        condicoes.append(Importacao.enviado_em < _inicio_do_dia(ate + timedelta(days=1)))

    total = s.scalar(select(func.count()).select_from(Importacao).where(*condicoes)) or 0

    # A contagem entra por junção agregada, não por consulta dentro do laço: uma
    # por linha é o N+1 que funciona na demonstração e morre com a base cheia.
    vigentes = (
        select(Metrica.importacao_id.label("importacao_id"), func.count().label("quantas"))
        .group_by(Metrica.importacao_id)
        .subquery()
    )

    linhas = s.execute(
        select(Importacao, func.coalesce(vigentes.c.quantas, 0))
        .outerjoin(vigentes, vigentes.c.importacao_id == Importacao.id)
        .options(selectinload(Importacao.periodo), selectinload(Importacao.autor))
        .where(*condicoes)
        .order_by(Importacao.enviado_em.desc(), Importacao.id.desc())
        .offset((pagina - 1) * tamanho)
        .limit(tamanho)
    ).all()

    return PaginaImportacoes(
        itens=[
            ImportacaoResposta.model_validate(i).model_copy(update={"metricas_vigentes": quantas})
            for i, quantas in linhas
        ],
        total=total,
        pagina=pagina,
        tamanho=tamanho,
    )


def _inicio_do_dia(dia: date) -> datetime:
    """Meia-noite daquele dia no fuso do servidor.

    Mesma razão descrita em `rotas/auditoria.py`: comparar em UTC faz o filtro
    "hoje" perder o que acabou de acontecer, porque às 23h em Brasília já é o
    dia seguinte em Greenwich.
    """
    return datetime.combine(dia, time.min).astimezone()
