import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { violacoes } from "./acessibilidade";

/* O instrumento antes da medição (`CLAUDE.md` §7): uma verificação que não acha
   nada precisa provar que acharia. Sem isto, "zero violações" nas páginas
   poderia ser o axe rodando sobre nada. */
describe("a verificação de acessibilidade", () => {
  it("acha o botão sem nome, o campo sem rótulo e a imagem sem texto", async () => {
    const { container, unmount } = render(
      <div>
        <button type="button">
          <svg aria-hidden="true" />
        </button>
        <input type="text" />
        <img src="grafico.png" />
      </div>,
    );

    const achadas = (await violacoes(container)).map((v) => v.split(" ")[0]);
    expect(achadas).toEqual(expect.arrayContaining(["button-name", "label", "image-alt"]));
    // Os erros daqui são de propósito: a conferência de todo teste não os vê.
    unmount();
  });

  it("não acusa o que está certo", async () => {
    const { container } = render(
      <div>
        <button type="button" aria-label="Fechar">
          <svg aria-hidden="true" />
        </button>
        <label htmlFor="campo">Nome</label>
        <input id="campo" type="text" />
      </div>,
    );

    expect(await violacoes(container)).toEqual([]);
  });
});
