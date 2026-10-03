"""Transcreve a comunicação, o assistente e o portal do parceiro, como evidência.

A oitava entrega da disciplina pede **todas as funcionalidades implementadas**,
com a evidência dos principais fluxos em funcionamento. Os módulos de
comunicação (UC10 e UC11), o assistente (UC12) e o portal do parceiro (UC13)
foram construídos nas Sprints 12 e 13 do projeto, e nenhuma entrega os mostrou
rodando. Aqui eles rodam contra a API no ar, do plano de campanha à mensagem
pronta para envio:

1. **gerar** — o analista gera as mensagens do plano que o gestor calculou; cada
   uma leva a ação do parceiro, e nenhum número que não esteja nos fatos (RN08);
2. **decidir** — a fila de aprovação: o analista vê e não decide; o gestor
   aprova, edita, rejeita e aprova em lote (RN06);
3. **histórico e exportação** — quem decidiu, quando, o texto final e o redigido;
   o arquivo para envio traz só as aprovadas;
4. **no banco** — as mensagens por estado, lidas por SQL de leitura;
5. **assistente** — a pergunta respondida com o número da tela e a fonte, e as
   duas abstenções: a pergunta que pede conta e a pergunta fora do catálogo;
6. **portal do parceiro** — a conta de perfil Parceiro vê o próprio histórico,
   com o mesmo faturamento que a lista de parceiros mostra ao analista.

**Com o modelo de linguagem no ar ou sem ele.** Com ele, as mensagens e as
respostas são redigidas pelo modelo, e a guarda numérica confere cada texto; sem
ele, as mensagens saem do modelo fixo e o assistente se diz indisponível — e as
duas coisas são resultado certo (ADR-013). A transcrição diz qual foi o caso, e
quantas mensagens saíram de cada redator.

Como as outras transcrições, não deixa resíduo: o plano, o lote e as mensagens
saem do banco, e os usuários são desativados (ver `e2e/limpeza.py`).

Uso, da pasta `api/`:
    GIH_ADMIN_SENHA=... python e2e/transcricao_comunicacao.py \\
        > ../docs/entrega/evidencias/sprint08/comunicacao.txt
"""
from __future__ import annotations

import argparse
import os
import secrets
import sys
import time

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.guarda_numerica import numeros_sem_origem, sentido_trocado  # noqa: E402
from e2e.persistencia import api_responde  # noqa: E402
from e2e.transcricao import LARGURA, desfazer, titulo, troca  # noqa: E402
from e2e.transcricao_campanha import acompanhar, historico  # noqa: E402
from e2e.transcricao_modelo import Conferencias, mostrar_sql, no_banco  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Um plano pequeno: oito mensagens bastam para mostrar cada decisão, e o modelo
# de linguagem leva de 2 a 4 s em cada uma.
PARAMETROS = {
    "orcamento": "1500.00",
    "maximo_acoes": 8,
    "cota_cauda_longa": "0.25",
    "aplicacao_inicio": "2026-10-05",
    "aplicacao_fim": "2026-10-11",
}
# A primeira chamada ao modelo paga o carregamento, perto de 45 s (ADR-013).
ESPERA_DO_MODELO = 240


def aguardar_lote(c: httpx.Client, lote_id: int) -> dict:
    inicio = time.monotonic()
    consultas = 0
    while True:
        lote = c.get(f"/api/mensagens/lotes/{lote_id}").json()
        consultas += 1
        if lote["situacao"] != "EM_ANDAMENTO":
            print(f"\n  ... {consultas} consulta(s) a GET /api/mensagens/lotes/{lote_id} até a "
                  f"geração terminar ({time.monotonic() - inicio:.1f} s)")
            return lote
        if time.monotonic() - inicio > 900:
            raise RuntimeError(f"O lote {lote_id} não terminou em 15 minutos.")
        time.sleep(2)


def reais(valor: object) -> str:
    return "R$ " + f"{float(valor):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def mostrar_mensagem(m: dict) -> None:
    print(f"\n  para {m['parceiro']} · {m['acao']} · redator {m['redator']} · {m['estado']}")
    print(f"    \"{m['texto']}\"")
    fatos = "; ".join(f"{f['fato']}: {f['valor']}" for f in m["fatos"])
    print(f"    fatos: {fatos}")
    if m.get("motivo_redator"):
        print(f"    por que o modelo fixo: {m['motivo_redator']}")


