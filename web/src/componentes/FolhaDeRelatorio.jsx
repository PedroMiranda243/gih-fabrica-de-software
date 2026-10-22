/**
 * A moldura comum dos relatórios — o que se leva para fora do sistema: trilha,
 * filtros, o recorte escrito na própria folha (a partir do que a API devolveu),
 * Exportar CSV e Imprimir ou salvar em PDF. Na impressão sai uma linha que a tela
 * não tem: quando foi emitido e por quem.
 */
import { tem, useSessao } from "../api/sessao";
import { comoDataHora } from "../formato";
import Icone from "./Icone";
import { Trilha } from "./Lista";

export default function FolhaDeRelatorio({ nome, filtros, recorte, csv, children, notaDaImpressao }) {
  const { usuario } = useSessao();
  return (
    <div className="pagina pagina--relatorio">
      <div className="barra-acoes nao-imprime">
        <Trilha passos={[{ rotulo: "Relatórios", para: tem(usuario, "relatorios") ? "/relatorios" : undefined }, { rotulo: nome }]} />
        <div className="barra-acoes__botoes">
          {csv && (
            <a className="botao botao--secundario" href={csv} download>
              <Icone nome="baixar" /> Exportar CSV
            </a>
          )}
          <button type="button" className="botao botao--secundario" onClick={() => window.print()}>
            <Icone nome="imprimir" /> Imprimir ou salvar em PDF
          </button>
        </div>
      </div>
      {filtros && (
        <form className="filtros nao-imprime" aria-label={`Filtros do relatório ${nome}`} onSubmit={(e) => e.preventDefault()}>
          {filtros}
        </form>
      )}
      <article className="folha" aria-labelledby="folha-titulo">
        <header className="folha__cabeca">
          <p className="so-impressao folha__marca">GIH — Growth Intelligence Hub</p>
          <h2 id="folha-titulo" className="folha__titulo">
            {nome}
          </h2>
          {recorte && <p className="folha__recorte">{recorte}</p>}
          <p className="so-impressao folha__emitido">
            Emitido em {comoDataHora(new Date().toISOString())} por {usuario?.nome}.
          </p>
          {notaDaImpressao && <p className="so-impressao folha__emitido">{notaDaImpressao}</p>}
        </header>
        {children}
      </article>
    </div>
  );
}
