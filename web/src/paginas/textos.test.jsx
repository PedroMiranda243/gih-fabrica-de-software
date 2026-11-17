/**
 * Os textos dos estados vazios num padrão só (#284): cada tela tinha escrito o seu.
 * O título de vazio não leva ponto — nem o motivo da API, que é frase e vira título;
 * o recorte filtrado é "nesse recorte"; e o atalho para a Campanha diz o nome da tela
 * como o menu o escreve.
 */
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { Vazio } from "../componentes/Estados";

// O vitest roda de web/, aqui e na CI.
const PAGINAS = join(process.cwd(), "src", "paginas");
const telas = () =>
  readdirSync(PAGINAS)
    .filter((n) => n.endsWith(".jsx") && !n.includes(".test."))
    .map((n) => [n, readFileSync(join(PAGINAS, n), "utf8")]);

describe("os textos dos estados vazios", () => {
  it("o título do vazio sai sem ponto, inclusive o motivo que vem da API", () => {
    render(
      <MemoryRouter>
        <Vazio titulo="Nenhum parceiro deste recorte tem previsão." />
      </MemoryRouter>,
    );
    expect(screen.getByText("Nenhum parceiro deste recorte tem previsão")).toBeInTheDocument();
  });

  it("nenhuma tela escreve título de vazio com ponto, \"neste recorte\" ou \"Ir para a campanha\"", () => {
    const achados = [];
    for (const [nome, jsx] of telas()) {
      for (const [, titulo] of jsx.matchAll(/<Vazio\b[^>]*?titulo=(?:"([^"]*)"|\{[^}]*?"([^"]*)"\s*\})/g)) {
        if (titulo?.endsWith(".")) achados.push(`${nome}: título com ponto — ${titulo}`);
      }
      for (const [linha] of jsx.matchAll(/.*(neste recorte|Ir para a campanha).*/g)) achados.push(`${nome}: ${linha.trim()}`);
    }
    expect(achados).toEqual([]);
  });
});
