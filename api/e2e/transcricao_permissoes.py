"""Transcreve o controle de permissões, com os quatro perfis, como evidência.

A oitava entrega da disciplina pede o controle de permissões **demonstrado com
os perfis de usuário**, com acessos permitidos e negados conforme as regras do
projeto. Aqui os quatro perfis entram na aplicação no ar, e cada um tenta o que
pode e o que não pode:

1. **a matriz perfil × rota** — as rotas e os perfis de cada uma saem do código
   (do `exigir` de cada rota, que é de onde a autorização sai de verdade), e
   cada combinação é exercitada: a negada tem de responder 403; a leitura
   permitida tem de passar; e, sem sessão, toda rota protegida responde 401;
2. **por caso de uso** — para cada um dos dezesseis, um acesso permitido e um
   negado, com o que voltou;
3. **por capacidade** — o que o perfil vê e não faz: o Analista vê a fila e não
   aprova (RN06), vê a campanha e não calcula; o Administrador vê o histórico
   das execuções e não abre o plano;
4. **por objeto** — dois parceiros, cada um com a sua conta: cada um vê o
   próprio histórico, e nenhum vê o do outro nem nada da rede (RF26);
5. **a sessão** — sem sessão, cookie forjado, a troca de senha que derruba as
   outras sessões, a redefinição que derruba todas, e a conta desativada;
6. **a trilha** — cada acesso negado desta execução está na auditoria (RF06).

**De onde vem o esperado.** Na parte 1, o que cada rota deve responder a cada
perfil sai do próprio código: ela mostra que a aplicação no ar cumpre o que
declara, em todas as rotas. Quem confere se o que o código declara é o que a
documentação manda é o `tests/test_autorizacao.py`, com a matriz transcrita à
mão de `docs/03`, e a matriz de rastreabilidade (`docs/11`). Nas partes 2 a 5 o
esperado está escrito aqui, caso a caso.

**O que esta transcrição não provoca, e por quê.** O bloqueio por tentativas de
login (RNF11) é por origem: provocá-lo aqui travaria a entrada de todo mundo
que usa a aplicação nesta máquina. E a regra do último administrador só aparece
quando resta um, e derrubar administrador de verdade para mostrá-la seria
trocar a evidência pelo acidente. Os dois têm teste automatizado, citado no
fim.

**A escrita permitida não é exercitada na matriz.** Um `POST` permitido, de
corpo vazio, pode gravar — começar um treino, por exemplo. Na matriz, a rota de
escrita permitida aparece como `·`; quem a exercita, com dado de verdade, é a
parte 2 e as outras transcrições. A negada é exercitada sempre: a recusa vem
antes de qualquer validação, e não grava nada além da trilha.

Como as outras transcrições, não deixa resíduo: o parceiro criado sai do banco
e os usuários são desativados (ver `e2e/limpeza.py`). A trilha fica — é
registro de segurança.

Uso, da pasta `api/`:
    GIH_ADMIN_SENHA=... python e2e/transcricao_permissoes.py \\
        > ../docs/entrega/evidencias/sprint08/permissoes.txt
"""
from __future__ import annotations

import argparse
import os
import secrets
import sys
from collections import Counter

import httpx
from fastapi.routing import APIRoute

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.dependencias import perfis_da_rota  # noqa: E402
from app.main import app  # noqa: E402
from app.modelos import Perfil  # noqa: E402
from e2e.persistencia import api_responde  # noqa: E402
from e2e.transcricao import LARGURA, desfazer, titulo  # noqa: E402
from e2e.transcricao_modelo import Conferencias, mostrar_sql, no_banco  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ADM, GES, ANL, PAR = Perfil.ADMINISTRADOR, Perfil.GESTOR, Perfil.ANALISTA, Perfil.PARCEIRO
ORDEM = (ADM, GES, ANL, PAR)
SIGLA = {ADM: "ADM", GES: "GES", ANL: "ANL", PAR: "PAR"}
# As duas rotas que não pedem sessão: a saúde e a própria entrada.
PUBLICAS = {("GET", "/api/health"), ("POST", "/api/sessao")}
IGNORADAS = {"/api/openapi.json", "/api/docs", "/api/docs/oauth2-redirect", "/api/redoc"}
# Para as rotas com identificador no caminho. Não precisa existir: o 404 já diz
# que a autorização deixou passar, que é o que se mede aqui.
INEXISTENTE = "999999999"
# O que o portal do Parceiro devolve: nada de ranking, posição ou comparação com a rede.
CAMPOS_DO_PORTAL = {"parceiro", "categoria", "atual", "anterior", "variacao", "pontos"}


