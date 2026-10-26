import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";

import { abrir, amostra } from "../testes/montar";

const menuDe = async () => {
  const menu = await screen.findByRole("navigation", { name: "Menu principal" });
  return Object.fromEntries(
    [...menu.querySelectorAll(".menu__grupo")].map((g) => [g.querySelector(".menu__nome").textContent, [...g.querySelectorAll(".menu__rotulo")].map((r) => r.textContent)]),
  );
};

/*
 * A casca: o menu é um mapa de rotas, montado de `usuario.telas` (RF05, H94); o
 * cabeçalho diz a área e o caminho de volta; o tema escolhido vale nas duas cores.
 */
describe("a casca", () => {
  afterEach(() => {
    delete document.documentElement.dataset.tema;
    try {
      window.localStorage.removeItem("gih-tema");
    } catch {
      /* sem armazenamento, o tema volta a seguir o sistema */
    }
  });

  it("o Gestor vê da Análise à Comunicação, e não a Administração", async () => {
    abrir("/conta", { perfil: "GESTOR" });

    expect(await menuDe()).toEqual({
      Análise: ["Painel", "Importação", "Parceiros", "Assistente", "Relatórios"],
      Previsão: ["Modelo"],
      Otimização: ["Campanha", "Execuções", "Benchmark"],
      Comunicação: ["Mensagens", "Aprovação"],
    });
  });

  it("o Analista não vê o Modelo nem o Benchmark, e não vê Auditoria", async () => {
    abrir("/conta", { perfil: "ANALISTA" });

    const menu = await menuDe();
    expect(menu["Previsão"]).toBeUndefined();
    expect(menu["Otimização"]).toEqual(["Campanha", "Execuções"]);
    expect(menu["Administração"]).toBeUndefined();
  });

  it("o Administrador vê a Administração e o histórico, mas não a lista de parceiros nem a campanha", async () => {
    abrir("/conta", { perfil: "ADMINISTRADOR" });

    const menu = await menuDe();
    expect(menu["Administração"]).toEqual(["Usuários", "Auditoria", "Operações", "Configuração"]);
    expect(menu["Análise"]).toEqual(["Painel", "Importação"]);
    expect(menu["Otimização"]).toEqual(["Execuções", "Benchmark"]);
  });

  it("cada item diz o que há lá dentro", async () => {
    abrir("/conta", { perfil: "GESTOR" });

    const menu = await screen.findByRole("navigation", { name: "Menu principal" });
    expect(within(menu).getByRole("link", { name: /Campanha/ })).toHaveTextContent("Calcular o plano com a verba");
  });

  it("o cabeçalho diz em que área a pessoa está, pelo nome, e não só pela cor", async () => {
    abrir("/parceiros", {
      perfil: "GESTOR",
      rotas: { "GET /api/parceiros": { corpo: amostra("GET_api_parceiros") }, "GET /api/categorias": { corpo: amostra("GET_api_categorias") } },
    });

    const onde = await screen.findByRole("navigation", { name: "Onde você está" });
    expect(onde).toHaveTextContent("Análise");
    expect(document.querySelector(".casca").dataset.rota).toBe("analise");
  });

  it("quem está dentro aparece no cabeçalho, com o perfil por extenso, e leva a Minha conta", async () => {
    abrir("/ajuda", { perfil: "GESTOR", rotas: { "GET /api/ajuda/regras": { corpo: amostra("GET_api_ajuda_regras") } } });

    expect(await screen.findByRole("link", { name: "Minha conta: Gestora do Laboratório Gestor" })).toHaveAttribute("href", "/conta");
  });

  it("o nome do link da conta contém o que está escrito nele, para quem usa comando de voz (WCAG 2.5.3)", async () => {
    abrir("/conta", { perfil: "GESTOR" });

    const link = await screen.findByRole("link", { name: /^Minha conta: / });
    const visivel = [...link.querySelectorAll(".quem__nome, .quem__perfil")].map((e) => e.textContent).join(" ");
    expect(link).not.toHaveAttribute("aria-label");
    expect(link).toHaveAccessibleName(expect.stringContaining(visivel));
  });

  it("o tema troca pelo botão do cabeçalho, que diz o que vai fazer", async () => {
    const usuario = userEvent.setup();
    abrir("/conta", { perfil: "GESTOR" });

    await usuario.click(await screen.findByRole("button", { name: "Mudar para o modo escuro" }));
    expect(document.documentElement.dataset.tema).toBe("escuro");
    expect(screen.getByRole("button", { name: "Mudar para o modo claro" })).toBeInTheDocument();
  });
});
