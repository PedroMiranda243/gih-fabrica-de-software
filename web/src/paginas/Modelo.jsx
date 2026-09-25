/**
 * O modelo preditivo — UC07, RF27, histórias H42 a H46 — para Administrador e
 * Gestor.
 *
 * **O treino não roda na requisição** (ADR-010). "Treinar agora" recebe `202`
 * com o treino em andamento, e a tela consulta o estado a cada 2 s até ele
 * terminar. Enquanto isso, a página continua usável, e quem sair e voltar
 * reencontra o andamento — ele vem do servidor, e não da memória da tela.
 *
 * **Quem decide é a API** (regra 2.4). Se dá para treinar, por que não, se a
 * versão nova entrou em uso e por que não entrou: tudo chega pronto, e a tela
 * só desenha. Ela não compara erro com erro para concluir nada.
 *
 * **O resultado é dito, não deduzido.** Ao terminar, a região de status
 * anuncia o que aconteceu — entrou em uso, ficou a anterior (com o motivo) ou
 * falhou —, e o leitor de tela ouve sem ninguém precisar procurar.
 */
import { useEffect, useState } from "react";

import { api } from "../api/cliente";
import { Esqueleto } from "../componentes/Carregando";
import ComparacaoReferencias from "../componentes/ComparacaoReferencias";
import Confirmacao from "../componentes/Confirmacao";
import EstadoVazio from "../componentes/EstadoVazio";
import {
  comoDataHora,
  comoDecimal,
  comoFracao,
  comoInteiro,
  comoPeriodo,
  ROTULO_ORIGEM_PREVISAO,
  ROTULO_SITUACAO_TREINO,
  TRACO,
} from "../formato";
import "../estilos/modelo.css";

/* De quanto em quanto tempo a tela pergunta pelo treino. O treino da base de
   demonstração leva cerca de 1 s e o de 5.000 parceiros cerca de 8 s
   (`docs/medicoes/modelo.md`): 2 s responde rápido sem martelar a API. */
export const INTERVALO_MS = 2000;
const POR_PAGINA = 10;

