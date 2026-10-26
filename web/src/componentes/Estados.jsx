/**
 * Os estados que toda tela tem: carregando, vazio, erro, sucesso e aviso.
 * Tela vazia sem explicação é defeito: todo vazio diz por quê e o que fazer.
 */
import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";

import Icone from "./Icone";

/** Espera anunciada, com esqueleto que reserva o espaço do que vem. */
export function Carregando({ rotulo = "Carregando", linhas = 3, altura }) {
  return (
    <div className="carregando" role="status" aria-live="polite" style={altura ? { minHeight: altura } : undefined}>
      <span className="sr-only">{rotulo}…</span>
      <div className="esqueleto" aria-hidden="true">
        {Array.from({ length: linhas }, (_, i) => (
          <span key={i} style={{ width: `${92 - ((i * 17) % 40)}%` }} />
        ))}
      </div>
    </div>
  );
}

/** Vazio: título, explicação e, quando houver, a ação seguinte. */
export function Vazio({ titulo, children, acao, para, aoClicar, icone = "vazio", compacto = false }) {
  return (
    <div className={`vazio${compacto ? " vazio--compacto" : ""}`}>
      <Icone nome={icone} className="vazio__icone" />
      <div>
        <p className="vazio__titulo">{titulo}</p>
        {children && <div className="vazio__texto">{children}</div>}
        {acao && para && (
          <Link className="botao botao--secundario" to={para}>
            {acao}
          </Link>
        )}
        {acao && aoClicar && (
          <button type="button" className="botao botao--secundario" onClick={aoClicar}>
            {acao}
          </button>
        )}
      </div>
    </div>
  );
}

/** O erro do servidor, com a ajuda dele e o identificador do log, no lugar do conteúdo. */
export function ErroDaTela({ erro, titulo, children }) {
  if (!erro) return null;
  return (
    <div className="erro-tela" role="alert">
      <Icone nome="erro" className="erro-tela__icone" />
      <div>
        <p className="erro-tela__titulo">{titulo ?? erro.message}</p>
        {titulo && <p>{erro.message}</p>}
        {erro.ajuda && <p className="erro-tela__ajuda">{erro.ajuda}</p>}
        {erro.correlacao && (
          <p className="erro-tela__correlacao">
            Identificador para o suporte: <code>{erro.correlacao}</code>
          </p>
        )}
        {children}
      </div>
    </div>
  );
}

/** Aviso de sucesso de uma ação, anunciado. */
export function Sucesso({ children, aoFechar, foco = false }) {
  const ref = useRef(null);
  useEffect(() => {
    if (foco) ref.current?.focus();
  }, [foco]);
  if (!children) return null;
  return (
    <div className="aviso aviso--sucesso" role="status" tabIndex={foco ? -1 : undefined} ref={ref}>
      <Icone nome="certo" className="aviso__icone" />
      <div className="aviso__texto">{children}</div>
      {aoFechar && (
        <button type="button" className="botao-icone" onClick={aoFechar} aria-label="Fechar o aviso">
          <Icone nome="fechar" />
        </button>
      )}
    </div>
  );
}

/** Aviso neutro (indisponível, abstenção, nota): não é erro e não usa vermelho. */
export function Nota({ tipo = "neutra", titulo, children, icone, papel }) {
  const nomeIcone = icone ?? { neutra: "info", atencao: "atencao", erro: "erro", estimativa: "estimativa" }[tipo];
  return (
    <div className={`nota nota--${tipo}`} role={papel}>
      <Icone nome={nomeIcone} className="nota__icone" />
      <div className="nota__texto">
        {titulo && <p className="nota__titulo">{titulo}</p>}
        {children}
      </div>
    </div>
  );
}

/** Erro curto de uma ação, com a ajuda do servidor. */
export function ErroDaAcao({ erro }) {
  if (!erro) return null;
  return (
    <div className="aviso aviso--erro" role="alert">
      <Icone nome="erro" className="aviso__icone" />
      <div className="aviso__texto">
        <p>{erro.message}</p>
        {erro.ajuda && <p className="aviso__ajuda">{erro.ajuda}</p>}
        {erro.correlacao && (
          <p className="aviso__ajuda">
            Identificador para o suporte: <code>{erro.correlacao}</code>
          </p>
        )}
      </div>
    </div>
  );
}
