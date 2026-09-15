import json
from pathlib import Path

import matplotlib.pyplot as plt

from corretor.config import GRAFICO_TREINAMENTO_PATH, HISTORICO_TREINO_PATH


def plotar():
    if not HISTORICO_TREINO_PATH.exists():
        print(f"Arquivo '{HISTORICO_TREINO_PATH}' não encontrado. Treine a rede primeiro.")
        return

    with open(HISTORICO_TREINO_PATH, "r") as f:
        historico = json.load(f)

    epochs = range(1, len(historico["train_loss"]) + 1)

    plt.figure(figsize=(12, 5))

    plt.subplot(1, 2, 1)
    plt.plot(epochs, historico["train_loss"], label="Treino Loss", marker="o")
    plt.plot(epochs, historico["val_loss"], label="Validação Loss", marker="o")
    plt.title("Evolução do Erro (Loss)")
    plt.xlabel("Épocas")
    plt.ylabel("BCE Loss")
    plt.legend()
    plt.grid(True)

    plt.subplot(1, 2, 2)
    plt.plot(epochs, historico["train_acc"], label="Treino Acurácia", marker="o")
    plt.plot(epochs, historico["val_acc"], label="Validação Acurácia", marker="o")
    plt.title("Evolução da Acurácia")
    plt.xlabel("Épocas")
    plt.ylabel("Acurácia (%)")
    plt.legend()
    plt.grid(True)

    plt.tight_layout()
    plt.savefig(GRAFICO_TREINAMENTO_PATH, dpi=300)
    print(f"Gráfico salvo em '{GRAFICO_TREINAMENTO_PATH}'.")
    plt.show()


if __name__ == "__main__":
    plotar()
