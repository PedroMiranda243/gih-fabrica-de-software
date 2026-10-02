/**
 * A trilha de auditoria (UC14, RF08, RF49 · H89): o que foi feito, por quem e quando.
 *
 * A API existia desde a H18; faltava a tela. O Administrador filtra por autor,
 * por ação e por datas, busca por texto — o nome de um parceiro, um login — e
 * exporta o recorte.
 *
 * **A frase vem do servidor.** O rótulo da ação e o resumo do que aconteceu são
 * montados na API (`servico_auditoria`), e são os mesmos na tela, no CSV e no
 * histórico do cadastro do parceiro. A tela não traduz código de ação nem lê os
 * parâmetros para concluir nada (regra 2.4): quem quiser o que foi gravado, cru,
 * abre "O que foi gravado" na linha.
 *
 * O recorte vive na URL, como na lista de parceiros: o link de exportar é a
 * mesma consulta com outro formato, e o botão voltar desfaz o filtro.
 */
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { api } from "../api/cliente";
import { Esqueleto } from "../componentes/Carregando";
import EstadoVazio from "../componentes/EstadoVazio";
import { comoDataHora, comoInteiro } from "../formato";
import "../estilos/auditoria.css";

const TAMANHO_PAGINA = 50;

export default function Auditoria() {
  const [parametros, setParametros] = useSearchParams();
  const [resultado, setResultado] = useState({ consulta: null, pagina: null });
  const [acoes, setAcoes] = useState([]);
  const [usuarios, setUsuarios] = useState([]);
  const [erro, setErro] = useState(null);

  const busca = parametros.get("busca") ?? "";
  const acao = parametros.get("acao") ?? "";
  const autor = parametros.get("autor") ?? "";
  const de = parametros.get("de") ?? "";
  const ate = parametros.get("ate") ?? "";
  const pagina = Number(parametros.get("pagina") ?? 1);

  /* Um objeto só com o que vai para a API, para a lista e para o arquivo: é o
     que garante que o CSV sai com o recorte que está na tela. */
  const filtros = { busca, acao, autor, de, ate };
  const consulta = JSON.stringify({ ...filtros, pagina });
  const dados = resultado.consulta === consulta ? resultado.pagina : null;

  useEffect(() => {
    /* As opções dos dois filtros. Se uma falhar, o filtro fica só com "todos" —
       a trilha continua consultável. */
    api.get("/api/auditoria/acoes").then(setAcoes).catch(() => setAcoes([]));
    api.get("/api/usuarios").then(setUsuarios).catch(() => setUsuarios([]));
  }, []);

  useEffect(() => {
    let vivo = true;
    /* A busca espera a digitação parar, como na lista de parceiros. */
    const relogio = setTimeout(() => {
      setErro(null);
      api
        .get("/api/auditoria", { ...filtros, pagina, tamanho: TAMANHO_PAGINA })
        .then((pagina) => vivo && setResultado({ consulta, pagina }))
        .catch((e) => vivo && setErro(e));
    }, 250);
    return () => {
      vivo = false;
      clearTimeout(relogio);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [consulta]);

  function ajustar(mudancas) {
    const proximos = new URLSearchParams(parametros);
    for (const [chave, valor] of Object.entries(mudancas)) {
      if (valor === "" || valor === undefined) proximos.delete(chave);
      else proximos.set(chave, String(valor));
    }
    /* Mudar o filtro volta para a primeira página: a página 7 pode não existir mais. */
    if (!("pagina" in mudancas)) proximos.delete("pagina");
    setParametros(proximos, { replace: true });
  }

  const filtrando = busca || acao || autor || de || ate;
  const total = dados?.total ?? 0;
  const primeiro = (pagina - 1) * TAMANHO_PAGINA + 1;
  const ultimo = Math.min(pagina * TAMANHO_PAGINA, total);

  return (
    <>
      <section className="painel" aria-label="Filtros da trilha">
        <div className="filtros">
          <div className="campo filtros__busca">
            <label htmlFor="busca">Buscar na trilha</label>
            <input
              id="busca"
              type="search"
              value={busca}
              placeholder="Um nome de parceiro, um login"
              onChange={(e) => ajustar({ busca: e.target.value })}
            />
          </div>

          <div className="campo">
            <label htmlFor="acao">Ação</label>
            <select id="acao" value={acao} onChange={(e) => ajustar({ acao: e.target.value })}>
              <option value="">Todas as ações</option>
              {acoes.map((a) => (
                <option key={a.acao} value={a.acao}>
                  {a.rotulo}
                </option>
              ))}
            </select>
          </div>

          <div className="campo">
            <label htmlFor="autor">Quem fez</label>
            <select id="autor" value={autor} onChange={(e) => ajustar({ autor: e.target.value })}>
              <option value="">Todas as pessoas</option>
              {usuarios.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.nome} ({u.login})
                </option>
              ))}
            </select>
          </div>

          <div className="campo">
            <label htmlFor="de">De</label>
            <input id="de" type="date" value={de} onChange={(e) => ajustar({ de: e.target.value })} />
          </div>

          <div className="campo">
            <label htmlFor="ate">Até</label>
            <input id="ate" type="date" value={ate} onChange={(e) => ajustar({ ate: e.target.value })} />
          </div>
        </div>
      </section>

      {erro && (
        <div className="aviso" role="alert">
          <p className="aviso__titulo">{erro.message}</p>
          {erro.ajuda && <p className="aviso__ajuda">{erro.ajuda}</p>}
        </div>
      )}

      <section className="painel" aria-labelledby="titulo-auditoria">
        <div className="painel__cabecalho">
          <h2 className="painel__titulo" id="titulo-auditoria">
            Trilha de auditoria
          </h2>
          <div className="parceiros__acoes">
            <span className="painel__nota">
              {dados ? `${comoInteiro(total)} ${total === 1 ? "registro" : "registros"}` : "carregando…"}
            </span>
            {/* Um link, e não um `fetch`: o navegador baixa o arquivo, e o cookie
                de sessão vai junto por ser a mesma origem. */}
            <a
              className="botao botao--secundario"
              href={`/api/auditoria/exportacao.csv?${new URLSearchParams(
                Object.entries(filtros).filter(([, v]) => v !== ""),
              )}`}
              download
            >
              Exportar CSV
            </a>
          </div>
        </div>

        {!dados && !erro && (
          <div style={{ padding: "var(--esp-16)" }} role="status" aria-label="Carregando a trilha">
            {[0, 1, 2, 3, 4].map((i) => (
              <Esqueleto key={i} altura={40} style={{ marginBottom: "var(--esp-8)" }} />
            ))}
          </div>
        )}

        {dados?.itens.length === 0 &&
          (filtrando ? (
            <EstadoVazio
              titulo="Nenhum registro nesse recorte"
              texto="Não houve operação com esses filtros. Amplie as datas ou limpe a busca."
            />
          ) : (
            <EstadoVazio
              titulo="A trilha ainda está vazia"
              texto="Cada entrada, importação, cálculo e decisão passa a aparecer aqui."
            />
          ))}

        {dados?.itens.length > 0 && (
          <>
            <div className="tabela-rolagem">
              <table className="tabela auditoria__tabela">
                <caption className="so-leitor">
                  Operações registradas, da mais recente para a mais antiga
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Quando</th>
                    <th scope="col">Quem fez</th>
                    <th scope="col">Ação</th>
                    <th scope="col">O que aconteceu</th>
                    <th scope="col">Origem</th>
                  </tr>
                </thead>
                <tbody>
                  {dados.itens.map((registro) => (
                    <Linha key={registro.id} registro={registro} />
                  ))}
                </tbody>
              </table>
            </div>

            <div className="paginacao">
              <span className="paginacao__posicao num">
                {comoInteiro(primeiro)}–{comoInteiro(ultimo)} de {comoInteiro(total)}
              </span>
              <button
                type="button"
                className="botao botao--secundario"
                disabled={pagina <= 1}
                onClick={() => ajustar({ pagina: pagina - 1 })}
              >
                Anterior
              </button>
              <button
                type="button"
                className="botao botao--secundario"
                disabled={ultimo >= total}
                onClick={() => ajustar({ pagina: pagina + 1 })}
              >
                Próxima
              </button>
            </div>
          </>
        )}
      </section>
    </>
  );
}

function Linha({ registro }) {
  return (
    <tr>
      <td className="secundaria num auditoria__quando">{comoDataHora(registro.ocorrido_em)}</td>
      <td>
        {registro.autor ? (
          <>
            {registro.autor} <span className="auditoria__login">{registro.autor_login}</span>
          </>
        ) : (
          /* A entrada recusada com login que não existe não tem usuário para
             apontar (UC14-A1): o login tentado está no resumo. */
          <span className="secundaria">sem usuário</span>
        )}
      </td>
      {/* A ação é o que se procura com os olhos: o único peso alto da linha. */}
      <td className="nome">{registro.rotulo}</td>
      <td className="auditoria__resumo">
        {registro.resumo}
        {registro.detalhes && (
          <details className="auditoria__gravado">
            <summary>O que foi gravado</summary>
            <pre>{JSON.stringify(registro.detalhes, null, 2)}</pre>
          </details>
        )}
      </td>
      <td className="secundaria num">{registro.origem ?? "—"}</td>
    </tr>
  );
}
