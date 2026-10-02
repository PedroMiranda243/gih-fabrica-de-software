import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { ContextoSessao } from "../api/contextoSessao";
import { avisariaAoFechar, simularApi } from "../testes/preparar";
import Usuario from "./Usuario";

const EU = { id: 1, login: "admin", nome: "Administração", perfil: "ADMINISTRADOR", ativo: true };
const OUTRA = {
  id: 2,
  login: "gestora",
  nome: "Gestora de Exemplo",
  perfil: "GESTOR",
  ativo: true,
  parceiro_id: null,
  criado_em: "2026-09-02T10:00:00Z",
};

function renderizar(endereco) {
  return render(
    <ContextoSessao.Provider value={{ usuario: EU }}>
      <MemoryRouter initialEntries={[endereco]}>
        <Routes>
          <Route path="/usuarios/novo" element={<Usuario />} />
          <Route path="/usuarios/:id" element={<Usuario />} />
        </Routes>
      </MemoryRouter>
    </ContextoSessao.Provider>,
  );
}

async function preencherNovo(usuario, { login = "nova.pessoa", nome = "Nova Pessoa", senha = "senha-bem-longa" } = {}) {
  await usuario.type(screen.getByLabelText(/^Login/), login);
  await usuario.type(screen.getByLabelText(/^Nome/), nome);
  await usuario.type(screen.getByLabelText(/^Senha inicial/), senha);
}

