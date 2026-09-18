import { comoDinheiro, comoInteiro, comoPercentual, sentidoDa, TRACO } from "../formato";
import { IconeVariacao } from "./Icones";

/**
 * O ranking do período.
 *
 * O nome do parceiro é o **único** elemento em peso alto e tinta cheia. É assim
 * que o olho encontra a linha numa tabela densa, sem depender de contraste
 * extra nem de fundo alternado — `docs/09`, regra 1.2.
 *
 * Toda coluna numérica usa Fira Code com `tabular-nums`: dígito que não alinha
 * obriga a reler para comparar duas linhas.
 */

/** Quem estreou não caiu de lugar nenhum — e sem isto pareceria ter despencado. */
function Posicao({ atual, anterior, estreante }) {
  if (estreante) {
    return (
      <span className="posicao" title="Não tinha faturamento no período anterior">
        {atual} <span style={{ color: "var(--ink-2)" }}>· novo</span>
      </span>
    );
  }

  if (anterior === null || anterior === undefined) {
    return <span className="posicao">{atual}</span>;
  }

  const movimento = anterior - atual;
  const sentido = movimento > 0 ? "sobe" : movimento < 0 ? "cai" : null;

  return (
    <span className="posicao">
      {atual}
      {sentido && (
        <span
          className={`indicador__variacao indicador__variacao--${sentido}`}
          style={{ marginLeft: "var(--esp-6)" }}
          title={`Era ${anterior} no período anterior`}
        >
          <IconeVariacao sentido={sentido} />
          {Math.abs(movimento)}
        </span>
      )}
    </span>
  );
}

export default function TabelaRanking({ itens }) {
  return (
    <div className="tabela-rolagem">
      <table className="tabela">
        <caption className="so-leitor">Ranking de parceiros por faturamento no período</caption>
        <thead>
          <tr>
            <th scope="col">Posição</th>
            <th scope="col">Parceiro</th>
            <th scope="col">Categoria</th>
            <th scope="col" className="numerica">
              Faturamento
            </th>
            <th scope="col" className="numerica">
              Pedidos
            </th>
            <th scope="col" className="numerica">
              Ticket médio
            </th>
            <th scope="col" className="numerica">
              Variação
            </th>
          </tr>
        </thead>
        <tbody>
          {itens.map((item) => {
            const sentido = sentidoDa(item.variacao_percentual);
            return (
              <tr key={item.parceiro_id}>
                <td>
                  <Posicao
                    atual={item.posicao}
                    anterior={item.posicao_anterior}
                    estreante={item.estreante}
                  />
                </td>
                <td className="nome">{item.nome}</td>
                <td className="secundaria">{item.categoria ?? "sem categoria"}</td>
                <td className="numerica">{comoDinheiro(item.faturamento)}</td>
                <td className="numerica">{comoInteiro(item.pedidos)}</td>
                <td className="numerica secundaria">{comoDinheiro(item.ticket_medio)}</td>
                <td className="numerica">
                  {sentido === "indefinida" ? (
                    <span style={{ color: "var(--ink-2)" }}>{TRACO}</span>
                  ) : (
                    <span className={`indicador__variacao indicador__variacao--${sentido}`}>
                      {sentido !== "estavel" && <IconeVariacao sentido={sentido} />}
                      {comoPercentual(item.variacao_percentual)}
                    </span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
