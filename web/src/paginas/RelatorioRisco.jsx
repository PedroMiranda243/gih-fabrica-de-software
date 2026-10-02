/**
 * O relatório de parceiros em risco (UC15 · RF45 · H85).
 *
 * Parceiro a parceiro: o que ele faturou, o que o modelo prevê, a chance de
 * queda e a ação que o último plano reserva para ele — o maior risco primeiro.
 *
 * **Estimativa não se veste de medição.** O relatório leva a etiqueta
 * "Estimativa" e diz de que modelo e com dados até quando; a chance não finge
 * certeza ("menos de 1%", "mais de 99%"), e quem não tem previsão aparece com o
 * motivo, e não com zero (RN09).
 *
 * **O risco mínimo é um filtro de quem consulta**, e não um limiar do sistema:
 * a pessoa digita a porcentagem a partir da qual quer ver, e ninguém é "de
 * risco" por passar dela. A conversão de porcentagem para fração é só formato;
 * quem compara é a API.
 *
 * A tela pagina; o CSV traz o recorte inteiro, e a folha impressa diz isso.
 */
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { api, comConsulta } from "../api/cliente";
import { Esqueleto } from "../componentes/Carregando";
import EstadoVazio from "../componentes/EstadoVazio";
import Relatorio, { ErroDoRelatorio, Variacao } from "../componentes/Relatorio";
import Segmento from "../componentes/Segmento";
import {
  comoData,
  comoDataHora,
  comoDinheiro,
  comoInteiro,
  comoProbabilidade,
  paraFracao,
  ROTULO_SEGMENTO,
  TRACO,
} from "../formato";

const TAMANHO_PAGINA = 50;

/* O cadastro aberto daqui volta para o relatório, e não para a lista. */
const voltaPara = (endereco) => ({
  lista: endereco,
  rotuloLista: "Relatório de risco",
  voltarPara: "Voltar para o relatório",
});

