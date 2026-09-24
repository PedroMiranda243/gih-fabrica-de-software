"""Configuração da segmentação — RF21, história H34.

Os três limiares de RN01 mudam **sem alteração de código**: tamanho do Top N,
períodos consecutivos para caracterizar tendência e períodos de histórico abaixo
dos quais o parceiro é recém-chegado.

**Só o Administrador.** É a única rota do sistema que muda como todo o resto
classifica: quem mexe aqui reescreve o significado de "em risco" para a rede
inteira. O Gestor decide campanha; o Administrador decide a régua.

A tela é `web/src/paginas/Configuracao.jsx`. Ela não estava no protótipo
aprovado (H08), e ficou como lacuna declarada na entrega da Sprint 04 até a
equipe decidir fechá-la — sobre o sistema visual já aprovado, sem direção
visual nova. O comando `configurar-segmentacao` continua existindo para quem
administra pelo terminal.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import auditoria
from app.auditoria import Acao
from app.dependencias import Banco, UsuarioAtual, exigir
from app.esquemas import ConfiguracaoSegmentacaoResposta, LimiaresSegmentacao
from app.modelos import ConfiguracaoSegmentacao, Perfil, Periodo, Usuario
from app.servico_segmentacao import Limiares, limiares_vigentes, reprocessar

router = APIRouter(
    prefix="/api/configuracao",
    tags=["configuração"],
    dependencies=[Depends(exigir(Perfil.ADMINISTRADOR))],
)


def _linha(s: Session) -> ConfiguracaoSegmentacao:
    """A linha de configuração, criada com os padrões se ainda não existir.

    A migração já a insere; isto cobre um banco criado antes dela e evita que
    uma rota de leitura devolva 500 por causa de uma linha ausente que tem
    padrão conhecido.
    """
    configuracao = s.get(ConfiguracaoSegmentacao, 1)
    if configuracao is None:
        vigentes = limiares_vigentes(s)
        configuracao = ConfiguracaoSegmentacao(
            id=1,
            top_n=vigentes.top_n,
            periodos_tendencia=vigentes.periodos_tendencia,
            periodos_novato=vigentes.periodos_novato,
        )
        s.add(configuracao)
        s.flush()
    return configuracao


def _resposta(
    s: Session, configuracao: ConfiguracaoSegmentacao, periodos: int = 0
) -> ConfiguracaoSegmentacaoResposta:
    autor = (
        s.get(Usuario, configuracao.atualizado_por_id)
        if configuracao.atualizado_por_id is not None
        else None
    )
    return ConfiguracaoSegmentacaoResposta(
        top_n=configuracao.top_n,
        periodos_tendencia=configuracao.periodos_tendencia,
        periodos_novato=configuracao.periodos_novato,
        atualizado_em=configuracao.atualizado_em,
        atualizado_por=autor.nome if autor else None,
        periodos_reprocessados=periodos,
    )


@router.get("/segmentacao", response_model=ConfiguracaoSegmentacaoResposta)
def obter(s: Banco) -> ConfiguracaoSegmentacaoResposta:
    """Os limiares em vigor."""
    return _resposta(s, _linha(s))


@router.put("/segmentacao", response_model=ConfiguracaoSegmentacaoResposta)
def alterar(
    novos: LimiaresSegmentacao,
    request: Request,
    s: Banco,
    autor: UsuarioAtual,
) -> ConfiguracaoSegmentacaoResposta:
    """Altera os limiares e **reclassifica o período mais recente**.

    Configuração que não se reflete na tela engana quem a mudou: o
    administrador baixaria o Top N de 15 para 10, olharia o painel e veria as
    mesmas quinze linhas marcadas como Top.

    Só o período mais recente entra na requisição. Reprocessar a base inteira
    levaria segundos com 10.000 parceiros e doze períodos — tempo demais para
    uma chamada síncrona, e o RNF03 vale para o sistema todo. Os períodos
    anteriores mantêm a classificação antiga até `reprocessar-segmentos` rodar,
    e a resposta diz quantos foram reclassificados agora justamente para que
    isso não passe despercebido.

    A auditoria guarda **o valor anterior junto do novo**. "Alterou a
    configuração" sem dizer o que era antes não responde à pergunta que a trilha
    existe para responder.
    """
    configuracao = _linha(s)
    anterior = {
        "top_n": configuracao.top_n,
        "periodos_tendencia": configuracao.periodos_tendencia,
        "periodos_novato": configuracao.periodos_novato,
    }

    configuracao.top_n = novos.top_n
    configuracao.periodos_tendencia = novos.periodos_tendencia
    configuracao.periodos_novato = novos.periodos_novato
    configuracao.atualizado_por_id = autor.id
    # O relógio é o do banco, e não o do processo: a trilha e esta coluna
    # precisam poder ser comparadas sem depender de dois relógios concordarem.
    configuracao.atualizado_em = s.scalar(select(func.now()))
    s.flush()

    recente = s.scalar(select(Periodo.id).order_by(Periodo.data_inicio.desc(), Periodo.id.desc()))
    periodos = 0
    if recente is not None:
        reprocessar(s, recente, Limiares(**novos.model_dump()))
        periodos = 1

    auditoria.registrar(
        Acao.SEGMENTACAO_CONFIGURADA,
        usuario_id=autor.id,
        detalhes={"anterior": anterior, "novo": novos.model_dump(), "periodos": periodos},
        origem=auditoria.origem_de(request),
    )
    return _resposta(s, configuracao, periodos)
