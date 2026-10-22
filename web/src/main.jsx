import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import "@fontsource-variable/atkinson-hyperlegible-next/wght.css";
import "./estilos/tokens.css";
import "./estilos/base.css";
import "./estilos/casca.css";
import "./estilos/componentes.css";
import "./estilos/telas.css";
import "./estilos/impressao.css";

import { ProvedorDeSessao } from "./api/sessao";
import App from "./App";
import { aplicarTemaInicial } from "./tema";

aplicarTemaInicial();

createRoot(document.getElementById("raiz")).render(
  <StrictMode>
    <BrowserRouter>
      <ProvedorDeSessao>
        <App />
      </ProvedorDeSessao>
    </BrowserRouter>
  </StrictMode>,
);
