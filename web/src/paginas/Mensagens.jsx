/**
 * Mensagens — uma mensagem de relacionamento para cada parceiro de um público.
 * Quem escreve é o modelo de linguagem (ou o texto fixo); os números são do
 * sistema; nada é enviado: toda mensagem nasce pendente e vai para a fila.
 */
import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { api } from "../api/cliente";
import { useAcompanhar, useAtraso, useCarregar } from "../api/ganchos";
import { tem, useSessao } from "../api/contextoSessao";
import CartaoMensagem from "../componentes/CartaoMensagem";
import { Ausente, Segmento } from "../componentes/Dados";
import { Carregando, ErroDaAcao, ErroDaTela, Nota, Sucesso, Vazio } from "../componentes/Estados";
import Icone from "../componentes/Icone";
import { CaixaDeTabela } from "../componentes/Lista";
import Seletor from "../componentes/Seletor";
import { useTitulo } from "../componentes/Titulo";
import { comoData, comoDataHora, comoInteiro, ORDEM_SEGMENTOS, plural, ROTULO_SEGMENTO } from "../formato";

export default function Mensagens() {
  useTitulo("Mensagens");
  const { usuario } = useSessao();
  const [busca] = useSearchParams();
  const planoDoEndereco = busca.get("plano");
  const estado = useCarregar(() => api.get("/api/mensagens/geracao"), "geracao");
  const categorias = useCarregar(() => api.get("/api/categorias"), "cat");
  const planos = useCarregar(() => api.get("/api/otimizacoes", { resultado: "VIAVEL", tamanho: 50 }), "planos");

  const [tipo, setTipo] = useState(planoDoEndereco ? "PLANO" : "FILTRO");
  const [segmento, setSegmento] = useState("");
  const [categoria, setCategoria] = useState("");
  const [plano, setPlano] = useState(planoDoEndereco ?? "");
  const [escolhidos, setEscolhidos] = useState([]);
  const [previa, setPrevia] = useState(null);
  const [erroPrevia, setErroPrevia] = useState(null);
  /* Vindo de um plano, a prévia já começa a ser pedida ao abrir (o efeito abaixo). */
  const [ocupado, setOcupado] = useState(planoDoEndereco ? "previa" : null);
  const [erroGerar, setErroGerar] = useState(null);
  const [acompanhando, setAcompanhando] = useState(null);
  const [terminados, setTerminados] = useState([]);
  const [prontas, setProntas] = useState([]);
  const [loteFinal, setLoteFinal] = useState(null);

  const emAndamento = estado.dados?.em_andamento;
  const idLote = acompanhando ?? (emAndamento && !terminados.includes(emAndamento.id) ? emAndamento.id : null);
  const lote = useAcompanhar(
    idLote,
    (x) => api.get(`/api/mensagens/lotes/${x}`),
    (l) => {
      setTerminados((t) => [...t, l.id]);
      setAcompanhando(null);
      setLoteFinal(l);
      estado.recarregar();
    },
  );
  /* As mensagens que já ficaram prontas no lote acompanhado: ajustadas na própria
     renderização quando chega uma consulta nova. */
  const [loteVisto, setLoteVisto] = useState(null);
  if (lote.atual !== loteVisto) {
    setLoteVisto(lote.atual);
    if (lote.atual?.mensagens) setProntas(lote.atual.mensagens);
  }

  /* A última geração, com as mensagens dela, quando não há nenhuma rodando. */
  const ultimoId = estado.dados?.ultimo?.id;
  const ultimo = useCarregar(() => api.get(`/api/mensagens/lotes/${ultimoId}`), `u${ultimoId}`, { ativo: Boolean(ultimoId) && !idLote && !loteFinal });

  const publico = useMemo(() => {
    if (tipo === "PLANO") return { tipo, execucao_id: plano ? Number(plano) : null };
    if (tipo === "SELECAO") return { tipo, parceiros: escolhidos.map((p) => p.id) };
    return { tipo, segmento: segmento || null, categoria_id: categoria ? Number(categoria) : null };
  }, [tipo, plano, escolhidos, segmento, categoria]);

  /* Mudar o público apaga a prévia: ela era de outro público. */
  const [publicoVisto, setPublicoVisto] = useState(publico);
  if (publico !== publicoVisto) {
    setPublicoVisto(publico);
    setPrevia(null);
    setErroPrevia(null);
    setErroGerar(null);
  }

  /* Vindo da Campanha ou de uma execução, o público já está escolhido: a prévia
     vem junto, sem mais um clique. */
  useEffect(() => {
    if (!planoDoEndereco) return undefined;
    let vivo = true;
    api
      .post("/api/mensagens/publico", { tipo: "PLANO", execucao_id: Number(planoDoEndereco) })
      .then((r) => vivo && setPrevia(r))
      .catch((e) => vivo && setErroPrevia(e))
      .finally(() => vivo && setOcupado(null));
    return () => {
      vivo = false;
    };
  }, [planoDoEndereco]);

  if (estado.carregando) return <Carregando rotulo="Carregando as mensagens" linhas={8} />;
  if (estado.erro) return <ErroDaTela erro={estado.erro} />;
  const g = estado.dados;
  const rodando = idLote !== null && (!lote.atual || lote.atual.situacao === "EM_ANDAMENTO");
  const loteExibido = rodando ? lote.atual : (loteFinal ?? ultimo.dados);
  const mensagensExibidas = rodando ? prontas : (loteExibido?.mensagens ?? []);

  async function verQuemEntra() {
    setOcupado("previa");
    setErroPrevia(null);
    try {
      setPrevia(await api.post("/api/mensagens/publico", publico));
    } catch (e) {
      setErroPrevia(e);
    } finally {
      setOcupado(null);
    }
  }

  async function gerar() {
    setOcupado("gerar");
    setErroGerar(null);
    try {
      const l = await api.post("/api/mensagens/lotes", publico);
      setProntas([]);
      setLoteFinal(null);
      setAcompanhando(l.id);
      setPrevia(null);
    } catch (e) {
      setErroGerar(e);
    } finally {
      setOcupado(null);
    }
  }

  async function refazer(id) {
    setOcupado("refazer");
    try {
      const l = await api.post(`/api/mensagens/lotes/${id}/refazer`);
      setLoteFinal(null);
      setAcompanhando(l.id);
      setTerminados((t) => t.filter((x) => x !== l.id));
    } catch (e) {
      setErroGerar(e);
    } finally {
      setOcupado(null);
    }
  }

  const planosViaveis = (planos.dados?.itens ?? []).filter((p) => p.viavel);

  return (
    <div className="pagina">
      <p className="sr-only" role="status" aria-live="polite">
        {rodando && lote.atual ? `${lote.atual.geradas} de ${lote.atual.total} mensagens prontas.` : loteFinal ? `${plural(loteFinal.geradas, "mensagem gerada", "mensagens geradas")}.` : ""}
      </p>
      <div className="redator-faixa">
        <Icone nome="assistente" />
        <p>{g.assistente.disponivel ? `Redigidas pelo ${g.assistente.modelo}, com os números conferidos antes de chegar à fila.` : "Redigidas pelo modelo fixo, com os números do sistema."}</p>
      </div>
      {!g.assistente.disponivel && (
        <Nota titulo="O assistente está indisponível.">
          {g.assistente.motivo && <p>{g.assistente.motivo}</p>}
          <p>A geração e a fila funcionam igual: cada mensagem sai do texto fixo do sistema, com os mesmos números.</p>
        </Nota>
      )}

      <section className="bloco passos" aria-labelledby="t-gerar">
        <h2 id="t-gerar" className="sr-only">
          Gerar mensagens
        </h2>
        <ol className="passos__lista">
          <li className="passo">
            <h3 className="passo__titulo">
              <span className="passo__numero" aria-hidden="true">
                1
              </span>
              Para quem
            </h3>
            <div className="segmentado" role="radiogroup" aria-label="Como escolher o público">
              {[
                ["FILTRO", "Segmento e categoria"],
                ["PLANO", "Plano de campanha"],
                ["SELECAO", "Escolher parceiros"],
              ].map(([v, r]) => (
                <label key={v} className={`segmentado__opcao${tipo === v ? " segmentado__opcao--ativa" : ""}`}>
                  <input type="radio" name="tipo-publico" value={v} checked={tipo === v} onChange={() => setTipo(v)} />
                  {r}
                </label>
              ))}
            </div>
            {tipo === "FILTRO" && (
              <div className="grupo-campos grupo-campos--duas">
                <Seletor id="m-segmento" rotulo="Segmento" valor={segmento} aoMudar={setSegmento} todos="Qualquer segmento" opcoes={ORDEM_SEGMENTOS.map((s) => [s, ROTULO_SEGMENTO[s]])} ajuda="O do período mais recente." />
                <Seletor id="m-categoria" rotulo="Categoria" valor={categoria} aoMudar={setCategoria} todos="Qualquer categoria" opcoes={(categorias.dados ?? []).map((c) => [c.id, c.nome])} ajuda="Só entra quem tem a categoria confirmada." />
              </div>
            )}
            {tipo === "PLANO" &&
              (planos.carregando ? (
                <Carregando rotulo="Carregando os planos" linhas={1} />
              ) : !planosViaveis.length ? (
                <Vazio titulo="Nenhum plano calculado ainda" compacto icone="campanha" acao={tem(usuario, "campanha") ? "Ir para a campanha" : undefined} para="/campanha">
                  O plano de campanha diz quem recebe cada ação; com ele, cada mensagem já leva a ação do parceiro.
                </Vazio>
              ) : (
                <Seletor
                  id="m-plano"
                  rotulo="Plano de campanha"
                  valor={plano}
                  aoMudar={setPlano}
                  todos="Escolha um plano"
                  ajuda="Cada parceiro do plano recebe a mensagem com a ação dele."
                  opcoes={planosViaveis.map((p) => [String(p.id), `${comoData(p.parametros.aplicacao_inicio)} a ${comoData(p.parametros.aplicacao_fim)} · ${plural(p.acoes ?? 0, "ação", "ações")} · calculado em ${comoDataHora(p.concluida_em ?? p.iniciada_em)}`])}
                />
              ))}
            {tipo === "SELECAO" && <EscolherParceiros escolhidos={escolhidos} setEscolhidos={setEscolhidos} />}
          </li>

          <li className="passo">
            <h3 className="passo__titulo">
              <span className="passo__numero" aria-hidden="true">
                2
              </span>
              Quem entra
            </h3>
            <div className="formulario__acoes">
              <button type="button" className="botao botao--secundario" onClick={verQuemEntra} disabled={ocupado !== null || (tipo === "PLANO" && !plano) || (tipo === "SELECAO" && !escolhidos.length)}>
                <Icone nome="parceiros" /> {ocupado === "previa" ? "Conferindo…" : "Ver quem entra"}
              </button>
              <span className="formulario__dica">A prévia não grava nada.</span>
            </div>
            <ErroDaAcao erro={erroPrevia} />
            {previa && <PreviaDoPublico previa={previa} comAcao={tipo === "PLANO"} />}
          </li>

          <li className="passo">
            <h3 className="passo__titulo">
              <span className="passo__numero" aria-hidden="true">
                3
              </span>
              Gerar
            </h3>
            {rodando ? (
              <p className="discreto">Há uma geração em andamento: espere ela terminar.</p>
            ) : previa?.pode_gerar ? (
              <>
                <button type="button" className="botao botao--primario botao--grande" onClick={gerar} disabled={ocupado !== null}>
                  <Icone nome="mensagens" /> {ocupado === "gerar" ? "Pedindo…" : `Gerar ${plural(previa.total, "mensagem", "mensagens")}`}
                </button>
                <p className="campo__ajuda">Todas nascem pendentes: nenhuma sai sem a aprovação de um gestor.</p>
              </>
            ) : (
              <p className="discreto">Veja quem entra antes de gerar.</p>
            )}
            <ErroDaAcao erro={erroGerar} />
          </li>
        </ol>
      </section>

      <section className="bloco" aria-labelledby="t-geracao" aria-busy={rodando}>
        <div className="bloco__cabeca">
          <h2 id="t-geracao" className="bloco__titulo">
            {rodando ? "Geração em andamento" : "Última geração"}
          </h2>
          {loteExibido && (
            <p className="bloco__sub">
              {loteExibido.descricao} · {comoDataHora(loteExibido.iniciado_em)}
              {loteExibido.autor ? `, por ${loteExibido.autor}` : ""}
            </p>
          )}
        </div>
        {rodando && lote.atual && (
          <div className="andamento" role="status">
            <p>
              <strong>
                {comoInteiro(lote.atual.geradas)} de {comoInteiro(lote.atual.total)} prontas
              </strong>{" "}
              · {comoInteiro(lote.atual.pelo_modelo)} pelo assistente, {comoInteiro(lote.atual.geradas - lote.atual.pelo_modelo)} pelo modelo fixo
            </p>
            <span className="andamento__barra" aria-hidden="true">
              <span style={{ width: `${(lote.atual.geradas / Math.max(lote.atual.total, 1)) * 100}%` }} />
            </span>
            <p className="discreto">A primeira mensagem pode levar cerca de um minuto: o assistente carrega o modelo antes de escrever. A geração roda no servidor; você pode sair e voltar.</p>
          </div>
        )}
        {!rodando && loteExibido?.situacao === "CONCLUIDA" && (
          <Sucesso>
            <p>{plural(loteExibido.geradas, "mensagem gerada", "mensagens geradas")}. Todas aguardam a aprovação de um gestor antes de qualquer envio.</p>
            {tem(usuario, "aprovacao") && (
              <Link to={`/aprovacao?lote=${loteExibido.id}`} className="link-seta">
                Ver estas mensagens na fila de aprovação <Icone nome="seta-direita" />
              </Link>
            )}
          </Sucesso>
        )}
        {!rodando && loteExibido?.situacao === "FALHOU" && <ErroDaAcao erro={{ message: "A geração parou antes do fim.", ajuda: loteExibido.motivo }} />}
        {loteExibido?.falhas?.length > 0 && (
          <div className="falhas" role="group" aria-label="Mensagens que falharam">
            <p>
              <strong>{plural(loteExibido.falhas.length, "mensagem falhou", "mensagens falharam")}:</strong>
            </p>
            <ul>
              {loteExibido.falhas.map((f) => (
                <li key={f.parceiro_id}>
                  {f.parceiro} — {f.motivo}
                </li>
              ))}
            </ul>
            {!rodando && (
              <button type="button" className="botao botao--secundario botao--pequeno" onClick={() => refazer(loteExibido.id)} disabled={ocupado !== null}>
                Tentar de novo
              </button>
            )}
          </div>
        )}
        {ultimo.carregando && <Carregando rotulo="Carregando a última geração" linhas={3} />}
        {!loteExibido && !rodando && !ultimo.carregando && (
          <Vazio titulo="Nenhuma mensagem gerada ainda." compacto icone="mensagens">
            Escolha o público e veja quem entra: as mensagens aparecem aqui, uma a uma, conforme ficam prontas.
          </Vazio>
        )}
        {mensagensExibidas.length > 0 && (
          <ol className="lista-mensagens">
            {mensagensExibidas.map((m) => (
              <li key={m.id}>
                <CartaoMensagem mensagem={m} />
              </li>
            ))}
          </ol>
        )}
      </section>
    </div>
  );
}

