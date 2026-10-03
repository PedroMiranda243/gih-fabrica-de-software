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

**Não deixa resíduo.** O banco é o que a equipe usa para testar e demonstrar, e
cada execução grava nele períodos no futuro. No fim — mesmo se algo estourar no
meio — o que a execução gravou sai do banco, e a verificação confere que o painel
voltou a abrir onde abria. A limpeza vai direto no banco, e não pela API — o
porquê está em `e2e/limpeza.py` —, então a verificação precisa alcançar também o
banco, pelo `DATABASE_URL` do `.env`.

Uso:
    python e2e/verificacao.py
    python e2e/verificacao.py --url http://localhost:8000 --login admin --senha ...

A senha do administrador sai no log do contêiner na primeira subida:
    docker compose logs api | grep "Senha sorteada"
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import secrets
import sys
import time
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

import httpx

# A matriz de permissões vem do módulo de teste, e não é copiada para cá: duas
# cópias divergiriam, e a daqui é a que ninguém olharia.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.guarda_numerica import numeros_sem_origem, sentido_trocado  # noqa: E402
from app.servico_mensagens import termos_internos  # noqa: E402
from e2e.limpeza import LimpezaRecusada, desativar_usuarios, limpar_execucao  # noqa: E402
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
                 busca.status_code == 200 and any(p["id"] == alvo for p in busca.json()["itens"]))

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
        existente = (duplicado.json().get("detail") or {}).get("existente") or {}
        r.checar(
            "a recusa aponta o parceiro que já usa o nome",
            existente.get("id") == alvo,
            "UC04-E1 — a tela oferece abrir o cadastro existente",
        )

        sem_categoria = c.post(
            "/api/parceiros", json={"nome": f"Outro {marca}", "categoria_id": 999999}
        )
        r.checar(
            "categoria inexistente é erro do campo, e não nome duplicado",
            sem_categoria.status_code == 422
            and sem_categoria.json()["campos"][0]["campo"] == "categoria_id",
            "o usuário corrige o campo certo",
        )

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
            com_historico = c.get(
                "/api/parceiros", params={"busca": f"{marca} hist"}
            ).json()["itens"]
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
def item_ingestao(r: Relatorio, url: str, criados: dict[str, str], marca: str) -> int | None:
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
        ja_existe = repetida.json().get("detail", {}).get("ja_existe", {})
        r.checar(
            "a recusa diz quantos registros seriam apagados e quem os trouxe",
            ja_existe.get("metricas_que_serao_apagadas") == 2 and bool(ja_existe.get("autor")),
            "H25",
        )

        # Uma linha só: se substituir somasse em vez de trocar, o total ficaria
        # em três e a checagem abaixo cairia.
        menor = f"Parceiro;Faturamento;Pedidos\nAlfa {marca};777,00;7\n"
        trocada = c.post(
            "/api/importacoes", json={**periodo, "texto": menor, "substituir": True}
        )
        r.checar(
            "com substituir, o período é trocado e não somado",
            trocada.status_code == 201 and trocada.json()["total_gravado"] == 1,
            trocada.text[:70] if trocada.status_code != 201 else "H25",
        )

        # Arquivo, e não texto colado: é o outro caminho de entrada, e ele
        # precisa chegar ao mesmo lugar (H22).
        por_arquivo = c.post(
            "/api/importacoes/arquivo",
            files={"arquivo": (f"{marca}.csv", relatorio_de(marca).encode("utf-8"), "text/csv")},
            data=periodo_de(marca, 2),
        )
        r.checar(
            "importa por arquivo enviado",
            por_arquivo.status_code == 201 and por_arquivo.json()["origem"] == "CSV",
            por_arquivo.text[:70] if por_arquivo.status_code != 201 else "H22",
        )

        historico = c.get("/api/importacoes").json()
        r.checar(
            "o histórico traz o autor de cada importação",
            all(i["autor"]["nome"] for i in historico["itens"]),
            "RF13",
        )
        # Só no período desta execução: o histórico é da base inteira, e uma
        # substituição feita por outra execução — ou por alguém testando a tela —
        # entraria na conta e reprovaria a verificação por algo que não é dela.
        substituidas = [
            i
            for i in historico["itens"]
            if i["metricas_vigentes"] == 0
            and i["periodo"]["data_inicio"] == periodo["periodo_inicio"]
        ]
        r.checar(
            "a importação substituída fica no histórico, com zero métrica vigente",
            len(substituidas) == 1,
            "o rastro sobrevive ao dado",
        )

        documentacao = c.get("/api/docs")
        r.checar("a documentação interativa está no ar", documentacao.status_code == 200,
                 "/api/docs")

    r.nota("a segmentação do período importado é conferida no bloco de segmentação")

    # O id do período volta para a verificação do painel poder consultar
    # **este** período. Sem ele restaria consultar "o mais recente", que numa
    # base com execuções anteriores pode ser o de outra execução.
    #
    # É o período do arquivo, e não o da primeira gravação: aquele foi trocado
    # acima por um relatório de uma linha só, e o painel mostraria um parceiro
    # onde a verificação espera os dois que a importação trouxe.
    if por_arquivo.status_code == 201:
        return por_arquivo.json()["periodo"]["id"]
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


# --------------------------------------------------------------------- extra
def item_segmentacao(
    r: Relatorio, url: str, criados: dict[str, str], periodo_id: int | None
) -> None:
    """Segmentação, distribuição e mobilidade (UC05 · H33, H35 · RN01, RN02).

    O que esta seção prova, e o `pytest` não: que a regra chega **até a resposta
    HTTP**, com a segmentação que a importação disparou na mesma transação. O
    período foi importado dois blocos acima e ninguém chamou reprocessamento
    nenhum — se o segmento não estiver lá, o gancho da importação quebrou.
    """
    r.secao("Segmentação, distribuição e mobilidade")

    login = criados.get("GESTOR")
    if not login or periodo_id is None:
        r.checar("há gestor e período para conferir a segmentação", False)
        return

    with sessao(url) as c:
        if not entrar(c, login, SENHA):
            r.checar("o gestor autentica", False)
            return

        rank = c.get("/api/painel/ranking", params={"periodo_id": periodo_id})
        itens = rank.json().get("itens", []) if rank.status_code == 200 else []
        r.checar(
            "a importação já deixou o período segmentado",
            bool(itens) and all(i.get("segmento") for i in itens),
            "sem reprocessamento manual",
        )

        dist = c.get("/api/painel/segmentos", params={"periodo_id": periodo_id})
        corpo = dist.json() if dist.status_code == 200 else {}
        fatias = corpo.get("itens", [])
        totais = [f["total"] for f in fatias]
        r.checar(
            "a distribuição soma os parceiros do período",
            corpo.get("total") == sum(totais) == len(itens),
            f"{corpo.get('total')} classificados em "
            f"{len(fatias)} segmento{'s' if len(fatias) != 1 else ''}",
        )
        r.checar(
            "a distribuição vem do maior para o menor",
            totais == sorted(totais, reverse=True),
            "sem desempate estável, o gráfico parece mudar sem nada ter mudado",
        )

        # RN01: cada parceiro em **exatamente um** segmento. O banco impede a
        # dupla classificação por restrição de unicidade; isto confirma pelo
        # lado de fora, que é onde o usuário veria o efeito.
        r.checar(
            "cada parceiro recebe exatamente um segmento",
            len({i["parceiro_id"] for i in itens}) == len(itens),
            "RN01",
        )

        mob = c.get("/api/painel/mobilidade", params={"periodo_id": periodo_id})
        mobilidade = mob.json() if mob.status_code == 200 else {}
        n = mobilidade.get("top_n")
        r.checar(
            "a mobilidade responde com o Top N configurado",
            mob.status_code == 200 and isinstance(n, int) and n >= 1,
            f"Top {n}",
        )

        # **RN02, pelo lado de fora.** Quem está dentro do Top N pelo ranking não
        # pode aparecer entre as saídas, mesmo quando o segmento gravado dele é
        # EM_RISCO — que é o caso que a precedência de RN01 cria. Derivar a
        # mobilidade do segmento faria esta verificação falhar.
        dentro = {i["parceiro_id"] for i in itens if i["posicao"] <= (n or 0)}
        saidas = {m["parceiro_id"] for m in mobilidade.get("saidas", [])}
        r.checar(
            "ninguém que está no Top N aparece como saída",
            not (dentro & saidas),
            "RN02 — a mobilidade lê o ranking, não o segmento",
        )


# --------------------------------------------------------------------- extra
def item_recorte(r: Relatorio, url: str, criados: dict[str, str], marca: str) -> None:
    """Filtro, ordenação, paginação e exportação (H36, H38 · RF23, RF25).

    A exportação é conferida **pelo conteúdo do arquivo**, comparada com a lista
    da tela sob os mesmos parâmetros: é a única forma de pegar o dia em que um
    filtro novo entrar numa e não na outra.
    """
    r.secao("Parceiros — recorte, ordenação e exportação")

    login = criados.get("ANALISTA")
    if not login:
        r.checar("há analista para consultar a lista", False)
        return

    with sessao(url) as c:
        if not entrar(c, login, SENHA):
            r.checar("o analista autentica", False)
            return

        pagina = c.get("/api/parceiros", params={"tamanho": 2})
        corpo = pagina.json() if pagina.status_code == 200 else {}
        r.checar(
            "a lista vem paginada, com o total do recorte",
            pagina.status_code == 200
            and len(corpo.get("itens", [])) <= 2
            and corpo.get("total", 0) >= len(corpo.get("itens", [])),
            f"{len(corpo.get('itens', []))} de {corpo.get('total')}",
        )

        ordenada = c.get(
            "/api/parceiros",
            params={"ordenar_por": "faturamento", "descendente": True, "tamanho": 200},
        )
        linhas = ordenada.json().get("itens", []) if ordenada.status_code == 200 else []
        com_metrica = [
            Decimal(i["desempenho"]["faturamento"])
            for i in linhas
            if i["desempenho"]["faturamento"] is not None
        ]
        r.checar(
            "a ordenação por faturamento respeita o sentido pedido",
            bool(com_metrica) and com_metrica == sorted(com_metrica, reverse=True),
            f"{len(com_metrica)} com movimento",
        )
        r.checar(
            "quem não teve métrica no período vai para o fim",
            len(com_metrica) == len(linhas)
            or linhas[-1]["desempenho"]["faturamento"] is None,
            "não é o melhor nem o pior",
        )
        r.checar(
            "ordenar por coluna desconhecida é recusado",
            c.get("/api/parceiros", params={"ordenar_por": "senha_hash"}).status_code == 422,
            "o valor entra num ORDER BY",
        )

        # O mesmo recorte, pelos dois caminhos.
        recorte = {"busca": marca, "ordenar_por": "faturamento", "descendente": True}
        na_tela = [
            i["nome"] for i in c.get("/api/parceiros", params=recorte).json().get("itens", [])
        ]
        arquivo = c.get("/api/parceiros/exportacao.csv", params=recorte)
        no_arquivo = [
            linha["Parceiro"]
            for linha in csv.DictReader(
                io.StringIO(arquivo.content.decode("utf-8-sig")), delimiter=";"
            )
        ]
        r.checar(
            "o arquivo exportado traz exatamente o recorte da tela",
            arquivo.status_code == 200 and bool(na_tela) and no_arquivo == na_tela,
            f"{len(no_arquivo)} linhas",
        )
        r.checar(
            "o arquivo vem pronto para a planilha",
            arquivo.content.startswith(b"\xef\xbb\xbf")
            and "attachment" in arquivo.headers.get("content-disposition", ""),
            "BOM de UTF-8, senão 'Praça' abre como 'PraÃ§a'",
        )


