/**
 * As rotas. Cada tela tem endereço próprio (os mesmos de hoje), e a guarda lê só
 * `usuario.telas`: quem não abre a tela vê "Sem acesso" sem a API ser chamada.
 */
import { lazy, Suspense, useEffect, useRef } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import { tem, useSessao } from "./api/contextoSessao";
import Casca from "./componentes/Casca";
import Conferindo from "./componentes/Conferindo";
import { Carregando } from "./componentes/Estados";
import { EXIGE } from "./navegacao/telas";
const Ajuda = lazy(() => import("./paginas/Ajuda"));
const Aprovacao = lazy(() => import("./paginas/Aprovacao"));
const Assistente = lazy(() => import("./paginas/Assistente"));
const Auditoria = lazy(() => import("./paginas/Auditoria"));
const Benchmark = lazy(() => import("./paginas/Benchmark"));
const Campanha = lazy(() => import("./paginas/Campanha"));
const Comparacao = lazy(() => import("./paginas/Comparacao"));
const Configuracao = lazy(() => import("./paginas/Configuracao"));
import Entrar from "./paginas/Entrar";
const Execucao = lazy(() => import("./paginas/Execucao"));
const Execucoes = lazy(() => import("./paginas/Execucoes"));
const Importacao = lazy(() => import("./paginas/Importacao"));
const Mensagens = lazy(() => import("./paginas/Mensagens"));
const MeuDesempenho = lazy(() => import("./paginas/MeuDesempenho"));
const MinhaConta = lazy(() => import("./paginas/MinhaConta"));
const Modelo = lazy(() => import("./paginas/Modelo"));
import NaoEncontrada from "./paginas/NaoEncontrada";
import Painel from "./paginas/Painel";
const Parceiro = lazy(() => import("./paginas/Parceiro"));
const Parceiros = lazy(() => import("./paginas/Parceiros"));
const RelatorioCampanha = lazy(() => import("./paginas/RelatorioCampanha"));
const RelatorioDesempenho = lazy(() => import("./paginas/RelatorioDesempenho"));
const RelatorioOperacoes = lazy(() => import("./paginas/RelatorioOperacoes"));
const RelatorioRisco = lazy(() => import("./paginas/RelatorioRisco"));
const Relatorios = lazy(() => import("./paginas/Relatorios"));
import SemAcesso from "./paginas/SemAcesso";
const Usuario = lazy(() => import("./paginas/Usuario"));
const Usuarios = lazy(() => import("./paginas/Usuarios"));

function Protegido({ children }) {
  const { usuario, conferindo, expirou } = useSessao();
  const lugar = useLocation();
  if (conferindo) return <Conferindo />;
  if (!usuario) return <Navigate to="/entrar" replace state={{ de: lugar.pathname + lugar.search + lugar.hash, expirou }} />;
  return children;
}

/** A tela que o perfil abre — ou a página que diz que ele não abre, sem chamar a API. */
function Tela({ exige, children }) {
  const { usuario } = useSessao();
  return tem(usuario, ...exige) ? children : <SemAcesso />;
}

function Inicio() {
  const { usuario } = useSessao();
  if (!tem(usuario, ...EXIGE.painel) && tem(usuario, ...EXIGE.meuDesempenho) && Array.isArray(usuario.telas)) return <Navigate to="/meu-desempenho" replace />;
  return (
    <Tela exige={EXIGE.painel}>
      <Painel />
    </Tela>
  );
}

/** Ao mudar o caminho (não o filtro), o foco vai para o título da tela nova — ou ao bloco da âncora. */
function FocoNaTroca() {
  const { pathname, hash } = useLocation();
  const anterior = useRef(pathname);
  useEffect(() => {
    if (anterior.current === pathname) return;
    anterior.current = pathname;
    if (hash) return;
    window.scrollTo(0, 0);
    requestAnimationFrame(() => document.getElementById("titulo-da-tela")?.focus({ preventScroll: true }));
  }, [pathname, hash]);
  return null;
}

const T = (exige, Componente) => (
  <Tela exige={exige}>
    <Suspense fallback={<Carregando rotulo="Abrindo a tela" linhas={6} />}>
      <Componente />
    </Suspense>
  </Tela>
);

export default function App() {
  return (
    <>
      <Routes>
        <Route path="/entrar" element={<Entrar />} />
        <Route
          element={
            <Protegido>
              <Casca />
            </Protegido>
          }
        >
          <Route index element={<Inicio />} />
          <Route path="meu-desempenho" element={T(EXIGE.meuDesempenho, MeuDesempenho)} />
          <Route path="importacao" element={T(EXIGE.importacao, Importacao)} />
          <Route path="parceiros" element={T(EXIGE.parceiros, Parceiros)} />
          <Route path="parceiros/novo" element={T(EXIGE.parceiros, Parceiro)} />
          <Route path="parceiros/:id" element={T(EXIGE.parceiros, Parceiro)} />
          <Route path="assistente" element={T(EXIGE.assistente, Assistente)} />
          <Route path="relatorios" element={T(EXIGE.relatorios, Relatorios)} />
          <Route path="relatorios/desempenho" element={T(EXIGE.relatorios, RelatorioDesempenho)} />
          <Route path="relatorios/risco" element={T(EXIGE.relatorios, RelatorioRisco)} />
          <Route path="relatorios/campanha" element={T(EXIGE.relatorios, RelatorioCampanha)} />
          <Route path="relatorios/operacoes" element={T(EXIGE.operacoes, RelatorioOperacoes)} />
          <Route path="modelo" element={T(EXIGE.modelo, Modelo)} />
          <Route path="campanha" element={T(EXIGE.campanha, Campanha)} />
          <Route path="execucoes" element={T(EXIGE.execucoes, Execucoes)} />
          <Route path="execucoes/comparar" element={T(EXIGE.execucao, Comparacao)} />
          <Route path="execucoes/:id" element={T(EXIGE.execucao, Execucao)} />
          <Route path="benchmark" element={T(EXIGE.benchmark, Benchmark)} />
          <Route path="mensagens" element={T(EXIGE.mensagens, Mensagens)} />
          <Route path="aprovacao" element={T(EXIGE.aprovacao, Aprovacao)} />
          <Route path="usuarios" element={T(EXIGE.usuarios, Usuarios)} />
          <Route path="usuarios/novo" element={T(EXIGE.usuarios, Usuario)} />
          <Route path="usuarios/:id" element={T(EXIGE.usuarios, Usuario)} />
          <Route path="auditoria" element={T(EXIGE.auditoria, Auditoria)} />
          <Route path="configuracao" element={T(EXIGE.configuracao, Configuracao)} />
          <Route path="conta" element={<Suspense fallback={<Carregando rotulo="Abrindo a tela" linhas={4} />}><MinhaConta /></Suspense>} />
          <Route path="ajuda" element={<Suspense fallback={<Carregando rotulo="Abrindo a tela" linhas={4} />}><Ajuda /></Suspense>} />
          <Route path="*" element={<NaoEncontrada />} />
        </Route>
      </Routes>
      <FocoNaTroca />
    </>
  );
}
