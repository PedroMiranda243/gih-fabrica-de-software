/**
 * A previsão e a campanha dentro do painel (H83, UC05-A5).
 *
 * O painel mostrava só o que foi medido. Aqui entram os outros dois módulos: o
 * que o modelo prevê para o próximo período e o que a última campanha decidiu,
 * cada um com o caminho para onde o detalhe mora — o cadastro do parceiro, a
 * lista ordenada pelo risco, o plano.
 *
 * **Nada aqui é calculado na tela** (regra 2.4): as somas, a diferença entre o
 * previsto e o medido e a ordem do risco vêm prontas de `/api/painel/decisao`.
 *
 * **Estimativa se distingue de medição.** O painel acima é medição; este bloco
 * leva a etiqueta "Estimativa" e a nota de qual modelo, com dados até quando —
 * o mesmo cuidado do cadastro do parceiro (H44). E diz que não acompanha o
 * período escolhido no painel: a previsão parte de onde o modelo foi treinado.
 *
 * Sem modelo treinado ou sem plano, o bloco diz o que falta, com o motivo que a
 * API manda. Sumir deixaria a pessoa sem saber que os outros módulos existem.
 */
import { Link } from "react-router-dom";

import {
  comoData,
  comoDataHora,
  comoDinheiro,
  comoInteiro,
  comoPercentual,
  comoProbabilidade,
  sentidoDa,
  TRACO,
} from "../formato";
import EstadoVazio from "./EstadoVazio";
import { IconeVariacao } from "./Icones";
import "../estilos/parceiros.css";
import "../estilos/painel.css";

/* O cadastro aberto daqui volta para o painel, como o aberto pelo ranking (H81). */
const DO_PAINEL = { lista: "/", rotuloLista: "Painel", voltarPara: "Voltar para o painel" };

export default function PrevisaoECampanha({ decisao }) {
  const { previsao, campanha, categoria } = decisao;

  return (
    <div className="painel-duplo">
      <Previsao previsao={previsao} categoria={categoria} />
      <Campanha campanha={campanha} categoria={categoria} />
    </div>
  );
}

function Previsao({ previsao, categoria }) {
  const sentido = sentidoDa(previsao.variacao_percentual);
  /* A lista inteira, na mesma ordem — e no mesmo recorte de categoria. */
  const todos = new URLSearchParams({ ordenar_por: "risco", descendente: "true" });
  if (categoria) todos.set("categoria_id", String(categoria.id));

  return (
    <section className="painel" aria-labelledby="titulo-proximo-periodo">
      <div className="painel__cabecalho">
        <h2 className="painel__titulo" id="titulo-proximo-periodo">
          Próximo período
        </h2>
        <span className="etiqueta-estimativa">Estimativa</span>
      </div>

      {previsao.disponivel ? (
        <>
          <dl className="decisao__numeros">
            <div>
              <dt>Faturamento previsto</dt>
              <dd className="num decisao__principal">
                {comoDinheiro(previsao.faturamento_previsto)}
              </dd>
            </div>
            <div>
              <dt>Medido, nos mesmos parceiros</dt>
              <dd className="num">{comoDinheiro(previsao.faturamento_medido)}</dd>
            </div>
            <div>
              <dt>Do medido para o previsto</dt>
              <dd className="num">
                {sentido === "indefinida" ? (
                  TRACO
                ) : (
                  <span className={`indicador__variacao indicador__variacao--${sentido}`}>
                    {sentido !== "estavel" && <IconeVariacao sentido={sentido} />}
                    {comoPercentual(previsao.variacao_percentual)}
                  </span>
                )}
              </dd>
            </div>
          </dl>
          <p className="previsao__nota">
            Soma de {comoInteiro(previsao.parceiros)}{" "}
            {previsao.parceiros === 1 ? "parceiro" : "parceiros"} com previsão
            {categoria ? ` em ${categoria.nome}` : ""}, pelo modelo {previsao.modelo_versao}, com
            dados até {comoData(previsao.periodo_base?.data_fim)}. É estimativa, e não medição — e
            parte desse período, e não do escolhido acima.
          </p>
          {previsao.desatualizada && (
            <p className="previsao__nota previsao__nota--alerta">
              Há período importado depois desta estimativa; o próximo treino a refaz.
            </p>
          )}

          <h3 className="decisao__subtitulo" id="titulo-maior-risco">
            Maior risco de queda
          </h3>
          <div className="tabela-rolagem">
            <table className="tabela" aria-labelledby="titulo-maior-risco">
              <thead>
                <tr>
                  <th scope="col">Parceiro</th>
                  <th scope="col">Categoria</th>
                  <th scope="col" className="numerica">
                    Medido
                  </th>
                  <th scope="col" className="numerica">
                    Previsto
                  </th>
                  <th scope="col" className="numerica">
                    Chance de queda
                  </th>
                </tr>
              </thead>
              <tbody>
                {previsao.maior_risco.map((parceiro) => (
                  <tr key={parceiro.parceiro_id}>
                    <td className="nome">
                      <Link
                        className="nome__link"
                        to={`/parceiros/${parceiro.parceiro_id}`}
                        state={DO_PAINEL}
                      >
                        {parceiro.nome}
                      </Link>
                    </td>
                    <td className="secundaria">{parceiro.categoria ?? "sem categoria"}</td>
                    <td className="numerica">{comoDinheiro(parceiro.faturamento)}</td>
                    <td className="numerica secundaria">
                      {comoDinheiro(parceiro.faturamento_previsto)}
                    </td>
                    <td className="numerica">{comoProbabilidade(parceiro.probabilidade_queda)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Link className="decisao__caminho" to={`/parceiros?${todos}`}>
            Ver todos os parceiros pelo risco
          </Link>
        </>
      ) : (
        <EstadoVazio titulo={previsao.motivo} texto={previsao.ajuda} />
      )}
    </section>
  );
}

function Campanha({ campanha, categoria }) {
  const { plano } = campanha;

  return (
    <section className="painel" aria-labelledby="titulo-ultima-campanha">
      <div className="painel__cabecalho">
        <h2 className="painel__titulo" id="titulo-ultima-campanha">
          Última campanha
        </h2>
        {plano && <span className="painel__nota">plano de {comoDataHora(plano.concluida_em)}</span>}
      </div>

      {plano ? (
        <>
          <dl className="desempenho">
            <dt>Ações</dt>
            <dd className="num">{comoInteiro(campanha.acoes)}</dd>
            <dt>Custo</dt>
            <dd className="num">{comoDinheiro(campanha.custo)}</dd>
            <dt>Ganho esperado</dt>
            <dd className="num">{comoDinheiro(campanha.ganho_esperado)}</dd>
            <dt>Aplicação</dt>
            <dd>
              {comoData(plano.aplicacao_inicio)} a {comoData(plano.aplicacao_fim)}
            </dd>
          </dl>
          <p className="previsao__nota">
            {categoria ? `Só as ações de parceiros de ${categoria.nome}. ` : ""}O ganho esperado é
            estimativa, pela previsão {plano.modelo_versao} (RN10).
          </p>
          <Link
            className="botao botao--secundario na-campanha__plano"
            to={`/execucoes/${plano.execucao_id}`}
          >
            Abrir o plano
          </Link>
        </>
      ) : (
        <EstadoVazio
          titulo="Nenhum plano de campanha calculado ainda"
          texto="O plano sai da tela Campanha, com o orçamento, o máximo de ações e as cotas."
          acao={{ para: "/campanha", rotulo: "Ir para a Campanha" }}
        />
      )}
    </section>
  );
}
