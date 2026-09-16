"""Caminhos centralizados do projeto."""
import os
from pathlib import Path

# ROOT = raiz do repositorio (uma pasta acima de corretor/)
ROOT = Path(__file__).resolve().parent.parent

# =====================================================================
# CAMINHOS LOCAIS (SSD DO COLAB OU PC)
# =====================================================================
# data/entrada e o unico lugar onde o usuario poe os .tif, nos dois modos.
ENTRADA_DIR = ROOT / "data" / "entrada"

if os.path.exists('/content'):
    # Colab: trabalha no SSD local. Ler do Drive montado e ordens de grandeza
    # mais lento, por isso os .tif sao copiados para ca antes de processar.
    LOCAL_DIR = Path("/content/dados_locais")
    SIMULADOS_DIR = LOCAL_DIR / "originais"
else:
    # Modo local: nao precisa copiar, le direto de data/entrada.
    LOCAL_DIR = ROOT / "data"
    SIMULADOS_DIR = ENTRADA_DIR
RECORTES_DIR = LOCAL_DIR / "recortes"
RECORTES_BOLHAS_DIR = RECORTES_DIR / "bolhas_respostas"
RECORTES_INSCRICAO_DIR = RECORTES_DIR / "bolhas_inscricao"
OUTPUTS_DIR = LOCAL_DIR / "outputs"

DATASET_TREINO_DIR = ROOT / "dataset"   # versionado: crops de bolha, sem dado pessoal

PESOS_DIR = ROOT / "pesos"              # versionado: 13 KB
CNN_BOLHAS_PATH = PESOS_DIR / "cnn_bolhas.pth"

HISTORICO_TREINO_PATH = OUTPUTS_DIR / "historico_treino.json"
GRAFICO_TREINAMENTO_PATH = OUTPUTS_DIR / "grafico_treinamento.png"
EXEMPLO_PREDICOES_PATH = OUTPUTS_DIR / "exemplo_predicoes.png"
RESULTADOS_CSV_PATH = OUTPUTS_DIR / "resultados_simulado.csv"
INSCRICOES_CSV_PATH = OUTPUTS_DIR / "inscricoes.csv"
# Item 4 do plano de alterações: registro das folhas descartadas na etapa de
# alinhamento (menos de 3 cantos encontrados, arquivo corrompido etc.). A
# extração grava aqui; gerar_planilha_unificada lê daqui para que a folha
# apareça no resultado final em vez de simplesmente desaparecer.
FALHAS_ALINHAMENTO_PATH = OUTPUTS_DIR / "falhas_alinhamento.json"

# Item 5 do plano de alterações: checkpoint de revisão manual, entre a
# inferência e o cálculo de nota. gerar_planilha_revisao() escreve aqui;
# aplicar_revisao() lê a versão que o operador baixou, revisou e subiu de
# volta.
PLANILHA_REVISAO_PATH = OUTPUTS_DIR / "planilha_revisao.xlsx"

# =====================================================================
# DICIONÁRIO DINÂMICO DE SIMULADOS
# =====================================================================
CONFIG_SIMULADOS = {
    "CASDINHO": {
        "NUM_QUESTOES": 50,
        "MATERIAS": {
            "Portugues": {"inicio": 1, "fim": 15},
            "Historia": {"inicio": 16, "fim": 20},
            "Geografia": {"inicio": 21, "fim": 25},
            "CH": {"inicio": 16, "fim": 25},
            "Matematica": {"inicio": 26, "fim": 40},
            "Biologia": {"inicio": 41, "fim": 45},
            "Quimica": {"inicio": 46, "fim": 50},
            "CN": {"inicio": 41, "fim": 50}
        },
        "ALINHAMENTO": {
            "AREA_MINIMA_MARCADOR": 5000,
            "MARGEM_FRACAO": 0.20          # Janela de busca de 30% nas bordas
        },
        "GRADE_RESPOSTAS": {
            "altura_alinhada": 1130,
            "y_questoes_ini": 690,
            "passo_y_divisor": 16,
            "blocos": [
                {"x": (25, 155), "linhas": 16},
                {"x": (190, 320), "linhas": 16},
                {"x": (355, 485), "linhas": 16},
                {"x": (520, 650), "linhas": 2},
            ]
        }
    },
    "SEMI": {
        "NUM_QUESTOES": 60,
        "MATERIAS": {
            "Matematica": {"inicio": 1, "fim": 15},
            "CN": {"inicio": 16, "fim": 30},
            "CH": {"inicio": 31, "fim": 45},
            "Linguagens": {"inicio": 46, "fim": 60}
        },
        "ALINHAMENTO": {
            "AREA_MINIMA_MARCADOR": 5000,
            "MARGEM_FRACAO": 0.22          # Janela mais ampla para evitar perda de cantos
        },
        "GRADE_RESPOSTAS": {
            "altura_alinhada": 1130,
            "y_questoes_ini": 690,
            "passo_y_divisor": 16,
            "blocos": [
                {"x": (25, 155), "linhas": 16},
                {"x": (190, 320), "linhas": 16},
                {"x": (355, 485), "linhas": 16},
                {"x": (520, 650), "linhas": 12}, 
            ]
        }
    }
}

# =====================================================================
# SELEÇÃO DO SIMULADO ATIVO E NOME DO ARQUIVO
# =====================================================================

# Lê a escolha feita no Colab. Se não achar, usa CASDINHO como padrão.
try:
    with open(LOCAL_DIR / "simulado_ativo.txt", "r") as f:
        SIMULADO_ATIVO = f.read().strip()
except FileNotFoundError:
    SIMULADO_ATIVO = "CASDINHO" 

# Lê o nome customizado do simulado definido no Colab
try:
    with open(LOCAL_DIR / "nome_simulado.txt", "r", encoding='utf-8') as f:
        NOME_SIMULADO = f.read().strip()
        if not NOME_SIMULADO:
            NOME_SIMULADO = "Resultados_Simulado"
except FileNotFoundError:
    NOME_SIMULADO = "Resultados_Simulado"

_cfg = CONFIG_SIMULADOS[SIMULADO_ATIVO]
NUM_QUESTOES = _cfg["NUM_QUESTOES"]
GRADE_RESPOSTAS = _cfg["GRADE_RESPOSTAS"]
ESTRUTURA_MATERIAS = _cfg["MATERIAS"]

# =====================================================================
# CONFIGURAÇÕES E HIPERPARÂMETROS FIXOS
# =====================================================================
LIMIAR_MAXIMO = 0.95
LIMIAR_DUPLA = 0.60
PRE_PROC_GAMMA = 1.5          
PRE_PROC_USAR_CLAHE = False   
PRE_PROC_CLAHE_CLIP = 2.0
ADAPTIVE_THRESH_BLOCK = 11
ADAPTIVE_THRESH_C = 0         

ALTERNATIVAS = ["A", "B", "C", "D", "E"]
NUM_DIGITOS_INSCRICAO = 7
DIGITOS_INSCRICAO = list(range(10))

GRADE_INSCRICAO = {
    "x_ini": 590,
    "x_fim": 780,
    "y_ini": 78,
    "y_fim": 380,
    "qtd_colunas": 7,
    "qtd_linhas": 10,
}

for pasta in [ENTRADA_DIR, OUTPUTS_DIR, RECORTES_BOLHAS_DIR, RECORTES_INSCRICAO_DIR, PESOS_DIR, SIMULADOS_DIR]:
    try:
        if not pasta.exists():
            pasta.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass