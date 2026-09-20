"""Comandos de manutenção da API.

Uso:
    python -m app.cli criar-admin        # só cria se não houver nenhum administrador
    python -m app.cli criar-usuario --login pedro --nome "Pedro" --perfil GESTOR
    python -m app.cli redefinir-senha --login admin

Nos dois últimos a senha é **digitada no terminal**, nunca passada como argumento.
Com o ambiente no ar:

    docker compose exec api python -m app.cli criar-usuario --login ... --nome ...

Existe por causa do ovo e da galinha: sem usuário no banco não há como entrar, e
criar usuário exige estar autenticado como Administrador (RF03).
"""
from __future__ import annotations

import argparse
import getpass
import os
import secrets
import sys

from sqlalchemy import func, select

from app import auditoria, sessoes
from app.auditoria import Acao
from app.config import config
from app.db import Sessao
from app.esquemas import LimiaresSegmentacao, NovoUsuario
from app.modelos import ConfiguracaoSegmentacao, Perfil, Periodo, Usuario
from app.seguranca import SenhaFraca, gerar_hash, validar_forca
from app.servico_segmentacao import (
    Limiares,
    limiares_vigentes,
    reprocessar,
    reprocessar_tudo,
)


def criar_admin() -> int:
    """Cria o administrador inicial, se ainda não existir nenhum.

    Idempotente de propósito: o entrypoint chama a cada subida do container, e o
    RNF07 pede que o ambiente suba com um comando só, sem etapa manual.

    **Não há senha padrão.** O repositório é público (regra 2.1), e um
    `admin/admin` no código seria uma porta aberta em qualquer implantação que
    esquecesse de trocá-la. Sem `GIH_ADMIN_SENHA` no ambiente, sorteia uma e
    imprime — quem sobe o sistema lê no log e troca no primeiro acesso.
    """
    s = Sessao()
    try:
        ja_existe = s.scalar(
            select(func.count())
            .select_from(Usuario)
            .where(Usuario.perfil == Perfil.ADMINISTRADOR, Usuario.ativo.is_(True))
        )
        if ja_existe:
            print("Administrador já existe — nada a fazer.")
            return 0

        senha = config.admin_senha or secrets.token_urlsafe(12)
        sorteada = not config.admin_senha

        s.add(
            Usuario(
                login=config.admin_login,
                nome=config.admin_nome,
                senha_hash=gerar_hash(senha),
                perfil=Perfil.ADMINISTRADOR,
                ativo=True,
            )
        )
        s.commit()

        print(f"Administrador criado: {config.admin_login}")
        if sorteada:
            print(f"Senha sorteada: {senha}")
            print("Anote agora — ela não é gravada em lugar nenhum e não pode ser recuperada.")
        return 0
    except Exception as e:
        s.rollback()
        print(f"Falhou: {e}", file=sys.stderr)
        return 1
    finally:
        s.close()


def _ler_senha(login: str) -> str:
    """A senha nova, digitada por quem roda o comando.

    **Nunca por argumento de linha de comando.** Argumento fica no histórico do
    shell e aparece na lista de processos para qualquer usuário da máquina.
    Fora do terminal interativo (automação, CI), vem de `GIH_SENHA_NOVA`.
    """
    senha = os.environ.get("GIH_SENHA_NOVA")
    if senha:
        return senha
    if not sys.stdin.isatty():
        raise ValueError(
            "Sem terminal interativo para digitar a senha. Rode com "
            "`docker compose exec api ...` (sem -T) ou defina GIH_SENHA_NOVA."
        )
    primeira = getpass.getpass(f"Senha para {login}: ")
    if getpass.getpass("Repita a senha: ") != primeira:
        raise ValueError("As duas senhas não conferem.")
    return primeira


