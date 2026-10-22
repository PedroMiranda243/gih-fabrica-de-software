/**
 * Painel — "como foi?", "como vinha sendo?", "quem?": indicadores no topo, a série
 * no meio, o ranking por último. O recorte (período e categoria) mora no endereço.
 */
import { Link } from "react-router-dom";

import { api, comConsulta } from "../api/cliente";
import { useCarregar, useFiltros } from "../api/ganchos";
import { tem, useSessao } from "../api/contextoSessao";
import { Ausente, Chance, Delta, Dinheiro, Estimativa, Segmento, Variacao } from "../componentes/Dados";
import { Carregando, ErroDaTela, Vazio } from "../componentes/Estados";
import Icone from "../componentes/Icone";
import Kpi from "../componentes/Kpi";
import Lacre from "../componentes/Lacre";
import { CaixaDeTabela, Paginacao } from "../componentes/Lista";
import Serie from "../componentes/Serie";
import { useTitulo } from "../componentes/Titulo";
import { comoData, comoDinheiro, comoInteiro, comoPeriodo, plural, ROTULO_ORIGEM_PREVISAO } from "../formato";

const TAMANHO_RANKING = 25;

export default function Painel() {
  useTitulo("Painel");
  const { usuario } = useSessao();
  const [filtros, mudar] = useFiltros();
  const recortes = useCarregar(() => api.get("/api/painel/recortes"), "recortes");

  if (recortes.carregando) return <Carregando rotulo="Carregando o painel" linhas={6} />;
  if (recortes.erro) return <ErroDaTela erro={recortes.erro} />;

  const { periodos, categorias } = recortes.dados;
  if (!periodos.length) {
    return (
      <Vazio titulo="Nenhum dado importado ainda" acao={tem(usuario, "importar") ? "Importar um relatório" : undefined} para="/importacao" icone="importacao">
        O painel mostra o desempenho da rede a partir dos relatórios importados. Comece pelo primeiro.
      </Vazio>
    );
  }

  const periodoId = filtros.periodo_id ? Number(filtros.periodo_id) : periodos[0].id;
  const categoriaId = filtros.categoria_id ? Number(filtros.categoria_id) : null;
  const maisRecente = periodoId === periodos[0].id;
  const categoria = categorias.find((c) => c.id === categoriaId) ?? null;

  return (
    <div className="pagina pagina--painel">
      <Recorte periodos={periodos} categorias={categorias} periodoId={periodoId} categoriaId={categoriaId} aoMudar={mudar} />
      <ConteudoDoPainel
        key={`${periodoId}-${categoriaId}`}
        periodoId={periodoId}
        categoria={categoria}
        categoriaId={categoriaId}
        maisRecente={maisRecente}
        pagina={Number(filtros.pagina) || 1}
        aoMudarPagina={(p) => mudar({ pagina: p > 1 ? p : null }, { manterPagina: true })}
        usuario={usuario}
      />
    </div>
  );
}

function Recorte({ periodos, categorias, periodoId, categoriaId, aoMudar }) {
  return (
    <form className="recorte" aria-label="Recorte do painel" onSubmit={(e) => e.preventDefault()}>
      <div className="campo campo--em-linha">
        <label className="campo__rotulo" htmlFor="recorte-periodo">
          Período
        </label>
        <select id="recorte-periodo" className="entrada" value={periodoId} onChange={(e) => aoMudar({ periodo_id: Number(e.target.value) === periodos[0].id ? null : e.target.value })}>
          {periodos.map((p, i) => (
            <option key={p.id} value={p.id}>
              {comoPeriodo(p)}
              {i === 0 ? " (mais recente)" : ""}
            </option>
          ))}
        </select>
      </div>
      <div className="campo campo--em-linha">
        <label className="campo__rotulo" htmlFor="recorte-categoria">
          Categoria
        </label>
        <select id="recorte-categoria" className="entrada" value={categoriaId ?? ""} onChange={(e) => aoMudar({ categoria_id: e.target.value })}>
          <option value="">Rede inteira</option>
          {categorias.map((c) => (
            <option key={c.id} value={c.id}>
              {c.nome}
            </option>
          ))}
        </select>
      </div>
    </form>
  );
}

