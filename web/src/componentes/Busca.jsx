/**
 * Campo de busca que espera a digitação parar antes de mudar o endereço — e que
 * acompanha o endereço quando ele muda por fora (voltar, limpar filtros).
 */
import { useEffect, useRef, useState } from "react";

import { useAtraso } from "../api/ganchos";
import Icone from "./Icone";

export default function Busca({ id, valor, aoMudar, placeholder, ...props }) {
  const [texto, setTexto] = useState(valor ?? "");
  const atrasado = useAtraso(texto, 400);
  const ultimo = useRef(valor ?? "");

  useEffect(() => {
    if ((valor ?? "") !== ultimo.current) {
      ultimo.current = valor ?? "";
      setTexto(valor ?? "");
    }
  }, [valor]);

  useEffect(() => {
    if (atrasado !== ultimo.current) {
      ultimo.current = atrasado;
      aoMudar(atrasado.trim());
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [atrasado]);

  return (
    <div className="busca">
      <Icone nome="busca" className="busca__icone" />
      <input {...props} id={id} type="search" className="entrada busca__entrada" value={texto} onChange={(e) => setTexto(e.target.value)} placeholder={placeholder} autoComplete="off" spellCheck={false} />
    </div>
  );
}
