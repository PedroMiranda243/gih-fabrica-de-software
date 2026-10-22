/**
 * Cadastro do parceiro — criar, editar, desativar e excluir, com o desempenho, a
 * previsão e a campanha dele ao lado. A validação é do servidor.
 */
import { useMemo, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";

import { api, ErroDaApi } from "../api/cliente";
import { useCarregar } from "../api/ganchos";
import { tem, useSessao } from "../api/contextoSessao";
import AlteracoesNaoSalvas from "../componentes/AlteracoesNaoSalvas";
import Confirmacao from "../componentes/Confirmacao";
import { Chance, Dinheiro, Estimativa, Segmento, Variacao } from "../componentes/Dados";
import { Carregando, ErroDaAcao, ErroDaTela, Sucesso, Vazio } from "../componentes/Estados";
import { Campo, ResumoDeErros } from "../componentes/Formulario";
import { useErrosDoFormulario } from "../componentes/useErrosDoFormulario";
import Icone from "../componentes/Icone";
import { Trilha } from "../componentes/Lista";
import Serie from "../componentes/Serie";
import { useTitulo } from "../componentes/Titulo";
import { comoData, comoDataHora, comoInteiro, comoPeriodo, ROTULO_ORIGEM_PREVISAO, ROTULO_STATUS } from "../formato";

const VAZIO = { nome: "", categoria_id: "", status: "ATIVO", contato: "" };

export default function Parceiro() {
  const { id } = useParams();
  const novo = !id;
  const lugar = useLocation();
  const parceiro = useCarregar(() => api.get(`/api/parceiros/${id}`), `p${id}`, { ativo: !novo });

  if (!novo && parceiro.carregando) return <Carregando rotulo="Carregando o parceiro" linhas={8} />;
  if (!novo && parceiro.erro?.status === 404) return <NaoEncontrado />;
  if (!novo && parceiro.erro) return <ErroDaTela erro={parceiro.erro} />;

  return <Cadastro key={id ?? "novo"} id={id} dados={parceiro.dados} recarregar={parceiro.recarregar} substituir={parceiro.substituir} origem={lugar.state} />;
}

function NaoEncontrado() {
  useTitulo("Parceiro não encontrado", "Parceiros");
  return (
    <div className="pagina">
      <Trilha passos={[{ rotulo: "Parceiros", para: "/parceiros" }, { rotulo: "Não encontrado" }]} />
      <Vazio titulo="Parceiro não encontrado" acao="Voltar para a lista" para="/parceiros" icone="busca">
        Ele pode ter sido excluído, ou o endereço está incompleto.
      </Vazio>
    </div>
  );
}

function deDados(p) {
  return p ? { nome: p.nome, categoria_id: p.categoria?.id ? String(p.categoria.id) : "", status: p.status, contato: p.contato ?? "" } : VAZIO;
}

function Cadastro({ id, dados, recarregar, substituir, origem }) {
  const novo = !id;
  const { usuario } = useSessao();
  const navegar = useNavigate();
  const lugar = useLocation();
  const [valores, setValores] = useState(() => deDados(dados));
  const [base, setBase] = useState(() => deDados(dados));
  const [salvo, setSalvo] = useState(lugar.state?.criado ? "Parceiro cadastrado." : null);
  const [enviando, setEnviando] = useState(false);
  const [conflito, setConflito] = useState(null);
  const [sugestao, setSugestao] = useState(null);
  const { erros, receber, limpar, limparCampo, registrar } = useErrosDoFormulario();
  const categorias = useCarregar(() => api.get("/api/categorias"), "cat");

  const nome = dados?.nome ?? "Novo parceiro";
  useTitulo(nome, "Parceiros");

  const alterado = useMemo(() => Object.keys(base).some((k) => base[k] !== valores[k]), [base, valores]);
  const deOndeVeio = origem?.de === "painel" ? { rotulo: "Painel", para: "/" } : origem?.de === "risco" ? { rotulo: "Parceiros em risco", para: `/relatorios/risco${origem.busca ?? ""}` } : { rotulo: "Parceiros", para: `/parceiros${origem?.busca ?? ""}` };

  function mudar(campo, valor) {
    setValores((v) => ({ ...v, [campo]: valor }));
    setSalvo(null);
    limparCampo(campo);
  }

  async function sugerir() {
    const n = valores.nome.trim();
    if (n.length < 2 || n === base.nome) return;
    try {
      const r = await api.get("/api/categorias/sugestao", { nome: n });
      setSugestao(r.categoria && String(r.categoria.id) !== valores.categoria_id ? r.categoria : null);
    } catch {
      setSugestao(null);
    }
  }

  async function enviar(evento) {
    evento.preventDefault();
    limpar();
    setConflito(null);
    setEnviando(true);
    try {
      if (novo) {
        const criado = await api.post("/api/parceiros", {
          nome: valores.nome,
          categoria_id: valores.categoria_id ? Number(valores.categoria_id) : null,
          status: valores.status,
          contato: valores.contato || null,
        });
        setBase(valores);
        navegar(`/parceiros/${criado.id}`, { replace: true, state: { criado: true } });
        return;
      }
      const corpo = {};
      if (valores.nome !== base.nome) corpo.nome = valores.nome;
      const sugerida = dados?.origem_categoria && dados.origem_categoria !== "MANUAL";
      if (valores.categoria_id !== base.categoria_id || (sugerida && valores.categoria_id)) corpo.categoria_id = valores.categoria_id ? Number(valores.categoria_id) : null;
      if (valores.status !== base.status) corpo.status = valores.status;
      if (valores.contato !== base.contato) corpo.contato = valores.contato || null;
      const r = await api.patch(`/api/parceiros/${id}`, corpo);
      substituir((d) => ({ ...d, ...r }));
      setBase(valores);
      setSalvo("Alterações salvas.");
      setSugestao(null);
    } catch (e) {
      if (e instanceof ErroDaApi && e.status === 409 && e.detalhe?.existente) setConflito(e);
      else receber(e, { ordem: ["nome", "categoria_id", "status", "contato"] });
    } finally {
      setEnviando(false);
    }
  }

  const ajudaCategoria =
    dados?.origem_categoria === "SUGERIDA_IA" && valores.categoria_id === base.categoria_id && valores.categoria_id
      ? "Sugerida pelo nome, ainda não confirmada — salvar o cadastro a confirma."
      : valores.categoria_id !== base.categoria_id && valores.categoria_id
        ? "Escolher uma categoria confirma a classificação."
        : "A categoria agrupa o parceiro no painel, nos relatórios e nas cotas da campanha.";

  const formulario = (
    <section className="bloco" aria-labelledby="titulo-cadastro">
      <div className="bloco__cabeca">
        <h2 id="titulo-cadastro" className="bloco__titulo">
          {novo ? "Cadastro" : "Dados do cadastro"}
        </h2>
        {!novo && dados?.criado_em && <p className="bloco__sub">No sistema desde {comoDataHora(dados.criado_em)}</p>}
      </div>
      <form className="formulario" onSubmit={enviar} noValidate>
        {salvo && <Sucesso>{salvo}</Sucesso>}
        <ResumoDeErros erros={erros} rotulos={{ nome: "Nome", categoria_id: "Categoria", status: "Status comercial", contato: "Contato" }} />
        {conflito && (
          <div className="aviso aviso--erro" role="alert">
            <Icone nome="erro" className="aviso__icone" />
            <div className="aviso__texto">
              <p>{conflito.message}</p>
              {conflito.ajuda && <p className="aviso__ajuda">{conflito.ajuda}</p>}
              <p>
                <Link to={`/parceiros/${conflito.detalhe.existente.id}`}>Abrir o cadastro de {conflito.detalhe.existente.nome}</Link>
              </p>
            </div>
          </div>
        )}
        <Campo nome="nome" rotulo="Nome" obrigatorio erro={erros.campos.nome} ajuda="Como o parceiro aparece nos relatórios importados.">
          {(a) => <input {...a} ref={registrar("nome")} className="entrada" value={valores.nome} onChange={(e) => mudar("nome", e.target.value)} onBlur={sugerir} autoComplete="off" />}
        </Campo>
        {sugestao && (
          <div className="sugestao" role="status">
            <span>
              Pelo nome, parece <strong>{sugestao.nome}</strong>.
            </span>
            <button
              type="button"
              className="botao botao--secundario botao--pequeno"
              onClick={() => {
                mudar("categoria_id", String(sugestao.id));
                setSugestao(null);
              }}
            >
              Usar {sugestao.nome}
            </button>
          </div>
        )}
        <Campo nome="categoria_id" rotulo="Categoria" erro={erros.campos.categoria_id} ajuda={ajudaCategoria}>
          {(a) => (
            <select {...a} ref={registrar("categoria_id")} className="entrada" value={valores.categoria_id} onChange={(e) => mudar("categoria_id", e.target.value)}>
              <option value="">Sem categoria</option>
              {(categorias.dados ?? []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nome}
                </option>
              ))}
            </select>
          )}
        </Campo>
        <Campo nome="status" rotulo="Status comercial" erro={erros.campos.status} ajuda="Prospecção é quem ainda não converteu.">
          {(a) => (
            <select {...a} ref={registrar("status")} className="entrada" value={valores.status} onChange={(e) => mudar("status", e.target.value)}>
              {Object.entries(ROTULO_STATUS).map(([v, r]) => (
                <option key={v} value={v}>
                  {r}
                </option>
              ))}
            </select>
          )}
        </Campo>
        <Campo nome="contato" rotulo="Contato" erro={erros.campos.contato} ajuda="E-mail ou telefone de quem responde pelo parceiro.">
          {(a) => <input {...a} ref={registrar("contato")} className="entrada" value={valores.contato} onChange={(e) => mudar("contato", e.target.value)} autoComplete="off" />}
        </Campo>
        <div className="formulario__acoes">
          <button type="submit" className="botao botao--primario" disabled={enviando || (!novo && !alterado)}>
            {enviando ? "Salvando…" : novo ? "Cadastrar parceiro" : "Salvar alterações"}
          </button>
          {!novo && alterado && (
            <button type="button" className="botao botao--fantasma" onClick={() => (setValores(base), limpar(), setSugestao(null))}>
              Desfazer mudanças
            </button>
          )}
        </div>
      </form>
      <AlteracoesNaoSalvas quando={alterado && !enviando} />
    </section>
  );

  return (
    <div className="pagina">
      <div className="barra-acoes">
        <Trilha passos={[deOndeVeio, { rotulo: nome }]} />
        <Link to={deOndeVeio.para} className="link-seta">
          <Icone nome="seta-esquerda" /> {deOndeVeio.rotulo === "Parceiros" ? "Voltar para a lista" : `Voltar para ${deOndeVeio.rotulo === "Painel" ? "o painel" : "o relatório"}`}
        </Link>
      </div>
      {novo ? (
        <div className="coluna-estreita">{formulario}</div>
      ) : (
        <div className="cadastro-grade">
          <div className="cadastro-grade__dados">
            <Desempenho parceiro={dados} />
            <Previsao id={id} />
            <NaCampanha id={id} usuario={usuario} />
          </div>
          <div className="cadastro-grade__form">
            {formulario}
            <Situacao dados={dados} id={id} substituir={substituir} />
            <Historico id={id} versao={dados} />
            <Excluir dados={dados} id={id} substituir={substituir} recarregar={recarregar} />
          </div>
        </div>
      )}
    </div>
  );
}

