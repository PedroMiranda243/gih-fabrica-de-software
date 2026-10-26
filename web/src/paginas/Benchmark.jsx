/**
 * Benchmark — o mesmo problema, com a mesma semente, em quatro modos. A API decide
 * tudo (quais modos a máquina tem, os ganhos, a explicação); a tela desenha. Cada
 * modo tem cor e marcador fixos, em qualquer execução.
 */
import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { api, ErroDaApi } from "../api/cliente";
import { useAcompanhar, useCarregar } from "../api/ganchos";
import { Ausente } from "../componentes/Dados";
import { Carregando, ErroDaAcao, ErroDaTela, Nota, Vazio } from "../componentes/Estados";
import { Campo, ResumoDeErros } from "../componentes/Formulario";
import { useErrosDoFormulario } from "../componentes/useErrosDoFormulario";
import Icone from "../componentes/Icone";
import { CaixaDeTabela } from "../componentes/Lista";
import { useTitulo } from "../componentes/Titulo";
import GraficoEscalabilidade, { Marcador } from "../graficos/GraficoEscalabilidade";
import VerNumeros from "../graficos/VerNumeros";
import { comoDataHora, comoDinheiro, comoFracao, comoInteiro, comoTempo, comoVezes, ORDEM_COLUNAS, ROTULO_COLUNA } from "../formato";

const DESCRICAO = {
  PYTHON: "O baseline: o mesmo genético, em Python puro.",
  CPP_SERIAL: "O mesmo genético compilado, numa thread só: mostra quanto é do compilador.",
  OPENMP: "O C++ com os núcleos do processador em paralelo: o CPU paralelo da campanha.",
  GPU: "O C++ com CUDA, na placa de vídeo: o modo GPU da campanha.",
};

