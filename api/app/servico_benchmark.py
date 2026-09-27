"""O benchmark — UC09, RF33, história H57.

Roda **o mesmo problema** em cada modo que a máquina tem, com a mesma semente,
repetido, e compara o tempo e o plano. As quatro colunas são as da ADR-012:

- **Python**, o baseline do RNF02 — o mesmo genético, em Python puro;
- **C++ serial**, **OpenMP** e **GPU**, o executável do núcleo.

O ganho do OpenMP e o da GPU são lidos também contra o C++ serial: contra o
Python, o ganho mediria o compilador junto com o paralelismo (ADR-012).

**O problema é sintético** (`gih_nucleo.cenario`), do tamanho que o gestor
escolhe: a base de trabalho tem a escala da operação, pequena demais para
mostrar o ganho do paralelismo (`docs/07` §4.3).

**Como se mede**, e por quê:

- **O Python roda noutro processo.** Dentro da API, ele dividiria o interpretador
  com as requisições da própria tela, que consulta o andamento, e o tempo do
  baseline sairia maior — e o ganho medido, mais bonito do que é.
- **Cada tempo é o de quem busca**: o Python e o executável medem a própria busca.
  Na GPU, ele inclui iniciar o driver e criar o contexto da placa, e o contexto
  vem também à parte (H54c): é o que explica a GPU que não ganha num cenário
  pequeno (UC09-A2).
- **Os modos se intercalam**: cada repetição roda todos, um depois do outro, para
  que uma oscilação da máquina caia sobre todos. Os modos do executável rodam
  uma vez antes, descartada: a primeira execução paga a leitura do executável do
  disco. O Python não — cada rodada dele leva segundos, e ele não tem o que
  aquecer.
- **O plano é conferido**: o ganho de cada modo, em cada repetição, contra o do
  Python. Acima de 2% é divergência, e a tela a destaca como possível defeito
  (RNF02, UC09-A3). Com a mesma semente, a diferença é zero (ADR-011).
- **Se outro cálculo pesado rodou junto** — uma otimização, um treino —, a
  execução fica marcada: os tempos podem ter saído maiores.

Roda em segundo plano, como o otimizador: `iniciar` grava a execução em
andamento, `executar` mede e grava o resultado. **Um por vez**, pelo banco.
"""
from __future__ import annotations

import logging
import multiprocessing
import statistics
import uuid
from collections.abc import Iterator
from concurrent.futures import Executor, ProcessPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass, field

import gih_nucleo
from gih_nucleo import cenario, nativo
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import auditoria, servico_otimizacao
from app.auditoria import Acao
from app.db import sessao
from app.esquemas import (
    ColunaBenchmark,
    ParametrosBenchmark,
    PontoEscalabilidade,
    ResultadoColuna,
    SerieEscalabilidade,
    SituacaoColuna,
)
from app.modelos import ExecucaoBenchmark, ExecucaoOtimizador, SituacaoExecucao, TreinoModelo

log = logging.getLogger("gih")

ORDEM = tuple(ColunaBenchmark)
ROTULO = {
    ColunaBenchmark.PYTHON: "Python",
    ColunaBenchmark.CPP_SERIAL: "C++ serial",
    ColunaBenchmark.OPENMP: "OpenMP",
    ColunaBenchmark.GPU: "GPU",
}
NO_EXECUTAVEL = {
    ColunaBenchmark.CPP_SERIAL: "serial",
    ColunaBenchmark.OPENMP: "openmp",
    ColunaBenchmark.GPU: "cuda",
}

# A semente da busca é a da campanha; a do problema é a do cenário. Com as duas
# fixas, o mesmo tamanho dá o mesmo plano, em qualquer modo e em qualquer dia.
SEMENTE = servico_otimizacao.SEMENTE

# O que a tela sugere ao abrir: o cenário de referência (`docs/07` §4.3), com
# menos repetições — as dez de lá levariam minutos de Python.
PADRAO = ParametrosBenchmark(parceiros=2000, acoes=5, repeticoes=3)

