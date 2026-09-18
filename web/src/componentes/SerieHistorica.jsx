/**
 * Série histórica em SVG, desenhada à mão.
 *
 * **Sem biblioteca de gráfico, e por decisão registrada.** São no máximo 52
 * pontos (RNF04), bem abaixo do limite em que SVG deixa de servir. Recharts ou
 * Chart.js trariam um sistema de temas inteiro para brigar com o nosso, e a
 * rampa fria do `docs/09` é o que precisa mandar na cor.
 *
 * **A lacuna é desenhada como lacuna.** A API devolve o ponto com os três
 * valores nulos quando não houve medição naquele período, e a linha se
 * interrompe ali. Ligar os vizinhos desenharia uma tendência que ninguém
 * mediu — é o mesmo erro que omitir o ponto cometeria, e o motivo de a API se
 * dar ao trabalho de devolvê-lo.
 */
import { useId, useMemo, useState } from "react";

import { comoDiaMes, comoDinheiro, comoInteiro, comoPeriodo } from "../formato";

const LARGURA = 720;
const ALTURA = 220;
/* Sobra à direita para o rótulo do último ponto caber dentro do `viewBox`.
   Rótulo cortado na borda é o defeito mais comum de gráfico em SVG. */
const MARGEM = { topo: 16, direita: 64, baixo: 28, esquerda: 60 };

const AREA = {
  largura: LARGURA - MARGEM.esquerda - MARGEM.direita,
  altura: ALTURA - MARGEM.topo - MARGEM.baixo,
};

/** Um teto "redondo" acima do máximo, para a grade cair em número legível. */
function tetoBonito(maximo) {
  if (maximo <= 0) return 1;
  const magnitude = 10 ** Math.floor(Math.log10(maximo));
  return Math.ceil(maximo / magnitude) * magnitude;
}

/** Quebra a série em trechos contínuos — cada buraco separa dois trechos. */
function trechosContinuos(coordenadas) {
  const trechos = [];
  let atual = [];
  coordenadas.forEach((ponto) => {
    if (ponto.vazio) {
      if (atual.length) trechos.push(atual);
      atual = [];
    } else {
      atual.push(ponto);
    }
  });
  if (atual.length) trechos.push(atual);
  return trechos;
}

