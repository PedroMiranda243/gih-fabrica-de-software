"""Modelo de dados do GIH.

Convenções do projeto: tabelas no singular, `snake_case`, e português no domínio
de negócio (ver CLAUDE.md, seção 5).

Duas decisões aqui não são óbvias e estão explicadas onde aparecem: o ticket
médio não existe como coluna (RN04) e a métrica é única por parceiro e período,
o que é o que impede período duplicado de corromper a série.
"""
from __future__ import annotations

import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.db import Base
from app.texto import normalizar


# --------------------------------------------------------------------------- enums
class Perfil(enum.StrEnum):
    ADMINISTRADOR = "ADMINISTRADOR"
    GESTOR = "GESTOR"
    ANALISTA = "ANALISTA"
    PARCEIRO = "PARCEIRO"


class Segmento(enum.StrEnum):
    """Ordem de precedência em RN01 — Em Risco vence Top de propósito."""

    PROSPECCAO = "PROSPECCAO"
    RECEM_CHEGADO = "RECEM_CHEGADO"
    EM_RISCO = "EM_RISCO"
    TOP = "TOP"
    EM_ASCENSAO = "EM_ASCENSAO"
    ESTAVEL = "ESTAVEL"


class OrigemCategoria(enum.StrEnum):
    """RN05 — sugestão não é confirmação; só MANUAL entra em ação por categoria."""

    INFERIDA = "INFERIDA"
    SUGERIDA_IA = "SUGERIDA_IA"
    MANUAL = "MANUAL"


class StatusComercial(enum.StrEnum):
    ATIVO = "ATIVO"
    PROSPECCAO = "PROSPECCAO"
    INATIVO = "INATIVO"


class OrigemImportacao(enum.StrEnum):
    TEXTO = "TEXTO"
    CSV = "CSV"


class ModoExecucao(enum.StrEnum):
    SERIAL = "SERIAL"
    CPU_PARALELO = "CPU_PARALELO"
    GPU = "GPU"


class EstadoMensagem(enum.StrEnum):
    PENDENTE = "PENDENTE"
    APROVADA = "APROVADA"
    REJEITADA = "REJEITADA"


class SituacaoTreino(enum.StrEnum):
    EM_ANDAMENTO = "EM_ANDAMENTO"
    CONCLUIDO = "CONCLUIDO"
    FALHOU = "FALHOU"


# --------------------------------------------------------------------------- acesso
class Usuario(Base):
    __tablename__ = "usuario"

    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(String(60), unique=True)
    nome: Mapped[str] = mapped_column(String(120))
    senha_hash: Mapped[str] = mapped_column(String(255))
    perfil: Mapped[Perfil] = mapped_column()
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    # Só o perfil PARCEIRO se vincula a um parceiro: é o que restringe a consulta
    # ao próprio desempenho (RF26).
    parceiro_id: Mapped[int | None] = mapped_column(ForeignKey("parceiro.id"))

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "(perfil = 'PARCEIRO') = (parceiro_id IS NOT NULL)",
            name="ck_usuario_parceiro_apenas_perfil_parceiro",
        ),
    )


class Auditoria(Base):
    """Trilha de ações sensíveis (RF06).

    `usuario_id` é opcional de propósito: tentativa de login com usuário
    inexistente precisa ser registrada, e nesse caso não há usuário.
    """

    __tablename__ = "auditoria"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"))
    acao: Mapped[str] = mapped_column(String(60))
    detalhes: Mapped[dict | None] = mapped_column(JSONB)
    origem: Mapped[str | None] = mapped_column(String(45))
    ocorrido_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (Index("ix_auditoria_ocorrido_em", "ocorrido_em"),)



class SessaoAcesso(Base):
    """Sessão autenticada, com estado no servidor (RF01, RF02).

    O nome não é `Sessao` porque `app.db.sessao` já é a sessão do SQLAlchemy —
    duas coisas diferentes com o mesmo nome no mesmo import é erro esperando
    acontecer.

    Guarda-se o **hash** do identificador, nunca ele próprio: quem conseguir ler
    esta tabela não consegue se passar por ninguém.
    """

    __tablename__ = "sessao_acesso"

    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"))

    criada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # Revogar em vez de apagar: "esta sessão foi encerrada por troca de senha"
    # é informação de investigação, e some se a linha for removida.
    revogada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    motivo_revogacao: Mapped[str | None] = mapped_column(String(40))

    origem: Mapped[str | None] = mapped_column(String(45))  # cabe IPv6
    agente: Mapped[str | None] = mapped_column(String(255))

    usuario: Mapped[Usuario] = relationship()

    __table_args__ = (Index("ix_sessao_acesso_usuario", "usuario_id"),)


