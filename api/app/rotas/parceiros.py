"""Gestão de parceiros (RF14 · história H26 · caso de uso UC04).

O parceiro é a entidade central do produto: tudo o mais — métrica, segmento,
previsão, plano de campanha e mensagem — pendura nele.

Perfis Gestor e Analista, conforme a matriz de `docs/03-casos-de-uso.md`. A
restrição está declarada na rota, não como `if` no corpo da função, onde
esquecer um é silencioso (regra 2.5).
"""
from __future__ import annotations

import csv
import io
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import StreamingResponse
from sqlalchemy import func, literal, nullslast, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app import auditoria, servico_previsao
from app.auditoria import Acao
from app.calculos import ticket_medio, variacao_percentual
from app.db import Sessao
from app.dependencias import Banco, UsuarioAtual, exigir
from app.esquemas import (
    DesempenhoParceiro,
    EdicaoParceiro,
    NovoParceiro,
    Ordenacao,
    PaginaParceiros,
    ParceiroComDesempenho,
    ParceiroResposta,
    PeriodoResposta,
    PrevisaoParceiro,
    VinculoParceiro,
)
from app.modelos import (
    Categoria,
    HistoricoSegmento,
    ItemPlano,
    Mensagem,
    Metrica,
    OrigemCategoria,
    Parceiro,
    Perfil,
    Periodo,
    Previsao,
    Segmento,
    StatusComercial,
    Usuario,
)
from app.texto import normalizar

router = APIRouter(
    prefix="/api/parceiros",
    tags=["parceiros"],
    dependencies=[Depends(exigir(Perfil.GESTOR, Perfil.ANALISTA))],
)

# O mesmo teto do ranking: página maior que isto é download disfarçado de
# consulta, e para isso existe a exportação.
TAMANHO_MAXIMO_PAGINA = 200

# Ponto e vírgula, e não vírgula: é o que o Excel em português espera, e é o
# mesmo separador que a importação aceita. Vírgula obrigaria o usuário a passar
# pelo assistente de importação de texto para abrir o próprio arquivo.
SEPARADOR_CSV = ";"

# Os rótulos que vão no arquivo. **Precisam bater com `web/src/formato.js`**:
# o usuário exporta o que está vendo, e ler "EM_RISCO" numa planilha onde a tela
# dizia "Em risco" faz parecer que são duas coisas diferentes. Não dá para
# compartilhar a fonte entre Python e JavaScript; dá para deixar o aviso aqui.
ROTULO_SEGMENTO = {
    Segmento.TOP: "Top 15",
    Segmento.EM_ASCENSAO: "Em ascensão",
    Segmento.EM_RISCO: "Em risco",
    Segmento.RECEM_CHEGADO: "Recém-chegado",
    Segmento.PROSPECCAO: "Prospecção",
    Segmento.ESTAVEL: "Estável",
}

ROTULO_STATUS = {
    StatusComercial.ATIVO: "Ativo",
    StatusComercial.PROSPECCAO: "Prospecção",
    StatusComercial.INATIVO: "Inativo",
}

CABECALHO_CSV = (
    "Parceiro",
    "Categoria",
    "Segmento",
    "Status",
    "Situacao",
    "Contato",
    "Faturamento",
    "Pedidos",
    "Ticket medio",
    "Variacao %",
)


def _para_busca(termo: str) -> str:
    """Termo digitado vira padrão de comparação seguro (RF24).

    Duas coisas acontecem aqui, e as duas importam:

    **Normaliza pela mesma regra da coluna.** `nome_normalizado` é gravado por
    `app.texto.normalizar`; comparar contra um termo cru não encontraria nada
    com acento, que é justamente o defeito que esta história corrige.

    **Escapa os curingas do LIKE.** Sem isso, quem digitasse `%` faria uma busca
    que casa com tudo, e `_` casaria com qualquer caractere — o usuário não pede
    curinga, ele digita um nome. A barra invertida é escapada primeiro, senão
    escaparia os escapes acrescentados depois.
    """
    normalizado = normalizar(termo)
    for caractere in ("\\", "%", "_"):
        normalizado = normalizado.replace(caractere, f"\\{caractere}")
    return normalizado