def perguntar(c: httpx.Client, texto: str) -> dict:
    print(f"\n$ POST /api/assistente/perguntas\n  > {texto}")
    inicio = time.monotonic()
    r = c.post("/api/assistente/perguntas", json={"texto": texto})
    corpo = r.json()
    print(f"  {r.status_code} em {time.monotonic() - inicio:.1f} s · situação "
          f"{corpo.get('situacao')} · tipo {corpo.get('tipo')} · redator {corpo.get('redator')}")
    for linha in str(corpo.get("texto", "")).splitlines():
        print(f"  < {linha}")
    if corpo.get("fonte"):
        print(f"  < fonte: {corpo['fonte']['texto']}")
    return corpo


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
    # Sorteada a cada execução, e nunca impressa: as contas são desativadas no fim.
    senha = f"evidencia-{secrets.token_urlsafe(12)}"
    confere = Conferencias()
    print(f"Comunicação, assistente e portal do parceiro · {a.url}")
    print("Dados sintéticos; nenhum nome real de empresa ou pessoa. Nenhuma senha na transcrição.")

    with httpx.Client(base_url=a.url, timeout=60) as admin:
        if admin.post("/api/sessao", json={"login": a.login, "senha": a.senha}).status_code != 201:
            print("Não consegui autenticar como administrador.", file=sys.stderr)
            return 2
        antes = historico(admin)
        try:
            transcrever(a.url, admin, marca, senha, confere)
        finally:
            limpo = desfazer(admin, marca)
        titulo("Depois da limpeza")
        confere("o histórico de execuções voltou a ser o de antes da transcrição",
                historico(admin) == antes)

    passaram = sum(ok for _, ok in confere.itens)
    print(f"\n{'=' * LARGURA}")
    print(f"Resultado: {passaram} de {len(confere.itens)} conferências passaram.")
    return 0 if limpo and passaram == len(confere.itens) else 1


def criar(admin: httpx.Client, marca: str, senha: str, apelido: str, perfil: str, **extra) -> dict:
    login = f"{marca}.{apelido}"
    r = admin.post("/api/usuarios", json={
        "login": login, "nome": f"{perfil.title()} da Evidência", "senha": senha,
        "perfil": perfil, **extra,
    })
    r.raise_for_status()
    print(f"  {r.status_code}  {login:<20} {perfil}")
    return r.json()


def transcrever(
    url: str, admin: httpx.Client, marca: str, senha: str, confere: Conferencias
) -> None:
    titulo("Preparação — um gestor, que calcula e decide, e um analista, que gera")
    criar(admin, marca, senha, "gestor", "GESTOR")
    criar(admin, marca, senha, "analista", "ANALISTA")

    with (
        httpx.Client(base_url=url, timeout=ESPERA_DO_MODELO) as g,
        httpx.Client(base_url=url, timeout=ESPERA_DO_MODELO) as an,
    ):
        g.post("/api/sessao", json={"login": f"{marca}.gestor", "senha": senha})
        an.post("/api/sessao", json={"login": f"{marca}.analista", "senha": senha})

        print("\nO gestor calcula um plano pequeno: é dele que as mensagens saem (UC08).")
        pedido = troca(g, "POST", "/api/otimizacoes", PARAMETROS)
        execucao = acompanhar(g, pedido.json()["id"])
        itens = execucao.get("itens") or []
        confere("o plano é viável, com uma ação por parceiro",
                execucao["viavel"] is True and len(itens) == len({i["parceiro_id"] for i in itens}))
        print(f"  {len(itens)} ações · custo {reais(execucao['custo_total'])} · ganho esperado "
              f"{reais(execucao['uplift_total'])}")

        lote = gerar(an, execucao, confere)
        if lote is None:
            return
        decidir(g, an, lote, confere)
        historico_e_exportacao(g, lote, confere)
        no_banco_de_dados(lote, confere)
        assistente(an, admin, marca, senha, url, confere)
    portal(url, admin, marca, senha, confere)


