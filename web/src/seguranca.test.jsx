/**
 * RNF12 na tela — história H70: todo texto que veio do usuário, ou da API, chega
 * ao navegador escapado.
 *
 * **Quem escapa é o React**, em toda expressão `{...}` do JSX. O vetor está nas
 * formas de pular esse escape: HTML injetado por propriedade, `innerHTML`,
 * `eval`, link `javascript:`. O primeiro teste lê o código de `src/` e recusa
 * todas elas — tela nova entra nele sem ninguém lembrar dela, e é o que reprova
 * o PR que abrir o vetor. Os outros abrem telas de verdade com carga de script
 * nos nomes, e conferem que ela aparece como texto e não vira elemento.
 */
import { readdirSync, readFileSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import PlanoDeCampanha from "./componentes/PlanoDeCampanha";
import { abrir, amostra, montar } from "./testes/montar";

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
  /* A sessão é cookie HttpOnly: o JavaScript não a lê nem a guarda (regra 9 do kit). */
  ["document." + "cookie", "cookie lido ou escrito pelo JavaScript"],
  ["Author" + "ization", "cabeçalho de autorização montado na tela"],
];

function codigoDaTela(pasta) {
  return readdirSync(pasta, { recursive: true, withFileTypes: true })
    .filter((e) => e.isFile() && /\.(jsx?|tsx?)$/.test(e.name) && !/\.test\./.test(e.name) && !/[\\/]testes[\\/]?/.test(e.parentPath ?? e.path))
    .map((e) => join(e.parentPath ?? e.path, e.name));
}

const CARGAS = ["<script>alert('gih')</script>", '"><img src=x onerror=alert(1)>', "<svg onload=alert(1)>"];

/* Nenhum elemento veio da carga: nem `<script>`, nem `<img>`, nem atributo de evento. */
function semElementoInjetado(container) {
  expect(container.querySelector("script, img")).toBeNull();
  const comEvento = [...container.querySelectorAll("*")].filter((el) => [...el.attributes].some((a) => a.name.startsWith("on")));
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

  it("a sessão não fica guardada no navegador: o único item guardado é o tema", () => {
    const usos = [];
    for (const arquivo of codigoDaTela(RAIZ)) {
      const texto = readFileSync(arquivo, "utf8");
      for (const m of texto.matchAll(/(localStorage|sessionStorage)\.(setItem|getItem)\(([^,)]+)/g)) usos.push(`${relative(RAIZ, arquivo)}: ${m[1]} ${m[3]}`);
    }
    expect(usos.every((u) => /tema\.js: localStorage CHAVE/.test(u))).toBe(true);
  });

  it.each(CARGAS)("a lista de parceiros mostra a carga como texto: %s", async (carga) => {
    const lista = amostra("GET_api_parceiros");
    lista.itens[0].nome = carga;
    const { container } = abrir("/parceiros", {
      rotas: {
        "GET /api/parceiros": { corpo: lista },
        "GET /api/categorias": { corpo: amostra("GET_api_categorias") },
        "GET /api/painel/recortes": { corpo: amostra("GET_api_painel_recortes") },
      },
    });
    expect(await screen.findByText(carga)).toBeInTheDocument();
    semElementoInjetado(container);
  });

  it.each(CARGAS)("o motivo de uma falha, vindo da API, aparece como texto: %s", (carga) => {
    const { container } = montar(<PlanoDeCampanha execucao={{ situacao: "FALHOU", motivo: carga }} />);
    expect(screen.getByText(new RegExp(carga.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")))).toBeInTheDocument();
    semElementoInjetado(container);
  });
});
