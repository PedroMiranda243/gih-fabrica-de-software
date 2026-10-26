/**
 * Desempenho por período — por categoria e por segmento. Duas variações
 * diferentes, e a tela diz qual é qual.
 */
import { useLocation } from "react-router-dom";

import { api, comConsulta } from "../api/cliente";
import { useCarregar, useFiltros } from "../api/ganchos";
import { tem, useSessao } from "../api/contextoSessao";
import { Ausente, Segmento, Variacao } from "../componentes/Dados";
import { Carregando, ErroDaTela, Vazio } from "../componentes/Estados";
import FolhaDeRelatorio from "../componentes/FolhaDeRelatorio";
import Kpi from "../componentes/Kpi";
import { CaixaDeTabela } from "../componentes/Lista";
import Seletor from "../componentes/Seletor";
import { useTitulo } from "../componentes/Titulo";
import { comoDinheiro, comoInteiro, comoPeriodo, ORDEM_SEGMENTOS, ROTULO_SEGMENTO } from "../formato";
import { Dinheiro } from "../componentes/Dados";

export default function RelatorioDesempenho() {
  useTitulo("Desempenho por período", "Relatórios");
  const { usuario } = useSessao();
  const lugar = useLocation();
  const [filtros, mudar] = useFiltros();
  const consulta = { periodo_id: filtros.periodo_id, categoria_id: filtros.categoria_id, segmento: filtros.segmento };
  const recortes = useCarregar(() => api.get("/api/painel/recortes"), "rec");
  const rel = useCarregar(() => api.get("/api/relatorios/desempenho", consulta), lugar.search);
  const r = rel.dados;

  const filtrosForm = (
    <>
      <Seletor id="f-periodo" rotulo="Período" valor={filtros.periodo_id} aoMudar={(v) => mudar({ periodo_id: v })} todos="O mais recente" opcoes={(recortes.dados?.periodos ?? []).map((p) => [p.id, comoPeriodo(p)])} />
      <Seletor id="f-categoria" rotulo="Categoria" valor={filtros.categoria_id} aoMudar={(v) => mudar({ categoria_id: v })} todos="Todas as categorias" opcoes={(recortes.dados?.categorias ?? []).map((c) => [c.id, c.nome])} />
      <Seletor id="f-segmento" rotulo="Segmento" valor={filtros.segmento} aoMudar={(v) => mudar({ segmento: v })} todos="Todos os segmentos" opcoes={ORDEM_SEGMENTOS.map((s) => [s, ROTULO_SEGMENTO[s]])} />
    </>
  );

  const recorte = r ? [r.periodo ? `Período de ${comoPeriodo(r.periodo)}` : null, r.categoria?.nome ?? "Todas as categorias", r.segmento ? ROTULO_SEGMENTO[r.segmento] : "Todos os segmentos"].filter(Boolean).join(" · ") : null;
  const semBase = recortes.dados && !recortes.dados.periodos.length;
  const semMovimento = r && (!r.total || r.total.parceiros === 0);

  return (
    <FolhaDeRelatorio nome="Desempenho por período" filtros={filtrosForm} recorte={recorte} csv={r && !semMovimento ? comConsulta("/api/relatorios/desempenho/exportacao.csv", consulta) : null}>
      {rel.carregando && <Carregando rotulo="Carregando o relatório" linhas={8} />}
      <ErroDaTela erro={rel.erro}>
        <p>Os filtros continuam acima para escolher outro recorte.</p>
      </ErroDaTela>
      {semBase && (
        <Vazio titulo="Nenhum dado importado ainda" acao={tem(usuario, "importar") ? "Importar um relatório" : undefined} para="/importacao" icone="importacao">
          O relatório mostra a rede a partir dos relatórios importados.
        </Vazio>
      )}
      {r && !semBase && semMovimento && (
        <Vazio titulo="Nenhum parceiro com movimento nesse recorte" icone="busca">
          Não houve faturamento com esses filtros neste período. Troque a categoria, o segmento ou o período.
        </Vazio>
      )}
      {r && !semMovimento && (
        <>
          <section aria-labelledby="t-total" className="folha__secao">
            <h3 id="t-total" className="folha__subtitulo">
              Total do recorte
            </h3>
            <div className="faixa-kpi__grade faixa-kpi__grade--quatro">
              <Kpi rotulo="Faturamento" principal>
                <Dinheiro valor={r.total.faturamento} grande />
              </Kpi>
              <Kpi rotulo="Pedidos">{comoInteiro(r.total.pedidos)}</Kpi>
              <Kpi rotulo="Ticket médio">
                <Dinheiro valor={r.total.ticket_medio} grande />
              </Kpi>
              <Kpi rotulo="Variação do faturamento">
                <Variacao valor={r.total.variacao_percentual} semBase="sem variação calculável" />
              </Kpi>
            </div>
            <p className="bloco__nota">
              {r.mesmos_parceiros
                ? "Com o filtro de segmento, a variação do total e das categorias é a dos mesmos parceiros no período anterior: o segmento muda de um período para o outro."
                : `A variação é a do faturamento contra o mesmo recorte no período anterior${r.periodo_anterior ? ` (${comoPeriodo(r.periodo_anterior)})` : ""}, como no painel.`}
            </p>
          </section>

          <TabelaDeGrupos
            id="t-categoria"
            titulo="Por categoria"
            nota={r.mesmos_parceiros ? "A variação é a dos mesmos parceiros, como no total." : "A variação é a do faturamento da categoria contra o dela mesma no período anterior, como no painel."}
            linhas={r.por_categoria}
            total={r.total}
            rotuloColuna="Categoria"
          />

          {r.segmentado ? (
            <TabelaDeGrupos
              id="t-segmento"
              titulo="Por segmento"
              nota="A variação é a dos mesmos parceiros no período anterior: o segmento muda de um período para o outro, e comparar o grupo de agora com o de antes mediria quem entrou e quem saiu dele."
              linhas={r.por_segmento}
              total={r.total}
              rotuloColuna="Segmento"
              segmento
            />
          ) : (
            <section className="folha__secao" aria-labelledby="t-segmento-vazio">
              <h3 id="t-segmento-vazio" className="folha__subtitulo">
                Por segmento
              </h3>
              <Vazio titulo="Segmentação ainda não calculada para este período" compacto>
                A classificação por segmento roda junto com a importação.
              </Vazio>
            </section>
          )}
        </>
      )}
    </FolhaDeRelatorio>
  );
}

