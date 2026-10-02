/**
 * Painel: indicadores, série histórica e ranking (UC05).
 *
 * Resumo antes do detalhe, como o `docs/09` manda: os números consolidados no
 * topo, o gráfico no meio, a tabela por último. É a ordem em que a pergunta se
 * forma — "como foi o período?", depois "como vinha sendo?", depois "quem".
 *
 * **Nenhum cálculo acontece aqui** (regra 2.4). Variação, ticket médio e
 * posição vêm prontos da API; a tela formata e desenha.
 *
 * **O recorte (H82, UC05-A4).** O período e a categoria ficam no endereço, como
 * os filtros da lista de parceiros: recarregar ou mandar o link abre o mesmo
 * painel. A categoria escolhe quem entra, e não renumera — a posição do
 * ranking e a mobilidade do Top N continuam as da rede inteira (RN02), e a
 * tela diz isso onde os dois aparecem. A tela não deduz o recorte do endereço:
 * a categoria que ela escreve é a que a API devolve.
 *
 * **A previsão e a campanha (H83, UC05-A5)** entram entre o gráfico e o
 * ranking, para quem a API autoriza (`painel_decisao` nas telas do usuário): o
 * Administrador lê o painel e não abre a campanha, e não vê o bloco.
 */
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { api } from "../api/cliente";
import { useSessao } from "../api/contextoSessao";
import { Esqueleto } from "../componentes/Carregando";
import EstadoVazio from "../componentes/EstadoVazio";
import DistribuicaoSegmentos from "../componentes/DistribuicaoSegmentos";
import Indicador from "../componentes/Indicador";
import PrevisaoECampanha from "../componentes/PrevisaoECampanha";
import SerieHistorica from "../componentes/SerieHistorica";
import TabelaRanking from "../componentes/TabelaRanking";
import { comoDinheiro, comoInteiro, comoPeriodo, TRACO } from "../formato";
import "../estilos/painel.css";