describe("conta de usuário", () => {
  it("criar leva à conta criada, com a confirmação", async () => {
    simularApi({
      "POST /api/usuarios": { status: 201, corpo: { ...OUTRA, id: 7, login: "nova.pessoa", nome: "Nova Pessoa" } },
      "GET /api/usuarios/7": { corpo: { ...OUTRA, id: 7, login: "nova.pessoa", nome: "Nova Pessoa" } },
    });
    const usuario = userEvent.setup();
    renderizar("/usuarios/novo");

    await preencherNovo(usuario);
    await usuario.click(screen.getByRole("button", { name: "Criar usuário" }));

    expect(await screen.findByRole("status")).toHaveTextContent(
      "Nova Pessoa já pode entrar com o login nova.pessoa",
    );
    expect(await screen.findByRole("heading", { name: "Situação" })).toBeInTheDocument();
  });

  it("os quatro perfis são oferecidos, e o parceiro da conta só aparece com o perfil Parceiro", async () => {
    const usuario = userEvent.setup();
    renderizar("/usuarios/novo");

    const perfis = within(screen.getByLabelText(/^Perfil/)).getAllByRole("option").map((o) => o.textContent);
    expect(perfis).toEqual(["Administrador", "Gestor", "Analista", "Parceiro"]);
    expect(screen.queryByLabelText(/^Parceiro da conta/)).not.toBeInTheDocument();

    await usuario.selectOptions(screen.getByLabelText(/^Perfil/), "PARCEIRO");
    expect(screen.getByLabelText(/^Parceiro da conta/)).toBeInTheDocument();
    expect(screen.getByText("Nenhum parceiro escolhido ainda.")).toBeInTheDocument();
  });

  it("a conta Parceiro é criada com o parceiro achado pelo nome (H101)", async () => {
    const buscas = [];
    const enviados = [];
    simularApi({
      "GET /api/usuarios/parceiros": (url) => {
        buscas.push(new URL(url, "http://x").searchParams.get("busca"));
        return {
          corpo: [
            { id: 31, nome: "Empório da Praça", ativo: true },
            { id: 32, nome: "Padaria Praça Nova", ativo: false },
          ],
        };
      },
      "POST /api/usuarios": (_url, opcoes) => {
        enviados.push(JSON.parse(opcoes.body));
        return { status: 201, corpo: { ...OUTRA, id: 9, perfil: "PARCEIRO", parceiro_id: 31 } };
      },
      "GET /api/usuarios/9": {
        corpo: {
          ...OUTRA, id: 9, perfil: "PARCEIRO", parceiro_id: 31,
          parceiro: { id: 31, nome: "Empório da Praça", ativo: true },
        },
      },
    });
    const usuario = userEvent.setup();
    renderizar("/usuarios/novo");

    await preencherNovo(usuario);
    await usuario.selectOptions(screen.getByLabelText(/^Perfil/), "PARCEIRO");
    await usuario.type(screen.getByLabelText(/^Parceiro da conta/), "praca");

    const achados = await screen.findByRole("list", { name: "Parceiros encontrados" });
    // Só o nome e a situação: é o que a API dá ao administrador.
    expect(within(achados).getAllByRole("button").map((b) => b.textContent)).toEqual([
      "Empório da Praça",
      "Padaria Praça Novadesativado",
    ]);
    await usuario.click(within(achados).getByRole("button", { name: "Empório da Praça" }));
    expect(screen.getByText(/A conta vê só o desempenho de/)).toHaveTextContent("Empório da Praça");

    await usuario.click(screen.getByRole("button", { name: "Criar usuário" }));

    await screen.findByRole("heading", { name: "Situação" });
    expect(buscas.at(-1)).toBe("praca");
    expect(enviados[0]).toMatchObject({ perfil: "PARCEIRO", parceiro_id: 31 });
    // A conta aberta diz de quem ela é, sem precisar buscar de novo.
    expect(screen.getByText(/A conta vê só o desempenho de/)).toHaveTextContent("Empório da Praça");
  });

  it("uma letra só não busca: a API recusaria, e a tela não pede", async () => {
    const espia = simularApi({});
    const usuario = userEvent.setup();
    renderizar("/usuarios/novo");

    await usuario.selectOptions(screen.getByLabelText(/^Perfil/), "PARCEIRO");
    await usuario.type(screen.getByLabelText(/^Parceiro da conta/), "p");
    await new Promise((r) => setTimeout(r, 350));

    expect(espia).not.toHaveBeenCalled();
  });

  it("sem parceiro, a recusa da API aparece no campo do parceiro, com o foco nele", async () => {
    simularApi({
      "POST /api/usuarios": {
        status: 422,
        corpo: {
          erro: "Alguns campos precisam de correção.",
          campos: [{ campo: "requisição", mensagem: "O perfil Parceiro exige um parceiro vinculado." }],
        },
      },
    });
    const usuario = userEvent.setup();
    renderizar("/usuarios/novo");

    await preencherNovo(usuario);
    await usuario.selectOptions(screen.getByLabelText(/^Perfil/), "PARCEIRO");
    await usuario.click(screen.getByRole("button", { name: "Criar usuário" }));

    expect(await screen.findByText("O perfil Parceiro exige um parceiro vinculado.")).toBeInTheDocument();
    expect(screen.getByLabelText(/^Parceiro da conta/)).toHaveFocus();
  });

  it("trocar o parceiro de uma conta manda só o vínculo novo", async () => {
    const enviados = [];
    const conta = {
      ...OUTRA, perfil: "PARCEIRO", parceiro_id: 31,
      parceiro: { id: 31, nome: "Empório da Praça", ativo: true },
    };
    simularApi({
      "GET /api/usuarios/2": { corpo: conta },
      "GET /api/usuarios/parceiros": { corpo: [{ id: 40, nome: "Mercado do Vale", ativo: true }] },
      "PATCH /api/usuarios/2": (_url, opcoes) => {
        enviados.push(JSON.parse(opcoes.body));
        return { corpo: { ...OUTRA, perfil: "PARCEIRO", parceiro_id: 40 } };
      },
    });
    const usuario = userEvent.setup();
    renderizar("/usuarios/2");

    await usuario.type(await screen.findByLabelText(/^Parceiro da conta/), "vale");
    await usuario.click(await screen.findByRole("button", { name: "Mercado do Vale" }));
    await usuario.click(screen.getByRole("button", { name: "Salvar alterações" }));

    expect(await screen.findByText("Alterações salvas.")).toBeInTheDocument();
    expect(enviados[0]).toEqual({ nome: "Gestora de Exemplo", parceiro_id: 40 });
    expect(screen.getByText(/A conta vê só o desempenho de/)).toHaveTextContent("Mercado do Vale");
  });

  it("login repetido aponta a conta que já o usa", async () => {
    simularApi({
      "POST /api/usuarios": {
        status: 409,
        corpo: {
          detail: {
            erro: "Já existe um usuário com o login 'antiga'.",
            ajuda: "Escolha outro login. Se a conta é da mesma pessoa e está desativada, reative-a em vez de criar outra.",
            existente: { id: 2, login: "antiga", nome: "Conta Antiga", ativo: false },
          },
        },
      },
    });
    const usuario = userEvent.setup();
    renderizar("/usuarios/novo");

    await preencherNovo(usuario, { login: "antiga" });
    await usuario.click(screen.getByRole("button", { name: "Criar usuário" }));

    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent("reative-a");
    expect(within(alerta).getByRole("link", { name: "Abrir a conta de Conta Antiga (desativada)" })).toHaveAttribute(
      "href",
      "/usuarios/2",
    );
  });

  it("senha fraca aparece embaixo do campo, com o foco nele", async () => {
    simularApi({
      "POST /api/usuarios": {
        status: 422,
        corpo: {
          erro: "Alguns campos precisam de correção.",
          campos: [{ campo: "senha", mensagem: "A senha precisa ter pelo menos 12 caracteres." }],
        },
      },
    });
    const usuario = userEvent.setup();
    renderizar("/usuarios/novo");

    await preencherNovo(usuario, { senha: "curta" });
    await usuario.click(screen.getByRole("button", { name: "Criar usuário" }));

    expect(await screen.findByText("A senha precisa ter pelo menos 12 caracteres.")).toBeInTheDocument();
    expect(screen.getByLabelText(/^Senha inicial/)).toHaveFocus();
  });

  it("trocar o perfil manda só o que mudou", async () => {
    const enviados = [];
    simularApi({
      "GET /api/usuarios/2": { corpo: OUTRA },
      "PATCH /api/usuarios/2": (_url, opcoes) => {
        enviados.push(JSON.parse(opcoes.body));
        return { corpo: { ...OUTRA, perfil: "ANALISTA" } };
      },
    });
    const usuario = userEvent.setup();
    renderizar("/usuarios/2");

    await usuario.selectOptions(await screen.findByLabelText(/^Perfil/), "ANALISTA");
    await usuario.click(screen.getByRole("button", { name: "Salvar alterações" }));

    expect(await screen.findByRole("status")).toHaveTextContent("O perfil novo vale já");
    expect(enviados[0]).toEqual({ nome: "Gestora de Exemplo", perfil: "ANALISTA" });
  });

  it("o último administrador não cai, e a recusa aparece na própria seção", async () => {
    simularApi({
      "GET /api/usuarios/1": { corpo: { ...OUTRA, ...EU } },
      "PATCH /api/usuarios/1": {
        status: 409,
        corpo: {
          detail: {
            erro: "Este é o último administrador ativo.",
            ajuda: "Sem ele, ninguém mais conseguiria gerenciar usuários. Promova outro usuário a Administrador antes.",
          },
        },
      },
    });
    const usuario = userEvent.setup();
    renderizar("/usuarios/1");

    await usuario.click(await screen.findByRole("button", { name: "Desativar" }));
    // A própria conta: a confirmação avisa que a sessão cai junto.
    const confirmacao = screen.getByRole("group", { name: "Confirmação" });
    expect(confirmacao).toHaveTextContent("Esta é a sua conta");
    await usuario.click(within(confirmacao).getByRole("button", { name: "Desativar" }));

    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent("Este é o último administrador ativo.");
    expect(alerta).toHaveTextContent("Promova outro usuário");
  });

  it("redefinir a senha pede confirmação, manda a senha nova e diz o que aconteceu (H93)", async () => {
    const enviados = [];
    simularApi({
      "GET /api/usuarios/2": { corpo: OUTRA },
      "POST /api/usuarios/2/senha": (_url, opcoes) => {
        enviados.push(JSON.parse(opcoes.body));
        return { status: 204 };
      },
    });
    const usuario = userEvent.setup();
    renderizar("/usuarios/2");

    const senha = within(await screen.findByRole("region", { name: "Senha" }));
    await usuario.type(senha.getByLabelText(/^Senha nova/), "senha-nova-bem-longa");
    await usuario.click(senha.getByRole("button", { name: "Redefinir a senha" }));

    // Nada foi enviado ainda: a confirmação diz que as sessões caem.
    expect(enviados).toEqual([]);
    const confirmacao = senha.getByRole("group", { name: "Confirmação" });
    expect(confirmacao).toHaveTextContent("As sessões abertas dela são encerradas agora");
    await usuario.click(within(confirmacao).getByRole("button", { name: "Redefinir a senha" }));

    expect(await senha.findByRole("status")).toHaveTextContent("Senha redefinida.");
    expect(enviados).toEqual([{ senha_nova: "senha-nova-bem-longa" }]);
    // A senha não fica na tela depois de salva.
    expect(senha.getByLabelText(/^Senha nova/)).toHaveValue("");
  });

  it("a senha fraca na redefinição aparece embaixo do campo, com o foco nele", async () => {
    simularApi({
      "GET /api/usuarios/2": { corpo: OUTRA },
      "POST /api/usuarios/2/senha": {
        status: 422,
        corpo: {
          erro: "Alguns campos precisam de correção.",
          campos: [{ campo: "senha_nova", mensagem: "A senha precisa ter pelo menos 12 caracteres." }],
        },
      },
    });
    const usuario = userEvent.setup();
    renderizar("/usuarios/2");

    const senha = within(await screen.findByRole("region", { name: "Senha" }));
    await usuario.type(senha.getByLabelText(/^Senha nova/), "curta");
    await usuario.click(senha.getByRole("button", { name: "Redefinir a senha" }));
    await usuario.click(
      within(senha.getByRole("group", { name: "Confirmação" })).getByRole("button", { name: "Redefinir a senha" }),
    );

    expect(await senha.findByText("A senha precisa ter pelo menos 12 caracteres.")).toBeInTheDocument();
    expect(senha.getByLabelText(/^Senha nova/)).toHaveFocus();
  });

  it("a própria senha não se redefine aqui: a tela leva à Minha conta", async () => {
    simularApi({ "GET /api/usuarios/1": { corpo: { ...OUTRA, ...EU } } });
    renderizar("/usuarios/1");

    const senha = within(await screen.findByRole("region", { name: "Senha" }));
    expect(senha.getByRole("link", { name: "Minha conta" })).toHaveAttribute("href", "/conta");
    expect(senha.queryByLabelText(/^Senha nova/)).not.toBeInTheDocument();
  });

  it("conta inexistente oferece a volta para a lista", async () => {
    simularApi({ "GET /api/usuarios/99": { status: 404, corpo: { detail: "Usuário não encontrado." } } });
    renderizar("/usuarios/99");

    expect(await screen.findByText("Usuário não encontrado")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Voltar para os usuários" })).toHaveAttribute("href", "/usuarios");
  });
});

describe("conta de usuário — alterações não salvas (H97)", () => {
  it("com o nome alterado, a trilha pergunta antes de sair; salva, a conta deixa sair", async () => {
    simularApi({
      "GET /api/usuarios/2": { corpo: OUTRA },
      "PATCH /api/usuarios/2": { corpo: { ...OUTRA, nome: "Gestora de Exemplo Lima" } },
    });
    const usuario = userEvent.setup();
    renderizar("/usuarios/2");
    const trilha = () =>
      within(screen.getByRole("navigation", { name: "Você está em" })).getByRole("link", { name: "Usuários" });

    await usuario.type(await screen.findByLabelText(/^Nome/), " Lima");
    expect(avisariaAoFechar()).toBe(true);
    await usuario.click(trilha());

    expect(screen.getByRole("alert")).toHaveTextContent("Há alterações que não foram salvas.");
    await usuario.click(screen.getByRole("button", { name: "Continuar editando" }));
    expect(screen.getByLabelText(/^Nome/)).toHaveValue("Gestora de Exemplo Lima");

    await usuario.click(screen.getByRole("button", { name: "Salvar alterações" }));
    expect(await screen.findByText("Alterações salvas.")).toBeInTheDocument();
    expect(avisariaAoFechar()).toBe(false);
  });

  it("a conta aberta e não mexida não pergunta nada", async () => {
    simularApi({ "GET /api/usuarios/2": { corpo: OUTRA } });
    renderizar("/usuarios/2");

    await screen.findByLabelText(/^Nome/);

    expect(avisariaAoFechar()).toBe(false);
  });

  it("a conta nova começada também é alteração: o que foi digitado se perderia", async () => {
    const usuario = userEvent.setup();
    renderizar("/usuarios/novo");
    expect(avisariaAoFechar()).toBe(false);

    await usuario.type(screen.getByLabelText(/^Login/), "nova.pessoa");

    expect(avisariaAoFechar()).toBe(true);
  });
});
