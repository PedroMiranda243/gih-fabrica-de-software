"""Verificação de ponta a ponta contra a API no ar — história H78.

Diferente da suíte do `pytest`, que sobe a aplicação em processo, esta roda
contra o servidor de verdade: HTTP real, cookie real, banco real. É o que pega o
que o teste unitário não pega — configuração de cookie, ordem de dependências,
serialização, e o próprio contêiner.

**Escrita em Python, não em `curl`.** Aspas de JSON no shell do Windows já
mascararam resultado neste projeto, com teste "passando" porque o corpo chegava
vazio. Ver a armadilha registrada no CLAUDE.md.

A saída é organizada pelos seis itens da terceira entrega da disciplina, o que a
torna também o roteiro da demonstração. O que o sistema ganhou depois daquela
entrega entra em blocos marcados com `[  + ]`, fora da numeração: renumerar faria
a saída deixar de casar com o documento, e não verificar faria o roteiro deixar
de representar o sistema.

Uso:
    python e2e/verificacao.py
    python e2e/verificacao.py --url http://localhost:8000 --login admin --senha ...

A senha do administrador sai no log do contêiner na primeira subida:
    docker compose logs api | grep "Senha sorteada"
"""
from __future__ import annotations

import argparse
import os
import secrets
import sys
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

import httpx

# A matriz de permissões vem do módulo de teste, e não é copiada para cá: duas
# cópias divergiriam, e a daqui é a que ninguém olharia.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.test_autorizacao import PERMISSOES, PUBLICO, concretizar  # noqa: E402

# Cor so quando a saida e um terminal. Redirecionada para arquivo — que e
# como a evidencia da entrega e capturada — os codigos de escape virariam
# lixo no meio do texto.
_COLORIDO = sys.stdout.isatty()
VERDE = "\033[32m" if _COLORIDO else ""
VERMELHO = "\033[31m" if _COLORIDO else ""
CINZA = "\033[90m" if _COLORIDO else ""
FIM = "\033[0m" if _COLORIDO else ""

# O console do Windows abre em cp1252 e quebra em qualquer caractere fora
# dela. Nao e bug de dado: e o terminal. Reconfigurar aqui evita perder a
# execucao inteira por causa de um acento numa mensagem.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SENHA = "verificacao-ponta-a-ponta"
PERFIS = ("ADMINISTRADOR", "GESTOR", "ANALISTA")

# Rotas que a varredura de autorização não percorre, porque exercitá-las
# atrapalha a própria varredura. `DELETE /api/sessao` encerra a sessão do
# cliente, e tudo depois dela responderia 401 — a primeira execução deste script
# reprovou exatamente assim, e o sintoma parecia falha de autorização.
DESTRUTIVAS = {("DELETE", "/api/sessao")}


class Relatorio:
    """Acumula o resultado de cada verificação e decide o código de saída.

    Reportar tudo e falhar no fim, em vez de parar na primeira falha: quem está
    diagnosticando quer ver o quadro inteiro, não descobrir um problema por
    execução.
    """

    def __init__(self) -> None:
        self.falhas: list[str] = []
        self.total = 0

    def item(self, numero: int, titulo: str) -> None:
        print(f"\n[{numero}/6] {titulo}")

    def secao(self, titulo: str) -> None:
        """Bloco fora da numeração dos seis itens da entrega.

        A numeração [n/6] espelha a lista da terceira entrega acadêmica, e o
        sistema cresce além dela. Renumerar faria a saída deixar de casar com o
        documento; não verificar faria o roteiro deixar de representar o sistema.
        """
        print(f"\n[  + ] {titulo}")

    def checar(self, descricao: str, condicao: bool, detalhe: str = "") -> bool:
        self.total += 1
        marca = f"{VERDE}ok  {FIM}" if condicao else f"{VERMELHO}FALHA{FIM}"
        sufixo = f"  {CINZA}{detalhe}{FIM}" if detalhe else ""
        print(f"      {marca} {descricao}{sufixo}")
        if not condicao:
            self.falhas.append(descricao)
        return condicao

    def nota(self, texto: str) -> None:
        print(f"      {CINZA}·    {texto}{FIM}")

    def encerrar(self) -> int:
        print()
        if self.falhas:
            print(f"{VERMELHO}{len(self.falhas)} de {self.total} verificações falharam:{FIM}")
            for f in self.falhas:
                print(f"  - {f}")
            return 1
        print(f"{VERDE}As {self.total} verificações passaram.{FIM}")
        return 0


