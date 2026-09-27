/**
 * O benchmark — UC09, RF33, história H57 — para Gestor e Administrador.
 *
 * **O mesmo problema em cada modo**, com a mesma semente, e a comparação: tempo,
 * desvio, ganho sobre o Python e sobre o C++ serial, e o ganho esperado do plano,
 * que precisa ser o mesmo nos quatro. As colunas são as da ADR-012; o ganho do
 * OpenMP e o da GPU se leem também contra o C++ serial, porque contra o Python
 * eles mediriam o compilador junto.
 *
 * **A medição roda no servidor**, em segundo plano, como a campanha: a tela
 * dispara, recebe `202` e acompanha o andamento a cada 2 s — o passo, o total e o
 * que está medindo agora. Quem sair e voltar reencontra o andamento.
 *
 * **Quem decide é a API** (regra 2.4): os modos que a máquina tem e por que falta
 * cada um, os ganhos, a divergência de plano e a explicação da GPU que não ganhou
 * chegam prontos. A tela só escolhe, entre os medidos, qual citar primeiro.
 *
 * **Uma execução antiga abre pelo endereço** (`?execucao=`), para o link do
 * histórico poder ser mandado a alguém.
 */
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { api } from "../api/cliente";
import { Esqueleto } from "../componentes/Carregando";
import Campo from "../componentes/Campo";
import Confirmacao from "../componentes/Confirmacao";
import Escalabilidade from "../componentes/Escalabilidade";
import EstadoVazio from "../componentes/EstadoVazio";
import {
  COLUNAS_BENCHMARK,
  COR_COLUNA,
  comoDataHora,
  comoDinheiro,
  comoFracao,
  comoInteiro,
  comoTempo,
  comoVezes,
  ROTULO_COLUNA,
  TRACO,
} from "../formato";
import "../estilos/benchmark.css";

/* De quanto em quanto tempo a tela pergunta pelo andamento. Um passo leva de
   milissegundos (GPU) a minutos (Python com 10.000 parceiros). */
export const INTERVALO_MS = 2000;

const CAMPOS = [
  ["parceiros", "Parceiros", "De 100 a 10.000. O cenário de referência do projeto tem 2.000."],
  ["acoes", "Tipos de ação", "De 1 a 10. As cinco primeiras são as do catálogo de demonstração."],
  ["repeticoes", "Repetições", "De 1 a 10. Mais repetições dão um desvio mais confiável."],
];