export default function Modelo() {
  const [estado, setEstado] = useState(null);
  const [erroCarga, setErroCarga] = useState(null);
  const [recarga, setRecarga] = useState(0);
  const [acompanhando, setAcompanhando] = useState(null);
  const [resultado, setResultado] = useState(null);
  const [confirmando, setConfirmando] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState(null);

  useEffect(() => {
    let vivo = true;
    api
      .get("/api/modelo")
      .then((dados) => {
        if (!vivo) return;
        setEstado(dados);
        /* Treino em andamento que a tela ainda não acompanha — disparado em
           outra aba, pelo terminal, ou antes de a pessoa sair e voltar. */
        if (dados.em_andamento) setAcompanhando(dados.em_andamento);
      })
      .catch((e) => vivo && setErroCarga(e));
    return () => {
      vivo = false;
    };
  }, [recarga]);

  const idAcompanhado = acompanhando?.id;
  useEffect(() => {
    if (!idAcompanhado) return undefined;
    const relogio = setInterval(() => {
      api
        .get(`/api/modelo/treinos/${idAcompanhado}`)
        .then((treino) => {
          if (treino.situacao === "EM_ANDAMENTO") return;
          setAcompanhando(null);
          setResultado(treino);
          setRecarga((r) => r + 1);
        })
        /* Falha de rede numa consulta não encerra o acompanhamento: a próxima
           tenta de novo. O treino continua no servidor de qualquer jeito. */
        .catch(() => {});
    }, INTERVALO_MS);
    return () => clearInterval(relogio);
  }, [idAcompanhado]);

  async function treinar() {
    setEnviando(true);
    setErro(null);
    setResultado(null);
    try {
      const treino = await api.post("/api/modelo/treinos");
      setAcompanhando(treino);
      setRecarga((r) => r + 1);
    } catch (e) {
      setErro(e);
    } finally {
      setEnviando(false);
      setConfirmando(false);
    }
  }

  if (erroCarga) {
    return (
      <div className="aviso" role="alert">
        <p className="aviso__titulo">{erroCarga.message}</p>
        {erroCarga.ajuda && <p className="aviso__ajuda">{erroCarga.ajuda}</p>}
      </div>
    );
  }

  if (!estado) {
    return (
      <section className="painel" aria-busy="true" aria-label="Carregando o modelo">
        <div className="modelo__corpo">
          <Esqueleto altura={260} />
        </div>
      </section>
    );
  }

  const podeTreinar = estado.pode_treinar && !acompanhando;

  return (
    <>
      {/* O anúncio fica sempre no DOM, só para o leitor de tela: região viva
          que aparece junto com o texto costuma não ser lida. Os avisos
          visíveis vêm e vão sem deixar espaço vazio na página. */}
      <p className="so-leitor" role="status">
        {anuncio(acompanhando, resultado)}
      </p>
      {acompanhando && <Andamento treino={acompanhando} />}
      {!acompanhando && resultado && <Resultado treino={resultado} />}

      {erro && (
        <div className="aviso" role="alert">
          <p className="aviso__titulo">{erro.message}</p>
          {erro.ajuda && <p className="aviso__ajuda">{erro.ajuda}</p>}
        </div>
      )}

      <section className="painel" aria-labelledby="titulo-versao">
        <div className="painel__cabecalho">
          <h2 className="painel__titulo" id="titulo-versao">
            Versão em uso
          </h2>
          <span className="painel__nota">
            {estado.versao_em_uso
              ? `${estado.versao_em_uso} · ${ROTULO_ORIGEM_PREVISAO[estado.origem] ?? ""}`
              : "Nenhuma ainda"}
          </span>
          <div className="painel__acoes">
            <button
              type="button"
              className="botao"
              disabled={!podeTreinar || confirmando}
              onClick={() => setConfirmando(true)}
            >
              {acompanhando ? "Treinando…" : "Treinar agora"}
            </button>
          </div>
        </div>

        {!estado.pode_treinar && !acompanhando && estado.motivo_bloqueio && (
          <p className="modelo__bloqueio">{estado.motivo_bloqueio}</p>
        )}

        {confirmando && (
          <div className="modelo__corpo">
            <Confirmacao
              texto={
                `Treinar com os ${estado.periodos_na_base} períodos da base? O treino roda em ` +
                "segundo plano, e a versão nova só entra em uso se errar menos que as " +
                "referências no faturamento e no risco."
              }
              acao="Treinar"
              ocupado={enviando}
              aoConfirmar={treinar}
              aoCancelar={() => setConfirmando(false)}
            />
          </div>
        )}

        {estado.desatualizado && (
          <div className="modelo__corpo">
            <div className="aviso aviso--informativo">
              <p className="aviso__titulo">Há período importado depois do último treino.</p>
              <p className="aviso__ajuda">
                As previsões em uso partem de {comoPeriodo(estado.periodo_das_previsoes)};
                o período mais recente é {comoPeriodo(estado.periodo_mais_recente)}. Um novo treino
                o incorpora.
              </p>
            </div>
          </div>
        )}

        {estado.treino_da_versao ? (
          <VersaoEmUso estado={estado} treino={estado.treino_da_versao} />
        ) : (
          <EstadoVazio
            titulo="O modelo ainda não foi treinado"
            texto={
              `O treino aprende com o histórico importado e gera a previsão de faturamento e o ` +
              `risco de cada parceiro. Exige ${estado.periodos_minimos} períodos; a base tem ` +
              `${estado.periodos_na_base}.`
            }
          />
        )}
      </section>

      <Historico recarga={recarga} />
    </>
  );
}