def periodo_de(marca: str, semana: int) -> dict[str, str]:
    """Uma semana no futuro, distinta a cada execução.

    Período fixo colidia com a execução anterior e a importação era recusada com
    409 — a verificação reprovava por causa de si mesma, não do sistema.
    """
    deslocamento = 365 + (int(marca.removeprefix("e2e")) % 500) * 7 + semana * 7
    inicio = date.today() + timedelta(days=deslocamento)
    return {
        "periodo_inicio": inicio.isoformat(),
        "periodo_fim": (inicio + timedelta(days=6)).isoformat(),
    }


def relatorio_de(marca: str, sufixo: str = "") -> str:
    # A linha do Gama tem faturamento nao numerico de proposito: e ela que da
    # a previa algo para rejeitar, e a rejeicao parcial e o que a verificacao
    # precisa exercitar.
    linhas = [
        "Parceiro;Faturamento;Pedidos",
        f"Alfa {marca}{sufixo};12500,40;312",
        f"Beta {marca}{sufixo};8940,00;201",
        f"Gama {marca}{sufixo};abacaxi;38",
    ]
    return "\n".join(linhas) + "\n"


def sessao(url: str) -> httpx.Client:
    return httpx.Client(base_url=url, timeout=30, follow_redirects=False)


def entrar(cliente: httpx.Client, login: str, senha: str) -> bool:
    r = cliente.post("/api/sessao", json={"login": login, "senha": senha})
    return r.status_code == 201


# --------------------------------------------------------------------------- 1
def item_banco(r: Relatorio, admin: httpx.Client) -> None:
    r.item(1, "Banco de dados conectado")

    saude = admin.get("/api/health")
    r.checar("a API responde à verificação de saúde", saude.status_code == 200)
    r.checar(
        "a API confirma o banco no ar",
        saude.json().get("banco") == "ok",
        f'banco={saude.json().get("banco")!r}',
    )

    # A trilha de auditoria só existe se houver escrita no banco acontecendo.
    trilha = admin.get("/api/auditoria", params={"tamanho": 1})
    r.checar(
        "o banco tem registros gravados pela aplicação",
        trilha.status_code == 200 and trilha.json()["total"] > 0,
        f'{trilha.json().get("total", 0)} eventos na trilha',
    )


# --------------------------------------------------------------------------- 2
def item_login(r: Relatorio, url: str, login: str, senha: str) -> None:
    r.item(2, "Login funcional")

    with sessao(url) as c:
        entrada = c.post("/api/sessao", json={"login": login, "senha": senha})
        r.checar("credencial válida abre sessão", entrada.status_code == 201)
        r.checar(
            "o cookie de sessão vem protegido",
            "httponly" in entrada.headers.get("set-cookie", "").lower(),
            "HttpOnly presente",
        )
        r.checar("a resposta não devolve senha", "senha" not in entrada.text.lower())

        quem = c.get("/api/sessao/atual")
        r.checar("a sessão identifica o usuário", quem.status_code == 200)

        c.delete("/api/sessao")
        r.checar(
            "encerrar invalida a sessão no servidor",
            c.get("/api/sessao/atual").status_code == 401,
        )

    with sessao(url) as c:
        errada = c.post("/api/sessao", json={"login": login, "senha": "nao-e-essa-senha"})
        inexistente = c.post("/api/sessao", json={"login": "ninguem", "senha": "nao-e-essa-senha"})
        r.checar("senha errada é recusada", errada.status_code == 401)
        r.checar(
            "usuário inexistente responde igual a senha errada",
            errada.status_code == inexistente.status_code
            and errada.json() == inexistente.json(),
            "indistinguível, como pede o RNF11",
        )


# --------------------------------------------------------------------------- 3
def item_cadastro(r: Relatorio, admin: httpx.Client, marca: str) -> dict[str, str]:
    r.item(3, "Cadastro de usuários")

    criados: dict[str, str] = {}
    for perfil in PERFIS:
        usuario = f"{marca}.{perfil.lower()}"
        resposta = admin.post(
            "/api/usuarios",
            json={"login": usuario, "nome": f"Verificação {perfil.title()}",
                  "senha": SENHA, "perfil": perfil},
        )
        if r.checar(f"cria usuário com perfil {perfil}", resposta.status_code == 201,
                    resposta.text[:60] if resposta.status_code != 201 else usuario):
            criados[perfil] = usuario

    if criados:
        listagem = admin.get("/api/usuarios")
        logins = {u["login"] for u in listagem.json()}
        r.checar(
            "os usuários criados estão persistidos",
            all(u in logins for u in criados.values()),
        )
        r.checar("a listagem não expõe hash de senha", "argon2" not in listagem.text.lower())

    return criados


