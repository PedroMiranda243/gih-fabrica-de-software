/**
 * Campanha — quanto há para gastar e com que restrições; o otimizador devolve o
 * plano. Quem pode o quê vem do estado (`pode_executar`, `pode_editar_catalogo`).
 * A tela só traduz o que a pessoa digita (% → fração, "12.000,50" → "12000.50").
 */
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { api, ErroDaApi } from "../api/cliente";
import { useAcompanhar, useCarregar } from "../api/ganchos";
import AlteracoesNaoSalvas from "../componentes/AlteracoesNaoSalvas";
import Confirmacao from "../componentes/Confirmacao";
import { Carregando, ErroDaAcao, ErroDaTela, Nota, Sucesso, Vazio } from "../componentes/Estados";
import { Campo, ResumoDeErros, useErrosDoFormulario } from "../componentes/Formulario";
import Icone from "../componentes/Icone";
import { CaixaDeTabela } from "../componentes/Lista";
import PlanoDeCampanha from "../componentes/PlanoDeCampanha";
import { useTitulo } from "../componentes/Titulo";
import { comoDinheiro, comoFracao, comoInteiro, comoPeriodo, deFracao, lerReais, paraCampoDeReais, paraFracao, plural, ROTULO_MODO_CURTO } from "../formato";

function diaSeguinte(iso, dias) {
  const [a, m, d] = iso.split("-").map(Number);
  const data = new Date(Date.UTC(a, m - 1, d + dias));
  return data.toISOString().slice(0, 10);
}

const EXCLUIDOS = {
  historico_curto: ["com histórico curto", "com histórico curto"],
  fora_do_periodo: ["sem dado no período das previsões", "sem dado no período das previsões"],
  sem_previsao: ["sem previsão na versão em uso", "sem previsão na versão em uso"],
  inativos: ["desativado", "desativados"],
  em_prospeccao: ["em prospecção", "em prospecção"],
};

export default function Campanha() {
  useTitulo("Campanha");
  const estado = useCarregar(() => api.get("/api/campanha"), "campanha");
  const [acompanhando, setAcompanhando] = useState(null);
  const [terminados, setTerminados] = useState([]);
  const [resultado, setResultado] = useState(null);

  const emAndamento = estado.dados?.em_andamento;
  const id = acompanhando ?? (emAndamento && !terminados.includes(emAndamento.id) ? emAndamento.id : null);
  const calculo = useAcompanhar(id, (x) => api.get(`/api/otimizacoes/${x}`), (e) => {
    setResultado(e);
    setTerminados((l) => [...l, e.id]);
    setAcompanhando(null);
    estado.recarregar();
  });

  if (estado.carregando) return <Carregando rotulo="Carregando a campanha" linhas={10} />;
  if (estado.erro) return <ErroDaTela erro={estado.erro} />;
  const c = estado.dados;
  const calculando = id !== null && (!calculo.atual || calculo.atual.situacao === "EM_ANDAMENTO");
  const plano = resultado ?? c.ultima;

  if (!c.modelo_versao) {
    return (
      <div className="pagina">
        <Vazio titulo={c.motivo_bloqueio ?? "Ainda não há modelo treinado."} icone="modelo" acao="Ir para o Modelo" para="/modelo">
          O plano parte da previsão de cada parceiro.
        </Vazio>
        <Catalogo estado={c} aoMudar={estado.recarregar} />
      </div>
    );
  }

  const fora = Object.entries(c.excluidos ?? {}).filter(([, n]) => n > 0);

  return (
    <div className="pagina">
      <p className="sr-only" role="status" aria-live="polite">
        {calculando ? "Calculando o plano." : resultado ? anuncio(resultado) : ""}
      </p>
      <div className="campanha-topo">
        <p className="campanha-topo__previsoes">
          Previsões da <strong>{c.modelo_versao}</strong>, com dados até {comoPeriodo(c.periodo_base)}
        </p>
        <p className="campanha-topo__quem">
          <strong className="numero-destaque">{comoInteiro(c.elegiveis)}</strong> parceiros podem receber ação.
          {fora.length > 0 && <> Ficam fora {fora.map(([k, n], i) => `${i ? (i === fora.length - 1 ? " e " : ", ") : ""}${comoInteiro(n)} ${EXCLUIDOS[k]?.[n === 1 ? 0 : 1] ?? k}`).join("")}.</>}
        </p>
      </div>

      <div className="campanha-grade">
        <Restricoes estado={c} calculando={calculando} aoCalcular={(idNovo) => (setResultado(null), setAcompanhando(idNovo))} />

        <section className="bloco bloco--plano" aria-labelledby="t-plano" aria-busy={calculando}>
          <div className="bloco__cabeca bloco__cabeca--linha">
            <h2 id="t-plano" className="bloco__titulo">
              {resultado ? "O plano recomendado" : "O último plano"}
            </h2>
            <Link to="/execucoes" className="link-seta">
              Ver as execuções anteriores <Icone nome="seta-direita" />
            </Link>
          </div>
          {calculando && (
            <div className="andamento" role="status">
              <span className="andamento__barra andamento__barra--indeterminada" aria-hidden="true" />
              <p>
                <strong>Calculando…</strong> O otimizador está montando o plano no servidor. Você pode sair desta tela: ao voltar, ela reencontra o cálculo.
              </p>
            </div>
          )}
          {!calculando && resultado && (
            <div className={`resultado resultado--${resultado.situacao === "FALHOU" ? "falha" : resultado.viavel ? "ok" : "inviavel"}`}>
              <p className="resultado__frase">{anuncio(resultado)}</p>
            </div>
          )}
          {!calculando && plano && <PlanoDeCampanha execucao={plano} novo={Boolean(resultado)} />}
          {!calculando && !plano && (
            <Vazio titulo="Nenhum plano de campanha calculado ainda" compacto icone="campanha">
              Preencha as restrições e calcule: o plano diz quais parceiros recebem qual ação.
            </Vazio>
          )}
        </section>
      </div>

      <Catalogo estado={c} aoMudar={estado.recarregar} />
    </div>
  );
}