function ConteudoDoPainel({ periodoId, categoria, categoriaId, maisRecente, pagina, aoMudarPagina, usuario }) {
  const recorte = { periodo_id: periodoId, categoria_id: categoriaId };
  const indicadores = useCarregar(() => api.get("/api/painel/indicadores", recorte), "i");
  const mobilidade = useCarregar(() => api.get("/api/painel/mobilidade", { periodo_id: periodoId }), "m");
  const serie = useCarregar(() => api.get("/api/painel/series", recorte), "s");
  const segmentos = useCarregar(() => api.get("/api/painel/segmentos", recorte), "g");
  const ranking = useCarregar(() => api.get("/api/painel/ranking", { ...recorte, pagina, tamanho: TAMANHO_RANKING }), `r${pagina}`);

  const ind = indicadores.dados;
  const selo = ind?.periodo?.id ? `Nº ${ind.periodo.id}` : null;

  return (
    <>
      <p className="recorte__comparacao" role="status">
        {indicadores.carregando ? (
          "Carregando o período…"
        ) : ind?.periodo_anterior ? (
          <>Comparado com {comoPeriodo(ind.periodo_anterior)}</>
        ) : ind ? (
          "Primeiro período importado — variação e tendência exigem histórico."
        ) : null}
      </p>

      <section className="faixa-kpi" aria-labelledby="titulo-indicadores" aria-busy={indicadores.carregando}>
        <h2 id="titulo-indicadores" className="sr-only">
          Indicadores do período
        </h2>
        {indicadores.carregando && <Carregando rotulo="Carregando os indicadores" linhas={2} />}
        {indicadores.erro && (
          <ErroDaTela erro={indicadores.erro}>
            <p>Escolha outro período ou outra categoria acima.</p>
          </ErroDaTela>
        )}
        {ind && (
          <div className="faixa-kpi__grade">
            <Kpi rotulo="Faturamento" principal selo={selo} variacao={<Variacao valor={ind.variacao?.faturamento} />}>
              <Dinheiro valor={ind.faturamento} grande />
            </Kpi>
            <Kpi rotulo="Pedidos" selo={selo} variacao={<Variacao valor={ind.variacao?.pedidos} />}>
              {comoInteiro(ind.pedidos)}
            </Kpi>
            <Kpi rotulo="Ticket médio" selo={selo} variacao={<Variacao valor={ind.variacao?.ticket_medio} />}>
              <Dinheiro valor={ind.ticket_medio} grande porque="sem pedidos no período" />
            </Kpi>
            <Kpi rotulo="Parceiros ativos" selo={selo} variacao={<Variacao valor={ind.variacao?.parceiros_ativos} />}>
              {comoInteiro(ind.parceiros_ativos)}
            </Kpi>
            <KpiEmRisco selo={selo} emRisco={ind.em_risco} categoriaId={categoriaId} maisRecente={maisRecente} podeVer={tem(usuario, "parceiros")} />
            <KpiMobilidade selo={selo} mobilidade={mobilidade} categoria={categoria} />
          </div>
        )}
      </section>

      <div className="painel-meio">
        <section className="bloco bloco--serie" aria-labelledby="titulo-serie" aria-busy={serie.carregando}>
          <div className="bloco__cabeca">
            <h2 id="titulo-serie" className="bloco__titulo">
              {categoria ? `Faturamento de ${categoria.nome}` : "Faturamento da rede"}
            </h2>
            <p className="bloco__sub">Um ponto por período, até {ind ? comoPeriodo(ind.periodo) : "o período escolhido"} · medido</p>
          </div>
          {serie.carregando && <Carregando rotulo="Carregando a série" linhas={5} altura={280} />}
          <ErroDaTela erro={serie.erro} />
          {serie.dados && <Serie pontos={serie.dados.pontos} rotulo={categoria ? `Faturamento de ${categoria.nome}` : "Faturamento da rede"} />}
        </section>

        <Distribuicao segmentos={segmentos} categoriaId={categoriaId} maisRecente={maisRecente} podeVer={tem(usuario, "parceiros")} />
      </div>

      {tem(usuario, "painel_decisao") && <Decisao categoriaId={categoriaId} usuario={usuario} />}

      <Ranking ranking={ranking} categoria={categoria} pagina={pagina} aoMudarPagina={aoMudarPagina} podeVer={tem(usuario, "parceiros")} />
    </>
  );
}

