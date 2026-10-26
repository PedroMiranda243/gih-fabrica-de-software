/**
 * Série histórica com a tabela dos números a um clique — o mesmo componente no
 * painel, no cadastro do parceiro e no portal do parceiro.
 */
import GraficoSerie from "../graficos/GraficoSerie";
import VerNumeros from "../graficos/VerNumeros";
import { comoDinheiro, comoInteiro, comoPeriodo } from "../formato";
import { Ausente } from "./Dados";
import { Vazio } from "./Estados";

export default function Serie({ pontos, rotulo, estimativa = null, altura = 280, vazio }) {
  if (!pontos?.length || pontos.length < 2) {
    return (
      vazio ?? (
        <Vazio titulo="Sem série para mostrar" compacto icone="painel">
          A série aparece quando houver mais de um período importado.
        </Vazio>
      )
    );
  }
  const linhas = pontos.map((p) => [
    comoPeriodo(p.periodo),
    p.faturamento === null ? <Ausente key="faturamento" porque="sem medição no período" /> : comoDinheiro(p.faturamento),
    p.pedidos === null || p.pedidos === undefined ? <Ausente key="pedidos" porque="sem medição no período" /> : comoInteiro(p.pedidos),
  ]);
  if (estimativa) linhas.push([`Próximo período (estimativa do modelo)`, comoDinheiro(estimativa.valor), <Ausente key="e" porque="o modelo não estima pedidos" />]);
  return (
    <VerNumeros
      legenda={`${rotulo}, período a período`}
      colunas={[{ rotulo: "Período", num: false }, { rotulo: "Faturamento" }, { rotulo: "Pedidos" }]}
      linhas={linhas}
    >
      <GraficoSerie pontos={pontos} rotulo={rotulo} estimativa={estimativa} altura={altura} />
    </VerNumeros>
  );
}
