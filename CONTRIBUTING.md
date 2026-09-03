# Como contribuir

Guia de trabalho da equipe do Growth Intelligence Hub. Detalhamento completo de papéis e cerimônias em
[`docs/06-equipe-e-processo.md`](docs/06-equipe-e-processo.md).

> **Antes do primeiro commit, leia [`CLAUDE.md`](CLAUDE.md).** Ele traz as regras inegociáveis, o mapa de
> responsabilidades por diretório, as convenções de nomenclatura e as orientações para trabalhar com
> assistente de IA sem que cinco pessoas produzam cinco arquiteturas diferentes.

## Ramos

`main` é **protegida**: recebe alterações apenas por Pull Request aprovado por outro integrante, com a
integração contínua verde.

| Prefixo | Uso | Exemplo |
|---|---|---|
| `feat/` | Nova funcionalidade | `feat/54-otimizador-cuda` |
| `fix/` | Correção | `fix/61-fila-duplicando-mensagem` |
| `docs/` | Somente documentação | `docs/ajuste-cronograma` |
| `spike/` | Investigação técnica | `spike/toolchain-cuda` |

Sempre inclua o número da issue no nome do ramo.

## Commits

Formato: `<tipo>: <o que mudou e por quê>`

Tipos: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `chore`

Mensagens em português. Explique **o porquê** — o "o quê" já está no diff.

```
feat: recusar importação sem período informado

Sem o período, as métricas ficam órfãs na linha do tempo e a segmentação
por tendência classifica errado sem emitir erro. Melhor falhar na entrada.
```

## Pull Requests

1. Abra a partir de um ramo com o número da issue
2. Título no formato `H54 · Otimizador em CUDA (#54)`
3. Preencha o modelo de descrição
4. Solicite revisão de **um integrante que não seja você**
5. Aguarde a CI ficar verde
6. Mescle por *squash*

## Definition of Done

Uma história só está concluída quando todos os itens forem verdadeiros:

- [ ] Critérios de aceite atendidos
- [ ] Pull Request revisado e aprovado por outro integrante
- [ ] CI verde: análise estática e testes
- [ ] Teste automatizado cobrindo o comportamento novo, quando for regra de negócio
- [ ] Autorização verificada no servidor, quando a história expõe endpoint
- [ ] Documentação afetada atualizada no mesmo Pull Request
- [ ] Funcionalidade demonstrada rodando
- [ ] Issue movida para Concluído no board

## Regras invioláveis

1. **Nenhum dado real** entra no repositório. Massa de demonstração vem sempre de
   `scripts/gerar_dados_sinteticos.py`.
2. **Nenhum segredo** versionado. Use `.env`, que está no `.gitignore`.
3. **Nenhum nome** de organização, pessoa ou parceiro real em código, documentação ou dados de exemplo.
4. **Regra de negócio nunca no frontend.** A interface exibe; a API decide.
5. **O modelo de linguagem não calcula número.** Todo valor vem do núcleo determinístico.