function KpiEmRisco({ emRisco, categoriaId, maisRecente, podeVer, selo }) {
  if (!emRisco) {
    return (
      <Kpi rotulo="Em risco" tom="risco" selo={selo} nota={<p>Segmentação ainda não calculada para este período.</p>}>
        <Ausente porque="Segmentação ainda não calculada para este período" />
      </Kpi>
    );
  }
  const link = podeVer && maisRecente && emRisco.total > 0;
  return (
    <Kpi
      rotulo={<Segmento codigo="EM_RISCO" />}
      tom="risco"
      selo={selo}
      variacao={<Delta valor={emRisco.delta} ruimQuandoSobe />}
      nota={
        link ? (
          <Link to={comConsulta("/parceiros", { segmento: "EM_RISCO", categoria_id: categoriaId })} className="link-seta">
            Ver quem está em risco <Icone nome="seta-direita" />
          </Link>
        ) : null
      }
    >
      {comoInteiro(emRisco.total)}
    </Kpi>
  );
}

function KpiMobilidade({ mobilidade, categoria, selo }) {
  if (mobilidade.carregando) return <Kpi rotulo="Mobilidade do Top">…</Kpi>;
  if (mobilidade.erro) return <Kpi rotulo="Mobilidade do Top" nota={<p>{mobilidade.erro.message}</p>}><Ausente porque="não foi possível carregar" /></Kpi>;
  const m = mobilidade.dados;
  if (!m.periodo_anterior) {
    return (
      <Kpi rotulo={`Mobilidade Top ${m.top_n}`} nota={<p>Sem período anterior para comparar.</p>}>
        <Ausente porque="Sem período anterior para comparar" />
      </Kpi>
    );
  }
  const mudaram = m.entradas.length + m.saidas.length;
  return (
    <Kpi
      rotulo={`Mobilidade Top ${m.top_n}`}
      selo={selo}
      variacao={
        <span className="variacao variacao--estavel variacao--texto">
          {plural(m.entradas.length, "entrou", "entraram")} · {plural(m.saidas.length, "saiu", "saíram")}
        </span>
      }
      nota={
        <>
          {mudaram > 0 && (
            <details className="detalhes-curto">
              <summary>
                <Icone nome="seta-direita" className="resumo__icone" />
                Quem entrou e quem saiu
              </summary>
              <ul className="mobilidade">
                {m.entradas.map((e) => (
                  <li key={`e${e.parceiro_id}`}>
                    <Icone nome="sobe" className="mobilidade__entrou" /> {e.nome} <span className="mobilidade__pos">{e.posicao_anterior ? `${e.posicao_anterior}º → ` : ""}{e.posicao}º</span>
                  </li>
                ))}
                {m.saidas.map((e) => (
                  <li key={`s${e.parceiro_id}`}>
                    <Icone nome="cai" className="mobilidade__saiu" /> {e.nome} <span className="mobilidade__pos">{e.posicao_anterior}º → {e.posicao ? `${e.posicao}º` : "sem faturamento"}</span>
                  </li>
                ))}
              </ul>
            </details>
          )}
          {categoria && <p>Do Top da rede inteira, e não só de {categoria.nome}.</p>}
        </>
      }
    >
      {comoInteiro(mudaram)}
    </Kpi>
  );
}

