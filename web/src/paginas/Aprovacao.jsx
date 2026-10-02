/**
 * A fila de aprovação — UC11, RF37 a RF39, RN06, histórias H61 a H63.
 *
 * **Nenhuma mensagem sai sem a decisão de um gestor.** O Gestor aprova, edita ou
 * rejeita cada mensagem, ou aprova várias de uma vez; o Analista vê a mesma fila,
 * sem os controles. Quem decide o que cada um pode é a API (`usuario.telas`, com
 * `decidir_mensagens`), como o menu — e a rota recusa de qualquer jeito
 * (regra 2.5).
 *
 * **A decisão tira a mensagem da fila, e o foco vai para a próxima** (passo 6): o
 * título dela recebe o foco, e o leitor de tela anuncia a decisão e para quem é a
 * próxima. Editar não decide: a mensagem continua na fila, com o texto novo e o
 * aviso dos números que não vieram dos dados.
 *
 * **A decisão que chegou tarde** — outra pessoa decidiu enquanto esta revisava —
 * volta com a decisão registrada, e a fila se atualiza (E1).
 *
 * **O histórico é a mesma lista, em outro estado** (RF40, H64): as aprovadas e as
 * rejeitadas, com quem decidiu, quando, o conteúdo final, o texto redigido quando
 * houve edição e o motivo da rejeição. As aprovadas estão prontas para envio — o
 * sistema não envia —, com o contato do parceiro, "Copiar texto" e a exportação
 * em CSV.
 *
 * **O filtro vive no endereço** (`?estado=`, `?segmento=`, `?lote=`, `?de=`,
 * `?ate=`, `?pagina=`), para o link da geração abrir a fila só das mensagens dela.
 */
import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { api } from "../api/cliente";
import { useSessao } from "../api/contextoSessao";
import AlteracoesNaoSalvas from "../componentes/AlteracoesNaoSalvas";
import { Esqueleto } from "../componentes/Carregando";
import CartaoMensagem from "../componentes/CartaoMensagem";
import Confirmacao from "../componentes/Confirmacao";
import EstadoVazio from "../componentes/EstadoVazio";
import { comoDataHora, comoInteiro, ROTULO_SEGMENTO } from "../formato";
import "../estilos/aprovacao.css";

export const TAMANHO = 20;

const VISTAS = [
  ["PENDENTE", "Pendentes"],
  ["APROVADA", "Aprovadas"],
  ["REJEITADA", "Rejeitadas"],
];

