/**
 * A campanha — UC08, RF29 a RF32, histórias H48 a H52 e H55.
 *
 * O Gestor configura as restrições e calcula o plano; o Analista consulta o
 * último plano e o catálogo. **Quem pode o quê vem da API** (regras 2.4 e 2.5):
 * a tela recebe `pode_executar` e `pode_editar_catalogo` prontos, com o porquê.
 *
 * **O cálculo não roda na requisição** (ADR-011): "Calcular plano" recebe `202`
 * com a execução em andamento, e a tela consulta a cada 2 s até ela terminar,
 * como na tela do modelo. O resultado é o plano, ou a campanha inviável com a
 * restrição e quanto falta (RN07) — nunca um plano parcial.
 *
 * **A tela só traduz o que a pessoa digita**: "30" na cota vira a fração 0,3 e
 * "12.000,00" vira 12000.00. Se é viável, quanto cabe e quem entra, quem
 * responde é a API. O mesmo vale para o modo de execução (RF32): quais existem
 * nesta instalação, e qual roda sem escolha, vêm da API.
 */
import { useEffect, useId, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api/cliente";
import Campo from "../componentes/Campo";
import { Esqueleto } from "../componentes/Carregando";
import Confirmacao from "../componentes/Confirmacao";
import EstadoVazio from "../componentes/EstadoVazio";
import Segmento from "../componentes/Segmento";
import {
  comoDataHora,
  comoDecimal,
  comoDinheiro,
  comoFracao,
  comoInteiro,
  comoPeriodo,
  lerReais,
  paraFracao,
  TRACO,
} from "../formato";
import "../estilos/campanha.css";

/* Mesmo intervalo da tela do modelo: a busca serial leva segundos na base de
   demonstração (`docs/medicoes/otimizador.md`). */
export const INTERVALO_MS = 2000;

/* Cada linha de cota ganha uma chave ao nascer: a posição mudaria ao remover
   uma do meio, e o React reaproveitaria o campo errado. */
let proximaChave = 0;
const novaCota = () => ({ chave: ++proximaChave, categoria_id: "", minimo: "", maximo: "" });

/* Na ordem em que aceleram, a mesma das séries do benchmark (docs/09): o rótulo
   do seletor, o nome no meio da frase e o que o modo é. */
const MODOS = [
  ["SERIAL", "Serial", "serial", "A referência, em Python: o mesmo plano, em muito mais tempo. Serve para comparar."],
  ["CPU_PARALELO", "CPU paralelo", "CPU paralelo", "O núcleo em C++, com os núcleos do processador em paralelo."],
  ["GPU", "GPU", "GPU", "O núcleo em CUDA, na placa de vídeo."],
];
const ROTULO_DO_MODO = Object.fromEntries(MODOS.map(([modo, rotulo]) => [modo, rotulo]));
const NOME_DO_MODO = Object.fromEntries(MODOS.map(([modo, , nome]) => [modo, nome]));

/** Abaixo de um segundo, em milissegundos: "0,1 s" esconderia a diferença entre os modos. */
function comoDuracao(ms) {
  return ms < 1000 ? `${comoInteiro(ms)} ms` : `${comoDecimal(ms / 1000, 1)} s`;
}

const MOTIVOS_FORA = [
  ["historico_curto", "com histórico curto"],
  ["fora_do_periodo", "sem dado no período das previsões"],
  ["sem_previsao", "sem previsão da versão em uso"],
  ["inativos", "inativos"],
  ["em_prospeccao", "em prospecção"],
];

function paraPercentual(fracao) {
  if (fracao === null || fracao === undefined) return "";
  return String(Math.round(Number(fracao) * 10000) / 100).replace(".", ",");
}

/** A campanha vale para o período seguinte ao das previsões: é o que elas estimam. */
function periodoSeguinte(periodo) {
  if (!periodo?.data_fim) return { inicio: "", fim: "" };
  const dia = (iso, mais) => {
    const d = new Date(`${iso}T12:00:00Z`);
    d.setUTCDate(d.getUTCDate() + mais);
    return d.toISOString().slice(0, 10);
  };
  return { inicio: dia(periodo.data_fim, 1), fim: dia(periodo.data_fim, 7) };
}

function valoresIniciais(estado) {
  const { inicio, fim } = periodoSeguinte(estado?.periodo_base);
  return { orcamento: "", maximo_acoes: "", cauda: "", cotas: [], inicio, fim, modo: "" };
}

function corpoDo(valores) {
  return {
    orcamento: lerReais(valores.orcamento),
    maximo_acoes: valores.maximo_acoes === "" ? null : Number(valores.maximo_acoes),
    cota_cauda_longa: paraFracao(valores.cauda),
    cotas_categoria: valores.cotas
      .filter((c) => c.categoria_id !== "")
      .map((c) => ({
        categoria_id: Number(c.categoria_id),
        minimo: paraFracao(c.minimo),
        maximo: paraFracao(c.maximo),
      })),
    aplicacao_inicio: valores.inicio,
    aplicacao_fim: valores.fim,
    modo: valores.modo || null,
  };
}

export default function Campanha() {
  const [estado, setEstado] = useState(null);
  const [erroCarga, setErroCarga] = useState(null);
  const [recarga, setRecarga] = useState(0);
  const [valores, setValores] = useState(null);
  const [acompanhando, setAcompanhando] = useState(null);
  const [resultado, setResultado] = useState(null);
  const [confirmando, setConfirmando] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState(null);

  useEffect(() => {
    let vivo = true;
    api
      .get("/api/campanha")
      .then((dados) => {
        if (!vivo) return;
        setEstado(dados);
        setValores((v) => v ?? valoresIniciais(dados));
        /* Cálculo disparado em outra aba, ou antes de a pessoa sair e voltar. */
        if (dados.em_andamento) setAcompanhando(dados.em_andamento);
      })
      .catch((e) => vivo && setErroCarga(e));
    return () => {
      vivo = false;
    };
  }, [recarga]);

  const idAcompanhado = acompanhando?.id;
  useEffect(() => {
    if (!idAcompanhado) return undefined;
    const relogio = setInterval(() => {
      api
        .get(`/api/otimizacoes/${idAcompanhado}`)
        .then((execucao) => {
          if (execucao.situacao === "EM_ANDAMENTO") return;
          setAcompanhando(null);
          setResultado(execucao);
          setErro(null);
          setRecarga((r) => r + 1);
        })
        /* Uma consulta que falha não encerra o acompanhamento: a próxima tenta
           de novo, e o cálculo continua no servidor de qualquer jeito. */
        .catch(() => {});
    }, INTERVALO_MS);
    return () => clearInterval(relogio);
  }, [idAcompanhado]);

  async function calcular() {
    setEnviando(true);
    setErro(null);
    setResultado(null);
    try {
      const execucao = await api.post("/api/otimizacoes", corpoDo(valores));
      setAcompanhando(execucao);
      setRecarga((r) => r + 1);
    } catch (e) {
      setErro(e);
      /* A recusa mais comum é "já há uma otimização em andamento": reler o
         estado faz a tela encontrá-la e acompanhá-la (como no modelo, #108). */
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
      <section className="painel" aria-busy="true" aria-label="Carregando a campanha">
        <div className="campanha__corpo">
          <Esqueleto altura={260} />
        </div>
      </section>
    );
  }

  const plano = resultado ?? estado.ultima;
  const erroDoCampo = Object.fromEntries((erro?.campos ?? []).map((c) => [c.campo, c]));

  return (
    <>
      <p className="so-leitor" role="status">
        {anuncio(acompanhando, resultado)}
      </p>

      {erro && (
        <div className="aviso" role="alert">
          <p className="aviso__titulo">{erro.message}</p>
          {erro.ajuda && <p className="aviso__ajuda">{erro.ajuda}</p>}
        </div>
      )}

      <section className="painel" aria-labelledby="titulo-restricoes">
        <div className="painel__cabecalho">
          <h2 className="painel__titulo" id="titulo-restricoes">
            Restrições
          </h2>
          <span className="painel__nota">
            {estado.modelo_versao
              ? `Previsões da ${estado.modelo_versao}, com dados até ${comoPeriodo(estado.periodo_base)}`
              : "Sem modelo treinado"}
          </span>
        </div>

        {!estado.modelo_versao ? (
          <EstadoVazio titulo={estado.motivo_bloqueio} texto="O plano parte da previsão de cada parceiro." />
        ) : (
          <Restricoes
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
            aoConfirmar={calcular}
            aoCancelar={() => setConfirmando(false)}
          />
        )}
      </section>

      {acompanhando && <Andamento execucao={acompanhando} />}
      {!acompanhando && plano && <Plano execucao={plano} />}

      <Catalogo estado={estado} aoMudar={() => setRecarga((r) => r + 1)} />
    </>
  );
}

function Restricoes({
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
  const mudar = (nome, valor) => aoMudar({ ...valores, [nome]: valor });
  const fora = MOTIVOS_FORA.filter(([chave]) => estado.excluidos?.[chave]);
  const erroNasCotas = Object.keys(erroDoCampo).some((c) => c.startsWith("cotas_categoria"));

  return (
    <form
      className="campanha__corpo campanha__restricoes"
      noValidate
      onSubmit={(e) => {
        e.preventDefault();
        aoPedir();
      }}
    >
      <p className="campanha__nota">
        <strong className="num">{comoInteiro(estado.elegiveis)}</strong> parceiros podem receber ação:
        ativos e com previsão (RN11).
        {fora.length > 0 &&
          ` Ficam fora ${fora.map(([c, r]) => `${comoInteiro(estado.excluidos[c])} ${r}`).join(", ")}.`}
      </p>

      <div className="campanha__campos">
        <Campo
          id="orcamento"
          rotulo="Orçamento"
          obrigatorio
          erro={erroDoCampo.orcamento}
          ajuda="Em reais, com vírgula nos centavos."
        >
          <input
            id="campo-orcamento"
            inputMode="decimal"
            placeholder="ex.: 12.000,00"
            value={valores.orcamento}
            onChange={(e) => mudar("orcamento", e.target.value)}
          />
        </Campo>
        <Campo
          id="maximo_acoes"
          rotulo="Máximo de ações"
          obrigatorio
          erro={erroDoCampo.maximo_acoes}
          ajuda="Quantas a equipe consegue executar no período."
        >
          <input
            id="campo-maximo_acoes"
            type="number"
            inputMode="numeric"
            min={1}
            value={valores.maximo_acoes}
            onChange={(e) => mudar("maximo_acoes", e.target.value)}
          />
        </Campo>
        <Campo
          id="cota_cauda_longa"
          rotulo="Cota mínima da cauda longa (%)"
          erro={erroDoCampo.cota_cauda_longa}
          ajuda={`Das ações, quantas vão para quem está fora do Top ${estado.top_n}.`}
        >
          <input
            id="campo-cota_cauda_longa"
            inputMode="decimal"
            placeholder="ex.: 30"
            value={valores.cauda}
            onChange={(e) => mudar("cauda", e.target.value)}
          />
        </Campo>
        <Campo id="aplicacao_inicio" rotulo="Início da aplicação" obrigatorio erro={erroDoCampo.aplicacao_inicio}>
          <input
            id="campo-aplicacao_inicio"
            type="date"
            value={valores.inicio}
            onChange={(e) => mudar("inicio", e.target.value)}
          />
        </Campo>
        <Campo
          id="aplicacao_fim"
          rotulo="Fim da aplicação"
          obrigatorio
          erro={erroDoCampo.aplicacao_fim ?? erroDoCampo["requisição"]}
        >
          <input
            id="campo-aplicacao_fim"
            type="date"
            value={valores.fim}
            onChange={(e) => mudar("fim", e.target.value)}
          />
        </Campo>
      </div>

      <CotasPorCategoria
        categorias={estado.categorias}
        semCategoria={estado.sem_categoria}
        cotas={valores.cotas}
        comErro={erroNasCotas}
        aoMudar={(cotas) => mudar("cotas", cotas)}
      />

      <ModoDeExecucao estado={estado} valor={valores.modo} aoMudar={(modo) => mudar("modo", modo)} />

      {!estado.pode_executar && !acompanhando && (
        <p className="campanha__bloqueio">{estado.motivo_bloqueio}</p>
      )}

      {confirmando ? (
        <Confirmacao
          texto={
            `Calcular o plano com orçamento de ${comoDinheiro(lerReais(valores.orcamento))} e até ` +
            `${valores.maximo_acoes || TRACO} ações, ` +
            (valores.modo
              ? `no modo ${NOME_DO_MODO[valores.modo]}`
              : `no modo mais rápido disponível (${NOME_DO_MODO[estado.modo_automatico]})`) +
            "? O cálculo roda em segundo plano; o plano nunca passa de nenhuma restrição."
          }
          acao="Calcular"
          ocupado={enviando}
          aoConfirmar={aoConfirmar}
          aoCancelar={aoCancelar}
        />
      ) : (
        estado.pode_executar && (
          <div className="campanha__acoes">
            <button className="botao" type="submit" disabled={Boolean(acompanhando)}>
              {acompanhando ? "Calculando…" : "Calcular plano"}
            </button>
          </div>
        )
      )}
    </form>
  );
}

/**
 * O modo de execução (RF32, UC08 passo 4). Um `select`, como no protótipo; o
 * modo que esta instalação não tem fica desabilitado, e o porquê vai na ajuda
 * embaixo do campo — uma opção desabilitada não tem como se explicar sozinha.
 */
function ModoDeExecucao({ estado, valor, aoMudar }) {
  const daApi = Object.fromEntries((estado.modos ?? []).map((m) => [m.modo, m]));
  const escolhido = MODOS.find(([modo]) => modo === valor);
  const ajuda = [
    escolhido
      ? escolhido[3]
      : `Sem escolha, roda o mais rápido disponível nesta instalação: ${NOME_DO_MODO[estado.modo_automatico]}.`,
    ...MODOS.filter(([modo]) => daApi[modo] && !daApi[modo].disponivel).map(
      ([modo, rotulo]) => `${rotulo}: ${daApi[modo].motivo}`,
    ),
  ].join(" ");

  return (
    <div className="campanha__modo">
      <Campo id="modo" rotulo="Modo de execução" ajuda={ajuda}>
        <select id="campo-modo" value={valor} onChange={(e) => aoMudar(e.target.value)}>
          <option value="">Automático ({NOME_DO_MODO[estado.modo_automatico]})</option>
          {MODOS.map(([modo, rotulo]) => {
            const disponivel = Boolean(daApi[modo]?.disponivel);
            return (
              <option key={modo} value={modo} disabled={!disponivel}>
                {disponivel ? rotulo : `${rotulo} — indisponível`}
              </option>
            );
          })}
        </select>
      </Campo>
    </div>
  );
}

function CotasPorCategoria({ categorias, semCategoria, cotas, comErro, aoMudar }) {
  const idTitulo = useId();
  const usadas = new Set(cotas.map((c) => c.categoria_id));
  const mudar = (i, campo, valor) =>
    aoMudar(cotas.map((c, j) => (j === i ? { ...c, [campo]: valor } : c)));

  return (
    <fieldset className="campanha__cotas" aria-describedby={`${idTitulo}-ajuda`}>
      <legend id={idTitulo}>Cotas por categoria</legend>
      <p id={`${idTitulo}-ajuda`} className={comErro ? "campo__erro" : "campo__ajuda"}>
        {comErro
          ? "Confira as cotas: o mínimo não pode passar do máximo, e cada categoria entra uma vez."
          : `Em % do máximo de ações. Só conta a categoria confirmada: ${comoInteiro(semCategoria)} ` +
            "elegíveis sem categoria confirmada recebem ação, mas não entram em cota (RN11)."}
      </p>
      {cotas.map((cota, i) => (
        <div className="campanha__cota" key={cota.chave}>
          <label>
            <span className="so-leitor">Categoria da cota {i + 1}</span>
            <select value={cota.categoria_id} onChange={(e) => mudar(i, "categoria_id", e.target.value)}>
              <option value="">Escolha a categoria</option>
              {categorias.map((c) => (
                <option
                  key={c.id}
                  value={String(c.id)}
                  disabled={usadas.has(String(c.id)) && cota.categoria_id !== String(c.id)}
                >
                  {c.nome} · {comoInteiro(c.elegiveis)} elegíveis
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>mín. %</span>
            <input
              inputMode="decimal"
              value={cota.minimo}
              onChange={(e) => mudar(i, "minimo", e.target.value)}
            />
          </label>
          <label>
            <span>máx. %</span>
            <input
              inputMode="decimal"
              value={cota.maximo}
              onChange={(e) => mudar(i, "maximo", e.target.value)}
            />
          </label>
          <button
            type="button"
            className="botao botao--secundario"
            onClick={() => aoMudar(cotas.filter((_, j) => j !== i))}
          >
            Remover
          </button>
        </div>
      ))}
      <button
        type="button"
        className="botao botao--secundario"
        onClick={() => aoMudar([...cotas, novaCota()])}
      >
        Adicionar cota de categoria
      </button>
    </fieldset>
  );
}

function Andamento({ execucao }) {
  return (
    <div className="aviso aviso--informativo campanha__andamento">
      <p className="aviso__titulo">Calculando o plano…</p>
      <p className="aviso__ajuda">
        Iniciado {comoDataHora(execucao.iniciada_em)}
        {execucao.autor ? ` por ${execucao.autor}` : " pelo terminal"}, no modo {NOME_DO_MODO[execucao.modo]}.
        A tela se atualiza sozinha quando o cálculo terminar; você pode sair e voltar.
      </p>
      {execucao.substituicao && <p className="aviso__ajuda">{execucao.substituicao}</p>}
      <div className="campanha__barra-andamento" aria-hidden="true" />
    </div>
  );
}

function Plano({ execucao }) {
  if (execucao.situacao === "FALHOU") {
    return (
      <div className="aviso" role="alert">
        <p className="aviso__titulo">O cálculo falhou.</p>
        <p className="aviso__ajuda">{execucao.motivo}</p>
      </div>
    );
  }
  if (execucao.viavel === false) {
    return (
      <section className="painel" aria-labelledby="titulo-plano">
        <div className="painel__cabecalho">
          <h2 className="painel__titulo" id="titulo-plano">
            Plano recomendado
          </h2>
          <span className="painel__nota">{comoDataHora(execucao.concluida_em)}</span>
        </div>
        <div className="campanha__corpo">
          <div className="aviso campanha__inviavel">
            <p className="aviso__titulo">Sem solução viável. {execucao.motivo}</p>
            {execucao.ajuda && <p className="aviso__ajuda">{execucao.ajuda}</p>}
            <p className="aviso__ajuda">O sistema não entrega plano que viole restrição (RN07).</p>
          </div>
          <Cotas cotas={execucao.cotas} />
        </div>
      </section>
    );
  }

  const p = execucao.parametros;
  const melhora =
    execucao.ganho_guloso && Number(execucao.ganho_guloso) > 0
      ? Number(execucao.uplift_total) / Number(execucao.ganho_guloso) - 1
      : null;

  return (
    <section className="painel" aria-labelledby="titulo-plano">
      <div className="painel__cabecalho">
        <h2 className="painel__titulo" id="titulo-plano">
          Plano recomendado
        </h2>
        <span className="etiqueta-estimativa">Estimativa</span>
        <span className="painel__nota num">
          {comoInteiro(execucao.acoes)} ações · {comoDinheiro(execucao.custo_total)} de{" "}
          {comoDinheiro(p.orcamento)} · ganho esperado {comoDinheiro(execucao.uplift_total)}
        </span>
      </div>

      <div className="campanha__corpo campanha__resumo">
        {execucao.parcial && (
          <p className="campanha__parcial">
            O cálculo atingiu o limite de tempo: este é o melhor plano viável encontrado até ali.
          </p>
        )}
        {execucao.substituicao && <p className="campanha__parcial">{execucao.substituicao}</p>}
        <dl className="campanha__fatos">
          <dt>Previsões</dt>
          <dd>
            {execucao.modelo_versao}, com dados até {comoPeriodo(execucao.periodo_base)}
          </dd>
          <dt>Aplicação</dt>
          <dd>{comoPeriodo({ data_inicio: p.aplicacao_inicio, data_fim: p.aplicacao_fim })}</dd>
          <dt>Folga</dt>
          <dd className="num">
            {comoDinheiro(execucao.folga_orcamento)} do orçamento · {comoInteiro(execucao.folga_acoes)}{" "}
            {execucao.folga_acoes === 1 ? "ação" : "ações"}
          </dd>
          <dt>Contra o guloso</dt>
          <dd className="num">
            {melhora === null
              ? TRACO
              : melhora > 0.00005
                ? `${comoFracao(melhora)} acima do plano guloso (${comoDinheiro(execucao.ganho_guloso)})`
                : `igual ao plano guloso (${comoDinheiro(execucao.ganho_guloso)})`}
          </dd>
          <dt>Cálculo</dt>
          <dd className="num">
            {ROTULO_DO_MODO[execucao.modo]}
            {execucao.threads ? `, ${comoInteiro(execucao.threads)} threads` : ""} ·{" "}
            {comoDuracao(execucao.tempo_ms)} · {comoDataHora(execucao.concluida_em)}
            {execucao.autor ? ` · ${execucao.autor}` : ""}
          </dd>
        </dl>
        <Cotas cotas={execucao.cotas} />
      </div>

      {execucao.itens?.length ? (
        <div className="tabela-rolagem">
          <table className="tabela campanha__itens">
            <caption className="so-leitor">Ações do plano, do maior ganho esperado para o menor</caption>
            <thead>
              <tr>
                <th scope="col">Parceiro</th>
                <th scope="col">Segmento</th>
                <th scope="col">Categoria</th>
                <th scope="col">Cauda longa</th>
                <th scope="col">Ação</th>
                <th scope="col" className="numerica">
                  Custo
                </th>
                <th scope="col" className="numerica">
                  Ganho esperado
                </th>
              </tr>
            </thead>
            <tbody>
              {execucao.itens.map((item) => (
                <tr key={item.parceiro_id}>
                  <td className="nome">
                    <Link className="nome__link" to={`/parceiros/${item.parceiro_id}`}>
                      {item.parceiro}
                    </Link>
                  </td>
                  <td>
                    <Segmento valor={item.segmento} />
                  </td>
                  <td>{item.categoria ?? "Pendente"}</td>
                  <td>{item.cauda_longa ? "Sim" : "Não"}</td>
                  <td>{item.acao}</td>
                  <td className="numerica">{comoDinheiro(item.custo)}</td>
                  <td className="numerica">{comoDinheiro(item.ganho)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EstadoVazio
          titulo="O plano não tem ações"
          texto="Nenhuma ação do catálogo cabe no orçamento com ganho esperado."
        />
      )}
    </section>
  );
}

/** As cotas em contagem (RN11), com quanto o plano deu a cada uma. */
function Cotas({ cotas }) {
  if (!cotas?.length) return null;
  return (
    <table className="tabela campanha__cotas-tabela">
      <caption className="campanha__legenda">Cotas, em número de ações</caption>
      <thead>
        <tr>
          <th scope="col">Cota</th>
          <th scope="col" className="numerica">
            Mínimo
          </th>
          <th scope="col" className="numerica">
            Máximo
          </th>
          <th scope="col" className="numerica">
            No plano
          </th>
        </tr>
      </thead>
      <tbody>
        {cotas.map((c) => (
          <tr key={c.categoria_id ?? "cauda"}>
            <td>{c.nome}</td>
            <td className="numerica">{comoInteiro(c.minimo)}</td>
            <td className="numerica">{comoInteiro(c.maximo)}</td>
            <td className="numerica">{c.acoes === null ? TRACO : comoInteiro(c.acoes)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

const ACAO_VAZIA = { nome: "", custo_unitario: "", efeito_crescimento: "", efeito_retencao: "", ativa: true };

function Catalogo({ estado, aoMudar }) {
  const [editando, setEditando] = useState(null); // id da ação, ou "nova"
  const [valores, setValores] = useState(ACAO_VAZIA);
  const [erro, setErro] = useState(null);
  const [salvando, setSalvando] = useState(false);
  const editavel = estado.pode_editar_catalogo;

  function editar(acao) {
    setErro(null);
    setEditando(acao?.id ?? "nova");
    setValores(
      acao
        ? {
            nome: acao.nome,
            custo_unitario: String(acao.custo_unitario).replace(".", ","),
            efeito_crescimento: paraPercentual(acao.efeito_crescimento),
            efeito_retencao: paraPercentual(acao.efeito_retencao),
            ativa: acao.ativa,
          }
        : ACAO_VAZIA,
    );
  }

  async function salvar() {
    setSalvando(true);
    const corpo = {
      nome: valores.nome,
      custo_unitario: lerReais(valores.custo_unitario),
      efeito_crescimento: paraFracao(valores.efeito_crescimento),
      efeito_retencao: paraFracao(valores.efeito_retencao),
      ativa: valores.ativa,
    };
    try {
      if (editando === "nova") await api.post("/api/acoes-comerciais", corpo);
      else await api.patch(`/api/acoes-comerciais/${editando}`, corpo);
      setEditando(null);
      aoMudar();
    } catch (e) {
      setErro(e);
    } finally {
      setSalvando(false);
    }
  }

  const edicao = (
    <LinhaDeEdicao
      valores={valores}
      erro={erro}
      salvando={salvando}
      aoMudar={setValores}
      aoSalvar={salvar}
      aoCancelar={() => setEditando(null)}
    />
  );

  return (
    <section className="painel" aria-labelledby="titulo-catalogo">
      <div className="painel__cabecalho">
        <h2 className="painel__titulo" id="titulo-catalogo">
          Catálogo de ações
        </h2>
        <span className="painel__nota">Ganho = previsto × crescimento + previsto × risco × retenção (RN10)</span>
        {editavel && editando === null && (
          <div className="painel__acoes">
            <button type="button" className="botao botao--secundario" onClick={() => editar(null)}>
              Nova ação
            </button>
          </div>
        )}
      </div>

      {erro && (
        <div className="campanha__corpo">
          <div className="aviso" role="alert">
            <p className="aviso__titulo">{erro.message}</p>
            {erro.ajuda && <p className="aviso__ajuda">{erro.ajuda}</p>}
            {erro.campos?.map((c) => (
              <p key={c.campo} className="aviso__ajuda">
                {c.mensagem}
              </p>
            ))}
          </div>
        </div>
      )}

      <div className="tabela-rolagem">
        <table className="tabela campanha__catalogo">
          <caption className="so-leitor">Ações que o otimizador pode distribuir</caption>
          <thead>
            <tr>
              <th scope="col">Ação</th>
              <th scope="col" className="numerica">
                Custo
              </th>
              <th scope="col" className="numerica">
                Crescimento
              </th>
              <th scope="col" className="numerica">
                Retenção
              </th>
              <th scope="col">Situação</th>
              {editavel && <th scope="col"><span className="so-leitor">Editar</span></th>}
            </tr>
          </thead>
          <tbody>
            {estado.acoes.map((acao) =>
              editando === acao.id ? (
                <LinhaDeEdicao
                  key={acao.id}
                  valores={valores}
                  erro={erro}
                  salvando={salvando}
                  aoMudar={setValores}
                  aoSalvar={salvar}
                  aoCancelar={() => setEditando(null)}
                />
              ) : (
                <tr key={acao.id}>
                  <td className="nome">{acao.nome}</td>
                  <td className="numerica">{comoDinheiro(acao.custo_unitario)}</td>
                  <td className="numerica">{comoFracao(acao.efeito_crescimento)}</td>
                  <td className="numerica">{comoFracao(acao.efeito_retencao)}</td>
                  <td>{acao.ativa ? "Ativa" : "Inativa"}</td>
                  {editavel && (
                    <td className="campanha__botoes">
                      <button
                        type="button"
                        className="botao botao--secundario"
                        disabled={editando !== null}
                        onClick={() => editar(acao)}
                        aria-label={`Editar ${acao.nome}`}
                      >
                        Editar
                      </button>
                    </td>
                  )}
                </tr>
              ),
            )}
            {editando === "nova" && edicao}
          </tbody>
        </table>
      </div>
    </section>
  );
}

/** Uma ação do catálogo em edição, na própria linha da tabela. */
function LinhaDeEdicao({ valores, erro, salvando, aoMudar, aoSalvar, aoCancelar }) {
  const erroDoCampo = Object.fromEntries((erro?.campos ?? []).map((c) => [c.campo, c]));
  const campo = (nome, rotulo, extra = {}) => (
    <input
      aria-label={rotulo}
      aria-invalid={erroDoCampo[nome] ? "true" : undefined}
      value={valores[nome]}
      onChange={(e) => aoMudar({ ...valores, [nome]: e.target.value })}
      {...extra}
    />
  );
  return (
    <tr className="campanha__edicao">
      <td>{campo("nome", "Nome da ação")}</td>
      <td className="numerica">{campo("custo_unitario", "Custo unitário, em reais", { inputMode: "decimal" })}</td>
      <td className="numerica">
        {campo("efeito_crescimento", "Efeito de crescimento, em %", { inputMode: "decimal" })}
      </td>
      <td className="numerica">
        {campo("efeito_retencao", "Efeito de retenção, em %", { inputMode: "decimal" })}
      </td>
      <td>
        <label className="campanha__ativa">
          <input
            type="checkbox"
            checked={valores.ativa}
            onChange={(e) => aoMudar({ ...valores, ativa: e.target.checked })}
          />
          Ativa
        </label>
      </td>
      <td className="campanha__botoes">
        <button type="button" className="botao" disabled={salvando} onClick={aoSalvar}>
          Salvar
        </button>
        <button type="button" className="botao botao--secundario" onClick={aoCancelar}>
          Cancelar
        </button>
      </td>
    </tr>
  );
}

function anuncio(acompanhando, resultado) {
  if (acompanhando) return "Calculando o plano.";
  if (!resultado) return "";
  if (resultado.situacao === "FALHOU") return `O cálculo falhou. ${resultado.motivo}`;
  if (resultado.viavel === false) return `Sem solução viável. ${resultado.motivo}`;
  return `Plano calculado: ${resultado.acoes} ações, ganho esperado de ${comoDinheiro(resultado.uplift_total)}.`;
}
