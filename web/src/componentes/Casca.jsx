/**
 * A casca: pular para o conteúdo, o menu em grupos (só o que o perfil abre, por
 * `telas`), o cabeçalho com o título da tela, quem está usando (→ Minha conta),
 * Ajuda, o tema e Encerrar sessão.
 *
 * Cada grupo do menu é uma rota com a sua cor: o trilho desenha as linhas, com uma
 * parada por tela, e o cabeçalho diz em que área a pessoa está e o caminho de volta.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";

import { tem, useSessao } from "../api/sessao";
import { ROTULO_PERFIL } from "../formato";
import { grupoDe, itemAtivo, MENU } from "../navegacao/telas";
import { useTema } from "../tema";
import Icone from "./Icone";
import Marca from "./Marca";
import { ContextoTitulo } from "./Titulo";

export default function Casca() {
  const { usuario, sair } = useSessao();
  const { efetivo, alternar } = useTema();
  const { pathname } = useLocation();
  const [titulo, setTitulo] = useState("");
  const [trilha, setTrilha] = useState(null);
  const [gaveta, setGaveta] = useState(false);
  const [saindo, setSaindo] = useState(false);
  const botaoMenu = useRef(null);
  const painelMenu = useRef(null);
  const definir = useCallback((t) => setTitulo(t), []);
  const definirTrilha = useCallback((t) => setTrilha(t?.length ? t : null), []);
  const contexto = useMemo(() => ({ definir, definirTrilha }), [definir, definirTrilha]);

  const grupos = MENU.map((g) => ({ ...g, itens: g.itens.filter((i) => tem(usuario, ...i.exige)) })).filter((g) => g.itens.length);
  const ativo = itemAtivo(pathname);
  const area = grupoDe(ativo);
  const volta = trilha?.filter((p) => p.para).at(-1) ?? null;

  useEffect(() => setGaveta(false), [pathname]);
  useEffect(() => {
    if (!gaveta) return undefined;
    painelMenu.current?.querySelector("a")?.focus();
    function tecla(e) {
      if (e.key === "Escape") {
        setGaveta(false);
        botaoMenu.current?.focus();
      }
    }
    document.addEventListener("keydown", tecla);
    return () => document.removeEventListener("keydown", tecla);
  }, [gaveta]);

  async function encerrar() {
    setSaindo(true);
    try {
      await sair();
    } finally {
      setSaindo(false);
    }
  }

  return (
    <ContextoTitulo.Provider value={contexto}>
      <a className="pular" href="#conteudo">
        Pular para o conteúdo
      </a>
      <div className={`casca${gaveta ? " casca--gaveta-aberta" : ""}`} data-rota={area?.rota}>
        <aside className="trilho" id="menu-principal" ref={painelMenu}>
          <div className="trilho__topo">
            <Link to="/" className="trilho__marca">
              <Marca />
            </Link>
            <button type="button" className="botao-icone trilho__fechar" onClick={() => setGaveta(false)} aria-label="Fechar o menu">
              <Icone nome="fechar" />
            </button>
          </div>
          <nav aria-label="Menu principal" className="menu">
            {grupos.map((g) => (
              <div key={g.grupo} className="menu__grupo" data-rota={g.rota} role="group" aria-labelledby={`grupo-${g.rota}`}>
                <p className="menu__nome" id={`grupo-${g.rota}`}>
                  {g.grupo}
                </p>
                <ul className="menu__linha">
                  {g.itens.map((i) => (
                    <li key={i.para}>
                      <NavLink to={i.para} end className={() => `menu__item${ativo === i.para ? " menu__item--ativo" : ""}`} aria-current={ativo === i.para ? "page" : undefined}>
                        <span className="menu__rotulo">{i.rotulo}</span>
                        <span className="menu__dica">{i.dica}</span>
                      </NavLink>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </nav>
        </aside>
        <button type="button" className="casca__veu" aria-hidden="true" tabIndex={-1} onClick={() => setGaveta(false)} />
        <div className="casca__corpo">
          <header className="cabecalho">
            <button type="button" ref={botaoMenu} className="botao-icone cabecalho__menu" onClick={() => setGaveta(true)} aria-expanded={gaveta} aria-controls="menu-principal" aria-label="Abrir o menu">
              <Icone nome="menu" />
            </button>
            <div className="cabecalho__onde">
              {(area || trilha) && (
                <nav className="caminho" aria-label="Onde você está">
                  <ol>
                    {area && (
                      <li>
                        <span className="rota-etiqueta">
                          <span className="rota-etiqueta__parada" aria-hidden="true" />
                          <span className="sr-only">Área: </span>
                          <span className="rota-etiqueta__nome">{area.grupo}</span>
                        </span>
                        <Icone nome="seta-direita" className="caminho__sep" />
                      </li>
                    )}
                    {trilha?.map((p) => (
                      <li key={`${p.rotulo}-${p.para ?? ""}`} className="caminho__passo">
                        {p.para ? <Link to={p.para}>{p.rotulo}</Link> : <span>{p.rotulo}</span>}
                        <Icone nome="seta-direita" className="caminho__sep" />
                      </li>
                    ))}
                  </ol>
                </nav>
              )}
              {volta && (
                <Link to={volta.para} className="caminho__voltar" aria-label={`Voltar para ${volta.rotulo}`} title={`Voltar para ${volta.rotulo}`}>
                  <Icone nome="seta-esquerda" />
                </Link>
              )}
              <h1 className="cabecalho__titulo" id="titulo-da-tela" tabIndex={-1}>
                {titulo}
              </h1>
            </div>
            <div className="cabecalho__acoes">
              <Link to="/conta" className="quem" aria-label={`${usuario.nome}, ${ROTULO_PERFIL[usuario.perfil] ?? usuario.perfil} — Minha conta`}>
                <span className="quem__avatar" aria-hidden="true">
                  {usuario.nome
                    .split(/\s+/)
                    .filter((p) => p.length > 2)
                    .slice(0, 2)
                    .map((p) => p[0])
                    .join("")
                    .toUpperCase() || usuario.nome[0]}
                </span>
                <span className="quem__texto">
                  <span className="quem__nome">{usuario.nome}</span>
                  <span className="quem__perfil">{ROTULO_PERFIL[usuario.perfil] ?? usuario.perfil}</span>
                </span>
              </Link>
              <Link to="/ajuda" className="botao-cabecalho">
                <Icone nome="ajuda" />
                <span>Ajuda</span>
              </Link>
              <button type="button" className="botao-cabecalho" onClick={alternar} aria-label={efetivo === "escuro" ? "Mudar para o modo claro" : "Mudar para o modo escuro"} title={efetivo === "escuro" ? "Mudar para o modo claro" : "Mudar para o modo escuro"}>
                <Icone nome={efetivo === "escuro" ? "sol" : "lua"} />
                <span className="botao-cabecalho__rotulo-tema">{efetivo === "escuro" ? "Modo claro" : "Modo escuro"}</span>
              </button>
              <button type="button" className="botao-cabecalho" onClick={encerrar} disabled={saindo}>
                <Icone nome="sair" />
                <span>{saindo ? "Encerrando…" : "Encerrar sessão"}</span>
              </button>
            </div>
          </header>
          <main id="conteudo" className="conteudo" tabIndex={-1}>
            <Outlet />
          </main>
        </div>
      </div>
    </ContextoTitulo.Provider>
  );
}