# Os parâmetros do genético, além do cenário. Vazio: os da campanha. Os testes
# os encurtam, para o Python terminar em milissegundos.
PARAMETROS_DA_BUSCA: dict[str, int] = {}

# A tolerância de qualidade do RNF02.
TOLERANCIA = 0.02


# ------------------------------------------------------------ as recusas
class BenchmarkRecusado(Exception):
    def __init__(self, erro: str, ajuda: str, *, status: int = 409, **extra) -> None:
        super().__init__(erro)
        self.erro = erro
        self.ajuda = ajuda
        self.status = status
        self.extra = extra


def em_andamento(s: Session) -> ExecucaoBenchmark | None:
    return s.scalar(
        select(ExecucaoBenchmark).where(
            ExecucaoBenchmark.situacao == SituacaoExecucao.EM_ANDAMENTO
        )
    )


def ultima_concluida(s: Session) -> ExecucaoBenchmark | None:
    return s.scalar(
        select(ExecucaoBenchmark)
        .where(ExecucaoBenchmark.situacao == SituacaoExecucao.CONCLUIDA)
        .order_by(ExecucaoBenchmark.id.desc())
    )


def _recusa_por_andamento(execucao: ExecucaoBenchmark) -> BenchmarkRecusado:
    return BenchmarkRecusado(
        "Já existe um benchmark em andamento.",
        "Acompanhe o atual; dois ao mesmo tempo dividiriam a máquina e mediriam a disputa.",
        em_andamento=execucao.id,
    )


# ------------------------------------------------------------ os modos
@dataclass(frozen=True)
class Disponibilidade:
    coluna: ColunaBenchmark
    disponivel: bool
    motivo: str | None
    detalhe: str | None = None


def colunas() -> tuple[list[Disponibilidade], nativo.Capacidades | None]:
    """As quatro colunas, e se esta máquina tem cada uma (UC09, passo 3 e A1).

    Os motivos são os da campanha: quem diz é o executável (ADR-012).
    """
    capacidades, sem_nucleo = servico_otimizacao.perguntar_ao_nucleo()
    threads = nativo.nucleos_fisicos()
    existe = {
        ColunaBenchmark.PYTHON: True,
        ColunaBenchmark.CPP_SERIAL: capacidades is not None,
        ColunaBenchmark.OPENMP: capacidades is not None and "openmp" in capacidades.modos,
        ColunaBenchmark.GPU: servico_otimizacao.tem_gpu(capacidades),
    }
    faltando = {
        ColunaBenchmark.CPP_SERIAL: sem_nucleo,
        ColunaBenchmark.OPENMP: sem_nucleo or servico_otimizacao.SEM_PARALELO,
        ColunaBenchmark.GPU: sem_nucleo or servico_otimizacao.motivo_sem_gpu(capacidades),
    }
    detalhe = {
        ColunaBenchmark.OPENMP: f"{threads} threads" if threads else None,
        ColunaBenchmark.GPU: capacidades.gpu.nome if capacidades and capacidades.gpu else None,
    }
    return [
        Disponibilidade(coluna, True, None, detalhe.get(coluna))
        if existe[coluna]
        else Disponibilidade(coluna, False, faltando[coluna])
        for coluna in ORDEM
    ], capacidades


# ------------------------------------------------------------ iniciar
def iniciar(
    s: Session, parametros: ParametrosBenchmark, *, usuario_id: int | None
) -> ExecucaoBenchmark:
    """Grava um benchmark em andamento, ou recusa se já há um.

    Como no otimizador: a consulta dá a recusa com o benchmark que está rodando,
    e o índice único parcial fecha a corrida entre duas requisições.
    """
    rodando = em_andamento(s)
    if rodando is not None:
        raise _recusa_por_andamento(rodando)
    execucao = ExecucaoBenchmark(
        usuario_id=usuario_id,
        parceiros=parametros.parceiros,
        acoes=parametros.acoes,
        repeticoes=parametros.repeticoes,
        semente=SEMENTE,
        progresso={"passo": 0, "total": 1, "etapa": "Montando o cenário"},
    )
    try:
        with s.begin_nested():
            s.add(execucao)
            s.flush()
    except IntegrityError:
        raise _recusa_por_andamento(em_andamento(s)) from None
    return execucao


