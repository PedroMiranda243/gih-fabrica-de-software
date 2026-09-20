"""Regras da importação de relatório (UC03 · histórias H21, H23, H24).

A prévia e a gravação usam **o mesmo** caminho de leitura e a **mesma** função
de casamento de parceiro. Se fossem dois códigos parecidos, a prévia acabaria
mostrando uma coisa e a gravação fazendo outra — e a prévia existe justamente
para o usuário confiar no que vai acontecer.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.leitor_relatorio import Leitura, LinhaLida, interpretar
from app.modelos import (
    HistoricoSegmento,
    Importacao,
    Metrica,
    OrigemImportacao,
    Parceiro,
    Periodo,
    Previsao,
    Usuario,
)
from app.servico_segmentacao import reprocessar_desde
from app.texto import normalizar


@dataclass
class PeriodoExistente:
    """O que já ocupa o período, para a decisão de substituir ser informada.

    Recusar dizendo apenas "já importado" obriga quem está importando a sair do
    fluxo para descobrir o que existe lá. Como a alternativa é apagar dados, a
    decisão precisa ser tomada com o número na frente.
    """

    importacao_id: int
    autor: str
    enviado_em: datetime
    total_metricas: int


@dataclass
class Analise:
    leitura: Leitura
    parceiros_novos: list[str]
    existente: PeriodoExistente | None

    @property
    def periodo_ja_importado(self) -> bool:
        return self.existente is not None


class PeriodoJaImportado(Exception):
    """RF12 — reimportar um período exige decisão explícita.

    O padrão continua sendo cancelar: substituir só acontece quando o pedido
    pede, porque gravar por cima sem perguntar é o que a regra proíbe (H25).
    """

    def __init__(self, existente: PeriodoExistente) -> None:
        super().__init__("Este período já foi importado.")
        self.existente = existente


def _indice_de_parceiros(s: Session) -> dict[str, Parceiro]:
    """Todos os parceiros, indexados pelo nome normalizado, **em uma consulta**.

    Buscar parceiro por parceiro funcionaria com 100 e morreria com 10.000, que
    é a carga do RNF04 — a armadilha do N+1 já está registrada no CLAUDE.md
    para a segmentação, e vale igual aqui.
    """
    return {normalizar(p.nome): p for p in s.scalars(select(Parceiro))}


def analisar(s: Session, texto: str, inicio: date, fim: date) -> Analise:
    """Lê o relatório e confronta com a base, **sem gravar nada** (H24).

    Pode ser repetida à vontade: é consulta.
    """
    leitura = interpretar(texto)
    existentes = _indice_de_parceiros(s)

    novos: list[str] = []
    vistos: set[str] = set()
    for linha in leitura.reconhecidos:
        chave = normalizar(linha.nome)
        if chave not in existentes and chave not in vistos:
            vistos.add(chave)
            novos.append(linha.nome)

    return Analise(
        leitura=leitura, parceiros_novos=novos, existente=_o_que_ja_ocupa(s, inicio, fim)
    )


def _o_que_ja_ocupa(s: Session, inicio: date, fim: date) -> PeriodoExistente | None:
    """A última importação do período e quantas métricas estão vigentes nele.

    "Vigente" é o que está no banco agora, e não o `total_gravado` da
    importação: depois de uma substituição esse total continua verdadeiro sobre
    o passado, mas deixa de descrever o presente.
    """
    periodo = s.scalar(
        select(Periodo).where(Periodo.data_inicio == inicio, Periodo.data_fim == fim)
    )
    if periodo is None:
        return None

    ultima = s.scalar(
        select(Importacao)
        .where(Importacao.periodo_id == periodo.id)
        .order_by(Importacao.enviado_em.desc(), Importacao.id.desc())
        .limit(1)
    )
    if ultima is None:
        return None

    return PeriodoExistente(
        importacao_id=ultima.id,
        autor=ultima.autor.nome if ultima.autor else "(usuário removido)",
        enviado_em=ultima.enviado_em,
        total_metricas=s.scalar(
            select(func.count()).select_from(Metrica).where(Metrica.periodo_id == periodo.id)
        )
        or 0,
    )


def gravar(
    s: Session,
    texto: str,
    inicio: date,
    fim: date,
    autor: Usuario,
    origem: OrigemImportacao = OrigemImportacao.TEXTO,
    substituir: bool = False,
) -> tuple[Importacao, Analise]:
    """Grava as métricas do período e cadastra os parceiros novos (H21).

    Tudo dentro da transação da requisição: ou o período inteiro entra, ou nada
    entra (UC03, E2). As linhas rejeitadas não impedem a gravação das válidas —
    o usuário já decidiu isso na prévia (UC03, A5).

    Com `substituir`, o conteúdo anterior do período é apagado antes da
    gravação — na **mesma** transação, para uma falha no meio não deixar o
    período com metade dos dados (H25).
    """
    analise = analisar(s, texto, inicio, fim)
    if analise.existente is not None and not substituir:
        raise PeriodoJaImportado(analise.existente)

    periodo = s.scalar(
        select(Periodo).where(Periodo.data_inicio == inicio, Periodo.data_fim == fim)
    )
    if periodo is None:
        periodo = Periodo(data_inicio=inicio, data_fim=fim)
        s.add(periodo)
        s.flush()
    elif substituir:
        _limpar_periodo(s, periodo.id)

    importacao = Importacao(
        periodo_id=periodo.id,
        usuario_id=autor.id,
        origem=origem,
        total_gravado=0,
        total_rejeitado=len(analise.leitura.rejeitados),
    )
    s.add(importacao)
    s.flush()

    parceiros = _indice_de_parceiros(s)
    for nome in analise.parceiros_novos:
        # Categoria fica em branco: a sugestão a partir do nome é a H27, e
        # categoria inferida só vale como sugestão até alguém confirmar (RN05).
        # Melhor vazio que palpite gravado como se fosse decisão.
        novo = Parceiro(nome=nome)
        s.add(novo)
        parceiros[normalizar(nome)] = novo
    s.flush()

    for linha in analise.leitura.reconhecidos:
        _gravar_metrica(s, linha, parceiros, periodo.id, importacao.id)

    importacao.total_gravado = len(analise.leitura.reconhecidos)
    s.flush()

    # A segmentação corre **na mesma transação** (H33): ou o período entra com
    # métrica e classificação, ou não entra. Período gravado sem segmento
    # deixaria o painel mostrando uma distribuição que não inclui a semana que
    # o usuário acabou de importar, sem nenhum erro na tela.
    #
    # `reprocessar_desde`, e não `reprocessar`, porque importar um período
    # antigo muda o histórico dos posteriores: um parceiro deixa de ser
    # recém-chegado, uma queda passa a ser a segunda seguida.
    reprocessar_desde(s, periodo.id)
    return importacao, analise


def _limpar_periodo(s: Session, periodo_id: int) -> None:
    """Apaga o que foi **derivado das métricas** daquele período (H25).

    Não é só a métrica. Segmento e previsão são calculados a partir dela: se a
    métrica é trocada e eles ficam, o sistema passa a afirmar uma classificação
    apoiada em número que não existe mais — e continua parecendo correto, que é
    a forma mais cara de errar neste domínio.

    O recálculo é de quem calcula (segmentação na Sprint 7, previsão na 8).
    Aqui a responsabilidade é não deixar resíduo.

    A `Importacao` anterior **permanece**: o que se apaga é o dado, não o
    rastro de quem o trouxe e quando.

    Cada tabela é nomeada uma a uma porque a coluna que aponta para o período
    **não** tem o mesmo nome nas três: na previsão ela é `periodo_base_id`, o
    período de onde a projeção partiu. Um laço genérico sobre `periodo_id`
    parece mais limpo e quebra justamente nessa.
    """
    s.execute(delete(Metrica).where(Metrica.periodo_id == periodo_id))
    s.execute(delete(HistoricoSegmento).where(HistoricoSegmento.periodo_id == periodo_id))
    s.execute(delete(Previsao).where(Previsao.periodo_base_id == periodo_id))
    s.flush()


def _gravar_metrica(
    s: Session,
    linha: LinhaLida,
    parceiros: dict[str, Parceiro],
    periodo_id: int,
    importacao_id: int,
) -> None:
    # Ticket médio **não** é gravado: é faturamento dividido por pedidos,
    # calculado na consulta (RN04). Guardá-lo faria o valor divergir das
    # parcelas que o originam na primeira correção de dado.
    s.add(
        Metrica(
            parceiro_id=parceiros[normalizar(linha.nome)].id,
            periodo_id=periodo_id,
            importacao_id=importacao_id,
            faturamento=linha.faturamento,
            pedidos=linha.pedidos,
        )
    )
