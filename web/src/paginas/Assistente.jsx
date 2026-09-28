/**
 * O assistente analítico — UC12, RF41 a RF43, histórias H65 a H68 — para o Gestor e o Analista.
 *
 * **A resposta é da API, inteira** (regra 2.4): o texto, a situação, a fonte, os
 * números e as opções de precisão. A tela não interpreta a pergunta nem confere
 * número nenhum; ela mostra o que veio, e mostra de onde veio.
 *
 * **A fonte fica sempre à vista**, embaixo da resposta, e não num clique (H66,
 * RF42): quem lê um número precisa ver de que relatório ele saiu sem ter de
 * pedir.
 *
 * **Abstenção não é erro** (H68, UC12-A1). "Não há base para responder" é a
 * resposta certa, e sai no mesmo cartão das outras, com uma barra neutra — o
 * vermelho do erro diria que algo quebrou, e nada quebrou. O mesmo vale para o
 * pedido de precisão (A2), com as opções clicáveis, e para o assistente
 * indisponível (E1).
 *
 * **A espera pode ser longa.** Com o modelo carregado, uma pergunta leva de 5 a
 * 10 s; a primeira depois de ele ficar parado, perto de 45 s (ADR-013). A tela
 * conta o tempo e, passado o normal, diz por quê — espera sem explicação parece
 * travamento.
 *
 * As respostas desta visita ficam na tela, a mais recente em cima. Não são
 * gravadas: o assistente é consulta (UC12, pós-condições).
 */
import { useEffect, useRef, useState } from "react";

import { api } from "../api/cliente";
import { Esqueleto } from "../componentes/Carregando";
import Campo from "../componentes/Campo";
import { comoDataHora, comoInteiro } from "../formato";
import "../estilos/assistente.css";

/* Passado isto, a espera deixa de ser a de uma pergunta com o modelo carregado. */
export const ESPERA_LONGA_MS = 12000;
/* A conversa guarda as últimas respostas; mais que isso é rolagem sem uso. */
const MAXIMO_NA_CONVERSA = 10;

const SITUACAO = {
  ABSTENCAO: "Sem base para responder",
  PRECISAO: "Falta uma precisão",
  INDISPONIVEL: "Assistente indisponível",
};

const ANUNCIO = {
  RESPONDIDA: "Resposta pronta.",
  ABSTENCAO: "O assistente não tem base para responder.",
  PRECISAO: "O assistente pediu uma precisão.",
  INDISPONIVEL: "O assistente está indisponível.",
};

