/** Espera anunciada: `role="status"` faz o leitor de tela avisar sozinho. */
export default function Carregando({ rotulo = "Carregando" }) {
  return (
    <div className="carregando" role="status">
      {rotulo}…
    </div>
  );
}

/**
 * Esqueleto que reserva o espaço do conteúdo que está por vir.
 *
 * `aria-hidden` porque não há informação aqui — quem usa leitor de tela recebe
 * o aviso pelo `role="status"` de quem o renderiza, e ler "caixa cinza" três
 * vezes só atrapalha.
 */
export function Esqueleto({ altura = 16, largura = "100%", style }) {
  return (
    <div
      className="esqueleto"
      aria-hidden="true"
      style={{ height: altura, width: largura, ...style }}
    />
  );
}
