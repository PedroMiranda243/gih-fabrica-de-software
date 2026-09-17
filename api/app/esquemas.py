"""Contrato da API: o que entra e o que sai.

Estes modelos **são** o contrato entre `api/` e `web/` (ver CLAUDE.md, seção 5).
O frontend codifica contra eles, não contra a implementação — e é daqui que sai
a especificação publicada em `/api/docs`.

Regra que vale para o arquivo inteiro: nenhuma resposta carrega `senha_hash`,
`token_hash` ou qualquer coisa parecida. Por isso as respostas são declaradas
campo a campo, em vez de serializarem a entidade inteira.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.config import config
from app.modelos import OrigemCategoria, OrigemImportacao, Perfil, StatusComercial

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


class SessaoResposta(BaseModel):
    usuario: UsuarioResposta
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


class ImportacaoResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    periodo: PeriodoResposta
    origem: OrigemImportacao
    total_gravado: int
    total_rejeitado: int
    enviado_em: datetime


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


class LinhaRanking(BaseModel):
    """Um parceiro no ranking do período (RF18, H31)."""

    parceiro_id: int
    nome: str
    categoria: str | None
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