# --------------------------------------------------------------------------- 4
def item_perfis(r: Relatorio, url: str, criados: dict[str, str]) -> None:
    r.item(4, "Controle de perfis")
    quantas = len(PERMISSOES) - len(DESTRUTIVAS)
    r.nota(f"{quantas} rotas conferidas contra {len(criados)} perfis, "
           "a partir da matriz de docs/03-casos-de-uso.md")

    sem_sessao_ok = True
    with sessao(url) as anonimo:
        for (metodo, caminho), permitidos in PERMISSOES.items():
            if permitidos is PUBLICO or (metodo, caminho) in DESTRUTIVAS:
                continue
            resposta = anonimo.request(metodo, concretizar(caminho), json={})
            if resposta.status_code != 401:
                sem_sessao_ok = False
                r.nota(f"{metodo} {caminho} respondeu {resposta.status_code} sem sessão")
    r.checar("sem sessão, todo endpoint protegido responde 401", sem_sessao_ok)

    for perfil, login in criados.items():
        divergencias = []
        with sessao(url) as c:
            if not entrar(c, login, SENHA):
                r.checar(f"perfil {perfil} autentica", False)
                continue
            for (metodo, caminho), permitidos in PERMISSOES.items():
                if permitidos is PUBLICO or (metodo, caminho) in DESTRUTIVAS:
                    continue
                resposta = c.request(metodo, concretizar(caminho), json={})
                negado = resposta.status_code == 403
                deveria_negar = perfil not in {str(p) for p in permitidos}
                if negado != deveria_negar:
                    divergencias.append(f"{metodo} {caminho} devolveu {resposta.status_code}")

        r.checar(
            f"perfil {perfil} só acessa o que a matriz permite",
            not divergencias,
            "; ".join(divergencias[:3]) if divergencias else "",
        )


# --------------------------------------------------------------------------- 5
def item_crud(r: Relatorio, url: str, criados: dict[str, str], marca: str) -> None:
    r.item(5, "CRUD principal — parceiros")

    login = criados.get("ANALISTA")
    if not login:
        r.checar("há um analista para exercitar o CRUD", False)
        return

    with sessao(url) as c:
        if not entrar(c, login, SENHA):
            r.checar("o analista autentica", False)
            return

        nome = f"Comércio {marca}"
        criacao = c.post("/api/parceiros", json={"nome": nome, "contato": "contato@exemplo.test"})
        criado = r.checar("cadastrar", criacao.status_code == 201,
                          criacao.text[:70] if criacao.status_code != 201 else nome)
        if not criado:
            return
        alvo = criacao.json()["id"]

        consulta = c.get(f"/api/parceiros/{alvo}")
        r.checar("consultar", consulta.status_code == 200 and consulta.json()["nome"] == nome)

        busca = c.get("/api/parceiros", params={"busca": marca})
        r.checar("consultar pela busca por nome",
                 busca.status_code == 200 and any(p["id"] == alvo for p in busca.json()))

        categoria = c.post("/api/categorias", json={"nome": f"Categoria {marca}"})
        r.checar("cadastrar categoria", categoria.status_code == 201)

        edicao = c.patch(
            f"/api/parceiros/{alvo}",
            json={"nome": f"{nome} Ltda", "categoria_id": categoria.json()["id"]},
        )
        r.checar("atualizar", edicao.status_code == 200)
        r.checar(
            "a categoria confirmada por pessoa é gravada como MANUAL",
            edicao.json().get("origem_categoria") == "MANUAL",
            "RN05",
        )

        duplicado = c.post("/api/parceiros", json={"nome": f"{nome} Ltda"})
        r.checar("nome repetido é recusado", duplicado.status_code == 409)

        exclusao = c.delete(f"/api/parceiros/{alvo}")
        r.checar("excluir", exclusao.status_code == 204)
        r.checar(
            "o excluído some da consulta",
            c.get(f"/api/parceiros/{alvo}").status_code == 404,
        )

        # O caminho que protege o histórico. Para exercitá-lo é preciso um
        # parceiro com métrica; a importação abaixo cria exatamente isso, e usa
        # um período próprio para não colidir com o do item 6.
        importacao = c.post(
            "/api/importacoes",
            json={**periodo_de(marca, 0), "texto": relatorio_de(marca, " hist")},
        )
        if importacao.status_code == 201:
            com_historico = c.get("/api/parceiros", params={"busca": f"{marca} hist"}).json()
            if com_historico:
                recusa = c.delete(f'/api/parceiros/{com_historico[0]["id"]}')
                r.checar(
                    "excluir parceiro com histórico é recusado",
                    recusa.status_code == 409,
                    f'{recusa.status_code}',
                )
                detalhe = recusa.json().get("detail", {})
                r.checar(
                    "a recusa diz quantos registros impedem e aponta a desativação",
                    isinstance(detalhe, dict)
                    and detalhe.get("vinculos", {}).get("metricas", 0) > 0
                    and "desative" in detalhe.get("ajuda", "").lower(),
                )
            else:
                r.checar("a importação criou parceiro para exercitar a recusa", False)
        else:
            r.checar("a importação de apoio funcionou", False, importacao.text[:70])