# ------------------------------------------------------------------ 1. gerar
def gerar(an: httpx.Client, execucao: dict, confere: Conferencias) -> dict | None:
    titulo("1. Gerar — as mensagens do plano, pelo analista (UC10, RF36, RF37)")
    estado = an.get("/api/mensagens/geracao").json()
    modelo = estado.get("assistente") or {}
    if modelo.get("disponivel"):
        print(f"\nO modelo de linguagem está no ar: {modelo.get('modelo')}. Ele redige, e a guarda")
        print("numérica confere cada texto contra os fatos; o que ela reprova sai do modelo fixo.")
    else:
        print(f"\nO modelo de linguagem não está no ar ({modelo.get('motivo')}). As mensagens saem")
        print("do modelo fixo, com os mesmos fatos: o sistema funciona igual sem ele.")

    publico = {"tipo": "PLANO", "execucao_id": execucao["id"]}
    acoes = {i["parceiro_id"]: i["acao"] for i in execucao["itens"]}
    previa = troca(an, "POST", "/api/mensagens/publico", publico, resumida=True).json()
    confere("a prévia traz os parceiros do plano, cada um com a ação dele, e não grava nada",
            {p["id"]: p["acao"] for p in previa["parceiros"]} == acoes)

    pedido = troca(an, "POST", "/api/mensagens/lotes", publico, resumida=True)
    if pedido.status_code != 202:
        confere("a geração foi aceita", False)
        return None
    lote = aguardar_lote(an, pedido.json()["id"])
    mensagens = lote.get("mensagens") or []
    pelo_modelo = lote.get("pelo_modelo") or 0
    print(f"\n  {lote['geradas']} de {lote['total']} geradas: {pelo_modelo} pelo modelo de "
          f"linguagem, {lote['geradas'] - pelo_modelo} pelo modelo fixo.")
    for m in mensagens[:3]:
        mostrar_mensagem(m)
    motivos = sorted({m["motivo_redator"] for m in mensagens if m["motivo_redator"]})
    if motivos and modelo.get("disponivel"):
        print("\n  Por que algumas saíram do modelo fixo, com o modelo no ar:")
        for motivo in motivos:
            print(f"    - {motivo}")

    confere("uma mensagem por parceiro do plano, sem falha",
            lote["situacao"] == "CONCLUIDA" and not lote["falhas"]
            and sorted(m["parceiro_id"] for m in mensagens) == sorted(acoes))
    confere("todas nascem pendentes: nenhuma está pronta para envio (RN06)",
            {m["estado"] for m in mensagens} == {"PENDENTE"})
    confere("cada mensagem leva a ação que o plano deu ao parceiro",
            all(m["acao"] == acoes[m["parceiro_id"]] for m in mensagens))
    confere("nenhum texto tem número que não veio dos fatos (RN08)",
            all(numeros_sem_origem(m["texto"], m["fatos"]) == [] for m in mensagens))
    confere("nenhum texto inverte o sentido de uma variação",
            all(sentido_trocado(m["texto"], m["fatos"]) == [] for m in mensagens))
    confere("a mensagem do modelo fixo diz por que não é do modelo",
            all(m["motivo_redator"] for m in mensagens if m["redator"] == "MODELO_FIXO"))
    return lote


