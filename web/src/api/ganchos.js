/**
 * Ganchos de dados que todas as telas usam: carregar com estado, filtros que
 * moram no endereço e operações longas acompanhadas a cada 2 segundos.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";

/**
 * Carrega com `buscar()` sempre que `chave` muda. Devolve o dado, o erro (o objeto
 * do servidor, preservado) e se está carregando. `recarregar` repete sem piscar.
 */
export function useCarregar(buscar, chave, { ativo = true } = {}) {
  const chaveAtual = `${ativo ? "1" : "0"}|${chave}`;
  const [estado, setEstado] = useState({ dados: null, erro: null, carregando: ativo, chave: null });
  const versao = useRef(0);
  const buscarRef = useRef(buscar);
  buscarRef.current = buscar;

  const executar = useCallback(
    (silencioso = false) => {
      if (!ativo) {
        setEstado({ dados: null, erro: null, carregando: false, chave: chaveAtual });
        return;
      }
      const minha = ++versao.current;
      if (!silencioso) setEstado((e) => ({ ...e, carregando: true, erro: null }));
      Promise.resolve()
        .then(() => buscarRef.current())
        .then((dados) => {
          if (minha === versao.current) setEstado({ dados, erro: null, carregando: false, chave: chaveAtual });
        })
        .catch((erro) => {
          if (erro?.name === "AbortError") return;
          if (minha === versao.current) setEstado((e) => ({ dados: silencioso ? e.dados : null, erro, carregando: false, chave: chaveAtual }));
        });
    },
    [ativo, chaveAtual],
  );

  useEffect(() => {
    executar(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chaveAtual]);

  const recarregar = useCallback(() => executar(true), [executar]);
  const substituir = useCallback((dados) => setEstado((e) => ({ ...e, dados: typeof dados === "function" ? dados(e.dados) : dados })), []);
  /* Enquanto a consulta da chave nova não volta, conta como carregando: o dado de
     antes pode continuar à vista (esmaecido), mas nunca passa por ser o novo. */
  const desatualizado = estado.chave !== chaveAtual;
  return {
    dados: ativo ? estado.dados : null,
    erro: desatualizado ? null : estado.erro,
    carregando: estado.carregando || (ativo && desatualizado),
    recarregar,
    substituir,
  };
}

/**
 * Os filtros de uma lista, no endereço. Mudar um filtro troca a consulta (não o
 * caminho) e volta para a página 1. Valor vazio sai do endereço.
 */
export function useFiltros() {
  const [busca, setBusca] = useSearchParams();
  const filtros = Object.fromEntries(busca.entries());

  const mudar = useCallback(
    (mudancas, { manterPagina = false } = {}) => {
      setBusca(
        (atual) => {
          const nova = new URLSearchParams(atual);
          for (const [chave, valor] of Object.entries(mudancas)) {
            if (valor === null || valor === undefined || valor === "") nova.delete(chave);
            else nova.set(chave, String(valor));
          }
          if (!manterPagina && !("pagina" in mudancas)) nova.delete("pagina");
          return nova;
        },
        { replace: false },
      );
    },
    [setBusca],
  );

  return [filtros, mudar];
}

/**
 * Acompanha uma operação longa: enquanto `situacao === "EM_ANDAMENTO"`, consulta
 * a cada 2 segundos. A tela pode ser deixada e reaberta: quem chama passa o id
 * que o estado do servidor trouxe.
 */
export function useAcompanhar(id, buscar, aoTerminar) {
  /* O que chegou, junto do id de que veio: ao trocar de operação, a anterior não
     aparece como se fosse a nova. */
  const [estado, setEstado] = useState({ id: null, atual: null, erro: null });
  const buscarRef = useRef(buscar);
  const terminarRef = useRef(aoTerminar);
  /* As funções mais recentes de quem chama, sem refazer a consulta quando elas mudam. */
  useEffect(() => {
    buscarRef.current = buscar;
    terminarRef.current = aoTerminar;
  });

  useEffect(() => {
    if (id === null || id === undefined) return undefined;
    let vivo = true;
    let relogio = null;
    async function consultar() {
      try {
        const r = await buscarRef.current(id);
        if (!vivo) return;
        setEstado({ id, atual: r, erro: null });
        if (r?.situacao === "EM_ANDAMENTO") relogio = setTimeout(consultar, 2000);
        else terminarRef.current?.(r);
      } catch (e) {
        if (!vivo) return;
        setEstado((anterior) => ({ id, atual: anterior.id === id ? anterior.atual : null, erro: e }));
        if (e?.status !== 401 && e?.status !== 404) relogio = setTimeout(consultar, 4000);
      }
    }
    consultar();
    return () => {
      vivo = false;
      clearTimeout(relogio);
    };
  }, [id]);

  const desta = id !== null && id !== undefined && estado.id === id;
  return { atual: desta ? estado.atual : null, erro: desta ? estado.erro : null };
}

/** Espera a digitação parar antes de consultar. */
export function useAtraso(valor, ms = 350) {
  const [atrasado, setAtrasado] = useState(valor);
  useEffect(() => {
    const t = setTimeout(() => setAtrasado(valor), ms);
    return () => clearTimeout(t);
  }, [valor, ms]);
  return atrasado;
}

/** Conta os segundos enquanto `ativo`. */
export function useSegundos(ativo) {
  const [segundos, setSegundos] = useState(0);
  const [estavaAtivo, setEstavaAtivo] = useState(ativo);
  /* Ao parar ou começar de novo, a conta volta a zero — ajustada na própria
     renderização, e não num efeito, que desenharia o número velho uma vez. */
  if (ativo !== estavaAtivo) {
    setEstavaAtivo(ativo);
    setSegundos(0);
  }
  useEffect(() => {
    if (!ativo) return undefined;
    const inicio = Date.now();
    const t = setInterval(() => setSegundos(Math.floor((Date.now() - inicio) / 1000)), 250);
    return () => clearInterval(t);
  }, [ativo]);
  return segundos;
}
