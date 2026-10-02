/**
 * Os relatórios do sistema (UC15): a lista, com o que cada um responde.
 *
 * Cada relatório resume o que outra tela mostra — o painel, a previsão, o plano,
 * a trilha —, num formato que se leva para fora: com o recorte escrito, o CSV e
 * a impressão em PDF.
 *
 * A lista mostra só o que o perfil abre, pelas telas que a API manda na sessão,
 * como o menu: os três da rede são do Gestor e do Analista, e o de operações, do
 * Administrador. Esconder não é controle de acesso — a rota recusa de qualquer
 * jeito (regra 2.5).
 */
import { Link } from "react-router-dom";

import { useSessao } from "../api/contextoSessao";
import EstadoVazio from "../componentes/EstadoVazio";
import "../estilos/relatorios.css";

const RELATORIOS = [
  {
    para: "/relatorios/desempenho",
    nome: "Desempenho por período",
    descricao:
      "Como a rede foi num período, por categoria e por segmento: faturamento, pedidos, ticket médio e variação.",
    exige: "relatorios",
  },
  {
    para: "/relatorios/risco",
    nome: "Parceiros em risco",
    descricao:
      "Quem o modelo prevê que caia: o medido, o previsto, a chance de queda e a ação no último plano.",
    exige: "relatorios",
  },
  {
    para: "/relatorios/campanha",
    nome: "Campanha",
    descricao:
      "Onde a verba de um plano foi, por ação, por categoria e por segmento, e o ganho que se espera dela.",
    exige: "relatorios",
  },
  {
    para: "/relatorios/operacoes",
    nome: "Operações do sistema",
    descricao: "O que foi feito num intervalo de datas, por tipo de ação, por pessoa e por dia.",
    exige: "relatorio_operacoes",
  },
];

export default function Relatorios() {
  const { usuario } = useSessao();
  const telas = usuario?.telas ?? [];
  const abertos = RELATORIOS.filter(({ exige }) => telas.includes(exige));

  return (
    <section className="painel" aria-labelledby="titulo-relatorios">
      <div className="painel__cabecalho">
        <h2 className="painel__titulo" id="titulo-relatorios">
          Relatórios
        </h2>
        <span className="painel__nota">cada um com CSV e impressão em PDF</span>
      </div>

      {abertos.length === 0 ? (
        <EstadoVazio
          titulo="Nenhum relatório para o seu perfil"
          texto="Os relatórios da rede são do Gestor e do Analista; o de operações, do Administrador."
        />
      ) : (
        <ul className="relatorios">
          {abertos.map(({ para, nome, descricao }) => (
            <li key={para} className="relatorios__item">
              <div>
                <h3 className="relatorios__nome">{nome}</h3>
                <p className="relatorios__descricao">{descricao}</p>
              </div>
              <Link className="botao botao--secundario" to={para}>
                Abrir <span className="so-leitor">o relatório {nome}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
