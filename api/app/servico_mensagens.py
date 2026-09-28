"""A geração de mensagens — UC10, RF36 e RF37, história H60 (ADR-013).

Do público à fila de aprovação, em três passos:

1. **O público** (`resolver`): um segmento e/ou uma categoria, um plano de
   campanha ou uma seleção manual. Sai numa prévia antes de gerar qualquer
   coisa (UC10, passo 2); o público vazio é recusado (E1).
2. **Os fatos de cada parceiro** (`fatos_do_parceiro`), calculados aqui: o
   desempenho do período mais recente, pela mesma consulta da lista de
   parceiros, e a ação do plano. **O que é da rede não entra**: nem o segmento,
   nem a posição no ranking, nem a previsão (RF26). O segmento escolhe o tom;
   dizer ao parceiro que ele está "em risco" foi justamente o que a sonda da
   ADR-013 pegou o modelo fazendo.
3. **A redação** (`redigir`): o modelo de linguagem escreve com os fatos, e a
   guarda numérica confere (RN08). Número sem origem, termo interno ou o modelo
   fora do ar: o texto sai do **modelo fixo** da equipe, com os mesmos fatos, e
   a mensagem guarda por quê.

**Em segundo plano, um lote por vez**, no molde do otimizador: `iniciar` grava
o lote com o público resolvido — o que a prévia mostrou é o que se gera —, e
`executar` gera. Cada mensagem é gravada assim que fica pronta, e a tela as
mostra uma a uma (A1). O parceiro que falha fica registrado com o motivo, e o
lote segue (A2); `refazer` tenta de novo só os que faltaram.

Toda mensagem nasce pendente (RF37): aprovar é outra história (H62, RN06).
"""
from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app import auditoria, formato
from app import redator as modelo_de_linguagem
from app.auditoria import Acao
from app.calculos import ticket_medio, variacao_percentual
from app.db import sessao
from app.desempenho import ROTULO_SEGMENTO, com_desempenho, recorte
from app.esquemas import MAXIMO_POR_LOTE, ParceiroDoPublico, PublicoMensagens, TipoPublico
from app.guarda_numerica import numeros_sem_origem
from app.modelos import (
    AcaoComercial,
    Categoria,
    ExecucaoOtimizador,
    HistoricoSegmento,
    ItemPlano,
    LoteMensagens,
    Mensagem,
    OrigemCategoria,
    Parceiro,
    PlanoCampanha,
    RedatorMensagem,
    Segmento,
    SituacaoExecucao,
)
from app.redator import FalhaDoRedator, Redator
from app.texto import normalizar

log = logging.getLogger("gih")

# ------------------------------------------------------------------ os fatos
# Os nomes dos fatos são o que o modelo lê, e o que a tela mostra ao lado do texto.
PARCEIRO = "Parceiro"
PERIODO = "Período"
FATURAMENTO = "Faturamento no período"
PEDIDOS = "Pedidos no período"
TICKET = "Ticket médio"
VARIACAO = "Variação do faturamento sobre o período anterior"
ACAO = "Ação oferecida"
PERIODO_DA_ACAO = "Período da ação"

DESATIVADO = "desativado"
REMOVIDO = "Parceiro removido"
NAO_ENCONTRADO = "não encontrado"
CATEGORIA_NAO_CONFIRMADA = "categoria não confirmada"


def fatos_do_parceiro(
    nome: str,
    *,
    periodo: tuple[date, date] | None,
    faturamento: Decimal | None,
    pedidos: int | None,
    anterior: Decimal | None,
    acao: str | None,
    periodo_da_acao: tuple[date, date] | None,
) -> list[dict]:
    """Os fatos de um parceiro, já formatados como a tela os mostra.

    Só o que é do próprio parceiro — o que ele veria no portal (RF26) — e a ação
    oferecida. Uma lista, e não um dicionário: a ordem é a da leitura, e o JSONB
    do Postgres não guarda a ordem das chaves.
    """
    fatos = [{"fato": PARCEIRO, "valor": nome}]
    if periodo is not None and faturamento is not None and pedidos is not None:
        fatos += [
            {"fato": PERIODO, "valor": formato.intervalo(*periodo)},
            {"fato": FATURAMENTO, "valor": formato.reais(faturamento)},
            {"fato": PEDIDOS, "valor": formato.inteiro(pedidos)},
        ]
        ticket = ticket_medio(faturamento, pedidos)
        if ticket is not None:
            fatos.append({"fato": TICKET, "valor": formato.reais(ticket)})
        variacao = variacao_percentual(faturamento, anterior)
        if variacao is not None:
            fatos.append({"fato": VARIACAO, "valor": formato.percentual(variacao)})
    if acao is not None:
        fatos.append({"fato": ACAO, "valor": acao})
        if periodo_da_acao is not None:
            fatos.append(
                {
                    "fato": PERIODO_DA_ACAO,
                    "valor": formato.intervalo(*periodo_da_acao),
                }
            )
    return fatos


