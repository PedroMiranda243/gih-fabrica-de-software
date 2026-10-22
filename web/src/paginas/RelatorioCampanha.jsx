/**
 * Campanha — onde a verba de um plano foi, por ação, por categoria e por
 * segmento. Sem escolha, vale o último plano viável.
 */
import { Link, useLocation } from "react-router-dom";

import { api, comConsulta } from "../api/cliente";
import { useCarregar, useFiltros } from "../api/ganchos";
import { tem, useSessao } from "../api/sessao";
import { Dinheiro, Estimativa, Segmento } from "../componentes/Dados";
import { Carregando, ErroDaTela, Vazio } from "../componentes/Estados";
import FolhaDeRelatorio from "../componentes/FolhaDeRelatorio";
import Icone from "../componentes/Icone";
import Kpi from "../componentes/Kpi";
import Lacre from "../componentes/Lacre";
import { CaixaDeTabela } from "../componentes/Lista";
import Seletor from "../componentes/Seletor";
import { useTitulo } from "../componentes/Titulo";
import { comoData, comoDataHora, comoDinheiro, comoInteiro, comoPeriodo } from "../formato";

export default function RelatorioCampanha() {
  useTitulo("Campanha", "Relatórios");
  const { usuario } = useSessao();
  const lugar = useLocation();
  const [filtros, mudar] = useFiltros();
  const planos = useCarregar(() => api.get("/api/relatorios/campanha/planos"), "planos");
  const rel = useCarregar(() => api.get("/api/relatorios/campanha", { execucao_id: filtros.execucao_id }), lugar.search);
  const r = rel.dados;

  const filtrosForm = (
    <Seletor
      id="f-plano"
      rotulo="Plano"
      valor={filtros.execucao_id}
      aoMudar={(v) => mudar({ execucao_id: v })}
      todos="O último plano viável"
      opcoes={(planos.dados ?? []).map((p) => [p.execucao_id, `Plano de ${comoDataHora(p.concluida_em)}`])}
    />
  );

  const recorte = r?.plano ? `Plano de ${comoDataHora(r.plano.concluida_em)} · aplicação de ${comoData(r.plano.aplicacao_inicio)} a ${comoData(r.plano.aplicacao_fim)} · previsões da ${r.plano.modelo_versao}` : null;

  return (
    <FolhaDeRelatorio nome="Campanha" filtros={filtrosForm} recorte={recorte} csv={r?.plano ? comConsulta("/api/relatorios/campanha/exportacao.csv", { execucao_id: r.plano.execucao_id }) : null}>
      {rel.carregando && <Carregando rotulo="Carregando o relatório" linhas={8} />}
      <ErroDaTela erro={rel.erro}>
        <p>Escolha outro plano no filtro acima.</p>
      </ErroDaTela>
      {r && !r.plano && (
        <Vazio titulo="Nenhum plano de campanha calculado ainda" acao={tem(usuario, "campanha") ? "Ir para a Campanha" : undefined} para="/campanha" icone="campanha">
          O plano sai da tela Campanha, com o orçamento, o máximo de ações e as cotas.
        </Vazio>
      )}
      {r?.plano && (
        <>
          <section className="folha__secao" aria-labelledby="t-total">
            <div className="folha__cabeca-secao">
              <h3 id="t-total" className="folha__subtitulo">
                Total do plano
              </h3>
              <Lacre numero={r.plano.execucao_id} titulo="Plano calculado" quando={r.plano.concluida_em} compacto />
            </div>
            <div className="faixa-kpi__grade faixa-kpi__grade--quatro">
              <Kpi rotulo={<>Ganho esperado <Estimativa /></>} principal className="kpi--estimado">
                <Dinheiro valor={r.total?.ganho_esperado} grande />
              </Kpi>
              <Kpi rotulo="Custo">
                <Dinheiro valor={r.total?.custo} grande />
              </Kpi>
              <Kpi rotulo="Orçamento">
                <Dinheiro valor={r.orcamento} grande />
              </Kpi>
              <Kpi rotulo="Ações">{comoInteiro(r.total?.parceiros)}</Kpi>
            </div>
            {tem(usuario, "execucao") && (
              <Link to={`/execucoes/${r.plano.execucao_id}`} className="link-seta bloco__rodape nao-imprime">
                Abrir o plano, parceiro a parceiro <Icone nome="seta-direita" />
              </Link>
            )}
          </section>
          <Grupos id="t-acao" titulo="Por ação" linhas={r.por_acao} total={r.total} coluna="Ação" />
          <Grupos id="t-categoria" titulo="Por categoria" linhas={r.por_categoria} total={r.total} coluna="Categoria" />
          <Grupos id="t-segmento" titulo="Por segmento" linhas={r.por_segmento} total={r.total} coluna="Segmento" segmento />
          {r.periodo_base && <p className="bloco__nota">O segmento é o do período de {comoPeriodo(r.periodo_base)}, de onde o plano partiu: é a classificação que o otimizador viu ao escolher, e não a de hoje.</p>}
        </>
      )}
    </FolhaDeRelatorio>
  );
}

function Grupos({ id, titulo, linhas, total, coluna, segmento = false }) {
  return (
    <section className="folha__secao" aria-labelledby={id}>
      <h3 id={id} className="folha__subtitulo">
        {titulo} <span className="folha__subtitulo-nota">do maior ganho esperado para o menor</span>
      </h3>
      <CaixaDeTabela rotulo={titulo}>
        <table className="tabela">
          <caption className="sr-only">
            {titulo}: parceiros, custo e ganho esperado (estimativa)
          </caption>
          <thead>
            <tr>
              <th scope="col">{coluna}</th>
              <th scope="col" className="num">
                Parceiros
              </th>
              <th scope="col" className="num">
                Custo
              </th>
              <th scope="col" className="num">
                Ganho esperado
              </th>
            </tr>
          </thead>
          <tbody>
            {linhas.map((l) => (
              <tr key={l.chave ?? l.rotulo}>
                <th scope="row">{segmento && l.chave ? <Segmento codigo={l.chave} /> : l.rotulo}</th>
                <td className="num">{comoInteiro(l.parceiros)}</td>
                <td className="num">{comoDinheiro(l.custo)}</td>
                <td className="num">{comoDinheiro(l.ganho_esperado)}</td>
              </tr>
            ))}
          </tbody>
          {total && (
            <tfoot>
              <tr>
                <th scope="row">Total</th>
                <td className="num">{comoInteiro(total.parceiros)}</td>
                <td className="num">{comoDinheiro(total.custo)}</td>
                <td className="num">{comoDinheiro(total.ganho_esperado)}</td>
              </tr>
            </tfoot>
          )}
        </table>
      </CaixaDeTabela>
    </section>
  );
}
