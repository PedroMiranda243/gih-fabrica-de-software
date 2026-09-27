"""O portal do Parceiro — UC13, RF19, RF26, história H39.

**Só o perfil Parceiro, e só o próprio parceiro.** A rota não recebe identificador
nenhum: o parceiro sai do vínculo do usuário da sessão, e não há parâmetro que se
possa trocar para pedir o de outro (UC13-E1, RNF14). Os outros perfis recebem
403 — eles têm o painel —, e qualquer rota de dados da rede que o Parceiro tente
abrir recusa pelo `exigir` dela, que registra a tentativa na auditoria.

**Sem ranking e sem comparação** (RF26): a série e os indicadores são do parceiro,
contra ele mesmo no período anterior. Posição relativa e desempenho alheio são
informação da rede, e não dele.

A série é a mesma do painel (`desempenho.serie_historica`), sem os períodos
anteriores à primeira medição dele: antes de ele chegar à rede, não havia o que
medir, e mostrar esses períodos como lacuna diria que ele deixou de vender.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.calculos import variacao_percentual
from app.dependencias import Banco, UsuarioAtual, exigir
from app.desempenho import serie_historica
from app.esquemas import MeuDesempenho, VariacaoDoParceiro
from app.modelos import OrigemCategoria, Parceiro, Perfil

router = APIRouter(
    prefix="/api/meu-desempenho",
    tags=["portal do parceiro"],
    dependencies=[Depends(exigir(Perfil.PARCEIRO))],
)


@router.get("", response_model=MeuDesempenho)
def meu_desempenho(s: Banco, usuario: UsuarioAtual) -> MeuDesempenho:
    """O histórico do próprio parceiro: faturamento, pedidos e ticket médio por
    período, e os do período mais recente contra o anterior (UC13, passos 1 a 3)."""
    # O banco garante o vínculo do perfil Parceiro (`ck_usuario_parceiro_apenas_perfil_parceiro`).
    parceiro = s.get(Parceiro, usuario.parceiro_id)
    pontos = serie_historica(s, parceiro.id)
    primeiro = next((i for i, p in enumerate(pontos) if p.faturamento is not None), None)
    pontos = pontos[primeiro:] if primeiro is not None else []

    atual = pontos[-1] if pontos else None
    anterior = pontos[-2] if len(pontos) > 1 else None
    variacao = None
    if atual is not None and anterior is not None:
        variacao = VariacaoDoParceiro(
            faturamento=variacao_percentual(atual.faturamento, anterior.faturamento),
            pedidos=variacao_percentual(atual.pedidos, anterior.pedidos),
            ticket_medio=variacao_percentual(atual.ticket_medio, anterior.ticket_medio),
        )
    categoria = (
        parceiro.categoria.nome
        if parceiro.categoria is not None and parceiro.origem_categoria == OrigemCategoria.MANUAL
        else None
    )
    return MeuDesempenho(
        parceiro=parceiro.nome,
        categoria=categoria,
        atual=atual,
        anterior=anterior.periodo if anterior else None,
        variacao=variacao,
        pontos=pontos,
    )
