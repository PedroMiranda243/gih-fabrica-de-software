"""A trilha de auditoria como se lê: o rótulo, o resumo e o recorte (RF08, RF49, RF50 · H89, H90).

`app/auditoria.py` **grava**; este módulo **lê**. A trilha guarda o código da
ação e os parâmetros crus, que é o que serve para investigar; a tela precisa de
uma frase. O rótulo e o resumo moram aqui, no servidor, e não na interface: são
a mesma frase na tela, no CSV e no histórico do parceiro, e um teste confere que
toda ação tem rótulo — ação nova sem frase reprova, em vez de aparecer na tela
como `MENSAGENS_FALHARAM`.

**O resumo nunca inventa.** Ele só reescreve o que está em `detalhes`; chave que
falta some da frase, e ação sem formatador cai no rótulo. Registro antigo, de
antes de um campo existir, continua legível.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta

from sqlalchemy import Select, String, cast, or_, select

from app.auditoria import Acao
from app.modelos import Auditoria, Usuario

ROTULOS: dict[Acao, str] = {
    Acao.LOGIN_SUCESSO: "Entrada no sistema",
    Acao.LOGIN_FALHA: "Entrada recusada",
    Acao.LOGIN_BLOQUEADO: "Login bloqueado",
    Acao.LOGOUT: "Saída do sistema",
    Acao.SENHA_ALTERADA: "Senha alterada",
    Acao.IMPORTACAO_REALIZADA: "Importação de relatório",
    Acao.IMPORTACAO_SUBSTITUIDA: "Importação que substituiu um período",
    Acao.PARCEIRO_CRIADO: "Parceiro cadastrado",
    Acao.PARCEIRO_EDITADO: "Cadastro de parceiro editado",
    Acao.PARCEIRO_CLASSIFICADO: "Categoria de parceiro alterada",
    Acao.PARCEIRO_DESATIVADO: "Parceiro desativado",
    Acao.PARCEIRO_REATIVADO: "Parceiro reativado",
    Acao.PARCEIRO_EXCLUIDO: "Parceiro excluído",
    Acao.CATEGORIA_CRIADA: "Categoria criada",
    Acao.SEGMENTACAO_CONFIGURADA: "Limiares da segmentação alterados",
    Acao.USUARIO_CRIADO: "Usuário criado",
    Acao.USUARIO_EDITADO: "Usuário editado",
    Acao.USUARIO_DESATIVADO: "Usuário desativado",
    Acao.USUARIO_REATIVADO: "Usuário reativado",
    Acao.PERFIL_ALTERADO: "Perfil de usuário alterado",
    Acao.ACESSO_NEGADO: "Acesso negado",
    Acao.MODELO_TREINADO: "Modelo treinado",
    Acao.MODELO_TREINO_FALHOU: "Treino do modelo falhou",
    Acao.ACAO_COMERCIAL_CRIADA: "Ação comercial criada",
    Acao.ACAO_COMERCIAL_EDITADA: "Ação comercial editada",
    Acao.OTIMIZACAO_EXECUTADA: "Campanha calculada",
    Acao.OTIMIZACAO_FALHOU: "Cálculo de campanha falhou",
    Acao.BENCHMARK_EXECUTADO: "Benchmark executado",
    Acao.BENCHMARK_FALHOU: "Benchmark falhou",
    Acao.MENSAGENS_GERADAS: "Mensagens geradas",
    Acao.MENSAGENS_FALHARAM: "Geração de mensagens falhou",
    Acao.MENSAGEM_APROVADA: "Mensagem aprovada",
    Acao.MENSAGEM_EDITADA: "Mensagem editada",
    Acao.MENSAGEM_REJEITADA: "Mensagem rejeitada",
}

# As ações que contam a história de um cadastro de parceiro (RF50). As
# mensagens e a campanha do parceiro têm telas próprias, e não entram aqui.
DO_CADASTRO_DO_PARCEIRO = (
    Acao.PARCEIRO_CRIADO,
    Acao.PARCEIRO_EDITADO,
    Acao.PARCEIRO_CLASSIFICADO,
    Acao.PARCEIRO_DESATIVADO,
    Acao.PARCEIRO_REATIVADO,
)


def rotulo(acao: str) -> str:
    """A ação em português. Código que o enum não tem mais volta como está."""
    try:
        return ROTULOS[Acao(acao)]
    except (ValueError, KeyError):
        return acao


def _mudanca(d: dict, de: str, para: str, nome: str) -> str | None:
    if de in d and para in d and d[de] != d[para]:
        return f"{nome} de {_valor(d[de])} para {_valor(d[para])}"
    return None


def _valor(v: object) -> str:
    return "vazio" if v is None or v == "" else str(v)


# Os nomes dos campos como a tela os chama; o que não está aqui sai como foi gravado.
_NOMES = {
    "top_n": "Top N",
    "periodos_tendencia": "períodos da tendência",
    "periodos_novato": "períodos de recém-chegado",
    "nome": "nome",
    "custo_unitario": "custo",
    "efeito_crescimento": "efeito de crescimento",
    "efeito_retencao": "efeito de retenção",
    "ativa": "ativa",
}


def _diferencas(antes: dict, depois: dict) -> list[str]:
    return [
        f"{_NOMES.get(k, k)} de {_valor(antes.get(k))} para {_valor(v)}"
        for k, v in depois.items()
        if antes.get(k) != v
    ]


def _limiares(d: dict) -> str:
    mudou = _diferencas(d.get("anterior") or {}, d.get("novo") or {})
    return "; ".join(mudou) if mudou else "sem mudança de valor"


def _campanha(d: dict) -> str:
    partes = [f"execução {d['execucao']}"] if "execucao" in d else []
    if d.get("modo"):
        partes.append(f"modo {d['modo']}")
    if d.get("viavel") is True:
        partes.append(f"plano com custo de R$ {d.get('custo_total')}")
    elif d.get("viavel") is False:
        partes.append(f"sem plano viável ({d.get('restricao_violada')})")
    return ", ".join(partes)


def _catalogo_editado(d: dict) -> str:
    antes, depois = d.get("antes") or {}, d.get("depois") or {}
    mudou = _diferencas(antes, depois)
    nome = depois.get("nome") or antes.get("nome") or ""
    return f"{nome}: {'; '.join(mudou)}" if mudou else nome


def _categoria_trocada(d: dict) -> str:
    """De que categoria para qual, pelo nome que tinham na hora.

    Registro de antes da H90 só tem os identificadores, e identificador não se
    lê: a frase fica vazia, e o que foi gravado continua na linha da auditoria.
    """
    if "de_nome" not in d and "para_nome" not in d:
        return ""
    de, para = (d.get(k) or "sem categoria" for k in ("de_nome", "para_nome"))
    return f"categoria de {de} para {para}"


def _cadastro_editado(d: dict) -> str:
    return "; ".join(
        m for m in (
            _mudanca(d, "nome_de", "nome", "nome"),
            _mudanca(d, "status_de", "status_para", "status"),
            # A trilha grava que o contato mudou, e não o valor: é dado de uma pessoa.
            "contato alterado" if d.get("contato_alterado") else None,
        ) if m
    )


# O que mudou num cadastro de parceiro, sem o nome dele. Cadastrar, desativar e
# reativar não têm mais o que dizer: o rótulo já é a frase inteira.
_MUDANCAS_DO_PARCEIRO = {
    Acao.PARCEIRO_CLASSIFICADO: _categoria_trocada,
    Acao.PARCEIRO_EDITADO: _cadastro_editado,
}


def _do_parceiro(acao: Acao):
    """Na trilha, que mistura todos os parceiros: o nome, e depois o que mudou."""

    def formatar(d: dict) -> str:
        mudou = _MUDANCAS_DO_PARCEIRO[acao](d) if acao in _MUDANCAS_DO_PARCEIRO else ""
        return ": ".join(p for p in (_valor(d.get("nome")), mudou) if p)

    return formatar


_FORMATADORES = {
    Acao.LOGIN_FALHA: lambda d: f"login tentado: {d['login']}" if "login" in d else "",
    Acao.LOGIN_BLOQUEADO: lambda d: f"login: {d['login']}" if "login" in d else "",
    Acao.SENHA_ALTERADA: lambda d: (
        f"{d['sessoes_encerradas']} sessão(ões) encerrada(s)" if "sessoes_encerradas" in d else ""
    ) + (", pelo terminal" if d.get("via") == "cli" else ""),
    Acao.IMPORTACAO_REALIZADA: lambda d: (
        f"período {d.get('periodo')}: {d.get('gravados')} registro(s) gravado(s), "
        f"{d.get('rejeitados')} rejeitado(s), {d.get('parceiros_criados')} parceiro(s) novo(s)"
    ),
    Acao.IMPORTACAO_SUBSTITUIDA: lambda d: (
        f"período {d.get('periodo')}: {d.get('gravados')} registro(s) gravado(s) no lugar de "
        f"{d.get('metricas_apagadas')} apagado(s)"
    ),
    Acao.PARCEIRO_CRIADO: _do_parceiro(Acao.PARCEIRO_CRIADO),
    Acao.PARCEIRO_EXCLUIDO: _do_parceiro(Acao.PARCEIRO_EXCLUIDO),
    Acao.PARCEIRO_DESATIVADO: _do_parceiro(Acao.PARCEIRO_DESATIVADO),
    Acao.PARCEIRO_REATIVADO: _do_parceiro(Acao.PARCEIRO_REATIVADO),
    Acao.PARCEIRO_CLASSIFICADO: _do_parceiro(Acao.PARCEIRO_CLASSIFICADO),
    Acao.PARCEIRO_EDITADO: _do_parceiro(Acao.PARCEIRO_EDITADO),
    Acao.CATEGORIA_CRIADA: lambda d: _valor(d.get("nome")),
    Acao.SEGMENTACAO_CONFIGURADA: _limiares,
    Acao.USUARIO_CRIADO: lambda d: f"{d.get('login')}, perfil {d.get('perfil')}",
    Acao.USUARIO_EDITADO: lambda d: ": ".join(
        p for p in (_valor(d.get("login")), _mudanca(d, "nome_de", "nome_para", "nome")) if p
    ),
    Acao.USUARIO_DESATIVADO: lambda d: _valor(d.get("login")),
    Acao.USUARIO_REATIVADO: lambda d: _valor(d.get("login")),
    Acao.PERFIL_ALTERADO: lambda d: f"{d.get('login')}: de {d.get('de')} para {d.get('para')}",
    Acao.ACESSO_NEGADO: lambda d: f"{d.get('metodo')} {d.get('caminho')}, perfil {d.get('perfil')}",
    Acao.MODELO_TREINADO: lambda d: (
        f"treino {d.get('treino')}: versão em uso {d.get('versao_em_uso')}"
        + ("" if d.get("promovido") else ", a anterior foi mantida")
    ),
    Acao.MODELO_TREINO_FALHOU: lambda d: f"treino {d.get('treino')}: {d.get('motivo')}",
    Acao.ACAO_COMERCIAL_CRIADA: lambda d: _valor(d.get("nome")),
    Acao.ACAO_COMERCIAL_EDITADA: _catalogo_editado,
    Acao.OTIMIZACAO_EXECUTADA: _campanha,
    Acao.OTIMIZACAO_FALHOU: lambda d: f"execução {d.get('execucao')}: {d.get('motivo')}",
    Acao.BENCHMARK_EXECUTADO: lambda d: (
        f"execução {d.get('execucao')}: {(d.get('parametros') or {}).get('parceiros')} parceiros"
    ),
    Acao.BENCHMARK_FALHOU: lambda d: f"execução {d.get('execucao')}: {d.get('motivo')}",
    Acao.MENSAGENS_GERADAS: lambda d: f"lote {d['lote']}" if "lote" in d else "",
    Acao.MENSAGENS_FALHARAM: lambda d: f"lote {d.get('lote')}: {d.get('motivo')}",
    Acao.MENSAGEM_APROVADA: lambda d: f"mensagem {d.get('mensagem')}"
    + (", em lote" if d.get("em_lote") else "")
    + (", depois de editada" if d.get("editada") else ""),
    Acao.MENSAGEM_EDITADA: lambda d: f"mensagem {d.get('mensagem')}",
    Acao.MENSAGEM_REJEITADA: lambda d: f"mensagem {d.get('mensagem')}: {d.get('motivo')}",
}


def _frase(formatadores: dict, acao: str, detalhes: dict | None) -> str:
    try:
        formatador = formatadores.get(Acao(acao))
    except ValueError:
        return ""
    if formatador is None or not detalhes:
        return ""
    try:
        return formatador(detalhes).strip(" :,")
    except (KeyError, TypeError, AttributeError):
        # Registro antigo, com outro formato: o detalhe cru continua na tela.
        return ""


def resumo(acao: str, detalhes: dict | None) -> str:
    """O que aconteceu, numa frase, a partir do que a trilha gravou."""
    return _frase(_FORMATADORES, acao, detalhes)


def mudanca_no_cadastro(acao: str, detalhes: dict | None) -> str:
    """O que mudou no cadastro de um parceiro, sem o nome dele (RF50).

    É a frase do histórico que fica na página do próprio parceiro: lá o nome é o
    título, e repeti-lo em cada linha esconderia o que mudou.
    """
    return _frase(_MUDANCAS_DO_PARCEIRO, acao, detalhes)


# ------------------------------------------------------------ o recorte
def inicio_do_dia(dia: date) -> datetime:
    """Meia-noite daquele dia **no fuso do servidor**.

    A coluna é `timestamptz`, então comparar com data ingênua levanta TypeError —
    mas o detalhe que importa é outro: usar UTC aqui faz o filtro "hoje" perder
    o que acabou de acontecer. Às 23h no horário de Brasília já é o dia seguinte
    em UTC, e o registro cai fora do intervalo que o usuário pediu. O dia é o do
    relógio de quem consulta, não o do meridiano de Greenwich.

    Isso torna o resultado dependente do `TZ` do servidor — que por isso está
    declarado no `docker-compose.yml` e no `.env.example`, e não deixado ao
    padrão do contêiner, que é UTC.
    """
    return datetime.combine(dia, time.min).astimezone()


def condicoes(
    *,
    autor: int | None = None,
    acao: Acao | None = None,
    de: date | None = None,
    ate: date | None = None,
    busca: str | None = None,
) -> list:
    """Os filtros da trilha, os mesmos para a lista, o CSV e o relatório."""
    filtros = []
    if autor is not None:
        filtros.append(Auditoria.usuario_id == autor)
    if acao is not None:
        filtros.append(Auditoria.acao == str(acao))
    if de is not None:
        filtros.append(Auditoria.ocorrido_em >= inicio_do_dia(de))
    if ate is not None:
        # Fim do dia, não início: quem filtra "até 15/09" espera o dia 15
        # inteiro. Comparar com o início excluiria tudo o que aconteceu nele.
        filtros.append(Auditoria.ocorrido_em < inicio_do_dia(ate + timedelta(days=1)))
    termo = (busca or "").strip()
    if termo:
        # No que foi gravado e em quem fez: o nome de um parceiro, um login.
        # `autoescape`: `%` e `_` digitados são texto, e não curinga.
        filtros.append(
            or_(
                cast(Auditoria.detalhes, String).icontains(termo, autoescape=True),
                Usuario.nome.icontains(termo, autoescape=True),
                Usuario.login.icontains(termo, autoescape=True),
            )
        )
    return filtros


def consulta(filtros: list) -> Select:
    """A trilha com o autor, do mais recente para o mais antigo — uma consulta só."""
    return (
        select(Auditoria, Usuario.nome, Usuario.login)
        .outerjoin(Usuario, Usuario.id == Auditoria.usuario_id)
        .where(*filtros)
        .order_by(Auditoria.ocorrido_em.desc(), Auditoria.id.desc())
    )