function Desempenho({ parceiro }) {
  const d = parceiro.desempenho ?? {};
  const serie = useCarregar(() => api.get("/api/painel/series", { parceiro_id: parceiro.id }), `s${parceiro.id}`);
  const previsao = useCarregar(() => api.get(`/api/parceiros/${parceiro.id}/previsao`), `pv${parceiro.id}`);
  const p = previsao.dados;
  const estimativa = p?.disponivel && !p.desatualizada && p.faturamento_previsto !== null ? { valor: p.faturamento_previsto } : null;
  const semMovimento = d.faturamento === null || d.faturamento === undefined;

  return (
    <section className="bloco" aria-labelledby="titulo-desempenho">
      <div className="bloco__cabeca">
        <h2 id="titulo-desempenho" className="bloco__titulo">
          Desempenho
        </h2>
        <p className="bloco__sub">Período mais recente · medido</p>
      </div>
      {semMovimento ? (
        <Vazio titulo="Sem movimento no período mais recente" compacto icone="relogio">
          O desempenho aparece aqui quando o parceiro constar num relatório importado.
        </Vazio>
      ) : (
        <dl className="pares pares--desempenho">
          <div>
            <dt>Segmento</dt>
            <dd>
              <Segmento codigo={d.segmento} />
            </dd>
          </div>
          <div>
            <dt>Faturamento</dt>
            <dd className="valor-forte">
              <Dinheiro valor={d.faturamento} />
            </dd>
          </div>
          <div>
            <dt>Pedidos</dt>
            <dd className="valor-forte">{comoInteiro(d.pedidos)}</dd>
          </div>
          <div>
            <dt>Ticket médio</dt>
            <dd className="valor-forte">
              <Dinheiro valor={d.ticket_medio} />
            </dd>
          </div>
          <div>
            <dt>Variação</dt>
            <dd>
              <Variacao valor={d.variacao_percentual} semBase="sem variação calculável" />
            </dd>
          </div>
        </dl>
      )}
      <h3 className="bloco__subtitulo">Faturamento período a período</h3>
      {serie.carregando && <Carregando rotulo="Carregando a série do parceiro" linhas={4} altura={240} />}
      <ErroDaTela erro={serie.erro} />
      {serie.dados && (
        <>
          <Serie pontos={serie.dados.pontos} rotulo={`Faturamento de ${parceiro.nome}`} estimativa={estimativa} altura={250} />
          {p?.disponivel && p.desatualizada && <p className="bloco__nota bloco__nota--atencao">A estimativa ficou fora do gráfico: há período importado depois dela, e o próximo treino a refaz.</p>}
        </>
      )}
    </section>
  );
}

