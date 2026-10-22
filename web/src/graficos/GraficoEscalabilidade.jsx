/**
 * Escalabilidade do benchmark: o tempo de cada modo pelo número de parceiros, com
 * o eixo do tempo em escala logarítmica (de milissegundos a minutos). Uma cor por
 * modo, a mesma em qualquer execução — e nunca só a cor: cada modo tem marcador
 * próprio, o nome no fim da linha e a dica com os quatro tempos.
 */
import { useId, useState } from "react";

import { comoInteiro, comoTempo, ORDEM_COLUNAS, ROTULO_COLUNA } from "../formato";
import { escalaLinear, escalaLog, marcasLog } from "./escala";
import { useLargura } from "./useLargura";

const MARGEM = { topo: 20, direita: 96, base: 40, esquerda: 70 };

export function Marcador({ coluna, x, y, r = 5 }) {
  const cls = `serie-marca serie-marca--${coluna.toLowerCase()}`;
  if (coluna === "PYTHON") return <circle className={cls} cx={x} cy={y} r={r} />;
  if (coluna === "CPP_SERIAL") return <rect className={cls} x={x - r} y={y - r} width={r * 2} height={r * 2} />;
  if (coluna === "OPENMP") return <path className={cls} d={`M${x} ${y - r * 1.25}L${x + r * 1.25} ${y}L${x} ${y + r * 1.25}L${x - r * 1.25} ${y}Z`} />;
  return <path className={cls} d={`M${x} ${y - r * 1.2}L${x + r * 1.15} ${y + r * 0.9}L${x - r * 1.15} ${y + r * 0.9}Z`} />;
}

export default function GraficoEscalabilidade({ escalabilidade, altura = 320 }) {
  const [ref, largura] = useLargura();
  const [foco, setFoco] = useState(null);
  const idDesc = useId();
  const series = ORDEM_COLUNAS.map((c) => escalabilidade.series.find((s) => s.coluna === c)).filter((s) => s && s.pontos.length);
  const tamanhos = [...new Set(series.flatMap((s) => s.pontos.map((p) => p.parceiros)))].sort((a, b) => a - b);
  const tempos = series.flatMap((s) => s.pontos.map((p) => p.media_s)).filter((t) => t > 0);
  if (!tempos.length) return null;
  const ticks = marcasLog(Math.min(...tempos), Math.max(...tempos));
  const y = escalaLog([ticks[0], ticks[ticks.length - 1]], [altura - MARGEM.base, MARGEM.topo]);
  const um = tamanhos.length === 1;
  const x = um ? () => (MARGEM.esquerda + largura - MARGEM.direita) / 2 : escalaLinear([tamanhos[0], tamanhos[tamanhos.length - 1]], [MARGEM.esquerda + 12, largura - MARGEM.direita - 12]);

  const descricao = `Tempo médio de cada modo pelo número de parceiros, em escala logarítmica. ${series
    .map((s) => `${ROTULO_COLUNA[s.coluna]}: ${s.pontos.map((p) => `${comoTempo(p.media_s)} com ${comoInteiro(p.parceiros)}`).join("; ")}`)
    .join(". ")}.`;

  function mover(evento) {
    const r = evento.currentTarget.getBoundingClientRect();
    const px = evento.clientX - r.left;
    let melhor = null;
    for (const t of tamanhos) if (melhor === null || Math.abs(x(t) - px) < Math.abs(x(melhor) - px)) melhor = t;
    setFoco(melhor);
  }

  return (
    <figure className="grafico grafico--escala" ref={ref}>
      <svg width={largura} height={altura} role="img" aria-labelledby={idDesc} onPointerMove={mover} onPointerLeave={() => setFoco(null)} className="grafico__svg">
        <title id={idDesc}>{descricao}</title>
        <g className="grafico__grade">
          {ticks.map((t) => (
            <g key={t}>
              <line x1={MARGEM.esquerda} x2={largura - MARGEM.direita} y1={y(t)} y2={y(t)} />
              <text x={MARGEM.esquerda - 10} y={y(t)} dy="0.32em" textAnchor="end">
                {comoTempo(t)}
              </text>
            </g>
          ))}
        </g>
        <g className="grafico__eixo-x">
          {tamanhos.map((t) => (
            <text key={t} x={x(t)} y={altura - 14} textAnchor="middle">
              {comoInteiro(t)}
            </text>
          ))}
          <text x={(MARGEM.esquerda + largura - MARGEM.direita) / 2} y={altura} textAnchor="middle" className="grafico__titulo-eixo">
            parceiros no cenário
          </text>
        </g>
        {foco !== null && <line className="grafico__mira" x1={x(foco)} x2={x(foco)} y1={MARGEM.topo} y2={altura - MARGEM.base} />}
        {series.map((s) => {
          const pts = [...s.pontos].sort((a, b) => a.parceiros - b.parceiros);
          const fim = pts[pts.length - 1];
          return (
            <g key={s.coluna} className={`serie serie--${s.coluna.toLowerCase()}`}>
              {pts.length > 1 && <polyline className="serie__linha" points={pts.map((p) => `${x(p.parceiros)},${y(p.media_s)}`).join(" ")} />}
              {pts.map((p) => (
                <Marcador key={p.parceiros} coluna={s.coluna} x={x(p.parceiros)} y={y(p.media_s)} />
              ))}
              <text className="serie__nome" x={x(fim.parceiros) + 12} y={y(fim.media_s)} dy="0.32em">
                {ROTULO_COLUNA[s.coluna]}
              </text>
            </g>
          );
        })}
      </svg>
      {foco !== null && (
        <div className="grafico__dica" style={{ left: Math.min(Math.max(x(foco), 100), largura - 100) }} aria-hidden="true">
          <strong>{comoInteiro(foco)} parceiros</strong>
          {series.map((s) => {
            const p = s.pontos.find((q) => q.parceiros === foco);
            return (
              <span key={s.coluna} className="grafico__dica-linha">
                <svg width="14" height="14" aria-hidden="true">
                  <Marcador coluna={s.coluna} x={7} y={7} r={4} />
                </svg>
                {ROTULO_COLUNA[s.coluna]}: {p ? comoTempo(p.media_s) : "não medido"}
              </span>
            );
          })}
        </div>
      )}
      <figcaption className="grafico__legenda">
        {series.map((s) => (
          <span key={s.coluna} className={`legenda serie--${s.coluna.toLowerCase()}`}>
            <svg width="28" height="14" aria-hidden="true">
              <line className="serie__linha" x1="2" y1="7" x2="26" y2="7" />
              <Marcador coluna={s.coluna} x={14} y={7} r={4} />
            </svg>
            {ROTULO_COLUNA[s.coluna]}
          </span>
        ))}
        <span className="legenda legenda--nota">Tempo em escala logarítmica: cada linha da grade é dez vezes a de baixo.</span>
      </figcaption>
    </figure>
  );
}
