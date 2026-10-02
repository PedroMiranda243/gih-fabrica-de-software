"""Transcreve o painel, os relatórios, as pesquisas, a exportação e a trilha, como evidência.

A sétima entrega da disciplina pede o sistema quase completo: dashboard,
relatórios, pesquisas, filtros, exportação e logs ou histórico de operações —
cada um funcionando, com dados reais, e integrado aos módulos anteriores. Aqui
os seis rodam contra a API no ar, e cada troca vai para a transcrição com o que
se esperava dela:

1. **dashboard** — o painel num recorte de período e categoria, e o bloco com a
   previsão e a campanha, conferidos contra o banco e contra os outros módulos;
2. **relatórios** — os quatro, cada um conferido contra a tela que resume: o
   desempenho contra o painel, o risco contra a previsão do cadastro, a
   campanha contra o plano gravado, as operações contra a trilha;
3. **pesquisas e filtros** — o endereço de cada recorte e o que voltou;
4. **exportação** — cada arquivo CSV contra a tela de onde ele sai;
5. **logs e histórico** — um analista cadastra e altera um parceiro, e a trilha
   de auditoria e o histórico do cadastro contam o que mudou, quando e por quem;
6. **no banco** — as somas e os registros, lidos por SQL de leitura.

Um relatório que só mostra números não diz se eles estão certos: por isso cada
número é comparado com o de outro lugar, e o fim da transcrição conta quantas
conferências bateram.

Os PDFs dos relatórios saem da impressão do navegador, e são gerados pelo
roteiro de captura (`docs/entrega/capturar_sprint07.js`); as recusas, pelo
`validacoes.py`.

Como as outras transcrições, não deixa resíduo: no fim, o parceiro e os planos
saem do banco, e os usuários são desativados (ver `e2e/limpeza.py`). A trilha
fica — é registro de segurança.

Uso, da pasta `api/`:
    GIH_ADMIN_SENHA=... python e2e/transcricao_relatorios.py \\
        > ../docs/entrega/evidencias/sprint07/relatorios.txt
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import secrets
import sys
from decimal import Decimal

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.texto import normalizar  # noqa: E402
from e2e.persistencia import api_responde  # noqa: E402
from e2e.transcricao import LARGURA, desfazer, titulo, troca  # noqa: E402
from e2e.transcricao_campanha import PARAMETROS, acompanhar, historico  # noqa: E402
from e2e.transcricao_modelo import Conferencias, mostrar_sql, no_banco  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SENHA = "relatorios-de-evidencia"


def baixar(c: httpx.Client, caminho: str, *, mostrar: int = 4) -> list[list[str]]:
    """Baixa um CSV e mostra o que chegou: o nome do arquivo, o tamanho e as primeiras linhas."""
    print(f"\n$ GET {caminho}")
    r = c.get(caminho)
    print(f"  {r.status_code} {r.reason_phrase}")
    if r.status_code != 200:
        print(f"  < {r.text[:200]}")
        return []
    texto = r.content.decode("utf-8-sig")
    linhas = list(csv.reader(io.StringIO(texto), delimiter=";"))
    marca_de_ordem = "com" if r.content.startswith(b"\xef\xbb\xbf") else "SEM"
    print(f"  < {r.headers['content-disposition']}")
    print(f"  < {r.headers['content-type']} · {marca_de_ordem} a marca de UTF-8 no começo"
          f" · {len(linhas) - 1} linhas além do cabeçalho")
    for linha in texto.splitlines()[:mostrar]:
        print(f"  < {linha}")
    if len(linhas) > mostrar:
        print(f"  < ... mais {len(linhas) - mostrar} linhas")
    return linhas


def br(valor: str | None) -> str:
    """O número como o CSV o escreve: com vírgula decimal."""
    return "" if valor is None else str(valor).replace(".", ",")


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
    print(f"Painel, relatórios, pesquisas, exportação e trilha · {a.url}")
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
    titulo("Preparação — um gestor, que calcula a campanha, e um analista, que consulta e cadastra")
    ids = {}
    for login, perfil in ((gestor, "GESTOR"), (analista, "ANALISTA")):
        ids[perfil] = troca(admin, "POST", "/api/usuarios", {
            "login": login, "nome": f"{perfil.title()} da Evidência", "senha": SENHA,
            "perfil": perfil,
        }).json()["id"]

    with httpx.Client(base_url=url, timeout=30) as g, httpx.Client(base_url=url, timeout=30) as an:
        g.post("/api/sessao", json={"login": gestor, "senha": SENHA})
        an.post("/api/sessao", json={"login": analista, "senha": SENHA})

        print("\nO gestor calcula um plano de campanha: é dele que o painel e os relatórios vão")
        print("falar. A busca roda fora da requisição (ADR-011):")
        pedido = troca(g, "POST", "/api/otimizacoes", PARAMETROS)
        plano = acompanhar(g, pedido.json()["id"])
        confere("o plano terminou viável", plano["situacao"] == "CONCLUIDA" and plano["viavel"])

        recorte = dashboard(an, admin, plano, confere)
        relatorios(an, admin, plano, confere)
        pesquisas(an, admin, marca, ids, plano, recorte, confere)
        exportacao(an, admin, marca, plano, confere)
        alvo = historico_de_operacoes(an, admin, marca, ids, recorte, confere)
        no_banco_de_dados(an, alvo, recorte, confere)


# ------------------------------------------------------------------ 1. dashboard
def dashboard(an: httpx.Client, admin: httpx.Client, plano: dict, confere: Conferencias) -> dict:
    titulo("[1/6] Dashboard — o painel num recorte, e os três módulos num lugar só (H82, H83)")
    print("\nO que o painel oferece para escolher. As listas longas aparecem com os dois")
    print("primeiros registros:")
    recortes = troca(an, "GET", "/api/painel/recortes", resumida=True).json()
    periodos, categorias = recortes["periodos"], recortes["categorias"]
    confere("os períodos vêm do mais recente para o mais antigo",
            [p["data_inicio"] for p in periodos]
            == sorted((p["data_inicio"] for p in periodos), reverse=True))

    # Um período que não é o mais recente, e a primeira categoria: o recorte que
    # o painel antigo não mostrava.
    periodo, categoria = periodos[min(2, len(periodos) - 1)], categorias[0]
    filtro = f"periodo_id={periodo['id']}&categoria_id={categoria['id']}"
    print(f"\nO painel no período de {periodo['data_inicio']} a {periodo['data_fim']}, só na")
    print(f"categoria {categoria['nome']}:")
    ind = troca(an, "GET", f"/api/painel/indicadores?{filtro}").json()
    confere("a resposta diz o recorte: o período pedido e a categoria",
            ind["periodo"]["id"] == periodo["id"] and ind["categoria"]["id"] == categoria["id"])

    consulta = """
        SELECT count(*), sum(m.faturamento), sum(m.pedidos)
          FROM metrica m JOIN parceiro p ON p.id = m.parceiro_id
         WHERE m.periodo_id = :periodo AND p.categoria_id = :categoria
    """
    linhas = no_banco(consulta, {"periodo": periodo["id"], "categoria": categoria["id"]})
    mostrar_sql(consulta, linhas, ("parceiros", "faturamento", "pedidos"))
    confere("os indicadores do recorte são a soma das métricas dele no banco",
            linhas[0][0] == ind["parceiros_ativos"]
            and linhas[0][1] == Decimal(ind["faturamento"])
            and linhas[0][2] == ind["pedidos"])

    print("\nO ranking da categoria. A posição continua a da rede inteira (RN02): a categoria")
    print("escolhe quem aparece, e não renumera.")
    rk = troca(an, "GET", f"/api/painel/ranking?{filtro}&tamanho=3", resumida=True).json()
    primeiro = rk["itens"][0]
    pagina = (primeiro["posicao"] - 1) // 200 + 1
    da_rede = an.get("/api/painel/ranking", params={
        "periodo_id": periodo["id"], "tamanho": 200, "pagina": pagina,
    }).json()["itens"]
    na_rede = next(i for i in da_rede if i["parceiro_id"] == primeiro["parceiro_id"])
    print(f"\n  {primeiro['nome']}: posição {primeiro['posicao']} no ranking da categoria,"
          f" e {na_rede['posicao']} no da rede.")
    confere("a posição no ranking da categoria é a mesma do ranking da rede (RN02)",
            primeiro["posicao"] == na_rede["posicao"] and rk["total"] == ind["parceiros_ativos"])

    print("\nA previsão e a campanha, dentro do painel (H83). Não acompanham o período")
    print("escolhido: a previsão parte de onde o modelo foi treinado, e o plano é o último.")
    decisao = troca(an, "GET", "/api/painel/decisao", resumida=True).json()
    previsao = decisao["previsao"]
    confere("o previsto vem ao lado do medido nos mesmos parceiros, com a versão do modelo",
            previsao["disponivel"] is True and previsao["parceiros"] > 0
            and previsao["modelo_versao"] == an.get("/api/campanha").json()["modelo_versao"])
    maior = previsao["maior_risco"][0]
    do_cadastro = an.get(f"/api/parceiros/{maior['parceiro_id']}/previsao").json()
    confere("o maior risco do painel é o da previsão no cadastro do parceiro",
            abs(maior["probabilidade_queda"] - do_cadastro["probabilidade_queda"]) < 1e-9
            and maior["faturamento_previsto"] == do_cadastro["faturamento_previsto"])
    confere("a campanha do painel é o plano que o gestor acabou de calcular",
            decisao["campanha"]["plano"]["execucao_id"] == plano["id"]
            and decisao["campanha"]["acoes"] == len(plano["itens"])
            and Decimal(decisao["campanha"]["custo"]) == Decimal(plano["custo_total"]))

    print("\nO Administrador lê o painel, mas não a previsão por parceiro nem a campanha:")
    confere("o administrador não recebe o bloco (403)",
            troca(admin, "GET", "/api/painel/decisao").status_code == 403)
    return {"periodo": periodo, "categoria": categoria, "categorias": categorias,
            "decisao": decisao}


# ----------------------------------------------------------------- 2. relatórios
def relatorios(an: httpx.Client, admin: httpx.Client, plano: dict, confere: Conferencias) -> None:
    titulo("[2/6] Relatórios — cada um conferido contra a tela que ele resume (H84 a H87)")

    print("\nDesempenho do período mais recente, por categoria e por segmento:")
    rel = troca(an, "GET", "/api/relatorios/desempenho", resumida=True).json()
    painel = an.get("/api/painel/indicadores").json()
    total = rel["total"]
    confere("o total do relatório é o indicador do painel no mesmo período",
            total["faturamento"] == painel["faturamento"] and total["pedidos"] == painel["pedidos"]
            and total["parceiros"] == painel["parceiros_ativos"]
            and total["ticket_medio"] == painel["ticket_medio"]
            and total["variacao_percentual"] == painel["variacao"]["faturamento"])

    iguais = 0
    for linha in rel["por_categoria"]:
        if linha["chave"] is None:
            continue
        do_painel = an.get(
            "/api/painel/indicadores", params={"categoria_id": linha["chave"]}
        ).json()
        iguais += (
            linha["faturamento"] == do_painel["faturamento"]
            and linha["parceiros"] == do_painel["parceiros_ativos"]
            and linha["variacao_percentual"] == do_painel["variacao"]["faturamento"]
        )
    com_categoria = sum(linha["chave"] is not None for linha in rel["por_categoria"])
    print(f"\n  {iguais} de {com_categoria} categorias com o faturamento, os parceiros e a")
    print("  variação iguais aos do painel filtrado por ela.")
    confere("cada categoria do relatório é o painel filtrado por ela (H82)",
            iguais == com_categoria and com_categoria > 0)
    confere("as categorias somam o total",
            sum(Decimal(linha["faturamento"]) for linha in rel["por_categoria"])
            == Decimal(total["faturamento"]))

    segmentos = an.get("/api/painel/segmentos").json()
    confere("cada segmento tem os parceiros que o painel conta nele",
            {linha["chave"]: linha["parceiros"] for linha in rel["por_segmento"]}
            == {fatia["segmento"]: fatia["total"] for fatia in segmentos["itens"]})
    em_risco = next((s for s in rel["por_segmento"] if s["chave"] == "EM_RISCO"), None)
    if em_risco:
        print(f"\n  Em risco: {em_risco['parceiros']} parceiros, variação de"
              f" {em_risco['variacao_percentual']}% — a dos mesmos parceiros, contra o que")
        print("  eles faturaram no período anterior.")

    print("\nParceiros em risco: o maior risco primeiro, com a ação no último plano.")
    risco = troca(an, "GET", "/api/relatorios/risco?tamanho=3", resumida=True).json()
    primeiro = risco["itens"][0]
    do_cadastro = an.get(f"/api/parceiros/{primeiro['parceiro_id']}/previsao").json()
    confere("o risco e o previsto do relatório são os da previsão no cadastro",
            abs(primeiro["probabilidade_queda"] - do_cadastro["probabilidade_queda"]) < 1e-9
            and primeiro["faturamento_previsto"] == do_cadastro["faturamento_previsto"]
            and risco["modelo_versao"] == do_cadastro["modelo_versao"])
    do_painel = an.get("/api/painel/decisao").json()["previsao"]
    confere("o resumo do relatório é o do painel: os mesmos parceiros, medido e previsto",
            risco["com_previsao"] == do_painel["parceiros"]
            and risco["faturamento_previsto"] == do_painel["faturamento_previsto"]
            and risco["faturamento_medido"] == do_painel["faturamento_medido"])
    confere("o relatório conta as ações do último plano",
            risco["plano"]["execucao_id"] == plano["id"]
            and risco["no_plano"] == len(plano["itens"]))

    print("\nQuem não tem previsão aparece com o motivo, e não com zero (RN09):")
    novatos = troca(an, "GET", "/api/relatorios/risco?segmento=RECEM_CHEGADO&tamanho=2",
                    resumida=True).json()
    sem = next((i for i in novatos["itens"] if i["sem_previsao"]), None)
    if sem is None:
        confere("há parceiro sem previsão para mostrar", False)
    else:
        motivo = an.get(f"/api/parceiros/{sem['parceiro_id']}/previsao").json()["motivo"]
        confere("o motivo é o mesmo que o cadastro do parceiro mostra",
                sem["probabilidade_queda"] is None and sem["sem_previsao"] == motivo)

    print("\nCampanha: onde a verba do último plano foi.")
    camp = troca(an, "GET", "/api/relatorios/campanha", resumida=True).json()
    confere("o relatório é do plano que o gestor calculou, e soma o plano gravado",
            camp["plano"]["execucao_id"] == plano["id"]
            and camp["total"]["parceiros"] == len(plano["itens"])
            and Decimal(camp["total"]["custo"]) == Decimal(plano["custo_total"])
            and Decimal(camp["total"]["ganho_esperado"])
            == sum(Decimal(i["ganho"]) for i in plano["itens"]))
    confere("cada agrupamento — ação, categoria e segmento — soma o total",
            all(sum(Decimal(linha["custo"]) for linha in camp[grupo])
                == Decimal(camp["total"]["custo"])
                and sum(linha["parceiros"] for linha in camp[grupo]) == camp["total"]["parceiros"]
                for grupo in ("por_acao", "por_categoria", "por_segmento")))

    print("\nOperações do sistema, do Administrador. Sem datas, os últimos trinta dias:")
    ops = troca(admin, "GET", "/api/relatorios/operacoes", resumida=True).json()
    trilha = admin.get("/api/auditoria", params={"de": ops["de"], "ate": ops["ate"]}).json()
    confere("o total do relatório é o da trilha de auditoria no mesmo intervalo",
            ops["total"] == trilha["total"])
    outras = (ops["outras_pessoas"] or {}).get("total", 0)
    confere("as ações, as pessoas e os dias somam, cada um, o total",
            sum(linha["total"] for linha in ops["por_acao"]) == ops["total"]
            and sum(linha["total"] for linha in ops["por_usuario"]) + outras == ops["total"]
            and sum(linha["total"] for linha in ops["por_dia"]) == ops["total"])


# -------------------------------------------------------- 3. pesquisas e filtros
def pesquisas(an: httpx.Client, admin: httpx.Client, marca: str, ids: dict, plano: dict,
              recorte: dict, confere: Conferencias) -> None:
    titulo("[3/6] Pesquisas e filtros — o endereço de cada recorte, e o que voltou")
    print("\nTodo recorte está no endereço: é o que deixa recarregar a tela, mandar o link e")
    print("exportar exatamente o que se vê.")

    print("\nParceiros — a busca ignora maiúscula e acento (RF24):")
    achados = troca(an, "GET", "/api/parceiros?busca=praca&tamanho=3", resumida=True).json()
    confere("\"praca\" acha os parceiros com \"Praça\" no nome",
            achados["total"] > 0
            and all("praca" in normalizar(p["nome"]) for p in achados["itens"])
            and any("Praça" in p["nome"] for p in achados["itens"]))

    categoria = recorte["categoria"]
    print(f"\nParceiros — em risco, da categoria {categoria['nome']}, do maior risco para o menor:")
    lista = troca(an, "GET", f"/api/parceiros?segmento=EM_RISCO&categoria_id={categoria['id']}"
                  "&ordenar_por=risco&descendente=true&tamanho=3", resumida=True).json()
    riscos = [p["risco_queda"] for p in lista["itens"] if p["risco_queda"] is not None]
    confere("os três filtros se combinam, e a ordem é a pedida",
            all(p["desempenho"]["segmento"] == "EM_RISCO"
                and p["categoria"]["id"] == categoria["id"] for p in lista["itens"])
            and riscos == sorted(riscos, reverse=True))

    print("\nExecuções — só as viáveis, calculadas pelo gestor desta transcrição (RF51):")
    execucoes = troca(an, "GET", f"/api/otimizacoes?resultado=VIAVEL&autor={ids['GESTOR']}",
                      resumida=True).json()
    confere("o histórico filtrado traz só o plano dele",
            [e["id"] for e in execucoes["itens"]] == [plano["id"]] and execucoes["total"] == 1)
    confere("a resposta oferece quem já calculou, para o filtro por autor",
            any(autor["id"] == ids["GESTOR"] for autor in execucoes["autores"]))

    print("\nUsuários — busca por nome ou login, sem maiúscula nem acento (RF52):")
    usuarios = troca(admin, "GET", f"/api/usuarios?busca={marca}").json()
    confere("a busca pelo trecho do login acha os dois usuários desta transcrição",
            {u["id"] for u in usuarios} == set(ids.values()))
    sem_acento = troca(admin, "GET", "/api/usuarios?busca=evidencia&ativo=true").json()
    confere("\"evidencia\" acha quem se chama \"… da Evidência\"",
            set(ids.values()) <= {u["id"] for u in sem_acento}
            and all("evidencia" in normalizar(u["nome"] + u["login"]) for u in sem_acento))

    print("\nTrilha de auditoria — busca por texto, com o filtro de ação (RF49):")
    trilha = troca(admin, "GET", f"/api/auditoria?busca={marca}&acao=USUARIO_CRIADO",
                   resumida=True).json()
    confere("a busca acha a criação dos dois usuários, com o autor e a frase",
            trilha["total"] == 2
            and all(r["rotulo"] == "Usuário criado" and marca in r["resumo"]
                    and r["autor"] is not None for r in trilha["itens"]))


# ----------------------------------------------------------------- 4. exportação
def exportacao(an: httpx.Client, admin: httpx.Client, marca: str, plano: dict,
               confere: Conferencias) -> None:
    titulo("[4/6] Exportação — cada arquivo contra a tela de onde ele sai (RF48, RF53)")
    print("\nO arquivo é a mesma consulta da tela, em CSV: ponto e vírgula, vírgula decimal e a")
    print("marca de UTF-8 no começo, que é o que a planilha em português abre sem ajuste.")
    print("Os PDFs saem da impressão do navegador, e estão nas capturas.")

    rel = an.get("/api/relatorios/desempenho").json()
    linhas = baixar(an, "/api/relatorios/desempenho/exportacao.csv")
    total = rel["total"]
    confere("desempenho: as categorias, os segmentos e o total da tela",
            len(linhas) - 1 == len(rel["por_categoria"]) + len(rel["por_segmento"]) + 1
            and linhas[-1][:5] == ["Total", "Total", str(total["parceiros"]),
                                   br(total["faturamento"]), str(total["pedidos"])])

    risco = an.get("/api/relatorios/risco", params={"risco_minimo": 0.9}).json()
    linhas = baixar(an, "/api/relatorios/risco/exportacao.csv?risco_minimo=0.9")
    confere("risco: o recorte inteiro, com o filtro da tela, na mesma ordem",
            len(linhas) - 1 == risco["total"]
            and [linha[0] for linha in linhas[1:]] == [i["nome"] for i in risco["itens"]])

    camp = an.get("/api/relatorios/campanha").json()
    linhas = baixar(an, "/api/relatorios/campanha/exportacao.csv")
    confere("campanha: os três agrupamentos e o total do plano",
            linhas[-1] == ["Total", "Total", str(camp["total"]["parceiros"]),
                           br(camp["total"]["custo"]), br(camp["total"]["ganho_esperado"])])

    linhas = baixar(an, f"/api/otimizacoes/{plano['id']}/exportacao.csv")
    confere("plano: uma linha por item, na ordem da tela, e o total (RF53)",
            [linha[0] for linha in linhas[1:-1]] == [i["parceiro"] for i in plano["itens"]]
            and linhas[-1][5] == br(plano["custo_total"]))

    ops = admin.get("/api/relatorios/operacoes").json()
    linhas = baixar(admin, "/api/relatorios/operacoes/exportacao.csv")
    confere("operações: todas as pessoas, que a tela resume, e o total",
            sum(linha[0] == "Usuário" for linha in linhas) == ops["pessoas"]
            and linhas[-1] == ["Total", "", str(ops["total"])])

    trilha = admin.get("/api/auditoria", params={"busca": marca}).json()
    linhas = baixar(admin, f"/api/auditoria/exportacao.csv?busca={marca}")
    confere("trilha: um registro por linha, com o recorte da busca (RF49)",
            len(linhas) - 1 == trilha["total"])

    print("\nO Administrador não baixa o plano, e o analista não baixa a trilha:")
    confere("a exportação segue a permissão da tela (403 e 403)",
            troca(admin, "GET", f"/api/otimizacoes/{plano['id']}/exportacao.csv").status_code == 403
            and troca(an, "GET", "/api/auditoria/exportacao.csv").status_code == 403)


# --------------------------------------------------- 5. logs e histórico de operações
def historico_de_operacoes(an: httpx.Client, admin: httpx.Client, marca: str, ids: dict,
                           recorte: dict, confere: Conferencias) -> int:
    titulo("[5/6] Logs e histórico de operações — o que foi feito, quando e por quem (H89, H90)")
    um, outra = recorte["categorias"][0], recorte["categorias"][1]
    print("\nO analista cadastra um parceiro, corrige o nome e o contato, troca a categoria e o")
    print("desativa. Cada alteração entra na trilha de auditoria:")
    alvo = troca(an, "POST", "/api/parceiros", {
        "nome": f"Comércio {marca}", "categoria_id": um["id"], "contato": "antigo@exemplo.test",
    }).json()["id"]
    an.patch(f"/api/parceiros/{alvo}", json={
        "nome": f"Comércio Central {marca}", "contato": "novo@exemplo.test",
    })
    an.patch(f"/api/parceiros/{alvo}", json={"categoria_id": outra["id"]})
    an.patch(f"/api/parceiros/{alvo}", json={"ativo": False})
    print("\n  ... três alterações: PATCH com o nome e o contato, PATCH com a categoria,")
    print("  PATCH com a situação.")

    print("\nO histórico, no cadastro do próprio parceiro (H90) — do mais recente ao mais antigo:")
    eventos = troca(an, "GET", f"/api/parceiros/{alvo}/historico").json()
    confere("o histórico traz os quatro eventos, com o rótulo em português e o autor",
            [e["rotulo"] for e in eventos] == [
                "Parceiro desativado", "Categoria de parceiro alterada",
                "Cadastro de parceiro editado", "Parceiro cadastrado",
            ] and all(e["autor"] == "Analista da Evidência" for e in eventos))
    confere("a frase diz o que mudou: o nome de antes e o de depois, e a categoria pelo nome",
            eventos[2]["resumo"] == f"nome de Comércio {marca} para Comércio Central {marca};"
                                    " contato alterado"
            and eventos[1]["resumo"] == f"categoria de {um['nome']} para {outra['nome']}")
    confere("o histórico não traz a origem nem os parâmetros crus, que são da auditoria",
            all(set(e) == {"acao", "rotulo", "resumo", "autor", "ocorrido_em"} for e in eventos))

    print("\nA mesma história, na trilha de auditoria, que é do Administrador (H89) — o que o")
    print("analista fez, buscando pela marca desta transcrição. O cadastro entrou com o nome")
    print("antigo, e a busca pelo nome novo não o acharia: a trilha guarda o nome da hora.")
    trilha = troca(admin, "GET", f"/api/auditoria?busca={marca}&autor={ids['ANALISTA']}",
                   resumida=True).json()
    do_parceiro = [r for r in trilha["itens"] if r["acao"].startswith("PARCEIRO_")]
    confere("a trilha traz os mesmos quatro eventos, com quem fez, o login e a origem",
            [r["acao"] for r in do_parceiro] == [e["acao"] for e in eventos]
            and all(r["autor"] == "Analista da Evidência" and r["autor_login"] and r["origem"]
                    for r in do_parceiro))
    confere("na trilha, a frase leva o nome do parceiro na frente; no cadastro dele, não",
            do_parceiro[2]["resumo"] == f"Comércio Central {marca}: {eventos[2]['resumo']}")

    print("\nO contato é dado de uma pessoa, e a trilha não se apaga: ela grava que mudou,")
    print("e não o valor.")
    consulta = """
        SELECT acao, detalhes::text FROM auditoria
         WHERE detalhes->>'alvo' = :alvo ORDER BY id
    """
    linhas = no_banco(consulta, {"alvo": str(alvo)})
    mostrar_sql(consulta, [(acao, texto[:60] + ("…" if len(texto) > 60 else ""))
                           for acao, texto in linhas], ("acao", "detalhes"))
    confere("nenhum dos dois contatos está gravado na trilha",
            len(linhas) == 4
            and not any("exemplo.test" in texto for _, texto in linhas))

    print("\nToda ação da trilha tem um rótulo em português, que é o que a tela mostra:")
    acoes = troca(admin, "GET", "/api/auditoria/acoes").json()
    confere("nenhuma ação aparece na tela pelo código",
            len(acoes) > 30 and all(a["rotulo"] and a["rotulo"] != a["acao"] for a in acoes))

    print("\nA trilha inteira é só do Administrador (RF08):")
    confere("o analista não consulta a trilha (403)",
            troca(an, "GET", "/api/auditoria").status_code == 403)
    return alvo


# ------------------------------------------------------------------ 6. no banco
def no_banco_de_dados(an: httpx.Client, alvo: int, recorte: dict, confere: Conferencias) -> None:
    titulo("[6/6] No banco — o que os relatórios somam e o que a trilha gravou")
    rel = an.get("/api/relatorios/desempenho").json()
    consulta = """
        SELECT c.nome, count(*), sum(m.faturamento), sum(m.pedidos)
          FROM metrica m
          JOIN parceiro p ON p.id = m.parceiro_id
          JOIN categoria c ON c.id = p.categoria_id
         WHERE m.periodo_id = :periodo
         GROUP BY c.nome ORDER BY sum(m.faturamento) DESC LIMIT 4
    """
    linhas = no_banco(consulta, {"periodo": rel["periodo"]["id"]})
    mostrar_sql(consulta, linhas, ("categoria", "parceiros", "faturamento", "pedidos"))
    do_relatorio = [(linha["rotulo"], linha["parceiros"], Decimal(linha["faturamento"]),
                     linha["pedidos"]) for linha in rel["por_categoria"][:4]]
    confere("as quatro maiores categorias do relatório são as do banco, com os mesmos números",
            [tuple(linha) for linha in linhas] == do_relatorio)

    consulta = """
        SELECT a.acao, u.login, a.origem IS NOT NULL
          FROM auditoria a JOIN usuario u ON u.id = a.usuario_id
         WHERE a.detalhes->>'alvo' = :alvo
           AND a.acao LIKE 'PARCEIRO_%' ORDER BY a.id
    """
    linhas = no_banco(consulta, {"alvo": str(alvo)})
    mostrar_sql(consulta, linhas, ("acao", "login", "tem origem"))
    confere("os quatro eventos do parceiro estão gravados, na ordem, com o autor e a origem",
            [linha[0] for linha in linhas] == [
                "PARCEIRO_CRIADO", "PARCEIRO_EDITADO", "PARCEIRO_CLASSIFICADO",
                "PARCEIRO_DESATIVADO",
            ] and all(linha[2] for linha in linhas))


if __name__ == "__main__":
    raise SystemExit(main())
