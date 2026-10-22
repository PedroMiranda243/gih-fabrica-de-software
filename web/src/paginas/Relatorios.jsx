/** A lista dos relatórios: só o que o perfil abre, cada um com o que responde. */
import { Link } from "react-router-dom";

import { tem, useSessao } from "../api/sessao";
import { Vazio } from "../componentes/Estados";
import Icone from "../componentes/Icone";
import { useTitulo } from "../componentes/Titulo";

const RELATORIOS = [
  { nome: "Desempenho por período", para: "/relatorios/desempenho", exige: "relatorios", icone: "painel", responde: "Como a rede foi num período, por categoria e por segmento: faturamento, pedidos, ticket médio e variação." },
  { nome: "Parceiros em risco", para: "/relatorios/risco", exige: "relatorios", icone: "atencao", responde: "Quem o modelo prevê que caia: o medido, o previsto, a chance de queda e a ação no último plano.", estimativa: true },
  { nome: "Campanha", para: "/relatorios/campanha", exige: "relatorios", icone: "campanha", responde: "Onde a verba de um plano foi, por ação, por categoria e por segmento, e o ganho que se espera dela." },
  { nome: "Operações do sistema", para: "/relatorios/operacoes", exige: "relatorio_operacoes", icone: "operacoes", responde: "O que foi feito num intervalo de datas, por tipo de ação, por pessoa e por dia." },
];

export default function Relatorios() {
  useTitulo("Relatórios");
  const { usuario } = useSessao();
  const visiveis = RELATORIOS.filter((r) => tem(usuario, r.exige));
  return (
    <div className="pagina">
      <p className="pagina__intro">Relatórios — cada um com CSV e impressão em PDF.</p>
      {!visiveis.length ? (
        <Vazio titulo="Nenhum relatório para o seu perfil" icone="relatorios">
          Os relatórios da rede são do Gestor e do Analista; o de operações, do Administrador.
        </Vazio>
      ) : (
        <ul className="relatorios">
          {visiveis.map((r) => (
            <li key={r.para} className="relatorio-item">
              <Icone nome={r.icone} className="relatorio-item__icone" />
              <div className="relatorio-item__texto">
                <h2 className="relatorio-item__nome">{r.nome}</h2>
                <p>{r.responde}</p>
              </div>
              <Link to={r.para} className="botao botao--secundario" aria-label={`Abrir o relatório ${r.nome}`}>
                Abrir <Icone nome="seta-direita" />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
