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

# Item 17 do plano de alterações: treinar.py NUNCA escreve em CNN_BOLHAS_PATH
# (o peso em produção, usado pela inferência de verdade) -- salva aqui, num
# arquivo separado. Promover para produção é uma ação manual (copiar este
# arquivo por cima de CNN_BOLHAS_PATH), só depois de validar o resultado do
# treino novo, inclusive no Teste B (corredor G2, nunca visto no treino).
CNN_BOLHAS_CANDIDATO_PATH = PESOS_DIR / "cnn_bolhas_candidato.pth"

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
# DATASET NOVO (item 7, seção 7.0) -- caminhos de origem das folhas para
# a amostragem de treino. Cada pessoa aponta os próprios caminhos em
# config_local.py; sem ele, ficam None, e sortear_amostra.py avisa que
# faltou configurar em vez de tentar rodar com caminho errado.
# =====================================================================
DATASET_NOVO_SIMULADO = None
DATASET_NOVO_SIMULADO_EXTRA = None
DATASET_NOVO_CORREDORES_DIR = {}
AMOSTRA_SORTEADA_CSV_PATH = OUTPUTS_DIR / "amostra_sorteada.csv"

# gerar_planilha_anotacao.py lê AMOSTRA_SORTEADA_CSV_PATH acima e escreve
# aqui a planilha pronta para o anotador preencher (mesmo papel que
# PLANILHA_REVISAO_PATH tem para o fluxo de revisão de notas).
PLANILHA_ANOTACAO_PATH = OUTPUTS_DIR / "planilha_anotacao.xlsx"

# Documento de metodologia (docs/metodologia_teste_acuracia_bolhas.md):
# sortear_amostra_teste.py grava aqui a amostra sorteada do POOL DE TESTE
# isolado (Teste A + Teste B), separada de AMOSTRA_SORTEADA_CSV_PATH acima
# (que é a amostra do TREINO) -- os dois nunca podem ser o mesmo arquivo,
# ou um sorteio sobrescreve o outro.
AMOSTRA_TESTE_CSV_PATH = OUTPUTS_DIR / "amostra_teste.csv"

# =====================================================================
# LIMIAR DE DETECCAO DE MARCADOR, INDEPENDENTE DE DPI (achado de
# 23/09/2026) -- AREA_MINIMA_MARCADOR era um numero fixo de pixels,
# calibrado so a 300 dpi (2480x3508 px; ver "Correcoes fora do plano" no
# plano de alteracoes). Um lote escaneado a 200 dpi teve as 144 folhas
# descartadas: a 200 dpi a mesma marca fisica cobre somente ~44% da area em
# pixels, caindo abaixo do limiar. Expressa como fracao da area total da
# imagem (nao pixels absolutos), a mesma calibracao vale em qualquer
# resolucao do scanner (100/200/300/400/600 dpi), porque area em pixels e
# area total da imagem escalam juntas com o quadrado do DPI.
# =====================================================================
AREA_MINIMA_MARCADOR_FRACAO = 5000 / (2480 * 3508)

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
            "AREA_MINIMA_MARCADOR_FRACAO": AREA_MINIMA_MARCADOR_FRACAO,
            "MARGEM_FRACAO": 0.20,         # Janela de busca de 30% nas bordas
            # Faixa cortada de cada lado da imagem ANTES de procurar
            # marcador, pra borrao/mancha bem na borda da folha nem entrar
            # como candidato. Bem menor que MARGEM_FRACAO -- so remove a
            # faixa mais externa, nunca chega perto de onde o marcador real
            # fica.
            "MARGEM_CORTE_BORDA_FRACAO": 0.01,
        },
        # Coordenadas medidas diretamente em gabaritos reais (3 lotes
        # escaneados do CASDINHO + a mesma medicao no SEMI, que usa a
        # identica grade fisica). passo_x/passo_y sao float -- o recorte
        # arredonda cada borda individualmente (round()) em vez de truncar
        # um passo inteiro reaproveitado em todas as linhas/colunas. Isso
        # evita o erro que se acumulava ao longo de 16 linhas (chegava a
        # ~20px de desvio na questao 16/32/48 de cada bloco) e produzia os
        # recortes em formato de meia-lua reportados na planilha de revisao.
        "GRADE_RESPOSTAS": {
            "y_questoes_ini": 671.9,
            "passo_y": 26.56,
            "blocos": [
                {"x_ini": 13.2, "passo_x": 25.61, "linhas": 16},
                {"x_ini": 181.5, "passo_x": 25.52, "linhas": 16},
                {"x_ini": 349.5, "passo_x": 25.53, "linhas": 16},
                {"x_ini": 517.5, "passo_x": 25.73, "linhas": 2},
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
            "AREA_MINIMA_MARCADOR_FRACAO": AREA_MINIMA_MARCADOR_FRACAO,
            "MARGEM_FRACAO": 0.22,         # Janela mais ampla para evitar perda de cantos
            "MARGEM_CORTE_BORDA_FRACAO": 0.01,
        },
        # Mesma grade fisica do CASDINHO (confirmado medindo os 2 lotes
        # CASDINHO reais + o compilado de gabaritos SEMI: os centros de
        # bolha caem nos mesmos pixels em ambas as provas). So o ultimo
        # bloco muda, com 12 linhas (questoes 49-60) em vez de 2.
        "GRADE_RESPOSTAS": {
            "y_questoes_ini": 671.9,
            "passo_y": 26.56,
            "blocos": [
                {"x_ini": 13.2, "passo_x": 25.61, "linhas": 16},
                {"x_ini": 181.5, "passo_x": 25.52, "linhas": 16},
                {"x_ini": 349.5, "passo_x": 25.53, "linhas": 16},
                {"x_ini": 517.5, "passo_x": 25.73, "linhas": 12},
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

# Coordenadas medidas diretamente em gabaritos reais (2 lotes CASDINHO +
# o compilado SEMI -- a grade de inscricao e identica nas duas provas).
# passo_x/passo_y sao float; extrair_bolhas_inscricao arredonda cada
# borda (round()) em vez de truncar um passo inteiro fixo.
GRADE_INSCRICAO = {
    "x_ini": 583.6,
    "passo_x": 28.14,
    "y_ini": 74.3,
    "passo_y": 29.18,
    "qtd_colunas": 7,
    "qtd_linhas": 10,
}

for pasta in [ENTRADA_DIR, OUTPUTS_DIR, RECORTES_BOLHAS_DIR, RECORTES_INSCRICAO_DIR, PESOS_DIR, SIMULADOS_DIR]:
    try:
        if not pasta.exists():
            pasta.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

# =====================================================================
# CONFIG LOCAL (item 2.1 do plano) -- sobrepõe caminhos pessoais sem
# versionar nada sensível. config_local.py fica no .gitignore; sem ele,
# o projeto roda inteiro com os padrões acima.
# =====================================================================
try:
    from corretor.config_local import *  # noqa: F401,F403
except ImportError:
    pass