# --------------------------------------------------------------------- extra
def item_configuracao(
    r: Relatorio, url: str, admin: httpx.Client, criados: dict[str, str]
) -> None:
    """Limiares da segmentação (H34 · RF21).

    **Altera e devolve.** O limiar é configuração global: deixá-lo mudado faria a
    próxima execução — e a demonstração — classificar por uma régua que ninguém
    escolheu. A devolução acontece no `finally` e é **conferida**, porque limpeza
    que não se verifica é limpeza que se presume.
    """
    r.secao("Configuração da segmentação")

    atual = admin.get("/api/configuracao/segmentacao")
    original = atual.json() if atual.status_code == 200 else {}
    r.checar(
        "o administrador lê os limiares em vigor",
        atual.status_code == 200 and original.get("top_n", 0) >= 1,
        f"Top {original.get('top_n')} · tendência {original.get('periodos_tendencia')}",
    )
    if atual.status_code != 200:
        return

    limiares = {c: original[c] for c in ("top_n", "periodos_tendencia", "periodos_novato")}

    gestor = criados.get("GESTOR")
    if gestor:
        with sessao(url) as c:
            entrar(c, gestor, SENHA)
            r.checar(
                "o gestor não altera a régua da segmentação",
                c.put("/api/configuracao/segmentacao", json=limiares).status_code == 403,
                "quem mexe aqui reescreve o que 'em risco' significa para a rede",
            )

    r.checar(
        "limiar sem sentido é recusado",
        admin.put(
            "/api/configuracao/segmentacao", json={**limiares, "top_n": 0}
        ).status_code
        == 422,
        "Top 0 não tem ninguém dentro",
    )

    try:
        mudado = admin.put(
            "/api/configuracao/segmentacao",
            json={**limiares, "top_n": limiares["top_n"] + 1},
        )
        corpo = mudado.json() if mudado.status_code == 200 else {}
        r.checar(
            "alterar o limiar reclassifica o período mais recente",
            mudado.status_code == 200
            and corpo.get("top_n") == limiares["top_n"] + 1
            and corpo.get("periodos_reprocessados") == 1,
            "configuração que não se reflete na tela engana quem a mudou",
        )

        trilha = admin.get("/api/auditoria", params={"acao": "SEGMENTACAO_CONFIGURADA"})
        registros = trilha.json().get("itens", []) if trilha.status_code == 200 else []
        r.checar(
            "a alteração fica na trilha, com o valor anterior",
            bool(registros)
            and registros[0].get("detalhes", {}).get("anterior", {}).get("top_n")
            == limiares["top_n"],
            "sem dizer o que era antes, a trilha não responde nada",
        )
    finally:
        admin.put("/api/configuracao/segmentacao", json=limiares)
        devolvido = admin.get("/api/configuracao/segmentacao").json()
        r.checar(
            "o limiar volta ao que era antes da verificação",
            {c: devolvido.get(c) for c in limiares} == limiares,
            "configuração é global: resíduo aqui muda a próxima execução",
        )


# ----------------------------------------------------------------- menu
def item_telas(r: Relatorio, url: str, admin: httpx.Client, criados: dict[str, str]) -> None:
    """O menu de cada perfil vem do servidor, e o histórico chega ao Administrador.

    A interface monta o menu com a lista `telas` da sessão. Se ela prometesse uma
    tela que a rota recusa, o usuário cairia num 403; conferir pela API no ar é
    o que pega uma divergência entre o que o menu mostra e o que o servidor cobra.
    """
    r.secao("Telas por perfil e histórico de importações")

    telas_admin = admin.get("/api/sessao/atual").json().get("telas", [])
    r.checar(
        "o administrador vê usuários e configuração, e não parceiros",
        "usuarios" in telas_admin and "configuracao" in telas_admin
        and "parceiros" not in telas_admin,
        ", ".join(telas_admin),
    )
    historico = admin.get("/api/importacoes", params={"tamanho": 5})
    r.checar(
        "o administrador lê o histórico de importações (RF13)",
        historico.status_code == 200 and "itens" in historico.json(),
        f"{historico.json().get('total', '?')} importações" if historico.status_code == 200 else
        f"HTTP {historico.status_code}",
    )

    analista = criados.get("ANALISTA")
    if analista:
        with sessao(url) as c:
            entrar(c, analista, SENHA)
            telas = c.get("/api/sessao/atual").json().get("telas", [])
            r.checar(
                "o analista vê importação e parceiros, e não usuários",
                "importar" in telas and "parceiros" in telas and "usuarios" not in telas,
                ", ".join(telas),
            )


# ------------------------------------------------------------ sugestão
def item_sugestao(r: Relatorio, url: str, criados: dict[str, str], marca: str) -> None:
    """A sugestão de categoria pelo nome (RN05, H27), contra a base no ar.

    Só consulta: a rota não grava nada. Depende de a base ter as categorias da
    regra — a de demonstração tem —, e diz quando não tem, em vez de reprovar
    por um dado que não é do código.
    """
    r.secao("Sugestão de categoria pelo nome")

    login = criados.get("ANALISTA")
    if not login:
        r.checar("há analista para pedir a sugestão", False)
        return
    with sessao(url) as c:
        entrar(c, login, SENHA)
        ativas = {x["nome"] for x in c.get("/api/categorias", params={"ativa": True}).json()}
        if "Pizzaria" not in ativas:
            r.nota("a base não tem a categoria Pizzaria ativa — sugestão não conferida")
            return
        sugerida = c.get("/api/categorias/sugestao", params={"nome": f"Pizzaria {marca}"}).json()
        r.checar(
            "um nome com a palavra da categoria recebe a sugestão",
            (sugerida.get("categoria") or {}).get("nome") == "Pizzaria",
            f"Pizzaria {marca}",
        )
        ambiguo = c.get(
            "/api/categorias/sugestao", params={"nome": f"Pizzaria e Lanchonete {marca}"}
        ).json()
        r.checar(
            "um nome que aponta duas categorias não recebe nenhuma",
            ambiguo.get("categoria") is None,
            "branco é melhor que palpite",
        )


