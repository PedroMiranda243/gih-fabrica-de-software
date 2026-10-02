/**
 * A ajuda — RF55, UC16, história H95.
 *
 * Quem abria o sistema pela primeira vez encontrava "Em risco", "Estimativa" e
 * "ganho esperado" sem nenhum lugar que dissesse o que são. A ajuda diz, em
 * quatro blocos: o que o perfil de quem lê faz, o que é cada segmento, o que é
 * estimativa e como se chega ao ganho esperado.
 *
 * **Nenhum número de regra está escrito aqui** (regra 2.4). O tamanho do Top,
 * os períodos de tendência e o histórico que o modelo pede vêm de
 * `GET /api/ajuda/regras`, como estão valendo agora — e a ordem dos segmentos
 * também, que é a precedência da RN01. O que a tela escreve é a frase em volta.
 *
 * **"O que você pode fazer" sai das telas que o servidor deu na sessão**, as
 * mesmas do menu: a ajuda não tem uma segunda lista de permissões para
 * discordar da primeira.
 *
 * **O Parceiro lê só a ajuda do portal dele** (RF26, UC16-A1). A sessão dele
 * não traz `ajuda_regras`, e a tela nem pede as regras: os segmentos e os
 * limiares são da operação interna.
 */
import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";

import { api } from "../api/cliente";
import { useSessao } from "../api/contextoSessao";
import { Esqueleto } from "../componentes/Carregando";
import { ROTULO_PERFIL, ROTULO_SEGMENTO } from "../formato";
import "../estilos/ajuda.css";

/* O que cada área deixa fazer. `tem`: as telas que a sustentam, todas; `sem`: a
   capacidade que, presente, troca a frase por outra mais larga. É a mesma
   informação do menu, dita por extenso. */
const AREAS = [
  {
    tem: ["painel"],
    para: "/",
    nome: "Painel",
    texto: "Acompanhar os indicadores da rede, o ranking, a distribuição por segmento e quem entrou ou saiu do Top.",
  },
  {
    tem: ["meu_desempenho"],
    para: "/meu-desempenho",
    nome: "Meu desempenho",
    texto: "Ver o faturamento, os pedidos e o ticket médio do seu comércio, período a período.",
  },
  {
    tem: ["importar"],
    para: "/importacao",
    nome: "Importação",
    texto: "Importar o relatório de um período, conferindo a prévia antes de gravar, e consultar o histórico.",
  },
  {
    tem: ["historico_importacoes"],
    sem: ["importar"],
    para: "/importacao",
    nome: "Importação",
    texto: "Consultar o histórico das importações. Importar não faz parte do seu perfil.",
  },
  {
    tem: ["parceiros"],
    para: "/parceiros",
    nome: "Parceiros",
    texto: "Cadastrar e editar parceiros, filtrar e exportar a lista e, no cadastro, ver o histórico e a previsão de cada um.",
  },
  {
    tem: ["assistente"],
    para: "/assistente",
    nome: "Assistente",
    texto: "Perguntar sobre os dados com as suas palavras. A resposta diz de que período veio, ou diz que não sabe.",
  },
  {
    tem: ["relatorios"],
    para: "/relatorios",
    nome: "Relatórios",
    texto: "Gerar os relatórios de desempenho, de parceiros em risco e da campanha, e exportá-los ou imprimi-los.",
  },
  {
    tem: ["modelo"],
    para: "/modelo",
    nome: "Modelo",
    texto: "Treinar o modelo de previsão e ver as métricas da versão em uso.",
  },
  {
    tem: ["campanha", "calcular_campanha"],
    para: "/campanha",
    nome: "Campanha",
    texto: "Calcular o plano de campanha, com o orçamento e as restrições, e consultar o catálogo de ações.",
  },
  {
    tem: ["campanha"],
    sem: ["calcular_campanha"],
    para: "/campanha",
    nome: "Campanha",
    texto: "Consultar o último plano e o catálogo de ações. Calcular o plano não faz parte do seu perfil.",
  },
  {
    tem: ["execucoes", "execucao"],
    para: "/execucoes",
    nome: "Execuções",
    texto: "Rever os planos já calculados, abrir cada um e comparar dois.",
  },
  {
    tem: ["execucoes"],
    sem: ["execucao"],
    para: "/execucoes",
    nome: "Execuções",
    texto: "Consultar o histórico das execuções do otimizador. Abrir o plano não faz parte do seu perfil.",
  },
  {
    tem: ["benchmark"],
    para: "/benchmark",
    nome: "Benchmark",
    texto: "Medir o otimizador nesta máquina: em série, na CPU em paralelo e na GPU.",
  },
  {
    tem: ["mensagens"],
    para: "/mensagens",
    nome: "Mensagens",
    texto: "Gerar as mensagens para os parceiros de um plano.",
  },
  {
    tem: ["aprovacao", "decidir_mensagens"],
    para: "/aprovacao",
    nome: "Aprovação",
    texto: "Aprovar, editar ou rejeitar cada mensagem. Nenhuma sai do sistema sem essa decisão.",
  },
  {
    tem: ["aprovacao"],
    sem: ["decidir_mensagens"],
    para: "/aprovacao",
    nome: "Aprovação",
    texto: "Acompanhar a fila de mensagens. Aprovar, editar e rejeitar não fazem parte do seu perfil.",
  },
  {
    tem: ["usuarios"],
    para: "/usuarios",
    nome: "Usuários",
    texto: "Criar contas, mudar o perfil, desativar e redefinir a senha de quem a esqueceu.",
  },
  {
    tem: ["auditoria"],
    para: "/auditoria",
    nome: "Auditoria",
    texto: "Consultar quem fez o quê, e quando, e exportar o recorte.",
  },
  {
    tem: ["relatorio_operacoes"],
    para: "/relatorios/operacoes",
    nome: "Operações",
    texto: "Gerar o relatório das operações do sistema, que resume a trilha de auditoria.",
  },
  {
    tem: ["configuracao"],
    para: "/configuracao",
    nome: "Configuração",
    texto: "Mudar os limiares da segmentação, que valem para a rede inteira.",
  },
];

