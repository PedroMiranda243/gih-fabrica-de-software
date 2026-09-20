import { readdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

/**
 * Toda variável usada precisa existir em `tokens.css`.
 *
 * **Variável de CSS inexistente não dá erro: a declaração inteira é
 * descartada.** `gap: var(--esp-10)` com esse token ausente não vira gap zero
 * com aviso — vira nenhum gap, em silêncio, e o defeito só aparece para quem
 * olhar a tela de perto. Foi exatamente o que aconteceu com a distribuição por
 * segmento: as barras ficaram coladas no rótulo, e nenhum teste reclamou.
 *
 * Lê os arquivos como texto de propósito. Montar o DOM e perguntar ao
 * `getComputedStyle` diria o valor efetivo — que é justamente `normal` nos dois
 * casos, o certo e o errado.
 */
/* `fileURLToPath`, e não `new URL(...).pathname`: no Windows o `pathname` vem
   como "/C:/Users/..." e o `join` monta um caminho que não existe. */
const RAIZ = dirname(fileURLToPath(import.meta.url));

function arquivos(pasta, extensoes) {
  return readdirSync(pasta, { recursive: true, withFileTypes: true })
    .filter((e) => e.isFile() && extensoes.some((x) => e.name.endsWith(x)))
    .map((e) => join(e.parentPath ?? e.path, e.name));
}

describe("tokens", () => {
  it("nenhuma variável é usada sem estar definida", () => {
    const tokens = readFileSync(join(RAIZ, "tokens.css"), "utf8");
    const definidos = new Set([...tokens.matchAll(/^\s*(--[a-z0-9-]+)\s*:/gm)].map((m) => m[1]));

    const ausentes = new Map();
    for (const caminho of arquivos(join(RAIZ, ".."), [".css", ".jsx"])) {
      const texto = readFileSync(caminho, "utf8");
      for (const [, token] of texto.matchAll(/var\((--[a-z0-9-]+)/g)) {
        if (!definidos.has(token)) ausentes.set(token, caminho);
      }
    }

    expect(Object.fromEntries(ausentes)).toEqual({});
  });
});
