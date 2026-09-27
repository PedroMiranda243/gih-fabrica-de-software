/**
 * Uma mensagem de relacionamento, no cartão do protótipo aprovado da aprovação
 * (H08): ponto do segmento, nome do parceiro em peso alto, etiquetas neutras e o
 * texto num quadro.
 *
 * Mora em `componentes/` porque duas telas o mostram: a geração (H60), com as
 * mensagens chegando, e a fila de aprovação (H61), com a decisão. O que muda de
 * uma para a outra entra pelas bordas — `antes` (a caixa de seleção), `corpo` (o
 * texto, ou o campo de edição) e `children` (os avisos e os botões).
 *
 * O nome do parceiro é um título que aceita foco (`tabIndex=-1`): depois de cada
 * decisão, a fila leva o foco para a próxima mensagem, e o leitor de tela anuncia
 * para quem ela vai.
 */
import { forwardRef } from "react";

import { comoDataHora, ROTULO_SEGMENTO } from "../formato";
import "../estilos/mensagens.css";

const CartaoMensagem = forwardRef(function CartaoMensagem(
  { mensagem: m, antes, corpo, mostrarQuando = false, children },
  refTitulo,
) {
  const doModelo = m.redator === "MODELO";
  return (
    <li className="mensagem">
      <div className="mensagem__cabecalho">
        {antes}
        {m.segmento && (
          <span className={`segmento__ponto segmento__ponto--${m.segmento.toLowerCase()}`} aria-hidden="true" />
        )}
        <h3 className="mensagem__parceiro" tabIndex={-1} ref={refTitulo}>
          {m.parceiro}
        </h3>
        {m.segmento && <span className="mensagem__etiqueta">{ROTULO_SEGMENTO[m.segmento]}</span>}
        {m.categoria && <span className="mensagem__etiqueta">{m.categoria}</span>}
        {m.acao && <span className="mensagem__etiqueta">{m.acao}</span>}
        <span className="mensagem__redator">
          {doModelo ? "Assistente" : "Modelo fixo"}
          {mostrarQuando && ` · gerada ${comoDataHora(m.gerada_em)}`}
        </span>
      </div>

      {corpo ?? <p className="mensagem__texto">{m.texto}</p>}

      {m.editada && (
        <details className="mensagem__fatos">
          <summary>Editada — ver o texto redigido</summary>
          <p className="mensagem__original">{m.texto_gerado}</p>
        </details>
      )}
      {!doModelo && m.motivo_redator && (
        <p className="mensagem__motivo">Redigida pelo modelo fixo: {m.motivo_redator}</p>
      )}
      {m.fatos.length > 0 && (
        <details className="mensagem__fatos">
          <summary>Os dados desta mensagem</summary>
          <dl>
            {m.fatos.map((f) => (
              <div key={f.fato}>
                <dt>{f.fato}</dt>
                <dd>{f.valor}</dd>
              </div>
            ))}
          </dl>
        </details>
      )}
      {children}
    </li>
  );
});

export default CartaoMensagem;
