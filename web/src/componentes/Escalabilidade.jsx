/**
 * O gráfico de escalabilidade do benchmark (UC09, passo 7): o tempo de cada modo
 * pelo número de parceiros, com os tamanhos já medidos com o mesmo número de
 * ações.
 *
 * **Uma cor por modo, a mesma em qualquer execução** (`docs/09`): a cor segue o
 * modo, e não a posição — sem a GPU, o OpenMP continua laranja. As quatro foram
 * validadas com todos os pares, porque as linhas se cruzam.
 *
 * **A cor nunca é o único sinal.** A legenda fica acima; o nome do modo, no fim
 * de cada linha, quando cabe; a dica, ao passar o mouse, lista os quatro tempos
 * daquele tamanho; e a tabela dos números está a um clique. Texto nunca usa a
 * cor da série: a identidade vem da marca ao lado.
 *
 * SVG desenhado à mão, como a série histórica, pelo mesmo motivo: são poucos
 * pontos, e a rampa do `docs/09` precisa mandar na cor. **Na largura real do
 * painel**, medida: num tamanho fixo esticado, o texto crescia junto com o
 * desenho, e num monitor largo ficava com o dobro do tamanho do resto da tela.
 */
import { useCallback, useMemo, useState } from "react";

import { COLUNAS_BENCHMARK, COR_COLUNA, comoInteiro, comoTempo, ROTULO_COLUNA, TRACO } from "../formato";
import {
  ALTURA,
  ALTURA_DA_AREA,
  dominioDoTempo,
  LARGURA_PADRAO,
  marcasDosParceiros,
  MARGEM,
  marcasDoTempo,
  PARCEIROS,
  rotuloDoTempo,
  rotulosQueCabem,
  xDosParceiros,
  yDoTempo,
} from "./escalaLog";

const ORDEM = COLUNAS_BENCHMARK.map(([coluna]) => coluna);

