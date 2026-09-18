/**
 * Alternância entre claro e escuro.
 *
 * São **três** estados, não dois: claro explícito, escuro explícito, e "o que o
 * sistema mandar" — que é o que a maioria das pessoas tem. O padrão é o
 * terceiro; a escolha explícita só existe depois que alguém clica, e aí ela
 * vence a preferência do sistema operacional (ver `tokens.css`).
 *
 * O `docs/09` define as duas paletas, as duas validadas contra daltonismo.
 * Entregar só a clara descartaria metade de um trabalho que já foi feito.
 */
import { useCallback, useEffect, useState } from "react";

const CHAVE = "gih:tema";

function lerPreferencia() {
  /* `localStorage` pode lançar em janela anônima ou com dados de site
     bloqueados. Falhar aqui derrubaria a aplicação inteira por causa de uma
     preferência visual. */
  try {
    const guardado = localStorage.getItem(CHAVE);
    if (guardado === "claro" || guardado === "escuro") return guardado;
  } catch {
    /* segue com o padrão do sistema */
  }
  return null;
}

function doSistema() {
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "escuro" : "claro";
}

export function useTema() {
  const [escolhido, setEscolhido] = useState(lerPreferencia);
  const tema = escolhido ?? doSistema();

  useEffect(() => {
    const raiz = document.documentElement;
    if (escolhido) {
      raiz.setAttribute("data-tema", escolhido);
    } else {
      /* Sem escolha explícita, o atributo sai e o `@media` volta a mandar. */
      raiz.removeAttribute("data-tema");
    }
  }, [escolhido]);

  const alternar = useCallback(() => {
    setEscolhido((atual) => {
      const proximo = (atual ?? doSistema()) === "escuro" ? "claro" : "escuro";
      try {
        localStorage.setItem(CHAVE, proximo);
      } catch {
        /* Sem persistência a escolha vale só nesta aba, o que é melhor que
           quebrar. */
      }
      return proximo;
    });
  }, []);

  return { tema, alternar };
}
