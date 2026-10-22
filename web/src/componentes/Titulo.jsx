/**
 * O título da tela: cada página diz o seu, e a casca o desenha no h1 e na aba,
 * do mais específico ao mais geral ("Ponto Azul 2 · Parceiros · GIH"). O caminho de
 * volta (a trilha) também mora no cabeçalho: a página diz os passos, a casca desenha.
 */
import { createContext, useContext, useEffect } from "react";

export const ContextoTitulo = createContext({ definir: () => {}, definirTrilha: () => {} });

export function useTitulo(titulo, ...contexto) {
  const { definir } = useContext(ContextoTitulo);
  const chave = [titulo, ...contexto].join("|");
  useEffect(() => {
    definir(titulo);
    document.title = [titulo, ...contexto.filter((c) => c && c !== titulo), "GIH"].filter(Boolean).join(" · ");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chave, definir]);
}

/** Os passos de volta até esta tela; o último é a própria tela (o h1) e não entra. */
export function useTrilha(passos) {
  const { definirTrilha } = useContext(ContextoTitulo);
  const chave = JSON.stringify(passos.map((p) => [p.rotulo, p.para ?? null]));
  useEffect(() => {
    definirTrilha(passos.slice(0, -1));
    return () => definirTrilha(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chave, definirTrilha]);
}
