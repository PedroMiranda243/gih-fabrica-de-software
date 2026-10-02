/**
 * Casca da aplicação: trilho lateral, cabeçalho e o conteúdo da rota.
 *
 * O trilho lista **apenas o que existe**: cada item entrou junto com a API que o
 * sustenta. Item de menu que leva a uma tela vazia é pior que item ausente —
 * promete e não entrega.
 *
 * **Os itens se agrupam pelos módulos do produto, na ordem do fluxo** (H79): a
 * análise da rede, a previsão, a otimização da campanha, a comunicação e, por
 * último e à parte, a administração. Até a Sprint 06 eram doze itens soltos, na
 * ordem em que foram construídos — o Assistente entre Parceiros e Campanha, o
 * Modelo depois do Benchmark —, e a pessoa precisava conhecer o sistema para
 * achar o módulo.
 *
 * Pela mesma razão, **cada perfil vê só o que abre**. A lista vem do servidor
 * (`usuario.telas`), que a lê das permissões das próprias rotas: a interface
 * não decide quem pode o quê (regra 2.4), só desenha o que ouviu. E esconder o
 * item não é controle de acesso — a rota continua recusando (regra 2.5).
 */
import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";

import { useSessao } from "../api/contextoSessao";
import { useTema } from "../temas/useTema";
import { ContextoTituloDaAba, tituloDaAba } from "./tituloDaAba";
import {
  IconeAprovacao,
  IconeAssistente,
  IconeAuditoria,
  IconeBenchmark,
  IconeCampanha,
  IconeConfiguracao,
  IconeExecucoes,
  IconeImportar,
  IconeMensagens,
  IconeModelo,
  IconeOperacoes,
  IconePainel,
  IconeParceiros,
  IconeRelatorios,
  IconeSair,
  IconeUsuarios,
  IconeTemaClaro,
  IconeTemaEscuro,
} from "./Icones";

/* `exige`: as telas do servidor que sustentam o item — basta uma. A Importação
   aparece para quem importa **ou** só lê o histórico, que é o caso do
   Administrador (RF13). */
const GRUPOS = [
  {
    chave: "analise",
    titulo: "Análise",
    itens: [
      { para: "/", rotulo: "Painel", Icone: IconePainel, fim: true, exige: ["painel"] },
      /* O Parceiro tem só esta: o histórico dele, e nada da rede (RF26, H39). */
      { para: "/meu-desempenho", rotulo: "Meu desempenho", Icone: IconePainel, exige: ["meu_desempenho"] },
      {
        para: "/importacao",
        rotulo: "Importação",
        Icone: IconeImportar,
        exige: ["importar", "historico_importacoes"],
      },
      { para: "/parceiros", rotulo: "Parceiros", Icone: IconeParceiros, exige: ["parceiros"] },
      /* Consulta, como o painel e a lista de parceiros: por isso junto deles (UC12). */
      { para: "/assistente", rotulo: "Assistente", Icone: IconeAssistente, exige: ["assistente"] },
      /* Os três relatórios da rede (UC15), que resumem o que este grupo mostra. */
      { para: "/relatorios", rotulo: "Relatórios", Icone: IconeRelatorios, exige: ["relatorios"] },
    ],
  },
  {
    chave: "previsao",
    titulo: "Previsão",
    itens: [{ para: "/modelo", rotulo: "Modelo", Icone: IconeModelo, exige: ["modelo"] }],
  },
  {
    /* "Otimização", e não "Campanha": o grupo leva o nome do módulo, e o item
       Campanha dentro de um grupo Campanha diria a mesma coisa duas vezes. */
    chave: "otimizacao",
    titulo: "Otimização",
    itens: [
      { para: "/campanha", rotulo: "Campanha", Icone: IconeCampanha, exige: ["campanha"] },
      /* O histórico (RF34) é também do Administrador, que não tem a Campanha. */
      { para: "/execucoes", rotulo: "Execuções", Icone: IconeExecucoes, exige: ["execucoes"] },
      { para: "/benchmark", rotulo: "Benchmark", Icone: IconeBenchmark, exige: ["benchmark"] },
    ],
  },
  {
    chave: "comunicacao",
    titulo: "Comunicação",
    itens: [
      { para: "/mensagens", rotulo: "Mensagens", Icone: IconeMensagens, exige: ["mensagens"] },
      { para: "/aprovacao", rotulo: "Aprovação", Icone: IconeAprovacao, exige: ["aprovacao"] },
    ],
  },
  {
    chave: "administracao",
    titulo: "Administração",
    itens: [
      { para: "/usuarios", rotulo: "Usuários", Icone: IconeUsuarios, exige: ["usuarios"] },
      /* A trilha do que foi feito (UC14): só o Administrador a abre. */
      { para: "/auditoria", rotulo: "Auditoria", Icone: IconeAuditoria, exige: ["auditoria"] },
      /* O relatório das operações resume a trilha, e fica ao lado dela (RF47). */
      {
        para: "/relatorios/operacoes",
        rotulo: "Operações",
        Icone: IconeOperacoes,
        exige: ["relatorio_operacoes"],
      },
      {
        para: "/configuracao",
        rotulo: "Configuração",
        Icone: IconeConfiguracao,
        exige: ["configuracao"],
      },
    ],
  },
];

