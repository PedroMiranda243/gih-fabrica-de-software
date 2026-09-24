/** Confirmação na própria página, e não num `window.confirm`: dá para ler,
    dá para testar, e não trava a tela inteira do navegador. */
export default function Confirmacao({ texto, acao, ocupado, aoConfirmar, aoCancelar }) {
  return (
    <div className="confirmacao" role="group" aria-label="Confirmação">
      <p className="confirmacao__texto">{texto}</p>
      <div className="confirmacao__acoes">
        <button type="button" className="botao" disabled={ocupado} onClick={aoConfirmar}>
          {acao}
        </button>
        <button type="button" className="botao botao--secundario" onClick={aoCancelar}>
          Cancelar
        </button>
      </div>
    </div>
  );
}