function EscolherParceiros({ escolhidos, setEscolhidos }) {
  const [texto, setTexto] = useState("");
  const termo = useAtraso(texto.trim(), 350);
  const achados = useCarregar(() => api.get("/api/parceiros", { busca: termo, ativo: "true", tamanho: 8 }), `b${termo}`, { ativo: termo.length >= 2 });
  return (
    <div className="escolher">
      <div className="campo">
        <label className="campo__rotulo" htmlFor="m-buscar">
          Buscar parceiro
        </label>
        <input id="m-buscar" className="entrada" type="search" value={texto} onChange={(e) => setTexto(e.target.value)} aria-describedby="m-buscar-ajuda" autoComplete="off" />
        <p className="campo__ajuda" id="m-buscar-ajuda">
          Digite ao menos duas letras do nome.
        </p>
      </div>
      {termo.length >= 2 && (
        <div className="achados" aria-live="polite">
          {achados.carregando && <p className="discreto">Buscando…</p>}
          {achados.dados && !achados.dados.itens.length && <p className="discreto">Nenhum parceiro ativo com “{termo}” no nome.</p>}
          {achados.dados?.itens.map((p) =>
            escolhidos.some((x) => x.id === p.id) ? null : (
              <button key={p.id} type="button" className="botao botao--secundario botao--pequeno" onClick={() => setEscolhidos((l) => [...l, { id: p.id, nome: p.nome }])}>
                <Icone nome="mais" /> Adicionar {p.nome}
              </button>
            ),
          )}
        </div>
      )}
      {escolhidos.length > 0 && (
        <ul className="escolhidos" aria-label="Parceiros escolhidos">
          {escolhidos.map((p) => (
            <li key={p.id} className="escolhido">
              {p.nome}
              <button type="button" className="botao-icone botao-icone--pequeno" onClick={() => setEscolhidos((l) => l.filter((x) => x.id !== p.id))} aria-label={`Remover ${p.nome}`}>
                <Icone nome="fechar" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function PreviaDoPublico({ previa, comAcao }) {
  const fora = Object.entries(previa.excluidos ?? {});
  return (
    <div className="previa-publico" role="status">
      <p className="previa-publico__descricao">
        <strong>{previa.descricao}</strong> · {plural(previa.total, "parceiro", "parceiros")}
      </p>
      {!previa.pode_gerar && previa.motivo && <Nota tipo="atencao">{previa.motivo}</Nota>}
      {previa.parceiros.length > 0 && (
        <CaixaDeTabela rotulo="Parceiros que recebem mensagem" className="caixa-tabela--alta">
          <table className="tabela tabela--compacta">
            <caption>Parceiros que recebem mensagem</caption>
            <thead>
              <tr>
                <th scope="col">Parceiro</th>
                <th scope="col">Segmento</th>
                <th scope="col">Categoria</th>
                {comAcao && <th scope="col">Ação do plano</th>}
              </tr>
            </thead>
            <tbody>
              {previa.parceiros.map((p) => (
                <tr key={p.id}>
                  <th scope="row" className="nome">
                    {p.nome}
                  </th>
                  <td>
                    <Segmento codigo={p.segmento} />
                  </td>
                  <td>{p.categoria ?? <Ausente porque="sem categoria confirmada" />}</td>
                  {comAcao && <td>{p.acao ?? <Ausente porque="sem ação" />}</td>}
                </tr>
              ))}
            </tbody>
          </table>
        </CaixaDeTabela>
      )}
      {fora.length > 0 && (
        <div className="fora">
          <p>
            <strong>Quem ficou de fora, e por quê:</strong>
          </p>
          <ul>
            {fora.map(([motivo, valor]) => (
              <li key={motivo}>
                {motivo}: {Array.isArray(valor) ? valor.map((v) => (typeof v === "object" ? (v.nome ?? v.id) : v)).join(", ") : typeof valor === "number" ? comoInteiro(valor) : String(valor)}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
