/**
 * O título da aba do navegador — H79.
 *
 * Até a Sprint 06, toda tela dizia "Growth Intelligence Hub" na aba: com três
 * abas abertas, ou no histórico do botão voltar, não havia como saber qual era
 * qual. Agora o título vai do mais específico ao mais geral — "Ponto Azul 2 ·
 * Parceiros · GIH" —, que é o que aparece quando a aba está estreita.
 *
 * A `Casca` sabe o nome da tela; o nome do item aberto, só a página de detalhe
 * sabe, e depois de carregar. Por isso a página o sobe por contexto, em vez de
 * escrever `document.title` ela mesma: o efeito da casca roda depois do da
 * página e apagaria o que ela escreveu.
 */
import { createContext, useContext, useEffect } from "react";

export const ContextoTituloDaAba = createContext(() => {});

export const PRODUTO = "GIH";

/** Do mais específico ao mais geral; o que não existe fica de fora. */
export function tituloDaAba(tela, detalhe) {
  return [detalhe, tela, PRODUTO].filter(Boolean).join(" · ");
}

/**
 * A página de detalhe diz qual item está aberto. Ao sair dela — de volta para a
 * lista, que usa a mesma casca —, o título volta a ser o da tela.
 */
export function useTituloDaAba(detalhe) {
  const definir = useContext(ContextoTituloDaAba);
  useEffect(() => {
    definir(detalhe || null);
    return () => definir(null);
  }, [definir, detalhe]);
}
