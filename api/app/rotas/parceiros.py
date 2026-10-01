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
from fastapi.exceptions import RequestValidationError
from fastapi.responses import StreamingResponse
from sqlalchemy import func, literal, nullslast, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import (
    auditoria,
    formato,
    planilha,
    servico_auditoria,
    servico_otimizacao,
    servico_previsao,
)
from app.auditoria import Acao
from app.calculos import ticket_medio, variacao_percentual
from app.dependencias import Banco, UsuarioAtual, exigir
from app.desempenho import ROTULO_SEGMENTO, com_desempenho, recorte
from app.esquemas import (
    CampanhaDoParceiro,
    DesempenhoParceiro,
    EdicaoParceiro,
    EventoDoParceiro,
    NovoParceiro,
    Ordenacao,
    OrigemDoRisco,
    PaginaParceiros,
    ParceiroComDesempenho,
    ParceiroResposta,
    PeriodoResposta,
    PlanoResumido,
    PrevisaoParceiro,
    VinculoParceiro,
)
from app.modelos import (
    Auditoria,
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
from app.texto import para_busca

router = APIRouter(
    prefix="/api/parceiros",
    tags=["parceiros"],
    dependencies=[Depends(exigir(Perfil.GESTOR, Perfil.ANALISTA))],
)

# O mesmo teto do ranking: página maior que isto é download disfarçado de
# consulta, e para isso existe a exportação.
TAMANHO_MAXIMO_PAGINA = 200

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
    "Risco de queda",
)


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
            Parceiro.nome_normalizado.like(f"%{para_busca(busca)}%", escape="\\")
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


def _com_risco(s: Session, consulta, colunas):
    """A chance de queda da versão em uso, na mesma junção da lista (H80).

    A mesma escolha do cadastro do parceiro (`servico_previsao.previsao_do_parceiro`):
    o último treino concluído diz a versão e o período de onde ela parte. Uma
    escolha diferente aqui faria a lista e o cadastro mostrarem dois riscos para o
    mesmo parceiro.

    **Junção externa, numa consulta só.** Buscar a previsão de cada linha depois
    seria o N+1 que a paginação existe para evitar (RNF03, RNF04); e quem não tem
    previsão continua na lista, com o risco nulo — que é diferente de risco zero.
    """
    concluido = servico_previsao.ultimo_concluido(s)
    if concluido is None:
        return consulta, colunas | {"risco": literal(None)}, None

    risco = (
        select(Previsao.parceiro_id, Previsao.probabilidade_queda)
        .where(
            Previsao.periodo_base_id == concluido.periodo_base_id,
            Previsao.modelo_versao == concluido.versao_em_uso,
        )
        .subquery("risco")
    )
    consulta = consulta.outerjoin(risco, risco.c.parceiro_id == Parceiro.id)

    base = s.get(Periodo, concluido.periodo_base_id)
    recente = servico_previsao.periodo_mais_recente(s)
    origem = OrigemDoRisco(
        modelo_versao=concluido.versao_em_uso,
        periodo_base=PeriodoResposta.model_validate(base),
        desatualizada=recente is not None and recente.id != base.id,
    )
    return consulta, colunas | {"risco": risco.c.probabilidade_queda}, origem


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
    parceiro, faturamento, pedidos, anterior, segmento, risco = bruta
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
        risco_queda=risco,
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
    alvo, anterior = recorte(s)
    consulta, colunas = com_desempenho(s, alvo, anterior)
    consulta, colunas, origem = _com_risco(s, consulta, colunas)
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
            colunas["risco"],
        )
        .offset((pagina - 1) * tamanho)
        .limit(tamanho)
    ).all()

    return PaginaParceiros(
        itens=[_linha(linha) for linha in linhas],
        total=total,
        pagina=pagina,
        tamanho=tamanho,
        risco=origem,
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
    alvo, anterior = recorte(s)
    consulta, colunas = com_desempenho(s, alvo, anterior)
    consulta, colunas, _ = _com_risco(s, consulta, colunas)
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
        colunas["risco"],
    )

    nome = f"parceiros-{alvo.data_fim.isoformat()}.csv" if alvo else "parceiros.csv"
    return StreamingResponse(
        planilha.gerar(CABECALHO_CSV, consulta, _linha_csv),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )


def _linha_csv(bruta) -> tuple:
    """Uma linha do arquivo, pelos mesmos cálculos da tela (`_linha`)."""
    item = _linha(bruta)
    return (
        planilha.texto(item.nome),
        planilha.texto(item.categoria.nome if item.categoria else None),
        ROTULO_SEGMENTO.get(item.desempenho.segmento, ""),
        ROTULO_STATUS[item.status],
        "Ativo" if item.ativo else "Inativo",
        planilha.texto(item.contato),
        planilha.numero(item.desempenho.faturamento),
        "" if item.desempenho.pedidos is None else item.desempenho.pedidos,
        planilha.numero(item.desempenho.ticket_medio),
        planilha.numero(item.desempenho.variacao_percentual),
        # O mesmo texto da tela — "24%", "menos de 1%" —, e não a fração crua: o
        # usuário exporta o que está vendo, e a estimativa não finge certeza no
        # arquivo que ela não finge na tela.
        "" if item.risco_queda is None else formato.probabilidade(item.risco_queda),
    )


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
    alvo, anterior = recorte(s)
    consulta, colunas = com_desempenho(s, alvo, anterior)
    consulta, colunas, _ = _com_risco(s, consulta, colunas)
    linha = s.execute(
        consulta.where(Parceiro.id == parceiro_id).add_columns(
            colunas["faturamento"],
            colunas["pedidos"],
            colunas["anterior"],
            colunas["segmento"],
            colunas["risco"],
        )
    ).one()
    return _linha(linha)