def criar_usuario(argumentos: list[str]) -> int:
    """Cria um usuário pelo terminal.

    Resolve o problema de quem acabou de clonar o projeto: a senha do
    administrador inicial é sorteada e só aparece no log da primeira subida, e
    importação e parceiros nem são do Administrador (UC03, UC04). Sem isto, subir
    o ambiente terminava numa tela de login sem ninguém que pudesse passar dela.

    Valida pelas **mesmas** regras da API — o esquema `NovoUsuario` e
    `validar_forca` — em vez de repetir a política aqui, onde ela divergiria.
    """
    p = argparse.ArgumentParser(prog="python -m app.cli criar-usuario")
    p.add_argument("--login", required=True)
    p.add_argument("--nome", required=True)
    # Parceiro fica de fora: exige vínculo com um parceiro, que é decisão de
    # tela de administração, não de terminal.
    p.add_argument(
        "--perfil",
        default=Perfil.GESTOR.value,
        choices=[Perfil.ADMINISTRADOR.value, Perfil.GESTOR.value, Perfil.ANALISTA.value],
    )
    a = p.parse_args(argumentos)

    try:
        senha = _ler_senha(a.login)
        dados = NovoUsuario(login=a.login, nome=a.nome, senha=senha, perfil=Perfil(a.perfil))
        validar_forca(dados.senha, dados.login)
    except (ValueError, SenhaFraca) as e:
        # `ValidationError` do Pydantic é um `ValueError`; a mensagem dele lista
        # o campo e o motivo.
        print(f"Recusado: {e}", file=sys.stderr)
        return 1

    s = Sessao()
    try:
        if s.scalar(select(Usuario).where(Usuario.login == dados.login)):
            print(
                f"Já existe o login {dados.login!r}. Para trocar a senha dele, use "
                "`redefinir-senha`.",
                file=sys.stderr,
            )
            return 1

        usuario = Usuario(
            login=dados.login,
            nome=dados.nome,
            senha_hash=gerar_hash(dados.senha),
            perfil=dados.perfil,
            ativo=True,
        )
        s.add(usuario)
        s.commit()
    finally:
        s.close()

    # Criado pelo terminal continua sendo criado: a trilha precisa responder
    # "de onde veio este usuário" mesmo quando não foi pela tela.
    auditoria.registrar(
        Acao.USUARIO_CRIADO,
        detalhes={"alvo": usuario.id, "login": dados.login, "perfil": str(dados.perfil)},
        origem="cli",
    )
    print(f"Usuário criado: {dados.login} ({dados.perfil})")
    return 0


def redefinir_senha(argumentos: list[str]) -> int:
    """Troca a senha de um usuário pelo terminal, e derruba as sessões dele.

    É o caminho de recuperação que não existia: perdida a senha sorteada do
    administrador, não havia volta. Derrubar as sessões abertas é o mesmo que a
    troca pela API faz (H19) — senha redefinida com sessão antiga ainda de pé
    não revogaria o acesso de quem motivou a troca.
    """
    p = argparse.ArgumentParser(prog="python -m app.cli redefinir-senha")
    p.add_argument("--login", required=True)
    a = p.parse_args(argumentos)

    s = Sessao()
    try:
        usuario = s.scalar(select(Usuario).where(Usuario.login == a.login))
        if usuario is None:
            print(f"Não existe o login {a.login!r}.", file=sys.stderr)
            return 1

        try:
            senha = _ler_senha(a.login)
            validar_forca(senha, a.login)
        except (ValueError, SenhaFraca) as e:
            print(f"Recusado: {e}", file=sys.stderr)
            return 1

        usuario.senha_hash = gerar_hash(senha)
        derrubadas = sessoes.revogar_do_usuario(s, usuario.id, "senha_redefinida_no_terminal")
        s.commit()
        usuario_id = usuario.id
    finally:
        s.close()

    auditoria.registrar(
        Acao.SENHA_ALTERADA,
        usuario_id=usuario_id,
        detalhes={"via": "cli", "sessoes_encerradas": derrubadas},
        origem="cli",
    )
    print(f"Senha redefinida para {a.login}. Sessões encerradas: {derrubadas}.")
    return 0


def reprocessar_segmentos(argumentos: list[str]) -> int:
    """Recalcula a segmentação de uma base já carregada (H33).

    A importação segmenta o que ela grava, mas quem já tinha dados antes desta
    história ficaria sem segmento nenhum até importar de novo — e o painel
    mostraria a distribuição vazia sem dizer por quê. Este comando fecha essa
    porta.

    Serve também para depois de mudar um limiar (H34) e para reconstruir a
    classificação quando a regra muda: como `reprocessar` é idempotente, rodar
    à toa não faz mal.
    """
    p = argparse.ArgumentParser(prog="python -m app.cli reprocessar-segmentos")
    p.add_argument(
        "--periodo-id",
        type=int,
        help="Só este período. O padrão é a base inteira.",
    )
    a = p.parse_args(argumentos)

    s = Sessao()
    try:
        if a.periodo_id is None:
            periodos = reprocessar_tudo(s)
            s.commit()
            print(f"Segmentação recalculada em {periodos} período(s).")
            return 0

        if s.get(Periodo, a.periodo_id) is None:
            print(f"Não existe o período {a.periodo_id}.", file=sys.stderr)
            return 1

        distribuicao = reprocessar(s, a.periodo_id)
        s.commit()
        print(f"Segmentação recalculada no período {a.periodo_id}:")
        for segmento, quantos in sorted(distribuicao.items(), key=lambda kv: -kv[1]):
            print(f"  {segmento.value:<14} {quantos}")
        return 0
    finally:
        s.close()


