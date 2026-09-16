"""Comandos de manutenção da API.

Uso:
    python -m app.cli criar-admin        # só cria se não houver nenhum administrador

Existe por causa do ovo e da galinha: sem usuário no banco não há como entrar, e
criar usuário exige estar autenticado como Administrador (RF03).
"""
from __future__ import annotations

import secrets
import sys

from sqlalchemy import func, select

from app.config import config
from app.db import Sessao
from app.modelos import Perfil, Usuario
from app.seguranca import gerar_hash


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


COMANDOS = {"criar-admin": criar_admin}


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in COMANDOS:
        print(f"Comandos: {', '.join(COMANDOS)}", file=sys.stderr)
        return 2
    return COMANDOS[sys.argv[1]]()


if __name__ == "__main__":
    raise SystemExit(main())
