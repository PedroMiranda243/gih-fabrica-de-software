"""O cliente do modelo de linguagem (ADR-013).

Contra um Ollama de mentira, num servidor HTTP local: é o que confere o pedido
que sai daqui e o que acontece com cada resposta, sem o modelo. O teste contra o
modelo de verdade roda só onde ele existe, e reprova sem ele quando
`GIH_ASSISTENTE_OBRIGATORIO=1`.
"""

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from pydantic import BaseModel

from app import redator
from app.guarda_numerica import numeros_sem_origem
from app.redator import (
    DEMOROU,
    FORA_DO_AR,
    ILEGIVEL,
    SEM_ENDERECO,
    SEM_MODELO,
    FalhaDoRedator,
    Redator,
)

MODELO = "qwen2.5:7b"


class Ollama:
    """Um Ollama de mentira: guarda os pedidos e responde o que o teste mandar."""

    def __init__(self) -> None:
        self.pedidos: list[tuple[str, dict | None]] = []
        self.modelos = [MODELO]
        self.resposta_do_chat: dict | str = {"message": {"role": "assistant", "content": "Olá."}}
        self.status = 200
        self.atraso = threading.Event()  # enquanto não for liberado, o chat não responde
        self.atraso.set()

    def servidor(self) -> ThreadingHTTPServer:
        ollama = self

        class Tratador(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def _responder(self, status: int, corpo) -> None:
                dados = corpo.encode() if isinstance(corpo, str) else json.dumps(corpo).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(dados)))
                self.end_headers()
                self.wfile.write(dados)

            def do_GET(self):
                ollama.pedidos.append((self.path, None))
                modelos = ollama.modelos
                if modelos is not None:
                    modelos = [{"name": m} for m in modelos]
                self._responder(200, {"models": modelos})

            def do_POST(self):
                tamanho = int(self.headers["Content-Length"])
                ollama.pedidos.append((self.path, json.loads(self.rfile.read(tamanho))))
                ollama.atraso.wait(5)
                if ollama.status != 200:
                    self._responder(ollama.status, {"error": "model not found"})
                else:
                    self._responder(200, ollama.resposta_do_chat)

        class Servidor(ThreadingHTTPServer):
            def handle_error(self, *_):
                # O cliente que desistiu por tempo fecha a conexão antes da resposta.
                pass

        return Servidor(("127.0.0.1", 0), Tratador)


@pytest.fixture
def ollama():
    falso = Ollama()
    servidor = falso.servidor()
    thread = threading.Thread(target=servidor.serve_forever, daemon=True)
    thread.start()
    falso.url = f"http://127.0.0.1:{servidor.server_address[1]}"
    yield falso
    falso.atraso.set()
    servidor.shutdown()
    servidor.server_close()


def _redator(ollama, tempo_limite_s: float = 5) -> Redator:
    return Redator(ollama.url, MODELO, tempo_limite_s)


def _porta_fechada() -> str:
    """Um endereço onde ninguém escuta: a porta de um servidor que acabou de fechar."""
    servidor = ThreadingHTTPServer(("127.0.0.1", 0), BaseHTTPRequestHandler)
    porta = servidor.server_address[1]
    servidor.server_close()
    return f"http://127.0.0.1:{porta}"


# ----------------------------------------------------------------- o estado
def test_pronto_quando_o_modelo_esta_baixado(ollama):
    assert _redator(ollama).estado() == redator.Estado(True, MODELO)
    assert ollama.pedidos == [("/api/tags", None)]


def test_modelo_que_falta_diz_qual(ollama):
    ollama.modelos = ["llama3:latest"]
    estado = _redator(ollama).estado()
    assert not estado.disponivel
    assert estado.motivo == SEM_MODELO.format(modelo=MODELO)


def test_modelo_sem_etiqueta_acha_o_latest(ollama):
    ollama.modelos = ["qwen2.5:latest"]
    assert Redator(ollama.url, "qwen2.5", 5).estado().disponivel


def test_lista_de_modelos_malformada_e_modelo_que_falta(ollama):
    ollama.modelos = None
    estado = _redator(ollama).estado()
    assert estado.motivo == SEM_MODELO.format(modelo=MODELO)


def test_sem_endereco_nao_tenta_nada():
    estado = Redator("", MODELO, 5).estado()
    assert estado == redator.Estado(False, MODELO, SEM_ENDERECO)


def test_servico_fora_do_ar():
    estado = Redator(_porta_fechada(), MODELO, 5).estado()
    assert estado == redator.Estado(False, MODELO, FORA_DO_AR)


# ----------------------------------------------------------------- redigir
def test_redigir_manda_o_sistema_os_fatos_e_as_opcoes(ollama):
    ollama.resposta_do_chat = {"message": {"content": "  Obrigado pela parceria.\n"}}
    texto = _redator(ollama).redigir("Você redige mensagens.", "Fatos: 412 pedidos.")

    assert texto == "Obrigado pela parceria."
    caminho, corpo = ollama.pedidos[-1]
    assert caminho == "/api/chat"
    assert corpo["model"] == MODELO
    assert corpo["stream"] is False
    assert corpo["messages"] == [
        {"role": "system", "content": "Você redige mensagens."},
        {"role": "user", "content": "Fatos: 412 pedidos."},
    ]
    # O texto varia o mínimo, e tem teto.
    assert corpo["options"]["temperature"] == 0
    assert corpo["options"]["seed"] == redator.OPCOES["seed"]
    assert corpo["options"]["num_predict"] == redator.MAXIMO_DE_TOKENS
    assert "format" not in corpo


