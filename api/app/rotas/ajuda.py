"""A ajuda — RF55, UC16, história H95.

A tela de ajuda explica os termos que o sistema usa. Os números que ela cita —
o tamanho do Top, os períodos de tendência, o histórico que o modelo exige —
são regra de negócio, e regra de negócio não se escreve na interface (regra
2.4): um "Top 15" digitado na tela continuaria dizendo 15 depois de o
Administrador baixar o limiar para 10. Por isso a tela pergunta aqui, e o que
volta é o que está valendo agora.

**A ordem dos segmentos também vem daqui.** Ela é a precedência da RN01 — Em
Risco antes de Top, de propósito —, e a ajuda que os listasse em outra ordem
ensinaria a regra errada.

**O Parceiro não recebe.** A classificação da rede é da operação interna
(RF26): a ajuda dele fala só do portal dele, e essa parte a tela escreve sem
número nenhum de regra (UC16, A1).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from gih_modelo import JANELA, PERIODOS_MINIMOS

from app import servico_previsao
from app.dependencias import Banco, exigir
from app.esquemas import PrevisaoNaAjuda, RegrasDaAjuda
from app.modelos import Perfil, Segmento
from app.servico_segmentacao import limiares_vigentes

router = APIRouter(
    prefix="/api/ajuda",
    tags=["ajuda"],
    dependencies=[Depends(exigir(Perfil.ADMINISTRADOR, Perfil.GESTOR, Perfil.ANALISTA))],
)


@router.get("/regras", response_model=RegrasDaAjuda)
def regras(s: Banco) -> RegrasDaAjuda:
    """Os números das regras que a ajuda cita, como estão valendo agora."""
    limiares = limiares_vigentes(s)
    concluido = servico_previsao.ultimo_concluido(s)
    versao = concluido.versao_em_uso if concluido else None
    return RegrasDaAjuda(
        # O enum é declarado na ordem de precedência da RN01, e o teste da
        # segmentação confere que `classificar` decide nessa mesma ordem.
        segmentos=list(Segmento),
        top_n=limiares.top_n,
        periodos_tendencia=limiares.periodos_tendencia,
        periodos_novato=limiares.periodos_novato,
        previsao=PrevisaoNaAjuda(
            versao_em_uso=versao,
            origem=(
                None
                if versao is None
                else "REFERENCIA" if servico_previsao.e_referencia(versao) else "MODELO"
            ),
            periodos_minimos_do_treino=PERIODOS_MINIMOS,
            periodos_minimos_do_parceiro=JANELA,
        ),
    )