export default function Benchmark() {
  const [estado, setEstado] = useState(null);
  const [historico, setHistorico] = useState(null);
  const [erroCarga, setErroCarga] = useState(null);
  const [recarga, setRecarga] = useState(0);
  const [valores, setValores] = useState(null);
  const [acompanhando, setAcompanhando] = useState(null);
  const [terminado, setTerminado] = useState(null);
  const [confirmando, setConfirmando] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState(null);
  const [parametrosUrl, setParametrosUrl] = useSearchParams();
  const idEscolhido = parametrosUrl.get("execucao");
  const [escolhido, setEscolhido] = useState(null);

  useEffect(() => {
    let vivo = true;
    Promise.all([api.get("/api/benchmark"), api.get("/api/benchmarks?tamanho=10")])
      .then(([dados, pagina]) => {
        if (!vivo) return;
        setEstado(dados);
        setHistorico(pagina.itens);
        setValores((atuais) => atuais ?? paraTexto(dados.padrao));
        /* Benchmark em andamento que a tela ainda não acompanha — disparado em
           outra aba, ou antes de a pessoa sair e voltar. */
        if (dados.em_andamento) setAcompanhando(dados.em_andamento);
      })
      .catch((e) => vivo && setErroCarga(e));
    return () => {
      vivo = false;
    };
  }, [recarga]);

  useEffect(() => {
    if (!idEscolhido) return undefined;
    let vivo = true;
    api
      .get(`/api/benchmarks/${idEscolhido}`)
      .then((dados) => vivo && setEscolhido(dados))
      .catch((e) => vivo && setErro(e));
    return () => {
      vivo = false;
    };
  }, [idEscolhido]);

  const idAcompanhado = acompanhando?.id;
  useEffect(() => {
    if (!idAcompanhado) return undefined;
    const relogio = setInterval(() => {
      api
        .get(`/api/benchmarks/${idAcompanhado}`)
        .then((execucao) => {
          if (execucao.situacao === "EM_ANDAMENTO") {
            setAcompanhando(execucao);
            return;
          }
          setAcompanhando(null);
          setTerminado(execucao);
          setErro(null);
          // O resultado novo é o que a tela mostra, e não a execução antiga aberta.
          setParametrosUrl({}, { replace: true });
          setRecarga((r) => r + 1);
        })
        /* Falha de rede numa consulta não encerra o acompanhamento: a próxima
           tenta de novo. O benchmark continua no servidor de qualquer jeito. */
        .catch(() => {});
    }, INTERVALO_MS);
    return () => clearInterval(relogio);
  }, [idAcompanhado, setParametrosUrl]);

  async function rodar() {
    setEnviando(true);
    setErro(null);
    setTerminado(null);
    try {
      const execucao = await api.post("/api/benchmarks", paraNumeros(valores));
      setAcompanhando(execucao);
      setRecarga((r) => r + 1);
    } catch (e) {
      setErro(e);
      /* A recusa mais comum é "já há um benchmark em andamento": reler o estado
         faz a tela encontrá-lo e acompanhá-lo (como no modelo, #108). */
      setRecarga((r) => r + 1);
    } finally {
      setEnviando(false);
      setConfirmando(false);
    }
  }

  if (erroCarga) {
    return (
      <div className="aviso" role="alert">
        <p className="aviso__titulo">{erroCarga.message}</p>
        {erroCarga.ajuda && <p className="aviso__ajuda">{erroCarga.ajuda}</p>}
      </div>
    );
  }

  if (!estado || !valores) {
    return (
      <section className="painel" aria-busy="true" aria-label="Carregando o benchmark">
        <div className="benchmark__corpo">
          <Esqueleto altura={260} />
        </div>
      </section>
    );
  }

  /* A execução aberta pelo endereço, se é ela que chegou; senão, a última. */
  const aberta = idEscolhido && escolhido?.id === Number(idEscolhido) ? escolhido : null;
  const mostrado = aberta ?? estado.ultima;
  const erroDoCampo = Object.fromEntries((erro?.campos ?? []).map((c) => [c.campo, c]));

  return (
    <>
      <p className="so-leitor" role="status">
        {anuncio(acompanhando, terminado)}
      </p>

      {erro && (
        <div className="aviso" role="alert">
          <p className="aviso__titulo">{erro.message}</p>
          {erro.ajuda && <p className="aviso__ajuda">{erro.ajuda}</p>}
        </div>
      )}

      <section className="painel" aria-labelledby="titulo-cenario">
        <div className="painel__cabecalho">
          <h2 className="painel__titulo" id="titulo-cenario">
            Cenário
          </h2>
          <span className="painel__nota">O mesmo problema sintético, com a mesma semente, em cada modo</span>
        </div>
        <Cenario
          estado={estado}
          valores={valores}
          erroDoCampo={erroDoCampo}
          acompanhando={acompanhando}
          confirmando={confirmando}
          enviando={enviando}
          aoMudar={(v) => {
            setValores(v);
            setConfirmando(false);
          }}
          aoPedir={() => {
            setErro(null);
            setConfirmando(true);
          }}
          aoConfirmar={rodar}
          aoCancelar={() => setConfirmando(false)}
        />
      </section>

      {acompanhando && <Andamento execucao={acompanhando} />}

      {mostrado ? (
        <Resultado execucao={mostrado} antiga={Boolean(aberta)} />
      ) : (
        !acompanhando && (
          <section className="painel" aria-label="Resultado">
            <EstadoVazio
              titulo="Nenhum benchmark ainda."
              texto="Rode o primeiro com o cenário sugerido: a tabela e o gráfico aparecem aqui quando ele terminar."
            />
          </section>
        )
      )}

      {historico?.length > 0 && <Historico itens={historico} mostradoId={mostrado?.id} />}
    </>
  );
}