# ------------------------------------------------------------- modelo
def item_modelo(r: Relatorio, url: str, criados: dict[str, str]) -> None:
    """O módulo de previsão (UC07, RF27, RF28, RN09), contra a base no ar.

    **Roda antes de qualquer importação da execução**, de propósito: o CRUD e a
    ingestão gravam semanas no futuro, e o treino parte do período mais
    recente. Depois delas, a base do treino seria uma semana de verificação com
    dois parceiros — e a previsão de um parceiro da demonstração diria, com
    razão, que ele não aparece no período mais recente. Foi o que a primeira
    execução mostrou.

    O treino desta execução sai na limpeza, com as previsões dele, e a versão em
    uso volta a ser a de antes — conferido no fim.
    """
    r.secao("Modelo preditivo — treino, versão em uso e previsão")

    analista = criados.get("ANALISTA")
    if analista:
        with sessao(url) as c:
            entrar(c, analista, SENHA)
            r.checar(
                "o analista não treina o modelo",
                c.post("/api/modelo/treinos").status_code == 403,
                "treinar muda as previsões de toda a equipe (UC07)",
            )

    gestor = criados.get("GESTOR")
    if not gestor:
        r.checar("há gestor para treinar", False)
        return
    with sessao(url) as c:
        entrar(c, gestor, SENHA)
        estado = c.get("/api/modelo").json()
        r.checar(
            "a tela do modelo diz se dá para treinar e por quê",
            "pode_treinar" in estado and estado.get("periodos_minimos") == 8,
            f"{estado.get('periodos_na_base')} períodos na base; mínimo "
            f"{estado.get('periodos_minimos')} (RN09)",
        )
        if not estado.get("pode_treinar"):
            r.nota(f"treino não conferido: {estado.get('motivo_bloqueio')}")
            return

        pedido = c.post("/api/modelo/treinos")
        if not r.checar(
            "o treino é aceito e roda fora da requisição",
            pedido.status_code == 202 and pedido.json().get("situacao") == "EM_ANDAMENTO",
            f"HTTP {pedido.status_code}",
        ):
            return
        treino_id = pedido.json()["id"]

        segundo = c.post("/api/modelo/treinos")
        andamento = c.get(f"/api/modelo/treinos/{treino_id}").json().get("situacao")
        if andamento == "EM_ANDAMENTO" or segundo.status_code == 409:
            r.checar(
                "um segundo treino, com o primeiro rodando, é recusado",
                segundo.status_code == 409,
                "um treino por vez, travado pelo banco (ADR-010)",
            )
        else:
            r.nota("o primeiro treino terminou antes do segundo pedido; trava não conferida")

        limite = time.monotonic() + 180
        treino = c.get(f"/api/modelo/treinos/{treino_id}").json()
        while treino.get("situacao") == "EM_ANDAMENTO" and time.monotonic() < limite:
            time.sleep(1)
            treino = c.get(f"/api/modelo/treinos/{treino_id}").json()
        metricas = treino.get("metricas", {})
        volume = treino.get("volume", {})
        if not r.checar(
            "o treino termina e registra data, volume e métricas (RF27)",
            treino.get("situacao") == "CONCLUIDO"
            and treino.get("concluido_em") is not None
            and (volume.get("amostras_teste") or 0) > 0
            and metricas.get("mape_modelo") is not None,
            f"{volume.get('parceiros')} parceiros · {volume.get('periodos')} períodos · "
            f"{treino.get('segundos')} s".replace(".", ",") if treino.get("situacao") == "CONCLUIDO"
            else f"{treino.get('situacao')}: {treino.get('motivo')}",
        ):
            return

        melhor = min(metricas["mape_ultimo"], metricas["mape_media_movel"])
        r.checar(
            "a versão em uso é a que venceu as referências, ou a anterior com o motivo (UC07-A1)",
            (treino["promovido"] and treino["versao_em_uso"] == treino["versao"])
            or (not treino["promovido"] and bool(treino.get("motivo"))),
            f"rede {metricas['mape_modelo']:.1%} contra {melhor:.1%} da melhor referência; "
            f"em uso: {treino['versao_em_uso']}".replace(".", ","),
        )

    if analista:
        with sessao(url) as c:
            entrar(c, analista, SENHA)
            # O maior do período mais recente: está nele, então tem previsão.
            maior = {"tamanho": 1, "ordenar_por": "faturamento", "descendente": True}
            lista = c.get("/api/parceiros", params=maior)
            itens = lista.json().get("itens", []) if lista.status_code == 200 else []
            if not itens:
                r.nota("não há parceiro na base para ler a previsão")
                return
            previsao = c.get(f"/api/parceiros/{itens[0]['id']}/previsao").json()
            disponivel = previsao.get("disponivel") is True
            r.checar(
                "o cadastro do parceiro mostra a previsão, com base e versão (RF28)",
                disponivel
                and previsao.get("modelo_versao") == treino["versao_em_uso"]
                and 0 <= (previsao.get("probabilidade_queda") or -1) <= 1,
                f"{itens[0]['nome']}: R$ "
                + str(previsao["faturamento_previsto"]).replace(".", ",")
                + f" previstos, risco de {previsao['probabilidade_queda']:.0%}"
                if disponivel
                else f"{itens[0]['nome']}: {previsao.get('motivo')}",
            )


# ------------------------------------------------------------- campanha
def _aguardar(c: httpx.Client, execucao_id: int) -> dict:
    limite = time.monotonic() + 180
    execucao = c.get(f"/api/otimizacoes/{execucao_id}").json()
    while execucao.get("situacao") == "EM_ANDAMENTO" and time.monotonic() < limite:
        time.sleep(1)
        execucao = c.get(f"/api/otimizacoes/{execucao_id}").json()
    return execucao


def _reais(valor) -> str:
    return "R$ " + f"{float(valor):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _plano(execucao: dict) -> list[tuple[int, int]]:
    return sorted((i["parceiro_id"], i["acao_id"]) for i in execucao.get("itens") or [])


def _segundos(execucao: dict) -> str:
    return f"{(execucao.get('tempo_ms') or 0) / 1000:.2f} s".replace(".", ",")


def item_campanha(r: Relatorio, url: str, criados: dict[str, str]) -> None:
    """O plano de campanha (UC08, RF29 a RF32, RN07, RN10, RN11), contra a base no ar.

    Roda logo depois do modelo e antes de qualquer importação da execução, pelo
    mesmo motivo: o plano usa as previsões da versão em uso, e uma semana de
    verificação no futuro não tem previsão. As execuções saem na limpeza.
    """
    r.secao("Campanha — plano viável, cotas e recusa com o que falta")

    analista = criados.get("ANALISTA")
    if analista:
        with sessao(url) as c:
            entrar(c, analista, SENHA)
            consulta = c.get("/api/campanha")
            calculo = c.post("/api/otimizacoes", json={})
            r.checar(
                "o analista consulta a campanha, mas não calcula o plano",
                consulta.status_code == 200 and calculo.status_code == 403,
                "o plano decide onde vai a verba (UC08)",
            )

    gestor = criados.get("GESTOR")
    if not gestor:
        r.checar("há gestor para calcular", False)
        return
    with sessao(url) as c:
        entrar(c, gestor, SENHA)
        estado = c.get("/api/campanha").json()
        excluidos = estado.get("excluidos") or {}
        r.checar(
            "a tela diz quantos parceiros entram e quantos ficam fora, e por quê (RN11)",
            estado.get("elegiveis", 0) > 0 and "historico_curto" in excluidos,
            f"{estado.get('elegiveis')} elegíveis; fora: "
            + ", ".join(f"{n} {m.replace('_', ' ')}" for m, n in excluidos.items() if n),
        )
        if not estado.get("pode_executar"):
            r.nota(f"plano não conferido: {estado.get('motivo_bloqueio')}")
            return

        parametros = {
            "orcamento": "5000.00",
            "maximo_acoes": 30,
            "cota_cauda_longa": "0.3",
            "aplicacao_inicio": "2026-10-05",
            "aplicacao_fim": "2026-10-11",
        }
        # O primeiro no serial, que é o baseline e leva segundos: é ele que dá
        # tempo de conferir a trava. O automático viria depois.
        pedido = c.post("/api/otimizacoes", json={**parametros, "modo": "SERIAL"})
        if not r.checar(
            "o cálculo é aceito e roda fora da requisição",
            pedido.status_code == 202 and pedido.json().get("situacao") == "EM_ANDAMENTO",
            f"HTTP {pedido.status_code}",
        ):
            return
        segundo = c.post("/api/otimizacoes", json=parametros)
        execucao_id = pedido.json()["id"]
        if c.get(f"/api/otimizacoes/{execucao_id}").json().get("situacao") == "EM_ANDAMENTO" or (
            segundo.status_code == 409
        ):
            r.checar(
                "um segundo cálculo, com o primeiro rodando, é recusado",
                segundo.status_code == 409,
                "um otimizador por vez, travado pelo banco (ADR-011)",
            )
        else:
            r.nota("o primeiro cálculo terminou antes do segundo pedido; trava não conferida")

        plano = _aguardar(c, execucao_id)
        itens = plano.get("itens") or []
        custo = sum(float(i["custo"]) for i in itens)
        na_cauda = sum(1 for i in itens if i["cauda_longa"])
        if not r.checar(
            "o plano respeita orçamento, máximo de ações e cota da cauda longa (RN07)",
            plano.get("situacao") == "CONCLUIDA"
            and plano.get("viavel") is True
            and len(itens) <= 30
            and len({i["parceiro_id"] for i in itens}) == len(itens)
            and custo <= 5000
            and na_cauda >= 9,
            f"{len(itens)} ações · {_reais(custo)} de {_reais(5000)} · {na_cauda} na cauda longa"
            if plano.get("viavel")
            else f"{plano.get('situacao')}: {plano.get('motivo')}",
        ):
            return
        r.checar(
            "o ganho do plano não fica abaixo do guloso, e sai da previsão em uso (RN10)",
            float(plano["uplift_total"]) >= float(plano["ganho_guloso"])
            and plano["modelo_versao"] == estado["modelo_versao"],
            f"ganho de {_reais(plano['uplift_total'])} contra {_reais(plano['ganho_guloso'])} do "
            f"guloso, em " + f"{plano['tempo_ms'] / 1000:.1f} s".replace(".", ","),
        )

        disponiveis = [m["modo"] for m in estado.get("modos", []) if m["disponivel"]]
        automatico = c.post("/api/otimizacoes", json=parametros)
        sem_escolha = _aguardar(c, automatico.json()["id"]) if automatico.status_code == 202 else {}
        r.checar(
            "sem escolha, roda o primeiro modo disponível — GPU, CPU paralelo, serial —, com o "
            "mesmo plano do serial (RF32)",
            sem_escolha.get("modo") == estado.get("modo_automatico")
            and disponiveis[:1] == [sem_escolha.get("modo")]
            and sem_escolha.get("situacao") == "CONCLUIDA"
            and _plano(sem_escolha) == _plano(plano),
            f"disponíveis: {', '.join(disponiveis)}; {sem_escolha.get('modo')} em "
            f"{_segundos(sem_escolha)}"
            + (f" com {sem_escolha['threads']} threads" if sem_escolha.get("threads") else "")
            + f", contra {_segundos(plano)} do serial",
        )

        # Os dois planos têm os mesmos parâmetros, menos o modo pedido: a comparação
        # precisa dizer só isso, e nenhum parceiro diferente (RF35, ADR-011).
        comparacao = c.get(
            "/api/otimizacoes/comparacao",
            params={"a": plano.get("id"), "b": sem_escolha.get("id")},
        )
        dados = comparacao.json() if comparacao.status_code == 200 else {}
        resumo = dados.get("resumo", {})
        r.checar(
            "dois planos lado a lado dizem o que mudou: só o modo, e nenhum parceiro (RF35)",
            dados.get("parametros_diferentes") == ["modo"]
            and resumo.get("mudaram") == resumo.get("so_a") == resumo.get("so_b") == 0
            and resumo.get("iguais") == len(plano.get("itens") or []),
            f"{resumo.get('iguais')} parceiros iguais nos dois"
            if dados
            else f"HTTP {comparacao.status_code}",
        )

        inviavel = c.post(
            "/api/otimizacoes",
            json={**parametros, "orcamento": "100.00", "cota_cauda_longa": "0.5"},
        )
        recusa = _aguardar(c, inviavel.json()["id"]) if inviavel.status_code == 202 else {}
        r.checar(
            "a campanha inviável é registrada sem plano, dizendo o que falta (RN07, UC08-A1)",
            recusa.get("viavel") is False
            and recusa.get("restricao_violada") == "orcamento"
            and "faltam" in (recusa.get("motivo") or "")
            and not recusa.get("itens"),
            recusa.get("motivo") or f"HTTP {inviavel.status_code}",
        )

        historico = c.get("/api/otimizacoes", params={"tamanho": 10}).json().get("itens", [])
        deste = {e["id"]: e for e in historico}
        calculadas = [execucao_id, sem_escolha.get("id"), recusa.get("id")]
        r.checar(
            "o histórico traz cada execução com autor, parâmetros, modo, tempo e resultado (RF34)",
            all(i in deste for i in calculadas)
            and all(
                deste[i]["autor"] and deste[i]["parametros"] and deste[i]["modo"]
                and deste[i]["tempo_ms"] is not None and deste[i]["viavel"] is not None
                for i in calculadas
            ),
            f"as {len(calculadas)} desta verificação entre as {len(historico)} mais recentes",
        )

    administrador = criados.get("ADMINISTRADOR")
    if administrador:
        with sessao(url) as c:
            entrar(c, administrador, SENHA)
            lista = c.get("/api/otimizacoes")
            plano_dele = c.get(f"/api/otimizacoes/{execucao_id}")
            r.checar(
                "o administrador vê o histórico, mas não abre o plano (RF34, UC08)",
                lista.status_code == 200 and plano_dele.status_code == 403,
                f"histórico HTTP {lista.status_code}; plano HTTP {plano_dele.status_code}",
            )


