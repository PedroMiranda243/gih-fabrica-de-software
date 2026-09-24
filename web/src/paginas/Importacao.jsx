/**
 * Importação de relatório (UC03).
 *
 * O fluxo é o que a API implementa: informar o período, colar o texto **ou**
 * enviar um arquivo, ver a **prévia**, e só então confirmar. A prévia não é
 * enfeite — é o que o RF11 pede, e é o que permite alguém conferir o que vai
 * entrar antes de entrar.
 *
 * Duas recusas do servidor aparecem como erro de negócio, e não como falha
 * genérica: sem período (RN03) e período já importado (RF12). As duas trazem
 * `ajuda` explicando o que fazer, e é essa explicação que a tela mostra.
 *
 * Abaixo do formulário, o **histórico** (RF13): quem trouxe cada período e o que
 * restou dele. O Administrador lê o histórico sem importar nada — para ele, a
 * tela é só essa parte.
 */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api/cliente";
import { useSessao } from "../api/contextoSessao";
import { Esqueleto } from "../componentes/Carregando";
import EstadoVazio from "../componentes/EstadoVazio";
import {
  comoDataHora,
  comoDinheiro,
  comoInteiro,
  comoPeriodo,
  ROTULO_ORIGEM,
  TRACO,
} from "../formato";
import "../estilos/importacao.css";

const VAZIO = { periodo_inicio: "", periodo_fim: "", texto: "" };
const TAMANHO_HISTORICO = 10;

export default function Importacao() {
  const { usuario } = useSessao();
  /* Quem importa vem das telas que o servidor mandou, e não de um `if` sobre o
     perfil aqui (regra 2.4). Sessão sem `telas`, de antes da atualização, vê o
     formulário como sempre viu — e a rota recusa se não puder. */
  const podeImportar = !Array.isArray(usuario?.telas) || usuario.telas.includes("importar");

  /* Cada importação gravada troca a chave do histórico: ele recarrega e volta
     à primeira página, onde a importação nova aparece. */
  const [gravadas, setGravadas] = useState(0);

  return (
    <>
      {podeImportar && <Formulario aoGravar={() => setGravadas((n) => n + 1)} />}
      <Historico key={gravadas} />
    </>
  );
}

