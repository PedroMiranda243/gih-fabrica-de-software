/**
 * Uma execução aberta pelo histórico — história H58, RF34.
 *
 * O que foi pedido — as restrições e o modo — e o plano que saiu, mostrado do
 * mesmo jeito que a Campanha o mostrou. É o que permite retomar uma decisão:
 * "com que orçamento e que cotas saiu aquele plano?" tem a resposta aqui, e não
 * na memória de quem calculou.
 *
 * **O plano sai do sistema por dois caminhos** (RF53, H91): o CSV, com os itens
 * que a tela mostra, e a impressão do navegador, pela mesma folha dos
 * relatórios. O CSV só aparece quando há itens — a execução inviável, a que
 * falhou e a que ainda calcula não têm o que exportar.
 */
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "../api/cliente";
import { Esqueleto } from "../componentes/Carregando";
import EstadoVazio from "../componentes/EstadoVazio";
import PlanoDeCampanha from "../componentes/PlanoDeCampanha";
import { useTituloDaAba } from "../componentes/tituloDaAba";
import { comoDataHora, comoDinheiro, comoFracao, comoInteiro, cotasDoPedido, ROTULO_MODO, TRACO } from "../formato";
import "../estilos/execucoes.css";
import "../estilos/relatorios.css";

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
  useTituloDaAba(execucao ? `Execução de ${comoDataHora(execucao.iniciada_em)}` : null);

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
      <div className="relatorio__cabecalho">
        <nav className="trilha nao-imprime" aria-label="Você está em">
          <Link to="/execucoes">Execuções</Link>
          <span aria-hidden="true">›</span>
          <span aria-current="page">{execucao ? comoDataHora(execucao.iniciada_em) : "Execução"}</span>
        </nav>

        {execucao && (
          <>
            {/* Só na folha: o título, que na tela é a trilha. */}
            <div className="so-impressao">
              <p className="relatorio__titulo">Plano de campanha</p>
              <p className="relatorio__emissao">
                Execução de {comoDataHora(execucao.iniciada_em)}
                {execucao.autor ? `, por ${execucao.autor}` : ""} · Growth Intelligence Hub
              </p>
            </div>
            <div className="relatorio__acoes nao-imprime">
              {execucao.itens?.length > 0 && (
                <a
                  className="botao botao--secundario"
                  href={`/api/otimizacoes/${execucao.id}/exportacao.csv`}
                  download
                >
                  Exportar CSV
                </a>
              )}
              <button type="button" className="botao botao--secundario" onClick={() => window.print()}>
                Imprimir ou salvar em PDF
              </button>
            </div>
          </>
        )}
      </div>

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
            <PlanoDeCampanha execucao={execucao} origem="Execução" />
          )}
        </>
      )}
    </>
  );
}

/** As restrições e o modo que o gestor pediu — os mesmos campos da tela de campanha. */
function Pedido({ execucao: e }) {
  const p = e.parametros;
  const cotas = cotasDoPedido(e);

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
          <dd>{p.modo ? ROTULO_MODO[p.modo] : "Automático: GPU, se houver, e senão CPU paralelo"}</dd>
        </dl>
      </div>
    </section>
  );
}
