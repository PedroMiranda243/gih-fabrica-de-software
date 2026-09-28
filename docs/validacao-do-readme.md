# Validação do README — H72 (RNF27)

> **O critério:** um integrante que não escreveu a parte em questão sobe o sistema do zero, numa máquina
> limpa, **só com o README**. O que travar vira correção no README ou no Compose.

**Quem valida segue o README, e não este roteiro.** Aqui está só o que conferir em cada passo e o que anotar.
Se for preciso consultar outra coisa além do README para avançar — este arquivo, o código, alguém da equipe —,
isso já é um travamento, e ele vai para o registro.

## Antes de começar

- **A máquina:** sem o projeto clonado e, de preferência, sem as imagens dele no Docker (`docker images`
  não lista nada com `gih`). Anote o sistema operacional, a memória, a versão do Docker Desktop e a placa de
  vídeo, se houver.
- **Um cronômetro.** O tempo de cada passo vai para o registro, e a primeira subida inclui o download das
  imagens.

## Sem GPU e sem o assistente

| # | Passo do README | O que conferir |
|--:|---|---|
| 1 | Clonar | Sem erro. No Windows, numa pasta de caminho curto |
| 2 | `cp .env.example .env` e `docker compose up -d` | Os três contêineres no ar: `docker compose ps` mostra `postgres`, `api` e `web` |
| 3 | `http://localhost:8000/api/health` e `http://localhost:5173` | A saúde responde `"banco": "ok"`, e a interface abre na tela de entrada |
| 4 | `popular-demonstracao` | A saída termina em "Versão em uso", em cerca de 10 s |
| 5 | `criar-usuario` | Pede a senha duas vezes; com ela, a tela de entrada deixa passar |
| 6 | Percorrer a aplicação | O Painel com números e gráficos; a lista de Parceiros; um parceiro com a previsão; a Campanha calcula um plano; o Assistente diz que está indisponível — é o esperado, sem o perfil |
| 7 | A senha do administrador no log | `grep` ou, no PowerShell, `Select-String`; com ela, o administrador entra e vê Usuários e Limiares |

## Com a GPU (se houver placa NVIDIA)

| # | Passo do README | O que conferir |
|--:|---|---|
| 8 | `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build` | A primeira vez baixa a imagem de compilação da NVIDIA (alguns GB). Na Campanha, o modo automático passa a ser a GPU |
| 9 | Benchmark | Mede os quatro modos lado a lado, com o mesmo plano |
| 10 | `docker compose up -d --build`, sem o arquivo | Volta à CPU, e a Campanha diz por que não há GPU |

## Com o assistente

| # | Passo do README | O que conferir |
|--:|---|---|
| 11 | `docker compose --profile assistente up -d` | A primeira vez baixa a imagem do Ollama (~8 GB) e o modelo (~4,7 GB); o serviço `ollama-modelo` baixa e sai |
| 12 | Assistente: "Como foi a rede na semana passada?" | A resposta traz a fonte embaixo. A primeira pergunta leva perto de 45 s, porque o modelo carrega |
| 13 | Com a GPU e o assistente juntos | O comando combinado do README; o modelo passa a responder em poucos segundos |

## O que registrar na issue #164

- a máquina, o sistema operacional e as versões;
- o tempo de cada passo, e o total;
- **cada travamento**, com o que foi preciso fazer para passar dele. Cada um vira correção no README ou no
  Compose, num PR.

## Ensaio prévio — 28/09/2026

Antes da validação, um ensaio seguindo o README ao pé da letra, num clone novo do GitHub, na máquina de
desenvolvimento do Pedro. **Não conta como a validação**, porque foi feito por quem escreveu boa parte do
código, e com as imagens base já no cache do Docker. O que ele achou já foi corrigido:

| O que travou | A correção |
|---|---|
| No Windows, numa pasta funda, o `git clone` falhou com `Filename too long` | O README manda clonar numa pasta de caminho curto, ou ativar o `core.longpaths` |
| Depois do `docker compose up`, a base estava vazia, e os dados de demonstração pediam o Python da máquina com as dependências da API: o `resetar_banco.py` parou num `ModuleNotFoundError` | O comando `popular-demonstracao`, que roda dentro do contêiner: gera a massa, segmenta e treina, sem nada instalado na máquina |
| O gerador, ao limpar a base, apagava os usuários junto — o administrador inclusive —, porque `usuario.parceiro_id` aponta para `parceiro`, e o `TRUNCATE ... CASCADE` esvazia quem aponta | Numa base vazia, o `popular-demonstracao` não apaga nada. Com `--substituir`, ele avisa e recria o administrador |
| O `docker compose up` sem `-d` prende o terminal, e o passo seguinte do README pede outro comando | O README usa `docker compose up -d` |
| No PowerShell, o `grep` do log não existe, e `GIH_ADMIN_SENHA=... python` é sintaxe do bash | O README dá as duas formas do PowerShell |
| A verificação de ponta a ponta roda do Python da máquina, e o README não dizia que ela precisa do `.venv` da API | O README diz |

**Os tempos do ensaio, com as imagens base no cache:**

| Passo | Tempo |
|---|--:|
| Subida (`docker compose up -d`) | 16 s |
| `popular-demonstracao` — 500 parceiros, 12 semanas, segmentação e treino | 7 s |
| A variante com GPU (a imagem da NVIDIA já no cache) | 5 s |
| O primeiro plano da Campanha, em CPU paralela | 73 ms |

Com o Ollama da máquina, pelo `OLLAMA_BASE_URL` do `.env`, o assistente respondeu com a fonte. O perfil
`assistente`, que baixa o modelo para o volume do Compose, fica para a validação.