export default function RelatorioRisco() {
  const [parametros, setParametros] = useSearchParams();
  const categoria = parametros.get("categoria") ?? "";
  const segmento = parametros.get("segmento") ?? "";
  const riscoMinimo = parametros.get("risco_minimo") ?? "";
  const pagina = Number(parametros.get("pagina") ?? 1);
  const filtros = { categoria_id: categoria, segmento, risco_minimo: paraFracao(riscoMinimo) };
  const consulta = JSON.stringify({ ...filtros, pagina });

  const [categorias, setCategorias] = useState([]);
  const [estado, setEstado] = useState({ consulta: null, dados: null, erro: null });

  useEffect(() => {
    api
      .get("/api/painel/recortes")
      .then((recortes) => setCategorias(recortes.categorias))
      .catch(() => setCategorias([]));
  }, []);

  useEffect(() => {
    let vivo = true;
    /* O risco mínimo é digitado: espera a digitação parar, como a busca das listas. */
    const relogio = setTimeout(() => {
      api
        .get("/api/relatorios/risco", { ...JSON.parse(consulta), tamanho: TAMANHO_PAGINA })
        .then((dados) => vivo && setEstado({ consulta, dados, erro: null }))
        .catch((erro) => vivo && setEstado({ consulta, dados: null, erro }));
    }, 250);
    return () => {
      vivo = false;
      clearTimeout(relogio);
    };
  }, [consulta]);

  function ajustar(mudancas) {
    const proximos = new URLSearchParams(parametros);
    Object.entries(mudancas).forEach(([chave, valor]) =>
      valor === "" || valor === undefined ? proximos.delete(chave) : proximos.set(chave, String(valor)),
    );
    /* Mudar o filtro volta para a primeira página: a página 7 pode não existir mais. */
    if (!("pagina" in mudancas)) proximos.delete("pagina");
    setParametros(proximos, { replace: true });
  }

  const atual = estado.consulta === consulta;
  const dados = atual ? estado.dados : null;
  const erro = atual ? estado.erro : null;
  const total = dados?.total ?? 0;
  const primeiro = (pagina - 1) * TAMANHO_PAGINA + 1;
  const ultimo = Math.min(pagina * TAMANHO_PAGINA, total);

  return (
    <>
      <Relatorio
        titulo="Parceiros em risco"
        recorte={dados?.disponivel ? recorteDe(dados, primeiro, ultimo) : []}
        csv={dados?.disponivel ? comConsulta("/api/relatorios/risco/exportacao.csv", filtros) : null}
        filtros={
          <div className="filtros">
            <div className="campo">
              <label htmlFor="categoria">Categoria</label>
              <select
                id="categoria"
                value={categoria}
                onChange={(e) => ajustar({ categoria: e.target.value })}
              >
                <option value="">Todas as categorias</option>
                {categorias.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.nome}
                  </option>
                ))}
              </select>
            </div>
            <div className="campo">
              <label htmlFor="segmento">Segmento</label>
              <select
                id="segmento"
                value={segmento}
                onChange={(e) => ajustar({ segmento: e.target.value })}
              >
                <option value="">Todos os segmentos</option>
                {Object.entries(ROTULO_SEGMENTO).map(([valor, rotulo]) => (
                  <option key={valor} value={valor}>
                    {rotulo}
                  </option>
                ))}
              </select>
            </div>
            <div className="campo">
              <label htmlFor="risco-minimo">Chance de queda a partir de (%)</label>
              <input
                id="risco-minimo"
                type="number"
                inputMode="numeric"
                min="0"
                max="100"
                step="5"
                value={riscoMinimo}
                placeholder="Todos"
                aria-describedby="ajuda-risco-minimo"
                onChange={(e) => ajustar({ risco_minimo: e.target.value })}
              />
              <span className="campo__ajuda" id="ajuda-risco-minimo">
                Em branco, entram todos — inclusive quem não tem previsão.
              </span>
            </div>
          </div>
      
        }
      >
        <ErroDoRelatorio erro={erro} />

        {!dados && !erro && (
          <div role="status" aria-label="Carregando o relatório">
            <Esqueleto altura={96} style={{ marginBottom: "var(--esp-12)" }} />
            <Esqueleto altura={320} />
          </div>
        )}

        {dados && !dados.disponivel && (
          <section className="painel">
            {/* Sem modelo treinado, o relatório diz o que falta (UC15-A1). */}
            <EstadoVazio titulo={dados.motivo} texto={dados.ajuda} />
          </section>
        )}

        {dados?.disponivel && (
          <>
            <section className="painel painel--inteiro" aria-labelledby="titulo-resumo-risco">
              <div className="painel__cabecalho">
                <h3 className="painel__titulo" id="titulo-resumo-risco">
                  Resumo do recorte
                </h3>
                <span className="etiqueta-estimativa">Estimativa</span>
              </div>
              <dl className="relatorio__resumo">
                <div>
                  <dt>Parceiros</dt>
                  <dd className="num relatorio__principal">{comoInteiro(dados.total)}</dd>
                </div>
                <div>
                  <dt>Com previsão</dt>
                  <dd className="num">{comoInteiro(dados.com_previsao)}</dd>
                </div>
                <div>
                  <dt>Medido, de quem tem previsão</dt>
                  <dd className="num">{comoDinheiro(dados.faturamento_medido)}</dd>
                </div>
                <div>
                  <dt>Previsto para o próximo período</dt>
                  <dd className="num">{comoDinheiro(dados.faturamento_previsto)}</dd>
                </div>
                <div>
                  <dt>No último plano</dt>
                  <dd className="num">{dados.plano ? comoInteiro(dados.no_plano) : TRACO}</dd>
                </div>
              </dl>
              <p className="relatorio__nota">
                O previsto e a chance de queda são estimativa do modelo {dados.modelo_versao}, com
                dados até {comoData(dados.periodo_base.data_fim)}, e não medição. A chance é a de o
                parceiro fechar o próximo período em risco (RN09).
                {dados.desatualizada &&
                  " Há período importado depois desta estimativa; o próximo treino a refaz."}
                {dados.plano
                  ? ` A ação é a do plano de ${comoDataHora(dados.plano.concluida_em)}.`
                  : " Nenhum plano de campanha foi calculado ainda, e a coluna da ação fica vazia."}
              </p>
            </section>

            <section className="painel" aria-labelledby="titulo-parceiros-risco">
              <div className="painel__cabecalho">
                <h3 className="painel__titulo" id="titulo-parceiros-risco">
                  Parceiros, do maior risco para o menor
                </h3>
                <span className="painel__nota">
                  {comoInteiro(total)} {total === 1 ? "parceiro" : "parceiros"}
                </span>
              </div>

              {dados.itens.length === 0 ? (
                <EstadoVazio
                  titulo="Nenhum parceiro nesse recorte"
                  texto="Não há parceiro com esses filtros. Diminua a chance de queda ou troque a categoria."
                />
              ) : (
                <>
                  <div className="tabela-rolagem">
                    <table className="tabela">
                      <caption className="so-leitor">
                        Parceiros com o faturamento medido, o previsto, a chance de queda e a ação
                        no último plano
                      </caption>
                      <thead>
                        <tr>
                          <th scope="col">Parceiro</th>
                          <th scope="col">Categoria</th>
                          <th scope="col">Segmento</th>
                          <th scope="col" className="numerica">
                            Faturamento
                          </th>
                          <th scope="col" className="numerica">
                            Variação
                          </th>
                          <th scope="col" className="numerica">
                            Previsto
                          </th>
                          <th scope="col" className="numerica">
                            Chance de queda
                          </th>
                          <th scope="col">Ação no plano</th>
                        </tr>
                      </thead>
                      <tbody>
                        {dados.itens.map((item) => (
                          <Linha
                            key={item.parceiro_id}
                            item={item}
                            origem={voltaPara(`/relatorios/risco?${parametros}`)}
                          />
                        ))}
                      </tbody>
                    </table>
                  </div>

                  <div className="paginacao nao-imprime">
                    <span className="paginacao__posicao num">
                      {comoInteiro(primeiro)}–{comoInteiro(ultimo)} de {comoInteiro(total)}
                    </span>
                    <button
                      type="button"
                      className="botao botao--secundario"
                      disabled={pagina <= 1}
                      onClick={() => ajustar({ pagina: pagina - 1 })}
                    >
                      Anterior
                    </button>
                    <button
                      type="button"
                      className="botao botao--secundario"
                      disabled={ultimo >= total}
                      onClick={() => ajustar({ pagina: pagina + 1 })}
                    >
                      Próxima
                    </button>
                  </div>
                </>
              )}
            </section>
          </>
        )}
      </Relatorio>
    </>
  );
}

