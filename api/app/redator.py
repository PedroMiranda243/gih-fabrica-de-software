"""O redator: o modelo de linguagem local, pelo Ollama (ADR-013).

O modelo **redige; não calcula** (RN08, regra 2.3). Ele faz duas coisas, e só
elas:

- `redigir`: recebe fatos já apurados pelo código e devolve texto em volta
  deles. Quem confere se o texto só tem número dos fatos é a guarda numérica
  (`app.guarda_numerica`), e não este módulo;
- `extrair`: recebe uma pergunta e devolve os campos dela num JSON com esquema,
  que o código valida. Quem responde à pergunta é o código.

**O modelo é opcional.** Sem endereço configurado, com o serviço fora do ar ou
sem o modelo baixado, `estado()` diz por quê, e quem chama segue sem ele: as
mensagens saem do modelo fixo, e o assistente se declara indisponível. Nada no
sistema depende de ele estar no ar (RNF06, H72).

A conversa com o Ollama é HTTP com JSON, pela biblioteca padrão: três chamadas
não justificam uma dependência nova (regra 2.8).
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.config import config

log = logging.getLogger("gih")

M = TypeVar("M", bound=BaseModel)

# Temperatura zero e semente fixa, para o texto variar o mínimo. Não é
# garantia: na GPU, duas chamadas seguidas com os mesmos fatos deram frases
# diferentes (a segunda reaproveita o cache do pedido). Nada depende de o texto
# se repetir; o que se repete são os números, e quem garante é a guarda.
OPCOES = {"temperature": 0, "seed": 2026}
# Um teto para o texto: a mensagem tem poucas frases, e o limite segura o tempo
# de um modelo que desanda.
MAXIMO_DE_TOKENS = 400
# Para saber se o serviço está no ar, não se espera o tempo de uma redação.
TEMPO_DA_CONSULTA_S = 3

SEM_ENDERECO = "O assistente não está configurado nesta instalação."
FORA_DO_AR = "O serviço do modelo de linguagem não respondeu."
DEMOROU = "O modelo de linguagem demorou mais de {s} s para responder."
SEM_MODELO = "O modelo {modelo} ainda não foi baixado no serviço do modelo de linguagem."
ILEGIVEL = "O modelo de linguagem respondeu num formato inesperado."


class FalhaDoRedator(Exception):
    """O modelo não entregou: fora do ar, lento demais ou com resposta que não se lê.

    A mensagem é para a tela; o detalhe técnico vai para o log (RNF18).
    """


@dataclass(frozen=True)
class Estado:
    disponivel: bool
    modelo: str
    motivo: str | None = None


class Redator:
    def __init__(self, url: str, modelo: str, tempo_limite_s: float) -> None:
        self.url = url.rstrip("/")
        self.modelo = modelo
        self.tempo_limite_s = tempo_limite_s

    # ------------------------------------------------------------- transporte
    def _pedir(self, caminho: str, corpo: dict | None, tempo_limite_s: float) -> dict:
        if not self.url:
            raise FalhaDoRedator(SEM_ENDERECO)
        dados = None if corpo is None else json.dumps(corpo).encode("utf-8")
        pedido = urllib.request.Request(
            self.url + caminho,
            data=dados,
            headers={"Content-Type": "application/json"},
            method="GET" if corpo is None else "POST",
        )
        try:
            with urllib.request.urlopen(pedido, timeout=tempo_limite_s) as resposta:
                bruto = resposta.read()
        except urllib.error.HTTPError as erro:
            detalhe = erro.read()[:300].decode("utf-8", "replace")
            log.warning("redator: %s respondeu %s: %s", caminho, erro.code, detalhe)
            # O Ollama responde 404 quando o modelo pedido não está baixado.
            if erro.code == 404:
                raise FalhaDoRedator(SEM_MODELO.format(modelo=self.modelo)) from erro
            raise FalhaDoRedator(FORA_DO_AR) from erro
        except TimeoutError as erro:
            log.warning("redator: %s passou de %s s", caminho, tempo_limite_s)
            raise FalhaDoRedator(DEMOROU.format(s=round(tempo_limite_s))) from erro
        except urllib.error.URLError as erro:
            if isinstance(erro.reason, TimeoutError):
                log.warning("redator: %s passou de %s s", caminho, tempo_limite_s)
                raise FalhaDoRedator(DEMOROU.format(s=round(tempo_limite_s))) from erro
            log.warning("redator: %s sem resposta: %s", caminho, erro.reason)
            raise FalhaDoRedator(FORA_DO_AR) from erro
        except OSError as erro:
            log.warning("redator: %s falhou: %r", caminho, erro)
            raise FalhaDoRedator(FORA_DO_AR) from erro
        try:
            resposta = json.loads(bruto)
        except ValueError as erro:
            log.warning("redator: %s respondeu fora de JSON: %r", caminho, bruto[:300])
            raise FalhaDoRedator(ILEGIVEL) from erro
        if not isinstance(resposta, dict):
            log.warning("redator: %s respondeu %r", caminho, bruto[:300])
            raise FalhaDoRedator(ILEGIVEL)
        return resposta

    def _conversar(self, sistema: str, mensagem: str, formato: dict | None = None) -> str:
        corpo = {
            "model": self.modelo,
            "stream": False,
            "messages": [
                {"role": "system", "content": sistema},
                {"role": "user", "content": mensagem},
            ],
            "options": {**OPCOES, "num_predict": MAXIMO_DE_TOKENS},
        }
        if formato is not None:
            corpo["format"] = formato
        resposta = self._pedir("/api/chat", corpo, self.tempo_limite_s)
        mensagem_do_modelo = resposta.get("message")
        conteudo = None
        if isinstance(mensagem_do_modelo, dict):
            conteudo = mensagem_do_modelo.get("content")
        if not isinstance(conteudo, str):
            log.warning("redator: resposta sem mensagem: %s", str(resposta)[:300])
            raise FalhaDoRedator(ILEGIVEL)
        return conteudo

    # ------------------------------------------------------------------ API
    def estado(self) -> Estado:
        """Se o modelo está pronto para uso, e, se não está, por quê."""
        if not self.url:
            return Estado(False, self.modelo, SEM_ENDERECO)
        try:
            resposta = self._pedir("/api/tags", None, TEMPO_DA_CONSULTA_S)
        except FalhaDoRedator:
            # Na consulta, qualquer silêncio é "fora do ar": não houve redação para demorar.
            return Estado(False, self.modelo, FORA_DO_AR)
        modelos = resposta.get("models")
        if not isinstance(modelos, list):
            modelos = []
        nomes = {m.get("name") for m in modelos if isinstance(m, dict)}
        # "qwen2.5" sem etiqueta é o "qwen2.5:latest" para o Ollama.
        procurado = self.modelo if ":" in self.modelo else f"{self.modelo}:latest"
        if procurado not in nomes:
            return Estado(False, self.modelo, SEM_MODELO.format(modelo=self.modelo))
        return Estado(True, self.modelo)

    def redigir(self, sistema: str, pedido: str) -> str:
        """O texto que o modelo escreve para o pedido, sem espaço nas pontas."""
        texto = self._conversar(sistema, pedido).strip()
        if not texto:
            raise FalhaDoRedator(ILEGIVEL)
        return texto

    def extrair(self, sistema: str, pergunta: str, esquema: type[M]) -> M:
        """Os campos da pergunta, no esquema pedido — validados pelo Pydantic, e não pela fé.

        A saída por esquema (`format`) faz o Ollama devolver JSON nesse formato;
        a validação aqui pega o que escapar dele.
        """
        texto = self._conversar(sistema, pergunta, formato=esquema.model_json_schema())
        try:
            return esquema.model_validate_json(texto)
        except ValidationError as erro:
            log.warning("redator: JSON fora do esquema %s: %s", esquema.__name__, texto[:300])
            raise FalhaDoRedator(ILEGIVEL) from erro


def atual() -> Redator:
    """O redator desta instalação, pela configuração. Os testes trocam esta função."""
    return Redator(config.ollama_base_url, config.llm_model, config.llm_tempo_limite_s)