class TentativaLogin(Base):
    """Tentativas de autenticação, base do bloqueio por força bruta (RNF11).

    `login` é texto livre e **não** é chave estrangeira de propósito: tentativa
    contra usuário inexistente também precisa ser contada, senão a defesa só
    protege quem já existe — e é justamente o login desconhecido que o ataque
    por dicionário usa.
    """

    __tablename__ = "tentativa_login"

    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(String(60))
    origem: Mapped[str] = mapped_column(String(45))
    sucesso: Mapped[bool] = mapped_column(Boolean)
    ocorrido_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (Index("ix_tentativa_origem_ocorrido", "origem", "ocorrido_em"),)


# --------------------------------------------------------------------------- parceiros
class Categoria(Base):
    __tablename__ = "categoria"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(60), unique=True)
    ativa: Mapped[bool] = mapped_column(Boolean, default=True)


class Parceiro(Base):
    __tablename__ = "parceiro"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(160), unique=True)

    # Forma de comparação do nome: minúscula, sem acento (RF24). Existe como
    # coluna, e não como função na consulta, porque `unaccent(lower(nome))`
    # aplicado linha a linha impede qualquer índice de servir — viraria
    # varredura completa na carga do RNF04.
    nome_normalizado: Mapped[str] = mapped_column(String(160))

    categoria_id: Mapped[int | None] = mapped_column(ForeignKey("categoria.id"))

    # Categoria em branco é resultado aceitável: melhor vazio que palpite errado.
    origem_categoria: Mapped[OrigemCategoria | None] = mapped_column()

    status: Mapped[StatusComercial] = mapped_column(default=StatusComercial.ATIVO)
    contato: Mapped[str | None] = mapped_column(String(120))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    categoria: Mapped[Categoria | None] = relationship()

    @validates("nome")
    def _sincronizar_nome_normalizado(self, chave: str, valor: str) -> str:
        """Mantém `nome_normalizado` colado em `nome`, em toda gravação.

        Deixar o preenchimento a cargo de quem grava faria a coluna envelhecer
        na primeira rota que esquecesse — e a busca deixaria de encontrar o
        parceiro renomeado **sem erro nenhum**, que é a forma de falha mais cara
        deste projeto.
        """
        self.nome_normalizado = normalizar(valor)
        return valor

    __table_args__ = (
        CheckConstraint(
            "(categoria_id IS NULL) = (origem_categoria IS NULL)",
            name="ck_parceiro_categoria_com_origem",
        ),
        Index("ix_parceiro_nome", "nome"),
        # Índice de trigrama: é o que faz `LIKE '%termo%'` usar índice em vez de
        # varrer a tabela. Um btree comum só serviria para busca por prefixo, e
        # o RF24 pede correspondência parcial em qualquer posição do nome.
        Index(
            "ix_parceiro_nome_normalizado_trgm",
            "nome_normalizado",
            postgresql_using="gin",
            postgresql_ops={"nome_normalizado": "gin_trgm_ops"},
        ),
    )


# --------------------------------------------------------------------------- dados
class Periodo(Base):
    """Janela de tempo de um relatório.

    O relatório de origem não traz datas — o período é informado no upload e a
    importação sem ele é recusada (RN03).
    """

    __tablename__ = "periodo"

    id: Mapped[int] = mapped_column(primary_key=True)
    data_inicio: Mapped[date] = mapped_column(Date)
    data_fim: Mapped[date] = mapped_column(Date)

    __table_args__ = (
        UniqueConstraint("data_inicio", "data_fim", name="uq_periodo_intervalo"),
        CheckConstraint("data_fim >= data_inicio", name="ck_periodo_ordem"),
    )


