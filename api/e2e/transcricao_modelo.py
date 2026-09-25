"""Transcreve o módulo de previsão integrado ao banco, para servir de evidência.

A quinta entrega da disciplina pede o segundo módulo **integrado ao banco**:
armazenar, consultar e atualizar dados, com a persistência demonstrada. Aqui o
fluxo do módulo de previsão roda contra a API no ar, e cada troca vai para a
transcrição com o que se esperava dela:

1. **consultar** — a versão em uso, antes de tudo;
2. **armazenar** — um gestor dispara o treino; a API grava o treino em
   andamento, roda fora da requisição e grava o resultado na mesma linha;
3. **consultar** — o histórico de treinos e a previsão no cadastro do parceiro;
4. **atualizar** — um segundo treino muda a versão em uso, e a previsão do
   parceiro passa a sair dela;
5. **no banco** — as linhas gravadas, lidas por SQL de leitura: o treino com as
   métricas, e as previsões das duas versões sobre o mesmo período (UC07-A2).

Que o gravado sobrevive a desligar e religar a aplicação é o `persistencia.py`.

Como as outras transcrições, não deixa resíduo: no fim, os treinos da execução
saem do banco com as previsões deles, e a versão em uso volta a ser a de antes
(ver `e2e/limpeza.py`).

Uso, da pasta `api/`:
    GIH_ADMIN_SENHA=... python e2e/transcricao_modelo.py \\
        > ../docs/entrega/evidencias/sprint05/modelo.txt
"""
from __future__ import annotations

import argparse
import os
import secrets
import sys
import time

import httpx
from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from e2e.limpeza import url_do_banco  # noqa: E402
from e2e.persistencia import api_responde  # noqa: E402
from e2e.transcricao import LARGURA, desfazer, titulo, troca  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SENHA = "modelo-de-evidencia"
ESPERA_MAXIMA = 180


class Conferencias:
    def __init__(self) -> None:
        self.itens: list[tuple[str, bool]] = []

    def __call__(self, descricao: str, ok: bool) -> bool:
        self.itens.append((descricao, ok))
        print(f"  {'ok   ' if ok else 'FALHA'} {descricao}")
        return ok


def acompanhar(c: httpx.Client, treino_id: int, *, calado: bool = False) -> dict:
    """Consulta o treino até ele sair de EM_ANDAMENTO, como a tela faz."""
    inicio = time.monotonic()
    consultas = 0
    while True:
        treino = c.get(f"/api/modelo/treinos/{treino_id}").json()
        consultas += 1
        if treino["situacao"] != "EM_ANDAMENTO":
            if not calado:
                print(f"\n  ... {consultas} consulta(s) a GET /api/modelo/treinos/{treino_id} "
                      f"até a situação mudar ({time.monotonic() - inicio:.1f} s)")
            return treino
        if time.monotonic() - inicio > ESPERA_MAXIMA:
            raise RuntimeError(f"O treino {treino_id} não terminou em {ESPERA_MAXIMA} s.")
        time.sleep(1)


def no_banco(consulta: str, parametros: dict) -> list[tuple]:
    """SQL de leitura contra o banco da API — só `SELECT`."""
    assert consulta.lstrip().upper().startswith("SELECT")
    motor = create_engine(url_do_banco())
    try:
        with motor.connect() as conexao:
            return list(conexao.execute(text(consulta), parametros))
    finally:
        motor.dispose()


