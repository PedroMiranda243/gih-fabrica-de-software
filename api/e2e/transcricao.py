"""Transcreve as trocas HTTP do CRUD principal, para servir de evidência.

A verificação de `verificacao.py` diz *que* funciona. Esta transcreve *o que
passa no fio*: método, endereço, corpo enviado e corpo recebido, em cada uma das
quatro operações e nas duas saídas da exclusão.

É o que a terceira entrega da disciplina pede como evidência do CRUD — e é mais
honesto que uma captura de tela, porque mostra o dado indo e voltando.

Como a verificação, não deixa resíduo: no fim, o que a transcrição gravou sai do
banco e o analista criado é desativado (ver `e2e/limpeza.py`). O aviso da
limpeza vai para a saída de erro, e não para a transcrição — ele não é parte da
evidência.

Uso:
    GIH_ADMIN_SENHA=... python e2e/transcricao.py > ../docs/entrega/evidencias/crud.txt
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
from datetime import date, timedelta

import httpx

# Mesmo arranjo da verificação: a limpeza usa o modelo de dados da API.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from e2e.limpeza import LimpezaRecusada, desativar_usuarios, limpar_execucao  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LARGURA = 78
SENHA = "transcricao-de-evidencia"


def titulo(texto: str) -> None:
    print(f"\n{'=' * LARGURA}\n{texto}\n{'=' * LARGURA}")


# Campos que nunca aparecem na transcricao, mesmo sendo descartaveis. O
# documento vai para fora, e senha em claro num anexo e o tipo de coisa que
# passa despercebida ate virar habito.
SIGILOSOS = {"senha", "senha_atual", "senha_nova"}


def mascarar(corpo: dict) -> dict:
    return {k: ("********" if k in SIGILOSOS else v) for k, v in corpo.items()}


def troca(
    cliente: httpx.Client, metodo: str, caminho: str, corpo: dict | None = None
) -> httpx.Response:
    """Faz a requisição e imprime os dois lados dela."""
    print(f"\n$ {metodo} {caminho}")
    if corpo is not None:
        visivel = json.dumps(mascarar(corpo), ensure_ascii=False, indent=2)
        for linha in visivel.splitlines():
            print(f"  > {linha}")

    resposta = cliente.request(metodo, caminho, json=corpo)
    print(f"  {resposta.status_code} {resposta.reason_phrase}")

    if resposta.status_code == 204:
        print("  < (sem conteúdo)")
        return resposta

    try:
        conteudo = resposta.json()
    except ValueError:
        print(f"  < {resposta.text[:200]}")
        return resposta

    # Listagem longa vira resumo: a evidência é o formato, não o volume.
    if isinstance(conteudo, list) and len(conteudo) > 3:
        amostra = json.dumps(conteudo[:2], ensure_ascii=False, indent=2)
        for linha in amostra.splitlines():
            print(f"  < {linha}")
        print(f"  < ... mais {len(conteudo) - 2} registros")
        return resposta

    for linha in json.dumps(conteudo, ensure_ascii=False, indent=2).splitlines():
        print(f"  < {linha}")
    return resposta


def desfazer(admin: httpx.Client, marca: str) -> bool:
    """Tira do banco o que a transcrição gravou; devolve se conseguiu."""
    if not desativar_usuarios(admin, marca):
        # O analista é quem grava tudo; sem ele, não há o que desfazer.
        return True
    try:
        removidos = limpar_execucao(marca)
    except LimpezaRecusada as e:
        print(f"Limpeza recusada, nada foi removido do banco: {e}", file=sys.stderr)
        return False
    print(f"Limpeza — removidos do banco: {removidos}; analista desativado.", file=sys.stderr)
    return True


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--url", default=os.environ.get("GIH_URL", "http://localhost:8000"))
    p.add_argument("--login", default=os.environ.get("GIH_ADMIN_LOGIN", "admin"))
    p.add_argument("--senha", default=os.environ.get("GIH_ADMIN_SENHA", ""))
    a = p.parse_args()

    if not a.senha:
        print("Informe a senha do administrador com --senha ou GIH_ADMIN_SENHA.", file=sys.stderr)
        return 2

    marca = f"t{secrets.randbelow(100000):05d}"
    print(f"Transcrição do CRUD principal · {a.url}")
    print("Dados sintéticos; nenhum nome real de empresa ou pessoa.")

    with httpx.Client(base_url=a.url, timeout=30) as admin:
        if admin.post("/api/sessao", json={"login": a.login, "senha": a.senha}).status_code != 201:
            print("Não consegui autenticar como administrador.", file=sys.stderr)
            return 2

        try:
            titulo("Preparação — um analista, que é quem gerencia parceiros (UC04)")
            analista = f"{marca}.analista"
            troca(admin, "POST", "/api/usuarios", {
                "login": analista, "nome": "Analista da Evidência",
                "senha": SENHA, "perfil": "ANALISTA",
            })
            transcrever_crud(a.url, marca, analista)
        finally:
            # No `finally`, pelo mesmo motivo da verificação: a execução
            # interrompida no meio é a que deixaria mais para trás.
            limpo = desfazer(admin, marca)

    print(f"\n{'=' * LARGURA}")
    print("Fim da transcrição.")
    return 0 if limpo else 1


def transcrever_crud(url: str, marca: str, analista: str) -> None:
    """O que o analista faz: login, as quatro operações e as duas saídas da exclusão."""
    with httpx.Client(base_url=url, timeout=30) as c:
        titulo("Login — item 2 da entrega")
        troca(c, "POST", "/api/sessao", {"login": analista, "senha": SENHA})

        titulo("CADASTRAR — item 5 da entrega")
        categoria = troca(c, "POST", "/api/categorias", {"nome": f"Categoria {marca}"})
        criado = troca(c, "POST", "/api/parceiros", {
            "nome": f"Comércio {marca}",
            "status": "PROSPECCAO",
            "contato": "contato@exemplo.test",
        })
        alvo = criado.json()["id"]

        titulo("CONSULTAR")
        troca(c, "GET", f"/api/parceiros/{alvo}")
        troca(c, "GET", f"/api/parceiros?busca={marca}")

        titulo("ATUALIZAR")
        troca(c, "PATCH", f"/api/parceiros/{alvo}", {
            "status": "ATIVO",
            "categoria_id": categoria.json()["id"],
        })

        titulo("Nome repetido é recusado — a unicidade é garantida pelo banco")
        troca(c, "POST", "/api/parceiros", {"nome": f"Comércio {marca}"})

        titulo("EXCLUIR — sem histórico, a exclusão acontece")
        troca(c, "DELETE", f"/api/parceiros/{alvo}")
        troca(c, "GET", f"/api/parceiros/{alvo}")

        titulo("EXCLUIR — com histórico, a exclusão é recusada com o motivo")
        print("\nPrimeiro uma importação, para o parceiro passar a ter faturamento:")
        inicio = date.today() + timedelta(days=365 + secrets.randbelow(2000) * 7)
        troca(c, "POST", "/api/importacoes", {
            "periodo_inicio": inicio.isoformat(),
            "periodo_fim": (inicio + timedelta(days=6)).isoformat(),
            "texto": f"Parceiro;Faturamento;Pedidos\nComércio {marca} hist;12500,40;312\n",
        })
        comhist = c.get(f"/api/parceiros?busca={marca} hist").json()
        if comhist:
            troca(c, "DELETE", f'/api/parceiros/{comhist[0]["id"]}')
            print("\n  Apagar um parceiro com faturamento importado falsearia as séries dos")
            print("  períodos já fechados. A recusa diz o que impede e aponta a desativação.")
            troca(c, "PATCH", f'/api/parceiros/{comhist[0]["id"]}', {"ativo": False})

        titulo("Controle de perfis — item 4 da entrega")
        print("\nO mesmo analista tentando a área de usuários, que é do Administrador:")
        troca(c, "GET", "/api/usuarios")


if __name__ == "__main__":
    raise SystemExit(main())
