/**
 * Entrada no sistema (UC01).
 *
 * A tela que o protótipo não tinha. Segue o sistema visual sem inventar
 * direção nova.
 *
 * **Nunca dizer se o login existe.** A API já responde igual para senha errada
 * e para usuário inexistente, de propósito (RNF11) — distinguir os dois
 * entregaria a lista de quem tem conta. A tela não pode desfazer isso sendo
 * "prestativa".
 */
import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { useSessao } from "../api/contextoSessao";
import "../estilos/login.css";

export default function Login() {
  const { usuario, entrar } = useSessao();
  const navegar = useNavigate();
  const lugar = useLocation();

  const [login, setLogin] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState(null);
  const [enviando, setEnviando] = useState(false);

  /* Volta para onde a pessoa queria ir antes de ser mandada para cá. */
  const destino = lugar.state?.de ?? "/";

  useEffect(() => {
    if (usuario) navegar(destino, { replace: true });
  }, [usuario, destino, navegar]);

  async function enviar(evento) {
    evento.preventDefault();
    setErro(null);
    setEnviando(true);
    try {
      await entrar(login.trim(), senha);
    } catch (e) {
      setErro(e);
      /* A senha sai do campo, o login fica: quem errou a senha digita a senha
         de novo, não o login inteiro. */
      setSenha("");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <main className="entrada">
      <form className="entrada__cartao" onSubmit={enviar}>
        <div className="entrada__marca">
          <span className="entrada__sigla">GIH</span>
          <h1 className="entrada__titulo">Growth Intelligence Hub</h1>
          <p className="entrada__subtitulo">
            Inteligência de crescimento para redes de parceiros
          </p>
        </div>

        {erro && (
          <div className="aviso" role="alert">
            <p className="aviso__titulo">{erro.message}</p>
            {erro.ajuda && <p className="aviso__ajuda">{erro.ajuda}</p>}
          </div>
        )}

        <div className="campo">
          <label htmlFor="login">Login</label>
          <input
            id="login"
            name="login"
            value={login}
            onChange={(e) => setLogin(e.target.value)}
            autoComplete="username"
            autoFocus
            required
          />
        </div>

        <div className="campo">
          <label htmlFor="senha">Senha</label>
          <input
            id="senha"
            name="senha"
            type="password"
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
            autoComplete="current-password"
            required
          />
        </div>

        <button className="botao" type="submit" disabled={enviando || !login || !senha}>
          {enviando ? "Entrando…" : "Entrar"}
        </button>

        <p className="entrada__rodape">
          Cinco tentativas falhas a partir da mesma origem bloqueiam novas tentativas por um tempo.
        </p>
      </form>
    </main>
  );
}
