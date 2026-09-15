import os
from pathlib import Path

import torch
from torch.utils.data import DataLoader, random_split
from torchvision import datasets, transforms

from corretor.config import DATASET_TREINO_DIR


def preparar_dataloaders(pasta_dataset=None, batch_size=32):
    """
    Carrega as imagens, aplica transformações e divide em Treino, Validação e Teste.
    """
    if pasta_dataset is None:
        pasta_dataset = str(DATASET_TREINO_DIR)

    if not os.path.exists(pasta_dataset):
        raise FileNotFoundError(f"A pasta '{pasta_dataset}' não foi encontrada.")

    transformacoes = transforms.Compose([
        transforms.Grayscale(num_output_channels=1),
        transforms.Resize((32, 32)),
        transforms.ToTensor()
    ])

    dataset_completo = datasets.ImageFolder(root=pasta_dataset, transform=transformacoes)
    class_names = dataset_completo.classes
    total_imgs = len(dataset_completo)

    if total_imgs == 0:
        raise ValueError("Nenhuma imagem encontrada nas subpastas.")

    train_size = int(0.70 * total_imgs)
    val_size = int(0.15 * total_imgs)
    test_size = total_imgs - train_size - val_size

    train_dataset, val_dataset, test_dataset = random_split(
        dataset_completo, [train_size, val_size, test_size],
        generator=torch.Generator().manual_seed(42)
    )

    print(f"Dataset: {train_size} Treino | {val_size} Validação | {test_size} Teste")

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)

    return train_loader, val_loader, test_loader, class_names
