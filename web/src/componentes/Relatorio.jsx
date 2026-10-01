/**
 * A moldura de um relatório (UC15 · RF48 · H88): o título, o recorte aplicado e
 * as duas saídas — o CSV e a impressão.
 *
 * **O relatório é o que se leva para fora do sistema.** Por isso ele diz, nele
 * mesmo, de que recorte é: quem lê a folha impressa ou o PDF não tem os filtros
 * na frente. O recorte vem escrito pela página, a partir do que a API devolveu —
 * e não do que está no endereço.
 *
 * **A impressão é a do navegador** (nenhuma dependência nova): "Imprimir ou
 * salvar em PDF" chama `window.print()`, e `estilos/impressao.css` tira o menu,
 * o cabeçalho e os filtros, solta as tabelas da rolagem e mostra a linha de
 * emissão — quando foi gerado, e por quem —, que na tela não aparece.
 *
 * O CSV é um link, e não um `fetch`: o navegador baixa o arquivo, e o cookie de
 * sessão vai junto por ser a mesma origem. Ele leva os mesmos filtros da tela.
 */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { useSessao } from "../api/contextoSessao";
import { comoDataHora, comoPercentual, ROTULO_PERFIL, sentidoDa, TRACO } from "../formato";
import { IconeVariacao } from "./Icones";
import "../estilos/relatorios.css";

export default function Relatorio({ titulo, recorte = [], csv, filtros, children }) {
  const { usuario } = useSessao();
  const [emitidoEm, setEmitidoEm] = useState(() => new Date().toISOString());

  useEffect(() => {
    /* A hora da folha é a de quando ela é impressa, e não a de quando a tela
       abriu: vale também para quem imprime pelo atalho do navegador. */
    const marcar = () => setEmitidoEm(new Date().toISOString());
    window.addEventListener("beforeprint", marcar);
    return () => window.removeEventListener("beforeprint", marcar);
  }, []);

  return (
    <>
      <nav className="trilha nao-imprime" aria-label="Você está em">
        <Link to="/relatorios">Relatórios</Link>
        <span aria-hidden="true">›</span>
        <span aria-current="page">{titulo}</span>
      </nav>

      <article className="relatorio" aria-labelledby="titulo-relatorio">
        <header className="relatorio__cabecalho">
          <div>
            <h2 className="relatorio__titulo" id="titulo-relatorio">
              {titulo}
            </h2>
            {recorte.length > 0 && <p className="relatorio__recorte">{recorte.join(" · ")}</p>}
            <p className="relatorio__emissao so-impressao">
              Gerado em {comoDataHora(emitidoEm)}
              {usuario ? ` por ${usuario.nome} (${ROTULO_PERFIL[usuario.perfil] ?? usuario.perfil})` : ""}{" "}
              · Growth Intelligence Hub
            </p>
          </div>

          <div className="relatorio__acoes nao-imprime">
            {csv && (
              <a className="botao botao--secundario" href={csv} download>
                Exportar CSV
              </a>
            )}
            <button type="button" className="botao botao--secundario" onClick={() => window.print()}>
              Imprimir ou salvar em PDF
            </button>
          </div>
        </header>

        {/* Depois do título e antes do conteúdo: primeiro o que é, depois o que
            se pode mudar nele. Não vão para a folha — o recorte acima já os diz. */}
        {filtros && (
          <section className="painel nao-imprime" aria-label="Filtros do relatório">
            {filtros}
          </section>
        )}

        {children}
      </article>
    </>
  );
}

/** A variação, com a seta, o sinal e a cor — e travessão quando não há com o que comparar. */
export function Variacao({ valor }) {
  const sentido = sentidoDa(valor);
  if (sentido === "indefinida") {
    return (
      <span style={{ color: "var(--ink-2)" }} title="Sem base de comparação">
        {TRACO}
        <span className="so-leitor"> sem variação calculável</span>
      </span>
    );
  }
  return (
    <span className={`indicador__variacao indicador__variacao--${sentido}`}>
      {sentido !== "estavel" && <IconeVariacao sentido={sentido} />}
      {comoPercentual(valor)}
    </span>
  );
}

/** O aviso de erro de um relatório, com a ajuda que a API mandou. */
export function ErroDoRelatorio({ erro }) {
  if (!erro) return null;
  return (
    <div className="aviso" role="alert">
      <p className="aviso__titulo">{erro.message}</p>
      {erro.ajuda && <p className="aviso__ajuda">{erro.ajuda}</p>}
    </div>
  );
}
