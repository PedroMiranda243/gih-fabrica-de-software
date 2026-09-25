"""Roda as três suítes de teste e gera o registro de testes de uma entrega.

O enunciado da Sprint 05 pede testes dos fluxos principais, das operações com o
banco, das validações e das situações de erro, **com os resultados registrados
no documento**. Este script é o registro: roda as suítes de verdade — API,
modelo e interface — e escreve o que passou e o que falhou, por suíte e por
arquivo.

**Os quatro tipos do enunciado vêm com exemplos nomeados**, escolhidos à mão e
conferidos contra a execução: se um exemplo deixar de existir, o script recusa
em vez de publicar um teste que não rodou. Classificar os seiscentos testes um a
um nos quatro tipos seria arbitrário — muitos são mais de um ao mesmo tempo —; os
exemplos mostram o que cada tipo cobre, e o total diz quanto roda.

A suíte da API precisa do Postgres no ar (o `conftest` cria o banco de teste).
**Não rode duas vezes ao mesmo tempo**: as duas execuções truncariam as tabelas
uma da outra.

Uso, da raiz do projeto:

    api/.venv/Scripts/python scripts/registrar_testes.py --saida docs/entrega/evidencias/sprint05
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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Os exemplos de cada tipo que o enunciado nomeia: (suíte, arquivo, teste, o que prova).
EXEMPLOS: dict[str, list[tuple[str, str, str, str]]] = {
    "Fluxos principais": [
        ("api", "test_previsao.py", "test_treinar_registra_data_volume_e_metricas",
         "o treino pela tela grava data, volume e métricas (RF27, UC07)"),
        ("api", "test_previsao.py", "test_previsao_no_cadastro_e_estimativa_com_base_e_versao",
         "a previsão chega ao cadastro do parceiro com base e versão (RF28)"),
        ("modelo", "test_treino.py", "test_na_rede_sintetica_a_rede_supera_as_referencias",
         "a rede supera as referências nas duas saídas (H42, H43)"),
        ("api", "test_importacao.py", "test_importa_e_grava_as_metricas",
         "a importação grava as métricas do período (módulo da Sprint 04)"),
        ("interface", "Modelo.test.jsx",
         "treinar pede confirmação, acompanha o andamento e anuncia o resultado",
         "a tela dispara o treino, acompanha e anuncia o resultado"),
    ],
    "Operações com o banco": [
        ("api", "test_previsao.py", "test_os_pesos_gravados_refazem_as_previsoes",
         "os pesos gravados no banco refazem as previsões gravadas"),
        ("api", "test_previsao.py", "test_versao_que_nao_supera_nao_entra_e_as_versoes_coexistem",
         "versões coexistem no banco sobre o mesmo período (UC07-A2)"),
        ("api", "test_previsao.py", "test_o_banco_nao_aceita_dois_treinos_em_andamento",
         "o índice único parcial recusa dois treinos em andamento"),
        ("api", "test_previsao.py", "test_ler_o_historico_nao_faz_uma_consulta_por_parceiro[60]",
         "ler o histórico não faz uma consulta por parceiro"),
        ("api", "test_importacao.py", "test_substituir_troca_as_metricas_sem_duplicar",
         "substituir um período troca as métricas sem duplicar"),
    ],
    "Validações": [
        ("api", "test_previsao.py", "test_historico_curto_recusa_dizendo_quantos_faltam",
         "histórico curto é recusado dizendo quantos períodos faltam (UC07-E1, RN09)"),
        ("api", "test_previsao.py", "test_o_rotulo_de_risco_e_o_segmento_em_risco",
         "o rótulo de risco é o segmento Em Risco, ponto a ponto (RN09)"),
        ("modelo", "test_variaveis.py", "test_nenhuma_amostra_anterior_enxerga_o_periodo_seguinte[teste]",
         "nenhuma amostra de treino enxerga o período de teste (H41)"),
        ("api", "test_importacao.py", "test_sem_periodo_a_importacao_e_recusada",
         "importação sem período é recusada (RN03)"),
        ("api", "test_erros.py", "test_tipo_ainda_sem_traducao_nao_vaza_a_frase_em_ingles",
         "erro de validação sem tradução não vaza a frase em inglês"),
    ],
    "Situações de erro": [
        ("api", "test_previsao.py", "test_falha_no_treino_vira_falhou_com_motivo_e_libera_a_trava",
         "falha no treino vira FALHOU, com motivo, e libera a trava"),
        ("api", "test_previsao.py", "test_a_subida_da_api_libera_o_treino_interrompido",
         "a API que reinicia no meio do treino o marca como falho na subida"),
        ("api", "test_previsao.py", "test_com_um_treino_rodando_o_segundo_e_recusado",
         "um segundo treino, com outro rodando, é recusado com 409"),
        ("modelo", "test_treino.py", "test_pesos_sao_lidos_sem_executar_codigo",
         "pesos adulterados não executam código ao serem lidos"),
        ("api", "test_erros.py", "test_falha_inesperada_responde_generico_com_correlacao",
         "falha inesperada responde genérico, com identificador de correlação"),
        ("interface", "Modelo.test.jsx", "a recusa do servidor aparece com a ajuda",
         "a recusa da API aparece na tela com a ajuda"),
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


def _pytest(nome: str, rotulo: str, pasta: Path, temporaria: Path) -> Suite:
    relatorio = temporaria / f"{nome}.xml"
    inicio = time.perf_counter()
    subprocess.run(
        [_python_da_api(), "-m", "pytest", "-q", "-p", "no:cacheprovider",
         f"--junitxml={relatorio}"],
        cwd=pasta, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    suite = Suite(nome, rotulo, segundos=time.perf_counter() - inicio)
    if not relatorio.exists():
        raise SystemExit(f"A suíte {rotulo} não produziu relatório — ela nem chegou a rodar.")
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


def texto(suites: list[Suite], commit: str) -> str:
    total = Counter()
    for suite in suites:
        total += suite.contagem()
    linhas = [
        "Registro de testes — as três suítes, rodadas de verdade",
        f"Gerado em {datetime.now():%d/%m/%Y %H:%M} por scripts/registrar_testes.py, "
        f"no commit {commit}",
        "",
        "Suítes",
    ]
    for suite in suites:
        c = suite.contagem()
        linhas.append(
            f"  {suite.rotulo:<30} {sum(c.values()):>4} testes  {c['passou']:>4} passaram  "
            f"{c['falhou']:>3} falharam  {suite.segundos:>6.0f} s"
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
            marca = "ok   " if situacao == "passou" else "FALHA"
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
        f"{total['falhou']} falharam.",
    ]
    return "\n".join(linhas) + "\n"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--saida", required=True, help="pasta das evidências da entrega")
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
        print("rodando a suíte da interface...", flush=True)
        interface = _vitest(temporaria)

    registro = texto([api, modelo, interface], commit)
    destino = RAIZ / a.saida
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "testes.txt").write_text(registro, encoding="utf-8")
    print(registro.splitlines()[-1])


if __name__ == "__main__":
    main()
