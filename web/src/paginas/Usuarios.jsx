/**
 * Usuários do sistema (UC02) — só o Administrador.
 *
 * A lista com nome, login, perfil e situação, filtrável por perfil e por
 * situação — o passo 2 do UC02. Os filtros vivem no endereço, como na lista de
 * parceiros: voltar do cadastro devolve o mesmo recorte, e um recorte pode ser
 * mandado por link.
 *
 * O nome abre a conta. Não há "excluir": a auditoria referencia o autor de cada
 * ação, e desativar tira o acesso sem apagar o histórico (UC02-A2) — por isso
 * os desativados continuam existindo, a um filtro de distância.
 *
 * **A lista abre nos ativos.** As contas desativadas só crescem — toda
 * verificação de ponta a ponta deixa as suas, desativadas —, e o trabalho do dia
 * é com quem entra no sistema. "Todas" tem valor próprio no endereço: sem ele,
 * escolher "Todas" apagaria o parâmetro e a lista voltaria aos ativos.
 */
import { useEffect, useState } from "react";
import { Link, useLocation, useSearchParams } from "react-router-dom";

import { api } from "../api/cliente";
import { Esqueleto } from "../componentes/Carregando";
import EstadoVazio from "../componentes/EstadoVazio";
import { comoInteiro, ROTULO_PERFIL } from "../formato";

const SITUACOES = [
  { valor: "true", rotulo: "Ativos" },
  { valor: "false", rotulo: "Desativados" },
  { valor: "todas", rotulo: "Todas as situações" },
];
const SITUACAO_PADRAO = "true";

export default function Usuarios() {
  const [parametros, setParametros] = useSearchParams();
  const lugar = useLocation();
  const perfil = parametros.get("perfil") ?? "";
  const ativo = parametros.get("ativo") || SITUACAO_PADRAO;
  const aqui = lugar.pathname + lugar.search;
  const aviso = lugar.state?.aviso;

  const consulta = `${perfil}|${ativo}`;
  const [estado, setEstado] = useState({ consulta: null, usuarios: null, erro: null });

  useEffect(() => {
    let vivo = true;
    api
      .get("/api/usuarios", { perfil, ativo: ativo === "todas" ? "" : ativo })
      .then((usuarios) => vivo && setEstado({ consulta, usuarios, erro: null }))
      .catch((erro) => vivo && setEstado({ consulta, usuarios: null, erro }));
    return () => {
      vivo = false;
    };
  }, [consulta, perfil, ativo]);

  const atual = estado.consulta === consulta;
  const usuarios = atual ? estado.usuarios : null;
  const erro = atual ? estado.erro : null;

  function ajustar(mudancas) {
    const proximos = new URLSearchParams(parametros);
    Object.entries(mudancas).forEach(([chave, valor]) =>
      valor ? proximos.set(chave, valor) : proximos.delete(chave),
    );
    setParametros(proximos, { replace: true });
  }

  return (
    <>
      {aviso && (
        <div className="aviso aviso--sucesso" role="status">
          <p className="aviso__titulo">{aviso}</p>
        </div>
      )}

      <section className="painel">
        <div className="filtros">
          <div className="campo">
            <label htmlFor="perfil">Perfil</label>
            <select id="perfil" value={perfil} onChange={(e) => ajustar({ perfil: e.target.value })}>
              <option value="">Todos os perfis</option>
              {Object.entries(ROTULO_PERFIL).map(([valor, rotulo]) => (
                <option key={valor} value={valor}>
                  {rotulo}
                </option>
              ))}
            </select>
          </div>
          <div className="campo">
            <label htmlFor="ativo">Situação</label>
            <select
              id="ativo"
              value={ativo}
              onChange={(e) =>
                ajustar({ ativo: e.target.value === SITUACAO_PADRAO ? "" : e.target.value })
              }
            >
              {SITUACOES.map(({ valor, rotulo }) => (
                <option key={valor} value={valor}>
                  {rotulo}
                </option>
              ))}
            </select>
          </div>
        </div>
      </section>

      {erro && (
        <div className="aviso" role="alert">
          <p className="aviso__titulo">{erro.message}</p>
          {erro.ajuda && <p className="aviso__ajuda">{erro.ajuda}</p>}
        </div>
      )}

      <section className="painel" aria-labelledby="titulo-usuarios">
        <div className="painel__cabecalho">
          <h2 className="painel__titulo" id="titulo-usuarios">
            Usuários
          </h2>
          <div className="painel__acoes">
            <span className="painel__nota">
              {usuarios ? `${comoInteiro(usuarios.length)} encontrados` : "carregando…"}
            </span>
            <Link className="botao" to="/usuarios/novo" state={{ lista: aqui }}>
              Novo usuário
            </Link>
          </div>
        </div>

        {!usuarios && !erro && (
          <div style={{ padding: "var(--esp-16)" }} role="status" aria-label="Carregando usuários">
            {[0, 1, 2].map((i) => (
              <Esqueleto key={i} altura={40} style={{ marginBottom: "var(--esp-8)" }} />
            ))}
          </div>
        )}

        {usuarios && usuarios.length === 0 && (
          <EstadoVazio
            titulo="Nenhum usuário neste recorte"
            texto="Mude o perfil ou a situação para ver outros usuários — a lista abre só nos ativos."
          />
        )}

        {usuarios && usuarios.length > 0 && (
          <div className="tabela-rolagem">
            <table className="tabela">
              <caption className="so-leitor">Usuários do sistema, em ordem de nome</caption>
              <thead>
                <tr>
                  <th scope="col">Nome</th>
                  <th scope="col">Login</th>
                  <th scope="col">Perfil</th>
                  <th scope="col">Situação</th>
                </tr>
              </thead>
              <tbody>
                {usuarios.map((u) => (
                  <tr key={u.id}>
                    <td className="nome">
                      <Link className="nome__link" to={`/usuarios/${u.id}`} state={{ lista: aqui }}>
                        {u.nome}
                      </Link>
                    </td>
                    <td className="secundaria num">{u.login}</td>
                    <td>{ROTULO_PERFIL[u.perfil] ?? u.perfil}</td>
                    <td>
                      <span
                        className={`ponto-situacao${u.ativo ? "" : " ponto-situacao--inativo"}`}
                        aria-hidden="true"
                      />
                      {u.ativo ? "Ativo" : "Desativado"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}
