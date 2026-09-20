"""
Exemplo de config_local.py -- copie este arquivo para
corretor/config_local.py (sem o .exemplo) e preencha com os caminhos da
sua máquina. config_local.py está no .gitignore e nunca será versionado;
tudo aqui embaixo são caminhos fictícios, só pra mostrar o formato.
"""
from pathlib import Path

DATASET_NOVO_SIMULADO = Path("/caminho/para/simulado1")
DATASET_NOVO_SIMULADO_EXTRA = Path("/caminho/para/simulado2")
DATASET_NOVO_CORREDORES_DIR = {
    "C1": Path("/caminho/para/C1"),
    "C2": Path("/caminho/para/C2"),
    "E1": Path("/caminho/para/E1"),
    "E2": Path("/caminho/para/E2"),
    "G1": Path("/caminho/para/G1"),
    "G2": Path("/caminho/para/G2"),
}
