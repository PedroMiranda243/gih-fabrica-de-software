/**
 * Modelo preditivo — a versão em uso, o quanto ela erra, e treinar de novo. A API
 * decide se dá para treinar e se a versão nova entrou em uso; a tela só desenha.
 */
import { useState } from "react";
import { useLocation } from "react-router-dom";

import { api, ErroDaApi } from "../api/cliente";
import { useAcompanhar, useCarregar, useFiltros } from "../api/ganchos";
import Confirmacao from "../componentes/Confirmacao";
import { Ausente } from "../componentes/Dados";
import { Carregando, ErroDaAcao, ErroDaTela, Nota, Sucesso, Vazio } from "../componentes/Estados";
import Icone from "../componentes/Icone";
import Lacre from "../componentes/Lacre";
import { CaixaDeTabela, Paginacao } from "../componentes/Lista";
import { useTitulo } from "../componentes/Titulo";
import Barras from "../graficos/Barras";
import { comoDataHora, comoDecimal, comoFracao, comoInteiro, comoPeriodo, comoTempo, plural, ROTULO_ORIGEM_PREVISAO, ROTULO_SITUACAO_TREINO } from "../formato";

const TAMANHO = 10;

export default function Modelo() {
  useTitulo("Modelo preditivo", "Modelo");
  const lugar = useLocation();
  const [filtros, mudar] = useFiltros();
  const pagina = Number(filtros.pagina) || 1;
  const estado = useCarregar(() => api.get("/api/modelo"), "modelo");
  const historico = useCarregar(() => api.get("/api/modelo/treinos", { pagina, tamanho: TAMANHO }), `h${lugar.search}`);
  const [acompanhando, setAcompanhando] = useState(null);
  const [confirmando, setConfirmando] = useState(false);
  const [erro, setErro] = useState(null);
  const [resultado, setResultado] = useState(null);
  const [disparando, setDisparando] = useState(false);
  const [terminados, setTerminados] = useState([]);

  const emAndamento = estado.dados?.em_andamento;
  const idEmAndamento = acompanhando ?? (emAndamento && !terminados.includes(emAndamento.id) ? emAndamento.id : null);
  const treino = useAcompanhar(idEmAndamento, (id) => api.get(`/api/modelo/treinos/${id}`), (t) => {
    setResultado(t);
    setTerminados((l) => [...l, t.id]);
    setAcompanhando(null);
    estado.recarregar();
    historico.recarregar();
  });

  if (estado.carregando) return <Carregando rotulo="Carregando o modelo" linhas={8} />;
  if (estado.erro) return <ErroDaTela erro={estado.erro} />;
  const m = estado.dados;
  const rodando = treino.atual?.situacao === "EM_ANDAMENTO" || (idEmAndamento !== null && !treino.atual);

  async function treinar() {
    setDisparando(true);
    setErro(null);
    setResultado(null);
    try {
      const t = await api.post("/api/modelo/treinos");
      setAcompanhando(t.id);
      setConfirmando(false);
    } catch (e) {
      setErro(e);
      setConfirmando(false);
      if (e instanceof ErroDaApi && e.status === 409 && e.detalhe?.em_andamento) setAcompanhando(e.detalhe.em_andamento);
    } finally {
      setDisparando(false);
    }
  }

  const tv = m.treino_da_versao;
  const metricas = tv?.metricas;

  return (
    <div className="pagina">
      <p className="sr-only" role="status" aria-live="polite">
        {rodando ? "Treino em andamento." : resultado ? textoDoResultado(resultado) : ""}
      </p>
      <div className="modelo-grade">
        <section className="bloco" aria-labelledby="t-versao">
          <div className="bloco__cabeca">
            <h2 id="t-versao" className="bloco__titulo">
              Versão em uso
            </h2>
          </div>
          {!m.versao_em_uso ? (
            <Vazio titulo="O modelo ainda não foi treinado" compacto icone="modelo">
              O treino aprende com o histórico importado e gera a previsão de faturamento e o risco de queda de cada parceiro para o próximo período. Ele pede {plural(m.periodos_minimos, "período importado", "períodos importados")}; a base tem {comoInteiro(m.periodos_na_base)}.
            </Vazio>
          ) : (
            <>
              <Lacre titulo={`${m.versao_em_uso} em uso · ${ROTULO_ORIGEM_PREVISAO[m.origem] ?? m.origem}`} quando={tv?.concluido_em} quem={tv?.autor ?? (tv ? "pelo terminal" : null)} />
              {tv && (
                <dl className="pares pares--modelo">
                  <div>
                    <dt>Treinada</dt>
                    <dd>{comoDataHora(tv.concluido_em)}</dd>
                  </div>
                  <div>
                    <dt>Dados até</dt>
                    <dd>{comoPeriodo(tv.periodo_base)}</dd>
                  </div>
                  <div>
                    <dt>Parceiros</dt>
                    <dd className="valor-forte">{comoInteiro(tv.volume?.parceiros)}</dd>
                  </div>
                  <div>
                    <dt>Períodos</dt>
                    <dd className="valor-forte">{comoInteiro(tv.volume?.periodos)}</dd>
                  </div>
                  <div>
                    <dt>Amostras de teste</dt>
                    <dd className="valor-forte">{comoInteiro(tv.volume?.amostras_teste)}</dd>
                  </div>
                  <div>
                    <dt>Duração</dt>
                    <dd className="valor-forte">{comoTempo(tv.segundos)}</dd>
                  </div>
                </dl>
              )}
              <p className="bloco__nota">As previsões de cada parceiro já saem dela. A comparação com as referências está ao lado.</p>
              {m.desatualizado && (
                <Nota tipo="atencao">
                  Há período importado depois do último treino: o mais recente é {comoPeriodo(m.periodo_mais_recente)}, e as previsões partem de {comoPeriodo(m.periodo_das_previsoes)}.
                </Nota>
              )}
            </>
          )}
        </section>

        <section className="bloco" aria-labelledby="t-erro">
          <div className="bloco__cabeca">
            <h2 id="t-erro" className="bloco__titulo">
              O quanto ela erra
            </h2>
            <p className="bloco__sub">No conjunto de teste, contra as contas simples. A barra começa no zero.</p>
          </div>
          {!metricas ? (
            <p className="discreto">As métricas aparecem depois do primeiro treino.</p>
          ) : (
            <div className="metricas">
              <div>
                <h3 className="bloco__subtitulo">Erro no faturamento previsto</h3>
                <p className="metricas__leitura">MAPE — menor é melhor</p>
                <Barras
                  rotulo="Erro no faturamento previsto (MAPE), menor é melhor"
                  formato={(v) => comoFracao(v, 1)}
                  itens={[
                    { chave: "rede", nome: "Rede", valor: metricas.mape_modelo, destaque: true },
                    { chave: "media", nome: "Média móvel dos últimos 4", valor: metricas.mape_media_movel },
                    { chave: "ultimo", nome: "Repetir o último período", valor: metricas.mape_ultimo },
                  ]}
                />
              </div>
              <div>
                <h3 className="bloco__subtitulo">Erro no risco de queda</h3>
                <p className="metricas__leitura">Brier — menor é melhor</p>
                <Barras
                  rotulo="Erro no risco de queda (Brier), menor é melhor"
                  formato={(v) => comoDecimal(v, 3)}
                  itens={[
                    { chave: "rede", nome: "Rede", valor: metricas.brier_modelo, destaque: true },
                    { chave: "taxa", nome: "Taxa observada", valor: metricas.brier_referencia },
                  ]}
                />
              </div>
            </div>
          )}
        </section>
      </div>

      <section className="bloco" aria-labelledby="t-treinar">
        <div className="bloco__cabeca bloco__cabeca--linha">
          <div>
            <h2 id="t-treinar" className="bloco__titulo">
              Treinar de novo
            </h2>
            <p className="bloco__sub">O treino roda em segundo plano no servidor; você pode sair desta tela e voltar.</p>
          </div>
          {!confirmando && (
            <button type="button" className="botao botao--primario" onClick={() => (setResultado(null), setErro(null), setConfirmando(true))} disabled={!m.pode_treinar || rodando}>
              <Icone nome="modelo" /> {rodando ? "Treinando…" : "Treinar agora"}
            </button>
          )}
        </div>
        {!m.pode_treinar && !rodando && m.motivo_bloqueio && <Nota>{m.motivo_bloqueio}</Nota>}
        {confirmando && (
          <Confirmacao
            texto={`Treinar com os ${comoInteiro(m.periodos_na_base)} períodos da base?`}
            detalhe="O treino roda em segundo plano e leva alguns segundos. A versão nova só entra em uso se errar menos que as contas simples — quem decide é o servidor."
            acao="Treinar"
            ocupado={disparando}
            aoConfirmar={treinar}
            aoCancelar={() => setConfirmando(false)}
          />
        )}
        <ErroDaAcao erro={erro} />
        {rodando && (
          <div className="andamento" role="status" aria-live="polite">
            <span className="andamento__barra andamento__barra--indeterminada" aria-hidden="true" />
            <p>
              <strong>Treinando{treino.atual ? ` a versão ${treino.atual.versao}` : ""}…</strong> Iniciado {treino.atual ? comoDataHora(treino.atual.iniciado_em) : "agora"}. A tela acompanha a cada 2 segundos.
            </p>
          </div>
        )}
        {resultado && resultado.situacao === "CONCLUIDO" && (
          <Sucesso foco>
            <p>{textoDoResultado(resultado)}</p>
            {!resultado.promovido && resultado.motivo && <p className="aviso__ajuda">{resultado.motivo}</p>}
          </Sucesso>
        )}
        {resultado && resultado.situacao === "FALHOU" && <ErroDaAcao erro={{ message: textoDoResultado(resultado) }} />}
      </section>

      <section className="bloco" aria-labelledby="t-historico" aria-busy={historico.carregando}>
        <div className="bloco__cabeca">
          <h2 id="t-historico" className="bloco__titulo">
            Histórico de treinos
          </h2>
          <p className="bloco__sub">Do mais recente para o mais antigo</p>
        </div>
        {historico.carregando && <Carregando rotulo="Carregando o histórico" linhas={4} />}
        <ErroDaTela erro={historico.erro} />
        {historico.dados && !historico.dados.itens.length && (
          <Vazio titulo="Nenhum treino ainda" compacto icone="modelo">
            Cada treino fica registrado aqui, com data, volume de dados e as métricas contra as referências.
          </Vazio>
        )}
        {historico.dados && historico.dados.itens.length > 0 && (
          <>
            <CaixaDeTabela rotulo="Histórico de treinos">
              <table className="tabela">
                <caption className="sr-only">Treinos do modelo, do mais recente para o mais antigo</caption>
                <thead>
                  <tr>
                    <th scope="col">Iniciado</th>
                    <th scope="col">Por</th>
                    <th scope="col">Situação</th>
                    <th scope="col" className="num">
                      Erro da rede
                    </th>
                    <th scope="col" className="num">
                      Média móvel
                    </th>
                    <th scope="col" className="num">
                      Último período
                    </th>
                    <th scope="col">Resultado</th>
                  </tr>
                </thead>
                <tbody>
                  {historico.dados.itens.map((t) => (
                    <tr key={t.id}>
                      <th scope="row">{comoDataHora(t.iniciado_em)}</th>
                      <td>{t.autor ?? <span className="discreto">pelo terminal</span>}</td>
                      <td>{ROTULO_SITUACAO_TREINO[t.situacao] ?? t.situacao}</td>
                      <td className="num">{t.metricas?.mape_modelo === null ? <Ausente porque="sem métrica" /> : comoFracao(t.metricas?.mape_modelo, 1)}</td>
                      <td className="num">{t.metricas?.mape_media_movel === null ? <Ausente porque="sem métrica" /> : comoFracao(t.metricas?.mape_media_movel, 1)}</td>
                      <td className="num">{t.metricas?.mape_ultimo === null ? <Ausente porque="sem métrica" /> : comoFracao(t.metricas?.mape_ultimo, 1)}</td>
                      <td>
                        {t.situacao === "EM_ANDAMENTO" ? (
                          <span className="discreto">em andamento</span>
                        ) : t.situacao === "FALHOU" ? (
                          <span className="texto-erro">falhou{t.motivo ? `: ${t.motivo}` : ""}</span>
                        ) : t.promovido ? (
                          <span className="resultado-promovido">{t.versao} entrou em uso</span>
                        ) : (
                          <span>Mantida: {t.versao_em_uso ?? "—"}</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CaixaDeTabela>
            <Paginacao pagina={pagina} tamanho={TAMANHO} total={historico.dados.total} aoMudar={(p) => mudar({ pagina: p > 1 ? p : null }, { manterPagina: true })} rotulo="treinos" />
          </>
        )}
      </section>
    </div>
  );
}

function textoDoResultado(t) {
  if (t.situacao === "FALHOU") return `O treino falhou.${t.motivo ? ` ${t.motivo}` : ""}`;
  if (t.promovido) return `Treino concluído: a versão ${t.versao} entrou em uso.`;
  return `Treino concluído; continua em uso a versão ${t.versao_em_uso ?? "anterior"}.`;
}