def _recorte(s: Session) -> tuple[Periodo | None, Periodo | None]:
    """O período mais recente e o anterior a ele.

    O desempenho que a lista mostra é sempre o do período mais recente: é a
    pergunta que o analista traz para esta tela — "quem está como, agora".
    Percorrer o histórico é trabalho do painel, que tem a série.
    """
    alvo = s.scalar(select(Periodo).order_by(Periodo.data_inicio.desc(), Periodo.id.desc()))
    if alvo is None:
        return None, None
    anterior = s.scalar(
        select(Periodo)
        .where(Periodo.data_inicio < alvo.data_inicio)
        .order_by(Periodo.data_inicio.desc(), Periodo.id.desc())
    )
    return alvo, anterior


def _com_desempenho(s: Session, alvo: Periodo | None, anterior: Periodo | None):
    """A consulta da lista, com desempenho e segmento — tudo numa junção só.

    **Junções externas nas três.** Parceiro sem métrica no período continua
    sendo parceiro: sumir com ele faria a tela esconder justamente quem ainda
    não vendeu, que é quem mais precisa aparecer.

    Devolve também as colunas pelas quais dá para ordenar. O ticket e a variação
    entram como expressão SQL **para ordenar**, com `NULLIF` nos dois divisores:
    pedidos zerados e base anterior zerada tornam a divisão indefinida, e
    `NULLIF` devolve nulo em vez de estourar. Os valores que a resposta
    **mostra** vêm de `app.calculos`, a mesma fonte do painel.
    """
    nulo = literal(None)
    consulta = select(Parceiro).options(selectinload(Parceiro.categoria))
    colunas = {
        "faturamento": nulo,
        "pedidos": nulo,
        "anterior": nulo,
        "ticket_medio": nulo,
        "variacao": nulo,
        "segmento": nulo,
    }

    if alvo is None:
        return consulta, colunas

    atual = (
        select(Metrica.parceiro_id, Metrica.faturamento, Metrica.pedidos)
        .where(Metrica.periodo_id == alvo.id)
        .subquery("atual")
    )
    segmentado = (
        select(HistoricoSegmento.parceiro_id, HistoricoSegmento.segmento)
        .where(HistoricoSegmento.periodo_id == alvo.id)
        .subquery("segmentado")
    )
    consulta = consulta.outerjoin(atual, atual.c.parceiro_id == Parceiro.id).outerjoin(
        segmentado, segmentado.c.parceiro_id == Parceiro.id
    )
    colunas |= {
        "faturamento": atual.c.faturamento,
        "pedidos": atual.c.pedidos,
        "ticket_medio": atual.c.faturamento / func.nullif(atual.c.pedidos, 0),
        "segmento": segmentado.c.segmento,
    }

    if anterior is not None:
        passado = (
            select(Metrica.parceiro_id, Metrica.faturamento.label("antes"))
            .where(Metrica.periodo_id == anterior.id)
            .subquery("passado")
        )
        consulta = consulta.outerjoin(passado, passado.c.parceiro_id == Parceiro.id)
        colunas |= {
            "anterior": passado.c.antes,
            "variacao": (atual.c.faturamento - passado.c.antes)
            / func.nullif(passado.c.antes, 0),
        }

    return consulta, colunas


