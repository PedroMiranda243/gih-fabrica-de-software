/**
 * Usuários — quem tem conta no sistema. A lista abre nos ativos; "Todas as
 * situações" tem valor próprio no endereço (?ativo=todas). Não existe excluir:
 * desativar tira o acesso sem apagar o histórico.
 */
import { Link, useLocation } from "react-router-dom";

import { api } from "../api/cliente";
import { useCarregar, useFiltros } from "../api/ganchos";
import Busca from "../componentes/Busca";
import { Carregando, ErroDaTela, Vazio } from "../componentes/Estados";
import Icone from "../componentes/Icone";
import { CaixaDeTabela } from "../componentes/Lista";
import Seletor from "../componentes/Seletor";
import { useTitulo } from "../componentes/Titulo";
import { plural, ROTULO_PERFIL } from "../formato";

export default function Usuarios() {
  useTitulo("Usuários");
  const lugar = useLocation();
  const [filtros, mudar] = useFiltros();
  const situacao = filtros.ativo ?? "true";
  const consulta = { busca: filtros.busca, perfil: filtros.perfil, ativo: situacao === "todas" ? undefined : situacao };
  const lista = useCarregar(() => api.get("/api/usuarios", consulta), lugar.search);
  const d = lista.dados;

  return (
    <div className="pagina">
      <div className="barra-acoes">
        <p className="barra-acoes__contexto">{d ? `${plural(d.length, "conta", "contas")} neste recorte` : " "}</p>
        <div className="barra-acoes__botoes">
          <Link className="botao botao--primario" to="/usuarios/novo">
            <Icone nome="mais" /> Novo usuário
          </Link>
        </div>
      </div>
      <form className="filtros" aria-label="Filtros dos usuários" onSubmit={(e) => e.preventDefault()}>
        <div className="campo filtros__busca">
          <label className="campo__rotulo" htmlFor="u-busca">
            Buscar por nome ou login
          </label>
          <Busca id="u-busca" valor={filtros.busca} aoMudar={(v) => mudar({ busca: v })} placeholder="Um trecho do nome ou do login" />
        </div>
        <Seletor id="u-perfil" rotulo="Perfil" valor={filtros.perfil} aoMudar={(v) => mudar({ perfil: v })} todos="Todos os perfis" opcoes={Object.entries(ROTULO_PERFIL)} />
        <Seletor
          id="u-situacao"
          rotulo="Situação"
          valor={situacao}
          aoMudar={(v) => mudar({ ativo: v === "true" ? null : v })}
          todos={null}
          opcoes={[
            ["true", "Ativos"],
            ["false", "Desativados"],
            ["todas", "Todas as situações"],
          ]}
        />
      </form>
      <section className="bloco bloco--tabela" aria-labelledby="t-usuarios" aria-busy={lista.carregando}>
        <h2 id="t-usuarios" className="sr-only">
          Contas do sistema
        </h2>
        {lista.carregando && !d && <Carregando rotulo="Carregando os usuários" linhas={6} />}
        <ErroDaTela erro={lista.erro} />
        {d && !d.length && (
          <Vazio titulo="Nenhum usuário neste recorte" icone="usuarios">
            Mude a busca, o perfil ou a situação para ver outros usuários — a lista abre só nos ativos.
          </Vazio>
        )}
        {d && d.length > 0 && (
          <CaixaDeTabela rotulo="Usuários">
            <table className="tabela">
              <caption className="sr-only">Contas do sistema, em ordem de nome</caption>
              <thead>
                <tr>
                  <th scope="col">Nome</th>
                  <th scope="col">Login</th>
                  <th scope="col">Perfil</th>
                  <th scope="col">Situação</th>
                </tr>
              </thead>
              <tbody>
                {d.map((u) => (
                  <tr key={u.id} className={u.ativo ? undefined : "linha--inativa"}>
                    <th scope="row" className="nome nome--destaque">
                      <Link to={`/usuarios/${u.id}`} state={{ busca: lugar.search }}>
                        {u.nome}
                      </Link>
                    </th>
                    <td>
                      <code>{u.login}</code>
                    </td>
                    <td>{ROTULO_PERFIL[u.perfil] ?? u.perfil}</td>
                    <td>{u.ativo ? "Ativa" : "Desativada"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CaixaDeTabela>
        )}
      </section>
    </div>
  );
}
