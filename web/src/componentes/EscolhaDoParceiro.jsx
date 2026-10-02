import { useEffect, useState } from "react";

import { api } from "../api/cliente";
import Campo from "./Campo";

/* Abaixo disso a API recusa a busca: ela acha um parceiro pelo nome, e não
   entrega a lista (RF56). A tela só deixa de pedir o que já sabe que não vem. */
const MINIMO = 2;

/**
 * O parceiro de uma conta de perfil Parceiro, achado pelo nome (RF56, H101).
 *
 * O Administrador não tem o cadastro nem a lista de parceiros (UC04): a busca
 * devolve só o nome e a situação de quem casa com o que foi digitado, e é o
 * bastante para dizer de quem é a conta. Sem este campo, a conta do parceiro só
 * se criava pela API.
 */
export default function EscolhaDoParceiro({ valor, aoEscolher, erro }) {
  const [termo, setTermo] = useState("");
  const [estado, setEstado] = useState({ termo: "", achados: null, erro: null });
  const busca = termo.trim();

  useEffect(() => {
    if (busca.length < MINIMO) return undefined;
    let vivo = true;
    /* A busca espera a digitação parar, como nas listas. */
    const relogio = setTimeout(() => {
      api
        .get("/api/usuarios/parceiros", { busca })
        .then((achados) => vivo && setEstado({ termo: busca, achados, erro: null }))
        .catch((e) => vivo && setEstado({ termo: busca, achados: null, erro: e }));
    }, 250);
    return () => {
      vivo = false;
      clearTimeout(relogio);
    };
  }, [busca]);

  // O resultado é de um termo: com outro termo na caixa, ele já não vale.
  const doTermo = busca.length >= MINIMO && estado.termo === busca;

  function escolher(parceiro) {
    aoEscolher(parceiro);
    setTermo("");
  }

  return (
    <div className="vinculo">
      <Campo
        id="parceiro_id"
        rotulo="Parceiro da conta"
        obrigatorio
        erro={erro}
        ajuda="Digite ao menos duas letras do nome. A busca mostra só o nome e a situação do parceiro."
      >
        <input
          id="campo-parceiro_id"
          type="search"
          autoComplete="off"
          maxLength={120}
          placeholder="Buscar pelo nome do parceiro"
          value={termo}
          onChange={(e) => setTermo(e.target.value)}
        />
      </Campo>

      {doTermo && estado.erro && (
        <p className="vinculo__nota" role="alert">
          {estado.erro.message}
        </p>
      )}

      {doTermo && estado.achados?.length === 0 && (
        <p className="vinculo__nota" role="status">
          Nenhum parceiro com “{busca}” no nome.
        </p>
      )}

      {doTermo && estado.achados?.length > 0 && (
        <ul className="vinculo__achados" aria-label="Parceiros encontrados">
          {estado.achados.map((p) => (
            <li key={p.id}>
              <button type="button" className="vinculo__achado" onClick={() => escolher(p)}>
                <span className="vinculo__nome">{p.nome}</span>
                {!p.ativo && <span className="vinculo__situacao">desativado</span>}
              </button>
            </li>
          ))}
        </ul>
      )}

      {/* `role="status"`: a escolha muda o que vai ser salvo, e quem usa leitor
          de tela precisa ouvir que mudou. */}
      <p className="vinculo__escolhido" role="status">
        {valor ? (
          <>
            A conta vê só o desempenho de <strong>{valor.nome}</strong>
            {valor.ativo ? "." : " — parceiro desativado."}
          </>
        ) : (
          "Nenhum parceiro escolhido ainda."
        )}
      </p>
    </div>
  );
}
