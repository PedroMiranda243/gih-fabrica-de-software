# `modelo/` — previsão de faturamento e risco

Pacote `gih_modelo`: variáveis (H41), referências (H46), rede e treino (H42, H43). **Prevê; não decide.**
Recebe séries numéricas e devolve números — não conhece banco, FastAPI nem regra de negócio. Quem diz o
que é queda (RN09) e se uma versão entra em uso (UC07-A1) é a API. O porquê de cada escolha está na
ADR-010 e na §4.4 de [`docs/07-arquitetura-preliminar.md`](../docs/07-arquitetura-preliminar.md).

| Arquivo | O que faz |
|---|---|
| `variaveis.py` | A janela de 4 períodos por parceiro, as variáveis e a separação **por tempo** |
| `baselines.py` | Repetir o último período, média móvel, e a taxa de risco observada |
| `rede.py` | A rede: duas camadas de 32, com uma saída para o faturamento e outra para o risco |
| `treino.py` | Treina com semente fixa, calibra o risco, mede contra as referências, serializa os pesos |
| `avaliacao.py` | MAPE, Brier e erro de calibração |

## Rodando os testes

No mesmo ambiente virtual da API, de dentro de `modelo/`:

```bash
pip install -r requirements.txt
pip install --no-deps -e .
pytest
```

Os testes usam uma rede sintética em memória (`tests/conftest.py`), sem banco. A medição oficial contra as
referências usa o gerador de verdade e fica em `docs/medicoes/`.
