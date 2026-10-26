/**
 * Operações do sistema — quanto se fez, e do quê. As datas que valem são as que a
 * API devolve (sem escolha, os últimos 30 dias). Barra e número: a barra dá a
 * proporção, o número garante que nada dependa só dela. Uma cor só: é quantidade.
 */
import { Link, useLocation } from "react-router-dom";

import { api, comConsulta } from "../api/cliente";
import { useCarregar, useFiltros } from "../api/ganchos";
import { Carregando, ErroDaTela, Vazio } from "../componentes/Estados";
import FolhaDeRelatorio from "../componentes/FolhaDeRelatorio";
import Icone from "../componentes/Icone";
import Kpi from "../componentes/Kpi";
import Seletor from "../componentes/Seletor";
import { useTitulo } from "../componentes/Titulo";
import Barras from "../graficos/Barras";
import { comoData, comoInteiro } from "../formato";

export default function RelatorioOperacoes() {
  useTitulo("Operações do sistema", "Relatórios");
  const lugar = useLocation();
  const [filtros, mudar] = useFiltros();
  const consulta = { de: filtros.de, ate: filtros.ate, autor: filtros.autor, acao: filtros.acao };
  const usuarios = useCarregar(() => api.get("/api/usuarios"), "u");
  const acoes = useCarregar(() => api.get("/api/auditoria/acoes"), "a");
  const rel = useCarregar(() => api.get("/api/relatorios/operacoes", consulta), lugar.search);
  const r = rel.dados;

  const filtrosForm = (
    <>
      <div className="campo">
        <label className="campo__rotulo" htmlFor="f-de">
          De
        </label>
        <input id="f-de" type="date" className="entrada" value={filtros.de ?? ""} onChange={(e) => mudar({ de: e.target.value })} />
      </div>
      <div className="campo">
        <label className="campo__rotulo" htmlFor="f-ate">
          Até
        </label>
        <input id="f-ate" type="date" className="entrada" value={filtros.ate ?? ""} onChange={(e) => mudar({ ate: e.target.value })} />
      </div>
      <Seletor id="f-autor" rotulo="Quem fez" valor={filtros.autor} aoMudar={(v) => mudar({ autor: v })} todos="Todas as pessoas" opcoes={(usuarios.dados ?? []).map((u) => [u.id, `${u.nome} (${u.login})`])} />
      <Seletor id="f-acao" rotulo="Ação" valor={filtros.acao} aoMudar={(v) => mudar({ acao: v })} todos="Todas as ações" opcoes={(acoes.dados ?? []).map((a) => [a.acao, a.rotulo])} />
    </>
  );

  const nomeDoAutor = r?.autor ? usuarios.dados?.find((u) => u.id === r.autor)?.nome : null;
  const rotuloDaAcao = r?.acao ? acoes.dados?.find((a) => a.acao === r.acao)?.rotulo : null;
  const recorte = r ? [`De ${comoData(r.de)} a ${comoData(r.ate)}`, nomeDoAutor ?? (r.autor ? null : "Todas as pessoas"), rotuloDaAcao ?? (r.acao ? null : "Todas as ações")].filter(Boolean).join(" · ") : null;
  const pessoas = r ? [...r.por_usuario.map((p) => ({ chave: p.chave, nome: p.rotulo, valor: p.total })), ...(r.outras_pessoas ? [{ chave: "outras", nome: r.outras_pessoas.rotulo, valor: r.outras_pessoas.total }] : [])] : [];

  return (
    <FolhaDeRelatorio nome="Operações do sistema" filtros={filtrosForm} recorte={recorte} csv={r ? comConsulta("/api/relatorios/operacoes/exportacao.csv", consulta) : null}>
      {rel.carregando && <Carregando rotulo="Carregando o relatório" linhas={8} />}
      <ErroDaTela erro={rel.erro}>
        <p>Os filtros continuam acima para corrigir o intervalo.</p>
      </ErroDaTela>
      {r && r.total === 0 && (
        <Vazio titulo="Nenhuma operação nesse recorte" icone="busca">
          Não houve operação registrada com esses filtros. Amplie as datas ou tire um dos filtros.
        </Vazio>
      )}
      {r && r.total > 0 && (
        <>
          <section className="folha__secao" aria-labelledby="t-total">
            <h3 id="t-total" className="folha__subtitulo">
              Total do intervalo
            </h3>
            <div className="faixa-kpi__grade faixa-kpi__grade--quatro">
              <Kpi rotulo="Operações" principal>
                {comoInteiro(r.total)}
              </Kpi>
              <Kpi rotulo="Tipos de ação">{comoInteiro(r.por_acao.length)}</Kpi>
              <Kpi rotulo="Pessoas">{comoInteiro(r.pessoas)}</Kpi>
              <Kpi rotulo="Dias com operação">{comoInteiro(r.por_dia.length)}</Kpi>
            </div>
            <Link to={comConsulta("/auditoria", { de: r.de, ate: r.ate, autor: r.autor, acao: r.acao })} className="link-seta bloco__rodape nao-imprime">
              Ver estas operações na trilha <Icone nome="seta-direita" />
            </Link>
          </section>
          <section className="folha__secao" aria-labelledby="t-acao">
            <h3 id="t-acao" className="folha__subtitulo">
              Por tipo de ação
            </h3>
            <Barras rotulo="Operações por tipo de ação" itens={r.por_acao.map((a) => ({ chave: a.chave, nome: a.rotulo, valor: a.total }))} formato={comoInteiro} />
          </section>
          <section className="folha__secao" aria-labelledby="t-pessoa">
            <h3 id="t-pessoa" className="folha__subtitulo">
              Por pessoa
            </h3>
            <Barras rotulo="Operações por pessoa" itens={pessoas} formato={comoInteiro} legenda={r.outras_pessoas ? "As que mais fizeram, e as demais somadas na última linha." : null} />
          </section>
          <section className="folha__secao" aria-labelledby="t-dia">
            <h3 id="t-dia" className="folha__subtitulo">
              Por dia
            </h3>
            <Barras rotulo="Operações por dia" itens={r.por_dia.map((d) => ({ chave: d.chave, nome: comoData(d.chave ?? d.rotulo), valor: d.total }))} formato={comoInteiro} legenda="Só os dias em que houve operação. O dia é o do relógio do servidor, como nos filtros da trilha." />
          </section>
        </>
      )}
    </FolhaDeRelatorio>
  );
}
