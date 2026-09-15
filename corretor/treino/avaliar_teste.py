from pathlib import Path

import matplotlib.pyplot as plt
import torch

from corretor.config import CNN_BOLHAS_PATH, EXEMPLO_PREDICOES_PATH
from corretor.treino.dataset_e_dataloaders import preparar_dataloaders
from corretor.rede.arquitetura_da_rede import CNNBin


def avaliar_teste(modelo, test_loader, device):
    modelo.eval()
    correct_test = 0
    total_test = 0

    with torch.no_grad():
        for images, labels in test_loader:
            images = images.to(device)
            labels = labels.to(device).float().unsqueeze(1)
            outputs = modelo(images)
            preds = (outputs > 0.5).float()
            correct_test += (preds == labels).sum().item()
            total_test += labels.size(0)

    acc = (correct_test / total_test) * 100
    print(f"\nAcurácia Geral no conjunto de TESTE: {acc:.2f}% ({correct_test}/{total_test})")


def visualizar_amostras(modelo, test_loader, device, class_names):
    modelo.eval()
    dataiter = iter(test_loader)
    images, labels = next(dataiter)

    images_device = images.to(device)

    with torch.no_grad():
        outputs = modelo(images_device)
        preds = (outputs > 0.5).float().cpu()

    fig = plt.figure(figsize=(12, 6))
    qtd_exibir = min(10, len(images))

    for idx in range(qtd_exibir):
        ax = fig.add_subplot(2, 5, idx + 1, xticks=[], yticks=[])

        img = images[idx].squeeze().numpy()
        plt.imshow(img, cmap="gray")

        label_real = class_names[int(labels[idx].item())]
        label_pred = class_names[int(preds[idx].item())]

        cor = "green" if label_real == label_pred else "red"
        ax.set_title(f"Real: {label_real}\nPred: {label_pred}", color=cor, fontsize=10)

    plt.tight_layout()
    plt.savefig(EXEMPLO_PREDICOES_PATH, dpi=300)
    print(f"Imagem salva em '{EXEMPLO_PREDICOES_PATH}'.")
    plt.show()


def main():
    if not CNN_BOLHAS_PATH.exists():
        print(f"Arquivo '{CNN_BOLHAS_PATH}' não encontrado. Treine a rede primeiro.")
        return

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    _, _, test_loader, class_names = preparar_dataloaders()

    modelo = CNNBin().to(device)
    modelo.load_state_dict(torch.load(CNN_BOLHAS_PATH, map_location=device, weights_only=True))

    avaliar_teste(modelo, test_loader, device)
    visualizar_amostras(modelo, test_loader, device, class_names)


if __name__ == "__main__":
    main()