def _csv(resposta: httpx.Response) -> list[list[str]]:
    """As linhas de um CSV exportado; lista vazia se a resposta não for um arquivo."""
    if resposta.status_code != 200:
        return []
    return list(csv.reader(io.StringIO(resposta.content.decode("utf-8-sig")), delimiter=";"))


def item_recorte_do_painel(r: Relatorio, url: str, admin: httpx.Client, criados: dict) -> None:
    """O painel por período e categoria, e a previsão e a campanha dentro dele (H82, H83).

    Roda depois da campanha e antes das importações da execução, como ela: o
    bloco fala do último plano viável e da previsão da versão em uso.
    """
    r.secao("Painel — o recorte por período e categoria, e os três módulos")

    login = criados.get("ANALISTA")
    if not login:
        r.checar("há analista para consultar o painel", False)
        return
    with sessao(url) as c:
        entrar(c, login, SENHA)
        recortes = c.get("/api/painel/recortes").json()
        periodos, categorias = recortes.get("periodos", []), recortes.get("categorias", [])
        if len(periodos) < 2 or not categorias:
            r.checar("há mais de um período e ao menos uma categoria para recortar", False)
            return
        r.checar(
            "o painel oferece os períodos do mais recente ao mais antigo, e as categorias",
            [p["data_inicio"] for p in periodos]
            == sorted((p["data_inicio"] for p in periodos), reverse=True),
            f"{len(periodos)} períodos, {len(categorias)} categorias",
        )

        antigo, categoria = periodos[1], categorias[0]
        filtro = {"periodo_id": antigo["id"], "categoria_id": categoria["id"]}
        ind = c.get("/api/painel/indicadores", params=filtro).json()
        ranking = c.get("/api/painel/ranking", params={**filtro, "tamanho": 200}).json()
        r.checar(
            "os indicadores do recorte são a soma do ranking do mesmo recorte",
            (ind.get("categoria") or {}).get("id") == categoria["id"]
            and ind["periodo"]["id"] == antigo["id"]
            and sum(Decimal(i["faturamento"]) for i in ranking["itens"])
            == Decimal(ind["faturamento"])
            and ranking["total"] == ind["parceiros_ativos"],
            f"{categoria['nome']}: R$ {ind.get('faturamento')} em {ind.get('parceiros_ativos')}"
            " parceiros",
        )

        # RN02: a categoria escolhe quem aparece, e não renumera.
        da_rede = {}
        pagina = 1
        while True:
            parte = c.get(
                "/api/painel/ranking",
                params={"periodo_id": antigo["id"], "tamanho": 200, "pagina": pagina},
            ).json()
            da_rede.update({i["parceiro_id"]: i["posicao"] for i in parte["itens"]})
            if len(da_rede) >= parte["total"] or not parte["itens"]:
                break
            pagina += 1
        posicoes = [i["posicao"] for i in ranking["itens"]]
        r.checar(
            "no ranking da categoria, a posição é a do ranking da rede (RN02)",
            bool(posicoes)
            and all(da_rede.get(i["parceiro_id"]) == i["posicao"] for i in ranking["itens"])
            and posicoes == sorted(posicoes),
            f"posições {posicoes[0]} a {posicoes[-1]}, entre {len(da_rede)}" if posicoes else "",
        )

        serie = c.get("/api/painel/series", params=filtro).json()
        r.checar(
            "a série do recorte é da categoria e termina no período escolhido",
            serie["escopo"] == "categoria"
            and serie["pontos"][-1]["periodo"]["id"] == antigo["id"]
            and serie["pontos"][-1]["faturamento"] == ind["faturamento"],
            f"{len(serie['pontos'])} períodos",
        )
        r.checar(
            "categoria que não existe é recusada, e não vira a rede inteira",
            c.get("/api/painel/indicadores", params={"categoria_id": 999999}).status_code == 404,
            "404",
        )

        decisao = c.get("/api/painel/decisao")
        corpo = decisao.json() if decisao.status_code == 200 else {}
        previsao, campanha = corpo.get("previsao", {}), corpo.get("campanha", {})
        r.checar(
            "o painel traz o previsto ao lado do medido, nos mesmos parceiros",
            previsao.get("disponivel") is True and previsao.get("parceiros", 0) > 0,
            f"previsto R$ {previsao.get('faturamento_previsto')} · medido R$"
            f" {previsao.get('faturamento_medido')} · {previsao.get('parceiros')} parceiros",
        )
        maior = (previsao.get("maior_risco") or [None])[0]
        do_cadastro = (
            c.get(f"/api/parceiros/{maior['parceiro_id']}/previsao").json() if maior else {}
        )
        riscos = [p["probabilidade_queda"] for p in previsao.get("maior_risco", [])]
        r.checar(
            "o maior risco do painel é o da previsão no cadastro do parceiro",
            bool(maior)
            and abs(maior["probabilidade_queda"] - do_cadastro.get("probabilidade_queda", -1))
            < 1e-9
            and riscos == sorted(riscos, reverse=True),
            f"{maior['nome']}: {maior['probabilidade_queda']:.2f}" if maior else "",
        )
        ultimo = c.get("/api/otimizacoes", params={"resultado": "VIAVEL", "tamanho": 1}).json()
        r.checar(
            "a campanha do painel é o último plano viável do histórico",
            bool(ultimo["itens"])
            and (campanha.get("plano") or {}).get("execucao_id") == ultimo["itens"][0]["id"]
            and campanha.get("acoes") == ultimo["itens"][0]["acoes"],
            f"execução {(campanha.get('plano') or {}).get('execucao_id')},"
            f" {campanha.get('acoes')} ações",
        )
    r.checar(
        "o administrador lê o painel, e não recebe a previsão e a campanha",
        admin.get("/api/painel/indicadores").status_code == 200
        and admin.get("/api/painel/decisao").status_code == 403,
        "o bloco é a soma do que ele não abre",
    )


