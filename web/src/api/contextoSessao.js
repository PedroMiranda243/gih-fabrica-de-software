import { createContext, useContext } from "react";

/**
 * Contexto da sessão, separado do provedor.
 *
 * Arquivo de componente que também exporta hook quebra o recarregamento a
 * quente do Vite — ele só preserva estado quando o módulo exporta apenas
 * componentes. Separar custa um arquivo e mantém a edição de tela sem perder a
 * sessão a cada salvamento.
 */
export const ContextoSessao = createContext(null);

export function useSessao() {
  const contexto = useContext(ContextoSessao);
  if (!contexto) throw new Error("useSessao precisa estar dentro de ProvedorDeSessao.");
  return contexto;
}
