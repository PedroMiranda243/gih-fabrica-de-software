"""A fila e a decisão das mensagens — UC11, RF37 a RF39, RN06, histórias H61 a H63.

**Nenhuma mensagem sai sem a decisão de um gestor** (RN06). As três formas de
decidir — aprovar, rejeitar e aprovar em lote — passam por aqui, e as rotas que
as chamam exigem o perfil Gestor no servidor; o banco recusa a mensagem decidida
sem autor e sem data (`ck_mensagem_decisao_tem_autor`). A edição não decide:
muda o texto e deixa a mensagem pendente, para o gestor aprová-la depois (A1).

**A decisão concorrente é recusada, e não sobrescrita** (E1). A mudança de
estado é um `UPDATE ... WHERE estado = 'PENDENTE'`: se outra pessoa decidiu no
meio, nenhuma linha muda, e quem chegou depois recebe a decisão que já estava
registrada. Consultar antes e gravar depois deixaria uma janela entre as duas.

**A edição guarda o original** (A1): `texto_gerado` é o que foi redigido, e
`texto_final`, o que o gestor deixou. Na aprovação, `texto_final` recebe o texto
que vale — o editado, ou o redigido —, e o histórico mostra o conteúdo final sem
precisar adivinhar (RF40).

**O número que o gestor escreve não é recusado, mas é apontado.** A RN08 trata do
modelo de linguagem; a pessoa pode escrever "20% de desconto". A resposta diz os
números do texto que não vieram dos fatos, para a tela mostrar antes da
aprovação.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.modelos import EstadoMensagem, Mensagem, Usuario

# O tamanho da aprovação em lote: uma tela cheia de mensagens de um segmento.
MAXIMO_EM_LOTE = 200


class DecisaoRecusada(Exception):
    """A mensagem não pode ser decidida: não existe, ou já foi decidida por alguém."""

    def __init__(self, erro: str, ajuda: str, *, status: int = 409, **extra) -> None:
        super().__init__(erro)
        self.erro = erro
        self.ajuda = ajuda
        self.status = status
        self.extra = extra


@dataclass(frozen=True)
class DecisaoRegistrada:
    mensagem_id: int
    estado: EstadoMensagem
    decidida_por: str | None
    decidida_em: datetime | None


def _registrada(s: Session, mensagem_id: int) -> DecisaoRegistrada | None:
    linha = s.execute(
        select(Mensagem.estado, Usuario.nome, Mensagem.decidida_em)
        .outerjoin(Usuario, Usuario.id == Mensagem.decidida_por_id)
        .where(Mensagem.id == mensagem_id)
    ).first()
    if linha is None:
        return None
    return DecisaoRegistrada(mensagem_id, linha[0], linha[1], linha[2])


def _recusa(s: Session, mensagem_id: int) -> DecisaoRecusada:
    """Por que a mudança não pegou: a mensagem não existe, ou já foi decidida."""
    registrada = _registrada(s, mensagem_id)
    if registrada is None:
        return DecisaoRecusada(
            "Mensagem não encontrada.", "Volte à fila de aprovação.", status=404
        )
    verbo = "aprovada" if registrada.estado == EstadoMensagem.APROVADA else "rejeitada"
    quem = f" por {registrada.decidida_por}" if registrada.decidida_por else ""
    return DecisaoRecusada(
        "Esta mensagem já foi decidida.",
        f"Ela foi {verbo}{quem} enquanto você a revisava. A fila foi atualizada.",
        mensagem_id=mensagem_id,
        estado=registrada.estado.value,
        decidida_por=registrada.decidida_por,
        decidida_em=registrada.decidida_em.isoformat() if registrada.decidida_em else None,
    )


def _pendente(mensagem_id: int):
    return (Mensagem.id == mensagem_id) & (Mensagem.estado == EstadoMensagem.PENDENTE)


def aprovar(s: Session, mensagem_id: int, *, usuario_id: int) -> Mensagem:
    """Aprova a mensagem pendente, com o texto que vale: o editado, ou o redigido."""
    mudou = s.execute(
        update(Mensagem)
        .where(_pendente(mensagem_id))
        .values(
            estado=EstadoMensagem.APROVADA,
            decidida_por_id=usuario_id,
            decidida_em=func.now(),
            texto_final=func.coalesce(Mensagem.texto_final, Mensagem.texto_gerado),
        )
        .returning(Mensagem.id)
    ).first()
    if mudou is None:
        raise _recusa(s, mensagem_id)
    return _recarregar(s, mensagem_id)


def rejeitar(s: Session, mensagem_id: int, *, usuario_id: int, motivo: str | None) -> Mensagem:
    """Rejeita a mensagem pendente, com o motivo, se a pessoa deu um (A2)."""
    motivo = (motivo or "").strip() or None
    mudou = s.execute(
        update(Mensagem)
        .where(_pendente(mensagem_id))
        .values(
            estado=EstadoMensagem.REJEITADA,
            decidida_por_id=usuario_id,
            decidida_em=func.now(),
            motivo_rejeicao=motivo,
        )
        .returning(Mensagem.id)
    ).first()
    if mudou is None:
        raise _recusa(s, mensagem_id)
    return _recarregar(s, mensagem_id)


def editar(s: Session, mensagem_id: int, texto: str) -> Mensagem:
    """Troca o texto da mensagem pendente, e ela continua pendente (A1).

    O texto igual ao redigido desfaz a edição: não há o que guardar à parte.
    """
    texto = texto.strip()
    mudou = s.execute(
        update(Mensagem)
        .where(_pendente(mensagem_id))
        .values(
            texto_final=func.nullif(texto, Mensagem.texto_gerado),
        )
        .returning(Mensagem.id)
    ).first()
    if mudou is None:
        raise _recusa(s, mensagem_id)
    return _recarregar(s, mensagem_id)


@dataclass
class ResultadoEmLote:
    aprovadas: list[int]
    ja_decididas: list[DecisaoRegistrada]
    nao_encontradas: list[int]


def aprovar_em_lote(s: Session, ids: list[int], *, usuario_id: int) -> ResultadoEmLote:
    """Aprova as pendentes entre `ids`, cada uma com a própria decisão registrada (A3).

    É ação humana explícita sobre mensagens que a pessoa selecionou uma a uma — e
    cada mensagem ganha autor e data, como na aprovação individual (RN06).
    """
    ids = list(dict.fromkeys(ids))
    aprovadas = list(
        s.scalars(
            update(Mensagem)
            .where(Mensagem.id.in_(ids), Mensagem.estado == EstadoMensagem.PENDENTE)
            .values(
                estado=EstadoMensagem.APROVADA,
                decidida_por_id=usuario_id,
                decidida_em=func.now(),
                texto_final=func.coalesce(Mensagem.texto_final, Mensagem.texto_gerado),
            )
            .returning(Mensagem.id)
        )
    )
    resultado = ResultadoEmLote(sorted(aprovadas), [], [])
    for mensagem_id in ids:
        if mensagem_id in aprovadas:
            continue
        registrada = _registrada(s, mensagem_id)
        if registrada is None:
            resultado.nao_encontradas.append(mensagem_id)
        else:
            resultado.ja_decididas.append(registrada)
    return resultado


def _recarregar(s: Session, mensagem_id: int) -> Mensagem:
    """A mensagem como o banco a deixou: o `UPDATE` direto não passa pela sessão."""
    mensagem = s.get(Mensagem, mensagem_id)
    s.refresh(mensagem)
    return mensagem
