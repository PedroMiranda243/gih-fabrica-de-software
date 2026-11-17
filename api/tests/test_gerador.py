"""O resumo que o gerador imprime no fim do `popular-demonstracao` (#287).

É o que quem segue o README lê depois de criar a base: os números saem como a tela
os escreve, e os maiores faturamentos não se chamam "Top" — o Top é o limiar da
segmentação, configurável (RN01, #229).
"""
from __future__ import annotations

from decimal import Decimal

from app.cli import _gerador


def test_o_resumo_escreve_os_numeros_como_a_tela_e_nao_chama_os_maiores_de_top():
    gerador = _gerador()
    linhas = gerador.texto_do_resumo(
        500, 12, 5752, 42,
        total=Decimal("1839707.96"),
        mediana=Decimal("2215.4"),
        soma_dos_maiores=Decimal("379525.41"),
        top=[("Ponto Azul 2", Decimal("79410.29")), ("Quintal Verde 2", Decimal("57841.79"))],
    )
    texto = "\n".join(linhas)

    assert "500 parceiros · 12 períodos · 5.752 métricas · semente 42" in texto
    assert "faturamento total R$ 1.839.707,96 · mediana R$ 2.215,40" in texto
    assert "Os 15 maiores faturamentos somam 20,63% do total" in texto
    assert "R$ 79.410,29" in texto and "Os 2 maiores do último período:" in texto
    assert "Top" not in texto
    assert "1,839,707" not in texto and "79,410.29" not in texto