class Negados:
    """Conta os 403 que as sessões desta execução receberam, para conferir com a trilha."""

    def __init__(self) -> None:
        self.total = 0
        self.mensagens: set[str] = set()

    def __call__(self, resposta: httpx.Response) -> httpx.Response:
        if resposta.status_code == 403:
            self.total += 1
            self.mensagens.add(recusa(resposta))
        return resposta


# ------------------------------------------------------------------ a matriz
def rotas_do_codigo() -> dict[tuple[str, str], frozenset[Perfil] | None]:
    """Cada rota com os perfis que o `exigir` dela aceita; `None` é qualquer sessão."""
    rotas = {}
    for rota in app.routes:
        if not isinstance(rota, APIRoute) or rota.path in IGNORADAS:
            continue
        for metodo in rota.methods - {"HEAD", "OPTIONS"}:
            rotas[(metodo, rota.path)] = perfis_da_rota(rota)
    return rotas


def rotas_no_ar(cliente: httpx.Client) -> set[tuple[str, str]]:
    """As rotas que a aplicação em execução publica, pela especificação dela."""
    caminhos = cliente.get("/api/openapi.json").json()["paths"]
    return {
        (metodo.upper(), caminho)
        for caminho, operacoes in caminhos.items()
        for metodo in operacoes
        if metodo.upper() in {"GET", "POST", "PUT", "PATCH", "DELETE"}
    }


def concretizar(caminho: str) -> str:
    partes = [INEXISTENTE if p.startswith("{") else p for p in caminho.split("/")]
    return "/".join(partes)


def pedir_vazio(cliente: httpx.Client, metodo: str, caminho: str) -> httpx.Response:
    corpo = None if metodo == "GET" else {}
    return cliente.request(metodo, concretizar(caminho), json=corpo)


def matriz(
    url: str,
    admin: httpx.Client,
    sessoes: dict[Perfil, httpx.Client],
    confere: Conferencias,
    negados: Negados,
) -> None:
    titulo("1. A matriz perfil × rota — tirada do código e exercitada")
    rotas = rotas_do_codigo()
    print(f"\n{len(rotas)} rotas, lidas das rotas registradas na aplicação. Os perfis de cada uma")
    print("vêm da dependência `exigir` da própria rota: não há uma segunda tabela.")
    confere(
        f"as {len(rotas)} rotas do código são as que a aplicação no ar publica",
        set(rotas) == rotas_no_ar(admin),
    )

    print("\nCada célula é o que a aplicação respondeu ao perfil, com a requisição vazia:")
    print("  403  negado, como a matriz manda        401  sem sessão")
    print("  200, 404, 409, 422  a autorização deixou passar; o resto é da própria rota")
    print("  ·    permitido e não exercitado aqui: é escrita, e o corpo vazio poderia gravar")
    print("  púb  rota pública\n")

    largura = max(len(f"{m} {c}") for m, c in rotas) + 2
    print(f"{'rota':<{largura}}" + "  ".join(SIGLA[p] for p in ORDEM) + "  sem sessão")
    print("-" * (largura + 4 * 5 + 10))

    contagem: Counter[str] = Counter()
    erradas: dict[str, list[str]] = {"negações": [], "leituras permitidas": [], "sem sessão": []}
    with httpx.Client(base_url=url, timeout=60) as anonimo:
        for (metodo, caminho), perfis in sorted(rotas.items(), key=lambda r: (r[0][1], r[0][0])):
            celulas = []
            for perfil in ORDEM:
                permitido = perfis is None or perfil in perfis
                if permitido and metodo != "GET":
                    contagem["escritas permitidas, não exercitadas"] += 1
                    celulas.append("  ·")
                    continue
                r = negados(pedir_vazio(sessoes[perfil], metodo, caminho))
                tipo = "leituras permitidas" if permitido else "negações"
                contagem[tipo] += 1
                certo = r.status_code not in (401, 403) if permitido else r.status_code == 403
                if not certo:
                    erradas[tipo].append(f"{metodo} {caminho} · {SIGLA[perfil]}: {r.status_code}")
                celulas.append(f"{r.status_code}")

            if (metodo, caminho) in PUBLICAS:
                celulas.append("púb")
            else:
                r = pedir_vazio(anonimo, metodo, caminho)
                contagem["sem sessão"] += 1
                if r.status_code != 401:
                    erradas["sem sessão"].append(f"{metodo} {caminho}: {r.status_code}")
                celulas.append(f"{r.status_code}")
            print(f"{f'{metodo} {caminho}':<{largura}}" + "  ".join(celulas))

    print()
    for o_que, quantas in contagem.items():
        print(f"  {quantas:>4}  {o_que}")
    for tipo, lista in erradas.items():
        for errada in lista:
            print(f"  FORA DA MATRIZ ({tipo}): {errada}")
    confere(
        f"as {contagem['negações']} combinações que a matriz nega responderam 403",
        not erradas["negações"],
    )
    confere(
        f"as {contagem['leituras permitidas']} leituras que a matriz permite passaram "
        "pela autorização",
        not erradas["leituras permitidas"],
    )
    confere(
        f"sem sessão, as {contagem['sem sessão']} rotas protegidas responderam 401",
        not erradas["sem sessão"],
    )