# ------------------------------------------------------------ medir
@dataclass
class _Medidas:
    tempos: list[float] = field(default_factory=list)
    contextos: list[float] = field(default_factory=list)
    ganhos: list[int] = field(default_factory=list)


@contextmanager
def processo_do_python() -> Iterator[Executor]:
    """Um processo à parte para o baseline, criado do zero (`spawn`).

    `fork` copiaria a API inteira, com as threads dela, para dentro do filho.
    """
    with ProcessPoolExecutor(
        max_workers=1, mp_context=multiprocessing.get_context("spawn")
    ) as executor:
        yield executor


def _rodar(
    coluna: ColunaBenchmark,
    inst: gih_nucleo.Instancia,
    python: Executor,
    threads: int | None,
) -> gih_nucleo.Resultado:
    if coluna == ColunaBenchmark.PYTHON:
        return python.submit(
            gih_nucleo.otimizar, inst, semente=SEMENTE, **PARAMETROS_DA_BUSCA
        ).result()
    return nativo.otimizar(
        inst,
        semente=SEMENTE,
        modo=NO_EXECUTAVEL[coluna],
        threads=threads if coluna == ColunaBenchmark.OPENMP else None,
        **PARAMETROS_DA_BUSCA,
    )


def _avancar(execucao_id: int, passo: int, total: int, etapa: str) -> None:
    """O andamento, numa transação curta: a tela consulta enquanto mede."""
    with sessao() as s:
        s.get(ExecucaoBenchmark, execucao_id).progresso = {
            "passo": passo,
            "total": total,
            "etapa": etapa,
        }


def _medir(execucao_id: int, parametros: ParametrosBenchmark) -> tuple[list[dict], dict]:
    """Mede cada coluna disponível; devolve os resultados crus e o ambiente."""
    inst = cenario.sintetico(parametros.parceiros, parametros.acoes)
    disponiveis, capacidades = colunas()
    threads = nativo.nucleos_fisicos()
    medidas = {d.coluna: _Medidas() for d in disponiveis if d.disponivel}
    falhas: dict[ColunaBenchmark, str] = {}
    compiladas = [c for c in medidas if c != ColunaBenchmark.PYTHON]
    repeticoes = parametros.repeticoes
    total = len(compiladas) + repeticoes * len(medidas)
    passo = 0

    def rodar(coluna: ColunaBenchmark) -> gih_nucleo.Resultado | None:
        try:
            return _rodar(coluna, inst, python, threads)
        except nativo.SemGpu as falha:
            # UC09-E1: a GPU que falha fica de fora desta execução, e o resto segue.
            log.warning("Benchmark %s: a GPU falhou e sai da medição (%s)", execucao_id, falha)
            falhas[coluna] = (
                "A GPU não respondeu durante a medição; os outros modos seguiram sem ela."
            )
            return None

    with processo_do_python() as python:
        for coluna in compiladas:
            passo += 1
            _avancar(execucao_id, passo, total, f"{ROTULO[coluna]}, rodada de aquecimento")
            rodar(coluna)
        for repeticao in range(1, repeticoes + 1):
            for coluna, m in medidas.items():
                passo += 1
                if coluna in falhas:
                    continue
                etapa = f"{ROTULO[coluna]}, repetição {repeticao} de {repeticoes}"
                _avancar(execucao_id, passo, total, etapa)
                r = rodar(coluna)
                if r is None:
                    continue
                m.tempos.append(r.segundos)
                m.contextos.append(r.contexto_s)
                m.ganhos.append(r.avaliacao.ganho)

    resultados = []
    for d in disponiveis:
        if not d.disponivel:
            resultados.append({"coluna": d.coluna, "situacao": "INDISPONIVEL", "motivo": d.motivo})
        elif d.coluna in falhas:
            motivo = falhas[d.coluna]
            resultados.append({"coluna": d.coluna, "situacao": "FALHOU", "motivo": motivo})
        else:
            m = medidas[d.coluna]
            resultados.append(
                {
                    "coluna": d.coluna,
                    "situacao": "MEDIDA",
                    "motivo": None,
                    "tempos_s": m.tempos,
                    "contextos_s": m.contextos if d.coluna == ColunaBenchmark.GPU else None,
                    "ganhos_centavos": m.ganhos,
                }
            )
    ambiente = {
        "threads": threads if ColunaBenchmark.OPENMP in medidas else None,
        "gpu": capacidades.gpu.nome if capacidades and capacidades.gpu else None,
        "compilador": capacidades.compilador if capacidades else None,
        "semente_do_cenario": cenario.SEMENTE,
        **PARAMETROS_DA_BUSCA,
    }
    return resultados, ambiente