# --------------------------------------------------------------- a redação
# O tom de cada segmento (UC10, passo 4). O segmento escolhe o tom e fica fora
# do texto: a classificação é da rede, e não do parceiro (RF26).
TOM = {
    Segmento.EM_RISCO: "reaproximar o parceiro, com cuidado e sem alarme, oferecendo apoio para "
    "retomar as vendas",
    Segmento.EM_ASCENSAO: "reconhecer o bom momento do parceiro e incentivá-lo a continuar "
    "crescendo",
    Segmento.TOP: "agradecer a parceria e reforçar o relacionamento com um parceiro importante",
    Segmento.RECEM_CHEGADO: "dar as boas-vindas a um parceiro que acabou de chegar à plataforma",
    Segmento.ESTAVEL: "manter o relacionamento próximo e lembrar que a plataforma está à "
    "disposição",
    Segmento.PROSPECCAO: "convidar o comércio a começar a vender pela plataforma",
    None: "manter o relacionamento próximo e lembrar que a plataforma está à disposição",
}

# Cada frase veio de um defeito que a amostra contra o modelo de verdade mostrou:
# o texto em terceira pessoa ("o faturamento da Esquina caiu"), o juízo sem base
# ("bateu novo recorde"), o número no lugar errado ("seus pedidos somaram R$ ...")
# e o formato de carta, com "Atenciosamente," no fim.
SISTEMA = (
    "Você escreve uma mensagem de relacionamento de uma plataforma de delivery para a equipe "
    "de um comércio parceiro, em português do Brasil. Comece com 'Olá, ' seguido do nome do "
    "parceiro, e fale diretamente com a equipe, usando 'vocês'. "
    "Use somente os fatos fornecidos, cada um com o sentido que ele tem: faturamento é valor "
    "em reais, pedidos é quantidade. Todo número, valor e data do texto precisa aparecer "
    "exatamente como está nos fatos: não calcule, não arredonde, não compare e não invente "
    "números. Não afirme nada que os fatos não digam: nada de recorde, de melhor ou de pior "
    "resultado. Não mencione segmento, classificação, ranking, posição, risco nem previsão. "
    "Escreva um parágrafo só, com no máximo 3 frases curtas, e termine com uma frase que "
    "cumpra o objetivo da mensagem. Sem assunto, sem despedida e sem assinatura."
)

# O modelo fixo: o texto da equipe para cada segmento, sem número nenhum. Os
# números entram pelos fatos, e só eles — a guarda passa por construção.
CORPO = {
    Segmento.EM_RISCO: "Queremos ajudar vocês a retomar o ritmo das vendas.",
    Segmento.EM_ASCENSAO: "Parabéns pelo bom momento: queremos crescer junto com vocês.",
    Segmento.TOP: "Obrigado pela parceria, que faz diferença na plataforma.",
    Segmento.RECEM_CHEGADO: "Que bom ter vocês com a gente: contem conosco neste começo.",
    Segmento.ESTAVEL: "Seguimos à disposição para o que precisarem.",
    Segmento.PROSPECCAO: "Queremos ajudar vocês a começar a vender pela plataforma.",
    None: "Seguimos à disposição para o que precisarem.",
}

# O que é da rede e não do parceiro (RF26), e que a sonda da ADR-013 viu o modelo
# escrever. Comparado sem acento e por palavra inteira.
TERMOS_INTERNOS = ("segmento", "ranking", "em risco", "classificação", "probabilidade")

