import { cloneElement } from "react";

/**
 * Um campo com rótulo, ajuda e erro.
 *
 * O erro **substitui** a ajuda, embaixo do campo, e não vai só para o topo:
 * mensagem longe do campo obriga a pessoa a ligar as duas coisas de cabeça.
 * `aria-describedby` aponta para o texto que estiver visível, e é o que o
 * leitor de tela lê ao entrar no campo.

 *
 * Mora em `componentes/` porque três telas o usam — o cadastro de parceiro, os
 * limiares e os usuários — e as três precisam marcar o campo do mesmo jeito.
 */
export default function Campo({ id, rotulo, obrigatorio = false, erro, ajuda, children }) {
  const idTexto = erro ? `erro-${id}` : `ajuda-${id}`;
  const controle = cloneElement(children, {
    "aria-invalid": erro ? "true" : undefined,
    "aria-required": obrigatorio ? "true" : undefined,
    "aria-describedby": idTexto,
  });

  return (
    <div className="campo">
      <label htmlFor={`campo-${id}`}>
        {rotulo}
        {obrigatorio && (
          <span className="campo__obrigatorio" aria-hidden="true">
            {" "}
            *
          </span>
        )}
      </label>
      {controle}
      {erro ? (
        <p id={idTexto} className="campo__erro">
          {erro.mensagem}
          {erro.ajuda && <span className="campo__erro-ajuda"> {erro.ajuda}</span>}
        </p>
      ) : (
        ajuda && (
          <p id={idTexto} className="campo__ajuda">
            {ajuda}
          </p>
        )
      )}
    </div>
  );
}