def _disputada(s: Session, execucao: ExecucaoBenchmark) -> bool:
    """Outra otimização ou um treino rodou em algum momento da medição?"""
    agora = s.scalar(select(func.clock_timestamp()))
    otimizacoes = s.scalar(
        select(func.count())
        .select_from(ExecucaoOtimizador)
        .where(
            ExecucaoOtimizador.iniciada_em <= agora,
            or_(
                ExecucaoOtimizador.concluida_em.is_(None),
                ExecucaoOtimizador.concluida_em >= execucao.iniciada_em,
            ),
        )
    )
    treinos = s.scalar(
        select(func.count())
        .select_from(TreinoModelo)
        .where(
            TreinoModelo.iniciado_em <= agora,
            or_(
                TreinoModelo.concluido_em.is_(None),
                TreinoModelo.concluido_em >= execucao.iniciada_em,
            ),
        )
    )
    return bool(otimizacoes or treinos)


def executar(execucao_id: int, *, origem: str | None = None) -> None:
    """Roda o benchmark gravado por `iniciar`. É o que vai para segundo plano.

    **Nunca propaga exceção**, como o otimizador: em segundo plano não há quem a
    receba, e o benchmark ficaria em andamento para sempre, prendendo a trava.
    """
    usuario_id = None
    try:
        with sessao() as s:
            execucao = s.get(ExecucaoBenchmark, execucao_id)
            usuario_id = execucao.usuario_id
            parametros = ParametrosBenchmark(
                parceiros=execucao.parceiros,
                acoes=execucao.acoes,
                repeticoes=execucao.repeticoes,
            )
        resultados, ambiente = _medir(execucao_id, parametros)
        with sessao() as s:
            execucao = s.get(ExecucaoBenchmark, execucao_id)
            execucao.resultados = resultados
            execucao.ambiente = ambiente
            execucao.progresso = None
            execucao.disputada = _disputada(s, execucao)
            execucao.situacao = SituacaoExecucao.CONCLUIDA
            execucao.concluida_em = s.scalar(select(func.clock_timestamp()))
            resumo = {
                r.coluna.value: r.media_s for r in resumir(execucao) if r.media_s is not None
            }
            detalhes = {
                "execucao": execucao.id,
                "parametros": parametros.model_dump(),
                "medias_s": resumo,
                "disputada": execucao.disputada,
            }
        auditoria.registrar(
            Acao.BENCHMARK_EXECUTADO, usuario_id=usuario_id, detalhes=detalhes, origem=origem
        )
    except Exception:
        correlacao = uuid.uuid4().hex[:12]
        log.exception("[%s] Benchmark %s falhou", correlacao, execucao_id)
        motivo = f"O benchmark falhou por um erro interno (registro {correlacao})."
        _marcar_falha(execucao_id, motivo)
        auditoria.registrar(
            Acao.BENCHMARK_FALHOU,
            usuario_id=usuario_id,
            detalhes={"execucao": execucao_id, "motivo": motivo},
            origem=origem,
        )