NUMEROS_SEM_ORIGEM = (
    "O texto do assistente trazia números que não vieram dos dados ({numeros}), e foi trocado "
    "pelo modelo fixo."
)
TERMO_INTERNO = (
    "O texto do assistente mencionava a classificação interna do parceiro ({termos}), e foi "
    "trocado pelo modelo fixo."
)


def modelo_fixo(segmento: Segmento | None, fatos: list[dict]) -> str:
    """O texto da equipe, com os fatos do parceiro."""
    valor = {f["fato"]: f["valor"] for f in fatos}
    frases = [f"Olá, {valor[PARCEIRO]}!"]
    if PERIODO in valor:
        pedidos = "pedido" if valor[PEDIDOS] == "1" else "pedidos"
        frases.append(
            f"No período de {valor[PERIODO]}, vocês registraram {valor[PEDIDOS]} {pedidos} e "
            f"{valor[FATURAMENTO]} em vendas."
        )
    frases.append(CORPO[segmento])
    if ACAO in valor:
        oferta = f"Preparamos uma ação para vocês: {valor[ACAO]}"
        if PERIODO_DA_ACAO in valor:
            oferta += f", de {valor[PERIODO_DA_ACAO]}"
        frases.append(oferta + ".")
    return " ".join(frases)


def _pedido(segmento: Segmento | None, fatos: list[dict]) -> str:
    linhas = [f"Objetivo da mensagem: {TOM[segmento]}.", "Fatos:"]
    linhas += [f"- {f['fato']}: {f['valor']}" for f in fatos]
    if any(f["fato"] == ACAO for f in fatos):
        linhas.append("Mencione a ação oferecida.")
    return "\n".join(linhas)


_DESPEDIDA = re.compile(
    r"\s*(atenciosamente|abraços|cordialmente|saudações)[.,!]?\s*$", re.IGNORECASE
)


def um_paragrafo(texto: str) -> str:
    """O texto do modelo num parágrafo, sem a despedida de carta.

    Mesmo pedindo um parágrafo, o modelo às vezes escreve como carta: "Olá, Casa
    Real," numa linha, "Vocês..." na seguinte, e "Atenciosamente." no fim. A linha
    que termina em vírgula continua na seguinte, em minúscula.
    """
    linhas = [linha.strip() for linha in texto.splitlines() if linha.strip()]
    partes: list[str] = []
    for linha in linhas:
        if partes and partes[-1].endswith(","):
            linha = linha[:1].lower() + linha[1:]
        partes.append(linha)
    return _DESPEDIDA.sub("", " ".join(" ".join(partes).split()))


def termos_internos(texto: str) -> list[str]:
    normalizado = normalizar(texto)
    return [
        termo
        for termo in TERMOS_INTERNOS
        if re.search(rf"\b{re.escape(normalizar(termo))}\b", normalizado)
    ]


@dataclass(frozen=True)
class Redacao:
    texto: str
    redator: RedatorMensagem
    modelo: str | None
    motivo: str | None
    # O modelo parou de responder: o resto do lote vai direto para o modelo fixo,
    # em vez de esperar o limite de tempo parceiro a parceiro.
    modelo_caiu: bool = False


def redigir(
    r: Redator | None, sem_modelo: str | None, segmento: Segmento | None, fatos: list[dict]
) -> Redacao:
    """O texto de uma mensagem: do modelo, se ele estiver no ar e passar pelas guardas."""
    fixo = modelo_fixo(segmento, fatos)
    if r is None:
        return Redacao(fixo, RedatorMensagem.MODELO_FIXO, None, sem_modelo)
    try:
        texto = um_paragrafo(r.redigir(SISTEMA, _pedido(segmento, fatos)))
    except FalhaDoRedator as falha:
        caiu = str(falha) != modelo_de_linguagem.ILEGIVEL
        return Redacao(fixo, RedatorMensagem.MODELO_FIXO, None, str(falha), modelo_caiu=caiu)
    sem_origem = numeros_sem_origem(texto, fatos)
    if sem_origem:
        motivo = NUMEROS_SEM_ORIGEM.format(numeros=", ".join(dict.fromkeys(sem_origem)))
        return Redacao(fixo, RedatorMensagem.MODELO_FIXO, None, motivo)
    internos = termos_internos(texto)
    if internos:
        motivo = TERMO_INTERNO.format(termos=", ".join(internos))
        return Redacao(fixo, RedatorMensagem.MODELO_FIXO, None, motivo)
    return Redacao(texto, RedatorMensagem.MODELO, r.modelo, None)


