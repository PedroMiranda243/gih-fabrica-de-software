/** O perfil não abre esta tela: diz qual perfil, qual endereço, e não chama a API. */
import { Link, useLocation } from "react-router-dom";

import { useSessao } from "../api/contextoSessao";
import Icone from "../componentes/Icone";
import { useTitulo } from "../componentes/Titulo";
import { ROTULO_PERFIL } from "../formato";

export default function SemAcesso() {
  useTitulo("Sem acesso");
  const { usuario } = useSessao();
  const { pathname } = useLocation();
  return (
    <div className="pagina pagina--aviso">
      <div className="aviso-pagina">
        <Icone nome="trava" className="aviso-pagina__icone" />
        <p className="aviso-pagina__titulo">O seu perfil não abre esta tela</p>
        <p>
          O perfil {ROTULO_PERFIL[usuario.perfil] ?? usuario.perfil} não tem acesso a <code>{pathname}</code>. As telas que você abre estão no menu. Se precisar desta, fale com o administrador do sistema.
        </p>
        <Link to="/" className="botao botao--primario">
          Ir para o início
        </Link>
      </div>
    </div>
  );
}
