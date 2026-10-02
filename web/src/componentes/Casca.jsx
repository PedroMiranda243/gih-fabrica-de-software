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
import { EXIGE } from "../navegacao/telas";
import { useTema } from "../temas/useTema";
import { ContextoTituloDaAba, tituloDaAba } from "./tituloDaAba";
import {
  IconeAjuda,
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

/* `exige`: as telas do servidor que sustentam o item — basta uma. Vem de
   `navegacao/telas.js`, a mesma tabela que a guarda das rotas lê (H94): o item
   que o menu esconde é a tela que o endereço não monta. */
const GRUPOS = [
  {
    chave: "analise",
    titulo: "Análise",
    itens: [
      { para: "/", rotulo: "Painel", Icone: IconePainel, fim: true, exige: EXIGE.painel },
      /* O Parceiro tem só esta: o histórico dele, e nada da rede (RF26, H39). */
      { para: "/meu-desempenho", rotulo: "Meu desempenho", Icone: IconePainel, exige: EXIGE.meuDesempenho },
      {
        para: "/importacao",
        rotulo: "Importação",
        Icone: IconeImportar,
        exige: EXIGE.importacao,
      },
      { para: "/parceiros", rotulo: "Parceiros", Icone: IconeParceiros, exige: EXIGE.parceiros },
      /* Consulta, como o painel e a lista de parceiros: por isso junto deles (UC12). */
      { para: "/assistente", rotulo: "Assistente", Icone: IconeAssistente, exige: EXIGE.assistente },
      /* Os três relatórios da rede (UC15), que resumem o que este grupo mostra. */
      { para: "/relatorios", rotulo: "Relatórios", Icone: IconeRelatorios, exige: EXIGE.relatorios },
    ],
  },
  {
    chave: "previsao",
    titulo: "Previsão",
    itens: [{ para: "/modelo", rotulo: "Modelo", Icone: IconeModelo, exige: EXIGE.modelo }],
  },
  {
    /* "Otimização", e não "Campanha": o grupo leva o nome do módulo, e o item
       Campanha dentro de um grupo Campanha diria a mesma coisa duas vezes. */
    chave: "otimizacao",
    titulo: "Otimização",
    itens: [
      { para: "/campanha", rotulo: "Campanha", Icone: IconeCampanha, exige: EXIGE.campanha },
      /* O histórico (RF34) é também do Administrador, que não tem a Campanha. */
      { para: "/execucoes", rotulo: "Execuções", Icone: IconeExecucoes, exige: EXIGE.execucoes },
      { para: "/benchmark", rotulo: "Benchmark", Icone: IconeBenchmark, exige: EXIGE.benchmark },
    ],
  },
  {
    chave: "comunicacao",
    titulo: "Comunicação",
    itens: [
      { para: "/mensagens", rotulo: "Mensagens", Icone: IconeMensagens, exige: EXIGE.mensagens },
      { para: "/aprovacao", rotulo: "Aprovação", Icone: IconeAprovacao, exige: EXIGE.aprovacao },
    ],
  },
  {
    chave: "administracao",
    titulo: "Administração",
    itens: [
      { para: "/usuarios", rotulo: "Usuários", Icone: IconeUsuarios, exige: EXIGE.usuarios },
      /* A trilha do que foi feito (UC14): só o Administrador a abre. */
      { para: "/auditoria", rotulo: "Auditoria", Icone: IconeAuditoria, exige: EXIGE.auditoria },
      /* O relatório das operações resume a trilha, e fica ao lado dela (RF47). */
      {
        para: "/relatorios/operacoes",
        rotulo: "Operações",
        Icone: IconeOperacoes,
        exige: EXIGE.operacoes,
      },
      {
        para: "/configuracao",
        rotulo: "Configuração",
        Icone: IconeConfiguracao,
        exige: EXIGE.configuracao,
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
      {/* O primeiro foco da página (H96): quem navega pelo teclado chega ao
          conteúdo sem atravessar o menu a cada tela. Só aparece ao receber o foco. */}
      <a className="pular" href="#conteudo">
        Pular para o conteúdo
      </a>

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
          {/* Recebe o foco quando a tela troca (`FocoNaTroca`, em App.jsx): é o que
              o leitor de tela anuncia, e de onde o Tab seguinte parte. */}
          <h1 className="cabecalho__titulo" id="titulo-da-tela" tabIndex={-1}>
            {titulo}
          </h1>

          <div className="cabecalho__direita">
            {/* O nome é o caminho para a conta de quem está usando (H92): é onde a
                pessoa procura "os meus dados", e a conta não é item de menu — todos
                os perfis a têm. */}
            {usuario && (
              <NavLink to="/conta" className="cabecalho__quem">
                {/* Sem ver o cabeçalho, "Gestora de Exemplo GESTOR" não diz aonde o link leva. */}
                {/* Os espaços soltos separam as três partes no nome que o leitor de
                    tela lê; na tela, que é uma coluna, eles não ocupam lugar. */}
                <span className="so-leitor">Minha conta:</span>{" "}
                <span className="cabecalho__nome">{usuario.nome}</span>{" "}
                <span className="cabecalho__perfil">{usuario.perfil}</span>
              </NavLink>
            )}

            {/* A ajuda é de todos os perfis, como a conta, e por isso também fica
                aqui e não no menu (H95). */}
            <NavLink to="/ajuda" className="icone-botao" aria-label="Ajuda">
              <IconeAjuda />
            </NavLink>

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

        <main className="pagina" id="conteudo" tabIndex={-1}>
          <ContextoTituloDaAba.Provider value={setDetalhe}>
            <Outlet />
          </ContextoTituloDaAba.Provider>
        </main>
      </div>
    </div>
  );
}
