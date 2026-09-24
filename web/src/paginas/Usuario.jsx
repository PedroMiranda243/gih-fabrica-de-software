/**
 * Conta de um usuário (UC02): criar, editar nome e perfil, desativar e reativar.
 *
 * **A validação é do servidor** (regra 2.4): formato do login, força da senha,
 * último administrador. A tela mostra a recusa no campo certo ou num aviso com o
 * que fazer — e, no login repetido, a conta que já o usa, porque o caso comum é
 * a conta desativada de quem voltou (UC02-E1).
 *
 * **O perfil Parceiro não é oferecido aqui.** Ele exige vincular um parceiro, o
 * Administrador não lista parceiros, e o portal do parceiro (H39) ainda não
 * existe. Uma conta Parceiro criada pela API aparece e pode ter o nome mudado;
 * o perfil dela, só pela API, até a H39.
 */
import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";

import { api } from "../api/cliente";
import { useSessao } from "../api/contextoSessao";
import Campo from "../componentes/Campo";
import { Esqueleto } from "../componentes/Carregando";
import Confirmacao from "../componentes/Confirmacao";
import EstadoVazio from "../componentes/EstadoVazio";
import { ROTULO_PERFIL } from "../formato";
import "../estilos/usuarios.css";

const PERFIS_DA_TELA = ["ADMINISTRADOR", "GESTOR", "ANALISTA"];
const ROTULO_CAMPO = { login: "Login", nome: "Nome", senha: "Senha inicial", perfil: "Perfil" };

export default function Usuario() {
  const { id } = useParams();
  // A chave recria o componente ao trocar de conta: sem ela, abrir outra conta
  // pelo link da recusa reaproveitaria o estado da anterior.
  return <Conta key={id ?? "novo"} id={id} />;
}

