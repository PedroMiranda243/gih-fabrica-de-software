"""A pergunta ao assistente, de ponta a ponta (UC12).

1. **Sem dados, sem pergunta ao modelo**: não há o que responder, e carregar o
   modelo custaria dezenas de segundos para dizer isso.
2. **Sem o modelo, a indisponibilidade** (E1): o motivo vem do redator, e o resto
   do sistema segue.
3. **O modelo identifica o tipo e os campos** (`redator.extrair`); fora do
   catálogo, a abstenção.
4. **A resolução confere os campos contra a base**, e o que falta vira pedido de
   precisão (A2).
5. **O código responde**, com as funções das telas.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import redator as modelo_de_linguagem
from app.assistente import resolucao
from app.assistente.catalogo import CATALOGO, Extracao, instrucao
from app.assistente.respostas import (
    RESPONDER,
    Contexto,
    Resposta,
    abstencao,
    precisao,
)
from app.desempenho import ROTULO_SEGMENTO
from app.esquemas import SituacaoResposta, TipoPergunta
from app.modelos import Categoria, Periodo
from app.redator import FalhaDoRedator, Redator

SEM_DADOS = (
    "Ainda não há relatório importado. O assistente responde sobre os dados da rede, e eles "
    "chegam com a primeira importação."
)
NAO_ENTENDI = "Não consegui ler a pergunta. Reformule, ou comece por um dos exemplos."
FORA_DO_CATALOGO = (
    "Essa pergunta está fora do que o assistente sabe responder. Ele responde sobre o "
    "desempenho, a evolução, a posição, o segmento e a previsão de um parceiro; o ranking, os "
    "segmentos e o Top de um período; o resumo da rede; e o último plano de campanha."
)
SEM_PARCEIRO = "De qual parceiro? Escreva o nome dele na pergunta."
SEM_SEGMENTO = "De qual segmento?"


def indisponivel(motivo: str) -> Resposta:
    return Resposta(
        SituacaoResposta.INDISPONIVEL,
        f"O assistente está indisponível agora. {motivo} O painel e as outras telas seguem "
        "funcionando.",
    )


def perguntar(s: Session, pergunta: str, r: Redator) -> tuple[TipoPergunta | None, Resposta]:
    """O tipo que o modelo identificou, e a resposta. O tipo é nulo quando o modelo nem chegou
    a ler a pergunta."""
    periodos = s.scalars(select(Periodo).order_by(Periodo.data_inicio, Periodo.id)).all()
    if not periodos:
        return None, abstencao(SEM_DADOS)

    estado = r.estado()
    if not estado.disponivel:
        return None, indisponivel(estado.motivo)

    categorias = s.scalars(
        select(Categoria.nome).where(Categoria.ativa.is_(True)).order_by(Categoria.nome)
    ).all()
    sistema = instrucao(list(categorias), [(p.data_inicio, p.data_fim) for p in periodos])
    try:
        extracao = r.extrair(sistema, pergunta, Extracao)
    except FalhaDoRedator as falha:
        if str(falha) == modelo_de_linguagem.ILEGIVEL:
            return None, abstencao(NAO_ENTENDI)
        return None, indisponivel(str(falha))

    return _responder(s, pergunta, extracao)


def _responder(s: Session, pergunta: str, extracao: Extracao) -> tuple[TipoPergunta, Resposta]:
    tipo = extracao.tipo
    if tipo is TipoPergunta.FORA_DO_CATALOGO:
        return tipo, abstencao(FORA_DO_CATALOGO)
    entrada = CATALOGO[tipo]
    contexto = Contexto(s)

    if entrada.parceiro:
        termo = (extracao.parceiro or "").strip()
        if not termo:
            return tipo, precisao(SEM_PARCEIRO)
        if not resolucao.citado(termo, pergunta):
            # O parceiro veio do modelo, e não da pessoa: a classificação inteira
            # é suspeita, e responder sobre ele seria responder outra pergunta.
            return TipoPergunta.FORA_DO_CATALOGO, abstencao(FORA_DO_CATALOGO)
        achado = resolucao.parceiro(s, termo)
        if isinstance(achado, Resposta):
            return tipo, achado
        contexto.parceiro = achado

    if entrada.segmento:
        if extracao.segmento is None:
            return tipo, precisao(SEM_SEGMENTO, list(ROTULO_SEGMENTO.values()))
        contexto.segmento = extracao.segmento

    if entrada.categoria and (extracao.categoria or "").strip():
        achada = resolucao.categoria(s, extracao.categoria.strip())
        if isinstance(achada, Resposta):
            return tipo, achada
        contexto.categoria = achada

    periodos = resolucao.periodos(s, extracao.inicio, extracao.fim, entrada.periodo)
    if isinstance(periodos, Resposta):
        return tipo, periodos
    contexto.periodos = periodos
    contexto.quantos = resolucao.quantos(extracao.quantos)
    return tipo, RESPONDER[tipo](contexto)