def _filtrar(
    consulta,
    colunas,
    *,
    busca,
    categoria_id,
    status_comercial,
    ativo,
    sem_categoria,
    segmento,
):
    """Os filtros, num lugar só — a lista e a exportação usam os mesmos.

    Duplicá-los faria o CSV divergir da tela no primeiro filtro novo, e exportar
    um recorte diferente do que está na frente do usuário é pior que não
    exportar (RF25).
    """
    if busca:
        consulta = consulta.where(
            Parceiro.nome_normalizado.like(f"%{_para_busca(busca)}%", escape="\\")
        )
    if categoria_id is not None:
        consulta = consulta.where(Parceiro.categoria_id == categoria_id)
    if status_comercial is not None:
        consulta = consulta.where(Parceiro.status == status_comercial)
    if ativo is not None:
        consulta = consulta.where(Parceiro.ativo.is_(ativo))
    if sem_categoria:
        # Pendente é quem não tem categoria **confirmada** (RN05): em branco, ou
        # só sugerida pelo nome (H27). Sem o segundo caso, o parceiro importado
        # com categoria inferida sairia da fila de quem precisa classificar
        # justamente por ter recebido um palpite.
        consulta = consulta.where(
            or_(
                Parceiro.categoria_id.is_(None),
                Parceiro.origem_categoria != OrigemCategoria.MANUAL,
            )
        )
    if segmento is not None:
        consulta = consulta.where(colunas["segmento"] == segmento)
    return consulta


def _ordenar(consulta, colunas, ordenar_por: str, descendente: bool):
    """Aplica a ordem pedida, por **lista fechada** de colunas.

    Interpolar o nome que chegar na URL dentro de `ORDER BY` é injeção, e o
    SQLAlchemy não protege o que já foi concatenado antes de chegar nele.
    """
    chave = Parceiro.nome if ordenar_por == "nome" else colunas[ordenar_por]
    ordem = chave.desc() if descendente else chave.asc()
    # `NULLS LAST` nos dois sentidos: quem não teve métrica no período não é o
    # melhor nem o pior, e mantê-lo no topo ao ordenar por faturamento
    # decrescente empurraria para fora da primeira página justamente quem a
    # ordenação existe para encontrar.
    desempate = Parceiro.id.asc() if ordenar_por == "nome" else Parceiro.nome.asc()
    return consulta.order_by(nullslast(ordem), desempate)


def _linha(bruta) -> ParceiroComDesempenho:
    """Monta um item da lista, derivando ticket e variação em `app.calculos`.

    Os valores que **aparecem** vêm de lá, e não das expressões que ordenaram: o
    arredondamento do painel e o desta tela precisam ser o mesmo, senão o
    sistema mostra R$ 48,23 numa tela e R$ 48,24 na outra para o mesmo parceiro.
    """
    parceiro, faturamento, pedidos, anterior, segmento = bruta
    return ParceiroComDesempenho(
        # O cadastro sai do ORM pelo esquema que já existia; o desempenho vem
        # das colunas da junção. Validar o parceiro sozinho e atribuir o
        # desempenho depois não funciona: o campo é obrigatório, e o Pydantic
        # recusa o objeto do ORM antes de chegar na atribuição.
        **ParceiroResposta.model_validate(parceiro).model_dump(),
        desempenho=DesempenhoParceiro(
            segmento=segmento,
            faturamento=faturamento,
            pedidos=pedidos,
            ticket_medio=ticket_medio(faturamento, pedidos),
            variacao_percentual=variacao_percentual(faturamento, anterior),
        ),
    )


