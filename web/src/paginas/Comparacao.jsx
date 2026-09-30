/**
 * Dois planos lado a lado — RF35, UC08-A3, história H59.
 *
 * O gestor calcula um plano, muda um parâmetro e quer ver **o que mudou por causa
 * disso**. A página responde de cima para baixo, do resumo ao detalhe:
 *
 * 1. os parâmetros dos dois, com os que mudaram marcados;
 * 2. o resultado de cada um e a diferença do segundo para o primeiro;
 * 3. os parceiros que mudaram de ação ou que só estão num dos planos — os iguais
 *    ficam a um clique, porque são quase sempre a maioria e não dizem nada novo.
 *
 * **Quem decide o que mudou é a API** (regra 2.4): a comparação chega pronta, com
 * os campos diferentes, a diferença e o caso de cada parceiro. A tela só desenha.
 *
 * O endereço (`?a=&b=`) é o que o histórico monta, e é o que se manda a alguém.
 */
import { useEffect, useState } from "react";
import { Link, useLocation, useSearchParams } from "react-router-dom";

import { api } from "../api/cliente";
import { Esqueleto } from "../componentes/Carregando";
import EstadoVazio from "../componentes/EstadoVazio";
import Segmento from "../componentes/Segmento";
import { useTituloDaAba } from "../componentes/tituloDaAba";
import {
  comoDataHora,
  comoDinheiro,
  comoFracao,
  comoInteiro,
  comoPercentual,
  cotasDoPedido,
  ROTULO_MODO,
  TRACO,
} from "../formato";
import "../estilos/execucoes.css";

const PARAMETROS = [
  ["orcamento", "Orçamento", (p) => comoDinheiro(p.orcamento)],
  ["maximo_acoes", "Máximo de ações", (p) => comoInteiro(p.maximo_acoes)],
  [
    "cota_cauda_longa",
    "Cauda longa",
    (p) => (p.cota_cauda_longa ? `ao menos ${comoFracao(p.cota_cauda_longa, 0)} das ações` : TRACO),
  ],
  ["cotas_categoria", "Cotas por categoria", (p, e) => cotasDoPedido(e).join(" · ") || TRACO],
  ["aplicacao_inicio", "Início da aplicação", (p) => p.aplicacao_inicio.split("-").reverse().join("/")],
  ["aplicacao_fim", "Fim da aplicação", (p) => p.aplicacao_fim.split("-").reverse().join("/")],
  ["modo", "Modo pedido", (p) => (p.modo ? ROTULO_MODO[p.modo] : "Automático")],
];

const SITUACAO = {
  MUDOU: "mudou de ação",
  SO_A: "só no plano A",
  SO_B: "só no plano B",
  IGUAL: "igual",
};

export default function Comparacao() {
  const [parametros] = useSearchParams();
  const a = parametros.get("a");
  const b = parametros.get("b");
  const chave = `${a}-${b}`;
  const [estado, setEstado] = useState({ chave: null, dados: null, erro: null });

  useEffect(() => {
    if (!a || !b) return undefined;
    let vivo = true;
    api
      .get("/api/otimizacoes/comparacao", { a, b })
      .then((dados) => vivo && setEstado({ chave, dados, erro: null }))
      .catch((erro) => vivo && setEstado({ chave, dados: null, erro }));
    return () => {
      vivo = false;
    };
  }, [a, b, chave]);
  useTituloDaAba("Comparação");

  const atual = estado.chave === chave;
  const comparacao = atual ? estado.dados : null;
  const erro = atual ? estado.erro : null;

  const trilha = (
    <nav className="trilha" aria-label="Você está em">
      <Link to="/execucoes">Execuções</Link>
      <span aria-hidden="true">›</span>
      <span aria-current="page">Comparação</span>
    </nav>
  );

  if (!a || !b || erro?.status === 404) {
    return (
      <>
        {trilha}
        <EstadoVazio
          titulo={!a || !b ? "Escolha dois planos para comparar" : "Plano não encontrado"}
          texto="No histórico das execuções, marque dois planos calculados e peça a comparação."
          acao={{ para: "/execucoes", rotulo: "Ir para as execuções" }}
        />
      </>
    );
  }

  return (
    <>
      {trilha}

      {erro && (
        <div className="aviso" role="alert">
          <p className="aviso__titulo">{erro.message}</p>
          {erro.ajuda && <p className="aviso__ajuda">{erro.ajuda}</p>}
        </div>
      )}

      {!comparacao && !erro && (
        <section className="painel" aria-busy="true" aria-label="Carregando a comparação">
          <div className="execucoes__corpo">
            <Esqueleto altura={260} />
          </div>
        </section>
      )}

      {comparacao && <Lado comparacao={comparacao} />}
    </>
  );
}