# ------------------------------------------------------------ os casos de uso
def linha(
    tipo: str, perfil: Perfil, metodo: str, caminho: str, r: httpx.Response, nota: str
) -> None:
    """Uma tentativa. A nota vai na linha de baixo: a transcrição cabe em 96 colunas."""
    print(f"  {tipo:<9} {SIGLA[perfil]}  {metodo:<5} {caminho:<44} {r.status_code}")
    if nota and tipo != "negado":
        print(f"                 {nota}")


def recusa(r: httpx.Response) -> str:
    try:
        return f'"{r.json()["detail"]}"'
    except (ValueError, KeyError, TypeError):
        return ""


def casos_de_uso(
    sessoes: dict[Perfil, httpx.Client],
    marca: str,
    parceiros: list[dict],
    confere: Conferencias,
    negados: Negados,
) -> None:
    titulo("2. Por caso de uso — um acesso permitido e um negado")
    um_parceiro = parceiros[0]["id"]
    previa = {
        "periodo_inicio": "2031-01-06",
        "periodo_fim": "2031-01-12",
        "texto": f"Parceiro;Faturamento;Pedidos\nComércio {marca} da prévia;1500,00;30\n",
    }
    novo = {"nome": f"Comércio {marca}", "status": "PROSPECCAO"}
    # Cada tentativa: (quem, método, caminho, corpo, o que mostrar). Com o que
    # mostrar, é a permitida, e espera 200 ou 201; sem, é a negada, e espera 403.
    casos = [
        ("UC02 Gerenciar usuários e perfis", [
            (ADM, "GET", f"/api/usuarios?busca={marca}", None,
             lambda c: f"{len(c)} contas desta execução"),
            (GES, "GET", f"/api/usuarios?busca={marca}", None, None),
        ]),
        ("UC03 Importar relatório de desempenho", [
            (ANL, "POST", "/api/importacoes/previa", previa, lambda c: "a prévia, sem gravar nada"),
            (ADM, "POST", "/api/importacoes/previa", previa, None),
            (ADM, "GET", "/api/importacoes?tamanho=1", None,
             lambda c: f"só o histórico: {c['total']} importações (RF13)"),
        ]),
        ("UC04 Gerenciar parceiros e categorias", [
            (ANL, "POST", "/api/parceiros", novo, lambda c: f"cadastrou {c['nome']}"),
            (ADM, "POST", "/api/parceiros", novo, None),
            (ADM, "GET", f"/api/usuarios/parceiros?busca={marca}", None,
             lambda c: f"só o nome e a situação: {sorted(c[0]) if c else c} (RF56)"),
        ]),
        ("UC05 Consultar painel e ranking", [
            (ADM, "GET", "/api/painel/indicadores", None,
             lambda c: "só leitura, pela matriz de docs/03"),
            (PAR, "GET", "/api/painel/indicadores", None, None),
        ]),
        ("UC06 Analisar mobilidade do Top N", [
            (GES, "GET", "/api/painel/mobilidade", None, lambda c: f"Top {c['top_n']}"),
            (PAR, "GET", "/api/painel/mobilidade", None, None),
        ]),
        ("UC07 Treinar modelo de previsão", [
            (GES, "GET", "/api/modelo", None, lambda c: f"versão em uso: {c['versao_em_uso']}"),
            (ANL, "GET", "/api/modelo", None, None),
            (ANL, "POST", "/api/modelo/treinos", {}, None),
            (ANL, "GET", f"/api/parceiros/{um_parceiro}/previsao", None,
             lambda c: "lê a previsão no cadastro (RF28), e não treina"),
        ]),
        ("UC09 Comparar desempenho serial, paralelo e GPU", [
            (ADM, "GET", "/api/benchmark", None, lambda c: "o estado do benchmark"),
            (ANL, "GET", "/api/benchmark", None, None),
        ]),
        ("UC10 Gerar mensagens por segmento", [
            (ANL, "GET", "/api/mensagens/geracao", None, lambda c: "o estado da geração"),
            (ADM, "GET", "/api/mensagens/geracao", None, None),
        ]),
        ("UC12 Consultar assistente analítico", [
            (GES, "GET", "/api/assistente", None, lambda c: "o estado do assistente"),
            (ADM, "GET", "/api/assistente", None, None),
        ]),
        ("UC13 Consultar meu desempenho", [
            (PAR, "GET", "/api/meu-desempenho", None, lambda c: f"o histórico de {c['parceiro']}"),
            (GES, "GET", "/api/meu-desempenho", None, None),
        ]),
        ("UC14 Auditar ações do sistema", [
            (ADM, "GET", "/api/auditoria?tamanho=1", None,
             lambda c: f"{c['total']} registros na trilha"),
            (GES, "GET", "/api/auditoria?tamanho=1", None, None),
        ]),
        ("UC15 Consultar e exportar relatórios", [
            (GES, "GET", "/api/relatorios/desempenho", None,
             lambda c: "o relatório de desempenho da rede"),
            (ADM, "GET", "/api/relatorios/desempenho", None, None),
            (ADM, "GET", "/api/relatorios/operacoes", None,
             lambda c: "o relatório de operações, que sai da trilha dele"),
            (GES, "GET", "/api/relatorios/operacoes", None, None),
        ]),
        ("UC16 Consultar a ajuda", [
            (ANL, "GET", "/api/ajuda/regras", None,
             lambda c: f"Top {c['top_n']}, {len(c['segmentos'])} segmentos na ordem da RN01"),
            (PAR, "GET", "/api/ajuda/regras", None, None),
        ]),
    ]

    print("\nUC01 Autenticar no sistema")
    print("  Os quatro perfis entraram na preparação, e a sessão de cada um diz o que ele abre.")
    print("  A recusa está na parte 5: sem sessão, senha antiga e conta desativada.")
    print("\nUC08 Configurar e executar otimização — e UC11 Aprovar mensagem: na parte 3, por")
    print("  capacidade, que é onde os dois se decidem.")

    for nome, tentativas in casos:
        print(f"\n{nome}")
        certo = True
        for perfil, metodo, caminho, corpo, mostrar in tentativas:
            r = negados(sessoes[perfil].request(metodo, caminho, json=corpo))
            if mostrar:
                passou = r.status_code in (200, 201)
                linha("permitido", perfil, metodo, caminho, r, mostrar(r.json()) if passou else "")
            else:
                passou = r.status_code == 403
                linha("negado", perfil, metodo, caminho, r, recusa(r))
            certo = certo and passou
        confere(f"{nome.split()[0]}: o permitido passou e o negado foi recusado", certo)