function TabelaDeGrupos({ id, titulo, nota, linhas, total, rotuloColuna, segmento = false }) {
  return (
    <section className="folha__secao" aria-labelledby={id}>
      <h3 id={id} className="folha__subtitulo">
        {titulo}
      </h3>
      <CaixaDeTabela rotulo={titulo}>
        <table className="tabela">
          <caption className="sr-only">{titulo}: parceiros, faturamento, pedidos, ticket médio e variação</caption>
          <thead>
            <tr>
              <th scope="col">{rotuloColuna}</th>
              <th scope="col" className="num">
                Parceiros
              </th>
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
            {linhas.map((l) => (
              <tr key={l.chave ?? l.rotulo}>
                <th scope="row">{segmento && l.chave ? <Segmento codigo={l.chave} /> : l.rotulo}</th>
                <td className="num">{comoInteiro(l.parceiros)}</td>
                <td className="num">{comoDinheiro(l.faturamento)}</td>
                <td className="num">{comoInteiro(l.pedidos)}</td>
                <td className="num">{l.ticket_medio === null ? <Ausente porque="sem pedidos" /> : comoDinheiro(l.ticket_medio)}</td>
                <td className="num">
                  <Variacao valor={l.variacao_percentual} semBase="sem variação calculável" />
                </td>
              </tr>
            ))}
          </tbody>
          {total && (
            <tfoot>
              <tr>
                <th scope="row">Total</th>
                <td className="num">{comoInteiro(total.parceiros)}</td>
                <td className="num">{comoDinheiro(total.faturamento)}</td>
                <td className="num">{comoInteiro(total.pedidos)}</td>
                <td className="num">{comoDinheiro(total.ticket_medio)}</td>
                <td className="num">
                  <Variacao valor={total.variacao_percentual} semBase="sem variação calculável" />
                </td>
              </tr>
            </tfoot>
          )}
        </table>
      </CaixaDeTabela>
      <p className="bloco__nota">{nota}</p>
    </section>
  );
}