function Andamento({ treino }) {
  return (
    <div className="aviso aviso--informativo modelo__andamento">
      <p className="aviso__titulo">Treinando o modelo…</p>
      <p className="aviso__ajuda">
        Iniciado {comoDataHora(treino.iniciado_em)}
        {treino.autor ? ` por ${treino.autor}` : " pelo terminal"}. A tela se atualiza sozinha
        quando ele terminar; você pode sair e voltar.
      </p>
      <div className="modelo__barra-andamento" aria-hidden="true" />
    </div>
  );
}

function Resultado({ treino }) {
  if (treino.situacao === "FALHOU") {
    return (
      <div className="aviso">
        <p className="aviso__titulo">O treino falhou.</p>
        <p className="aviso__ajuda">{treino.motivo}</p>
      </div>
    );
  }
  if (treino.promovido) {
    return (
      <div className="aviso aviso--sucesso">
        <p className="aviso__titulo">Treino concluído: a versão {treino.versao} entrou em uso.</p>
        <p className="aviso__ajuda">
          As previsões de cada parceiro já saem dela. A comparação com as referências está abaixo.
        </p>
      </div>
    );
  }
  return (
    <div className="aviso aviso--informativo">
      <p className="aviso__titulo">
        Treino concluído, mas a versão nova não entrou em uso. Em uso: {treino.versao_em_uso}.
      </p>
      <p className="aviso__ajuda">{treino.motivo}</p>
    </div>
  );
}

function VersaoEmUso({ estado, treino }) {
  const m = treino.metricas;
  const v = treino.volume;
  return (
    <div className="modelo__corpo modelo__versao">
      <div>
        {estado.origem === "REFERENCIA" && (
          <p className="modelo__explica">
            Nenhuma versão da rede superou as referências ainda. Enquanto isso, as previsões saem
            das contas simples medidas neste treino — e são identificadas assim no cadastro de cada
            parceiro.
          </p>
        )}
        <dl className="modelo__fatos">
          <dt>Treinada</dt>
          <dd>
            {comoDataHora(treino.concluido_em)}
            {treino.autor ? ` · ${treino.autor}` : " · pelo terminal"}
          </dd>
          <dt>Dados até</dt>
          <dd>{comoPeriodo(treino.periodo_base)}</dd>
          <dt>Parceiros</dt>
          <dd className="num">{comoInteiro(v.parceiros)}</dd>
          <dt>Períodos</dt>
          <dd className="num">{comoInteiro(v.periodos)}</dd>
          <dt>Amostras de teste</dt>
          <dd className="num">{comoInteiro(v.amostras_teste)}</dd>
          <dt>Duração</dt>
          <dd className="num">
            {treino.segundos === null ? TRACO : `${comoDecimal(treino.segundos, 1)} s`}
          </dd>
        </dl>
      </div>

      <div className="modelo__graficos">
        <ComparacaoReferencias
          titulo="Erro no faturamento previsto"
          nota="MAPE — menor é melhor"
          formatar={(x) => comoFracao(x)}
          barras={[
            { rotulo: "Rede", valor: m.mape_modelo, destaque: true },
            { rotulo: "Média móvel dos últimos 4", valor: m.mape_media_movel },
            { rotulo: "Repetir o último período", valor: m.mape_ultimo },
          ]}
        />
        <ComparacaoReferencias
          titulo="Erro no risco de queda"
          nota="Brier — menor é melhor"
          formatar={(x) => comoDecimal(x)}
          barras={[
            { rotulo: "Rede", valor: m.brier_modelo, destaque: true },
            { rotulo: "Taxa observada", valor: m.brier_referencia },
          ]}
        />
        <p className="modelo__rodape">
          Medido no período mais recente da base, que o treino não viu: o último período testa, o
          penúltimo valida e os anteriores treinam (RN09).
        </p>
      </div>
    </div>
  );
}

