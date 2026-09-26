/**
 * Uma execução aberta pelo histórico — história H58, RF34.
 *
 * O que foi pedido — as restrições e o modo — e o plano que saiu, mostrado do
 * mesmo jeito que a Campanha o mostrou. É o que permite retomar uma decisão:
 * "com que orçamento e que cotas saiu aquele plano?" tem a resposta aqui, e não
 * na memória de quem calculou.
 */
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "../api/cliente";
import { Esqueleto } from "../componentes/Carregando";
import EstadoVazio from "../componentes/EstadoVazio";
import PlanoDeCampanha from "../componentes/PlanoDeCampanha";
import { comoDataHora, comoDinheiro, comoFracao, comoInteiro, ROTULO_MODO, TRACO } from "../formato";
import "../estilos/execucoes.css";

export default function Execucao() {
  const { id } = useParams();
  const [estado, setEstado] = useState({ id: null, dados: null, erro: null });

  useEffect(() => {
    let vivo = true;
    api
      .get(`/api/otimizacoes/${id}`)
      .then((dados) => vivo && setEstado({ id, dados, erro: null }))
      .catch((erro) => vivo && setEstado({ id, dados: null, erro }));
    return () => {
      vivo = false;
    };
  }, [id]);

  const atual = estado.id === id;
  const execucao = atual ? estado.dados : null;
  const erro = atual ? estado.erro : null;

  if (erro?.status === 404) {
    return (
      <EstadoVazio
        titulo="Execução não encontrada"
        texto="Ela pode ter sido removida, ou o endereço está incompleto."
        acao={{ para: "/execucoes", rotulo: "Voltar para as execuções" }}
      />
    );
  }

  return (
    <>
      <nav className="trilha" aria-label="Você está em">
        <Link to="/execucoes">Execuções</Link>
        <span aria-hidden="true">›</span>
        <span aria-current="page">{execucao ? comoDataHora(execucao.iniciada_em) : "Execução"}</span>
      </nav>

      {erro && (
        <div className="aviso" role="alert">
          <p className="aviso__titulo">{erro.message}</p>
          {erro.ajuda && <p className="aviso__ajuda">{erro.ajuda}</p>}
        </div>
      )}

      {!execucao && !erro && (
        <section className="painel" aria-busy="true" aria-label="Carregando a execução">
          <div className="execucoes__corpo">
            <Esqueleto altura={220} />
          </div>
        </section>
      )}

      {execucao && (
        <>
          <Pedido execucao={execucao} />
          {execucao.situacao === "EM_ANDAMENTO" ? (
            <div className="aviso aviso--informativo">
              <p className="aviso__titulo">Esta execução ainda está calculando.</p>
              <p className="aviso__ajuda">
                A tela de campanha a acompanha até o fim; o plano aparece aqui quando ela terminar.
              </p>
            </div>
          ) : (
            <PlanoDeCampanha execucao={execucao} />
          )}
        </>
      )}
    </>
  );
}

/** As restrições e o modo que o gestor pediu — os mesmos campos da tela de campanha. */
function Pedido({ execucao: e }) {
  const p = e.parametros;
  const nomes = Object.fromEntries(e.cotas.filter((c) => c.categoria_id !== null).map((c) => [c.categoria_id, c.nome]));
  const cotas = p.cotas_categoria.map((c) => {
    const limites = [
      c.minimo !== null && `mín. ${comoFracao(c.minimo, 0)}`,
      c.maximo !== null && `máx. ${comoFracao(c.maximo, 0)}`,
    ].filter(Boolean);
    return `${nomes[c.categoria_id] ?? `categoria ${c.categoria_id}`}: ${limites.join(", ")}`;
  });

  return (
    <section className="painel" aria-labelledby="titulo-pedido">
      <div className="painel__cabecalho">
        <h2 className="painel__titulo" id="titulo-pedido">
          O que foi pedido
        </h2>
        <span className="painel__nota">
          {e.autor ? `Por ${e.autor}` : "Pelo terminal"}, {comoDataHora(e.iniciada_em)}
        </span>
      </div>
      <div className="execucoes__corpo">
        <dl className="campanha__fatos">
          <dt>Orçamento</dt>
          <dd className="num">{comoDinheiro(p.orcamento)}</dd>
          <dt>Máximo de ações</dt>
          <dd className="num">{comoInteiro(p.maximo_acoes)}</dd>
          <dt>Cauda longa</dt>
          <dd>{p.cota_cauda_longa ? `ao menos ${comoFracao(p.cota_cauda_longa, 0)} das ações` : TRACO}</dd>
          <dt>Cotas por categoria</dt>
          <dd>{cotas.length ? cotas.join(" · ") : TRACO}</dd>
          <dt>Modo</dt>
          <dd>{p.modo ? ROTULO_MODO[p.modo] : "Automático, o mais rápido disponível"}</dd>
        </dl>
      </div>
    </section>
  );
}