class Importacao(Base):
    __tablename__ = "importacao"

    id: Mapped[int] = mapped_column(primary_key=True)
    periodo_id: Mapped[int] = mapped_column(ForeignKey("periodo.id"))
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"))
    origem: Mapped[OrigemImportacao] = mapped_column()
    total_gravado: Mapped[int] = mapped_column(Integer, default=0)
    total_rejeitado: Mapped[int] = mapped_column(Integer, default=0)
    enviado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    periodo: Mapped[Periodo] = relationship()
    # O histórico da H29 precisa responder "quem trouxe este dado", e o RF13
    # pede o autor pelo nome. Sem a relação, a listagem faria uma consulta por
    # linha para descobrir isso.
    autor: Mapped[Usuario] = relationship()


class Metrica(Base):
    """Desempenho de um parceiro em um período.

    **Ticket médio não é coluna** (RN04): é faturamento dividido por pedidos,
    calculado na consulta. Guardá-lo faria o valor divergir das parcelas que o
    originam na primeira correção de dado.

    A restrição de unicidade por (parceiro, período) é o que impede uma
    reimportação de duplicar a série e corromper a segmentação por tendência.
    """

    __tablename__ = "metrica"

    id: Mapped[int] = mapped_column(primary_key=True)
    parceiro_id: Mapped[int] = mapped_column(ForeignKey("parceiro.id"))
    periodo_id: Mapped[int] = mapped_column(ForeignKey("periodo.id"))
    importacao_id: Mapped[int] = mapped_column(ForeignKey("importacao.id"))

    faturamento: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    pedidos: Mapped[int] = mapped_column(Integer)
    projecao: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))

    __table_args__ = (
        UniqueConstraint("parceiro_id", "periodo_id", name="uq_metrica_parceiro_periodo"),
        CheckConstraint("faturamento >= 0", name="ck_metrica_faturamento_nao_negativo"),
        CheckConstraint("pedidos >= 0", name="ck_metrica_pedidos_nao_negativo"),
        # Ranking do período: ordena por faturamento sem varrer a tabela (RNF05).
        Index("ix_metrica_periodo_faturamento", "periodo_id", "faturamento"),
    )


class ConfiguracaoSegmentacao(Base):
    """Os limiares da segmentacao, configuraveis sem alterar codigo (RF21, H34).

    **Uma linha so**, garantida pelo `CHECK id = 1`. Configuracao global sem
    essa trava vira duas linhas na primeira gravacao concorrente, e a regra
    passa a depender de qual delas o `SELECT` devolver primeiro — um defeito que
    nao quebra nada na hora e classifica errado para sempre.

    Os valores nascem em `app.servico_segmentacao.Limiares`, que continua sendo
    o padrao usado quando esta linha nao existe.
    """

    __tablename__ = "configuracao_segmentacao"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    top_n: Mapped[int] = mapped_column(Integer)
    periodos_tendencia: Mapped[int] = mapped_column(Integer)
    periodos_novato: Mapped[int] = mapped_column(Integer)

    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    atualizado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"))

    __table_args__ = (
        CheckConstraint("id = 1", name="ck_configuracao_linha_unica"),
        # Zero ou negativo nao e "mais permissivo", e sem sentido: Top 0 nao
        # tem ninguem dentro, e tendencia de 0 periodos classificaria a rede
        # inteira como em risco e em ascensao ao mesmo tempo.
        CheckConstraint("top_n >= 1", name="ck_configuracao_top_n"),
        CheckConstraint("periodos_tendencia >= 1", name="ck_configuracao_tendencia"),
        CheckConstraint("periodos_novato >= 1", name="ck_configuracao_novato"),
    )


class HistoricoSegmento(Base):
    """Segmento atribuído a um parceiro em um período.

    Guarda o segmento **final**, já resolvido pela precedência de RN01. Por isso
    a mobilidade do Top N (RF22) **não** pode ser derivada daqui: um parceiro
    entre os N maiores mas em queda fica gravado como EM_RISCO, e lê-lo daqui
    faria o painel anunciar que ele saiu do Top N enquanto continua lá (RN02).
    """

    __tablename__ = "historico_segmento"

    id: Mapped[int] = mapped_column(primary_key=True)
    parceiro_id: Mapped[int] = mapped_column(ForeignKey("parceiro.id"))
    periodo_id: Mapped[int] = mapped_column(ForeignKey("periodo.id"))
    segmento: Mapped[Segmento] = mapped_column()
    calculado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("parceiro_id", "periodo_id", name="uq_segmento_parceiro_periodo"),
        Index("ix_segmento_periodo_segmento", "periodo_id", "segmento"),
    )


