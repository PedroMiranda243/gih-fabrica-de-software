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
        rapido = _aguardar(c, automatico.json()["id"]) if automatico.status_code == 202 else {}
        r.checar(
            "sem escolha, roda o modo mais rápido disponível, com o mesmo plano do serial (RF32)",
            rapido.get("modo") == estado.get("modo_automatico")
            and disponiveis[:1] == [rapido.get("modo")]
            and rapido.get("situacao") == "CONCLUIDA"
            and _plano(rapido) == _plano(plano),
            f"disponíveis: {', '.join(disponiveis)}; {rapido.get('modo')} em {_segundos(rapido)}"
            + (f" com {rapido['threads']} threads" if rapido.get("threads") else "")
            + f", contra {_segundos(plano)} do serial",
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
        calculadas = [execucao_id, rapido.get("id"), recusa.get("id")]
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
