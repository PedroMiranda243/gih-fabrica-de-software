/**
 * Importação — trazer o relatório da semana, conferindo antes de gravar.
 * O formulário só para quem tem `importar`; o histórico para quem tem qualquer um.
 */
import { useRef, useState } from "react";
import { Link } from "react-router-dom";

import { api, ErroDaApi } from "../api/cliente";
import { useCarregar, useFiltros } from "../api/ganchos";
import { tem, useSessao } from "../api/sessao";
import Confirmacao from "../componentes/Confirmacao";
import { Ausente } from "../componentes/Dados";
import { Carregando, ErroDaTela, Nota, Sucesso, Vazio } from "../componentes/Estados";
import { Campo, ResumoDeErros, useErrosDoFormulario } from "../componentes/Formulario";
import Icone from "../componentes/Icone";
import { CaixaDeTabela, Paginacao } from "../componentes/Lista";
import { useTitulo } from "../componentes/Titulo";
import { comoDataHora, comoDinheiro, comoInteiro, comoPeriodo, plural, ROTULO_ORIGEM } from "../formato";

const EXEMPLO = "Parceiro;Faturamento;Pedidos\nComércio Alfa;12500,40;312";
const TAMANHO = 10;

export default function Importacao() {
  useTitulo("Importação de relatório", "Importação");
  const { usuario } = useSessao();
  const [filtros, mudar] = useFiltros();
  const pagina = Number(filtros.pagina) || 1;
  const historico = useCarregar(() => api.get("/api/importacoes", { pagina, tamanho: TAMANHO }), `h${pagina}`);
  const podeImportar = tem(usuario, "importar");

  return (
    <div className="pagina pagina--importacao">
      {podeImportar ? (
        <FormularioDeImportacao aoGravar={() => historico.recarregar()} />
      ) : (
        <Nota titulo="O seu perfil consulta o histórico">Importar um relatório é do Gestor e do Analista. Abaixo estão todas as importações, com quem as trouxe e quando.</Nota>
      )}
      <Historico historico={historico} pagina={pagina} aoMudarPagina={(p) => mudar({ pagina: p > 1 ? p : null }, { manterPagina: true })} />
    </div>
  );
}

