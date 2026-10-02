import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import Campo from "./Campo";
import EntradaDeSenha from "./EntradaDeSenha";

function renderizar(erro) {
  return render(
    <Campo id="senha_nova" rotulo="Senha nova" obrigatorio erro={erro} ajuda="O servidor confere a força.">
      <EntradaDeSenha id="campo-senha_nova" de="a senha nova" defaultValue="segredo" />
    </Campo>,
  );
}

describe("campo de senha", () => {
  it("começa oculto, mostra o que foi digitado e volta a esconder", async () => {
    const usuario = userEvent.setup();
    renderizar();
    const campo = screen.getByLabelText(/^Senha nova/);

    expect(campo).toHaveAttribute("type", "password");

    await usuario.click(screen.getByRole("button", { name: "Mostrar a senha nova" }));
    expect(campo).toHaveAttribute("type", "text");
    expect(campo).toHaveValue("segredo");

    await usuario.click(screen.getByRole("button", { name: "Ocultar a senha nova" }));
    expect(campo).toHaveAttribute("type", "password");
  });

  it("o botão não envia o formulário", async () => {
    let enviados = 0;
    const usuario = userEvent.setup();
    render(
      <form
        aria-label="Entrada"
        onSubmit={(e) => {
          e.preventDefault();
          enviados += 1;
        }}
      >
        <label htmlFor="senha">Senha</label>
        <EntradaDeSenha id="senha" />
      </form>,
    );

    await usuario.click(screen.getByRole("button", { name: "Mostrar a senha" }));

    expect(enviados).toBe(0);
  });

  it("o erro e a ajuda do campo chegam ao controle, e não ao embrulho", () => {
    renderizar({ mensagem: "A senha precisa ter pelo menos 12 caracteres." });
    const campo = screen.getByLabelText(/^Senha nova/);

    expect(campo).toHaveAttribute("aria-invalid", "true");
    expect(campo).toHaveAccessibleDescription("A senha precisa ter pelo menos 12 caracteres.");
  });
});
