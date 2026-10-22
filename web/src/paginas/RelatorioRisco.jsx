/**
 * Parceiros em risco — o relatório inteiro é estimativa. A chance mínima é um
 * filtro de quem consulta (a pessoa digita %, a tela manda a fração), e não um
 * limiar do sistema.
 */
import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";

import { api, comConsulta } from "../api/cliente";
import { useAtraso, useCarregar, useFiltros } from "../api/ganchos";
import { tem, useSessao } from "../api/sessao";
import { Ausente, Chance, Dinheiro, Estimativa, Segmento, Variacao } from "../componentes/Dados";
import { Carregando, ErroDaTela, Vazio } from "../componentes/Estados";
import FolhaDeRelatorio from "../componentes/FolhaDeRelatorio";
import Kpi from "../componentes/Kpi";
import { CaixaDeTabela, Paginacao } from "../componentes/Lista";
import Seletor from "../componentes/Seletor";
import { useTitulo } from "../componentes/Titulo";
import { comoData, comoDinheiro, comoInteiro, comoPeriodo, deFracao, ORDEM_SEGMENTOS, paraFracao, ROTULO_ORIGEM_PREVISAO, ROTULO_SEGMENTO } from "../formato";

const TAMANHO = 25;

export default function RelatorioRisco() {
  useTitulo("Parceiros em risco", "Relatórios");
  const { usuario } = useSessao();
  const lugar = useLocation();
  const [filtros, mudar] = useFiltros();
  const pagina = Number(filtros.pagina) || 1;
  const consulta = { categoria_id: filtros.categoria_id, segmento: filtros.segmento, risco_minimo: filtros.risco_minimo };
  const categorias = useCarregar(() => api.get("/api/categorias"), "cat");
  const rel = useCarregar(() => api.get("/api/relatorios/risco", { ...consulta, pagina, tamanho: TAMANHO }), lugar.search);
  const r = rel.dados;

  const [minimo, setMinimo] = useState(filtros.risco_minimo ? deFracao(filtros.risco_minimo) : "");
  const minimoAtrasado = useAtraso(minimo, 500);
  useEffect(() => {
    const fracao = paraFracao(minimoAtrasado);
    if ((fracao ?? "") !== (filtros.risco_minimo ?? "")) mudar({ risco_minimo: fracao });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [minimoAtrasado]);

  const filtrosForm = (
    <>
      <Seletor id="f-categoria" rotulo="Categoria" valor={filtros.categoria_id} aoMudar={(v) => mudar({ categoria_id: v })} todos="Todas as categorias" opcoes={(categorias.dados ?? []).map((c) => [c.id, c.nome])} />
      <Seletor id="f-segmento" rotulo="Segmento" valor={filtros.segmento} aoMudar={(v) => mudar({ segmento: v })} todos="Todos os segmentos" opcoes={ORDEM_SEGMENTOS.map((s) => [s, ROTULO_SEGMENTO[s]])} />
      <div className="campo">
        <label className="campo__rotulo" htmlFor="f-minimo">
          Chance de queda a partir de (%)
        </label>
        <input id="f-minimo" className="entrada entrada--numero" inputMode="decimal" value={minimo} onChange={(e) => setMinimo(e.target.value)} aria-describedby="f-minimo-ajuda" />
        <p className="campo__ajuda" id="f-minimo-ajuda">
          Em branco, entram todos — inclusive quem não tem previsão.
        </p>
      </div>
    </>
  );

  const recorte = r ? [r.categoria?.nome ?? "Todas as categorias", r.segmento ? ROTULO_SEGMENTO[r.segmento] : "Todos os segmentos", r.risco_minimo !== null && r.risco_minimo !== undefined ? `chance de queda a partir de ${deFracao(r.risco_minimo)}%` : null].filter(Boolean).join(" · ") : null;
  const variasPaginas = r && r.total > TAMANHO;

  return (
    <FolhaDeRelatorio
      nome="Parceiros em risco"
      filtros={filtrosForm}
      recorte={recorte}
      csv={r?.disponivel ? comConsulta("/api/relatorios/risco/exportacao.csv", consulta) : null}
      notaDaImpressao={variasPaginas ? `Esta folha mostra a página ${pagina} de ${Math.ceil(r.total / TAMANHO)}; o CSV traz o recorte inteiro.` : null}
    >
      {rel.carregando && <Carregando rotulo="Carregando o relatório" linhas={8} />}
      <ErroDaTela erro={rel.erro}>
        <p>Os filtros continuam acima para escolher outro recorte.</p>
      </ErroDaTela>
      {r && !r.disponivel && (
        <Vazio titulo={r.motivo ?? "Ainda não há previsão."} icone="modelo" acao={tem(usuario, "modelo") ? "Ir para o Modelo" : undefined} para="/modelo">
          {r.ajuda}
        </Vazio>
      )}
      {r && r.disponivel && (
        <>
          <p className="nota-estimativa folha__nota-estimativa">
            <Estimativa />
            <span>
              Pela {r.origem === "REFERENCIA" ? "referência" : "versão"} {r.modelo_versao} ({ROTULO_ORIGEM_PREVISAO[r.origem] ?? r.origem}). Previsão a partir do período de {comoPeriodo(r.periodo_base)}.
              {r.desatualizada && " Há período importado depois desse: o próximo treino refaz a previsão."}
            </span>
          </p>
          <section className="folha__secao" aria-labelledby="t-resumo">
            <h3 id="t-resumo" className="folha__subtitulo">
              Resumo do recorte
            </h3>
            <div className="faixa-kpi__grade faixa-kpi__grade--cinco">
              <Kpi rotulo="Parceiros">{comoInteiro(r.total)}</Kpi>
              <Kpi rotulo="Com previsão">{comoInteiro(r.com_previsao)}</Kpi>
              <Kpi rotulo="Medido, de quem tem previsão">
                <Dinheiro valor={r.faturamento_medido} grande />
              </Kpi>
              <Kpi rotulo="Previsto para o próximo período" className="kpi--estimado">
                <Dinheiro valor={r.faturamento_previsto} grande />
              </Kpi>
              <Kpi rotulo="No último plano">{comoInteiro(r.no_plano)}</Kpi>
            </div>
          </section>
          {!r.itens.length ? (
            <Vazio titulo="Nenhum parceiro nesse recorte" icone="busca">
              Não há parceiro com esses filtros. Diminua a chance de queda ou troque a categoria.
            </Vazio>
          ) : (
            <section className="folha__secao" aria-labelledby="t-lista">
              <h3 id="t-lista" className="folha__subtitulo">
                Parceiros, do maior risco para o menor
              </h3>
              {!r.plano && <p className="bloco__nota">A coluna "Ação no plano" fica vazia porque nenhum plano de campanha viável foi calculado ainda.</p>}
              <CaixaDeTabela rotulo="Parceiros em risco">
                <table className="tabela">
                  <caption className="sr-only">Parceiros, do maior risco de queda para o menor (estimativa)</caption>
                  <thead>
                    <tr>
                      <th scope="col">Parceiro</th>
                      <th scope="col">Categoria</th>
                      <th scope="col">Segmento</th>
                      <th scope="col" className="num">
                        Faturamento
                      </th>
                      <th scope="col" className="num">
                        Variação
                      </th>
                      <th scope="col" className="num">
                        Previsto
                      </th>
                      <th scope="col" className="num">
                        Chance de queda
                      </th>
                      <th scope="col">Ação no plano</th>
                    </tr>
                  </thead>
                  <tbody>
                    {r.itens.map((l) => (
                      <tr key={l.parceiro_id}>
                        <th scope="row" className="nome">
                          {tem(usuario, "parceiros") ? (
                            <Link to={`/parceiros/${l.parceiro_id}`} state={{ de: "risco", busca: lugar.search }}>
                              {l.nome}
                            </Link>
                          ) : (
                            l.nome
                          )}
                        </th>
                        <td>{l.categoria ?? <Ausente porque="sem categoria confirmada" />}</td>
                        <td>
                          <Segmento codigo={l.segmento} />
                        </td>
                        <td className="num">{comoDinheiro(l.faturamento)}</td>
                        <td className="num">
                          <Variacao valor={l.variacao_percentual} semBase="sem variação calculável" />
                        </td>
                        <td className="num">{l.faturamento_previsto === null ? <Ausente porque={l.sem_previsao ?? "sem previsão"} /> : comoDinheiro(l.faturamento_previsto)}</td>
                        <td className="num">{l.probabilidade_queda === null ? <span className="discreto texto-pequeno">{l.sem_previsao ?? "Sem previsão"}</span> : <Chance valor={l.probabilidade_queda} />}</td>
                        <td>{l.acao ?? (r.plano ? <span className="discreto">fora do último plano</span> : <Ausente porque="nenhum plano calculado" />)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CaixaDeTabela>
              {r.plano && <p className="bloco__nota">A ação é a do último plano viável, com aplicação de {comoData(r.plano.aplicacao_inicio)} a {comoData(r.plano.aplicacao_fim)}.</p>}
              <div className="nao-imprime">
                <Paginacao pagina={pagina} tamanho={TAMANHO} total={r.total} aoMudar={(p) => mudar({ pagina: p > 1 ? p : null }, { manterPagina: true })} rotulo="parceiros" />
              </div>
            </section>
          )}
        </>
      )}
    </FolhaDeRelatorio>
  );
}