def _marcar_falha(execucao_id: int, motivo: str) -> None:
    try:
        with sessao() as s:
            execucao = s.get(ExecucaoBenchmark, execucao_id)
            if execucao is not None and execucao.situacao == SituacaoExecucao.EM_ANDAMENTO:
                execucao.situacao = SituacaoExecucao.FALHOU
                execucao.concluida_em = s.scalar(select(func.clock_timestamp()))
                execucao.progresso = None
                execucao.motivo = motivo
    except Exception:
        log.exception("Não foi possível marcar o benchmark %s como falho", execucao_id)


def recuperar_interrompidos(s: Session) -> int:
    """Marca como falhos os benchmarks que ficaram em andamento — chamada na subida."""
    interrompidos = list(
        s.scalars(
            select(ExecucaoBenchmark).where(
                ExecucaoBenchmark.situacao == SituacaoExecucao.EM_ANDAMENTO
            )
        )
    )
    agora = s.scalar(select(func.now()))
    for execucao in interrompidos:
        execucao.situacao = SituacaoExecucao.FALHOU
        execucao.concluida_em = agora
        execucao.progresso = None
        execucao.motivo = "Interrompido: a API reiniciou durante o benchmark. Rode de novo."
    return len(interrompidos)


# ------------------------------------------------------------ ler o resultado
def _media(valores: list[float]) -> float | None:
    return statistics.fmean(valores) if valores else None


def resumir(execucao: ExecucaoBenchmark) -> list[ResultadoColuna]:
    """A tabela comparativa (UC09, passo 6), a partir das medidas cruas."""
    if not execucao.resultados:
        return []
    crus = {ColunaBenchmark(r["coluna"]): r for r in execucao.resultados}
    medias = {c: _media(r.get("tempos_s") or []) for c, r in crus.items()}
    python = medias.get(ColunaBenchmark.PYTHON)
    cpp = medias.get(ColunaBenchmark.CPP_SERIAL)
    ganhos_python = (crus.get(ColunaBenchmark.PYTHON) or {}).get("ganhos_centavos") or []
    referencia = ganhos_python[0] if ganhos_python else None

    resposta = []
    for coluna in ORDEM:
        r = crus.get(coluna)
        if r is None:
            continue
        tempos = r.get("tempos_s") or []
        media = medias[coluna]
        ganhos = r.get("ganhos_centavos") or []
        diferenca = None
        if ganhos and referencia:
            diferenca = max(abs(g - referencia) for g in ganhos) / referencia
        contextos = r.get("contextos_s")
        resposta.append(
            ResultadoColuna(
                coluna=coluna,
                situacao=SituacaoColuna(r["situacao"]),
                motivo=r.get("motivo"),
                tempos_s=tempos,
                media_s=media,
                desvio_s=statistics.stdev(tempos) if len(tempos) >= 2 else None,
                contexto_s=_media(contextos) if contextos else None,
                speedup_python=python / media if python and media else None,
                speedup_cpp=(
                    cpp / media
                    if cpp and media
                    and coluna in (ColunaBenchmark.OPENMP, ColunaBenchmark.GPU)
                    else None
                ),
                uplift=servico_otimizacao.reais(ganhos[0]) if ganhos else None,
                diferenca_uplift=diferenca,
                divergente=diferenca is not None and diferenca > TOLERANCIA,
            )
        )
    return resposta


def escalabilidade(s: Session, acoes: int) -> list[SerieEscalabilidade]:
    """O tempo de cada modo pelo número de parceiros (UC09, passo 7).

    Das execuções concluídas com este número de ações, a mais recente de cada
    tamanho: o gráfico se completa conforme o gestor mede tamanhos diferentes.
    """
    execucoes = s.scalars(
        select(ExecucaoBenchmark)
        .where(
            ExecucaoBenchmark.situacao == SituacaoExecucao.CONCLUIDA,
            ExecucaoBenchmark.acoes == acoes,
        )
        .order_by(ExecucaoBenchmark.id.desc())
    )
    por_tamanho: dict[int, ExecucaoBenchmark] = {}
    for e in execucoes:
        por_tamanho.setdefault(e.parceiros, e)
    pontos: dict[ColunaBenchmark, list[PontoEscalabilidade]] = {c: [] for c in ORDEM}
    for parceiros in sorted(por_tamanho):
        e = por_tamanho[parceiros]
        for r in resumir(e):
            if r.media_s is not None:
                pontos[r.coluna].append(
                    PontoEscalabilidade(parceiros=parceiros, media_s=r.media_s, execucao_id=e.id)
                )
    return [SerieEscalabilidade(coluna=c, pontos=p) for c, p in pontos.items() if p]