# --------------------------------------------------------------------------- 6
def item_ingestao(r: Relatorio, url: str, criados: dict[str, str], marca: str) -> None:
    r.item(6, "Ingestão e execução local")

    login = criados.get("ANALISTA")
    if not login:
        r.checar("há um analista para exercitar a ingestão", False)
        return

    with sessao(url) as c:
        if not entrar(c, login, SENHA):
            r.checar("o analista autentica", False)
            return

        relatorio = relatorio_de(marca)
        periodo = periodo_de(marca, 1)

        sem_periodo = c.post("/api/importacoes", json={"texto": relatorio})
        r.checar("importação sem período é recusada", sem_periodo.status_code == 422, "RN03")
        r.checar(
            "a recusa explica por que o período é obrigatório",
            "RN03" in sem_periodo.text,
        )

        previa = c.post("/api/importacoes/previa", json={**periodo, "texto": relatorio})
        r.checar("a prévia lista reconhecidos e rejeitados",
                 previa.status_code == 200
                 and previa.json()["total_reconhecido"] == 2
                 and previa.json()["total_rejeitado"] == 1)

        gravacao = c.post("/api/importacoes", json={**periodo, "texto": relatorio})
        r.checar("a importação grava as métricas", gravacao.status_code == 201,
                 gravacao.text[:70] if gravacao.status_code != 201 else "2 gravadas")

        repetida = c.post("/api/importacoes", json={**periodo, "texto": relatorio})
        r.checar("reimportar o mesmo período é recusado", repetida.status_code == 409, "RF12")

        documentacao = c.get("/api/docs")
        r.checar("a documentação interativa está no ar", documentacao.status_code == 200,
                 "/api/docs")

    r.nota("o recálculo da segmentação entra na Sprint 7 e ainda não existe")

    # O id do período volta para a verificação do painel poder consultar
    # **este** período. Sem ele restaria consultar "o mais recente", que numa
    # base com execuções anteriores pode ser o de outra execução.
    if gravacao.status_code == 201:
        return gravacao.json()["periodo"]["id"]
    return None