def test_redigir_sem_endereco():
    with pytest.raises(FalhaDoRedator, match=SEM_ENDERECO):
        Redator("", MODELO, 5).redigir("s", "p")


def test_redigir_fora_do_ar():
    with pytest.raises(FalhaDoRedator, match=FORA_DO_AR):
        Redator(_porta_fechada(), MODELO, 5).redigir("s", "p")


def test_redigir_sem_o_modelo_baixado(ollama):
    ollama.status = 404
    with pytest.raises(FalhaDoRedator) as falha:
        _redator(ollama).redigir("s", "p")
    assert str(falha.value) == SEM_MODELO.format(modelo=MODELO)


def test_redigir_com_erro_do_servico(ollama):
    ollama.status = 500
    with pytest.raises(FalhaDoRedator, match=FORA_DO_AR):
        _redator(ollama).redigir("s", "p")


def test_redigir_que_demora_mais_que_o_limite(ollama):
    ollama.atraso.clear()
    with pytest.raises(FalhaDoRedator) as falha:
        _redator(ollama, tempo_limite_s=1).redigir("s", "p")
    assert str(falha.value) == DEMOROU.format(s=1)


@pytest.mark.parametrize(
    "resposta",
    [
        {"message": {"content": "   "}},  # vazio
        {"message": {"content": None}},
        {"message": "texto solto"},
        {"sem": "mensagem"},
        ["uma", "lista"],
        "isto não é JSON",
    ],
)
def test_redigir_com_resposta_ilegivel(ollama, resposta):
    ollama.resposta_do_chat = resposta
    with pytest.raises(FalhaDoRedator) as falha:
        _redator(ollama).redigir("s", "p")
    assert str(falha.value) == ILEGIVEL


# ----------------------------------------------------------------- extrair
class Pergunta(BaseModel):
    tipo: str
    parceiro: str | None


def test_extrair_pede_o_esquema_e_valida_a_resposta(ollama):
    ollama.resposta_do_chat = {
        "message": {"content": '{"tipo": "faturamento", "parceiro": "Mercearia Boa Vista"}'}
    }
    campos = _redator(ollama).extrair("Classifique.", "Quanto a Mercearia faturou?", Pergunta)

    assert campos == Pergunta(tipo="faturamento", parceiro="Mercearia Boa Vista")
    _, corpo = ollama.pedidos[-1]
    assert corpo["format"] == Pergunta.model_json_schema()


@pytest.mark.parametrize(
    "conteudo",
    ['{"tipo": 3}', '{"parceiro": "x"}', "nem JSON", ""],
)
def test_extrair_fora_do_esquema_nao_passa(ollama, conteudo):
    ollama.resposta_do_chat = {"message": {"content": conteudo}}
    with pytest.raises(FalhaDoRedator, match=ILEGIVEL):
        _redator(ollama).extrair("s", "p", Pergunta)


# --------------------------------------------------------- a configuração
def test_atual_segue_a_configuracao(monkeypatch):
    monkeypatch.setattr(redator.config, "ollama_base_url", "http://ollama:11434/")
    monkeypatch.setattr(redator.config, "llm_model", "qwen2.5:7b")
    monkeypatch.setattr(redator.config, "llm_tempo_limite_s", 42)
    r = redator.atual()
    assert (r.url, r.modelo, r.tempo_limite_s) == ("http://ollama:11434", "qwen2.5:7b", 42)


# ------------------------------------------------------- o modelo de verdade
@pytest.fixture
def modelo_real():
    """O modelo de verdade, pelo `OLLAMA_BASE_URL`. Sem ele o teste pula — exceto com
    `GIH_ASSISTENTE_OBRIGATORIO=1`."""
    r = redator.atual()
    estado = r.estado()
    if not estado.disponivel:
        if os.environ.get("GIH_ASSISTENTE_OBRIGATORIO") == "1":
            pytest.fail(f"O modelo de linguagem é obrigatório aqui: {estado.motivo}")
        pytest.skip(f"Modelo de linguagem fora do ar: {estado.motivo}")
    return r


def test_o_modelo_de_verdade_redige_so_com_os_fatos(modelo_real):
    fatos = {"parceiro": "Mercearia Boa Vista", "periodo": "08/2026", "pedidos": "412"}
    texto = modelo_real.redigir(
        "Você escreve uma frase curta em português do Brasil. Use só os fatos, com os números "
        "exatamente como estão.",
        "\n".join(f"- {k}: {v}" for k, v in fatos.items()),
    )
    assert texto
    # Não é garantia de que o modelo obedeça — é o que a guarda existe para pegar —,
    # mas, com uma instrução assim, ele obedece; se deixar de obedecer, é notícia.
    assert numeros_sem_origem(texto, fatos) == []


def test_o_modelo_de_verdade_devolve_o_esquema(modelo_real):
    campos = modelo_real.extrair(
        "Classifique a pergunta e extraia o parceiro. Não responda a pergunta.",
        "Quanto a Mercearia Boa Vista faturou em agosto?",
        Pergunta,
    )
    assert isinstance(campos, Pergunta)
