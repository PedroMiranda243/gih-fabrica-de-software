/**
 * RNF12 na tela — história H70: todo texto que veio do usuário, ou da API, chega
 * ao navegador escapado.
 *
 * **Quem escapa é o React**, em toda expressão `{...}` do JSX. O vetor está nas
 * formas de pular esse escape: HTML injetado por propriedade, `innerHTML`,
 * `eval`, link `javascript:`. O primeiro teste lê o código de `src/` e recusa
 * todas elas — tela nova entra nele sem ninguém lembrar dela, e é o que reprova
 * o PR que abrir o vetor. Os outros renderizam telas de verdade com carga de
 * script nos nomes, e conferem que ela aparece como texto e não vira elemento.
 *
 * O texto do assistente (H65) vai passar pelo mesmo caminho quando existir: a
 * varredura já o cobre.
 */
import { readdirSync, readFileSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import PlanoDeCampanha from "./componentes/PlanoDeCampanha";
import TabelaRanking from "./componentes/TabelaRanking";

const RAIZ = dirname(fileURLToPath(import.meta.url));

/* As formas de pôr HTML ou código na página sem passar pelo escape do React. As
   palavras são montadas por partes para este arquivo não se acusar. */
const PROIBIDAS = [
  ["dangerously" + "SetInnerHTML", "HTML injetado por propriedade"],
  [".inner" + "HTML", "HTML atribuído direto ao elemento"],
  [".outer" + "HTML", "HTML atribuído direto ao elemento"],
  ["insertAdjacent" + "HTML", "HTML inserido direto no documento"],
  ["document." + "write", "HTML escrito direto no documento"],
  ["ev" + "al(", "texto executado como código"],
  ["new Fun" + "ction(", "texto executado como código"],
  ["java" + "script:", "link que executa código"],
];

function codigoDaTela(pasta) {
  return readdirSync(pasta, { recursive: true, withFileTypes: true })
    .filter((e) => e.isFile() && /\.(jsx?|tsx?)$/.test(e.name) && !/\.test\./.test(e.name))
    .map((e) => join(e.parentPath ?? e.path, e.name));
}

const CARGAS = ["<script>alert('gih')</script>", '"><img src=x onerror=alert(1)>', "<svg onload=alert(1)>"];

/* Nenhum elemento veio da carga: nem `<script>`, nem `<img>`, nem atributo de evento. */
function semElementoInjetado(container) {
  expect(container.querySelector("script, img")).toBeNull();
  const comEvento = [...container.querySelectorAll("*")].filter((el) =>
    [...el.attributes].some((a) => a.name.startsWith("on")),
  );
  expect(comEvento).toEqual([]);
}

describe("RNF12 — a saída chega escapada ao navegador", () => {
  it("nenhum código da tela pula o escape do React", () => {
    const achados = [];
    for (const arquivo of codigoDaTela(RAIZ)) {
      const texto = readFileSync(arquivo, "utf8");
      for (const [palavra, porque] of PROIBIDAS) {
        if (texto.includes(palavra)) achados.push(`${relative(RAIZ, arquivo)}: ${porque} (${palavra})`);
      }
    }
    expect(achados).toEqual([]);
  });

  it.each(CARGAS)("o ranking mostra a carga como texto: %s", (carga) => {
    const { container } = render(
      <MemoryRouter>
        <TabelaRanking
          itens={[
            {
              parceiro_id: 1,
              nome: carga,
              categoria: carga,
              posicao: 1,
              posicao_anterior: null,
              faturamento: "2000.00",
              pedidos: 20,
              ticket_medio: "100.00",
              variacao_percentual: null,
              estreante: true,
            },
          ]}
        />
      </MemoryRouter>,
    );
    // O nome e a categoria: a carga aparece nos dois como texto, letra por letra.
    expect(screen.getAllByText(carga)).toHaveLength(2);
    semElementoInjetado(container);
  });

  it.each(CARGAS)("o motivo de uma falha, vindo da API, aparece como texto: %s", (carga) => {
    const { container } = render(
      <MemoryRouter>
        <PlanoDeCampanha execucao={{ situacao: "FALHOU", motivo: carga }} />
      </MemoryRouter>,
    );
    expect(screen.getByText(carga)).toBeInTheDocument();
    semElementoInjetado(container);
  });
});
