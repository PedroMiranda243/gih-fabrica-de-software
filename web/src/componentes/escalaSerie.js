/**
 * Geometria da série histórica: tamanho do desenho, margens e escala.
 *
 * Mora fora do componente para poder ser testada sem desenhar nada. O jsdom não
 * mede texto, mas aqui não precisa: os rótulos são em Fira Code, que é
 * **monoespaçada** — todo caractere tem 0,6 em de largura. A largura de um
 * rótulo é conta, e a conta cabe num teste.
 *
 * Isso importa porque a primeira versão tinha 60 px de margem esquerda, e o
 * rótulo "R$ 500 mil" em 10 px ocupa 60 px sozinho, mais a folga até o eixo. O
 * resultado apareceu na captura para o documento de entrega: "₹$ 1,5 mi", com o
 * "R" cortado pela borda do desenho.
 */
import { comoDinheiro } from "../formato";

export const LARGURA = 720;
export const ALTURA = 220;

/* Tamanhos de fonte dos rótulos, em px — os mesmos de `.grafico__eixo` e
   `.grafico__rotulo-final` em `estilos/componentes.css`. */
export const FONTE_EIXO = 10;
export const FONTE_ROTULO_FINAL = 11;

/* Folga entre o texto e o que ele rotula. */
export const FOLGA_EIXO = 8;
export const FOLGA_ROTULO_FINAL = 10;

/* Margens dimensionadas para o **pior rótulo possível**, não para o de hoje:
   "R$ 999,9 mil" tem 12 caracteres. A margem certa depende do maior valor que o
   eixo pode mostrar, e o teste confere isso em várias ordens de grandeza. */
export const MARGEM = { topo: 16, direita: 96, baixo: 28, esquerda: 92 };

export const AREA = {
  largura: LARGURA - MARGEM.esquerda - MARGEM.direita,
  altura: ALTURA - MARGEM.topo - MARGEM.baixo,
};

/** Largura, em px, de um texto em Fira Code: 0,6 em por caractere. */
export function larguraDoTexto(texto, tamanhoDaFonte) {
  return texto.length * 0.6 * tamanhoDaFonte;
}

/** Um teto "redondo" acima do máximo, para a grade cair em número legível. */
export function tetoBonito(maximo) {
  if (maximo <= 0) return 1;
  const magnitude = 10 ** Math.floor(Math.log10(maximo));
  return Math.ceil(maximo / magnitude) * magnitude;
}

/** O rótulo compacto usado no eixo e no último ponto. */
export function rotuloCompacto(valor) {
  return comoDinheiro(valor, { compacto: true });
}

export const FRACOES_DA_GRADE = [0, 0.25, 0.5, 0.75, 1];
