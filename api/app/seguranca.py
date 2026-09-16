"""Primitivas de segurança: hash de senha, identificador de sessão e força mínima.

Tudo o que mexe com senha passa por aqui. Concentrar num arquivo só é o que
permite auditar a regra inteira lendo um lugar — e é o arquivo que a revisão de
Pull Request precisa ler com mais atenção.
"""
from __future__ import annotations

import hashlib
import secrets
import unicodedata

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.config import config

# Argon2id com os parâmetros padrão da biblioteca, que seguem a recomendação da
# RFC 9106. Atende o RNF09: derivação lenta e sal por usuário, gerado pela
# própria biblioteca e embutido no hash — não existe coluna de sal separada.
_hasher = PasswordHasher()

# Hash de uma senha que ninguém tem, usado para gastar o mesmo tempo quando o
# login não existe. Sem isto, responder mais rápido já denuncia que o usuário
# não está cadastrado, e o RNF11 exige respostas indistinguíveis.
_ISCA = _hasher.hash(secrets.token_urlsafe(32))


def gerar_hash(senha: str) -> str:
    return _hasher.hash(senha)


def conferir_senha(senha: str, hash_armazenado: str) -> bool:
    try:
        return _hasher.verify(hash_armazenado, senha)
    except (VerifyMismatchError, InvalidHashError):
        return False


def gastar_tempo_de_conferencia() -> None:
    """Confere contra um hash descartável, para o caminho do login inexistente.

    Parece trabalho inútil e é exatamente o ponto: o custo precisa ser o mesmo
    dos dois lados (RNF11).
    """
    conferir_senha("nao-importa", _ISCA)


# --------------------------------------------------------------- sessão
def gerar_token() -> str:
    """Identificador de sessão imprevisível.

    `secrets` usa a fonte criptográfica do sistema operacional. Nunca derive
    isto de id, de horário ou de `random` — sequência previsível é sessão
    adivinhável.
    """
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """O que vai para o banco.

    SHA-256 simples basta aqui, e Argon2 seria errado: o token já tem 256 bits
    de entropia, então não há o que proteger contra força bruta — o que se quer
    é que um vazamento da tabela não entregue sessões vivas. E a conferência
    acontece a cada requisição, onde um hash lento custaria caro.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# --------------------------------------------------------------- força da senha
class SenhaFraca(ValueError):
    """A mensagem desta exceção vai para o usuário — precisa explicar a regra."""


def validar_forca(senha: str, login: str) -> None:
    """Regra mínima de senha (H19).

    Comprimento em vez de composição obrigatória: exigir maiúscula, número e
    símbolo produz `Senha@123`, que um dicionário quebra antes de uma frase
    longa e sem símbolo nenhum.
    """
    minimo = config.senha_tamanho_minimo

    if len(senha) < minimo:
        raise SenhaFraca(f"A senha precisa ter pelo menos {minimo} caracteres.")

    normalizada = _normalizar(senha)

    if _normalizar(login) in normalizada:
        raise SenhaFraca("A senha não pode conter o login.")

    if len(set(normalizada)) < 4:
        raise SenhaFraca("A senha é repetitiva demais — use mais variedade de caracteres.")


def _normalizar(texto: str) -> str:
    """Minúsculas e sem acento, para comparar 'Joao' com 'joão'."""
    sem_acento = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in sem_acento if not unicodedata.combining(c)).casefold()
