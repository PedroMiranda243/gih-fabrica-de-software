/**
 * O histórico das execuções do otimizador — RF34, UC08 passo 10, história H58.
 *
 * Cada linha diz quem calculou, quando, com que parâmetros, em que modo, em
 * quanto tempo e com que resultado, da mais recente para a mais antiga.
 *
 * **Abrir o plano de uma execução é da campanha** (UC08): o Gestor e o Analista
 * abrem; o Administrador vê o histórico (RF34), mas não o plano parceiro a
 * parceiro. Quem abre o quê vem da API (`usuario.telas`), como o menu — a tela
 * só desenha a linha com ou sem o link.
 */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api/cliente";
import { useSessao } from "../api/contextoSessao";
import { Esqueleto } from "../componentes/Carregando";
import EstadoVazio from "../componentes/EstadoVazio";
import {
  comoDataHora,
  comoDinheiro,
  comoDuracao,
  comoFracao,
  comoInteiro,
  ROTULO_MODO,
  ROTULO_RESTRICAO,
} from "../formato";
import "../estilos/execucoes.css";

const TAMANHO_PAGINA = 20;

export default function Execucoes() {
  const { usuario } = useSessao();
  const abrePlano = Boolean(usuario?.telas?.includes("execucao"));
  const [pagina, setPagina] = useState(1);
  const [estado, setEstado] = useState({ pagina: null, dados: null, erro: null });

  useEffect(() => {
    let vivo = true;
    api
      .get("/api/otimizacoes", { pagina, tamanho: TAMANHO_PAGINA })
      .then((dados) => vivo && setEstado({ pagina, dados, erro: null }))
      .catch((erro) => vivo && setEstado({ pagina, dados: null, erro }));
    return () => {
      vivo = false;
    };
  }, [pagina]);

  const atual = estado.pagina === pagina;
  const dados = atual ? estado.dados : null;
  const erro = atual ? estado.erro : null;
  const total = dados?.total ?? 0;
  const primeiro = (pagina - 1) * TAMANHO_PAGINA + 1;
  const ultimo = Math.min(pagina * TAMANHO_PAGINA, total);

  return (
    <section className="painel" aria-labelledby="titulo-execucoes">
      <div className="painel__cabecalho">
        <h2 className="painel__titulo" id="titulo-execucoes">
          Histórico
        </h2>
        {dados && <span className="painel__nota">{comoInteiro(total)} no total</span>}
      </div>

      {!abrePlano && (
        <p className="execucoes__nota">
          O plano de cada execução, parceiro a parceiro, é da tela de campanha. Aqui fica o resumo de cada
          uma: quem calculou, com que parâmetros, em que modo, em quanto tempo e com que resultado.
        </p>
      )}

      {erro && (
        <div className="aviso" role="alert">
          <p className="aviso__titulo">{erro.message}</p>
          {erro.ajuda && <p className="aviso__ajuda">{erro.ajuda}</p>}
        </div>
      )}

      {!dados && !erro && (
        <div className="execucoes__corpo" aria-hidden="true">
          <Esqueleto altura={220} />
        </div>
      )}

      {dados && total === 0 && (
        <EstadoVazio
          titulo="Nenhuma execução ainda"
          texto="Cada plano calculado na campanha aparece aqui, com quem o calculou e o resultado."
        />
      )}

      {dados && total > 0 && (
        <>
          <div className="tabela-rolagem">
            <table className="tabela execucoes__tabela">
              <caption className="so-leitor">
                Execuções do otimizador, da mais recente para a mais antiga
              </caption>
              <thead>
                <tr>
                  <th scope="col">Iniciada em</th>
                  <th scope="col">Por</th>
                  <th scope="col">Parâmetros</th>
                  <th scope="col">Modo</th>
                  <th scope="col" className="numerica">
                    Tempo
                  </th>
                  <th scope="col">Resultado</th>
                </tr>
              </thead>
              <tbody>
                {dados.itens.map((e) => (
                  <LinhaExecucao key={e.id} execucao={e} abrePlano={abrePlano} />
                ))}
              </tbody>
            </table>
          </div>

          <div className="paginacao">
            <span className="paginacao__posicao num">
              {comoInteiro(primeiro)}–{comoInteiro(ultimo)} de {comoInteiro(total)}
            </span>
            <button
              type="button"
              className="botao botao--secundario"
              disabled={pagina <= 1}
              onClick={() => setPagina((p) => p - 1)}
            >
              Anterior
            </button>
            <button
              type="button"
              className="botao botao--secundario"
              disabled={ultimo >= total}
              onClick={() => setPagina((p) => p + 1)}
            >
              Próxima
            </button>
          </div>
        </>
      )}
    </section>
  );
}

function LinhaExecucao({ execucao: e, abrePlano }) {
  const quando = comoDataHora(e.iniciada_em);
  return (
    <tr>
      <td className="nome quando">
        {abrePlano ? (
          <Link className="nome__link" to={`/execucoes/${e.id}`}>
            {quando}
          </Link>
        ) : (
          quando
        )}
      </td>
      <td>{e.autor ?? "Terminal"}</td>
      <td className="secundaria">{resumoDosParametros(e.parametros)}</td>
      <td>
        {ROTULO_MODO[e.modo]}
        {e.threads ? <span className="secundaria">, {comoInteiro(e.threads)} threads</span> : null}
        {/* A troca (UC08-A4) em poucas palavras; a frase inteira está no plano. */}
        {e.substituicao && (
          <span className="execucoes__detalhe">pedido em {ROTULO_MODO[e.parametros.modo]}</span>
        )}
      </td>
      <td className="numerica">{comoDuracao(e.tempo_ms)}</td>
      <td>
        <Resultado execucao={e} />
      </td>
    </tr>
  );
}

function resumoDosParametros(p) {
  const partes = [comoDinheiro(p.orcamento), `até ${comoInteiro(p.maximo_acoes)} ações`];
  if (p.cota_cauda_longa) partes.push(`cauda longa ≥ ${comoFracao(p.cota_cauda_longa, 0)}`);
  const cotas = p.cotas_categoria?.length ?? 0;
  if (cotas) partes.push(`${comoInteiro(cotas)} ${cotas === 1 ? "cota" : "cotas"} de categoria`);
  return partes.join(" · ");
}

function Resultado({ execucao: e }) {
  if (e.situacao === "EM_ANDAMENTO") return "Calculando…";
  if (e.situacao === "FALHOU") {
    return (
      <>
        Falhou
        <span className="execucoes__detalhe">{e.motivo}</span>
      </>
    );
  }
  if (e.viavel === false) {
    return (
      <>
        Sem solução viável
        <span className="execucoes__detalhe">
          restrição: {ROTULO_RESTRICAO[e.restricao_violada] ?? e.restricao_violada}
        </span>
      </>
    );
  }
  return (
    <>
      {comoInteiro(e.acoes)} {e.acoes === 1 ? "ação" : "ações"} · ganho de {comoDinheiro(e.uplift_total)}
      {e.parcial && <span className="execucoes__detalhe">parcial: atingiu o limite de tempo</span>}
    </>
  );
}
