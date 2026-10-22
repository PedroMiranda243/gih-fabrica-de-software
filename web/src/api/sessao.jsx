/**
 * A sessão de quem está usando. O servidor é a fonte: ao abrir, a interface
 * pergunta `GET /api/sessao/atual`; nada fica guardado no navegador.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { aoEncerrarSessao, api, ErroDaApi } from "./cliente";

const Contexto = createContext(null);

export function ProvedorDeSessao({ children }) {
  const [usuario, setUsuario] = useState(null);
  const [conferindo, setConferindo] = useState(true);
  const [expirou, setExpirou] = useState(false);
  const navegar = useNavigate();
  const dentro = useRef(false);

  useEffect(() => {
    let vivo = true;
    api
      .get("/api/sessao/atual")
      .then((u) => {
        if (!vivo) return;
        dentro.current = true;
        setUsuario(u);
      })
      .catch(() => {
        if (vivo) setUsuario(null);
      })
      .finally(() => {
        if (vivo) setConferindo(false);
      });
    return () => {
      vivo = false;
    };
  }, []);

  /* A sessão que termina no meio: a casca leva à entrada com o aviso, guardando o
     endereço (com os filtros) para devolver a pessoa ao mesmo lugar depois. */
  useEffect(
    () =>
      aoEncerrarSessao(() => {
        if (!dentro.current) return;
        dentro.current = false;
        setExpirou(true);
        setUsuario(null);
      }),
    [],
  );

  const entrar = useCallback(async (login, senha) => {
    const resposta = await api.post("/api/sessao", { login, senha });
    dentro.current = true;
    setExpirou(false);
    setUsuario(resposta.usuario);
    return resposta.usuario;
  }, []);

  const sair = useCallback(async () => {
    try {
      await api.delete("/api/sessao");
    } catch (erro) {
      if (!(erro instanceof ErroDaApi)) throw erro;
    }
    dentro.current = false;
    setExpirou(false);
    setUsuario(null);
    navegar("/entrar", { replace: true });
  }, [navegar]);

  const valor = useMemo(() => ({ usuario, conferindo, expirou, entrar, sair, setUsuario }), [usuario, conferindo, expirou, entrar, sair]);
  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function useSessao() {
  return useContext(Contexto);
}

/** Se o perfil abre aquilo. Sem `telas` na sessão, a interface não adivinha: deixa a API responder. */
export function tem(usuario, ...telas) {
  if (!usuario) return false;
  if (!Array.isArray(usuario.telas)) return true;
  return telas.some((t) => usuario.telas.includes(t));
}
