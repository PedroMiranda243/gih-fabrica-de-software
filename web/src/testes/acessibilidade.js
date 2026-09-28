import axe from "axe-core";

/**
 * Rótulos, papéis e nomes acessíveis, conferidos pelo axe-core — RNF22, história H76.
 *
 * Cada página roda com os dados do próprio teste e devolve a lista das
 * violações, uma por linha, com o elemento: vazia é o que passa, e a que não é
 * vazia diz onde olhar.
 *
 * **O que fica de fora aqui, e por quê:**
 * - o contraste: o jsdom não desenha, e o axe leria cores sem layout. Ele é
 *   medido do `tokens.css` (`estilos/contraste.test.js`) e no navegador de
 *   verdade (`scripts/medir_telas.py`);
 * - as regras da página inteira — o `main`, o título de nível 1, o conteúdo
 *   fora de região: a página renderizada sozinha não tem a casca, que as dá. A
 *   casca é conferida à parte, com uma página dentro (`App.acessibilidade.test.jsx`).
 */
const SEM_LAYOUT = { "color-contrast": { enabled: false } };
const DA_PAGINA_INTEIRA = {
  region: { enabled: false },
  "landmark-one-main": { enabled: false },
  "page-has-heading-one": { enabled: false },
  bypass: { enabled: false },
};

async function rodar(alvo, regras) {
  const resultado = await axe.run(alvo, { rules: regras, resultTypes: ["violations"] });
  return resultado.violations.map(
    (v) => `${v.id} (${v.impact}): ${v.nodes.map((n) => n.target.join(" ")).join(" | ")}`,
  );
}

/** As violações de uma página renderizada sem a casca. */
export function violacoes(alvo = document.body) {
  return rodar(alvo, { ...SEM_LAYOUT, ...DA_PAGINA_INTEIRA });
}

/** As violações da aplicação inteira, com a casca: aí as regras da página valem. */
export function violacoesDaAplicacao(alvo = document.body) {
  return rodar(alvo, SEM_LAYOUT);
}
