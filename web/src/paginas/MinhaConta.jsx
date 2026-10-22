/**
 * Minha conta — os seus dados (só leitura) e a troca da própria senha. A única
 * conferência da tela é a das duas digitações; o resto é o servidor quem diz.
 */
import { useRef, useState } from "react";

import { api, ErroDaApi } from "../api/cliente";
import { useSessao } from "../api/sessao";
import { Sucesso } from "../componentes/Estados";
import { Campo, ResumoDeErros, Senha, useErrosDoFormulario } from "../componentes/Formulario";
import Icone from "../componentes/Icone";
import { useTitulo } from "../componentes/Titulo";
import { comoDataHora, ROTULO_PERFIL } from "../formato";

export default function MinhaConta() {
  useTitulo("Minha conta");
  const { usuario } = useSessao();
  const [atual, setAtual] = useState("");
  const [nova, setNova] = useState("");
  const [deNovo, setDeNovo] = useState("");
  const [diferentes, setDiferentes] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [sucesso, setSucesso] = useState(null);
  const { erros, receber, limpar, limparCampo, registrar } = useErrosDoFormulario();
  const refDeNovo = useRef(null);

  async function trocar(evento) {
    evento.preventDefault();
    limpar();
    setSucesso(null);
    if (nova !== deNovo) {
      setDiferentes(true);
      refDeNovo.current?.focus();
      return;
    }
    setDiferentes(false);
    setEnviando(true);
    try {
      await api.post("/api/sessao/senha", { senha_atual: atual, senha_nova: nova });
      setAtual("");
      setNova("");
      setDeNovo("");
      setSucesso("Senha trocada. As outras sessões desta conta foram encerradas; esta continua aberta.");
    } catch (e) {
      if (e instanceof ErroDaApi) receber(e, { ordem: ["senha_atual", "senha_nova"] });
      else throw e;
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="pagina conta-pessoal">
      <section className="bloco" aria-labelledby="t-dados">
        <div className="bloco__cabeca">
          <h2 id="t-dados" className="bloco__titulo">
            Seus dados
          </h2>
          <p className="bloco__sub">Quem muda o nome e o perfil é o administrador.</p>
        </div>
        <dl className="pares pares--leitura">
          <div>
            <dt>Nome</dt>
            <dd>{usuario.nome}</dd>
          </div>
          <div>
            <dt>Login</dt>
            <dd>
              <code>{usuario.login}</code>
            </dd>
          </div>
          <div>
            <dt>Perfil</dt>
            <dd>{ROTULO_PERFIL[usuario.perfil] ?? usuario.perfil}</dd>
          </div>
          {usuario.criado_em && (
            <div>
              <dt>Conta criada em</dt>
              <dd>{comoDataHora(usuario.criado_em)}</dd>
            </div>
          )}
        </dl>
      </section>

      <section className="bloco" aria-labelledby="t-trocar">
        <div className="bloco__cabeca">
          <h2 id="t-trocar" className="bloco__titulo">
            Trocar a senha
          </h2>
        </div>
        <form className="formulario" onSubmit={trocar} noValidate>
          {sucesso && <Sucesso foco>{sucesso}</Sucesso>}
          <ResumoDeErros erros={erros} rotulos={{ senha_atual: "Senha atual", senha_nova: "Senha nova" }} />
          <Campo nome="senha_atual" rotulo="Senha atual" obrigatorio erro={erros.campos.senha_atual} ajuda="A senha com que você entrou.">
            {(a) => <Senha {...a} ref={registrar("senha_atual")} valor={atual} aoMudar={(x) => (setAtual(x), limparCampo("senha_atual"))} />}
          </Campo>
          <Campo nome="senha_nova" rotulo="Senha nova" obrigatorio erro={erros.campos.senha_nova} ajuda="O servidor confere a força; depois de salva, ninguém a vê.">
            {(a) => <Senha {...a} ref={registrar("senha_nova")} valor={nova} aoMudar={(x) => (setNova(x), limparCampo("senha_nova"), setDiferentes(false))} autoComplete="new-password" />}
          </Campo>
          <Campo nome="senha_de_novo" rotulo="Senha nova, de novo" obrigatorio erro={diferentes ? { mensagem: "As duas digitações da senha nova não são iguais." } : null} ajuda="Para pegar o erro de digitação antes de ele trancar a sua conta.">
            {(a) => <Senha {...a} ref={refDeNovo} valor={deNovo} aoMudar={(x) => (setDeNovo(x), setDiferentes(false))} autoComplete="new-password" />}
          </Campo>
          <div className="formulario__acoes">
            <button type="submit" className="botao botao--primario" disabled={enviando || !atual || !nova || !deNovo}>
              <Icone nome="trava" /> {enviando ? "Trocando…" : "Trocar a senha"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
