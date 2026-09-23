"""
Lê a planilha de anotação (gerar_planilha_anotacao.py) depois que o revisor
preencheu a coluna 'Marcada', e copia os recortes físicos para
DATASET_TREINO_DIR/preenchida/ ou DATASET_TREINO_DIR/vazia/, seguindo a
estrutura que ImageFolder espera (ver dataset_e_dataloaders.py) -- item 7 do
plano (retreinamento com dataset mais robusto).
"""
from pathlib import Path
import shutil

import openpyxl

from corretor.config import AMOSTRA_SORTEADA_CSV_PATH, DATASET_TREINO_DIR, PLANILHA_ANOTACAO_PATH
from corretor.revisao.gerar_planilha_anotacao import ler_amostra, _montar_itens


def ler_planilha_anotada(caminho_planilha: Path) -> list[dict]:
    """
    Lê a planilha de anotação (gerar_planilha_anotacao) depois que o
    anotador preencheu a coluna 'Marcada', e devolve uma linha por item
    (Item, Marcada) -- ignorando a coluna de imagem, que não é lida de
    volta (as imagens só existem pra o anotador ver, não carregam dado).
    """
    wb = openpyxl.load_workbook(caminho_planilha, data_only=True)
    ws = wb["Anotação"]
    itens = []
    for linha in ws.iter_rows(min_row=2, values_only=True):
        rotulo, marcada = linha[0], linha[1]
        if not rotulo:
            continue
        itens.append({"rotulo": rotulo, "marcada": str(marcada).strip() if marcada else ""})
    return itens


def decidir_destinos(item: dict) -> dict:
    """
    A partir de um item anotado ('rotulo', 'marcada') e do item original
    (com 'crops', a lista de (caminho, letra/dígito) que gerou a tira),
    decide o destino de cada recorte individual: o que bate com o valor
    anotado vai para preenchida/, os outros 4 (ou 9) vão para vazia/ --
    reflete a estrutura DATASET_TREINO_DIR/<classe>/imagem.png que
    ImageFolder espera (ver dataset_e_dataloaders.py).

    Anotações "BRANCO" ou vazias marcam a questão inteira como sem bolha
    marcada: todos os recortes daquele item vão para vazia/, nenhum para
    preenchida/.

    Anotações "MULT" marcam dupla marcação (ou outra ambiguidade): o item
    inteiro é pulado, sem nenhum destino gerado -- nem preenchida/ nem
    vazia/ -- porque não dá pra saber, só pela planilha, qual das bolhas
    marcadas é a "extra" indevida. Incluir qualquer uma delas em vazia/
    ensinaria o modelo, errado, que uma bolha preenchida é vazia.
    """
    if item["marcada"] == "MULT":
        return {}

    destinos = {}
    for caminho, rotulo_recorte in item["crops"]:
        if item["marcada"] and rotulo_recorte == item["marcada"]:
            classe = "preenchida"
        else:
            classe = "vazia"
        destinos[caminho] = DATASET_TREINO_DIR / classe / caminho.name
    return destinos


def aplicar_anotacao(caminho_planilha_anotada, caminho_csv_amostra):
    """
    Ponto de entrada: lê a planilha já anotada, reconstrói os itens
    originais (mesmos 'rotulo' de gerar_planilha_anotacao, a partir do CSV
    de amostra) para recuperar os 'crops' de cada um, casa cada item
    anotado com seu 'crops' pelo rótulo, decide os destinos e copia os
    arquivos físicos para DATASET_TREINO_DIR/<classe>/.
    """
    anotados = ler_planilha_anotada(caminho_planilha_anotada)
    linhas = ler_amostra(caminho_csv_amostra)
    itens_originais = _montar_itens(linhas)

    crops_por_rotulo = {item["rotulo"]: item["crops"] for item in itens_originais}

    total_copiados = 0
    for anotado in anotados:
        crops = crops_por_rotulo[anotado["rotulo"]]
        item = {"marcada": anotado["marcada"], "crops": crops}
        destinos = decidir_destinos(item)

        for origem, destino in destinos.items():
            destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(origem, destino)
            total_copiados += 1

    print(f"{total_copiados} recortes copiados para {DATASET_TREINO_DIR}")


if __name__ == "__main__":
    aplicar_anotacao(PLANILHA_ANOTACAO_PATH, AMOSTRA_SORTEADA_CSV_PATH)
