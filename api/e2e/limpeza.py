"""Desfaz o que uma execução da verificação de ponta a ponta gravou.

`verificacao.py` e `transcricao.py` rodam contra a API no ar — e, portanto,
contra o banco que a equipe usa para testar e demonstrar. Cada execução importa
relatórios em semanas no futuro, para não colidir com os dados sintéticos nem com
outra execução. Sem limpeza essas semanas se acumulavam: em 18/09/2026 o banco
de desenvolvimento tinha 30 períodos, a maioria resíduo de teste, e o painel —
que abre no período de início mais recente — abria numa semana de 2055 com um
único parceiro. Foi preciso recriar o banco para voltar a testar com dados
realistas.

**Por que a limpeza vai direto no banco, e não pela API.** A API não tem caminho
para apagar o que a verificação grava, e isso é de propósito:

- parceiro com métrica não pode ser excluído — a API responde 409 (UC04, A4),
  porque apagar histórico falsearia as séries dos períodos fechados;
- não existe rota que apague período ou importação: substituir (H25) troca o
  conteúdo do período, mas mantém o rastro de quem importou.

Uma rota "apague os dados de teste" seria, na API que vai para produção,
exatamente o atalho que essas regras existem para fechar — protegido só por uma
convenção de nome. A limpeza fica nesta ferramenta de desenvolvimento, que roda
na máquina de quem já tem acesso ao banco, como `scripts/resetar_banco.py`. Pelo
mesmo motivo ela não aparece na trilha de auditoria: não é uma ação do sistema,
é a ferramenta desmontando o próprio andaime.

**Por que não um banco separado.** A verificação existe para exercitar o
contêiner que está no ar, e é também o roteiro da demonstração. Rodá-la contra
outro banco exigiria outra instância da API, e ela deixaria de verificar a que a
equipe de fato usa.

**O que fica, de propósito.** Os usuários da execução são desativados pela API,
não apagados: a trilha de auditoria referencia o autor de cada ação, e remover a
linha deixaria o histórico apontando para o nada. Ficam também a trilha, as
sessões e as tentativas de login — são registros de segurança, e uma limpeza que
os apagasse ensinaria que eles são apagáveis.
"""
from __future__ import annotations

import re
from dataclasses import astuple, dataclass
from pathlib import Path

import httpx
from sqlalchemy import create_engine, delete, select
from sqlalchemy.engine import Connection, make_url
from sqlalchemy.exc import IntegrityError, OperationalError

from app.config import Config
from app.modelos import (
    Categoria,
    ExecucaoOtimizador,
    HistoricoSegmento,
    Importacao,
    ItemPlano,
    Metrica,
    Parceiro,
    Periodo,
    PlanoCampanha,
    Previsao,
    TreinoModelo,
    Usuario,
)

RAIZ_API = Path(__file__).resolve().parent.parent

# Conferida antes de qualquer exclusão. Uma marca vazia faria o padrão de palavra
# inteira abaixo casar com **todo** parceiro e toda categoria da base.
FORMATO_DA_MARCA = re.compile(r"(e2e|t)\d{5}")


class LimpezaRecusada(Exception):
    """Nada foi removido, e a mensagem diz o que impediu."""


@dataclass
class Contagem:
    periodos: int = 0
    importacoes: int = 0
    metricas: int = 0
    parceiros: int = 0
    categorias: int = 0
    treinos: int = 0
    otimizacoes: int = 0

    def __str__(self) -> str:
        nomes = (
            ("período", "períodos"),
            ("importação", "importações"),
            ("métrica", "métricas"),
            ("parceiro", "parceiros"),
            ("categoria", "categorias"),
            ("treino", "treinos"),
            ("otimização", "otimizações"),
        )
        partes = [
            f"{n} {um if n == 1 else varios}"
            for n, (um, varios) in zip(astuple(self), nomes, strict=True)
            if n
        ]
        return ", ".join(partes) or "nada gravado"


