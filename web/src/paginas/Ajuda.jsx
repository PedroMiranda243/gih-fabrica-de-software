/**
 * Ajuda — explica o sistema a quem chega. Os números das regras vêm de
 * `GET /api/ajuda/regras` (só para quem tem `ajuda_regras`); o Parceiro lê só o
 * portal dele e a tela nem pede as regras.
 */
import { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";

import { api } from "../api/cliente";
import { useCarregar } from "../api/ganchos";
import { tem, useSessao } from "../api/sessao";
import { Estimativa, Segmento } from "../componentes/Dados";
import { Carregando, Nota } from "../componentes/Estados";
import Icone from "../componentes/Icone";
import { useTitulo } from "../componentes/Titulo";
import { plural } from "../formato";
import { grupoDe, itemAtivo } from "../navegacao/telas";

function oQuePodeFazer(u) {
  const t = (x) => tem(u, x);
  const itens = [];
  if (t("painel")) itens.push(["Painel", "/", "Ver como a rede foi no período: indicadores, série, segmentos e ranking."]);
  if (t("meu_desempenho")) itens.push(["Meu desempenho", "/meu-desempenho", "Ver o desempenho do seu comércio, período a período."]);
  if (t("importar")) itens.push(["Importação", "/importacao", "Importar o relatório da semana, conferindo na prévia antes de gravar."]);
  else if (t("historico_importacoes")) itens.push(["Importação", "/importacao", "Consultar o histórico das importações. Importar um relatório não faz parte do seu perfil."]);
  if (t("parceiros")) itens.push(["Parceiros", "/parceiros", "Consultar, filtrar e exportar a lista da rede, e cadastrar ou editar um parceiro."]);
  if (t("assistente")) itens.push(["Assistente", "/assistente", "Perguntar sobre os dados com as suas palavras, com a fonte de cada número."]);
  if (t("relatorios")) itens.push(["Relatórios", "/relatorios", "Levar para fora do sistema o desempenho, o risco e a campanha, em CSV ou PDF."]);
  if (t("modelo")) itens.push(["Modelo", "/modelo", "Ver a versão do modelo de previsão em uso, o quanto ela erra, e treinar de novo."]);
  if (t("calcular_campanha")) itens.push(["Campanha", "/campanha", "Calcular o plano de campanha, com o orçamento e as restrições, e consultar o catálogo de ações."]);
  else if (t("campanha")) itens.push(["Campanha", "/campanha", "Consultar o último plano e o catálogo de ações. Calcular o plano não faz parte do seu perfil."]);
  if (t("execucao")) itens.push(["Execuções", "/execucoes", "Abrir cada plano calculado e comparar dois deles lado a lado."]);
  else if (t("execucoes")) itens.push(["Execuções", "/execucoes", "Consultar o histórico das execuções do otimizador. Abrir o plano de uma delas não faz parte do seu perfil."]);
  if (t("benchmark")) itens.push(["Benchmark", "/benchmark", "Medir o otimizador nesta máquina, nos quatro modos de execução."]);
  if (t("mensagens")) itens.push(["Mensagens", "/mensagens", "Gerar uma mensagem para cada parceiro de um público, que vai para a fila de aprovação."]);
  if (t("decidir_mensagens")) itens.push(["Aprovação", "/aprovacao", "Aprovar, editar ou rejeitar as mensagens geradas: nenhuma sai sem essa decisão."]);
  else if (t("aprovacao")) itens.push(["Aprovação", "/aprovacao", "Acompanhar a fila de mensagens. Decidir é do perfil Gestor."]);
  if (t("usuarios")) itens.push(["Usuários", "/usuarios", "Criar contas, mudar perfil, desativar e redefinir senhas."]);
  if (t("auditoria")) itens.push(["Auditoria", "/auditoria", "Ver a trilha do que foi feito, por quem e quando."]);
  if (t("relatorio_operacoes")) itens.push(["Operações", "/relatorios/operacoes", "Ver quanto se fez no sistema, por tipo de ação, por pessoa e por dia."]);
  if (t("configuracao")) itens.push(["Configuração", "/configuracao", "Mudar os limiares que decidem os segmentos da rede."]);
  itens.push(["Minha conta", "/conta", "Ver os seus dados e trocar a sua senha."]);
  return itens;
}

const p = (n) => plural(n, "período", "períodos");
const CRITERIO = {
  PROSPECCAO: () => "Marcado no cadastro como prospecção: ainda não converteu.",
  RECEM_CHEGADO: (r) => `Tem menos de ${p(r.periodos_novato)} de histórico: é cedo para falar em tendência.`,
  EM_RISCO: (r) => `O faturamento caiu ${p(r.periodos_tendencia)} seguido${r.periodos_tendencia === 1 ? "" : "s"}. Vem antes do Top de propósito: quem está entre os maiores e em queda aparece como risco, e não entre os campeões.`,
  TOP: (r) => `Está entre os ${r.top_n} maiores faturamentos do período mais recente.`,
  EM_ASCENSAO: (r) => `O faturamento subiu ${p(r.periodos_tendencia)} seguido${r.periodos_tendencia === 1 ? "" : "s"}, e o parceiro está fora do Top.`,
  ESTAVEL: () => "Nenhum dos critérios anteriores vale.",
};

export default function Ajuda() {
  useTitulo("Ajuda");
  const { usuario } = useSessao();
  const { hash } = useLocation();
  const portal = tem(usuario, "meu_desempenho") && !tem(usuario, "painel") && Array.isArray(usuario.telas);
  const podeRegras = tem(usuario, "ajuda_regras") && !portal;
  const regras = useCarregar(() => api.get("/api/ajuda/regras"), "regras", { ativo: podeRegras });

  /* Quem chega por um link para um bloco cai nele, com o foco nele. */
  useEffect(() => {
    if (!hash || regras.carregando) return;
    const alvo = document.getElementById(decodeURIComponent(hash.slice(1)));
    if (alvo) {
      alvo.scrollIntoView({ block: "start" });
      alvo.focus({ preventScroll: true });
    }
  }, [hash, regras.carregando]);

  if (portal) {
    return (
      <div className="pagina ajuda">
        <section className="bloco ajuda__bloco" id="portal" tabIndex={-1} aria-labelledby="t-portal">
          <h2 id="t-portal" className="bloco__titulo">
            O seu portal
          </h2>
          <div className="prosa">
            <p>
              <strong>O que aparece.</strong> O faturamento, os pedidos e o ticket médio do seu comércio, período a período — cada período é uma semana. Os três números do alto comparam o período mais recente com o anterior, só com os seus próprios números.
            </p>
            <p>
              <strong>De onde vêm os números.</strong> Do relatório semanal que a operação importa no sistema. Se o último relatório não trouxe o seu comércio, o período aparece vazio, e o gráfico mostra a falta como um intervalo, e não como zero.
            </p>
            <p>
              <strong>O que não aparece.</strong> Dados de outros parceiros. O portal mostra só o seu comércio.
            </p>
          </div>
          <Link to="/meu-desempenho" className="link-seta">
            Ir para Meu desempenho <Icone nome="seta-direita" />
          </Link>
        </section>
      </div>
    );
  }

  const r = regras.dados;
  const pv = r?.previsao;

  return (
    <div className="pagina ajuda">
      <nav className="ajuda__indice" aria-label="Nesta página">
        <a href="#pode-fazer">O que você pode fazer</a>
        <a href="#segmentos">Os segmentos</a>
        <a href="#estimativa">Estimativa</a>
        <a href="#ganho">Ganho esperado</a>
      </nav>

      <section className="bloco ajuda__bloco" id="pode-fazer" tabIndex={-1} aria-labelledby="t-pode">
        <h2 id="t-pode" className="bloco__titulo">
          O que você pode fazer
        </h2>
        <ul className="pode-fazer">
          {oQuePodeFazer(usuario).map(([rotulo, para, frase]) => {
            const area = grupoDe(itemAtivo(para));
            return (
              <li key={para + rotulo}>
                <Link to={para} className="pode-fazer__link">
                  {rotulo}
                </Link>
                {area ? (
                  <span className="rota-etiqueta rota-etiqueta--compacta" data-rota={area.rota}>
                    <span className="rota-etiqueta__parada" aria-hidden="true" />
                    <span className="sr-only">Área: </span>
                    {area.grupo}
                  </span>
                ) : (
                  <span aria-hidden="true" />
                )}
                <span>{frase}</span>
              </li>
            );
          })}
        </ul>
      </section>

      {podeRegras && regras.carregando && <Carregando rotulo="Carregando as regras em vigor" linhas={6} />}
      {podeRegras && (regras.erro || !tem(usuario, "ajuda_regras")) && (
        <Nota tipo="atencao">A explicação dos segmentos e da estimativa depende das regras em vigor. Tente de novo em instantes.</Nota>
      )}

      {r && (
        <>
          <section className="bloco ajuda__bloco" id="segmentos" tabIndex={-1} aria-labelledby="t-segmentos">
            <h2 id="t-segmentos" className="bloco__titulo">
              Os segmentos
            </h2>
            <p className="bloco__sub">Na ordem em que a regra decide: o primeiro critério que vale define o segmento.</p>
            <ol className="segmentos-regra">
              {r.segmentos.map((s, i) => (
                <li key={s}>
                  <span className="segmentos-regra__ordem" aria-hidden="true">
                    {i + 1}
                  </span>
                  <Segmento codigo={s} />
                  <p>{CRITERIO[s]?.(r) ?? ""}</p>
                </li>
              ))}
            </ol>
            <p className="bloco__nota">
              Os limiares de agora: Top de {r.top_n}, tendência de {p(r.periodos_tendencia)}, recém-chegado com menos de {p(r.periodos_novato)}.{" "}
              {tem(usuario, "configuracao") ? (
                <>
                  Eles mudam em <Link to="/configuracao">Configuração</Link>.
                </>
              ) : (
                "Quem os muda é o administrador."
              )}
            </p>
          </section>

          <section className="bloco ajuda__bloco bloco--estimativa" id="estimativa" tabIndex={-1} aria-labelledby="t-estimativa">
            <div className="bloco__cabeca bloco__cabeca--etiqueta">
              <h2 id="t-estimativa" className="bloco__titulo">
                Estimativa
              </h2>
              <Estimativa />
            </div>
            <div className="prosa">
              <p>
                <strong>Medição</strong> é o que os relatórios importados trouxeram: faturamento, pedidos e ticket médio. Sai com o número do período e não muda depois. <strong>Estimativa</strong> é o que o modelo de previsão calcula para o próximo período, e aparece sempre marcada assim, com contorno tracejado.
              </p>
              <ul>
                <li>
                  <strong>Faturamento previsto</strong>: quanto o parceiro deve faturar no próximo período.
                </li>
                <li>
                  <strong>Chance de queda</strong>: a probabilidade de o parceiro estar em risco no próximo período. Ela nunca se escreve como certeza: os extremos aparecem como “menos de 1%” e “mais de 99%”.
                </li>
              </ul>
              <p>
                {!pv.versao_em_uso
                  ? `Ainda não há modelo em uso, e por isso nenhuma estimativa aparece. O primeiro treino precisa de ${p(pv.periodos_minimos_do_treino)} importados.`
                  : pv.origem === "REFERENCIA"
                    ? `As estimativas de agora saem da referência ${pv.versao_em_uso}: nenhuma rede treinada a superou ainda.`
                    : `As estimativas de agora saem do modelo ${pv.versao_em_uso}.`}{" "}
                Um parceiro com menos de {p(pv.periodos_minimos_do_parceiro)} de histórico não recebe previsão.
              </p>
            </div>
          </section>

          <section className="bloco ajuda__bloco bloco--estimativa" id="ganho" tabIndex={-1} aria-labelledby="t-ganho">
            <div className="bloco__cabeca bloco__cabeca--etiqueta">
              <h2 id="t-ganho" className="bloco__titulo">
                Ganho esperado
              </h2>
              <Estimativa />
            </div>
            <div className="prosa">
              <p>É quanto uma ação da campanha deve render num parceiro, no próximo período. Soma duas parcelas: o que a ação acrescenta e o que ela evita perder.</p>
              <pre className="formula" aria-label="ganho é igual a previsto vezes crescimento, mais previsto vezes chance de queda vezes retenção">
                {"ganho = previsto × crescimento\n      + previsto × chance de queda × retenção"}
              </pre>
              <p>
                O <strong>previsto</strong> e a <strong>chance de queda</strong> são as estimativas do modelo; o <strong>crescimento</strong> e a <strong>retenção</strong> são os efeitos da ação, no catálogo da campanha. Por isso uma ação de retenção vale mais para quem está prestes a cair, e uma de crescimento, para quem fatura mais. A tela explica a conta; quem a faz é o servidor.
              </p>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
