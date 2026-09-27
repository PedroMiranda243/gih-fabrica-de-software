/**
 * A geração de mensagens — UC10, RF36 e RF37, história H60 — para o Analista e o Gestor.
 *
 * **Três passos, na ordem do caso de uso:** escolher o público; ver quem entra,
 * e quem ficou de fora e por quê, antes de gerar qualquer coisa (passo 2); e
 * gerar, com as mensagens aparecendo conforme ficam prontas (A1).
 *
 * **A geração roda no servidor**, em segundo plano: a tela recebe `202` e pergunta
 * pelo lote a cada 2 s. Cada consulta traz as mensagens prontas até ali, e é isso
 * que a tela mostra — o andamento corresponde a trabalho feito, e não a uma
 * animação que o finge. Quem sair e voltar reencontra o lote.
 *
 * **Quem decide é a API** (regra 2.4): quem entra no público, os fatos de cada
 * parceiro, o tom, se o texto é do modelo de linguagem ou do modelo fixo, e por
 * quê. A tela escolhe só como mostrar.
 *
 * **Um plano abre pelo endereço** (`?plano=`): é o caminho da Campanha e da
 * execução até aqui, com o público já escolhido.
 */
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { api } from "../api/cliente";
import { Esqueleto } from "../componentes/Carregando";
import Campo from "../componentes/Campo";
import CartaoMensagem from "../componentes/CartaoMensagem";
import EstadoVazio from "../componentes/EstadoVazio";
import Segmento from "../componentes/Segmento";
import { comoDataHora, comoInteiro, comoPeriodo, ROTULO_SEGMENTO } from "../formato";
import "../estilos/mensagens.css";

/* De quanto em quanto tempo a tela pergunta pelo lote. Com o modelo carregado,
   uma mensagem leva de 2 a 4 s; sem ele, o lote inteiro termina na hora. */
export const INTERVALO_MS = 2000;

const TIPOS = [
  ["FILTRO", "Segmento e categoria"],
  ["PLANO", "Plano de campanha"],
  ["SELECAO", "Escolher parceiros"],
];

const PUBLICO_VAZIO = { tipo: "FILTRO", segmento: "", categoria_id: "", execucao_id: "", parceiros: [] };

/* O pedido como a API o espera. Campo vazio vai como nulo: quem diz que falta
   escolher é a API, com a frase dela. */
function pedido(publico) {
  if (publico.tipo === "FILTRO") {
    return {
      tipo: "FILTRO",
      segmento: publico.segmento || null,
      categoria_id: publico.categoria_id ? Number(publico.categoria_id) : null,
    };
  }
  if (publico.tipo === "PLANO") {
    return { tipo: "PLANO", execucao_id: publico.execucao_id ? Number(publico.execucao_id) : null };
  }
  return { tipo: "SELECAO", parceiros: publico.parceiros.map((p) => p.id) };
}