# ----------------------------------------------------------------- o público
class MensagensRecusadas(Exception):
    """O pedido não pode ser atendido: a mensagem é para a pessoa, com o que fazer."""

    def __init__(self, erro: str, ajuda: str, *, status: int = 409, **extra) -> None:
        super().__init__(erro)
        self.erro = erro
        self.ajuda = ajuda
        self.status = status
        self.extra = extra


@dataclass
class Previa:
    descricao: str
    parceiros: list[ParceiroDoPublico]
    # Um por parceiro da prévia: `{"parceiro_id": 3, "item_plano_id": 12}`.
    alvos: list[dict]
    excluidos: dict[str, int]


def _categoria_confirmada(p: Parceiro) -> str | None:
    """A categoria só conta confirmada (RN05)."""
    if p.categoria is not None and p.origem_categoria == OrigemCategoria.MANUAL:
        return p.categoria.nome
    return None


def _segmentos(s: Session, ids: list[int]) -> dict[int, Segmento]:
    """O segmento de cada parceiro no período mais recente."""
    alvo, _ = recorte(s)
    if alvo is None or not ids:
        return {}
    return dict(
        s.execute(
            select(HistoricoSegmento.parceiro_id, HistoricoSegmento.segmento).where(
                HistoricoSegmento.periodo_id == alvo.id, HistoricoSegmento.parceiro_id.in_(ids)
            )
        ).all()
    )


def _contar(excluidos: dict[str, int], motivo: str) -> None:
    excluidos[motivo] = excluidos.get(motivo, 0) + 1


def _por_filtro(s: Session, publico: PublicoMensagens) -> Previa:
    categoria = None
    if publico.categoria_id is not None:
        categoria = s.get(Categoria, publico.categoria_id)
        if categoria is None:
            raise MensagensRecusadas(
                "Categoria não encontrada.",
                "Escolha outra categoria da lista.",
                status=404,
                categoria_id=publico.categoria_id,
            )
    alvo, anterior = recorte(s)
    consulta, colunas = com_desempenho(s, alvo, anterior)
    consulta = consulta.add_columns(colunas["segmento"])
    if publico.segmento is not None:
        consulta = consulta.where(colunas["segmento"] == publico.segmento)
    if categoria is not None:
        consulta = consulta.where(Parceiro.categoria_id == categoria.id)
    parceiros, alvos, excluidos = [], [], {}
    for parceiro, segmento in s.execute(consulta.order_by(Parceiro.nome)):
        if not parceiro.ativo:
            _contar(excluidos, DESATIVADO)
        elif categoria is not None and parceiro.origem_categoria != OrigemCategoria.MANUAL:
            _contar(excluidos, CATEGORIA_NAO_CONFIRMADA)
        else:
            parceiros.append(
                ParceiroDoPublico(
                    id=parceiro.id,
                    nome=parceiro.nome,
                    segmento=segmento,
                    categoria=_categoria_confirmada(parceiro),
                    acao=None,
                )
            )
            alvos.append({"parceiro_id": parceiro.id, "item_plano_id": None})
    partes = []
    if publico.segmento is not None:
        partes.append(ROTULO_SEGMENTO[publico.segmento])
    if categoria is not None:
        partes.append(f"em {categoria.nome}" if partes else categoria.nome)
    return Previa(", ".join(partes), parceiros, alvos, excluidos)


