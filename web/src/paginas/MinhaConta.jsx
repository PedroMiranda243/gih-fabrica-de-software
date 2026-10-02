/**
 * Minha conta (UC01-A4 · RF07 · H92): os dados de quem está usando o sistema, e a
 * troca da própria senha.
 *
 * A rota de troca existe desde a H19, mas nunca teve tela: a senha só se trocava
 * pela API. **A validação é do servidor** (regra 2.4) — a senha atual que não
 * confere e a nova que é fraca voltam como erro do campo, e a tela as mostra
 * embaixo dele. A única conferência daqui é a das duas digitações da senha
 * nova, que o servidor não tem como fazer: ele só recebe uma.
 */
import { useState } from "react";

import { api } from "../api/cliente";
import { useSessao } from "../api/contextoSessao";
import Campo from "../componentes/Campo";
import EntradaDeSenha from "../componentes/EntradaDeSenha";
import { ROTULO_PERFIL } from "../formato";
import "../estilos/usuarios.css";

const VAZIO = { senha_atual: "", senha_nova: "", confirmacao: "" };
const ORDEM = ["senha_atual", "senha_nova", "confirmacao"];

export default function MinhaConta() {
  const { usuario } = useSessao();
  const [form, setForm] = useState(VAZIO);
  const [erro, setErro] = useState(null);
  const [diferentes, setDiferentes] = useState(false);
  const [trocada, setTrocada] = useState(false);
  const [enviando, setEnviando] = useState(false);

  const erroDoCampo = Object.fromEntries((erro?.campos ?? []).map((c) => [c.campo, c]));
  if (diferentes) erroDoCampo.confirmacao = { mensagem: "As duas digitações da senha nova não são iguais." };

  function mudar(campo, valor) {
    setForm((f) => ({ ...f, [campo]: valor }));
    setTrocada(false);
    if (campo !== "senha_atual") setDiferentes(false);
  }

  async function trocar(evento) {
    evento.preventDefault();
    setErro(null);
    setTrocada(false);
    if (form.senha_nova !== form.confirmacao) {
      setDiferentes(true);
      document.getElementById("campo-confirmacao")?.focus();
      return;
    }
    setEnviando(true);
    try {
      await api.post("/api/sessao/senha", {
        senha_atual: form.senha_atual,
        senha_nova: form.senha_nova,
      });
      setForm(VAZIO);
      setTrocada(true);
    } catch (e) {
      setErro(e);
      const primeiro = ORDEM.find((c) => e.campos?.some((x) => x.campo === c));
      if (primeiro) document.getElementById(`campo-${primeiro}`)?.focus();
    } finally {
      setEnviando(false);
    }
  }

  return (
    <>
      <section className="painel" aria-labelledby="titulo-dados">
        <div className="painel__cabecalho">
          <h2 className="painel__titulo" id="titulo-dados">
            Seus dados
          </h2>
          <span className="painel__nota">quem muda o nome e o perfil é o administrador</span>
        </div>
        <dl className="conta-dados">
          <div>
            <dt>Nome</dt>
            <dd>{usuario.nome}</dd>
          </div>
          <div>
            <dt>Login</dt>
            <dd className="num">{usuario.login}</dd>
          </div>
          <div>
            <dt>Perfil</dt>
            <dd>{ROTULO_PERFIL[usuario.perfil] ?? usuario.perfil}</dd>
          </div>
        </dl>
      </section>

      <section className="painel" aria-labelledby="titulo-senha">
        <div className="painel__cabecalho">
          <h2 className="painel__titulo" id="titulo-senha">
            Trocar a senha
          </h2>
          <span className="painel__nota">* obrigatório</span>
        </div>

        <form className="conta conta--coluna" onSubmit={trocar} noValidate>
          {trocada && (
            <div className="aviso aviso--sucesso conta__aviso" role="status">
              <p className="aviso__titulo">Senha trocada.</p>
              <p className="aviso__ajuda">
                As outras sessões desta conta foram encerradas; esta continua aberta.
              </p>
            </div>
          )}

          {/* O erro que não é de um campo — o serviço fora do ar, por exemplo. */}
          {erro && !erro.campos?.length && (
            <div className="aviso conta__aviso" role="alert">
              <p className="aviso__titulo">{erro.message}</p>
              {erro.ajuda && <p className="aviso__ajuda">{erro.ajuda}</p>}
            </div>
          )}

          <Campo
            id="senha_atual"
            rotulo="Senha atual"
            obrigatorio
            erro={erroDoCampo.senha_atual}
            ajuda="A senha com que você entrou."
          >
            <EntradaDeSenha
              id="campo-senha_atual"
              de="a senha atual"
              autoComplete="current-password"
              value={form.senha_atual}
              onChange={(e) => mudar("senha_atual", e.target.value)}
            />
          </Campo>

          <Campo
            id="senha_nova"
            rotulo="Senha nova"
            obrigatorio
            erro={erroDoCampo.senha_nova}
            ajuda="O servidor confere a força; depois de salva, ninguém a vê."
          >
            <EntradaDeSenha
              id="campo-senha_nova"
              de="a senha nova"
              autoComplete="new-password"
              value={form.senha_nova}
              onChange={(e) => mudar("senha_nova", e.target.value)}
            />
          </Campo>

          <Campo
            id="confirmacao"
            rotulo="Senha nova, de novo"
            obrigatorio
            erro={erroDoCampo.confirmacao}
            ajuda="Para pegar o erro de digitação antes de ele trancar a sua conta."
          >
            <EntradaDeSenha
              id="campo-confirmacao"
              de="a senha nova, de novo"
              autoComplete="new-password"
              value={form.confirmacao}
              onChange={(e) => mudar("confirmacao", e.target.value)}
            />
          </Campo>

          <div className="conta__acoes">
            <button className="botao" type="submit" disabled={enviando}>
              {enviando ? "Trocando…" : "Trocar a senha"}
            </button>
          </div>
        </form>
      </section>
    </>
  );
}