# ------------------------------------------------------------- por capacidade
def capacidades(
    sessoes: dict[Perfil, httpx.Client], confere: Conferencias, negados: Negados
) -> None:
    titulo("3. Por capacidade — o que o perfil vê e não faz")
    adm, ges, anl = sessoes[ADM], sessoes[GES], sessoes[ANL]

    print("\nA sessão diz a cada perfil o que ele pode. A tela desenha os botões a partir disto:")
    telas = {p: sessoes[p].get("/api/sessao/atual").json()["telas"] for p in ORDEM}
    for capacidade in ("calcular_campanha", "decidir_mensagens", "execucao", "ajuda_regras"):
        quem = ", ".join(SIGLA[p] for p in ORDEM if capacidade in telas[p]) or "ninguém"
        print(f"  {capacidade:<20} {quem}")
    print(f"  o Parceiro, inteiro: {telas[PAR]}")
    confere(
        "só o Gestor calcula a campanha e decide as mensagens",
        all(
            [SIGLA[p] for p in ORDEM if capacidade in telas[p]] == ["GES"]
            for capacidade in ("calcular_campanha", "decidir_mensagens")
        ),
    )
    confere("o Parceiro tem só o portal dele", telas[PAR] == ["meu_desempenho"])

    print("\nUC08 — a campanha: o Gestor calcula, o Analista consulta, o Administrador não abre")
    do_gestor = ges.get("/api/campanha")
    do_analista = anl.get("/api/campanha")
    linha("permitido", GES, "GET", "/api/campanha", do_gestor,
          f"pode calcular: {do_gestor.json().get('pode_executar')}")
    linha("permitido", ANL, "GET", "/api/campanha", do_analista,
          f"pode calcular: {do_analista.json().get('pode_executar')}")
    calculo = negados(anl.post("/api/otimizacoes", json={}))
    linha("negado", ANL, "POST", "/api/otimizacoes", calculo, recusa(calculo))
    da_campanha = negados(adm.get("/api/campanha"))
    linha("negado", ADM, "GET", "/api/campanha", da_campanha, recusa(da_campanha))
    confere(
        "o Analista vê a campanha e não a calcula; a API diz isso e recusa a tentativa",
        do_gestor.json().get("pode_executar") is True
        and do_analista.json().get("pode_executar") is False
        and calculo.status_code == 403
        and da_campanha.status_code == 403,
    )

    print("\nRF34 — o histórico das execuções: o Administrador lista e não abre o plano")
    historico = adm.get("/api/otimizacoes?tamanho=1")
    linha("permitido", ADM, "GET", "/api/otimizacoes?tamanho=1", historico,
          f"{historico.json()['total']} execuções")
    plano = negados(adm.get(f"/api/otimizacoes/{INEXISTENTE}"))
    linha("negado", ADM, "GET", "/api/otimizacoes/{id}", plano, recusa(plano))
    comparacao = negados(adm.get("/api/otimizacoes/comparacao"))
    linha("negado", ADM, "GET", "/api/otimizacoes/comparacao", comparacao,
          recusa(comparacao))
    confere(
        "o Administrador vê o histórico e é recusado no plano e na comparação",
        historico.status_code == 200 and plano.status_code == 403 and comparacao.status_code == 403,
    )

    print("\nUC11 — a fila de aprovação: o Analista vê, e só o Gestor decide (RN06)")
    fila = anl.get("/api/mensagens?tamanho=1")
    linha("permitido", ANL, "GET", "/api/mensagens?tamanho=1", fila,
          f"{fila.json()['total']} na fila")
    decisoes = []
    for caminho in (
        f"/api/mensagens/{INEXISTENTE}/aprovacao",
        f"/api/mensagens/{INEXISTENTE}/edicao",
        f"/api/mensagens/{INEXISTENTE}/rejeicao",
        "/api/mensagens/aprovacao-em-lote",
    ):
        r = negados(anl.post(caminho, json={}))
        linha("negado", ANL, "POST", caminho.replace(INEXISTENTE, "{id}"), r, recusa(r))
        decisoes.append(r.status_code)
    do_gestor = ges.post(f"/api/mensagens/{INEXISTENTE}/aprovacao", json={})
    linha("permitido", GES, "POST", "/api/mensagens/{id}/aprovacao", do_gestor,
          "passou da autorização: a mensagem é que não existe")
    confere(
        "aprovar, editar, rejeitar e aprovar em lote são recusados ao Analista",
        fila.status_code == 200 and decisoes == [403] * 4,
    )
    confere("o Gestor passa pela autorização da decisão", do_gestor.status_code == 404)


