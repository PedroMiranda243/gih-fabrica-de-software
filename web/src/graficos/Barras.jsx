/**
 * Barras horizontais que começam no zero, cada uma com o nome e o valor em texto:
 * a barra dá a proporção de relance, o texto garante que nada dependa só dela.
 */
export default function Barras({ itens, rotulo, formato = (v) => v, destaque, maximo, legenda }) {
  const topo = maximo ?? Math.max(...itens.map((i) => Number(i.valor) || 0), 0);
  return (
    <figure className="barras">
      <ul className="barras__lista" aria-label={rotulo}>
        {itens.map((item) => {
          const v = Number(item.valor);
          const ausente = item.valor === null || item.valor === undefined || Number.isNaN(v);
          const largura = ausente || topo <= 0 ? 0 : Math.max((v / topo) * 100, v > 0 ? 0.8 : 0);
          return (
            <li key={item.chave ?? item.nome} className={`barras__item${destaque === (item.chave ?? item.nome) || item.destaque ? " barras__item--destaque" : ""}`}>
              <span className="barras__nome">{item.nome}</span>
              <span className="barras__trilho" aria-hidden="true">
                <span className="barras__barra" style={{ width: `${largura}%`, ...(item.cor ? { background: item.cor } : null) }} />
              </span>
              <span className="barras__valor">{ausente ? "—" : formato(item.valor)}</span>
            </li>
          );
        })}
      </ul>
      {legenda && <figcaption className="barras__legenda">{legenda}</figcaption>}
    </figure>
  );
}
