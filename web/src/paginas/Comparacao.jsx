/**
 * Comparação de dois planos — o que mudou por causa de um parâmetro. A comparação
 * chega pronta da API; a tela desenha do resumo ao detalhe, A e B na mesma escala.
 */
import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { api } from "../api/cliente";
import { useCarregar } from "../api/ganchos";
import { tem, useSessao } from "../api/contextoSessao";
import { Segmento } from "../componentes/Dados";
import { Carregando, ErroDaTela, Nota, Vazio } from "../componentes/Estados";
import { CaixaDeTabela, Trilha } from "../componentes/Lista";
import { useTitulo } from "../componentes/Titulo";
import { comoData, comoDataHora, comoDinheiro, comoFracao, comoInteiro, cotasDoPedido, ROTULO_MODO_CURTO, ROTULO_PARAMETRO } from "../formato";

function comSinalDinheiro(v) {
  const n = Number(v);
  if (Number.isNaN(n)) return "—";
  if (n === 0) return "igual";
  return `${n > 0 ? "+" : "−"}${comoDinheiro(Math.abs(n))}`;
}

function comSinalInteiro(n) {
  if (n === null || n === undefined) return "—";
  if (n === 0) return "igual";
  return `${n > 0 ? "+" : "−"}${comoInteiro(Math.abs(n))}`;
}

const SITUACAO = { MUDOU: "Mudou de ação", SO_A: "Só no plano A", SO_B: "Só no plano B", IGUAL: "Igual" };