def _por_plano(s: Session, publico: PublicoMensagens) -> Previa:
    execucao = s.get(ExecucaoOtimizador, publico.execucao_id)
    if execucao is None:
        raise MensagensRecusadas(
            "Otimização não encontrada.",
            "Escolha um plano do histórico de execuções.",
            status=404,
            execucao_id=publico.execucao_id,
        )
    plano = s.scalar(select(PlanoCampanha).where(PlanoCampanha.execucao_id == execucao.id))
    if execucao.situacao != SituacaoExecucao.CONCLUIDA or not execucao.viavel or plano is None:
        raise MensagensRecusadas(
            "Esta execução não tem plano.",
            "Escolha um plano calculado e viável no histórico de execuções.",
            status=422,
            execucao_id=execucao.id,
        )
    linhas = s.execute(
        select(ItemPlano.id, Parceiro, AcaoComercial.nome)
        .join(Parceiro, Parceiro.id == ItemPlano.parceiro_id)
        .join(AcaoComercial, AcaoComercial.id == ItemPlano.acao_id)
        .options(selectinload(Parceiro.categoria))
        .where(ItemPlano.plano_id == plano.id)
        .order_by(ItemPlano.uplift_esperado.desc(), Parceiro.nome)
    ).all()
    segmentos = _segmentos(s, [p.id for _, p, _ in linhas])
    parceiros, alvos, excluidos = [], [], {}
    for item_id, parceiro, acao in linhas:
        if not parceiro.ativo:
            _contar(excluidos, DESATIVADO)
            continue
        parceiros.append(
            ParceiroDoPublico(
                id=parceiro.id,
                nome=parceiro.nome,
                segmento=segmentos.get(parceiro.id),
                categoria=_categoria_confirmada(parceiro),
                acao=acao,
            )
        )
        alvos.append({"parceiro_id": parceiro.id, "item_plano_id": item_id})
    descricao = (
        f"Plano de campanha de {formato.intervalo(plano.aplicacao_inicio, plano.aplicacao_fim)}"
    )
    return Previa(descricao, parceiros, alvos, excluidos)


def _por_selecao(s: Session, publico: PublicoMensagens) -> Previa:
    ids = list(dict.fromkeys(publico.parceiros))
    encontrados = {
        p.id: p
        for p in s.scalars(
            select(Parceiro).options(selectinload(Parceiro.categoria)).where(Parceiro.id.in_(ids))
        )
    }
    segmentos = _segmentos(s, list(encontrados))
    parceiros, alvos, excluidos = [], [], {}
    for parceiro_id in ids:
        parceiro = encontrados.get(parceiro_id)
        if parceiro is None:
            _contar(excluidos, NAO_ENCONTRADO)
        elif not parceiro.ativo:
            _contar(excluidos, DESATIVADO)
        else:
            parceiros.append(
                ParceiroDoPublico(
                    id=parceiro.id,
                    nome=parceiro.nome,
                    segmento=segmentos.get(parceiro.id),
                    categoria=_categoria_confirmada(parceiro),
                    acao=None,
                )
            )
            alvos.append({"parceiro_id": parceiro.id, "item_plano_id": None})
    n = len(parceiros)
    descricao = f"Seleção de {n} parceiro" if n == 1 else f"Seleção de {n} parceiros"
    return Previa(descricao, parceiros, alvos, excluidos)


def resolver(s: Session, publico: PublicoMensagens) -> Previa:
    """Quem entra no público, e quem ficou de fora e por quê (UC10, passos 1 e 2)."""
    if publico.tipo == TipoPublico.FILTRO:
        return _por_filtro(s, publico)
    if publico.tipo == TipoPublico.PLANO:
        return _por_plano(s, publico)
    return _por_selecao(s, publico)


def impedimento(previa: Previa) -> str | None:
    """Por que este público não pode ser gerado; `None` quando pode."""
    if not previa.alvos:
        return "Nenhum parceiro ativo neste público: nada a gerar."
    if len(previa.alvos) > MAXIMO_POR_LOTE:
        return (
            f"São {formato.inteiro(len(previa.alvos))} parceiros, e um lote gera até "
            f"{formato.inteiro(MAXIMO_POR_LOTE)}: escolha um público menor, como um segmento "
            "de uma categoria."
        )
    return None


# ------------------------------------------------------------------- o lote
def em_andamento(s: Session) -> LoteMensagens | None:
    return s.scalar(
        select(LoteMensagens).where(LoteMensagens.situacao == SituacaoExecucao.EM_ANDAMENTO)
    )


def ultimo(s: Session) -> LoteMensagens | None:
    return s.scalar(
        select(LoteMensagens)
        .where(LoteMensagens.situacao != SituacaoExecucao.EM_ANDAMENTO)
        .order_by(LoteMensagens.id.desc())
    )


