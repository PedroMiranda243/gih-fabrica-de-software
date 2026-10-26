/**
 * Assistente — perguntar sobre os dados com as próprias palavras. A resposta vem
 * inteira da API; a tela não interpreta a pergunta nem confere número. A chamada
 * fica aberta de 5 a 45 s: a espera é dita, com os segundos contando.
 */
import { useEffect, useRef, useState } from "react";

import { api } from "../api/cliente";
import { useCarregar, useSegundos } from "../api/ganchos";
import { Carregando, ErroDaTela, Nota } from "../componentes/Estados";
import Icone from "../componentes/Icone";
import { useTitulo } from "../componentes/Titulo";
import { comoDataHora, comoInteiro } from "../formato";

const NORMAL = 15;

export default function Assistente() {
  useTitulo("Assistente");
  const estado = useCarregar(() => api.get("/api/assistente"), "a");
  const [texto, setTexto] = useState("");
  const [esperando, setEsperando] = useState(null);
  const [erroCampo, setErroCampo] = useState(null);
  const [respostas, setRespostas] = useState([]);
  const [anuncio, setAnuncio] = useState("");
  const segundos = useSegundos(Boolean(esperando));
  const refCampo = useRef(null);
  const refNova = useRef(null);
  const contador = useRef(0);

  useEffect(() => {
    refNova.current?.focus();
  }, [respostas.length]);

  if (estado.carregando) return <Carregando rotulo="Carregando o assistente" linhas={5} />;
  if (estado.erro) return <ErroDaTela erro={estado.erro} />;
  const { assistente, exemplos, tamanho_maximo: maximo } = estado.dados;

  async function perguntar(pergunta) {
    const t = pergunta.trim();
    if (!t || esperando) return;
    setErroCampo(null);
    setEsperando(t);
    setAnuncio("Lendo a pergunta e buscando os números no sistema.");
    try {
      const r = await api.post("/api/assistente/perguntas", { texto: t });
      contador.current += 1;
      setRespostas((lista) => [{ id: contador.current, pergunta: t, resposta: r, em: new Date().toISOString() }, ...lista]);
      setTexto("");
      setAnuncio(r.situacao === "PRECISAO" ? "O assistente pediu uma precisão." : r.situacao === "ABSTENCAO" ? "O assistente respondeu que não tem base para responder." : r.situacao === "INDISPONIVEL" ? "O assistente está indisponível." : "Resposta pronta.");
    } catch (e) {
      setErroCampo(e);
      setAnuncio("");
      refCampo.current?.focus();
    } finally {
      setEsperando(null);
    }
  }

  function teclas(evento) {
    if (evento.key === "Enter" && !evento.shiftKey && !evento.nativeEvent.isComposing) {
      evento.preventDefault();
      perguntar(texto);
    }
  }

  const erroDoTexto = erroCampo?.campos?.find((c) => c.campo === "texto");

  return (
    <div className="pagina pagina--assistente">
      <p className="sr-only" role="status" aria-live="polite">
        {anuncio}
      </p>
      <div className="assistente-grade">
        <section className="bloco bloco--pergunta" aria-labelledby="titulo-pergunte">
          <div className="bloco__cabeca">
            <h2 id="titulo-pergunte" className="bloco__titulo">
              Pergunte sobre os dados
            </h2>
            <p className="bloco__sub">Os números vêm do sistema; o {assistente.modelo} lê a pergunta e redige.</p>
          </div>
          {!assistente.disponivel && (
            <Nota titulo="O assistente está indisponível agora." papel="status">
              {assistente.motivo && <p>{assistente.motivo}</p>}
              <p>As outras telas seguem funcionando, e a pergunta ainda pode ser feita: o sistema monta a resposta com os números dele.</p>
            </Nota>
          )}
          <form
            className="formulario"
            noValidate
            onSubmit={(e) => {
              e.preventDefault();
              perguntar(texto);
            }}
          >
            <div className={`campo${erroCampo ? " campo--erro" : ""}`}>
              <label className="campo__rotulo" htmlFor="campo-pergunta">
                Sua pergunta
              </label>
              <textarea
                id="campo-pergunta"
                ref={refCampo}
                className="entrada entrada--pergunta"
                rows={3}
                value={texto}
                onChange={(e) => setTexto(e.target.value)}
                onKeyDown={teclas}
                aria-describedby={`pergunta-ajuda${erroCampo ? " pergunta-erro" : ""}`}
                aria-invalid={erroCampo ? true : undefined}
                placeholder={exemplos[0]?.exemplo}
              />
              {erroCampo && (
                <p className="campo__erro" id="pergunta-erro">
                  <Icone nome="erro" />
                  <span>
                    {erroDoTexto?.mensagem ?? erroCampo.message}
                    {erroCampo.ajuda && <span className="campo__erro-ajuda"> {erroCampo.ajuda}</span>}
                  </span>
                </p>
              )}
              <p className="campo__ajuda" id="pergunta-ajuda">
                <span className={`contador${texto.length > maximo ? " contador--passou" : ""}`}>
                  {comoInteiro(texto.length)} de {comoInteiro(maximo)} caracteres.
                </span>{" "}
                Enter pergunta; Shift+Enter quebra a linha.
              </p>
            </div>
            <div className="formulario__acoes">
              <button type="submit" className="botao botao--primario" disabled={!texto.trim() || Boolean(esperando)}>
                <Icone nome="enviar" /> {esperando ? "Perguntando…" : "Perguntar"}
              </button>
            </div>
          </form>

          {esperando && (
            <div className="espera" role="status" aria-live="polite">
              <span className="espera__relogio" aria-hidden="true">
                {segundos}s
              </span>
              <div>
                <p className="espera__pergunta">“{esperando}”</p>
                <p>Lendo a pergunta e buscando os números no sistema… {segundos} s.</p>
                {segundos >= NORMAL && <p className="espera__demora">Está demorando mais que o normal: o modelo de linguagem deve estar sendo carregado. A primeira pergunta depois de uma pausa leva perto de 45 s.</p>}
              </div>
            </div>
          )}
        </section>

        <aside className="bloco bloco--exemplos" aria-labelledby="titulo-exemplos">
          <div className="bloco__cabeca">
            <h2 id="titulo-exemplos" className="bloco__titulo">
              O que o assistente responde
            </h2>
            <p className="bloco__sub">Clique num exemplo para perguntar.</p>
          </div>
          <ul className="exemplos">
            {exemplos.map((e) => (
              <li key={e.tipo}>
                <button
                  type="button"
                  className="exemplo"
                  onClick={() => {
                    setTexto(e.exemplo);
                    refCampo.current?.focus();
                  }}
                >
                  <span className="exemplo__pergunta">{e.exemplo}</span>
                  <span className="exemplo__descricao">{e.descricao}</span>
                </button>
              </li>
            ))}
          </ul>
        </aside>
      </div>

      {respostas.length > 0 && (
        <section aria-labelledby="titulo-respostas" className="respostas">
          <h2 id="titulo-respostas" className="secao-titulo">
            Respostas desta conversa
          </h2>
          <p className="bloco__sub respostas__nota">A mais recente em cima. As respostas não são gravadas: saem ao recarregar a tela.</p>
          <ol className="respostas__lista">
            {respostas.map((r, i) => (
              <li key={r.id}>
                <Resposta item={r} modelo={assistente.modelo} refTitulo={i === 0 ? refNova : undefined} aoEscolher={(opcao) => perguntar(`${r.pergunta} (${opcao})`)} ocupado={Boolean(esperando)} />
              </li>
            ))}
          </ol>
        </section>
      )}
    </div>
  );
}