# --------------------------------------------------------------------------- núcleo
class TreinoModelo(Base):
    """Uma execução do treino do modelo preditivo — RF27, UC07, histórias H42 a H45.

    Registra o que o RF27 pede — data, volume de dados e métricas — e o que o
    UC07-A1 precisa para decidir: a versão treinada entra em uso só se superar
    as referências; senão, fica a anterior, e `motivo` diz por quê.

    **A versão em uso depois deste treino** fica gravada na própria linha, e não
    em configuração à parte: a resposta a "qual modelo está valendo?" é o último
    treino concluído, sem uma segunda fonte que possa discordar dele.

    **Os pesos ficam aqui** (ADR-010): poucos KB, e a versão em uso sobrevive a
    reinício sem depender de arquivo num volume.

    **Um treino por vez**, garantido pelo índice único parcial sobre os que
    estão em andamento. Trava em memória não serviria: com mais de um processo,
    um não enxerga a memória do outro.
    """

    __tablename__ = "treino_modelo"

    id: Mapped[int] = mapped_column(primary_key=True)
    situacao: Mapped[SituacaoTreino] = mapped_column(default=SituacaoTreino.EM_ANDAMENTO)
    # Nulo quando o treino veio do terminal, e não de uma pessoa na tela.
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"))
    periodo_base_id: Mapped[int] = mapped_column(ForeignKey("periodo.id"))
    semente: Mapped[int] = mapped_column(Integer)

    iniciado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    concluido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Volume de dados (RF27).
    parceiros: Mapped[int | None] = mapped_column(Integer)
    periodos: Mapped[int | None] = mapped_column(Integer)
    amostras_treino: Mapped[int | None] = mapped_column(Integer)
    amostras_validacao: Mapped[int | None] = mapped_column(Integer)
    amostras_teste: Mapped[int | None] = mapped_column(Integer)

    # Métricas no conjunto de teste, lado a lado com as referências (H42, H43, H46).
    mape_modelo: Mapped[float | None] = mapped_column()
    mape_ultimo: Mapped[float | None] = mapped_column()
    mape_media_movel: Mapped[float | None] = mapped_column()
    brier_modelo: Mapped[float | None] = mapped_column()
    brier_referencia: Mapped[float | None] = mapped_column()
    calibracao_modelo: Mapped[float | None] = mapped_column()
    calibracao_referencia: Mapped[float | None] = mapped_column()
    # O que não precisa de coluna própria: curva de calibração, épocas,
    # temperatura, duração e as taxas da referência de risco.
    detalhes: Mapped[dict | None] = mapped_column(JSONB)

    promovido: Mapped[bool | None] = mapped_column(Boolean)
    versao_em_uso: Mapped[str | None] = mapped_column(String(40))
    motivo: Mapped[str | None] = mapped_column(Text)
    pesos: Mapped[bytes | None] = mapped_column(LargeBinary)

    __table_args__ = (
        Index(
            "uq_treino_um_em_andamento",
            "situacao",
            unique=True,
            postgresql_where=text("situacao = 'EM_ANDAMENTO'"),
        ),
        CheckConstraint(
            "situacao <> 'CONCLUIDO' OR (versao_em_uso IS NOT NULL AND promovido IS NOT NULL)",
            name="ck_treino_concluido_tem_versao",
        ),
        CheckConstraint(
            "situacao <> 'FALHOU' OR motivo IS NOT NULL",
            name="ck_treino_falho_tem_motivo",
        ),
    )

    @property
    def versao(self) -> str:
        """O nome da rede treinada nesta execução."""
        return f"rede-{self.id}"


class Previsao(Base):
    __tablename__ = "previsao"

    id: Mapped[int] = mapped_column(primary_key=True)
    parceiro_id: Mapped[int] = mapped_column(ForeignKey("parceiro.id"))
    periodo_base_id: Mapped[int] = mapped_column(ForeignKey("periodo.id"))

    faturamento_previsto: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    probabilidade_queda: Mapped[float] = mapped_column()
    modelo_versao: Mapped[str] = mapped_column(String(40))
    gerada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "parceiro_id",
            "periodo_base_id",
            "modelo_versao",
            name="uq_previsao_parceiro_periodo_modelo",
        ),
        CheckConstraint(
            "probabilidade_queda >= 0 AND probabilidade_queda <= 1",
            name="ck_previsao_probabilidade",
        ),
        # A leitura é sempre "as previsões desta versão sobre este período": a
        # unicidade acima começa por parceiro e não atende a busca da rede toda.
        Index("ix_previsao_periodo_versao", "periodo_base_id", "modelo_versao"),
    )