/** O recorte como a folha o diz, a partir do que a API devolveu. */
function recorteDe(dados, primeiro, ultimo) {
  const partes = [
    `Previsão a partir do período de ${comoData(dados.periodo_base.data_inicio)} a ${comoData(dados.periodo_base.data_fim)}`,
    dados.categoria ? `categoria ${dados.categoria.nome}` : "todas as categorias",
    dados.segmento ? `segmento ${ROTULO_SEGMENTO[dados.segmento] ?? dados.segmento}` : "todos os segmentos",
    dados.risco_minimo === null
      ? "qualquer chance de queda"
      : `chance de queda a partir de ${comoProbabilidade(dados.risco_minimo)}`,
  ];
  /* A tela mostra uma página; quem lê a folha precisa saber que há mais. */
  if (dados.total > dados.itens.length) {
    partes.push(
      `parceiros ${comoInteiro(primeiro)} a ${comoInteiro(ultimo)} de ${comoInteiro(dados.total)} — o arquivo CSV traz todos`,
    );
  }
  return partes;
}

function Linha({ item, origem }) {
  return (
    <tr>
      <td className="nome">
        <Link className="nome__link" to={`/parceiros/${item.parceiro_id}`} state={origem}>
          {item.nome}
        </Link>
      </td>
      <td className="secundaria">{item.categoria ?? "sem categoria"}</td>
      <td className="secundaria">
        <Segmento valor={item.segmento} />
      </td>
      <td className="numerica">{comoDinheiro(item.faturamento)}</td>
      <td className="numerica">
        <Variacao valor={item.variacao_percentual} />
      </td>
      {item.sem_previsao ? (
        /* Sem previsão não é risco zero: o motivo ocupa o lugar dos dois números (RN09). */
        <td className="relatorio__motivo" colSpan={2}>
          {item.sem_previsao}
        </td>
      ) : (
        <>
          <td className="numerica secundaria">{comoDinheiro(item.faturamento_previsto)}</td>
          <td className="numerica">{comoProbabilidade(item.probabilidade_queda)}</td>
        </>
      )}
      <td className="secundaria relatorio__acao">
        {item.acao ? (
          <>
            {item.acao} <span className="num">· {comoDinheiro(item.custo)}</span>
          </>
        ) : (
          <span title="Fora do último plano">
            {TRACO}
            <span className="so-leitor"> fora do último plano</span>
          </span>
        )}
      </td>
    </tr>
  );
}
