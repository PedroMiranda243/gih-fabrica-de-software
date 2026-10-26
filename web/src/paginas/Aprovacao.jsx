/**
 * Aprovação — nenhuma mensagem sai do sistema sem a decisão de um gestor. A fila
 * do que foi gerado e o histórico do que foi decidido, tudo no endereço. Quem não
 * tem `decidir_mensagens` vê a mesma fila, sem caixa de seleção e sem botão.
 */
import { useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";

import { api, comConsulta, ErroDaApi } from "../api/cliente";
import { useCarregar, useFiltros } from "../api/ganchos";
import { tem, useSessao } from "../api/contextoSessao";
import AlteracoesNaoSalvas from "../componentes/AlteracoesNaoSalvas";
import CartaoMensagem from "../componentes/CartaoMensagem";
import Confirmacao from "../componentes/Confirmacao";
import { Carregando, ErroDaAcao, ErroDaTela, Nota, Sucesso, Vazio } from "../componentes/Estados";
import Icone from "../componentes/Icone";
import Lacre from "../componentes/Lacre";
import { Paginacao } from "../componentes/Lista";
import Seletor from "../componentes/Seletor";
import { useTitulo } from "../componentes/Titulo";
import { comoDataHora, comoInteiro, ORDEM_SEGMENTOS, plural, ROTULO_SEGMENTO } from "../formato";

const TAMANHO = 20;
const ABAS = [
  ["PENDENTE", "Pendentes"],
  ["APROVADA", "Aprovadas"],
  ["REJEITADA", "Rejeitadas"],
];

export default function Aprovacao() {
  useTitulo("Aprovação");
  const { usuario } = useSessao();
  const lugar = useLocation();
  const [filtros, mudar] = useFiltros();
  const estado = ABAS.some(([v]) => v === filtros.estado) ? filtros.estado : "PENDENTE";
  const pagina = Number(filtros.pagina) || 1;
  const decide = tem(usuario, "decidir_mensagens");
  const consulta = { estado, segmento: filtros.segmento, lote_id: filtros.lote, de: estado === "PENDENTE" ? undefined : filtros.de, ate: estado === "PENDENTE" ? undefined : filtros.ate, pagina, tamanho: TAMANHO };
  const lista = useCarregar(() => api.get("/api/mensagens", consulta), lugar.search);
  const [itens, setItens] = useState([]);
  const [anuncio, setAnuncio] = useState(null);
  const [selecionadas, setSelecionadas] = useState([]);
  const [confirmandoLote, setConfirmandoLote] = useState(false);
  const [ocupadoLote, setOcupadoLote] = useState(false);
  const [erroLote, setErroLote] = useState(null);
  const [sujos, setSujos] = useState({});
  const titulos = useRef({});

  /* Trocar de aba apaga o anúncio da anterior; uma lista nova da API troca os
     itens e desmarca tudo — ajustes feitos na própria renderização. */
  const [estadoVisto, setEstadoVisto] = useState(estado);
  if (estado !== estadoVisto) {
    setEstadoVisto(estado);
    setAnuncio(null);
  }
  const [dadosVistos, setDadosVistos] = useState(null);
  if (lista.dados !== dadosVistos) {
    setDadosVistos(lista.dados);
    if (lista.dados) setItens(lista.dados.itens);
    setSelecionadas([]);
  }

  function sairDaFila(id, frase) {
    setItens((atual) => {
      const i = atual.findIndex((m) => m.id === id);
      const resto = atual.filter((m) => m.id !== id);
      const proxima = resto[Math.min(i, resto.length - 1)];
      requestAnimationFrame(() => {
        if (proxima) titulos.current[proxima.id]?.focus();
      });
      if (!resto.length) lista.recarregar();
      return resto;
    });
    setSelecionadas((s) => s.filter((x) => x !== id));
    setSujos((s) => ({ ...s, [id]: false }));
    setAnuncio(frase);
  }

  async function aprovarLote() {
    setOcupadoLote(true);
    setErroLote(null);
    try {
      const r = await api.post("/api/mensagens/aprovacao-em-lote", { ids: selecionadas });
      const partes = [`${plural(r.aprovadas.length, "mensagem aprovada", "mensagens aprovadas")}.`];
      if (r.ja_decididas.length) partes.push(`${plural(r.ja_decididas.length, "já tinha sido decidida", "já tinham sido decididas")} por outra pessoa e ficou como estava.`);
      if (r.nao_encontradas.length) partes.push(`${plural(r.nao_encontradas.length, "não foi encontrada", "não foram encontradas")}.`);
      setAnuncio({ texto: partes.join(" "), lacre: r.aprovadas.length > 0 });
      setConfirmandoLote(false);
      setSelecionadas([]);
      lista.recarregar();
    } catch (e) {
      setErroLote(e);
      setConfirmandoLote(false);
    } finally {
      setOcupadoLote(false);
    }
  }

  const d = lista.dados;
  const filtrado = Boolean(filtros.segmento || filtros.de || filtros.ate || filtros.lote);
  const csv = comConsulta("/api/mensagens/exportacao.csv", { segmento: filtros.segmento, de: filtros.de, ate: filtros.ate });
  const pendentes = estado === "PENDENTE";
  const todasMarcadas = itens.length > 0 && itens.every((m) => selecionadas.includes(m.id));
  const algumSujo = Object.values(sujos).some(Boolean);

  return (
    <div className="pagina">
      <AlteracoesNaoSalvas quando={algumSujo} />
      {!decide && (
        <Nota titulo="Só um gestor decide.">Você vê a fila, mas aprovar, editar e rejeitar são do perfil Gestor: nenhuma mensagem sai sem essa decisão.</Nota>
      )}

      <nav className="abas" aria-label="Estado das mensagens">
        {ABAS.map(([v, r]) => (
          <Link key={v} to={comConsulta("/aprovacao", { estado: v === "PENDENTE" ? undefined : v, segmento: filtros.segmento, lote: filtros.lote })} className={`abas__aba${estado === v ? " abas__aba--ativa" : ""}`} aria-current={estado === v ? "page" : undefined}>
            {r}
          </Link>
        ))}
      </nav>

      <form className="filtros" aria-label="Filtros da fila" onSubmit={(e) => e.preventDefault()}>
        <Seletor id="a-segmento" rotulo="Segmento" valor={filtros.segmento} aoMudar={(v) => mudar({ segmento: v })} todos="Todos os segmentos" opcoes={ORDEM_SEGMENTOS.map((s) => [s, ROTULO_SEGMENTO[s]])} />
        {!pendentes && (
          <>
            <div className="campo">
              <label className="campo__rotulo" htmlFor="a-de">
                Decididas de
              </label>
              <input id="a-de" type="date" className="entrada" value={filtros.de ?? ""} onChange={(e) => mudar({ de: e.target.value })} />
            </div>
            <div className="campo">
              <label className="campo__rotulo" htmlFor="a-ate">
                até
              </label>
              <input id="a-ate" type="date" className="entrada" value={filtros.ate ?? ""} onChange={(e) => mudar({ ate: e.target.value })} />
            </div>
          </>
        )}
        {estado === "APROVADA" && (
          <a className="botao botao--secundario filtros__limpar" href={csv} download>
            <Icone nome="baixar" /> Exportar aprovadas (CSV)
          </a>
        )}
      </form>

      {filtros.lote && (
        <div className="faixa-anterior" role="status">
          <p>
            <Icone nome="filtro" /> <strong>Só as mensagens de uma geração.</strong>
          </p>
          <button type="button" className="botao botao--secundario botao--pequeno" onClick={() => mudar({ lote: null })}>
            Ver toda a fila
          </button>
        </div>
      )}

      {anuncio &&
        (anuncio.lacre ? (
          <div className="anuncio" role="status">
            <Lacre numero={anuncio.numero} titulo={anuncio.texto} novo compacto />
          </div>
        ) : (
          <Sucesso aoFechar={() => setAnuncio(null)}>{anuncio.texto ?? anuncio}</Sucesso>
        ))}

      <section className="bloco bloco--fila" aria-labelledby="t-fila" aria-busy={lista.carregando}>
        <div className="bloco__cabeca bloco__cabeca--linha">
          <div>
            <h2 id="t-fila" className="bloco__titulo">
              {pendentes ? "Fila de aprovação" : estado === "APROVADA" ? "Aprovadas — prontas para envio" : "Rejeitadas"}
            </h2>
            {d && <p className="bloco__sub">{plural(d.total, "mensagem", "mensagens")}{pendentes ? " esperando a decisão" : estado === "APROVADA" ? " · o sistema não envia: quem envia usa o contato do parceiro" : ""}</p>}
          </div>
          {decide && pendentes && itens.length > 0 && (
            <div className="selecao-lote">
              <label className="caixa-de-selecao">
                <input type="checkbox" checked={todasMarcadas} onChange={(e) => setSelecionadas(e.target.checked ? itens.map((m) => m.id) : [])} /> Selecionar as {comoInteiro(itens.length)} desta página
              </label>
              <button type="button" className="botao botao--primario" disabled={!selecionadas.length || confirmandoLote} onClick={() => setConfirmandoLote(true)}>
                Aprovar selecionadas ({comoInteiro(selecionadas.length)})
              </button>
            </div>
          )}
        </div>
        {confirmandoLote && <Confirmacao texto={`Aprovar as ${comoInteiro(selecionadas.length)}?`} detalhe="Cada uma fica pronta para envio, com a sua decisão registrada. As que outra pessoa decidiu no meio ficam como estavam." acao="Aprovar" ocupado={ocupadoLote} aoConfirmar={aprovarLote} aoCancelar={() => setConfirmandoLote(false)} />}
        <ErroDaAcao erro={erroLote} />
        {lista.carregando && !d && <Carregando rotulo="Carregando a fila" linhas={6} />}
        <ErroDaTela erro={lista.erro} />
        {d && !itens.length && pendentes && !filtrado && (
          <Vazio titulo="Nenhuma mensagem pendente." compacto icone="aprovacao" acao={tem(usuario, "mensagens") ? "Gerar mensagens" : undefined} para="/mensagens">
            As mensagens geradas chegam aqui e esperam a decisão de um gestor.
          </Vazio>
        )}
        {d && !itens.length && pendentes && filtrado && (
          <Vazio titulo="Nenhuma mensagem pendente neste recorte." compacto icone="busca">
            Tire um dos filtros para ver a fila inteira.
          </Vazio>
        )}
        {d && !itens.length && !pendentes && (
          <Vazio titulo={filtrado ? "Nenhuma decisão neste recorte." : "Nenhuma decisão ainda."} compacto icone="aprovacao" acao="Ver as pendentes" para="/aprovacao">
            As decisões aparecem aqui, da mais recente para a mais antiga, com quem decidiu e quando.
          </Vazio>
        )}
        {itens.length > 0 && (
          <ol className="lista-mensagens">
            {itens.map((m) => (
              <li key={m.id}>
                {pendentes ? (
                  <Pendente
                    mensagem={m}
                    decide={decide}
                    selecionada={selecionadas.includes(m.id)}
                    aoSelecionar={(sim) => setSelecionadas((s) => (sim ? [...s, m.id] : s.filter((x) => x !== m.id)))}
                    refTitulo={(el) => {
                      titulos.current[m.id] = el;
                    }}
                    aoDecidir={sairDaFila}
                    aoAtualizar={(nova, frase) => {
                      setItens((l) => l.map((x) => (x.id === nova.id ? nova : x)));
                      setAnuncio(frase);
                    }}
                    aoConflito={(frase) => {
                      setAnuncio(frase);
                      lista.recarregar();
                    }}
                    aoSujar={(sujo) => setSujos((s) => ({ ...s, [m.id]: sujo }))}
                  />
                ) : (
                  <Decidida mensagem={m} />
                )}
              </li>
            ))}
          </ol>
        )}
        {d && itens.length > 0 && <Paginacao pagina={pagina} tamanho={TAMANHO} total={d.total} aoMudar={(p) => mudar({ pagina: p > 1 ? p : null }, { manterPagina: true })} rotulo="mensagens" />}
      </section>
    </div>
  );
}

function Pendente({ mensagem: m, decide, selecionada, aoSelecionar, refTitulo, aoDecidir, aoAtualizar, aoConflito, aoSujar }) {
  const [modo, setModo] = useState(null);
  const [texto, setTexto] = useState(m.texto);
  const [motivo, setMotivo] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState(null);
  const campo = useRef(null);

  useEffect(() => {
    aoSujar((modo === "editar" && texto !== m.texto) || (modo === "rejeitar" && motivo.trim() !== ""));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [modo, texto, motivo]);

  useEffect(() => {
    if (modo) campo.current?.focus();
  }, [modo]);

  async function agir(fazer) {
    setOcupado(true);
    setErro(null);
    try {
      await fazer();
    } catch (e) {
      if (e instanceof ErroDaApi && e.status === 409) aoConflito(`${e.message}${e.ajuda ? ` ${e.ajuda}` : ""}`);
      else setErro(e);
    } finally {
      setOcupado(false);
    }
  }

  const aprovar = () => agir(async () => {
    await api.post(`/api/mensagens/${m.id}/aprovacao`);
    aoDecidir(m.id, { texto: `Mensagem para ${m.parceiro} aprovada.`, lacre: true, numero: m.id });
  });
  const rejeitar = () => agir(async () => {
    await api.post(`/api/mensagens/${m.id}/rejeicao`, { motivo: motivo.trim() || null });
    aoDecidir(m.id, `Mensagem para ${m.parceiro} rejeitada.`);
  });
  const salvar = () => agir(async () => {
    const nova = await api.post(`/api/mensagens/${m.id}/edicao`, { texto });
    setModo(null);
    aoAtualizar(nova, `Texto da mensagem para ${m.parceiro} salvo. Ela continua na fila, esperando a decisão.`);
  });

  const erroDoTexto = erro?.campos?.find((c) => c.campo === "texto");
  const editor =
    modo === "editar" ? (
      <div className="campo">
        <label className="campo__rotulo" htmlFor={`texto-${m.id}`}>
          Texto da mensagem
        </label>
        <textarea id={`texto-${m.id}`} ref={campo} className="entrada" rows={6} value={texto} onChange={(e) => setTexto(e.target.value)} aria-describedby={`texto-${m.id}-ajuda${erroDoTexto ? ` texto-${m.id}-erro` : ""}`} aria-invalid={erroDoTexto ? true : undefined} />
        {erroDoTexto && (
          <p className="campo__erro" id={`texto-${m.id}-erro`}>
            <Icone nome="erro" />
            <span>{erroDoTexto.mensagem}</span>
          </p>
        )}
        <p className="campo__ajuda" id={`texto-${m.id}-ajuda`}>
          <strong>Salvar não aprova</strong>: a mensagem continua na fila.
        </p>
      </div>
    ) : null;

  return (
    <CartaoMensagem mensagem={m} ref={refTitulo} editor={editor} rodape={!erroDoTexto && <ErroDaAcao erro={erro} />}>
      {decide && (
        <>
          {modo === null && (
            <>
              <label className="caixa-de-selecao cartao-mensagem__marca">
                <input type="checkbox" checked={selecionada} onChange={(e) => aoSelecionar(e.target.checked)} />
                <span className="sr-only">Selecionar a mensagem para {m.parceiro}</span>
              </label>
              <button type="button" className="botao botao--primario" onClick={aprovar} disabled={ocupado}>
                <Icone nome="certo" /> Aprovar
              </button>
              <button type="button" className="botao botao--secundario" onClick={() => (setTexto(m.texto), setModo("editar"))} disabled={ocupado}>
                <Icone nome="lapis" /> Editar
              </button>
              <button type="button" className="botao botao--secundario" onClick={() => setModo("rejeitar")} disabled={ocupado}>
                <Icone nome="fechar" /> Rejeitar
              </button>
            </>
          )}
          {modo === "editar" && (
            <>
              <button type="button" className="botao botao--primario" onClick={salvar} disabled={ocupado || !texto.trim()}>
                {ocupado ? "Salvando…" : "Salvar o texto"}
              </button>
              <button type="button" className="botao botao--secundario" onClick={() => (setModo(null), setErro(null))} disabled={ocupado}>
                Cancelar
              </button>
            </>
          )}
          {modo === "rejeitar" && (
            <div className="rejeicao">
              <div className="campo">
                <label className="campo__rotulo" htmlFor={`motivo-${m.id}`}>
                  Motivo da rejeição (opcional)
                </label>
                <textarea id={`motivo-${m.id}`} ref={campo} className="entrada" rows={2} value={motivo} onChange={(e) => setMotivo(e.target.value)} aria-describedby={`motivo-${m.id}-ajuda`} />
                <p className="campo__ajuda" id={`motivo-${m.id}-ajuda`}>
                  Fica no histórico, e ajuda a ajustar as próximas mensagens.
                </p>
              </div>
              <div className="formulario__acoes">
                <button type="button" className="botao botao--perigo" onClick={rejeitar} disabled={ocupado}>
                  {ocupado ? "Rejeitando…" : "Rejeitar mensagem"}
                </button>
                <button type="button" className="botao botao--secundario" onClick={() => (setModo(null), setMotivo(""))} disabled={ocupado}>
                  Cancelar
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </CartaoMensagem>
  );
}

function Decidida({ mensagem: m }) {
  const [copia, setCopia] = useState(null);

  async function copiar() {
    try {
      await navigator.clipboard.writeText(m.texto);
      setCopia({ ok: true, texto: `Texto da mensagem para ${m.parceiro} copiado.` });
    } catch {
      setCopia({ ok: false, texto: "Não foi possível copiar o texto. O navegador não deu acesso à área de transferência: selecione o texto e copie à mão." });
    }
  }

  const aprovada = m.estado === "APROVADA";
  return (
    <CartaoMensagem
      mensagem={m}
      rodape={
        <div className="cartao-mensagem__decisao">
          {aprovada ? (
            <Lacre numero={m.id} titulo="Aprovada" quem={m.decidida_por} quando={m.decidida_em} compacto />
          ) : (
            <p className="decisao-rejeitada">
              <strong>Rejeitada</strong> por {m.decidida_por ?? "—"} em {comoDataHora(m.decidida_em)}
              {m.motivo_rejeicao ? <span className="decisao-rejeitada__motivo"> — {m.motivo_rejeicao}</span> : <span className="discreto"> — sem motivo registrado</span>}
            </p>
          )}
          {aprovada && <p className="cartao-mensagem__contato">{m.contato ? `Contato: ${m.contato}` : "Parceiro sem contato cadastrado"}</p>}
          {copia && (
            <p className={copia.ok ? "texto-ok" : "texto-erro"} role="status">
              {copia.texto}
            </p>
          )}
        </div>
      }
    >
      {aprovada && (
        <button type="button" className="botao botao--secundario" onClick={copiar}>
          <Icone nome="copiar" /> Copiar texto
        </button>
      )}
    </CartaoMensagem>
  );
}