export default function Painel() {
  const { usuario } = useSessao();
  const veADecisao = Boolean(usuario?.telas?.includes("painel_decisao"));

  const [parametros, setParametros] = useSearchParams();
  const periodo = parametros.get("periodo") ?? "";
  const categoria = parametros.get("categoria") ?? "";
  const recorte = `${periodo}|${categoria}`;

  const [recortes, setRecortes] = useState(null);
  const [estado, setEstado] = useState({ recorte: null, dados: null, erro: null });
  const [decisao, setDecisao] = useState({ categoria: null, dados: null });

  useEffect(() => {
    /* O que dá para escolher. Se falhar, o painel abre no período mais recente,
       como sempre abriu — só não oferece os seletores. */
    api
      .get("/api/painel/recortes")
      .then(setRecortes)
      .catch(() => setRecortes(null));
  }, []);

  useEffect(() => {
    let vivo = true;
    const filtro = { periodo_id: periodo, categoria_id: categoria };

    Promise.all([
      api.get("/api/painel/indicadores", filtro),
      api.get("/api/painel/ranking", { ...filtro, tamanho: 25 }),
      api.get("/api/painel/series", filtro),
      api.get("/api/painel/segmentos", filtro),
      /* Sem a categoria: o Top N é da rede inteira (RN02). */
      api.get("/api/painel/mobilidade", { periodo_id: periodo }),
    ])
      .then(([indicadores, ranking, serie, segmentos, mobilidade]) => {
        if (vivo) {
          setEstado({
            recorte,
            dados: { indicadores, ranking, serie, segmentos, mobilidade },
            erro: null,
          });
        }
      })
      .catch((erro) => {
        if (vivo) setEstado({ recorte, dados: null, erro });
      });

    /* A resposta pode chegar depois de a pessoa sair da tela — ou de trocar o
       recorte. Escrever estado num componente desmontado é vazamento, e a
       resposta do recorte antigo por cima do novo mostraria o painel errado. */
    return () => {
      vivo = false;
    };
  }, [recorte, periodo, categoria]);

  useEffect(() => {
    if (!veADecisao) return undefined;
    let vivo = true;
    /* Só a categoria: a previsão parte de onde o modelo foi treinado, e o plano
       é o último calculado — nenhum dos dois muda com o período escolhido. Se
       falhar, o painel continua inteiro, sem o bloco. */
    api
      .get("/api/painel/decisao", { categoria_id: categoria })
      .then((dados) => vivo && setDecisao({ categoria, dados }))
      .catch(() => vivo && setDecisao({ categoria, dados: null }));
    return () => {
      vivo = false;
    };
  }, [veADecisao, categoria]);

  function ajustar(mudancas) {
    const proximos = new URLSearchParams(parametros);
    Object.entries(mudancas).forEach(([chave, valor]) =>
      valor ? proximos.set(chave, valor) : proximos.delete(chave),
    );
    setParametros(proximos, { replace: true });
  }

  const atual = estado.recorte === recorte;
  const dados = atual ? estado.dados : null;
  const erro = atual ? estado.erro : null;
  const maisRecente = recortes?.periodos[0];

  /* UC05, A1 — base vazia. Não é erro: é quem ainda não importou nada. */
  if (dados && !dados.indicadores.periodo) {
    return (
      <EstadoVazio
        titulo="Nenhum dado importado ainda"
        texto="O painel mostra o desempenho da rede a partir dos relatórios importados. Comece pelo primeiro."
        acao={{ para: "/importacao", rotulo: "Importar um relatório" }}
      />
    );
  }

  return (
    <>
      {maisRecente && (
        <section className="painel recorte" aria-label="Recorte do painel">
          <div className="campo">
            <label htmlFor="periodo">Período</label>
            <select
              id="periodo"
              value={periodo || String(maisRecente.id)}
              /* O mais recente é o padrão, e fica fora do endereço: o link de
                 quem não escolheu período continua abrindo no mais recente
                 depois da próxima importação. */
              onChange={(e) =>
                ajustar({ periodo: e.target.value === String(maisRecente.id) ? "" : e.target.value })
              }
            >
              {/* Endereço com período que não existe: o seletor não finge que
                  está no mais recente enquanto a página mostra o erro. */}
              {periodo && !recortes.periodos.some((p) => String(p.id) === periodo) && (
                <option value={periodo}>Escolha um período</option>
              )}
              {recortes.periodos.map((p) => (
                <option key={p.id} value={p.id}>
                  {comoPeriodo(p)}
                </option>
              ))}
            </select>
          </div>
          <div className="campo">
            <label htmlFor="categoria">Categoria</label>
            <select
              id="categoria"
              value={categoria}
              onChange={(e) => ajustar({ categoria: e.target.value })}
            >
              <option value="">Rede inteira</option>
              {categoria && !recortes.categorias.some((c) => String(c.id) === categoria) && (
                <option value={categoria}>Escolha uma categoria</option>
              )}
              {recortes.categorias.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nome}
                </option>
              ))}
            </select>
          </div>
          {dados && <p className="recorte__nota">{comparacao(dados.indicadores)}</p>}
        </section>
      )}

      {erro && (
        <div className="aviso" role="alert">
          <p className="aviso__titulo">{erro.message}</p>
          {erro.ajuda && <p className="aviso__ajuda">{erro.ajuda}</p>}
        </div>
      )}

      {!dados && !erro && <PainelCarregando />}

      {dados && (
        <Conteudo
          dados={dados}
          semSeletores={!maisRecente}
          /* O segmento que a lista de parceiros mostra é o do período mais
             recente. De outro período, o número daqui não é o que a lista
             encontraria — e por isso o caminho para ela não aparece. */
          noMaisRecente={!maisRecente || dados.indicadores.periodo.id === maisRecente.id}
          decisao={veADecisao && decisao.categoria === categoria ? decisao.dados : null}
        />
      )}
    </>
  );
}

/** Contra o que o período se compara — ou por que não há com o que comparar. */
function comparacao(indicadores) {
  /* UC05, A2 — período único: não há com que comparar, e toda variação vem
     nula. O aviso é o que impede alguém de ler os travessões como defeito. */
  if (!indicadores.periodo_anterior) {
    return "Primeiro período importado — variação e tendência exigem histórico.";
  }
  const anterior = `Comparado com ${comoPeriodo(indicadores.periodo_anterior)}`;
  return indicadores.categoria ? `${anterior}, na mesma categoria.` : `${anterior}.`;
}