export default function Benchmark() {
  useTitulo("Benchmark");
  const [busca, setBusca] = useSearchParams();
  const anterior = busca.get("execucao");
  const estado = useCarregar(() => api.get("/api/benchmark"), "bench");
  const historico = useCarregar(() => api.get("/api/benchmarks", { tamanho: 10 }), "hist");
  const antigo = useCarregar(() => api.get(`/api/benchmarks/${anterior}`), `a${anterior}`, { ativo: Boolean(anterior) });
  const [acompanhando, setAcompanhando] = useState(null);
  const [terminados, setTerminados] = useState([]);
  const [recemTerminado, setRecemTerminado] = useState(null);

  const emAndamento = estado.dados?.em_andamento;
  const id = acompanhando ?? (emAndamento && !terminados.includes(emAndamento.id) ? emAndamento.id : null);
  const medicao = useAcompanhar(id, (x) => api.get(`/api/benchmarks/${x}`), (b) => {
    setTerminados((l) => [...l, b.id]);
    setAcompanhando(null);
    setRecemTerminado(b);
    estado.recarregar();
    historico.recarregar();
  });

  if (estado.carregando) return <Carregando rotulo="Carregando o benchmark" linhas={8} />;
  if (estado.erro) return <ErroDaTela erro={estado.erro} />;
  const e = estado.dados;
  const rodando = id !== null && (!medicao.atual || medicao.atual.situacao === "EM_ANDAMENTO");
  const exibido = anterior ? antigo.dados : (recemTerminado ?? e.ultima);

  return (
    <div className="pagina">
      <p className="sr-only" role="status" aria-live="polite">
        {rodando ? `Benchmark em andamento${medicao.atual?.progresso ? `, passo ${medicao.atual.progresso.passo} de ${medicao.atual.progresso.total}` : ""}.` : recemTerminado ? (recemTerminado.situacao === "FALHOU" ? "O benchmark falhou." : "Benchmark concluído.") : ""}
      </p>
      <div className="bench-grade">
        <Cenario estado={e} rodando={rodando} aoRodar={(x) => (setRecemTerminado(null), setAcompanhando(x))} medicao={medicao.atual} />
        <section className="bloco" aria-labelledby="t-modos">
          <div className="bloco__cabeca">
            <h2 id="t-modos" className="bloco__titulo">
              Modos nesta máquina
            </h2>
          </div>
          <ul className="modos">
            {ORDEM_COLUNAS.map((c) => {
              const d = e.colunas.find((x) => x.coluna === c);
              return (
                <li key={c} className={`modo serie--${c.toLowerCase()}${d?.disponivel ? "" : " modo--ausente"}`}>
                  <svg width="18" height="18" aria-hidden="true" className="modo__marca">
                    <Marcador coluna={c} x={9} y={9} r={6} />
                  </svg>
                  <div>
                    <p className="modo__nome">
                      {ROTULO_COLUNA[c]}
                      {d?.detalhe && <span className="discreto"> · {d.detalhe}</span>}
                    </p>
                    <p className="modo__descricao">{DESCRICAO[c]}</p>
                    {d && !d.disponivel && <p className="modo__falta">Indisponível: {d.motivo}</p>}
                  </div>
                </li>
              );
            })}
          </ul>
        </section>
      </div>

      {anterior && (
        <div className="faixa-anterior" role="status">
          <p>
            <Icone nome="relogio" /> <strong>Benchmark anterior</strong>
            {antigo.dados ? ` — medido em ${comoDataHora(antigo.dados.iniciada_em)}` : ""}.
          </p>
          <button type="button" className="botao botao--secundario botao--pequeno" onClick={() => setBusca({})}>
            Ver o mais recente
          </button>
        </div>
      )}
      {anterior && antigo.carregando && <Carregando rotulo="Carregando o benchmark anterior" linhas={6} />}
      {anterior && <ErroDaTela erro={antigo.erro} />}

      {!exibido && !anterior && !rodando && (
        <Vazio titulo="Nenhum benchmark ainda." icone="benchmark">
          Rode o primeiro com o cenário sugerido: a tabela e o gráfico aparecem aqui quando ele terminar.
        </Vazio>
      )}
      {exibido && <Resultado b={exibido} />}

      <section className="bloco" aria-labelledby="t-anteriores">
        <div className="bloco__cabeca">
          <h2 id="t-anteriores" className="bloco__titulo">
            Benchmarks anteriores
          </h2>
          <p className="bloco__sub">Os dez mais recentes</p>
        </div>
        {historico.carregando && <Carregando rotulo="Carregando os anteriores" linhas={3} />}
        <ErroDaTela erro={historico.erro} />
        {historico.dados && !historico.dados.itens.length && <p className="discreto">Nenhum ainda.</p>}
        {historico.dados && historico.dados.itens.length > 0 && (
          <CaixaDeTabela rotulo="Benchmarks anteriores">
            <table className="tabela">
              <caption className="sr-only">Os dez benchmarks mais recentes, com o tempo médio de cada modo</caption>
              <thead>
                <tr>
                  <th scope="col">Quando</th>
                  <th scope="col">Cenário</th>
                  {ORDEM_COLUNAS.map((c) => (
                    <th key={c} scope="col" className="num">
                      {ROTULO_COLUNA[c]}
                    </th>
                  ))}
                  <th scope="col">
                    <span className="sr-only">Abrir</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {historico.dados.itens.map((b) => (
                  <tr key={b.id} className={String(b.id) === anterior ? "linha--marcada" : undefined}>
                    <th scope="row">{comoDataHora(b.iniciada_em)}</th>
                    <td>
                      {comoInteiro(b.parametros.parceiros)} parceiros · {comoInteiro(b.parametros.acoes)} ações · {comoInteiro(b.parametros.repeticoes)} repetições
                    </td>
                    {ORDEM_COLUNAS.map((c) => {
                      const col = b.colunas.find((x) => x.coluna === c);
                      return (
                        <td key={c} className="num">
                          {b.situacao === "EM_ANDAMENTO" ? <span className="discreto">medindo…</span> : col?.media_s === null || col?.media_s === undefined ? <Ausente porque={col?.motivo ?? "não medido"} /> : comoTempo(col.media_s)}
                        </td>
                      );
                    })}
                    <td>
                      {b.situacao !== "EM_ANDAMENTO" && (
                        <Link to={`/benchmark?execucao=${b.id}`} aria-label={`Abrir o benchmark de ${comoDataHora(b.iniciada_em)}`}>
                          Abrir
                        </Link>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CaixaDeTabela>
        )}
      </section>
    </div>
  );
}

function Cenario({ estado, rodando, aoRodar, medicao }) {
  const [v, setV] = useState({ parceiros: String(estado.padrao.parceiros), acoes: String(estado.padrao.acoes), repeticoes: String(estado.padrao.repeticoes) });
  const [enviando, setEnviando] = useState(false);
  const [recusa, setRecusa] = useState(null);
  const { erros, receber, limpar, limparCampo, registrar } = useErrosDoFormulario();
  const num = (s) => (s === "" || Number.isNaN(Number(s)) ? s : Number(s));

  const estimativa = estado.python_s_por_parceiro && Number(v.parceiros) > 0 && Number(v.repeticoes) > 0 ? estado.python_s_por_parceiro * Number(v.parceiros) * Number(v.repeticoes) : null;

  async function rodar(evento) {
    evento.preventDefault();
    limpar();
    setRecusa(null);
    setEnviando(true);
    try {
      const b = await api.post("/api/benchmarks", { parceiros: num(v.parceiros), acoes: num(v.acoes), repeticoes: num(v.repeticoes) });
      aoRodar(b.id);
    } catch (e) {
      if (e instanceof ErroDaApi && e.status === 409) {
        setRecusa(e);
        if (e.detalhe?.em_andamento) aoRodar(e.detalhe.em_andamento);
      } else receber(e, { ordem: ["parceiros", "acoes", "repeticoes"] });
    } finally {
      setEnviando(false);
    }
  }

  const p = medicao?.progresso;
  return (
    <section className="bloco" aria-labelledby="t-cenario">
      <div className="bloco__cabeca">
        <h2 id="t-cenario" className="bloco__titulo">
          Cenário
        </h2>
        <p className="bloco__sub">O mesmo problema sintético, com a mesma semente, em cada modo.</p>
      </div>
      <form className="formulario" onSubmit={rodar} noValidate>
        <ResumoDeErros erros={erros} rotulos={{ parceiros: "Parceiros", acoes: "Ações", repeticoes: "Repetições" }} />
        <ErroDaAcao erro={recusa} />
        <div className="grupo-campos grupo-campos--tres">
          <Campo nome="parceiros" rotulo="Parceiros" erro={erros.campos.parceiros} ajuda="De 100 a 10.000. O cenário de referência do projeto tem 2.000.">
            {(a) => <input {...a} ref={registrar("parceiros")} className="entrada" inputMode="numeric" value={v.parceiros} onChange={(e) => (setV((x) => ({ ...x, parceiros: e.target.value })), limparCampo("parceiros"))} />}
          </Campo>
          <Campo nome="acoes" rotulo="Ações" erro={erros.campos.acoes} ajuda="De 1 a 10. As cinco primeiras são as do catálogo de demonstração.">
            {(a) => <input {...a} ref={registrar("acoes")} className="entrada" inputMode="numeric" value={v.acoes} onChange={(e) => (setV((x) => ({ ...x, acoes: e.target.value })), limparCampo("acoes"))} />}
          </Campo>
          <Campo nome="repeticoes" rotulo="Repetições" erro={erros.campos.repeticoes} ajuda="De 1 a 10. Mais repetições dão um desvio mais confiável.">
            {(a) => <input {...a} ref={registrar("repeticoes")} className="entrada" inputMode="numeric" value={v.repeticoes} onChange={(e) => (setV((x) => ({ ...x, repeticoes: e.target.value })), limparCampo("repeticoes"))} />}
          </Campo>
        </div>
        {estimativa !== null && <p className="campo__ajuda">Leva cerca de {comoTempo(estimativa)}, quase todo no Python, que é o mais lento de longe.</p>}
        {estado.pode_executar ? (
          <div className="formulario__acoes">
            <button type="submit" className="botao botao--primario" disabled={rodando || enviando}>
              <Icone nome="benchmark" /> {rodando ? "Benchmark em andamento…" : "Rodar benchmark"}
            </button>
          </div>
        ) : (
          <Nota>{estado.motivo_bloqueio ?? "Rodar o benchmark não é do seu perfil."}</Nota>
        )}
      </form>
      {rodando && (
        <div className="andamento" role="status">
          <p>
            <strong>Benchmark em andamento</strong>
            {p ? ` — passo ${comoInteiro(p.passo)} de ${comoInteiro(p.total)}: ${p.etapa}` : ""}
          </p>
          <span className="andamento__barra" aria-hidden="true">
            <span style={{ width: p ? `${Math.min(100, (p.passo / Math.max(p.total, 1)) * 100)}%` : "4%" }} />
          </span>
          <p className="discreto">A medição roda no servidor; você pode sair e voltar.</p>
        </div>
      )}
    </section>
  );
}

function Resultado({ b }) {
  if (b.situacao === "FALHOU") return <ErroDaAcao erro={{ message: `O benchmark falhou.${b.motivo ? ` ${b.motivo}` : ""}` }} />;
  if (b.situacao === "EM_ANDAMENTO") return null;
  const cols = ORDEM_COLUNAS.map((c) => b.colunas.find((x) => x.coluna === c) ?? { coluna: c, situacao: "INDISPONIVEL", media_s: null });
  const medidas = cols.filter((c) => c.situacao === "MEDIDA" && c.media_s !== null);
  const rapido = medidas.reduce((m, c) => (m === null || c.media_s < m.media_s ? c : m), null);
  const python = cols.find((c) => c.coluna === "PYTHON");
  const divergiu = cols.some((c) => c.divergente);
  const ausentes = cols.filter((c) => c.situacao !== "MEDIDA");

  const linhas = [
    ["Tempo médio", (c) => (c.media_s === null ? null : comoTempo(c.media_s))],
    ["Desvio padrão", (c) => (c.desvio_s === null || c.desvio_s === undefined ? null : `± ${comoTempo(c.desvio_s)}`)],
    ["Ganho sobre o Python", (c) => (c.coluna === "PYTHON" ? "base" : c.speedup_python === null || c.speedup_python === undefined ? null : comoVezes(c.speedup_python))],
    ["Ganho sobre o C++ serial", (c) => (c.coluna === "CPP_SERIAL" ? "base" : c.speedup_cpp === null || c.speedup_cpp === undefined ? null : comoVezes(c.speedup_cpp))],
    ["Início da GPU (contexto)", (c) => (c.contexto_s === null || c.contexto_s === undefined ? null : comoTempo(c.contexto_s))],
    ["Uplift do plano", (c) => (c.uplift === null || c.uplift === undefined ? null : comoDinheiro(c.uplift))],
    ["Diferença para o Python", (c) => (c.coluna === "PYTHON" ? "base" : c.diferenca_uplift === null || c.diferenca_uplift === undefined ? null : `${comoFracao(Math.abs(c.diferenca_uplift), 2)}${c.divergente ? ", acima de 2%" : ""}`)],
  ];

  return (
    <section className="bloco bloco--resultado-bench" aria-labelledby="t-resultado">
      <div className="bloco__cabeca">
        <h2 id="t-resultado" className="bloco__titulo">
          Resultado
        </h2>
        <p className="bloco__sub">
          {comoInteiro(b.parametros.parceiros)} parceiros · {comoInteiro(b.parametros.acoes)} ações · {comoInteiro(b.parametros.repeticoes)} repetições · medido em {comoDataHora(b.iniciada_em)}
          {b.autor ? ` por ${b.autor}` : ""}
        </p>
      </div>
      {rapido && (
        <p className="frase-resumo">
          O mais rápido foi {rapido.coluna === "GPU" ? "a GPU" : `o ${ROTULO_COLUNA[rapido.coluna]}`}: <strong>{comoTempo(rapido.media_s)}</strong> em média
          {python?.media_s && rapido.coluna !== "PYTHON" && rapido.speedup_python ? `, ${comoVezes(rapido.speedup_python)} mais rápid${rapido.coluna === "GPU" ? "a" : "o"} que o Python, que levou ${comoTempo(python.media_s)}` : ""}.{" "}
          {divergiu ? <span className="texto-erro">O plano divergiu: veja abaixo.</span> : `O plano foi o mesmo nos ${medidas.length} modos.`}
        </p>
      )}
      {b.disputada && <Nota tipo="atencao">Outro cálculo rodou durante a medição: os tempos podem ter saído maiores.</Nota>}

      <h3 className="bloco__subtitulo">Comparativo dos modos de execução</h3>
      <CaixaDeTabela rotulo="Comparativo dos modos de execução">
        <table className="tabela tabela--bench">
          <caption className="sr-only">Comparativo dos quatro modos: tempo, desvio, ganhos, início da GPU e o plano encontrado</caption>
          <thead>
            <tr>
              <th scope="col">Medida</th>
              {cols.map((c) => (
                <th key={c.coluna} scope="col" className={`num serie--${c.coluna.toLowerCase()}${c.divergente ? " coluna--divergente" : ""}`}>
                  <span className="cabeca-serie">
                    <svg width="12" height="12" aria-hidden="true">
                      <Marcador coluna={c.coluna} x={6} y={6} r={4.5} />
                    </svg>
                    {ROTULO_COLUNA[c.coluna]}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {linhas.map(([rotulo, valor]) => (
              <tr key={rotulo}>
                <th scope="row">{rotulo}</th>
                {cols.map((c) => {
                  const texto = c.situacao === "MEDIDA" ? valor(c) : null;
                  return (
                    <td key={c.coluna} className={`num${c.divergente ? " coluna--divergente" : ""}${c === rapido && rotulo === "Tempo médio" ? " celula--vencedora" : ""}`}>
                      {texto ?? <Ausente porque={c.situacao === "MEDIDA" ? "não se aplica" : (c.motivo ?? "modo indisponível")} />}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </CaixaDeTabela>
      {divergiu && (
        <Nota tipo="erro" titulo="Possível defeito">
          O ganho esperado do plano precisa ser o mesmo nos quatro modos. O modo destacado passou da tolerância de 2% contra o Python.
        </Nota>
      )}
      {ausentes.length > 0 && (
        <ul className="notas-ausentes">
          {ausentes.map((c) => (
            <li key={c.coluna}>
              <strong>{ROTULO_COLUNA[c.coluna]}</strong> sem medição{c.motivo ? `: ${c.motivo}` : "."}
            </li>
          ))}
        </ul>
      )}
      {b.explicacao_gpu && (
        <div className="explicacao">
          <h3 className="bloco__subtitulo">Por que a GPU não ganhou aqui</h3>
          <p>{b.explicacao_gpu}</p>
        </div>
      )}
      {b.ambiente && (
        <div className="explicacao">
          <h3 className="bloco__subtitulo">Onde mediu</h3>
          <ul className="ambiente">
            {b.ambiente.threads && <li>OpenMP com {comoInteiro(b.ambiente.threads)} threads, uma por núcleo físico</li>}
            {b.ambiente.gpu && <li>Placa: {b.ambiente.gpu}</li>}
            {b.ambiente.compilador && <li>Compilador: {b.ambiente.compilador}</li>}
          </ul>
        </div>
      )}

      {b.escalabilidade?.series?.length > 0 && (
        <>
          <h3 className="bloco__subtitulo">Escalabilidade</h3>
          <p className="bloco__sub">O tempo de cada modo pelo número de parceiros, com {comoInteiro(b.escalabilidade.acoes)} ações, nos tamanhos já medidos.</p>
          <VerNumeros
            legenda="Escalabilidade: tempo médio de cada modo por número de parceiros"
            colunas={[{ rotulo: "Parceiros" }, ...ORDEM_COLUNAS.map((c) => ({ rotulo: ROTULO_COLUNA[c] }))]}
            linhas={[...new Set(b.escalabilidade.series.flatMap((s) => s.pontos.map((p) => p.parceiros)))]
              .sort((x, y) => x - y)
              .map((n) => [
                comoInteiro(n),
                ...ORDEM_COLUNAS.map((c) => {
                  const pt = b.escalabilidade.series.find((s) => s.coluna === c)?.pontos.find((p) => p.parceiros === n);
                  return pt ? comoTempo(pt.media_s) : <Ausente key={c} porque="não medido" />;
                }),
              ])}
          >
            <GraficoEscalabilidade escalabilidade={b.escalabilidade} />
          </VerNumeros>
        </>
      )}
    </section>
  );
}