def url_do_banco() -> str:
    """O banco da API do `docker compose`, visto do host.

    Mesma precedência da aplicação — variável de ambiente antes do `.env` —, mas
    com os `.env` lidos pelo caminho, e não pelo diretório corrente. A
    verificação é rodada tanto da raiz quanto de `api/`, e o `Config()` padrão
    procuraria o `.env` onde estivesse, caindo, quando não achasse, na porta 5432
    — que costuma ser de outro Postgres.
    """
    return Config(_env_file=(RAIZ_API.parent / ".env", RAIZ_API / ".env")).database_url


def desativar_usuarios(admin: httpx.Client, marca: str) -> list[str]:
    """Desativa, pela API, os usuários da execução; devolve os logins achados.

    Desativar, e não apagar: a trilha de auditoria referencia o autor de cada
    ação. E pela API, porque desativar é uma ação do sistema e fica registrada.

    Achados pelo prefixo da marca, e não por uma lista montada durante a
    execução: uma exceção no meio do cadastro deixaria a lista incompleta — e um
    usuário ativo com a senha que está publicada no repositório.
    """
    achados = []
    for usuario in admin.get("/api/usuarios").json():
        if usuario["login"].startswith(f"{marca}."):
            achados.append(usuario["login"])
            if usuario["ativo"]:
                admin.patch(f'/api/usuarios/{usuario["id"]}', json={"ativo": False})
    return achados


def limpar_execucao(marca: str, url: str | None = None) -> Contagem:
    """Apaga, numa transação só, o que a execução `marca` gravou.

    A execução é reconhecida pelo que o banco registra dela, e não por ids
    guardados durante a execução — uma exceção no meio deixaria a lista
    incompleta justamente na execução que mais precisa de limpeza:

    - usuários: o login começa com `<marca>.`;
    - importações: o autor é um desses usuários;
    - períodos: os dessas importações;
    - parceiros e categorias: a marca aparece no nome como palavra inteira;
    - treinos do modelo: disparados por um desses usuários, com as previsões
      das versões que eles produziram. Sem o treino, a versão em uso volta a
      ser a do último treino de fora da execução;
    - otimizações: disparadas por um desses usuários, com o plano e os itens.

    **Recusa em vez de apagar dado alheio.** Se alguém de fora da execução
    importou num desses períodos, ou se algo fora dela aponta para um parceiro
    ou categoria marcados, nada é removido e a exceção diz o que impediu. O
    resíduo fica para alguém olhar e a verificação reprova — melhor que uma
    limpeza que acerta quase sempre.
    """
    if not FORMATO_DA_MARCA.fullmatch(marca):
        raise ValueError(f"Marca fora do formato dos scripts de verificação: {marca!r}")

    url = url or url_do_banco()
    endereco = make_url(url)
    destino = f"{endereco.host}:{endereco.port}/{endereco.database}"

    engine = create_engine(url)
    try:
        with engine.begin() as c:
            return _apagar(c, marca, destino)
    except OperationalError as e:
        raise LimpezaRecusada(
            f"o banco em {destino} (DATABASE_URL) não aceitou a conexão: {_primeira_linha(e)}"
        ) from e
    except IntegrityError as e:
        # Chave estrangeira: algo fora da execução depende do que ela criou — um
        # parceiro marcado com métrica em outro período, por exemplo. O banco
        # recusar é o que garante que a limpeza nunca leva junto dado alheio.
        raise LimpezaRecusada(
            f"algo fora da execução depende do que ela gravou: {_primeira_linha(e)}"
        ) from e
    finally:
        engine.dispose()


