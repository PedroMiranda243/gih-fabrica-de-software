import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Link, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { avisariaAoFechar } from "../testes/preparar";
import AlteracoesNaoSalvas from "./AlteracoesNaoSalvas";

function Tela({ alterado }) {
  return (
    <MemoryRouter initialEntries={["/parceiros/1"]}>
      <Routes>
        <Route
          path="/parceiros/1"
          element={
            <main>
              <h1>Cadastro</h1>
              <Link to="/parceiros">Voltar para a lista</Link>
              <a href="#contato">Ir para o contato</a>
              <Link to="/parceiros/1?aba=historico">Ver o histórico</Link>
              <AlteracoesNaoSalvas quando={alterado} />
            </main>
          }
        />
        <Route path="/parceiros" element={<h1>Lista de parceiros</h1>} />
      </Routes>
    </MemoryRouter>
  );
}

/* H97 — sair com alteração não salva para numa pergunta, e só quando há o que perder. */
describe("as alterações não salvas", () => {
  it("sem nada alterado, nada pergunta", async () => {
    const usuario = userEvent.setup();
    render(<Tela alterado={false} />);

    expect(avisariaAoFechar()).toBe(false);
    await usuario.click(screen.getByRole("link", { name: "Voltar para a lista" }));
    expect(screen.getByRole("heading", { name: "Lista de parceiros" })).toBeInTheDocument();
  });

  it("com alteração, o link para outra tela pergunta antes; 'Continuar editando' fica", async () => {
    const usuario = userEvent.setup();
    render(<Tela alterado />);

    await usuario.click(screen.getByRole("link", { name: "Voltar para a lista" }));
    expect(screen.getByText(/Há alterações que não foram salvas/)).toBeInTheDocument();
    await usuario.click(screen.getByRole("button", { name: "Continuar editando" }));
    expect(screen.getByRole("heading", { name: "Cadastro" })).toBeInTheDocument();
    expect(screen.queryByText(/Há alterações que não foram salvas/)).not.toBeInTheDocument();
  });

  it("'Sair sem salvar' segue para onde a pessoa ia", async () => {
    const usuario = userEvent.setup();
    render(<Tela alterado />);

    await usuario.click(screen.getByRole("link", { name: "Voltar para a lista" }));
    await usuario.click(screen.getByRole("button", { name: "Sair sem salvar" }));
    expect(screen.getByRole("heading", { name: "Lista de parceiros" })).toBeInTheDocument();
  });

  it("fechar a aba ou recarregar passa pelo aviso do navegador", () => {
    render(<Tela alterado />);
    expect(avisariaAoFechar()).toBe(true);
  });

  it("âncora e mudança só de filtro, na mesma tela, não perguntam", async () => {
    const usuario = userEvent.setup();
    render(<Tela alterado />);

    await usuario.click(screen.getByRole("link", { name: "Ir para o contato" }));
    await usuario.click(screen.getByRole("link", { name: "Ver o histórico" }));
    expect(screen.queryByText(/Há alterações que não foram salvas/)).not.toBeInTheDocument();
  });
});