# ---------------------------------------------------------------- 2. decidir
def decidir(g: httpx.Client, an: httpx.Client, lote: dict, confere: Conferencias) -> None:
    titulo("2. Decidir — a fila de aprovação (UC11, RF38, RF39, RN06)")
    ids = [m["id"] for m in lote["mensagens"]]
    fila = an.get("/api/mensagens", params={"lote_id": lote["id"], "tamanho": 100}).json()
    print(f"\nO analista abre a fila: GET /api/mensagens?lote_id={lote['id']} → "
          f"{fila['total']} pendentes.")
    print("Ele gerou as mensagens, e tenta aprovar a primeira:")
    barrado = troca(an, "POST", f"/api/mensagens/{ids[0]}/aprovacao")
    confere("o analista vê a fila e não aprova", fila["total"] == len(ids)
            and barrado.status_code == 403)

    print("\nO gestor aprova a primeira:")
    aprovada = troca(g, "POST", f"/api/mensagens/{ids[0]}/aprovacao", resumida=True).json()
    confere("a aprovação registra quem decidiu e quando",
            aprovada["estado"] == "APROVADA" and aprovada["decidida_por"] == "Gestor da Evidência"
            and bool(aprovada["decidida_em"]))

    print("\nEdita a segunda, e escreve um desconto que não está nos fatos:")
    original = lote["mensagens"][1]["texto"]
    novo = f"{original} Nesta semana, 15% de desconto na taxa."
    editada = troca(g, "POST", f"/api/mensagens/{ids[1]}/edicao", {"texto": novo},
                    resumida=True).json()
    confere("editar guarda o texto redigido e não aprova: a mensagem continua pendente",
            editada["estado"] == "PENDENTE" and editada["texto"] == novo
            and editada["texto_gerado"] == original and editada["editada"] is True)
    confere("o número que o gestor escreveu fica apontado, para ele conferir antes de aprovar",
            editada["numeros_fora_dos_fatos"] == ["15%"])
    depois = g.post(f"/api/mensagens/{ids[1]}/aprovacao").json()
    print(f"\n  ... e aprova a editada: {depois['estado']}, com o texto dele.")

    print("\nRejeita a terceira, com o motivo:")
    rejeitada = troca(g, "POST", f"/api/mensagens/{ids[2]}/rejeicao",
                      {"motivo": "O tom não serve para este parceiro."}, resumida=True).json()
    confere("a rejeição guarda o motivo", rejeitada["estado"] == "REJEITADA"
            and rejeitada["motivo_rejeicao"] == "O tom não serve para este parceiro.")

    print("\nTenta decidir de novo a que já foi aprovada:")
    de_novo = troca(g, "POST", f"/api/mensagens/{ids[0]}/rejeicao", {})
    confere("mensagem já decidida não é decidida de novo", de_novo.status_code == 409)

    print("\nE aprova três de uma vez:")
    em_lote = troca(g, "POST", "/api/mensagens/aprovacao-em-lote", {"ids": ids[3:6]},
                    resumida=True)
    restam = g.get("/api/mensagens", params={"lote_id": lote["id"]}).json()["total"]
    confere("a aprovação em lote decide as três, e o resto continua na fila",
            em_lote.status_code == 200 and restam == len(ids) - 6)
    print(f"\n  Na fila ficaram {restam} de {len(ids)}: nenhuma sai sem decisão.")


# ------------------------------------------------- 3. histórico e exportação
def historico_e_exportacao(g: httpx.Client, lote: dict, confere: Conferencias) -> None:
    titulo("3. Histórico e exportação — o que foi decidido, e o que vai para envio (RF40)")
    aprovadas = g.get("/api/mensagens",
                      params={"estado": "APROVADA", "lote_id": lote["id"], "tamanho": 100}).json()
    rejeitadas = g.get("/api/mensagens",
                       params={"estado": "REJEITADA", "lote_id": lote["id"]}).json()
    print(f"\nGET /api/mensagens?estado=APROVADA&lote_id={lote['id']} → {aprovadas['total']}")
    print(f"GET /api/mensagens?estado=REJEITADA&lote_id={lote['id']} → {rejeitadas['total']}")
    for m in aprovadas["itens"]:
        marca_de_edicao = " · editada" if m["editada"] else ""
        print(f"  {m['parceiro']:<28} aprovada por {m['decidida_por']}{marca_de_edicao}")
    for m in rejeitadas["itens"]:
        print(f"  {m['parceiro']:<28} rejeitada por {m['decidida_por']}: {m['motivo_rejeicao']}")
    confere("o histórico traz cinco aprovadas e uma rejeitada, cada uma com quem decidiu",
            aprovadas["total"] == 5 and rejeitadas["total"] == 1
            and all(m["decidida_por"] for m in aprovadas["itens"] + rejeitadas["itens"]))
    editada = next((m for m in aprovadas["itens"] if m["editada"]), None)
    confere("a editada guarda o texto final e o que foi redigido",
            editada is not None and editada["texto"] != editada["texto_gerado"])

    print("\n$ GET /api/mensagens/exportacao.csv")
    r = g.get("/api/mensagens/exportacao.csv")
    texto = r.content.decode("utf-8-sig")
    linhas = texto.strip().splitlines()
    print(f"  {r.status_code} · {r.headers.get('content-disposition')}")
    print(f"  < {linhas[0]}")
    do_lote = [linha for linha in linhas[1:]
               if any(m["parceiro"] in linha for m in aprovadas["itens"])]
    for linha in do_lote[:2]:
        print(f"  < {linha[:150]}{'...' if len(linha) > 150 else ''}")
    print(f"  < ... {len(linhas) - 1} linhas além do cabeçalho")
    rejeitada = rejeitadas["itens"][0]["texto"]
    confere("o arquivo para envio traz as aprovadas deste lote",
            r.status_code == 200 and len(do_lote) >= 5)
    confere("e não traz a rejeitada", rejeitada not in texto)
    pendente = lote["mensagens"][-1]["texto"]
    confere("nem as que ainda esperam a decisão", pendente not in texto)