@router.get("", response_model=PaginaParceiros)
def listar(
    s: Banco,
    busca: Annotated[
        str | None,
        Query(description="Trecho do nome. Ignora maiúsculas e acentuação."),
    ] = None,
    categoria_id: Annotated[int | None, Query()] = None,
    status_comercial: Annotated[StatusComercial | None, Query(alias="status")] = None,
    ativo: Annotated[bool | None, Query(description="Filtra por situação.")] = None,
    sem_categoria: Annotated[
        bool | None,
        Query(description="Só os pendentes: sem categoria confirmada — em branco ou só sugerida."),
    ] = None,
    segmento: Annotated[
        Segmento | None, Query(description="Segmento no período mais recente.")
    ] = None,
    ordenar_por: Annotated[Ordenacao, Query()] = Ordenacao.NOME,
    descendente: Annotated[bool, Query(description="Inverte a ordem.")] = False,
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamanho: Annotated[int, Query(ge=1, le=TAMANHO_MAXIMO_PAGINA)] = 50,
) -> PaginaParceiros:
    """Lista paginada, com busca, filtros e ordenação (RF14, RF23, RF24).

    `selectinload` na categoria não é detalhe: sem ele, montar a resposta faria
    uma consulta por linha para buscar o nome da categoria — o N+1 que funciona
    com 100 parceiros e morre com 10.000, que é a carga do RNF04.

    **A paginação não é enfeite.** Antes dela, medido com o gerador: 141 ms com
    5.000 parceiros e 295 ms com 10.000, a única consulta do painel que crescia
    com o tamanho da base (ver `docs/medicoes/`).
    """
    alvo, anterior = _recorte(s)
    consulta, colunas = _com_desempenho(s, alvo, anterior)
    consulta = _filtrar(
        consulta,
        colunas,
        busca=busca,
        categoria_id=categoria_id,
        status_comercial=status_comercial,
        ativo=ativo,
        sem_categoria=sem_categoria,
        segmento=segmento,
    )

    total = s.scalar(select(func.count()).select_from(consulta.subquery())) or 0
    consulta = _ordenar(consulta, colunas, ordenar_por.value, descendente)

    linhas = s.execute(
        consulta.add_columns(
            colunas["faturamento"],
            colunas["pedidos"],
            colunas["anterior"],
            colunas["segmento"],
        )
        .offset((pagina - 1) * tamanho)
        .limit(tamanho)
    ).all()

    return PaginaParceiros(
        itens=[_linha(linha) for linha in linhas],
        total=total,
        pagina=pagina,
        tamanho=tamanho,
        periodo=PeriodoResposta.model_validate(alvo) if alvo else None,
    )


@router.get("/exportacao.csv", response_class=StreamingResponse)
def exportar(
    s: Banco,
    busca: Annotated[str | None, Query()] = None,
    categoria_id: Annotated[int | None, Query()] = None,
    status_comercial: Annotated[StatusComercial | None, Query(alias="status")] = None,
    ativo: Annotated[bool | None, Query()] = None,
    sem_categoria: Annotated[bool | None, Query()] = None,
    segmento: Annotated[Segmento | None, Query()] = None,
    ordenar_por: Annotated[Ordenacao, Query()] = Ordenacao.NOME,
    descendente: Annotated[bool, Query()] = False,
) -> StreamingResponse:
    """Exporta a visão filtrada em CSV (RF25, H38).

    **Declarada antes de `/{parceiro_id}`**, e isso não é estilo: o FastAPI casa
    as rotas na ordem em que foram registradas, e `exportacao.csv` entraria como
    id de parceiro, devolvendo 422 em vez do arquivo.

    Recebe **exatamente** os mesmos filtros da listagem, e os aplica pela mesma
    função: exportar um recorte diferente do que está na tela é pior que não
    exportar.

    Sem paginação de propósito — é o arquivo inteiro do recorte — mas também sem
    montar a lista em memória: as linhas saem em lotes, pelo `yield_per`, e o
    gerador entrega cada uma conforme ela chega do banco.
    """
    alvo, anterior = _recorte(s)
    consulta, colunas = _com_desempenho(s, alvo, anterior)
    consulta = _filtrar(
        consulta,
        colunas,
        busca=busca,
        categoria_id=categoria_id,
        status_comercial=status_comercial,
        ativo=ativo,
        sem_categoria=sem_categoria,
        segmento=segmento,
    )
    consulta = _ordenar(consulta, colunas, ordenar_por.value, descendente).add_columns(
        colunas["faturamento"],
        colunas["pedidos"],
        colunas["anterior"],
        colunas["segmento"],
    )

    nome = f"parceiros-{alvo.data_fim.isoformat()}.csv" if alvo else "parceiros.csv"
    return StreamingResponse(
        _linhas_csv(consulta),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )


def _numero(valor) -> str:
    """Número com vírgula decimal e sem separador de milhar.

    É o que a planilha em português lê como número. Com ponto decimal ela trata
    a coluna inteira como texto, e o usuário exporta para não conseguir somar.
    """
    return "" if valor is None else str(valor).replace(".", ",")


