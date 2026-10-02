/**
 * Cadastro de um parceiro: criar, editar, desativar e excluir (UC04).
 *
 * **A validação é do servidor.** O formulário não repete as regras — nome
 * obrigatório, tamanhos, categoria existente, nome único —, porque a API já as
 * aplica e responde em português dizendo o que corrigir (regra 2.4). Repetir
 * aqui faria as duas cópias divergirem na primeira mudança, e a tela passaria a
 * aceitar o que o servidor recusa. Os atributos `maxLength` só impedem digitar
 * além do limite; `noValidate` desliga os balões do navegador, que falam outra
 * língua e somem antes de a pessoa terminar de ler.
 *
 * **Todo erro traz o caminho de volta.** Campo inválido: a mensagem embaixo
 * dele, e o foco vai para o primeiro. Nome em uso: um link para o cadastro que
 * já tem o nome (UC04-E1). Exclusão recusada: um botão para desativar, que é o
 * que resolve o problema sem apagar histórico (UC04-A4).
 *
 * **O desempenho fica ao lado do cadastro.** Segmento, faturamento e série
 * vêm da mesma consulta da lista: é o que liga o registro à análise, e o que
 * deixa ver o efeito de reclassificar ou desativar alguém.
 *
 * **E o próximo período, marcado como estimativa** (RF28, H44). O que o modelo
 * prevê fica embaixo do que foi medido, com o período de onde parte e a versão
 * que o produziu. Sem previsão, o motivo vem da API (RN09) — a tela não
 * adivinha por que não há.
 */
import { useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";

import { api } from "../api/cliente";
import AlteracoesNaoSalvas from "../componentes/AlteracoesNaoSalvas";
import { Esqueleto } from "../componentes/Carregando";
import Campo from "../componentes/Campo";
import Confirmacao from "../componentes/Confirmacao";
import EstadoVazio from "../componentes/EstadoVazio";
import { IconeVariacao } from "../componentes/Icones";
import Segmento from "../componentes/Segmento";
import SerieHistorica from "../componentes/SerieHistorica";
import { useTituloDaAba } from "../componentes/tituloDaAba";
import {
  comoData,
  comoDataHora,
  comoDinheiro,
  comoInteiro,
  comoPercentual,
  comoPeriodo,
  comoProbabilidade,
  ROTULO_ORIGEM_PREVISAO,
  ROTULO_STATUS,
  sentidoDa,
  TRACO,
} from "../formato";
import "../estilos/auditoria.css";
import "../estilos/parceiros.css";

const VAZIO = { nome: "", categoria_id: "", status: "ATIVO", contato: "" };

/* Os nomes dos campos como o usuário os lê — é o que aparece no resumo de
   erros, que não pode dizer "categoria_id" para quem preencheu "Categoria". */
const ROTULO_CAMPO = {
  nome: "Nome",
  categoria_id: "Categoria",
  status: "Status comercial",
  contato: "Contato",
};

/**
 * Uma instância por parceiro.
 *
 * As duas rotas — `/parceiros/novo` e `/parceiros/:id` — renderizam este
 * componente na mesma posição da árvore, e o React **reaproveita** a instância
 * quando só o endereço muda. Depois de cadastrar, a tela ficava com o estado do
 * formulário vazio e quebrava ao ler o parceiro que ainda não tinha carregado; o
 * mesmo acontecia ao abrir, pelo aviso de nome em uso, o cadastro de outro
 * parceiro. A chave pelo id força uma instância nova a cada troca.
 */
export default function Parceiro() {
  const { id } = useParams();
  return <Cadastro key={id ?? "novo"} id={id} />;
}

function Cadastro({ id }) {
  const novo = !id;
  const navegar = useNavigate();
  const lugar = useLocation();

  /* A lista vem com o filtro na URL. Guardar de onde a pessoa veio é o que faz
     "Voltar" devolver o mesmo recorte, e não a base inteira. Quem chega de outro
     módulo — o ranking do painel, um plano de campanha (H81) — manda também o
     nome do lugar, e a trilha volta para lá com o nome certo. */
  const lista = lugar.state?.lista ?? "/parceiros";
  const rotuloLista = lugar.state?.rotuloLista ?? "Parceiros";
  const voltarPara = lugar.state?.voltarPara ?? "Voltar para a lista";
  const origem = { lista, rotuloLista, voltarPara };

  const [parceiro, setParceiro] = useState(null);
  const [form, setForm] = useState(VAZIO);
  const [categorias, setCategorias] = useState([]);
  const [serie, setSerie] = useState(null);
  const [previsao, setPrevisao] = useState(null);
  const [campanha, setCampanha] = useState(null);
  const [situacao, setSituacao] = useState(novo ? "pronto" : "carregando");
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState(null);
  const [sucesso, setSucesso] = useState(lugar.state?.criado ? "Parceiro cadastrado." : null);
  const [confirmando, setConfirmando] = useState(null);
  /* Desativar e excluir respondem **na própria seção**, e não no topo da
     página: quem clicou está lá embaixo, e um alerta fora da vista é o mesmo
     que nenhum — a primeira versão fazia isso, e a recusa da exclusão
     acontecia sem ninguém ver. */
  const [avisoSituacao, setAvisoSituacao] = useState(null);
  useTituloDaAba(novo ? "Novo parceiro" : parceiro?.nome);
  /* A categoria que a regra da RN05 aponta pelo nome (H27). A API decide; a
     tela só oferece — usar, trocar ou ignorar é da pessoa. */
  const [sugestao, setSugestao] = useState(null);
  /* Cresce a cada alteração salva: é o que faz o histórico do cadastro buscar
     de novo e mostrar o evento que acabou de acontecer. */
  const [alteracoes, setAlteracoes] = useState(0);

  const refNome = useRef(null);
  const refCategoria = useRef(null);
  const refStatus = useRef(null);
  const refContato = useRef(null);

  useEffect(() => {
    api.get("/api/categorias").then(setCategorias).catch(() => setCategorias([]));
  }, []);

  useEffect(() => {
    if (novo) return undefined;
    let vivo = true;

    Promise.all([
      api.get(`/api/parceiros/${id}`),
      /* A série é complemento: se falhar, o cadastro continua editável. Deixar
         a falha dela derrubar a tela inteira impediria corrigir um nome por
         causa de um gráfico. */
      api.get("/api/painel/series", { parceiro_id: id }).catch(() => null),
      /* A previsão também: é complemento do cadastro, pelo mesmo motivo. */
      api.get(`/api/parceiros/${id}/previsao`).catch(() => null),
      /* E o parceiro no último plano (H81), idem. */
      api.get(`/api/parceiros/${id}/campanha`).catch(() => null),
    ])
      .then(([dados, historico, previsto, noPlano]) => {
        if (!vivo) return;
        setParceiro(dados);
        setForm(paraFormulario(dados));
        setSerie(historico);
        setPrevisao(previsto);
        setCampanha(noPlano);
        setSituacao("pronto");
      })
      .catch((e) => {
        if (!vivo) return;
        if (e.status === 404) setSituacao("inexistente");
        else setErro(e);
      });

    return () => {
      vivo = false;
    };
  }, [id, novo]);

  function mudar(campo, valor) {
    setForm((atual) => ({ ...atual, [campo]: valor }));
    /* A confirmação de "salvo" deixa de ser verdade assim que algo muda. */
    setSucesso(null);
  }

  async function salvar(evento) {
    evento.preventDefault();
    setEnviando(true);
    setErro(null);
    setSucesso(null);

    const corpo = {
      nome: form.nome,
      categoria_id: form.categoria_id === "" ? null : Number(form.categoria_id),
      status: form.status,
      contato: form.contato === "" ? null : form.contato,
    };

    try {
      if (novo) {
        const criado = await api.post("/api/parceiros", corpo);
        /* `replace`: voltar de um cadastro recém-criado não pode cair no
           formulário vazio de novo, que convidaria a criar o mesmo duas vezes. */
        navegar(`/parceiros/${criado.id}`, { replace: true, state: { ...origem, criado: true } });
        return;
      }
      const salvo = await api.patch(`/api/parceiros/${id}`, corpo);
      setParceiro((atual) => ({ ...atual, ...salvo }));
      setForm(paraFormulario(salvo));
      setSucesso("Alterações salvas.");
      setAlteracoes((n) => n + 1);
    } catch (e) {
      setErro(e);
      /* O foco vai para o primeiro campo recusado. Sem isso, quem usa teclado
         ou leitor de tela precisa procurar o erro pela página. */
      const primeiro = e.campos?.[0]?.campo;
      const refs = {
        nome: refNome,
        categoria_id: refCategoria,
        status: refStatus,
        contato: refContato,
      };
      refs[primeiro]?.current?.focus();
    } finally {
      setEnviando(false);
    }
  }

  async function mudarSituacao(ativo) {
    setEnviando(true);
    setAvisoSituacao(null);
    setConfirmando(null);
    try {
      const salvo = await api.patch(`/api/parceiros/${id}`, { ativo });
      setParceiro((atual) => ({ ...atual, ...salvo }));
      setAlteracoes((n) => n + 1);
      setAvisoSituacao({
        tipo: "sucesso",
        texto: ativo
          ? "Parceiro reativado."
          : "Parceiro desativado. O histórico dele continua no painel.",
      });
    } catch (e) {
      setAvisoSituacao({ tipo: "erro", erro: e });
    } finally {
      setEnviando(false);
    }
  }

  async function excluir() {
    setEnviando(true);
    setAvisoSituacao(null);
    setConfirmando(null);
    try {
      await api.delete(`/api/parceiros/${id}`);
      navegar(lista, { state: { aviso: `${parceiro.nome} foi excluído.` } });
    } catch (e) {
      setAvisoSituacao({ tipo: "erro", erro: e });
      setEnviando(false);
    }
  }

  if (situacao === "inexistente") {
    return (
      <EstadoVazio
        titulo="Parceiro não encontrado"
        texto="Ele pode ter sido excluído, ou o endereço está incompleto."
        acao={{ para: lista, rotulo: "Voltar para a lista" }}
      />
    );
  }

  if (situacao === "carregando") return <CadastroCarregando />;

  const erroDoCampo = Object.fromEntries((erro?.campos ?? []).map((c) => [c.campo, c]));

  /* Consulta ao sair do campo, e não a cada tecla: a sugestão depende do nome
     inteiro, e perguntar no meio da palavra só faria a oferta piscar. Com uma
     categoria já escolhida não há o que sugerir. */
  function consultarSugestao() {
    if (form.categoria_id !== "" || !form.nome.trim()) {
      setSugestao(null);
      return;
    }
    api
      .get("/api/categorias/sugestao", { nome: form.nome })
      .then((r) => setSugestao(r.categoria))
      .catch(() => setSugestao(null));
  }

  function ajudaDaCategoria() {
    if (sugestao && form.categoria_id === "") {
      return (
        <>
          Pelo nome, parece <strong>{sugestao.nome}</strong>.{" "}
          <button
            type="button"
            className="campo__acao"
            onClick={() => {
              mudar("categoria_id", String(sugestao.id));
              setSugestao(null);
            }}
          >
            Usar {sugestao.nome}
          </button>
        </>
      );
    }
    const soSugerida =
      parceiro?.origem_categoria === "INFERIDA" &&
      form.categoria_id === String(parceiro.categoria?.id ?? "");
    return soSugerida
      ? "Sugerida pelo nome, ainda não confirmada — salvar o cadastro a confirma (RN05)."
      : "Escolher uma categoria confirma a classificação (RN05).";
  }
  const detalhe = erro?.corpo?.detail;
  const existente = typeof detalhe === "object" ? detalhe?.existente : null;
  /* O que está nos campos é diferente do que está salvo? É o que decide o
     aviso de alterações não salvas (H97). Enviando, não: a criação leva à
     ficha do parceiro novo, e essa saída é a do próprio formulário. */
  const gravado = parceiro ? paraFormulario(parceiro) : VAZIO;
  const alterado = !enviando && Object.keys(VAZIO).some((campo) => form[campo] !== gravado[campo]);
  const erroSituacao = avisoSituacao?.tipo === "erro" ? avisoSituacao.erro : null;
  const recusouExclusao = erroSituacao?.status === 409 && Boolean(erroSituacao.corpo?.detail?.vinculos);

  return (
    <>
      <nav className="trilha" aria-label="Você está em">
        <Link to={lista}>{rotuloLista}</Link>
        <span aria-hidden="true">›</span>
        <span aria-current="page">{novo ? "Novo parceiro" : parceiro.nome}</span>
      </nav>

      <AlteracoesNaoSalvas quando={alterado} />

      {sucesso && (
        <div className="aviso aviso--sucesso" role="status">
          <p className="aviso__titulo">{sucesso}</p>
        </div>
      )}

      {erro && (
        <div className="aviso" role="alert">
          <p className="aviso__titulo">{erro.message}</p>
          {erro.ajuda && <p className="aviso__ajuda">{erro.ajuda}</p>}

          {erro.campos?.length > 1 && (
            <ul className="aviso__lista">
              {erro.campos.map((c) => (
                <li key={c.campo}>
                  <a href={`#campo-${c.campo}`}>{ROTULO_CAMPO[c.campo] ?? c.campo}</a>: {c.mensagem}
                </li>
              ))}
            </ul>
          )}

          {existente && (
            <p className="aviso__acao">
              <Link to={`/parceiros/${existente.id}`} state={origem}>
                Abrir o cadastro de {existente.nome}
              </Link>
            </p>
          )}

        </div>
      )}

      <div className={novo ? undefined : "painel-duplo"}>
        <section className="painel" aria-labelledby="titulo-cadastro">
          <div className="painel__cabecalho">
            <h2 className="painel__titulo" id="titulo-cadastro">
              {novo ? "Novo parceiro" : "Cadastro"}
            </h2>
            <span className="painel__nota">* obrigatório</span>
          </div>

          <form className="cadastro" onSubmit={salvar} noValidate>
            <Campo id="nome" rotulo="Nome" obrigatorio erro={erroDoCampo.nome}
              ajuda="Como o parceiro aparece nos relatórios importados.">
              <input
                id="campo-nome"
                ref={refNome}
                type="text"
                autoComplete="off"
                maxLength={160}
                value={form.nome}
                onChange={(e) => mudar("nome", e.target.value)}
                onBlur={consultarSugestao}
              />
            </Campo>

            <Campo id="categoria_id" rotulo="Categoria" erro={erroDoCampo.categoria_id}
              ajuda={ajudaDaCategoria()}>
              <select
                id="campo-categoria_id"
                ref={refCategoria}
                value={form.categoria_id}
                onChange={(e) => mudar("categoria_id", e.target.value)}
              >
                <option value="">Sem categoria</option>
                {categorias.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.nome}
                  </option>
                ))}
              </select>
            </Campo>

            <Campo id="status" rotulo="Status comercial" erro={erroDoCampo.status}
              ajuda="Prospecção é quem ainda não converteu.">
              <select
                id="campo-status"
                ref={refStatus}
                value={form.status}
                onChange={(e) => mudar("status", e.target.value)}
              >
                {Object.entries(ROTULO_STATUS).map(([valor, rotulo]) => (
                  <option key={valor} value={valor}>
                    {rotulo}
                  </option>
                ))}
              </select>
            </Campo>

            <Campo id="contato" rotulo="Contato" erro={erroDoCampo.contato}
              ajuda="E-mail ou telefone de quem responde pelo parceiro.">
              <input
                id="campo-contato"
                ref={refContato}
                type="text"
                autoComplete="off"
                maxLength={120}
                value={form.contato}
                onChange={(e) => mudar("contato", e.target.value)}
              />
            </Campo>

            <div className="cadastro__acoes">
              <button type="submit" className="botao" disabled={enviando}>
                {enviando ? "Salvando…" : novo ? "Cadastrar parceiro" : "Salvar alterações"}
              </button>
              <Link className="botao botao--secundario" to={lista}>
                {novo ? "Cancelar" : voltarPara}
              </Link>
            </div>
          </form>
        </section>

        {!novo && (
          <div className="cadastro__lateral">
            <Desempenho desempenho={parceiro.desempenho} serie={serie} />
            <Previsao previsao={previsao} />
            <NaCampanha campanha={campanha} />
          </div>
        )}
      </div>

      {!novo && serie?.pontos?.some((p) => p.faturamento !== null) && (
        <section className="painel" aria-labelledby="titulo-serie-parceiro">
          <div className="painel__cabecalho">
            <h2 className="painel__titulo" id="titulo-serie-parceiro">
              Faturamento de {parceiro.nome}
            </h2>
            <span className="painel__nota">
              {serie.pontos.length} {serie.pontos.length === 1 ? "período" : "períodos"}
            </span>
          </div>
          <SerieHistorica
            pontos={serie.pontos}
            previsao={
              /* Só a previsão de hoje: a desatualizada é de um período que já
                 aconteceu e está medido no gráfico. */
              previsao?.disponivel && !previsao.desatualizada
                ? { valor: previsao.faturamento_previsto }
                : null
            }
          />
        </section>
      )}

      {!novo && (
        <section className="painel situacao" aria-labelledby="titulo-situacao">
          <div className="painel__cabecalho">
            <h2 className="painel__titulo" id="titulo-situacao">
              Situação
            </h2>
          </div>

          <div className="situacao__corpo">
            {avisoSituacao?.tipo === "sucesso" && (
              <div className="aviso aviso--sucesso" role="status">
                <p className="aviso__titulo">{avisoSituacao.texto}</p>
              </div>
            )}

            {erroSituacao && (
              <div className="aviso" role="alert">
                <p className="aviso__titulo">{erroSituacao.message}</p>
                {erroSituacao.ajuda && <p className="aviso__ajuda">{erroSituacao.ajuda}</p>}
                {recusouExclusao && parceiro.ativo && (
                  <p className="aviso__acao">
                    <button
                      type="button"
                      className="botao botao--secundario"
                      disabled={enviando}
                      onClick={() => mudarSituacao(false)}
                    >
                      Desativar em vez de excluir
                    </button>
                  </p>
                )}
              </div>
            )}

            <p className="situacao__texto">
              <span className={`ponto-situacao${parceiro.ativo ? "" : " ponto-situacao--inativo"}`} />
              {parceiro.ativo
                ? "Ativo — entra nas consultas e nas próximas campanhas."
                : "Desativado — fica fora das próximas campanhas, e o histórico continua no painel."}
            </p>

            {confirmando ? (
              <Confirmacao
                texto={
                  confirmando === "excluir"
                    ? `Excluir ${parceiro.nome}? Isto não pode ser desfeito.`
                    : `Desativar ${parceiro.nome}? Ele deixa de entrar nas próximas campanhas.`
                }
                acao={confirmando === "excluir" ? "Excluir" : "Desativar"}
                ocupado={enviando}
                aoConfirmar={() => (confirmando === "excluir" ? excluir() : mudarSituacao(false))}
                aoCancelar={() => setConfirmando(null)}
              />
            ) : (
              <div className="situacao__acoes">
                {parceiro.ativo ? (
                  <button
                    type="button"
                    className="botao botao--secundario"
                    onClick={() => setConfirmando("desativar")}
                  >
                    Desativar
                  </button>
                ) : (
                  <button
                    type="button"
                    className="botao botao--secundario"
                    disabled={enviando}
                    onClick={() => mudarSituacao(true)}
                  >
                    Reativar
                  </button>
                )}
                {/* Separado das outras ações, e sempre com confirmação: é a
                    única que não tem volta. */}
                <button
                  type="button"
                  className="botao botao--secundario situacao__excluir"
                  onClick={() => setConfirmando("excluir")}
                >
                  Excluir parceiro
                </button>
              </div>
            )}
          </div>
        </section>
      )}

      {!novo && <HistoricoDoCadastro id={id} alteracoes={alteracoes} />}
    </>
  );
}