def _mil(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def _duracao(segundos: float) -> str:
    if segundos >= 1:
        return f"{segundos:.2f} s".replace(".", ",")
    ms = segundos * 1000
    return (f"{ms:.1f}" if ms < 100 else f"{ms:.0f}").replace(".", ",") + " ms"


def _vezes(fator: float) -> str:
    return f"{fator:.1f}x".replace(".", ",")


def explicar_gpu(
    execucao: ExecucaoBenchmark,
    resumo: list[ResultadoColuna],
    series: list[SerieEscalabilidade],
) -> str | None:
    """Por que a GPU não ganhou neste tamanho, quando não ganhou (UC09-A2).

    A comparação é com o CPU paralelo, ou com o C++ serial se ele faltar. O
    resultado negativo é informação, e não defeito: a GPU paga um custo fixo
    antes de qualquer conta (H54c), e só compensa quando o laço pesa mais que ele.
    """
    por_coluna = {r.coluna: r for r in resumo}
    gpu = por_coluna.get(ColunaBenchmark.GPU)
    rival = next(
        (
            por_coluna[c]
            for c in (ColunaBenchmark.OPENMP, ColunaBenchmark.CPP_SERIAL)
            if c in por_coluna and por_coluna[c].media_s
        ),
        None,
    )
    if gpu is None or gpu.media_s is None or rival is None or gpu.media_s <= rival.media_s:
        return None
    nome_rival = "o CPU paralelo" if rival.coluna == ColunaBenchmark.OPENMP else "o C++ serial"
    texto = f"Com {_mil(execucao.parceiros)} parceiros, a GPU não ganha d{nome_rival}"
    contexto = gpu.contexto_s or 0.0
    laco = gpu.media_s - contexto
    if contexto > 0 and laco > 0:
        texto += (
            f": ela gasta {_duracao(contexto)} para começar — iniciar o driver e criar o "
            f"contexto da placa — antes de qualquer conta. A busca em si leva {_duracao(laco)}"
        )
        if laco < rival.media_s:
            texto += f", {_vezes(rival.media_s / laco)} mais rápida que a d{nome_rival}"
        texto += "."
    else:
        texto += "."
    # O tamanho em que ela passou a ganhar, se já foi medido.
    gpu_serie = next((s for s in series if s.coluna == ColunaBenchmark.GPU), None)
    rival_serie = next((s for s in series if s.coluna == rival.coluna), None)
    virada = None
    if gpu_serie and rival_serie:
        do_rival = {p.parceiros: p.media_s for p in rival_serie.pontos}
        virada = next(
            (
                p.parceiros
                for p in gpu_serie.pontos
                if p.parceiros > execucao.parceiros
                and p.parceiros in do_rival
                and p.media_s < do_rival[p.parceiros]
            ),
            None,
        )
    if virada:
        texto += (
            f" Nas medições com {execucao.acoes} ações, ela passa a ganhar com "
            f"{_mil(virada)} parceiros."
        )
    else:
        texto += " Ela ganha nas campanhas maiores, quando a busca pesa mais que esse custo fixo."
    return texto + " É um resultado legítimo, e não um defeito."


def python_s_por_parceiro(s: Session) -> float | None:
    """O tempo do Python por parceiro e repetição, na última medição que o tem."""
    for e in s.scalars(
        select(ExecucaoBenchmark)
        .where(ExecucaoBenchmark.situacao == SituacaoExecucao.CONCLUIDA)
        .order_by(ExecucaoBenchmark.id.desc())
        .limit(5)
    ):
        python = next(
            (r for r in resumir(e) if r.coluna == ColunaBenchmark.PYTHON and r.media_s), None
        )
        if python is not None:
            return python.media_s / e.parceiros
    return None
