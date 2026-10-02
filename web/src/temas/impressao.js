/**
 * A folha sai no tema claro, qualquer que seja o tema da tela (RF48 · H88).
 *
 * O tema escuro é para a tela. No papel — e no PDF, que é a impressão —, fundo
 * escuro gasta tinta e o texto claro some. Trocar para o claro só durante a
 * impressão resolve sem repetir os tokens numa segunda folha de estilo: a
 * paleta clara continua tendo uma fonte só, o `tokens.css`, e o teste de
 * contraste continua medindo tudo o que se imprime.
 *
 * Nos eventos do navegador, e não no botão: quem imprime pelo atalho do teclado
 * ou pelo menu passa por aqui do mesmo jeito.
 */
const ATRIBUTO = "data-tema";

export function imprimirNoTemaClaro(janela = window) {
  const raiz = janela.document.documentElement;
  /* `undefined` é "nada guardado"; `null` é "não havia escolha explícita", e
     precisa ser devolvido como ausência do atributo, para o sistema voltar a
     mandar no tema. */
  let antes;

  const clarear = () => {
    antes = raiz.getAttribute(ATRIBUTO);
    raiz.setAttribute(ATRIBUTO, "claro");
  };
  const devolver = () => {
    if (antes === undefined) return;
    if (antes === null) raiz.removeAttribute(ATRIBUTO);
    else raiz.setAttribute(ATRIBUTO, antes);
    antes = undefined;
  };

  janela.addEventListener("beforeprint", clarear);
  janela.addEventListener("afterprint", devolver);
  return () => {
    janela.removeEventListener("beforeprint", clarear);
    janela.removeEventListener("afterprint", devolver);
  };
}