def item_relatorios(r: Relatorio, url: str, admin: httpx.Client, criados: dict) -> None:
    """Os quatro relatórios, cada um contra a tela que resume, e o CSV de cada um
    (UC15 · RF44 a RF48 · H84 a H88).

    Um relatório que só mostra números não diz se eles estão certos. Aqui cada
    um é comparado com o que o painel, o cadastro, o plano e a trilha dizem.
    """
    r.secao("Relatórios — conferidos contra as telas que resumem, e o CSV de cada um")

    login = criados.get("ANALISTA")
    if not login:
        r.checar("há analista para abrir os relatórios", False)
        return
    with sessao(url) as c:
        entrar(c, login, SENHA)

        rel = c.get("/api/relatorios/desempenho").json()
        painel = c.get("/api/painel/indicadores").json()
        total = rel["total"]
        r.checar(
            "desempenho: o total é o indicador do painel no mesmo período",
            total["faturamento"] == painel["faturamento"]
            and total["parceiros"] == painel["parceiros_ativos"]
            and total["ticket_medio"] == painel["ticket_medio"]
            and total["variacao_percentual"] == painel["variacao"]["faturamento"],
            f"R$ {total['faturamento']} em {total['parceiros']} parceiros",
        )
        iguais = [
            linha["faturamento"]
            == c.get("/api/painel/indicadores", params={"categoria_id": linha["chave"]}).json()[
                "faturamento"
            ]
            for linha in rel["por_categoria"]
            if linha["chave"] is not None
        ]
        r.checar(
            "desempenho: cada categoria é o painel filtrado por ela, e elas somam o total",
            bool(iguais)
            and all(iguais)
            and sum(Decimal(linha["faturamento"]) for linha in rel["por_categoria"])
            == Decimal(total["faturamento"]),
            f"{len(iguais)} categorias",
        )
        segmentos = c.get("/api/painel/segmentos").json()
        r.checar(
            "desempenho: cada segmento tem os parceiros que o painel conta nele",
            {linha["chave"]: linha["parceiros"] for linha in rel["por_segmento"]}
            == {fatia["segmento"]: fatia["total"] for fatia in segmentos["itens"]},
            f"{len(rel['por_segmento'])} segmentos",
        )
        arquivo = _csv(c.get("/api/relatorios/desempenho/exportacao.csv"))
        r.checar(
            "desempenho: o CSV traz as categorias, os segmentos e o total da tela",
            len(arquivo) - 1 == len(rel["por_categoria"]) + len(rel["por_segmento"]) + 1
            and arquivo[-1][3] == total["faturamento"].replace(".", ","),
            f"{len(arquivo) - 1} linhas",
        )

        risco = c.get("/api/relatorios/risco", params={"tamanho": 200}).json()
        com_risco = [i for i in risco["itens"] if i["probabilidade_queda"] is not None]
        chances = [i["probabilidade_queda"] for i in com_risco]
        do_cadastro = (
            c.get(f"/api/parceiros/{com_risco[0]['parceiro_id']}/previsao").json()
            if com_risco
            else {}
        )
        r.checar(
            "risco: do maior para o menor, e o primeiro é a previsão do cadastro dele",
            risco["disponivel"] is True
            and bool(chances)
            and chances == sorted(chances, reverse=True)
            and abs(chances[0] - do_cadastro.get("probabilidade_queda", -1)) < 1e-9,
            f"{risco['total']} parceiros, {risco['com_previsao']} com previsão",
        )
        # Os recém-chegados não têm a janela de histórico que a previsão exige, e
        # ficam no fim da ordem por risco: é entre eles que se acha quem não tem.
        novatos = c.get(
            "/api/relatorios/risco", params={"segmento": "RECEM_CHEGADO", "tamanho": 200}
        ).json()
        sem = [i for i in novatos["itens"] if i["probabilidade_queda"] is None]
        r.checar(
            "risco: quem não tem previsão vem com o motivo, e não com zero (RN09)",
            bool(sem)
            and all(i["sem_previsao"] and i["faturamento_previsto"] is None for i in sem)
            and all(i["sem_previsao"] is None for i in com_risco),
            f"{len(sem)} recém-chegados sem previsão: {sem[0]['sem_previsao']}" if sem else "",
        )
        filtrado = c.get("/api/relatorios/risco", params={"risco_minimo": 0.5}).json()
        arquivo = _csv(c.get("/api/relatorios/risco/exportacao.csv", params={"risco_minimo": 0.5}))
        r.checar(
            "risco: o CSV é o recorte inteiro, com o filtro da tela",
            all(i["probabilidade_queda"] >= 0.5 for i in filtrado["itens"])
            and len(arquivo) - 1 == filtrado["total"],
            f"{filtrado['total']} com chance a partir de 50%",
        )

        camp = c.get("/api/relatorios/campanha").json()
        do_plano = (camp["plano"] or {}).get("execucao_id")
        plano = c.get(f"/api/otimizacoes/{do_plano}").json() if do_plano else {}
        itens = plano.get("itens") or []
        r.checar(
            "campanha: o relatório soma o plano gravado, e cada agrupamento soma o total",
            bool(itens)
            and camp["total"]["parceiros"] == len(itens)
            and Decimal(camp["total"]["custo"]) == sum(Decimal(i["custo"]) for i in itens)
            and Decimal(camp["total"]["ganho_esperado"]) == sum(Decimal(i["ganho"]) for i in itens)
            and all(
                sum(Decimal(linha["custo"]) for linha in camp[grupo])
                == Decimal(camp["total"]["custo"])
                for grupo in ("por_acao", "por_categoria", "por_segmento")
            ),
            f"{len(itens)} ações, custo R$ {camp['total']['custo']}" if itens else "sem plano",
        )
        if itens:
            arquivo = _csv(c.get(f"/api/otimizacoes/{plano['id']}/exportacao.csv"))
            r.checar(
                "campanha: o CSV do plano tem uma linha por item, na ordem da tela (RF53)",
                [linha[0] for linha in arquivo[1:-1]] == [i["parceiro"] for i in itens]
                and arquivo[-1][0] == "Total",
                f"{len(arquivo) - 2} itens",
            )
        r.checar(
            "o analista não abre o relatório de operações",
            c.get("/api/relatorios/operacoes").status_code == 403,
            "é do administrador",
        )

    ops = admin.get("/api/relatorios/operacoes").json()
    trilha = admin.get("/api/auditoria", params={"de": ops["de"], "ate": ops["ate"]}).json()
    outras = (ops["outras_pessoas"] or {}).get("total", 0)
    r.checar(
        "operações: o total é o da trilha no mesmo intervalo, e cada agrupamento o soma",
        ops["total"] == trilha["total"]
        and sum(linha["total"] for linha in ops["por_acao"]) == ops["total"]
        and sum(linha["total"] for linha in ops["por_usuario"]) + outras == ops["total"]
        and sum(linha["total"] for linha in ops["por_dia"]) == ops["total"],
        f"{ops['total']} operações de {ops['de']} a {ops['ate']}",
    )
    arquivo = _csv(admin.get("/api/relatorios/operacoes/exportacao.csv"))
    r.checar(
        "operações: o CSV traz todas as pessoas, que a tela resume",
        sum(linha[0] == "Usuário" for linha in arquivo) == ops["pessoas"]
        and ops["pessoas"] >= len(ops["por_usuario"]),
        f"{ops['pessoas']} pessoas, {len(ops['por_usuario'])} na tela",
    )
    r.checar(
        "o administrador não abre os relatórios da rede",
        admin.get("/api/relatorios/desempenho").status_code == 403
        and admin.get("/api/relatorios/risco").status_code == 403
        and admin.get("/api/relatorios/campanha").status_code == 403,
        "são do gestor e do analista",
    )


def item_trilha(r: Relatorio, url: str, admin: httpx.Client, criados: dict, marca: str) -> None:
    """A trilha de auditoria lida, o histórico do cadastro e os filtros das listas
    (H89, H90, H91 · RF49 a RF52).
    """
    r.secao("Trilha de auditoria, histórico do cadastro e filtros das listas")

    acoes = admin.get("/api/auditoria/acoes").json()
    r.checar(
        "toda ação da trilha tem rótulo em português",
        len(acoes) > 30 and all(a["rotulo"] and a["rotulo"] != a["acao"] for a in acoes),
        f"{len(acoes)} ações",
    )

    login = criados.get("ANALISTA")
    if not login:
        r.checar("há analista para alterar um parceiro", False)
        return
    with sessao(url) as c:
        entrar(c, login, SENHA)
        categorias = c.get("/api/categorias").json()
        criado = c.post("/api/parceiros", json={"nome": f"Histórico {marca}"})
        alvo = criado.json()["id"]
        c.patch(f"/api/parceiros/{alvo}", json={"nome": f"Histórico Novo {marca}"})
        if categorias:
            c.patch(f"/api/parceiros/{alvo}", json={"categoria_id": categorias[0]["id"]})
        eventos = c.get(f"/api/parceiros/{alvo}/historico").json()
        r.checar(
            "o cadastro do parceiro mostra o que mudou nele, do mais recente ao mais antigo",
            [e["acao"] for e in eventos][-2:] == ["PARCEIRO_EDITADO", "PARCEIRO_CRIADO"]
            and eventos[-2]["resumo"] == f"nome de Histórico {marca} para Histórico Novo {marca}"
            and all(
                set(e) == {"acao", "rotulo", "resumo", "autor", "ocorrido_em"} for e in eventos
            ),
            f"{len(eventos)} eventos, sem a origem nem os parâmetros crus",
        )
        if categorias:
            r.checar(
                "a troca de categoria diz de qual para qual, pelo nome",
                eventos[0]["resumo"] == f"categoria de sem categoria para {categorias[0]['nome']}",
                eventos[0]["resumo"],
            )
        r.checar(
            "o analista não consulta a trilha inteira",
            c.get("/api/auditoria").status_code == 403,
            "é do administrador (RF08)",
        )

        viaveis, inviaveis = (
            c.get("/api/otimizacoes", params={"resultado": resultado, "tamanho": 50}).json()
            for resultado in ("VIAVEL", "INVIAVEL")
        )
        r.checar(
            "o histórico de execuções filtra pelo resultado (RF51)",
            bool(viaveis["itens"])
            and all(e["viavel"] is True for e in viaveis["itens"])
            and all(e["viavel"] is False for e in inviaveis["itens"]),
            f"{viaveis['total']} viáveis, {inviaveis['total']} inviáveis",
        )

    trilha = admin.get("/api/auditoria", params={"busca": f"Histórico Novo {marca}"}).json()
    r.checar(
        "a busca na trilha acha as alterações pelo nome do parceiro, com autor e frase (RF49)",
        trilha["total"] >= 1
        and all(
            reg["autor"] and reg["rotulo"] and marca in reg["resumo"] for reg in trilha["itens"]
        ),
        f"{trilha['total']} registros",
    )
    arquivo = _csv(
        admin.get("/api/auditoria/exportacao.csv", params={"busca": f"Histórico Novo {marca}"})
    )
    r.checar(
        "o CSV da trilha traz o recorte da busca",
        len(arquivo) - 1 == trilha["total"],
        f"{len(arquivo) - 1} linhas",
    )
    usuarios = admin.get("/api/usuarios", params={"busca": marca}).json()
    sem_acento = admin.get("/api/usuarios", params={"busca": "verificacao", "ativo": True}).json()
    r.checar(
        "a busca de usuários acha pelo login e ignora o acento do nome (RF52)",
        {u["login"] for u in usuarios} == set(criados.values())
        and {u["login"] for u in usuarios} <= {u["login"] for u in sem_acento},
        f"{len(usuarios)} pelo login, {len(sem_acento)} por \"verificacao\"",
    )


def _tempo(segundos: float) -> str:
    texto = f"{segundos:.2f} s" if segundos >= 1 else f"{segundos * 1000:.1f} ms"
    return texto.replace(".", ",")


def _aguardar_benchmark(c: httpx.Client, execucao_id: int) -> dict:
    limite = time.monotonic() + 300
    execucao = c.get(f"/api/benchmarks/{execucao_id}").json()
    while execucao.get("situacao") == "EM_ANDAMENTO" and time.monotonic() < limite:
        time.sleep(1)
        execucao = c.get(f"/api/benchmarks/{execucao_id}").json()
    return execucao


