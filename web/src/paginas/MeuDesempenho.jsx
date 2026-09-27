/**
 * O portal do Parceiro — UC13, RF19, RF26, história H39.
 *
 * **O histórico dele, e nada da rede.** Os três indicadores do período mais
 * recente contra o anterior dele, e a série em gráfico, com a tabela como
 * alternativa (UC13, passos 2 e 3). Sem ranking, sem posição, sem comparação com
 * outros parceiros: é requisito, e não simplificação (RF26).
 *
 * **De quem é o histórico, quem diz é a API**, pelo vínculo da sessão: a tela não
 * manda identificador nenhum, e não há o que trocar na URL para ver o de outro
 * (UC13-E1).
 *
 * Os componentes são os do painel — o indicador e a série —, já validados no
 * contraste e na leitura sem cor (`docs/09`).
 */
import { useEffect, useState } from "react";

import { api } from "../api/cliente";
import { Esqueleto } from "../componentes/Carregando";
import EstadoVazio from "../componentes/EstadoVazio";
import Indicador from "../componentes/Indicador";
import SerieHistorica from "../componentes/SerieHistorica";
import { comoDinheiro, comoInteiro, comoPeriodo, TRACO } from "../formato";

export default function MeuDesempenho() {
  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState(null);

  useEffect(() => {
    let vivo = true;
    api
      .get("/api/meu-desempenho")
      .then((corpo) => vivo && setDados(corpo))
      .catch((e) => vivo && setErro(e));
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

  if (!dados) {
    return (
      <section className="painel" aria-busy="true" aria-label="Carregando o seu desempenho">
        <Esqueleto altura={220} />
      </section>
    );
  }

  /* UC13-A1: parceiro recém-cadastrado. Não é erro, é o começo. */
  if (!dados.pontos.length) {
    return (
      <EstadoVazio
        titulo={`${dados.parceiro}: seus números ainda não chegaram.`}
        texto="Eles aparecem aqui depois da primeira importação de relatório que incluir o seu comércio."
      />
    );
  }

  const { atual, anterior, variacao } = dados;
  const semDados = atual.faturamento === null;
  const nota = semDados ? "sem dados neste período" : undefined;

  return (
    <>
      <div className="painel__cabecalho" style={{ border: "none", padding: 0 }}>
        <div>
          <h2 className="painel__titulo">
            {dados.parceiro}
            {dados.categoria ? ` · ${dados.categoria}` : ""}
          </h2>
          <p className="painel__nota">
            Período de {comoPeriodo(atual.periodo)}
            {anterior ? `, comparado com ${comoPeriodo(anterior)}` : " — o primeiro com os seus números"}. Só os seus
            números: nenhum outro parceiro aparece aqui.
          </p>
        </div>
      </div>

      {semDados && (
        <div className="aviso aviso--informativo">
          <p className="aviso__titulo">O último relatório não trouxe o seu comércio.</p>
          <p className="aviso__ajuda">
            Os indicadores do período ficam vazios, e o gráfico mostra a falta como um intervalo, e não como zero.
          </p>
        </div>
      )}

      <section className="indicadores" aria-label="Os seus indicadores do período">
        <Indicador
          rotulo="Faturamento"
          valor={semDados ? TRACO : comoDinheiro(atual.faturamento)}
          variacao={variacao?.faturamento}
          nota={nota}
        />
        <Indicador
          rotulo="Pedidos"
          valor={semDados ? TRACO : comoInteiro(atual.pedidos)}
          variacao={variacao?.pedidos}
          nota={nota}
        />
        <Indicador
          rotulo="Ticket médio"
          valor={semDados || atual.ticket_medio === null ? TRACO : comoDinheiro(atual.ticket_medio)}
          variacao={variacao?.ticket_medio}
          nota={nota}
        />
      </section>

      <section className="painel" aria-labelledby="titulo-serie">
        <div className="painel__cabecalho">
          <h2 className="painel__titulo" id="titulo-serie">
            Seu faturamento
          </h2>
          <span className="painel__nota">
            {dados.pontos.length} {dados.pontos.length === 1 ? "período" : "períodos"}, desde a sua primeira medição
          </span>
        </div>
        <SerieHistorica pontos={dados.pontos} />
      </section>
    </>
  );
}