export default function Mensagens() {
  const [parametrosUrl] = useSearchParams();
  const planoDaUrl = parametrosUrl.get("plano");

  const [estado, setEstado] = useState(null);
  const [categorias, setCategorias] = useState([]);
  const [planos, setPlanos] = useState([]);
  const [erroCarga, setErroCarga] = useState(null);
  const [recarga, setRecarga] = useState(0);
  const [publico, setPublico] = useState(() =>
    planoDaUrl ? { ...PUBLICO_VAZIO, tipo: "PLANO", execucao_id: planoDaUrl } : PUBLICO_VAZIO,
  );
  const [previa, setPrevia] = useState(null);
  const [consultando, setConsultando] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState(null);
  const [lote, setLote] = useState(null);

  useEffect(() => {
    let vivo = true;
    Promise.all([
      api.get("/api/mensagens/geracao"),
      api.get("/api/categorias"),
      api.get("/api/otimizacoes", { tamanho: 20 }),
    ])
      .then(async ([dados, lista, historico]) => {
        if (!vivo) return;
        setEstado(dados);
        setCategorias(lista);
        setPlanos(historico.itens.filter((e) => e.situacao === "CONCLUIDA" && e.viavel));
        /* O lote em andamento — disparado em outra aba, ou antes de a pessoa sair
           e voltar —, ou o último, com as mensagens. */
        const aberto = dados.em_andamento ?? dados.ultimo;
        if (aberto) {
          const completo = await api.get(`/api/mensagens/lotes/${aberto.id}`);
          if (vivo) setLote((atual) => (atual && atual.id !== completo.id ? atual : completo));
        }
      })
      .catch((e) => vivo && setErroCarga(e));
    return () => {
      vivo = false;
    };
  }, [recarga]);

  /* Vindo da Campanha ou da execução, o público já está escolhido: a prévia vem
     junto, sem mais um clique. */
  useEffect(() => {
    if (!planoDaUrl) return undefined;
    let vivo = true;
    api
      .post("/api/mensagens/publico", { tipo: "PLANO", execucao_id: Number(planoDaUrl) })
      .then((resposta) => vivo && setPrevia(resposta))
      .catch((e) => vivo && setErro(e));
    return () => {
      vivo = false;
    };
  }, [planoDaUrl]);

  const idAcompanhado = lote?.situacao === "EM_ANDAMENTO" ? lote.id : null;
  useEffect(() => {
    if (!idAcompanhado) return undefined;
    const relogio = setInterval(() => {
      api
        .get(`/api/mensagens/lotes/${idAcompanhado}`)
        .then((atual) => {
          setLote(atual);
          if (atual.situacao !== "EM_ANDAMENTO") setRecarga((r) => r + 1);
        })
        /* Falha de rede numa consulta não encerra o acompanhamento: a próxima
           tenta de novo. O lote continua no servidor de qualquer jeito. */
        .catch(() => {});
    }, INTERVALO_MS);
    return () => clearInterval(relogio);
  }, [idAcompanhado]);

  function mudarPublico(novo) {
    setPublico(novo);
    // A prévia é de outro público: mostrá-la com o público novo seria mentir.
    setPrevia(null);
    setErro(null);
  }

  async function verQuemEntra() {
    setConsultando(true);
    setErro(null);
    try {
      setPrevia(await api.post("/api/mensagens/publico", pedido(publico)));
    } catch (e) {
      setPrevia(null);
      setErro(e);
    } finally {
      setConsultando(false);
    }
  }

  async function gerar() {
    setEnviando(true);
    setErro(null);
    try {
      const novo = await api.post("/api/mensagens/lotes", pedido(publico));
      setLote({ ...novo, mensagens: [] });
      setPrevia(null);
    } catch (e) {
      setErro(e);
      /* A recusa mais comum é "já há uma geração em andamento": reler o estado faz
         a tela encontrá-la e acompanhá-la, como no benchmark. */
      setRecarga((r) => r + 1);
    } finally {
      setEnviando(false);
    }
  }

  async function tentarDeNovo() {
    setErro(null);
    try {
      const refeito = await api.post(`/api/mensagens/lotes/${lote.id}/refazer`);
      setLote((atual) => ({ ...refeito, mensagens: atual?.mensagens ?? [] }));
    } catch (e) {
      setErro(e);
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
      <section className="painel" aria-busy="true" aria-label="Carregando as mensagens">
        <div className="mensagens__corpo">
          <Esqueleto altura={220} />
        </div>
      </section>
    );
  }

  const gerando = lote?.situacao === "EM_ANDAMENTO";

  return (
    <>
      <p className="so-leitor" role="status">
        {anuncio(lote)}
      </p>

      {!estado.assistente.disponivel && (
        <div className="aviso aviso--informativo">
          <p className="aviso__titulo">O assistente está indisponível.</p>
          <p className="aviso__ajuda">
            {estado.assistente.motivo} As mensagens saem do modelo fixo da equipe, com os mesmos números, e a
            aprovação funciona igual.
          </p>
        </div>
      )}

      {erro && (
        <div className="aviso" role="alert">
          <p className="aviso__titulo">{erro.message}</p>
          {erro.ajuda && <p className="aviso__ajuda">{erro.ajuda}</p>}
        </div>
      )}

      <section className="painel" aria-labelledby="titulo-publico">
        <div className="painel__cabecalho">
          <h2 className="painel__titulo" id="titulo-publico">
            Público
          </h2>
          <span className="painel__nota">
            {estado.assistente.disponivel
              ? `Redigidas pelo ${estado.assistente.modelo}, com os números conferidos antes de chegar à fila`
              : "Redigidas pelo modelo fixo, com os números do sistema"}
          </span>
        </div>
        <Publico
          publico={publico}
          categorias={categorias}
          planos={planos}
          consultando={consultando}
          aoMudar={mudarPublico}
          aoConsultar={verQuemEntra}
        />
      </section>

      {previa && (
        <Previa
          previa={previa}
          gerando={gerando}
          enviando={enviando}
          plano={publico.tipo === "PLANO"}
          aoGerar={gerar}
        />
      )}

      {lote ? (
        <Lote lote={lote} assistente={estado.assistente} aoTentarDeNovo={tentarDeNovo} />
      ) : (
        !previa && (
          <section className="painel" aria-label="Mensagens geradas">
            <EstadoVazio
              titulo="Nenhuma mensagem gerada ainda."
              texto="Escolha o público e veja quem entra: as mensagens aparecem aqui, uma a uma, conforme ficam prontas."
            />
          </section>
        )
      )}
    </>
  );
}