def _recusa_por_andamento(lote: LoteMensagens | None) -> MensagensRecusadas:
    return MensagensRecusadas(
        "Já existe uma geração de mensagens em andamento.",
        "Acompanhe a que está rodando; quando ela terminar, gere a próxima.",
        lote_id=lote.id if lote else None,
    )


def iniciar(s: Session, publico: PublicoMensagens, *, usuario_id: int | None) -> LoteMensagens:
    """Grava o lote com o público resolvido, ou recusa (UC10, E1)."""
    rodando = em_andamento(s)
    if rodando is not None:
        raise _recusa_por_andamento(rodando)
    previa = resolver(s, publico)
    motivo = impedimento(previa)
    if motivo is not None:
        raise MensagensRecusadas(
            motivo,
            "Escolha outro público.",
            status=422,
            total=len(previa.alvos),
            excluidos=previa.excluidos,
        )
    lote = LoteMensagens(
        usuario_id=usuario_id,
        publico={**publico.model_dump(mode="json"), "descricao": previa.descricao},
        alvos=previa.alvos,
        falhas=[],
    )
    try:
        with s.begin_nested():
            s.add(lote)
            s.flush()
    except IntegrityError:
        raise _recusa_por_andamento(em_andamento(s)) from None
    return lote


def geradas(s: Session, lote_id: int) -> int:
    return s.scalar(select(func.count()).select_from(Mensagem).where(Mensagem.lote_id == lote_id))


def _sem_mensagem(s: Session, lote: LoteMensagens) -> list[dict]:
    """Os alvos do lote que ainda não têm mensagem."""
    feitos = set(s.scalars(select(Mensagem.parceiro_id).where(Mensagem.lote_id == lote.id)))
    return [a for a in lote.alvos if a["parceiro_id"] not in feitos]


def _faltam(s: Session, lote: LoteMensagens) -> list[dict]:
    """Os alvos do lote sem mensagem e sem falha registrada: o que falta gerar."""
    falhos = {f["parceiro_id"] for f in lote.falhas}
    return [a for a in _sem_mensagem(s, lote) if a["parceiro_id"] not in falhos]


def refazer(s: Session, lote_id: int) -> LoteMensagens:
    """Volta a gerar as que faltaram de um lote que terminou (UC10-A2)."""
    lote = s.get(LoteMensagens, lote_id)
    if lote is None:
        raise MensagensRecusadas(
            "Geração de mensagens não encontrada.", "Volte à tela de mensagens.", status=404
        )
    if lote.situacao == SituacaoExecucao.EM_ANDAMENTO:
        raise MensagensRecusadas(
            "Esta geração ainda está em andamento.",
            "Espere ela terminar para tentar de novo as que falharem.",
            lote_id=lote.id,
        )
    rodando = em_andamento(s)
    if rodando is not None:
        raise _recusa_por_andamento(rodando)
    if not _sem_mensagem(s, lote):
        raise MensagensRecusadas(
            "Todas as mensagens deste lote já foram geradas.",
            "Não há nada a tentar de novo.",
            status=422,
            lote_id=lote.id,
        )
    lote.falhas = []
    lote.situacao = SituacaoExecucao.EM_ANDAMENTO
    lote.concluido_em = None
    lote.motivo = None
    try:
        with s.begin_nested():
            s.flush()
    except IntegrityError:
        raise _recusa_por_andamento(em_andamento(s)) from None
    return lote


@dataclass
class _Contexto:
    parceiro_id: int
    nome: str
    segmento: Segmento | None
    item_plano_id: int | None
    fatos: list[dict]


