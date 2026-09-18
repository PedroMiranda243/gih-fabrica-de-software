/**
 * Casca da aplicação: trilho lateral, cabeçalho e o conteúdo da rota.
 *
 * O trilho lista **apenas o que existe**. Campanha e aprovação estão no
 * protótipo e não entram aqui: o otimizador é a Sprint 9–10 e as mensagens são
 * a Sprint 12, então não há API atrás delas. Item de menu que leva a uma tela
 * vazia é pior que item ausente — promete e não entrega.
 */
import { NavLink, Outlet } from "react-router-dom";

import { useSessao } from "../api/contextoSessao";
import { useTema } from "../temas/useTema";
import {
  IconeImportar,
  IconePainel,
  IconeParceiros,
  IconeSair,
  IconeTemaClaro,
  IconeTemaEscuro,
} from "./Icones";

const TELAS = [
  { para: "/", rotulo: "Painel", Icone: IconePainel, fim: true },
  { para: "/importacao", rotulo: "Importação", Icone: IconeImportar },
  { para: "/parceiros", rotulo: "Parceiros", Icone: IconeParceiros },
];

export default function Casca({ titulo }) {
  const { usuario, sair } = useSessao();
  const { tema, alternar } = useTema();

  return (
    <div className="casca">
      <nav className="trilho" aria-label="Seções do sistema">
        <div className="trilho__marca">
          <span className="trilho__sigla">GIH</span>
          <span className="trilho__produto">Growth Intelligence</span>
        </div>

        <div className="trilho__navegacao">
          {TELAS.map(({ para, rotulo, Icone, fim }) => (
            <NavLink key={para} to={para} end={fim} className="trilho__item">
              <Icone />
              {rotulo}
            </NavLink>
          ))}
        </div>
      </nav>

      <div className="conteudo">
        <header className="cabecalho">
          <h1 className="cabecalho__titulo">{titulo}</h1>

          <div className="cabecalho__direita">
            {usuario && (
              <div className="cabecalho__quem">
                <span className="cabecalho__nome">{usuario.nome}</span>
                <span className="cabecalho__perfil">{usuario.perfil}</span>
              </div>
            )}

            <button
              type="button"
              className="icone-botao"
              onClick={alternar}
              /* O rótulo diz o que **vai acontecer**, não o estado atual: é o
                 que o leitor de tela anuncia, e "modo escuro" sozinho deixa
                 ambíguo se liga ou desliga. */
              aria-label={tema === "escuro" ? "Mudar para o modo claro" : "Mudar para o modo escuro"}
            >
              {tema === "escuro" ? <IconeTemaClaro /> : <IconeTemaEscuro />}
            </button>

            <button type="button" className="icone-botao" onClick={sair} aria-label="Encerrar sessão">
              <IconeSair />
            </button>
          </div>
        </header>

        <main className="pagina">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
