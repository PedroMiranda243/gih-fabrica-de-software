import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import { ProvedorDeSessao } from "./api/sessao";
import App from "./App";
import "./estilos/base.css";
import "./estilos/casca.css";
import "./estilos/componentes.css";
import "./estilos/lista-e-cadastro.css";

createRoot(document.getElementById("raiz")).render(
  <StrictMode>
    <BrowserRouter>
      <ProvedorDeSessao>
        <App />
      </ProvedorDeSessao>
    </BrowserRouter>
  </StrictMode>,
);