def _contextos(s: Session, alvos: list[dict]) -> list[_Contexto]:
    """Os fatos de todos os alvos, numa consulta de desempenho e numa de ações."""
    ids = [a["parceiro_id"] for a in alvos]
    periodo, anterior = recorte(s)
    consulta, colunas = com_desempenho(s, periodo, anterior)
    linhas = {
        parceiro.id: (parceiro, faturamento, pedidos, antes, segmento)
        for parceiro, faturamento, pedidos, antes, segmento in s.execute(
            consulta.where(Parceiro.id.in_(ids)).add_columns(
                colunas["faturamento"], colunas["pedidos"], colunas["anterior"], colunas["segmento"]
            )
        )
    }
    itens = [a["item_plano_id"] for a in alvos if a["item_plano_id"] is not None]
    acoes = {
        item_id: (acao, (inicio, fim))
        for item_id, acao, inicio, fim in s.execute(
            select(
                ItemPlano.id,
                AcaoComercial.nome,
                PlanoCampanha.aplicacao_inicio,
                PlanoCampanha.aplicacao_fim,
            )
            .join(AcaoComercial, AcaoComercial.id == ItemPlano.acao_id)
            .join(PlanoCampanha, PlanoCampanha.id == ItemPlano.plano_id)
            .where(ItemPlano.id.in_(itens))
        )
    }
    contextos = []
    for alvo in alvos:
        linha = linhas.get(alvo["parceiro_id"])
        if linha is None:
            # Apagado depois do pedido: vira falha com motivo, e não mensagem órfã.
            continue
        parceiro, faturamento, pedidos, antes, segmento = linha
        acao, periodo_da_acao = acoes.get(alvo["item_plano_id"], (None, None))
        contextos.append(
            _Contexto(
                parceiro_id=parceiro.id,
                nome=parceiro.nome,
                segmento=segmento,
                item_plano_id=alvo["item_plano_id"],
                fatos=fatos_do_parceiro(
                    parceiro.nome,
                    periodo=(periodo.data_inicio, periodo.data_fim) if periodo else None,
                    faturamento=faturamento,
                    pedidos=pedidos,
                    anterior=antes,
                    acao=acao,
                    periodo_da_acao=periodo_da_acao,
                ),
            )
        )
    return contextos


def _registrar_falha(lote_id: int, parceiro_id: int, nome: str, motivo: str) -> None:
    with sessao() as s:
        lote = s.get(LoteMensagens, lote_id)
        # Atribuição nova, e não `append`: o JSONB não percebe a lista mudada no lugar.
        lote.falhas = [
            *lote.falhas,
            {"parceiro_id": parceiro_id, "parceiro": nome, "motivo": motivo},
        ]


def _gravar(lote_id: int, contexto: _Contexto, redacao: Redacao) -> None:
    with sessao() as s:
        s.add(
            Mensagem(
                parceiro_id=contexto.parceiro_id,
                item_plano_id=contexto.item_plano_id,
                lote_id=lote_id,
                segmento=contexto.segmento,
                fatos=contexto.fatos,
                texto_gerado=redacao.texto,
                redator=redacao.redator,
                modelo=redacao.modelo,
                motivo_redator=redacao.motivo,
            )
        )
        if redacao.modelo is not None:
            s.get(LoteMensagens, lote_id).modelo = redacao.modelo