/**
 * O que mudou no cadastro, quando e por quem (RF50, H90).
 *
 * Sai da trilha de auditoria, mas só os eventos deste parceiro, e só a frase: a
 * trilha inteira, com a origem e os parâmetros, é do Administrador. O rótulo e o
 * resumo vêm prontos da API. É complemento do cadastro: se a consulta falhar, o
 * bloco não aparece, e o cadastro continua editável.
 */
function HistoricoDoCadastro({ id, alteracoes }) {
  const [eventos, setEventos] = useState(null);

  useEffect(() => {
    let vivo = true;
    api
      .get(`/api/parceiros/${id}/historico`)
      .then((lista) => vivo && setEventos(lista))
      .catch(() => vivo && setEventos(null));
    return () => {
      vivo = false;
    };
  }, [id, alteracoes]);

  if (!eventos) return null;

  return (
    <section className="painel" aria-labelledby="titulo-historico-cadastro">
      <div className="painel__cabecalho">
        <h2 className="painel__titulo" id="titulo-historico-cadastro">
          Histórico do cadastro
        </h2>
        <span className="painel__nota">
          {eventos.length} {eventos.length === 1 ? "registro" : "registros"}
        </span>
      </div>
      {eventos.length === 0 ? (
        <p className="previsao__nota">
          Nenhuma alteração registrada: o cadastro veio de uma importação e não foi editado.
        </p>
      ) : (
        <ol className="historico-cadastro">
          {eventos.map((evento) => (
            <li key={`${evento.acao}-${evento.ocorrido_em}`} className="historico-cadastro__evento">
              <span className="historico-cadastro__quando">{comoDataHora(evento.ocorrido_em)}</span>
              <span>
                <span className="historico-cadastro__acao">{evento.rotulo}</span>
                <span className="historico-cadastro__detalhe">
                  {evento.autor ? ` · por ${evento.autor}` : ""}
                  {evento.resumo ? ` · ${evento.resumo}` : ""}
                </span>
              </span>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

function paraFormulario(dados) {
  return {
    nome: dados.nome ?? "",
    categoria_id: dados.categoria?.id ? String(dados.categoria.id) : "",
    status: dados.status ?? "ATIVO",
    contato: dados.contato ?? "",
  };
}


/** O desempenho do período mais recente — o mesmo que a lista mostra. */
function Desempenho({ desempenho, serie }) {
  const ultimo = [...(serie?.pontos ?? [])].reverse().find((p) => p.faturamento !== null);
  const sentido = sentidoDa(desempenho.variacao_percentual);

  return (
    <section className="painel" aria-labelledby="titulo-desempenho">
      <div className="painel__cabecalho">
        <h2 className="painel__titulo" id="titulo-desempenho">
          Desempenho
        </h2>
        <span className="painel__nota">{ultimo ? comoPeriodo(ultimo.periodo) : ""}</span>
      </div>

      {desempenho.faturamento === null ? (
        <EstadoVazio
          titulo="Sem movimento no período mais recente"
          texto="O desempenho aparece aqui quando o parceiro constar num relatório importado."
        />
      ) : (
        <dl className="desempenho">
          <dt>Segmento</dt>
          <dd>
            <Segmento valor={desempenho.segmento} />
          </dd>
          <dt>Faturamento</dt>
          <dd className="num">{comoDinheiro(desempenho.faturamento)}</dd>
          <dt>Pedidos</dt>
          <dd className="num">{comoInteiro(desempenho.pedidos)}</dd>
          <dt>Ticket médio</dt>
          <dd className="num">{comoDinheiro(desempenho.ticket_medio)}</dd>
          <dt>Variação</dt>
          <dd className="num">
            {sentido === "indefinida" ? (
              TRACO
            ) : (
              <span className={`indicador__variacao indicador__variacao--${sentido}`}>
                {sentido !== "estavel" && <IconeVariacao sentido={sentido} />}
                {comoPercentual(desempenho.variacao_percentual)}
              </span>
            )}
          </dd>
        </dl>
      )}
    </section>
  );
}

/**
 * O próximo período, pelo modelo (RF28, H44).
 *
 * A etiqueta "Estimativa" no cabeçalho e a nota embaixo não são enfeite: é o
 * critério de aceite da H44. Número previsto ao lado de número medido, sem
 * marca, seria lido como medição.
 */
function Previsao({ previsao }) {
  if (!previsao) return null;

  return (
    <section className="painel" aria-labelledby="titulo-previsao">
      <div className="painel__cabecalho">
        <h2 className="painel__titulo" id="titulo-previsao">
          Próximo período
        </h2>
        <span className="etiqueta-estimativa">Estimativa</span>
      </div>

      {previsao.disponivel ? (
        <>
          <dl className="desempenho">
            <dt>Faturamento previsto</dt>
            <dd className="num">{comoDinheiro(previsao.faturamento_previsto)}</dd>
            <dt>Chance de estar em risco</dt>
            <dd className="num">{comoProbabilidade(previsao.probabilidade_queda)}</dd>
            <dt>Com dados até</dt>
            <dd>{comoData(previsao.periodo_base?.data_fim)}</dd>
            <dt>Origem</dt>
            <dd>
              {ROTULO_ORIGEM_PREVISAO[previsao.origem] ?? previsao.origem} ·{" "}
              {previsao.modelo_versao}
            </dd>
          </dl>
          <p className="previsao__nota">
            Estimativa do modelo, e não medição. A chance é a de o parceiro fechar o próximo
            período em risco — em queda seguida, pela mesma regra da segmentação (RN09).
          </p>
          {previsao.desatualizada && (
            <p className="previsao__nota previsao__nota--alerta">
              Há período importado depois desta estimativa; o próximo treino a refaz.
            </p>
          )}
        </>
      ) : (
        <EstadoVazio titulo={previsao.motivo} texto={previsao.ajuda} />
      )}
    </section>
  );
}

/**
 * O parceiro no último plano de campanha viável (H81).
 *
 * É o caminho do cadastro para a campanha: a ação que o plano reserva para o
 * parceiro, e o link para o plano. Ficar de fora também aparece — diz que a
 * verba desta rodada foi para outros. O ganho esperado é estimativa (RN10), e a
 * nota diz de qual previsão ele saiu.
 */
function NaCampanha({ campanha }) {
  if (!campanha) return null;
  const { plano } = campanha;

  return (
    <section className="painel" aria-labelledby="titulo-na-campanha">
      <div className="painel__cabecalho">
        <h2 className="painel__titulo" id="titulo-na-campanha">
          Na campanha
        </h2>
        {plano && <span className="painel__nota">plano de {comoDataHora(plano.concluida_em)}</span>}
      </div>

      {!plano ? (
        <EstadoVazio
          titulo="Nenhum plano de campanha calculado ainda"
          texto="O plano sai da tela Campanha, com o orçamento, o máximo de ações e as cotas."
          acao={{ para: "/campanha", rotulo: "Ir para a Campanha" }}
        />
      ) : (
        <>
          {campanha.no_plano ? (
            <>
              <dl className="desempenho">
                <dt>Ação</dt>
                <dd>{campanha.acao}</dd>
                <dt>Custo</dt>
                <dd className="num">{comoDinheiro(campanha.custo)}</dd>
                <dt>Ganho esperado</dt>
                <dd className="num">{comoDinheiro(campanha.uplift_esperado)}</dd>
                <dt>Aplicação</dt>
                <dd>
                  {comoData(plano.aplicacao_inicio)} a {comoData(plano.aplicacao_fim)}
                </dd>
              </dl>
              <p className="previsao__nota">
                O ganho esperado é estimativa, pela previsão {plano.modelo_versao} (RN10).
              </p>
            </>
          ) : (
            <p className="previsao__nota">
              Não entrou no último plano: a verba desta rodada foi para outros parceiros.
            </p>
          )}
          <Link className="botao botao--secundario na-campanha__plano" to={`/execucoes/${plano.execucao_id}`}>
            Abrir o plano
          </Link>
        </>
      )}
    </section>
  );
}

/** Mesmo formato do conteúdo que vem, para a página não saltar ao carregar. */
function CadastroCarregando() {
  return (
    <div role="status" aria-label="Carregando o cadastro">
      <Esqueleto altura={18} largura="30%" style={{ marginBottom: "var(--esp-16)" }} />
      <div className="painel-duplo">
        <Esqueleto altura={360} />
        <Esqueleto altura={240} />
      </div>
    </div>
  );
}
