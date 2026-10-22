/**
 * O menu e a guarda dos endereços leem a mesma tabela, e as duas leem só
 * `usuario.telas`, que vem do servidor. Nenhum `if (perfil === ...)`.
 *
 * Cada grupo é uma rota, com a sua cor (`rota`, ver tokens.css); cada item diz em
 * poucas palavras o que há lá dentro (`dica`), para a pessoa achar onde fica cada coisa.
 */

export const MENU = [
  {
    grupo: "Análise",
    rota: "analise",
    itens: [
      { rotulo: "Painel", dica: "Os números do período", para: "/", exige: ["painel"], icone: "painel" },
      { rotulo: "Meu desempenho", dica: "Os seus números, período a período", para: "/meu-desempenho", exige: ["meu_desempenho"], icone: "desempenho" },
      { rotulo: "Importação", dica: "Enviar o relatório da semana", para: "/importacao", exige: ["importar", "historico_importacoes"], icone: "importacao" },
      { rotulo: "Parceiros", dica: "A lista e a ficha de cada um", para: "/parceiros", exige: ["parceiros"], icone: "parceiros" },
      { rotulo: "Assistente", dica: "Perguntas sobre os dados", para: "/assistente", exige: ["assistente"], icone: "assistente" },
      { rotulo: "Relatórios", dica: "Para exportar e imprimir", para: "/relatorios", exige: ["relatorios"], icone: "relatorios" },
    ],
  },
  {
    grupo: "Previsão",
    rota: "previsao",
    itens: [{ rotulo: "Modelo", dica: "A versão em uso e o treino", para: "/modelo", exige: ["modelo"], icone: "modelo" }],
  },
  {
    grupo: "Otimização",
    rota: "otimizacao",
    itens: [
      { rotulo: "Campanha", dica: "Calcular o plano com a verba", para: "/campanha", exige: ["campanha"], icone: "campanha" },
      { rotulo: "Execuções", dica: "Os planos já calculados", para: "/execucoes", exige: ["execucoes"], icone: "execucoes" },
      { rotulo: "Benchmark", dica: "O tempo de cada modo", para: "/benchmark", exige: ["benchmark"], icone: "benchmark" },
    ],
  },
  {
    grupo: "Comunicação",
    rota: "comunicacao",
    itens: [
      { rotulo: "Mensagens", dica: "Gerar as mensagens do plano", para: "/mensagens", exige: ["mensagens"], icone: "mensagens" },
      { rotulo: "Aprovação", dica: "Aprovar, editar ou rejeitar", para: "/aprovacao", exige: ["aprovacao"], icone: "aprovacao" },
    ],
  },
  {
    grupo: "Administração",
    rota: "administracao",
    itens: [
      { rotulo: "Usuários", dica: "Contas e perfis", para: "/usuarios", exige: ["usuarios"], icone: "usuarios" },
      { rotulo: "Auditoria", dica: "Quem fez o quê, e quando", para: "/auditoria", exige: ["auditoria"], icone: "auditoria" },
      { rotulo: "Operações", dica: "Quanto se fez, e do quê", para: "/relatorios/operacoes", exige: ["relatorio_operacoes"], icone: "operacoes" },
      { rotulo: "Configuração", dica: "Os limiares em vigor", para: "/configuracao", exige: ["configuracao"], icone: "configuracao" },
    ],
  },
];

/** Qual item do menu fica marcado num caminho (inclusive nas telas de detalhe). */
export function itemAtivo(caminho) {
  if (caminho === "/") return "/";
  if (caminho.startsWith("/relatorios/operacoes")) return "/relatorios/operacoes";
  const todos = MENU.flatMap((g) => g.itens.map((i) => i.para)).filter((p) => p !== "/");
  return todos.filter((p) => caminho === p || caminho.startsWith(`${p}/`)).sort((a, b) => b.length - a.length)[0] ?? null;
}

/** O grupo (a rota) do item marcado, ou nada fora das áreas do menu (conta, ajuda). */
export function grupoDe(para) {
  if (!para) return null;
  return MENU.find((g) => g.itens.some((i) => i.para === para)) ?? null;
}