/* De todos os perfis, e por isso fora das telas da sessão. */
const MINHA_CONTA = {
  para: "/conta",
  nome: "Minha conta",
  texto: "Ver os seus dados e trocar a sua senha.",
};

function areasDe(telas) {
  const tem = (nome) => telas.includes(nome);
  return [...AREAS.filter((a) => a.tem.every(tem) && !(a.sem ?? []).some(tem)), MINHA_CONTA];
}

const periodos = (n) => (n === 1 ? "1 período" : `${n} períodos`);
const seguidos = (n) => (n === 1 ? "no último período" : `em ${n} períodos seguidos, ou mais`);

/* O critério de cada segmento, com os limiares em vigor no lugar dos números. */
const CRITERIO = {
  PROSPECCAO: () => "Marcado no cadastro como prospecção: ainda não converteu.",
  RECEM_CHEGADO: (r) =>
    `Tem menos de ${periodos(r.periodos_novato)} de histórico: é cedo para falar em tendência.`,
  EM_RISCO: (r) =>
    `O faturamento caiu ${seguidos(r.periodos_tendencia)}. Vem antes do Top de propósito: quem está entre os maiores e em queda aparece como risco, e não entre os campeões.`,
  TOP: (r) => `Está entre os ${r.top_n} maiores faturamentos do período mais recente.`,
  EM_ASCENSAO: (r) => `O faturamento subiu ${seguidos(r.periodos_tendencia)}, e o parceiro está fora do Top.`,
  ESTAVEL: () => "Nenhum dos critérios anteriores vale.",
};

/* O rótulo do Top leva o tamanho em vigor, e não o número escrito no rótulo comum. */
const rotuloDe = (segmento, regras) =>
  segmento === "TOP" ? `Top ${regras.top_n}` : (ROTULO_SEGMENTO[segmento] ?? segmento);