def _linhas_csv(consulta):
    """Gera o arquivo linha a linha, sem montar a lista inteira antes.

    **Abre a própria sessão**, em vez de reusar a da requisição. O corpo de uma
    resposta em fluxo é consumido **depois** que a função da rota retorna, e a
    essa altura o FastAPI já fechou as dependências: usar a sessão da requisição
    aqui pendura a resposta. Foi exatamente o que aconteceu — os testes de
    exportação travaram até o tempo limite, sem erro nenhum.

    O BOM na primeira linha é o que faz a planilha abrir o arquivo como UTF-8.
    Sem ele, "Praça" vira "PraÃ§a", e o usuário conclui que o sistema gravou o
    nome errado — não que o programa dele adivinhou a codificação.
    """
    buffer = io.StringIO()
    escritor = csv.writer(buffer, delimiter=SEPARADOR_CSV, lineterminator="\r\n")

    def despejar() -> str:
        texto = buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)
        return texto

    escritor.writerow(CABECALHO_CSV)
    yield "﻿" + despejar()

    s = Sessao()
    try:
        for bruta in s.execute(consulta.execution_options(yield_per=500)):
            item = _linha(bruta)
            escritor.writerow(
                (
                    item.nome,
                    item.categoria.nome if item.categoria else "",
                    ROTULO_SEGMENTO.get(item.desempenho.segmento, ""),
                    ROTULO_STATUS[item.status],
                    "Ativo" if item.ativo else "Inativo",
                    item.contato or "",
                    _numero(item.desempenho.faturamento),
                    "" if item.desempenho.pedidos is None else item.desempenho.pedidos,
                    _numero(item.desempenho.ticket_medio),
                    _numero(item.desempenho.variacao_percentual),
                )
            )
            yield despejar()
    finally:
        s.close()


@router.get("/{parceiro_id}", response_model=ParceiroComDesempenho)
def obter(parceiro_id: int, s: Banco) -> ParceiroComDesempenho:
    """Um parceiro, com o desempenho do período mais recente.

    O mesmo formato de um item da lista, pela mesma consulta. A tela de cadastro
    mostra o segmento e o faturamento ao lado dos dados cadastrais: é o que liga
    o registro à análise, e o que deixa o usuário ver o efeito de desativar ou
    reclassificar alguém. Montar isso numa segunda consulta, diferente da lista,
    faria as duas telas discordarem sobre o mesmo parceiro.
    """
    _buscar(s, parceiro_id)  # 404 com a mesma mensagem de sempre
    alvo, anterior = _recorte(s)
    consulta, colunas = _com_desempenho(s, alvo, anterior)
    linha = s.execute(
        consulta.where(Parceiro.id == parceiro_id).add_columns(
            colunas["faturamento"],
            colunas["pedidos"],
            colunas["anterior"],
            colunas["segmento"],
        )
    ).one()
    return _linha(linha)


@router.get("/{parceiro_id}/previsao", response_model=PrevisaoParceiro)
def previsao(parceiro_id: int, s: Banco) -> PrevisaoParceiro:
    """Faturamento previsto e risco do parceiro (RF28, H44) — ou o porquê de não haver.

    Rota própria, e não um campo a mais no parceiro: a lista e a exportação
    usam o mesmo formato do parceiro, e a previsão lá seria uma consulta por
    linha que nenhuma das duas mostra.
    """
    _buscar(s, parceiro_id)  # 404 com a mesma mensagem de sempre
    lida = servico_previsao.previsao_do_parceiro(s, parceiro_id)
    base = PeriodoResposta.model_validate(lida.periodo_base) if lida.periodo_base else None
    if lida.previsao is None:
        return PrevisaoParceiro(
            disponivel=False,
            periodo_base=base,
            modelo_versao=lida.versao,
            desatualizada=lida.desatualizada,
            motivo=lida.motivo,
            ajuda=lida.ajuda,
        )
    previsto = lida.previsao
    return PrevisaoParceiro(
        disponivel=True,
        faturamento_previsto=previsto.faturamento_previsto,
        probabilidade_queda=previsto.probabilidade_queda,
        periodo_base=base,
        modelo_versao=previsto.modelo_versao,
        origem="REFERENCIA" if servico_previsao.e_referencia(previsto.modelo_versao) else "MODELO",
        gerada_em=previsto.gerada_em,
        desatualizada=lida.desatualizada,
    )


