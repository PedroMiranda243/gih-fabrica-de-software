/** Endereço que não existe: mostra o endereço pedido e nunca redireciona em silêncio. */
import { Link, useLocation } from "react-router-dom";

import Icone from "../componentes/Icone";
import { useTitulo } from "../componentes/Titulo";

export default function NaoEncontrada() {
  useTitulo("Página não encontrada");
  const { pathname } = useLocation();
  return (
    <div className="pagina pagina--aviso">
      <div className="aviso-pagina">
        <Icone nome="busca" className="aviso-pagina__icone" />
        <p className="aviso-pagina__titulo">Página não encontrada</p>
        <p>
          Não existe tela em <code>{pathname}</code>. O endereço pode ter sido digitado errado, ou o link está incompleto.
        </p>
        <Link to="/" className="botao botao--primario">
          Ir para o início
        </Link>
      </div>
    </div>
  );
}
