/**
 * O relatório das operações do sistema (UC15 · RF47 · H87) — do Administrador.
 *
 * A trilha de auditoria responde "quem fez isto?"; este relatório responde
 * "quanto se fez, e do quê": as operações de um intervalo, por tipo de ação,
 * por pessoa e por dia. Os filtros são os da trilha, e o total é o que a tela
 * de auditoria mostra no mesmo recorte.
 *
 * **As datas que valem são as que a API devolve.** Sem escolha, ela usa os
 * últimos trinta dias; a tela escreve o intervalo da resposta, e não o do
 * endereço, que pode estar vazio.
 *
 * **Barra e número, e não só barra.** Cada grupo tem a barra, que dá a
 * proporção de relance, e a contagem em texto ao lado — nada depende só da
 * barra, e a folha impressa continua legível sem ela. Uma cor só, a da rampa
 * dos gráficos: é quantidade, e não categoria. A barra mais longa é a do maior
 * grupo daquela tabela.
 */
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { api, comConsulta } from "../api/cliente";
import { Esqueleto } from "../componentes/Carregando";
import EstadoVazio from "../componentes/EstadoVazio";
import Relatorio, { ErroDoRelatorio } from "../componentes/Relatorio";
import { comoData, comoInteiro } from "../formato";

export default function RelatorioOperacoes() {
  const [parametros, setParametros] = useSearchParams();
  const de = parametros.get("de") ?? "";
  const ate = parametros.get("ate") ?? "";
  const autor = parametros.get("autor") ?? "";
  const acao = parametros.get("acao") ?? "";
  const filtros = { de, ate, autor, acao };
  const consulta = JSON.stringify(filtros);

  const [acoes, setAcoes] = useState([]);
  const [usuarios, setUsuarios] = useState([]);
  const [estado, setEstado] = useState({ consulta: null, dados: null, erro: null });

  useEffect(() => {
    /* As opções dos dois filtros, as mesmas da tela de auditoria. Se uma
       falhar, o filtro fica só com "todos". */
    api.get("/api/auditoria/acoes").then(setAcoes).catch(() => setAcoes([]));
    api.get("/api/usuarios").then(setUsuarios).catch(() => setUsuarios([]));
  }, []);

  useEffect(() => {
    let vivo = true;
    api
      .get("/api/relatorios/operacoes", JSON.parse(consulta))
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

  return (
    <>
      <Relatorio
        titulo="Operações do sistema"
        recorte={dados ? recorteDe(dados, usuarios, acoes) : []}
        csv={dados ? comConsulta("/api/relatorios/operacoes/exportacao.csv", filtros) : null}
        filtros={
          <div className="filtros">
            <div className="campo">
              <label htmlFor="de">De</label>
              <input id="de" type="date" value={de} onChange={(e) => ajustar({ de: e.target.value })} />
            </div>
            <div className="campo">
              <label htmlFor="ate">Até</label>
              <input id="ate" type="date" value={ate} onChange={(e) => ajustar({ ate: e.target.value })} />
            </div>
            <div className="campo">
              <label htmlFor="autor">Quem fez</label>
              <select id="autor" value={autor} onChange={(e) => ajustar({ autor: e.target.value })}>
                <option value="">Todas as pessoas</option>
                {usuarios.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.nome} ({u.login})
                  </option>
                ))}
              </select>
            </div>
            <div className="campo">
              <label htmlFor="acao">Ação</label>
              <select id="acao" value={acao} onChange={(e) => ajustar({ acao: e.target.value })}>
                <option value="">Todas as ações</option>
                {acoes.map((a) => (
                  <option key={a.acao} value={a.acao}>
                    {a.rotulo}
                  </option>
                ))}
              </select>
            </div>
          </div>
      
        }
      >
        <ErroDoRelatorio erro={erro} />

        {!dados && !erro && (
          <div role="status" aria-label="Carregando o relatório">
            <Esqueleto altura={96} style={{ marginBottom: "var(--esp-12)" }} />
            <Esqueleto altura={280} />
          </div>
        )}

        {dados && dados.total === 0 && (
          <section className="painel">
            {/* UC15-E1: recorte sem dado diz isso, em vez de três tabelas vazias. */}
            <EstadoVazio
              titulo="Nenhuma operação nesse recorte"
              texto="Não houve operação registrada com esses filtros. Amplie as datas ou tire um dos filtros."
            />
          </section>
        )}

        {dados && dados.total > 0 && (
          <>
            <section className="painel painel--inteiro" aria-labelledby="titulo-total-operacoes">
              <div className="painel__cabecalho">
                <h3 className="painel__titulo" id="titulo-total-operacoes">
                  Total do intervalo
                </h3>
                <Link
                  className="indicador__acao nao-imprime"
                  to={`/auditoria?${new URLSearchParams(
                    Object.entries({ ...filtros, de: dados.de, ate: dados.ate }).filter(([, v]) => v),
                  )}`}
                >
                  Ver estas operações na trilha
                </Link>
              </div>
              <dl className="relatorio__resumo">
                <div>
                  <dt>Operações</dt>
                  <dd className="num relatorio__principal">{comoInteiro(dados.total)}</dd>
                </div>
                <div>
                  <dt>Tipos de ação</dt>
                  <dd className="num">{comoInteiro(dados.por_acao.length)}</dd>
                </div>
                <div>
                  <dt>Pessoas</dt>
                  <dd className="num">{comoInteiro(dados.pessoas)}</dd>
                </div>
                <div>
                  <dt>Dias com operação</dt>
                  <dd className="num">{comoInteiro(dados.por_dia.length)}</dd>
                </div>
              </dl>
            </section>

            <Contagens id="por-acao" titulo="Por tipo de ação" coluna="Ação" linhas={dados.por_acao} />
            <Contagens
              id="por-usuario"
              titulo="Por pessoa"
              coluna="Quem fez"
              linhas={dados.por_usuario}
              /* As que mais fizeram, uma a uma; as outras, somadas pela API. */
              resto={dados.outras_pessoas}
              nota={
                "“Sem usuário” são as operações que não têm a quem apontar, como a entrada recusada com um login que não existe." +
                (dados.outras_pessoas ? " O arquivo CSV traz todas as pessoas, uma a uma." : "")
              }
            />
            <Contagens
              id="por-dia"
              titulo="Por dia"
              coluna="Dia"
              linhas={dados.por_dia}
              rotulo={(linha) => comoData(linha.chave)}
              nota="Só os dias em que houve operação. O dia é o do relógio do servidor, como nos filtros da trilha."
            />
          </>
        )}
      </Relatorio>
    </>
  );
}