function Previsao({ id }) {
  const previsao = useCarregar(() => api.get(`/api/parceiros/${id}/previsao`), `pv${id}`);
  const p = previsao.dados;
  return (
    <section className="bloco bloco--estimativa" aria-labelledby="titulo-previsao">
      <div className="bloco__cabeca bloco__cabeca--etiqueta">
        <h2 id="titulo-previsao" className="bloco__titulo">
          Próximo período
        </h2>
        <Estimativa />
      </div>
      {previsao.carregando && <Carregando rotulo="Carregando a previsão" linhas={3} />}
      <ErroDaTela erro={previsao.erro} />
      {p && !p.disponivel && (
        <Vazio titulo={p.motivo ?? "Sem previsão para este parceiro."} compacto icone="modelo">
          {p.ajuda}
        </Vazio>
      )}
      {p && p.disponivel && (
        <>
          <dl className="pares">
            <div>
              <dt>Faturamento previsto</dt>
              <dd className="valor-forte">
                <Dinheiro valor={p.faturamento_previsto} />
              </dd>
            </div>
            <div>
              <dt>Chance de estar em risco</dt>
              <dd className="valor-forte">
                <Chance valor={p.probabilidade_queda} />
              </dd>
            </div>
            <div>
              <dt>Com dados até</dt>
              <dd>{comoPeriodo(p.periodo_base)}</dd>
            </div>
            <div>
              <dt>Origem</dt>
              <dd>
                {ROTULO_ORIGEM_PREVISAO[p.origem] ?? p.origem} · {p.modelo_versao}
              </dd>
            </div>
          </dl>
          {p.desatualizada && <p className="bloco__nota bloco__nota--atencao">Há período importado depois desta previsão; o próximo treino a refaz.</p>}
        </>
      )}
      <Link to="/ajuda#estimativa" className="link-seta bloco__rodape">
        O que é estimativa? <Icone nome="seta-direita" />
      </Link>
    </section>
  );
}

