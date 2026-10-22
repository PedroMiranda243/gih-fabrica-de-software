/**
 * Entrada. Rótulos visíveis, Mostrar/Ocultar na senha, o botão desabilitado
 * enquanto falta campo. Na recusa, o texto do servidor e só a senha limpa — a tela
 * nunca diz se o login existe.
 *
 * A tela é a frente da bolsa de entrega fechada: a marca na faixa refletiva, de
 * ponta a ponta, e o formulário como a etiqueta na janela da bolsa.
 */
import { useEffect, useRef, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { ErroDaApi } from "../api/cliente";
import { useSessao } from "../api/sessao";
import Conferindo from "../componentes/Conferindo";
import { Campo, Senha } from "../componentes/Formulario";
import Icone from "../componentes/Icone";
import { useTema } from "../tema";

export default function Entrar() {
  const { usuario, conferindo, entrar } = useSessao();
  const { efetivo, alternar } = useTema();
  const lugar = useLocation();
  const navegar = useNavigate();
  const [login, setLogin] = useState("");
  const [senha, setSenha] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState(null);
  const refSenha = useRef(null);
  const expirou = Boolean(lugar.state?.expirou);
  const destino = lugar.state?.de && lugar.state.de !== "/entrar" ? lugar.state.de : "/";

  useEffect(() => {
    document.title = "Entrar · GIH";
  }, []);

  if (conferindo) return <Conferindo />;
  if (usuario && !enviando) return <Navigate to={destino} replace />;

  async function enviar(evento) {
    evento.preventDefault();
    if (!login || !senha) return;
    setEnviando(true);
    setErro(null);
    try {
      await entrar(login, senha);
      navegar(destino, { replace: true });
    } catch (e) {
      setErro(e instanceof ErroDaApi ? e : new ErroDaApi(0, null));
      setSenha("");
      setEnviando(false);
      if (!(e instanceof ErroDaApi) || e.status !== 429) refSenha.current?.focus();
    }
  }

  return (
    <div className="bolsa">
      <a className="pular" href="#entrar-form">
        Pular para o formulário
      </a>
      <div className="bolsa__costura" aria-hidden="true" />
      <button type="button" className="botao-cabecalho bolsa__tema" onClick={alternar} aria-label={efetivo === "escuro" ? "Mudar para o modo claro" : "Mudar para o modo escuro"}>
        <Icone nome={efetivo === "escuro" ? "sol" : "lua"} />
        <span>{efetivo === "escuro" ? "Modo claro" : "Modo escuro"}</span>
      </button>
      <header className="bolsa__faixa">
        <p className="bolsa__marca">
          <span className="bolsa__sigla">GIH</span>
          <span className="bolsa__nome">
            <span className="sr-only">— </span>Growth Intelligence Hub
          </span>
        </p>
      </header>
      {/* A frente da bolsa diz o que é o sistema: é texto de verdade, então fica
          numa região com nome, e não solto fora de todas. */}
      <section className="bolsa__frente" aria-label="Sobre o GIH">
        <p className="bolsa__lema">Inteligência de crescimento para redes de parceiros</p>
        <p className="bolsa__lacre">
          <span className="bolsa__lacre-sigla" aria-hidden="true">
            GIH
          </span>
          <span className="bolsa__lacre-texto">
            <strong>Acesso lacrado</strong>
            Cada perfil vê só a sua parte
          </span>
        </p>
      </section>
      <main className="bolsa__janela">
        <form className="entrada-form" id="entrar-form" onSubmit={enviar} noValidate>
          <h1 className="entrada-form__titulo">Entrar</h1>
          {expirou && (
            <div className="aviso aviso--neutro" role="status">
              <Icone nome="relogio" className="aviso__icone" />
              <p className="aviso__texto">A sua sessão terminou. Entre de novo para continuar de onde parou.</p>
            </div>
          )}
          {erro && (
            <div className="aviso aviso--erro" role="alert">
              <Icone nome="erro" className="aviso__icone" />
              <div className="aviso__texto">
                <p>{erro.message}</p>
                {erro.ajuda && <p className="aviso__ajuda">{erro.ajuda}</p>}
              </div>
            </div>
          )}
          <Campo nome="login" rotulo="Login">
            {(a) => <input {...a} className="entrada" value={login} onChange={(e) => setLogin(e.target.value)} autoComplete="username" autoCapitalize="none" spellCheck={false} />}
          </Campo>
          <Campo nome="senha" rotulo="Senha">
            {(a) => <Senha {...a} ref={refSenha} valor={senha} aoMudar={setSenha} />}
          </Campo>
          <button type="submit" className="botao botao--primario botao--largo" disabled={!login || !senha || enviando}>
            {enviando ? "Entrando…" : "Entrar"}
          </button>
          <p className="entrada-form__nota">
            <Icone nome="trava" />
            Cinco tentativas falhas a partir da mesma origem bloqueiam novas tentativas por um tempo.
          </p>
        </form>
      </main>
    </div>
  );
}