function paraTexto(parametros) {
  return Object.fromEntries(Object.entries(parametros).map(([k, v]) => [k, String(v)]));
}

/* Campo vazio vai como nulo, e não como zero: a API responde "obrigatório", e não
   "precisa ser ao menos 100" para algo que a pessoa não digitou. */
function paraNumeros(valores) {
  return Object.fromEntries(
    Object.entries(valores).map(([k, v]) => [k, v.trim() === "" ? null : Number(v)]),
  );
}

function Cenario({
  estado,
  valores,
  erroDoCampo,
  acompanhando,
  confirmando,
  enviando,
  aoMudar,
  aoPedir,
  aoConfirmar,
  aoCancelar,
}) {
  const estimativa = estimar(estado.python_s_por_parceiro, valores);
  return (
    <form
      className="benchmark__corpo benchmark__cenario"
      noValidate
      onSubmit={(e) => {
        e.preventDefault();
        aoPedir();
      }}
    >
      <div className="benchmark__campos">
        {CAMPOS.map(([nome, rotulo, ajuda]) => (
          <Campo key={nome} id={nome} rotulo={rotulo} obrigatorio erro={erroDoCampo[nome]} ajuda={ajuda}>
            <input
              id={`campo-${nome}`}
              type="number"
              inputMode="numeric"
              value={valores[nome]}
              onChange={(e) => aoMudar({ ...valores, [nome]: e.target.value })}
            />
          </Campo>
        ))}
      </div>

      <div>
        <h3 className="benchmark__subtitulo" id="titulo-modos">
          Modos nesta máquina
        </h3>
        <ul className="benchmark__modos" aria-labelledby="titulo-modos">
          {estado.colunas.map((c) => (
            <li key={c.coluna} className={c.disponivel ? "" : "benchmark__modo--fora"}>
              <Chave coluna={c.coluna} />
              <span className="benchmark__modo-nome">{ROTULO_COLUNA[c.coluna]}</span>
              <span className="benchmark__modo-situacao">
                {c.disponivel ? (c.detalhe ? `disponível, ${c.detalhe}` : "disponível") : `indisponível: ${c.motivo}`}
              </span>
            </li>
          ))}
        </ul>
      </div>

      <p className="benchmark__estimativa">
        {estimativa !== null
          ? `Leva cerca de ${comoTempo(estimativa)}, quase todo no Python, que é o mais lento de longe.`
          : "O Python é o mais lento de longe: com 10.000 parceiros, cada repetição dele leva minutos."}{" "}
        A medição roda no servidor; você pode sair e voltar.
      </p>

      {confirmando ? (
        <Confirmacao
          texto={`Rodar o benchmark com ${comoInteiro(valores.parceiros)} parceiros, ${valores.acoes} tipos de ação e ${
            valores.repeticoes
          } repetições, em cada modo desta máquina?`}
          acao="Rodar"
          ocupado={enviando}
          aoConfirmar={aoConfirmar}
          aoCancelar={aoCancelar}
        />
      ) : (
        <div className="benchmark__acoes">
          <button className="botao" type="submit" disabled={Boolean(acompanhando) || !estado.pode_executar}>
            {acompanhando ? "Medindo…" : "Rodar benchmark"}
          </button>
        </div>
      )}
    </form>
  );
}

/* A estimativa multiplica o tempo do Python por parceiro, da última medição, pelo
   tamanho pedido: o genético cresce em linha com os parceiros. Os outros modos
   somam pouco perto dele. Sem medição anterior, ou com campo vazio, não há o que
   estimar. */
function estimar(porParceiro, valores) {
  const parceiros = Number(valores.parceiros);
  const repeticoes = Number(valores.repeticoes);
  if (!porParceiro || !parceiros || !repeticoes) return null;
  return porParceiro * parceiros * repeticoes;
}

