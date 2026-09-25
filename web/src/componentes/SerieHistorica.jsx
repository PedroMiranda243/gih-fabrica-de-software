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
 *
 * **A estimativa se distingue do medido por mais que a cor** (H44). Com
 * `previsao`, a série ganha um período a mais: o trecho até ele é tracejado, o
 * marcador é vazado, e a legenda diz qual é qual. Cor diferente sozinha não
 * bastaria — quem não a distingue leria a previsão como medição.
 */
import { useId, useMemo, useState } from "react";

import { comoDiaMes, comoDinheiro, comoInteiro, comoPeriodo } from "../formato";
import {
  ALTURA,
  AREA,
  FOLGA_EIXO,
  FOLGA_ROTULO_FINAL,
  FRACOES_DA_GRADE,
  LARGURA,
  MARGEM,
  rotuloCompacto,
  tetoBonito,
} from "./escalaSerie";

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

export default function SerieHistorica({ pontos, rotulo = "Faturamento", previsao = null }) {
  const [emFoco, setEmFoco] = useState(null);
  const [mostrarTabela, setMostrarTabela] = useState(false);
  const idArea = useId();

  const { coordenadas, teto, temLacuna, prevista } = useMemo(() => {
    const valores = pontos
      .map((p) => (p.faturamento === null ? null : Number(p.faturamento)))
      .filter((v) => v !== null);
    const valorPrevisto = previsao ? Number(previsao.valor) : null;
    if (valorPrevisto !== null) valores.push(valorPrevisto);
    const limite = tetoBonito(Math.max(...valores, 0));
    // A estimativa ocupa um período a mais, à direita do último medido.
    const posicoes = pontos.length + (valorPrevisto === null ? 0 : 1);
    const passo = posicoes > 1 ? AREA.largura / (posicoes - 1) : 0;

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
      prevista:
        valorPrevisto === null
          ? null
          : {
              indice: pontos.length,
              valor: valorPrevisto,
              previsto: true,
              x: MARGEM.esquerda + passo * (posicoes - 1),
              y: MARGEM.topo + AREA.altura * (1 - valorPrevisto / limite),
            },
    };
  }, [pontos, previsao]);

  const trechos = trechosContinuos(coordenadas);
  const ultimo = [...coordenadas].reverse().find((c) => !c.vazio);

  /* O mouse chega em pixels da tela; o desenho vive no sistema do `viewBox`.
     Converter pela largura real é o que faz a cruz acompanhar o cursor em
     qualquer tamanho de janela. */
  function aoMover(evento) {
    const caixa = evento.currentTarget.getBoundingClientRect();
    const xNoDesenho = ((evento.clientX - caixa.left) / caixa.width) * LARGURA;
    const alvos = prevista ? [...coordenadas, prevista] : coordenadas;
    const maisPerto = alvos.reduce((melhor, atual) =>
      Math.abs(atual.x - xNoDesenho) < Math.abs(melhor.x - xNoDesenho) ? atual : melhor,
    );
    setEmFoco(maisPerto);
  }


  return (
    <div className="grafico__moldura">
      <svg
        className="grafico"
        viewBox={`0 0 ${LARGURA} ${ALTURA}`}
        preserveAspectRatio="xMidYMid meet"
        role="img"
        aria-label={`${rotulo} por período. ${pontos.length} períodos${
          prevista ? ", e a estimativa do próximo" : ""
        }.`}
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
        {FRACOES_DA_GRADE.map((fracao) => {
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
              <text
                className="grafico__eixo"
                x={MARGEM.esquerda - FOLGA_EIXO}
                y={y + 3}
                textAnchor="end"
              >
                {rotuloCompacto(teto * (1 - fracao))}
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

        {/* O trecho estimado parte do último ponto medido. Sem ele, a
            estimativa flutuaria solta, sem dizer de onde saiu. */}
        {prevista && ultimo && (
          <>
            <path
              className="grafico__linha grafico__linha--prevista"
              d={`M${ultimo.x} ${ultimo.y} L${prevista.x} ${prevista.y}`}
            />
            <circle
              className="grafico__ponto grafico__ponto--previsto"
              cx={prevista.x}
              cy={prevista.y}
              r={emFoco?.previsto ? 5 : 4}
            />
          </>
        )}

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
        {(prevista ?? ultimo) && (
          <text
            className="grafico__rotulo-final"
            x={(prevista ?? ultimo).x + FOLGA_ROTULO_FINAL}
            y={(prevista ?? ultimo).y + 4}
          >
            {rotuloCompacto((prevista ?? ultimo).valor)}
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
              x={(prevista ?? coordenadas[coordenadas.length - 1]).x}
              y={ALTURA - 8}
              textAnchor="end"
            >
              {prevista
                ? "próximo"
                : comoDiaMes(coordenadas[coordenadas.length - 1].ponto.periodo.data_inicio)}
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
          <div style={{ fontWeight: 600 }}>
            {emFoco.previsto ? "Próximo período" : comoPeriodo(emFoco.ponto.periodo)}
          </div>
          <div className="num">
            {emFoco.vazio ? "sem medição neste período" : comoDinheiro(emFoco.valor)}
          </div>
          {emFoco.previsto && <div style={{ color: "var(--ink-2)" }}>estimativa do modelo</div>}
          {!emFoco.vazio && !emFoco.previsto && (
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

      {prevista && (
        <p className="grafico__legenda-lacuna">
          <svg width="22" height="8" aria-hidden="true">
            <path className="grafico__linha" d="M1 4 H21" />
          </svg>
          medido
          <svg width="22" height="8" aria-hidden="true" style={{ marginLeft: "var(--esp-12)" }}>
            <path className="grafico__linha grafico__linha--prevista" d="M1 4 H21" />
          </svg>
          estimativa do modelo para o próximo período
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
              {prevista && (
                <tr>
                  <td>Próximo período (estimativa)</td>
                  <td className="numerica">{comoDinheiro(prevista.valor)}</td>
                  <td className="numerica">—</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
