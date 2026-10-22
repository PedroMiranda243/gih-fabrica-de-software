/**
 * Peças das listas: trilha, paginação, cabeçalho ordenável e a caixa que deixa a
 * tabela larga rolar dentro dela (a página nunca rola na horizontal).
 */
import { comoInteiro } from "../formato";
import Icone from "./Icone";
import { useTrilha } from "./Titulo";

/** A trilha de volta: os passos vão para o cabeçalho, que fica sempre à vista. */
export function Trilha({ passos }) {
  useTrilha(passos);
  return null;
}

export function Paginacao({ pagina, tamanho, total, aoMudar, rotulo = "itens" }) {
  const paginas = Math.max(1, Math.ceil(total / tamanho));
  if (total <= tamanho && pagina === 1) return null;
  const de = total === 0 ? 0 : (pagina - 1) * tamanho + 1;
  const ate = Math.min(pagina * tamanho, total);
  return (
    <nav className="paginacao" aria-label="Paginação">
      <p className="paginacao__onde">
        {comoInteiro(de)}–{comoInteiro(ate)} de {comoInteiro(total)} {rotulo} · página {pagina} de {paginas}
      </p>
      <div className="paginacao__botoes">
        <button type="button" className="botao botao--secundario botao--pequeno" disabled={pagina <= 1} onClick={() => aoMudar(pagina - 1)}>
          <Icone nome="seta-esquerda" /> Anterior
        </button>
        <button type="button" className="botao botao--secundario botao--pequeno" disabled={pagina >= paginas} onClick={() => aoMudar(pagina + 1)}>
          Próxima <Icone nome="seta-direita" />
        </button>
      </div>
    </nav>
  );
}

/** Cabeçalho que ordena: número ordena do maior para o menor no primeiro clique. */
export function ColunaOrdenavel({ chave, rotulo, ordem, descendente, aoOrdenar, numerica = false, className = "" }) {
  const ativa = ordem === chave;
  const sort = ativa ? (descendente ? "descending" : "ascending") : "none";
  function clicar() {
    if (ativa) aoOrdenar(chave, !descendente);
    else aoOrdenar(chave, numerica);
  }
  return (
    <th scope="col" aria-sort={sort} className={`${numerica ? "num " : ""}${className}`}>
      <button type="button" className={`ordenar${ativa ? " ordenar--ativa" : ""}`} onClick={clicar}>
        <span>{rotulo}</span>
        <Icone nome={ativa ? (descendente ? "ordem-desc" : "ordem-asc") : "ordem"} className="ordenar__icone" />
        <span className="sr-only">{ativa ? (descendente ? ", do maior para o menor" : ", do menor para o maior") : ", clique para ordenar"}</span>
      </button>
    </th>
  );
}

/** A tabela larga rola aqui dentro; a caixa é alcançável pelo teclado e tem nome. */
export function CaixaDeTabela({ rotulo, children, className = "" }) {
  return (
    <div className={`caixa-tabela ${className}`} role="region" aria-label={rotulo} tabIndex={0}>
      {children}
    </div>
  );
}
