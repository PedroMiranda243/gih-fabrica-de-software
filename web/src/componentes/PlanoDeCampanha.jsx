/**
 * O plano de uma execução — o mesmo bloco na Campanha e na execução aberta pelo
 * histórico: viável (com lacre), inviável (a restrição e quanto falta, nunca um
 * plano parcial) ou falha.
 */
import { Link } from "react-router-dom";

import { tem, useSessao } from "../api/contextoSessao";
import { comoData, comoDinheiro, comoInteiro, comoMilissegundos, ROTULO_MODO_CURTO, ROTULO_RESTRICAO } from "../formato";
import { Ausente, Dinheiro, Estimativa, Segmento } from "./Dados";
import { ErroDaAcao, Nota, Vazio } from "./Estados";
import Icone from "./Icone";
import Lacre from "./Lacre";
import { CaixaDeTabela } from "./Lista";

export default function PlanoDeCampanha({ execucao, novo = false, comMensagens = true }) {
  const { usuario } = useSessao();
  const e = execucao;

  if (e.situacao === "FALHOU") {
    return <ErroDaAcao erro={{ message: `O cálculo falhou.${e.motivo ? ` ${e.motivo}` : ""}`, ajuda: e.ajuda }} />;
  }

  if (e.viavel === false) {
    return (
      <div className="inviavel" role="status">
        <div className="inviavel__cabeca">
          <Icone nome="atencao" className="inviavel__icone" />
          <div>
            <p className="inviavel__titulo">Sem solução viável{e.restricao_violada ? `: ${ROTULO_RESTRICAO[e.restricao_violada] ?? e.restricao_violada}` : ""}.</p>
            {e.motivo && <p>{e.motivo}</p>}
            {e.ajuda && <p className="discreto">{e.ajuda}</p>}
          </div>
        </div>
        <p className="bloco__nota">O sistema não entrega plano que viole restrição: nenhuma ação foi reservada.</p>
        {e.cotas?.length > 0 && <TabelaDeCotas cotas={e.cotas} />}
      </div>
    );
  }

  const modo = `${ROTULO_MODO_CURTO[e.modo] ?? e.modo}${e.threads ? `, ${e.threads} threads` : ""} · ${comoMilissegundos(e.tempo_ms)}`;

  return (
    <div className="plano">
      <div className="plano__topo">
        <Lacre numero={e.id} titulo="Plano calculado" quando={e.concluida_em} quem={e.autor} novo={novo}>
          <span className="lacre__assinatura">Previsões da {e.modelo_versao}, com dados até {comoData(e.periodo_base?.data_fim)}</span>
        </Lacre>
        <Link to="/ajuda#ganho" className="link-seta">
          Como se chega ao ganho esperado? <Icone nome="seta-direita" />
        </Link>
      </div>

      <div className="plano__resumo">
        <div className="plano__ganho">
          <p className="plano__rotulo">
            Ganho esperado <Estimativa />
          </p>
          <p className="plano__valor">
            <Dinheiro valor={e.uplift_total} grande />
          </p>
          <p className="plano__contra">
            Contra o guloso: <strong>{comoDinheiro(e.ganho_guloso)}</strong> <span className="discreto">— o plano simples, para comparar; o otimizador nunca fica abaixo dele.</span>
          </p>
        </div>
        <dl className="pares plano__pares">
          <div>
            <dt>Custo</dt>
            <dd className="valor-forte">
              <Dinheiro valor={e.custo_total} />
            </dd>
            <dd className="discreto texto-pequeno">de {comoDinheiro(e.parametros?.orcamento)} de orçamento</dd>
          </div>
          <div>
            <dt>Ações</dt>
            <dd className="valor-forte">{comoInteiro(e.acoes)}</dd>
            <dd className="discreto texto-pequeno">de até {comoInteiro(e.parametros?.maximo_acoes)}</dd>
          </div>
          <div>
            <dt>Folga</dt>
            <dd>{comoDinheiro(e.folga_orcamento)} e {comoInteiro(e.folga_acoes)} ações</dd>
          </div>
          <div>
            <dt>Aplicação</dt>
            <dd>
              {comoData(e.parametros?.aplicacao_inicio)} a {comoData(e.parametros?.aplicacao_fim)}
            </dd>
          </div>
          <div>
            <dt>Cálculo</dt>
            <dd>{modo}</dd>
          </div>
        </dl>
      </div>

      {e.parcial && <Nota tipo="atencao">O cálculo atingiu o limite de tempo: este é o melhor plano viável encontrado até ali.</Nota>}
      {e.substituicao && <Nota>{e.substituicao}</Nota>}

      {!e.itens?.length ? (
        <Vazio titulo="O plano não tem ações" compacto icone="campanha">
          Nenhuma ação do catálogo cabe no orçamento com ganho esperado.
        </Vazio>
      ) : (
        <>
          <h3 className="bloco__subtitulo">Ações do plano, do maior ganho esperado para o menor</h3>
          <CaixaDeTabela rotulo="Ações do plano">
            <table className="tabela">
              <caption className="sr-only">Ações do plano, do maior ganho esperado (estimativa) para o menor</caption>
              <thead>
                <tr>
                  <th scope="col">Parceiro</th>
                  <th scope="col">Segmento</th>
                  <th scope="col">Categoria</th>
                  <th scope="col">Cauda longa</th>
                  <th scope="col">Ação</th>
                  <th scope="col" className="num">
                    Custo
                  </th>
                  <th scope="col" className="num">
                    Ganho esperado
                  </th>
                </tr>
              </thead>
              <tbody>
                {e.itens.map((i) => (
                  <tr key={`${i.parceiro_id}-${i.acao_id}`}>
                    <th scope="row" className="nome">
                      {tem(usuario, "parceiros") ? <Link to={`/parceiros/${i.parceiro_id}`}>{i.parceiro}</Link> : i.parceiro}
                    </th>
                    <td>
                      <Segmento codigo={i.segmento} />
                    </td>
                    <td>{i.categoria ?? <Ausente porque="sem categoria confirmada" />}</td>
                    <td>{i.cauda_longa ? "sim" : "não"}</td>
                    <td>{i.acao}</td>
                    <td className="num">{comoDinheiro(i.custo)}</td>
                    <td className="num">{comoDinheiro(i.ganho)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CaixaDeTabela>
        </>
      )}

      {e.cotas?.length > 0 && <TabelaDeCotas cotas={e.cotas} />}

      {comMensagens && tem(usuario, "mensagens") && e.itens?.length > 0 && (
        <Link to={`/mensagens?plano=${e.id}`} className="botao botao--secundario plano__mensagens">
          <Icone nome="mensagens" /> Gerar mensagens para este plano
        </Link>
      )}
    </div>
  );
}

function TabelaDeCotas({ cotas }) {
  return (
    <>
      <h3 className="bloco__subtitulo">Cotas, em número de ações</h3>
      <CaixaDeTabela rotulo="Cotas">
        <table className="tabela tabela--compacta tabela--cotas">
          <caption className="sr-only">Cotas em número de ações: mínimo, máximo e quanto o plano deu</caption>
          <thead>
            <tr>
              <th scope="col">Cota</th>
              <th scope="col" className="num">
                Mínimo
              </th>
              <th scope="col" className="num">
                Máximo
              </th>
              <th scope="col" className="num">
                No plano
              </th>
            </tr>
          </thead>
          <tbody>
            {cotas.map((c) => (
              <tr key={c.categoria_id ?? "cauda"}>
                <th scope="row">{c.nome}</th>
                <td className="num">{comoInteiro(c.minimo)}</td>
                <td className="num">{comoInteiro(c.maximo)}</td>
                <td className="num">{c.acoes === null ? <Ausente porque="sem plano" /> : comoInteiro(c.acoes)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </CaixaDeTabela>
    </>
  );
}
