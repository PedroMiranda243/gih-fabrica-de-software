/**
 * Rotas da aplicação.
 *
 * Cada tela tem endereço próprio, e isso não é detalhe: o botão voltar precisa
 * funcionar, e um painel filtrado precisa poder ser mandado para outra pessoa
 * por link. Roteador à mão erraria exatamente esses dois pontos.
 */
import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import { useSessao } from "./api/contextoSessao";
import Casca from "./componentes/Casca";
import Carregando from "./componentes/Carregando";
import Importacao from "./paginas/Importacao";
import Login from "./paginas/Login";
import Painel from "./paginas/Painel";
import Parceiros from "./paginas/Parceiros";

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

export default function App() {
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
        <Route index element={<Painel />} />
      </Route>

      <Route
        element={
          <Protegido>
            <Casca titulo="Importação de relatório" />
          </Protegido>
        }
      >
        <Route path="/importacao" element={<Importacao />} />
      </Route>

      <Route
        element={
          <Protegido>
            <Casca titulo="Parceiros" />
          </Protegido>
        }
      >
        <Route path="/parceiros" element={<Parceiros />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
