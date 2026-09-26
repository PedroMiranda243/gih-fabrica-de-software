/**
 * O plano de uma execução do otimizador (UC08, passo 8): as ações, as cotas, as
 * folgas, a comparação com o guloso e em que modo rodou — ou a campanha
 * inviável, com a restrição e quanto falta (RN07), ou a falha.
 *
 * Mora em `componentes/` porque duas telas o mostram do mesmo jeito: a Campanha,
 * com o último plano, e a execução aberta pelo histórico (H58).
 */
import { Link } from "react-router-dom";

import {
  comoDataHora,
  comoDinheiro,
  comoDuracao,
  comoFracao,
  comoInteiro,
  comoPeriodo,
  ROTULO_MODO,
  TRACO,
} from "../formato";
import EstadoVazio from "./EstadoVazio";
import Segmento from "./Segmento";
import "../estilos/campanha.css";

export default function PlanoDeCampanha({ execucao }) {
  if (execucao.situacao === "FALHOU") {
    return (
      <div className="aviso" role="alert">
        <p className="aviso__titulo">O cálculo falhou.</p>
        <p className="aviso__ajuda">{execucao.motivo}</p>
      </div>
    );
  }
  if (execucao.viavel === false) {
    return (
      <section className="painel" aria-labelledby="titulo-plano">
        <div className="painel__cabecalho">
          <h2 className="painel__titulo" id="titulo-plano">
            Plano recomendado
          </h2>
          <span className="painel__nota">{comoDataHora(execucao.concluida_em)}</span>
        </div>
        <div className="campanha__corpo">
          <div className="aviso campanha__inviavel">
            <p className="aviso__titulo">Sem solução viável. {execucao.motivo}</p>
            {execucao.ajuda && <p className="aviso__ajuda">{execucao.ajuda}</p>}
            <p className="aviso__ajuda">O sistema não entrega plano que viole restrição (RN07).</p>
          </div>
          <Cotas cotas={execucao.cotas} />
        </div>
      </section>
    );
  }

  const p = execucao.parametros;
  const melhora =
    execucao.ganho_guloso && Number(execucao.ganho_guloso) > 0
      ? Number(execucao.uplift_total) / Number(execucao.ganho_guloso) - 1
      : null;

  return (
    <section className="painel" aria-labelledby="titulo-plano">
      <div className="painel__cabecalho">
        <h2 className="painel__titulo" id="titulo-plano">
          Plano recomendado
        </h2>
        <span className="etiqueta-estimativa">Estimativa</span>
        <span className="painel__nota num">
          {comoInteiro(execucao.acoes)} ações · {comoDinheiro(execucao.custo_total)} de{" "}
          {comoDinheiro(p.orcamento)} · ganho esperado {comoDinheiro(execucao.uplift_total)}
        </span>
      </div>

      <div className="campanha__corpo campanha__resumo">
        {execucao.parcial && (
          <p className="campanha__parcial">
            O cálculo atingiu o limite de tempo: este é o melhor plano viável encontrado até ali.
          </p>
        )}
        {execucao.substituicao && <p className="campanha__parcial">{execucao.substituicao}</p>}
        <dl className="campanha__fatos">
          <dt>Previsões</dt>
          <dd>
            {execucao.modelo_versao}, com dados até {comoPeriodo(execucao.periodo_base)}
          </dd>
          <dt>Aplicação</dt>
          <dd>{comoPeriodo({ data_inicio: p.aplicacao_inicio, data_fim: p.aplicacao_fim })}</dd>
          <dt>Folga</dt>
          <dd className="num">
            {comoDinheiro(execucao.folga_orcamento)} do orçamento · {comoInteiro(execucao.folga_acoes)}{" "}
            {execucao.folga_acoes === 1 ? "ação" : "ações"}
          </dd>
          <dt>Contra o guloso</dt>
          <dd className="num">
            {melhora === null
              ? TRACO
              : melhora > 0.00005
                ? `${comoFracao(melhora)} acima do plano guloso (${comoDinheiro(execucao.ganho_guloso)})`
                : `igual ao plano guloso (${comoDinheiro(execucao.ganho_guloso)})`}
          </dd>
          <dt>Cálculo</dt>
          <dd className="num">
            {ROTULO_MODO[execucao.modo]}
            {execucao.threads ? `, ${comoInteiro(execucao.threads)} threads` : ""} ·{" "}
            {comoDuracao(execucao.tempo_ms)} · {comoDataHora(execucao.concluida_em)}
            {execucao.autor ? ` · ${execucao.autor}` : ""}
          </dd>
        </dl>
        <Cotas cotas={execucao.cotas} />
      </div>

      {execucao.itens?.length ? (
        <div className="tabela-rolagem">
          <table className="tabela campanha__itens">
            <caption className="so-leitor">Ações do plano, do maior ganho esperado para o menor</caption>
            <thead>
              <tr>
                <th scope="col">Parceiro</th>
                <th scope="col">Segmento</th>
                <th scope="col">Categoria</th>
                <th scope="col">Cauda longa</th>
                <th scope="col">Ação</th>
                <th scope="col" className="numerica">
                  Custo
                </th>
                <th scope="col" className="numerica">
                  Ganho esperado
                </th>
              </tr>
            </thead>
            <tbody>
              {execucao.itens.map((item) => (
                <tr key={item.parceiro_id}>
                  <td className="nome">
                    <Link className="nome__link" to={`/parceiros/${item.parceiro_id}`}>
                      {item.parceiro}
                    </Link>
                  </td>
                  <td>
                    <Segmento valor={item.segmento} />
                  </td>
                  <td>{item.categoria ?? "Pendente"}</td>
                  <td>{item.cauda_longa ? "Sim" : "Não"}</td>
                  <td>{item.acao}</td>
                  <td className="numerica">{comoDinheiro(item.custo)}</td>
                  <td className="numerica">{comoDinheiro(item.ganho)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EstadoVazio
          titulo="O plano não tem ações"
          texto="Nenhuma ação do catálogo cabe no orçamento com ganho esperado."
        />
      )}
    </section>
  );
}

/** As cotas em contagem (RN11), com quanto o plano deu a cada uma. */
function Cotas({ cotas }) {
  if (!cotas?.length) return null;
  return (
    <table className="tabela campanha__cotas-tabela">
      <caption className="campanha__legenda">Cotas, em número de ações</caption>
      <thead>
        <tr>
          <th scope="col">Cota</th>
          <th scope="col" className="numerica">
            Mínimo
          </th>
          <th scope="col" className="numerica">
            Máximo
          </th>
          <th scope="col" className="numerica">
            No plano
          </th>
        </tr>
      </thead>
      <tbody>
        {cotas.map((c) => (
          <tr key={c.categoria_id ?? "cauda"}>
            <td>{c.nome}</td>
            <td className="numerica">{comoInteiro(c.minimo)}</td>
            <td className="numerica">{comoInteiro(c.maximo)}</td>
            <td className="numerica">{c.acoes === null ? TRACO : comoInteiro(c.acoes)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
