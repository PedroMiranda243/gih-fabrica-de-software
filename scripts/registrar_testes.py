"""Roda as quatro suítes de teste e gera o registro de testes de uma entrega.

O enunciado da Sprint 05 pede testes dos fluxos principais, das operações com o
banco, das validações e das situações de erro, **com os resultados registrados
no documento**; o da Sprint 06, as evidências das funcionalidades. Este script
é o registro: roda as suítes de verdade — API, modelo, otimizador e interface —
e escreve o que passou e o que falhou, por suíte e por arquivo.

**O otimizador roda na imagem do núcleo** (`nucleo/Dockerfile`), compilado com
CUDA e com a placa da máquina (`--gpus all`). Na máquina de desenvolvimento o
executável é compilado sem CUDA, e os testes da GPU pulariam; na imagem eles
rodam na placa — é a evidência objetiva da GPU que a Pré-Banca pediu. A imagem
liga o `GIH_NUCLEO_OBRIGATORIO`: sem o executável, a suíte reprova em vez de
pular. Numa máquina sem placa NVIDIA, `--sem-gpu`: os testes da GPU pulam, e o
registro diz isso.

**Os quatro tipos do enunciado vêm com exemplos nomeados**, escolhidos à mão e
conferidos contra a execução: se um exemplo deixar de existir, o script recusa
em vez de publicar um teste que não rodou. Classificar os mais de mil testes um
a um nos quatro tipos seria arbitrário — muitos são mais de um ao mesmo tempo —;
os exemplos mostram o que cada tipo cobre, e o total diz quanto roda. Os
exemplos são os da entrega em curso: os de antes ficam no registro congelado
dela.

A suíte da API precisa do Postgres no ar (o `conftest` cria o banco de teste).
**Não rode duas vezes ao mesmo tempo**: as duas execuções truncariam as tabelas
uma da outra.

Uso, da raiz do projeto:

    api/.venv/Scripts/python scripts/registrar_testes.py --saida docs/entrega/evidencias/sprint06
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
IMAGEM_DO_NUCLEO = "gih-nucleo"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Os exemplos de cada tipo que o enunciado nomeia: (suíte, arquivo, teste, o que prova).
# Os da Sprint 06: o terceiro módulo — a campanha e o otimizador —, a integração
# entre os módulos (H80, H81) e a navegação (H79).
EXEMPLOS: dict[str, list[tuple[str, str, str, str]]] = {
    "Fluxos principais": [
        ("api", "test_campanha.py", "test_o_plano_respeita_as_restricoes_e_e_o_otimo",
         "o plano respeita as restrições e é o ótimo da instância (UC08, RF30)"),
        ("otimizador", "test_otimizador.py", "test_o_guloso_erra_onde_o_genetico_acerta",
         "a busca acerta onde a escolha gulosa erra"),
        ("otimizador", "test_gpu.py", "test_a_busca_na_gpu_e_a_do_python_numa_instancia_grande",
         "a busca na GPU dá o mesmo plano do Python, numa instância grande (H54)"),
        ("api", "test_parceiros_risco.py",
         "test_a_lista_traz_o_risco_da_versao_em_uso_e_diz_de_onde_ele_vem",
         "a lista de parceiros traz o risco da versão em uso, e de onde ele vem (H80)"),
        ("api", "test_parceiros_campanha.py",
         "test_o_parceiro_no_plano_ve_a_acao_o_custo_e_o_ganho_esperado",
         "o cadastro do parceiro mostra a ação do último plano (H81)"),
        ("interface", "Campanha.test.jsx",
         "calcular manda frações e reais no formato da API, acompanha e mostra o plano",
         "a tela calcula, acompanha e mostra o plano"),
        ("interface", "Casca.test.jsx",
         "os grupos seguem o fluxo do produto, e cada um é uma região com o nome dele",
         "o menu agrupado por módulo, na ordem do fluxo (H79)"),
    ],
    "Operações com o banco": [
        ("api", "test_campanha.py", "test_a_execucao_fica_na_auditoria_com_parametros_modo_e_tempo",
         "a execução fica gravada e auditada, com parâmetros, modo e tempo"),
        ("api", "test_campanha.py", "test_o_historico_lista_da_mais_recente_para_a_mais_antiga",
         "o histórico de execuções, da mais recente à mais antiga (RF34)"),
        ("api", "test_campanha.py", "test_dois_planos_lado_a_lado_com_o_que_mudou",
         "dois planos gravados, lado a lado, com o que mudou (RF35)"),
        ("api", "test_parceiros_campanha.py", "test_vale_o_plano_mais_recente",
         "o cadastro lê o plano mais recente gravado"),
        ("api", "test_parceiros_risco.py", "test_o_risco_nao_custa_uma_consulta_por_linha",
         "o risco na lista não faz uma consulta por parceiro"),
    ],
    "Validações": [
        ("api", "test_campanha.py", "test_campanha_inviavel_diz_quanto_falta",
         "campanha inviável diz a restrição e quanto falta (RN07)"),
        ("otimizador", "test_viabilidade.py",
         "test_minimos_que_o_orcamento_nao_paga_nem_com_a_acao_mais_barata",
         "mínimos que o orçamento não paga são inviáveis antes da busca (RF31)"),
        ("api", "test_campanha.py", "test_cota_de_categoria_que_nao_existe",
         "cota para uma categoria que não existe é recusada"),
        ("api", "test_erros.py", "test_orcamento_zero_na_campanha_diz_o_minimo",
         "orçamento zero diz o mínimo, na língua de quem usa"),
        ("interface", "Campanha.test.jsx", "os erros de campo da API aparecem embaixo do campo",
         "o erro de cada campo aparece embaixo dele"),
    ],
    "Situações de erro": [
        ("api", "test_campanha.py", "test_falha_vira_falhou_com_motivo_e_libera_a_trava",
         "falha no cálculo vira FALHOU, com motivo, e libera a trava"),
        ("api", "test_campanha.py", "test_com_uma_otimizacao_rodando_a_segunda_e_recusada",
         "uma segunda otimização, com outra rodando, é recusada com 409"),
        ("api", "test_campanha.py", "test_nucleo_que_nao_responde_deixa_so_o_serial",
         "o núcleo que não responde deixa só o serial, e a campanha segue (RNF06)"),
        ("otimizador", "test_otimizador.py",
         "test_o_limite_de_tempo_devolve_o_melhor_viavel_e_marca_parcial",
         "o limite de tempo devolve o melhor plano viável, marcado como parcial"),
        ("interface", "NaoEncontrada.test.jsx",
         "diz que a página não existe, mostra o endereço pedido e oferece a volta",
         "endereço que não existe mostra a página não encontrada, com a volta (H79)"),
    ],
}


@dataclass
class Suite:
    nome: str
    rotulo: str
    resultados: dict[tuple[str, str], str] = field(default_factory=dict)  # (arquivo, teste) → situação
    segundos: float = 0.0

    def contagem(self) -> Counter:
        return Counter(self.resultados.values())

    def por_arquivo(self) -> dict[str, Counter]:
        arquivos: dict[str, Counter] = defaultdict(Counter)
        for (arquivo, _), situacao in self.resultados.items():
            arquivos[arquivo][situacao] += 1
        return dict(sorted(arquivos.items()))


def _python_da_api() -> str:
    for candidato in (RAIZ / "api/.venv/Scripts/python.exe", RAIZ / "api/.venv/bin/python"):
        if candidato.exists():
            return str(candidato)
    return sys.executable


def _junit(suite: Suite, relatorio: Path) -> Suite:
    if not relatorio.exists():
        raise SystemExit(f"A suíte {suite.rotulo} não produziu relatório — ela nem chegou a rodar.")
    for caso in ET.parse(relatorio).getroot().iter("testcase"):
        arquivo = caso.get("classname", "").split(".")[-1] + ".py"
        if caso.find("failure") is not None or caso.find("error") is not None:
            situacao = "falhou"
        elif caso.find("skipped") is not None:
            situacao = "pulado"
        else:
            situacao = "passou"
        suite.resultados[(arquivo, caso.get("name"))] = situacao
    return suite


def _pytest(nome: str, rotulo: str, pasta: Path, temporaria: Path) -> Suite:
    relatorio = temporaria / f"{nome}.xml"
    inicio = time.perf_counter()
    subprocess.run(
        [_python_da_api(), "-m", "pytest", "-q", "-p", "no:cacheprovider",
         f"--junitxml={relatorio}"],
        cwd=pasta, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return _junit(Suite(nome, rotulo, segundos=time.perf_counter() - inicio), relatorio)


def _otimizador(temporaria: Path, gpu: bool) -> tuple[Suite, str]:
    """A suíte do núcleo na imagem dele, e a linha em que o executável diz a GPU."""
    construcao = subprocess.run(
        ["docker", "build", "-q", "-t", IMAGEM_DO_NUCLEO, "nucleo"],
        cwd=RAIZ, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if construcao.returncode != 0:
        raise SystemExit(f"A imagem do núcleo não foi construída:\n{construcao.stderr[-2000:]}")
    placa = ["--gpus", "all"] if gpu else []
    versao = subprocess.run(
        ["docker", "run", "--rm", *placa, IMAGEM_DO_NUCLEO, "gih-nucleo", "versao"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    ).stdout
    gpu_vista = next((linha for linha in versao.splitlines() if linha.startswith("gpu ")), "")

    # O `scripts/` só de leitura, onde o teste do catálogo procura o gerador de
    # dados: a imagem leva só o `nucleo/`, e sem ele esse teste pularia.
    inicio = time.perf_counter()
    subprocess.run(
        ["docker", "run", "--rm", *placa,
         "--mount", f"type=bind,source={temporaria},target=/saida",
         "--mount", f"type=bind,source={RAIZ / 'scripts'},target=/scripts,readonly",
         IMAGEM_DO_NUCLEO, "python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
         "--junitxml=/saida/otimizador.xml"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    rotulo = "Otimizador (pytest, com GPU)" if gpu else "Otimizador (pytest, sem GPU)"
    suite = Suite("otimizador", rotulo, segundos=time.perf_counter() - inicio)
    return _junit(suite, temporaria / "otimizador.xml"), gpu_vista


def _vitest(temporaria: Path) -> Suite:
    relatorio = temporaria / "interface.json"
    npx = shutil.which("npx") or "npx"
    inicio = time.perf_counter()
    subprocess.run(
        [npx, "vitest", "run", "--reporter=json", f"--outputFile={relatorio}"],
        cwd=RAIZ / "web", capture_output=True, text=True, encoding="utf-8", errors="replace",
        shell=os.name == "nt",
    )
    suite = Suite("interface", "Interface (Vitest)", segundos=time.perf_counter() - inicio)
    if not relatorio.exists():
        raise SystemExit("A suíte da interface não produziu relatório — ela nem chegou a rodar.")
    dados = json.loads(relatorio.read_text(encoding="utf-8"))
    for arquivo in dados["testResults"]:
        nome = Path(arquivo["name"]).name
        for caso in arquivo["assertionResults"]:
            situacao = {"passed": "passou", "failed": "falhou"}.get(caso["status"], "pulado")
            suite.resultados[(nome, caso["title"])] = situacao
    return suite


def _placa(gpu_vista: str) -> str:
    """`gpu 1 8.9 8187 NVIDIA GeForce RTX 4060` → a placa, a capacidade e a memória."""
    partes = gpu_vista.split(maxsplit=4)
    if len(partes) < 5 or partes[1] == "0":
        return "nenhuma placa vista: os testes da GPU pularam"
    return f"{partes[4]} (capacidade {partes[2]}, {partes[3]} MB)"


def texto(suites: list[Suite], commit: str, gpu_vista: str) -> str:
    total = Counter()
    for suite in suites:
        total += suite.contagem()
    linhas = [
        "Registro de testes — as quatro suítes, rodadas de verdade",
        f"Gerado em {datetime.now():%d/%m/%Y %H:%M} por scripts/registrar_testes.py, "
        f"no commit {commit}",
        f"O otimizador rodou na imagem do núcleo, compilado com CUDA. GPU: {_placa(gpu_vista)}",
        "",
        "Suítes",
    ]
    for suite in suites:
        c = suite.contagem()
        linhas.append(
            f"  {suite.rotulo:<29} {sum(c.values()):>4} testes {c['passou']:>5} passaram"
            f" {c['falhou']:>3} falharam {c['pulado']:>3} pulados {suite.segundos:>5.0f} s"
        )

    linhas += ["", "Os quatro tipos que o enunciado pede — exemplos, com o resultado desta execução"]
    indice = {(s.nome, arquivo, teste): situacao
              for s in suites for (arquivo, teste), situacao in s.resultados.items()}
    for tipo, exemplos in EXEMPLOS.items():
        linhas += ["", f"  {tipo}"]
        for suite, arquivo, teste, prova in exemplos:
            situacao = indice.get((suite, arquivo, teste))
            if situacao is None:
                raise SystemExit(f"O exemplo {suite}:{arquivo}::{teste} não existe mais nesta execução.")
            marca = {"passou": "ok   ", "pulado": "pulou"}.get(situacao, "FALHA")
            linhas.append(f"    {marca} {prova}")
            linhas.append(f"          {suite} · {arquivo} · {teste}")

    linhas += ["", "Por arquivo"]
    for suite in suites:
        linhas += ["", f"  {suite.rotulo}"]
        for arquivo, c in suite.por_arquivo().items():
            falhas = f"  {c['falhou']} FALHA(S)" if c["falhou"] else ""
            linhas.append(f"    {arquivo:<44} {sum(c.values()):>4}{falhas}")

    falhas = [f"{s.rotulo}: {a}::{t}" for s in suites
              for (a, t), sit in s.resultados.items() if sit == "falhou"]
    if falhas:
        linhas += ["", "Falharam:"] + [f"  FALHA {f}" for f in falhas]
    linhas += [
        "",
        f"Resultado: {sum(total.values())} testes, {total['passou']} passaram, "
        f"{total['falhou']} falharam, {total['pulado']} pulados.",
    ]
    return "\n".join(linhas) + "\n"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--saida", required=True, help="pasta das evidências da entrega")
    p.add_argument("--sem-gpu", action="store_true",
                   help="máquina sem placa NVIDIA: o otimizador roda sem --gpus all")
    a = p.parse_args()

    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=RAIZ, capture_output=True, text=True
    ).stdout.strip()
    with tempfile.TemporaryDirectory() as pasta:
        temporaria = Path(pasta)
        print("rodando a suíte da API...", flush=True)
        api = _pytest("api", "API (pytest, Postgres)", RAIZ / "api", temporaria)
        print("rodando a suíte do modelo...", flush=True)
        modelo = _pytest("modelo", "Modelo preditivo (pytest)", RAIZ / "modelo", temporaria)
        print("rodando a suíte do otimizador, na imagem do núcleo...", flush=True)
        otimizador, gpu_vista = _otimizador(temporaria, gpu=not a.sem_gpu)
        print("rodando a suíte da interface...", flush=True)
        interface = _vitest(temporaria)

    registro = texto([api, modelo, otimizador, interface], commit, gpu_vista)
    destino = RAIZ / a.saida
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "testes.txt").write_text(registro, encoding="utf-8")
    print(registro.splitlines()[-1])


if __name__ == "__main__":
    main()