def mostrar_sql(consulta: str, linhas: list[tuple], cabecalho: tuple[str, ...]) -> None:
    print("\n$ SQL, só leitura, no banco da API")
    for linha in consulta.strip().splitlines():
        print(f"  > {linha.strip()}")
    larguras = [max(len(str(v)) for v in coluna) for coluna in zip(cabecalho, *linhas, strict=True)]
    print("  < " + " | ".join(str(h).ljust(w) for h, w in zip(cabecalho, larguras, strict=True)))
    print("  < " + "-+-".join("-" * w for w in larguras))
    for linha in linhas:
        print("  < " + " | ".join(str(v).ljust(w) for v, w in zip(linha, larguras, strict=True)))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--url", default=os.environ.get("GIH_URL", "http://localhost:8000"))
    p.add_argument("--login", default=os.environ.get("GIH_ADMIN_LOGIN", "admin"))
    p.add_argument("--senha", default=os.environ.get("GIH_ADMIN_SENHA", ""))
    a = p.parse_args()

    if not a.senha:
        print("Informe a senha do administrador com --senha ou GIH_ADMIN_SENHA.", file=sys.stderr)
        return 2
    if not api_responde(a.url):
        print(f"A API não responde em {a.url}. Suba com: docker compose up -d", file=sys.stderr)
        return 2

    marca = f"t{secrets.randbelow(100000):05d}"
    confere = Conferencias()
    print(f"Módulo de previsão integrado ao banco · {a.url}")
    print("Dados sintéticos; nenhum nome real de empresa ou pessoa.")

    with httpx.Client(base_url=a.url, timeout=30) as admin:
        if admin.post("/api/sessao", json={"login": a.login, "senha": a.senha}).status_code != 201:
            print("Não consegui autenticar como administrador.", file=sys.stderr)
            return 2
        versao_antes = admin.get("/api/modelo").json().get("versao_em_uso")
        try:
            transcrever(a.url, admin, marca, confere)
        finally:
            limpo = desfazer(admin, marca)
        titulo("Depois da limpeza")
        versao = troca(admin, "GET", "/api/modelo").json().get("versao_em_uso")
        confere("a versão em uso voltou a ser a de antes da transcrição", versao == versao_antes)

    passaram = sum(ok for _, ok in confere.itens)
    print(f"\n{'=' * LARGURA}")
    print(f"Resultado: {passaram} de {len(confere.itens)} conferências passaram.")
    return 0 if limpo and passaram == len(confere.itens) else 1