/* Sessão aberta antes de o servidor mandar `telas` — uma aba esquecida aberta
   durante a atualização — continua vendo o menu de antes, em vez de um trilho
   vazio, e sem as telas de administração que vieram depois. Na próxima
   recarga, a lista chega. */
const MENU_ANTERIOR = ["painel", "importar", "parceiros"];

/* Grupo sem nenhum item que o perfil abre não aparece: um título sobre nada é
   ruído, e diria ao Analista que existe uma Administração que ele não vê. */
function visiveis(usuario) {
  const telas = Array.isArray(usuario?.telas) ? usuario.telas : MENU_ANTERIOR;
  return GRUPOS.map((grupo) => ({
    ...grupo,
    itens: grupo.itens.filter(({ exige }) => exige.some((tela) => telas.includes(tela))),
  })).filter(({ itens }) => itens.length > 0);
}

export default function Casca({ titulo }) {
  const { usuario, sair } = useSessao();
  const { tema, alternar } = useTema();
  // O item aberto numa tela de detalhe, que a página sobe por `useTituloDaAba`.
  const [detalhe, setDetalhe] = useState(null);

  useEffect(() => {
    document.title = tituloDaAba(titulo, detalhe);
  }, [titulo, detalhe]);

  return (
    <div className="casca">
      <nav className="trilho" aria-label="Seções do sistema">
        <div className="trilho__marca">
          <span className="trilho__sigla">GIH</span>
          <span className="trilho__produto">Growth Intelligence</span>
        </div>

        <div className="trilho__navegacao">
          {visiveis(usuario).map(({ chave, titulo: grupo, itens }) => (
            <div key={chave} className="trilho__grupo" role="group" aria-labelledby={`grupo-${chave}`}>
              <span className="trilho__grupo-titulo" id={`grupo-${chave}`}>
                {grupo}
              </span>
              {itens.map(({ para, rotulo, Icone, fim }) => (
                <NavLink key={para} to={para} end={fim} className="trilho__item">
                  <Icone />
                  {rotulo}
                </NavLink>
              ))}
            </div>
          ))}
        </div>
      </nav>

      <div className="conteudo">
        <header className="cabecalho">
          <h1 className="cabecalho__titulo">{titulo}</h1>

          <div className="cabecalho__direita">
            {usuario && (
              <div className="cabecalho__quem">
                <span className="cabecalho__nome">{usuario.nome}</span>
                <span className="cabecalho__perfil">{usuario.perfil}</span>
              </div>
            )}

            <button
              type="button"
              className="icone-botao"
              onClick={alternar}
              /* O rótulo diz o que **vai acontecer**, não o estado atual: é o
                 que o leitor de tela anuncia, e "modo escuro" sozinho deixa
                 ambíguo se liga ou desliga. */
              aria-label={tema === "escuro" ? "Mudar para o modo claro" : "Mudar para o modo escuro"}
            >
              {tema === "escuro" ? <IconeTemaClaro /> : <IconeTemaEscuro />}
            </button>

            <button type="button" className="icone-botao" onClick={sair} aria-label="Encerrar sessão">
              <IconeSair />
            </button>
          </div>
        </header>

        <main className="pagina">
          <ContextoTituloDaAba.Provider value={setDetalhe}>
            <Outlet />
          </ContextoTituloDaAba.Provider>
        </main>
      </div>
    </div>
  );
}