# ----------------------------------------------------------------- 4. banco
def no_banco_de_dados(lote: dict, confere: Conferencias) -> None:
    titulo("4. No banco — as mensagens do lote, por estado")
    consulta = """
        SELECT m.estado, count(*), count(m.decidida_por_id), count(m.decidida_em)
        FROM mensagem m WHERE m.lote_id = :lote
        GROUP BY m.estado ORDER BY m.estado
    """
    linhas = no_banco(consulta, {"lote": lote["id"]})
    mostrar_sql(consulta, linhas, ("estado", "mensagens", "com quem decidiu", "com quando"))
    por_estado = {estado: (total, autor, quando) for estado, total, autor, quando in linhas}
    total = len(lote["mensagens"])
    confere("cinco aprovadas, uma rejeitada e o resto pendente",
            {estado: v[0] for estado, v in por_estado.items()}
            == {"APROVADA": 5, "REJEITADA": 1, "PENDENTE": total - 6})
    confere("toda mensagem decidida tem quem decidiu e quando; nenhuma pendente tem",
            por_estado["APROVADA"] == (5, 5, 5) and por_estado["REJEITADA"] == (1, 1, 1)
            and por_estado["PENDENTE"][1:] == (0, 0))


# ------------------------------------------------------------ 5. assistente
def assistente(
    an: httpx.Client, admin: httpx.Client, marca: str, senha: str, url: str, confere: Conferencias
) -> None:
    titulo("5. Assistente — a resposta com a fonte, ou a abstenção (UC12, RF41 a RF43)")
    estado = an.get("/api/assistente").json()
    modelo = estado.get("assistente") or {}
    print(f"\nGET /api/assistente → disponível: {modelo.get('disponivel')}"
          f"{', ' + str(modelo.get('modelo')) if modelo.get('disponivel') else ''}; "
          f"{len(estado.get('exemplos', []))} tipos de pergunta no catálogo.")

    conta = perguntar(an, "Qual a média de faturamento das pizzarias?")
    confere("a pergunta que pede conta recebe a abstenção do código, com ou sem o modelo",
            conta["situacao"] == "ABSTENCAO" and conta["tipo"] == "fora_do_catalogo")

    criar(admin, marca, senha, "adm", "ADMINISTRADOR")
    with httpx.Client(base_url=url, timeout=30) as adm:
        adm.post("/api/sessao", json={"login": f"{marca}.adm", "senha": senha})
        negado = adm.post("/api/assistente/perguntas", json={"texto": "Como foi a rede?"})
    print(f"\n  O administrador pergunta: {negado.status_code}. As respostas falam de parceiros "
          "e de planos, que ele não abre.")
    confere("o administrador não pergunta ao assistente", negado.status_code == 403)

    if not modelo.get("disponivel"):
        fora = perguntar(an, "Como foi a rede na semana passada?")
        confere("sem o modelo, o assistente se diz indisponível, e o painel segue",
                fora["situacao"] == "INDISPONIVEL"
                and an.get("/api/painel/indicadores").status_code == 200)
        print("\n  Sem o modelo de linguagem, ninguém lê a pergunta. O assistente com o modelo de")
        print("  verdade está medido em docs/medicoes/assistente.md.")
        return

    maior = an.get("/api/parceiros", params={
        "ordenar_por": "faturamento", "descendente": True, "tamanho": 1,
    }).json()["itens"][0]
    faturamento = maior["desempenho"]["faturamento"]
    do_parceiro = perguntar(an, f"Quanto {maior['nome']} faturou na última semana?")
    confere("a pergunta do parceiro traz o faturamento que a lista de parceiros mostra",
            do_parceiro["situacao"] == "RESPONDIDA" and reais(faturamento) in do_parceiro["texto"])
    confere("o texto só tem números dos fatos, no sentido deles (RN08)",
            numeros_sem_origem(do_parceiro["texto"], do_parceiro["fatos"]) == []
            and sentido_trocado(do_parceiro["texto"], do_parceiro["fatos"]) == [])

    da_rede = perguntar(an, "Como foi a rede na última semana?")
    fonte = da_rede.get("fonte") or {}
    # O período de que a resposta fala é o último relatório da fonte. "A última
    # semana" é a mais recente, a que o painel abre sem período escolhido: o
    # modelo chegou a trocá-la pela anterior, com o número certo da semana errada
    # (#235).
    do_periodo = (fonte.get("relatorios") or [{}])[-1].get("periodo") or {}
    painel = an.get("/api/painel/indicadores").json()
    print(f"\n  O painel abre em {painel['periodo']['data_inicio']} a "
          f"{painel['periodo']['data_fim']}: {reais(painel['faturamento'])}")
    confere("a última semana da pergunta é a semana mais recente, a que o painel abre",
            do_periodo.get("id") == painel["periodo"]["id"])
    confere("e a resposta traz o faturamento que o painel mostra nela",
            da_rede["situacao"] == "RESPONDIDA"
            and reais(painel["faturamento"]) in da_rede["texto"])
    confere("e a fonte: os relatórios de onde os números saíram, com a data da importação",
            bool(fonte.get("relatorios"))
            and all(rel.get("importado_em") for rel in fonte["relatorios"]))

    fora = perguntar(an, "Qual a capital da França?")
    confere("a pergunta fora do catálogo recebe a abstenção, e não um palpite",
            fora["situacao"] == "ABSTENCAO" and not fora.get("fatos"))
    causa = perguntar(an, f"Por que {maior['nome']} faturou isso?")
    confere("a pergunta pela causa também: o sistema sabe quanto, e não por quê",
            causa["situacao"] == "ABSTENCAO")