function Chave({ coluna }) {
  return <span className="benchmark__chave" style={{ background: COR_COLUNA[coluna] }} aria-hidden="true" />;
}

function Andamento({ execucao }) {
  const { passo = 0, total = 1, etapa = "Começando" } = execucao.progresso ?? {};
  return (
    <div className="aviso aviso--informativo benchmark__andamento">
      <p className="aviso__titulo">Benchmark em andamento</p>
      <p className="aviso__ajuda">
        {etapa} · passo {passo} de {total}. Iniciado {comoDataHora(execucao.iniciada_em)}
        {execucao.autor ? ` por ${execucao.autor}` : " pelo terminal"}. A tela se atualiza sozinha quando terminar.
      </p>
      <progress className="benchmark__barra" max={total} value={passo} aria-label="Andamento do benchmark" />
    </div>
  );
}

function Resultado({ execucao, antiga }) {
  const p = execucao.parametros;
  const medidas = execucao.colunas.filter((c) => c.situacao === "MEDIDA");
  const foraDoComparativo = execucao.colunas.filter((c) => c.situacao !== "MEDIDA");
  const divergentes = medidas.filter((c) => c.divergente);
  const series = execucao.escalabilidade?.series ?? [];

  return (
    <>
      <section className="painel" aria-labelledby="titulo-resultado">
        <div className="painel__cabecalho">
          <h2 className="painel__titulo" id="titulo-resultado">
            {antiga ? "Benchmark anterior" : "Resultado"}
          </h2>
          <span className="painel__nota">
            {comoInteiro(p.parceiros)} parceiros · {p.acoes} tipos de ação · {p.repeticoes}{" "}
            {p.repeticoes === 1 ? "repetição" : "repetições"} · {comoDataHora(execucao.iniciada_em)}
            {execucao.autor ? `, por ${execucao.autor}` : ""}
          </span>
        </div>

        <div className="benchmark__corpo benchmark__resultado">
          {execucao.situacao === "FALHOU" ? (
            <div className="aviso" role="alert">
              <p className="aviso__titulo">O benchmark não terminou.</p>
              <p className="aviso__ajuda">{execucao.motivo}</p>
            </div>
          ) : (
            <>
              <p className="benchmark__manchete">{manchete(medidas)}</p>

              {divergentes.map((c) => (
                <div key={c.coluna} className="aviso" role="alert">
                  <p className="aviso__titulo">
                    O plano do {ROTULO_COLUNA[c.coluna]} diverge do Python em {comoFracao(c.diferenca_uplift)}.
                  </p>
                  <p className="aviso__ajuda">
                    Com a mesma semente, os modos dão o mesmo plano; acima de 2% (RNF02), é possível defeito de
                    implementação.
                  </p>
                </div>
              ))}

              {execucao.explicacao_gpu && (
                <div className="aviso aviso--informativo">
                  <p className="aviso__titulo">Por que a GPU não ganhou aqui</p>
                  <p className="aviso__ajuda">{execucao.explicacao_gpu}</p>
                </div>
              )}

              {execucao.disputada && (
                <div className="aviso aviso--informativo">
                  <p className="aviso__titulo">Outro cálculo rodou durante a medição.</p>
                  <p className="aviso__ajuda">
                    Uma otimização ou um treino dividiu a máquina com o benchmark, e os tempos podem ter saído maiores.
                    Para comparar, rode de novo com a máquina livre.
                  </p>
                </div>
              )}

              <Comparativo colunas={execucao.colunas} />

              {(foraDoComparativo.length > 0 || execucao.ambiente) && (
                <ul className="benchmark__notas">
                  {foraDoComparativo.map((c) => (
                    <li key={c.coluna}>
                      {ROTULO_COLUNA[c.coluna]}: {c.motivo}
                    </li>
                  ))}
                  {execucao.ambiente && <li>{ambiente(execucao.ambiente)}</li>}
                </ul>
              )}
            </>
          )}
        </div>
      </section>

      {series.length > 0 && (
        <section className="painel" aria-labelledby="titulo-escalabilidade">
          <div className="painel__cabecalho">
            <h2 className="painel__titulo" id="titulo-escalabilidade">
              Escalabilidade
            </h2>
            <span className="painel__nota">
              Tempo médio por número de parceiros, com {execucao.escalabilidade.acoes} tipos de ação · escalas
              logarítmicas
            </span>
          </div>
          <Escalabilidade series={series} acoes={execucao.escalabilidade.acoes} destaque={p.parceiros} />
        </section>
      )}
    </>
  );
}

