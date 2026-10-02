/**
 * O relatório de desempenho de um período (UC15 · RF44 · H84).
 *
 * Como a rede foi, por categoria e por segmento, com o total — que é o
 * indicador do painel no mesmo período. Os filtros vivem no endereço, e o CSV é
 * a mesma consulta em outro formato.
 *
 * **Nenhum cálculo acontece aqui** (regra 2.4): as somas, o ticket médio e as
 * variações vêm prontos de `/api/relatorios/desempenho`. A tela escreve o
 * recorte que **a API devolveu**, e não o que está no endereço.
 *
 * **Duas variações, e a tela diz qual é qual.** Por categoria e no total, é a
 * do painel: o grupo contra ele mesmo no período anterior. Por segmento, é a
 * dos mesmos parceiros — o segmento muda de um período para o outro, e comparar
 * o de agora com o de antes mediria quem entrou e quem saiu dele. A API manda
 * `mesmos_parceiros` quando o filtro de segmento faz o total e as categorias
 * virarem também a dos mesmos parceiros.
 */
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { api, comConsulta } from "../api/cliente";
import { Esqueleto } from "../componentes/Carregando";
import EstadoVazio from "../componentes/EstadoVazio";
import Relatorio, { ErroDoRelatorio, Variacao } from "../componentes/Relatorio";
import Segmento from "../componentes/Segmento";
import { comoDinheiro, comoInteiro, comoPeriodo, ROTULO_SEGMENTO } from "../formato";

const DOS_MESMOS_PARCEIROS =
  "A variação é a dos mesmos parceiros: o que os parceiros do grupo que venderam nos dois " +
  "períodos faturaram agora, contra o que faturaram antes.";

export default function RelatorioDesempenho() {
  const [parametros, setParametros] = useSearchParams();
  const periodo = parametros.get("periodo") ?? "";
  const categoria = parametros.get("categoria") ?? "";
  const segmento = parametros.get("segmento") ?? "";
  const filtros = { periodo_id: periodo, categoria_id: categoria, segmento };
  const consulta = JSON.stringify(filtros);

  const [recortes, setRecortes] = useState(null);
  const [estado, setEstado] = useState({ consulta: null, dados: null, erro: null });

  useEffect(() => {
    /* As opções dos filtros. Se falharem, o relatório abre no período mais
       recente, sem os seletores. */
    api
      .get("/api/painel/recortes")
      .then(setRecortes)
      .catch(() => setRecortes(null));
  }, []);

  useEffect(() => {
    let vivo = true;
    api
      .get("/api/relatorios/desempenho", JSON.parse(consulta))
      .then((dados) => vivo && setEstado({ consulta, dados, erro: null }))
      .catch((erro) => vivo && setEstado({ consulta, dados: null, erro }));
    return () => {
      vivo = false;
    };
  }, [consulta]);

  function ajustar(mudancas) {
    const proximos = new URLSearchParams(parametros);
    Object.entries(mudancas).forEach(([chave, valor]) =>
      valor ? proximos.set(chave, valor) : proximos.delete(chave),
    );
    setParametros(proximos, { replace: true });
  }

  const atual = estado.consulta === consulta;
  const dados = atual ? estado.dados : null;
  const erro = atual ? estado.erro : null;
  const maisRecente = recortes?.periodos[0];

  return (
    <>
      <Relatorio
        titulo="Desempenho por período"
        recorte={dados?.periodo ? recorteDe(dados) : []}
        csv={dados?.periodo ? comConsulta("/api/relatorios/desempenho/exportacao.csv", filtros) : null}
        filtros={
          maisRecente && (
            <div className="filtros">
              <div className="campo">
                <label htmlFor="periodo">Período</label>
                <select
                  id="periodo"
                  value={periodo || String(maisRecente.id)}
                  onChange={(e) =>
                    ajustar({ periodo: e.target.value === String(maisRecente.id) ? "" : e.target.value })
                  }
                >
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
                  <option value="">Todas as categorias</option>
                  {recortes.categorias.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.nome}
                    </option>
                  ))}
                </select>
              </div>
              <div className="campo">
                <label htmlFor="segmento">Segmento</label>
                <select
                  id="segmento"
                  value={segmento}
                  onChange={(e) => ajustar({ segmento: e.target.value })}
                >
                  <option value="">Todos os segmentos</option>
                  {Object.entries(ROTULO_SEGMENTO).map(([valor, rotulo]) => (
                    <option key={valor} value={valor}>
                      {rotulo}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )
        }
      >
        <ErroDoRelatorio erro={erro} />

        {!dados && !erro && (
          <div role="status" aria-label="Carregando o relatório">
            <Esqueleto altura={96} style={{ marginBottom: "var(--esp-12)" }} />
            <Esqueleto altura={280} />
          </div>
        )}

        {dados && !dados.periodo && (
          <section className="painel">
            <EstadoVazio
              titulo="Nenhum dado importado ainda"
              texto="O relatório resume o desempenho da rede a partir dos relatórios importados."
              acao={{ para: "/importacao", rotulo: "Importar um relatório" }}
            />
          </section>
        )}

        {dados?.periodo && dados.total.parceiros === 0 && (
          <section className="painel">
            <EstadoVazio
              titulo="Nenhum parceiro com movimento nesse recorte"
              texto="Não houve faturamento com esses filtros neste período. Troque a categoria, o segmento ou o período."
            />
          </section>
        )}

        {dados?.periodo && dados.total.parceiros > 0 && <Conteudo dados={dados} />}
      </Relatorio>
    </>
  );
}

