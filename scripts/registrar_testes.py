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

    api/.venv/Scripts/python scripts/registrar_testes.py --saida docs/entrega/evidencias/sprint08
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

# Os exemplos de cada tipo: (suíte, arquivo, teste, o que prova). Os quatro
# tipos são os que as entregas anteriores nomeiam; o quinto, permissões, é o que
# a Sprint 08 pede.
# Os da Sprint 08: a conta, a redefinição de senha e a conta de perfil Parceiro
# (H92, H93, H101), a página "Sem acesso", o teclado e a sessão (H94, H96), o
# aviso de alterações não salvas (H97), a ajuda (H95), a rastreabilidade (H98) e
# a revisão das regras (H99).
EXEMPLOS: dict[str, list[tuple[str, str, str, str]]] = {
    "Fluxos principais": [
        ("api", "test_usuarios_senha_e_vinculo.py",
         "test_o_administrador_redefine_a_senha_e_a_pessoa_entra_com_a_nova",
         "o administrador redefine a senha, e a pessoa entra com a nova (RF54)"),
        ("api", "test_usuarios_senha_e_vinculo.py",
         "test_cria_a_conta_parceiro_e_a_trilha_diz_de_quem",
         "a conta de perfil Parceiro nasce com o parceiro dela, e a trilha diz qual (RF56)"),
        ("api", "test_ajuda.py", "test_mudar_o_limiar_na_configuracao_muda_o_que_a_ajuda_diz",
         "mudar um limiar na configuração muda o que a ajuda diz (RF55)"),
        ("interface", "MinhaConta.test.jsx",
         "trocar manda a atual e a nova, esvazia os campos e diz que as outras sessões caíram",
         "a troca da própria senha, pela tela (RF07, H92)"),
        ("interface", "Ajuda.test.jsx",
         "os segmentos vêm na ordem que a API mandou, com os limiares em vigor no critério",
         "a ajuda lista os segmentos na ordem da regra, com os limiares em vigor (H95)"),
        ("interface", "AlteracoesNaoSalvas.test.jsx",
         "'Sair sem salvar' segue o link que foi clicado, com o que ele carregava",
         "o aviso de alterações não salvas deixa sair, para onde a pessoa ia (H97)"),
    ],
    "Permissões": [
        ("api", "test_autorizacao.py", "test_toda_rota_tem_permissao_declarada",
         "toda rota da aplicação tem a permissão declarada na matriz (RNF14)"),
        ("api", "test_aprovacao.py",
         "test_o_gestor_ganha_a_capacidade_de_decidir_e_o_analista_nao",
         "a sessão dá ao Gestor a capacidade de decidir as mensagens, e ao Analista não (RN06)"),
        ("api", "test_usuarios_senha_e_vinculo.py", "test_a_busca_devolve_so_o_nome_e_a_situacao",
         "a busca de parceiros do administrador devolve só o nome e a situação (RF56)"),
        ("api", "test_ajuda.py",
         "test_o_parceiro_nao_recebe_as_regras_da_rede_e_a_tela_dele_nao_as_pede",
         "o Parceiro não recebe as regras da rede, e a tentativa fica na trilha (RF26)"),
        ("api", "test_rastreabilidade.py", "test_toda_rota_da_aplicacao_esta_no_documento",
         "toda rota da aplicação está na matriz de rastreabilidade (H98)"),
        ("interface", "App.guarda.test.jsx",
         "a tela que o perfil não tem diz isso, com o perfil e a volta, e não pede nada à API",
         "a página \"Sem acesso\", sem nenhuma chamada à API (H94)"),
    ],
    "Operações com o banco": [
        ("api", "test_usuarios_senha_e_vinculo.py",
         "test_a_redefinicao_derruba_todas_as_sessoes_da_conta",
         "a redefinição encerra todas as sessões da conta"),
        ("api", "test_usuarios_senha_e_vinculo.py",
         "test_a_redefinicao_entra_na_trilha_sem_a_senha",
         "a redefinição entra na trilha de auditoria, sem a senha (RF06)"),
        ("api", "test_usuarios_senha_e_vinculo.py",
         "test_trocar_o_vinculo_registra_o_parceiro_de_antes_e_o_de_depois",
         "trocar o parceiro da conta registra o de antes e o de depois"),
        ("api", "test_ajuda.py", "test_com_treino_concluido_a_ajuda_diz_a_versao_em_uso",
         "a ajuda lê do banco a versão do modelo em uso"),
    ],
    "Validações": [
        ("api", "test_usuarios_senha_e_vinculo.py",
         "test_senha_fraca_na_redefinicao_e_erro_do_campo",
         "a senha fraca na redefinição é erro do campo"),
        ("api", "test_usuarios_senha_e_vinculo.py", "test_a_busca_para_num_teto",
         "a busca de parceiros do administrador para num teto: não devolve a rede inteira"),
        ("api", "test_segmentacao.py", "test_a_ordem_do_enum_e_a_ordem_em_que_a_regra_decide",
         "a ordem dos segmentos que a ajuda mostra é a ordem em que a regra decide (RN01)"),
        ("api", "test_segmentacao.py", "test_nenhum_rotulo_de_segmento_traz_o_numero_do_limiar",
         "nenhum rótulo de segmento traz o número do limiar, que é configurável (#229)"),
        ("interface", "MinhaConta.test.jsx",
         "as duas digitações diferentes não chegam ao servidor",
         "a senha nova digitada de dois jeitos não é enviada"),
    ],
    "Situações de erro": [
        ("api", "test_usuarios_senha_e_vinculo.py",
         "test_a_propria_senha_nao_se_redefine_por_aqui",
         "o administrador não redefine a própria senha: tem a Minha conta, que pede a atual"),
        ("api", "test_usuarios_senha_e_vinculo.py",
         "test_editar_para_parceiro_inexistente_e_erro_do_campo_e_nao_erro_500",
         "vincular a um parceiro que não existe é erro do campo, e não erro 500 (#227)"),
        ("api", "test_ajuda.py",
         "test_sem_treino_concluido_a_ajuda_diz_que_nao_ha_modelo_e_quanto_falta_de_historico",
         "sem modelo treinado, a ajuda diz que não há modelo e quanto histórico falta"),
        ("interface", "Ajuda.test.jsx",
         "se as regras não chegam, a tela diz isso e mantém o que o perfil pode fazer",
         "a ajuda sem as regras diz o que houve, e mantém o que o perfil faz"),
        ("interface", "App.teclado.test.jsx",
         "leva ao login dizendo que a sessão terminou, e depois de entrar volta para onde a "
         "pessoa estava",
         "a sessão que o servidor encerra leva ao login, com o aviso e a volta (H96)"),
        ("interface", "MinhaConta.test.jsx",
         "a senha atual que não confere aparece embaixo dela, com o foco nela",
         "a senha atual errada aparece embaixo do campo, com o foco nele"),
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
