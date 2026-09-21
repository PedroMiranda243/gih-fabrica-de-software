/**
 * Lista de parceiros, com busca, filtros, ordenação e exportação (UC04, RF23).
 *
 * A busca ignora maiúsculas **e acentuação** — é o servidor que faz isso, por
 * coluna normalizada e índice de trigrama. A tela só manda o termo.
 *
 * O recorte inteiro vive na URL. Não é capricho: um recorte útil precisa poder
 * ser mandado para outra pessoa por link, o botão voltar precisa desfazer o
 * filtro em vez de sair da tela, e o **botão de exportar** é só um link para a
 * mesma consulta com outro formato — o que só funciona porque os parâmetros
 * são os mesmos.
 *
 * **Nenhum cálculo acontece aqui** (regra 2.4): faturamento, ticket, variação e
 * segmento vêm prontos da API, do período mais recente.
 */
import { useEffect, useState } from "react";
import { Link, useLocation, useSearchParams } from "react-router-dom";

import { api } from "../api/cliente";
import { Esqueleto } from "../componentes/Carregando";
import EstadoVazio from "../componentes/EstadoVazio";
import { IconeVariacao } from "../componentes/Icones";
import Segmento from "../componentes/Segmento";
import {
  comoDinheiro,
  comoInteiro,
  comoPercentual,
  ROTULO_SEGMENTO,
  ROTULO_STATUS,
  sentidoDa,
  TRACO,
} from "../formato";
import "../estilos/parceiros.css";

const SITUACOES = [
  { valor: "", rotulo: "Todas as situações" },
  { valor: "true", rotulo: "Somente ativos" },
  { valor: "false", rotulo: "Somente inativos" },
];

const STATUS = [
  { valor: "", rotulo: "Todos os status" },
  { valor: "ATIVO", rotulo: "Ativo" },
  { valor: "PROSPECCAO", rotulo: "Prospecção" },
  { valor: "INATIVO", rotulo: "Inativo" },
];

const SEGMENTOS = [
  { valor: "", rotulo: "Todos os segmentos" },
  ...Object.entries(ROTULO_SEGMENTO).map(([valor, rotulo]) => ({ valor, rotulo })),
];

/* As colunas ordenáveis, e **para que lado o primeiro clique ordena**.
   Nome cresce de A a Z, porque é como se lê uma lista. Número começa pelo
   maior, porque quem clica em "faturamento" quer ver quem fatura mais — pedir
   dois cliques para chegar ali é ruído. */
const COLUNAS = [
  { campo: "nome", rotulo: "Parceiro", descPrimeiro: false },
  { campo: "faturamento", rotulo: "Faturamento", descPrimeiro: true, numerica: true },
  { campo: "pedidos", rotulo: "Pedidos", descPrimeiro: true, numerica: true },
  { campo: "ticket_medio", rotulo: "Ticket médio", descPrimeiro: true, numerica: true },
  { campo: "variacao", rotulo: "Variação", descPrimeiro: true, numerica: true },
];

const TAMANHO_PAGINA = 50;

