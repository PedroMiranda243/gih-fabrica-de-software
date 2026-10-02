import { afterEach, describe, expect, it } from "vitest";

import { imprimirNoTemaClaro } from "./impressao";

describe("a folha sai no tema claro (H88)", () => {
  const raiz = document.documentElement;
  let desligar;

  afterEach(() => {
    desligar?.();
    raiz.removeAttribute("data-tema");
  });

  const disparar = (evento) => window.dispatchEvent(new Event(evento));

  it("quem escolheu o escuro imprime no claro, e volta ao escuro depois", () => {
    raiz.setAttribute("data-tema", "escuro");
    desligar = imprimirNoTemaClaro();

    disparar("beforeprint");
    expect(raiz).toHaveAttribute("data-tema", "claro");

    disparar("afterprint");
    expect(raiz).toHaveAttribute("data-tema", "escuro");
  });

  it("quem segue o sistema volta a segui-lo: o atributo sai, em vez de ficar no claro", () => {
    /* Sem escolha explícita não há atributo, e é o `@media` que manda. Deixar
       "claro" depois de imprimir prenderia no claro quem usa o sistema no escuro. */
    desligar = imprimirNoTemaClaro();

    disparar("beforeprint");
    expect(raiz).toHaveAttribute("data-tema", "claro");

    disparar("afterprint");
    expect(raiz).not.toHaveAttribute("data-tema");
  });

  it("um `afterprint` sem impressão antes não mexe no tema", () => {
    raiz.setAttribute("data-tema", "escuro");
    desligar = imprimirNoTemaClaro();

    disparar("afterprint");

    expect(raiz).toHaveAttribute("data-tema", "escuro");
  });
});
