"""
Roda o modelo em produção (cnn_bolhas.pth) sobre os recortes da amostra de
teste (amostra_teste.csv) e salva a PROBABILIDADE BRUTA de cada bolha --
não a decisão final -- num CSV, pré-requisito para a calibração de margem
por varredura (seção 5 do documento de metodologia): sem a probabilidade
bruta salva, seria preciso rodar o modelo de novo para testar cada margem
candidata.

Uso, a partir da raiz do repositório:
    python -m corretor.treino.inferir_probabilidades_teste
"""
from pathlib import Path
import csv

import torch

from corretor import config
from corretor.revisao import gerar_planilha_anotacao as gpa
from corretor.treino.preparar_recortes_teste import (
    RECORTES_BOLHAS_TESTE_DIR,
    RECORTES_INSCRICAO_TESTE_DIR,
)
from corretor.inferencia.modelo_bolhas import carregar_modelo, obter_device, preprocessar

PROBABILIDADES_TESTE_CSV_PATH = config.OUTPUTS_DIR / "probabilidades_teste.csv"


def montar_itens_teste() -> list[dict]:
    """
    Redireciona os caminhos de recortes do módulo original (mesmo truque
    de gerar_planilha_anotacao_teste.py) e devolve a lista de itens da
    amostra de teste (2 questões por folha, sem inscrição -- a proporção
    de inscrição foi 0.0 no sorteio), no mesmo formato que gerar_planilha()
    usa para montar a planilha de anotação.
    """
    gpa.RECORTES_BOLHAS_DIR = RECORTES_BOLHAS_TESTE_DIR
    gpa.RECORTES_INSCRICAO_DIR = RECORTES_INSCRICAO_TESTE_DIR
    return gpa._montar_itens(gpa.ler_amostra(config.AMOSTRA_TESTE_CSV_PATH))


def inferir_probabilidade_recorte(modelo, device, caminho: Path) -> float | None:
    """
    Roda o modelo sobre um único recorte e devolve a probabilidade bruta
    de "vazia" (mesma convenção do resto do projeto -- probabilidade
    baixa = bolha marcada), ou None se o PNG não abrir. Diferente de
    prob_bolha_preenchida (modelo_bolhas.py), que troca a falha por 1.0
    para não anular uma questão em produção -- aqui queremos o valor
    bruto sem esse fallback: uma falha de leitura na amostra deve
    aparecer como ausência de dado, não como "vazia" fingida.
    """
    tensor = preprocessar(caminho)
    if tensor is None:
        return None
    with torch.no_grad():
        saida = modelo(tensor.unsqueeze(0).to(device))
        return saida.item()


def inferir_probabilidades_teste() -> None:
    """
    Ponto de entrada: monta os itens da amostra de teste, roda o modelo em
    produção sobre cada recorte de cada item, e salva uma linha por
    recorte (item, letra/dígito do recorte, probabilidade bruta) em
    PROBABILIDADES_TESTE_CSV_PATH -- pré-requisito para a calibração de
    margem por varredura (seção 5 do documento de metodologia).
    """
    itens = montar_itens_teste()

    device = obter_device()
    modelo = carregar_modelo(device)

    linhas_csv = []
    for item in itens:
        for caminho, rotulo_recorte in item["crops"]:
            prob = inferir_probabilidade_recorte(modelo, device, caminho)
            linhas_csv.append({
                "item": item["rotulo"],
                "recorte": rotulo_recorte,
                "probabilidade": prob,
            })

    PROBABILIDADES_TESTE_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PROBABILIDADES_TESTE_CSV_PATH, "w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=["item", "recorte", "probabilidade"])
        escritor.writeheader()
        escritor.writerows(linhas_csv)

    print(f"{len(linhas_csv)} probabilidade(s) salva(s) em '{PROBABILIDADES_TESTE_CSV_PATH}'.")


if __name__ == "__main__":
    inferir_probabilidades_teste()