export default function Comparacao() {
  useTitulo("Comparação de dois planos", "Execuções");
  const { usuario } = useSessao();
  const [busca] = useSearchParams();
  const a = busca.get("a");
  const b = busca.get("b");
  const temOsDois = Boolean(a && b);
  const comp = useCarregar(() => api.get("/api/otimizacoes/comparacao", { a, b }), `${a}-${b}`, { ativo: temOsDois });
  const [mostrarIguais, setMostrarIguais] = useState(false);

  const trilha = <Trilha passos={[{ rotulo: "Execuções", para: "/execucoes" }, { rotulo: "Comparação de dois planos" }]} />;

  if (!temOsDois) {
    return (
      <div className="pagina">
        {trilha}
        <Vazio titulo="Escolha dois planos para comparar" acao="Ir para as execuções" para="/execucoes" icone="comparar">
          No histórico das execuções, marque dois planos calculados e peça a comparação.
        </Vazio>
      </div>
    );
  }
  if (comp.carregando) return <Carregando rotulo="Carregando a comparação" linhas={8} />;
  if (comp.erro?.status === 404) {
    return (
      <div className="pagina">
        {trilha}
        <Vazio titulo="Plano não encontrado" acao="Ir para as execuções" para="/execucoes" icone="busca">
          {comp.erro.ajuda ?? "Um dos dois planos do endereço não existe. Escolha dois planos no histórico das execuções."}
        </Vazio>
      </div>
    );
  }
  if (comp.erro) {
    return (
      <div className="pagina">
        {trilha}
        <ErroDaTela erro={comp.erro} />
      </div>
    );
  }

  const c = comp.dados;
  const mudou = new Set(c.parametros_diferentes);
  const linhaParametro = (chave, rotulo, valor) => ({ chave, rotulo, a: valor(c.a), b: valor(c.b) });
  const parametros = [
    linhaParametro("orcamento", ROTULO_PARAMETRO.orcamento, (e) => comoDinheiro(e.parametros.orcamento)),
    linhaParametro("maximo_acoes", ROTULO_PARAMETRO.maximo_acoes, (e) => comoInteiro(e.parametros.maximo_acoes)),
    linhaParametro("cota_cauda_longa", ROTULO_PARAMETRO.cota_cauda_longa, (e) => (e.parametros.cota_cauda_longa === null ? "Sem cota" : comoFracao(e.parametros.cota_cauda_longa, 0))),
    linhaParametro("cotas_categoria", ROTULO_PARAMETRO.cotas_categoria, (e) => (e.parametros.cotas_categoria.length ? cotasDoPedido(e).join("; ") : "Nenhuma")),
    linhaParametro("aplicacao_inicio", ROTULO_PARAMETRO.aplicacao_inicio, (e) => comoData(e.parametros.aplicacao_inicio)),
    linhaParametro("aplicacao_fim", ROTULO_PARAMETRO.aplicacao_fim, (e) => comoData(e.parametros.aplicacao_fim)),
    linhaParametro("modo", ROTULO_PARAMETRO.modo, (e) => (e.parametros.modo ? ROTULO_MODO_CURTO[e.parametros.modo] : "Automático")),
  ];
  const diferentes = c.itens.filter((i) => i.situacao !== "IGUAL");
  const iguais = c.itens.filter((i) => i.situacao === "IGUAL");
  const visiveis = mostrarIguais ? c.itens : diferentes;

  return (
    <div className="pagina">
      {trilha}
      {!c.mesmas_previsoes && (
        <Nota tipo="atencao" titulo="Os dois planos partiram de previsões diferentes.">
          A diferença de um parceiro pode ser da previsão, e não do plano.
        </Nota>
      )}

      <div className="comparacao-cabeca">
        {[
          ["A", c.a],
          ["B", c.b],
        ].map(([letra, e]) => (
          <div key={letra} className="comparacao-cabeca__plano">
            <span className="comparacao-cabeca__letra">{letra}</span>
            <div>
              <p className="comparacao-cabeca__nome">
                {tem(usuario, "execucao") ? <Link to={`/execucoes/${e.id}`}>Plano de {comoDataHora(e.concluida_em ?? e.iniciada_em)}</Link> : `Plano de ${comoDataHora(e.concluida_em ?? e.iniciada_em)}`}
              </p>
              <p className="discreto">
                {e.autor ?? "pelo terminal"} · previsões da {e.modelo_versao}
              </p>
            </div>
          </div>
        ))}
      </div>

      <section className="bloco" aria-labelledby="t-pedido">
        <div className="bloco__cabeca">
          <h2 id="t-pedido" className="bloco__titulo">
            O que foi pedido
          </h2>
          {!c.parametros_diferentes.length && <p className="bloco__sub">Os mesmos parâmetros.</p>}
        </div>
        <CaixaDeTabela rotulo="Parâmetros dos dois planos">
          <table className="tabela tabela--comparacao">
            <caption className="sr-only">Parâmetros pedidos no plano A e no plano B, com os que mudaram marcados</caption>
            <thead>
              <tr>
                <th scope="col">Parâmetro</th>
                <th scope="col">Plano A</th>
                <th scope="col">Plano B</th>
                <th scope="col">
                  <span className="sr-only">Mudou?</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {parametros.map((p) => (
                <tr key={p.chave} className={mudou.has(p.chave) ? "linha--mudou" : undefined}>
                  <th scope="row">{p.rotulo}</th>
                  <td>{p.a}</td>
                  <td>{p.b}</td>
                  <td>{mudou.has(p.chave) && <span className="selo-texto selo-texto--mudou">mudou</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CaixaDeTabela>
      </section>

      <section className="bloco" aria-labelledby="t-saiu">
        <div className="bloco__cabeca">
          <h2 id="t-saiu" className="bloco__titulo">
            O que saiu
          </h2>
          <p className="bloco__sub">A diferença é do plano B para o plano A. O ganho esperado é estimativa.</p>
        </div>
        <CaixaDeTabela rotulo="Resultado dos dois planos">
          <table className="tabela tabela--comparacao">
            <caption className="sr-only">Ganho esperado, custo e ações do plano A e do plano B, e a diferença</caption>
            <thead>
              <tr>
                <th scope="col">Medida</th>
                <th scope="col" className="num">
                  Plano A
                </th>
                <th scope="col" className="num">
                  Plano B
                </th>
                <th scope="col" className="num">
                  Diferença
                </th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <th scope="row">Ganho esperado (estimativa)</th>
                <td className="num">{comoDinheiro(c.a.uplift_total)}</td>
                <td className="num">{comoDinheiro(c.b.uplift_total)}</td>
                <td className="num diferenca">{comSinalDinheiro(c.diferenca_uplift)}</td>
              </tr>
              <tr>
                <th scope="row">Custo</th>
                <td className="num">{comoDinheiro(c.a.custo_total)}</td>
                <td className="num">{comoDinheiro(c.b.custo_total)}</td>
                <td className="num diferenca">{comSinalDinheiro(c.diferenca_custo)}</td>
              </tr>
              <tr>
                <th scope="row">Ações</th>
                <td className="num">{comoInteiro(c.a.acoes)}</td>
                <td className="num">{comoInteiro(c.b.acoes)}</td>
                <td className="num diferenca">{comSinalInteiro(c.diferenca_acoes)}</td>
              </tr>
            </tbody>
          </table>
        </CaixaDeTabela>
      </section>

      <section className="bloco" aria-labelledby="t-parceiros">
        <div className="bloco__cabeca bloco__cabeca--linha">
          <div>
            <h2 id="t-parceiros" className="bloco__titulo">
              Parceiro a parceiro
            </h2>
            <p className="bloco__sub">
              {comoInteiro(c.resumo.mudaram)} mudaram de ação · {comoInteiro(c.resumo.so_a)} só no A · {comoInteiro(c.resumo.so_b)} só no B · {comoInteiro(c.resumo.iguais)} iguais
            </p>
          </div>
          {iguais.length > 0 && (
            <button type="button" className="botao botao--secundario botao--pequeno" aria-expanded={mostrarIguais} onClick={() => setMostrarIguais((m) => !m)}>
              {mostrarIguais ? "Esconder os que ficaram iguais" : `Mostrar também os ${comoInteiro(iguais.length)} que ficaram iguais`}
            </button>
          )}
        </div>
        {!diferentes.length && (
          <Nota>{c.parametros_diferentes.length ? "Os parâmetros que mudaram não mudaram o plano." : "Os dois planos dão a mesma ação aos mesmos parceiros."}</Nota>
        )}
        {visiveis.length > 0 && (
          <CaixaDeTabela rotulo="Parceiro a parceiro">
            <table className="tabela">
              <caption className="sr-only">Parceiros dos dois planos: a ação em cada um e o que mudou</caption>
              <thead>
                <tr>
                  <th scope="col">Parceiro</th>
                  <th scope="col">Segmento</th>
                  <th scope="col">Ação no A</th>
                  <th scope="col">Ação no B</th>
                  <th scope="col">O que mudou</th>
                </tr>
              </thead>
              <tbody>
                {visiveis.map((i) => (
                  <tr key={i.parceiro_id} className={i.situacao === "IGUAL" ? "linha--igual" : undefined}>
                    <th scope="row" className="nome">
                      {tem(usuario, "parceiros") ? <Link to={`/parceiros/${i.parceiro_id}`}>{i.parceiro}</Link> : i.parceiro}
                    </th>
                    <td>
                      <Segmento codigo={i.segmento} />
                    </td>
                    <td>{i.acao_a ?? <span className="discreto">sem ação</span>}</td>
                    <td>{i.acao_b ?? <span className="discreto">sem ação</span>}</td>
                    <td>
                      <span className={`mudanca mudanca--${i.situacao.toLowerCase()}`}>{SITUACAO[i.situacao] ?? i.situacao}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CaixaDeTabela>
        )}
      </section>
    </div>
  );
}