export default function Ajuda() {
  const { usuario } = useSessao();
  const { hash } = useLocation();
  const telas = Array.isArray(usuario?.telas) ? usuario.telas : [];
  const daRede = telas.includes("ajuda_regras");
  const [regras, setRegras] = useState(null);
  const [erro, setErro] = useState(null);

  useEffect(() => {
    if (!daRede) return undefined;
    let vivo = true;
    api
      .get("/api/ajuda/regras")
      .then((corpo) => vivo && setRegras(corpo))
      .catch((e) => vivo && setErro(e));
    return () => {
      vivo = false;
    };
  }, [daRede]);

  /* Quem chegou por "o que é isto?" pediu um bloco, e não o topo da página. Só
     depois de as regras chegarem: antes, o bloco ainda não está na tela. */
  useEffect(() => {
    if (!hash || (daRede && !regras)) return;
    const bloco = document.getElementById(hash.slice(1));
    bloco?.scrollIntoView?.({ block: "start" });
    bloco?.focus();
  }, [hash, daRede, regras]);

  return (
    <div className="ajuda">
      <section className="painel" aria-labelledby="o-que-fazer">
        <div className="painel__cabecalho">
          <h2 className="painel__titulo" id="o-que-fazer" tabIndex={-1}>
            O que você pode fazer
          </h2>
          <span className="painel__nota">perfil {ROTULO_PERFIL[usuario?.perfil] ?? usuario?.perfil}</span>
        </div>
        <ul className="ajuda__areas">
          {areasDe(telas).map(({ para, nome, texto }) => (
            <li key={`${para}-${nome}`}>
              <Link className="ajuda__area" to={para}>
                {nome}
              </Link>
              <span>{texto}</span>
            </li>
          ))}
        </ul>
      </section>

      {!daRede && <DoPortal />}

      {daRede && erro && (
        <div className="aviso" role="alert">
          <p className="aviso__titulo">{erro.message}</p>
          <p className="aviso__ajuda">
            {erro.ajuda ?? "A explicação dos segmentos e da estimativa depende das regras em vigor. Tente de novo em instantes."}
          </p>
        </div>
      )}

      {daRede && !regras && !erro && (
        <section className="painel" aria-busy="true" aria-label="Carregando as regras em vigor">
          <div className="ajuda__texto">
            <Esqueleto altura={220} />
          </div>
        </section>
      )}

      {regras && <DaRede regras={regras} mudaLimiares={telas.includes("configuracao")} />}
    </div>
  );
}

