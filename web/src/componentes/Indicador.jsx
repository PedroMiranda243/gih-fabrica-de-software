import { comoDelta, comoPercentual, sentidoDa, TRACO } from "../formato";
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
 *
 * `subirEBom` desacopla **para onde a seta aponta** de **qual cor ela usa**.
 * Em "Em risco", mais parceiros é pior: a seta continua apontando para cima,
 * porque o número subiu, e a cor passa a ser a de risco. Sem essa separação, o
 * painel pintaria de verde a única notícia ruim da tela.
 *
 * `absoluta` troca o percentual pela diferença em unidades. Contagem pede
 * diferença absoluta: de 1 para 2 também é +100%, e "+100% em risco" faz o
 * gestor entender outra coisa do que aconteceu.
 */
export default function Indicador({
  rotulo,
  valor,
  variacao,
  absoluta = false,
  subirEBom = true,
  nota,
}) {
  const sentido = sentidoDa(variacao);
  const indefinida = sentido === "indefinida";
  const tom = subirEBom ? sentido : INVERSO[sentido] ?? sentido;

  return (
    <div className="painel indicador">
      <span className="indicador__rotulo">{rotulo}</span>
      <span className="indicador__valor num">{valor}</span>

      {nota !== undefined ? (
        <span className="indicador__nota">{nota}</span>
      ) : (
        <span
          className={`indicador__variacao indicador__variacao--${tom}`}
          title={indefinida ? "Sem base de comparação neste período" : undefined}
        >
          {(sentido === "sobe" || sentido === "cai") && <IconeVariacao sentido={sentido} />}
          {indefinida ? TRACO : absoluta ? comoDelta(variacao) : comoPercentual(variacao)}
          <span className="so-leitor">
            {indefinida
              ? "sem variação calculável em relação ao período anterior"
              : `em relação ao período anterior`}
          </span>
        </span>
      )}
    </div>
  );
}

/* Só a **cor** inverte; a seta continua dizendo para onde o número foi. */
const INVERSO = { sobe: "cai", cai: "sobe" };