def executar(lote_id: int, *, origem: str | None = None, usuario_id: int | None = None) -> None:
    """Gera as mensagens do lote gravado por `iniciar`. É o que vai para segundo plano.

    **Nunca propaga exceção**, como o otimizador: em segundo plano não há quem a
    receba, e o lote ficaria em andamento para sempre, prendendo a trava.

    A conversa com o modelo fica fora de qualquer transação: uma redação pode
    levar dezenas de segundos, e a conexão com o banco não espera por ela.

    `usuario_id` é quem pediu esta rodada — o autor do lote, ou quem pediu para
    tentar de novo.
    """
    refeita = usuario_id is not None
    try:
        with sessao() as s:
            lote = s.get(LoteMensagens, lote_id)
            if usuario_id is None:
                usuario_id = lote.usuario_id
            faltam = _faltam(s, lote)
            contextos = _contextos(s, faltam)
        prontos = {c.parceiro_id for c in contextos}
        for alvo in faltam:
            if alvo["parceiro_id"] not in prontos:
                _registrar_falha(
                    lote_id, alvo["parceiro_id"], REMOVIDO, "O parceiro não existe mais na base."
                )

        r = modelo_de_linguagem.atual()
        estado = r.estado()
        usar: Redator | None = r if estado.disponivel else None
        sem_modelo = None if estado.disponivel else estado.motivo
        for contexto in contextos:
            try:
                redacao = redigir(usar, sem_modelo, contexto.segmento, contexto.fatos)
                if redacao.modelo_caiu:
                    usar, sem_modelo = None, redacao.motivo
                _gravar(lote_id, contexto, redacao)
            except Exception:
                correlacao = uuid.uuid4().hex[:12]
                log.exception(
                    "[%s] Mensagem do parceiro %s, lote %s",
                    correlacao,
                    contexto.parceiro_id,
                    lote_id,
                )
                _registrar_falha(
                    lote_id,
                    contexto.parceiro_id,
                    contexto.nome,
                    f"Erro interno ao gerar a mensagem (registro {correlacao}).",
                )

        with sessao() as s:
            lote = s.get(LoteMensagens, lote_id)
            lote.situacao = SituacaoExecucao.CONCLUIDA
            lote.concluido_em = s.scalar(select(func.clock_timestamp()))
            detalhes = {**_resumo(s, lote), "tentativa_de_novo": refeita}
        auditoria.registrar(
            Acao.MENSAGENS_GERADAS, usuario_id=usuario_id, detalhes=detalhes, origem=origem
        )
    except Exception:
        correlacao = uuid.uuid4().hex[:12]
        log.exception("[%s] Lote de mensagens %s falhou", correlacao, lote_id)
        motivo = f"A geração falhou por um erro interno (registro {correlacao})."
        _marcar_falha(lote_id, motivo)
        auditoria.registrar(
            Acao.MENSAGENS_FALHARAM,
            usuario_id=usuario_id,
            detalhes={"lote": lote_id, "motivo": motivo},
            origem=origem,
        )


def pelo_modelo(s: Session, lote_id: int) -> int:
    return s.scalar(
        select(func.count())
        .select_from(Mensagem)
        .where(Mensagem.lote_id == lote_id, Mensagem.redator == RedatorMensagem.MODELO)
    )


def _resumo(s: Session, lote: LoteMensagens) -> dict:
    return {
        "lote": lote.id,
        "publico": lote.publico.get("descricao"),
        "total": len(lote.alvos),
        "geradas": geradas(s, lote.id),
        "pelo_modelo": pelo_modelo(s, lote.id),
        "falhas": len(lote.falhas),
        "modelo": lote.modelo,
    }


def _marcar_falha(lote_id: int, motivo: str) -> None:
    try:
        with sessao() as s:
            lote = s.get(LoteMensagens, lote_id)
            if lote is not None and lote.situacao == SituacaoExecucao.EM_ANDAMENTO:
                lote.situacao = SituacaoExecucao.FALHOU
                lote.concluido_em = s.scalar(select(func.clock_timestamp()))
                lote.motivo = motivo
    except Exception:
        log.exception("Não foi possível marcar o lote de mensagens %s como falho", lote_id)


INTERROMPIDO = (
    "Interrompido: a API reiniciou durante a geração. As mensagens que faltaram podem ser "
    "geradas de novo."
)


def recuperar_interrompidos(s: Session) -> int:
    """Os lotes que ficaram em andamento — chamada na subida.

    As mensagens já gravadas ficam. As que faltaram viram falhas, com o motivo,
    e "tentar de novo" as gera (UC10-A2): nenhum parceiro some em silêncio.
    """
    interrompidos = list(
        s.scalars(
            select(LoteMensagens).where(LoteMensagens.situacao == SituacaoExecucao.EM_ANDAMENTO)
        )
    )
    agora = s.scalar(select(func.now()))
    for lote in interrompidos:
        faltam = _faltam(s, lote)
        nomes = dict(
            s.execute(
                select(Parceiro.id, Parceiro.nome).where(
                    Parceiro.id.in_([a["parceiro_id"] for a in faltam])
                )
            ).all()
        )
        lote.falhas = [
            *lote.falhas,
            *(
                {
                    "parceiro_id": a["parceiro_id"],
                    "parceiro": nomes.get(a["parceiro_id"], REMOVIDO),
                    "motivo": "Não foi gerada: a API reiniciou no meio do lote.",
                }
                for a in faltam
            ),
        ]
        lote.situacao = SituacaoExecucao.FALHOU
        lote.concluido_em = agora
        lote.motivo = INTERROMPIDO
    return len(interrompidos)
