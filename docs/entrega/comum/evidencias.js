/**
 * Lê as evidências geradas pelos scripts e as prepara para o documento.
 *
 * A evidência entra no PDF a partir do arquivo produzido por uma execução real,
 * e não transcrita à mão. Se alguém reescrever um trecho para ficar mais bonito,
 * a evidência deixa de ser evidência.
 *
 * **Cada entrega tem a sua pasta** — `evidencias/sprint03/`, `evidencias/sprint04/`
 * — e o nome passado a `ler()` e a `trecho()` inclui a pasta. Na Sprint 03 as
 * evidências ficavam soltas em `evidencias/`, e regerá-las para a Sprint 04
 * teria reescrito em silêncio a Parte III, que já foi entregue: evidência de
 * execução é retrato da data em que foi tirada, não documento vivo.
 *
 * Os da Sprint 03 vieram de:
 *   python api/e2e/verificacao.py  > docs/entrega/evidencias/sprint03/verificacao.txt
 *   python api/e2e/transcricao.py  > docs/entrega/evidencias/sprint03/crud.txt
 */
const fs = require('fs');
const path = require('path');

const EVIDENCIAS = path.join(__dirname, '..', 'evidencias');

// A 8 pt em Consolas, cabem cerca de cem caracteres na largura útil da página.
// Passar disso faz a linha sair pela margem — e o Word não avisa, só corta.
const COLUNAS = 96;

function ler(nome) {
  const arquivo = path.join(EVIDENCIAS, nome);
  if (!fs.existsSync(arquivo)) {
    throw new Error(
      `Falta ${nome}. Rode os scripts de evidência com a API no ar — ver o cabeçalho deste módulo.`,
    );
  }
  return fs.readFileSync(arquivo, 'utf8').replace(/\r\n/g, '\n').split('\n');
}

/**
 * Quebra a linha comprida mantendo o alinhamento.
 *
 * A continuação entra recuada, para ficar claro que é a mesma linha e não uma
 * nova — o JSON da resposta perde o sentido se as quebras parecerem estrutura.
 */
function quebrar(linha) {
  if (linha.length <= COLUNAS) return [linha];

  const recuo = (linha.match(/^\s*/) || [''])[0] + '    ';
  const pedacos = [];
  let restante = linha;
  let primeira = true;

  while (restante.length > COLUNAS) {
    const limite = primeira ? COLUNAS : COLUNAS - recuo.length;
    let corte = restante.lastIndexOf(' ', limite);
    if (corte <= recuo.length) corte = limite;   // palavra única, corta no limite

    pedacos.push((primeira ? '' : recuo) + restante.slice(0, corte).trimEnd());
    restante = restante.slice(corte).trimStart();
    primeira = false;
  }
  if (restante) pedacos.push(recuo + restante);
  return pedacos;
}

/** Todas as linhas do arquivo, já quebradas. */
function todas(nome) {
  return ler(nome).flatMap(quebrar);
}

/**
 * As linhas entre dois marcadores, pelo texto que contêm.
 *
 * Recortar por texto, e não por número de linha, é o que permite a evidência ser
 * regerada sem que o recorte passe a mostrar outro trecho.
 */
function trecho(nome, de, ate = null) {
  const linhas = ler(nome);
  const inicio = linhas.findIndex((l) => l.includes(de));
  if (inicio < 0) throw new Error(`Não achei ${JSON.stringify(de)} em ${nome}.`);

  const resto = linhas.slice(inicio);
  const fim = ate ? resto.findIndex((l, i) => i > 0 && l.includes(ate)) : -1;
  return (fim > 0 ? resto.slice(0, fim) : resto).flatMap(quebrar);
}

/** Evidência estruturada, como o registro de bugs — lida do arquivo que o script gerou. */
function json(nome) {
  return JSON.parse(ler(nome).join('\n'));
}

module.exports = { todas, trecho, json, COLUNAS };
