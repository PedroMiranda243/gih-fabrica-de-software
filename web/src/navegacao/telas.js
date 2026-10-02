/**
 * Que telas do servidor sustentam cada endereço da interface — H94.
 *
 * O servidor diz, na sessão, quais áreas o perfil abre (`usuario.telas`, que sai
 * das permissões das rotas da API). Esta tabela liga cada endereço a essas
 * áreas, e **o menu e a guarda das rotas leem daqui**: enquanto cada um tinha a
 * sua lista, o menu escondia a Auditoria do analista e o endereço `/auditoria`
 * a montava para ele, vazia, com a recusa da API dentro.
 *
 * **Basta uma das telas.** A Importação aparece para quem importa ou para quem
 * só lê o histórico, que é o caso do Administrador (RF13).
 *
 * **Isto não é controle de acesso** (regra 2.5): quem decide é a API, a cada
 * requisição. Aqui é a interface deixando de mostrar uma tela que ela já sabe
 * que vai ser recusada.
 */
export const EXIGE = {
  /* O endereço raiz é o painel — ou o portal, para o Parceiro, que não tem painel (RF26). */
  inicio: ["painel", "meu_desempenho"],
  painel: ["painel"],
  meuDesempenho: ["meu_desempenho"],
  importacao: ["importar", "historico_importacoes"],
  parceiros: ["parceiros"],
  assistente: ["assistente"],
  relatorios: ["relatorios"],
  operacoes: ["relatorio_operacoes"],
  modelo: ["modelo"],
  campanha: ["campanha"],
  /* O histórico (RF34) é também do Administrador; abrir um plano, não. */
  execucoes: ["execucoes"],
  execucao: ["execucao"],
  benchmark: ["benchmark"],
  mensagens: ["mensagens"],
  aprovacao: ["aprovacao"],
  usuarios: ["usuarios"],
  auditoria: ["auditoria"],
  configuracao: ["configuracao"],
};

/**
 * O perfil abre o que este endereço exige?
 *
 * Sessão aberta antes de o servidor mandar `telas` não tem a lista: sem ela a
 * interface não tem como saber, e deixa a API responder.
 */
export function abre(usuario, exige) {
  const telas = usuario?.telas;
  if (!Array.isArray(telas)) return true;
  return exige.some((tela) => telas.includes(tela));
}
