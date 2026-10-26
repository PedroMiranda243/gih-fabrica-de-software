/**
 * Auditoria — o que foi feito, por quem e quando. O rótulo e o resumo chegam
 * prontos do servidor: a tela não traduz código de ação nem lê os parâmetros.
 */
import { Fragment, useState } from "react";
import { useLocation } from "react-router-dom";

import { api, comConsulta } from "../api/cliente";
import { useCarregar, useFiltros } from "../api/ganchos";
import Busca from "../componentes/Busca";
import { Carregando, ErroDaTela, Vazio } from "../componentes/Estados";
import Icone from "../componentes/Icone";
import { CaixaDeTabela, Paginacao } from "../componentes/Lista";
import Seletor from "../componentes/Seletor";
import { useTitulo } from "../componentes/Titulo";
import { comoDataHora } from "../formato";

const TAMANHO = 50;
const CHAVES = ["busca", "acao", "autor", "de", "ate"];

export default function Auditoria() {
  useTitulo("Auditoria");
  const lugar = useLocation();
  const [filtros, mudar] = useFiltros();
  const pagina = Number(filtros.pagina) || 1;
  const consulta = Object.fromEntries(CHAVES.map((c) => [c, filtros[c]]));
  const acoes = useCarregar(() => api.get("/api/auditoria/acoes"), "acoes");
  const usuarios = useCarregar(() => api.get("/api/usuarios"), "usuarios");
  const trilha = useCarregar(() => api.get("/api/auditoria", { ...consulta, pagina, tamanho: TAMANHO }), lugar.search);
  const [aberto, setAberto] = useState(null);
  const d = trilha.dados;
  const filtrado = CHAVES.some((c) => filtros[c]);

  return (
    <div className="pagina">
      <div className="barra-acoes">
        <p className="barra-acoes__contexto">Operações registradas, da mais recente para a mais antiga.</p>
        <div className="barra-acoes__botoes">
          <a className="botao botao--secundario" href={comConsulta("/api/auditoria/exportacao.csv", consulta)} download>
            <Icone nome="baixar" /> Exportar CSV
          </a>
        </div>
      </div>
      <form className="filtros" aria-label="Filtros da trilha" onSubmit={(e) => e.preventDefault()}>
        <div className="campo filtros__busca">
          <label className="campo__rotulo" htmlFor="t-busca">
            Buscar na trilha
          </label>
          <Busca id="t-busca" valor={filtros.busca} aoMudar={(v) => mudar({ busca: v })} placeholder="Um nome de parceiro, um login" />
        </div>
        <Seletor id="t-acao" rotulo="Ação" valor={filtros.acao} aoMudar={(v) => mudar({ acao: v })} todos="Todas as ações" opcoes={(acoes.dados ?? []).map((a) => [a.acao, a.rotulo])} />
        <Seletor id="t-autor" rotulo="Quem fez" valor={filtros.autor} aoMudar={(v) => mudar({ autor: v })} todos="Todas as pessoas" opcoes={(usuarios.dados ?? []).map((u) => [u.id, `${u.nome} (${u.login})`])} />
        <div className="campo">
          <label className="campo__rotulo" htmlFor="t-de">
            De
          </label>
          <input id="t-de" type="date" className="entrada" value={filtros.de ?? ""} onChange={(e) => mudar({ de: e.target.value })} />
        </div>
        <div className="campo">
          <label className="campo__rotulo" htmlFor="t-ate">
            Até
          </label>
          <input id="t-ate" type="date" className="entrada" value={filtros.ate ?? ""} onChange={(e) => mudar({ ate: e.target.value })} />
        </div>
        {filtrado && (
          <button type="button" className="botao botao--fantasma filtros__limpar" onClick={() => mudar(Object.fromEntries(CHAVES.map((c) => [c, null])))}>
            <Icone nome="fechar" /> Limpar filtros
          </button>
        )}
      </form>
      <section className="bloco bloco--tabela" aria-labelledby="t-registros" aria-busy={trilha.carregando}>
        <h2 id="t-registros" className="sr-only">
          Registros da trilha
        </h2>
        {trilha.carregando && !d && <Carregando rotulo="Carregando a trilha" linhas={10} />}
        <ErroDaTela erro={trilha.erro} />
        {d && !d.itens.length && filtrado && (
          <Vazio titulo="Nenhum registro nesse recorte" icone="busca">
            Não houve operação com esses filtros. Amplie as datas ou limpe a busca.
          </Vazio>
        )}
        {d && !d.itens.length && !filtrado && (
          <Vazio titulo="A trilha ainda está vazia" icone="auditoria">
            Cada entrada, importação, cálculo e decisão passa a aparecer aqui.
          </Vazio>
        )}
        {d && d.itens.length > 0 && (
          <>
            <CaixaDeTabela rotulo="Trilha de auditoria">
              <table className={`tabela tabela--auditoria${trilha.carregando ? " tabela--recarregando" : ""}`}>
                <caption className="sr-only">Operações registradas, da mais recente para a mais antiga</caption>
                <thead>
                  <tr>
                    <th scope="col">Quando</th>
                    <th scope="col">Quem fez</th>
                    <th scope="col">Ação</th>
                    <th scope="col">O que aconteceu</th>
                    <th scope="col">Origem</th>
                    <th scope="col">
                      <span className="sr-only">Detalhes</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {d.itens.map((r) => (
                    <Fragment key={r.id}>
                      <tr>
                        <th scope="row" className="quando">
                          {comoDataHora(r.ocorrido_em)}
                        </th>
                        <td>{r.autor ? <>{r.autor} <span className="discreto">({r.autor_login})</span></> : <span className="discreto">sem usuário</span>}</td>
                        <td>
                          <span className="rotulo-acao">{r.rotulo}</span>
                        </td>
                        <td className="resumo">{r.resumo || <span className="discreto">—</span>}</td>
                        <td>{r.origem ? <code>{r.origem}</code> : <span className="discreto">—</span>}</td>
                        <td>
                          <button type="button" className="botao botao--fantasma botao--pequeno" aria-expanded={aberto === r.id} aria-controls={`detalhe-${r.id}`} onClick={() => setAberto((a) => (a === r.id ? null : r.id))}>
                            O que foi gravado
                          </button>
                        </td>
                      </tr>
                      {aberto === r.id && (
                        <tr className="linha--detalhe" id={`detalhe-${r.id}`}>
                          <td colSpan={6}>
                            <pre className="gravado">{r.detalhes ? JSON.stringify(r.detalhes, null, 2) : "Nada além do resumo foi gravado neste registro."}</pre>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  ))}
                </tbody>
              </table>
            </CaixaDeTabela>
            <Paginacao pagina={pagina} tamanho={TAMANHO} total={d.total} aoMudar={(p) => mudar({ pagina: p > 1 ? p : null }, { manterPagina: true })} rotulo="registros" />
          </>
        )}
      </section>
    </div>
  );
}