function Formulario({ aoGravar }) {
  const [form, setForm] = useState(VAZIO);
  const [arquivo, setArquivo] = useState(null);
  const [previa, setPrevia] = useState(null);
  const [erro, setErro] = useState(null);
  const [ocupado, setOcupado] = useState(false);
  const [resultado, setResultado] = useState(null);

  const temPeriodo = form.periodo_inicio && form.periodo_fim;
  const temConteudo = arquivo || form.texto.trim();

  function campo(nome) {
    return {
      value: form[nome],
      onChange: (e) => setForm((f) => ({ ...f, [nome]: e.target.value })),
    };
  }

  /* O arquivo e o texto colado são caminhos alternativos. Manter os dois
     preenchidos deixaria ambíguo o que será importado. */
  function escolherArquivo(e) {
    setArquivo(e.target.files?.[0] ?? null);
    setForm((f) => ({ ...f, texto: "" }));
    setPrevia(null);
  }

  function montarFormulario(extra = {}) {
    const dados = new FormData();
    dados.set("arquivo", arquivo);
    dados.set("periodo_inicio", form.periodo_inicio);
    dados.set("periodo_fim", form.periodo_fim);
    Object.entries(extra).forEach(([chave, valor]) => dados.set(chave, String(valor)));
    return dados;
  }

  async function executar(acao) {
    setErro(null);
    setOcupado(true);
    try {
      return await acao();
    } catch (e) {
      setErro(e);
      return null;
    } finally {
      setOcupado(false);
    }
  }

  async function verPrevia(evento) {
    evento.preventDefault();
    setResultado(null);
    const resposta = await executar(() =>
      arquivo
        ? api.enviarArquivo("/api/importacoes/arquivo/previa", montarFormulario())
        : api.post("/api/importacoes/previa", { ...form }),
    );
    if (resposta) setPrevia(resposta);
  }

  async function confirmar(substituir = false) {
    const resposta = await executar(() =>
      arquivo
        ? api.enviarArquivo("/api/importacoes/arquivo", montarFormulario({ substituir }))
        : api.post("/api/importacoes", { ...form, substituir }),
    );
    if (resposta) {
      setResultado(resposta);
      setPrevia(null);
      setForm(VAZIO);
      setArquivo(null);
      aoGravar();
    }
  }

  /* O 409 do período repetido traz quantos registros seriam apagados e quem os
     trouxe. A substituição só é oferecida depois disso — o padrão do RF12 é
     cancelar, e destruir dado não pode ser um clique distraído. */
  const conflito = erro?.status === 409 ? erro.corpo?.detail?.ja_existe : null;

  return (
    <>
      {resultado && (
        <div className="aviso aviso--sucesso" role="status">
          <p className="aviso__titulo">
            Importação concluída — {comoInteiro(resultado.total_gravado)} registros gravados.
          </p>
          <p className="aviso__ajuda">
            {resultado.total_rejeitado > 0
              ? `${comoInteiro(resultado.total_rejeitado)} linha(s) rejeitada(s) não entraram.`
              : "Nenhuma linha rejeitada."}
          </p>
          {/* A importação termina segmentando a base, e o resultado disso está no
              painel, não aqui. Sem o link, o passo seguinte ficava por conta de
              achar o menu. */}
          <p className="aviso__acao">
            <Link to="/">Ver no painel</Link>
          </p>
        </div>
      )}

      <form className="painel importacao" onSubmit={verPrevia}>
        <div className="painel__cabecalho">
          <h2 className="painel__titulo">Relatório do período</h2>
          <span className="painel__nota">Colar o texto ou enviar um arquivo CSV</span>
        </div>

        <div className="importacao__corpo">
          <div className="importacao__periodo">
            <div className="campo">
              <label htmlFor="inicio">Início do período</label>
              <input id="inicio" type="date" required {...campo("periodo_inicio")} />
            </div>
            <div className="campo">
              <label htmlFor="fim">Fim do período</label>
              <input id="fim" type="date" required {...campo("periodo_fim")} />
            </div>
          </div>

          <p className="importacao__nota">
            O relatório não traz datas. Sem o período, as métricas ficam órfãs na linha do tempo e a
            segmentação por tendência classifica errado sem emitir erro — por isso ele é obrigatório.
          </p>

          <div className="campo">
            <label htmlFor="texto">Colar o relatório</label>
            <textarea
              id="texto"
              rows={8}
              placeholder={"Parceiro;Faturamento;Pedidos\nComércio Alfa;12500,40;312"}
              disabled={Boolean(arquivo)}
              {...campo("texto")}
            />
          </div>

          <div className="campo">
            <label htmlFor="arquivo">…ou enviar um arquivo</label>
            <input id="arquivo" type="file" accept=".csv,.txt,text/csv,text/plain" onChange={escolherArquivo} />
            {arquivo && (
              <span className="importacao__arquivo">
                {arquivo.name}
                <button
                  type="button"
                  className="importacao__remover"
                  onClick={() => setArquivo(null)}
                >
                  remover
                </button>
              </span>
            )}
          </div>

          {erro && (
            <div className="aviso" role="alert">
              <p className="aviso__titulo">{erro.message}</p>
              {erro.ajuda && <p className="aviso__ajuda">{erro.ajuda}</p>}
              {erro.campos?.map((c) => (
                <p key={c.campo} className="aviso__ajuda">
                  <strong>{c.campo}:</strong> {c.ajuda ?? c.mensagem}
                </p>
              ))}
              {conflito && (
                <div className="importacao__conflito">
                  <p>
                    Já existem <strong>{comoInteiro(conflito.metricas_que_serao_apagadas)}</strong>{" "}
                    registros neste período, trazidos por {conflito.autor}. Substituir apaga todos
                    eles.
                  </p>
                  <button
                    type="button"
                    className="botao"
                    disabled={ocupado}
                    onClick={() => confirmar(true)}
                  >
                    Substituir mesmo assim
                  </button>
                </div>
              )}
            </div>
          )}

          <button className="botao" type="submit" disabled={ocupado || !temPeriodo || !temConteudo}>
            {ocupado ? "Lendo…" : "Ver a prévia"}
          </button>
        </div>
      </form>

      {previa && <Previa previa={previa} ocupado={ocupado} aoConfirmar={() => confirmar(false)} />}
    </>
  );
}

