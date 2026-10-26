/**
 * Os ícones do GIH: desenhados aqui, numa grade de 24 e num traço só, sem
 * biblioteca de fora. Decorativos por padrão (aria-hidden); botão só com ícone
 * leva o nome no aria-label do botão.
 */
const D = {
  painel: "M4 20V10M10 20V4M16 20v-7M22 20H2",
  desempenho: "M3 17l5-5 4 3 8-8M15 7h5v5",
  importacao: "M12 3v12M7 10l5 5 5-5M4 21h16",
  parceiros: "M4 21v-1.5A4.5 4.5 0 0 1 8.5 15h3A4.5 4.5 0 0 1 16 19.5V21M10 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7M17 4.5a3.5 3.5 0 0 1 0 6.5M20 21v-1.5a4.5 4.5 0 0 0-2.5-4",
  assistente: "M4 5h16v11H9l-5 4V5zM8 9.5h8M8 12.5h5",
  relatorios: "M6 3h9l4 4v14H6zM14 3v5h5M9 13h7M9 17h5",
  modelo: "M12 3v3M12 18v3M3 12h3M18 12h3M6.5 6.5l2 2M15.5 15.5l2 2M6.5 17.5l2-2M15.5 8.5l2-2M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6",
  campanha: "M3 11l15-6v14L3 13zM7 12.5V18a1.5 1.5 0 0 0 3 0v-4.3M18 9a3 3 0 0 1 0 6",
  execucoes: "M4 6h16M4 12h16M4 18h10M18 16l2 2-2 2",
  benchmark: "M12 13l4-4M4 18a8 8 0 1 1 16 0M12 13.5a1 1 0 1 0 0-1",
  mensagens: "M3 6l9 6 9-6M3 6v12h18V6z",
  aprovacao: "M9 12l2 2 4-4M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18",
  usuarios: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8M4 21a8 8 0 0 1 16 0",
  auditoria: "M12 3l8 3v6c0 4.5-3.4 8-8 9-4.6-1-8-4.5-8-9V6zM9 12l2 2 4-4",
  operacoes: "M4 19V9M9 19V5M14 19v-6M19 19v-9M2 19h20",
  configuracao: "M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0M14 4v4M8 10v4M16 16v4",
  ajuda: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .8-1 1.5v.7M12 17h.01",
  sol: "M12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4",
  lua: "M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5",
  sair: "M15 4h4v16h-4M10 8l-4 4 4 4M6 12h11",
  menu: "M4 6h16M4 12h16M4 18h16",
  fechar: "M6 6l12 12M18 6L6 18",
  "seta-direita": "M9 6l6 6-6 6",
  "seta-esquerda": "M15 6l-6 6 6 6",
  "seta-baixo": "M6 9l6 6 6-6",
  sobe: "M12 19V5M6 11l6-6 6 6",
  cai: "M12 5v14M6 13l6 6 6-6",
  ordem: "M8 9l4-4 4 4M8 15l4 4 4-4",
  "ordem-asc": "M8 10l4-4 4 4M12 6v13",
  "ordem-desc": "M8 14l4 4 4-4M12 18V5",
  mostrar: "M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6",
  ocultar: "M3 3l18 18M10.6 5.1A10 10 0 0 1 12 5c6.5 0 10 7 10 7a17 17 0 0 1-3 3.9M6.6 6.6A17 17 0 0 0 2 12s3.5 7 10 7a9.6 9.6 0 0 0 5.4-1.6M9.9 9.9a3 3 0 0 0 4.2 4.2",
  erro: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18M12 7.5v5.5M12 16.5h.01",
  certo: "M5 12.5l4.5 4.5L19 7.5",
  info: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18M12 11v5.5M12 7.5h.01",
  atencao: "M12 3.5l9.5 16.5h-19zM12 10v4.5M12 17.5h.01",
  estimativa: "M3 18c3-1 4-8 7-8s3 5 5 5 3-4 6-6",
  vazio: "M4 8l8-4 8 4v8l-8 4-8-4zM4 8l8 4 8-4M12 12v8",
  baixar: "M12 4v11M7.5 10.5L12 15l4.5-4.5M5 20h14",
  imprimir: "M7 9V3h10v6M7 17H4v-7h16v7h-3M7 14h10v7H7z",
  mais: "M12 5v14M5 12h14",
  lixo: "M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13",
  lapis: "M4 20l4-1 11-11-3-3L5 16zM14 6l3 3",
  copiar: "M9 9h11v11H9zM5 15H4V4h11v1",
  enviar: "M4 12l16-8-6 16-2.5-6.5z",
  relogio: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18M12 7v5l3 2",
  arquivo: "M6 3h9l4 4v14H6zM14 3v5h5",
  busca: "M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14M20 20l-4-4",
  filtro: "M4 5h16l-6 7.5V19l-4 2v-8.5z",
  comparar: "M8 4v16M16 4v16M4 8h4M16 16h4M4 16h4M16 8h4",
  raio: "M13 2L4 14h7l-1 8 9-12h-7z",
  externo: "M14 4h6v6M20 4l-9 9M18 14v6H4V6h6",
  pessoa: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8M4 21a8 8 0 0 1 16 0",
  trava: "M6 11h12v10H6zM8 11V7a4 4 0 0 1 8 0v4",
};

export default function Icone({ nome, className = "", titulo }) {
  const caminho = D[nome];
  if (!caminho) return null;
  return (
    <svg
      className={`icone ${className}`}
      viewBox="0 0 24 24"
      width="1em"
      height="1em"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden={titulo ? undefined : "true"}
      role={titulo ? "img" : undefined}
      aria-label={titulo}
      focusable="false"
    >
      <path d={caminho} />
    </svg>
  );
}