function NaCampanha({ id, usuario }) {
  const campanha = useCarregar(() => api.get(`/api/parceiros/${id}/campanha`), `c${id}`);
  const c = campanha.dados;
  return (
    <section className="bloco" aria-labelledby="titulo-na-campanha">
      <div className="bloco__cabeca">
        <h2 id="titulo-na-campanha" className="bloco__titulo">
          Na campanha
        </h2>
        {c?.plano && (
          <p className="bloco__sub">
            Último plano: aplicação de {comoData(c.plano.aplicacao_inicio)} a {comoData(c.plano.aplicacao_fim)}
          </p>
        )}
      </div>
      {campanha.carregando && <Carregando rotulo="Carregando a campanha" linhas={2} />}
      <ErroDaTela erro={campanha.erro} />
      {c && !c.plano && (
        <Vazio titulo="Nenhum plano de campanha calculado ainda" compacto icone="campanha" acao={tem(usuario, "campanha") ? "Ir para a Campanha" : undefined} para="/campanha">
          O plano sai da tela Campanha, com o orçamento, o máximo de ações e as cotas.
        </Vazio>
      )}
      {c && c.plano && !c.no_plano && <p className="discreto">Não entrou no último plano: a verba desta rodada foi para outros parceiros.</p>}
      {c && c.plano && c.no_plano && (
        <dl className="pares">
          <div>
            <dt>Ação</dt>
            <dd>{c.acao}</dd>
          </div>
          <div>
            <dt>Custo</dt>
            <dd>
              <Dinheiro valor={c.custo} />
            </dd>
          </div>
          <div>
            <dt>
              Ganho esperado <Estimativa />
            </dt>
            <dd className="valor-forte">
              <Dinheiro valor={c.uplift_esperado} />
            </dd>
          </div>
        </dl>
      )}
      {c?.plano && tem(usuario, "execucao") && (
        <Link to={`/execucoes/${c.plano.execucao_id}`} className="link-seta bloco__rodape">
          Abrir o plano <Icone nome="seta-direita" />
        </Link>
      )}
    </section>
  );
}