# ----------------------------------------------------------------- 6. portal
def portal(url: str, admin: httpx.Client, marca: str, senha: str, confere: Conferencias) -> None:
    titulo("6. Portal do parceiro — o próprio histórico, e só ele (UC13, RF19, RF26)")
    with httpx.Client(base_url=url, timeout=30) as an:
        an.post("/api/sessao", json={"login": f"{marca}.analista", "senha": senha})
        dele = an.get("/api/parceiros", params={
            "ordenar_por": "faturamento", "descendente": True, "tamanho": 1,
        }).json()["itens"][0]
    print("\nO administrador acha o parceiro pelo nome e cria a conta dele (RF56, RF04):")
    achados = admin.get("/api/usuarios/parceiros", params={"busca": dele["nome"]}).json()
    print(f"  GET /api/usuarios/parceiros?busca=… → {achados[:1]}")
    criar(admin, marca, senha, "parceiro", "PARCEIRO", parceiro_id=dele["id"])

    with httpx.Client(base_url=url, timeout=30) as par:
        entrada = par.post("/api/sessao", json={"login": f"{marca}.parceiro", "senha": senha})
        telas = entrada.json()["usuario"]["telas"]
        print(f"\nA conta entra: {entrada.status_code}. A sessão lhe dá: {telas}")
        meu = troca(par, "GET", "/api/meu-desempenho", resumida=True).json()
        confere("o parceiro tem só o portal dele", telas == ["meu_desempenho"])
        confere("o histórico é o do parceiro da conta", meu["parceiro"] == dele["nome"])
        confere("o faturamento do período mais recente é o que a lista mostra ao analista",
                meu["atual"]["faturamento"] == dele["desempenho"]["faturamento"])
        confere("a resposta não traz ranking, posição nem comparação com a rede",
                set(meu) == {"parceiro", "categoria", "atual", "anterior", "variacao", "pontos"})
        da_rede = par.get("/api/painel/ranking")
        print(f"\n  O ranking da rede, pela conta do parceiro: {da_rede.status_code}")
        confere("os dados da rede são recusados", da_rede.status_code == 403)


if __name__ == "__main__":
    raise SystemExit(main())