def _apagar(c: Connection, marca: str, destino: str) -> Contagem:
    usuarios = c.scalars(select(Usuario.id).where(Usuario.login.startswith(f"{marca}."))).all()
    if not usuarios:
        # A API acabou de criar esses usuários. Não achá-los aqui quer dizer que
        # este não é o banco dela — e responder "nada a remover" daria a limpeza
        # por feita sem ter olhado o banco certo.
        raise LimpezaRecusada(
            f"nenhum usuário da execução em {destino}: o DATABASE_URL aponta para outro "
            "banco que não o da API em uso"
        )

    importacoes = c.scalars(
        select(Importacao.id).where(Importacao.usuario_id.in_(usuarios))
    ).all()
    periodos = c.scalars(
        select(Importacao.periodo_id).where(Importacao.id.in_(importacoes)).distinct()
    ).all()

    # Conferido antes, e não deixado para a chave estrangeira: a métrica sai
    # **por período**, e num período compartilhado isso levaria junto a métrica
    # de quem não é da execução, sem nenhuma chave reclamar.
    alheio = c.execute(
        select(Periodo.data_inicio, Periodo.data_fim)
        .join(Importacao, Importacao.periodo_id == Periodo.id)
        .where(Periodo.id.in_(periodos), Importacao.usuario_id.not_in(usuarios))
        .limit(1)
    ).first()
    if alheio:
        raise LimpezaRecusada(
            f"o período de {alheio.data_inicio} a {alheio.data_fim} também tem importação "
            "de fora da execução"
        )

    # A otimização da execução sai com o plano e os itens, antes do treino e
    # dos períodos: ela aponta para o período-base das previsões que usou.
    execucoes = c.scalars(
        select(ExecucaoOtimizador.id).where(ExecucaoOtimizador.usuario_id.in_(usuarios))
    ).all()
    planos = c.scalars(
        select(PlanoCampanha.id).where(PlanoCampanha.execucao_id.in_(execucoes))
    ).all()
    c.execute(delete(ItemPlano).where(ItemPlano.plano_id.in_(planos)))
    c.execute(delete(PlanoCampanha).where(PlanoCampanha.id.in_(planos)))
    otimizacoes = c.execute(
        delete(ExecucaoOtimizador).where(ExecucaoOtimizador.id.in_(execucoes))
    ).rowcount

    # O treino da execução sai com as previsões das versões que ele produziu —
    # `rede-7` e `referencia-7` vêm do treino 7. Antes dos períodos: o treino
    # aponta para o período-base, e a chave estrangeira recusaria apagá-lo.
    treinos = c.scalars(select(TreinoModelo.id).where(TreinoModelo.usuario_id.in_(usuarios))).all()
    versoes = [f"{prefixo}{t}" for t in treinos for prefixo in ("rede-", "referencia-")]
    c.execute(delete(Previsao).where(Previsao.modelo_versao.in_(versoes)))

    # A ordem é a das chaves estrangeiras. Segmento e previsão saem com o
    # período, como em `servico_importacao._limpar_periodo`: são derivados da
    # métrica, e a coluna do período não tem o mesmo nome nas duas tabelas.
    c.execute(delete(HistoricoSegmento).where(HistoricoSegmento.periodo_id.in_(periodos)))
    c.execute(delete(Previsao).where(Previsao.periodo_base_id.in_(periodos)))

    # `\m` e `\M` marcam início e fim de palavra na expressão regular do
    # Postgres: a marca `t12345` não pode casar com o meio de outro nome.
    palavra = rf"\m{marca}\M"

    removidos = Contagem(otimizacoes=otimizacoes)
    removidos.treinos = c.execute(
        delete(TreinoModelo).where(TreinoModelo.id.in_(treinos))
    ).rowcount
    removidos.metricas = c.execute(
        delete(Metrica).where(Metrica.periodo_id.in_(periodos))
    ).rowcount
    removidos.importacoes = c.execute(
        delete(Importacao).where(Importacao.id.in_(importacoes))
    ).rowcount
    removidos.periodos = c.execute(
        delete(Periodo).where(Periodo.id.in_(periodos))
    ).rowcount
    removidos.parceiros = c.execute(
        delete(Parceiro).where(Parceiro.nome.regexp_match(palavra))
    ).rowcount
    removidos.categorias = c.execute(
        delete(Categoria).where(Categoria.nome.regexp_match(palavra))
    ).rowcount
    return removidos


def _primeira_linha(e: Exception) -> str:
    """A mensagem do banco sem o SQL e o endereço de documentação que o SQLAlchemy anexa."""
    return str(getattr(e, "orig", e)).strip().splitlines()[0]
