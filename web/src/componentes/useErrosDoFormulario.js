import { useCallback, useRef, useState } from "react";

import { ErroDaApi } from "../api/cliente";

/**
 * Distribui o erro do servidor: os campos que ele nomeou vão para baixo de cada
 * campo; o resto, para o topo. Foco no primeiro campo errado.
 */
export function useErrosDoFormulario() {
  const [erros, setErros] = useState({ campos: {}, topo: null, ajudaTopo: null, erro: null });
  const referencias = useRef({});

  const registrar = useCallback((nome) => (el) => {
    if (el) referencias.current[nome] = el;
  }, []);

  const receber = useCallback((erro, { mapa = {}, ordem = [] } = {}) => {
    if (!(erro instanceof ErroDaApi)) {
      setErros({ campos: {}, topo: "Não foi possível concluir. Tente de novo.", ajudaTopo: null, erro: null });
      return;
    }
    const campos = {};
    const soltos = [];
    for (const c of erro.campos ?? []) {
      const nome = mapa[c.campo] ?? c.campo;
      if (nome in referencias.current) campos[nome] = { mensagem: c.mensagem, ajuda: c.ajuda ?? null };
      else soltos.push(c.mensagem);
    }
    const temCampos = Object.keys(campos).length > 0;
    const topo = soltos.length ? soltos.join(" ") : erro.message;
    setErros({ campos, topo, ajudaTopo: erro.ajuda, erro, resumo: temCampos });
    const primeiro = [...ordem, ...Object.keys(referencias.current)].find((n) => campos[n]);
    if (primeiro) requestAnimationFrame(() => referencias.current[primeiro]?.focus());
  }, []);

  const limpar = useCallback(() => setErros({ campos: {}, topo: null, ajudaTopo: null, erro: null }), []);
  const limparCampo = useCallback(
    (nome) =>
      setErros((e) => {
        if (!e.campos[nome]) return e;
        const campos = { ...e.campos };
        delete campos[nome];
        return { ...e, campos };
      }),
    [],
  );

  return { erros, receber, limpar, limparCampo, registrar };
}