function anuncio(e) {
  if (e.situacao === "FALHOU") return `O cálculo falhou.${e.motivo ? ` ${e.motivo}` : ""}`;
  if (e.viavel === false) return `Sem solução viável.${e.motivo ? ` ${e.motivo}` : ""}`;
  return `Plano calculado: ${plural(e.acoes ?? 0, "ação", "ações")}, ganho esperado de ${comoDinheiro(e.uplift_total)}.`;
}

let proximaCota = 1;

function Restricoes({ estado, calculando, aoCalcular }) {
  const base = estado.periodo_base;
  const [valores, setValores] = useState(() => ({
    orcamento: "",
    maximo_acoes: "",
    cota_cauda_longa: "",
    aplicacao_inicio: base ? diaSeguinte(base.data_fim, 1) : "",
    aplicacao_fim: base ? diaSeguinte(base.data_fim, 7) : "",
    modo: "",
  }));
  const [cotas, setCotas] = useState([]);
  const [erroCotas, setErroCotas] = useState(null);
  const [confirmando, setConfirmando] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [recusa, setRecusa] = useState(null);
  const { erros, receber, limpar, limparCampo, registrar } = useErrosDoFormulario();

  function mudar(campo, valor) {
    setValores((v) => ({ ...v, [campo]: valor }));
    limparCampo(campo);
  }

  function conferirCotas() {
    const vistas = new Set();
    for (const c of cotas) {
      if (!c.categoria_id) continue;
      if (vistas.has(c.categoria_id)) return false;
      vistas.add(c.categoria_id);
      const min = Number(String(c.minimo).replace(",", "."));
      const max = Number(String(c.maximo).replace(",", "."));
      if (c.minimo !== "" && c.maximo !== "" && !Number.isNaN(min) && !Number.isNaN(max) && min > max) return false;
    }
    return true;
  }

  function pedir(evento) {
    evento.preventDefault();
    setRecusa(null);
    limpar();
    if (!conferirCotas()) {
      setErroCotas("Confira as cotas: o mínimo não pode passar do máximo, e cada categoria entra uma vez.");
      return;
    }
    setErroCotas(null);
    setConfirmando(true);
  }

  async function calcular() {
    setEnviando(true);
    try {
      const corpo = {
        orcamento: lerReais(valores.orcamento),
        maximo_acoes: valores.maximo_acoes === "" ? null : Number.isNaN(Number(valores.maximo_acoes)) ? valores.maximo_acoes : Number(valores.maximo_acoes),
        cota_cauda_longa: paraFracao(valores.cota_cauda_longa),
        cotas_categoria: cotas.filter((c) => c.categoria_id).map((c) => ({ categoria_id: Number(c.categoria_id), minimo: paraFracao(c.minimo), maximo: paraFracao(c.maximo) })),
        aplicacao_inicio: valores.aplicacao_inicio || null,
        aplicacao_fim: valores.aplicacao_fim || null,
        modo: valores.modo || null,
      };
      const e = await api.post("/api/otimizacoes", corpo);
      setConfirmando(false);
      aoCalcular(e.id);
    } catch (e) {
      setConfirmando(false);
      if (e instanceof ErroDaApi && e.status === 409) {
        setRecusa(e);
        if (e.detalhe?.em_andamento) aoCalcular(e.detalhe.em_andamento);
      } else if (e instanceof ErroDaApi && e.campos) {
        receber(e, { ordem: ["orcamento", "maximo_acoes", "cota_cauda_longa", "aplicacao_inicio", "aplicacao_fim", "modo"] });
      } else {
        setRecusa(e);
      }
    } finally {
      setEnviando(false);
    }
  }

  const categoriasUsadas = cotas.map((c) => c.categoria_id);
  const modoAuto = ROTULO_MODO_CURTO[estado.modo_automatico] ?? estado.modo_automatico;
  const modoEscolhido = estado.modos.find((m) => m.modo === valores.modo);

  return (
    <section className="bloco bloco--restricoes" aria-labelledby="t-restricoes">
      <div className="bloco__cabeca">
        <h2 id="t-restricoes" className="bloco__titulo">
          Restrições
        </h2>
        <p className="bloco__sub">O que o otimizador precisa respeitar. Se é viável, quem responde é o servidor.</p>
      </div>
      <form className="formulario" onSubmit={pedir} noValidate>
        <ResumoDeErros erros={erros} rotulos={{ orcamento: "Orçamento", maximo_acoes: "Máximo de ações", cota_cauda_longa: "Cota da cauda longa", aplicacao_inicio: "Início da aplicação", aplicacao_fim: "Fim da aplicação", modo: "Modo de execução" }} />
        <ErroDaAcao erro={recusa} />
        <div className="grupo-campos grupo-campos--duas">
          <Campo nome="orcamento" rotulo="Orçamento" obrigatorio erro={erros.campos.orcamento} ajuda="Em reais, com vírgula nos centavos (ex.: 12.000,00).">
            {(a) => (
              <div className="entrada-com-prefixo">
                <span aria-hidden="true">R$</span>
                <input {...a} ref={registrar("orcamento")} className="entrada" inputMode="decimal" value={valores.orcamento} onChange={(e) => mudar("orcamento", e.target.value)} onBlur={() => valores.orcamento && !Number.isNaN(Number(lerReais(valores.orcamento))) && mudar("orcamento", paraCampoDeReais(lerReais(valores.orcamento)))} />
              </div>
            )}
          </Campo>
          <Campo nome="maximo_acoes" rotulo="Máximo de ações" obrigatorio erro={erros.campos.maximo_acoes} ajuda="Quantas a equipe consegue executar no período.">
            {(a) => <input {...a} ref={registrar("maximo_acoes")} className="entrada" inputMode="numeric" value={valores.maximo_acoes} onChange={(e) => mudar("maximo_acoes", e.target.value)} />}
          </Campo>
        </div>
        <Campo nome="cota_cauda_longa" rotulo="Cota mínima da cauda longa (%)" erro={erros.campos.cota_cauda_longa} ajuda={`Das ações, quantas vão para quem está fora do Top ${estado.top_n} (ex.: 30). Em branco, sem cota.`}>
          {(a) => <input {...a} ref={registrar("cota_cauda_longa")} className="entrada entrada--numero" inputMode="decimal" value={valores.cota_cauda_longa} onChange={(e) => mudar("cota_cauda_longa", e.target.value)} />}
        </Campo>
        <div className="grupo-campos grupo-campos--duas">
          <Campo nome="aplicacao_inicio" rotulo="Início da aplicação" obrigatorio erro={erros.campos.aplicacao_inicio}>
            {(a) => <input {...a} ref={registrar("aplicacao_inicio")} type="date" className="entrada" value={valores.aplicacao_inicio} onChange={(e) => mudar("aplicacao_inicio", e.target.value)} />}
          </Campo>
          <Campo nome="aplicacao_fim" rotulo="Fim da aplicação" obrigatorio erro={erros.campos.aplicacao_fim}>
            {(a) => <input {...a} ref={registrar("aplicacao_fim")} type="date" className="entrada" value={valores.aplicacao_fim} onChange={(e) => mudar("aplicacao_fim", e.target.value)} />}
          </Campo>
        </div>
        <p className="campo__ajuda">O período seguinte ao das previsões, já sugerido.</p>

        <fieldset className="grupo-campos cotas">
          <legend className="grupo-campos__legenda">Cotas por categoria</legend>
          <p className="campo__ajuda">
            Em % do máximo de ações. Só conta a categoria confirmada{estado.sem_categoria > 0 ? `: ${plural(estado.sem_categoria, "elegível sem categoria confirmada recebe", "elegíveis sem categoria confirmada recebem")} ação, mas não entra${estado.sem_categoria === 1 ? "" : "m"} em cota` : ""}.
          </p>
          {cotas.map((cota, i) => (
            <div key={cota.id} className="cota" role="group" aria-label={`Cota ${i + 1}`}>
              <div className="campo">
                <label className="campo__rotulo" htmlFor={`cota-cat-${cota.id}`}>
                  Categoria
                </label>
                <select id={`cota-cat-${cota.id}`} className="entrada" value={cota.categoria_id} onChange={(e) => (setCotas((l) => l.map((x) => (x.id === cota.id ? { ...x, categoria_id: e.target.value } : x))), setErroCotas(null))}>
                  <option value="">Escolha a categoria</option>
                  {estado.categorias.map((cat) => (
                    <option key={cat.id} value={cat.id} disabled={categoriasUsadas.includes(String(cat.id)) && String(cat.id) !== cota.categoria_id}>
                      {cat.nome} · {comoInteiro(cat.elegiveis)} elegíveis
                    </option>
                  ))}
                </select>
              </div>
              <div className="campo">
                <label className="campo__rotulo" htmlFor={`cota-min-${cota.id}`}>
                  mín. %
                </label>
                <input id={`cota-min-${cota.id}`} className="entrada" inputMode="decimal" value={cota.minimo} onChange={(e) => (setCotas((l) => l.map((x) => (x.id === cota.id ? { ...x, minimo: e.target.value } : x))), setErroCotas(null))} />
              </div>
              <div className="campo">
                <label className="campo__rotulo" htmlFor={`cota-max-${cota.id}`}>
                  máx. %
                </label>
                <input id={`cota-max-${cota.id}`} className="entrada" inputMode="decimal" value={cota.maximo} onChange={(e) => (setCotas((l) => l.map((x) => (x.id === cota.id ? { ...x, maximo: e.target.value } : x))), setErroCotas(null))} />
              </div>
              <button type="button" className="botao botao--fantasma botao--pequeno cota__remover" onClick={() => setCotas((l) => l.filter((x) => x.id !== cota.id))} aria-label={`Remover a cota ${i + 1}`}>
                Remover
              </button>
            </div>
          ))}
          {erroCotas && (
            <p className="campo__erro" role="alert">
              <Icone nome="erro" />
              <span>{erroCotas}</span>
            </p>
          )}
          <button type="button" className="botao botao--secundario botao--pequeno cotas__adicionar" onClick={() => setCotas((l) => [...l, { id: proximaCota++, categoria_id: "", minimo: "", maximo: "" }])}>
            <Icone nome="mais" /> Adicionar cota de categoria
          </button>
        </fieldset>

        <Campo nome="modo" rotulo="Modo de execução" erro={erros.campos.modo} ajuda={`Sem escolha, roda na GPU, se houver, e senão no CPU paralelo. Nesta instalação: ${modoAuto}.`}>
          {(a) => (
            <select {...a} ref={registrar("modo")} className="entrada" value={valores.modo} onChange={(e) => mudar("modo", e.target.value)}>
              <option value="">Automático</option>
              {estado.modos.map((m) => (
                <option key={m.modo} value={m.modo} disabled={!m.disponivel}>
                  {ROTULO_MODO_CURTO[m.modo] ?? m.modo}
                  {m.disponivel ? "" : " — indisponível"}
                </option>
              ))}
            </select>
          )}
        </Campo>
        {estado.modos.some((m) => !m.disponivel) && (
          <ul className="modos-indisponiveis">
            {estado.modos
              .filter((m) => !m.disponivel)
              .map((m) => (
                <li key={m.modo}>
                  <strong>{ROTULO_MODO_CURTO[m.modo]}</strong>: {m.motivo}
                </li>
              ))}
          </ul>
        )}
        {modoEscolhido && !modoEscolhido.disponivel && <Nota tipo="atencao">{modoEscolhido.motivo}</Nota>}

        {confirmando ? (
          <Confirmacao
            texto={`Calcular o plano com orçamento de ${comoDinheiro(lerReais(valores.orcamento)) === "—" ? valores.orcamento || "(vazio)" : comoDinheiro(lerReais(valores.orcamento))} e até ${valores.maximo_acoes || "?"} ações?`}
            detalhe="O cálculo roda em segundo plano; o plano aparece ao lado quando ele terminar."
            acao="Calcular plano"
            ocupado={enviando}
            aoConfirmar={calcular}
            aoCancelar={() => setConfirmando(false)}
          />
        ) : estado.pode_executar ? (
          <div className="formulario__acoes">
            <button type="submit" className="botao botao--primario botao--grande" disabled={calculando}>
              <Icone nome="raio" /> {calculando ? "Calculando…" : "Calcular plano"}
            </button>
          </div>
        ) : (
          <Nota titulo="Calcular o plano não é do seu perfil">{estado.motivo_bloqueio}</Nota>
        )}
      </form>
    </section>
  );
}