function Situacao({ dados, id, substituir }) {
  const [confirmando, setConfirmando] = useState(false);
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState(null);
  const [aviso, setAviso] = useState(null);

  async function mudar(ativo) {
    setOcupado(true);
    setErro(null);
    try {
      const r = await api.patch(`/api/parceiros/${id}`, { ativo });
      substituir((d) => ({ ...d, ...r }));
      setAviso(ativo ? "Parceiro reativado." : "Parceiro desativado.");
      setConfirmando(false);
    } catch (e) {
      setErro(e);
    } finally {
      setOcupado(false);
    }
  }

  return (
    <section className="bloco" aria-labelledby="titulo-situacao">
      <div className="bloco__cabeca">
        <h2 id="titulo-situacao" className="bloco__titulo">
          Situação
        </h2>
      </div>
      <p className={`situacao${dados.ativo ? "" : " situacao--inativa"}`}>
        <strong>{dados.ativo ? "Ativo" : "Desativado"}</strong> — {dados.ativo ? "entra nas consultas e nas próximas campanhas." : "fica fora das próximas campanhas, e o histórico continua no painel."}
      </p>
      {aviso && <Sucesso>{aviso}</Sucesso>}
      <ErroDaAcao erro={erro} />
      {confirmando ? (
        <Confirmacao texto={`Desativar ${dados.nome}? Ele deixa de entrar nas próximas campanhas.`} acao="Desativar" perigo ocupado={ocupado} aoConfirmar={() => mudar(false)} aoCancelar={() => setConfirmando(false)} />
      ) : (
        <div className="formulario__acoes">
          {dados.ativo ? (
            <button type="button" className="botao botao--secundario" onClick={() => (setAviso(null), setConfirmando(true))}>
              Desativar
            </button>
          ) : (
            <button type="button" className="botao botao--secundario" onClick={() => mudar(true)} disabled={ocupado}>
              {ocupado ? "Reativando…" : "Reativar"}
            </button>
          )}
        </div>
      )}
    </section>
  );
}

