import pandas as pd
import numpy as np
from pathlib import Path

from corretor.config import OUTPUTS_DIR, LOCAL_DIR, ESTRUTURA_MATERIAS, NUM_QUESTOES, NOME_SIMULADO, SIMULADO_ATIVO
from corretor.inferencia.inferir_completo import gerar_planilha_unificada

def gerar_excel_final(dados_brutos=None):
    """
    dados_brutos: quando informado (lista de dicts), é o resultado de
    aplicar_revisao() — a leitura já corrigida pelo operador (item 5).
    Quando None, calcula direto da leitura automática do modelo, sem passar
    por nenhuma revisão — é o caminho de quem não teve nada pra corrigir.
    """
    if dados_brutos is None:
        print("Obtendo dados de leitura das imagens...")
        dados_brutos, _, _, _ = gerar_planilha_unificada()

    if not dados_brutos:
        print("Nenhum dado processado para gerar o Excel.")
        return
        
    df_bruto = pd.DataFrame(dados_brutos)
    
    # Garante que as colunas '1' a '50' sejam tratadas como strings
    cols_questoes = [str(i) for i in range(1, NUM_QUESTOES + 1)]
    # Apenas para debug, vamos ver o que o dataframe tem
    print("Colunas encontradas:", df_bruto.columns.tolist()) 
    # ----------------------------------
    
    # 1. Ler o Gabarito Oficial salvo
    caminho_gabarito = LOCAL_DIR / 'gabarito_atual.txt'
    if not caminho_gabarito.exists():
        print("ERRO: Arquivo 'gabarito_atual.txt' não encontrado. Rode a célula de gabarito no Colab primeiro.")
        return
        
    with open(caminho_gabarito, 'r') as f:
        gabarito_oficial = f.read().strip()
        
    # 2. Avaliação de Acertos Básicos
    df_acertos = pd.DataFrame()
    df_acertos['Inscricao'] = df_bruto['Inscricao']
    
    for i in range(1, NUM_QUESTOES + 1):
        col_q = f'Q{i}'
        # Mantém apenas letras, removendo espaços e pontuações
        resposta_limpa = df_bruto[col_q].astype(str).str.upper().str.replace(r"[^A-Z]", "", regex=True)
        # Aceita apenas se for estritamente A, B, C, D ou E
        resposta_aluno = resposta_limpa.where(resposta_limpa.isin(['A', 'B', 'C', 'D', 'E']), "")
        
        resposta_correta = gabarito_oficial[i-1].strip().upper()
        
        if resposta_correta == 'X':
            df_acertos[col_q] = 1
        else:
            df_acertos[col_q] = (resposta_aluno == resposta_correta).astype(int)
        
    # 3. Estatísticas por Aluno
    df_estatisticas = pd.DataFrame()
    df_estatisticas['Inscricao'] = df_bruto['Inscricao']
    
    # Calcula acertos por matéria
    for materia, limites in ESTRUTURA_MATERIAS.items():
        cols_materia = [f'Q{i}' for i in range(limites['inicio'], limites['fim'] + 1)]
        df_estatisticas[materia] = df_acertos[cols_materia].sum(axis=1)

    # Base para o cálculo da média final
    if SIMULADO_ATIVO == "CASDINHO":
        materias_base = ["Portugues", "Matematica", "CH", "CN"]
    else:
        materias_base = list(ESTRUTURA_MATERIAS.keys())

    df_estatisticas['Acertos_Totais'] = df_estatisticas[materias_base].sum(axis=1)
    
    # Multiplicador dinâmico
    multiplicador = 2 if NUM_QUESTOES == 50 else (100 / 60)
    df_estatisticas['Nota Final'] = df_estatisticas['Acertos_Totais'] * multiplicador
    
    # 4. Relatório Sintético dos Testes
    relatorio = []
    notas = df_estatisticas['Acertos_Totais']
    
    # Define grupos de 27% aceitando empates no limite
    limite_sup = np.percentile(notas, 100 - 27)
    limite_inf = np.percentile(notas, 27)
    
    df_sup = df_acertos[notas >= limite_sup]
    df_inf = df_acertos[notas <= limite_inf]
    
    for i in range(1, NUM_QUESTOES + 1):
        col_q = f'Q{i}'
        resp_correta = gabarito_oficial[i-1]
        
        # Frequência da resposta ignorando textos longos, nulos e duplas marcações
        resposta_limpa = df_bruto[col_q].astype(str).str.upper().str.replace(r"[^A-Z]", "", regex=True)
        respostas_validas = resposta_limpa[resposta_limpa.isin(['A', 'B', 'C', 'D', 'E'])]
        total_validos = len(respostas_validas)
        
        freqs = {alt: 0.0 for alt in ['A', 'B', 'C', 'D', 'E']}
        if total_validos > 0:
            contagens = respostas_validas.value_counts()
            for alt in ['A', 'B', 'C', 'D', 'E']:
                freqs[alt] = contagens.get(alt, 0) / total_validos
                
        # Grupos corretas
        total_pct = df_acertos[col_q].mean() 
        sup_pct = df_sup[col_q].mean() if not df_sup.empty else 0
        inf_pct = df_inf[col_q].mean() if not df_inf.empty else 0
        
        # Ponto Bisserial
        if df_acertos[col_q].std() > 0 and notas.std() > 0:
            bisserial = df_acertos[col_q].corr(notas)
        else:
            bisserial = 0.0
            
        relatorio.append({
            'Questão': i,
            'Resposta Correta': resp_correta,
            'A': freqs['A'],
            'B': freqs['B'],
            'C': freqs['C'],
            'D': freqs['D'],
            'E': freqs['E'],
            'Total %': total_pct,
            'Superior a 27%': sup_pct,
            'Inferior a 27%': inf_pct,
            'Ponto Bisserial': bisserial
        })
        
    df_relatorio = pd.DataFrame(relatorio)
    
    # Formatação %
    cols_pct = ['A', 'B', 'C', 'D', 'E', 'Total %', 'Superior a 27%', 'Inferior a 27%']
    for c in cols_pct:
        df_relatorio[c] = df_relatorio[c].apply(lambda x: f"{x:.1%}")
    df_relatorio['Ponto Bisserial'] = df_relatorio['Ponto Bisserial'].round(3)
    
    # 5. Aba de auditoria (item 4 do plano): registro permanente das folhas
    # descartadas no alinhamento e das bolhas que falharam ao abrir. Antes
    # essas duas falhas só apareciam como print no console e se perdiam.
    colunas_auditoria = ["Simulado", "Inscricao", "Alinhamento_OK", "Motivo_Alinhamento", "Bolhas_Ilegiveis"]
    colunas_auditoria_existentes = [c for c in colunas_auditoria if c in df_bruto.columns]
    df_falhas = df_bruto[colunas_auditoria_existentes].copy()
    if "Alinhamento_OK" in df_falhas.columns and "Bolhas_Ilegiveis" in df_falhas.columns:
        df_falhas = df_falhas[
            (df_falhas["Alinhamento_OK"] == "Não") | (df_falhas["Bolhas_Ilegiveis"] != "")
        ]

    # 6. Exportação
    if 'Caminho_Imagem' in df_bruto.columns:
        df_bruto['Link_Imagem'] = df_bruto['Caminho_Imagem'].apply(lambda x: f'=HYPERLINK("{x}", "Ver Scan")')
        df_bruto = df_bruto.drop(columns=['Caminho_Imagem'])

    nome_arquivo = f"{NOME_SIMULADO}.xlsx"
    caminho_saida = OUTPUTS_DIR / nome_arquivo

    with pd.ExcelWriter(caminho_saida, engine='xlsxwriter') as writer:
        df_bruto.to_excel(writer, sheet_name='Resultados Brutos', index=False)
        df_estatisticas.to_excel(writer, sheet_name='Estatísticas por Aluno', index=False)
        df_relatorio.to_excel(writer, sheet_name='Relatório Sintético dos Testes', index=False)
        df_falhas.to_excel(writer, sheet_name='Falhas de Leitura', index=False)

    if len(df_falhas) > 0:
        print(f"AVISO: {len(df_falhas)} simulado(s) com falha de leitura — ver aba 'Falhas de Leitura'.")
    print(f"✓ Excel gerado com sucesso: {caminho_saida}")

if __name__ == "__main__":
    gerar_excel_final()