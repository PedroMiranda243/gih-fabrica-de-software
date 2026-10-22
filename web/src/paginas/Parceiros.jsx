/**
 * Parceiros — a lista da rede, com o desempenho do período mais recente ao lado
 * do cadastro. Filtros e ordenação moram no endereço, com os nomes da API.
 */
import { Link, useLocation } from "react-router-dom";

import { api, comConsulta } from "../api/cliente";
import { useCarregar, useFiltros } from "../api/ganchos";
import { tem, useSessao } from "../api/contextoSessao";
import Busca from "../componentes/Busca";
import Seletor from "../componentes/Seletor";
import { Ausente, Chance, Estimativa, Segmento, Variacao } from "../componentes/Dados";
import { Carregando, ErroDaTela, Sucesso, Vazio } from "../componentes/Estados";
import Icone from "../componentes/Icone";
import { CaixaDeTabela, ColunaOrdenavel, Paginacao } from "../componentes/Lista";
import { useTitulo } from "../componentes/Titulo";
import { comoDinheiro, comoInteiro, comoPeriodo, ORDEM_SEGMENTOS, ROTULO_SEGMENTO, ROTULO_STATUS } from "../formato";

const TAMANHO = 25;
const CHAVES = ["busca", "categoria_id", "segmento", "status", "ativo"];