function Lado({ comparacao: c }) {
  return (
    <>
      {!c.mesmas_previsoes && (
        <div className="aviso aviso--informativo">
          <p className="aviso__titulo">Os dois planos partiram de previsões diferentes.</p>
          <p className="aviso__ajuda">
            O plano A usou a {c.a.modelo_versao} e o plano B, a {c.b.modelo_versao}, ou períodos
            diferentes. O ganho de um mesmo parceiro pode ter mudado por causa da previsão, e não dos
            parâmetros.
          </p>
        </div>
      )}
      <Parametros comparacao={c} />
      <Resultado comparacao={c} />
      <Parceiros comparacao={c} />
    </>
  );
}

function CabecalhoDosPlanos({ a, b }) {
  return (
    <>
      <th scope="col">
        Plano A
        <span className="comparacao__quando">
          {comoDataHora(a.iniciada_em)}
          {a.autor ? `, ${a.autor}` : ""}
        </span>
      </th>
      <th scope="col">
        Plano B
        <span className="comparacao__quando">
          {comoDataHora(b.iniciada_em)}
          {b.autor ? `, ${b.autor}` : ""}
        </span>
      </th>
    </>
  );
}

function Parametros({ comparacao: c }) {
  const mudaram = new Set(c.parametros_diferentes);
  return (
    <section className="painel" aria-labelledby="titulo-parametros">
      <div className="painel__cabecalho">
        <h2 className="painel__titulo" id="titulo-parametros">
          O que foi pedido
        </h2>
        <span className="painel__nota">
          {mudaram.size
            ? `${mudaram.size} ${mudaram.size === 1 ? "parâmetro mudou" : "parâmetros mudaram"}`
            : "Os mesmos parâmetros"}
        </span>
      </div>
      <div className="tabela-rolagem">
        <table className="tabela comparacao__tabela">
          <caption className="so-leitor">Os parâmetros dos dois planos</caption>
          <thead>
            <tr>
              <th scope="col">Parâmetro</th>
              <CabecalhoDosPlanos a={c.a} b={c.b} />
            </tr>
          </thead>
          <tbody>
            {PARAMETROS.map(([campo, rotulo, valor]) => {
              const mudou = mudaram.has(campo);
              return (
                <tr key={campo} className={mudou ? "comparacao__mudou" : undefined}>
                  <th scope="row">
                    {rotulo}
                    {mudou && <span className="comparacao__marca">mudou</span>}
                  </th>
                  <td>{valor(c.a.parametros, c.a)}</td>
                  <td>{valor(c.b.parametros, c.b)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

/* A diferença com sinal, e a variação em porcentagem quando a base não é zero. */
function diferenca(valor, base, formatar) {
  const n = Number(valor);
  if (n === 0) return "igual";
  const sinal = n > 0 ? "+" : "−";
  const texto = `${sinal}${formatar(Math.abs(n))}`;
  const b = Number(base);
  return b ? `${texto} (${comoPercentual((n / b) * 100)})` : texto;
}

function Resultado({ comparacao: c }) {
  const linhas = [
    [
      "Ganho esperado",
      comoDinheiro(c.a.uplift_total),
      comoDinheiro(c.b.uplift_total),
      diferenca(c.diferenca_uplift, c.a.uplift_total, comoDinheiro),
    ],
    [
      "Custo",
      comoDinheiro(c.a.custo_total),
      comoDinheiro(c.b.custo_total),
      diferenca(c.diferenca_custo, c.a.custo_total, comoDinheiro),
    ],
    ["Ações", comoInteiro(c.a.acoes), comoInteiro(c.b.acoes), diferenca(c.diferenca_acoes, null, comoInteiro)],
  ];
  return (
    <section className="painel" aria-labelledby="titulo-resultado">
      <div className="painel__cabecalho">
        <h2 className="painel__titulo" id="titulo-resultado">
          O que saiu
        </h2>
        <span className="painel__nota">A diferença é do plano B para o plano A</span>
      </div>
      <div className="tabela-rolagem">
        <table className="tabela comparacao__tabela">
          <caption className="so-leitor">O resultado dos dois planos e a diferença</caption>
          <thead>
            <tr>
              <th scope="col">Medida</th>
              <CabecalhoDosPlanos a={c.a} b={c.b} />
              <th scope="col" className="numerica">
                Diferença
              </th>
            </tr>
          </thead>
          <tbody>
            {linhas.map(([rotulo, va, vb, dif]) => (
              <tr key={rotulo}>
                <th scope="row">{rotulo}</th>
                <td className="num">{va}</td>
                <td className="num">{vb}</td>
                <td className="numerica comparacao__diferenca">{dif}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Parceiros({ comparacao: c }) {
  /* O parceiro aberto daqui volta para a comparação, e não para a lista (H81). */
  const lugar = useLocation();
  const [comIguais, setComIguais] = useState(false);
  const { mudaram, so_a: soA, so_b: soB, iguais } = c.resumo;
  const visiveis = comIguais ? c.itens : c.itens.filter((i) => i.situacao !== "IGUAL");
  return (
    <section className="painel" aria-labelledby="titulo-parceiros">
      <div className="painel__cabecalho">
        <h2 className="painel__titulo" id="titulo-parceiros">
          Parceiro a parceiro
        </h2>
        <span className="painel__nota">
          {comoInteiro(mudaram)} {mudaram === 1 ? "mudou" : "mudaram"} de ação · {comoInteiro(soA)} só no A ·{" "}
          {comoInteiro(soB)} só no B · {comoInteiro(iguais)} {iguais === 1 ? "igual" : "iguais"}
        </span>
      </div>

      {visiveis.length === 0 ? (
        <EstadoVazio
          titulo="Os dois planos dão a mesma ação aos mesmos parceiros."
          texto="Os parâmetros que mudaram não mudaram o plano."
        />
      ) : (
        <div className="tabela-rolagem">
          <table className="tabela comparacao__tabela">
            <caption className="so-leitor">Os parceiros dos dois planos, com o que mudou</caption>
            <thead>
              <tr>
                <th scope="col">Parceiro</th>
                <th scope="col">Segmento</th>
                <th scope="col">Plano A</th>
                <th scope="col">Plano B</th>
                <th scope="col">O que mudou</th>
              </tr>
            </thead>
            <tbody>
              {visiveis.map((i) => (
                <tr key={i.parceiro_id}>
                  <td className="nome">
                    <Link
                      className="nome__link"
                      to={`/parceiros/${i.parceiro_id}`}
                      state={{
                        lista: lugar.pathname + lugar.search,
                        rotuloLista: "Comparação",
                        voltarPara: "Voltar para a comparação",
                      }}
                    >
                      {i.parceiro}
                    </Link>
                  </td>
                  <td>
                    <Segmento valor={i.segmento} />
                  </td>
                  <td>
                    <Acao acao={i.acao_a} ganho={i.ganho_a} />
                  </td>
                  <td>
                    <Acao acao={i.acao_b} ganho={i.ganho_b} />
                  </td>
                  <td className="secundaria">{SITUACAO[i.situacao]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {iguais > 0 && (
        <div className="execucoes__corpo">
          <button
            type="button"
            className="botao botao--secundario"
            aria-expanded={comIguais}
            onClick={() => setComIguais((v) => !v)}
          >
            {comIguais
              ? "Esconder os que ficaram iguais"
              : iguais === 1
                ? "Mostrar também o que ficou igual"
                : `Mostrar também os ${comoInteiro(iguais)} que ficaram iguais`}
          </button>
        </div>
      )}
    </section>
  );
}

function Acao({ acao, ganho }) {
  if (!acao) return <span className="secundaria">sem ação</span>;
  return (
    <>
      {acao}
      <span className="execucoes__detalhe num">ganho de {comoDinheiro(ganho)}</span>
    </>
  );
}