/** O recorte como a folha o diz: as datas que valeram e os filtros, pelo nome. */
function recorteDe(dados, usuarios, acoes) {
  const autor = usuarios.find((u) => u.id === dados.autor);
  const acao = acoes.find((a) => a.acao === dados.acao);
  return [
    `De ${comoData(dados.de)} a ${comoData(dados.ate)}`,
    dados.autor === null ? "todas as pessoas" : `feitas por ${autor ? autor.nome : `usuário ${dados.autor}`}`,
    dados.acao === null ? "todas as ações" : `ação: ${acao ? acao.rotulo : dados.acao}`,
  ];
}

function Contagens({ id, titulo, coluna, linhas, resto, rotulo = (linha) => linha.rotulo, nota }) {
  /* A barra mais longa é a do maior grupo desta tabela, e não a do total: com o
     total como referência, um grupo dominante deixaria os outros como fiapos. */
  const maior = Math.max(...linhas.map((linha) => linha.total));

  return (
    <section className="painel" aria-labelledby={`titulo-${id}`}>
      <div className="painel__cabecalho">
        <h3 className="painel__titulo" id={`titulo-${id}`}>
          {titulo}
        </h3>
        <span className="painel__nota">
          {resto
            ? `as ${comoInteiro(linhas.length)} que mais fizeram`
            : `${comoInteiro(linhas.length)} ${linhas.length === 1 ? "linha" : "linhas"}`}
        </span>
      </div>
      <div className="tabela-rolagem">
        <table className="tabela" aria-labelledby={`titulo-${id}`}>
          <thead>
            <tr>
              <th scope="col">{coluna}</th>
              {/* A barra repete o número ao lado: fica fora da leitura da tabela. */}
              <td className="contagem__celula" aria-hidden="true" />
              <th scope="col" className="numerica">
                Operações
              </th>
            </tr>
          </thead>
          <tbody>
            {linhas.map((linha) => (
              <tr key={linha.chave ?? linha.rotulo}>
                <th scope="row" className="nome">
                  {rotulo(linha)}
                </th>
                <td className="contagem__celula" aria-hidden="true">
                  <span className="contagem__trilho">
                    <span
                      className="contagem__barra"
                      style={{ width: `${(linha.total / maior) * 100}%` }}
                    />
                  </span>
                </td>
                <td className="numerica">{comoInteiro(linha.total)}</td>
              </tr>
            ))}
          </tbody>
          {resto && (
            <tfoot>
              <tr>
                <th scope="row">{resto.rotulo}</th>
                <td aria-hidden="true" />
                <td className="numerica">{comoInteiro(resto.total)}</td>
              </tr>
            </tfoot>
          )}
        </table>
      </div>
      {nota && <p className="relatorio__nota">{nota}</p>}
    </section>
  );
}
