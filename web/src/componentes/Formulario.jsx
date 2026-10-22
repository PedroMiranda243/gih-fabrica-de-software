/**
 * Peças de formulário. Todo campo tem rótulo visível, ajuda embaixo, marca de
 * obrigatório e o erro do servidor embaixo dele, ligado por aria-describedby.
 * A validação é do servidor: aqui só se mostra o que ele disse.
 */
import { forwardRef, useCallback, useEffect, useId, useRef, useState } from "react";

import { ErroDaApi } from "../api/cliente";
import Icone from "./Icone";

/**
 * Distribui o erro do servidor: os campos que ele nomeou vão para baixo de cada
 * campo; o resto, para o topo. Foco no primeiro campo errado.
 */
export function useErrosDoFormulario() {
  const [erros, setErros] = useState({ campos: {}, topo: null, ajudaTopo: null, erro: null });
  const referencias = useRef({});

  const registrar = useCallback((nome) => (el) => {
    if (el) referencias.current[nome] = el;
  }, []);

  const receber = useCallback((erro, { mapa = {}, ordem = [] } = {}) => {
    if (!(erro instanceof ErroDaApi)) {
      setErros({ campos: {}, topo: "Não foi possível concluir. Tente de novo.", ajudaTopo: null, erro: null });
      return;
    }
    const campos = {};
    const soltos = [];
    for (const c of erro.campos ?? []) {
      const nome = mapa[c.campo] ?? c.campo;
      if (nome in referencias.current) campos[nome] = { mensagem: c.mensagem, ajuda: c.ajuda ?? null };
      else soltos.push(c.mensagem);
    }
    const temCampos = Object.keys(campos).length > 0;
    const topo = soltos.length ? soltos.join(" ") : erro.message;
    setErros({ campos, topo, ajudaTopo: erro.ajuda, erro, resumo: temCampos });
    const primeiro = [...ordem, ...Object.keys(referencias.current)].find((n) => campos[n]);
    if (primeiro) requestAnimationFrame(() => referencias.current[primeiro]?.focus());
  }, []);

  const limpar = useCallback(() => setErros({ campos: {}, topo: null, ajudaTopo: null, erro: null }), []);
  const limparCampo = useCallback(
    (nome) =>
      setErros((e) => {
        if (!e.campos[nome]) return e;
        const campos = { ...e.campos };
        delete campos[nome];
        return { ...e, campos };
      }),
    [],
  );

  return { erros, receber, limpar, limparCampo, registrar };
}

/** O resumo no topo do formulário: o que não é de campo, e quantos campos pedem correção. */
export function ResumoDeErros({ erros, rotulos = {} }) {
  const ref = useRef(null);
  const nomes = Object.keys(erros.campos ?? {});
  const tem = erros.topo || nomes.length;
  useEffect(() => {
    if (tem && !nomes.length) ref.current?.focus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [erros]);
  if (!tem) return null;
  return (
    <div className="aviso aviso--erro" role="alert" tabIndex={-1} ref={ref}>
      <Icone nome="erro" className="aviso__icone" />
      <div className="aviso__texto">
        <p>{erros.topo}</p>
        {erros.ajudaTopo && <p className="aviso__ajuda">{erros.ajudaTopo}</p>}
        {nomes.length > 0 && (
          <ul className="aviso__lista">
            {nomes.map((n) => (
              <li key={n}>
                <a href={`#campo-${n}`}>
                  {rotulos[n] ?? n}: {erros.campos[n].mensagem}
                </a>
              </li>
            ))}
          </ul>
        )}
        {erros.erro?.correlacao && (
          <p className="aviso__ajuda">
            Identificador para o suporte: <code>{erros.erro.correlacao}</code>
          </p>
        )}
      </div>
    </div>
  );
}

/** Um campo: rótulo, controle, ajuda e erro, ligados. */
export function Campo({ nome, rotulo, ajuda, erro, obrigatorio = false, children, className = "", largura }) {
  const id = `campo-${nome}`;
  const idAjuda = ajuda ? `${id}-ajuda` : null;
  const idErro = erro ? `${id}-erro` : null;
  const descritores = [idErro, idAjuda].filter(Boolean).join(" ") || undefined;
  return (
    <div className={`campo${erro ? " campo--erro" : ""} ${className}`} style={largura ? { maxWidth: largura } : undefined}>
      <label className="campo__rotulo" htmlFor={id}>
        {rotulo}
        {obrigatorio && (
          <span className="campo__obrigatorio">
            <span aria-hidden="true"> *</span>
            <span className="sr-only"> (obrigatório)</span>
          </span>
        )}
      </label>
      {children({ id, "aria-describedby": descritores, "aria-invalid": erro ? true : undefined, "aria-required": obrigatorio || undefined })}
      {erro && (
        <p className="campo__erro" id={idErro}>
          <Icone nome="erro" />
          <span>
            {erro.mensagem}
            {erro.ajuda && <span className="campo__erro-ajuda"> {erro.ajuda}</span>}
          </span>
        </p>
      )}
      {ajuda && (
        <p className="campo__ajuda" id={idAjuda}>
          {ajuda}
        </p>
      )}
    </div>
  );
}

/** Campo de senha com Mostrar / Ocultar; o botão não envia o formulário. */
export const Senha = forwardRef(function Senha({ valor, aoMudar, autoComplete = "current-password", ...props }, ref) {
  const [visivel, setVisivel] = useState(false);
  const idBotao = useId();
  return (
    <div className="senha">
      <input
        {...props}
        ref={ref}
        className="entrada"
        type={visivel ? "text" : "password"}
        value={valor}
        onChange={(e) => aoMudar(e.target.value)}
        autoComplete={autoComplete}
        spellCheck={false}
      />
      <button type="button" id={idBotao} className="senha__botao" onClick={() => setVisivel((v) => !v)} aria-pressed={visivel} aria-controls={props.id}>
        <Icone nome={visivel ? "ocultar" : "mostrar"} />
        <span>{visivel ? "Ocultar" : "Mostrar"}</span>
      </button>
    </div>
  );
});