function Conteudo({ dados, semSeletores, noMaisRecente, decisao }) {
  const { indicadores, ranking, serie, segmentos, mobilidade } = dados;
  const { categoria } = indicadores;
  /* A lista de parceiros no mesmo recorte de categoria do painel. */
  const naLista = (filtros) => {
    const busca = new URLSearchParams(filtros);
    if (categoria) busca.set("categoria_id", String(categoria.id));
    return `/parceiros?${busca}`;
  };

  return (
    <>
      {semSeletores && (
        <div className="painel__cabecalho" style={{ border: "none", padding: 0 }}>
          <div>
            <p className="painel__titulo">Período de {comoPeriodo(indicadores.periodo)}</p>
            <p className="painel__nota">{comparacao(indicadores)}</p>
          </div>
        </div>
      )}

      <section
        className="indicadores"
        aria-label={
          categoria
            ? `Indicadores consolidados do período, em ${categoria.nome}`
            : "Indicadores consolidados do período"
        }
      >
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
        {/* Mais parceiros em risco é a única notícia ruim da fileira: a seta
            continua dizendo que o número subiu, mas a cor deixa de ser a de
            crescimento. Sem `subirEBom={false}`, o painel pintaria de verde
            justamente o indicador que pede ação. */}
        <Indicador
          rotulo="Em risco"
          valor={indicadores.em_risco ? comoInteiro(indicadores.em_risco.total) : TRACO}
          variacao={indicadores.em_risco?.delta}
          absoluta
          subirEBom={false}
          nota={
            indicadores.em_risco
              ? undefined
              : "Segmentação ainda não calculada para este período"
          }
          acao={
            indicadores.em_risco?.total && noMaisRecente
              ? { para: naLista({ segmento: "EM_RISCO" }), rotulo: "Ver quem está em risco" }
              : undefined
          }
        />
        <Indicador
          rotulo={`Mobilidade Top ${mobilidade.top_n}`}
          valor={comoInteiro(mobilidade.entradas.length)}
          nota={
            mobilidade.periodo_anterior
              ? /* O Top N é da rede (RN02): com categoria, o número não é só dela. */
                `entraram · ${mobilidade.saidas.length} saíram${categoria ? " · na rede inteira" : ""}`
              : "exige um período anterior para comparar"
          }
        />
      </section>

      {/* O gráfico ocupa o dobro da distribuição: a série tem doze pontos e um
          eixo, a distribuição tem meia dúzia de barras. Abaixo de 1000 px as
          duas empilham — ver `componentes.css`. */}
      <div className="painel-duplo">
        <section className="painel" aria-labelledby="titulo-serie">
          <div className="painel__cabecalho">
            <h2 className="painel__titulo" id="titulo-serie">
              {serie.categoria ? `Faturamento de ${serie.categoria.nome}` : "Faturamento da rede"}
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

        <section className="painel" aria-labelledby="titulo-segmentos">
          <div className="painel__cabecalho">
            <h2 className="painel__titulo" id="titulo-segmentos">
              Distribuição por segmento
            </h2>
            <span className="painel__nota">
              {segmentos.total ? `${comoInteiro(segmentos.total)} parceiros` : ""}
            </span>
          </div>
          <DistribuicaoSegmentos
            itens={segmentos.itens}
            total={segmentos.total}
            para={noMaisRecente ? (segmento) => naLista({ segmento }) : null}
          />
        </section>
      </div>

      {decisao && <PrevisaoECampanha decisao={decisao} />}

      <section className="painel" aria-labelledby="titulo-ranking">
        <div className="painel__cabecalho">
          <h2 className="painel__titulo" id="titulo-ranking">
            Ranking de parceiros
          </h2>
          <span className="painel__nota">
            {ranking.itens.length} de {comoInteiro(ranking.total)}
            {/* A categoria escolhe quem aparece, e não renumera (RN02). */}
            {ranking.categoria ? " · posição na rede inteira" : ""}
          </span>
        </div>
        {ranking.itens.length ? (
          <TabelaRanking itens={ranking.itens} />
        ) : (
          <EstadoVazio
            titulo={
              ranking.categoria
                ? `Nenhum parceiro de ${ranking.categoria.nome} com movimento neste período`
                : "Nenhum parceiro com movimento neste período"
            }
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
