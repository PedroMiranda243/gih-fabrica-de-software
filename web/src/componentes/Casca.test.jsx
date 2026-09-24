import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { ContextoSessao } from "../api/contextoSessao";
import Casca from "./Casca";

function menu(usuario) {
  render(
    <ContextoSessao.Provider value={{ usuario, sair: () => {} }}>
      <MemoryRouter>
        <Casca titulo="Painel" />
      </MemoryRouter>
    </ContextoSessao.Provider>,
  );
  const trilho = screen.getByRole("navigation", { name: "Seções do sistema" });
  return within(trilho)
    .getAllByRole("link")
    .map((a) => a.textContent.trim());
}

describe("menu lateral", () => {
  it("o Administrador vê usuários e configuração, e não Parceiros, que a rota lhe recusa", () => {
    const itens = menu({
      nome: "Admin",
      perfil: "ADMINISTRADOR",
      telas: ["painel", "historico_importacoes", "usuarios", "configuracao"],
    });

    expect(itens).toEqual(["Painel", "Importação", "Usuários", "Configuração"]);
  });

  it("quem importa vê as três telas de sempre", () => {
    const itens = menu({
      nome: "Gestora",
      perfil: "GESTOR",
      telas: ["painel", "importar", "historico_importacoes", "parceiros"],
    });

    expect(itens).toEqual(["Painel", "Importação", "Parceiros"]);
  });

  it("sessão de antes da atualização, sem telas, mantém o menu anterior", () => {
    /* Uma aba aberta durante a atualização não pode ficar com o trilho vazio. */
    const itens = menu({ nome: "Antiga", perfil: "GESTOR" });

    expect(itens).toEqual(["Painel", "Importação", "Parceiros"]);
  });
});