export default function Parceiros() {
  const [parametros, setParametros] = useSearchParams();
  const lugar = useLocation();
  /* O endereço completo da lista, com o filtro. Vai junto para o cadastro, e é
     o que faz o "Voltar" de lá devolver este mesmo recorte. */
  const aqui = lugar.pathname + lugar.search;
  const [resultado, setResultado] = useState({ consulta: null, pagina: null });
  const [categorias, setCategorias] = useState([]);
  const [erro, setErro] = useState(null);

  const busca = parametros.get("busca") ?? "";
  const status = parametros.get("status") ?? "";
  const ativo = parametros.get("ativo") ?? "";
  const categoriaId = parametros.get("categoria_id") ?? "";
  const segmento = parametros.get("segmento") ?? "";
  const ordenarPor = parametros.get("ordenar_por") ?? "nome";
  const descendente = parametros.get("descendente") === "true";
  const pagina = Number(parametros.get("pagina") ?? 1);

  /* Um objeto só com tudo que vai para a API. Montar isto em dois lugares —
     um para a tabela e outro para o link de exportação — é como o arquivo
     passa a sair com um recorte diferente do que está na tela. */
  const filtros = {
    busca,
    status,
    ativo,
    categoria_id: categoriaId,
    segmento,
    ordenar_por: ordenarPor,
    descendente,
  };

  /* "Carregando" é **derivado**: a página na tela só vale se for a resposta da
     consulta atual. Zerar a lista à mão a cada filtro faria um render extra
     e, pior, deixaria a resposta de uma busca antiga aparecer se chegasse
     depois da nova. */
  const consulta = JSON.stringify({ ...filtros, pagina });
  const dados = resultado.consulta === consulta ? resultado.pagina : null;

  useEffect(() => {
    api.get("/api/categorias").then(setCategorias).catch(() => setCategorias([]));
  }, []);

  useEffect(() => {
    let vivo = true;

    /* A busca espera a digitação parar. Uma requisição por tecla inundaria o
       servidor e faria respostas antigas chegarem depois das novas. */
    const relogio = setTimeout(() => {
      api
        .get("/api/parceiros", { ...filtros, pagina, tamanho: TAMANHO_PAGINA })
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
      if (valor === "" || valor === false || valor === undefined) proximos.delete(chave);
      else proximos.set(chave, String(valor));
    }
    /* Mudar filtro volta para a primeira página. Sem isto, quem está na página
       7 e filtra vê "nenhum parceiro" — e conclui que o filtro não encontrou
       nada, quando o que aconteceu foi a página ter deixado de existir. */
    if (!("pagina" in mudancas)) proximos.delete("pagina");
    /* `replace` para o botão voltar não percorrer cada tecla digitada. */
    setParametros(proximos, { replace: true });
  }

  function ordenar(coluna) {
    const mesma = ordenarPor === coluna.campo;
    ajustar({
      ordenar_por: coluna.campo === "nome" && !mesma ? "" : coluna.campo,
      descendente: mesma ? !descendente : coluna.descPrimeiro,
    });
  }

  const filtrando = busca || status || ativo || categoriaId || segmento;
  const total = dados?.total ?? 0;
  const primeiro = (pagina - 1) * TAMANHO_PAGINA + 1;
  const ultimo = Math.min(pagina * TAMANHO_PAGINA, total);

  return (
    <>
      <section className="painel">
        <div className="filtros">
          <div className="campo filtros__busca">
            <label htmlFor="busca">Buscar por nome</label>
            <input
              id="busca"
              type="search"
              value={busca}
              placeholder="Ignora maiúsculas e acentuação"
              onChange={(e) => ajustar({ busca: e.target.value })}
            />
          </div>

          <div className="campo">
            <label htmlFor="categoria">Categoria</label>
            <select
              id="categoria"
              value={categoriaId}
              onChange={(e) => ajustar({ categoria_id: e.target.value })}
            >
              <option value="">Todas as categorias</option>
              {categorias.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nome}
                </option>
              ))}
            </select>
          </div>

          <div className="campo">
            <label htmlFor="segmento">Segmento</label>
            <select
              id="segmento"
              value={segmento}
              onChange={(e) => ajustar({ segmento: e.target.value })}
            >
              {SEGMENTOS.map((s) => (
                <option key={s.valor} value={s.valor}>
                  {s.rotulo}
                </option>
              ))}
            </select>
          </div>

          <div className="campo">
            <label htmlFor="status">Status comercial</label>
            <select
              id="status"
              value={status}
              onChange={(e) => ajustar({ status: e.target.value })}
            >
              {STATUS.map((s) => (
                <option key={s.valor} value={s.valor}>
                  {s.rotulo}
                </option>
              ))}
            </select>
          </div>

          <div className="campo">
            <label htmlFor="ativo">Situação</label>
            <select id="ativo" value={ativo} onChange={(e) => ajustar({ ativo: e.target.value })}>
              {SITUACOES.map((s) => (
                <option key={s.valor} value={s.valor}>
                  {s.rotulo}
                </option>
              ))}
            </select>
          </div>
        </div>
      </section>

      {lugar.state?.aviso && (
        <div className="aviso aviso--sucesso" role="status">
          <p className="aviso__titulo">{lugar.state.aviso}</p>
        </div>
      )}

      {erro && (
        <div className="aviso" role="alert">
          <p className="aviso__titulo">{erro.message}</p>
          {erro.ajuda && <p className="aviso__ajuda">{erro.ajuda}</p>}
        </div>
      )}

      <section className="painel" aria-labelledby="titulo-parceiros">
        <div className="painel__cabecalho">
          <h2 className="painel__titulo" id="titulo-parceiros">
            Parceiros
          </h2>
          <div className="parceiros__acoes">
            <span className="painel__nota">
              {dados ? `${comoInteiro(total)} encontrados` : "carregando…"}
            </span>
            {/* Um link, e não um `fetch`: o navegador já sabe baixar arquivo, e
                o cookie de sessão vai junto por ser a mesma origem. Buscar o
                arquivo por JavaScript exigiria montá-lo inteiro em memória para
                depois entregá-lo — o contrário do que a rota faz. */}
            <a
              className="botao botao--secundario"
              href={`/api/parceiros/exportacao.csv?${new URLSearchParams(
                Object.entries(filtros).filter(([, v]) => v !== "" && v !== false),
              )}`}
              download
            >
              Exportar CSV
            </a>
            <Link className="botao" to="/parceiros/novo" state={{ lista: aqui }}>
              Novo parceiro
            </Link>
          </div>
        </div>

        {!dados && (
          <div style={{ padding: "var(--esp-16)" }} role="status" aria-label="Carregando parceiros">
            {[0, 1, 2, 3, 4].map((i) => (
              <Esqueleto key={i} altura={40} style={{ marginBottom: "var(--esp-8)" }} />
            ))}
          </div>
        )}

        {dados?.itens.length === 0 &&
          (filtrando ? (
            <EstadoVazio
              titulo="Nenhum parceiro com esse recorte"
              texto="Limpe a busca ou os filtros para ver a base inteira."
            />
          ) : (
            <EstadoVazio
              titulo="Nenhum parceiro cadastrado ainda"
              texto="Os parceiros são criados ao importar o primeiro relatório do período."
              acao={{ para: "/importacao", rotulo: "Importar um relatório" }}
            />
          ))}

        {dados?.itens.length > 0 && (
          <>
            <div className="tabela-rolagem">
              <table className="tabela">
                <caption className="so-leitor">
                  Parceiros cadastrados, com o desempenho do período mais recente
                </caption>
                <thead>
                  <tr>
                    {COLUNAS.slice(0, 1).map((coluna) => (
                      <Cabecalho
                        key={coluna.campo}
                        coluna={coluna}
                        ordenarPor={ordenarPor}
                        descendente={descendente}
                        aoOrdenar={ordenar}
                      />
                    ))}
                    <th scope="col">Categoria</th>
                    <th scope="col">Segmento</th>
                    <th scope="col">Status</th>
                    <th scope="col">Situação</th>
                    {COLUNAS.slice(1).map((coluna) => (
                      <Cabecalho
                        key={coluna.campo}
                        coluna={coluna}
                        ordenarPor={ordenarPor}
                        descendente={descendente}
                        aoOrdenar={ordenar}
                      />
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {dados.itens.map((p) => (
                    <Linha key={p.id} parceiro={p} lista={aqui} />
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

/**
 * Um cabeçalho de coluna que ordena.
 *
 * `aria-sort` no `th` é o que diz a um leitor de tela que a tabela está
 * ordenada e por onde. A seta sozinha é informação visual, e não serve a quem
 * não a vê.
 */
function Cabecalho({ coluna, ordenarPor, descendente, aoOrdenar }) {
  const ativa = ordenarPor === coluna.campo;
  const direcao = !ativa ? "none" : descendente ? "descending" : "ascending";

  return (
    <th scope="col" className={coluna.numerica ? "numerica" : undefined} aria-sort={direcao}>
      <button
        type="button"
        className={`ordenavel${ativa ? " ordenavel--ativa" : ""}`}
        onClick={() => aoOrdenar(coluna)}
      >
        {coluna.rotulo}
        {ativa && <IconeVariacao sentido={descendente ? "cai" : "sobe"} aria-hidden="true" />}
      </button>
    </th>
  );
}

function Linha({ parceiro, lista }) {
  const { desempenho } = parceiro;
  const sentido = sentidoDa(desempenho.variacao_percentual);

  return (
    <tr>
      <td className="nome">
        <Link className="nome__link" to={`/parceiros/${parceiro.id}`} state={{ lista }}>
          {parceiro.nome}
        </Link>
      </td>
      <td className="secundaria">{parceiro.categoria?.nome ?? "sem categoria"}</td>
      <td className="secundaria">
        <Segmento valor={desempenho.segmento} />
      </td>
      <td className="secundaria">{ROTULO_STATUS[parceiro.status] ?? parceiro.status}</td>
      <td>
        {/* Situação cadastral **não é segmento**, então não usa cor de
            segmento — "em ascensão" tem um significado só, e ele não é
            "ativo". A diferença vem da forma: ponto cheio ou vazado, ao lado
            do rótulo. */}
        <span className={`ponto-situacao${parceiro.ativo ? "" : " ponto-situacao--inativo"}`} />
        {parceiro.ativo ? "Ativo" : "Inativo"}
      </td>
      <td className="numerica">{comoDinheiro(desempenho.faturamento)}</td>
      <td className="numerica">{comoInteiro(desempenho.pedidos)}</td>
      <td className="numerica secundaria">{comoDinheiro(desempenho.ticket_medio)}</td>
      <td className="numerica">
        {sentido === "indefinida" ? (
          <span style={{ color: "var(--ink-2)" }}>{TRACO}</span>
        ) : (
          <span className={`indicador__variacao indicador__variacao--${sentido}`}>
            {sentido !== "estavel" && <IconeVariacao sentido={sentido} />}
            {comoPercentual(desempenho.variacao_percentual)}
          </span>
        )}
      </td>
    </tr>
  );
}
