/**
 * O relatório de um plano de campanha (UC15 · RF46 · H86).
 *
 * Onde a verba foi, por ação, por categoria e por segmento, e o ganho que se
 * espera dela. Sem escolha, vale o último plano viável — o mesmo "último" do
 * painel e do cadastro do parceiro.
 *
 * **Quem diz que execução tem plano é a API**: a lista para escolher vem de
 * `/api/relatorios/campanha/planos`, só com as concluídas e viáveis (RN07). A
 * tela não filtra execução por resultado.
 *
 * **O ganho esperado é estimativa** (RN10), e o relatório diz de que previsão
 * ele partiu. O segmento é o do período de onde o plano saiu — a classificação
 * que o otimizador viu ao escolher, e não a de hoje.
 */
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { api, comConsulta } from "../api/cliente";
import { Esqueleto } from "../componentes/Carregando";
import EstadoVazio from "../componentes/EstadoVazio";
import Relatorio, { ErroDoRelatorio } from "../componentes/Relatorio";
import Segmento from "../componentes/Segmento";
import { comoData, comoDataHora, comoDinheiro, comoInteiro, comoPeriodo } from "../formato";

export default function RelatorioCampanha() {
  const [parametros, setParametros] = useSearchParams();
  const execucao = parametros.get("execucao") ?? "";
  const filtros = { execucao_id: execucao };

  const [planos, setPlanos] = useState([]);
  const [estado, setEstado] = useState({ execucao: null, dados: null, erro: null });

  useEffect(() => {
    api
      .get("/api/relatorios/campanha/planos")
      .then(setPlanos)
      .catch(() => setPlanos([]));
  }, []);

  useEffect(() => {
    let vivo = true;
    api
      .get("/api/relatorios/campanha", { execucao_id: execucao })
      .then((dados) => vivo && setEstado({ execucao, dados, erro: null }))
      .catch((erro) => vivo && setEstado({ execucao, dados: null, erro }));
    return () => {
      vivo = false;
    };
  }, [execucao]);

  const atual = estado.execucao === execucao;
  const dados = atual ? estado.dados : null;
  const erro = atual ? estado.erro : null;
  const ultimo = planos[0];

  return (
    <>
      <Relatorio
        titulo="Campanha"
        recorte={dados?.plano ? recorteDe(dados) : []}
        csv={dados?.plano ? comConsulta("/api/relatorios/campanha/exportacao.csv", filtros) : null}
        filtros={
          ultimo && (
            <div className="filtros">
              <div className="campo filtros__busca">
                <label htmlFor="execucao">Plano</label>
                <select
                  id="execucao"
                  value={execucao || String(ultimo.execucao_id)}
                  /* O último é o padrão, e fica fora do endereço: o link de quem
                     não escolheu continua abrindo no último plano depois do próximo cálculo. */
                  onChange={(e) =>
                    setParametros(
                      e.target.value === String(ultimo.execucao_id) ? {} : { execucao: e.target.value },
                      { replace: true },
                    )
                  }
                >
                  {/* Endereço com execução fora da lista — antiga, ou sem plano: o
                      seletor não finge que está no último enquanto a página mostra outra coisa. */}
                  {execucao && !planos.some((p) => String(p.execucao_id) === execucao) && (
                    <option value={execucao}>Execução {execucao}</option>
                  )}
                  {planos.map((p) => (
                    <option key={p.execucao_id} value={p.execucao_id}>
                      Plano de {comoDataHora(p.concluida_em)} · aplicação de{" "}
                      {comoData(p.aplicacao_inicio)} a {comoData(p.aplicacao_fim)}
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

        {dados && !dados.plano && (
          <section className="painel">
            {/* UC15-A2: sem plano, o relatório leva à tela que o calcula. */}
            <EstadoVazio
              titulo="Nenhum plano de campanha calculado ainda"
              texto="O plano sai da tela Campanha, com o orçamento, o máximo de ações e as cotas."
              acao={{ para: "/campanha", rotulo: "Ir para a Campanha" }}
            />
          </section>
        )}

        {dados?.plano && <Conteudo dados={dados} />}
      </Relatorio>
    </>
  );
}

/** O recorte como a folha o diz, a partir do que a API devolveu. */
function recorteDe(dados) {
  const { plano } = dados;
  return [
    `Plano de ${comoDataHora(plano.concluida_em)}`,
    `aplicação de ${comoData(plano.aplicacao_inicio)} a ${comoData(plano.aplicacao_fim)}`,
    `a partir do período de ${comoPeriodo(dados.periodo_base)}`,
    `previsão ${plano.modelo_versao}`,
  ];
}

function Conteudo({ dados }) {
  const { total, plano } = dados;

  return (
    <>
      <section className="painel painel--inteiro" aria-labelledby="titulo-total-campanha">
        <div className="painel__cabecalho">
          <h3 className="painel__titulo" id="titulo-total-campanha">
            Total do plano
          </h3>
          <span className="etiqueta-estimativa">Estimativa</span>
        </div>
        <dl className="relatorio__resumo">
          <div>
            <dt>Ganho esperado</dt>
            <dd className="num relatorio__principal">{comoDinheiro(total.ganho_esperado)}</dd>
          </div>
          <div>
            <dt>Custo</dt>
            <dd className="num">{comoDinheiro(total.custo)}</dd>
          </div>
          <div>
            <dt>Orçamento</dt>
            <dd className="num">{comoDinheiro(dados.orcamento)}</dd>
          </div>
          <div>
            <dt>Ações</dt>
            <dd className="num">{comoInteiro(total.parceiros)}</dd>
          </div>
        </dl>
        <p className="relatorio__nota">
          O ganho esperado é estimativa, pela previsão {plano.modelo_versao} (RN10) — o custo e o
          número de ações são os do plano gravado. Cada parceiro recebe no máximo uma ação.
        </p>
        <Link
          className="botao botao--secundario relatorio__caminho nao-imprime"
          to={`/execucoes/${plano.execucao_id}`}
        >
          Abrir o plano, parceiro a parceiro
        </Link>
      </section>

      <Grupos
        id="por-acao"
        titulo="Por ação"
        coluna="Ação"
        linhas={dados.por_acao}
        total={total}
        celula={(linha) => linha.rotulo}
      />
      <Grupos
        id="por-categoria"
        titulo="Por categoria"
        coluna="Categoria"
        linhas={dados.por_categoria}
        total={total}
        celula={(linha) => linha.rotulo}
      />
      <Grupos
        id="por-segmento"
        titulo="Por segmento"
        coluna="Segmento"
        linhas={dados.por_segmento}
        total={total}
        celula={(linha) => (linha.chave ? <Segmento valor={linha.chave} /> : linha.rotulo)}
        nota={`O segmento é o do período de ${comoPeriodo(dados.periodo_base)}, de onde o plano partiu.`}
      />
    </>
  );
}

function Grupos({ id, titulo, coluna, linhas, total, celula, nota }) {
  return (
    <section className="painel painel--inteiro" aria-labelledby={`titulo-${id}`}>
      <div className="painel__cabecalho">
        <h3 className="painel__titulo" id={`titulo-${id}`}>
          {titulo}
        </h3>
        <span className="painel__nota">do maior ganho esperado para o menor</span>
      </div>
      <div className="tabela-rolagem">
        <table className="tabela" aria-labelledby={`titulo-${id}`}>
          <thead>
            <tr>
              <th scope="col">{coluna}</th>
              <th scope="col" className="numerica">
                Parceiros
              </th>
              <th scope="col" className="numerica">
                Custo
              </th>
              <th scope="col" className="numerica">
                Ganho esperado
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
                <td className="numerica">{comoDinheiro(linha.custo)}</td>
                <td className="numerica">{comoDinheiro(linha.ganho_esperado)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <th scope="row">Total</th>
              <td className="numerica">{comoInteiro(total.parceiros)}</td>
              <td className="numerica">{comoDinheiro(total.custo)}</td>
              <td className="numerica">{comoDinheiro(total.ganho_esperado)}</td>
            </tr>
          </tfoot>
        </table>
      </div>
      {nota && <p className="relatorio__nota">{nota}</p>}
    </section>
  );
}