/* A frase que resume a tabela: o modo mais rápido, quanto ele ganha do Python, e
   se o plano foi o mesmo. Escolher o mais rápido entre os medidos é leitura da
   tabela, e não regra: os números vêm prontos da API. */
function manchete(medidas) {
  if (!medidas.length) return "Nenhum modo terminou a medição.";
  const python = medidas.find((c) => c.coluna === "PYTHON");
  const maisRapido = medidas.reduce((a, b) => (b.media_s < a.media_s ? b : a));
  const mesmoPlano = medidas.every((c) => !c.divergente);
  const plano = mesmoPlano
    ? medidas.length > 1
      ? ` O plano foi o mesmo ${medidas.length === 2 ? "nos dois modos" : `nos ${medidas.length} modos`}.`
      : ""
    : " O plano divergiu: veja abaixo.";
  if (maisRapido.coluna === "PYTHON" || !python) {
    return `${ROTULO_COLUNA[maisRapido.coluna]}: ${comoTempo(maisRapido.media_s)} em média.${plano}`;
  }
  const gpu = maisRapido.coluna === "GPU";
  return `O mais rápido foi ${gpu ? "a" : "o"} ${ROTULO_COLUNA[maisRapido.coluna]}: ${comoTempo(
    maisRapido.media_s,
  )} em média, ${comoVezes(maisRapido.speedup_python)} ${gpu ? "mais rápida" : "mais rápido"} que o Python, que levou ${comoTempo(
    python.media_s,
  )}.${plano}`;
}

function ambiente({ threads, gpu, compilador }) {
  const partes = [];
  if (threads) partes.push(`OpenMP com ${threads} threads, uma por núcleo físico`);
  if (gpu) partes.push(`GPU ${gpu}`);
  if (compilador) partes.push(`compilado com ${compilador}`);
  return `Onde mediu: ${partes.join(" · ")}.`;
}

/* As quatro colunas da ADR-012, sempre na mesma ordem e com a mesma cor do
   gráfico; o modo que não mediu fica na tabela, com travessão, e o motivo vai na
   nota embaixo — sumir com a coluna faria a comparação parecer completa. */
const LINHAS = [
  ["Tempo médio", (c) => comoTempo(c.media_s), true],
  ["Desvio padrão", (c) => (c.desvio_s === null ? TRACO : `± ${comoTempo(c.desvio_s)}`)],
  ["Ganho sobre o Python", (c) => (c.coluna === "PYTHON" ? "base" : comoVezes(c.speedup_python)), true],
  [
    "Ganho sobre o C++ serial",
    (c) => (c.coluna === "CPP_SERIAL" ? "base" : c.speedup_cpp === null ? TRACO : comoVezes(c.speedup_cpp)),
  ],
  ["Início da GPU (contexto)", (c) => (c.contexto_s === null ? TRACO : comoTempo(c.contexto_s))],
  ["Uplift do plano", (c) => comoDinheiro(c.uplift)],
  [
    "Diferença para o Python",
    (c) =>
      c.diferenca_uplift === null
        ? TRACO
        : `${comoFracao(c.diferenca_uplift)}${c.divergente ? ", acima de 2%" : ""}`,
  ],
];

