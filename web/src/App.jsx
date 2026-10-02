/**
 * Rotas da aplicação.
 *
 * Cada tela tem endereço próprio, e isso não é detalhe: o botão voltar precisa
 * funcionar, e um painel filtrado precisa poder ser mandado para outra pessoa
 * por link. Roteador à mão erraria exatamente esses dois pontos.
 */
import { useEffect, useRef } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import { useSessao } from "./api/contextoSessao";
import Casca from "./componentes/Casca";
import Carregando from "./componentes/Carregando";
import { EXIGE, abre } from "./navegacao/telas";
import Ajuda from "./paginas/Ajuda";
import Aprovacao from "./paginas/Aprovacao";
import Assistente from "./paginas/Assistente";
import Auditoria from "./paginas/Auditoria";
import Benchmark from "./paginas/Benchmark";
import Campanha from "./paginas/Campanha";
import Comparacao from "./paginas/Comparacao";
import Configuracao from "./paginas/Configuracao";
import Execucao from "./paginas/Execucao";
import Execucoes from "./paginas/Execucoes";
import Importacao from "./paginas/Importacao";
import Login from "./paginas/Login";
import Mensagens from "./paginas/Mensagens";
import MinhaConta from "./paginas/MinhaConta";
import MeuDesempenho from "./paginas/MeuDesempenho";
import Modelo from "./paginas/Modelo";
import NaoEncontrada from "./paginas/NaoEncontrada";
import Painel from "./paginas/Painel";
import Parceiro from "./paginas/Parceiro";
import Parceiros from "./paginas/Parceiros";
import RelatorioCampanha from "./paginas/RelatorioCampanha";
import RelatorioDesempenho from "./paginas/RelatorioDesempenho";
import RelatorioOperacoes from "./paginas/RelatorioOperacoes";
import RelatorioRisco from "./paginas/RelatorioRisco";
import Relatorios from "./paginas/Relatorios";
import SemAcesso from "./paginas/SemAcesso";
import Usuario from "./paginas/Usuario";
import Usuarios from "./paginas/Usuarios";

/**
 * Portão de entrada.
 *
 * Isto **não é controle de acesso** — esconder tela não protege nada, e a API
 * valida o perfil no servidor a cada requisição (regra 2.5). Aqui é só
 * navegação: quem não tem sessão não tem o que ver, e é levado ao login.
 */
function Protegido({ children }) {
  const { usuario, conferindo } = useSessao();
  const lugar = useLocation();

  /* Enquanto não se sabe, não se decide. Renderizar o login durante a
     conferência faria a tela piscar a cada recarga de quem já está dentro. */
  if (conferindo) return <Carregando rotulo="Conferindo a sessão" />;

  if (!usuario) {
    /* Guarda de onde a pessoa veio, para voltar ao lugar certo depois de
       entrar — abrir um link direto e cair no painel genérico é perder o que
       se estava indo ver. */
    return <Navigate to="/entrar" replace state={{ de: lugar.pathname + lugar.search }} />;
  }

  return children;
}

/**
 * A tela que o perfil abre — ou a página que diz que ele não abre (H94).
 *
 * Como o `Protegido`, **isto não é controle de acesso**: a API valida o perfil a
 * cada requisição. É a interface deixando de montar uma tela que ela já sabe,
 * pelas telas que o servidor mandou na sessão, que vai ser recusada. A tabela
 * `EXIGE` é a mesma que o menu lê.
 */
function Tela({ exige, children }) {
  const { usuario } = useSessao();
  return abre(usuario, exige) ? children : <SemAcesso />;
}

/**
 * A página inicial de cada um. O Parceiro não tem o painel da rede (RF26): o
 * endereço raiz o leva ao portal dele, em vez de a um painel que a API recusa.
 */
function Inicio() {
  const { usuario } = useSessao();
  const telas = usuario?.telas ?? [];
  if (!telas.includes("painel") && telas.includes("meu_desempenho")) {
    return <Navigate to="/meu-desempenho" replace />;
  }
  return <Painel />;
}