# ---------------------------------------------------------------- por objeto
def por_objeto(
    url: str,
    contas: dict[str, tuple[str, dict]],
    senha: str,
    confere: Conferencias,
    negados: Negados,
) -> None:
    titulo("4. Por objeto — cada parceiro vê o próprio histórico, e só ele (RF26)")
    (login_a, parceiro_a), (login_b, parceiro_b) = contas["a"], contas["b"]
    print(f"\nDuas contas de perfil Parceiro: uma de {parceiro_a['nome']}, outra de "
          f"{parceiro_b['nome']}.")

    with httpx.Client(base_url=url, timeout=30) as a, httpx.Client(base_url=url, timeout=30) as b:
        a.post("/api/sessao", json={"login": login_a, "senha": senha})
        b.post("/api/sessao", json={"login": login_b, "senha": senha})

        de_a, de_b = a.get("/api/meu-desempenho"), b.get("/api/meu-desempenho")
        for quem, r in (("A", de_a), ("B", de_b)):
            corpo = r.json()
            print(f"  conta {quem}  GET /api/meu-desempenho  {r.status_code}  "
                  f"{corpo['parceiro']} · {len(corpo['pontos'])} períodos")
        print(f"  os campos da resposta: {', '.join(sorted(de_a.json()))}")
        confere(
            "cada conta recebe o histórico do parceiro dela",
            de_a.json()["parceiro"] == parceiro_a["nome"]
            and de_b.json()["parceiro"] == parceiro_b["nome"],
        )
        confere(
            "a resposta não traz ranking, posição nem comparação com a rede",
            set(de_a.json()) == CAMPOS_DO_PORTAL,
        )

        print("\nA conta A tentando chegar ao parceiro B:")
        pelo_parametro = a.get(f"/api/meu-desempenho?parceiro_id={parceiro_b['id']}")
        print(f"  GET /api/meu-desempenho?parceiro_id={parceiro_b['id']}  "
              f"{pelo_parametro.status_code}  continua sendo {pelo_parametro.json()['parceiro']}: "
              "a rota não tem parâmetro")
        confere(
            "pedir outro parceiro pelo endereço não muda de quem é o histórico",
            pelo_parametro.json()["parceiro"] == parceiro_a["nome"],
        )
        tentativas = (
            f"/api/parceiros/{parceiro_b['id']}",
            f"/api/painel/series?parceiro_id={parceiro_b['id']}",
            f"/api/parceiros/{parceiro_b['id']}/previsao",
            "/api/painel/ranking",
            "/api/parceiros",
            "/api/relatorios/desempenho",
        )
        respostas = []
        for caminho in tentativas:
            r = negados(a.get(caminho))
            print(f"  GET {caminho:<46} {r.status_code}")
            respostas.append(r.status_code)
        confere(
            "o cadastro, a série e a previsão do outro, e os dados da rede, são recusados",
            respostas == [403] * len(tentativas),
        )


