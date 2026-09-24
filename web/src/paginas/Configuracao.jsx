/**
 * Limiares da segmentação (RF21, H34) — só o Administrador.
 *
 * Os três números que decidem a régua de RN01 para a rede inteira: quantos são
 * o Top, quantos períodos seguidos fazem tendência, e até quando um parceiro é
 * recém-chegado. **A validação é do servidor** (regra 2.4): os atributos `min` e
 * `max` só dão as setas do campo, e `noValidate` deixa a mensagem da API — em
 * português, dizendo o limite — aparecer embaixo do campo certo.
 *
 * **O que a gravação faz é dito antes e depois.** A API reclassifica só o
 * período mais recente; os anteriores ficam com a classificação antiga até o
 * reprocessamento completo, pelo terminal. Configuração que muda menos do que a
 * pessoa imagina engana quem a mudou — por isso a confirmação avisa, e o aviso
 * de sucesso repete com o número que a API devolveu.
 */
import { useEffect, useState } from "react";

import { api } from "../api/cliente";
import { Esqueleto } from "../componentes/Carregando";
import Campo from "../componentes/Campo";
import Confirmacao from "../componentes/Confirmacao";
import { comoDataHora } from "../formato";
import "../estilos/configuracao.css";

/* Rótulo e explicação de cada limiar. O texto acompanha a descrição de
   `LimiaresSegmentacao` na API; os limites de `max` espelham os de lá só para
   as setas do campo — quem recusa é o servidor. */
const LIMIARES = [
  {
    nome: "top_n",
    rotulo: "Tamanho do Top",
    ajuda: "Quantos parceiros, a partir do maior faturamento do período, formam o Top.",
    max: 1000,
  },
  {
    nome: "periodos_tendencia",
    rotulo: "Períodos de tendência",
    ajuda:
      "Quantos períodos seguidos de queda classificam como em risco — e de alta, como em ascensão.",
    max: 52,
  },
  {
    nome: "periodos_novato",
    rotulo: "Períodos de recém-chegado",
    ajuda: "Com histórico menor que isto, o parceiro é recém-chegado.",
    max: 52,
  },
];

const COMANDO = "docker compose exec api python -m app.cli reprocessar-segmentos";

function valoresDe(configuracao) {
  return Object.fromEntries(LIMIARES.map(({ nome }) => [nome, String(configuracao[nome])]));
}

export default function Configuracao() {
  const [atual, setAtual] = useState(null);
  const [valores, setValores] = useState(null);
  const [erroCarga, setErroCarga] = useState(null);
  const [erro, setErro] = useState(null);
  const [sucesso, setSucesso] = useState(null);
  const [confirmando, setConfirmando] = useState(false);
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    let vivo = true;
    api
      .get("/api/configuracao/segmentacao")
      .then((c) => {
        if (!vivo) return;
        setAtual(c);
        setValores(valoresDe(c));
      })
      .catch((e) => vivo && setErroCarga(e));
    return () => {
      vivo = false;
    };
  }, []);

  if (erroCarga) {
    return (
      <div className="aviso" role="alert">
        <p className="aviso__titulo">{erroCarga.message}</p>
        {erroCarga.ajuda && <p className="aviso__ajuda">{erroCarga.ajuda}</p>}
      </div>
    );
  }

  if (!atual) {
    return (
      <section className="painel" aria-busy="true" aria-label="Carregando os limiares">
        <div className="limiares">
          <Esqueleto altura={220} />
        </div>
      </section>
    );
  }

  const mudou = LIMIARES.some(({ nome }) => valores[nome] !== String(atual[nome]));
  const erroDoCampo = Object.fromEntries((erro?.campos ?? []).map((c) => [c.campo, c]));

  function mudar(nome, valor) {
    setValores((v) => ({ ...v, [nome]: valor }));
    // A confirmação e o aviso falam do que estava na tela quando apareceram.
    setSucesso(null);
    setConfirmando(false);
  }

  function pedirConfirmacao(evento) {
    evento.preventDefault();
    setErro(null);
    setConfirmando(true);
  }

  async function salvar() {
    setEnviando(true);
    try {
      const salvo = await api.put("/api/configuracao/segmentacao", valores);
      setAtual(salvo);
      setValores(valoresDe(salvo));
      setSucesso(salvo.periodos_reprocessados);
      setErro(null);
    } catch (e) {
      setErro(e);
      const primeiro = LIMIARES.find(({ nome }) => e.campos?.some((c) => c.campo === nome));
      if (primeiro) document.getElementById(`campo-${primeiro.nome}`)?.focus();
    } finally {
      setEnviando(false);
      setConfirmando(false);
    }
  }

  return (
    <>
      {sucesso !== null && (
        <div className="aviso aviso--sucesso" role="status">
          <p className="aviso__titulo">Limiares salvos.</p>
          <p className="aviso__ajuda">
            {sucesso > 0
              ? "O período mais recente já foi reclassificado com os valores novos. Os anteriores " +
                "mantêm a classificação de antes até o reprocessamento completo, pelo terminal:"
              : "Ainda não há período importado para reclassificar. Os próximos já entram com os " +
                "valores novos."}
          </p>
          {sucesso > 0 && <code className="limiares__comando">{COMANDO}</code>}
        </div>
      )}

      {erro && !erro.campos?.length && (
        <div className="aviso" role="alert">
          <p className="aviso__titulo">{erro.message}</p>
          {erro.ajuda && <p className="aviso__ajuda">{erro.ajuda}</p>}
        </div>
      )}

      <section className="painel" aria-labelledby="titulo-limiares">
        <div className="painel__cabecalho">
          <h2 className="painel__titulo" id="titulo-limiares">
            Limiares da segmentação
          </h2>
          <span className="painel__nota">
            {atual.atualizado_por
              ? `Alterados por ${atual.atualizado_por} em ${comoDataHora(atual.atualizado_em)}`
              : "Valores de fábrica — ninguém alterou ainda"}
          </span>
        </div>

        <form className="limiares" onSubmit={pedirConfirmacao} noValidate>
          <p className="limiares__nota">
            Estes três números decidem o segmento de cada parceiro na rede inteira. Mudá-los
            reclassifica o período mais recente assim que você salvar.
          </p>

          <div className="limiares__campos">
            {LIMIARES.map(({ nome, rotulo, ajuda, max }) => (
              <Campo key={nome} id={nome} rotulo={rotulo} obrigatorio erro={erroDoCampo[nome]} ajuda={ajuda}>
                <input
                  id={`campo-${nome}`}
                  type="number"
                  inputMode="numeric"
                  min={1}
                  max={max}
                  value={valores[nome]}
                  onChange={(e) => mudar(nome, e.target.value)}
                />
              </Campo>
            ))}
          </div>

          {confirmando ? (
            <Confirmacao
              texto={
                "Salvar os limiares? A rede é reclassificada agora no período mais recente; os " +
                "anteriores só mudam com o reprocessamento pelo terminal."
              }
              acao="Salvar limiares"
              ocupado={enviando}
              aoConfirmar={salvar}
              aoCancelar={() => setConfirmando(false)}
            />
          ) : (
            <div className="limiares__acoes">
              <button className="botao" type="submit" disabled={!mudou}>
                Salvar limiares
              </button>
              <button
                type="button"
                className="botao botao--secundario"
                disabled={!mudou}
                onClick={() => {
                  setValores(valoresDe(atual));
                  setErro(null);
                }}
              >
                Desfazer mudanças
              </button>
            </div>
          )}
        </form>
      </section>
    </>
  );
}
