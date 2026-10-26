/**
 * O cliente da API: tudo passa por aqui.
 *
 * - A sessão é cookie HttpOnly: o navegador a envia, o JavaScript nunca a vê
 *   (`credentials: "same-origin"`, sem cabeçalho de autorização).
 * - A mensagem de erro é a do servidor, com a ajuda e os campos que ele mandou.
 * - 401 é a sessão que terminou, e não um erro de tela: quem se inscreve em
 *   `aoEncerrarSessao` leva a pessoa à entrada, guardando o endereço.
 */

export class ErroDaApi extends Error {
  constructor(status, corpo) {
    super(mensagemDe(status, corpo));
    this.status = status;
    this.corpo = corpo;
    const detalhe = corpo?.detail;
    this.ajuda = (detalhe && typeof detalhe === "object" ? detalhe.ajuda : null) ?? null;
    this.detalhe = detalhe && typeof detalhe === "object" ? detalhe : null;
    this.campos = Array.isArray(corpo?.campos) ? corpo.campos : null;
    this.correlacao = corpo?.correlacao ?? null;
  }
}

function mensagemDe(status, corpo) {
  const detalhe = corpo?.detail;
  if (typeof detalhe === "string") return detalhe;
  if (detalhe?.erro) return detalhe.erro;
  if (corpo?.erro) return corpo.erro;
  if (status === 0) return "Não foi possível falar com o servidor. Confira a conexão e tente de novo.";
  return `O servidor recusou o pedido (código ${status}).`;
}

const ouvintes = new Set();
export function aoEncerrarSessao(ouvinte) {
  ouvintes.add(ouvinte);
  return () => ouvintes.delete(ouvinte);
}

async function requisitar(metodo, caminho, { corpo, formulario, sinal } = {}) {
  const opcoes = { method: metodo, credentials: "same-origin", headers: { Accept: "application/json" }, signal: sinal };
  if (formulario) {
    opcoes.body = formulario;
  } else if (corpo !== undefined) {
    opcoes.headers["Content-Type"] = "application/json";
    opcoes.body = JSON.stringify(corpo);
  }

  let resposta;
  try {
    resposta = await fetch(caminho, opcoes);
  } catch (erro) {
    if (erro?.name === "AbortError") throw erro;
    throw new ErroDaApi(0, null);
  }

  if (resposta.status === 204) return null;

  let conteudo = null;
  try {
    conteudo = await resposta.json();
  } catch {
    conteudo = null;
  }

  if (!resposta.ok) {
    /* O 401 da própria tentativa de entrar é recusa de senha, e não fim de sessão. */
    if (resposta.status === 401 && !(metodo === "POST" && caminho === "/api/sessao")) {
      ouvintes.forEach((avisar) => avisar());
    }
    throw new ErroDaApi(resposta.status, conteudo);
  }
  return conteudo;
}

/** O caminho com os parâmetros que têm valor: `?busca=` filtraria por texto vazio. */
export function comConsulta(caminho, parametros) {
  if (!parametros) return caminho;
  const busca = new URLSearchParams();
  for (const [chave, valor] of Object.entries(parametros)) {
    if (valor !== undefined && valor !== null && valor !== "") busca.set(chave, String(valor));
  }
  const texto = busca.toString();
  return texto ? `${caminho}?${texto}` : caminho;
}

export const api = {
  get: (caminho, parametros, sinal) => requisitar("GET", comConsulta(caminho, parametros), { sinal }),
  post: (caminho, corpo) => requisitar("POST", caminho, { corpo }),
  patch: (caminho, corpo) => requisitar("PATCH", caminho, { corpo }),
  put: (caminho, corpo) => requisitar("PUT", caminho, { corpo }),
  delete: (caminho) => requisitar("DELETE", caminho),
  enviarArquivo: (caminho, formulario) => requisitar("POST", caminho, { formulario }),
};