/** O recorte como a folha o diz, a partir do que a API devolveu. */
function recorteDe(dados) {
  return [
    `Período de ${comoPeriodo(dados.periodo)}`,
    dados.periodo_anterior
      ? `comparado com ${comoPeriodo(dados.periodo_anterior)}`
      : "primeiro período importado, sem com o que comparar",
    dados.categoria ? `categoria ${dados.categoria.nome}` : "todas as categorias",
    dados.segmento ? `segmento ${ROTULO_SEGMENTO[dados.segmento] ?? dados.segmento}` : "todos os segmentos",
  ];
}

function Conteudo({ dados }) {
  const { total } = dados;

  return (
    <>
      <section className="painel painel--inteiro" aria-labelledby="titulo-total">
        <div className="painel__cabecalho">
          <h3 className="painel__titulo" id="titulo-total">
            Total do recorte
          </h3>
          <span className="painel__nota">
            {comoInteiro(total.parceiros)} {total.parceiros === 1 ? "parceiro" : "parceiros"} com
            movimento
          </span>
        </div>
        <dl className="relatorio__resumo">
          <div>
            <dt>Faturamento</dt>
            <dd className="num relatorio__principal">{comoDinheiro(total.faturamento)}</dd>
          </div>
          <div>
            <dt>Pedidos</dt>
            <dd className="num">{comoInteiro(total.pedidos)}</dd>
          </div>
          <div>
            <dt>Ticket médio</dt>
            <dd className="num">{comoDinheiro(total.ticket_medio)}</dd>
          </div>
          <div>
            <dt>Variação do faturamento</dt>
            <dd className="num">
              <Variacao valor={total.variacao_percentual} />
            </dd>
          </div>
        </dl>
        {dados.mesmos_parceiros && <p className="relatorio__nota">{DOS_MESMOS_PARCEIROS}</p>}
      </section>

      <section className="painel painel--inteiro" aria-labelledby="titulo-por-categoria">
        <div className="painel__cabecalho">
          <h3 className="painel__titulo" id="titulo-por-categoria">
            Por categoria
          </h3>
          <span className="painel__nota">
            {dados.por_categoria.length}{" "}
            {dados.por_categoria.length === 1 ? "categoria" : "categorias"}
          </span>
        </div>
        <Grupos
          legenda="Desempenho do período por categoria"
          coluna="Categoria"
          linhas={dados.por_categoria}
          total={total}
          celula={(linha) => linha.rotulo}
        />
        <p className="relatorio__nota">
          {dados.mesmos_parceiros
            ? DOS_MESMOS_PARCEIROS
            : "A variação é a do faturamento da categoria contra o dela mesma no período anterior, como no painel."}
        </p>
      </section>

      <section className="painel painel--inteiro" aria-labelledby="titulo-por-segmento">
        <div className="painel__cabecalho">
          <h3 className="painel__titulo" id="titulo-por-segmento">
            Por segmento
          </h3>
          {dados.segmentado && (
            <span className="painel__nota">
              {dados.por_segmento.length}{" "}
              {dados.por_segmento.length === 1 ? "segmento" : "segmentos"}
            </span>
          )}
        </div>
        {dados.segmentado ? (
          <>
            <Grupos
              legenda="Desempenho do período por segmento"
              coluna="Segmento"
              linhas={dados.por_segmento}
              total={total}
              celula={(linha) => (linha.chave ? <Segmento valor={linha.chave} /> : linha.rotulo)}
            />
            <p className="relatorio__nota">
              {DOS_MESMOS_PARCEIROS} O segmento muda de um período para o outro, e comparar o de
              agora com o de antes mediria quem entrou e quem saiu dele.
              {!dados.mesmos_parceiros && " Por isso a variação do total, que é a do painel, não é a soma destas."}
            </p>
          </>
        ) : (
          <EstadoVazio
            titulo="Segmentação ainda não calculada para este período"
            texto="A classificação por segmento roda junto com a importação."
          />
        )}
      </section>
    </>
  );
}

function Grupos({ legenda, coluna, linhas, total, celula }) {
  return (
    <div className="tabela-rolagem">
      <table className="tabela">
        <caption className="so-leitor">{legenda}</caption>
        <thead>
          <tr>
            <th scope="col">{coluna}</th>
            <th scope="col" className="numerica">
              Parceiros
            </th>
            <th scope="col" className="numerica">
              Faturamento
            </th>
            <th scope="col" className="numerica">
              Pedidos
            </th>
            <th scope="col" className="numerica">
              Ticket médio
            </th>
            <th scope="col" className="numerica">
              Variação
            </th>
          </tr>
        </thead>
        <tbody>
          {linhas.map((linha) => (
            <tr key={linha.chave ?? linha.rotulo}>
              <th scope="row" className="nome">
                {celula(linha)}
              </th>
              <td className="numerica">{comoInteiro(linha.parceiros)}</td>
              <td className="numerica">{comoDinheiro(linha.faturamento)}</td>
              <td className="numerica">{comoInteiro(linha.pedidos)}</td>
              <td className="numerica secundaria">{comoDinheiro(linha.ticket_medio)}</td>
              <td className="numerica">
                <Variacao valor={linha.variacao_percentual} />
              </td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <th scope="row">Total</th>
            <td className="numerica">{comoInteiro(total.parceiros)}</td>
            <td className="numerica">{comoDinheiro(total.faturamento)}</td>
            <td className="numerica">{comoInteiro(total.pedidos)}</td>
            <td className="numerica">{comoDinheiro(total.ticket_medio)}</td>
            {/* A variação do total está no resumo, com a nota de que grupo ela é:
                repetida aqui, pareceria a soma das linhas de cima. */}
            <td className="numerica" />
          </tr>
        </tfoot>
      </table>
    </div>
  );
}
