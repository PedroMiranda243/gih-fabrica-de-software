"""Quanto custa passar a instância da API ao núcleo por processo (ADR-012).

Monta uma instância do tamanho do cenário de referência — 2.000 parceiros, 5
ações, ganhos em centavos —, manda ao `eco` pela entrada padrão e lê a resposta.
O `eco` só lê e soma: o que se mede é o custo de processo e de texto, e não o do
otimizador. Roda dentro da imagem do spike (ver o Dockerfile).
"""
import random
import statistics
import subprocess
import time

rng = random.Random(1)
n, a = 2000, 5
custo = [12000, 26000, 48000, 9000, 35000]
ganhos = [[rng.randint(0, 5_000_000) for _ in range(a)] for _ in range(n)]
texto = (
    f"{n} {a}\n"
    + " ".join(map(str, custo))
    + "\n"
    + "\n".join(" ".join(map(str, linha)) for linha in ganhos)
    + "\n"
)
esperado = sum(map(sum, ganhos))

tempos = []
for _ in range(30):
    inicio = time.perf_counter()
    r = subprocess.run(["eco"], input=texto.encode(), capture_output=True, check=True)
    tempos.append((time.perf_counter() - inicio) * 1000)
    assert r.stdout.split() == [str(n).encode(), str(esperado).encode()]

print(f"instância de {n} parceiros × {a} ações: {len(texto) / 1024:.0f} KB em texto")
print(
    f"ida e volta por subprocesso: mediana {statistics.median(tempos):.1f} ms "
    f"(de {min(tempos):.1f} a {max(tempos):.1f}), 30 vezes"
)
