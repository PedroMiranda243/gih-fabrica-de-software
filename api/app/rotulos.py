"""O nome que a tela dá a cada código — para o texto que a API escreve.

O código (`ADMINISTRADOR`, `CPU_PARALELO`) é o que se grava e o que a API troca
com a interface; quem lê uma mensagem lê "Administrador" e "CPU paralelo". A
mensagem de um campo recusado e o resumo da trilha de auditoria saíam com o
código cru (#281, #294). A tabela segue a de `web/src/formato.js`: não dá para
compartilhar a fonte entre Python e JavaScript, dá para deixar o aviso aqui.

Só os enums que a pessoa escolhe ou lê numa frase. Um código que não está aqui
sai como veio — o que é melhor que um nome inventado.
"""
from __future__ import annotations

ROTULOS = {
    # Perfil (ROTULO_PERFIL)
    "ADMINISTRADOR": "Administrador",
    "GESTOR": "Gestor",
    "ANALISTA": "Analista",
    "PARCEIRO": "Parceiro",
    # Segmento e status comercial (ROTULO_SEGMENTO, ROTULO_STATUS); "Prospecção" é o mesmo nos dois
    "PROSPECCAO": "Prospecção",
    "RECEM_CHEGADO": "Recém-chegado",
    "EM_RISCO": "Em risco",
    "TOP": "Top",
    "EM_ASCENSAO": "Em ascensão",
    "ESTAVEL": "Estável",
    "ATIVO": "Ativo",
    "INATIVO": "Inativo",
    # Modo de execução do otimizador (ROTULO_MODO_CURTO)
    "SERIAL": "Serial",
    "CPU_PARALELO": "CPU paralelo",
    "GPU": "GPU",
    # O público das mensagens, como a tela de Mensagens o oferece
    "FILTRO": "Segmento e categoria",
    "PLANO": "Plano de campanha",
    "SELECAO": "Escolher parceiros",
    # O estado de uma mensagem
    "PENDENTE": "Pendente",
    "APROVADA": "Aprovada",
    "REJEITADA": "Rejeitada",
    # A origem de uma importação (ROTULO_ORIGEM)
    "TEXTO": "Texto colado",
    "CSV": "Arquivo CSV",
}


def rotulo(codigo: object) -> str:
    """O nome do código na tela; o próprio código, se ele não tem nome aqui."""
    return ROTULOS.get(str(codigo), str(codigo))
