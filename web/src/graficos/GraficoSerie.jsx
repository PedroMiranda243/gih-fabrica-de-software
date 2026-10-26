/**
 * A série histórica: um ponto por período. A lacuna (valor nulo) interrompe a
 * linha — ligar os vizinhos desenharia uma tendência que ninguém mediu. A
 * estimativa do modelo, quando há, entra como trecho tracejado com marcador vazado
 * e legenda; a cor sozinha não basta.
 */
import { useId, useMemo, useState } from "react";

import { comoData, comoDiaMes, comoDinheiro, comoDinheiroCurto, comoInteiro, comoPeriodo } from "../formato";
import { escalaLinear, marcas } from "./escala";
import { useLargura } from "./useLargura";

const MARGEM = { topo: 28, direita: 28, base: 34, esquerda: 64 };

export default function GraficoSerie({ pontos, altura = 280, estimativa = null, rotulo, campo = "faturamento", formatoEixo = comoDinheiroCurto, formatoValor = comoDinheiro, destacarUltimo = true }) {
  const [ref, largura] = useLargura();
  const [foco, setFoco] = useState(null);
  const idDesc = useId();

  const dados = useMemo(() => pontos.map((p) => ({ periodo: p.periodo, v: p[campo] === null || p[campo] === undefined ? null : Number(p[campo]), bruto: p })), [pontos, campo]);
  const valores = dados.map((d) => d.v).filter((v) => v !== null);
  if (estimativa?.valor !== null && estimativa?.valor !== undefined) valores.push(Number(estimativa.valor));

  const n = dados.length + (estimativa ? 1 : 0);
  const minV = Math.min(...valores);
  const maxV = Math.max(...valores);
  const folga = (maxV - minV) * 0.12 || maxV * 0.05 || 1;
  const ticks = marcas(minV - folga, maxV + folga, 4);
  const y = escalaLinear([ticks[0], ticks[ticks.length - 1]], [altura - MARGEM.base, MARGEM.topo]);
  const passo = (largura - MARGEM.esquerda - MARGEM.direita) / Math.max(n - 1, 1);
  const x = (i) => MARGEM.esquerda + i * passo;

  /* Trechos contínuos: a lacuna quebra a linha. */
  const trechos = [];
  let atual = [];
  dados.forEach((d, i) => {
    if (d.v === null) {
      if (atual.length) trechos.push(atual);
      atual = [];
    } else atual.push([x(i), y(d.v)]);
  });
  if (atual.length) trechos.push(atual);

  const ultimoIdx = dados.map((d) => d.v !== null).lastIndexOf(true);
  const ultimo = ultimoIdx >= 0 ? dados[ultimoIdx] : null;
  const temLacuna = dados.some((d) => d.v === null);
  const xEst = estimativa ? x(dados.length) : null;
  const yEst = estimativa ? y(Number(estimativa.valor)) : null;

  const rotuloEixoX = (i) => {
    const intervalo = Math.max(1, Math.ceil(n / Math.max(2, Math.floor(largura / 90))));
    /* com estimativa, o último período cede a vez ao "próximo" quando os dois não cabem lado a lado */
    if (i === dados.length - 1) return !(estimativa && passo < 72);
    return i % intervalo === 0;
  };
  /* o valor da estimativa fica do lado de fora do traço: acima quando ela sobe, abaixo quando cai */
  const estimativaSobe = estimativa && ultimo ? Number(estimativa.valor) >= ultimo.v : true;

  function mover(evento) {
    const r = evento.currentTarget.getBoundingClientRect();
    const px = evento.clientX - r.left;
    const i = Math.round((px - MARGEM.esquerda) / passo);
    setFoco(Math.max(0, Math.min(n - 1, i)));
  }

  const descricao = ultimo
    ? `${rotulo}: ${dados.length} períodos, de ${comoData(dados[0].periodo.data_inicio)} a ${comoData(dados[dados.length - 1].periodo.data_fim)}. Mínimo de ${formatoValor(minV)} e máximo de ${formatoValor(maxV)}; no último período medido, ${formatoValor(ultimo.v)}.${temLacuna ? " Há período sem medição, e a linha se interrompe nele." : ""}${estimativa ? ` Estimativa do modelo para o próximo período: ${formatoValor(estimativa.valor)}.` : ""}`
    : `${rotulo}: sem valores medidos.`;

  const focado = foco === null ? null : foco < dados.length ? dados[foco] : { estimativa: true };

  return (
    <figure className="grafico" ref={ref}>
      <svg width={largura} height={altura} role="img" aria-labelledby={idDesc} onPointerMove={mover} onPointerLeave={() => setFoco(null)} className="grafico__svg">
        <title id={idDesc}>{descricao}</title>
        <g className="grafico__grade">
          {ticks.map((t) => (
            <g key={t}>
              <line x1={MARGEM.esquerda} x2={largura - MARGEM.direita} y1={y(t)} y2={y(t)} />
              <text x={MARGEM.esquerda - 10} y={y(t)} dy="0.32em" textAnchor="end">
                {formatoEixo(t)}
              </text>
            </g>
          ))}
        </g>
        <g className="grafico__eixo-x">
          {dados.map((d, i) =>
            rotuloEixoX(i) ? (
              <text key={i} x={x(i)} y={altura - 10} textAnchor="middle">
                {comoDiaMes(d.periodo.data_inicio)}
              </text>
            ) : null,
          )}
          {estimativa && (
            <text x={xEst} y={altura - 10} textAnchor="middle" className="grafico__rotulo-est">
              próximo
            </text>
          )}
        </g>
        {dados.map((d, i) =>
          d.v === null ? <rect key={`l${i}`} className="grafico__lacuna" x={x(i) - passo / 2 + 4} y={MARGEM.topo} width={Math.max(passo - 8, 4)} height={altura - MARGEM.topo - MARGEM.base} /> : null,
        )}
        {trechos.map((t, i) =>
          t.length > 1 ? <polygon key={`a${i}`} className="grafico__area" points={[...t, [t[t.length - 1][0], altura - MARGEM.base], [t[0][0], altura - MARGEM.base]].map((p) => p.join(",")).join(" ")} /> : null,
        )}
        {focado && <line className="grafico__mira" x1={x(foco)} x2={x(foco)} y1={MARGEM.topo} y2={altura - MARGEM.base} />}
        {trechos.map((t, i) => (
          <polyline key={i} className="grafico__linha" points={t.map((p) => p.join(",")).join(" ")} />
        ))}
        {estimativa && ultimo && <line className="grafico__linha-est" x1={x(ultimoIdx)} y1={y(ultimo.v)} x2={xEst} y2={yEst} />}
        {dados.map((d, i) =>
          d.v === null ? null : i === ultimoIdx && destacarUltimo ? (
            <rect key={i} className="grafico__estacao grafico__estacao--atual" x={x(i) - 8} y={y(d.v) - 8} width={16} height={16} rx={3} />
          ) : (
            <circle key={i} className="grafico__estacao" cx={x(i)} cy={y(d.v)} r={foco === i ? 5.5 : 3.5} />
          ),
        )}
        {estimativa && <circle className="grafico__estacao-est" cx={xEst} cy={yEst} r={7} />}
        {ultimo && destacarUltimo && (
          <text className="grafico__valor-atual" x={x(ultimoIdx) - (estimativa ? 0 : 14)} y={dados[ultimoIdx - 1]?.v != null && dados[ultimoIdx - 1].v > ultimo.v ? Math.min(y(ultimo.v) + 28, altura - MARGEM.base - 6) : y(ultimo.v) - 16} textAnchor={estimativa ? "middle" : "end"}>
            {formatoEixo(ultimo.v)}
          </text>
        )}
        {estimativa && (
          <text className="grafico__valor-est" x={Math.min(xEst, largura - 26)} y={estimativaSobe ? yEst - 16 : Math.min(yEst + 26, altura - MARGEM.base - 6)} textAnchor="middle">
            {formatoEixo(estimativa.valor)}
          </text>
        )}
      </svg>
      {focado && (
        <div className="grafico__dica" style={{ left: Math.min(Math.max(x(foco), 90), largura - 90) }} aria-hidden="true">
          {focado.estimativa ? (
            <>
              <strong>Próximo período · estimativa</strong>
              <span>{formatoValor(estimativa.valor)}</span>
            </>
          ) : (
            <>
              <strong>{comoPeriodo(focado.periodo)}</strong>
              <span>{focado.v === null ? "Sem medição neste período" : formatoValor(focado.v)}</span>
              {focado.bruto.pedidos !== undefined && focado.v !== null && <span>{comoInteiro(focado.bruto.pedidos)} pedidos</span>}
            </>
          )}
        </div>
      )}
      {(estimativa || temLacuna) && (
        <figcaption className="grafico__legenda">
          <span className="legenda legenda--medido">
            <svg width="28" height="12" aria-hidden="true">
              <line x1="2" y1="6" x2="26" y2="6" />
              <circle cx="14" cy="6" r="3.5" />
            </svg>
            medido
          </span>
          {estimativa && (
            <span className="legenda legenda--estimativa">
              <svg width="28" height="12" aria-hidden="true">
                <line x1="2" y1="6" x2="26" y2="6" />
                <circle cx="14" cy="6" r="4" />
              </svg>
              {estimativa.rotulo ?? "estimativa do modelo para o próximo período"}
            </span>
          )}
          {temLacuna && <span className="legenda legenda--lacuna">A linha se interrompe onde não houve medição no período.</span>}
        </figcaption>
      )}
    </figure>
  );
}
