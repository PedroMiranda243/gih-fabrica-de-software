/** Enquanto a sessão é conferida: espera, e não a tela de entrada piscando. */
import Marca from "./Marca";

export default function Conferindo() {
  return (
    <div className="conferindo" role="status" aria-live="polite">
      <Marca />
      <p>Conferindo a sua sessão…</p>
    </div>
  );
}