# ------------------------------------------------------------------ a sessão
def sessao(
    url: str, admin: httpx.Client, reserva: dict, senha: str, confere: Conferencias
) -> None:
    titulo("5. A sessão — sem ela, com ela forjada, trocada, redefinida e desativada")
    entrada = {"login": reserva["login"], "senha": senha}

    with httpx.Client(base_url=url, timeout=30) as anonimo:
        sem = anonimo.get("/api/parceiros")
        print(f"\n  sem sessão            GET /api/parceiros     {sem.status_code}  {recusa(sem)}")
        anonimo.cookies.set("gih_sessao", secrets.token_urlsafe(32))
        forjado = anonimo.get("/api/parceiros")
        print(f"  cookie forjado        GET /api/parceiros     {forjado.status_code}  "
              f"{recusa(forjado)}")
    confere("sem sessão, ou com um cookie inventado, a resposta é 401",
            (sem.status_code, forjado.status_code) == (401, 401))

    with (
        httpx.Client(base_url=url, timeout=30) as um,
        httpx.Client(base_url=url, timeout=30) as outro,
    ):
        um.post("/api/sessao", json=entrada)
        outro.post("/api/sessao", json=entrada)
        cookie = next(iter(um.cookies.jar))
        so_http = cookie.has_nonstandard_attr("HttpOnly")
        mesmo_site = cookie.get_nonstandard_attr("SameSite")
        print("\nA mesma pessoa em duas sessões — dois navegadores. O cookie de cada uma:")
        print(f"  {cookie.name}: HttpOnly={so_http}, SameSite={mesmo_site}")
        confere(
            "o cookie da sessão não é lido por script nem enviado por outro site (RNF10)",
            so_http and str(mesmo_site).lower() in {"lax", "strict"},
        )

        nova = f"trocada-{secrets.token_urlsafe(12)}"
        troca = um.post("/api/sessao/senha", json={"senha_atual": senha, "senha_nova": nova})
        print(f"\n  a primeira troca a senha    POST /api/sessao/senha   {troca.status_code}")
        de_quem = um.get("/api/sessao/atual")
        da_outra = outro.get("/api/sessao/atual")
        print(f"  a sessão de quem trocou     GET /api/sessao/atual    {de_quem.status_code}")
        print(f"  a outra sessão              GET /api/sessao/atual    {da_outra.status_code}  "
              f"{recusa(da_outra)}")
        confere(
            "trocar a senha derruba as outras sessões e mantém a de quem trocou (RF07)",
            (troca.status_code, de_quem.status_code, da_outra.status_code) == (204, 200, 401),
        )

        outro.post("/api/sessao", json={"login": reserva["login"], "senha": nova})
        redefinida = f"redefinida-{secrets.token_urlsafe(12)}"
        r = admin.post(f"/api/usuarios/{reserva['id']}/senha", json={"senha_nova": redefinida})
        print(f"\n  o administrador redefine    POST /api/usuarios/{{id}}/senha   {r.status_code}")
        depois = tuple(c.get("/api/sessao/atual").status_code for c in (um, outro))
        print(f"  as duas sessões da conta    GET /api/sessao/atual    {depois[0]} e {depois[1]}")
        antiga = um.post("/api/sessao", json={"login": reserva["login"], "senha": nova})
        com_a_nova = um.post("/api/sessao", json={"login": reserva["login"], "senha": redefinida})
        print(f"  entrar com a senha de antes POST /api/sessao         {antiga.status_code}")
        print(f"  entrar com a redefinida     POST /api/sessao         {com_a_nova.status_code}")
        confere(
            "a redefinição derruba todas as sessões da conta, e só a senha nova entra (RF54)",
            r.status_code == 204 and depois == (401, 401)
            and (antiga.status_code, com_a_nova.status_code) == (401, 201),
        )

        r = admin.patch(f"/api/usuarios/{reserva['id']}", json={"ativo": False})
        print(f"\n  o administrador desativa    PATCH /api/usuarios/{{id}}   {r.status_code}")
        da_sessao = um.get("/api/sessao/atual")
        print(f"  a sessão aberta da conta    GET /api/sessao/atual    {da_sessao.status_code}  "
              f"{recusa(da_sessao)}")
        entrar = um.post("/api/sessao", json={"login": reserva["login"], "senha": redefinida})
        print(f"  entrar de novo              POST /api/sessao         {entrar.status_code}  "
              f"{recusa(entrar)}")
        # Um acerto depois da falha, para o contador de tentativas desta origem voltar a zero.
        admin.get("/api/sessao/atual")
        confere(
            "desativar a conta derruba a sessão aberta na hora e impede a entrada",
            (da_sessao.status_code, entrar.status_code) == (401, 401),
        )


