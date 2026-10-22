import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { ProvedorDeSessao } from "../api/sessao";
import App from "../App";
import sessoes from "./amostras/sessao_de_cada_perfil.json";
import Endereco from "./Endereco";
import { simularApi } from "./preparar";

/*
 * As respostas de verdade da API do laboratório (dados sintéticos), uma por
 * consulta — as mesmas do kit que gerou a interface. O teste desenha com o dado
 * real, e a cópia impede que um teste mude o dado de outro.
 */
const ARQUIVOS = import.meta.glob("./amostras/*.json", { eager: true, import: "default" });

export function amostra(nome) {
  const dado = ARQUIVOS[`./amostras/${nome}.json`];
  if (dado === undefined) throw new Error(`amostra que não existe: ${nome}`);
  return structuredClone(dado);
}

/** A sessão de cada perfil, com as `telas` que o servidor manda. */
export function sessaoDe(perfil) {
  return structuredClone(sessoes[perfil]);
}

/** Onde a aplicação está — para o teste conferir um redirecionamento. */
export { endereco } from "./ondeEsta";

/**
 * Abre a aplicação inteira num endereço — guarda, casca e rotas de verdade —, com
 * a sessão de um perfil e a API simulada no nível do `fetch`.
 *
 * `perfil: null` abre sem sessão. Devolve, além do que o `render` devolve, as
 * chamadas feitas à API, como "GET /api/parceiros?pagina=1".
 */
export function abrir(rota, { perfil = "GESTOR", rotas = {}, usuario } = {}) {
  const sessao = usuario ?? (perfil ? sessaoDe(perfil) : null);
  const fetch = simularApi({
    "GET /api/sessao/atual": sessao ? { corpo: sessao } : { status: 401, corpo: { detail: "Sessão ausente ou expirada." } },
    ...rotas,
  });
  const tela = render(
    <MemoryRouter initialEntries={[rota]}>
      <ProvedorDeSessao>
        <App />
        <Endereco />
      </ProvedorDeSessao>
    </MemoryRouter>,
  );
  const chamadas = () => fetch.mock.calls.map(([url, opcoes = {}]) => `${opcoes.method ?? "GET"} ${url}`);
  const corpoDe = (metodoECaminho) => {
    const achada = fetch.mock.calls.find(([url, opcoes = {}]) => `${opcoes.method ?? "GET"} ${String(url).split("?")[0]}` === metodoECaminho);
    return achada?.[1]?.body ? JSON.parse(achada[1].body) : undefined;
  };
  return { ...tela, fetch, chamadas, corpoDe };
}

/**
 * Monta um componente solto, dentro do roteador e da sessão de um perfil — para
 * testar uma peça sem a tela inteira em volta.
 */
export function montar(elemento, { perfil = "GESTOR", rotas = {}, rota = "/" } = {}) {
  const sessao = perfil ? sessaoDe(perfil) : null;
  const fetch = simularApi({
    "GET /api/sessao/atual": sessao ? { corpo: sessao } : { status: 401, corpo: { detail: "Sessão ausente ou expirada." } },
    ...rotas,
  });
  const tela = render(
    <MemoryRouter initialEntries={[rota]}>
      <ProvedorDeSessao>{elemento}</ProvedorDeSessao>
    </MemoryRouter>,
  );
  return { ...tela, fetch };
}

/** As consultas do painel, com as respostas do kit: várias telas abrem nele. */
export function rotasDoPainel() {
  return {
    "GET /api/painel/recortes": { corpo: amostra("GET_api_painel_recortes") },
    "GET /api/painel/indicadores": { corpo: amostra("GET_api_painel_indicadores") },
    "GET /api/painel/ranking": { corpo: amostra("GET_api_painel_ranking") },
    "GET /api/painel/series": { corpo: amostra("GET_api_painel_series") },
    "GET /api/painel/segmentos": { corpo: amostra("GET_api_painel_segmentos") },
    "GET /api/painel/mobilidade": { corpo: amostra("GET_api_painel_mobilidade") },
    "GET /api/painel/decisao": { corpo: amostra("GET_api_painel_decisao") },
    "GET /api/otimizacoes": { corpo: amostra("GET_api_otimizacoes") },
    "GET /api/otimizacoes/:id": { corpo: amostra("GET_api_otimizacoes_execucao_id") },
  };
}
