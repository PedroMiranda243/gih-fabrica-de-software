/**
 * Tema claro / escuro. Três estados: o do sistema (padrão), claro escolhido e
 * escuro escolhido. A escolha explícita vence a do sistema e fica lembrada no
 * aparelho — o localStorage guarda só isso. A impressão sai sempre no claro (CSS).
 */
import { useCallback, useEffect, useState } from "react";

const CHAVE = "gih-tema";
const consulta = () => window.matchMedia?.("(prefers-color-scheme: dark)");

function lerEscolha() {
  try {
    const v = window.localStorage.getItem(CHAVE);
    return v === "claro" || v === "escuro" ? v : null;
  } catch {
    return null;
  }
}

export function aplicarTemaInicial() {
  const escolha = lerEscolha();
  if (escolha) document.documentElement.dataset.tema = escolha;
}

export function useTema() {
  const [escolha, setEscolha] = useState(lerEscolha);
  const [doSistema, setDoSistema] = useState(() => (consulta()?.matches ? "escuro" : "claro"));

  useEffect(() => {
    const mq = consulta();
    if (!mq) return undefined;
    const ouvir = (e) => setDoSistema(e.matches ? "escuro" : "claro");
    mq.addEventListener("change", ouvir);
    return () => mq.removeEventListener("change", ouvir);
  }, []);

  const efetivo = escolha ?? doSistema;

  useEffect(() => {
    if (escolha) document.documentElement.dataset.tema = escolha;
    else delete document.documentElement.dataset.tema;
    const cor = getComputedStyle(document.documentElement).getPropertyValue("--cor-barra-navegador").trim();
    if (cor) document.querySelector('meta[name="theme-color"]:not([media])')?.setAttribute("content", cor);
  }, [escolha, efetivo]);

  const alternar = useCallback(() => {
    const novo = efetivo === "escuro" ? "claro" : "escuro";
    try {
      window.localStorage.setItem(CHAVE, novo);
    } catch {
      /* Sem armazenamento: a escolha vale até recarregar. */
    }
    setEscolha(novo);
  }, [efetivo]);

  return { efetivo, alternar };
}
