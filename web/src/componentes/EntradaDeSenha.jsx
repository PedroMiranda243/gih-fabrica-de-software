import { useState } from "react";

/**
 * Um campo de senha que dá para conferir — H96.
 *
 * Senha digitada às cegas é a origem do "minha senha não entra": um erro de
 * digitação que a pessoa não tem como ver. O botão mostra o que foi digitado, e
 * volta a esconder. Quem decide é quem está digitando: a senha começa oculta.
 *
 * Os atributos que o `Campo` põe no controle — o `aria-describedby` do erro, o
 * `aria-invalid` — chegam aqui e vão para o `input`, que é o controle de fato.
 *
 * `de` completa o nome do botão para o leitor de tela: numa tela com três campos
 * de senha, três botões "Mostrar" não dizem qual é qual.
 */
export default function EntradaDeSenha({ de = "a senha", ...campo }) {
  const [visivel, setVisivel] = useState(false);

  return (
    <span className="senha">
      <input {...campo} type={visivel ? "text" : "password"} />
      <button
        type="button"
        className="botao botao--secundario senha__botao"
        onClick={() => setVisivel((v) => !v)}
      >
        {/* O espaço solto separa as duas partes no nome que o leitor de tela lê. */}
        {visivel ? "Ocultar" : "Mostrar"}{" "}
        <span className="so-leitor">{de}</span>
      </button>
    </span>
  );
}
