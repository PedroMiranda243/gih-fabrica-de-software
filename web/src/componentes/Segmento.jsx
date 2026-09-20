import { ROTULO_SEGMENTO, TRACO } from "../formato";

/**
 * O segmento de um parceiro: **ponto colorido + rótulo neutro**.
 *
 * As duas metades são obrigatórias. A cor sozinha reprovaria a RNF22 — nenhuma
 * informação pode ser transmitida só por cor — e o rótulo colorido violaria a
 * regra 1.1 do `docs/09`, que reserva a cor de segmento para ponto ou barra.
 *
 * Segmento nulo vira travessão, e não "Estável". Os dois são coisas
 * diferentes: um diz "a segmentação ainda não rodou para este período", o
 * outro diz "rodou, e este parceiro não tem tendência".
 */
export default function Segmento({ valor }) {
  if (!valor) {
    return (
      <span style={{ color: "var(--ink-2)" }} title="Segmentação ainda não calculada">
        {TRACO}
      </span>
    );
  }

  return (
    <span className="segmento">
      <span className={`segmento__ponto segmento__ponto--${valor.toLowerCase()}`} aria-hidden="true" />
      {ROTULO_SEGMENTO[valor] ?? valor}
    </span>
  );
}