@router.get("/{parceiro_id}/previsao", response_model=PrevisaoParceiro)
def previsao(parceiro_id: int, s: Banco) -> PrevisaoParceiro:
    """Faturamento previsto e risco do parceiro (RF28, H44) — ou o porquê de não haver.

    Rota própria, com a previsão inteira e o porquê de não haver. A lista e a
    exportação levam só o risco, e pela mesma junção da consulta delas (H80) —
    e não por esta rota, que numa lista seria uma consulta por linha.
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


@router.get("/{parceiro_id}/campanha", response_model=CampanhaDoParceiro)
def campanha(parceiro_id: int, s: Banco) -> CampanhaDoParceiro:
    """O parceiro no último plano de campanha viável (H81) — ou que ficou de fora dele.

    É o caminho do cadastro para a campanha: quem abre o parceiro vê a ação que o
    plano reserva para ele, e dali abre o plano. Rota própria, como a previsão: é
    complemento do cadastro, e a lista não precisa dela.
    """
    _buscar(s, parceiro_id)  # 404 com a mesma mensagem de sempre
    no_plano = servico_otimizacao.parceiro_no_ultimo_plano(s, parceiro_id)
    if no_plano is None:
        return CampanhaDoParceiro()
    plano = PlanoResumido(
        execucao_id=no_plano.execucao.id,
        concluida_em=no_plano.execucao.concluida_em,
        aplicacao_inicio=no_plano.plano.aplicacao_inicio,
        aplicacao_fim=no_plano.plano.aplicacao_fim,
        modelo_versao=no_plano.execucao.modelo_versao,
    )
    if no_plano.item is None:
        return CampanhaDoParceiro(plano=plano)
    return CampanhaDoParceiro(
        plano=plano,
        no_plano=True,
        acao=no_plano.acao,
        custo=no_plano.item.custo,
        uplift_esperado=no_plano.item.uplift_esperado,
    )


# Os eventos de um cadastro são poucos; o teto existe para um cadastro que
# alguém editou centenas de vezes não virar uma página sem fim.
EVENTOS_DO_HISTORICO = 50


@router.get("/{parceiro_id}/historico", response_model=list[EventoDoParceiro])
def historico(parceiro_id: int, s: Banco) -> list[EventoDoParceiro]:
    """O que mudou no cadastro do parceiro, quando e por quem (RF50, H90).

    Sai da trilha de auditoria — os eventos de cadastro com este parceiro como
    alvo —, do mais recente para o mais antigo. **Só os do próprio parceiro**: a
    trilha inteira continua sendo do Administrador (RF08), e por isso a origem e
    os parâmetros crus não vêm aqui, só a frase. E a frase é só a mudança: o
    nome do parceiro, que a trilha repete em cada linha, aqui é o título da página.
    """
    _buscar(s, parceiro_id)  # 404 com a mesma mensagem de sempre
    linhas = s.execute(
        servico_auditoria.consulta(
            [
                Auditoria.acao.in_([str(a) for a in servico_auditoria.DO_CADASTRO_DO_PARCEIRO]),
                # Como texto, que é a expressão do índice: `detalhes->>'alvo'`.
                Auditoria.detalhes["alvo"].astext == str(parceiro_id),
            ]
        ).limit(EVENTOS_DO_HISTORICO)
    )
    return [
        EventoDoParceiro(
            acao=evento.acao,
            rotulo=servico_auditoria.rotulo(evento.acao),
            resumo=servico_auditoria.mudanca_no_cadastro(evento.acao, evento.detalhes),
            autor=nome,
            ocorrido_em=evento.ocorrido_em,
        )
        for evento, nome, _login in linhas
    ]


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
    # O nome da categoria vem por `s.get`, e não por `parceiro.categoria`: ler o
    # relacionamento agora o deixaria carregado com a categoria antiga, e a
    # resposta sairia com ela depois da troca.
    categoria = s.get(Categoria, parceiro.categoria_id) if parceiro.categoria_id else None
    anterior = {
        "nome": parceiro.nome,
        "categoria_id": parceiro.categoria_id,
        "categoria": categoria.nome if categoria else None,
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

    _auditar_edicao(s, parceiro, anterior, autor_id=autor.id, origem=origem)
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


def _auditar_edicao(
    s: Session, parceiro: Parceiro, anterior: dict, *, autor_id: int, origem: str
) -> None:
    """Uma ação por tipo de mudança, para o filtro da trilha ser útil.

    Registrar tudo como "parceiro editado" faria a consulta por classificação
    devolver toda correção de contato junto.

    **A trilha diz o que mudou, e não só que mudou** (RF50). A categoria vai com
    o nome que tinha na hora — o identificador sozinho não se lê, e o nome de uma
    categoria pode ser outro amanhã. O contato vai como "mudou", sem o valor: é o
    dado de uma pessoa, e a trilha não se apaga.
    """
    alvo = {"alvo": parceiro.id, "nome": parceiro.nome}

    if parceiro.categoria_id != anterior["categoria_id"]:
        nova = s.get(Categoria, parceiro.categoria_id) if parceiro.categoria_id else None
        auditoria.registrar(
            Acao.PARCEIRO_CLASSIFICADO,
            usuario_id=autor_id,
            detalhes={
                **alvo,
                "de": anterior["categoria_id"],
                "para": parceiro.categoria_id,
                "de_nome": anterior["categoria"],
                "para_nome": nova.nome if nova else None,
            },
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
                "contato_alterado": parceiro.contato != anterior["contato"],
            },
            origem=origem,
        )