/**
 * Ao trocar de tela, o foco vai para o título dela (H96).
 *
 * Numa aplicação de página única, clicar num item do menu troca o conteúdo e
 * deixa o foco onde estava — no item do menu. Quem usa leitor de tela não ouve
 * que a tela mudou, e quem usa o teclado continua no menu. Levar o foco ao
 * título resolve os dois: ele é anunciado, e o Tab seguinte entra no conteúdo.
 *
 * **Só quando o caminho muda.** Os filtros das listas moram na URL: mudar um
 * filtro troca a consulta, e não o caminho — e tirar o foco do campo em que a
 * pessoa está digitando seria pior que o defeito que isto corrige.
 *
 * Fora das rotas, e depois delas, para o efeito rodar com a tela nova já montada.
 */
function FocoNaTroca() {
  const { pathname, hash } = useLocation();
  const anterior = useRef(pathname);

  useEffect(() => {
    if (anterior.current === pathname) return;
    anterior.current = pathname;
    /* Quem seguiu um link para um bloco da tela — "o que é cada segmento?" —
       pediu o bloco, e é a tela que leva o foco até ele (H95). */
    if (hash) return;
    document.getElementById("titulo-da-tela")?.focus();
  }, [pathname, hash]);

  return null;
}

export default function App() {
  return (
    <>
      <Rotas />
      <FocoNaTroca />
    </>
  );
}

