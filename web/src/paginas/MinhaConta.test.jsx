import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { ContextoSessao } from "../api/contextoSessao";
import { simularApi } from "../testes/preparar";
import MinhaConta from "./MinhaConta";

const EU = { id: 5, login: "ana.lista", nome: "Ana de Exemplo", perfil: "ANALISTA", ativo: true };

function renderizar(usuario = EU) {
  return render(
    <ContextoSessao.Provider value={{ usuario }}>
      <MemoryRouter>
        <MinhaConta />
      </MemoryRouter>
    </ContextoSessao.Provider>,
  );
}

async function preencher(usuario, { atual = "senha-de-agora", nova = "senha-nova-bem-longa", de_novo = nova } = {}) {
  await usuario.type(screen.getByLabelText(/^Senha atual/), atual);
  await usuario.type(screen.getByLabelText(/^Senha nova \*/), nova);
  await usuario.type(screen.getByLabelText(/^Senha nova, de novo/), de_novo);
}

describe("minha conta", () => {
  it("mostra os dados de quem está usando, com o perfil por extenso", () => {
    renderizar();

    const dados = screen.getByRole("region", { name: "Seus dados" });
    expect(dados).toHaveTextContent("Ana de Exemplo");
    expect(dados).toHaveTextContent("ana.lista");
    expect(dados).toHaveTextContent("Analista");
  });

  it("trocar manda a atual e a nova, esvazia os campos e diz que as outras sessões caíram", async () => {
    const enviados = [];
    simularApi({
      "POST /api/sessao/senha": (_url, opcoes) => {
        enviados.push(JSON.parse(opcoes.body));
        return { status: 204 };
      },
    });
    const usuario = userEvent.setup();
    renderizar();

    await preencher(usuario);
    await usuario.click(screen.getByRole("button", { name: "Trocar a senha" }));

    const aviso = await screen.findByRole("status");
    expect(aviso).toHaveTextContent("Senha trocada.");
    expect(aviso).toHaveTextContent("As outras sessões desta conta foram encerradas");
    // A confirmação é da tela: o servidor recebe a atual e a nova, e só.
    expect(enviados).toEqual([{ senha_atual: "senha-de-agora", senha_nova: "senha-nova-bem-longa" }]);
    expect(screen.getByLabelText(/^Senha atual/)).toHaveValue("");
    expect(screen.getByLabelText(/^Senha nova \*/)).toHaveValue("");
  });

  it("a senha atual que não confere aparece embaixo dela, com o foco nela", async () => {
    simularApi({
      "POST /api/sessao/senha": {
        status: 422,
        corpo: {
          erro: "Alguns campos precisam de correção.",
          campos: [{ campo: "senha_atual", mensagem: "A senha atual está incorreta." }],
        },
      },
    });
    const usuario = userEvent.setup();
    renderizar();

    await preencher(usuario, { atual: "chute" });
    await usuario.click(screen.getByRole("button", { name: "Trocar a senha" }));

    expect(await screen.findByText("A senha atual está incorreta.")).toBeInTheDocument();
    expect(screen.getByLabelText(/^Senha atual/)).toHaveFocus();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("a senha nova que é fraca aparece embaixo dela, com a regra que o servidor mandou", async () => {
    simularApi({
      "POST /api/sessao/senha": {
        status: 422,
        corpo: {
          erro: "Alguns campos precisam de correção.",
          campos: [{ campo: "senha_nova", mensagem: "A senha precisa ter pelo menos 12 caracteres." }],
        },
      },
    });
    const usuario = userEvent.setup();
    renderizar();

    await preencher(usuario, { nova: "curta" });
    await usuario.click(screen.getByRole("button", { name: "Trocar a senha" }));

    expect(await screen.findByText("A senha precisa ter pelo menos 12 caracteres.")).toBeInTheDocument();
    expect(screen.getByLabelText(/^Senha nova \*/)).toHaveFocus();
  });

  it("as duas digitações diferentes não chegam ao servidor", async () => {
    const espia = simularApi({});
    const usuario = userEvent.setup();
    renderizar();

    await preencher(usuario, { de_novo: "senha-nova-bem-lomga" });
    await usuario.click(screen.getByRole("button", { name: "Trocar a senha" }));

    expect(screen.getByText("As duas digitações da senha nova não são iguais.")).toBeInTheDocument();
    expect(screen.getByLabelText(/^Senha nova, de novo/)).toHaveFocus();
    expect(espia).not.toHaveBeenCalled();
  });

  it("o erro que não é de campo aparece no topo do formulário", async () => {
    simularApi({
      "POST /api/sessao/senha": {
        status: 500,
        corpo: { erro: "Não foi possível concluir a operação.", correlacao: "abc123" },
      },
    });
    const usuario = userEvent.setup();
    renderizar();

    await preencher(usuario);
    await usuario.click(screen.getByRole("button", { name: "Trocar a senha" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Não foi possível concluir a operação.");
  });
});
