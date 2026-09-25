/**
 * O erro do modelo ao lado do erro das referências (H46) — barras horizontais.
 *
 * **Ênfase, e não categorias**: a rede na cor da rampa, as referências em
 * cinza. O gráfico existe para responder uma pergunta só — a rede erra menos
 * que a conta simples? —, e dar uma cor a cada referência faria o olho procurar
 * três histórias onde há uma. O par de cores foi validado nos dois temas (ver
 * `--serie-referencia` em `tokens.css`).
 *
 * **Barras em HTML, com o nome e o valor em texto.** O leitor de tela lê os
 * números sem depender do desenho, e o `title` de cada linha dá a dica no
 * mouse. A barra começa no zero: começar no menor valor faria 9,2% contra 10,0%
 * parecer o dobro.
 *
 * **Uma métrica por gráfico.** MAPE e Brier têm escalas diferentes; juntá-los
 * pediria dois eixos, e gráfico de dois eixos engana (ver a skill de
 * visualização e o `docs/09`).
 */
import { useId } from "react";

export default function ComparacaoReferencias({ titulo, nota, barras, formatar }) {
  const idTitulo = useId();
  const validas = barras.filter((b) => b.valor !== null && b.valor !== undefined);
  const maximo = Math.max(...validas.map((b) => Number(b.valor)), 0);

  return (
    <figure className="comparacao" aria-labelledby={idTitulo}>
      <figcaption className="comparacao__titulo" id={idTitulo}>
        {titulo}
        {nota && <span className="comparacao__nota">{nota}</span>}
      </figcaption>
      <ul className="comparacao__barras">
        {validas.map((barra) => {
          const proporcao = maximo > 0 ? Number(barra.valor) / maximo : 0;
          return (
            <li
              key={barra.rotulo}
              className={`comparacao__linha${barra.destaque ? " comparacao__linha--destaque" : ""}`}
              title={`${barra.rotulo}: ${formatar(barra.valor)}`}
            >
              <span className="comparacao__rotulo">{barra.rotulo}</span>
              <span className="comparacao__trilho">
                {/* A largura sai da conta, no estilo da própria barra: o espaço do
                    valor, à direita, fica reservado, para o número nunca ser
                    cortado nem sair do painel. */}
                <span
                  className="comparacao__barra"
                  style={{ width: `calc((100% - 7ch) * ${proporcao.toFixed(4)})` }}
                  data-proporcao={proporcao.toFixed(4)}
                  aria-hidden="true"
                />
                <span className="comparacao__valor num">{formatar(barra.valor)}</span>
              </span>
            </li>
          );
        })}
      </ul>
    </figure>
  );
}
