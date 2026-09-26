"""Contrato da API: o que entra e o que sai.

Estes modelos **são** o contrato entre `api/` e `web/` (ver CLAUDE.md, seção 5).
O frontend codifica contra eles, não contra a implementação — e é daqui que sai
a especificação publicada em `/api/docs`.

Regra que vale para o arquivo inteiro: nenhuma resposta carrega `senha_hash`,
`token_hash` ou qualquer coisa parecida. Por isso as respostas são declaradas
campo a campo, em vez de serializarem a entidade inteira.
"""
from __future__ import annotations

import enum
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.config import config
from app.modelos import (
    ModoExecucao,
    OrigemCategoria,
    OrigemImportacao,
    Perfil,
    Segmento,
    SituacaoExecucao,
    SituacaoTreino,
    StatusComercial,
)

# Senha longa demais é trabalho de hash caro sem ganho nenhum — o Argon2 leva o
# tempo que for pedido dele. O teto é proteção de recurso (RNF15).
SENHA_MAXIMA = 200

LOGIN = Field(
    min_length=3,
    max_length=60,
    pattern=r"^[a-z0-9._-]+$",
    description="Minúsculas, dígitos, ponto, hífen e sublinhado.",
)


# --------------------------------------------------------------------- sessão
class Credenciais(BaseModel):
    login: str = Field(min_length=1, max_length=60)
    senha: str = Field(min_length=1, max_length=SENHA_MAXIMA)


class UsuarioResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    login: str
    nome: str
    perfil: Perfil
    ativo: bool
    parceiro_id: int | None
    criado_em: datetime


class UsuarioAtualResposta(UsuarioResposta):
    """Quem está autenticado, e o que o perfil dele abre.

    `telas` serve para a interface montar o menu — e **não** é controle de
    acesso: cada rota continua verificando o perfil (regra 2.5). A lista é lida
    das próprias rotas (ver `dependencias.telas_de`), para o menu nunca prometer
    uma tela que o servidor recusa.
    """

    telas: list[str]


class SessaoResposta(BaseModel):
    usuario: UsuarioAtualResposta
    expira_em: datetime


# -------------------------------------------------------------------- usuários
class _PerfilComParceiro(BaseModel):
    """Regra compartilhada: só o perfil Parceiro se vincula a um parceiro.

    O banco já garante isso por CHECK, mas violar lá vira erro 500 genérico.
    Validar aqui devolve a mensagem que explica o que fazer.
    """

    @model_validator(mode="after")
    def conferir_vinculo(self):
        perfil = getattr(self, "perfil", None)
        if perfil is None:
            return self

        parceiro_id = getattr(self, "parceiro_id", None)
        if perfil == Perfil.PARCEIRO and parceiro_id is None:
            raise ValueError("O perfil Parceiro exige um parceiro vinculado.")
        if perfil != Perfil.PARCEIRO and parceiro_id is not None:
            raise ValueError("Somente o perfil Parceiro pode ter parceiro vinculado.")
        return self


class NovoUsuario(_PerfilComParceiro):
    login: str = LOGIN
    nome: str = Field(min_length=2, max_length=120)
    senha: str = Field(min_length=1, max_length=SENHA_MAXIMA)
    perfil: Perfil
    parceiro_id: int | None = None

    @field_validator("nome")
    @classmethod
    def sem_espaco_sobrando(cls, v: str) -> str:
        return v.strip()


class EdicaoUsuario(_PerfilComParceiro):
    """Tudo opcional: o que não vier fica como está.

    `senha` não está aqui de propósito. Administrador trocar senha alheia é
    outra operação, com outra consequência para a auditoria, e não foi pedida em
    nenhuma história — a troca de senha é sempre a própria (RF07, H19).
    """

    nome: str | None = Field(default=None, min_length=2, max_length=120)
    perfil: Perfil | None = None
    parceiro_id: int | None = None
    ativo: bool | None = None

    @model_validator(mode="after")
    def algo_para_mudar(self):
        if all(
            getattr(self, campo) is None
            for campo in ("nome", "perfil", "parceiro_id", "ativo")
        ):
            raise ValueError("Informe ao menos um campo para alterar.")
        return self


