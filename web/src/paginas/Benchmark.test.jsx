import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { simularApi } from "../testes/preparar";
import Benchmark, { INTERVALO_MS } from "./Benchmark";

const MODOS_TODOS = [
  { coluna: "PYTHON", disponivel: true, motivo: null, detalhe: null },
  { coluna: "CPP_SERIAL", disponivel: true, motivo: null, detalhe: null },
  { coluna: "OPENMP", disponivel: true, motivo: null, detalhe: "8 threads" },
  { coluna: "GPU", disponivel: true, motivo: null, detalhe: "NVIDIA GeForce RTX 4060" },
];
const SEM_GPU = "Nenhuma GPU NVIDIA disponível nesta máquina.";

function coluna(nome, media, extra = {}) {
  return {
    coluna: nome,
    situacao: "MEDIDA",
    motivo: null,
    tempos_s: [media, media],
    media_s: media,
    desvio_s: media / 50,
    contexto_s: null,
    speedup_python: 26.3 / media,
    speedup_cpp: null,
    uplift: "34843.00",
    diferenca_uplift: 0,
    divergente: false,
    ...extra,
  };
}

function execucao(extra = {}) {
  return {
    id: 7,
    situacao: "CONCLUIDA",
    autor: "Gestora",
    iniciada_em: "2026-09-27T14:00:00Z",
    concluida_em: "2026-09-27T14:02:00Z",
    parametros: { parceiros: 2000, acoes: 5, repeticoes: 2 },
    progresso: null,
    colunas: [
      coluna("PYTHON", 26.3),
      coluna("CPP_SERIAL", 0.322),
      coluna("OPENMP", 0.0545, { speedup_cpp: 0.322 / 0.0545 }),
      coluna("GPU", 0.195, { speedup_cpp: 0.322 / 0.195, contexto_s: 0.188 }),
    ],
    ambiente: { threads: 8, gpu: "NVIDIA GeForce RTX 4060", compilador: "g++ 13.3.0" },
    disputada: false,
    motivo: null,
    explicacao_gpu:
      "Com 2.000 parceiros, a GPU não ganha do CPU paralelo: ela gasta 188 ms para começar. É um resultado legítimo, e não um defeito.",
    escalabilidade: {
      acoes: 5,
      series: [
        { coluna: "PYTHON", pontos: [{ parceiros: 2000, media_s: 26.3, execucao_id: 7 }] },
        { coluna: "CPP_SERIAL", pontos: [{ parceiros: 2000, media_s: 0.322, execucao_id: 7 }] },
        { coluna: "OPENMP", pontos: [{ parceiros: 2000, media_s: 0.0545, execucao_id: 7 }] },
        { coluna: "GPU", pontos: [{ parceiros: 2000, media_s: 0.195, execucao_id: 7 }] },
      ],
    },
    ...extra,
  };
}

function estado(extra = {}) {
  return {
    colunas: MODOS_TODOS,
    padrao: { parceiros: 2000, acoes: 5, repeticoes: 3 },
    em_andamento: null,
    ultima: null,
    pode_executar: true,
    motivo_bloqueio: null,
    python_s_por_parceiro: null,
    ...extra,
  };
}

const HISTORICO_VAZIO = { itens: [], total: 0, pagina: 1, tamanho: 10 };

function renderizar(endereco = "/benchmark") {
  return render(
    <MemoryRouter initialEntries={[endereco]}>
      <Benchmark />
    </MemoryRouter>,
  );
}

