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

    api/.venv/Scripts/python scripts/registrar_testes.py --saida docs/entrega/evidencias/sprint07
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
# Os da Sprint 07: o painel num recorte e com os três módulos (H82, H83), os
# relatórios e a exportação (H84 a H88), a trilha na tela e o histórico do
# cadastro (H89, H90), e os filtros e a busca que faltavam (H91).
EXEMPLOS: dict[str, list[tuple[str, str, str, str]]] = {
    "Fluxos principais": [
        ("api", "test_painel.py", "test_no_ranking_da_categoria_a_posicao_continua_a_da_rede",
         "no painel filtrado por categoria, a posição continua a da rede (H82, RN02)"),
        ("api", "test_painel_decisao.py", "test_o_previsto_e_o_medido_somam_os_mesmos_parceiros",
         "o painel traz o previsto ao lado do medido, nos mesmos parceiros (H83)"),
        ("api", "test_relatorios.py", "test_o_total_do_relatorio_e_o_indicador_do_painel",
         "o total do relatório de desempenho é o indicador do painel (RF44)"),
        ("api", "test_relatorios.py", "test_o_risco_do_relatorio_e_o_do_cadastro_e_diz_de_que_modelo",
         "o risco do relatório é o da previsão no cadastro, e diz de que modelo (RF45)"),
        ("api", "test_parceiros_historico.py",
         "test_o_historico_conta_o_que_mudou_quando_e_por_quem",
         "o cadastro do parceiro conta o que mudou, quando e por quem (RF50)"),
        ("interface", "Relatorios.test.jsx",
         "os filtros vão para a API e para o CSV, que é a mesma consulta",
         "os filtros do relatório vão para a tela e para o arquivo exportado"),
        ("interface", "Auditoria.test.jsx",
         "mostra quando, quem, a ação em português e o que aconteceu",
         "a trilha de auditoria na tela, com a ação em português (H89)"),
    ],
    "Operações com o banco": [
        ("api", "test_relatorios.py", "test_o_relatorio_da_campanha_soma_o_plano_gravado",
         "o relatório da campanha soma o plano gravado (RF46)"),
        ("api", "test_relatorios.py", "test_as_operacoes_somam_a_trilha_no_mesmo_recorte",
         "o relatório de operações soma a trilha no mesmo recorte (RF47)"),
        ("api", "test_relatorios.py", "test_o_desempenho_nao_faz_uma_consulta_por_parceiro",
         "o relatório de desempenho não faz uma consulta por parceiro (RNF03)"),
        ("api", "test_auditoria.py", "test_busca_no_que_foi_gravado_e_em_quem_fez",
         "a busca na trilha procura no que foi gravado e em quem fez (RF49)"),
        ("api", "test_campanha.py",
         "test_os_filtros_do_historico_se_combinam_e_o_total_e_o_do_recorte",
         "os filtros do histórico de execuções se combinam (RF51)"),
        ("api", "test_usuarios.py", "test_a_busca_ignora_maiuscula_e_acento_dos_dois_lados",
         "a busca de usuários ignora maiúscula e acento (RF52)"),
    ],
    "Validações": [
        ("api", "test_usuarios.py", "test_a_busca_trata_curinga_como_texto",
         "a busca de usuários trata o curinga digitado como texto"),
        ("api", "test_relatorios.py", "test_datas_invertidas_sao_recusa_e_nao_um_relatorio_vazio",
         "datas invertidas são recusadas, em vez de virar um relatório vazio"),
        ("api", "test_painel.py",
         "test_a_serie_e_de_um_parceiro_ou_de_uma_categoria_e_nao_dos_dois",
         "a série é de um parceiro ou de uma categoria, e não dos dois"),
        ("api", "test_relatorios.py",
         "test_categoria_com_nome_de_formula_nao_vira_formula_na_planilha",
         "texto com cara de fórmula não vira fórmula no arquivo exportado"),
        ("api", "test_parceiros_historico.py",
         "test_o_contato_entra_como_alterado_e_o_valor_fica_fora_da_trilha",
         "o contato entra na trilha como alterado, sem o valor"),
    ],
    "Situações de erro": [
        ("api", "test_relatorios.py", "test_execucao_sem_plano_e_recusada_com_o_porque",
         "o relatório de uma execução sem plano é recusado, com o porquê"),
        ("api", "test_relatorios.py",
         "test_sem_modelo_treinado_o_relatorio_de_risco_diz_o_que_falta",
         "sem modelo treinado, o relatório de risco diz o que falta"),
        ("api", "test_auditoria.py", "test_a_exportacao_e_so_do_administrador",
         "a exportação da trilha de auditoria é só do administrador (RF08)"),
        ("api", "test_campanha.py",
         "test_execucao_sem_plano_nao_tem_csv_e_a_resposta_diz_por_que",
         "a execução sem plano não tem o que exportar, e a resposta diz por quê (RF53)"),
        ("interface", "impressao.test.js",
         "quem escolheu o escuro imprime no claro, e volta ao escuro depois",
         "a tela no tema escuro imprime no claro, e volta ao escuro depois (RF48)"),
        ("interface", "Painel.test.jsx",
         "recorte que a API recusa mostra o erro e deixa escolher outro",
         "o recorte que a API recusa mostra o erro, e deixa escolher outro"),
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