def item_benchmark(r: Relatorio, url: str, criados: dict[str, str]) -> None:
    """O benchmark (UC09, RF33), no menor cenário: o mesmo problema em cada modo desta
    instalação, e o mesmo plano em todos. O benchmark sai na limpeza."""
    r.secao("Benchmark — o mesmo problema em cada modo, com o mesmo plano")

    analista = criados.get("ANALISTA")
    if analista:
        with sessao(url) as c:
            entrar(c, analista, SENHA)
            r.checar(
                "o analista não tem o benchmark (UC09)",
                c.get("/api/benchmark").status_code == 403,
            )

    gestor = criados.get("GESTOR")
    if not gestor:
        r.nota("sem gestor criado, o benchmark não foi disparado")
        return
    with sessao(url) as c:
        entrar(c, gestor, SENHA)
        estado = c.get("/api/benchmark").json()
        disponiveis = [m["coluna"] for m in estado.get("colunas", []) if m["disponivel"]]
        pedido = c.post("/api/benchmarks", json={"parceiros": 100, "acoes": 2, "repeticoes": 1})
        execucao = _aguardar_benchmark(c, pedido.json()["id"]) if pedido.status_code == 202 else {}
        colunas = execucao.get("colunas", [])
        medidas = [col for col in colunas if col["situacao"] == "MEDIDA"]
        r.checar(
            "mede cada modo desta instalação, com o mesmo plano em todos (RF33, RNF02)",
            execucao.get("situacao") == "CONCLUIDA"
            and [col["coluna"] for col in medidas] == disponiveis
            and all(col["diferenca_uplift"] == 0 for col in medidas),
            ", ".join(f"{col['coluna']} em {_tempo(col['media_s'])}" for col in medidas)
            or f"HTTP {pedido.status_code}: {execucao.get('motivo') or pedido.text[:120]}",
        )
        fora = [col for col in colunas if col["situacao"] != "MEDIDA"]
        r.checar(
            "o modo que falta nesta máquina diz por quê (UC09-A1)",
            all(col["motivo"] for col in fora),
            "; ".join(f"{col['coluna']}: {col['motivo']}" for col in fora) or "nenhum falta",
        )
        series = (execucao.get("escalabilidade") or {}).get("series", [])
        r.checar(
            "o gráfico de escalabilidade traz o tamanho medido (UC09, passo 7)",
            any(p["execucao_id"] == execucao.get("id") for s in series for p in s["pontos"]),
            f"{len(series)} série(s)",
        )


def _aguardar_lote(c: httpx.Client, lote_id: int) -> dict:
    # Com o modelo de linguagem, a primeira mensagem paga o carregamento (~45 s),
    # e cada uma das outras leva de 2 a 4 s (ADR-013).
    limite = time.monotonic() + 900
    lote = c.get(f"/api/mensagens/lotes/{lote_id}").json()
    while lote.get("situacao") == "EM_ANDAMENTO" and time.monotonic() < limite:
        time.sleep(2)
        lote = c.get(f"/api/mensagens/lotes/{lote_id}").json()
    return lote


def item_conta(
    r: Relatorio, url: str, admin: httpx.Client, criados: dict[str, str], marca: str
) -> None:
    """A conta, a senha, o vínculo do parceiro e a ajuda (RF07, RF54, RF55, RF56).

    Com uma conta só para isto: trocar e redefinir senha derruba sessões, e as
    dos outros itens precisam continuar de pé. A conta é desativada na limpeza,
    como as outras da execução.
    """
    r.secao("Conta — a troca e a redefinição de senha, a busca do parceiro e a ajuda")
    login = f"{marca}.conta"
    criada = admin.post(
        "/api/usuarios",
        json={"login": login, "nome": "Verificação Conta", "senha": SENHA, "perfil": "ANALISTA"},
    )
    if not r.checar("cria a conta que vai trocar de senha", criada.status_code == 201):
        return
    conta = criada.json()["id"]
    trocada = f"trocada-{secrets.token_urlsafe(12)}"
    redefinida = f"redefinida-{secrets.token_urlsafe(12)}"

    with sessao(url) as um, sessao(url) as outro:
        entrar(um, login, SENHA)
        entrar(outro, login, SENHA)
        errada = um.post(
            "/api/sessao/senha", json={"senha_atual": "não é esta", "senha_nova": trocada}
        )
        fraca = um.post("/api/sessao/senha", json={"senha_atual": SENHA, "senha_nova": "curta"})
        r.checar(
            "a senha atual errada e a nova fraca voltam como erro do campo (RF07)",
            errada.status_code == fraca.status_code == 422
            and [c["campo"] for c in errada.json().get("campos", [])] == ["senha_atual"]
            and [c["campo"] for c in fraca.json().get("campos", [])] == ["senha_nova"],
            (fraca.json().get("campos") or [{}])[0].get("mensagem", ""),
        )
        troca = um.post("/api/sessao/senha", json={"senha_atual": SENHA, "senha_nova": trocada})
        r.checar(
            "trocar a senha mantém a sessão de quem trocou e derruba as outras",
            troca.status_code == 204
            and um.get("/api/sessao/atual").status_code == 200
            and outro.get("/api/sessao/atual").status_code == 401,
        )

        eu = admin.get("/api/sessao/atual").json()
        propria = admin.post(f"/api/usuarios/{eu['id']}/senha", json={"senha_nova": redefinida})
        r.checar(
            "o administrador não redefine a própria senha por aqui: tem a Minha conta (RF54)",
            propria.status_code == 409,
            (propria.json().get("detail") or {}).get("ajuda", "")
            if propria.status_code == 409 else f"HTTP {propria.status_code}",
        )
        redefinicao = admin.post(f"/api/usuarios/{conta}/senha", json={"senha_nova": redefinida})
        r.checar(
            "a redefinição derruba todas as sessões da conta, e só a senha nova entra",
            redefinicao.status_code == 204
            and um.get("/api/sessao/atual").status_code == 401
            and not entrar(outro, login, trocada)
            and entrar(outro, login, redefinida),
        )
    trilha = admin.get("/api/auditoria", params={"acao": "SENHA_REDEFINIDA", "tamanho": 5})
    da_conta = [
        e for e in trilha.json().get("itens", [])
        if (e.get("detalhes") or {}).get("login") == login
    ] if trilha.status_code == 200 else []
    r.checar(
        "a redefinição entra na trilha, sem a senha (RF06)",
        bool(da_conta) and redefinida not in trilha.text,
        da_conta[0].get("resumo", "") if da_conta else f"HTTP {trilha.status_code}",
    )

    # O vínculo da conta de perfil Parceiro, pela busca de nomes (RF56).
    analista = criados.get("ANALISTA")
    nome = None
    if analista:
        with sessao(url) as c:
            entrar(c, analista, SENHA)
            itens = c.get("/api/parceiros", params={"tamanho": 1}).json().get("itens", [])
            nome = itens[0]["nome"] if itens else None
            negada = c.get("/api/usuarios/parceiros", params={"busca": "ab"}).status_code
            regras = c.get("/api/ajuda/regras")
    if nome is None:
        r.nota("a base não tem parceiro: a busca de nomes não foi conferida")
        return
    curta = admin.get("/api/usuarios/parceiros", params={"busca": nome[:1]})
    achados = admin.get("/api/usuarios/parceiros", params={"busca": nome})
    r.checar(
        "a busca de parceiros do administrador devolve só o nome e a situação (RF56)",
        curta.status_code == 422
        and achados.status_code == 200
        and bool(achados.json())
        and all(set(p) == {"id", "nome", "ativo"} for p in achados.json())
        and negada == 403,
        f"{len(achados.json())} achado(s) para {nome!r}; a busca de uma letra é recusada",
    )
    orfa = admin.post(
        "/api/usuarios",
        json={"login": f"{marca}.orfa", "nome": "Verificação Órfã", "senha": SENHA,
              "perfil": "PARCEIRO", "parceiro_id": 2_000_000_000},
    )
    r.checar(
        "vincular a um parceiro que não existe é erro do campo, e não login em uso (#227)",
        orfa.status_code == 422
        and [c["campo"] for c in orfa.json().get("campos", [])] == ["parceiro_id"],
        (orfa.json().get("campos") or [{}])[0].get("mensagem", "")
        if orfa.status_code == 422 else f"HTTP {orfa.status_code}",
    )

    # A ajuda (RF55): os limiares que ela mostra são os da configuração.
    configurado = admin.get("/api/configuracao/segmentacao").json()
    corpo = regras.json() if regras.status_code == 200 else {}
    r.checar(
        "a ajuda mostra os limiares em vigor e os segmentos na ordem da RN01 (RF55)",
        all(corpo.get(k) == configurado.get(k)
            for k in ("top_n", "periodos_tendencia", "periodos_novato"))
        and corpo.get("segmentos", [])[:4] == ["PROSPECCAO", "RECEM_CHEGADO", "EM_RISCO", "TOP"],
        f"Top {corpo.get('top_n')}, {corpo.get('periodos_tendencia')} períodos de tendência, "
        f"{corpo.get('periodos_novato')} de recém-chegado",
    )


