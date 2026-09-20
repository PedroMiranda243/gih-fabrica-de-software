import { comoInteiro, ROTULO_SEGMENTO } from "../formato";

import EstadoVazio from "./EstadoVazio";

/**
 * Quantos parceiros em cada segmento, em barras horizontais.
 *
 * **Barra, e não pizza.** A pergunta aqui é "quantos em cada um" e "qual é o
 * maior", e comparar comprimentos alinhados numa mesma base é a tarefa visual
 * mais fácil que existe; comparar ângulos é a mais difícil. A ordem já vem da
 * API, do maior para o menor, com desempate estável — sem isso, dois segmentos
 * empatados trocariam de lugar entre recargas e o gráfico pareceria mudar sem
 * nada ter mudado.
 *
 * Especificação das marcas: barra de 12 px, extremidade do dado arredondada e
 * **base reta**, trilho recessivo de um passo da superfície. O valor fica ao
 * lado em texto — não é rótulo dentro da barra, que some quando a barra é
 * curta, nem número em cima de cada uma, que é ruído.
 *
 * A cor é a do segmento, a mesma da tabela e do indicador. Como o número
 * aparece em texto ao lado, nada aqui depende só de cor (RNF22).
 */
export default function DistribuicaoSegmentos({ itens, total }) {
  if (!itens.length) {
    return (
      <EstadoVazio
        titulo="Segmentação ainda não calculada"
        texto="A classificação por segmento roda junto com a importação. Importe um período para vê-la aqui."
      />
    );
  }

  /* A barra mais longa é a do maior segmento, não a do total: com o total como
     referência, uma rede concentrada em "Estável" deixaria as outras cinco
     barras como fiapos ilegíveis. */
  const maior = Math.max(...itens.map((i) => i.total));

  return (
    <ul className="distribuicao">
      {itens.map((item) => (
        <li className="distribuicao__linha" key={item.segmento}>
          <span className="distribuicao__rotulo">
            {ROTULO_SEGMENTO[item.segmento] ?? item.segmento}
          </span>
          <span className="distribuicao__trilho">
            <span
              className={`distribuicao__barra distribuicao__barra--${item.segmento.toLowerCase()}`}
              style={{ width: `${(item.total / maior) * 100}%` }}
            />
          </span>
          <span className="distribuicao__valor num">
            {comoInteiro(item.total)}
            <span className="so-leitor">
              {" "}
              de {comoInteiro(total)} parceiros classificados no período
            </span>
          </span>
        </li>
      ))}
    </ul>
  );
}
