/**
 * Confirmação antes do irreversível, na própria página (nunca window.confirm):
 * o texto do que vai acontecer, o botão que confirma, o que cancela, e o foco nela.
 */
import { useEffect, useRef } from "react";

export default function Confirmacao({ texto, detalhe, acao, cancelar = "Cancelar", aoConfirmar, aoCancelar, perigo = false, ocupado = false, children }) {
  const ref = useRef(null);
  useEffect(() => {
    ref.current?.focus();
    ref.current?.scrollIntoView?.({ block: "nearest" });
  }, []);

  function teclas(evento) {
    if (evento.key === "Escape" && !ocupado) aoCancelar();
  }

  return (
    <div className={`confirmacao${perigo ? " confirmacao--perigo" : ""}`} role="alertdialog" aria-labelledby="confirmacao-texto" tabIndex={-1} ref={ref} onKeyDown={teclas}>
      <p className="confirmacao__texto" id="confirmacao-texto">
        {texto}
      </p>
      {detalhe && <p className="confirmacao__detalhe">{detalhe}</p>}
      {children}
      <div className="confirmacao__acoes">
        <button type="button" className={`botao ${perigo ? "botao--perigo" : "botao--primario"}`} onClick={aoConfirmar} disabled={ocupado}>
          {ocupado ? "Aguarde…" : acao}
        </button>
        <button type="button" className="botao botao--secundario" onClick={aoCancelar} disabled={ocupado}>
          {cancelar}
        </button>
      </div>
    </div>
  );
}