describe("tela do benchmark", () => {
  it("sem benchmark ainda: o cenário sugerido, os modos da máquina e por que falta cada um", async () => {
    simularApi({
      "GET /api/benchmark": {
        corpo: estado({
          colunas: [
            MODOS_TODOS[0],
            MODOS_TODOS[1],
            MODOS_TODOS[2],
            { coluna: "GPU", disponivel: false, motivo: SEM_GPU, detalhe: null },
          ],
        }),
      },
      "GET /api/benchmarks": { corpo: HISTORICO_VAZIO },
    });
    renderizar();

    expect(await screen.findByLabelText(/Parceiros/)).toHaveValue(2000);
    expect(screen.getByLabelText(/Tipos de ação/)).toHaveValue(5);
    expect(screen.getByLabelText(/Repetições/)).toHaveValue(3);
    const modos = screen.getByRole("list", { name: "Modos nesta máquina" });
    expect(within(modos).getByText("disponível, 8 threads")).toBeInTheDocument();
    // UC09-A1: o que falta está na lista, com o motivo escrito.
    expect(within(modos).getByText(`indisponível: ${SEM_GPU}`)).toBeInTheDocument();
    expect(screen.getByText(/cada repetição dele leva minutos/)).toBeInTheDocument();
    expect(screen.getByText("Nenhum benchmark ainda.")).toBeInTheDocument();
  });

  it("com medição anterior, estima a duração pelo Python", async () => {
    simularApi({
      "GET /api/benchmark": { corpo: estado({ python_s_por_parceiro: 0.013 }) },
      "GET /api/benchmarks": { corpo: HISTORICO_VAZIO },
    });
    const usuario = userEvent.setup();
    renderizar();
    // 0,013 s por parceiro × 2.000 × 3 repetições = 78 s.
    expect(await screen.findByText(/Leva cerca de 1 min 18 s, quase todo no Python/)).toBeInTheDocument();
    await usuario.clear(screen.getByLabelText(/Repetições/));
    await usuario.type(screen.getByLabelText(/Repetições/), "1");
    expect(screen.getByText(/Leva cerca de 26,0 s/)).toBeInTheDocument();
  });

  it("o comparativo: as quatro colunas, os ganhos e a frase que resume", async () => {
    simularApi({
      "GET /api/benchmark": { corpo: estado({ ultima: execucao() }) },
      "GET /api/benchmarks": { corpo: { ...HISTORICO_VAZIO, itens: [execucao()], total: 1 } },
    });
    renderizar();

    expect(
      await screen.findByText(
        "O mais rápido foi o OpenMP: 54,5 ms em média, 483x mais rápido que o Python, que levou 26,3 s. O plano foi o mesmo nos 4 modos.",
      ),
    ).toBeInTheDocument();
    const tabela = screen.getByRole("table", { name: "Comparativo dos modos de execução" });
    const cabecalho = within(tabela).getAllByRole("columnheader").map((c) => c.textContent);
    expect(cabecalho).toEqual(["Medida", "Python", "C++ serial", "OpenMP", "GPU"]);
    const linha = (rotulo) =>
      within(tabela)
        .getByRole("rowheader", { name: rotulo })
        .closest("tr")
        .querySelectorAll("td");
    expect([...linha("Tempo médio")].map((c) => c.textContent)).toEqual(["26,3 s", "322 ms", "54,5 ms", "195 ms"]);
    expect([...linha("Ganho sobre o Python")].map((c) => c.textContent)).toEqual(["base", "81,7x", "483x", "135x"]);
    expect([...linha("Ganho sobre o C++ serial")].map((c) => c.textContent)).toEqual(["—", "base", "5,9x", "1,7x"]);
    expect([...linha("Início da GPU (contexto)")].map((c) => c.textContent)).toEqual(["—", "—", "—", "188 ms"]);
    expect([...linha("Diferença para o Python")].map((c) => c.textContent)).toEqual(Array(4).fill("0,0%"));
    // UC09-A2: a GPU que não ganha é explicada, com a frase da API.
    expect(screen.getByText("Por que a GPU não ganhou aqui")).toBeInTheDocument();
    expect(screen.getByText(/ela gasta 188 ms para começar/)).toBeInTheDocument();
    expect(screen.getByText(/OpenMP com 8 threads, uma por núcleo físico · GPU NVIDIA GeForce RTX 4060/)).toBeInTheDocument();
  });

  it("sem GPU, a coluna fica na tabela com travessão, e o motivo vai na nota", async () => {
    const semGpu = execucao({
      colunas: [
        ...execucao().colunas.slice(0, 3),
        { ...coluna("GPU", null), situacao: "INDISPONIVEL", motivo: SEM_GPU, tempos_s: [], media_s: null },
      ],
      explicacao_gpu: null,
    });
    simularApi({
      "GET /api/benchmark": { corpo: estado({ ultima: semGpu }) },
      "GET /api/benchmarks": { corpo: HISTORICO_VAZIO },
    });
    renderizar();

    const tabela = await screen.findByRole("table", { name: "Comparativo dos modos de execução" });
    expect(within(tabela).getByRole("columnheader", { name: /GPU/ })).toHaveTextContent("indisponível");
    expect(screen.getByText(`GPU: ${SEM_GPU}`)).toBeInTheDocument();
    expect(screen.getByText(/O plano foi o mesmo nos 3 modos/)).toBeInTheDocument();
    expect(screen.queryByText("Por que a GPU não ganhou aqui")).not.toBeInTheDocument();
  });

  it("o plano que diverge do Python é destacado como possível defeito", async () => {
    const divergente = execucao({
      colunas: execucao().colunas.map((c) =>
        c.coluna === "OPENMP" ? { ...c, diferenca_uplift: 0.05, divergente: true } : c,
      ),
    });
    simularApi({
      "GET /api/benchmark": { corpo: estado({ ultima: divergente }) },
      "GET /api/benchmarks": { corpo: HISTORICO_VAZIO },
    });
    renderizar();
    expect(await screen.findByRole("alert")).toHaveTextContent("O plano do OpenMP diverge do Python em 5,0%.");
    expect(screen.getByText("5,0%, acima de 2%")).toBeInTheDocument();
    expect(screen.getByText(/O plano divergiu: veja abaixo/)).toBeInTheDocument();
  });

  it("o gráfico: legenda com os quatro modos, e os números num clique", async () => {
    simularApi({
      "GET /api/benchmark": { corpo: estado({ ultima: execucao() }) },
      "GET /api/benchmarks": { corpo: HISTORICO_VAZIO },
    });
    const usuario = userEvent.setup();
    renderizar();

    const legenda = await screen.findByRole("list", { name: "Legenda" });
    expect(within(legenda).getAllByRole("listitem").map((i) => i.textContent)).toEqual([
      "Python",
      "C++ serial",
      "OpenMP",
      "GPU",
    ]);
    expect(screen.getByRole("img", { name: /em escalas logarítmicas\. 1 tamanho medido: 2\.000 parceiros/ })).toBeInTheDocument();
    expect(screen.getByText(/Um tamanho só, por enquanto/)).toBeInTheDocument();

    await usuario.click(screen.getByRole("button", { name: "Ver os números" }));
    const numeros = screen.getByRole("table", { name: /por número de parceiros/ });
    expect(within(numeros).getByRole("row", { name: /2\.000/ })).toHaveTextContent("26,3 s322 ms54,5 ms195 ms");
  });

  it("dispara, acompanha o andamento e mostra o resultado quando termina", async () => {
    let consultas = 0;
    let corpoEnviado = null;
    const rodando = execucao({
      id: 8,
      situacao: "EM_ANDAMENTO",
      colunas: [],
      explicacao_gpu: null,
      escalabilidade: null,
      progresso: { passo: 0, total: 1, etapa: "Montando o cenário" },
    });
    simularApi({
      "GET /api/benchmark": { corpo: estado() },
      "GET /api/benchmarks": { corpo: HISTORICO_VAZIO },
      "POST /api/benchmarks": (_url, opcoes) => {
        corpoEnviado = JSON.parse(opcoes.body);
        return { status: 202, corpo: rodando };
      },
      "GET /api/benchmarks/8": () => {
        consultas += 1;
        return consultas === 1
          ? { corpo: { ...rodando, progresso: { passo: 5, total: 9, etapa: "Python, repetição 2 de 3" } } }
          : { corpo: execucao({ id: 8 }) };
      },
    });
    const usuario = userEvent.setup();
    renderizar();

    await usuario.clear(await screen.findByLabelText(/Parceiros/));
    await usuario.type(screen.getByLabelText(/Parceiros/), "500");
    await usuario.click(screen.getByRole("button", { name: "Rodar benchmark" }));
    expect(screen.getByRole("group", { name: "Confirmação" })).toHaveTextContent(
      "Rodar o benchmark com 500 parceiros, 5 tipos de ação e 3 repetições",
    );
    await usuario.click(screen.getByRole("button", { name: "Rodar" }));

    expect(corpoEnviado).toEqual({ parceiros: 500, acoes: 5, repeticoes: 3 });
    expect(await screen.findByText("Benchmark em andamento")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Medindo…" })).toBeDisabled();
    expect(
      await screen.findByText(/Python, repetição 2 de 3 · passo 5 de 9/, {}, { timeout: INTERVALO_MS + 2000 }),
    ).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: "Andamento do benchmark" })).toHaveAttribute("value", "5");
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent(/^Benchmark concluído\. O mais rápido/), {
      timeout: INTERVALO_MS * 2 + 2000,
    });
  }, 15000);

  it("o erro de um campo aparece embaixo dele, com a frase da API", async () => {
    simularApi({
      "GET /api/benchmark": { corpo: estado() },
      "GET /api/benchmarks": { corpo: HISTORICO_VAZIO },
      "POST /api/benchmarks": {
        status: 422,
        corpo: {
          erro: "Confira os campos.",
          campos: [{ campo: "parceiros", mensagem: "Precisa ser no máximo 10000." }],
        },
      },
    });
    const usuario = userEvent.setup();
    renderizar();
    await usuario.clear(await screen.findByLabelText(/Parceiros/));
    await usuario.type(screen.getByLabelText(/Parceiros/), "20000");
    await usuario.click(screen.getByRole("button", { name: "Rodar benchmark" }));
    await usuario.click(screen.getByRole("button", { name: "Rodar" }));
    expect(await screen.findByLabelText(/Parceiros/)).toHaveAccessibleDescription("Precisa ser no máximo 10000.");
  });

  it("o histórico abre uma execução antiga pelo endereço", async () => {
    const antiga = execucao({ id: 3, parametros: { parceiros: 500, acoes: 5, repeticoes: 1 } });
    simularApi({
      "GET /api/benchmark": { corpo: estado({ ultima: execucao() }) },
      "GET /api/benchmarks": { corpo: { ...HISTORICO_VAZIO, itens: [execucao(), antiga], total: 2 } },
      "GET /api/benchmarks/3": { corpo: antiga },
    });
    const usuario = userEvent.setup();
    renderizar();

    const historico = await screen.findByRole("table", { name: /Benchmarks anteriores/ });
    const linhas = within(historico).getAllByRole("row").slice(1);
    expect(linhas[0]).toHaveAttribute("aria-current", "true");
    expect(within(linhas[0]).queryByRole("link", { name: "Abrir" })).not.toBeInTheDocument();
    expect(linhas[1]).toHaveTextContent("500 × 5 ações × 1");
    await usuario.click(within(linhas[1]).getByRole("link", { name: "Abrir" }));
    expect(await screen.findByRole("heading", { name: "Benchmark anterior" })).toBeInTheDocument();
  });
});