@router.post("", response_model=ParceiroResposta, status_code=status.HTTP_201_CREATED)
def criar(
    dados: NovoParceiro,
    request: Request,
    s: Banco,
    autor: UsuarioAtual,
) -> Parceiro:
    _categoria_existe(s, dados.categoria_id)
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
        if _violou_o_nome(e):
            raise _nome_em_uso(s, dados.nome) from e
        raise

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
        _categoria_existe(s, dados.categoria_id)
        parceiro.categoria_id = dados.categoria_id
        parceiro.origem_categoria = (
            OrigemCategoria.MANUAL if dados.categoria_id is not None else None
        )

    try:
        s.flush()
    except IntegrityError as e:
        s.rollback()
        if _violou_o_nome(e):
            raise _nome_em_uso(s, dados.nome) from e
        raise

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
                # A mensagem aparece na tela, para quem usa o sistema. A versão
                # anterior dizia "PATCH neste mesmo endereço" — instrução para
                # quem escreve cliente de API. A tela oferece o botão.
                "ajuda": (
                    "Excluir apagaria registros que outros períodos já contabilizam. "
                    "Para tirá-lo de circulação sem perder o histórico, desative o parceiro."
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
# O nome da restrição de unicidade, como o Postgres a batizou na migração
# inicial. É por ele que se distingue "nome em uso" de qualquer outra violação.
RESTRICAO_DO_NOME = "parceiro_nome_key"


def _violou_o_nome(erro: IntegrityError) -> bool:
    """A violação foi a do nome único — e não outra.

    O `except` antigo tratava **qualquer** violação de integridade como nome
    duplicado. Uma categoria inexistente estoura a chave estrangeira, e a
    resposta dizia "já existe um parceiro com esse nome": o usuário iria
    corrigir o campo errado.
    """
    diagnostico = getattr(erro.orig, "diag", None)
    return getattr(diagnostico, "constraint_name", None) == RESTRICAO_DO_NOME


def _categoria_existe(s: Session, categoria_id: int | None) -> None:
    """Categoria inexistente é erro **do campo**, e sai como os outros erros de campo.

    Levantar `RequestValidationError`, em vez de montar a resposta aqui, faz a
    mensagem passar pelo mesmo tradutor de `app/erros.py` que todo 422 usa: a
    tela recebe o formato de sempre e marca o campo certo.
    """
    if categoria_id is not None and s.get(Categoria, categoria_id) is None:
        raise RequestValidationError(
            [
                {
                    "type": "value_error",
                    "loc": ("body", "categoria_id"),
                    "msg": "Value error, Categoria não encontrada. "
                    "Escolha uma da lista ou deixe o parceiro sem categoria.",
                    "input": categoria_id,
                }
            ]
        )


def _nome_em_uso(s: Session, nome: str) -> HTTPException:
    """A recusa **aponta o parceiro que já usa o nome** (UC04, E1).

    Sem isso, o usuário fica entre duas adivinhações: se o outro cadastro é o
    mesmo parceiro, ou se é outro com nome parecido. Com o existente na
    resposta, a tela oferece abri-lo.
    """
    existente = s.scalar(select(Parceiro).where(Parceiro.nome == nome))
    detalhe = {
        "erro": f"Já existe um parceiro com o nome {nome!r}.",
        "ajuda": "Corrija o nome, ou abra o cadastro existente e edite-o em vez de criar outro.",
    }
    if existente is not None:
        detalhe["existente"] = {"id": existente.id, "nome": existente.nome}
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detalhe)


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
