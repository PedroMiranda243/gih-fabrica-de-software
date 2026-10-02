"""A pergunta ao assistente, de ponta a ponta (UC12).

1. **A conta, a causa e o dado que não existe, antes de tudo**: a pergunta que
   pede soma, média, o porquê ou o lucro recebe a abstenção pelo código, sem o
   modelo (H68).
2. **Sem dados, sem pergunta ao modelo**: não há o que responder, e carregar o
   modelo custaria dezenas de segundos para dizer isso.
3. **Sem o modelo, a indisponibilidade** (E1): o motivo vem do redator, e o resto
   do sistema segue.
4. **O modelo identifica o tipo e os campos** (`redator.extrair`); fora do
   catálogo, ou comparando dois parceiros, a abstenção.
5. **A resolução confere os campos contra a base**, e o que falta vira pedido de
   precisão (A2).
6. **O código responde**, com as funções das telas e a fonte (H66).
7. **O modelo redige a resposta**, e a guarda confere (H67); reprovada, fica a
   do código.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import redator as modelo_de_linguagem
from app.assistente import resolucao
from app.assistente.catalogo import (
    CATALOGO,
    COMPARACAO,
    Extracao,
    UsoDoPeriodo,
    abstencao_pelo_codigo,
    instrucao,
    pede_total,
)
from app.assistente.redacao import Redacao, redigir
from app.assistente.respostas import (
    RESPONDER,
    Contexto,
    Resposta,
    abstencao,
    precisao,
)
from app.desempenho import ROTULO_SEGMENTO
from app.esquemas import SituacaoResposta, TipoPergunta
from app.modelos import Categoria, Periodo, RedatorMensagem
from app.redator import FalhaDoRedator, Redator
from app.texto import normalizar

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


@dataclass(frozen=True)
class Resultado:
    # O tipo do catálogo, ou fora dele. Nulo quando ninguém chegou a ler a
    # pergunta: sem dados, ou sem o modelo.
    tipo: TipoPergunta | None
    resposta: Resposta
    redacao: Redacao


def _do_codigo(tipo: TipoPergunta | None, resposta: Resposta) -> Resultado:
    return Resultado(tipo, resposta, Redacao(resposta.texto, RedatorMensagem.MODELO_FIXO))


def indisponivel(motivo: str) -> Resposta:
    return Resposta(
        SituacaoResposta.INDISPONIVEL,
        f"O assistente está indisponível agora. {motivo} O painel e as outras telas seguem "
        "funcionando.",
    )


def perguntar(s: Session, pergunta: str, r: Redator) -> Resultado:
    fora = abstencao_pelo_codigo(pergunta)
    if fora is not None:
        return _do_codigo(TipoPergunta.FORA_DO_CATALOGO, abstencao(fora))

    periodos = s.scalars(select(Periodo).order_by(Periodo.data_inicio, Periodo.id)).all()
    if not periodos:
        return _do_codigo(None, abstencao(SEM_DADOS))

    estado = r.estado()
    if not estado.disponivel:
        return _do_codigo(None, indisponivel(estado.motivo))

    categorias = s.scalars(
        select(Categoria.nome).where(Categoria.ativa.is_(True)).order_by(Categoria.nome)
    ).all()
    sistema = instrucao(list(categorias), [(p.data_inicio, p.data_fim) for p in periodos])
    try:
        extracao = r.extrair(sistema, pergunta, Extracao)
    except FalhaDoRedator as falha:
        if str(falha) == modelo_de_linguagem.ILEGIVEL:
            return _do_codigo(None, abstencao(NAO_ENTENDI))
        return _do_codigo(None, indisponivel(str(falha)))

    tipo, resposta = _responder(s, pergunta, extracao)
    return Resultado(tipo, resposta, redigir(r, pergunta, tipo, resposta))


def _dois_parceiros(pergunta: str, extracao: Extracao) -> bool:
    """A pergunta cita dois parceiros diferentes: é comparação, ou soma, dos dois."""
    outro = (extracao.outro_parceiro or "").strip()
    if not outro or not resolucao.citado(outro, pergunta):
        return False
    return normalizar(outro) != normalizar(extracao.parceiro or "")


def _corrigir(
    s: Session, pergunta: str, tipo: TipoPergunta, extracao: Extracao
) -> tuple[TipoPergunta, Extracao]:
    """O que o código acerta sobre a leitura do modelo — cada regra, um erro medido.

    - **O resumo da rede com um parceiro citado é o desempenho dele.** "Como foi o
      Quintal do Norte nesta semana?" saiu como o resumo da rede.
    - **A semana dita pelo nome, o código lê**, mesmo que o modelo tenha trazido
      outra: "na última semana" saiu como a semana anterior à mais recente (#235).
    - **A data que o modelo não trouxe, o código lê**: o mês, o ano, "o mês que
      vem". "Em 2019" e "em dezembro" chegaram sem data.
    - **O desempenho de várias semanas é a evolução**, semana a semana, em vez da
      precisão de qual semana: são os números do intervalo pedido, sem somar. Se a
      pergunta pede o total, é a abstenção, na resolução do período.
    """
    if (
        tipo is TipoPergunta.RESUMO_DO_PERIODO
        and (extracao.parceiro or "").strip()
        and resolucao.citado(extracao.parceiro, pergunta)
    ):
        tipo = TipoPergunta.DESEMPENHO_DO_PARCEIRO
    semana = resolucao.semana_dita(s, pergunta)
    if semana is not None and CATALOGO[tipo].periodo is not UsoDoPeriodo.NENHUM:
        extracao = extracao.model_copy(
            update={"inicio": semana[0].isoformat(), "fim": semana[1].isoformat()}
        )
    if extracao.inicio is None and extracao.fim is None:
        fim_dos_dados = s.scalar(select(func.max(Periodo.data_fim)))
        futuro = CATALOGO[tipo].periodo is UsoDoPeriodo.NENHUM
        citadas = resolucao.datas_da_pergunta(pergunta, fim_dos_dados, futuro=futuro)
        if citadas is not None:
            extracao = extracao.model_copy(
                update={"inicio": citadas[0].isoformat(), "fim": citadas[1].isoformat()}
            )
    if (
        tipo is TipoPergunta.DESEMPENHO_DO_PARCEIRO
        and not pede_total(pergunta)
        and resolucao.semanas(s, extracao.inicio, extracao.fim) > 1
    ):
        tipo = TipoPergunta.EVOLUCAO_DO_PARCEIRO
    return tipo, extracao


def _responder(s: Session, pergunta: str, extracao: Extracao) -> tuple[TipoPergunta, Resposta]:
    tipo = extracao.tipo
    if tipo is TipoPergunta.FORA_DO_CATALOGO:
        return tipo, abstencao(FORA_DO_CATALOGO)
    if _dois_parceiros(pergunta, extracao):
        return TipoPergunta.FORA_DO_CATALOGO, abstencao(COMPARACAO)
    tipo, extracao = _corrigir(s, pergunta, tipo, extracao)
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

    periodos = resolucao.periodos(
        s, extracao.inicio, extracao.fim, entrada.periodo, total=pede_total(pergunta)
    )
    if isinstance(periodos, Resposta):
        return tipo, periodos
    contexto.periodos = periodos
    if entrada.periodo is UsoDoPeriodo.NENHUM:
        contexto.pedido = resolucao.pedido(extracao.inicio, extracao.fim)
    contexto.quantos = resolucao.quantos(extracao.quantos)
    return tipo, RESPONDER[tipo](contexto)
