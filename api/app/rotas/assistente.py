"""O assistente analítico — UC12, RF41, história H65 (ADR-013).

Do Gestor e do Analista (matriz do UC12). É **consulta**: nada muda o estado,
e por isso nada audita, como no painel.

**As quatro situações são respostas, e não erros.** Fora do catálogo, com a
pergunta ambígua ou com o modelo fora do ar, a rota responde 200 com a situação
e o texto: dizer "não há base para responder" é a resposta certa (A1), e o
assistente indisponível é um estado da instalação, e não uma falha da API (E1).
A pergunta acima do limite, sim, é recusada, com o limite na mensagem (E2,
RNF15).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app import redator
from app.assistente import fonte, servico
from app.assistente.catalogo import CATALOGO
from app.config import config
from app.dependencias import Banco, exigir
from app.esquemas import (
    EstadoAssistente,
    EstadoDoAssistente,
    ExemploPergunta,
    FatoMensagem,
    PerguntaAssistente,
    RespostaAssistente,
)
from app.modelos import Perfil

router = APIRouter(
    prefix="/api/assistente",
    tags=["assistente"],
    dependencies=[Depends(exigir(Perfil.GESTOR, Perfil.ANALISTA))],
)


@router.get("", response_model=EstadoDoAssistente)
def estado() -> EstadoDoAssistente:
    """O que a tela mostra ao abrir: se o modelo está no ar, e os exemplos do catálogo."""
    atual = redator.atual().estado()
    return EstadoDoAssistente(
        assistente=EstadoAssistente(
            disponivel=atual.disponivel, modelo=atual.modelo, motivo=atual.motivo
        ),
        exemplos=[
            ExemploPergunta(tipo=e.tipo, descricao=e.descricao, exemplo=e.exemplo)
            for e in CATALOGO.values()
        ],
        tamanho_maximo=config.tamanho_maximo_pergunta,
    )


@router.post("/perguntas", response_model=RespostaAssistente)
def perguntar(pedido: PerguntaAssistente, s: Banco) -> RespostaAssistente:
    """A resposta a uma pergunta em linguagem natural (UC12, passos 1 a 4).

    O modelo lê a pergunta e redige a resposta: com ele carregado, leva de 5 a 10 s;
    a primeira pergunta depois de ele ficar parado paga o carregamento, perto de
    45 s (ADR-013). A fonte é do código, e o modelo não a vê (H66).
    """
    resultado = servico.perguntar(s, pedido.texto, redator.atual())
    resposta = resultado.resposta
    return RespostaAssistente(
        situacao=resposta.situacao,
        tipo=resultado.tipo,
        texto=resultado.redacao.texto,
        fonte=fonte.montar(s, resposta.fonte) if resposta.fonte else None,
        redator=resultado.redacao.redator,
        motivo=resultado.redacao.motivo,
        fatos=[FatoMensagem(**f) for f in resposta.fatos],
        candidatos=resposta.candidatos,
    )
