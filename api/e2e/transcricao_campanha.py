"""Transcreve o módulo de campanha integrado ao banco e aos outros módulos, como evidência.

A sexta entrega da disciplina pede o terceiro módulo implementado e a
integração entre os módulos. Aqui o fluxo da campanha roda contra a API no ar,
e cada troca vai para a transcrição com o que se esperava dela:

1. **consultar** — com o que a campanha vai trabalhar: a versão do modelo em
   uso, o período-base, quem entra e quem fica fora, e os modos desta
   instalação;
2. **armazenar** — um gestor calcula o plano; a API grava a execução em
   andamento, busca fora da requisição (ADR-011) e grava o plano e os itens;
3. **integração** — o plano parte da previsão do segundo módulo (RN10) e do
   ranking do primeiro (RN11), e volta para o cadastro do parceiro (H81);
4. **atualizar** — um segundo plano, com outro orçamento, passa a ser o último,
   e a comparação diz o que mudou (RF35);
5. **no banco** — as linhas gravadas, lidas por SQL de leitura.

As validações e o plano que não cabe estão no `validacoes.py`; que o plano
sobrevive a desligar e religar a aplicação, no `persistencia.py`.

Como as outras transcrições, não deixa resíduo: no fim, as execuções saem do
banco com o plano e os itens, e o histórico volta a ser o de antes (ver
`e2e/limpeza.py`).

Uso, da pasta `api/`:
    GIH_ADMIN_SENHA=... python e2e/transcricao_campanha.py \\
        > ../docs/entrega/evidencias/sprint06/campanha.txt
"""
from __future__ import annotations

import argparse
import os
import secrets
import sys
import time
from decimal import Decimal

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from e2e.persistencia import api_responde  # noqa: E402
from e2e.transcricao import LARGURA, desfazer, titulo, troca  # noqa: E402
from e2e.transcricao_modelo import Conferencias, mostrar_sql, no_banco  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SENHA = "campanha-de-evidencia"
ESPERA_MAXIMA = 240

# Os parâmetros da verificação de ponta a ponta e das capturas: cabem na base
# de demonstração, com folga para a cota da cauda longa.
PARAMETROS = {
    "orcamento": "5000.00",
    "maximo_acoes": 30,
    "cota_cauda_longa": "0.3",
    "aplicacao_inicio": "2026-10-05",
    "aplicacao_fim": "2026-10-11",
}


def acompanhar(c: httpx.Client, execucao_id: int) -> dict:
    """Consulta a execução até ela sair de EM_ANDAMENTO, como a tela faz."""
    inicio = time.monotonic()
    consultas = 0
    while True:
        execucao = c.get(f"/api/otimizacoes/{execucao_id}").json()
        consultas += 1
        if execucao["situacao"] != "EM_ANDAMENTO":
            print(f"\n  ... {consultas} consulta(s) a GET /api/otimizacoes/{execucao_id} "
                  f"até a situação mudar ({time.monotonic() - inicio:.1f} s)")
            return execucao
        if time.monotonic() - inicio > ESPERA_MAXIMA:
            raise RuntimeError(f"A execução {execucao_id} não terminou em {ESPERA_MAXIMA} s.")
        time.sleep(1)


def historico(admin: httpx.Client) -> list[int]:
    """As execuções mais recentes. O administrador vê o histórico, não a campanha (H58)."""
    return [e["id"] for e in admin.get("/api/otimizacoes?tamanho=5").json()["itens"]]


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
    print(f"Módulo de campanha integrado ao banco e aos outros módulos · {a.url}")
    print("Dados sintéticos; nenhum nome real de empresa ou pessoa.")

    with httpx.Client(base_url=a.url, timeout=30) as admin:
        if admin.post("/api/sessao", json={"login": a.login, "senha": a.senha}).status_code != 201:
            print("Não consegui autenticar como administrador.", file=sys.stderr)
            return 2
        antes = historico(admin)
        try:
            transcrever(a.url, admin, marca, confere)
        finally:
            limpo = desfazer(admin, marca)
        titulo("Depois da limpeza")
        confere("o histórico de execuções voltou a ser o de antes da transcrição",
                historico(admin) == antes)

    passaram = sum(ok for _, ok in confere.itens)
    print(f"\n{'=' * LARGURA}")
    print(f"Resultado: {passaram} de {len(confere.itens)} conferências passaram.")
    return 0 if limpo and passaram == len(confere.itens) else 1


