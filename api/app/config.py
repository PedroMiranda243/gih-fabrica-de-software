"""Configuração da aplicação, lida do ambiente.

Nada de segredo embutido no código: tudo vem do .env, que está no .gitignore.
O repositório é público (ver CLAUDE.md, regra 2.1).
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://gih:gih@localhost:5432/gih"
    api_port: int = 8000

    # Limite de entrada para evitar consumo excessivo de recursos (RNF15).
    tamanho_maximo_relatorio: int = 500_000
    tamanho_maximo_pergunta: int = 1_000

    # ----------------------------------------------------------------- sessão
    # Duração absoluta, sem renovação por uso: quem fica oito horas logado
    # reautentica. Não há requisito fixando esse número — está aqui, e não
    # embutido no código, justamente para a equipe poder mudá-lo sem caçar.
    sessao_duracao_horas: int = 8
    sessao_cookie: str = "gih_sessao"

    # `Secure` exige HTTPS, o que o ambiente local não tem. Em produção isto
    # precisa ser verdadeiro — está no .env.example com o aviso.
    cookie_seguro: bool = False

    # ------------------------------------------------- proteção de força bruta
    # RNF11 fixa as 5 falhas e diz que o bloqueio é por origem; a janela não
    # está no requisito. O bloqueio se desfaz sozinho quando as falhas saem da
    # janela — por isso não existe um "tempo de bloqueio" separado.
    login_falhas_para_bloquear: int = 5
    login_janela_minutos: int = 15

    # ------------------------------------------------------------------ senha
    # Comprimento em vez de regra de composição: exigir símbolo e maiúscula
    # produz "Senha@123", que é pior que uma frase longa.
    senha_tamanho_minimo: int = 10

    # ---------------------------------------------- administrador inicial
    # Sem usuário no banco não há como entrar, e o RNF07 pede que o ambiente
    # suba com um comando só. O entrypoint cria este administrador quando a
    # tabela está vazia. Sem senha definida, ele sorteia uma e imprime no log —
    # senha padrão em repositório público seria um convite.
    admin_login: str = "admin"
    admin_nome: str = "Administrador"
    admin_senha: str = ""


config = Config()
