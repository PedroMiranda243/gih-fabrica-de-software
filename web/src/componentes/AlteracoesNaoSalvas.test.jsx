import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { Link, MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { describe, expect, it } from "vitest";

import AlteracoesNaoSalvas from "./AlteracoesNaoSalvas";

function Formulario() {
  const [nome, setNome] = useState("");
  const [salvo, setSalvo] = useState("");
  return (
    <>
      <nav aria-label="Seções">
        <Link to="/outra" state={{ de: "formulário" }}>
          Outra tela
        </Link>
        <Link to="/formulario?pagina=2">Mesma tela, outro filtro</Link>
        <a href="#campo-nome">Ir para o campo</a>
      </nav>
      <AlteracoesNaoSalvas quando={nome !== salvo} />
      <label htmlFor="campo-nome">Nome</label>
      <input id="campo-nome" value={nome} onChange={(e) => setNome(e.target.value)} />
      <button type="button" onClick={() => setSalvo(nome)}>
        Salvar
      </button>
    </>
  );
}

function Outra() {
  const { state } = useLocation();
  return <p>Outra tela aberta, vindo de: {state?.de ?? "lugar nenhum"}</p>;
}

function renderizar() {
  return render(
    <MemoryRouter initialEntries={["/formulario"]}>
      <Routes>
        <Route path="/formulario" element={<Formulario />} />
        <Route path="/outra" element={<Outra />} />
      </Routes>
    </MemoryRouter>,
  );
}

const pergunta = () => screen.queryByText(/Há alterações que não foram salvas/);

describe("aviso de alterações não salvas", () => {
  it("sem nada alterado, o link leva à outra tela sem perguntar", async () => {
    const usuario = userEvent.setup();
    renderizar();

    await usuario.click(screen.getByRole("link", { name: "Outra tela" }));

    expect(screen.getByText(/Outra tela aberta/)).toBeInTheDocument();
  });

  it("com o campo alterado, o link para na pergunta, e ela recebe o foco", async () => {
    const usuario = userEvent.setup();
    renderizar();

    await usuario.type(screen.getByLabelText("Nome"), "Ana");
    await usuario.click(screen.getByRole("link", { name: "Outra tela" }));

    expect(screen.queryByText(/Outra tela aberta/)).not.toBeInTheDocument();
    const aviso = screen.getByRole("alert");
    expect(aviso).toHaveTextContent("Há alterações que não foram salvas.");
    expect(aviso).toHaveFocus();
    // O que a pessoa digitou continua lá.
    expect(screen.getByLabelText("Nome")).toHaveValue("Ana");
  });

  it("'Continuar editando' fecha a pergunta e deixa a pessoa onde estava", async () => {
    const usuario = userEvent.setup();
    renderizar();

    await usuario.type(screen.getByLabelText("Nome"), "Ana");
    await usuario.click(screen.getByRole("link", { name: "Outra tela" }));
    await usuario.click(screen.getByRole("button", { name: "Continuar editando" }));

    expect(pergunta()).not.toBeInTheDocument();
    expect(screen.getByLabelText("Nome")).toHaveValue("Ana");
  });

  it("'Sair sem salvar' segue o link que foi clicado, com o que ele carregava", async () => {
    const usuario = userEvent.setup();
    renderizar();

    await usuario.type(screen.getByLabelText("Nome"), "Ana");
    await usuario.click(screen.getByRole("link", { name: "Outra tela" }));
    await usuario.click(screen.getByRole("button", { name: "Sair sem salvar" }));

    expect(screen.getByText("Outra tela aberta, vindo de: formulário")).toBeInTheDocument();
  });

  it("depois de salvar, o link volta a levar direto", async () => {
    const usuario = userEvent.setup();
    renderizar();

    await usuario.type(screen.getByLabelText("Nome"), "Ana");
    await usuario.click(screen.getByRole("button", { name: "Salvar" }));
    await usuario.click(screen.getByRole("link", { name: "Outra tela" }));

    expect(screen.getByText(/Outra tela aberta/)).toBeInTheDocument();
  });

  it("salvar com a pergunta na tela a retira, e ela não volta sozinha na próxima alteração", async () => {
    const usuario = userEvent.setup();
    renderizar();

    await usuario.type(screen.getByLabelText("Nome"), "Ana");
    await usuario.click(screen.getByRole("link", { name: "Outra tela" }));
    await usuario.click(screen.getByRole("button", { name: "Salvar" }));
    expect(pergunta()).not.toBeInTheDocument();

    await usuario.type(screen.getByLabelText("Nome"), " Lima");
    expect(pergunta()).not.toBeInTheDocument();
  });

  it("o que não sai da tela não pergunta: a âncora da página e o mesmo endereço com outro filtro", async () => {
    const usuario = userEvent.setup();
    renderizar();

    await usuario.type(screen.getByLabelText("Nome"), "Ana");
    await usuario.click(screen.getByRole("link", { name: "Ir para o campo" }));
    expect(pergunta()).not.toBeInTheDocument();

    await usuario.click(screen.getByRole("link", { name: "Mesma tela, outro filtro" }));
    expect(pergunta()).not.toBeInTheDocument();
    expect(screen.getByLabelText("Nome")).toHaveValue("Ana");
  });

  it("fechar a aba ou recarregar passa pelo aviso do navegador, só com algo alterado", async () => {
    const usuario = userEvent.setup();
    renderizar();
    const fechar = () => {
      const evento = new Event("beforeunload", { cancelable: true });
      window.dispatchEvent(evento);
      return evento.defaultPrevented;
    };

    expect(fechar()).toBe(false);

    await usuario.type(screen.getByLabelText("Nome"), "Ana");
    expect(fechar()).toBe(true);

    await usuario.click(screen.getByRole("button", { name: "Salvar" }));
    expect(fechar()).toBe(false);
  });
});