def item_mensagens(r: Relatorio, url: str, criados: dict[str, str]) -> None:
    """As mensagens do último plano (UC10, RF36, RF37, RN08), pelo Analista.

    Roda depois da campanha, que deixa um plano calculado. Com o modelo de
    linguagem no ar, ele redige; sem ele, o modelo fixo — e as duas coisas são
    resultado certo (ADR-013). O que não pode, nos dois casos, é número no texto
    que não veio dos fatos. O lote e as mensagens saem na limpeza.
    """
    r.secao("Mensagens — do plano à fila, sem número que o núcleo não calculou")

    admin = criados.get("ADMINISTRADOR")
    if admin:
        with sessao(url) as c:
            entrar(c, admin, SENHA)
            r.checar(
                "o administrador não gera mensagens (UC10)",
                c.get("/api/mensagens/geracao").status_code == 403
                and c.post("/api/mensagens/lotes", json={"tipo": "SELECAO", "parceiros": [1]})
                .status_code == 403,
            )

    analista = criados.get("ANALISTA")
    if not analista:
        r.checar("há analista para gerar", False)
        return
    with sessao(url) as c:
        entrar(c, analista, SENHA)
        estado = c.get("/api/mensagens/geracao").json()
        assistente = estado.get("assistente") or {}
        if assistente.get("disponivel"):
            r.nota(f"assistente no ar: {assistente.get('modelo')}")
        else:
            motivo = assistente.get("motivo")
            r.nota(f"assistente fora: {motivo} — as mensagens saem do modelo fixo")

        vazio = {"tipo": "SELECAO", "parceiros": [2_000_000_000]}
        previa_vazia = c.post("/api/mensagens/publico", json=vazio).json()
        recusa = c.post("/api/mensagens/lotes", json=vazio)
        r.checar(
            "público vazio: a prévia diz, e nada é gerado (UC10-E1)",
            previa_vazia.get("total") == 0
            and previa_vazia.get("pode_gerar") is False
            and recusa.status_code == 422,
            (recusa.json().get("detail") or {}).get("erro", recusa.text[:120])
            if recusa.status_code == 422
            else f"HTTP {recusa.status_code}",
        )

        viaveis = [
            e
            for e in c.get("/api/otimizacoes", params={"tamanho": 20}).json().get("itens", [])
            if e.get("situacao") == "CONCLUIDA" and e.get("viavel")
        ]
        if not viaveis:
            r.nota("sem plano viável no histórico, as mensagens do plano não foram geradas")
            return
        execucao = c.get(f"/api/otimizacoes/{viaveis[0]['id']}").json()
        acoes = {i["parceiro_id"]: i["acao"] for i in execucao.get("itens") or []}
        publico = {"tipo": "PLANO", "execucao_id": execucao["id"]}
        previa = c.post("/api/mensagens/publico", json=publico).json()
        r.checar(
            "a prévia do plano traz os parceiros dele, com a ação de cada um (UC10, passo 2)",
            {p["id"]: p["acao"] for p in previa.get("parceiros", [])} == acoes and acoes,
            f"{previa.get('descricao')}: {previa.get('total')} parceiro(s)",
        )

        pedido = c.post("/api/mensagens/lotes", json=publico)
        inicio = time.monotonic()
        lote = _aguardar_lote(c, pedido.json()["id"]) if pedido.status_code == 202 else {}
        mensagens = lote.get("mensagens") or []
        r.checar(
            "uma mensagem por parceiro do plano, todas pendentes (RF36, RF37)",
            lote.get("situacao") == "CONCLUIDA"
            and not lote.get("falhas")
            and sorted(m["parceiro_id"] for m in mensagens) == sorted(acoes)
            and all(m["estado"] == "PENDENTE" for m in mensagens),
            f"{lote.get('geradas')} de {lote.get('total')} em {_tempo(time.monotonic() - inicio)}: "
            f"{lote.get('pelo_modelo')} pelo modelo, "
            f"{(lote.get('geradas') or 0) - (lote.get('pelo_modelo') or 0)} pelo modelo fixo"
            if lote
            else f"HTTP {pedido.status_code}: {pedido.text[:120]}",
        )
        sem_origem = {
            m["parceiro"]: numeros_sem_origem(m["texto"], m["fatos"])
            for m in mensagens
            if numeros_sem_origem(m["texto"], m["fatos"])
        }
        r.checar(
            "nenhum texto tem número que não veio dos fatos (RN08, RF43)",
            bool(mensagens) and not sem_origem,
            "; ".join(f"{p}: {', '.join(n)}" for p, n in sem_origem.items())
            or f"{len(mensagens)} texto(s) conferido(s)",
        )
        internos = {m["parceiro"]: termos_internos(m["texto"]) for m in mensagens}
        r.checar(
            "nenhum texto conta ao parceiro a classificação da rede (RF26)",
            bool(mensagens) and not any(internos.values()),
            "; ".join(f"{p}: {', '.join(t)}" for p, t in internos.items() if t) or "",
        )
        r.checar(
            "cada mensagem leva a ação do plano, e a do modelo fixo diz por quê (ADR-013)",
            bool(mensagens)
            and all(m["acao"] == acoes.get(m["parceiro_id"]) for m in mensagens)
            and all(m["motivo_redator"] for m in mensagens if m["redator"] == "MODELO_FIXO"),
            "; ".join(
                sorted({m["motivo_redator"] for m in mensagens if m["redator"] == "MODELO_FIXO"})
            )[:200]
            or "todas pelo modelo",
        )

        if len(mensagens) < 3:
            r.nota("menos de três mensagens: a decisão não foi conferida")
            return
        primeira, segunda, terceira = (m["id"] for m in mensagens[:3])
        barrado = c.post(f"/api/mensagens/{primeira}/aprovacao")
        r.checar(
            "o analista vê a fila, mas não aprova (RN06, UC11-A4)",
            c.get("/api/mensagens", params={"lote_id": lote["id"]}).status_code == 200
            and barrado.status_code == 403,
            f"HTTP {barrado.status_code} ao aprovar",
        )

    gestor = criados.get("GESTOR")
    if not gestor:
        r.checar("há gestor para decidir", False)
        return
    with sessao(url) as c:
        entrar(c, gestor, SENHA)
        aprovada = c.post(f"/api/mensagens/{primeira}/aprovacao")
        editada = c.post(
            f"/api/mensagens/{segunda}/edicao",
            json={"texto": "Olá! Preparamos uma ação para vocês nesta campanha."},
        )
        editada_e_aprovada = c.post(f"/api/mensagens/{segunda}/aprovacao")
        rejeitada = c.post(
            f"/api/mensagens/{terceira}/rejeicao", json={"motivo": "Tom errado para o parceiro."}
        )
        r.checar(
            "o gestor aprova, edita e rejeita, com autor e data em cada decisão (RF38, RF39)",
            aprovada.status_code == editada.status_code == 200
            and editada.json()["estado"] == "PENDENTE"
            and editada_e_aprovada.status_code == rejeitada.status_code == 200
            and all(
                d.json()["decidida_por"] and d.json()["decidida_em"]
                for d in (aprovada, editada_e_aprovada, rejeitada)
            ),
            f"HTTP {aprovada.status_code}, {editada.status_code}, "
            f"{editada_e_aprovada.status_code}, {rejeitada.status_code}",
        )
        r.checar(
            "a edição guarda o texto redigido ao lado do final (UC11-A1)",
            editada_e_aprovada.status_code == 200
            and editada_e_aprovada.json()["editada"]
            and editada_e_aprovada.json()["texto_gerado"] != editada_e_aprovada.json()["texto"],
        )
        de_novo = c.post(f"/api/mensagens/{terceira}/aprovacao")
        r.checar(
            "a mensagem já decidida não é sobrescrita, e a resposta diz a decisão (UC11-E1)",
            de_novo.status_code == 409 and de_novo.json()["detail"].get("estado") == "REJEITADA",
            (de_novo.json().get("detail") or {}).get("ajuda", de_novo.text[:120]),
        )
        pendentes = c.get("/api/mensagens", params={"lote_id": lote["id"]}).json()
        r.checar(
            "as decididas saem da fila de pendentes (UC11, passo 5)",
            pendentes.get("total") == len(mensagens) - 3,
            f"{pendentes.get('total')} pendente(s) do lote",
        )

        hoje = date.today().isoformat()
        aprovadas = c.get(
            "/api/mensagens", params={"estado": "APROVADA", "lote_id": lote["id"], "de": hoje}
        ).json()
        rejeitadas = c.get(
            "/api/mensagens", params={"estado": "REJEITADA", "lote_id": lote["id"]}
        ).json()
        r.checar(
            "o histórico traz as decididas de hoje, com autor, data, texto final e motivo (RF40)",
            {m["id"] for m in aprovadas.get("itens", [])} == {primeira, segunda}
            and all(m["decidida_por"] and m["decidida_em"] for m in aprovadas["itens"])
            and [m["motivo_rejeicao"] for m in rejeitadas.get("itens", [])]
            == ["Tom errado para o parceiro."],
            f"{aprovadas.get('total')} aprovada(s), {rejeitadas.get('total')} rejeitada(s)",
        )
        exportacao = c.get("/api/mensagens/exportacao.csv", params={"de": hoje})
        linhas = list(
            csv.reader(io.StringIO(exportacao.text.lstrip("\ufeff")), delimiter=";")
        )
        textos = {linha[5] for linha in linhas[1:]}
        r.checar(
            "a exportação traz as aprovadas prontas para envio, com o texto final (RF40)",
            exportacao.status_code == 200
            and linhas[0][:2] == ["Parceiro", "Contato"]
            and {m["texto"] for m in aprovadas.get("itens", [])} <= textos,
            f"{len(linhas) - 1} linha(s) no CSV de hoje",
        )


def item_portal(
    r: Relatorio, url: str, admin: httpx.Client, criados: dict[str, str], marca: str
) -> None:
    """O portal do Parceiro (UC13, RF26): um usuário Parceiro, vinculado ao parceiro de
    maior faturamento da base, vê o histórico dele e é barrado em tudo o que é da rede.
    O usuário é desativado na limpeza, como os outros da execução."""
    r.secao("Portal do Parceiro — só o próprio histórico, nada da rede")

    gestor = criados.get("GESTOR")
    if not gestor:
        r.checar("há gestor para achar um parceiro com histórico", False)
        return
    with sessao(url) as c:
        entrar(c, gestor, SENHA)
        lista = c.get(
            "/api/parceiros",
            params={"ordenar_por": "faturamento", "descendente": "true", "tamanho": 2},
        ).json()
    itens = lista.get("itens", [])
    if len(itens) < 2:
        r.nota("a base tem menos de dois parceiros: o portal não foi conferido")
        return
    dele, outro = itens[0], itens[1]
    login = f"{marca}.parceiro"
    criado = admin.post(
        "/api/usuarios",
        json={
            "login": login,
            "nome": "Verificação Parceiro",
            "senha": SENHA,
            "perfil": "PARCEIRO",
            "parceiro_id": dele["id"],
        },
    )
    if not r.checar("cria o usuário Parceiro vinculado a um parceiro", criado.status_code == 201):
        return

    with sessao(url) as c:
        entrar(c, login, SENHA)
        telas = c.get("/api/sessao/atual").json().get("telas", [])
        r.checar(
            "o menu do Parceiro tem só o portal dele", telas == ["meu_desempenho"], ", ".join(telas)
        )
        meu = c.get("/api/meu-desempenho")
        corpo = meu.json() if meu.status_code == 200 else {}
        r.checar(
            "vê o próprio histórico, sem ranking nem comparação (UC13, RF26)",
            corpo.get("parceiro") == dele["nome"]
            and len(corpo.get("pontos", [])) > 0
            and set(corpo) == {"parceiro", "categoria", "atual", "anterior", "variacao", "pontos"},
            f"{len(corpo.get('pontos', []))} período(s) de {corpo.get('parceiro')}"
            if corpo
            else f"HTTP {meu.status_code}",
        )
        recusas = {
            caminho: c.get(caminho).status_code
            for caminho in (
                f"/api/parceiros/{outro['id']}",
                f"/api/painel/series?parceiro_id={outro['id']}",
                "/api/painel/ranking",
                "/api/mensagens",
            )
        }
        r.checar(
            "o dado da rede e o de outro parceiro são recusados no servidor (UC13-E1, RNF14)",
            set(recusas.values()) == {403},
            ", ".join(f"{c.split('?')[0]} {s}" for c, s in recusas.items()),
        )