/**
 * O que será gravado, antes de gravar.
 *
 * Os rejeitados vêm **com o motivo de cada um**: "3 linhas rejeitadas" não
 * permite corrigir nada, e o número da linha é o que deixa achar a célula errada
 * num relatório de duzentas.
 */
function Previa({ previa, ocupado, aoConfirmar }) {
  return (
    <section className="painel" aria-labelledby="titulo-previa">
      <div className="painel__cabecalho">
        <h2 className="painel__titulo" id="titulo-previa">
          Prévia
        </h2>
        <span className="painel__nota">
          {comoInteiro(previa.total_reconhecido)} reconhecidas ·{" "}
          {comoInteiro(previa.total_rejeitado)} rejeitadas
        </span>
      </div>

      <div className="importacao__corpo">
        {previa.parceiros_novos.length > 0 && (
          <p className="importacao__nota">
            <strong>{previa.parceiros_novos.length} parceiro(s) novo(s)</strong> serão cadastrados:{" "}
            {previa.parceiros_novos.slice(0, 6).join(", ")}
            {previa.parceiros_novos.length > 6 && "…"}
          </p>
        )}

        {previa.rejeitados.length > 0 && (
          <div className="tabela-rolagem">
            <table className="tabela">
              <caption className="so-leitor">Linhas rejeitadas, com o motivo</caption>
              <thead>
                <tr>
                  <th scope="col">Linha</th>
                  <th scope="col">Conteúdo</th>
                  <th scope="col">Motivo</th>
                </tr>
              </thead>
              <tbody>
                {previa.rejeitados.map((r) => (
                  <tr key={r.linha}>
                    <td className="posicao">{r.linha}</td>
                    <td className="secundaria num">{r.conteudo}</td>
                    <td>{r.motivo}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {previa.reconhecidos.length > 0 && (
          <div className="tabela-rolagem">
            <table className="tabela">
              <caption className="so-leitor">Linhas que serão gravadas</caption>
              <thead>
                <tr>
                  <th scope="col">Parceiro</th>
                  <th scope="col" className="numerica">
                    Faturamento
                  </th>
                  <th scope="col" className="numerica">
                    Pedidos
                  </th>
                </tr>
              </thead>
              <tbody>
                {previa.reconhecidos.slice(0, 20).map((linha) => (
                  <tr key={linha.linha}>
                    <td className="nome">{linha.nome}</td>
                    <td className="numerica">{comoDinheiro(linha.faturamento)}</td>
                    <td className="numerica">{comoInteiro(linha.pedidos)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <button
          className="botao"
          type="button"
          onClick={aoConfirmar}
          disabled={ocupado || previa.total_reconhecido === 0}
        >
          {ocupado ? "Gravando…" : `Gravar ${comoInteiro(previa.total_reconhecido)} registros`}
        </button>
      </div>
    </section>
  );
}

/**
 * O histórico das importações (RF13, H29), da mais recente para a mais antiga.
 *
 * "Vigentes" é quanto daquela importação ainda está no banco, contado pela API.
 * Zero depois de ter gravado alguma coisa é o rastro de uma **substituição**: o
 * período foi trocado por uma importação mais nova. A tela diz isso com a
 * palavra, porque um zero sozinho pareceria importação vazia.
 */
function Historico() {
  const [pagina, setPagina] = useState(1);
  const [estado, setEstado] = useState({ pagina: null, dados: null, erro: null });

  useEffect(() => {
    let vivo = true;
    api
      .get("/api/importacoes", { pagina, tamanho: TAMANHO_HISTORICO })
      .then((dados) => vivo && setEstado({ pagina, dados, erro: null }))
      .catch((erro) => vivo && setEstado({ pagina, dados: null, erro }));
    return () => {
      vivo = false;
    };
  }, [pagina]);

  const atual = estado.pagina === pagina;
  const dados = atual ? estado.dados : null;
  const erro = atual ? estado.erro : null;
  const total = dados?.total ?? 0;
  const primeiro = (pagina - 1) * TAMANHO_HISTORICO + 1;
  const ultimo = Math.min(pagina * TAMANHO_HISTORICO, total);

  return (
    <section className="painel historico" aria-labelledby="titulo-historico">
      <div className="painel__cabecalho">
        <h2 className="painel__titulo" id="titulo-historico">
          Importações anteriores
        </h2>
        {dados && <span className="painel__nota">{comoInteiro(total)} no total</span>}
      </div>

      {erro && (
        <div className="aviso" role="alert">
          <p className="aviso__titulo">{erro.message}</p>
          {erro.ajuda && <p className="aviso__ajuda">{erro.ajuda}</p>}
        </div>
      )}

      {!dados && !erro && (
        <div className="importacao__corpo" aria-hidden="true">
          <Esqueleto altura={160} />
        </div>
      )}

      {dados && total === 0 && (
        <EstadoVazio
          titulo="Nenhuma importação ainda"
          texto="Cada relatório importado aparece aqui, com quem o trouxe e quando."
        />
      )}

      {dados && total > 0 && (
        <>
          <div className="tabela-rolagem">
            <table className="tabela">
              <caption className="so-leitor">
                Importações anteriores, da mais recente para a mais antiga
              </caption>
              <thead>
                <tr>
                  <th scope="col">Período</th>
                  <th scope="col">Enviada em</th>
                  <th scope="col">Por</th>
                  <th scope="col">Origem</th>
                  <th scope="col" className="numerica">
                    Gravados
                  </th>
                  <th scope="col" className="numerica">
                    Rejeitados
                  </th>
                  <th scope="col" className="numerica">
                    Vigentes
                  </th>
                </tr>
              </thead>
              <tbody>
                {dados.itens.map((i) => (
                  <LinhaHistorico key={i.id} importacao={i} />
                ))}
              </tbody>
            </table>
          </div>

          <div className="paginacao">
            <span className="paginacao__posicao num">
              {comoInteiro(primeiro)}–{comoInteiro(ultimo)} de {comoInteiro(total)}
            </span>
            <button
              type="button"
              className="botao botao--secundario"
              disabled={pagina <= 1}
              onClick={() => setPagina((p) => p - 1)}
            >
              Anterior
            </button>
            <button
              type="button"
              className="botao botao--secundario"
              disabled={ultimo >= total}
              onClick={() => setPagina((p) => p + 1)}
            >
              Próxima
            </button>
          </div>
        </>
      )}
    </section>
  );
}

function LinhaHistorico({ importacao: i }) {
  const substituida = i.metricas_vigentes === 0 && i.total_gravado > 0;
  return (
    <tr>
      <td className="nome">{comoPeriodo(i.periodo)}</td>
      <td className="secundaria quando">{comoDataHora(i.enviado_em)}</td>
      <td>{i.autor?.nome ?? TRACO}</td>
      <td className="secundaria">{ROTULO_ORIGEM[i.origem] ?? i.origem}</td>
      <td className="numerica">{comoInteiro(i.total_gravado)}</td>
      <td className="numerica">{comoInteiro(i.total_rejeitado)}</td>
      <td className="numerica">
        {substituida ? <span className="secundaria">substituída</span> : comoInteiro(i.metricas_vigentes)}
      </td>
    </tr>
  );
}
