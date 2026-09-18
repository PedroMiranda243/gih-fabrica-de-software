import { Link } from "react-router-dom";

/**
 * Estado vazio, com o próximo passo à mão.
 *
 * "Tela vazia sem explicação é defeito" — `docs/09`, seção 6. Os três estados
 * previstos ali (base sem dados, período único, otimização inviável) passam
 * todos por aqui, e nenhum deles deixa a pessoa sem saber o que fazer.
 */
export default function EstadoVazio({ titulo, texto, acao }) {
  return (
    <div className="vazio">
      <p className="vazio__titulo">{titulo}</p>
      {texto && <p className="vazio__texto">{texto}</p>}
      {acao && (
        <Link className="botao vazio__acao" to={acao.para}>
          {acao.rotulo}
        </Link>
      )}
    </div>
  );
}
