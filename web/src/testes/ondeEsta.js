/* Onde a aplicação de teste está: o componente Endereco anota, o teste lê.
   A anotação acontece num efeito, depois de a tela ser desenhada: o teste espera
   o endereço com waitFor, e não o lê logo depois de achar um texto na tela. */
let ondeEsta = null;

export const anotarEndereco = (caminho) => {
  ondeEsta = caminho;
};

export const endereco = () => ondeEsta;
