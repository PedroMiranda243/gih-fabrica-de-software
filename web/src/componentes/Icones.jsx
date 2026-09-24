/**
 * Ícones em SVG, nunca emoji.
 *
 * Emoji muda de desenho a cada sistema, não herda a cor do texto e é lido em
 * voz alta pelo leitor de tela com o nome que o Unicode lhe deu — "gráfico com
 * tendência ascendente" no meio de um menu. O `docs/09` proíbe, e é por isso.
 *
 * Todos herdam `currentColor` e têm `aria-hidden`: o significado está no rótulo
 * ao lado, e um ícone anunciado duas vezes atrapalha quem usa leitor.
 */

const comuns = {
  width: 16,
  height: 16,
  viewBox: "0 0 16 16",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.5,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": "true",
  focusable: "false",
};

export function IconePainel(props) {
  return (
    <svg {...comuns} {...props}>
      <path d="M2 11.5 5.5 7l3 2.5L14 4" />
      <path d="M2 14h12" />
    </svg>
  );
}

export function IconeImportar(props) {
  return (
    <svg {...comuns} {...props}>
      <path d="M8 2v8" />
      <path d="m5 7 3 3 3-3" />
      <path d="M2.5 12.5v1h11v-1" />
    </svg>
  );
}

export function IconeParceiros(props) {
  return (
    <svg {...comuns} {...props}>
      <path d="M2.5 13.5v-1a3 3 0 0 1 3-3h1a3 3 0 0 1 3 3v1" />
      <circle cx="6" cy="5" r="2.25" />
      <path d="M11 9.75h.5a3 3 0 0 1 3 3v.75" />
      <path d="M10.5 3.1a2.25 2.25 0 0 1 0 4.3" />
    </svg>
  );
}

/* Uma pessoa com um cartão de acesso ao lado: contas e perfis, e não a rede de
   parceiros — que já usa o ícone de duas pessoas. */
export function IconeUsuarios(props) {
  return (
    <svg {...comuns} {...props}>
      <circle cx="6" cy="5" r="2.5" />
      <path d="M1.75 13.5v-.75a3.5 3.5 0 0 1 3.5-3.5h1.5a3.5 3.5 0 0 1 3.5 3.5v.75" />
      <rect x="11" y="3" width="3.5" height="5" rx="0.75" />
      <path d="M12 5.5h1.5" />
    </svg>
  );
}

/* Três réguas com o cursor em pontos diferentes: ajuste de limiar, e não
   engrenagem genérica de "configurações" — a tela só muda três números. */
export function IconeConfiguracao(props) {
  return (
    <svg {...comuns} {...props}>
      <path d="M2.5 4h6M11.5 4h2" />
      <circle cx="10" cy="4" r="1.5" />
      <path d="M2.5 8h2M7.5 8h6" />
      <circle cx="6" cy="8" r="1.5" />
      <path d="M2.5 12h7M12.5 12h1" />
      <circle cx="11" cy="12" r="1.5" />
    </svg>
  );
}

export function IconeSair(props) {
  return (
    <svg {...comuns} {...props}>
      <path d="M6 14H3.5v-12H6" />
      <path d="M10 11l3-3-3-3" />
      <path d="M13 8H6" />
    </svg>
  );
}

export function IconeTemaClaro(props) {
  return (
    <svg {...comuns} {...props}>
      <circle cx="8" cy="8" r="3" />
      <path d="M8 1v1.5M8 13.5V15M15 8h-1.5M2.5 8H1M12.95 3.05l-1.06 1.06M4.11 11.89l-1.06 1.06M12.95 12.95l-1.06-1.06M4.11 4.11 3.05 3.05" />
    </svg>
  );
}

export function IconeTemaEscuro(props) {
  return (
    <svg {...comuns} {...props}>
      <path d="M13.5 9.6A5.6 5.6 0 0 1 6.4 2.5a5.75 5.75 0 1 0 7.1 7.1Z" />
    </svg>
  );
}

/** Seta da variação. O sinal e a direção carregam o significado, não a cor. */
export function IconeVariacao({ sentido, ...props }) {
  const caminho =
    sentido === "sobe" ? "M8 12.5V3.5M4.5 7 8 3.5 11.5 7" : "M8 3.5v9M4.5 9 8 12.5 11.5 9";
  return (
    <svg {...comuns} width={12} height={12} {...props}>
      <path d={caminho} />
    </svg>
  );
}
