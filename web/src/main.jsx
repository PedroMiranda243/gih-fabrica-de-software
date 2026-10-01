import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import { ProvedorDeSessao } from "./api/sessao";
import App from "./App";
import "./estilos/base.css";
import "./estilos/casca.css";
import "./estilos/componentes.css";
import "./estilos/lista-e-cadastro.css";
/* Por último: as regras da folha impressa precisam ganhar das folhas das telas. */
import "./estilos/impressao.css";
import { imprimirNoTemaClaro } from "./temas/impressao";

imprimirNoTemaClaro();

createRoot(document.getElementById("raiz")).render(
  <StrictMode>
    <BrowserRouter>
      <ProvedorDeSessao>
        <App />
      </ProvedorDeSessao>
    </BrowserRouter>
  </StrictMode>,
);