/** O histórico de treinos (RF27), do mais recente para o mais antigo. */
function Historico({ recarga }) {
  const [pagina, setPagina] = useState(1);
  const [dados, setDados] = useState(null);

  useEffect(() => {
    let vivo = true;
    api
      .get("/api/modelo/treinos", { pagina, tamanho: POR_PAGINA })
      .then((d) => vivo && setDados(d))
      .catch(() => vivo && setDados({ itens: [], total: 0 }));
    return () => {
      vivo = false;
    };
  }, [pagina, recarga]);

  const total = dados?.total ?? 0;
  const inicio = (pagina - 1) * POR_PAGINA;

  return (
    <section className="painel historico-treinos" aria-labelledby="titulo-treinos">
      <div className="painel__cabecalho">
        <h2 className="painel__titulo" id="titulo-treinos">
          Histórico de treinos
        </h2>
        <span className="painel__nota">
          {dados ? `${comoInteiro(total)} ${total === 1 ? "treino" : "treinos"}` : "carregando…"}
        </span>
      </div>

      {dados && total === 0 && (
        <EstadoVazio
          titulo="Nenhum treino ainda"
          texto="Cada treino fica registrado aqui, com data, volume de dados e as métricas contra as referências."
        />
      )}

      {dados && total > 0 && (
        <>
          <div className="tabela-rolagem">
            <table className="tabela">
              <caption className="so-leitor">
                Treinos do modelo, do mais recente para o mais antigo
              </caption>
              <thead>
                <tr>
                  <th scope="col">Iniciado</th>
                  <th scope="col">Por</th>
                  <th scope="col">Situação</th>
                  <th scope="col" className="numerica">
                    Erro da rede
                  </th>
                  <th scope="col" className="numerica">
                    Média móvel
                  </th>
                  <th scope="col" className="numerica">
                    Último período
                  </th>
                  <th scope="col">Resultado</th>
                </tr>
              </thead>
              <tbody>
                {dados.itens.map((t) => (
                  <tr key={t.id}>
                    <td className="quando num">{comoDataHora(t.iniciado_em)}</td>
                    <td>{t.autor ?? "terminal"}</td>
                    <td>{ROTULO_SITUACAO_TREINO[t.situacao] ?? t.situacao}</td>
                    <td className="numerica">{comoFracao(t.metricas.mape_modelo)}</td>
                    <td className="numerica">{comoFracao(t.metricas.mape_media_movel)}</td>
                    <td className="numerica">{comoFracao(t.metricas.mape_ultimo)}</td>
                    <td className="resultado">{resultadoDe(t)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {total > POR_PAGINA && (
            <nav className="paginacao" aria-label="Páginas do histórico de treinos">
              <span className="paginacao__posicao">
                {inicio + 1}–{Math.min(inicio + POR_PAGINA, total)} de {comoInteiro(total)}
              </span>
              <button
                type="button"
                className="botao botao--secundario"
                disabled={pagina === 1}
                onClick={() => setPagina((p) => p - 1)}
              >
                Anterior
              </button>
              <button
                type="button"
                className="botao botao--secundario"
                disabled={inicio + POR_PAGINA >= total}
                onClick={() => setPagina((p) => p + 1)}
              >
                Próxima
              </button>
            </nav>
          )}
        </>
      )}
    </section>
  );
}

function anuncio(acompanhando, resultado) {
  if (acompanhando) return "Treinando o modelo.";
  if (!resultado) return "";
  if (resultado.situacao === "FALHOU") return `O treino falhou. ${resultado.motivo}`;
  if (resultado.promovido) return `Treino concluído: a versão ${resultado.versao} entrou em uso.`;
  return `Treino concluído; continua em uso a versão ${resultado.versao_em_uso}.`;
}

/** O que o treino deixou, em palavras — com o que a API registrou. */
function resultadoDe(treino) {
  if (treino.situacao === "EM_ANDAMENTO") return TRACO;
  if (treino.situacao === "FALHOU") return treino.motivo;
  if (treino.promovido) return `${treino.versao} entrou em uso`;
  return `Mantida: ${treino.versao_em_uso}`;
}