function Conta({ id }) {
  const novo = !id;
  const navegar = useNavigate();
  const lugar = useLocation();
  const lista = lugar.state?.lista ?? "/usuarios";
  const { usuario: eu } = useSessao();

  const [conta, setConta] = useState(null);
  const [naoExiste, setNaoExiste] = useState(false);
  const [form, setForm] = useState({ login: "", nome: "", senha: "", perfil: "GESTOR" });
  const [erro, setErro] = useState(null);
  const [sucesso, setSucesso] = useState(lugar.state?.aviso ?? null);
  const [enviando, setEnviando] = useState(false);
  const [confirmando, setConfirmando] = useState(false);
  const [avisoSituacao, setAvisoSituacao] = useState(null);

  useEffect(() => {
    if (novo) return undefined;
    let vivo = true;
    api
      .get(`/api/usuarios/${id}`)
      .then((u) => {
        if (!vivo) return;
        setConta(u);
        setForm({ login: u.login, nome: u.nome, senha: "", perfil: u.perfil });
      })
      .catch((e) => {
        if (!vivo) return;
        if (e.status === 404) setNaoExiste(true);
        else setErro(e);
      });
    return () => {
      vivo = false;
    };
  }, [id, novo]);

  if (naoExiste) {
    return (
      <EstadoVazio
        titulo="Usuário não encontrado"
        texto="O endereço aponta para uma conta que não existe."
        acao={{ para: lista, rotulo: "Voltar para os usuários" }}
      />
    );
  }

  if (!novo && !conta) {
    // Sem a conta não há o que editar: o formulário vazio convidaria a salvar
    // em cima de nada. Fica só o aviso, ou o esqueleto enquanto carrega.
    return erro ? (
      <div className="aviso" role="alert">
        <p className="aviso__titulo">{erro.message}</p>
        {erro.ajuda && <p className="aviso__ajuda">{erro.ajuda}</p>}
      </div>
    ) : (
      <section className="painel" aria-busy="true" aria-label="Carregando a conta">
        <div className="conta">
          <Esqueleto altura={180} />
        </div>
      </section>
    );
  }

  const erroDoCampo = Object.fromEntries((erro?.campos ?? []).map((c) => [c.campo, c]));
  const existente = erro?.status === 409 ? erro.corpo?.detail?.existente : null;
  const perfis = conta?.perfil === "PARCEIRO" ? [...PERFIS_DA_TELA, "PARCEIRO"] : PERFIS_DA_TELA;
  const souEu = conta && eu?.id === conta.id;

  function mudar(campo, valor) {
    setForm((f) => ({ ...f, [campo]: valor }));
    setSucesso(null);
  }

  async function salvar(evento) {
    evento.preventDefault();
    setErro(null);
    setSucesso(null);
    setEnviando(true);
    try {
      if (novo) {
        const criado = await api.post("/api/usuarios", form);
        navegar(`/usuarios/${criado.id}`, {
          replace: true,
          state: {
            lista,
            aviso: `Usuário criado. ${criado.nome} já pode entrar com o login ${criado.login}.`,
          },
        });
        return;
      }
      const corpo = { nome: form.nome };
      if (form.perfil !== conta.perfil) corpo.perfil = form.perfil;
      const salvo = await api.patch(`/api/usuarios/${id}`, corpo);
      setConta(salvo);
      setForm((f) => ({ ...f, nome: salvo.nome, perfil: salvo.perfil }));
      setSucesso(
        corpo.perfil
          ? "Alterações salvas. O perfil novo vale já na próxima ação da pessoa."
          : "Alterações salvas.",
      );
    } catch (e) {
      setErro(e);
      const primeiro = ["login", "nome", "senha", "perfil"].find((c) =>
        e.campos?.some((x) => x.campo === c),
      );
      if (primeiro) document.getElementById(`campo-${primeiro}`)?.focus();
    } finally {
      setEnviando(false);
    }
  }

  async function mudarSituacao(ativo) {
    setAvisoSituacao(null);
    setEnviando(true);
    try {
      const salvo = await api.patch(`/api/usuarios/${id}`, { ativo });
      setConta(salvo);
      setAvisoSituacao({
        tipo: "sucesso",
        texto: ativo
          ? "Conta reativada. A pessoa volta a entrar com a senha que tinha."
          : "Conta desativada. As sessões abertas foram encerradas agora.",
      });
    } catch (e) {
      setAvisoSituacao({ tipo: "erro", erro: e });
    } finally {
      setEnviando(false);
      setConfirmando(false);
    }
  }

  return (
    <>
      <nav className="trilha" aria-label="Você está em">
        <Link to={lista}>Usuários</Link>
        <span aria-hidden="true">›</span>
        <span aria-current="page">{novo ? "Novo usuário" : conta?.nome}</span>
      </nav>

      {sucesso && (
        <div className="aviso aviso--sucesso" role="status">
          <p className="aviso__titulo">{sucesso}</p>
        </div>
      )}

      {erro && (
        <div className="aviso" role="alert">
          <p className="aviso__titulo">{erro.message}</p>
          {erro.ajuda && <p className="aviso__ajuda">{erro.ajuda}</p>}
          {erro.campos?.length > 1 && (
            <ul className="aviso__lista">
              {erro.campos.map((c) => (
                <li key={c.campo}>
                  <a href={`#campo-${c.campo}`}>{ROTULO_CAMPO[c.campo] ?? c.campo}</a>: {c.mensagem}
                </li>
              ))}
            </ul>
          )}
          {existente && (
            <p className="aviso__acao">
              <Link to={`/usuarios/${existente.id}`} state={{ lista }}>
                Abrir a conta de {existente.nome}
                {existente.ativo ? "" : " (desativada)"}
              </Link>
            </p>
          )}
        </div>
      )}

      <section className="painel" aria-labelledby="titulo-conta">
        <div className="painel__cabecalho">
          <h2 className="painel__titulo" id="titulo-conta">
            {novo ? "Novo usuário" : "Conta"}
          </h2>
          <span className="painel__nota">
            {novo ? "* obrigatório" : <span className="num">{conta?.login}</span>}
          </span>
        </div>

        <form className="conta" onSubmit={salvar} noValidate>
          {novo && (
            <Campo
              id="login"
              rotulo="Login"
              obrigatorio
              erro={erroDoCampo.login}
              ajuda="Como a pessoa entra: minúsculas, números, ponto, hífen e sublinhado."
            >
              <input
                id="campo-login"
                autoComplete="off"
                maxLength={60}
                value={form.login}
                onChange={(e) => mudar("login", e.target.value)}
              />
            </Campo>
          )}

          <Campo
            id="nome"
            rotulo="Nome"
            obrigatorio
            erro={erroDoCampo.nome}
            ajuda="Como a pessoa aparece nas telas e na auditoria."
          >
            <input
              id="campo-nome"
              maxLength={120}
              value={form.nome}
              onChange={(e) => mudar("nome", e.target.value)}
            />
          </Campo>

          {novo && (
            <Campo
              id="senha"
              rotulo="Senha inicial"
              obrigatorio
              erro={erroDoCampo.senha}
              ajuda="A senha do primeiro acesso. O servidor confere a força; depois de salva, ninguém a vê."
            >
              <input
                id="campo-senha"
                type="password"
                autoComplete="new-password"
                value={form.senha}
                onChange={(e) => mudar("senha", e.target.value)}
              />
            </Campo>
          )}

          <Campo
            id="perfil"
            rotulo="Perfil"
            obrigatorio
            erro={erroDoCampo.perfil}
            ajuda={
              conta?.perfil === "PARCEIRO"
                ? "Conta vinculada a um parceiro. Mudar para outro perfil desfaz o vínculo."
                : "O perfil Parceiro ainda não é oferecido aqui: depende do portal do parceiro."
            }
          >
            <select
              id="campo-perfil"
              value={form.perfil}
              onChange={(e) => mudar("perfil", e.target.value)}
            >
              {perfis.map((p) => (
                <option key={p} value={p}>
                  {ROTULO_PERFIL[p]}
                </option>
              ))}
            </select>
          </Campo>

          <div className="conta__acoes">
            <button className="botao" type="submit" disabled={enviando}>
              {enviando ? "Salvando…" : novo ? "Criar usuário" : "Salvar alterações"}
            </button>
            <Link className="botao botao--secundario" to={lista}>
              {novo ? "Cancelar" : "Voltar para a lista"}
            </Link>
          </div>
        </form>
      </section>

      {!novo && conta && (
        <section className="painel" aria-labelledby="titulo-situacao">
          <div className="painel__cabecalho">
            <h2 className="painel__titulo" id="titulo-situacao">
              Situação
            </h2>
          </div>
          <div className="situacao__corpo">
            {avisoSituacao?.tipo === "sucesso" && (
              <div className="aviso aviso--sucesso" role="status">
                <p className="aviso__titulo">{avisoSituacao.texto}</p>
              </div>
            )}
            {avisoSituacao?.tipo === "erro" && (
              <div className="aviso" role="alert">
                <p className="aviso__titulo">{avisoSituacao.erro.message}</p>
                {avisoSituacao.erro.ajuda && (
                  <p className="aviso__ajuda">{avisoSituacao.erro.ajuda}</p>
                )}
              </div>
            )}

            <p className="situacao__texto">
              <span
                className={`ponto-situacao${conta.ativo ? "" : " ponto-situacao--inativo"}`}
                aria-hidden="true"
              />
              {conta.ativo
                ? "Ativa — entra no sistema com o perfil acima."
                : "Desativada — não entra; o histórico e a auditoria continuam."}
            </p>

            {confirmando ? (
              <Confirmacao
                texto={
                  souEu
                    ? "Esta é a sua conta. Desativá-la encerra a sua sessão agora, e você só volta a " +
                      "entrar se outro administrador a reativar."
                    : `Desativar a conta de ${conta.nome}? As sessões abertas são encerradas agora.`
                }
                acao="Desativar"
                ocupado={enviando}
                aoConfirmar={() => mudarSituacao(false)}
                aoCancelar={() => setConfirmando(false)}
              />
            ) : (
              <div className="situacao__acoes">
                {conta.ativo ? (
                  <button
                    type="button"
                    className="botao botao--secundario"
                    onClick={() => setConfirmando(true)}
                  >
                    Desativar
                  </button>
                ) : (
                  <button
                    type="button"
                    className="botao botao--secundario"
                    disabled={enviando}
                    onClick={() => mudarSituacao(true)}
                  >
                    Reativar
                  </button>
                )}
              </div>
            )}
          </div>
        </section>
      )}
    </>
  );
}
