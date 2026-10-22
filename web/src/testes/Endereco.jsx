import { useEffect } from "react";
import { useLocation } from "react-router-dom";

import { anotarEndereco } from "./ondeEsta";

/** Anota o endereço atual da aplicação de teste, a cada troca. */
export default function Endereco() {
  const lugar = useLocation();
  useEffect(() => anotarEndereco(lugar.pathname + lugar.search), [lugar]);
  return null;
}