function FormularioDeImportacao({ aoGravar }) {
  const [inicio, setInicio] = useState("");
  const [fim, setFim] = useState("");
  const [modo, setModo] = useState("texto");
  const [texto, setTexto] = useState("");
  const [arquivo, setArquivo] = useState(null);
  const [previa, setPrevia] = useState(null);
  const [conflito, setConflito] = useState(null);
  const [gravado, setGravado] = useState(null);
  const [ocupado, setOcupado] = useState(null);
  const { erros, receber, limpar, registrar } = useErrosDoFormulario();
  const refArquivo = useRef(null);
  const refPrevia = useRef(null);

  function mexeu() {
    setPrevia(null);
    setConflito(null);
    setGravado(null);
  }

  function corpo(substituir = false) {
    if (modo === "arquivo") {
      const f = new FormData();
      if (arquivo) f.append("arquivo", arquivo);
      if (inicio) f.append("periodo_inicio", inicio);
      if (fim) f.append("periodo_fim", fim);
      if (substituir) f.append("substituir", "true");
      return f;
    }
    return { periodo_inicio: inicio || undefined, periodo_fim: fim || undefined, texto, ...(substituir ? { substituir: true } : {}) };
  }

  async function verPrevia(evento) {
    evento.preventDefault();
    limpar();
    mexeu();
    setOcupado("previa");
    try {
      const r = modo === "arquivo" ? await api.enviarArquivo("/api/importacoes/arquivo/previa", corpo()) : await api.post("/api/importacoes/previa", corpo());
      setPrevia(r);
      requestAnimationFrame(() => refPrevia.current?.focus());
    } catch (e) {
      receber(e, { ordem: ["periodo_inicio", "periodo_fim", "texto", "arquivo"] });
    } finally {
      setOcupado(null);
    }
  }

  async function gravar(substituir = false) {
    limpar();
    setOcupado(substituir ? "substituir" : "gravar");
    try {
      const r = modo === "arquivo" ? await api.enviarArquivo("/api/importacoes/arquivo", corpo(substituir)) : await api.post("/api/importacoes", corpo(substituir));
      setGravado(r);
      setPrevia(null);
      setConflito(null);
      aoGravar();
    } catch (e) {
      if (e instanceof ErroDaApi && e.status === 409 && e.detalhe?.ja_existe) setConflito(e);
      else receber(e, { ordem: ["periodo_inicio", "periodo_fim", "texto", "arquivo"] });
    } finally {
      setOcupado(null);
    }
  }

  const temConteudo = modo === "texto" ? texto.trim().length > 0 : Boolean(arquivo);

  return (
    <section className="bloco bloco--formulario" aria-labelledby="titulo-novo-relatorio">
      <div className="bloco__cabeca">
        <h2 id="titulo-novo-relatorio" className="bloco__titulo">
          Relatório da semana
        </h2>
        <p className="bloco__sub">Confira na prévia o que será gravado antes de gravar.</p>
      </div>

      {gravado && (
        <Sucesso foco>
          <p>
            Importação gravada: {plural(gravado.total_gravado, "registro", "registros")} do período {comoPeriodo(gravado.periodo)}
            {gravado.total_rejeitado ? `, e ${plural(gravado.total_rejeitado, "linha rejeitada", "linhas rejeitadas")}` : ""}.
          </p>
          <Link to="/" className="link-seta">
            Ver no painel <Icone nome="seta-direita" />
          </Link>
        </Sucesso>
      )}

      <form onSubmit={verPrevia} noValidate className="formulario">
        <ResumoDeErros erros={erros} rotulos={{ periodo_inicio: "Início do período", periodo_fim: "Fim do período", texto: "Relatório", arquivo: "Arquivo" }} />
        <fieldset className="grupo-campos grupo-campos--linha">
          <legend className="grupo-campos__legenda">Período do relatório</legend>
          <Campo nome="periodo_inicio" rotulo="Início do período" obrigatorio erro={erros.campos.periodo_inicio} largura="220px">
            {(a) => <input {...a} ref={registrar("periodo_inicio")} type="date" className="entrada" value={inicio} onChange={(e) => (setInicio(e.target.value), mexeu())} />}
          </Campo>
          <Campo nome="periodo_fim" rotulo="Fim do período" obrigatorio erro={erros.campos.periodo_fim} largura="220px">
            {(a) => <input {...a} ref={registrar("periodo_fim")} type="date" className="entrada" value={fim} onChange={(e) => (setFim(e.target.value), mexeu())} />}
          </Campo>
        </fieldset>

        <fieldset className="grupo-campos">
          <legend className="grupo-campos__legenda">Como o relatório chega</legend>
          <div className="segmentado" role="radiogroup" aria-label="Como o relatório chega">
            {[
              ["texto", "Colar o texto"],
              ["arquivo", "Enviar um arquivo CSV"],
            ].map(([v, r]) => (
              <label key={v} className={`segmentado__opcao${modo === v ? " segmentado__opcao--ativa" : ""}`}>
                <input type="radio" name="modo" value={v} checked={modo === v} onChange={() => (setModo(v), mexeu())} />
                {r}
              </label>
            ))}
          </div>
          {modo === "texto" ? (
            <Campo nome="texto" rotulo="Relatório" obrigatorio erro={erros.campos.texto} ajuda="Uma linha por parceiro, com cabeçalho: nome, faturamento (vírgula nos centavos) e pedidos, separados por ponto e vírgula.">
              {(a) => <textarea {...a} ref={registrar("texto")} className="entrada entrada--codigo" rows={9} placeholder={EXEMPLO} value={texto} onChange={(e) => (setTexto(e.target.value), mexeu())} spellCheck={false} />}
            </Campo>
          ) : (
            <Campo nome="arquivo" rotulo="Arquivo CSV" obrigatorio erro={erros.campos.arquivo} ajuda="CSV ou texto, com cabeçalho. Planilha do Excel precisa ser exportada como CSV antes.">
              {(a) =>
                arquivo ? (
                  <div className="arquivo-escolhido" id={a.id}>
                    <Icone nome="arquivo" />
                    <span className="arquivo-escolhido__nome">{arquivo.name}</span>
                    <span className="arquivo-escolhido__tamanho">{comoInteiro(Math.ceil(arquivo.size / 1024))} KB</span>
                    <button
                      type="button"
                      className="botao botao--fantasma botao--pequeno"
                      onClick={() => {
                        setArquivo(null);
                        mexeu();
                        requestAnimationFrame(() => refArquivo.current?.focus());
                      }}
                    >
                      Remover
                    </button>
                  </div>
                ) : (
                  <input
                    {...a}
                    ref={(el) => {
                      refArquivo.current = el;
                      registrar("arquivo")(el);
                    }}
                    type="file"
                    accept=".csv,.txt,text/csv,text/plain"
                    className="entrada entrada--arquivo"
                    onChange={(e) => (setArquivo(e.target.files?.[0] ?? null), mexeu())}
                  />
                )
              }
            </Campo>
          )}
        </fieldset>

        <div className="formulario__acoes">
          <button type="submit" className="botao botao--primario" disabled={!temConteudo || ocupado !== null}>
            {ocupado === "previa" ? "Conferindo…" : "Ver a prévia"}
          </button>
          <span className="formulario__dica">A prévia não grava nada.</span>
        </div>
      </form>

      {conflito && (
        <Confirmacao
          perigo
          texto={
            <>
              {conflito.message} Já existem <strong>{comoInteiro(conflito.detalhe.ja_existe.metricas_que_serao_apagadas)}</strong> registros deste período, importados por {conflito.detalhe.ja_existe.autor} em{" "}
              {comoDataHora(conflito.detalhe.ja_existe.enviado_em)}.
            </>
          }
          detalhe={conflito.ajuda}
          acao="Substituir mesmo assim"
          ocupado={ocupado === "substituir"}
          aoConfirmar={() => gravar(true)}
          aoCancelar={() => setConflito(null)}
        />
      )}

      {previa && (
        <section className="previa" aria-labelledby="titulo-previa" tabIndex={-1} ref={refPrevia}>
          <div className="previa__cabeca">
            <h3 id="titulo-previa" className="bloco__titulo">
              Prévia de {comoPeriodo(previa.periodo)}
            </h3>
            <p className="bloco__sub">
              {plural(previa.total_reconhecido, "linha será gravada", "linhas serão gravadas")} · {plural(previa.total_rejeitado, "linha rejeitada", "linhas rejeitadas")}
              {previa.parceiros_novos.length ? ` · ${plural(previa.parceiros_novos.length, "parceiro novo", "parceiros novos")}` : ""}
            </p>
          </div>
          {previa.periodo_ja_importado && (
            <Nota tipo="atencao">Este período já foi importado. Ao gravar, o sistema vai perguntar antes de substituir o que já existe.</Nota>
          )}

          <div className="previa__grade">
            <div>
              <h4 className="bloco__subtitulo">Linhas que serão gravadas</h4>
              {previa.reconhecidos.length ? (
                <CaixaDeTabela rotulo="Linhas que serão gravadas" className="caixa-tabela--alta">
                  <table className="tabela tabela--compacta">
                    <caption className="sr-only">Linhas reconhecidas, que serão gravadas</caption>
                    <thead>
                      <tr>
                        <th scope="col" className="num">
                          Linha
                        </th>
                        <th scope="col">Parceiro</th>
                        <th scope="col" className="num">
                          Faturamento
                        </th>
                        <th scope="col" className="num">
                          Pedidos
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {previa.reconhecidos.map((l) => (
                        <tr key={l.linha}>
                          <td className="num discreto">{l.linha}</td>
                          <th scope="row" className="nome">
                            {l.nome}
                            {previa.parceiros_novos.includes(l.nome) && <span className="selo-texto">novo</span>}
                          </th>
                          <td className="num">{comoDinheiro(l.faturamento)}</td>
                          <td className="num">{comoInteiro(l.pedidos)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </CaixaDeTabela>
              ) : (
                <Vazio titulo="Nenhuma linha aproveitável" compacto>
                  Nada será gravado. Corrija as linhas rejeitadas e veja a prévia de novo.
                </Vazio>
              )}
            </div>
            <div>
              <h4 className="bloco__subtitulo">Linhas rejeitadas, com o motivo</h4>
              {previa.rejeitados.length ? (
                <CaixaDeTabela rotulo="Linhas rejeitadas" className="caixa-tabela--alta">
                  <table className="tabela tabela--compacta tabela--rejeitadas">
                    <caption className="sr-only">Linhas rejeitadas e o motivo de cada uma</caption>
                    <thead>
                      <tr>
                        <th scope="col" className="num">
                          Linha
                        </th>
                        <th scope="col">Conteúdo</th>
                        <th scope="col">Motivo</th>
                      </tr>
                    </thead>
                    <tbody>
                      {previa.rejeitados.map((l) => (
                        <tr key={l.linha}>
                          <th scope="row" className="num">
                            {l.linha}
                          </th>
                          <td>
                            <code>{l.conteudo || <Ausente porque="linha vazia" />}</code>
                          </td>
                          <td>{l.motivo}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </CaixaDeTabela>
              ) : (
                <p className="linha-ok">
                  <Icone nome="certo" /> Nenhuma linha rejeitada.
                </p>
              )}
            </div>
          </div>

          {previa.total_reconhecido > 0 && (
            <div className="formulario__acoes">
              <button type="button" className="botao botao--primario botao--grande" onClick={() => gravar(false)} disabled={ocupado !== null}>
                {ocupado === "gravar" ? "Gravando…" : `Gravar ${plural(previa.total_reconhecido, "registro", "registros")}`}
              </button>
            </div>
          )}
        </section>
      )}
    </section>
  );
}

function Historico({ historico, pagina, aoMudarPagina }) {
  const h = historico.dados;
  return (
    <section className="bloco" aria-labelledby="titulo-historico" aria-busy={historico.carregando}>
      <div className="bloco__cabeca">
        <h2 id="titulo-historico" className="bloco__titulo">
          Importações anteriores
        </h2>
        <p className="bloco__sub">Da mais recente para a mais antiga</p>
      </div>
      {historico.carregando && <Carregando rotulo="Carregando o histórico" linhas={5} />}
      <ErroDaTela erro={historico.erro} />
      {h && !h.itens.length && (
        <Vazio titulo="Nenhuma importação ainda" compacto icone="importacao">
          Cada relatório importado aparece aqui, com quem o trouxe e quando.
        </Vazio>
      )}
      {h && h.itens.length > 0 && (
        <>
          <CaixaDeTabela rotulo="Importações anteriores">
            <table className="tabela">
              <caption className="sr-only">Importações anteriores, da mais recente para a mais antiga</caption>
              <thead>
                <tr>
                  <th scope="col">Período</th>
                  <th scope="col">Enviada em</th>
                  <th scope="col">Por</th>
                  <th scope="col">Origem</th>
                  <th scope="col" className="num">
                    Gravados
                  </th>
                  <th scope="col" className="num">
                    Rejeitados
                  </th>
                  <th scope="col" className="num">
                    Vigentes
                  </th>
                </tr>
              </thead>
              <tbody>
                {h.itens.map((i) => (
                  <tr key={i.id} className={i.metricas_vigentes === 0 && i.total_gravado > 0 ? "linha--apagada" : undefined}>
                    <th scope="row" className="nome">
                      {comoPeriodo(i.periodo)}
                    </th>
                    <td>{comoDataHora(i.enviado_em)}</td>
                    <td>{i.autor?.nome}</td>
                    <td>{ROTULO_ORIGEM[i.origem] ?? i.origem}</td>
                    <td className="num">{comoInteiro(i.total_gravado)}</td>
                    <td className="num">{comoInteiro(i.total_rejeitado)}</td>
                    <td className="num">{i.metricas_vigentes === 0 && i.total_gravado > 0 ? <span className="selo-texto selo-texto--neutro">substituída</span> : comoInteiro(i.metricas_vigentes)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CaixaDeTabela>
          <Paginacao pagina={pagina} tamanho={TAMANHO} total={h.total} aoMudar={aoMudarPagina} rotulo="importações" />
        </>
      )}
    </section>
  );
}
