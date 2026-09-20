import json
from pathlib import Path

import torch
import torch.nn as nn
import torch.optim as optim

from corretor.config import CNN_BOLHAS_CANDIDATO_PATH, HISTORICO_TREINO_PATH
from corretor.treino.dataset_e_dataloaders import preparar_dataloaders
from corretor.rede.arquitetura_da_rede import CNNBin


def main():
    num_epochs = 15
    learning_rate = 0.001
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Treinando em: {device}")

    train_loader, val_loader, _, _ = preparar_dataloaders()

    modelo = CNNBin().to(device)
    criterion = nn.BCELoss()
    # weight_decay: regularização L2, item do plano, junto com o Dropout em
    # CNNBin combate overfitting no dataset novo (dropout ataca dependência
    # de neurônios específicos; weight_decay ataca pesos individuais grandes).
    optimizer = optim.Adam(modelo.parameters(), lr=learning_rate, weight_decay=1e-4)

    historico = {"train_loss": [], "train_acc": [], "val_loss": [], "val_acc": []}

    print("\nIniciando o treinamento...")
    for epoch in range(num_epochs):
        modelo.train()
        running_loss = 0.0
        correct_train = 0
        total_train = 0

        for images, labels in train_loader:
            images = images.to(device)
            labels = labels.to(device).float().unsqueeze(1)

            optimizer.zero_grad()
            outputs = modelo(images)
            loss = criterion(outputs, labels)

            loss.backward()
            optimizer.step()

            running_loss += loss.item() * images.size(0)
            preds = (outputs > 0.5).float()
            correct_train += (preds == labels).sum().item()
            total_train += labels.size(0)

        epoch_train_loss = running_loss / total_train
        epoch_train_acc = (correct_train / total_train) * 100

        modelo.eval()
        running_val_loss = 0.0
        correct_val = 0
        total_val = 0

        with torch.no_grad():
            for images, labels in val_loader:
                images = images.to(device)
                labels = labels.to(device).float().unsqueeze(1)

                outputs = modelo(images)
                loss = criterion(outputs, labels)

                running_val_loss += loss.item() * images.size(0)
                preds = (outputs > 0.5).float()
                correct_val += (preds == labels).sum().item()
                total_val += labels.size(0)

        epoch_val_loss = running_val_loss / total_val
        epoch_val_acc = (correct_val / total_val) * 100

        historico["train_loss"].append(epoch_train_loss)
        historico["train_acc"].append(epoch_train_acc)
        historico["val_loss"].append(epoch_val_loss)
        historico["val_acc"].append(epoch_val_acc)

        print(
            f"Época [{epoch + 1}/{num_epochs}] | "
            f"Treino Loss: {epoch_train_loss:.4f} Acc: {epoch_train_acc:.2f}% | "
            f"Val Loss: {epoch_val_loss:.4f} Acc: {epoch_val_acc:.2f}%"
        )

    # Item 17 do plano: nunca escreve direto em CNN_BOLHAS_PATH (produção).
    # Salva num arquivo candidato -- promover para produção é manual, feito
    # só depois de validar o resultado (inclusive no Teste B).
    torch.save(modelo.state_dict(), CNN_BOLHAS_CANDIDATO_PATH)
    print(f"\nTreinamento concluído! Pesos candidatos salvos em '{CNN_BOLHAS_CANDIDATO_PATH}'.")
    print("Produção NÃO foi alterada. Valide o candidato antes de promovê-lo manualmente.")

    with open(HISTORICO_TREINO_PATH, "w") as f:
        json.dump(historico, f)
    print(f"Histórico salvo em '{HISTORICO_TREINO_PATH}'.")


if __name__ == "__main__":
    main()
