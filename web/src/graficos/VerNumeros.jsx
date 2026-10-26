/**
 * Todo gráfico tem a tabela dos números a um clique: é a alternativa acessível,
 * e um estado honesto do mesmo dado — "Ver os números" / "Ocultar os números".
 */
import { useId, useState } from "react";

import Icone from "../componentes/Icone";
import { CaixaDeTabela } from "../componentes/Lista";

export default function VerNumeros({ legenda, colunas, linhas, children }) {
  const [aberto, setAberto] = useState(false);
  const id = useId();
  return (
    <div className="ver-numeros">
      {children}
      <button type="button" className="botao botao--fantasma botao--pequeno ver-numeros__botao" aria-expanded={aberto} aria-controls={id} onClick={() => setAberto((a) => !a)}>
        <Icone nome={aberto ? "fechar" : "relatorios"} />
        {aberto ? "Ocultar os números" : "Ver os números"}
      </button>
      <div id={id} hidden={!aberto}>
        {aberto && (
          <CaixaDeTabela rotulo={legenda}>
            <table className="tabela tabela--compacta">
              <caption>{legenda}</caption>
              <thead>
                <tr>
                  {colunas.map((c, i) => (
                    <th key={c.rotulo} scope="col" className={i > 0 && c.num !== false ? "num" : undefined}>
                      {c.rotulo}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {linhas.map((linha, i) => (
                  <tr key={i}>
                    {linha.map((celula, j) =>
                      j === 0 ? (
                        <th key={j} scope="row">
                          {celula}
                        </th>
                      ) : (
                        <td key={j} className={colunas[j].num !== false ? "num" : undefined}>
                          {celula}
                        </td>
                      ),
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </CaixaDeTabela>
        )}
      </div>
    </div>
  );
}