function Catalogo({ estado, aoMudar }) {
  const [editando, setEditando] = useState(null);
  const [novo, setNovo] = useState(false);
  const [aviso, setAviso] = useState(null);
  const podeEditar = estado.pode_editar_catalogo;

  return (
    <section className="bloco" aria-labelledby="t-catalogo">
      <div className="bloco__cabeca bloco__cabeca--linha">
        <div>
          <h2 id="t-catalogo" className="bloco__titulo">
            Catálogo de ações
          </h2>
          <p className="bloco__sub">Ações que o otimizador pode distribuir. Ganho = previsto × crescimento + previsto × risco × retenção.</p>
        </div>
        {podeEditar && !novo && editando === null && (
          <button type="button" className="botao botao--secundario" onClick={() => (setAviso(null), setNovo(true))}>
            <Icone nome="mais" /> Nova ação
          </button>
        )}
      </div>
      {aviso && <Sucesso>{aviso}</Sucesso>}
      <CaixaDeTabela rotulo="Catálogo de ações">
        <table className="tabela tabela--catalogo">
          <caption className="sr-only">Catálogo de ações comerciais: custo, efeitos e situação</caption>
          <thead>
            <tr>
              <th scope="col">Ação</th>
              <th scope="col" className="num">
                Custo
              </th>
              <th scope="col" className="num">
                Crescimento
              </th>
              <th scope="col" className="num">
                Retenção
              </th>
              <th scope="col">Situação</th>
              {podeEditar && (
                <th scope="col">
                  <span className="sr-only">Editar</span>
                </th>
              )}
            </tr>
          </thead>
          <tbody>
            {estado.acoes.map((a) =>
              editando === a.id ? (
                <LinhaEditavel key={a.id} acao={a} aoCancelar={() => setEditando(null)} aoSalvar={(nome) => (setEditando(null), setAviso(`Ação ${nome} salva.`), aoMudar())} />
              ) : (
                <tr key={a.id} className={a.ativa ? undefined : "linha--inativa"}>
                  <th scope="row" className="nome">
                    {a.nome}
                  </th>
                  <td className="num">{comoDinheiro(a.custo_unitario)}</td>
                  <td className="num">{comoFracao(a.efeito_crescimento, 0)}</td>
                  <td className="num">{comoFracao(a.efeito_retencao, 0)}</td>
                  <td>{a.ativa ? "Ativa" : "Inativa"}</td>
                  {podeEditar && (
                    <td className="celula-acao">
                      <button type="button" className="botao botao--fantasma botao--pequeno" onClick={() => (setAviso(null), setNovo(false), setEditando(a.id))} disabled={editando !== null || novo} aria-label={`Editar ${a.nome}`}>
                        <Icone nome="lapis" /> Editar
                      </button>
                    </td>
                  )}
                </tr>
              ),
            )}
            {novo && <LinhaEditavel acao={null} aoCancelar={() => setNovo(false)} aoSalvar={(nome) => (setNovo(false), setAviso(`Ação ${nome} criada.`), aoMudar())} />}
          </tbody>
        </table>
      </CaixaDeTabela>
    </section>
  );
}

