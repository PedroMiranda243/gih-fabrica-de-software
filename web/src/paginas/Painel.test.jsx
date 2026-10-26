import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { abrir, amostra, rotasDoPainel } from "../testes/montar";

const secao = (titulo) => screen.getByRole("heading", { name: titulo }).closest("section");

/* RF17 (indicadores), RF18 (ranking) e RF22 (mobilidade do Top) — o painel. */
describe("o painel", () => {
  it("mostra os indicadores do período, com a variação sinalizada (RF17)", async () => {
    abrir("/", { rotas: rotasDoPainel() });

    expect(await screen.findByRole("heading", { level: 1, name: "Painel" })).toBeInTheDocument();
    const indicadores = await waitFor(() => {
      const s = document.querySelector('[aria-labelledby="titulo-indicadores"]');
      expect(s).toHaveTextContent("1.839.707");
      return s;
    });
    expect(indicadores).toHaveTextContent("41.974");
    expect(indicadores).toHaveTextContent("−0,12%");
    expect(indicadores).toHaveTextContent("+2,25%");
  });

  it("o recorte por categoria vai para a API, e a API devolve o recorte (RF17)", async () => {
    const usuario = userEvent.setup();
    const { chamadas } = abrir("/", { rotas: rotasDoPainel() });

    const categoria = await screen.findByLabelText("Categoria");
    const primeira = amostra("GET_api_painel_recortes").categorias[0];
    await usuario.selectOptions(categoria, String(primeira.id));

    await waitFor(() => expect(chamadas().some((c) => c.startsWith("GET /api/painel/indicadores") && c.includes(`categoria_id=${primeira.id}`))).toBe(true));
    expect(chamadas().some((c) => c.startsWith("GET /api/painel/ranking") && c.includes(`categoria_id=${primeira.id}`))).toBe(true);
  });

  it("o ranking traz a posição, a anterior e a variação de cada parceiro (RF18)", async () => {
    abrir("/", { rotas: rotasDoPainel() });

    await screen.findByText("Ponto Azul 2");
    const ranking = secao("Ranking de parceiros");
    const linha = within(ranking).getByText("Ponto Azul 2").closest("tr");
    expect(linha).toHaveTextContent("79.410,29");
    expect(linha).toHaveTextContent("−15,06%");
    expect(within(ranking).getByRole("region", { name: "Tabela: Ranking de parceiros" })).toBeInTheDocument();
  });

  it("a mobilidade do Top diz o tamanho do Top que a API mandou, e quem entrou e saiu (RF22)", async () => {
    abrir("/", { rotas: rotasDoPainel() });

    expect(await screen.findByText(/Mobilidade Top 15/)).toBeInTheDocument();
    expect(screen.getByText(/Parada Real/)).toBeInTheDocument();
    expect(screen.getByText(/Quintal do Sol 3/)).toBeInTheDocument();
  });

  it("com o Top configurado em 10, a tela diz 10 — o número nunca está escrito no código (#229)", async () => {
    const rotas = rotasDoPainel();
    rotas["GET /api/painel/mobilidade"].corpo.top_n = 10;
    abrir("/", { rotas });

    expect(await screen.findByText(/Mobilidade Top 10/)).toBeInTheDocument();
    expect(screen.queryByText(/Top 15/)).not.toBeInTheDocument();
  });

  it("a previsão aparece marcada como estimativa, separada do que foi medido", async () => {
    abrir("/", { rotas: rotasDoPainel() });

    await screen.findByText("Ponto Azul 2");
    expect((await screen.findAllByText("Estimativa")).length).toBeGreaterThan(0);
  });

  it("cada segmento da distribuição leva à lista filtrada, e o nome do link é o que se lê nele (WCAG 2.5.3)", async () => {
    abrir("/", { rotas: rotasDoPainel() });

    const links = await screen.findAllByRole("link", { name: /parceiros — ver na lista$/ });
    expect(links.length).toBeGreaterThan(0);
    for (const link of links) {
      const visivel = `${link.querySelector(".segmento").textContent.trim()} ${link.querySelector(".distribuicao__total").textContent}`;
      expect(link).not.toHaveAttribute("aria-label");
      expect(link).toHaveAccessibleName(expect.stringContaining(visivel));
      expect(link.getAttribute("href")).toMatch(/^\/parceiros\?segmento=/);
    }
  });

  it("base vazia explica por quê e oferece o primeiro passo a quem importa", async () => {
    const rotas = rotasDoPainel();
    rotas["GET /api/painel/recortes"] = { corpo: { periodos: [], categorias: [] } };
    abrir("/", { rotas });

    expect(await screen.findByText("Nenhum dado importado ainda")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Importar um relatório" })).toHaveAttribute("href", "/importacao");
  });

  it("variação nula é 'sem base de comparação', e não zero", async () => {
    const rotas = rotasDoPainel();
    const ranking = rotas["GET /api/painel/ranking"].corpo;
    ranking.itens[0].variacao_percentual = null;
    abrir("/", { rotas });

    const linha = (await screen.findByText("Ponto Azul 2")).closest("tr");
    expect(linha).toHaveTextContent("—");
    expect(linha).not.toHaveTextContent("0,00%");
  });
});
