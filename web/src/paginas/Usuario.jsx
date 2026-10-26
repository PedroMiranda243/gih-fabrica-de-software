/**
 * A conta de um usuário — criar e editar (mandando só o que mudou), desativar ou
 * reativar, e redefinir a senha de quem esqueceu a dela. As recusas aparecem no
 * lugar certo: senha fraca no campo, login repetido aponta a conta, o último
 * administrador não cai.
 */
import { useMemo, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";

import { api, ErroDaApi } from "../api/cliente";
import { useAtraso, useCarregar } from "../api/ganchos";
import { useSessao } from "../api/contextoSessao";
import AlteracoesNaoSalvas from "../componentes/AlteracoesNaoSalvas";
import Confirmacao from "../componentes/Confirmacao";
import { Carregando, ErroDaAcao, ErroDaTela, Nota, Sucesso, Vazio } from "../componentes/Estados";
import { Campo, ResumoDeErros, Senha } from "../componentes/Formulario";
import { useErrosDoFormulario } from "../componentes/useErrosDoFormulario";
import Icone from "../componentes/Icone";
import { Trilha } from "../componentes/Lista";
import { useTitulo } from "../componentes/Titulo";
import { comoDataHora, ROTULO_PERFIL } from "../formato";

export default function Usuario() {
  const { id } = useParams();
  const conta = useCarregar(() => api.get(`/api/usuarios/${id}`), `u${id}`, { ativo: Boolean(id) });
  if (id && conta.carregando) return <Carregando rotulo="Carregando a conta" linhas={6} />;
  if (id && conta.erro?.status === 404) return <NaoEncontrado />;
  if (id && conta.erro) return <ErroDaTela erro={conta.erro} />;
  return <Conta key={id ?? "nova"} id={id} dados={conta.dados} substituir={conta.substituir} />;
}

function NaoEncontrado() {
  useTitulo("Usuário não encontrado", "Usuários");
  return (
    <div className="pagina">
      <Trilha passos={[{ rotulo: "Usuários", para: "/usuarios" }, { rotulo: "Não encontrado" }]} />
      <Vazio titulo="Usuário não encontrado" acao="Voltar para os usuários" para="/usuarios" icone="busca">
        O endereço aponta para uma conta que não existe.
      </Vazio>
    </div>
  );
}

const valoresDe = (d) => ({ login: d?.login ?? "", nome: d?.nome ?? "", senha: "", perfil: d?.perfil ?? "", parceiro: d?.parceiro ?? null });

function Conta({ id, dados, substituir }) {
  const nova = !id;
  const { usuario } = useSessao();
  const lugar = useLocation();
  const navegar = useNavigate();
  const [base, setBase] = useState(() => valoresDe(dados));
  const [v, setV] = useState(() => valoresDe(dados));
  const [salvo, setSalvo] = useState(lugar.state?.criado ?? null);
  const [enviando, setEnviando] = useState(false);
  const [conflito, setConflito] = useState(null);
  const { erros, receber, limpar, limparCampo, registrar } = useErrosDoFormulario();
  const propria = !nova && dados?.id === usuario.id;
  const nome = dados?.nome ?? "Novo usuário";
  useTitulo(nome, "Usuários");

  const alterado = useMemo(() => v.nome !== base.nome || v.perfil !== base.perfil || v.login !== base.login || v.senha !== "" || (v.parceiro?.id ?? null) !== (base.parceiro?.id ?? null), [v, base]);
  const voltar = `/usuarios${lugar.state?.busca ?? ""}`;

  function mudar(campo, valor) {
    setV((x) => ({ ...x, [campo]: valor }));
    setSalvo(null);
    limparCampo(campo === "parceiro" ? "parceiro_id" : campo);
  }

  async function enviar(evento) {
    evento.preventDefault();
    limpar();
    setConflito(null);
    setEnviando(true);
    const mapa = v.perfil === "PARCEIRO" ? { requisição: "parceiro_id" } : {};
    try {
      if (nova) {
        const criado = await api.post("/api/usuarios", { login: v.login, nome: v.nome, senha: v.senha, perfil: v.perfil || null, parceiro_id: v.perfil === "PARCEIRO" ? (v.parceiro?.id ?? null) : null });
        setBase(v);
        navegar(`/usuarios/${criado.id}`, { replace: true, state: { criado: `Usuário criado. ${criado.nome} já pode entrar com o login ${criado.login}.`, busca: lugar.state?.busca } });
        return;
      }
      const corpo = {};
      if (v.nome !== base.nome) corpo.nome = v.nome;
      if (v.perfil !== base.perfil) corpo.perfil = v.perfil;
      if ((v.parceiro?.id ?? null) !== (base.parceiro?.id ?? null) && v.perfil === "PARCEIRO") corpo.parceiro_id = v.parceiro?.id ?? null;
      const r = await api.patch(`/api/usuarios/${id}`, corpo);
      substituir((d) => ({ ...d, ...r, parceiro: v.perfil === "PARCEIRO" ? v.parceiro : null }));
      const nb = { ...v, parceiro: v.perfil === "PARCEIRO" ? v.parceiro : null };
      setBase(nb);
      setV(nb);
      setSalvo("Alterações salvas. O perfil novo vale já na próxima ação da pessoa.");
    } catch (e) {
      if (e instanceof ErroDaApi && e.status === 409 && !e.campos) setConflito(e);
      else receber(e, { mapa, ordem: ["login", "nome", "senha", "perfil", "parceiro_id"] });
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="pagina">
      <div className="barra-acoes">
        <Trilha passos={[{ rotulo: "Usuários", para: voltar }, { rotulo: nome }]} />
        <Link to={voltar} className="link-seta">
          <Icone nome="seta-esquerda" /> Voltar para a lista
        </Link>
      </div>
      <div className={nova ? "coluna-estreita" : "conta-grade"}>
        <section className="bloco" aria-labelledby="t-conta">
          <div className="bloco__cabeca">
            <h2 id="t-conta" className="bloco__titulo">
              {nova ? "Nova conta" : "Dados da conta"}
            </h2>
            {!nova && <p className="bloco__sub">Criada em {comoDataHora(dados.criado_em)}</p>}
          </div>
          <form className="formulario" onSubmit={enviar} noValidate>
            {salvo && <Sucesso>{salvo}</Sucesso>}
            <ResumoDeErros erros={erros} rotulos={{ login: "Login", nome: "Nome", senha: "Senha inicial", perfil: "Perfil", parceiro_id: "Parceiro da conta" }} />
            {conflito && (
              <div className="aviso aviso--erro" role="alert">
                <Icone nome="erro" className="aviso__icone" />
                <div className="aviso__texto">
                  <p>{conflito.message}</p>
                  {conflito.ajuda && <p className="aviso__ajuda">{conflito.ajuda}</p>}
                  {conflito.detalhe?.existente && (
                    <p>
                      <Link to={`/usuarios/${conflito.detalhe.existente.id}`}>
                        Abrir a conta que já usa este login{conflito.detalhe.existente.nome ? ` (${conflito.detalhe.existente.nome}${conflito.detalhe.existente.ativo === false ? ", desativada" : ""})` : ""}
                      </Link>
                    </p>
                  )}
                </div>
              </div>
            )}
            {nova ? (
              <Campo nome="login" rotulo="Login" obrigatorio erro={erros.campos.login} ajuda="Como a pessoa entra: minúsculas, números, ponto, hífen e sublinhado.">
                {(a) => <input {...a} ref={registrar("login")} className="entrada" value={v.login} onChange={(e) => mudar("login", e.target.value)} autoComplete="off" autoCapitalize="none" spellCheck={false} />}
              </Campo>
            ) : (
              <div className="campo">
                <p className="campo__rotulo">Login</p>
                <p className="valor-leitura">
                  <code>{dados.login}</code> <span className="discreto">— o login não muda.</span>
                </p>
              </div>
            )}
            <Campo nome="nome" rotulo="Nome" obrigatorio erro={erros.campos.nome} ajuda="Como a pessoa aparece nas telas e na auditoria.">
              {(a) => <input {...a} ref={registrar("nome")} className="entrada" value={v.nome} onChange={(e) => mudar("nome", e.target.value)} autoComplete="off" />}
            </Campo>
            {nova && (
              <Campo nome="senha" rotulo="Senha inicial" obrigatorio erro={erros.campos.senha} ajuda="A senha do primeiro acesso. O servidor confere a força; depois de salva, ninguém a vê.">
                {(a) => <Senha {...a} ref={registrar("senha")} valor={v.senha} aoMudar={(x) => mudar("senha", x)} autoComplete="new-password" />}
              </Campo>
            )}
            <Campo nome="perfil" rotulo="Perfil" obrigatorio erro={erros.campos.perfil} ajuda="O perfil decide o que a pessoa abre. O Parceiro vê só o portal dele.">
              {(a) => (
                <select {...a} ref={registrar("perfil")} className="entrada" value={v.perfil} onChange={(e) => mudar("perfil", e.target.value)}>
                  {nova && <option value="">Escolha o perfil</option>}
                  {Object.entries(ROTULO_PERFIL).map(([k, r]) => (
                    <option key={k} value={k}>
                      {r}
                    </option>
                  ))}
                </select>
              )}
            </Campo>
            {!nova && base.perfil === "PARCEIRO" && v.perfil !== "PARCEIRO" && <Nota tipo="atencao">Mudar para outro perfil desfaz o vínculo com o parceiro.</Nota>}
            {v.perfil === "PARCEIRO" && <ParceiroDaConta escolhido={v.parceiro} aoEscolher={(p) => mudar("parceiro", p)} erro={erros.campos.parceiro_id} registrar={registrar} />}
            <div className="formulario__acoes">
              <button type="submit" className="botao botao--primario" disabled={enviando || (!nova && !alterado)}>
                {enviando ? "Salvando…" : nova ? "Criar usuário" : "Salvar alterações"}
              </button>
            </div>
          </form>
          <AlteracoesNaoSalvas quando={alterado && !enviando} />
        </section>
        {!nova && (
          <div className="conta-grade__lado">
            <Situacao dados={dados} propria={propria} substituir={substituir} />
            <RedefinirSenha dados={dados} propria={propria} />
          </div>
        )}
      </div>
    </div>
  );
}

function ParceiroDaConta({ escolhido, aoEscolher, erro, registrar }) {
  const [texto, setTexto] = useState("");
  const termo = useAtraso(texto.trim(), 350);
  const achados = useCarregar(() => api.get("/api/usuarios/parceiros", { busca: termo }), `p${termo}`, { ativo: termo.length >= 2 });
  return (
    <fieldset className={`grupo-campos parceiro-da-conta${erro ? " campo--erro" : ""}`} aria-describedby={erro ? "campo-parceiro_id-erro" : undefined}>
      <legend className="grupo-campos__legenda">
        Parceiro da conta<span className="campo__obrigatorio"> *</span>
        <span className="sr-only"> (obrigatório)</span>
      </legend>
      <p className="parceiro-da-conta__atual">{escolhido ? <>A conta vê só o desempenho de <strong>{escolhido.nome}</strong>.</> : "Nenhum parceiro escolhido ainda."}</p>
      <div className="campo">
        <label className="campo__rotulo" htmlFor="campo-parceiro_id">
          Buscar pelo nome do parceiro
        </label>
        <input id="campo-parceiro_id" ref={registrar("parceiro_id")} className="entrada" type="search" value={texto} onChange={(e) => setTexto(e.target.value)} aria-describedby="parceiro-busca-ajuda" autoComplete="off" />
        <p className="campo__ajuda" id="parceiro-busca-ajuda">
          Digite ao menos duas letras do nome. A busca mostra só o nome e a situação do parceiro.
        </p>
      </div>
      {erro && (
        <p className="campo__erro" id="campo-parceiro_id-erro">
          <Icone nome="erro" />
          <span>{erro.mensagem}</span>
        </p>
      )}
      {termo.length >= 2 && (
        <div className="achados" aria-live="polite">
          {achados.carregando && <p className="discreto">Buscando…</p>}
          {achados.erro && <p className="texto-erro">{achados.erro.campos?.[0]?.mensagem ?? achados.erro.message}</p>}
          {achados.dados && !achados.dados.length && <p className="discreto">Nenhum parceiro com “{termo}” no nome.</p>}
          {achados.dados?.map((p) => (
            <button key={p.id} type="button" className={`botao botao--secundario botao--pequeno${escolhido?.id === p.id ? " botao--escolhido" : ""}`} aria-pressed={escolhido?.id === p.id} onClick={() => aoEscolher({ id: p.id, nome: p.nome, ativo: p.ativo })}>
              {p.nome}
              {!p.ativo && <span className="selo-texto selo-texto--neutro">desativado</span>}
            </button>
          ))}
        </div>
      )}
    </fieldset>
  );
}

function Situacao({ dados, propria, substituir }) {
  const [confirmando, setConfirmando] = useState(false);
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState(null);
  const [aviso, setAviso] = useState(null);

  async function mudar(ativo) {
    setOcupado(true);
    setErro(null);
    try {
      const r = await api.patch(`/api/usuarios/${dados.id}`, { ativo });
      substituir((d) => ({ ...d, ...r }));
      setAviso(ativo ? "Conta reativada. A pessoa volta a entrar com a senha que tinha." : "Conta desativada. As sessões abertas foram encerradas agora.");
      setConfirmando(false);
    } catch (e) {
      setErro(e);
      setConfirmando(false);
    } finally {
      setOcupado(false);
    }
  }

  return (
    <section className="bloco" aria-labelledby="t-situacao">
      <div className="bloco__cabeca">
        <h2 id="t-situacao" className="bloco__titulo">
          Situação
        </h2>
      </div>
      <p className={`situacao${dados.ativo ? "" : " situacao--inativa"}`}>
        <strong>{dados.ativo ? "Ativa" : "Desativada"}</strong> — {dados.ativo ? "entra no sistema com o perfil acima." : "não entra; o histórico e a auditoria continuam."}
      </p>
      {aviso && <Sucesso>{aviso}</Sucesso>}
      <ErroDaAcao erro={erro} />
      {confirmando ? (
        <Confirmacao
          texto={`Desativar a conta de ${dados.nome}? As sessões abertas são encerradas agora.`}
          detalhe={propria ? "Esta é a sua conta. Desativá-la encerra a sua sessão agora, e você só volta a entrar se outro administrador a reativar." : null}
          acao="Desativar"
          perigo
          ocupado={ocupado}
          aoConfirmar={() => mudar(false)}
          aoCancelar={() => setConfirmando(false)}
        />
      ) : dados.ativo ? (
        <button type="button" className="botao botao--secundario" onClick={() => (setAviso(null), setConfirmando(true))}>
          Desativar
        </button>
      ) : (
        <button type="button" className="botao botao--secundario" onClick={() => mudar(true)} disabled={ocupado}>
          {ocupado ? "Reativando…" : "Reativar"}
        </button>
      )}
    </section>
  );
}

function RedefinirSenha({ dados, propria }) {
  const [senha, setSenha] = useState("");
  const [confirmando, setConfirmando] = useState(false);
  const [ocupado, setOcupado] = useState(false);
  const [aviso, setAviso] = useState(null);
  const [erroTopo, setErroTopo] = useState(null);
  const { erros, receber, limpar, registrar } = useErrosDoFormulario();

  if (propria) {
    return (
      <section className="bloco" aria-labelledby="t-senha">
        <div className="bloco__cabeca">
          <h2 id="t-senha" className="bloco__titulo">
            Senha
          </h2>
        </div>
        <p>
          Esta é a sua conta: a sua senha se troca em <Link to="/conta">Minha conta</Link>, que pede a senha atual.
        </p>
      </section>
    );
  }

  async function redefinir() {
    setOcupado(true);
    limpar();
    setErroTopo(null);
    try {
      await api.post(`/api/usuarios/${dados.id}/senha`, { senha_nova: senha });
      setSenha("");
      setAviso("Senha redefinida. A senha não volta na resposta: passe-a à pessoa por fora do sistema.");
      setConfirmando(false);
    } catch (e) {
      setConfirmando(false);
      if (e instanceof ErroDaApi && e.campos) receber(e, { ordem: ["senha_nova"] });
      else setErroTopo(e);
    } finally {
      setOcupado(false);
    }
  }

  return (
    <section className="bloco" aria-labelledby="t-senha">
      <div className="bloco__cabeca">
        <h2 id="t-senha" className="bloco__titulo">
          Senha
        </h2>
        <p className="bloco__sub">Para quem esqueceu a dela.</p>
      </div>
      <form
        className="formulario"
        noValidate
        onSubmit={(e) => {
          e.preventDefault();
          setAviso(null);
          setConfirmando(true);
        }}
      >
        {aviso && <Sucesso>{aviso}</Sucesso>}
        <ErroDaAcao erro={erroTopo} />
        <Campo nome="senha_nova" rotulo="Senha nova" erro={erros.campos.senha_nova} ajuda="O servidor confere a força. Depois de salva, ninguém a vê — nem aqui.">
          {(a) => <Senha {...a} ref={registrar("senha_nova")} valor={senha} aoMudar={(x) => (setSenha(x), setAviso(null))} autoComplete="new-password" />}
        </Campo>
        {confirmando ? (
          <Confirmacao texto={`Redefinir a senha de ${dados.nome}? As sessões abertas dela são encerradas agora, e a senha de antes deixa de valer.`} acao="Redefinir a senha" perigo ocupado={ocupado} aoConfirmar={redefinir} aoCancelar={() => setConfirmando(false)} />
        ) : (
          <div className="formulario__acoes">
            <button type="submit" className="botao botao--secundario" disabled={!senha}>
              Redefinir a senha
            </button>
          </div>
        )}
      </form>
    </section>
  );
}
