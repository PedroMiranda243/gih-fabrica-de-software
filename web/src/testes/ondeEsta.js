/* Onde a aplicação de teste está: o componente Endereco anota, o teste lê. */
let ondeEsta = null;

export const anotarEndereco = (caminho) => {
  ondeEsta = caminho;
};

export const endereco = () => ondeEsta;
