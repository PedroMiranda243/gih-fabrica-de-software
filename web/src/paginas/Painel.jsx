/**
 * Painel: indicadores, série histórica e ranking (UC05).
 *
 * Resumo antes do detalhe, como o `docs/09` manda: os números consolidados no
 * topo, o gráfico no meio, a tabela por último. É a ordem em que a pergunta se
 * forma — "como foi o período?", depois "como vinha sendo?", depois "quem".
 *
 * **Nenhum cálculo acontece aqui** (regra 2.4). Variação, ticket médio e
 * posição vêm prontos da API; a tela formata e desenha.
 */
import { useEffect, useState } from "react";

import { api } from "../api/cliente";
import { Esqueleto } from "../componentes/Carregando";
import EstadoVazio from "../componentes/EstadoVazio";
import Indicador from "../componentes/Indicador";
import SerieHistorica from "../componentes/SerieHistorica";
import TabelaRanking from "../componentes/TabelaRanking";
import { comoDinheiro, comoInteiro, comoPeriodo } from "../formato";

export default function Painel() {
  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState(null);

  useEffect(() => {
    let vivo = true;

    Promise.all([
      api.get("/api/painel/indicadores"),
      api.get("/api/painel/ranking", { tamanho: 25 }),
      api.get("/api/painel/series"),
    ])
      .then(([indicadores, ranking, serie]) => {
        if (vivo) setDados({ indicadores, ranking, serie });
      })
      .catch((e) => {
        if (vivo) setErro(e);
      });

    /* A resposta pode chegar depois de a pessoa sair da tela. Escrever estado
       num componente desmontado é vazamento, e o aviso do React some no meio
       do console sem ninguém investigar. */
    return () => {
      vivo = false;
    };
  }, []);

  if (erro) {
    return (
      <div className="aviso" role="alert">
        <p className="aviso__titulo">{erro.message}</p>
        {erro.ajuda && <p className="aviso__ajuda">{erro.ajuda}</p>}
      </div>
    );
  }

  if (!dados) return <PainelCarregando />;

  const { indicadores, ranking, serie } = dados;

  /* UC05, A1 — base vazia. Não é erro: é quem ainda não importou nada. */
  if (!indicadores.periodo) {
    return (
      <EstadoVazio
        titulo="Nenhum dado importado ainda"
        texto="O painel mostra o desempenho da rede a partir dos relatórios importados. Comece pelo primeiro."
        acao={{ para: "/importacao", rotulo: "Importar um relatório" }}
      />
    );
  }

  /* UC05, A2 — período único: não há com que comparar, e toda variação vem
     nula. O aviso é o que impede alguém de ler os travessões como defeito. */
  const periodoUnico = !indicadores.periodo_anterior;

  return (
    <>
      <div className="painel__cabecalho" style={{ border: "none", padding: 0 }}>
        <div>
          <p className="painel__titulo">Período de {comoPeriodo(indicadores.periodo)}</p>
          <p className="painel__nota">
            {periodoUnico
              ? "Primeiro período importado — variação e tendência exigem histórico."
              : `Comparado com ${comoPeriodo(indicadores.periodo_anterior)}`}
          </p>
        </div>
      </div>

      <section className="indicadores" aria-label="Indicadores consolidados do período">
        <Indicador
          rotulo="Faturamento"
          valor={comoDinheiro(indicadores.faturamento)}
          variacao={indicadores.variacao?.faturamento}
        />
        <Indicador
          rotulo="Pedidos"
          valor={comoInteiro(indicadores.pedidos)}
          variacao={indicadores.variacao?.pedidos}
        />
        <Indicador
          rotulo="Ticket médio"
          valor={comoDinheiro(indicadores.ticket_medio)}
          variacao={indicadores.variacao?.ticket_medio}
        />
        <Indicador
          rotulo="Parceiros ativos"
          valor={comoInteiro(indicadores.parceiros_ativos)}
          variacao={indicadores.variacao?.parceiros_ativos}
        />
      </section>

      <section className="painel" aria-labelledby="titulo-serie">
        <div className="painel__cabecalho">
          <h2 className="painel__titulo" id="titulo-serie">
            Faturamento da rede
          </h2>
          <span className="painel__nota">
            {serie.pontos.length} {serie.pontos.length === 1 ? "período" : "períodos"}
          </span>
        </div>
        {serie.pontos.length ? (
          <SerieHistorica pontos={serie.pontos} />
        ) : (
          <EstadoVazio titulo="Sem série para mostrar" texto="Nenhum período importado ainda." />
        )}
      </section>

      <section className="painel" aria-labelledby="titulo-ranking">
        <div className="painel__cabecalho">
          <h2 className="painel__titulo" id="titulo-ranking">
            Ranking de parceiros
          </h2>
          <span className="painel__nota">
            {ranking.itens.length} de {comoInteiro(ranking.total)}
          </span>
        </div>
        {ranking.itens.length ? (
          <TabelaRanking itens={ranking.itens} />
        ) : (
          <EstadoVazio
            titulo="Nenhum parceiro com movimento neste período"
            texto="O ranking lista quem teve faturamento no período selecionado."
          />
        )}
      </section>
    </>
  );
}

/**
 * Esqueleto com **o mesmo formato** do conteúdo que vem.
 *
 * Reservar o espaço é o que impede a página de saltar quando o dado chega —
 * conteúdo que pula ao carregar é a diferença entre parecer pronto e parecer
 * quebrado.
 */
function PainelCarregando() {
  return (
    <div role="status" aria-label="Carregando o painel">
      <div className="indicadores" style={{ marginBottom: "var(--esp-20)" }}>
        {[0, 1, 2, 3].map((i) => (
          <Esqueleto key={i} altura={96} />
        ))}
      </div>
      <Esqueleto altura={280} style={{ marginBottom: "var(--esp-20)" }} />
      <Esqueleto altura={320} />
    </div>
  );
}