def configurar_segmentacao(argumentos: list[str]) -> int:
    """Lê ou altera os limiares da segmentação pelo terminal (RF21, H34).

    Existe porque **não há tela de administração**: sem ele, mudar um limiar
    exigiria montar a requisição à mão contra a API. Sem argumento nenhum, só
    mostra o que está em vigor.

    Valida pelo **mesmo** esquema da API, `LimiaresSegmentacao`, em vez de
    repetir os limites aqui, onde eles divergiriam na primeira mudança.
    """
    p = argparse.ArgumentParser(prog="python -m app.cli configurar-segmentacao")
    p.add_argument("--top-n", type=int, help="Quantos parceiros formam o Top N.")
    p.add_argument("--periodos-tendencia", type=int, help="Períodos consecutivos de queda ou alta.")
    p.add_argument("--periodos-novato", type=int, help="Abaixo disto, o parceiro é recém-chegado.")
    p.add_argument(
        "--reprocessar",
        action="store_true",
        help="Reclassifica a base inteira depois de alterar. Sem isto, só o painel mais recente"
        " muda na próxima importação.",
    )
    a = p.parse_args(argumentos)

    s = Sessao()
    try:
        vigentes = limiares_vigentes(s)
        mudancas = {
            campo: valor
            for campo, valor in (
                ("top_n", a.top_n),
                ("periodos_tendencia", a.periodos_tendencia),
                ("periodos_novato", a.periodos_novato),
            )
            if valor is not None
        }

        if not mudancas:
            print("Limiares em vigor:")
            print(f"  top_n                {vigentes.top_n}")
            print(f"  periodos_tendencia   {vigentes.periodos_tendencia}")
            print(f"  periodos_novato      {vigentes.periodos_novato}")
            return 0

        try:
            novos = LimiaresSegmentacao(
                top_n=mudancas.get("top_n", vigentes.top_n),
                periodos_tendencia=mudancas.get(
                    "periodos_tendencia", vigentes.periodos_tendencia
                ),
                periodos_novato=mudancas.get("periodos_novato", vigentes.periodos_novato),
            )
        except ValueError as e:
            print(f"Recusado: {e}", file=sys.stderr)
            return 1

        configuracao = s.get(ConfiguracaoSegmentacao, 1)
        if configuracao is None:
            configuracao = ConfiguracaoSegmentacao(id=1, **novos.model_dump())
            s.add(configuracao)
        else:
            for campo, valor in novos.model_dump().items():
                setattr(configuracao, campo, valor)
        s.flush()

        periodos = 0
        if a.reprocessar:
            periodos = reprocessar_tudo(s, Limiares(**novos.model_dump()))
        s.commit()
    finally:
        s.close()

    auditoria.registrar(
        Acao.SEGMENTACAO_CONFIGURADA,
        detalhes={
            "anterior": {
                "top_n": vigentes.top_n,
                "periodos_tendencia": vigentes.periodos_tendencia,
                "periodos_novato": vigentes.periodos_novato,
            },
            "novo": novos.model_dump(),
            "via": "cli",
            "periodos": periodos,
        },
        origem="cli",
    )

    print("Limiares atualizados:")
    for campo, valor in novos.model_dump().items():
        anterior = getattr(vigentes, campo)
        marca = "" if anterior == valor else f"  (era {anterior})"
        print(f"  {campo:<20} {valor}{marca}")
    if a.reprocessar:
        print(f"Segmentação recalculada em {periodos} período(s).")
    else:
        print(
            "Os períodos já classificados mantêm a classificação antiga. "
            "Use --reprocessar, ou o comando reprocessar-segmentos."
        )
    return 0


# Cada comando recebe o resto da linha de comando. `criar-admin` não tem
# argumentos e é chamado pelo entrypoint a cada subida.
COMANDOS = {
    "criar-admin": lambda _argumentos: criar_admin(),
    "criar-usuario": criar_usuario,
    "redefinir-senha": redefinir_senha,
    "reprocessar-segmentos": reprocessar_segmentos,
    "configurar-segmentacao": configurar_segmentacao,
}


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in COMANDOS:
        print(f"Comandos: {', '.join(COMANDOS)}", file=sys.stderr)
        return 2
    return COMANDOS[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    raise SystemExit(main())
