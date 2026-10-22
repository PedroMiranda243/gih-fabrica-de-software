/**
 * Configuração — os três números que decidem a segmentação da rede inteira. O que
 * a gravação faz é dito antes e depois. A tela não valida: o limite vem da API.
 */
import { useState } from "react";

import { api } from "../api/cliente";
import { useCarregar } from "../api/ganchos";
import AlteracoesNaoSalvas from "../componentes/AlteracoesNaoSalvas";
import Confirmacao from "../componentes/Confirmacao";
import { Carregando, ErroDaTela, Sucesso } from "../componentes/Estados";
import { Campo, ResumoDeErros, useErrosDoFormulario } from "../componentes/Formulario";
import Lacre from "../componentes/Lacre";
import { useTitulo } from "../componentes/Titulo";

const CAMPOS = [
  ["top_n", "Tamanho do Top", "Quantos parceiros, a partir do maior faturamento do período, formam o Top."],
  ["periodos_tendencia", "Períodos de tendência", "Quantos períodos seguidos de queda classificam como em risco — e de alta, como em ascensão."],
  ["periodos_novato", "Períodos de recém-chegado", "Com histórico menor que isto, o parceiro é recém-chegado."],
];

const comoTexto = (c) => Object.fromEntries(CAMPOS.map(([k]) => [k, String(c[k])]));

export default function Configuracao() {
  useTitulo("Configuração");
  const conf = useCarregar(() => api.get("/api/configuracao/segmentacao"), "conf");
  if (conf.carregando) return <Carregando rotulo="Carregando os limiares" linhas={5} />;
  if (conf.erro) return <ErroDaTela erro={conf.erro} />;
  return <Limiares inicial={conf.dados} />;
}

function Limiares({ inicial }) {
  const [atual, setAtual] = useState(inicial);
  const [v, setV] = useState(() => comoTexto(inicial));
  const [confirmando, setConfirmando] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [sucesso, setSucesso] = useState(null);
  const { erros, receber, limpar, limparCampo, registrar } = useErrosDoFormulario();
  const emVigor = comoTexto(atual);
  const alterado = CAMPOS.some(([k]) => v[k] !== emVigor[k]);

  async function salvar() {
    setEnviando(true);
    limpar();
    try {
      const num = (s) => (s.trim() === "" || Number.isNaN(Number(s)) ? s : Number(s));
      const r = await api.put("/api/configuracao/segmentacao", Object.fromEntries(CAMPOS.map(([k]) => [k, num(v[k])])));
      setAtual(r);
      setV(comoTexto(r));
      setSucesso(
        r.periodos_reprocessados > 0
          ? "Limiares salvos. O período mais recente já foi reclassificado com os valores novos. Os anteriores mantêm a classificação que tinham."
          : "Limiares salvos. Ainda não há período importado para reclassificar. Os próximos já entram com os valores novos.",
      );
      setConfirmando(false);
    } catch (e) {
      setConfirmando(false);
      receber(e, { ordem: CAMPOS.map(([k]) => k) });
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="pagina">
      <section className="bloco coluna-estreita" aria-labelledby="t-limiares">
        <div className="bloco__cabeca">
          <h2 id="t-limiares" className="bloco__titulo">
            Limiares da segmentação
          </h2>
          <p className="bloco__sub">Valem para a rede inteira, e para todos os perfis.</p>
        </div>
        {atual.atualizado_por ? <Lacre titulo="Limiares em vigor" quem={atual.atualizado_por} quando={atual.atualizado_em} novo={Boolean(sucesso)} /> : <p className="valor-leitura discreto">Valores de fábrica — ninguém alterou ainda.</p>}
        <form
          className="formulario"
          noValidate
          onSubmit={(e) => {
            e.preventDefault();
            setSucesso(null);
            setConfirmando(true);
          }}
        >
          {sucesso && <Sucesso foco>{sucesso}</Sucesso>}
          <ResumoDeErros erros={erros} rotulos={Object.fromEntries(CAMPOS.map(([k, r]) => [k, r]))} />
          {CAMPOS.map(([k, rotulo, ajuda]) => (
            <Campo key={k} nome={k} rotulo={rotulo} obrigatorio erro={erros.campos[k]} ajuda={`${ajuda} Em vigor: ${atual[k]}.`}>
              {(a) => <input {...a} ref={registrar(k)} className="entrada entrada--numero" inputMode="numeric" value={v[k]} onChange={(e) => (setV((x) => ({ ...x, [k]: e.target.value })), limparCampo(k), setSucesso(null))} />}
            </Campo>
          ))}
          {confirmando ? (
            <Confirmacao
              texto="Salvar os limiares?"
              detalhe="A rede é reclassificada agora no período mais recente; os anteriores mantêm a classificação antiga. O painel, a lista de parceiros e a próxima campanha passam a usar os valores novos."
              acao="Salvar limiares"
              ocupado={enviando}
              aoConfirmar={salvar}
              aoCancelar={() => setConfirmando(false)}
            />
          ) : (
            <div className="formulario__acoes">
              <button type="submit" className="botao botao--primario" disabled={!alterado}>
                Salvar limiares
              </button>
              <button type="button" className="botao botao--fantasma" disabled={!alterado} onClick={() => (setV(emVigor), limpar())}>
                Desfazer mudanças
              </button>
            </div>
          )}
        </form>
        <AlteracoesNaoSalvas quando={alterado && !enviando} />
      </section>
    </div>
  );
}
