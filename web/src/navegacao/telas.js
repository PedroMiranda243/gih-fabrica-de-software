/**
 * Que telas do servidor sustentam cada endereço, e o menu.
 *
 * O servidor diz, na sessão, quais áreas o perfil abre (`usuario.telas`). A tabela
 * `EXIGE` liga cada endereço a essas áreas, e **o menu e a guarda dos endereços
 * leem daqui**: quando cada um tinha a sua lista, o menu escondia a Auditoria do
 * analista e o endereço `/auditoria` a montava para ele, vazia, com a recusa da
 * API dentro. Basta uma das telas da lista. Nenhum `if (perfil === ...)`, e isto
 * não é controle de acesso: quem decide é a API, a cada requisição.
 *
 * Cada grupo do menu é uma rota, com a sua cor (`rota`, ver tokens.css); cada item
 * diz em poucas palavras o que há lá dentro (`dica`), para a pessoa achar onde fica
 * cada coisa.
 */

export const EXIGE = {
  painel: ["painel"],
  meuDesempenho: ["meu_desempenho"],
  /* Quem importa, ou quem só lê o histórico, como o Administrador. */
  importacao: ["importar", "historico_importacoes"],
  parceiros: ["parceiros"],
  assistente: ["assistente"],
  relatorios: ["relatorios"],
  operacoes: ["relatorio_operacoes"],
  modelo: ["modelo"],
  campanha: ["campanha"],
  /* O histórico é também do Administrador; abrir ou comparar planos, não. */
  execucoes: ["execucoes"],
  execucao: ["execucao"],
  benchmark: ["benchmark"],
  mensagens: ["mensagens"],
  aprovacao: ["aprovacao"],
  usuarios: ["usuarios"],
  auditoria: ["auditoria"],
  configuracao: ["configuracao"],
};

export const MENU = [
  {
    grupo: "Análise",
    rota: "analise",
    itens: [
      { rotulo: "Painel", dica: "Os números do período", para: "/", exige: EXIGE.painel, icone: "painel" },
      { rotulo: "Meu desempenho", dica: "Os seus números, período a período", para: "/meu-desempenho", exige: EXIGE.meuDesempenho, icone: "desempenho" },
      { rotulo: "Importação", dica: "Enviar o relatório da semana", para: "/importacao", exige: EXIGE.importacao, icone: "importacao" },
      { rotulo: "Parceiros", dica: "A lista e a ficha de cada um", para: "/parceiros", exige: EXIGE.parceiros, icone: "parceiros" },
      { rotulo: "Assistente", dica: "Perguntas sobre os dados", para: "/assistente", exige: EXIGE.assistente, icone: "assistente" },
      { rotulo: "Relatórios", dica: "Para exportar e imprimir", para: "/relatorios", exige: EXIGE.relatorios, icone: "relatorios" },
    ],
  },
  {
    grupo: "Previsão",
    rota: "previsao",
    itens: [{ rotulo: "Modelo", dica: "A versão em uso e o treino", para: "/modelo", exige: EXIGE.modelo, icone: "modelo" }],
  },
  {
    grupo: "Otimização",
    rota: "otimizacao",
    itens: [
      { rotulo: "Campanha", dica: "Calcular o plano com a verba", para: "/campanha", exige: EXIGE.campanha, icone: "campanha" },
      { rotulo: "Execuções", dica: "Os planos já calculados", para: "/execucoes", exige: EXIGE.execucoes, icone: "execucoes" },
      { rotulo: "Benchmark", dica: "O tempo de cada modo", para: "/benchmark", exige: EXIGE.benchmark, icone: "benchmark" },
    ],
  },
  {
    grupo: "Comunicação",
    rota: "comunicacao",
    itens: [
      { rotulo: "Mensagens", dica: "Gerar as mensagens do plano", para: "/mensagens", exige: EXIGE.mensagens, icone: "mensagens" },
      { rotulo: "Aprovação", dica: "Aprovar, editar ou rejeitar", para: "/aprovacao", exige: EXIGE.aprovacao, icone: "aprovacao" },
    ],
  },
  {
    grupo: "Administração",
    rota: "administracao",
    itens: [
      { rotulo: "Usuários", dica: "Contas e perfis", para: "/usuarios", exige: EXIGE.usuarios, icone: "usuarios" },
      { rotulo: "Auditoria", dica: "Quem fez o quê, e quando", para: "/auditoria", exige: EXIGE.auditoria, icone: "auditoria" },
      { rotulo: "Operações", dica: "Quanto se fez, e do quê", para: "/relatorios/operacoes", exige: EXIGE.operacoes, icone: "operacoes" },
      { rotulo: "Configuração", dica: "Os limiares em vigor", para: "/configuracao", exige: EXIGE.configuracao, icone: "configuracao" },
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
