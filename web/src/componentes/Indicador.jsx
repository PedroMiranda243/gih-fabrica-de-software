import { comoPercentual, sentidoDa, TRACO } from "../formato";
import { IconeVariacao } from "./Icones";

/**
 * Um indicador consolidado do período.
 *
 * A variação carrega o significado em **três** sinais redundantes: a seta, o
 * sinal do número e a cor. Quem não distingue verde de vermelho lê a seta;
 * quem usa leitor de tela ouve o texto. A cor é reforço, nunca a informação.
 *
 * Variação nula vira travessão. Renderizar 0% ali diria "não mudou" sobre algo
 * que não foi medido — sem período anterior, ou com base anterior zerada, em
 * que a divisão é indefinida.
 */
export default function Indicador({ rotulo, valor, variacao }) {
  const sentido = sentidoDa(variacao);
  const indefinida = sentido === "indefinida";

  return (
    <div className="painel indicador">
      <span className="indicador__rotulo">{rotulo}</span>
      <span className="indicador__valor num">{valor}</span>

      <span
        className={`indicador__variacao indicador__variacao--${sentido}`}
        title={indefinida ? "Sem base de comparação neste período" : undefined}
      >
        {(sentido === "sobe" || sentido === "cai") && <IconeVariacao sentido={sentido} />}
        {indefinida ? TRACO : comoPercentual(variacao)}
        <span className="so-leitor">
          {indefinida
            ? "sem variação calculável em relação ao período anterior"
            : `em relação ao período anterior`}
        </span>
      </span>
    </div>
  );
}