export default function Assistente() {
  const [estado, setEstado] = useState(null);
  const [erroCarga, setErroCarga] = useState(null);
  const [texto, setTexto] = useState("");
  const [erroCampo, setErroCampo] = useState(null);
  const [erro, setErro] = useState(null);
  const [aguardando, setAguardando] = useState(null);
  const [conversa, setConversa] = useState([]);
  const [anuncio, setAnuncio] = useState("");
  const proximoId = useRef(1);
  const focoPendente = useRef(null);

  useEffect(() => {
    let vivo = true;
    api
      .get("/api/assistente")
      .then((corpo) => vivo && setEstado(corpo))
      .catch((e) => vivo && setErroCarga(e));
    return () => {
      vivo = false;
    };
  }, []);

  /* A resposta nova recebe o foco: quem usa teclado ou leitor de tela continua
     dela, e não do botão que já apertou. */
  useEffect(() => {
    if (focoPendente.current === null) return;
    document.getElementById(`pergunta-${focoPendente.current}`)?.focus();
    focoPendente.current = null;
  }, [conversa]);

  async function perguntar(pergunta) {
    const limpa = pergunta.trim();
    if (!limpa || aguardando) return;
    setTexto(limpa);
    setErroCampo(null);
    setErro(null);
    setAguardando({ pergunta: limpa, desde: Date.now() });
    setAnuncio("Perguntando ao assistente.");
    try {
      const resposta = await api.post("/api/assistente/perguntas", { texto: limpa });
      const id = proximoId.current++;
      focoPendente.current = id;
      setConversa((antes) => [{ id, pergunta: limpa, resposta }, ...antes].slice(0, MAXIMO_NA_CONVERSA));
      setTexto("");
      setAnuncio(ANUNCIO[resposta.situacao] ?? "");
    } catch (e) {
      const doCampo = e.campos?.find((c) => c.campo === "texto");
      if (doCampo) setErroCampo(doCampo);
      else setErro(e);
      setAnuncio("");
    } finally {
      setAguardando(null);
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

  if (!estado) {
    return (
      <section className="painel" aria-busy="true" aria-label="Carregando o assistente">
        <div className="assistente__formulario">
          <Esqueleto altura={120} />
        </div>
      </section>
    );
  }

  const { assistente } = estado;

  return (
    <div className="assistente">
      <p className="so-leitor" role="status">
        {anuncio}
      </p>

      {!assistente.disponivel && (
        <div className="aviso aviso--informativo">
          <p className="aviso__titulo">O assistente está indisponível agora.</p>
          <p className="aviso__ajuda">
            {assistente.motivo} O painel e as outras telas seguem funcionando.
          </p>
        </div>
      )}

      {erro && (
        <div className="aviso" role="alert">
          <p className="aviso__titulo">{erro.message}</p>
          {erro.ajuda && <p className="aviso__ajuda">{erro.ajuda}</p>}
        </div>
      )}

      <section className="painel" aria-labelledby="titulo-pergunta">
        <div className="painel__cabecalho">
          <h2 className="painel__titulo" id="titulo-pergunta">
            Pergunte sobre os dados
          </h2>
          <span className="painel__nota">
            {assistente.disponivel
              ? `Os números vêm do sistema; o ${assistente.modelo} lê a pergunta e redige`
              : "Os números vêm do sistema"}
          </span>
        </div>
        <Pergunta
          texto={texto}
          maximo={estado.tamanho_maximo}
          erro={erroCampo}
          aguardando={Boolean(aguardando)}
          aoMudar={(valor) => {
            setTexto(valor);
            setErroCampo(null);
          }}
          aoPerguntar={() => perguntar(texto)}
        />
        <Exemplos exemplos={estado.exemplos} desativados={Boolean(aguardando)} aoEscolher={perguntar} />
      </section>

      {(aguardando || conversa.length > 0) && (
        <section aria-labelledby="titulo-respostas" aria-busy={Boolean(aguardando)}>
          <h2 className="so-leitor" id="titulo-respostas">
            Respostas
          </h2>
          <ol className="conversa">
            {aguardando && <Aguardando pergunta={aguardando.pergunta} desde={aguardando.desde} />}
            {conversa.map(({ id, pergunta, resposta }) => (
              <Resposta
                key={id}
                id={id}
                pergunta={pergunta}
                resposta={resposta}
                modelo={assistente.modelo}
                desativada={Boolean(aguardando)}
                aoEscolher={(opcao) => perguntar(`${pergunta} (${opcao})`)}
              />
            ))}
          </ol>
        </section>
      )}
    </div>
  );
}

function Pergunta({ texto, maximo, erro, aguardando, aoMudar, aoPerguntar }) {
  function enviar(evento) {
    evento.preventDefault();
    aoPerguntar();
  }

  /* Enter pergunta, e Shift+Enter quebra a linha, como em qualquer campo de
     conversa. Durante a composição de um acento, o Enter é do teclado. */
  function aoTeclar(evento) {
    if (evento.key === "Enter" && !evento.shiftKey && !evento.nativeEvent.isComposing) {
      evento.preventDefault();
      aoPerguntar();
    }
  }

  return (
    <form className="assistente__formulario" onSubmit={enviar} noValidate>
      <Campo
        id="pergunta"
        rotulo="Sua pergunta"
        erro={erro}
        ajuda={`${comoInteiro(texto.length)} de ${comoInteiro(maximo)} caracteres. Enter pergunta; Shift+Enter quebra a linha.`}
      >
        <textarea
          id="campo-pergunta"
          className="assistente__pergunta"
          rows={3}
          maxLength={maximo}
          value={texto}
          onChange={(e) => aoMudar(e.target.value)}
          onKeyDown={aoTeclar}
          placeholder="Por exemplo: como foi a rede na semana passada?"
        />
      </Campo>
      <div className="assistente__acoes">
        <button type="submit" className="botao" disabled={aguardando || !texto.trim()}>
          {aguardando ? "Perguntando…" : "Perguntar"}
        </button>
      </div>
    </form>
  );
}

function Exemplos({ exemplos, desativados, aoEscolher }) {
  return (
    <div className="assistente__exemplos">
      <h3 className="assistente__exemplos-titulo" id="titulo-exemplos">
        O que o assistente responde
      </h3>
      <ul className="sugestoes" aria-labelledby="titulo-exemplos">
        {exemplos.map((e) => (
          <li key={e.tipo}>
            <button
              type="button"
              className="sugestao"
              title={e.descricao}
              disabled={desativados}
              onClick={() => aoEscolher(e.exemplo)}
            >
              {e.exemplo}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Aguardando({ pergunta, desde }) {
  const [agora, setAgora] = useState(() => Date.now());

  useEffect(() => {
    const relogio = setInterval(() => setAgora(Date.now()), 1000);
    return () => clearInterval(relogio);
  }, []);

  const passados = agora - desde;
  const segundos = Math.floor(passados / 1000);
  return (
    <li className="painel resposta resposta--aguardando">
      <h3 className="resposta__pergunta">{pergunta}</h3>
      <p className="resposta__espera">
        {passados < ESPERA_LONGA_MS
          ? "Lendo a pergunta e buscando os números no sistema…"
          : "Está demorando mais que o normal: o modelo de linguagem deve estar sendo carregado. A primeira pergunta depois de uma pausa leva perto de 45 s."}{" "}
        <span className="num">{segundos} s</span>
      </p>
      <Esqueleto altura={14} largura="72%" />
      <Esqueleto altura={14} largura="48%" />
    </li>
  );
}

/* O texto da API, com as listas como listas: a linha que começa por "- " ou por
   um ordinal ("1º ") é item. O resto é parágrafo. */
function blocos(texto) {
  const saida = [];
  for (const linha of texto.split("\n")) {
    const item = linha.startsWith("- ") ? linha.slice(2) : /^\d+º /.test(linha) ? linha : null;
    const ultimo = saida.at(-1);
    if (item === null) saida.push({ tipo: "p", linhas: [linha] });
    else if (ultimo?.tipo === "lista") ultimo.linhas.push(item);
    else saida.push({ tipo: "lista", linhas: [item] });
  }
  return saida.map((bloco, i) =>
    bloco.tipo === "p" ? (
      <p key={i}>{bloco.linhas[0]}</p>
    ) : (
      <ul key={i} className="resposta__lista">
        {bloco.linhas.map((linha, j) => (
          <li key={j}>{linha}</li>
        ))}
      </ul>
    ),
  );
}

function Resposta({ id, pergunta, resposta, modelo, desativada, aoEscolher }) {
  const rotulo = SITUACAO[resposta.situacao];
  return (
    <li className={`painel resposta${rotulo ? " resposta--sem-base" : ""}`} aria-labelledby={`pergunta-${id}`}>
      <h3 className="resposta__pergunta" id={`pergunta-${id}`} tabIndex={-1}>
        {pergunta}
      </h3>
      {rotulo && <p className="resposta__situacao">{rotulo}</p>}
      <div className="resposta__texto">{blocos(resposta.texto)}</div>

      {resposta.candidatos.length > 0 && (
        <ul className="sugestoes" aria-label="Escolha uma opção para perguntar de novo">
          {resposta.candidatos.map((opcao) => (
            <li key={opcao}>
              <button type="button" className="sugestao" disabled={desativada} onClick={() => aoEscolher(opcao)}>
                {opcao}
              </button>
            </li>
          ))}
        </ul>
      )}

      {resposta.fonte && <Fonte fonte={resposta.fonte} />}
      <Redacao resposta={resposta} modelo={modelo} />

      {resposta.situacao === "RESPONDIDA" && resposta.fatos.length > 0 && (
        <details className="resposta__numeros">
          <summary>Os números da resposta</summary>
          <dl>
            {resposta.fatos.map((f) => (
              <div key={`${f.fato}-${f.valor}`} className="resposta__fato">
                <dt>{f.fato}</dt>
                <dd>{f.valor}</dd>
              </div>
            ))}
          </dl>
        </details>
      )}
    </li>
  );
}

function Fonte({ fonte }) {
  const recente = fonte.relatorios.at(-1);
  let importacao = null;
  if (recente?.importado_em) {
    const quem = recente.importado_por ? ` por ${recente.importado_por}` : "";
    importacao =
      fonte.relatorios.length === 1
        ? `Importado em ${comoDataHora(recente.importado_em)}${quem}.`
        : `O mais recente foi importado em ${comoDataHora(recente.importado_em)}${quem}.`;
  }
  return (
    <p className="resposta__fonte">
      <span className="resposta__fonte-rotulo">Fonte</span> {fonte.texto} {importacao}
    </p>
  );
}

/* Quem escreveu o texto, e por que não o modelo, quando ele tentou e não passou
   pela guarda (H67). Só na resposta com números: a abstenção e a precisão são
   sempre do sistema. */
function Redacao({ resposta, modelo }) {
  if (resposta.situacao !== "RESPONDIDA") return null;
  let texto;
  if (resposta.redator === "MODELO") texto = `Redigida pelo ${modelo}, com os números do sistema conferidos.`;
  else if (resposta.motivo) texto = resposta.motivo;
  else texto = "Montada pelo sistema, com os números dele.";
  return <p className="resposta__redacao">{texto}</p>;
}
