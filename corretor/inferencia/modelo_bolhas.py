"""Utilitários compartilhados para inferência de bolhas com CNNBin."""
from pathlib import Path
from PIL import Image
import torch
import torchvision.transforms as transforms

from corretor.config import CNN_BOLHAS_PATH
from corretor.rede.arquitetura_da_rede import CNNBin

_TRANSFORM = transforms.Compose([
    transforms.Grayscale(),
    transforms.Resize((32, 32)),
    transforms.ToTensor(),
])

def obter_device():
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")

def carregar_modelo(device=None):
    if device is None:
        device = obter_device()
    if not CNN_BOLHAS_PATH.exists():
        raise FileNotFoundError(
            f"Modelo não encontrado em '{CNN_BOLHAS_PATH}'. "
            "Coloque cnn_bolhas.pth em models/ ou treine a rede."
        )
    modelo = CNNBin().to(device)
    modelo.load_state_dict(torch.load(CNN_BOLHAS_PATH, map_location=device, weights_only=True))
    modelo.eval()
    return modelo

def preprocessar(caminho_img):
    try:
        img = Image.open(caminho_img)
        return _TRANSFORM(img)
    except Exception:
        return None

def prob_bolha_preenchida(modelo, caminho, device):
    """
    Retorna (probabilidade, leitura_ok).

    leitura_ok=False sinaliza que o PNG não abriu (item 4 do plano): quem
    chama decide o que fazer com isso, mas antes essa falha ficava só no
    valor 1.0 assumido, sem nenhum rastro de que aconteceu.
    """
    tensor = preprocessar(caminho)
    if tensor is None:
        return 1.0, False  # Assume vazia (1.0) para não anular a questão, mas marca a falha
    with torch.no_grad():
        out = modelo(tensor.unsqueeze(0).to(device))
        return out.item(), True