/**
 * Execuções — o histórico de tudo o que o otimizador calculou, de 20 em 20. A
 * linha abre o plano só para quem tem `execucao`; quem tem pode marcar dois
 * planos viáveis e compará-los (o mais antigo como A).
 */
import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { api } from "../api/cliente";
import { useCarregar, useFiltros } from "../api/ganchos";
import { tem, useSessao } from "../api/sessao";
import { Carregando, ErroDaTela, Vazio } from "../componentes/Estados";
import Icone from "../componentes/Icone";
import { CaixaDeTabela, Paginacao } from "../componentes/Lista";
import Seletor from "../componentes/Seletor";
import { useTitulo } from "../componentes/Titulo";
import { comoDataHora, comoDinheiro, comoFracao, comoInteiro, comoMilissegundos, cotasDoPedido, plural, ROTULO_MODO_CURTO, ROTULO_RESTRICAO } from "../formato";

const TAMANHO = 20;
const CHAVES = ["resultado", "modo", "autor", "de", "ate"];

export default function Execucoes() {
  useTitulo("Execuções do otimizador", "Execuções");
  const { usuario } = useSessao();
  const lugar = useLocation();
  const navegar = useNavigate();
  const [filtros, mudar] = useFiltros();
  const pagina = Number(filtros.pagina) || 1;
  const consulta = Object.fromEntries(CHAVES.map((c) => [c, filtros[c]]));
  const lista = useCarregar(() => api.get("/api/otimizacoes", { ...consulta, pagina, tamanho: TAMANHO }), lugar.search);
  const [marcados, setMarcados] = useState([]);
  const abre = tem(usuario, "execucao");
  const d = lista.dados;
  const filtrado = CHAVES.some((c) => filtros[c]);

  function marcar(execucao, sim) {
    setMarcados((m) => (sim ? [...m.filter((x) => x.id !== execucao.id), execucao].slice(-2) : m.filter((x) => x.id !== execucao.id)));
  }

  function comparar() {
    const [a, b] = [...marcados].sort((x, y) => Date.parse(x.iniciada_em) - Date.parse(y.iniciada_em));
    navegar(`/execucoes/comparar?a=${a.id}&b=${b.id}`);
  }

  const frase = marcados.length === 0 ? "Marque dois planos calculados para compará-los lado a lado." : marcados.length === 1 ? "Marque mais um plano." : "Dois planos marcados.";

  return (
    <div className="pagina">
      <form className="filtros" aria-label="Filtros das execuções" onSubmit={(e) => e.preventDefault()}>
        <Seletor id="f-resultado" rotulo="Resultado" valor={filtros.resultado} aoMudar={(v) => mudar({ resultado: v })} todos="Todos os resultados" opcoes={[["VIAVEL", "Com plano"], ["INVIAVEL", "Sem solução viável"], ["FALHOU", "Falhou"]]} />
        <Seletor id="f-modo" rotulo="Modo em que rodou" valor={filtros.modo} aoMudar={(v) => mudar({ modo: v })} todos="Todos os modos" opcoes={Object.entries(ROTULO_MODO_CURTO)} />
        <Seletor id="f-autor" rotulo="Quem calculou" valor={filtros.autor} aoMudar={(v) => mudar({ autor: v })} todos="Todas as pessoas" opcoes={(d?.autores ?? []).map((a) => [a.id, a.nome])} />
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
        {filtrado && (
          <button type="button" className="botao botao--fantasma filtros__limpar" onClick={() => mudar(Object.fromEntries(CHAVES.map((c) => [c, null])))}>
            <Icone nome="fechar" /> Limpar filtros
          </button>
        )}
      </form>

      {abre && d && d.itens.length > 0 && (
        <div className="comparar" role="status" aria-live="polite">
          <p>
            <Icone nome="comparar" /> {frase}
          </p>
          <button type="button" className="botao botao--primario" disabled={marcados.length !== 2} onClick={comparar}>
            Comparar os dois
          </button>
        </div>
      )}

      <section className="bloco bloco--tabela" aria-labelledby="t-execucoes" aria-busy={lista.carregando}>
        <h2 id="t-execucoes" className="sr-only">
          Execuções do otimizador
        </h2>
        {lista.carregando && !d && <Carregando rotulo="Carregando as execuções" linhas={8} />}
        <ErroDaTela erro={lista.erro} />
        {d && !d.itens.length && !filtrado && (
          <Vazio titulo="Nenhuma execução ainda" acao={tem(usuario, "campanha") ? "Ir para a Campanha" : undefined} para="/campanha" icone="execucoes">
            Cada plano calculado na campanha aparece aqui, com quem o calculou e o resultado.
          </Vazio>
        )}
        {d && !d.itens.length && filtrado && (
          <Vazio titulo="Nenhuma execução nesse recorte" icone="busca">
            Não há execução com esses filtros. Amplie as datas ou tire um dos filtros.
          </Vazio>
        )}
        {d && d.itens.length > 0 && (
          <>
            <CaixaDeTabela rotulo="Execuções">
              <table className={`tabela tabela--execucoes${lista.carregando ? " tabela--recarregando" : ""}`}>
                <caption className="sr-only">Execuções do otimizador, da mais recente para a mais antiga</caption>
                <thead>
                  <tr>
                    {abre && (
                      <th scope="col">
                        <span className="sr-only">Marcar para comparar</span>
                      </th>
                    )}
                    <th scope="col">Iniciada em</th>
                    <th scope="col">Por</th>
                    <th scope="col">Parâmetros</th>
                    <th scope="col">Modo</th>
                    <th scope="col" className="num">
                      Tempo
                    </th>
                    <th scope="col">Resultado</th>
                  </tr>
                </thead>
                <tbody>
                  {d.itens.map((e) => {
                    const marcado = marcados.some((m) => m.id === e.id);
                    return (
                      <tr key={e.id} className={marcado ? "linha--marcada" : undefined}>
                        {abre && (
                          <td className="celula-marca">
                            {e.viavel ? (
                              <input type="checkbox" className="marca-comparar" checked={marcado} onChange={(ev) => marcar(e, ev.target.checked)} aria-label={`Marcar a execução de ${comoDataHora(e.iniciada_em)} para comparar`} />
                            ) : null}
                          </td>
                        )}
                        <th scope="row" className="nome">
                          {abre ? <Link to={`/execucoes/${e.id}`}>{comoDataHora(e.iniciada_em)}</Link> : comoDataHora(e.iniciada_em)}
                        </th>
                        <td>{e.autor ?? <span className="discreto">pelo terminal</span>}</td>
                        <td className="parametros">
                          <span>{comoDinheiro(e.parametros.orcamento)}</span>
                          <span>até {comoInteiro(e.parametros.maximo_acoes)} ações</span>
                          {e.parametros.cota_cauda_longa !== null && <span>cauda longa {comoFracao(e.parametros.cota_cauda_longa, 0)}</span>}
                          {cotasDoPedido(e).map((t) => (
                            <span key={t}>{t}</span>
                          ))}
                        </td>
                        <td>{ROTULO_MODO_CURTO[e.modo] ?? e.modo}</td>
                        <td className="num">{comoMilissegundos(e.tempo_ms)}</td>
                        <td>
                          <Resultado execucao={e} />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </CaixaDeTabela>
            <Paginacao pagina={pagina} tamanho={TAMANHO} total={d.total} aoMudar={(p) => mudar({ pagina: p > 1 ? p : null }, { manterPagina: true })} rotulo="execuções" />
          </>
        )}
      </section>
    </div>
  );
}

export function Resultado({ execucao: e }) {
  if (e.situacao === "EM_ANDAMENTO") return <span className="discreto">calculando…</span>;
  if (e.situacao === "FALHOU") return <span className="texto-erro">Falhou</span>;
  if (e.viavel === false) return <span className="resultado-inviavel">Sem solução viável{e.restricao_violada ? `: ${ROTULO_RESTRICAO[e.restricao_violada] ?? e.restricao_violada}` : ""}</span>;
  return (
    <span className="resultado-viavel">
      <strong>{comoDinheiro(e.uplift_total)}</strong> · {plural(e.acoes ?? 0, "ação", "ações")}
      {e.parcial && <span className="discreto"> · parcial: atingiu o limite de tempo</span>}
    </span>
  );
}
