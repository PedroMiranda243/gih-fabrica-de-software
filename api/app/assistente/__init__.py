"""O assistente analítico — UC12, RF41 a RF43, histórias H65 a H68 (ADR-013).

**O catálogo é fechado.** O modelo de linguagem lê a pergunta e diz de que tipo
ela é e quais campos traz — o parceiro, a categoria, o segmento, as datas. Só
isso. Quem busca os valores é o código, com as mesmas funções das telas, e quem
escreve a resposta também: os números da resposta são os do painel, porque saem
da mesma consulta.

- `catalogo`: os tipos de pergunta, o que cada um precisa e a instrução ao modelo;
- `resolucao`: dos campos extraídos às entidades da base — o parceiro pela busca
  normalizada (RF24), o período pelas datas;
- `respostas`: a resposta de cada tipo, com os fatos que a sustentam;
- `servico`: a pergunta de ponta a ponta.

Sem o modelo no ar, o assistente se declara indisponível, e o resto do sistema
segue (UC12-E1).
"""
