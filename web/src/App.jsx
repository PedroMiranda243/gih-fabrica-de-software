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
import Configuracao from "./paginas/Configuracao";
import Importacao from "./paginas/Importacao";
import Login from "./paginas/Login";
import Painel from "./paginas/Painel";
import Parceiro from "./paginas/Parceiro";
import Parceiros from "./paginas/Parceiros";
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
        {/* Cadastro e edição no mesmo componente, cada um com endereço próprio:
            o cadastro de um parceiro precisa poder ser aberto por link, e o
            botão voltar precisa devolver a lista com o filtro que ela tinha. */}
        <Route path="/parceiros/novo" element={<Parceiro />} />
        <Route path="/parceiros/:id" element={<Parceiro />} />
      </Route>

      <Route
        element={
          <Protegido>
            <Casca titulo="Usuários" />
          </Protegido>
        }
      >
        <Route path="/usuarios" element={<Usuarios />} />
        <Route path="/usuarios/novo" element={<Usuario />} />
        <Route path="/usuarios/:id" element={<Usuario />} />
      </Route>

      <Route
        element={
          <Protegido>
            <Casca titulo="Configuração" />
          </Protegido>
        }
      >
        <Route path="/configuracao" element={<Configuracao />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