class TrocaSenha(BaseModel):
    senha_atual: str = Field(min_length=1, max_length=SENHA_MAXIMA)
    senha_nova: str = Field(min_length=1, max_length=SENHA_MAXIMA)


# ------------------------------------------------------------------- auditoria
class RegistroAuditoria(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    usuario_id: int | None
    acao: str
    detalhes: dict | None
    origem: str | None
    ocorrido_em: datetime


class PaginaAuditoria(BaseModel):
    """Paginada porque a tabela cresce sem teto e a consulta não pode varrer tudo."""

    itens: list[RegistroAuditoria]
    total: int
    pagina: int
    tamanho: int


# ------------------------------------------------------------------ importação
class PedidoImportacao(BaseModel):
    """Entrada da prévia e da gravação.

    `periodo_inicio` e `periodo_fim` são **obrigatórios e sem valor padrão**
    (RF10, RN03). A explicação de por quê vai junto na resposta de erro — ver
    `app/erros.py`.
    """

    periodo_inicio: date
    periodo_fim: date
    texto: str = Field(min_length=1, max_length=config.tamanho_maximo_relatorio)
    substituir: bool = Field(
        default=False,
        description=(
            "Apaga o conteúdo anterior do período antes de gravar. "
            "O padrão é não substituir: o RF12 manda cancelar."
        ),
    )

    @model_validator(mode="after")
    def periodo_coerente(self):
        if self.periodo_fim < self.periodo_inicio:
            raise ValueError("A data final do período não pode ser anterior à inicial.")
        return self


class LinhaReconhecida(BaseModel):
    linha: int
    nome: str
    faturamento: Decimal
    pedidos: int


class LinhaRejeitadaResposta(BaseModel):
    linha: int
    conteudo: str
    motivo: str


class PeriodoResposta(BaseModel):
    """Janela de tempo de um relatório.

    O `id` é o que permite ao cliente pedir um período específico ao painel —
    sem ele, o parâmetro `periodo_id` existiria sem ninguém ter como preenchê-lo.

    Vem nulo **só** na prévia da importação, onde o período ainda não foi
    gravado: mostrar um id ali seria inventar um registro que não existe.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    data_inicio: date
    data_fim: date


class PreviaImportacao(BaseModel):
    """O que será gravado, antes de gravar (RF11, H24).

    Os rejeitados vêm com o motivo de cada um: "3 linhas rejeitadas" não permite
    corrigir nada.
    """

    periodo: PeriodoResposta
    reconhecidos: list[LinhaReconhecida]
    rejeitados: list[LinhaRejeitadaResposta]
    parceiros_novos: list[str]
    total_reconhecido: int
    total_rejeitado: int
    periodo_ja_importado: bool


class AutorResposta(BaseModel):
    """Quem trouxe o dado, no histórico.

    Só id e nome: a listagem responde "quem importou", e carregar login e perfil
    junto exporia dado de conta numa tela que não precisa dele.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str


class ImportacaoResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    periodo: PeriodoResposta
    autor: AutorResposta
    origem: OrigemImportacao
    total_gravado: int
    total_rejeitado: int
    enviado_em: datetime
    metricas_vigentes: int = Field(
        default=0,
        description=(
            "Quantas métricas desta importação continuam no banco. "
            "Zero significa que outra importação substituiu o período."
        ),
    )


class PaginaImportacoes(BaseModel):
    """Paginada pelo mesmo motivo da auditoria: a lista só cresce."""

    itens: list[ImportacaoResposta]
    total: int
    pagina: int
    tamanho: int


# ------------------------------------------------------- parceiros e categorias
class NovaCategoria(BaseModel):
    nome: str = Field(min_length=2, max_length=60)

    @field_validator("nome")
    @classmethod
    def sem_espaco_sobrando(cls, v: str) -> str:
        return v.strip()


class CategoriaResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    ativa: bool


class SugestaoCategoria(BaseModel):
    """A sugestão da RN05 para um nome — nula quando ele não aponta uma categoria só."""

    categoria: CategoriaResposta | None


class NovoParceiro(BaseModel):
    """Cadastro de parceiro (RF14).

    **`origem_categoria` não entra aqui de propósito.** Quem cadastra pela API é
    uma pessoa escolhendo a categoria, e isso é confirmação — a rota grava
    `MANUAL`. Deixar o cliente informar a origem permitiria marcar como confirmada
    uma classificação que ninguém confirmou, que é exatamente o que a RN05 impede.
    """

    nome: str = Field(min_length=2, max_length=160)
    categoria_id: int | None = None
    status: StatusComercial = StatusComercial.ATIVO
    contato: str | None = Field(default=None, max_length=120)

    @field_validator("nome", "contato")
    @classmethod
    def sem_espaco_sobrando(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class EdicaoParceiro(BaseModel):
    """Tudo opcional: o que não vier fica como está.

    `categoria_id` aceita nulo **explicitamente** para permitir desclassificar um
    parceiro. Por isso a ausência do campo e o nulo precisam ser distinguidos —
    ver `campos_informados` abaixo.
    """

    nome: str | None = Field(default=None, min_length=2, max_length=160)
    categoria_id: int | None = None
    status: StatusComercial | None = None
    contato: str | None = Field(default=None, max_length=120)
    ativo: bool | None = None

    @model_validator(mode="after")
    def algo_para_mudar(self):
        if not self.model_fields_set:
            raise ValueError("Informe ao menos um campo para alterar.")
        return self

    @property
    def campos_informados(self) -> set[str]:
        """Quais campos vieram no corpo, distinguindo ausente de nulo."""
        return self.model_fields_set


class ParceiroResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    categoria: CategoriaResposta | None
    origem_categoria: OrigemCategoria | None
    status: StatusComercial
    contato: str | None
    ativo: bool
    criado_em: datetime


class Ordenacao(enum.StrEnum):
    """Por onde a lista de parceiros pode ser ordenada (RF23).

    Enum, e não texto livre: o valor entra num `ORDER BY`, e interpolar o que
    chegar na URL é injeção. Sendo enum, o FastAPI recusa qualquer outra coisa
    antes de a consulta existir — e o Swagger ainda lista as opções.
    """

    NOME = "nome"
    FATURAMENTO = "faturamento"
    PEDIDOS = "pedidos"
    TICKET_MEDIO = "ticket_medio"
    VARIACAO = "variacao"


class DesempenhoParceiro(BaseModel):
    """O que o parceiro fez no período mais recente (RF23).

    Vem **junto da lista** porque a H36 deixa ordenar por estes valores, e
    ordenar por um número que a tela não mostra é pedir para o usuário confiar
    numa ordem que ele não consegue conferir.

    Todos nulos quando o parceiro não teve métrica no período — que é diferente
    de ter faturado zero.
    """

    segmento: Segmento | None = None
    faturamento: Decimal | None = None
    pedidos: int | None = None
    ticket_medio: Decimal | None = None
    variacao_percentual: Decimal | None = None


class ParceiroComDesempenho(ParceiroResposta):
    desempenho: DesempenhoParceiro


class PaginaParceiros(BaseModel):
    """A lista de parceiros, paginada (RF23, H36).

    Paginada porque a base chega a 10.000 (RNF04): medido antes desta história,
    devolver tudo levava 141 ms com 5.000 parceiros e 295 ms com 10.000 — a
    única consulta do painel que crescia com o tamanho da base.
    """

    itens: list[ParceiroComDesempenho]
    total: int
    pagina: int
    tamanho: int
    periodo: PeriodoResposta | None = Field(
        default=None,
        description="Período de onde vem o desempenho. Nulo quando não há nenhum importado.",
    )


class VinculoParceiro(BaseModel):
    """O que impede um parceiro de ser excluído, contado por tipo.

    Devolvido junto com a recusa do `DELETE`: dizer apenas "não é possível excluir"
    obriga o usuário a adivinhar o que apagar antes.
    """

    metricas: int
    segmentos: int
    previsoes: int
    itens_de_plano: int
    mensagens: int
    usuarios: int

    @property
    def total(self) -> int:
        return (
            self.metricas + self.segmentos + self.previsoes
            + self.itens_de_plano + self.mensagens + self.usuarios
        )


# ---------------------------------------------------------------------- painel
# Contrato do UC05. Três convenções valem para tudo o que vem abaixo, e o
# frontend depende delas:
#
#   1. `periodo` nulo significa **base vazia** (UC05, A1) — não é erro, é o
#      estado inicial de quem ainda não importou nada.
#   2. `periodo_anterior` nulo significa **período único** (UC05, A2): não há
#      contra o que comparar, e toda variação vem nula junto.
#   3. Variação nula **não** é zero. Zero é "não mudou"; nulo é "não dá para
#      dizer" — sem período anterior, ou com base anterior zerada, que tornaria
#      a divisão indefinida. Desenhar zero nesses casos seria afirmar
#      estabilidade que ninguém mediu.
class VariacaoIndicadores(BaseModel):
    """Variação percentual de cada indicador contra o período anterior (RF17)."""

    faturamento: Decimal | None
    pedidos: Decimal | None
    ticket_medio: Decimal | None
    parceiros_ativos: Decimal | None


class IndicadoresPainel(BaseModel):
    """Indicadores consolidados do período (RF17, H30).

    **Ticket médio é derivado aqui, nunca lido de coluna** (RN04): é o
    faturamento somado dividido pelos pedidos somados. Guardá-lo faria o valor
    divergir das parcelas que o originam na primeira correção de dado.

    Note que o ticket médio da rede **não** é a média dos tickets dos parceiros:
    é a razão dos totais, que é o que responde "quanto vale um pedido nesta
    rede". A média das médias daria peso igual a quem fez 3 pedidos e a quem fez
    3.000.
    """

    periodo: PeriodoResposta | None
    periodo_anterior: PeriodoResposta | None
    faturamento: Decimal
    pedidos: int
    ticket_medio: Decimal | None
    parceiros_ativos: int
    variacao: VariacaoIndicadores | None
    em_risco: ContagemSegmento | None = Field(
        default=None,
        description=(
            "Nulo quando o período não tem segmentação calculada. Zero seria "
            "mentira: diria 'ninguém em risco' onde o certo é 'ainda não sei'."
        ),
    )


class ContagemSegmento(BaseModel):
    """Quantos parceiros num segmento, e o movimento contra o período anterior.

    O delta é **absoluto**, e não percentual: "6 a mais" responde a pergunta do
    gestor melhor que "+19%", e nesta contagem o percentual esconde a escala —
    de 1 para 2 também é +100%.
    """

    total: int
    delta: int | None = Field(
        default=None,
        description="Nulo quando não há período anterior segmentado para comparar.",
    )


class LinhaRanking(BaseModel):
    """Um parceiro no ranking do período (RF18, H31)."""

    parceiro_id: int
    nome: str
    categoria: str | None
    segmento: Segmento | None = Field(
        default=None,
        description=(
            "Nulo quando a segmentação ainda não foi calculada para o período. "
            "É diferente de ESTAVEL: um diz 'não sei', o outro diz 'sem tendência'."
        ),
    )
    posicao: int
    posicao_anterior: int | None
    faturamento: Decimal
    pedidos: int
    ticket_medio: Decimal | None
    variacao_percentual: Decimal | None
    estreante: bool = Field(
        description=(
            "Não tinha métrica no período anterior. É diferente de ter caído: "
            "sem esta marca, posição anterior nula seria lida como queda."
        ),
    )


class PaginaRanking(BaseModel):
    periodo: PeriodoResposta | None
    periodo_anterior: PeriodoResposta | None
    itens: list[LinhaRanking]
    total: int
    pagina: int
    tamanho: int


class FatiaSegmento(BaseModel):
    segmento: Segmento
    total: int


class DistribuicaoSegmentos(BaseModel):
    """Quantos parceiros em cada segmento no período (RF20, H33).

    `itens` vem **vazio** quando o período não tem segmentação calculada, e não
    com seis zeros: seis zeros desenham um gráfico que afirma uma distribuição
    plana que ninguém mediu.
    """

    periodo: PeriodoResposta | None
    total: int
    itens: list[FatiaSegmento]


class MovimentoTopN(BaseModel):
    """Um parceiro que entrou ou saiu do Top N."""

    parceiro_id: int
    nome: str
    posicao: int | None = Field(
        default=None, description="Nula quando o parceiro não faturou no período."
    )
    posicao_anterior: int | None = Field(
        default=None, description="Nula quando não havia métrica no período anterior."
    )


class MobilidadeTopN(BaseModel):
    """Quem entrou e quem saiu do Top N entre dois períodos (RF22, H35, RN02).

    **Derivada do ranking, nunca do segmento armazenado.** Como Em Risco vence
    Top na precedência de RN01, um parceiro entre os N maiores mas em queda fica
    gravado como EM_RISCO — lê-lo de lá faria o painel anunciar uma saída que
    não aconteceu.

    Sem período anterior, as duas listas vêm vazias: ninguém entrou nem saiu de
    lugar nenhum quando não há de onde sair.
    """

    periodo: PeriodoResposta | None
    periodo_anterior: PeriodoResposta | None
    top_n: int
    entradas: list[MovimentoTopN]
    saidas: list[MovimentoTopN]


class LimiaresSegmentacao(BaseModel):
    """Os limiares de RN01, configuráveis sem alterar código (RF21, H34).

    Os mínimos não são preciosismo: Top 0 não tem ninguém dentro, e tendência de
    0 períodos classificaria a rede inteira como em risco **e** em ascensão ao
    mesmo tempo. O banco cobra os mesmos limites por `CHECK` — a validação aqui
    existe para a mensagem ser útil, não para ser a única.
    """

    top_n: int = Field(ge=1, le=1000, description="Quantos parceiros formam o Top N.")
    periodos_tendencia: int = Field(
        ge=1,
        le=52,
        description="Períodos consecutivos de queda (ou de alta) para caracterizar tendência.",
    )
    periodos_novato: int = Field(
        ge=1,
        le=52,
        description="Períodos de histórico abaixo dos quais o parceiro é recém-chegado.",
    )


class ConfiguracaoSegmentacaoResposta(LimiaresSegmentacao):
    atualizado_em: datetime
    atualizado_por: str | None = Field(
        default=None, description="Quem mudou por último. Nulo quando são os valores de fábrica."
    )
    periodos_reprocessados: int = Field(
        default=0,
        description=(
            "Quantos períodos foram reclassificados agora. Mudar um limiar só "
            "reprocessa o período mais recente — os anteriores mantêm a "
            "classificação antiga até o comando de terminal rodar."
        ),
    )


class PontoSerie(BaseModel):
    """Um período na série (RF19, H32).

    Os três valores vêm **nulos juntos** quando não houve medição naquele
    período. A lacuna é explícita de propósito: omitir o ponto faria o gráfico
    ligar os vizinhos com uma reta, desenhando uma tendência onde não houve
    medição nenhuma.
    """

    periodo: PeriodoResposta
    faturamento: Decimal | None
    pedidos: int | None
    ticket_medio: Decimal | None


class SerieHistorica(BaseModel):
    escopo: str = Field(description='"rede" ou "parceiro".')
    parceiro_id: int | None
    parceiro_nome: str | None
    pontos: list[PontoSerie]


# ------------------------------------------------------------ modelo preditivo
class VolumeTreino(BaseModel):
    """O volume de dados do treino (RF27)."""

    parceiros: int | None
    periodos: int | None
    amostras_treino: int | None
    amostras_validacao: int | None
    amostras_teste: int | None


class MetricasTreino(BaseModel):
    """As métricas no conjunto de teste, lado a lado com as referências.

    O MAPE vem em fração (0,098 = 9,8%), como sai do cálculo: formatar é
    trabalho da tela.
    """

    mape_modelo: float | None
    mape_ultimo: float | None
    mape_media_movel: float | None
    brier_modelo: float | None
    brier_referencia: float | None
    calibracao_modelo: float | None
    calibracao_referencia: float | None


class FaixaCalibracao(BaseModel):
    inicio: float
    fim: float
    previsto: float
    observado: float
    amostras: int


class TreinoResposta(BaseModel):
    """Um treino do modelo (RF27, UC07).

    `versao` é o nome da rede treinada nele; `versao_em_uso`, a que ficou
    valendo depois dele — a própria, se superou as referências, ou a anterior,
    com o `motivo` (UC07-A1).
    """

    id: int
    situacao: SituacaoTreino
    autor: str | None = Field(description="Nome de quem disparou. Nulo quando veio do terminal.")
    iniciado_em: datetime
    concluido_em: datetime | None
    periodo_base: PeriodoResposta
    volume: VolumeTreino
    metricas: MetricasTreino
    curva: list[FaixaCalibracao]
    segundos: float | None
    promovido: bool | None
    versao: str
    versao_em_uso: str | None
    motivo: str | None


class PaginaTreinos(BaseModel):
    itens: list[TreinoResposta]
    total: int
    pagina: int
    tamanho: int


class EstadoModelo(BaseModel):
    """O que a tela do modelo mostra ao abrir (UC07, passo 1).

    **Se dá para treinar agora é decisão da API** (regra 2.4): a tela recebe
    `pode_treinar` e o porquê, em vez de refazer a conta dos períodos.
    """

    versao_em_uso: str | None
    origem: str | None = Field(description="MODELO ou REFERENCIA.")
    treino_da_versao: TreinoResposta | None = Field(
        description="O treino que produziu a versão em uso, com as métricas dela."
    )
    ultimo_treino: TreinoResposta | None
    em_andamento: TreinoResposta | None
    periodos_na_base: int
    periodos_minimos: int
    periodo_mais_recente: PeriodoResposta | None
    periodo_das_previsoes: PeriodoResposta | None = Field(
        description="De onde partem as previsões em uso: o período-base do último treino concluído."
    )
    desatualizado: bool = Field(
        description="Há período mais novo que o das previsões em uso; um novo treino o incorpora."
    )
    pode_treinar: bool
    motivo_bloqueio: str | None


class PrevisaoParceiro(BaseModel):
    """Previsão e risco de um parceiro (RF28, H44) — ou o porquê de não haver.

    **É estimativa, e a resposta diz de onde ela vem**: o período-base, a
    versão e se saiu da rede ou da referência. Sem previsão, `motivo` e `ajuda`
    dizem por quê (RN09) — a tela não adivinha.
    """

    disponivel: bool
    faturamento_previsto: Decimal | None = None
    probabilidade_queda: float | None = None
    periodo_base: PeriodoResposta | None = None
    modelo_versao: str | None = None
    origem: str | None = Field(default=None, description="MODELO ou REFERENCIA.")
    gerada_em: datetime | None = None
    desatualizada: bool = False
    motivo: str | None = None
    ajuda: str | None = None



# --------------------------------------------------------------- campanha (UC08)
def _fracao(descricao: str, obrigatoria: bool = True):
    """Uma fração entre 0 e 1, com até 4 casas: 0,14 é 14%."""
    return Field(
        ... if obrigatoria else None,
        ge=0,
        le=1,
        max_digits=5,
        decimal_places=4,
        description=descricao,
    )


class AcaoComercialEntrada(BaseModel):
    """Uma ação do catálogo (RF29), com os dois efeitos da RN10."""

    nome: str = Field(min_length=2, max_length=80)
    custo_unitario: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    efeito_crescimento: Decimal = _fracao(
        "Fração do faturamento previsto que a ação acrescenta. 0,14 é 14%."
    )
    efeito_retencao: Decimal = _fracao(
        "Fração do faturamento que a ação preserva quando o parceiro cairia."
    )
    ativa: bool = True

    @field_validator("nome")
    @classmethod
    def nome_sem_sobra(cls, valor: str) -> str:
        return " ".join(valor.split())


class AcaoComercialEdicao(BaseModel):
    """Só os campos enviados mudam."""

    nome: str | None = Field(default=None, min_length=2, max_length=80)
    custo_unitario: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    efeito_crescimento: Decimal | None = _fracao("Fração, de 0 a 1.", obrigatoria=False)
    efeito_retencao: Decimal | None = _fracao("Fração, de 0 a 1.", obrigatoria=False)
    ativa: bool | None = None


class AcaoComercialResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    custo_unitario: Decimal
    efeito_crescimento: Decimal
    efeito_retencao: Decimal
    ativa: bool


class CotaCategoria(BaseModel):
    """Mínimo e máximo de ações para uma categoria, em fração do máximo de ações (RN11)."""

    categoria_id: int
    minimo: Decimal | None = _fracao("Fração mínima das ações da campanha.", obrigatoria=False)
    maximo: Decimal | None = _fracao("Fração máxima das ações da campanha.", obrigatoria=False)

    @model_validator(mode="after")
    def minimo_ate_o_maximo(self):
        if self.minimo is None and self.maximo is None:
            raise ValueError("Informe o mínimo, o máximo ou os dois.")
        if self.minimo is not None and self.maximo is not None and self.minimo > self.maximo:
            raise ValueError("O mínimo da categoria não pode passar do máximo.")
        return self


class ParametrosCampanha(BaseModel):
    """As restrições da campanha e o modo de execução (RF29, RF32, UC08 passos 2 a 4).

    As cotas são frações do **máximo de ações**, e viram contagem: o mínimo
    arredonda para cima e o máximo para baixo (RN11). Frações das ações que o
    plano acabasse escolhendo deixariam o plano vazio cumprir qualquer cota.
    """

    orcamento: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    maximo_acoes: int = Field(ge=1, le=10_000)
    cota_cauda_longa: Decimal | None = _fracao(
        "Fração mínima das ações para quem está fora do Top N.", obrigatoria=False
    )
    cotas_categoria: list[CotaCategoria] = Field(default_factory=list, max_length=100)
    aplicacao_inicio: date
    aplicacao_fim: date
    modo: ModoExecucao | None = Field(
        default=None,
        description="O modo pedido (RF32). Nulo: o mais rápido disponível. O usado fica na "
        "execução, que diz a troca quando o pedido não está disponível (UC08-A4).",
    )

    @model_validator(mode="after")
    def coerente(self):
        if self.aplicacao_fim < self.aplicacao_inicio:
            raise ValueError("O fim da aplicação não pode ser anterior ao início.")
        ids = [c.categoria_id for c in self.cotas_categoria]
        if len(ids) != len(set(ids)):
            raise ValueError("Cada categoria entra uma vez só nas cotas.")
        return self


class ExcluidosCampanha(BaseModel):
    """Quem ficou fora do plano, e por quê (RN11)."""

    historico_curto: int = Field(description="Ativo, com menos de 4 períodos até o período-base.")
    fora_do_periodo: int = Field(description="Ativo, sem dado no período-base das previsões.")
    sem_previsao: int = Field(description="Ativo, com histórico, sem previsão da versão em uso.")
    inativos: int
    em_prospeccao: int


class CotaEmContagem(BaseModel):
    categoria_id: int | None = Field(description="Nulo na cota da cauda longa.")
    nome: str
    acoes: int | None = Field(description="Quantas o plano deu; nulo antes de haver plano.")
    minimo: int
    maximo: int


class ItemPlanoResposta(BaseModel):
    parceiro_id: int
    parceiro: str
    segmento: Segmento | None
    categoria: str | None = Field(description="Só a categoria confirmada (RN05).")
    cauda_longa: bool
    acao_id: int
    acao: str
    custo: Decimal
    ganho: Decimal


class ExecucaoResposta(BaseModel):
    """Uma execução do otimizador (UC08, RF34).

    Concluída, ela é viável — com o plano — ou inviável, com a restrição e o
    motivo (RN07). Os itens vêm só na consulta de uma execução.
    """

    id: int
    situacao: SituacaoExecucao
    autor: str | None
    modo: ModoExecucao = Field(description="O modo em que rodou; o pedido está nos parâmetros.")
    substituicao: str | None = Field(
        default=None, description="Por que o modo pedido não foi o usado (UC08-A4)."
    )
    threads: int | None = Field(
        default=None, description="As threads que calcularam, no CPU paralelo."
    )
    iniciada_em: datetime
    concluida_em: datetime | None
    parametros: ParametrosCampanha
    periodo_base: PeriodoResposta
    modelo_versao: str
    viavel: bool | None
    restricao_violada: str | None
    motivo: str | None
    ajuda: str | None
    uplift_total: Decimal | None
    custo_total: Decimal | None
    tempo_ms: int | None
    parcial: bool | None
    acoes: int | None
    elegiveis: int | None
    excluidos: ExcluidosCampanha | None
    cotas: list[CotaEmContagem]
    folga_orcamento: Decimal | None
    folga_acoes: int | None
    ganho_guloso: Decimal | None = Field(
        description="O melhor plano guloso, para comparar: o otimizador nunca fica abaixo dele."
    )
    itens: list[ItemPlanoResposta] | None = None


class PaginaExecucoes(BaseModel):
    itens: list[ExecucaoResposta]
    total: int
    pagina: int
    tamanho: int


class CategoriaCampanha(BaseModel):
    id: int
    nome: str
    elegiveis: int = Field(description="Parceiros elegíveis com esta categoria confirmada.")


class ModoCampanha(BaseModel):
    """Um modo de execução e se ele existe nesta instalação (RF32)."""

    modo: ModoExecucao
    disponivel: bool
    motivo: str | None = Field(description="Por que não está disponível.")


class EstadoCampanha(BaseModel):
    """O que a tela de campanha mostra ao abrir (UC08, passo 1).

    **Se dá para calcular agora é decisão da API** (regra 2.4), como na tela do
    modelo: a tela recebe `pode_executar` e o porquê.
    """

    modelo_versao: str | None
    periodo_base: PeriodoResposta | None
    top_n: int
    elegiveis: int
    excluidos: ExcluidosCampanha | None
    sem_categoria: int = Field(
        description="Elegíveis sem categoria confirmada: não contam em cota."
    )
    categorias: list[CategoriaCampanha]
    acoes: list[AcaoComercialResposta]
    em_andamento: ExecucaoResposta | None
    ultima: ExecucaoResposta | None
    pode_executar: bool
    motivo_bloqueio: str | None
    modos: list[ModoCampanha] = Field(description="Do mais rápido para o mais lento.")
    modo_automatico: ModoExecucao = Field(
        description="O que roda quando o gestor não escolhe: o mais rápido disponível."
    )
