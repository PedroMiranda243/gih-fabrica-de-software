"""Mede o assistente contra o modelo de verdade — H65, H66, H67 e H68.

Três conjuntos de perguntas, versionados em `api/tests/assistente/`:

- **`referencia.json` (RF41):** cada pergunta com o tipo e os campos esperados.
  Mede a extração: o modelo leu a pergunta certo?
- **`armadilhas.json` (H67):** perguntas que convidam o modelo a escrever um
  número que o núcleo não calculou. Mede se algum chega à resposta — tem de ser
  zero — e quantas vezes a guarda precisou agir.
- **`sem_resposta.json` (H68):** perguntas sem resposta nos dados. Mede a
  abstenção — tem de ser 100%.

**A extração usa o contexto do conjunto**, e não o do banco: as categorias e o
calendário estão no arquivo, e o resultado não muda com a massa.

**As armadilhas e as sem resposta passam pelo caminho inteiro** — o
`servico.perguntar` da rota, com a redação e a guarda — contra a massa do
gerador num banco à parte, segmentada e com o modelo preditivo treinado. Sem
plano calculado: a pergunta do plano está só na referência.

**O modelo não se repete** (`CLAUDE.md` §7): a mesma pergunta pode sair de outro
jeito numa segunda rodada. O relatório diz a data e o modelo, e cada resposta.

Uso:

    api/.venv/Scripts/python scripts/medir_assistente.py
    api/.venv/Scripts/python scripts/medir_assistente.py --sem-preparar
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import sys
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "api"))
sys.path.insert(0, str(RAIZ / "scripts"))

from medir_otimizador import _treinar  # noqa: E402
from medir_painel import _mil, _url_base, _url_medicao, preparar  # noqa: E402

CONJUNTOS = RAIZ / "api" / "tests" / "assistente"
PERIODOS = 12


def _carregar(nome: str) -> dict:
    return json.loads((CONJUNTOS / nome).read_text(encoding="utf-8"))


def _texto_curto(texto: str, limite: int = 110) -> str:
    texto = " ".join(texto.split()).replace("|", "/")
    return texto if len(texto) <= limite else texto[: limite - 1] + "…"


def _segundos(valor: float) -> str:
    return f"{valor:.1f} s".replace(".", ",")


def _porcento(parte: int, todo: int) -> str:
    return f"{100 * parte / todo:.0f}%" if todo else "—"


# ---------------------------------------------------------------- referência
@dataclass
class Leitura:
    pergunta: str
    tipo: str
    campos: dict
    obtido: dict
    tipo_certo: bool
    campos_certos: bool
    segundos: float
    erro: str | None = None
    # A leitura errada que o código acerta depois (`servico._corrigir`).
    corrigida: bool = False


def _semanas(inicio, fim, calendario) -> frozenset[int] | None:
    """As semanas do calendário que o intervalo toca — é assim que a resolução lê a data."""
    if inicio is None and fim is None:
        return None
    try:
        de = date.fromisoformat(inicio or fim)
        ate = date.fromisoformat(fim or inicio)
    except ValueError:
        return frozenset({-1})
    de, ate = min(de, ate), max(de, ate)
    return frozenset(i for i, (a, b) in enumerate(calendario) if a <= ate and b >= de)


def _campos_certos(tipo: str, esperado: dict, obtido: dict, calendario) -> bool:
    from app.assistente.catalogo import CATALOGO, UsoDoPeriodo
    from app.assistente.resolucao import sem_artigo
    from app.esquemas import TipoPergunta
    from app.texto import normalizar

    def nome(valor):
        return normalizar(sem_artigo(valor)) if valor else None

    for campo in ("parceiro", "outro_parceiro"):
        if campo in esperado and nome(obtido.get(campo)) != nome(esperado[campo]):
            return False
    if "categoria" in esperado and (
        normalizar(obtido.get("categoria") or "") != normalizar(esperado["categoria"])
    ):
        return False
    for campo in ("segmento", "quantos"):
        if campo in esperado and obtido.get(campo) != esperado[campo]:
            return False

    entrada = CATALOGO.get(TipoPergunta(tipo)) if tipo != "fora_do_catalogo" else None
    if entrada is None or entrada.periodo is UsoDoPeriodo.NENHUM:
        return True
    esperadas = _semanas(esperado.get("inicio"), esperado.get("fim"), calendario)
    obtidas = _semanas(obtido.get("inicio"), obtido.get("fim"), calendario)
    if esperadas == obtidas:
        return True
    # Sem data, vale a semana mais recente — que é o que "nesta semana" também diz.
    ultima = len(calendario) - 1
    if entrada.periodo is UsoDoPeriodo.UM:
        return {esperadas, obtidas} <= {None, frozenset({ultima})}
    # Na evolução sem data ("o histórico", "as últimas semanas"), qualquer intervalo
    # que chegue à semana mais recente é a leitura certa: o sem data também é um.
    return esperadas is None and ultima in obtidas


def _o_codigo_corrige(esperado: str, obtido: dict, calendario) -> bool:
    """As leituras erradas que `servico._corrigir` acerta, e os testes cobrem: o resumo da
    rede com um parceiro citado, e o desempenho de várias semanas."""
    lido = obtido.get("tipo")
    if esperado == "desempenho_do_parceiro" and lido == "resumo_do_periodo":
        return bool(obtido.get("parceiro"))
    if esperado == "evolucao_do_parceiro" and lido == "desempenho_do_parceiro":
        semanas = _semanas(obtido.get("inicio"), obtido.get("fim"), calendario)
        return bool(semanas) and len(semanas) > 1
    return False


def medir_referencia(r) -> tuple[list[Leitura], dict]:
    from app.assistente.catalogo import Extracao, instrucao
    from app.redator import FalhaDoRedator

    conjunto = _carregar("referencia.json")
    contexto = conjunto["contexto"]
    primeira = date.fromisoformat(contexto["primeira_semana"])
    calendario = [
        (primeira + timedelta(weeks=i), primeira + timedelta(weeks=i, days=6))
        for i in range(contexto["semanas"])
    ]
    sistema = instrucao(contexto["categorias"], calendario)

    leituras = []
    for item in conjunto["perguntas"]:
        inicio = time.perf_counter()
        try:
            obtido = r.extrair(sistema, item["pergunta"], Extracao).model_dump(mode="json")
            erro = None
        except FalhaDoRedator as falha:
            obtido, erro = {}, str(falha)
        segundos = time.perf_counter() - inicio
        tipo_certo = obtido.get("tipo") == item["tipo"]
        leitura = Leitura(
            item["pergunta"],
            item["tipo"],
            item["campos"],
            {k: v for k, v in obtido.items() if v is not None},
            tipo_certo,
            tipo_certo and _campos_certos(item["tipo"], item["campos"], obtido, calendario),
            segundos,
            erro,
        )
        leitura.corrigida = not leitura.campos_certos and _o_codigo_corrige(
            item["tipo"], obtido, calendario
        )
        leituras.append(leitura)
        marca = "ok  " if leitura.campos_certos else ("TIPO" if not tipo_certo else "CAMPO")
        print(f"  {marca} {segundos:4.1f}s {item['pergunta']}")
    return leituras, contexto


# --------------------------------------------------------- o caminho inteiro
@dataclass
class Caminho:
    pergunta: str
    situacao: str
    tipo: str | None
    redator: str
    motivo: str | None
    texto: str
    sem_origem: list[str] = field(default_factory=list)
    segundos: float = 0.0
    pelo_codigo_antes: bool = False


def _perguntar(r, pergunta: str) -> Caminho:
    from app.assistente import servico
    from app.assistente.catalogo import abstencao_pelo_codigo
    from app.db import Sessao
    from app.guarda_numerica import numeros_sem_origem, sentido_trocado

    s = Sessao()
    try:
        inicio = time.perf_counter()
        resultado = servico.perguntar(s, pergunta, r)
        segundos = time.perf_counter() - inicio
    finally:
        s.close()
    texto = resultado.redacao.texto
    fatos = resultado.resposta.fatos
    return Caminho(
        pergunta=pergunta,
        situacao=resultado.resposta.situacao.value,
        tipo=resultado.tipo.value if resultado.tipo else None,
        redator=resultado.redacao.redator.value,
        motivo=resultado.redacao.motivo,
        texto=texto,
        sem_origem=numeros_sem_origem(texto, fatos) + sentido_trocado(texto, fatos),
        segundos=segundos,
        pelo_codigo_antes=abstencao_pelo_codigo(pergunta) is not None,
    )


def _o_que_a_guarda_pegou(c: Caminho) -> str:
    from app.assistente import redacao

    if c.motivo is None:
        return "—"
    for modelo, rotulo in (
        (redacao.NUMEROS_SEM_ORIGEM, "número sem origem"),
        (redacao.SENTIDO_TROCADO, "sentido trocado"),
        (redacao.UNIDADE_SEM_ORIGEM, "unidade sem origem"),
    ):
        prefixo = modelo.split("{")[0]
        if c.motivo.startswith(prefixo):
            achados = c.motivo[len(prefixo) :].split(")")[0]
            return f"{rotulo}: {achados}"
    if c.motivo == redacao.LONGO:
        return "texto longo demais"
    return f"sem redação: {c.motivo}"


def _quem_se_absteve(c: Caminho) -> str:
    from app.assistente import catalogo, servico

    if c.pelo_codigo_antes:
        return "o código, antes do modelo"
    if c.texto == catalogo.COMPARACAO:
        return "o código: dois parceiros na pergunta"
    if c.texto == servico.FORA_DO_CATALOGO:
        return "a classificação: fora do catálogo"
    return "a resolução, contra a base"


# ------------------------------------------------------------------ relatório
def montar_relatorio(ambiente: dict, leituras, contexto, armadilhas, sem_resposta) -> str:
    linhas = [
        "# Medição do assistente — H65 a H68",
        "",
        "> Gerado por `scripts/medir_assistente.py`. **Não edite à mão**: número escrito à mão "
        "não é evidência. Para atualizar, rode o comando abaixo de novo.",
        "",
        "O assistente responde a um catálogo fechado de perguntas (ADR-013). O modelo de "
        "linguagem lê a pergunta e redige a resposta; os números vêm do código, e a guarda "
        "numérica confere o que o modelo escreveu. Os três conjuntos de perguntas estão em "
        "`api/tests/assistente/`.",
        "",
        "## Ambiente",
        "",
        "| Item | Valor |",
        "|---|---|",
        f"| Data | {ambiente['data']} |",
        f"| Modelo de linguagem | `{ambiente['modelo']}`, pelo Ollama |",
        f"| Massa | `scripts/gerar_dados_sinteticos.py`, {ambiente['parceiros']} parceiros, "
        f"{PERIODOS} semanas, semente {ambiente['semente']}, no banco `{ambiente['banco']}` |",
        "| Caminho | gerador → segmentação → treino do modelo preditivo → `servico.perguntar`, "
        "o mesmo da rota |",
        f"| Máquina | {ambiente['maquina']} |",
        "",
        "## Como reproduzir",
        "",
        "```bash",
        ambiente["comando"],
        "```",
        "",
        "A primeira chamada carrega o modelo na memória; ela fica fora da medição.",
        "",
    ]

    # --- referência
    total = len(leituras)
    tipos = sum(x.tipo_certo for x in leituras)
    certos = sum(x.campos_certos for x in leituras)
    linhas += [
        "## Referência — o modelo lê a pergunta certo (RF41, H65)",
        "",
        f"**O tipo certo em {tipos} de {total} ({_porcento(tipos, total)}); o tipo e os campos "
        f"certos em {certos} de {total} ({_porcento(certos, total)}).** Com o calendário do "
        f"conjunto: {contexto['semanas']} semanas a partir de "
        f"{date.fromisoformat(contexto['primeira_semana']).strftime('%d/%m/%Y')}.",
        "",
        "| Tipo | Perguntas | Tipo certo | Tipo e campos certos |",
        "|---|--:|--:|--:|",
    ]
    por_tipo: dict[str, list[Leitura]] = {}
    for x in leituras:
        por_tipo.setdefault(x.tipo, []).append(x)
    for tipo, grupo in por_tipo.items():
        linhas.append(
            f"| `{tipo}` | {len(grupo)} | {sum(x.tipo_certo for x in grupo)} | "
            f"{sum(x.campos_certos for x in grupo)} |"
        )
    erradas = [x for x in leituras if not x.campos_certos]
    if erradas:
        corrigidas = sum(x.corrigida for x in erradas)
        linhas += [
            "",
            f"**O que o modelo leu errado** — e, destas {len(erradas)} leituras, {corrigidas} o "
            "código acerta depois, antes de responder (`servico._corrigir`):",
            "",
        ]
        for x in erradas:
            esperado = {"tipo": x.tipo, **x.campos}
            obtido = x.obtido or {"falha": x.erro}
            linhas.append(
                f"- \"{x.pergunta}\" — esperado `{json.dumps(esperado, ensure_ascii=False)}`; "
                f"obtido `{json.dumps(obtido, ensure_ascii=False)}`"
                + (" — **o código corrige**" if x.corrigida else "")
            )
    linhas.append("")

    # --- armadilhas
    na_tela = [c for c in armadilhas if c.sem_origem]
    pelo_modelo = [c for c in armadilhas if c.redator == "MODELO"]
    pegas = [c for c in armadilhas if c.motivo]
    linhas += [
        "## Armadilhas — nenhum número inventado na tela (RF43, H67)",
        "",
        f"**Número sem origem na resposta que chega à tela: {len(na_tela)} em "
        f"{len(armadilhas)} perguntas.** Por construção: o texto do modelo com número que "
        "não veio dos fatos volta a ser o do código. O que a medição conta é quantas vezes "
        "a guarda precisou agir:",
        "",
        f"- **{len(pelo_modelo)}** respostas redigidas pelo modelo e aprovadas pela guarda;",
        f"- **{len(pegas)}** redações recusadas, e a resposta saiu como o código a montou;",
        "- as demais são listas, que o modelo não redige, abstenções ou pedidos de precisão.",
        "",
        "| Pergunta | Situação | Texto de | O que a guarda pegou |",
        "|---|---|---|---|",
    ]
    for c in armadilhas:
        linhas.append(
            f"| {_texto_curto(c.pergunta, 90)} | {c.situacao} | "
            f"{'modelo' if c.redator == 'MODELO' else 'código'} | "
            f"{_texto_curto(_o_que_a_guarda_pegou(c), 80)} |"
        )
    linhas += ["", "<details><summary>Cada resposta</summary>", ""]
    for c in armadilhas:
        linhas += [f"- **{c.pergunta}**", f"  {_texto_curto(c.texto, 400)}"]
    linhas += ["", "</details>", ""]

    # --- sem resposta
    abstencoes = [c for c in sem_resposta if c.situacao == "ABSTENCAO"]
    linhas += [
        "## Sem resposta — a abstenção (RF42, H68)",
        "",
        f"**Abstenção em {len(abstencoes)} de {len(sem_resposta)} "
        f"({_porcento(len(abstencoes), len(sem_resposta))}).**",
        "",
        "| Pergunta | Situação | Quem se absteve |",
        "|---|---|---|",
    ]
    for c in sem_resposta:
        quem = _quem_se_absteve(c) if c.situacao == "ABSTENCAO" else _texto_curto(c.texto, 80)
        linhas.append(f"| {_texto_curto(c.pergunta, 90)} | {c.situacao} | {quem} |")
    linhas.append("")

    # --- tempo
    extracao = [x.segundos for x in leituras if not x.erro]
    caminho = [c.segundos for c in armadilhas + sem_resposta if not c.pelo_codigo_antes]
    linhas += [
        "## Tempo",
        "",
        "Com o modelo já carregado. Mediana, e entre parênteses a faixa.",
        "",
        "| O quê | Tempo |",
        "|---|--:|",
    ]
    if extracao:
        linhas.append(
            f"| Ler a pergunta (a extração) | {_segundos(statistics.median(extracao))} "
            f"({_segundos(min(extracao))} a {_segundos(max(extracao))}) |"
        )
    if caminho:
        linhas.append(
            f"| A pergunta inteira, com a redação | {_segundos(statistics.median(caminho))} "
            f"({_segundos(min(caminho))} a {_segundos(max(caminho))}) |"
        )
    linhas.append("")
    return "\n".join(linhas)


def main() -> None:
    p = argparse.ArgumentParser(description="Mede o assistente (H65 a H68).")
    p.add_argument("--banco", default="gih_medicao")
    p.add_argument("--parceiros", type=int, default=500)
    p.add_argument("--semente", type=int, default=42)
    p.add_argument("--ollama", default="http://localhost:11434")
    p.add_argument("--modelo", default="qwen2.5:7b")
    p.add_argument(
        "--sem-preparar", action="store_true", help="usa a massa que já está no banco de medição"
    )
    p.add_argument("--relatorio", default=str(RAIZ / "docs" / "medicoes" / "assistente.md"))
    args = p.parse_args()

    url = _url_medicao(args.banco)
    if urlsplit(url).path.lstrip("/") == urlsplit(_url_base()).path.lstrip("/"):
        raise SystemExit("O banco de medição não pode ser o banco de trabalho.")
    os.environ["DATABASE_URL"] = url

    from app.redator import Redator

    r = Redator(args.ollama, args.modelo, 180)
    estado = r.estado()
    if not estado.disponivel:
        raise SystemExit(f"O modelo de linguagem não está disponível: {estado.motivo}")

    if not args.sem_preparar:
        preparar(url, args.parceiros, PERIODOS, args.semente)
        print("  treinando o modelo preditivo")
        _treinar()

    print("aquecendo o modelo")
    r.redigir("Responda só: ok.", "ok")

    print("referência")
    leituras, contexto = medir_referencia(r)
    print("armadilhas")
    armadilhas = []
    for pergunta in _carregar("armadilhas.json")["perguntas"]:
        c = _perguntar(r, pergunta)
        armadilhas.append(c)
        print(f"  {c.situacao:12} {c.redator:11} {len(c.sem_origem)} {pergunta}")
    print("sem resposta")
    sem_resposta = []
    for item in _carregar("sem_resposta.json")["perguntas"]:
        c = _perguntar(r, item["pergunta"])
        sem_resposta.append(c)
        print(f"  {c.situacao:12} {item['pergunta']}")

    comando = "api/.venv/Scripts/python scripts/medir_assistente.py"
    if args.parceiros != 500 or args.semente != 42:
        comando += f" --parceiros {args.parceiros} --semente {args.semente}"
    ambiente = {
        "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "modelo": args.modelo,
        "parceiros": _mil(args.parceiros),
        "semente": args.semente,
        "banco": args.banco,
        "maquina": (
            f"{platform.processor() or platform.machine()}, Python {platform.python_version()}"
        ),
        "comando": comando,
    }
    destino = Path(args.relatorio)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        montar_relatorio(ambiente, leituras, contexto, armadilhas, sem_resposta), encoding="utf-8"
    )
    print(f"\nrelatório: {destino}")


if __name__ == "__main__":
    main()
