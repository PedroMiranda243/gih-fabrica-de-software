/**
 * Como um número aparece. A cor nunca é o único sinal: variação tem seta e sinal,
 * segmento tem o nome ao lado do ponto, estimativa tem etiqueta. Nulo é travessão
 * com um texto para leitor de tela dizendo por quê.
 */
import { comoDelta, comoDinheiro, comoProbabilidade, comoVariacao, partesDoDinheiro, ROTULO_SEGMENTO, sentidoDa, TRACO } from "../formato";
import Icone from "./Icone";

/** Travessão com a razão para leitor de tela. */
export function Ausente({ porque = "sem valor" }) {
  return (
    <span className="ausente">
      <span aria-hidden="true">{TRACO}</span>
      <span className="sr-only">{porque}</span>
    </span>
  );
}

/**
 * Variação em %, com seta e sinal. `ruimQuandoSobe` inverte só a cor (o "Em risco"
 * que sobe é ruim); a seta e o sinal continuam dizendo a direção.
 */
export function Variacao({ valor, ruimQuandoSobe = false, semBase = "Sem base de comparação neste período", compacta = false }) {
  const sentido = sentidoDa(valor);
  if (sentido === "indefinida") {
    return (
      <span className="variacao variacao--indefinida">
        <span aria-hidden="true">{TRACO}</span>
        <span className="sr-only">{semBase}</span>
      </span>
    );
  }
  const tom = sentido === "estavel" ? "estavel" : (sentido === "sobe") !== ruimQuandoSobe ? "boa" : "ruim";
  return (
    <span className={`variacao variacao--${tom}${compacta ? " variacao--compacta" : ""}`}>
      {sentido !== "estavel" && <Icone nome={sentido === "sobe" ? "sobe" : "cai"} />}
      <span>{sentido === "estavel" ? "estável" : comoVariacao(valor)}</span>
      {sentido === "estavel" && <span className="sr-only"> (mediu e não mudou)</span>}
    </span>
  );
}

/** Diferença de contagem ("8 a mais"), com seta. */
export function Delta({ valor, ruimQuandoSobe = false, semBase = "Sem período anterior segmentado para comparar" }) {
  if (valor === null || valor === undefined) {
    return (
      <span className="variacao variacao--indefinida">
        <span aria-hidden="true">{TRACO}</span>
        <span className="sr-only">{semBase}</span>
      </span>
    );
  }
  const n = Number(valor);
  const tom = n === 0 ? "estavel" : (n > 0) !== ruimQuandoSobe ? "boa" : "ruim";
  return (
    <span className={`variacao variacao--${tom}`}>
      {n !== 0 && <Icone nome={n > 0 ? "sobe" : "cai"} />}
      <span>{comoDelta(n)}</span>
    </span>
  );
}

/** O segmento: ponto da cor dele e o nome, sempre. */
export function Segmento({ codigo, semRotulo = false }) {
  if (!codigo) return <Ausente porque="Segmentação ainda não calculada para este período" />;
  return (
    <span className={`segmento segmento--${codigo.toLowerCase().replace(/_/g, "-")}${semRotulo ? "" : " segmento--etiqueta"}`}>
      <span className="segmento__ponto" aria-hidden="true" />
      <span className={semRotulo ? "sr-only" : "segmento__nome"}>{ROTULO_SEGMENTO[codigo] ?? codigo}</span>
    </span>
  );
}

/** A etiqueta que marca estimativa (modelo), separada de medição. */
export function Estimativa({ children = "Estimativa" }) {
  return (
    <span className="etiqueta-estimativa">
      <Icone nome="estimativa" />
      {children}
    </span>
  );
}

/** Dinheiro para leitura de painel: inteiros grandes e centavos menores. */
export function Dinheiro({ valor, grande = false, porque }) {
  const partes = partesDoDinheiro(valor);
  if (!partes) return <Ausente porque={porque} />;
  if (!grande) return <span className="dinheiro">{comoDinheiro(valor)}</span>;
  return (
    <span className="dinheiro dinheiro--grande">
      <span className="sr-only">{comoDinheiro(valor)}</span>
      <span className="dinheiro__moeda" aria-hidden="true">
        {partes.sinal}R$
      </span>
      <span className="dinheiro__inteiros" aria-hidden="true">
        {partes.inteiros}
      </span>
      <span className="dinheiro__centavos" aria-hidden="true">
        ,{partes.centavos}
      </span>
    </span>
  );
}

/** Chance estimada, sem fingir certeza. */
export function Chance({ valor, porque = "Sem previsão na versão em uso do modelo" }) {
  if (valor === null || valor === undefined) return <Ausente porque={porque} />;
  return <span className="chance">{comoProbabilidade(valor)}</span>;
}
