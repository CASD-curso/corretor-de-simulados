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
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(14 * 5 * 5, 1),
            nn.Sigmoid()
        )

    def forward(self, x):
        x = self.features(x)
        x = self.classifier(x)
        return x