export default function Escalabilidade({ series, acoes, destaque }) {
  const [emFoco, setEmFoco] = useState(null);
  const [mostrarTabela, setMostrarTabela] = useState(false);
  const [largura, setLargura] = useState(LARGURA_PADRAO);

  /* A largura do painel, sem o respiro da moldura: medida ao montar — o layout já
     existe, mesmo com a aba escondida, quando o `ResizeObserver` não avisa — e de
     novo a cada vez que ela muda. O jsdom dos testes mede zero: fica a padrão. */
  const moldura = useCallback((elemento) => {
    if (!elemento) return undefined;
    const medir = () => {
      const estilo = getComputedStyle(elemento);
      const respiro = parseFloat(estilo.paddingLeft) + parseFloat(estilo.paddingRight);
      const medida = Math.floor(elemento.clientWidth - respiro);
      if (medida > 0) setLargura(medida);
    };
    medir();
    if (typeof ResizeObserver === "undefined") return undefined;
    const observador = new ResizeObserver(medir);
    observador.observe(elemento);
    return () => observador.disconnect();
  }, []);

  const desenho = useMemo(() => {
    const ordenadas = [...series].sort((a, b) => ORDEM.indexOf(a.coluna) - ORDEM.indexOf(b.coluna));
    const dominio = dominioDoTempo(ordenadas.flatMap((s) => s.pontos.map((p) => p.media_s)));
    const linhas = ordenadas.map((s) => ({
      coluna: s.coluna,
      pontos: s.pontos.map((p) => ({
        ...p,
        x: xDosParceiros(p.parceiros, largura),
        y: yDoTempo(p.media_s, dominio),
      })),
    }));
    const tamanhos = [...new Set(ordenadas.flatMap((s) => s.pontos.map((p) => p.parceiros)))].sort((a, b) => a - b);
    const maiorTamanho = tamanhos[tamanhos.length - 1];
    /* Rótulo no fim só das linhas que chegam ao maior tamanho medido: as outras
       terminam no meio do desenho, e o nome ali cairia em cima de outra linha. */
    const finais = linhas
      .filter((l) => l.pontos.length && l.pontos[l.pontos.length - 1].parceiros === maiorTamanho)
      .map((l) => ({ coluna: l.coluna, ...l.pontos[l.pontos.length - 1] }));
    return { dominio, linhas, tamanhos, rotulos: rotulosQueCabem(finais) };
  }, [series, largura]);

  const { dominio, linhas, tamanhos, rotulos } = desenho;
  const tempoEm = (coluna, parceiros) =>
    linhas.find((l) => l.coluna === coluna)?.pontos.find((p) => p.parceiros === parceiros)?.media_s ?? null;

  /* O desenho tem a largura da tela, então o pixel do mouse já é o do desenho. A
     dica vai para o tamanho medido mais perto do cursor. */
  function aoMover(evento) {
    const caixa = evento.currentTarget.getBoundingClientRect();
    const x = ((evento.clientX - caixa.left) / caixa.width) * largura;
    const perto = (t) => Math.abs(xDosParceiros(t, largura) - x);
    setEmFoco(tamanhos.reduce((melhor, t) => (perto(t) < perto(melhor) ? t : melhor)));
  }

  const base = MARGEM.topo + ALTURA_DA_AREA;
  const xDoFoco = emFoco ? xDosParceiros(emFoco, largura) : 0;

  return (
    <div className="grafico__moldura escalabilidade" ref={moldura}>
      <ul className="escalabilidade__legenda" aria-label="Legenda">
        {linhas.map(({ coluna }) => (
          <li key={coluna}>
            <svg width="20" height="10" aria-hidden="true">
              <line x1="1" y1="5" x2="19" y2="5" stroke={COR_COLUNA[coluna]} strokeWidth="2" strokeLinecap="round" />
              <circle cx="10" cy="5" r="3.5" fill={COR_COLUNA[coluna]} />
            </svg>
            {ROTULO_COLUNA[coluna]}
          </li>
        ))}
      </ul>

      <svg
        className="grafico"
        width={largura}
        height={ALTURA}
        viewBox={`0 0 ${largura} ${ALTURA}`}
        role="img"
        aria-label={`Tempo de cada modo pelo número de parceiros, com ${acoes} ações, em escalas logarítmicas. ${
          tamanhos.length
        } tamanho${tamanhos.length === 1 ? "" : "s"} medido${tamanhos.length === 1 ? "" : "s"}: ${tamanhos
          .map(comoInteiro)
          .join(", ")} parceiros.`}
        onMouseMove={tamanhos.length ? aoMover : undefined}
        onMouseLeave={() => setEmFoco(null)}
      >
        {/* Grade recessiva, nas potências de dez do tempo. */}
        {marcasDoTempo(dominio).map((marca) => {
          const y = yDoTempo(marca, dominio);
          return (
            <g key={marca}>
              <line className="grafico__grade" x1={MARGEM.esquerda} y1={y} x2={largura - MARGEM.direita} y2={y} />
              <text className="grafico__eixo" x={MARGEM.esquerda - 8} y={y + 3} textAnchor="end">
                {rotuloDoTempo(marca)}
              </text>
            </g>
          );
        })}

        {marcasDosParceiros(largura).map((marca) => (
          <text
            key={marca}
            className="grafico__eixo"
            x={xDosParceiros(marca, largura)}
            y={ALTURA - 12}
            textAnchor={marca === PARCEIROS[0] ? "start" : marca === PARCEIROS[1] ? "end" : "middle"}
          >
            {comoInteiro(marca)}
          </text>
        ))}
        {/* O nome do eixo na margem direita, na linha das marcas: embaixo do
            "10.000", ele saía do desenho e cobria a marca. */}
        <text className="grafico__eixo" x={largura - MARGEM.direita + 8} y={ALTURA - 12}>
          parceiros
        </text>

        {/* O tamanho da execução que a tela mostra, marcado sem cor de dado. */}
        {destaque && (
          <line
            className="escalabilidade__destaque"
            x1={xDosParceiros(destaque, largura)}
            y1={MARGEM.topo}
            x2={xDosParceiros(destaque, largura)}
            y2={base}
          />
        )}

        {emFoco && (
          <line className="grafico__cruz" x1={xDoFoco} y1={MARGEM.topo} x2={xDoFoco} y2={base} />
        )}

        {linhas.map(({ coluna, pontos }) => (
          <g key={coluna}>
            {pontos.length > 1 && (
              <path
                className="escalabilidade__linha"
                stroke={COR_COLUNA[coluna]}
                d={pontos.map((p, i) => `${i ? "L" : "M"}${p.x} ${p.y}`).join(" ")}
              />
            )}
            {/* Um ponto por tamanho medido, com um anel da cor do fundo: onde
                duas linhas se cruzam, as marcas continuam separadas. */}
            {pontos.map((p) => (
              <circle
                key={p.parceiros}
                className="escalabilidade__ponto"
                cx={p.x}
                cy={p.y}
                r={emFoco === p.parceiros ? 5.5 : 4}
                fill={COR_COLUNA[coluna]}
              />
            ))}
          </g>
        ))}

        {rotulos.map((r) => (
          <text key={r.coluna} className="escalabilidade__rotulo" x={r.x + 10} y={r.y + 4}>
            {ROTULO_COLUNA[r.coluna]}
          </text>
        ))}
      </svg>

      {emFoco && (
        <div
          className="grafico__dica"
          style={{
            // A moldura tem 16 px de respiro antes do desenho; à direita do meio,
            // a dica abre para a esquerda do cursor, para não sair do painel.
            left: xDoFoco > largura * 0.6 ? xDoFoco + 16 - 190 : xDoFoco + 16 + 12,
            // Abaixo da legenda, que ocupa o topo da moldura.
            top: 48,
          }}
        >
          <div style={{ fontWeight: 600 }}>{comoInteiro(emFoco)} parceiros</div>
          {linhas.map(({ coluna }) => (
            <div key={coluna} className="escalabilidade__dica-linha">
              <span className="escalabilidade__chave" style={{ background: COR_COLUNA[coluna] }} aria-hidden="true" />
              <span>{ROTULO_COLUNA[coluna]}</span>
              <span className="num">{comoTempo(tempoEm(coluna, emFoco))}</span>
            </div>
          ))}
        </div>
      )}

      {tamanhos.length === 1 && (
        <p className="grafico__legenda-lacuna">
          Um tamanho só, por enquanto. Rode o benchmark com outro número de parceiros e as mesmas {acoes} ações para
          ver como cada modo cresce.
        </p>
      )}

      <button
        type="button"
        className="botao botao--secundario"
        style={{ marginTop: "var(--esp-12)", minHeight: 32 }}
        onClick={() => setMostrarTabela((v) => !v)}
        aria-expanded={mostrarTabela}
      >
        {mostrarTabela ? "Ocultar os números" : "Ver os números"}
      </button>

      {mostrarTabela && (
        <div className="tabela-rolagem" style={{ marginTop: "var(--esp-12)" }}>
          <table className="tabela">
            <caption className="so-leitor">Tempo médio de cada modo, por número de parceiros</caption>
            <thead>
              <tr>
                <th scope="col" className="numerica">
                  Parceiros
                </th>
                {linhas.map(({ coluna }) => (
                  <th key={coluna} scope="col" className="numerica">
                    {ROTULO_COLUNA[coluna]}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {tamanhos.map((t) => (
                <tr key={t}>
                  <td className="numerica">{comoInteiro(t)}</td>
                  {linhas.map(({ coluna }) => {
                    const tempo = tempoEm(coluna, t);
                    return (
                      <td key={coluna} className="numerica">
                        {tempo === null ? TRACO : comoTempo(tempo)}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