# --------------------------------------------------------------------- extra
def item_painel(r: Relatorio, url: str, criados: dict[str, str], periodo_id: int | None) -> None:
    """Painel: indicadores, ranking e séries (UC05 · H30, H31, H32).

    Fica fora da numeração porque não é um dos seis itens da terceira entrega —
    mas precisa ser verificado, senão o roteiro de demonstração passa a cobrir
    menos do que o sistema faz.
    """
    r.secao("Painel — indicadores, ranking e séries")

    login = criados.get("GESTOR")
    if not login or periodo_id is None:
        r.checar("há gestor e período para consultar o painel", False)
        return

    with sessao(url) as c:
        if not entrar(c, login, SENHA):
            r.checar("o gestor autentica", False)
            return

        ind = c.get("/api/painel/indicadores", params={"periodo_id": periodo_id})
        corpo = ind.json() if ind.status_code == 200 else {}
        r.checar(
            "os indicadores consolidam o período importado",
            ind.status_code == 200 and corpo.get("parceiros_ativos") == 2,
            f"{corpo.get('faturamento')} em {corpo.get('pedidos')} pedidos",
        )

        # Invariante da RN04: o ticket é a razão dos totais, calculada na
        # consulta. Conferir a relação, e não um número fixo, é o que mantém a
        # verificação válida quando a massa muda.
        faturamento = Decimal(corpo.get("faturamento") or 0)
        pedidos = int(corpo.get("pedidos") or 0)
        esperado = (
            (faturamento / pedidos).quantize(Decimal("0.01"), ROUND_HALF_UP) if pedidos else None
        )
        r.checar(
            "o ticket médio é a razão dos totais, e não coluna guardada",
            corpo.get("ticket_medio") == (str(esperado) if esperado is not None else None),
            "RN04",
        )

        rank = c.get("/api/painel/ranking", params={"periodo_id": periodo_id})
        itens = rank.json().get("itens", []) if rank.status_code == 200 else []
        faturamentos = [Decimal(i["faturamento"]) for i in itens]
        r.checar(
            "o ranking ordena por faturamento, com posições sem buraco",
            bool(itens)
            and [i["posicao"] for i in itens] == list(range(1, len(itens) + 1))
            and faturamentos == sorted(faturamentos, reverse=True),
            f"{len(itens)} parceiros",
        )

        serie = c.get("/api/painel/series")
        pontos = serie.json().get("pontos", []) if serie.status_code == 200 else []
        datas = [p["periodo"]["data_inicio"] for p in pontos]
        r.checar(
            "a série da rede sai em ordem cronológica",
            bool(pontos) and datas == sorted(datas),
            f"{len(pontos)} períodos",
        )

        individual = c.get(
            "/api/painel/series", params={"parceiro_id": itens[0]["parceiro_id"]} if itens else {}
        )
        r.checar(
            "a série individual cobre todos os períodos, com lacuna explícita",
            individual.status_code == 200
            and len(individual.json()["pontos"]) == len(pontos)
            and individual.json()["escopo"] == "parceiro",
            "período sem medição vem nulo, não sumido",
        )


def limpar(admin: httpx.Client, criados: dict[str, str]) -> None:
    """Desativa os usuários que a verificação criou.

    Desativar, e não apagar: a trilha de auditoria referencia o autor de cada
    ação, e remover a linha deixaria o histórico apontando para o nada.
    """
    for usuario in admin.get("/api/usuarios").json():
        if usuario["login"] in criados.values() and usuario["ativo"]:
            admin.patch(f'/api/usuarios/{usuario["id"]}', json={"ativo": False})


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--url", default=os.environ.get("GIH_URL", "http://localhost:8000"))
    p.add_argument("--login", default=os.environ.get("GIH_ADMIN_LOGIN", "admin"))
    p.add_argument("--senha", default=os.environ.get("GIH_ADMIN_SENHA", ""))
    a = p.parse_args()

    if not a.senha:
        print("Informe a senha do administrador com --senha ou GIH_ADMIN_SENHA.")
        print('Ela sai no log da primeira subida: docker compose logs api | grep "Senha sorteada"')
        return 2

    print(f"Verificação de ponta a ponta · {a.url}")

    r = Relatorio()
    # Marca sorteada, e não derivada do relógio: duas execuções no mesmo
    # intervalo de tempo cairiam no mesmo período e a segunda seria recusada com
    # 409 — a verificação reprovaria por causa de si mesma.
    marca = f"e2e{secrets.randbelow(100000):05d}"

    with sessao(a.url) as admin:
        try:
            saude = admin.get("/api/health")
        except httpx.ConnectError:
            print(f"\n{VERMELHO}A API não respondeu em {a.url}.{FIM}")
            print("Suba o ambiente com: docker compose up -d")
            return 2

        if not entrar(admin, a.login, a.senha):
            print(f"\n{VERMELHO}Não consegui autenticar como {a.login!r}.{FIM}")
            print('A senha sai no log: docker compose logs api | grep "Senha sorteada"')
            return 2

        assert saude.status_code == 200
        item_banco(r, admin)
        item_login(r, a.url, a.login, a.senha)
        criados = item_cadastro(r, admin, marca)
        item_perfis(r, a.url, criados)
        item_crud(r, a.url, criados, marca)
        periodo_id = item_ingestao(r, a.url, criados, marca)
        item_painel(r, a.url, criados, periodo_id)
        limpar(admin, criados)

    return r.encerrar()


if __name__ == "__main__":
    raise SystemExit(main())