/** O texto em parágrafos, e as linhas que começam com marcador como lista. */
function Texto({ texto }) {
  const blocos = [];
  let lista = null;
  for (const linha of texto.split(/\n/)) {
    const item = /^\s*(?:[-•*]|\d+[.)])\s+(.*)$/.exec(linha);
    if (item) {
      if (!lista) {
        lista = [];
        blocos.push({ lista });
      }
      lista.push(item[1]);
    } else if (linha.trim()) {
      lista = null;
      blocos.push({ paragrafo: linha.trim() });
    } else {
      lista = null;
    }
  }
  return (
    <div className="resposta__texto">
      {blocos.map((b, i) =>
        b.lista ? (
          <ul key={i}>
            {b.lista.map((t, j) => (
              <li key={j}>{t}</li>
            ))}
          </ul>
        ) : (
          <p key={i}>{b.paragrafo}</p>
        ),
      )}
    </div>
  );
}

function Resposta({ item, modelo, refTitulo, aoEscolher, ocupado }) {
  const r = item.resposta;
  const rotulo = { RESPONDIDA: null, ABSTENCAO: "Sem base para responder", PRECISAO: "Falta uma precisão", INDISPONIVEL: "Assistente indisponível" }[r.situacao];
  return (
    <article className={`resposta resposta--${r.situacao.toLowerCase()}`} aria-labelledby={`resposta-${item.id}`}>
      <header className="resposta__cabeca">
        <h3 id={`resposta-${item.id}`} className="resposta__pergunta" tabIndex={-1} ref={refTitulo}>
          {item.pergunta}
        </h3>
        <p className="resposta__quando">{comoDataHora(item.em)}</p>
      </header>
      {rotulo && <p className="resposta__situacao">{rotulo}</p>}
      <Texto texto={r.texto} />
      {r.situacao === "PRECISAO" && r.candidatos.length > 0 && (
        <div className="candidatos" role="group" aria-label="Escolha uma das opções">
          {r.candidatos.map((c) => (
            <button key={c} type="button" className="botao botao--secundario botao--pequeno" onClick={() => aoEscolher(c)} disabled={ocupado}>
              {c}
            </button>
          ))}
        </div>
      )}
      {(r.fonte || r.situacao === "RESPONDIDA") && (
        <footer className="resposta__rodape">
          {r.fonte && (
            <div className="resposta__fonte">
              <p>
                <strong>Fonte:</strong> {r.fonte.texto}
              </p>
              {r.fonte.relatorios?.length > 0 && (
                <p className="discreto">
                  O mais recente foi importado em {comoDataHora(r.fonte.relatorios[r.fonte.relatorios.length - 1].importado_em)}
                  {r.fonte.relatorios[r.fonte.relatorios.length - 1].importado_por ? ` por ${r.fonte.relatorios[r.fonte.relatorios.length - 1].importado_por}` : ""}.
                </p>
              )}
            </div>
          )}
          <p className="resposta__redator">
            {r.redator === "MODELO" ? `Redigida pelo ${modelo}, com os números do sistema conferidos.` : "Montada pelo sistema, com os números dele."}
            {r.motivo && <span className="discreto"> {r.motivo}</span>}
          </p>
          {r.fatos?.length > 0 && (
            <details className="detalhes">
              <summary>
                <Icone nome="seta-direita" className="resumo__icone" />
                Os números da resposta
              </summary>
              <dl className="fatos">
                {r.fatos.map((f, i) => (
                  <div key={i}>
                    <dt>{f.fato}</dt>
                    <dd>{f.valor}</dd>
                  </div>
                ))}
              </dl>
            </details>
          )}
        </footer>
      )}
    </article>
  );
}