function anuncio(lote) {
  if (!lote) return "";
  const prontas = lote.geradas + lote.falhas.length;
  if (lote.situacao === "EM_ANDAMENTO") return `${prontas} de ${lote.total} mensagens prontas.`;
  const falhas = lote.falhas.length ? ` ${lote.falhas.length} sem mensagem.` : "";
  return `Geração concluída: ${lote.geradas} de ${lote.total} mensagens.${falhas}`;
}

/* ------------------------------------------------------------------ o público */
function Publico({ publico, categorias, planos, consultando, aoMudar, aoConsultar }) {
  return (
    <form
      className="mensagens__corpo mensagens__publico"
      noValidate
      onSubmit={(e) => {
        e.preventDefault();
        aoConsultar();
      }}
    >
      <fieldset className="escolha">
        <legend className="escolha__legenda">Para quem</legend>
        <div className="escolha__opcoes">
          {TIPOS.map(([tipo, rotulo]) => (
            <label key={tipo} className="escolha__opcao">
              <input
                type="radio"
                name="tipo-publico"
                value={tipo}
                checked={publico.tipo === tipo}
                onChange={() => aoMudar({ ...publico, tipo })}
              />
              <span>{rotulo}</span>
            </label>
          ))}
        </div>
      </fieldset>

      {publico.tipo === "FILTRO" && (
        <div className="mensagens__campos">
          <Campo id="segmento" rotulo="Segmento" ajuda="O do período mais recente.">
            <select
              id="campo-segmento"
              value={publico.segmento}
              onChange={(e) => aoMudar({ ...publico, segmento: e.target.value })}
            >
              <option value="">Qualquer segmento</option>
              {Object.entries(ROTULO_SEGMENTO).map(([valor, rotulo]) => (
                <option key={valor} value={valor}>
                  {rotulo}
                </option>
              ))}
            </select>
          </Campo>
          <Campo id="categoria" rotulo="Categoria" ajuda="Só entra quem tem a categoria confirmada (RN05).">
            <select
              id="campo-categoria"
              value={publico.categoria_id}
              onChange={(e) => aoMudar({ ...publico, categoria_id: e.target.value })}
            >
              <option value="">Qualquer categoria</option>
              {categorias.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nome}
                </option>
              ))}
            </select>
          </Campo>
        </div>
      )}

      {publico.tipo === "PLANO" &&
        (planos.length ? (
          <div className="mensagens__campos">
            <Campo id="plano" rotulo="Plano" ajuda="Cada parceiro do plano recebe a mensagem com a ação dele.">
              <select
                id="campo-plano"
                value={publico.execucao_id}
                onChange={(e) => aoMudar({ ...publico, execucao_id: e.target.value })}
              >
                <option value="">Escolha um plano</option>
                {planos.map((e) => (
                  <option key={e.id} value={e.id}>
                    {rotuloDoPlano(e)}
                  </option>
                ))}
              </select>
            </Campo>
          </div>
        ) : (
          <EstadoVazio
            titulo="Nenhum plano calculado ainda."
            texto="O plano de campanha diz quem recebe cada ação; com ele, cada mensagem já leva a ação do parceiro."
            acao={{ para: "/campanha", rotulo: "Ir para a campanha" }}
          />
        ))}

      {publico.tipo === "SELECAO" && (
        <Selecao
          escolhidos={publico.parceiros}
          aoMudar={(parceiros) => aoMudar({ ...publico, parceiros })}
        />
      )}

      <div className="mensagens__acoes">
        <button className="botao" type="submit" disabled={consultando}>
          {consultando ? "Consultando…" : "Ver quem entra"}
        </button>
      </div>
    </form>
  );
}

function rotuloDoPlano(e) {
  const p = e.parametros ?? {};
  const aplicacao = comoPeriodo({ data_inicio: p.aplicacao_inicio, data_fim: p.aplicacao_fim });
  const acoes = `${comoInteiro(e.acoes)} ${e.acoes === 1 ? "ação" : "ações"}`;
  return `${aplicacao} · ${acoes} · calculado em ${comoDataHora(e.concluida_em)}`;
}