export default function Aprovacao() {
  const { usuario } = useSessao();
  const decide = Boolean(usuario?.telas?.includes("decidir_mensagens"));
  const [parametros, setParametros] = useSearchParams();
  const estado = parametros.get("estado") ?? "PENDENTE";
  const pendentes = estado === "PENDENTE";
  const segmento = parametros.get("segmento") ?? "";
  const lote = parametros.get("lote") ?? "";
  const de = parametros.get("de") ?? "";
  const ate = parametros.get("ate") ?? "";
  const pagina = Number(parametros.get("pagina") ?? 1) || 1;

  const [dados, setDados] = useState(null);
  const [erroCarga, setErroCarga] = useState(null);
  const [recarga, setRecarga] = useState(0);
  const [aviso, setAviso] = useState(null);
  const [anuncio, setAnuncio] = useState("");
  const [selecionadas, setSelecionadas] = useState(() => new Set());
  const [confirmandoLote, setConfirmandoLote] = useState(false);
  const [ocupada, setOcupada] = useState(null);
  const titulos = useRef(new Map());
  /* Para onde o foco vai quando a lista nova estiver na tela. Numa referência, e
     não no estado: depois de usado, some, e a próxima recarga não rouba o foco de
     quem estiver, por exemplo, no filtro. */
  const focoPendente = useRef(null);

  useEffect(() => {
    let vivo = true;
    api
      .get("/api/mensagens", { estado, segmento, lote_id: lote, de, ate, pagina, tamanho: TAMANHO })
      .then((corpo) => vivo && setDados(corpo))
      .catch((e) => vivo && setErroCarga(e));
    return () => {
      vivo = false;
    };
  }, [estado, segmento, lote, de, ate, pagina, recarga]);

  /* O foco segue para a próxima mensagem depois que ela está na tela. */
  useEffect(() => {
    if (focoPendente.current === null) return;
    titulos.current.get(focoPendente.current)?.focus();
    focoPendente.current = null;
  }, [dados]);

  function filtrar(mudancas) {
    const novos = new URLSearchParams(parametros);
    Object.entries(mudancas).forEach(([chave, valor]) => {
      if (valor === "" || valor === null) novos.delete(chave);
      else novos.set(chave, String(valor));
    });
    // Mudar o filtro volta à primeira página, e a seleção era de outra lista.
    if (!("pagina" in mudancas)) novos.delete("pagina");
    setParametros(novos);
    setSelecionadas(new Set());
    setAviso(null);
  }

  /* A mensagem decidida sai da lista, e o foco vai para a que tomou o lugar dela
     — ou para a anterior, se era a última. Lista vazia pede a página de novo. */
  function tirarDaFila(id, frase) {
    const itens = dados.itens;
    const posicao = Math.max(itens.findIndex((m) => m.id === id), 0);
    const restantes = itens.filter((m) => m.id !== id);
    const proxima = restantes[Math.min(posicao, restantes.length - 1)];
    focoPendente.current = proxima ? proxima.id : null;
    setDados((atual) => ({
      ...atual,
      itens: atual.itens.filter((m) => m.id !== id),
      total: Math.max(atual.total - 1, 0),
    }));
    setSelecionadas((atual) => {
      const nova = new Set(atual);
      nova.delete(id);
      return nova;
    });
    if (frase) {
      setAnuncio(proxima ? `${frase} Próxima: mensagem para ${proxima.parceiro}.` : `${frase} A fila desta página acabou.`);
    }
    // Página vazia: a próxima página, se houver, vem para cá.
    if (!restantes.length) setRecarga((r) => r + 1);
  }

  function trocarNaFila(mensagem) {
    focoPendente.current = mensagem.id;
    setDados((atual) => ({ ...atual, itens: atual.itens.map((m) => (m.id === mensagem.id ? mensagem : m)) }));
  }

  /* A decisão que chegou tarde: a mensagem já saiu da fila por outra mão, e a
     fila se atualiza (UC11-E1). */
  function tratarErro(e, id) {
    setAviso({ tipo: "erro", titulo: e.message, ajuda: e.ajuda });
    if (e.status === 409 || e.status === 404) {
      tirarDaFila(id, "");
      setRecarga((r) => r + 1);
    }
  }

  async function aprovar(m) {
    setOcupada(m.id);
    setAviso(null);
    try {
      await api.post(`/api/mensagens/${m.id}/aprovacao`);
      tirarDaFila(m.id, `Mensagem para ${m.parceiro} aprovada.`);
    } catch (e) {
      tratarErro(e, m.id);
    } finally {
      setOcupada(null);
    }
  }

  async function rejeitar(m, motivo) {
    setOcupada(m.id);
    setAviso(null);
    try {
      await api.post(`/api/mensagens/${m.id}/rejeicao`, { motivo: motivo.trim() || null });
      tirarDaFila(m.id, `Mensagem para ${m.parceiro} rejeitada.`);
      return true;
    } catch (e) {
      tratarErro(e, m.id);
      return false;
    } finally {
      setOcupada(null);
    }
  }

  async function editar(m, texto) {
    setOcupada(m.id);
    setAviso(null);
    try {
      const editada = await api.post(`/api/mensagens/${m.id}/edicao`, { texto });
      trocarNaFila(editada);
      setAnuncio(`Texto da mensagem para ${m.parceiro} salvo. Ela continua na fila, esperando a decisão.`);
      return true;
    } catch (e) {
      if (e.status === 422) {
        setAviso({ tipo: "erro", titulo: e.message, ajuda: e.ajuda });
      } else {
        tratarErro(e, m.id);
      }
      return false;
    } finally {
      setOcupada(null);
    }
  }

  async function aprovarSelecionadas() {
    setOcupada("lote");
    setAviso(null);
    try {
      const resultado = await api.post("/api/mensagens/aprovacao-em-lote", { ids: [...selecionadas] });
      const n = resultado.aprovadas.length;
      const tarde = resultado.ja_decididas.length;
      const titulo = n === 1 ? "1 mensagem aprovada." : `${comoInteiro(n)} mensagens aprovadas.`;
      const ajuda = tarde
        ? `${tarde === 1 ? "1 já tinha" : `${tarde} já tinham`} sido decidida${tarde === 1 ? "" : "s"} por outra pessoa, e ficou como estava.`
        : null;
      setAviso({ tipo: "sucesso", titulo, ajuda });
      setAnuncio([titulo, ajuda].filter(Boolean).join(" "));
      setSelecionadas(new Set());
      setRecarga((r) => r + 1);
    } catch (e) {
      setAviso({ tipo: "erro", titulo: e.message, ajuda: e.ajuda });
    } finally {
      setOcupada(null);
      setConfirmandoLote(false);
    }
  }

  async function copiar(m) {
    try {
      await navigator.clipboard.writeText(m.texto);
      setAnuncio(`Texto da mensagem para ${m.parceiro} copiado.`);
      return true;
    } catch {
      setAviso({
        tipo: "erro",
        titulo: "Não foi possível copiar o texto.",
        ajuda: "O navegador não deu acesso à área de transferência: selecione o texto e copie à mão.",
      });
      return false;
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

  if (!dados) {
    return (
      <section className="painel" aria-busy="true" aria-label="Carregando a fila">
        <div className="aprovacao__corpo">
          <Esqueleto altura={240} />
        </div>
      </section>
    );
  }

  const itens = dados.itens;
  const todas = itens.length > 0 && itens.every((m) => selecionadas.has(m.id));
  const primeiro = (pagina - 1) * TAMANHO + (itens.length ? 1 : 0);
  const ultimo = (pagina - 1) * TAMANHO + itens.length;

  return (
    <>
      <p className="so-leitor" role="status">
        {anuncio}
      </p>

      <fieldset className="escolha aprovacao__vistas">
        <legend className="so-leitor">Mensagens</legend>
        <div className="escolha__opcoes">
          {VISTAS.map(([valor, rotulo]) => (
            <label key={valor} className="escolha__opcao">
              <input
                type="radio"
                name="vista"
                value={valor}
                checked={estado === valor}
                onChange={() =>
                  // O período é o da decisão: na fila de pendentes, ele não existe.
                  filtrar(valor === "PENDENTE" ? { estado: "", de: "", ate: "" } : { estado: valor })
                }
              />
              <span>{rotulo}</span>
            </label>
          ))}
        </div>
      </fieldset>

      {pendentes && !decide && (
        <div className="aviso aviso--informativo">
          <p className="aviso__titulo">Só um gestor decide.</p>
          <p className="aviso__ajuda">
            Você vê a fila, mas aprovar, editar e rejeitar são do perfil Gestor: nenhuma mensagem sai sem essa decisão.
          </p>
        </div>
      )}

      {aviso && (
        <div className={aviso.tipo === "sucesso" ? "aviso aviso--sucesso" : "aviso"} role="alert">
          <p className="aviso__titulo">{aviso.titulo}</p>
          {aviso.ajuda && <p className="aviso__ajuda">{aviso.ajuda}</p>}
        </div>
      )}

      <section className="painel" aria-labelledby="titulo-fila">
        <div className="painel__cabecalho">
          <h2 className="painel__titulo" id="titulo-fila">
            {VISTAS.find(([valor]) => valor === estado)?.[1] ?? "Pendentes"}
          </h2>
          <span className="painel__nota">{nota(estado, dados.total)}</span>
        </div>

        <div className="aprovacao__corpo aprovacao__filtros">
          <div className="campo aprovacao__filtro">
            <label htmlFor="filtro-segmento">Segmento</label>
            <select id="filtro-segmento" value={segmento} onChange={(e) => filtrar({ segmento: e.target.value })}>
              <option value="">Todos os segmentos</option>
              {Object.entries(ROTULO_SEGMENTO).map(([valor, rotulo]) => (
                <option key={valor} value={valor}>
                  {rotulo}
                </option>
              ))}
            </select>
          </div>
          {!pendentes && (
            <>
              <div className="campo aprovacao__filtro aprovacao__filtro--data">
                <label htmlFor="filtro-de">Decididas de</label>
                <input id="filtro-de" type="date" value={de} onChange={(e) => filtrar({ de: e.target.value })} />
              </div>
              <div className="campo aprovacao__filtro aprovacao__filtro--data">
                <label htmlFor="filtro-ate">até</label>
                <input id="filtro-ate" type="date" value={ate} onChange={(e) => filtrar({ ate: e.target.value })} />
              </div>
            </>
          )}
          {estado === "APROVADA" && (
            <a
              className="botao botao--secundario aprovacao__exportar"
              href={`/api/mensagens/exportacao.csv?${new URLSearchParams(
                Object.entries({ segmento, de, ate }).filter(([, v]) => v !== ""),
              )}`}
              download
            >
              Exportar aprovadas (CSV)
            </a>
          )}
          {lote && (
            <p className="aprovacao__recorte">
              Só as mensagens de uma geração.{" "}
              <button type="button" className="aprovacao__limpar" onClick={() => filtrar({ lote: "" })}>
                Ver toda a fila
              </button>
            </p>
          )}
        </div>

        {decide && pendentes && itens.length > 0 && (
          <div className="aprovacao__corpo aprovacao__lote">
            <label className="aprovacao__todas">
              <input
                type="checkbox"
                checked={todas}
                onChange={() => setSelecionadas(todas ? new Set() : new Set(itens.map((m) => m.id)))}
              />
              Selecionar as {comoInteiro(itens.length)} desta página
            </label>
            {confirmandoLote ? (
              <Confirmacao
                texto={`Aprovar ${
                  selecionadas.size === 1 ? "1 mensagem" : `${comoInteiro(selecionadas.size)} mensagens`
                }? Cada uma fica registrada com a sua decisão, e nenhuma volta para a fila.`}
                acao={selecionadas.size === 1 ? "Aprovar 1 mensagem" : `Aprovar as ${comoInteiro(selecionadas.size)}`}
                ocupado={ocupada === "lote"}
                aoConfirmar={aprovarSelecionadas}
                aoCancelar={() => setConfirmandoLote(false)}
              />
            ) : (
              <button
                type="button"
                className="botao"
                disabled={selecionadas.size === 0}
                onClick={() => setConfirmandoLote(true)}
              >
                {selecionadas.size ? `Aprovar selecionadas (${comoInteiro(selecionadas.size)})` : "Aprovar selecionadas"}
              </button>
            )}
          </div>
        )}

        {itens.length ? (
          <ol
            className="mensagens__lista aprovacao__lista"
            aria-label={pendentes ? "Mensagens pendentes" : "Mensagens decididas"}
          >
            {itens.map((m) =>
              !pendentes ? (
                <Decidida key={m.id} mensagem={m} aoCopiar={() => copiar(m)} />
              ) : (
                <Pendente
                  key={m.id}
                  mensagem={m}
                  decide={decide}
                  ocupada={ocupada === m.id}
                  selecionada={selecionadas.has(m.id)}
                  refTitulo={(no) => {
                    if (no) titulos.current.set(m.id, no);
                    else titulos.current.delete(m.id);
                  }}
                  aoSelecionar={() =>
                    setSelecionadas((atual) => {
                      const nova = new Set(atual);
                      if (nova.has(m.id)) nova.delete(m.id);
                      else nova.add(m.id);
                      return nova;
                    })
                  }
                  aoAprovar={() => aprovar(m)}
                  aoRejeitar={(motivo) => rejeitar(m, motivo)}
                  aoEditar={(texto) => editar(m, texto)}
                />
              ),
            )}
          </ol>
        ) : pendentes ? (
          <EstadoVazio
            titulo={segmento || lote ? "Nenhuma mensagem pendente neste recorte." : "Nenhuma mensagem pendente."}
            texto="As mensagens geradas chegam aqui e esperam a decisão de um gestor."
            acao={{ para: "/mensagens", rotulo: "Gerar mensagens" }}
          />
        ) : (
          <EstadoVazio
            titulo={`Nenhuma mensagem ${estado === "APROVADA" ? "aprovada" : "rejeitada"} neste recorte.`}
            texto="As decisões aparecem aqui, da mais recente para a mais antiga, com quem decidiu e quando."
            acao={{ para: "/aprovacao", rotulo: "Ver as pendentes" }}
          />
        )}

        {dados.total > TAMANHO && (
          <div className="aprovacao__corpo paginacao">
            <span className="paginacao__posicao num">
              {comoInteiro(primeiro)}–{comoInteiro(ultimo)} de {comoInteiro(dados.total)}
            </span>
            <button
              type="button"
              className="botao botao--secundario"
              disabled={pagina <= 1}
              onClick={() => filtrar({ pagina: pagina - 1 })}
            >
              Anterior
            </button>
            <button
              type="button"
              className="botao botao--secundario"
              disabled={ultimo >= dados.total}
              onClick={() => filtrar({ pagina: pagina + 1 })}
            >
              Próxima
            </button>
          </div>
        )}
      </section>
    </>
  );
}

function nota(estado, total) {
  const quantas = total === 1 ? "1 mensagem" : `${comoInteiro(total)} mensagens`;
  if (estado === "APROVADA") return `${quantas} · prontas para envio: o sistema não envia, quem envia é você`;
  if (estado === "REJEITADA") return `${quantas} · ficam registradas, com o motivo`;
  return `${quantas} esperando a decisão · nenhuma é enviada sem ela`;
}

/* A mensagem decidida (RF40): quem decidiu, quando e — na rejeitada — por quê. A
   aprovada traz o contato do parceiro e "Copiar texto": é o caminho até o envio,
   que é de uma pessoa, fora do sistema (ADR-013). */
function Decidida({ mensagem: m, aoCopiar }) {
  const [copiado, setCopiado] = useState(false);
  const aprovada = m.estado === "APROVADA";
  const decisao = `${aprovada ? "Aprovada" : "Rejeitada"} por ${m.decidida_por ?? "—"} em ${comoDataHora(
    m.decidida_em,
  )}`;
  return (
    <CartaoMensagem mensagem={m} mostrarQuando>
      <p className="aprovacao__decisao">
        {decisao}
        {!aprovada && (m.motivo_rejeicao ? `. Motivo: ${m.motivo_rejeicao}` : ", sem motivo registrado")}.
      </p>
      {aprovada && (
        <div className="aprovacao__acoes">
          <button
            type="button"
            className="botao botao--secundario"
            onClick={async () => {
              if (await aoCopiar()) {
                setCopiado(true);
                setTimeout(() => setCopiado(false), 2000);
              }
            }}
          >
            {copiado ? "Copiado" : "Copiar texto"}
          </button>
          <span className="aprovacao__contato">
            {m.contato ? `Contato: ${m.contato}` : "Parceiro sem contato cadastrado"}
          </span>
        </div>
      )}
    </CartaoMensagem>
  );
}

function Pendente({
  mensagem: m,
  decide,
  ocupada,
  selecionada,
  refTitulo,
  aoSelecionar,
  aoAprovar,
  aoRejeitar,
  aoEditar,
}) {
  const [modo, setModo] = useState(null);
  const [texto, setTexto] = useState(m.texto);
  const [motivo, setMotivo] = useState("");
  const idTexto = `texto-${m.id}`;
  const idMotivo = `motivo-${m.id}`;

  const corpo =
    modo === "editar" ? (
      <div className="campo">
        <label htmlFor={idTexto}>Texto da mensagem para {m.parceiro}</label>
        <textarea
          id={idTexto}
          className="aprovacao__edicao"
          rows={4}
          maxLength={2000}
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
        />
      </div>
    ) : undefined;

  return (
    <CartaoMensagem
      ref={refTitulo}
      mensagem={m}
      mostrarQuando
      corpo={corpo}
      antes={
        decide && (
          <input
            type="checkbox"
            className="aprovacao__marca"
            checked={selecionada}
            onChange={aoSelecionar}
            aria-label={`Selecionar a mensagem para ${m.parceiro}`}
          />
        )
      }
    >
      {m.numeros_fora_dos_fatos.length > 0 && (
        <div className="aviso aviso--informativo aprovacao__numeros">
          <p className="aviso__titulo">Números que não vieram dos dados: {m.numeros_fora_dos_fatos.join(", ")}.</p>
          <p className="aviso__ajuda">
            Quem editou pode escrever um número novo, como um desconto; confira antes de aprovar.
          </p>
        </div>
      )}

      {/* O texto reescrito e o motivo digitado se perdem com a troca de tela (H97). */}
      <AlteracoesNaoSalvas
        quando={(modo === "editar" && texto !== m.texto) || (modo === "rejeitar" && motivo !== "")}
      />

      {decide && modo === null && (
        <div className="aprovacao__acoes">
          <button type="button" className="botao" disabled={ocupada} onClick={aoAprovar}>
            Aprovar
          </button>
          <button
            type="button"
            className="botao botao--secundario"
            disabled={ocupada}
            onClick={() => {
              setTexto(m.texto);
              setModo("editar");
            }}
          >
            Editar
          </button>
          <button type="button" className="botao botao--secundario" disabled={ocupada} onClick={() => setModo("rejeitar")}>
            Rejeitar
          </button>
        </div>
      )}

      {decide && modo === "editar" && (
        <div className="aprovacao__acoes">
          <button
            type="button"
            className="botao"
            disabled={ocupada}
            onClick={async () => {
              if (await aoEditar(texto)) setModo(null);
            }}
          >
            Salvar o texto
          </button>
          <button type="button" className="botao botao--secundario" onClick={() => setModo(null)}>
            Cancelar
          </button>
          <span className="aprovacao__dica">Salvar não aprova: a mensagem continua na fila.</span>
        </div>
      )}

      {decide && modo === "rejeitar" && (
        <div className="aprovacao__rejeicao">
          <div className="campo">
            <label htmlFor={idMotivo}>Motivo da rejeição (opcional)</label>
            <input
              id={idMotivo}
              type="text"
              maxLength={240}
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
              aria-describedby={`${idMotivo}-ajuda`}
            />
            <p id={`${idMotivo}-ajuda`} className="campo__ajuda">
              Fica no histórico, e ajuda a ajustar as próximas mensagens.
            </p>
          </div>
          <div className="aprovacao__acoes">
            <button type="button" className="botao" disabled={ocupada} onClick={() => aoRejeitar(motivo)}>
              Rejeitar mensagem
            </button>
            <button type="button" className="botao botao--secundario" onClick={() => setModo(null)}>
              Cancelar
            </button>
          </div>
        </div>
      )}
    </CartaoMensagem>
  );
}
