/**
 * O lacre: o que foi medido ou decidido sai lacrado, com número, quem e quando —
 * o plano calculado, a mensagem aprovada, o limiar salvo, a versão do modelo em
 * uso. Quando a decisão acaba de ser gravada (`novo`), ele se aplica em dois
 * quadros secos. Estimativa nunca leva lacre.
 *
 * `quem` é o nome de quem fez, e sai depois de "por". O que foi feito pelo terminal
 * não tem usuário: `peloTerminal` assina "pelo terminal" — passar a frase em `quem`
 * dava "por pelo terminal" (#279).
 */
import { comoDataHora } from "../formato";

export default function Lacre({ numero, titulo, quem, peloTerminal = false, quando, novo = false, children, compacto = false }) {
  return (
    <div className={`lacre${novo ? " lacre--novo" : ""}${compacto ? " lacre--compacto" : ""}`}>
      {numero !== undefined && numero !== null && (
        <span className="lacre__numero">
          <span className="lacre__no" aria-hidden="true">
            Nº
          </span>
          <span className="sr-only">número </span>
          {numero}
        </span>
      )}
      <span className="lacre__texto">
        {titulo && <strong className="lacre__titulo">{titulo}</strong>}
        {(quando || quem || peloTerminal) && (
          <span className="lacre__assinatura">
            {quando && <>em {comoDataHora(quando)}</>}
            {quem ? <> por {quem}</> : peloTerminal && <> pelo terminal</>}
          </span>
        )}
        {children}
      </span>
    </div>
  );
}