function LinhaEditavel({ acao, aoCancelar, aoSalvar }) {
  const inicial = useMemo(
    () => ({
      nome: acao?.nome ?? "",
      custo_unitario: acao ? paraCampoDeReais(acao.custo_unitario) : "",
      efeito_crescimento: acao ? deFracao(acao.efeito_crescimento) : "",
      efeito_retencao: acao ? deFracao(acao.efeito_retencao) : "",
      ativa: acao?.ativa ?? true,
    }),
    [acao],
  );
  const [v, setV] = useState(inicial);
  const [enviando, setEnviando] = useState(false);
  const { erros, receber, registrar } = useErrosDoFormulario();
  const alterado = Object.keys(inicial).some((k) => inicial[k] !== v[k]);
  const sufixo = acao ? acao.id : "nova";

  async function salvar() {
    setEnviando(true);
    try {
      const corpo = {
        nome: v.nome,
        custo_unitario: lerReais(v.custo_unitario),
        efeito_crescimento: paraFracao(v.efeito_crescimento),
        efeito_retencao: paraFracao(v.efeito_retencao),
        ativa: v.ativa,
      };
      if (acao) {
        const mudou = Object.fromEntries(Object.entries(corpo).filter(([k]) => inicial[k] !== v[k]));
        await api.patch(`/api/acoes-comerciais/${acao.id}`, mudou);
      } else {
        await api.post("/api/acoes-comerciais", corpo);
      }
      aoSalvar(v.nome);
    } catch (e) {
      receber(e, { ordem: ["nome", "custo_unitario", "efeito_crescimento", "efeito_retencao"] });
    } finally {
      setEnviando(false);
    }
  }

  const campo = (nome, rotulo, extra = {}) => (
    <div className={`campo campo--tabela${erros.campos[nome] ? " campo--erro" : ""}`}>
      <label className="campo__rotulo" htmlFor={`acao-${nome}-${sufixo}`}>
        {rotulo}
      </label>
      <input
        id={`acao-${nome}-${sufixo}`}
        ref={registrar(nome)}
        className="entrada"
        value={v[nome]}
        onChange={(e) => setV((x) => ({ ...x, [nome]: e.target.value }))}
        aria-invalid={erros.campos[nome] ? true : undefined}
        aria-describedby={erros.campos[nome] ? `acao-${nome}-${sufixo}-erro` : undefined}
        {...extra}
      />
      {erros.campos[nome] && (
        <p className="campo__erro" id={`acao-${nome}-${sufixo}-erro`}>
          <Icone nome="erro" />
          <span>{erros.campos[nome].mensagem}</span>
        </p>
      )}
    </div>
  );

  return (
    <tr className="linha--editando">
      <td colSpan={6}>
        <div className="edicao-em-linha" role="group" aria-label={acao ? `Editar ${acao.nome}` : "Nova ação"}>
          {erros.topo && !Object.keys(erros.campos).length && <ErroDaAcao erro={erros.erro ?? { message: erros.topo }} />}
          <div className="edicao-em-linha__campos">
            {campo("nome", "Nome")}
            {campo("custo_unitario", "Custo unitário, em reais", { inputMode: "decimal" })}
            {campo("efeito_crescimento", "Efeito de crescimento, em %", { inputMode: "decimal" })}
            {campo("efeito_retencao", "Efeito de retenção, em %", { inputMode: "decimal" })}
            <label className="caixa-de-selecao edicao-em-linha__ativa">
              <input type="checkbox" checked={v.ativa} onChange={(e) => setV((x) => ({ ...x, ativa: e.target.checked }))} /> Ativa
            </label>
          </div>
          <div className="formulario__acoes">
            <button type="button" className="botao botao--primario botao--pequeno" onClick={salvar} disabled={enviando || (acao && !alterado)}>
              {enviando ? "Salvando…" : "Salvar"}
            </button>
            <button type="button" className="botao botao--secundario botao--pequeno" onClick={aoCancelar} disabled={enviando}>
              Cancelar
            </button>
          </div>
        </div>
        <AlteracoesNaoSalvas quando={alterado && !enviando} />
      </td>
    </tr>
  );
}
