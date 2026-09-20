import torch
import torch.nn as nn

class CNNBin(nn.Module):
    def __init__(self):
        super().__init__()

        # Bloco 1: Extração de características visuais
        self.features = nn.Sequential(
            nn.Conv2d(1, 6, kernel_size=5),  # 32x32 → 28x28
            nn.ReLU(),
            nn.MaxPool2d(2, 2),              # → 14x14

            nn.Conv2d(6, 14, kernel_size=5), # 14x14 → 10x10
            nn.ReLU(),
            nn.MaxPool2d(2, 2)               # 10x10 → 5x5
        )

        # Bloco 2: Decisão (Vazia ou Preenchida)
        # Dropout(0.3) antes do Linear: item do plano, combate overfitting no
        # dataset novo -- só atua durante .train(), .eval() desliga sozinho.
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(p=0.3),
            nn.Linear(14 * 5 * 5, 1),
            nn.Sigmoid()
        )

    def forward(self, x):
        x = self.features(x)
        x = self.classifier(x)
        return x


class CNNBinSemDropout(nn.Module):
    """
    Réplica de CNNBin na arquitetura de ANTES do item de regularização
    deste plano (sem nn.Dropout no classifier) -- existe só para o Teste B
    conseguir carregar cnn_bolhas_old.pth, cujo state_dict foi salvo com
    essa estrutura antiga (Linear na posição classifier.1, não classifier.2).
    Produção nunca usa esta classe -- carregar_modelo() em modelo_bolhas.py
    continua usando CNNBin normalmente.
    """
    def __init__(self):
        super().__init__()

        self.features = nn.Sequential(
            nn.Conv2d(1, 6, kernel_size=5),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),

            nn.Conv2d(6, 14, kernel_size=5),
            nn.ReLU(),
            nn.MaxPool2d(2, 2)
        )

        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(14 * 5 * 5, 1),
            nn.Sigmoid()
        )

    def forward(self, x):
        x = self.features(x)
        x = self.classifier(x)
        return x
