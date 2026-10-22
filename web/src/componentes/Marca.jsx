/** A marca do GIH. */
export default function Marca({ completa = false }) {
  return (
    <span className={`marca${completa ? " marca--completa" : ""}`}>
      <span className="marca__sigla" aria-hidden={completa ? "true" : undefined}>
        GIH
      </span>
      <span className="marca__nome">
        <span className={completa ? undefined : "sr-only"}>GIH — </span>Growth Intelligence Hub
      </span>
      {completa && <span className="marca__lema">Inteligência de crescimento para redes de parceiros</span>}
    </span>
  );
}
