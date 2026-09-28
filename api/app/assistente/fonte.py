"""A fonte da resposta, montada pelo código — RF42, história H66.

Cada resposta diz de que períodos consultou os dados (`respostas.Fonte`); aqui
esses períodos viram o que a tela mostra: o relatório de cada um — quando e por
quem foi importado — e, na previsão e no plano, a versão do modelo e o cálculo.

**O modelo de linguagem não vê a fonte.** Ele redige o texto da resposta, e a
fonte vai ao lado, pronta. Se ele a escrevesse, poderia citar outro período com
a mesma confiança com que cita o certo.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import formato
from app.assistente.respostas import Fonte
from app.esquemas import FonteResposta, PeriodoResposta, RelatorioDaFonte
from app.modelos import Importacao, Usuario


def _texto(periodos: list, fonte: Fonte) -> str:
    partes = []
    if len(periodos) == 1:
        (p,) = periodos
        partes.append(f"Relatório de {formato.intervalo(p.data_inicio, p.data_fim)}.")
    elif len(periodos) == 2:
        a, b = periodos
        partes.append(
            f"Relatórios de {formato.intervalo(a.data_inicio, a.data_fim)} e de "
            f"{formato.intervalo(b.data_inicio, b.data_fim)}."
        )
    elif periodos:
        partes.append(
            f"{len(periodos)} relatórios semanais, de {formato.data(periodos[0].data_inicio)} a "
            f"{formato.data(periodos[-1].data_fim)}."
        )
    if fonte.modelo_versao:
        partes.append(f"Modelo preditivo {fonte.modelo_versao}.")
    if fonte.execucao_id:
        partes.append(f"Cálculo de plano nº {fonte.execucao_id}.")
    return " ".join(partes)


def montar(s: Session, fonte: Fonte) -> FonteResposta:
    periodos = sorted(
        {p.id: p for p in fonte.periodos}.values(), key=lambda p: (p.data_inicio, p.id)
    )
    # A importação mais recente de cada período: depois de uma substituição (H25),
    # é ela que trouxe os dados.
    importacoes: dict[int, tuple[Importacao, str | None]] = {}
    for importacao, autor in s.execute(
        select(Importacao, Usuario.nome)
        .outerjoin(Usuario, Usuario.id == Importacao.usuario_id)
        .where(Importacao.periodo_id.in_([p.id for p in periodos]))
        .order_by(Importacao.enviado_em, Importacao.id)
    ).all():
        importacoes[importacao.periodo_id] = (importacao, autor)

    relatorios = []
    for p in periodos:
        importacao, autor = importacoes.get(p.id, (None, None))
        relatorios.append(
            RelatorioDaFonte(
                periodo=PeriodoResposta(id=p.id, data_inicio=p.data_inicio, data_fim=p.data_fim),
                importado_em=importacao.enviado_em if importacao else None,
                importado_por=autor,
                origem=importacao.origem if importacao else None,
            )
        )
    return FonteResposta(
        texto=_texto(periodos, fonte),
        relatorios=relatorios,
        modelo_versao=fonte.modelo_versao,
        execucao_id=fonte.execucao_id,
    )
