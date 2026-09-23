"""
Gera a planilha de anotação cega para o experimento de acurácia (seção 2.2
do documento de metodologia), reaproveitando gerar_planilha_anotacao.py
sem alterar o arquivo -- só redireciona, em tempo de execução, os dois
caminhos de recortes que o módulo original tem fixos para produção
(RECORTES_BOLHAS_DIR/RECORTES_INSCRICAO_DIR) para os caminhos isolados do
teste (preparar_recortes_teste.py).

Uso, a partir da raiz do repositório:
    python -m corretor.treino.gerar_planilha_anotacao_teste
"""
from corretor import config
from corretor.revisao import gerar_planilha_anotacao as gpa
from corretor.treino.preparar_recortes_teste import (
    RECORTES_BOLHAS_TESTE_DIR,
    RECORTES_INSCRICAO_TESTE_DIR,
)

PLANILHA_ANOTACAO_TESTE_PATH = config.OUTPUTS_DIR / "planilha_anotacao_teste.xlsx"


def gerar_planilha_anotacao_teste() -> None:
    """
    Redireciona os caminhos de recortes do módulo original para os
    caminhos isolados do teste e chama gerar_planilha_anotacao() sem
    tocar no arquivo original -- o módulo (gpa) guarda RECORTES_BOLHAS_DIR
    e RECORTES_INSCRICAO_DIR como nomes próprios (copiados no import), por
    isso a substituição precisa ser feita no namespace do módulo, não em
    corretor.config.
    """
    gpa.RECORTES_BOLHAS_DIR = RECORTES_BOLHAS_TESTE_DIR
    gpa.RECORTES_INSCRICAO_DIR = RECORTES_INSCRICAO_TESTE_DIR
    gpa.gerar_planilha_anotacao(config.AMOSTRA_TESTE_CSV_PATH, PLANILHA_ANOTACAO_TESTE_PATH)


if __name__ == "__main__":
    gerar_planilha_anotacao_teste()