function Distribuicao({ segmentos, categoriaId, maisRecente, podeVer }) {
  const d = segmentos.dados;
  const topo = d ? Math.max(...d.itens.map((i) => i.total), 1) : 1;
  return (
    <section className="bloco bloco--segmentos" aria-labelledby="titulo-segmentos" aria-busy={segmentos.carregando}>
      <div className="bloco__cabeca">
        <h2 id="titulo-segmentos" className="bloco__titulo">
          Parceiros por segmento
        </h2>
        {d && d.itens.length > 0 && <p className="bloco__sub">{plural(d.total, "parceiro", "parceiros")} no período</p>}
      </div>
      {segmentos.carregando && <Carregando rotulo="Carregando a distribuição" linhas={6} />}
      <ErroDaTela erro={segmentos.erro} />
      {d && !d.itens.length && (
        <Vazio titulo="Segmentação ainda não calculada" compacto icone="painel">
          A classificação por segmento roda junto com a importação. Importe um período para vê-la aqui.
        </Vazio>
      )}
      {d && d.itens.length > 0 && (
        <>
          <div className="faixa-segmentos" aria-hidden="true">
            {d.itens.map((i) => (
              <span key={i.segmento} className={`faixa-segmentos__parte segmento-fundo--${i.segmento.toLowerCase().replace(/_/g, "-")}`} style={{ flexGrow: i.total }} />
            ))}
          </div>
          <ul className="distribuicao">
            {d.itens.map((i) => {
              const conteudo = (
                <>
                  <Segmento codigo={i.segmento} />{" "}
                  <span className="distribuicao__trilho" aria-hidden="true">
                    <span className={`distribuicao__barra segmento-fundo--${i.segmento.toLowerCase().replace(/_/g, "-")}`} style={{ width: `${(i.total / topo) * 100}%` }} />
                  </span>
                  <span className="distribuicao__total">{comoInteiro(i.total)}</span>
                </>
              );
              return (
                <li key={i.segmento}>
                  {podeVer && maisRecente ? (
                    /* O nome do link é o que se vê ("Em risco 104"), e o resto só para quem ouve. */
                    <Link className="distribuicao__linha distribuicao__linha--link" to={comConsulta("/parceiros", { segmento: i.segmento, categoria_id: categoriaId })}>
                      {conteudo}{" "}
                      <span className="sr-only">parceiros — ver na lista</span>
                    </Link>
                  ) : (
                    <span className="distribuicao__linha">{conteudo}</span>
                  )}
                </li>
              );
            })}
          </ul>
          {!maisRecente && <p className="bloco__nota">Em períodos anteriores o segmento não abre a lista: a lista de parceiros é sempre do período mais recente.</p>}
        </>
      )}
      <Link to="/ajuda#segmentos" className="link-seta bloco__rodape">
        O que é cada segmento? <Icone nome="seta-direita" />
      </Link>
    </section>
  );
}

function Decisao({ categoriaId, usuario }) {
  const decisao = useCarregar(() => api.get("/api/painel/decisao", { categoria_id: categoriaId }), `d${categoriaId}`);
  return (
    <section className="decisao" aria-labelledby="titulo-decisao" aria-busy={decisao.carregando}>
      <h2 id="titulo-decisao" className="secao-titulo">
        Próximo período e última campanha
      </h2>
      {decisao.carregando && <Carregando rotulo="Carregando a previsão e a campanha" linhas={4} />}
      <ErroDaTela erro={decisao.erro} />
      {decisao.dados && (
        <div className="decisao__grade">
          <ProximoPeriodo previsao={decisao.dados.previsao} usuario={usuario} />
          <UltimaCampanha campanha={decisao.dados.campanha} usuario={usuario} />
        </div>
      )}
    </section>
  );
}