function Historico({ id, versao }) {
  const historico = useCarregar(() => api.get(`/api/parceiros/${id}/historico`), `h${id}-${versao?.nome}-${versao?.ativo}-${versao?.status}-${versao?.categoria?.id}`);
  if (historico.erro) return null;
  const h = historico.dados;
  return (
    <section className="bloco" aria-labelledby="titulo-historico-cadastro">
      <div className="bloco__cabeca">
        <h2 id="titulo-historico-cadastro" className="bloco__titulo">
          Histórico do cadastro
        </h2>
      </div>
      {historico.carregando && <Carregando rotulo="Carregando o histórico" linhas={2} />}
      {h && !h.length && <p className="discreto">Nenhuma alteração registrada: o cadastro veio de uma importação e não foi editado.</p>}
      {h && h.length > 0 && (
        <ol className="linha-do-tempo">
          {h.map((e, i) => (
            <li key={i}>
              <p className="linha-do-tempo__o-que">
                <strong>{e.rotulo}</strong> {e.resumo}
              </p>
              <p className="linha-do-tempo__quando">
                {comoDataHora(e.ocorrido_em)}
                {e.autor ? ` · ${e.autor}` : ""}
              </p>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

function Excluir({ dados, id, substituir }) {
  const navegar = useNavigate();
  const [confirmando, setConfirmando] = useState(false);
  const [ocupado, setOcupado] = useState(false);
  const [recusa, setRecusa] = useState(null);
  const [desativado, setDesativado] = useState(false);

  async function excluir() {
    setOcupado(true);
    try {
      await api.delete(`/api/parceiros/${id}`);
      navegar("/parceiros", { replace: true, state: { aviso: `${dados.nome} foi excluído.` } });
    } catch (e) {
      setRecusa(e);
      setConfirmando(false);
    } finally {
      setOcupado(false);
    }
  }

  async function desativar() {
    setOcupado(true);
    try {
      const r = await api.patch(`/api/parceiros/${id}`, { ativo: false });
      substituir((d) => ({ ...d, ...r }));
      setDesativado(true);
      setRecusa(null);
    } catch (e) {
      setRecusa(e);
    } finally {
      setOcupado(false);
    }
  }

  const v = recusa?.detalhe?.vinculos;
  const ROTULOS = { metricas: "métricas", segmentos: "segmentos", previsoes: "previsões", itens_de_plano: "itens de plano", mensagens: "mensagens", usuarios: "usuários" };

  return (
    <section className="bloco bloco--perigo" aria-labelledby="titulo-excluir">
      <div className="bloco__cabeca">
        <h2 id="titulo-excluir" className="bloco__titulo">
          Excluir parceiro
        </h2>
        <p className="bloco__sub">Só quem não tem histórico pode ser excluído.</p>
      </div>
      {desativado && <Sucesso>Parceiro desativado: fica fora das próximas campanhas, e o histórico continua no painel.</Sucesso>}
      {recusa && (
        <div className="aviso aviso--erro" role="alert">
          <Icone nome="erro" className="aviso__icone" />
          <div className="aviso__texto">
            <p>{recusa.message}</p>
            {recusa.ajuda && <p className="aviso__ajuda">{recusa.ajuda}</p>}
            {v && (
              <ul className="aviso__lista">
                {Object.entries(v)
                  .filter(([, n]) => n > 0)
                  .map(([k, n]) => (
                    <li key={k}>
                      {comoInteiro(n)} {ROTULOS[k] ?? k}
                    </li>
                  ))}
              </ul>
            )}
            {v && dados.ativo && (
              <p>
                <button type="button" className="botao botao--secundario botao--pequeno" onClick={desativar} disabled={ocupado}>
                  {ocupado ? "Desativando…" : "Desativar em vez de excluir"}
                </button>
              </p>
            )}
          </div>
        </div>
      )}
      {confirmando ? (
        <Confirmacao texto={`Excluir ${dados.nome}? Isto não pode ser desfeito.`} acao="Excluir" perigo ocupado={ocupado} aoConfirmar={excluir} aoCancelar={() => setConfirmando(false)} />
      ) : (
        <button type="button" className="botao botao--secundario botao--perigo-texto" onClick={() => (setRecusa(null), setConfirmando(true))}>
          <Icone nome="lixo" /> Excluir parceiro
        </button>
      )}
    </section>
  );
}