def transcrever(url: str, admin: httpx.Client, marca: str, confere: Conferencias) -> None:
    gestor, analista = f"{marca}.gestor", f"{marca}.analista"
    titulo("Preparação — um gestor, que treina (UC07), e um analista, que lê (RF28)")
    for login, perfil in ((gestor, "GESTOR"), (analista, "ANALISTA")):
        troca(admin, "POST", "/api/usuarios", {
            "login": login, "nome": f"{perfil.title()} da Evidência", "senha": SENHA,
            "perfil": perfil,
        })

    with httpx.Client(base_url=url, timeout=30) as g, httpx.Client(base_url=url, timeout=30) as an:
        g.post("/api/sessao", json={"login": gestor, "senha": SENHA})
        an.post("/api/sessao", json={"login": analista, "senha": SENHA})

        # ------------------------------------------------------------------ 1
        titulo("[1/5] Consultar — a versão em uso e se dá para treinar")
        estado = troca(g, "GET", "/api/modelo").json()
        confere("a API diz se dá para treinar, e o mínimo da RN09",
                "pode_treinar" in estado and estado["periodos_minimos"] == 8)

        # ------------------------------------------------------------------ 2
        titulo("[2/5] Armazenar — o gestor dispara o treino")
        print("\nA requisição devolve na hora, com o treino gravado em andamento; o treino")
        print("roda fora dela (ADR-010):")
        pedido = troca(g, "POST", "/api/modelo/treinos")
        confere("o treino é aceito e gravado em andamento (202)",
                pedido.status_code == 202 and pedido.json()["situacao"] == "EM_ANDAMENTO")
        primeiro = acompanhar(g, pedido.json()["id"])
        print("\nO registro gravado, lido de volta:")
        troca(g, "GET", f"/api/modelo/treinos/{primeiro['id']}")
        confere("o treino terminou e registrou data, autor, volume e métricas (RF27)",
                primeiro["situacao"] == "CONCLUIDO" and primeiro["concluido_em"] is not None
                and primeiro["autor"] == "Gestor da Evidência"
                and primeiro["volume"]["amostras_teste"] > 0
                and primeiro["metricas"]["mape_modelo"] is not None)
        confere("a versão em uso é a que venceu as referências, ou a anterior com o motivo (A1)",
                (primeiro["promovido"] and primeiro["versao_em_uso"] == primeiro["versao"])
                or (not primeiro["promovido"] and bool(primeiro["motivo"])))

        # ------------------------------------------------------------------ 3
        titulo("[3/5] Consultar — o histórico de treinos e a previsão no cadastro")
        troca(g, "GET", "/api/modelo/treinos?tamanho=3")
        maior = an.get("/api/parceiros", params={
            "tamanho": 1, "ordenar_por": "faturamento", "descendente": True,
        }).json()["itens"][0]
        print(f"\nO analista abre o cadastro de {maior['nome']}, o maior do período mais recente:")
        previsao = troca(an, "GET", f"/api/parceiros/{maior['id']}/previsao").json()
        confere("a previsão do parceiro sai da versão em uso, com a base",
                previsao["disponivel"] and previsao["modelo_versao"] == primeiro["versao_em_uso"]
                and previsao["periodo_base"] is not None)

        # ------------------------------------------------------------------ 4
        titulo("[4/5] Atualizar — um novo treino muda a versão em uso")
        segundo = acompanhar(g, troca(g, "POST", "/api/modelo/treinos").json()["id"])
        estado = troca(g, "GET", "/api/modelo").json()
        confere("o último treino é o novo, e a tela sabe qual versão está valendo",
                estado["ultimo_treino"]["id"] == segundo["id"]
                and estado["versao_em_uso"] == segundo["versao_em_uso"])
        print(f"\nO cadastro de {maior['nome']}, de novo:")
        depois = troca(an, "GET", f"/api/parceiros/{maior['id']}/previsao").json()
        confere("a previsão do parceiro passou a sair da versão nova",
                depois["modelo_versao"] == segundo["versao_em_uso"])

        # ------------------------------------------------------------------ 5
        titulo("[5/5] No banco — o que ficou gravado")
        ids = (primeiro["id"], segundo["id"])
        consulta = """
            SELECT id, situacao, parceiros, periodos, amostras_teste,
                   round(mape_modelo::numeric, 4), round(brier_modelo::numeric, 4),
                   promovido, versao_em_uso, octet_length(pesos)
              FROM treino_modelo WHERE id IN (:a, :b) ORDER BY id
        """
        linhas = no_banco(consulta, {"a": ids[0], "b": ids[1]})
        mostrar_sql(consulta, linhas, ("id", "situacao", "parceiros", "periodos", "teste",
                                       "mape", "brier", "promovido", "versao_em_uso", "bytes"))
        confere("os dois treinos estão gravados, com os pesos na própria linha (ADR-010)",
                len(linhas) == 2 and all(linha[-1] and linha[-1] > 0 for linha in linhas))

        consulta = """
            SELECT modelo_versao, periodo_base_id, count(*)
              FROM previsao WHERE modelo_versao IN (:a, :b)
             GROUP BY modelo_versao, periodo_base_id ORDER BY modelo_versao
        """
        versoes = {primeiro["versao_em_uso"], segundo["versao_em_uso"]}
        a, b = sorted(versoes) if len(versoes) == 2 else (next(iter(versoes)),) * 2
        linhas = no_banco(consulta, {"a": a, "b": b})
        mostrar_sql(consulta, linhas, ("modelo_versao", "periodo_base_id", "previsoes"))
        confere("as previsões das versões coexistem no banco sobre o mesmo período (UC07-A2)",
                len(linhas) == len(versoes) and len({linha[1] for linha in linhas}) == 1)

        # O treino roda em segundo plano; a limpeza não pode apagar um que ainda
        # esteja gravando.
        for t in ids:
            acompanhar(g, t, calado=True)


if __name__ == "__main__":
    raise SystemExit(main())
