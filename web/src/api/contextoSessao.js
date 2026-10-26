/**
 * O contexto da sessão e o que as telas leem dele. Fica num módulo sem componente
 * (o provedor está em sessao.jsx) para a recarga rápida do Vite funcionar.
 */
import { createContext, useContext } from "react";

export const Contexto = createContext(null);

export function useSessao() {
  return useContext(Contexto);
}

/** Se o perfil abre aquilo. Sem `telas` na sessão, a interface não adivinha: deixa a API responder. */
export function tem(usuario, ...telas) {
  if (!usuario) return false;
  if (!Array.isArray(usuario.telas)) return true;
  return telas.some((t) => usuario.telas.includes(t));
}