function DaRede({ regras, mudaLimiares }) {
  const { previsao } = regras;

  return (
    <>
      <section className="painel" aria-labelledby="segmentos">
        <div className="painel__cabecalho">
          <h2 className="painel__titulo" id="segmentos" tabIndex={-1}>
            Os segmentos
          </h2>
          <span className="painel__nota">na ordem em que a regra decide</span>
        </div>
        <div className="ajuda__texto">
          <p>
            Cada parceiro recebe um segmento só, calculado a cada importação. Quando mais de um critério vale
            para o mesmo parceiro, fica o que vem primeiro nesta lista.
          </p>
        </div>
        <ol className="ajuda__segmentos">
          {regras.segmentos.map((segmento) => (
            <li key={segmento}>
              <span className="segmento ajuda__segmento">
                <span
                  className={`segmento__ponto segmento__ponto--${segmento.toLowerCase()}`}
                  aria-hidden="true"
                />
                {rotuloDe(segmento, regras)}
              </span>
              <span>{CRITERIO[segmento]?.(regras) ?? "Sem descrição nesta versão da ajuda."}</span>
            </li>
          ))}
        </ol>
        <div className="ajuda__texto">
          <p className="ajuda__nota">
            Os números desta lista são os que estão valendo agora.{" "}
            {mudaLimiares ? (
              <>
                Eles mudam em <Link to="/configuracao">Configuração</Link>.
              </>
            ) : (
              "Quem os muda é o administrador."
            )}
          </p>
        </div>
      </section>

      <section className="painel" aria-labelledby="estimativa">
        <div className="painel__cabecalho">
          <h2 className="painel__titulo" id="estimativa" tabIndex={-1}>
            Estimativa
          </h2>
          <span className="etiqueta-estimativa">Estimativa</span>
        </div>
        <div className="ajuda__texto">
          <p>
            O faturamento, os pedidos e o segmento saem dos relatórios importados: são medição. O que leva a
            etiqueta acima sai do modelo de previsão: é uma conta sobre o histórico, e pode errar.
          </p>
          <dl className="ajuda__termos">
            <div>
              <dt>Faturamento previsto</dt>
              <dd>Quanto o parceiro deve faturar no próximo período.</dd>
            </div>
            <div>
              <dt>Chance de queda</dt>
              <dd>
                A chance de o parceiro fechar o próximo período em risco — com o faturamento caindo{" "}
                {seguidos(regras.periodos_tendencia)}, pela mesma regra do segmento Em risco.
              </dd>
            </div>
          </dl>
          <p>
            {previsao.versao_em_uso
              ? previsao.origem === "REFERENCIA"
                ? `As estimativas de agora saem da referência ${previsao.versao_em_uso}: nenhuma rede treinada a superou ainda.`
                : `As estimativas de agora saem do modelo ${previsao.versao_em_uso}.`
              : `Ainda não há modelo em uso, e por isso nenhuma estimativa aparece. O primeiro treino precisa de ${periodos(previsao.periodos_minimos_do_treino)} importados.`}{" "}
            Parceiro com menos de {periodos(previsao.periodos_minimos_do_parceiro)} de histórico não recebe
            estimativa, e a tela diz por quê.
          </p>
        </div>
      </section>

      <section className="painel" aria-labelledby="ganho">
        <div className="painel__cabecalho">
          <h2 className="painel__titulo" id="ganho" tabIndex={-1}>
            Ganho esperado
          </h2>
          <span className="etiqueta-estimativa">Estimativa</span>
        </div>
        <div className="ajuda__texto">
          <p>
            É quanto uma ação da campanha deve render num parceiro, no próximo período. Soma duas parcelas: o
            que a ação acrescenta e o que ela evita perder.
          </p>
          {/* Uma parcela por linha: é o que o texto acima acabou de dizer. */}
          <p className="ajuda__formula num">
            {"ganho = previsto × crescimento\n      + previsto × chance de queda × retenção"}
          </p>
          <p>
            O <strong>previsto</strong> e a <strong>chance de queda</strong> são as estimativas do modelo; o{" "}
            <strong>crescimento</strong> e a <strong>retenção</strong> são os efeitos da ação, no catálogo. Por
            isso uma ação de retenção vale mais para quem está prestes a cair, e uma de crescimento, para quem
            fatura mais. O plano de campanha escolhe as ações que somam o maior ganho dentro do orçamento.
          </p>
        </div>
      </section>
    </>
  );
}

/* A ajuda do Parceiro (UC16-A1): o que ele vê e de onde vêm os números. Nada
   aqui é regra da rede, e por isso nada vem da API. */
function DoPortal() {
  return (
    <section className="painel" aria-labelledby="portal">
      <div className="painel__cabecalho">
        <h2 className="painel__titulo" id="portal" tabIndex={-1}>
          O seu portal
        </h2>
      </div>
      <div className="ajuda__texto">
        <dl className="ajuda__termos">
          <div>
            <dt>O que aparece</dt>
            <dd>
              O faturamento, os pedidos e o ticket médio do seu comércio no período mais recente, comparados
              com o período anterior, e o histórico em gráfico e em tabela.
            </dd>
          </div>
          <div>
            <dt>De onde vêm os números</dt>
            <dd>
              Dos relatórios de cada período, importados pela equipe que opera a rede. O ticket médio é o
              faturamento dividido pelo número de pedidos.
            </dd>
          </div>
          <div>
            <dt>O que não aparece</dt>
            <dd>Dados de outros parceiros. O portal mostra só o seu comércio.</dd>
          </div>
        </dl>
      </div>
    </section>
  );
}
