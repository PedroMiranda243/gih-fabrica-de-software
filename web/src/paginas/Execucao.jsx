/** Uma execução: o que foi pedido e o plano que saiu, com CSV (só com itens) e impressão. */
import { useParams } from "react-router-dom";

import { api } from "../api/cliente";
import { useCarregar } from "../api/ganchos";
import { useSessao } from "../api/sessao";
import { Carregando, ErroDaTela, Nota, Vazio } from "../componentes/Estados";
import Icone from "../componentes/Icone";
import { Trilha } from "../componentes/Lista";
import PlanoDeCampanha from "../componentes/PlanoDeCampanha";
import { useTitulo } from "../componentes/Titulo";
import { comoData, comoDataHora, comoDinheiro, comoFracao, comoInteiro, cotasDoPedido, ROTULO_MODO_CURTO } from "../formato";

export default function Execucao() {
  const { id } = useParams();
  const { usuario } = useSessao();
  const execucao = useCarregar(() => api.get(`/api/otimizacoes/${id}`), id);
  const e = execucao.dados;
  const nome = e ? `Execução de ${comoDataHora(e.iniciada_em)}` : "Execução";
  useTitulo(nome, "Execuções");

  if (execucao.carregando) return <Carregando rotulo="Carregando a execução" linhas={8} />;
  if (execucao.erro?.status === 404) {
    return (
      <div className="pagina">
        <Trilha passos={[{ rotulo: "Execuções", para: "/execucoes" }, { rotulo: "Não encontrada" }]} />
        <Vazio titulo="Execução não encontrada" acao="Voltar para as execuções" para="/execucoes" icone="busca">
          Ela pode ter sido removida, ou o endereço está incompleto.
        </Vazio>
      </div>
    );
  }
  if (execucao.erro) return <ErroDaTela erro={execucao.erro} />;

  const p = e.parametros;
  const temItens = e.situacao === "CONCLUIDA" && e.viavel && e.itens?.length > 0;

  return (
    <div className="pagina pagina--relatorio">
      <div className="barra-acoes nao-imprime">
        <Trilha passos={[{ rotulo: "Execuções", para: "/execucoes" }, { rotulo: nome }]} />
        <div className="barra-acoes__botoes">
          {temItens && (
            <a className="botao botao--secundario" href={`/api/otimizacoes/${e.id}/exportacao.csv`} download>
              <Icone nome="baixar" /> Exportar CSV
            </a>
          )}
          <button type="button" className="botao botao--secundario" onClick={() => window.print()}>
            <Icone nome="imprimir" /> Imprimir ou salvar em PDF
          </button>
        </div>
      </div>
      <article className="folha" aria-labelledby="folha-titulo">
        <header className="folha__cabeca">
          <p className="so-impressao folha__marca">GIH — Growth Intelligence Hub</p>
          <h2 id="folha-titulo" className="folha__titulo">
            {nome}
          </h2>
          <p className="folha__recorte">
            Calculada por {e.autor ?? "pelo terminal"} · previsões da {e.modelo_versao}
          </p>
          <p className="so-impressao folha__emitido">
            Emitido em {comoDataHora(new Date().toISOString())} por {usuario?.nome}.
          </p>
        </header>
        <section className="folha__secao" aria-labelledby="t-pedido">
          <h3 id="t-pedido" className="folha__subtitulo">
            O que foi pedido
          </h3>
          <dl className="pares pares--pedido">
            <div>
              <dt>Orçamento</dt>
              <dd>{comoDinheiro(p.orcamento)}</dd>
            </div>
            <div>
              <dt>Máximo de ações</dt>
              <dd>{comoInteiro(p.maximo_acoes)}</dd>
            </div>
            <div>
              <dt>Cauda longa</dt>
              <dd>{p.cota_cauda_longa === null ? "Sem cota" : comoFracao(p.cota_cauda_longa, 0)}</dd>
            </div>
            <div>
              <dt>Cotas por categoria</dt>
              <dd>{p.cotas_categoria.length ? cotasDoPedido(e).join("; ") : "Nenhuma"}</dd>
            </div>
            <div>
              <dt>Aplicação</dt>
              <dd>
                {comoData(p.aplicacao_inicio)} a {comoData(p.aplicacao_fim)}
              </dd>
            </div>
            <div>
              <dt>Modo</dt>
              <dd>{p.modo ? ROTULO_MODO_CURTO[p.modo] : "Automático: GPU, se houver, e senão CPU paralelo"}</dd>
            </div>
          </dl>
        </section>
        <section className="folha__secao" aria-labelledby="t-saiu">
          <h3 id="t-saiu" className="folha__subtitulo">
            O plano que saiu
          </h3>
          {e.situacao === "EM_ANDAMENTO" ? (
            <Nota>Esta execução ainda está calculando. A tela de campanha a acompanha até o fim; o plano aparece aqui quando ela terminar.</Nota>
          ) : (
            <PlanoDeCampanha execucao={e} />
          )}
        </section>
      </article>
    </div>
  );
}