/* A seleção manual: busca pelo nome, como na lista de parceiros (RF24), e os
   escolhidos logo abaixo. Quem está desativado nem aparece na busca. */
function Selecao({ escolhidos, aoMudar }) {
  const [termo, setTermo] = useState("");
  const [achados, setAchados] = useState({ termo: "", itens: [] });
  const busca = termo.trim();

  useEffect(() => {
    if (busca.length < 2) return undefined;
    let vivo = true;
    // Espera a pessoa parar de digitar: uma consulta por palavra, e não por letra.
    const relogio = setTimeout(() => {
      api
        .get("/api/parceiros", { busca, ativo: true, tamanho: 8 })
        .then((pagina) => vivo && setAchados({ termo: busca, itens: pagina.itens }))
        .catch(() => {});
    }, 300);
    return () => {
      vivo = false;
      clearTimeout(relogio);
    };
  }, [busca]);

  const ids = new Set(escolhidos.map((p) => p.id));
  const resultados = busca.length >= 2 && achados.termo === busca ? achados.itens : [];

  return (
    <div className="selecao">
      <Campo id="busca-parceiro" rotulo="Buscar parceiro" ajuda="Digite ao menos duas letras do nome.">
        <input
          id="campo-busca-parceiro"
          type="search"
          autoComplete="off"
          value={termo}
          onChange={(e) => setTermo(e.target.value)}
        />
      </Campo>

      {resultados.length > 0 && (
        <ul className="selecao__resultados" aria-label="Parceiros encontrados">
          {resultados.map((p) => (
            <li key={p.id}>
              <span className="selecao__nome">{p.nome}</span>
              <button
                className="botao botao--secundario"
                type="button"
                disabled={ids.has(p.id)}
                aria-label={ids.has(p.id) ? `${p.nome} já escolhido` : `Adicionar ${p.nome}`}
                onClick={() => aoMudar([...escolhidos, { id: p.id, nome: p.nome }])}
              >
                {ids.has(p.id) ? "Escolhido" : "Adicionar"}
              </button>
            </li>
          ))}
        </ul>
      )}
      {busca.length >= 2 && achados.termo === busca && resultados.length === 0 && (
        <p className="selecao__nada">Nenhum parceiro ativo com “{busca}” no nome.</p>
      )}

      <div>
        <h3 className="mensagens__subtitulo" id="titulo-escolhidos">
          {escolhidos.length === 1 ? "1 parceiro escolhido" : `${comoInteiro(escolhidos.length)} parceiros escolhidos`}
        </h3>
        {escolhidos.length > 0 && (
          <ul className="selecao__escolhidos" aria-labelledby="titulo-escolhidos">
            {escolhidos.map((p) => (
              <li key={p.id}>
                {p.nome}
                <button
                  className="selecao__remover"
                  type="button"
                  aria-label={`Remover ${p.nome}`}
                  onClick={() => aoMudar(escolhidos.filter((x) => x.id !== p.id))}
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ a prévia */
function Previa({ previa, gerando, enviando, plano, aoGerar }) {
  const fora = Object.entries(previa.excluidos);
  return (
    <section className="painel" aria-labelledby="titulo-previa">
      <div className="painel__cabecalho">
        <h2 className="painel__titulo" id="titulo-previa">
          Quem entra
        </h2>
        <span className="painel__nota">
          {previa.descricao} · {previa.total === 1 ? "1 parceiro" : `${comoInteiro(previa.total)} parceiros`}
        </span>
      </div>

      <div className="mensagens__corpo">
        {fora.length > 0 && (
          <p className="mensagens__fora">
            Ficaram de fora:{" "}
            {fora.map(([motivo, n]) => `${comoInteiro(n)} ${n === 1 ? "parceiro" : "parceiros"} (${motivo})`).join(", ")}
            .
          </p>
        )}

        {previa.motivo && (
          <div className="aviso" role="alert">
            <p className="aviso__titulo">{previa.motivo}</p>
          </div>
        )}

        {previa.pode_gerar && (
          <div className="mensagens__acoes">
            <button className="botao" type="button" disabled={gerando || enviando} onClick={aoGerar}>
              {enviando
                ? "Pedindo…"
                : previa.total === 1
                  ? "Gerar 1 mensagem"
                  : `Gerar ${comoInteiro(previa.total)} mensagens`}
            </button>
            <p className="mensagens__nota">
              {gerando
                ? "Há uma geração em andamento: espere ela terminar."
                : "Todas nascem pendentes: nenhuma sai sem a aprovação de um gestor."}
            </p>
          </div>
        )}
      </div>

      {previa.parceiros.length > 0 && (
        <div className="tabela-rolagem">
          <table className="tabela">
            <caption className="so-leitor">Parceiros que recebem mensagem</caption>
            <thead>
              <tr>
                <th scope="col">Parceiro</th>
                <th scope="col">Segmento</th>
                <th scope="col">Categoria</th>
                {plano && <th scope="col">Ação do plano</th>}
              </tr>
            </thead>
            <tbody>
              {previa.parceiros.map((p) => (
                <tr key={p.id}>
                  <td className="nome">{p.nome}</td>
                  <td>
                    <Segmento valor={p.segmento} />
                  </td>
                  <td>{p.categoria ?? "—"}</td>
                  {plano && <td>{p.acao}</td>}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

/* ------------------------------------------------------------------- o lote */
function Lote({ lote, assistente, aoTentarDeNovo }) {
  const gerando = lote.situacao === "EM_ANDAMENTO";
  const prontas = lote.geradas + lote.falhas.length;
  const mensagens = lote.mensagens ?? [];
  const pelaEquipe = lote.geradas - lote.pelo_modelo;

  return (
    <section className="painel" aria-labelledby="titulo-lote">
      <div className="painel__cabecalho">
        <h2 className="painel__titulo" id="titulo-lote">
          {gerando ? "Gerando mensagens" : "Última geração"}
        </h2>
        <span className="painel__nota">
          {lote.descricao} · {comoDataHora(lote.iniciado_em)}
          {lote.autor ? `, por ${lote.autor}` : ""}
        </span>
      </div>

      <div className="mensagens__corpo">
        <div className="mensagens__andamento">
          <p className="mensagens__contagem">
            {comoInteiro(prontas)} de {comoInteiro(lote.total)} prontas
            {lote.geradas > 0 &&
              ` · ${comoInteiro(lote.pelo_modelo)} pelo assistente, ${comoInteiro(pelaEquipe)} pelo modelo fixo`}
          </p>
          <progress
            className="mensagens__barra"
            max={lote.total}
            value={prontas}
            aria-label="Andamento da geração"
          />
          {gerando && prontas === 0 && assistente.disponivel && (
            <p className="mensagens__nota">
              A primeira mensagem pode levar cerca de um minuto: o assistente carrega o modelo antes de escrever.
            </p>
          )}
          {gerando && (
            <p className="mensagens__nota">A geração roda no servidor; você pode sair e voltar.</p>
          )}
        </div>

        {lote.situacao === "FALHOU" && (
          <div className="aviso" role="alert">
            <p className="aviso__titulo">A geração parou antes do fim.</p>
            <p className="aviso__ajuda">{lote.motivo}</p>
          </div>
        )}

        {lote.situacao === "CONCLUIDA" && lote.falhas.length === 0 && (
          <div className="aviso aviso--sucesso">
            <p className="aviso__titulo">
              {lote.geradas === 1 ? "1 mensagem gerada." : `${comoInteiro(lote.geradas)} mensagens geradas.`}
            </p>
            <p className="aviso__ajuda">Todas aguardam a aprovação de um gestor antes de qualquer envio.</p>
            <p className="aviso__acao">
              <Link to={`/aprovacao?lote=${lote.id}`}>Ver estas mensagens na fila de aprovação</Link>
            </p>
          </div>
        )}

        {lote.falhas.length > 0 && (
          <div className="aviso" role={gerando ? undefined : "alert"}>
            <p className="aviso__titulo">
              {lote.falhas.length === 1
                ? "1 parceiro ficou sem mensagem."
                : `${comoInteiro(lote.falhas.length)} parceiros ficaram sem mensagem.`}
            </p>
            <ul className="mensagens__falhas">
              {lote.falhas.map((f) => (
                <li key={f.parceiro_id}>
                  <span className="mensagens__falha-nome">{f.parceiro}</span>: {f.motivo}
                </li>
              ))}
            </ul>
            {!gerando && (
              <button className="botao aviso__acao" type="button" onClick={aoTentarDeNovo}>
                Tentar de novo
              </button>
            )}
          </div>
        )}
      </div>

      {mensagens.length > 0 && (
        <ol className="mensagens__lista" aria-label="Mensagens geradas">
          {mensagens.map((m) => (
            <CartaoMensagem key={m.id} mensagem={m} />
          ))}
        </ol>
      )}
    </section>
  );
}