function Rotas() {
  return (
    <Routes>
      <Route path="/entrar" element={<Login />} />

      <Route
        element={
          <Protegido>
            <Casca titulo="Painel" />
          </Protegido>
        }
      >
        <Route
          index
          element={
            <Tela exige={EXIGE.inicio}>
              <Inicio />
            </Tela>
          }
        />
      </Route>

      <Route
        element={
          <Protegido>
            <Casca titulo="Importação de relatório" />
          </Protegido>
        }
      >
        <Route
          path="/importacao"
          element={
            <Tela exige={EXIGE.importacao}>
              <Importacao />
            </Tela>
          }
        />
      </Route>

      <Route
        element={
          <Protegido>
            <Casca titulo="Parceiros" />
          </Protegido>
        }
      >
        <Route
          path="/parceiros"
          element={
            <Tela exige={EXIGE.parceiros}>
              <Parceiros />
            </Tela>
          }
        />
        {/* Cadastro e edição no mesmo componente, cada um com endereço próprio:
            o cadastro de um parceiro precisa poder ser aberto por link, e o
            botão voltar precisa devolver a lista com o filtro que ela tinha. */}
        <Route
          path="/parceiros/novo"
          element={
            <Tela exige={EXIGE.parceiros}>
              <Parceiro />
            </Tela>
          }
        />
        <Route
          path="/parceiros/:id"
          element={
            <Tela exige={EXIGE.parceiros}>
              <Parceiro />
            </Tela>
          }
        />
      </Route>

      {/* A conta de quem está usando (H92): de todos os perfis, e por isso fora do
          menu — chega-se a ela pelo nome, no cabeçalho. */}
      <Route
        element={
          <Protegido>
            <Casca titulo="Minha conta" />
          </Protegido>
        }
      >
        <Route path="/conta" element={<MinhaConta />} />
      </Route>

      {/* A ajuda (H95), também de todos os perfis: o que ela mostra a cada um sai
          das telas da sessão. */}
      <Route
        element={
          <Protegido>
            <Casca titulo="Ajuda" />
          </Protegido>
        }
      >
        <Route path="/ajuda" element={<Ajuda />} />
      </Route>

      <Route
        element={
          <Protegido>
            <Casca titulo="Usuários" />
          </Protegido>
        }
      >
        <Route
          path="/usuarios"
          element={
            <Tela exige={EXIGE.usuarios}>
              <Usuarios />
            </Tela>
          }
        />
        <Route
          path="/usuarios/novo"
          element={
            <Tela exige={EXIGE.usuarios}>
              <Usuario />
            </Tela>
          }
        />
        <Route
          path="/usuarios/:id"
          element={
            <Tela exige={EXIGE.usuarios}>
              <Usuario />
            </Tela>
          }
        />
      </Route>

      <Route
        element={
          <Protegido>
            <Casca titulo="Auditoria" />
          </Protegido>
        }
      >
        <Route
          path="/auditoria"
          element={
            <Tela exige={EXIGE.auditoria}>
              <Auditoria />
            </Tela>
          }
        />
      </Route>

      <Route
        element={
          <Protegido>
            <Casca titulo="Relatórios" />
          </Protegido>
        }
      >
        {/* Cada relatório com endereço próprio, e o recorte nele: é o que deixa
            mandar o link de um relatório já filtrado (UC15). */}
        <Route
          path="/relatorios"
          element={
            <Tela exige={EXIGE.relatorios}>
              <Relatorios />
            </Tela>
          }
        />
        <Route
          path="/relatorios/desempenho"
          element={
            <Tela exige={EXIGE.relatorios}>
              <RelatorioDesempenho />
            </Tela>
          }
        />
        <Route
          path="/relatorios/risco"
          element={
            <Tela exige={EXIGE.relatorios}>
              <RelatorioRisco />
            </Tela>
          }
        />
        <Route
          path="/relatorios/campanha"
          element={
            <Tela exige={EXIGE.relatorios}>
              <RelatorioCampanha />
            </Tela>
          }
        />
        <Route
          path="/relatorios/operacoes"
          element={
            <Tela exige={EXIGE.operacoes}>
              <RelatorioOperacoes />
            </Tela>
          }
        />
      </Route>

      <Route
        element={
          <Protegido>
            <Casca titulo="Configuração" />
          </Protegido>
        }
      >
        <Route
          path="/configuracao"
          element={
            <Tela exige={EXIGE.configuracao}>
              <Configuracao />
            </Tela>
          }
        />
      </Route>

      <Route
        element={
          <Protegido>
            <Casca titulo="Modelo preditivo" />
          </Protegido>
        }
      >
        <Route
          path="/modelo"
          element={
            <Tela exige={EXIGE.modelo}>
              <Modelo />
            </Tela>
          }
        />
      </Route>

      <Route
        element={
          <Protegido>
            <Casca titulo="Campanha" />
          </Protegido>
        }
      >
        <Route
          path="/campanha"
          element={
            <Tela exige={EXIGE.campanha}>
              <Campanha />
            </Tela>
          }
        />
      </Route>

      <Route
        element={
          <Protegido>
            <Casca titulo="Execuções do otimizador" />
          </Protegido>
        }
      >
        <Route
          path="/execucoes"
          element={
            <Tela exige={EXIGE.execucoes}>
              <Execucoes />
            </Tela>
          }
        />
        <Route
          path="/execucoes/comparar"
          element={
            <Tela exige={EXIGE.execucao}>
              <Comparacao />
            </Tela>
          }
        />
        <Route
          path="/execucoes/:id"
          element={
            <Tela exige={EXIGE.execucao}>
              <Execucao />
            </Tela>
          }
        />
      </Route>

      <Route
        element={
          <Protegido>
            <Casca titulo="Benchmark" />
          </Protegido>
        }
      >
        <Route
          path="/benchmark"
          element={
            <Tela exige={EXIGE.benchmark}>
              <Benchmark />
            </Tela>
          }
        />
      </Route>

      <Route
        element={
          <Protegido>
            <Casca titulo="Mensagens" />
          </Protegido>
        }
      >
        <Route
          path="/mensagens"
          element={
            <Tela exige={EXIGE.mensagens}>
              <Mensagens />
            </Tela>
          }
        />
      </Route>

      <Route
        element={
          <Protegido>
            <Casca titulo="Aprovação" />
          </Protegido>
        }
      >
        <Route
          path="/aprovacao"
          element={
            <Tela exige={EXIGE.aprovacao}>
              <Aprovacao />
            </Tela>
          }
        />
      </Route>

      <Route
        element={
          <Protegido>
            <Casca titulo="Assistente" />
          </Protegido>
        }
      >
        <Route
          path="/assistente"
          element={
            <Tela exige={EXIGE.assistente}>
              <Assistente />
            </Tela>
          }
        />
      </Route>

      <Route
        element={
          <Protegido>
            <Casca titulo="Meu desempenho" />
          </Protegido>
        }
      >
        <Route
          path="/meu-desempenho"
          element={
            <Tela exige={EXIGE.meuDesempenho}>
              <MeuDesempenho />
            </Tela>
          }
        />
      </Route>

      {/* Endereço que não existe mostra a página que diz isso, dentro da casca
          e com o menu (H79). Antes ia para o painel sem aviso, e o endereço
          pedido sumia da barra. Sem sessão, o portão leva ao login e, depois
          de entrar, de volta aqui. */}
      <Route
        element={
          <Protegido>
            <Casca titulo="Página não encontrada" />
          </Protegido>
        }
      >
        <Route path="*" element={<NaoEncontrada />} />
      </Route>
    </Routes>
  );
}