def transcrever(url: str, admin: httpx.Client, marca: str, confere: Conferencias) -> None:
    gestor, analista = f"{marca}.gestor", f"{marca}.analista"
    titulo("Preparação — um gestor, que calcula a campanha (UC08), e um analista, que a consulta")
    for login, perfil in ((gestor, "GESTOR"), (analista, "ANALISTA")):
        troca(admin, "POST", "/api/usuarios", {
            "login": login, "nome": f"{perfil.title()} da Evidência", "senha": SENHA,
            "perfil": perfil,
        })

    with httpx.Client(base_url=url, timeout=30) as g, httpx.Client(base_url=url, timeout=30) as an:
        g.post("/api/sessao", json={"login": gestor, "senha": SENHA})
        an.post("/api/sessao", json={"login": analista, "senha": SENHA})

        # ------------------------------------------------------------------ 1
        titulo("[1/5] Consultar — com o que a campanha vai trabalhar")
        print("\nAs listas longas da resposta aparecem com os dois primeiros registros.")
        estado = troca(g, "GET", "/api/campanha", resumida=True).json()
        modelo = g.get("/api/modelo").json()
        confere("a campanha parte da versão do modelo em uso e do período das previsões (RN10)",
                estado["modelo_versao"] == modelo["versao_em_uso"]
                and estado["periodo_base"] == modelo["periodo_das_previsoes"])
        confere("quem fica fora do plano tem o motivo contado (RN11)",
                estado["elegiveis"] > 0 and estado["excluidos"] is not None)
        confere("a API diz se dá para calcular, e os modos desta instalação (RF32)",
                estado["pode_executar"] is True and len(estado["modos"]) == 3
                and any(m["disponivel"] for m in estado["modos"]))

        # ------------------------------------------------------------------ 2
        titulo("[2/5] Armazenar — o gestor calcula o plano")
        print("\nA requisição devolve na hora, com a execução gravada em andamento; a busca")
        print("roda fora dela (ADR-011):")
        pedido = troca(g, "POST", "/api/otimizacoes", PARAMETROS)
        confere("o pedido é aceito e gravado em andamento (202)",
                pedido.status_code == 202 and pedido.json()["situacao"] == "EM_ANDAMENTO")
        acompanhar(g, pedido.json()["id"])
        print("\nO registro gravado, lido de volta — com o plano, parceiro a parceiro:")
        primeiro = g.get(f"/api/otimizacoes/{pedido.json()['id']}").json()
        troca(g, "GET", f"/api/otimizacoes/{primeiro['id']}", resumida=True)
        itens = primeiro["itens"] or []
        confere("a execução terminou viável, com autor, modo, tempo e o plano (RF33)",
                primeiro["situacao"] == "CONCLUIDA" and primeiro["viavel"] is True
                and primeiro["autor"] == "Gestor da Evidência"
                and primeiro["tempo_ms"] is not None and len(itens) > 0)
        confere("o plano cabe no orçamento e no máximo de ações (RN07)",
                Decimal(primeiro["custo_total"]) <= Decimal(PARAMETROS["orcamento"])
                and len(itens) <= PARAMETROS["maximo_acoes"])
        confere("cada cota ficou entre o mínimo e o máximo dela",
                all(c["minimo"] <= c["acoes"] and (c["maximo"] is None or c["acoes"] <= c["maximo"])
                    for c in primeiro["cotas"]))
        # O ganho total é arredondado uma vez, sobre a soma; o de cada item, item
        # a item. A diferença fica em centavos, no máximo um por item.
        confere("os itens somam o custo total, e o ganho total a menos do arredondamento",
                sum(Decimal(i["custo"]) for i in itens) == Decimal(primeiro["custo_total"])
                and abs(sum(Decimal(i["ganho"]) for i in itens) - Decimal(primeiro["uplift_total"]))
                <= Decimal("0.01") * len(itens))

        # ------------------------------------------------------------------ 3
        titulo("[3/5] Integração — o plano parte da previsão e do ranking, e volta ao cadastro")
        alvo = itens[0]
        print(f"\nO analista abre o cadastro de {alvo['parceiro']}, o de maior ganho esperado no")
        print("plano. A previsão, do segundo módulo:")
        previsao = troca(an, "GET", f"/api/parceiros/{alvo['parceiro_id']}/previsao").json()
        confere("o plano saiu da previsão da versão em uso, sobre o mesmo período-base (RN10)",
                previsao["disponivel"] is True
                and previsao["modelo_versao"] == primeiro["modelo_versao"]
                and previsao["periodo_base"]["id"] == primeiro["periodo_base"]["id"])

        print("\nO risco na lista de parceiros (H80) é o da mesma previsão:")
        lista = troca(an, "GET", f"/api/parceiros?busca={alvo['parceiro']}&ordenar_por=risco",
                      resumida=True).json()
        linha = next((p for p in lista["itens"] if p["id"] == alvo["parceiro_id"]), None)
        confere("o risco da lista é a probabilidade de queda da previsão",
                linha is not None and linha["risco_queda"] is not None
                and abs(linha["risco_queda"] - previsao["probabilidade_queda"]) < 1e-9)

        print("\nE a campanha, no mesmo cadastro (H81):")
        na_campanha = troca(an, "GET", f"/api/parceiros/{alvo['parceiro_id']}/campanha").json()
        confere("o cadastro mostra a ação, o custo e o ganho que o plano reservou (H81)",
                na_campanha["no_plano"] is True
                and na_campanha["plano"]["execucao_id"] == primeiro["id"]
                and na_campanha["acao"] == alvo["acao"]
                and Decimal(na_campanha["custo"]) == Decimal(alvo["custo"])
                and Decimal(na_campanha["uplift_esperado"]) == Decimal(alvo["ganho"]))

        top_n = estado["top_n"]
        print(f"\nO ranking do painel, do primeiro módulo: os {top_n} maiores do período-base.")
        base = primeiro["periodo_base"]["id"]
        ranking = troca(an, "GET", f"/api/painel/ranking?periodo_id={base}&tamanho={top_n}",
                        resumida=True).json()["itens"]
        no_topo = {r["parceiro_id"] for r in ranking}
        na_cauda = sum(i["cauda_longa"] for i in itens)
        print(f"\n  No plano: {len(itens) - na_cauda} ações no Top {top_n}"
              f" e {na_cauda} na cauda longa.")
        confere(f"a cauda longa do plano é quem está fora do Top {top_n} do painel (RN11)",
                len(ranking) == top_n
                and all(i["cauda_longa"] == (i["parceiro_id"] not in no_topo) for i in itens))

        no_plano = {i["parceiro_id"] for i in itens}
        fora = next((r for r in ranking if r["parceiro_id"] not in no_plano), None)
        if fora is None:
            confere("um parceiro do Top N ficou fora do plano, para mostrar", False)
        else:
            print(f"\n{fora['nome']}, {fora['posicao']}º do ranking, ficou fora do plano:")
            resposta = troca(an, "GET", f"/api/parceiros/{fora['parceiro_id']}/campanha").json()
            confere("quem ficou fora aparece como fora, com o plano de referência",
                    resposta["no_plano"] is False
                    and resposta["plano"]["execucao_id"] == primeiro["id"])

        # ------------------------------------------------------------------ 4
        titulo("[4/5] Atualizar — um segundo plano, com outro orçamento, passa a ser o último")
        pedido = troca(g, "POST", "/api/otimizacoes", {**PARAMETROS, "orcamento": "8000.00"})
        segundo = acompanhar(g, pedido.json()["id"])
        print(f"  ... {len(segundo['itens'] or [])} ações · custo R$ {segundo['custo_total']}"
              f" · ganho R$ {segundo['uplift_total']}")
        confere("o segundo plano terminou viável",
                segundo["situacao"] == "CONCLUIDA" and segundo["viavel"] is True)

        print(f"\nO cadastro de {alvo['parceiro']}, de novo:")
        depois = troca(an, "GET", f"/api/parceiros/{alvo['parceiro_id']}/campanha").json()
        confere("o cadastro passa a ler o plano novo — o último concluído e viável",
                depois["plano"]["execucao_id"] == segundo["id"])

        print("\nOs dois planos lado a lado (RF35):")
        comparacao = troca(g, "GET", f"/api/otimizacoes/comparacao?a={primeiro['id']}"
                           f"&b={segundo['id']}", resumida=True).json()
        confere("a comparação diz que só o orçamento mudou, sobre as mesmas previsões",
                comparacao["parametros_diferentes"] == ["orcamento"]
                and comparacao["mesmas_previsoes"] is True)
        confere("as diferenças são do segundo plano para o primeiro",
                Decimal(comparacao["diferenca_custo"])
                == Decimal(segundo["custo_total"]) - Decimal(primeiro["custo_total"]))

        print("\nO histórico, do mais recente para o mais antigo (RF34):")
        recentes = troca(an, "GET", "/api/otimizacoes?tamanho=2", resumida=True).json()["itens"]
        confere("o histórico traz os dois planos, o novo primeiro",
                [e["id"] for e in recentes] == [segundo["id"], primeiro["id"]])

        # ------------------------------------------------------------------ 5
        titulo("[5/5] No banco — o que ficou gravado")
        ids = {"a": primeiro["id"], "b": segundo["id"]}
        consulta = """
            SELECT id, situacao, modo, viavel, custo_total, uplift_total,
                   modelo_versao, periodo_base_id
              FROM execucao_otimizador WHERE id IN (:a, :b) ORDER BY id
        """
        linhas = no_banco(consulta, ids)
        mostrar_sql(consulta, linhas, ("id", "situacao", "modo", "viavel", "custo", "ganho",
                                       "versao", "periodo"))
        confere("as duas execuções estão gravadas, com o resultado na própria linha",
                len(linhas) == 2 and all(str(linha[1]) == "CONCLUIDA" and linha[3] is True
                                         for linha in linhas))

        consulta = """
            SELECT p.execucao_id, p.aplicacao_inicio, p.aplicacao_fim,
                   count(i.id), sum(i.custo), sum(i.uplift_esperado)
              FROM plano_campanha p JOIN item_plano i ON i.plano_id = p.id
             WHERE p.execucao_id IN (:a, :b)
             GROUP BY p.id ORDER BY p.execucao_id
        """
        linhas = no_banco(consulta, ids)
        mostrar_sql(consulta, linhas, ("execucao", "inicio", "fim", "itens", "custo", "ganho"))
        gravado = {linha[0]: linha for linha in linhas}
        confere("o plano e os itens de cada execução estão gravados, com o custo total dela",
                all(e["id"] in gravado and gravado[e["id"]][3] == len(e["itens"])
                    and gravado[e["id"]][4] == Decimal(e["custo_total"])
                    for e in (primeiro, segundo)))


if __name__ == "__main__":
    raise SystemExit(main())
