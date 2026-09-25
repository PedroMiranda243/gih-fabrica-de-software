/**
 * Casca da aplicação: trilho lateral, cabeçalho e o conteúdo da rota.
 *
 * O trilho lista **apenas o que existe**. Campanha e aprovação estão no
 * protótipo e não entram aqui: o otimizador é a Sprint 9–10 e as mensagens são
 * a Sprint 12, então não há API atrás delas. O modelo preditivo entrou na
 * Sprint 05 da disciplina, com a API junto. Item de menu que leva a uma tela
 * vazia é pior que item ausente — promete e não entrega.
 *
 * Pela mesma razão, **cada perfil vê só o que abre**. A lista vem do servidor
 * (`usuario.telas`), que a lê das permissões das próprias rotas: a interface
 * não decide quem pode o quê (regra 2.4), só desenha o que ouviu. E esconder o
 * item não é controle de acesso — a rota continua recusando (regra 2.5).
 */
import { NavLink, Outlet } from "react-router-dom";

import { useSessao } from "../api/contextoSessao";
import { useTema } from "../temas/useTema";
import {
  IconeConfiguracao,
  IconeImportar,
  IconeModelo,
  IconePainel,
  IconeParceiros,
  IconeSair,
  IconeUsuarios,
  IconeTemaClaro,
  IconeTemaEscuro,
} from "./Icones";

/* `exige`: as telas do servidor que sustentam o item — basta uma. A Importação
   aparece para quem importa **ou** só lê o histórico, que é o caso do
   Administrador (RF13). */
const TELAS = [
  { para: "/", rotulo: "Painel", Icone: IconePainel, fim: true, exige: ["painel"] },
  {
    para: "/importacao",
    rotulo: "Importação",
    Icone: IconeImportar,
    exige: ["importar", "historico_importacoes"],
  },
  { para: "/parceiros", rotulo: "Parceiros", Icone: IconeParceiros, exige: ["parceiros"] },
  { para: "/modelo", rotulo: "Modelo", Icone: IconeModelo, exige: ["modelo"] },
  { para: "/usuarios", rotulo: "Usuários", Icone: IconeUsuarios, exige: ["usuarios"] },
  {
    para: "/configuracao",
    rotulo: "Configuração",
    Icone: IconeConfiguracao,
    exige: ["configuracao"],
  },
];

/* Sessão aberta antes de o servidor mandar `telas` — uma aba esquecida aberta
   durante a atualização — continua vendo o menu de antes, em vez de um trilho
   vazio, e sem as telas de administração que vieram depois. Na próxima
   recarga, a lista chega. */
const MENU_ANTERIOR = ["painel", "importar", "parceiros"];

function visiveis(usuario) {
  const telas = Array.isArray(usuario?.telas) ? usuario.telas : MENU_ANTERIOR;
  return TELAS.filter(({ exige }) => exige.some((tela) => telas.includes(tela)));
}

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
          {visiveis(usuario).map(({ para, rotulo, Icone, fim }) => (
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