function Comparativo({ colunas }) {
  const porColuna = Object.fromEntries(colunas.map((c) => [c.coluna, c]));
  const ordem = COLUNAS_BENCHMARK.map(([c]) => c).filter((c) => porColuna[c]);
  return (
    <div className="tabela-rolagem">
      <table className="tabela benchmark__tabela">
        <caption className="so-leitor">Comparativo dos modos de execução</caption>
        <thead>
          <tr>
            <th scope="col">Medida</th>
            {ordem.map((c) => (
              <th key={c} scope="col" className="numerica">
                <span className="benchmark__coluna">
                  <Chave coluna={c} />
                  {ROTULO_COLUNA[c]}
                </span>
                {porColuna[c].situacao !== "MEDIDA" && (
                  <span className="benchmark__coluna-fora">
                    {porColuna[c].situacao === "FALHOU" ? "falhou" : "indisponível"}
                  </span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {LINHAS.map(([rotulo, valor, forte]) => (
            <tr key={rotulo}>
              <th scope="row" className={forte ? "nome" : undefined}>
                {rotulo}
              </th>
              {ordem.map((c) => {
                const coluna = porColuna[c];
                const medida = coluna.situacao === "MEDIDA";
                return (
                  <td
                    key={c}
                    className={`numerica${forte && medida ? " benchmark__forte" : ""}${
                      coluna.divergente && rotulo === "Diferença para o Python" ? " benchmark__divergente" : ""
                    }`}
                  >
                    {medida ? valor(coluna) : TRACO}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Historico({ itens, mostradoId }) {
  return (
    <section className="painel" aria-labelledby="titulo-historico">
      <div className="painel__cabecalho">
        <h2 className="painel__titulo" id="titulo-historico">
          Benchmarks anteriores
        </h2>
        <span className="painel__nota">Os dez mais recentes</span>
      </div>
      <div className="tabela-rolagem">
        <table className="tabela">
          <caption className="so-leitor">Benchmarks anteriores, do mais recente para o mais antigo</caption>
          <thead>
            <tr>
              <th scope="col">Quando</th>
              <th scope="col">Cenário</th>
              {COLUNAS_BENCHMARK.map(([c, rotulo]) => (
                <th key={c} scope="col" className="numerica">
                  {rotulo}
                </th>
              ))}
              <th scope="col">
                <span className="so-leitor">Abrir</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {itens.map((e) => {
              const porColuna = Object.fromEntries(e.colunas.map((c) => [c.coluna, c]));
              return (
                <tr key={e.id} aria-current={e.id === mostradoId ? "true" : undefined}>
                  <td>
                    {comoDataHora(e.iniciada_em)}
                    <span className="secundaria">{e.autor ? ` · ${e.autor}` : " · terminal"}</span>
                  </td>
                  <td className="secundaria">
                    {comoInteiro(e.parametros.parceiros)} × {e.parametros.acoes} ações × {e.parametros.repeticoes}
                  </td>
                  {e.situacao === "CONCLUIDA" ? (
                    COLUNAS_BENCHMARK.map(([c]) => (
                      <td key={c} className="numerica">
                        {(porColuna[c]?.media_s ?? null) === null ? TRACO : comoTempo(porColuna[c].media_s)}
                      </td>
                    ))
                  ) : (
                    <td colSpan={COLUNAS_BENCHMARK.length} className="secundaria">
                      {e.situacao === "FALHOU" ? "Falhou" : "Em andamento"}
                    </td>
                  )}
                  <td>
                    {e.situacao !== "EM_ANDAMENTO" && e.id !== mostradoId && (
                      <Link className="nome__link" to={`/benchmark?execucao=${e.id}`}>
                        Abrir
                      </Link>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function anuncio(acompanhando, terminado) {
  if (acompanhando) return "Medindo o benchmark.";
  if (!terminado) return "";
  if (terminado.situacao === "FALHOU") return `O benchmark falhou. ${terminado.motivo}`;
  return `Benchmark concluído. ${manchete(terminado.colunas.filter((c) => c.situacao === "MEDIDA"))}`;
}