def item_assistente(r: Relatorio, url: str, criados: dict[str, str]) -> None:
    """O assistente (UC12, RF41 a RF43, RN08), pelo Analista.

    Com ou sem o modelo, a pergunta que pede uma média recebe a abstenção do
    código (H68). Com o modelo no ar: uma pergunta sobre o parceiro de maior
    faturamento, que precisa trazer o faturamento que a lista de parceiros
    mostra, só com números dos fatos e no sentido deles (H67); uma sobre a rede,
    com a fonte (H66); e uma fora do catálogo, que é abstenção. Sem o modelo, o
    assistente se diz indisponível e o painel segue (E1). Nada é gravado: não há
    o que limpar.
    """
    r.secao("Assistente — o catálogo, com os números das telas, ou a abstenção")

    admin = criados.get("ADMINISTRADOR")
    if admin:
        with sessao(url) as c:
            entrar(c, admin, SENHA)
            r.checar(
                "o administrador não pergunta ao assistente (UC12)",
                c.post("/api/assistente/perguntas", json={"texto": "Como foi a rede?"})
                .status_code == 403,
            )

    analista = criados.get("ANALISTA")
    if not analista:
        r.checar("há analista para perguntar", False)
        return
    # A primeira pergunta depois de o modelo ficar parado paga o carregamento,
    # perto de 45 s (ADR-013): o limite da sessão comum, 30 s, a derrubaria.
    with httpx.Client(base_url=url, timeout=180, follow_redirects=False) as c:
        entrar(c, analista, SENHA)
        estado = c.get("/api/assistente").json()
        assistente = estado.get("assistente") or {}
        r.checar(
            "o assistente diz se está no ar e mostra os exemplos do catálogo",
            "disponivel" in assistente and len(estado.get("exemplos", [])) >= 10,
            f"{len(estado.get('exemplos', []))} tipos de pergunta",
        )
        longa = c.post("/api/assistente/perguntas", json={"texto": "a" * 1001})
        r.checar(
            "a pergunta acima do limite é recusada com o limite (UC12-E2, RNF15)",
            longa.status_code == 422 and "1000" in longa.text,
        )
        media = c.post(
            "/api/assistente/perguntas",
            json={"texto": "Qual a média de faturamento das pizzarias?"},
        ).json()
        r.checar(
            "a pergunta que pede conta recebe a abstenção do código, com ou sem o modelo (H68)",
            media.get("situacao") == "ABSTENCAO" and media.get("tipo") == "fora_do_catalogo",
            media.get("texto", "")[:90],
        )

        if not assistente.get("disponivel"):
            corpo = c.post("/api/assistente/perguntas", json={"texto": "Como foi a rede?"}).json()
            r.checar(
                "sem o modelo, o assistente se diz indisponível, e o painel segue (UC12-E1)",
                corpo.get("situacao") == "INDISPONIVEL"
                and c.get("/api/painel/indicadores").status_code == 200,
                assistente.get("motivo") or "",
            )
            return

        r.nota(f"assistente no ar: {assistente.get('modelo')}")
        lista = c.get(
            "/api/parceiros",
            params={"ordenar_por": "faturamento", "descendente": "true", "tamanho": 1},
        ).json()
        maior = (lista.get("itens") or [{}])[0]
        faturamento = (maior.get("desempenho") or {}).get("faturamento")
        if faturamento is None:
            r.nota("a base não tem parceiro com faturamento: a pergunta dele não foi feita")
        else:
            inicio = time.monotonic()
            corpo = c.post(
                "/api/assistente/perguntas",
                json={"texto": f"Quanto {maior['nome']} faturou na última semana?"},
            ).json()
            texto = corpo.get("texto", "")
            r.checar(
                "a pergunta do parceiro traz o faturamento da lista, e só números dos fatos "
                "(RF41, RN08)",
                corpo.get("situacao") == "RESPONDIDA"
                and _reais(faturamento) in texto
                and numeros_sem_origem(texto, corpo.get("fatos", [])) == []
                and sentido_trocado(texto, corpo.get("fatos", [])) == [],
                f"{corpo.get('tipo')} em {time.monotonic() - inicio:.1f} s, redigida pelo "
                f"{corpo.get('redator')}: {texto[:80]}",
            )

        corpo = c.post(
            "/api/assistente/perguntas", json={"texto": "Como foi a rede na semana passada?"}
        ).json()
        fonte = corpo.get("fonte") or {}
        r.checar(
            "a pergunta sobre a rede traz a fonte, montada pelo código (RF42, H66)",
            corpo.get("tipo") == "resumo_do_periodo"
            and corpo.get("situacao") == "RESPONDIDA"
            and numeros_sem_origem(corpo.get("texto", ""), corpo.get("fatos", [])) == []
            and bool(fonte.get("relatorios"))
            and all(rel.get("importado_em") for rel in fonte["relatorios"]),
            fonte.get("texto", ""),
        )
        corpo = c.post(
            "/api/assistente/perguntas", json={"texto": "Qual a capital da França?"}
        ).json()
        r.checar(
            "a pergunta fora do catálogo recebe a abstenção, e não um palpite (UC12-A1)",
            corpo.get("situacao") == "ABSTENCAO" and not corpo.get("fatos"),
            corpo.get("tipo") or "",
        )


# --------------------------------------------------------------------- extra
def item_limpeza(
    r: Relatorio,
    admin: httpx.Client,
    marca: str,
    painel_antes: httpx.Response,
    versao_antes: str | None,
) -> None:
    """Desfaz o que a execução gravou, e confere pelo painel que desfez.

    Sem isto, cada execução deixava três semanas no futuro no banco da equipe, e
    o painel — que abre no período mais recente — passava a abrir numa delas. A
    última checagem olha exatamente esse sintoma, e pela API: o que importa é o
    painel mostrar o que mostrava antes, não a contagem de linhas apagadas.
    """
    r.secao("Limpeza — o banco volta ao que era antes da execução")

    if not desativar_usuarios(admin, marca):
        # Tudo o mais é gravado pelos usuários da execução; sem eles não há o que
        # desfazer, e procurar no banco só acusaria "banco errado".
        r.nota("a execução não chegou a criar usuários, e sem eles nada foi gravado")
        return

    try:
        removidos = limpar_execucao(marca)
    except LimpezaRecusada as e:
        r.checar("remove do banco o que a execução gravou", False, f"{e}; nada foi removido")
    else:
        r.checar("remove do banco o que a execução gravou", True, str(removidos))

    depois = admin.get("/api/painel/indicadores")
    igual = painel_antes.status_code == depois.status_code == 200 and (
        depois.json() == painel_antes.json()
    )
    r.checar(
        "o painel volta a abrir no mesmo período, com os mesmos totais",
        igual,
        onde_o_painel_abre(depois)
        if igual
        else f"antes: {onde_o_painel_abre(painel_antes)}; agora: {onde_o_painel_abre(depois)}",
    )
    versao = admin.get("/api/modelo").json().get("versao_em_uso")
    r.checar(
        "a versão do modelo em uso volta a ser a de antes",
        versao == versao_antes,
        f"{versao or 'nenhuma — o modelo não estava treinado'}",
    )
    r.nota("os usuários da execução ficam, desativados: a trilha de auditoria aponta para eles")


def onde_o_painel_abre(resposta: httpx.Response) -> str:
    if resposta.status_code != 200:
        return f"o painel respondeu {resposta.status_code}"
    periodo = resposta.json()["periodo"]
    return f'período de {periodo["data_inicio"]}' if periodo else "base sem período"


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

        # Onde o painel abre antes de a verificação gravar qualquer coisa. É
        # contra isto que a limpeza é conferida no fim.
        painel_antes = admin.get("/api/painel/indicadores")
        versao_antes = admin.get("/api/modelo").json().get("versao_em_uso")
        try:
            item_banco(r, admin)
            item_login(r, a.url, a.login, a.senha)
            criados = item_cadastro(r, admin, marca)
            item_perfis(r, a.url, criados)
            item_modelo(r, a.url, criados)
            item_campanha(r, a.url, criados)
            item_recorte_do_painel(r, a.url, admin, criados)
            item_relatorios(r, a.url, admin, criados)
            item_trilha(r, a.url, admin, criados, marca)
            item_benchmark(r, a.url, criados)
            item_mensagens(r, a.url, criados)
            item_portal(r, a.url, admin, criados, marca)
            item_conta(r, a.url, admin, criados, marca)
            item_assistente(r, a.url, criados)
            item_crud(r, a.url, criados, marca)
            periodo_id = item_ingestao(r, a.url, criados, marca)
            item_painel(r, a.url, criados, periodo_id)
            item_segmentacao(r, a.url, criados, periodo_id)
            item_recorte(r, a.url, criados, marca)
            item_configuracao(r, a.url, admin, criados)
            item_telas(r, a.url, admin, criados)
            item_sugestao(r, a.url, criados, marca)
        finally:
            # No `finally`: a execução interrompida por uma exceção é justamente
            # a que deixaria mais para trás — período no futuro no painel e
            # usuário ativo com a senha que está publicada neste arquivo.
            item_limpeza(r, admin, marca, painel_antes, versao_antes)

    return r.encerrar()


if __name__ == "__main__":
    raise SystemExit(main())
