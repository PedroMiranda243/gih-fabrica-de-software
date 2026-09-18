/**
 * Lista de parceiros, com busca e filtros (UC04, RF24).
 *
 * A busca ignora maiúsculas **e acentuação** — é o servidor que faz isso, por
 * coluna normalizada e índice de trigrama. A tela só manda o termo.
 *
 * O filtro vive na URL. Não é capricho: um recorte útil precisa poder ser
 * mandado para outra pessoa por link, e o botão voltar precisa desfazer o
 * filtro, não sair da tela.
 */
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { api } from "../api/cliente";
import { Esqueleto } from "../componentes/Carregando";
import EstadoVazio from "../componentes/EstadoVazio";
import { comoData } from "../formato";
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

export default function Parceiros() {
  const [parametros, setParametros] = useSearchParams();
  const [resultado, setResultado] = useState({ consulta: null, lista: null });
  const [categorias, setCategorias] = useState([]);
  const [erro, setErro] = useState(null);

  const busca = parametros.get("busca") ?? "";
  const status = parametros.get("status") ?? "";
  const ativo = parametros.get("ativo") ?? "";
  const categoriaId = parametros.get("categoria_id") ?? "";

  /* "Carregando" é **derivado**: a lista na tela só vale se for a resposta da
     consulta atual. Zerar a lista à mão a cada filtro faria um render extra
     e, pior, deixaria a resposta de uma busca antiga aparecer se chegasse
     depois da nova. */
  const consulta = JSON.stringify({ busca, status, ativo, categoriaId });
  const lista = resultado.consulta === consulta ? resultado.lista : null;

  useEffect(() => {
    api.get("/api/categorias").then(setCategorias).catch(() => setCategorias([]));
  }, []);

  useEffect(() => {
    let vivo = true;

    /* A busca espera a digitação parar. Uma requisição por tecla inundaria o
       servidor e faria respostas antigas chegarem depois das novas. */
    const relogio = setTimeout(() => {
      api
        .get("/api/parceiros", { busca, status, ativo, categoria_id: categoriaId })
        .then((dados) => vivo && setResultado({ consulta, lista: dados }))
        .catch((e) => vivo && setErro(e));
    }, 250);

    return () => {
      vivo = false;
      clearTimeout(relogio);
    };
  }, [consulta, busca, status, ativo, categoriaId]);

  function ajustar(chave, valor) {
    const proximos = new URLSearchParams(parametros);
    if (valor) proximos.set(chave, valor);
    else proximos.delete(chave);
    /* `replace` para o botão voltar não percorrer cada tecla digitada. */
    setParametros(proximos, { replace: true });
  }

  const filtrando = busca || status || ativo || categoriaId;

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
              onChange={(e) => ajustar("busca", e.target.value)}
            />
          </div>

          <div className="campo">
            <label htmlFor="categoria">Categoria</label>
            <select
              id="categoria"
              value={categoriaId}
              onChange={(e) => ajustar("categoria_id", e.target.value)}
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
            <label htmlFor="status">Status comercial</label>
            <select id="status" value={status} onChange={(e) => ajustar("status", e.target.value)}>
              {STATUS.map((s) => (
                <option key={s.valor} value={s.valor}>
                  {s.rotulo}
                </option>
              ))}
            </select>
          </div>

          <div className="campo">
            <label htmlFor="ativo">Situação</label>
            <select id="ativo" value={ativo} onChange={(e) => ajustar("ativo", e.target.value)}>
              {SITUACOES.map((s) => (
                <option key={s.valor} value={s.valor}>
                  {s.rotulo}
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

      <section className="painel" aria-labelledby="titulo-parceiros">
        <div className="painel__cabecalho">
          <h2 className="painel__titulo" id="titulo-parceiros">
            Parceiros
          </h2>
          <span className="painel__nota">{lista ? `${lista.length} encontrados` : "carregando…"}</span>
        </div>

        {!lista && (
          <div style={{ padding: "var(--esp-16)" }} role="status" aria-label="Carregando parceiros">
            {[0, 1, 2, 3, 4].map((i) => (
              <Esqueleto key={i} altura={40} style={{ marginBottom: "var(--esp-8)" }} />
            ))}
          </div>
        )}

        {lista?.length === 0 &&
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

        {lista?.length > 0 && (
          <div className="tabela-rolagem">
            <table className="tabela">
              <caption className="so-leitor">Parceiros cadastrados</caption>
              <thead>
                <tr>
                  <th scope="col">Parceiro</th>
                  <th scope="col">Categoria</th>
                  <th scope="col">Status</th>
                  <th scope="col">Situação</th>
                  <th scope="col">Contato</th>
                  <th scope="col">Cadastrado em</th>
                </tr>
              </thead>
              <tbody>
                {lista.map((p) => (
                  <tr key={p.id}>
                    <td className="nome">{p.nome}</td>
                    <td className="secundaria">{p.categoria?.nome ?? "sem categoria"}</td>
                    <td className="secundaria">{p.status}</td>
                    <td>
                      {/* Situação cadastral **não é segmento**, então não usa
                          cor de segmento — "em ascensão" tem um significado
                          só, e ele não é "ativo". A diferença vem da forma:
                          ponto cheio ou vazado, ao lado do rótulo. */}
                      <span className={`ponto-situacao${p.ativo ? "" : " ponto-situacao--inativo"}`} />
                      {p.ativo ? "Ativo" : "Inativo"}
                    </td>
                    <td className="secundaria">{p.contato ?? "—"}</td>
                    <td className="secundaria num">{comoData(p.criado_em?.slice(0, 10))}</td>
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
