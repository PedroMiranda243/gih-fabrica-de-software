/**
 * Cliente da API.
 *
 * Tudo passa por aqui, por três razões que valem repetir:
 *
 * 1. **A sessão é cookie HttpOnly.** O JavaScript não lê nem escreve o token —
 *    é o navegador que o envia. `credentials: "same-origin"` é o que garante
 *    isso, e a interface roda na mesma origem da API justamente para o cookie
 *    `SameSite=Lax` funcionar sem afrouxar nada no servidor.
 *
 * 2. **A mensagem de erro vem do servidor.** A API já responde em português,
 *    com `erro` e `ajuda` explicando o que fazer — a recusa de importar sem
 *    período diz por que o período existe, e a de excluir parceiro com
 *    histórico diz quantos registros impedem. Reescrever isso na tela jogaria
 *    fora a parte útil.
 *
 * 3. **401 é sessão encerrada, não erro de tela.** Tratar num lugar só evita
 *    que cada página invente o seu próprio jeito de reagir.
 */

/** Erro com o que o servidor disse, preservado. */
export class ErroDaApi extends Error {
  constructor(status, corpo) {
    super(mensagemDe(corpo) || `Falha na requisição (${status}).`);
    this.status = status;
    this.corpo = corpo;
    this.ajuda = corpo?.detail?.ajuda ?? null;
    /* A validação vem como lista de campos, cada um com a explicação do
       porquê — é o que a tela usa para marcar o campo certo. */
    this.campos = corpo?.campos ?? null;
  }
}

function mensagemDe(corpo) {
  const detalhe = corpo?.detail;
  if (typeof detalhe === "string") return detalhe;
  if (detalhe?.erro) return detalhe.erro;
  /* O erro de validação traz o resumo no topo do corpo, e os campos à parte.
     Usar a mensagem do primeiro campo como título fazia ela aparecer duas
     vezes na tela — no alerta e embaixo do campo — e escondia que podia haver
     mais de um campo errado. */
  if (corpo?.erro) return corpo.erro;
  if (corpo?.campos?.length) return corpo.campos[0].mensagem ?? "Confira os campos.";
  return null;
}

/* Quem quiser reagir ao fim da sessão se inscreve aqui. Um `window.location`
   solto no meio do cliente funcionaria e tiraria da aplicação a chance de
   avisar o usuário antes. */
const ouvintesDeSessaoEncerrada = new Set();

export function aoEncerrarSessao(ouvinte) {
  ouvintesDeSessaoEncerrada.add(ouvinte);
  return () => ouvintesDeSessaoEncerrada.delete(ouvinte);
}

async function requisitar(metodo, caminho, { corpo, formulario } = {}) {
  const opcoes = {
    method: metodo,
    credentials: "same-origin",
    headers: {},
  };

  if (formulario) {
    /* `FormData` define o próprio `Content-Type`, com o limite do multipart.
       Defini-lo à mão quebra o envio de arquivo — o servidor não acha a
       fronteira entre as partes. */
    opcoes.body = formulario;
  } else if (corpo !== undefined) {
    opcoes.headers["Content-Type"] = "application/json";
    opcoes.body = JSON.stringify(corpo);
  }

  const resposta = await fetch(caminho, opcoes);

  if (resposta.status === 204) return null;

  let conteudo = null;
  try {
    conteudo = await resposta.json();
  } catch {
    /* Resposta sem JSON: o `ErroDaApi` cai na mensagem genérica. */
  }

  if (!resposta.ok) {
    if (resposta.status === 401) {
      ouvintesDeSessaoEncerrada.forEach((avisar) => avisar());
    }
    throw new ErroDaApi(resposta.status, conteudo);
  }

  return conteudo;
}

function comConsulta(caminho, parametros) {
  if (!parametros) return caminho;
  /* Chave com valor nulo ou vazio não vira parâmetro: `?busca=` faria o
     servidor filtrar por texto vazio em vez de não filtrar. */
  const busca = new URLSearchParams();
  Object.entries(parametros).forEach(([chave, valor]) => {
    if (valor !== undefined && valor !== null && valor !== "") {
      busca.set(chave, String(valor));
    }
  });
  const consulta = busca.toString();
  return consulta ? `${caminho}?${consulta}` : caminho;
}

export const api = {
  get: (caminho, parametros) => requisitar("GET", comConsulta(caminho, parametros)),
  post: (caminho, corpo) => requisitar("POST", caminho, { corpo }),
  patch: (caminho, corpo) => requisitar("PATCH", caminho, { corpo }),
  put: (caminho, corpo) => requisitar("PUT", caminho, { corpo }),
  delete: (caminho) => requisitar("DELETE", caminho),
  enviarArquivo: (caminho, formulario) => requisitar("POST", caminho, { formulario }),
};