# -------------------------------------------------------------------- a trilha
def trilha(marca: str, confere: Conferencias, negados: Negados) -> None:
    titulo("6. A trilha — cada acesso negado desta execução está na auditoria (RF06)")
    consulta = """
        SELECT u.perfil, count(*)
        FROM auditoria a JOIN usuario u ON u.id = a.usuario_id
        WHERE a.acao = 'ACESSO_NEGADO' AND u.login LIKE :marca
        GROUP BY u.perfil ORDER BY u.perfil
    """
    linhas = no_banco(consulta, {"marca": f"{marca}.%"})
    mostrar_sql(consulta, linhas, ("perfil", "acessos negados"))
    na_trilha = sum(quantos for _, quantos in linhas)
    print(f"\n  A transcrição recebeu {negados.total} respostas 403; a trilha tem {na_trilha} "
          "registros de acesso negado.")
    confere("cada 403 desta execução virou um registro na trilha, com o perfil de quem tentou",
            na_trilha == negados.total)
    print("\n  A mensagem de todas as recusas por perfil: " + " · ".join(sorted(negados.mensagens)))
    confere("a recusa é sempre a mesma frase: ela não diz o que existe por trás da rota",
            len(negados.mensagens) == 1)


# ------------------------------------------------------------------------ main
def preparar(admin: httpx.Client, url: str, marca: str, senha: str):
    """As contas da execução: uma por perfil, uma segunda de parceiro e uma de reserva."""
    titulo("Preparação — uma conta por perfil, criadas pelo administrador (UC02)")

    def criar(apelido: str, perfil: str, **extra) -> dict:
        login = f"{marca}.{apelido}"
        r = admin.post("/api/usuarios", json={
            "login": login, "nome": f"{perfil.title()} da Evidência", "senha": senha,
            "perfil": perfil, **extra,
        })
        r.raise_for_status()
        print(f"  {r.status_code}  {login:<22} {perfil}")
        return r.json()

    criar("adm", "ADMINISTRADOR")
    criar("gestor", "GESTOR")
    criar("analista", "ANALISTA")
    reserva = criar("reserva", "ANALISTA")

    # Os dois parceiros de maior faturamento, lidos por quem pode listá-los.
    recorte = {"ordenar_por": "faturamento", "descendente": True, "tamanho": 2, "ativo": True}
    with httpx.Client(base_url=url, timeout=30) as analista:
        analista.post("/api/sessao", json={"login": f"{marca}.analista", "senha": senha})
        parceiros = analista.get("/api/parceiros", params=recorte).json()["itens"]
    if len(parceiros) < 2:
        raise SystemExit("A base tem menos de dois parceiros: popule a demonstração antes.")
    criar("parceiro", "PARCEIRO", parceiro_id=parceiros[0]["id"])
    criar("parceirob", "PARCEIRO", parceiro_id=parceiros[1]["id"])

    contas = {
        "a": (f"{marca}.parceiro", parceiros[0]),
        "b": (f"{marca}.parceirob", parceiros[1]),
    }
    return reserva, parceiros, contas


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
    negados = Negados()
    print(f"Controle de permissões, com os quatro perfis · {a.url}")
    print("Dados sintéticos; nenhum nome real de empresa ou pessoa. Nenhuma senha na transcrição.")

    with httpx.Client(base_url=a.url, timeout=60) as admin:
        if admin.post("/api/sessao", json={"login": a.login, "senha": a.senha}).status_code != 201:
            print("Não consegui autenticar como administrador.", file=sys.stderr)
            return 2
        try:
            reserva, parceiros, contas = preparar(admin, a.url, marca, senha)
            logins = {ADM: "adm", GES: "gestor", ANL: "analista", PAR: "parceiro"}
            sessoes = {perfil: httpx.Client(base_url=a.url, timeout=60) for perfil in ORDEM}
            try:
                print()
                entraram = []
                for perfil in ORDEM:
                    r = sessoes[perfil].post(
                        "/api/sessao", json={"login": f"{marca}.{logins[perfil]}", "senha": senha}
                    )
                    entraram.append(r.status_code)
                    telas = len(r.json()["usuario"]["telas"])
                    print(f"  {SIGLA[perfil]} entra: {r.status_code}, e a sessão lhe dá "
                          f"{telas} {'área' if telas == 1 else 'áreas'}")
                confere("os quatro perfis entram (UC01)", entraram == [201] * 4)

                matriz(a.url, admin, sessoes, confere, negados)
                casos_de_uso(sessoes, marca, parceiros, confere, negados)
                capacidades(sessoes, confere, negados)
            finally:
                for cliente in sessoes.values():
                    cliente.close()
            por_objeto(a.url, contas, senha, confere, negados)
            sessao(a.url, admin, reserva, senha, confere)
            trilha(marca, confere, negados)
        finally:
            limpo = desfazer(admin, marca)

    titulo("O que fica por conta dos testes automatizados")
    print("\nDuas regras não são provocadas contra a aplicação no ar, e têm teste que as cobra:")
    print("  - o bloqueio depois de cinco falhas de login, que é por origem (RNF11):")
    print("    api/tests/test_autenticacao.py::test_bloqueia_apos_cinco_falhas")
    print("  - o último administrador ativo não pode ser desativado nem perder o perfil:")
    print("    api/tests/test_usuarios.py::test_ultimo_administrador_ativo_nao_pode_cair")
    print("E a matriz inteira, com a escrita permitida, roda no banco de testes:")
    print("    api/tests/test_autorizacao.py::test_cada_endpoint_contra_cada_perfil")

    passaram = sum(ok for _, ok in confere.itens)
    print(f"\n{'=' * LARGURA}")
    print(f"Resultado: {passaram} de {len(confere.itens)} conferências passaram.")
    return 0 if limpo and passaram == len(confere.itens) else 1


if __name__ == "__main__":
    raise SystemExit(main())