function ProximoPeriodo({ previsao, usuario }) {
  if (!previsao.disponivel) {
    return (
      <div className="bloco bloco--estimativa">
        <div className="bloco__cabeca bloco__cabeca--etiqueta">
          <h3 className="bloco__titulo">Próximo período</h3>
          <Estimativa />
        </div>
        <Vazio titulo={previsao.motivo ?? "Ainda não há previsão."} compacto icone="modelo" acao={tem(usuario, "modelo") ? "Ir para o Modelo" : undefined} para="/modelo">
          {previsao.ajuda}
        </Vazio>
      </div>
    );
  }
  return (
    <div className="bloco bloco--estimativa">
      <div className="bloco__cabeca bloco__cabeca--etiqueta">
        <h3 className="bloco__titulo">Próximo período</h3>
        <Estimativa />
      </div>
      <dl className="pares pares--tres">
        <div>
          <dt>Faturamento previsto</dt>
          <dd className="valor-estimado valor-grande">
            <Dinheiro valor={previsao.faturamento_previsto} grande />
          </dd>
        </div>
        <div>
          <dt>Medido, nos mesmos parceiros</dt>
          <dd>
            <Dinheiro valor={previsao.faturamento_medido} />
          </dd>
        </div>
        <div>
          <dt>Do medido para o previsto</dt>
          <dd>
            <Variacao valor={previsao.variacao_percentual} />
          </dd>
        </div>
      </dl>
      <p className="bloco__nota">
        {plural(previsao.parceiros, "parceiro tem", "parceiros têm")} previsão, pela {previsao.origem === "REFERENCIA" ? "referência" : "versão"} {previsao.modelo_versao} ({ROTULO_ORIGEM_PREVISAO[previsao.origem] ?? previsao.origem}), com dados até{" "}
        {comoPeriodo(previsao.periodo_base)}. É estimativa, e não medição — e parte desse período, e não do escolhido acima.
      </p>
      {previsao.desatualizada && <p className="bloco__nota bloco__nota--atencao">Há período importado depois desta estimativa; o próximo treino a refaz.</p>}
      {previsao.maior_risco.length > 0 && (
        <>
          <h4 className="bloco__subtitulo">Maior risco de queda</h4>
          <CaixaDeTabela rotulo="Parceiros com maior risco de queda">
            <table className="tabela tabela--compacta">
              <caption className="sr-only">Parceiros com maior chance de queda no próximo período (estimativa)</caption>
              <thead>
                <tr>
                  <th scope="col">Parceiro</th>
                  <th scope="col">Categoria</th>
                  <th scope="col" className="num">
                    Medido
                  </th>
                  <th scope="col" className="num">
                    Previsto
                  </th>
                  <th scope="col" className="num">
                    Chance de queda
                  </th>
                </tr>
              </thead>
              <tbody>
                {previsao.maior_risco.map((r) => (
                  <tr key={r.parceiro_id}>
                    <th scope="row" className="nome">
                      {tem(usuario, "parceiros") ? (
                        <Link to={`/parceiros/${r.parceiro_id}`} state={{ de: "painel" }}>
                          {r.nome}
                        </Link>
                      ) : (
                        r.nome
                      )}
                    </th>
                    <td>{r.categoria ?? <Ausente porque="sem categoria confirmada" />}</td>
                    <td className="num">{comoDinheiro(r.faturamento)}</td>
                    <td className="num estimado">{comoDinheiro(r.faturamento_previsto)}</td>
                    <td className="num estimado">
                      <Chance valor={r.probabilidade_queda} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CaixaDeTabela>
          {tem(usuario, "parceiros") && (
            <Link to="/parceiros?ordenar_por=risco&descendente=true" className="link-seta bloco__rodape">
              Ver todos os parceiros pelo risco <Icone nome="seta-direita" />
            </Link>
          )}
        </>
      )}
    </div>
  );
}

function UltimaCampanha({ campanha, usuario }) {
  const p = campanha.plano;
  /* Quem calculou está na execução; só pede quem abre o plano. */
  const execucao = useCarregar(() => api.get(`/api/otimizacoes/${p.execucao_id}`), `ex${p?.execucao_id}`, { ativo: Boolean(p) && tem(usuario, "execucao") });
  if (!p) {
    return (
      <div className="bloco">
        <div className="bloco__cabeca">
          <h3 className="bloco__titulo">Última campanha</h3>
        </div>
        <Vazio titulo="Nenhum plano de campanha calculado ainda" compacto icone="campanha" acao={tem(usuario, "campanha") ? "Ir para a Campanha" : undefined} para="/campanha">
          O plano sai da tela Campanha, com o orçamento, o máximo de ações e as cotas.
        </Vazio>
      </div>
    );
  }
  return (
    <div className="bloco bloco--campanha">
      <div className="bloco__cabeca">
        <h3 className="bloco__titulo">Última campanha</h3>
        <p className="bloco__sub">Aplicação de {comoData(p.aplicacao_inicio)} a {comoData(p.aplicacao_fim)}</p>
      </div>
      <Lacre numero={p.execucao_id} titulo="Plano calculado" quando={p.concluida_em} quem={execucao.dados?.autor ?? null}>
        <span className="lacre__assinatura">Previsões da {p.modelo_versao}</span>
      </Lacre>
      <dl className="pares pares--campanha">
        <div>
          <dt>Ações</dt>
          <dd className="valor-forte">{comoInteiro(campanha.acoes)}</dd>
        </div>
        <div>
          <dt>Custo</dt>
          <dd className="valor-forte">
            <Dinheiro valor={campanha.custo} />
          </dd>
        </div>
      </dl>
      <div className="sem-lacre">
        <p className="sem-lacre__rotulo">
          Ganho esperado <Estimativa />
        </p>
        <p className="sem-lacre__valor">
          <Dinheiro valor={campanha.ganho_esperado} grande />
        </p>
      </div>
      {tem(usuario, "execucao") && (
        <Link to={`/execucoes/${p.execucao_id}`} className="botao botao--secundario">
          Abrir o plano <Icone nome="seta-direita" />
        </Link>
      )}
    </div>
  );
}

function Ranking({ ranking, categoria, pagina, aoMudarPagina, podeVer }) {
  const r = ranking.dados;
  return (
    <section className="bloco bloco--ranking" aria-labelledby="titulo-ranking" aria-busy={ranking.carregando}>
      <div className="bloco__cabeca bloco__cabeca--linha">
        <div>
          <h2 id="titulo-ranking" className="bloco__titulo">
            Ranking de parceiros
          </h2>
          {r && (
            <p className="bloco__sub">
              {comoInteiro(r.itens.length)} de {comoInteiro(r.total)}
              {categoria ? ` em ${categoria.nome} · a posição é a da rede inteira` : ""}
            </p>
          )}
        </div>
      </div>
      {ranking.carregando && <Carregando rotulo="Carregando o ranking" linhas={8} />}
      <ErroDaTela erro={ranking.erro} />
      {r && !r.itens.length && (
        <Vazio titulo={categoria ? `Nenhum parceiro de ${categoria.nome} com movimento neste período` : "Nenhum parceiro com movimento neste período"} compacto>
          Escolha outro período ou outra categoria no recorte acima.
        </Vazio>
      )}
      {r && r.itens.length > 0 && (
        <>
          <CaixaDeTabela rotulo="Ranking de parceiros">
            <table className="tabela tabela--ranking">
              <caption className="sr-only">
                Ranking de parceiros por faturamento, {comoPeriodo(r.periodo)}
                {categoria ? `, em ${categoria.nome} (posição na rede inteira)` : ""}
              </caption>
              <thead>
                <tr>
                  <th scope="col" className="num">
                    Posição
                  </th>
                  <th scope="col">Parceiro</th>
                  <th scope="col">Categoria</th>
                  <th scope="col">Segmento</th>
                  <th scope="col" className="num">
                    Faturamento
                  </th>
                  <th scope="col" className="num">
                    Pedidos
                  </th>
                  <th scope="col" className="num">
                    Ticket médio
                  </th>
                  <th scope="col" className="num">
                    Variação
                  </th>
                </tr>
              </thead>
              <tbody>
                {r.itens.map((l) => (
                  <tr key={l.parceiro_id}>
                    <td className="num posicao">
                      <span className="posicao__numero">{l.posicao}</span>
                      <Movimento linha={l} />
                    </td>
                    <th scope="row" className="nome">
                      {podeVer ? (
                        <Link to={`/parceiros/${l.parceiro_id}`} state={{ de: "painel" }}>
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
                    <td className="num">{comoInteiro(l.pedidos)}</td>
                    <td className="num">{comoDinheiro(l.ticket_medio)}</td>
                    <td className="num">
                      <Variacao valor={l.variacao_percentual} semBase={l.estreante ? "estreante: não tinha faturamento no período anterior" : "sem variação calculável"} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CaixaDeTabela>
          <Paginacao pagina={pagina} tamanho={TAMANHO_RANKING} total={r.total} aoMudar={aoMudarPagina} rotulo="parceiros" />
        </>
      )}
    </section>
  );
}

function Movimento({ linha }) {
  if (linha.estreante) {
    return (
      <span className="movimento movimento--novo">
        · novo<span className="sr-only"> (não tinha faturamento no período anterior)</span>
      </span>
    );
  }
  if (linha.posicao_anterior === null || linha.posicao_anterior === undefined) return null;
  const diferenca = linha.posicao_anterior - linha.posicao;
  if (diferenca === 0) return <span className="sr-only">, mesma posição do período anterior</span>;
  return (
    <span className={`movimento movimento--${diferenca > 0 ? "subiu" : "caiu"}`}>
      <span aria-hidden="true">{diferenca > 0 ? "↑" : "↓"}</span> {Math.abs(diferenca)}
      <span className="sr-only">{diferenca > 0 ? " posições acima" : " posições abaixo"} do período anterior</span>
    </span>
  );
}
