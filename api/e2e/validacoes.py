"""Transcreve as validações e as mensagens de erro, para servir de evidência.

A quarta entrega da disciplina pede exemplos das validações e evidência das
mensagens de erro; a quinta, os testes das validações e das situações de erro
do segundo módulo — o de previsão, que tem seção própria desde então. Aqui cada
regra é provocada contra a API no ar, e a troca inteira vai para a transcrição:
o que foi enviado, o código que voltou e a mensagem que a tela mostra ao usuário.

Cada troca vem com o que se esperava dela, e o fim da transcrição conta quantas
bateram. Uma evidência que só mostra respostas não diz se elas estão certas.

A última parte derruba o banco por alguns segundos (`docker compose stop
postgres`) para mostrar a **falha inesperada** como o usuário a vê: mensagem
genérica e um identificador de correlação, que é achado no log junto com o
detalhe (RNF18, RNF19). O banco volta no `finally` — uma exceção no meio não
pode deixá-lo parado. Sem contêineres, rode com `--sem-falha`.

Como a transcrição do CRUD, não deixa resíduo (ver `e2e/limpeza.py`).

Uso, da pasta `api/`:
    GIH_ADMIN_SENHA=... python e2e/validacoes.py \
        > ../docs/entrega/evidencias/sprint05/validacoes.txt
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import subprocess
import sys
import time
from datetime import UTC, date, datetime, timedelta

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from e2e.persistencia import RAIZ, api_responde, compose  # noqa: E402
from e2e.transcricao import LARGURA, desfazer, titulo, troca  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SENHA = "validacoes-de-evidencia"
RELATORIO = "Parceiro;Faturamento;Pedidos\nComércio {marca} hist;12500,40;312\n"


class Conferencias:
    """O que se esperava de cada troca, e se veio."""

    def __init__(self) -> None:
        self.itens: list[tuple[str, bool]] = []

    def __call__(
        self, descricao: str, resposta: httpx.Response, codigo: int, *trechos: str
    ) -> httpx.Response:
        ok = resposta.status_code == codigo and all(t in resposta.text for t in trechos)
        self.itens.append((descricao, ok))
        esperado = f"{codigo}" + (f" com {', '.join(repr(t) for t in trechos)}" if trechos else "")
        print(f"  {'ok   ' if ok else 'FALHA'} esperado: {esperado}")
        return resposta

    def registrar(self, descricao: str, ok: bool) -> None:
        self.itens.append((descricao, ok))
        print(f"  {'ok   ' if ok else 'FALHA'} {descricao}")


def enviar_arquivo(
    c: httpx.Client, caminho: str, nome: str, conteudo: bytes, campos: dict
) -> httpx.Response:
    """Como `troca`, para envio de arquivo: o conteúdo binário não vai à transcrição."""
    print(f"\n$ POST {caminho}  (formulário com arquivo)")
    print(f"  > arquivo: {nome}, {len(conteudo)} bytes, começando por {conteudo[:4]!r}")
    for chave, valor in campos.items():
        print(f"  > {chave}: {valor}")
    r = c.post(caminho, files={"arquivo": (nome, conteudo)}, data=campos)
    print(f"  {r.status_code} {r.reason_phrase}")
    for linha in json.dumps(r.json(), ensure_ascii=False, indent=2).splitlines():
        print(f"  < {linha}")
    return r


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--url", default=os.environ.get("GIH_URL", "http://localhost:8000"))
    p.add_argument("--login", default=os.environ.get("GIH_ADMIN_LOGIN", "admin"))
    p.add_argument("--senha", default=os.environ.get("GIH_ADMIN_SENHA", ""))
    p.add_argument("--sem-falha", action="store_true",
                   help="não derrubar o banco para mostrar a falha inesperada")
    a = p.parse_args()

    if not a.senha:
        print("Informe a senha do administrador com --senha ou GIH_ADMIN_SENHA.", file=sys.stderr)
        return 2
    if not api_responde(a.url):
        print(f"A API não responde em {a.url}. Suba com: docker compose up -d", file=sys.stderr)
        return 2

    marca = f"t{secrets.randbelow(100000):05d}"
    confere = Conferencias()
    print(f"Validações e mensagens de erro · {a.url}")
    print("Dados sintéticos; nenhum nome real de empresa ou pessoa.")

    with httpx.Client(base_url=a.url, timeout=30) as admin:
        if admin.post("/api/sessao", json={"login": a.login, "senha": a.senha}).status_code != 201:
            print("Não consegui autenticar como administrador.", file=sys.stderr)
            return 2
        try:
            transcrever(a.url, admin, marca, confere, falha=not a.sem_falha)
        finally:
            limpo = desfazer(admin, marca)

    passaram = sum(ok for _, ok in confere.itens)
    print(f"\n{'=' * LARGURA}")
    print(f"Resultado: {passaram} de {len(confere.itens)} respostas como esperado.")
    return 0 if limpo and passaram == len(confere.itens) else 1


def transcrever(url: str, admin: httpx.Client, marca: str, confere: Conferencias,
                falha: bool) -> None:
    analista, gestor = f"{marca}.analista", f"{marca}.gestor"
    titulo("Preparação — um analista, um gestor, e um parceiro com faturamento importado")
    troca(admin, "POST", "/api/usuarios", {
        "login": analista, "nome": "Analista da Evidência", "senha": SENHA, "perfil": "ANALISTA",
    })
    troca(admin, "POST", "/api/usuarios", {
        "login": gestor, "nome": "Gestor da Evidência", "senha": SENHA, "perfil": "GESTOR",
    })

    with httpx.Client(base_url=url, timeout=30) as c:
        c.post("/api/sessao", json={"login": analista, "senha": SENHA})
        # Um período longe no futuro, que nenhuma base de demonstração tem: a
        # limpeza recusa apagar período que tenha importação de outra pessoa.
        inicio = date.today() + timedelta(days=365 + secrets.randbelow(2000) * 7)
        periodo = {
            "periodo_inicio": inicio.isoformat(),
            "periodo_fim": (inicio + timedelta(days=6)).isoformat(),
        }
        troca(c, "POST", "/api/importacoes", {**periodo, "texto": RELATORIO.format(marca=marca)})
        comhist = c.get(f"/api/parceiros?busca={marca} hist").json()["itens"][0]

        importacao(c, periodo, marca, confere)
        cadastro(c, marca, comhist, confere)
        lista(c, confere)
        limiares(admin, confere)
        acesso(url, c, analista, confere)
        modelo(url, c, gestor, confere)
        if falha:
            falha_inesperada(url, c, confere)


# ------------------------------------------------------------------ importação
def importacao(c: httpx.Client, periodo: dict, marca: str, confere: Conferencias) -> None:
    titulo("[1/7] Importação de relatório (UC03)")
    texto = "Parceiro;Faturamento;Pedidos\nComércio Alfa;12500,40;312\n"

    print("\nRN03 — sem o período, a importação é recusada e diz por quê:")
    confere("período ausente", troca(c, "POST", "/api/importacoes", {"texto": texto}),
            422, "periodo_inicio", "periodo_fim", "RN03")

    print("\nPeríodo com o fim antes do início:")
    invertido = {"periodo_inicio": periodo["periodo_fim"], "periodo_fim": periodo["periodo_inicio"]}
    confere("período invertido",
            troca(c, "POST", "/api/importacoes", {**invertido, "texto": texto}), 422, "anterior")

    print("\nData fora do formato:")
    confere("data em formato errado", troca(c, "POST", "/api/importacoes", {
        "periodo_inicio": "31/12/2026", "periodo_fim": periodo["periodo_fim"], "texto": texto,
    }), 422, "AAAA-MM-DD")

    print("\nUma linha ruim não derruba as outras — a prévia mostra cada rejeição com o motivo:")
    ruim = (
        "Parceiro;Faturamento;Pedidos\n"
        "Comércio Alfa;12500,40;312\n"
        ";900,00;10\n"
        "Comércio Beta;abacaxi;20\n"
        "Comércio Gama;100,00;muitos\n"
    )
    confere("linhas rejeitadas com o motivo",
            troca(c, "POST", "/api/importacoes/previa", {**periodo, "texto": ruim}),
            200, '"total_reconhecido":1', '"total_rejeitado":3')

    print("\nNenhuma linha aproveitável: nada é gravado.")
    # A semana seguinte, ainda livre. No período já importado, a recusa por
    # período repetido viria antes e esconderia esta.
    livre = {
        chave: (date.fromisoformat(valor) + timedelta(days=7)).isoformat()
        for chave, valor in periodo.items()
    }
    confere("relatório sem linha válida", troca(c, "POST", "/api/importacoes", {
        **livre, "texto": "Parceiro;Faturamento;Pedidos\nComércio Alfa;abacaxi;312\n",
    }), 422, "Nenhuma linha válida")

    print("\nPlanilha do Excel enviada no lugar do CSV:")
    xlsx = b"PK\x03\x04\x14\x00\x06\x00" + bytes(56)
    confere("arquivo que não é texto",
            enviar_arquivo(c, "/api/importacoes/arquivo/previa", "relatorio.xlsx", xlsx, periodo),
            422, "exporte como CSV")

    print("\nRF12 — o mesmo período de novo. O padrão é cancelar, e a recusa diz o que seria")
    print("apagado antes de oferecer a substituição:")
    confere("período já importado", troca(c, "POST", "/api/importacoes", {
        **periodo, "texto": RELATORIO.format(marca=marca),
    }), 409, "metricas_que_serao_apagadas")


# -------------------------------------------------------------------- cadastro
def cadastro(c: httpx.Client, marca: str, comhist: dict, confere: Conferencias) -> None:
    titulo("[2/7] Cadastro de parceiro (UC04)")

    print("\nNome vazio — a mensagem diz que é obrigatório e quanto falta:")
    confere("nome vazio", troca(c, "POST", "/api/parceiros", {"nome": ""}),
            422, "Obrigatório: informe ao menos 2 caracteres.")

    print("\nNome curto:")
    confere("nome curto", troca(c, "POST", "/api/parceiros", {"nome": "A"}),
            422, "Curto demais: use ao menos 2 caracteres.")

    print("\nContato longo:")
    confere("contato longo", troca(c, "POST", "/api/parceiros", {
        "nome": f"Comércio {marca}", "contato": "x" * 121,
    }), 422, "Longo demais: use no máximo 120 caracteres.")

    print("\nSituação comercial fora da lista:")
    confere("status fora da lista", troca(c, "POST", "/api/parceiros", {
        "nome": f"Comércio {marca}", "status": "VIP",
    }), 422, "Escolha uma destas opções")

    print("\nCategoria que não existe — erro do campo, e não conflito de nome:")
    confere("categoria inexistente", troca(c, "POST", "/api/parceiros", {
        "nome": f"Comércio {marca}", "categoria_id": 999999,
    }), 422, "categoria_id", "Categoria não encontrada")

    print("\nUC04-E1 — nome em uso: a recusa aponta o parceiro que já o usa:")
    confere("nome em uso", troca(c, "POST", "/api/parceiros", {"nome": comhist["nome"]}),
            409, '"existente"', str(comhist["id"]))

    print("\nExcluir parceiro com faturamento importado apagaria números de períodos já")
    print("fechados. A recusa diz o que impede e aponta a saída — desativar:")
    confere("exclusão com histórico", troca(c, "DELETE", f"/api/parceiros/{comhist['id']}"),
            409, "desative")


# ----------------------------------------------------------------------- lista
def lista(c: httpx.Client, confere: Conferencias) -> None:
    titulo("[3/7] Lista de parceiros — filtros e ordenação vêm da URL")
    print("\nUm link editado à mão chega aqui. A recusa diz o que vale:")
    confere("ordenação desconhecida", troca(c, "GET", "/api/parceiros?ordenar_por=idade"),
            422, "Escolha uma destas opções")
    confere("página zero", troca(c, "GET", "/api/parceiros?pagina=0"),
            422, "Use um valor a partir de 1.")
    confere("página grande demais", troca(c, "GET", "/api/parceiros?tamanho=5000"),
            422, "Use um valor até 200.")


# -------------------------------------------------------------------- limiares
def limiares(admin: httpx.Client, confere: Conferencias) -> None:
    titulo("[4/7] Limiares da segmentação (RF21) — só o administrador")
    print("\nTop 0 esvaziaria o segmento Top da rede inteira. Nada é gravado:")
    confere("Top N zero", troca(admin, "PUT", "/api/configuracao/segmentacao", {
        "top_n": 0, "periodos_tendencia": 2, "periodos_novato": 3,
    }), 422, "top_n", "Use um valor a partir de 1.")


# ---------------------------------------------------------------------- acesso
def acesso(url: str, c: httpx.Client, analista: str, confere: Conferencias) -> None:
    titulo("[5/7] Acesso (RF01, RF03, RNF11)")
    with httpx.Client(base_url=url, timeout=30) as anonimo:
        print("\nSenha errada, e depois um login que não existe. RNF11: as duas respostas são")
        print("iguais — duas mensagens diferentes entregariam a lista de logins válidos.")
        errada = troca(anonimo, "POST", "/api/sessao", {"login": analista, "senha": "outra-senha"})
        confere("senha errada", errada, 401, "Login ou senha inválidos.")
        inexistente = troca(anonimo, "POST", "/api/sessao", {
            "login": "ninguem.com.este.login", "senha": "outra-senha",
        })
        confere("login inexistente", inexistente, 401, "Login ou senha inválidos.")
        confere.registrar("as duas recusas são indistinguíveis",
                          errada.json() == inexistente.json())

        print("\nSem sessão:")
        confere("sem sessão", troca(anonimo, "GET", "/api/parceiros"),
                401, "Sessão inválida ou expirada.")

    print("\nO analista tentando a área de usuários, que é do administrador:")
    confere("perfil sem permissão", troca(c, "GET", "/api/usuarios"),
            403, "Seu perfil não permite esta operação.")


# ------------------------------------------------------------------- modelo
def modelo(url: str, c: httpx.Client, gestor: str, confere: Conferencias) -> None:
    titulo("[6/7] Modelo preditivo (UC07, RN09) — quem treina, e um por vez")
    print("\nO analista lê a previsão no cadastro (RF28), mas não troca o modelo que toda a")
    print("equipe usa (UC07):")
    confere("analista não treina", troca(c, "POST", "/api/modelo/treinos"),
            403, "Seu perfil não permite esta operação.")

    with httpx.Client(base_url=url, timeout=30) as g:
        g.post("/api/sessao", json={"login": gestor, "senha": SENHA})
        print("\nUm treino por vez, travado pelo banco (ADR-010). O segundo pedido chega com o")
        print("primeiro ainda rodando:")
        primeiro = troca(g, "POST", "/api/modelo/treinos")
        segundo = troca(g, "POST", "/api/modelo/treinos")
        confere("segundo treino com o primeiro rodando", segundo, 409,
                "Já existe um treino em andamento.", "Acompanhe o treino atual")

        print("\nUm treino que não existe:")
        confere("treino inexistente", troca(g, "GET", "/api/modelo/treinos/999999"),
                404, "Treino não encontrado.")

        # O treino roda em segundo plano; a limpeza não pode apagar um que ainda
        # esteja gravando.
        if primeiro.status_code == 202:
            limite = time.monotonic() + 180
            while (g.get(f"/api/modelo/treinos/{primeiro.json()['id']}").json()["situacao"]
                   == "EM_ANDAMENTO" and time.monotonic() < limite):
                time.sleep(1)

    print("\nUm parceiro recém-chegado, com menos períodos que a janela da RN09: o cadastro")
    print("não inventa previsão, e diz por quê.")
    curtos = c.get("/api/parceiros", params={"segmento": "RECEM_CHEGADO", "tamanho": 1})
    itens = curtos.json().get("itens", []) if curtos.status_code == 200 else []
    if not itens:
        confere.registrar("há parceiro recém-chegado para mostrar", False)
        return
    confere("previsão sem histórico suficiente",
            troca(c, "GET", f"/api/parceiros/{itens[0]['id']}/previsao"),
            200, '"disponivel":false', "ainda não há previsão", "são necessários 4")


# ----------------------------------------------------------- falha inesperada
def falha_inesperada(url: str, c: httpx.Client, confere: Conferencias) -> None:
    titulo("[7/7] Falha inesperada (RNF18, RNF19) — o banco fora do ar")
    print("\nPara ver o que o usuário vê quando algo quebra de verdade, o banco é parado")
    print("por alguns segundos.")
    desde = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    print("\n$ docker compose stop postgres")
    try:
        for linha in compose("stop", "postgres"):
            print(f"  {linha}")

        print("\nA verificação de saúde separa \"API fora\" de \"banco fora\":")
        troca(c, "GET", "/api/health")

        print("\nUma tela pedindo a lista de parceiros:")
        r = troca(c, "GET", "/api/parceiros?tamanho=1")
        confere("falha inesperada", r, 500, "Não foi possível concluir a operação.", "correlacao")
        corpo = r.json() if r.status_code == 500 else {}
        vazou = [p for p in ("Traceback", "psycopg", "sqlalchemy", "postgres", "5432")
                 if p.lower() in r.text.lower()]
        confere.registrar("a resposta não mostra nada do servidor"
                          + (f" — vazou: {', '.join(vazou)}" if vazou else ""), not vazou)

        correlacao = corpo.get("correlacao", "")
        print(f"\n$ docker compose logs api  (só o que tem {correlacao or 'o identificador'})")
        registro = log_com(correlacao, desde) if correlacao else []
        for linha in registro:
            print(f"  {linha}")
        confere.registrar(
            "o mesmo identificador está no log, com a exceção que ficou fora da resposta",
            len(registro) == 2 and ("Error" in registro[1] or "Exception" in registro[1]),
        )
    finally:
        print("\n$ docker compose start postgres")
        for linha in compose("start", "postgres"):
            print(f"  {linha}")

    inicio = time.monotonic()
    while httpx.get(f"{url}/api/health", timeout=5).json().get("banco") != "ok":
        if time.monotonic() - inicio > 120:
            raise RuntimeError("O banco não voltou em 120 s.")
        time.sleep(1)
    print(f"\nO banco voltou em {time.monotonic() - inicio:.0f} s. A mesma tela, de novo,")
    print("sem reiniciar a API:")
    confere("a API se recupera sozinha", troca(c, "GET", "/api/parceiros?tamanho=1"), 200)


# Linhas da pilha que não são a exceção: o cabeçalho, o encadeamento entre as
# exceções e o endereço de documentação que o SQLAlchemy anexa.
MOLDURA_DA_PILHA = ("Traceback", "The above exception", "During handling", "(Background")
# Onde o registro seguinte começa. O log de acesso (`INFO:`) **não** marca o
# fim: ele vai pela saída padrão, a pilha pela de erro, e a linha do 500 cai no
# meio da pilha — medido, na linha 19 de uma pilha de 160.
PROXIMO_REGISTRO = ("WARNING:", "ERROR:", "[")
INTERCALADAS = ("INFO:",)


def log_com(correlacao: str, desde: str) -> list[str]:
    """As linhas do log da API que ligam a resposta ao evento.

    A primeira linha do registro e a última exceção da pilha — o tipo e a
    mensagem. A pilha inteira tem dezenas de linhas de biblioteca e não diz
    nada que essas duas não digam.

    Não usa `compose()`: o `docker compose logs` separa a saída e a saída de
    erro do contêiner, e juntá-las depois embaralha a ordem — na primeira
    versão, a linha seguinte ao identificador saía sendo o log de acesso, e não
    a pilha. Aqui as duas vão pelo mesmo cano, na ordem em que foram escritas.
    """
    linhas = subprocess.run(
        ["docker", "compose", "logs", "api", "--no-log-prefix", "--since", desde],
        cwd=RAIZ, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
    ).stdout.splitlines()
    for i, linha in enumerate(linhas):
        if correlacao not in linha:
            continue
        excecoes = []
        for seguinte in linhas[i + 1:]:
            if seguinte.startswith(PROXIMO_REGISTRO):
                break
            if seguinte.strip() and not seguinte.startswith(
                (" ", "\t", *MOLDURA_DA_PILHA, *INTERCALADAS)
            ):
                excecoes.append(seguinte.strip())
        return [linha.strip()] + excecoes[-1:]
    return []


if __name__ == "__main__":
    raise SystemExit(main())