class AcaoComercial(Base):
    """Tipo de ação que o otimizador pode alocar, com custo e efeito esperado."""

    __tablename__ = "acao_comercial"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(80), unique=True)
    custo_unitario: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    uplift_esperado_pct: Mapped[float] = mapped_column()
    ativa: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        CheckConstraint("custo_unitario >= 0", name="ck_acao_custo_nao_negativo"),
    )


class ExecucaoOtimizador(Base):
    """Registro de uma execução, com o modo e o tempo — é a base do benchmark (RF33, RF34)."""

    __tablename__ = "execucao_otimizador"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"))
    modo: Mapped[ModoExecucao] = mapped_column()
    parametros: Mapped[dict] = mapped_column(JSONB)

    viavel: Mapped[bool] = mapped_column(Boolean)
    restricao_violada: Mapped[str | None] = mapped_column(String(120))
    uplift_total: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    custo_total: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    tempo_ms: Mapped[int] = mapped_column(Integer)

    executada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        # RN07: ou o plano respeita todas as restrições, ou não existe plano.
        CheckConstraint(
            "(viavel AND restricao_violada IS NULL)"
            " OR (NOT viavel AND restricao_violada IS NOT NULL)",
            name="ck_execucao_inviavel_tem_motivo",
        ),
    )


class PlanoCampanha(Base):
    __tablename__ = "plano_campanha"

    id: Mapped[int] = mapped_column(primary_key=True)
    execucao_id: Mapped[int] = mapped_column(ForeignKey("execucao_otimizador.id"), unique=True)
    aplicacao_inicio: Mapped[date] = mapped_column(Date)
    aplicacao_fim: Mapped[date] = mapped_column(Date)

    itens: Mapped[list[ItemPlano]] = relationship(back_populates="plano")


class ItemPlano(Base):
    """Par (parceiro, ação) escolhido pelo otimizador. No máximo uma ação por parceiro."""

    __tablename__ = "item_plano"

    id: Mapped[int] = mapped_column(primary_key=True)
    plano_id: Mapped[int] = mapped_column(ForeignKey("plano_campanha.id"))
    parceiro_id: Mapped[int] = mapped_column(ForeignKey("parceiro.id"))
    acao_id: Mapped[int] = mapped_column(ForeignKey("acao_comercial.id"))
    uplift_esperado: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    custo: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    plano: Mapped[PlanoCampanha] = relationship(back_populates="itens")

    __table_args__ = (
        UniqueConstraint("plano_id", "parceiro_id", name="uq_item_plano_parceiro"),
    )


# --------------------------------------------------------------------------- comunicação
class Mensagem(Base):
    """Mensagem gerada por segmento, sujeita a aprovação humana.

    `texto_gerado` e `texto_final` são separados de propósito: se o Gestor
    editar antes de aprovar, o original permanece para auditoria.
    """

    __tablename__ = "mensagem"

    id: Mapped[int] = mapped_column(primary_key=True)
    parceiro_id: Mapped[int] = mapped_column(ForeignKey("parceiro.id"))
    item_plano_id: Mapped[int | None] = mapped_column(ForeignKey("item_plano.id"))

    texto_gerado: Mapped[str] = mapped_column(Text)
    texto_final: Mapped[str | None] = mapped_column(Text)
    estado: Mapped[EstadoMensagem] = mapped_column(default=EstadoMensagem.PENDENTE)

    decidida_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"))
    motivo_rejeicao: Mapped[str | None] = mapped_column(String(240))
    gerada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    decidida_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        # RN06: nenhuma mensagem sai do estado pendente sem um humano registrado.
        CheckConstraint(
            "(estado = 'PENDENTE' AND decidida_por_id IS NULL AND decidida_em IS NULL)"
            " OR (estado <> 'PENDENTE' AND decidida_por_id IS NOT NULL"
            " AND decidida_em IS NOT NULL)",
            name="ck_mensagem_decisao_tem_autor",
        ),
        Index("ix_mensagem_estado", "estado"),
    )
