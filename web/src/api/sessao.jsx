/**
 * Estado da sessão, num lugar só.
 *
 * A sessão tem estado **no servidor** (RF02): encerrar invalida de verdade, e
 * não apenas apaga o cookie do navegador. Por isso a interface nunca guarda o
 * usuário em `localStorage` — ela pergunta ao servidor quem está autenticado.
 * Confiar num usuário guardado localmente faria a tela continuar mostrando
 * sessão ativa depois de a senha ser trocada em outro lugar, que é exatamente
 * o cenário que a revogação no servidor existe para cobrir.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { aoEncerrarSessao, api } from "./cliente";
import { ContextoSessao } from "./contextoSessao";

export function ProvedorDeSessao({ children }) {
  const [usuario, setUsuario] = useState(null);
  /* Três estados, não dois: "ainda não sei" é diferente de "não autenticado".
     Sem isso a tela pisca o login antes de descobrir que havia sessão. */
  const [conferindo, setConferindo] = useState(true);

  useEffect(() => {
    let vivo = true;
    api
      .get("/api/sessao/atual")
      .then((atual) => vivo && setUsuario(atual))
      .catch(() => vivo && setUsuario(null))
      .finally(() => vivo && setConferindo(false));
    return () => {
      vivo = false;
    };
  }, []);

  /* A sessão terminou com a tela aberta? (H96) Só vale para quem estava dentro:
     o 401 da primeira conferência, de quem ainda não entrou, não é "a sua
     sessão terminou" — é só "você não entrou". */
  const [encerrada, setEncerrada] = useState(false);
  const dentro = useRef(false);
  useEffect(() => {
    dentro.current = Boolean(usuario);
  }, [usuario]);

  /* Qualquer 401 vindo de qualquer requisição derruba o usuário local. A
     sessão pode ter expirado ou sido revogada enquanto a aba estava aberta, e
     a tela precisa acompanhar — e dizer por que a pessoa voltou ao login. */
  useEffect(
    () =>
      aoEncerrarSessao(() => {
        if (dentro.current) setEncerrada(true);
        setUsuario(null);
      }),
    [],
  );

  const entrar = useCallback(async (login, senha) => {
    const sessao = await api.post("/api/sessao", { login, senha });
    setEncerrada(false);
    setUsuario(sessao.usuario);
    return sessao.usuario;
  }, []);

  const sair = useCallback(async () => {
    try {
      await api.delete("/api/sessao");
    } finally {
      /* Mesmo que a chamada falhe, o usuário pediu para sair: a tela obedece.
         O servidor já invalidou, ou invalidará na expiração. Sair de propósito
         não é "a sessão terminou". */
      dentro.current = false;
      setEncerrada(false);
      setUsuario(null);
    }
  }, []);

  const valor = useMemo(
    () => ({ usuario, conferindo, encerrada, entrar, sair }),
    [usuario, conferindo, encerrada, entrar, sair],
  );

  return <ContextoSessao.Provider value={valor}>{children}</ContextoSessao.Provider>;
}
