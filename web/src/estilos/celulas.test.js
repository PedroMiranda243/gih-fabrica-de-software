/**
 * Célula de tabela continua célula. Uma classe com `display: flex` (ou grid, ou
 * block) posta num `<td>` tira a célula da tabela: ela deixa de acompanhar a
 * altura da linha, e o fio que separa as linhas se parte — foi assim na coluna
 * Parâmetros das Execuções (#277), e o teste da tela não via, porque o jsdom não
 * desenha. Este confere o código: nenhuma classe que muda o `display` vai num
 * `<td>` ou num `<th>`. O arranjo em linha mora num elemento dentro da célula.
 */
import { readdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const RAIZ = dirname(fileURLToPath(import.meta.url));
const SRC = join(RAIZ, "..");

/** As classes cujo bloco de regra muda o `display` para algo que não é célula. */
function classesQueMudamODisplay() {
  const classes = new Set();
  for (const nome of readdirSync(RAIZ).filter((n) => n.endsWith(".css"))) {
    const css = readFileSync(join(RAIZ, nome), "utf8").replace(/\/\*[\s\S]*?\*\//g, "");
    for (const [, seletores, corpo] of css.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
      const display = corpo.match(/(?:^|;|\s)display\s*:\s*([\w-]+)/);
      if (!display || ["table-cell", "none", "contents"].includes(display[1])) continue;
      for (const seletor of seletores.split(",")) {
        // Só a classe que é o alvo do seletor: em `.tabela .num span`, o alvo é o span.
        const alvo = seletor.trim().split(/[\s>+~]+/).at(-1) ?? "";
        if (/^(td|th)?\./.test(alvo) && !/[:[]/.test(alvo)) {
          for (const [, classe] of alvo.matchAll(/\.([\w-]+)/g)) classes.add(classe);
        }
      }
    }
  }
  return classes;
}

function arquivosJsx(pasta) {
  return readdirSync(pasta, { withFileTypes: true }).flatMap((e) =>
    e.isDirectory() ? arquivosJsx(join(pasta, e.name)) : e.name.endsWith(".jsx") && !e.name.includes(".test.") ? [join(pasta, e.name)] : [],
  );
}

describe("as células das tabelas", () => {
  it("nenhuma classe que muda o display vai num <td> ou num <th> (#277)", () => {
    const proibidas = classesQueMudamODisplay();
    const achados = [];
    for (const arquivo of arquivosJsx(SRC)) {
      const jsx = readFileSync(arquivo, "utf8");
      for (const [, tag, classes] of jsx.matchAll(/<(td|th)\b[^>]*?className="([^"]+)"/g)) {
        for (const classe of classes.split(/\s+/)) {
          if (proibidas.has(classe)) achados.push(`${arquivo.slice(SRC.length + 1)}: <${tag} className="${classes}">`);
        }
      }
    }
    expect(achados).toEqual([]);
  });

  it("a conferência acha a classe que quebrava a tabela", () => {
    // Sem isto, um erro no leitor do CSS faria o teste de cima passar sem olhar nada.
    expect(classesQueMudamODisplay()).toContain("parametros");
  });
});