export default function Parceiros() {
  useTitulo("Parceiros");
  const { usuario } = useSessao();
  const lugar = useLocation();
  const [filtros, mudar] = useFiltros();
  const pagina = Number(filtros.pagina) || 1;
  const ordem = filtros.ordenar_por || "nome";
  const descendente = filtros.descendente === "true";
  const consulta = Object.fromEntries(CHAVES.map((c) => [c, filtros[c]]));
  const categorias = useCarregar(() => api.get("/api/categorias"), "cat");
  const lista = useCarregar(() => api.get("/api/parceiros", { ...consulta, ordenar_por: ordem === "nome" ? undefined : ordem, descendente: descendente || undefined, pagina, tamanho: TAMANHO }), lugar.search);

  const filtrado = CHAVES.some((c) => filtros[c]);
  const csv = comConsulta("/api/parceiros/exportacao.csv", { ...consulta, ordenar_por: ordem === "nome" ? undefined : ordem, descendente: descendente || undefined });
  const d = lista.dados;

  function ordenar(chave, desc) {
    mudar({ ordenar_por: chave === "nome" ? null : chave, descendente: desc ? "true" : null });
  }

  return (
    <div className="pagina">
      <div className="barra-acoes">
        <p className="barra-acoes__contexto">{d?.periodo ? <>Desempenho de {comoPeriodo(d.periodo)}, o período mais recente.</> : " "}</p>
        <div className="barra-acoes__botoes">
          <a className="botao botao--secundario" href={csv} download>
            <Icone nome="baixar" /> Exportar CSV
          </a>
          <Link className="botao botao--primario" to="/parceiros/novo">
            <Icone nome="mais" /> Novo parceiro
          </Link>
        </div>
      </div>

      <form className="filtros" aria-label="Filtros da lista de parceiros" onSubmit={(e) => e.preventDefault()}>
        <div className="campo filtros__busca">
          <label className="campo__rotulo" htmlFor="filtro-busca">
            Buscar por nome
          </label>
          <Busca id="filtro-busca" valor={filtros.busca} aoMudar={(v) => mudar({ busca: v })} aria-describedby="filtro-busca-ajuda" />
          <p className="campo__ajuda" id="filtro-busca-ajuda">
            Ignora maiúsculas e acentuação.
          </p>
        </div>
        <Seletor id="filtro-categoria" rotulo="Categoria" valor={filtros.categoria_id} aoMudar={(v) => mudar({ categoria_id: v })} todos="Todas as categorias" opcoes={(categorias.dados ?? []).map((c) => [c.id, c.nome])} />
        <Seletor id="filtro-segmento" rotulo="Segmento" valor={filtros.segmento} aoMudar={(v) => mudar({ segmento: v })} todos="Todos os segmentos" opcoes={ORDEM_SEGMENTOS.map((s) => [s, ROTULO_SEGMENTO[s]])} />
        <Seletor id="filtro-status" rotulo="Status comercial" valor={filtros.status} aoMudar={(v) => mudar({ status: v })} todos="Todos os status" opcoes={Object.entries(ROTULO_STATUS)} />
        <Seletor id="filtro-ativo" rotulo="Situação" valor={filtros.ativo} aoMudar={(v) => mudar({ ativo: v })} todos="Todas as situações" opcoes={[["true", "Somente ativos"], ["false", "Somente inativos"]]} />
        {filtrado && (
          <button type="button" className="botao botao--fantasma filtros__limpar" onClick={() => mudar(Object.fromEntries(CHAVES.map((c) => [c, null])))}>
            <Icone nome="fechar" /> Limpar filtros
          </button>
        )}
      </form>

      {lugar.state?.aviso && <Sucesso>{lugar.state.aviso}</Sucesso>}
      {d && <NotaDoRisco risco={d.risco} />}

      <section className="bloco bloco--tabela" aria-labelledby="titulo-lista" aria-busy={lista.carregando}>
        <h2 id="titulo-lista" className="sr-only">
          Lista de parceiros
        </h2>
        {lista.carregando && !d && <Carregando rotulo="Carregando os parceiros" linhas={10} />}
        <ErroDaTela erro={lista.erro} />
        {d && !d.itens.length && filtrado && (
          <Vazio titulo="Nenhum parceiro com esse recorte" icone="busca">
            Limpe a busca ou os filtros para ver a base inteira.
          </Vazio>
        )}
        {d && !d.itens.length && !filtrado && (
          <Vazio titulo="Nenhum parceiro cadastrado ainda" acao={tem(usuario, "importar") ? "Importar um relatório" : undefined} para="/importacao" icone="parceiros">
            Os parceiros são criados ao importar o primeiro relatório do período.
          </Vazio>
        )}
        {d && d.itens.length > 0 && (
          <>
            <CaixaDeTabela rotulo="Parceiros">
              <table className={`tabela tabela--parceiros${lista.carregando ? " tabela--recarregando" : ""}`}>
                <caption className="sr-only">
                  Parceiros{filtrado ? " no recorte escolhido" : ""}, com o desempenho do período mais recente
                </caption>
                <thead>
                  <tr>
                    <ColunaOrdenavel chave="nome" rotulo="Parceiro" ordem={ordem} descendente={descendente} aoOrdenar={ordenar} />
                    <th scope="col">Categoria</th>
                    <th scope="col">Segmento</th>
                    <th scope="col">Status</th>
                    <ColunaOrdenavel chave="faturamento" rotulo="Faturamento" numerica ordem={ordem} descendente={descendente} aoOrdenar={ordenar} />
                    <ColunaOrdenavel chave="pedidos" rotulo="Pedidos" numerica ordem={ordem} descendente={descendente} aoOrdenar={ordenar} />
                    <ColunaOrdenavel chave="ticket_medio" rotulo="Ticket médio" numerica ordem={ordem} descendente={descendente} aoOrdenar={ordenar} />
                    <ColunaOrdenavel chave="variacao" rotulo="Variação" numerica ordem={ordem} descendente={descendente} aoOrdenar={ordenar} />
                    <ColunaOrdenavel chave="risco" rotulo="Risco de queda" numerica ordem={ordem} descendente={descendente} aoOrdenar={ordenar} className="col-estimativa" />
                  </tr>
                </thead>
                <tbody>
                  {d.itens.map((p) => (
                    <tr key={p.id} className={p.ativo ? undefined : "linha--inativa"}>
                      <th scope="row" className="nome nome--destaque">
                        <Link to={`/parceiros/${p.id}`} state={{ de: "lista", busca: lugar.search }}>
                          {p.nome}
                        </Link>
                        {!p.ativo && <span className="selo-texto selo-texto--neutro">desativado</span>}
                      </th>
                      <td>
                        {p.categoria ? (
                          <span className="categoria">
                            {p.categoria.nome}
                            {p.origem_categoria === "SUGERIDA_IA" && (
                              <span className="selo-texto selo-texto--sugerida" title="Sugerida pelo nome, ainda não confirmada">
                                sugerida<span className="sr-only">: pelo nome, ainda não confirmada</span>
                              </span>
                            )}
                          </span>
                        ) : (
                          <Ausente porque="sem categoria" />
                        )}
                      </td>
                      <td>{p.desempenho?.segmento ? <Segmento codigo={p.desempenho.segmento} /> : <Ausente porque="sem segmento no período mais recente" />}</td>
                      <td>{ROTULO_STATUS[p.status] ?? p.status}</td>
                      <td className="num">{p.desempenho?.faturamento === null ? <Ausente porque="sem desempenho no período" /> : comoDinheiro(p.desempenho?.faturamento)}</td>
                      <td className="num">{p.desempenho?.pedidos === null ? <Ausente porque="sem desempenho no período" /> : comoInteiro(p.desempenho?.pedidos)}</td>
                      <td className="num">{p.desempenho?.ticket_medio === null ? <Ausente porque="sem desempenho no período" /> : comoDinheiro(p.desempenho?.ticket_medio)}</td>
                      <td className="num">
                        <Variacao valor={p.desempenho?.variacao_percentual} semBase="sem variação calculável" />
                      </td>
                      <td className="num estimado">
                        <Chance valor={p.risco_queda} porque={d.risco ? "Sem previsão na versão em uso do modelo" : "O modelo ainda não foi treinado"} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CaixaDeTabela>
            <Paginacao pagina={pagina} tamanho={TAMANHO} total={d.total} aoMudar={(p) => mudar({ pagina: p > 1 ? p : null }, { manterPagina: true })} rotulo="parceiros" />
          </>
        )}
      </section>
    </div>
  );
}


function NotaDoRisco({ risco }) {
  if (!risco) {
    return (
      <p className="nota-estimativa">
        <Estimativa />
        <span>
          O risco de queda aparece depois do primeiro treino do modelo, na tela Modelo. <Link to="/ajuda#estimativa">O que é estimativa?</Link>
        </span>
      </p>
    );
  }
  return (
    <p className="nota-estimativa">
      <Estimativa />
      <span>
        O risco de queda é a chance de o parceiro estar em risco no próximo período, pela versão {risco.modelo_versao}, com dados até {comoPeriodo(risco.periodo_base)}.
        {risco.desatualizada && " Há período importado depois desse: o risco parte de dado antigo até o próximo treino."} <Link to="/ajuda#estimativa">O que é estimativa?</Link>
      </span>
    </p>
  );
}