export default function SerieHistorica({ pontos, rotulo = "Faturamento" }) {
  const [emFoco, setEmFoco] = useState(null);
  const [mostrarTabela, setMostrarTabela] = useState(false);
  const idArea = useId();

  const { coordenadas, teto, temLacuna } = useMemo(() => {
    const valores = pontos
      .map((p) => (p.faturamento === null ? null : Number(p.faturamento)))
      .filter((v) => v !== null);
    const limite = tetoBonito(Math.max(...valores, 0));
    const passo = pontos.length > 1 ? AREA.largura / (pontos.length - 1) : 0;

    const coords = pontos.map((ponto, i) => {
      const valor = ponto.faturamento === null ? null : Number(ponto.faturamento);
      return {
        ponto,
        indice: i,
        valor,
        vazio: valor === null,
        x: MARGEM.esquerda + (pontos.length > 1 ? passo * i : AREA.largura / 2),
        y: valor === null ? null : MARGEM.topo + AREA.altura * (1 - valor / limite),
      };
    });

    return {
      coordenadas: coords,
      teto: limite,
      temLacuna: coords.some((c) => c.vazio),
    };
  }, [pontos]);

  const trechos = trechosContinuos(coordenadas);
  const ultimo = [...coordenadas].reverse().find((c) => !c.vazio);

  /* O mouse chega em pixels da tela; o desenho vive no sistema do `viewBox`.
     Converter pela largura real é o que faz a cruz acompanhar o cursor em
     qualquer tamanho de janela. */
  function aoMover(evento) {
    const caixa = evento.currentTarget.getBoundingClientRect();
    const xNoDesenho = ((evento.clientX - caixa.left) / caixa.width) * LARGURA;
    const maisPerto = coordenadas.reduce((melhor, atual) =>
      Math.abs(atual.x - xNoDesenho) < Math.abs(melhor.x - xNoDesenho) ? atual : melhor,
    );
    setEmFoco(maisPerto);
  }

  const linhasDeGrade = [0, 0.25, 0.5, 0.75, 1];

  return (
    <div className="grafico__moldura">
      <svg
        className="grafico"
        viewBox={`0 0 ${LARGURA} ${ALTURA}`}
        preserveAspectRatio="xMidYMid meet"
        role="img"
        aria-label={`${rotulo} por período. ${pontos.length} períodos.`}
        onMouseMove={aoMover}
        onMouseLeave={() => setEmFoco(null)}
      >
        <defs>
          <linearGradient id={idArea} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--serie-1)" stopOpacity="0.22" />
            <stop offset="100%" stopColor="var(--serie-1)" stopOpacity="0.02" />
          </linearGradient>
        </defs>

        {/* Grade recessiva: existe para ser ignorada. A linha é que fala. */}
        {linhasDeGrade.map((fracao) => {
          const y = MARGEM.topo + AREA.altura * fracao;
          return (
            <g key={fracao}>
              <line
                className="grafico__grade"
                x1={MARGEM.esquerda}
                y1={y}
                x2={LARGURA - MARGEM.direita}
                y2={y}
              />
              <text className="grafico__eixo" x={MARGEM.esquerda - 8} y={y + 3} textAnchor="end">
                {comoDinheiro(teto * (1 - fracao), { compacto: true })}
              </text>
            </g>
          );
        })}

        {/* Uma área e uma linha por trecho contínuo. */}
        {trechos.map((trecho) => {
          const chave = `t${trecho[0].indice}`;
          const d = trecho.map((c, i) => `${i ? "L" : "M"}${c.x} ${c.y}`).join(" ");
          const base = MARGEM.topo + AREA.altura;
          return (
            <g key={chave}>
              {trecho.length > 1 && (
                <path
                  className="grafico__area"
                  fill={`url(#${idArea})`}
                  d={`${d} L${trecho[trecho.length - 1].x} ${base} L${trecho[0].x} ${base} Z`}
                />
              )}
              <path className="grafico__linha" d={d} />
            </g>
          );
        })}

        {/* Trecho de um ponto só não desenha linha nenhuma — sem o marcador ele
            sumiria do gráfico, e o período existiu. */}
        {coordenadas
          .filter((c) => !c.vazio)
          .map((c) => (
            <circle
              key={c.indice}
              className="grafico__ponto"
              cx={c.x}
              cy={c.y}
              r={emFoco?.indice === c.indice ? 5 : 3.5}
            />
          ))}

        {emFoco && (
          <line
            className="grafico__cruz"
            x1={emFoco.x}
            y1={MARGEM.topo}
            x2={emFoco.x}
            y2={MARGEM.topo + AREA.altura}
          />
        )}

        {/* Rótulo direto **só no último ponto**. Número sobre cada marca vira
            ruído e some dentro do próprio gráfico. */}
        {ultimo && (
          <text className="grafico__rotulo-final" x={ultimo.x + 10} y={ultimo.y + 4}>
            {comoDinheiro(ultimo.valor, { compacto: true })}
          </text>
        )}

        {/* Primeiro e último no eixo: rótulo em cada período embolaria com 52
            deles, e a data exata fica no tooltip. */}
        {coordenadas.length > 0 && (
          <>
            <text
              className="grafico__eixo"
              x={coordenadas[0].x}
              y={ALTURA - 8}
              textAnchor="start"
            >
              {comoDiaMes(coordenadas[0].ponto.periodo.data_inicio)}
            </text>
            <text
              className="grafico__eixo"
              x={coordenadas[coordenadas.length - 1].x}
              y={ALTURA - 8}
              textAnchor="end"
            >
              {comoDiaMes(coordenadas[coordenadas.length - 1].ponto.periodo.data_inicio)}
            </text>
          </>
        )}
      </svg>

      {emFoco && (
        <div
          className="grafico__dica"
          style={{
            left: `calc(${(emFoco.x / LARGURA) * 100}% + 12px)`,
            top: "var(--esp-16)",
          }}
        >
          <div style={{ fontWeight: 600 }}>{comoPeriodo(emFoco.ponto.periodo)}</div>
          <div className="num">
            {emFoco.vazio ? "sem medição neste período" : comoDinheiro(emFoco.valor)}
          </div>
          {!emFoco.vazio && (
            <div className="num" style={{ color: "var(--ink-2)" }}>
              {comoInteiro(emFoco.ponto.pedidos)} pedidos
            </div>
          )}
        </div>
      )}

      {temLacuna && (
        <p className="grafico__legenda-lacuna">
          A linha se interrompe onde não houve medição no período.
        </p>
      )}

      {/* Tabela alternativa: é o recurso de acessibilidade que série temporal
          pede, e serve também a quem prefere o número ao desenho. */}
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
            <caption className="so-leitor">{rotulo} por período</caption>
            <thead>
              <tr>
                <th scope="col">Período</th>
                <th scope="col" className="numerica">
                  Faturamento
                </th>
                <th scope="col" className="numerica">
                  Pedidos
                </th>
              </tr>
            </thead>
            <tbody>
              {pontos.map((p) => (
                <tr key={p.periodo.id ?? p.periodo.data_inicio}>
                  <td>{comoPeriodo(p.periodo)}</td>
                  <td className="numerica">
                    {p.faturamento === null ? "sem medição" : comoDinheiro(p.faturamento)}
                  </td>
                  <td className="numerica">{comoInteiro(p.pedidos)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
