/** Um filtro de lista: rótulo visível e a opção "todos" que tira o parâmetro do endereço. */
export default function Seletor({ id, rotulo, valor, aoMudar, todos, opcoes, ajuda }) {
  return (
    <div className="campo">
      <label className="campo__rotulo" htmlFor={id}>
        {rotulo}
      </label>
      <select id={id} className="entrada" value={valor ?? ""} onChange={(e) => aoMudar(e.target.value)} aria-describedby={ajuda ? `${id}-ajuda` : undefined}>
        {todos !== null && <option value="">{todos}</option>}
        {opcoes.map(([v, r]) => (
          <option key={v} value={v}>
            {r}
          </option>
        ))}
      </select>
      {ajuda && (
        <p className="campo__ajuda" id={`${id}-ajuda`}>
          {ajuda}
        </p>
      )}
    </div>
  );
}
