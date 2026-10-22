/** Um indicador: o rótulo, o número com presença, e o que ele diz contra o período anterior. */
export default function Kpi({ rotulo, children, variacao, nota, principal = false, tom, selo, className = "" }) {
  return (
    <div className={`kpi${principal ? " kpi--principal" : ""}${tom ? ` kpi--${tom}` : ""} ${className}`}>
      <p className="kpi__rotulo">
        <span>{rotulo}</span>
        {selo && (
          <span className="kpi__selo" aria-hidden="true">
            {selo}
          </span>
        )}
      </p>
      <p className="kpi__valor">{children}</p>
      {variacao !== undefined && <p className="kpi__variacao">{variacao}</p>}
      {nota && <div className="kpi__nota">{nota}</div>}
    </div>
  );
}
