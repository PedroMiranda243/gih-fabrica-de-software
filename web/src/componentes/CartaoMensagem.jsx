/**
 * O cartão de uma mensagem — o mesmo na geração e na fila de aprovação: o ponto
 * do segmento e o nome do parceiro (título que aceita foco), etiquetas neutras,
 * quem redigiu, o texto num quadro e os dados de onde os números saíram.
 */
import { forwardRef } from "react";

import { ROTULO_SEGMENTO } from "../formato";
import Icone from "./Icone";

const CartaoMensagem = forwardRef(function CartaoMensagem({ mensagem: m, children, editor, rodape, idTitulo }, refTitulo) {
  const id = idTitulo ?? `mensagem-${m.id}`;
  return (
    <article className={`cartao-mensagem cartao-mensagem--${m.estado.toLowerCase()}`} aria-labelledby={id}>
      <header className="cartao-mensagem__cabeca">
        <h3 className="cartao-mensagem__parceiro" id={id} tabIndex={-1} ref={refTitulo}>
          {m.parceiro}
        </h3>
        <ul className="cartao-mensagem__etiquetas" aria-label="Sobre o parceiro">
          {m.segmento && (
            <li className={`segmento segmento--${m.segmento.toLowerCase().replace(/_/g, "-")} segmento--etiqueta`}>
              <span className="segmento__ponto" aria-hidden="true" />
              {ROTULO_SEGMENTO[m.segmento]}
            </li>
          )}
          {m.categoria && <li>{m.categoria}</li>}
          {m.acao && <li>{m.acao}</li>}
        </ul>
      </header>
      <p className="cartao-mensagem__redator">
        <Icone nome={m.redator === "MODELO" ? "assistente" : "arquivo"} />
        {m.redator === "MODELO" ? `Assistente${m.modelo ? ` (${m.modelo})` : ""}` : "Modelo fixo"}
        {m.redator === "MODELO_FIXO" && m.motivo_redator && <span className="discreto"> — {m.motivo_redator}</span>}
      </p>
      {editor ?? <div className="cartao-mensagem__texto">{m.texto}</div>}
      {m.editada && !editor && (
        <details className="detalhes-curto cartao-mensagem__original">
          <summary>
                <Icone nome="seta-direita" className="resumo__icone" />
                Editada — ver o texto redigido
              </summary>
          <div className="cartao-mensagem__texto cartao-mensagem__texto--original">{m.texto_gerado}</div>
        </details>
      )}
      {m.estado === "PENDENTE" && m.numeros_fora_dos_fatos?.length > 0 && !editor && (
        <p className="cartao-mensagem__alerta" role="note">
          <Icone nome="atencao" />
          <span>
            Números que não vieram dos dados: <strong>{m.numeros_fora_dos_fatos.join(", ")}</strong>. Quem editou pode escrever um número novo, como um desconto; confira antes de aprovar.
          </span>
        </p>
      )}
      {m.fatos?.length > 0 && (
        <details className="detalhes-curto">
          <summary>
                <Icone nome="seta-direita" className="resumo__icone" />
                Os dados desta mensagem
              </summary>
          <dl className="fatos">
            {m.fatos.map((f, i) => (
              <div key={i}>
                <dt>{f.fato}</dt>
                <dd>{f.valor}</dd>
              </div>
            ))}
          </dl>
        </details>
      )}
      {rodape}
      {children && <div className="cartao-mensagem__acoes">{children}</div>}
    </article>
  );
});

export default CartaoMensagem;
