import csv # csv import might still be needed for other dependencies in DictWriter types, but DictWriter isn't needed here. Removed.
from collections import defaultdict
from pathlib import Path

# REMOVED RESULTADOS_CSV_PATH from import
from corretor.config import SIMULADOS_DIR, NUM_QUESTOES 
from corretor.inferencia.inferir_inscricao import inferir_inscricoes
from corretor.inferencia.inferir_simulado import inferir_simulados

def gerar_planilha_unificada():
    # 1. Obter os dados de inscrição
    dados_inscricao = inferir_inscricoes(exportar_csv=False) 

    # 2. Obter as respostas das questões
    dados_respostas = inferir_simulados(exportar_csv=False)

    # 3. Consolidar os dados
    linhas = []
    # Pegamos todos os simulados encontrados em qualquer um dos passos
    todos_simulados = set(dados_inscricao.keys()).union(set(dados_respostas.keys()))

    for simulado in sorted(todos_simulados):
        # Pega a inscrição (ou 'NAO_LIDO' se falhou)
        inscricao = dados_inscricao.get(simulado, "NAO_LIDO")
        
        # Pega a lista de respostas (ou lista vazia se falhou)
        respostas = dados_respostas.get(simulado, [])

        # TRAVA DE SEGURANÇA: Completa com "EM BRANCO"
        while len(respostas) < NUM_QUESTOES:
            respostas.append("EM BRANCO")
            
        # TRAVA DE SEGURANÇA 2: Corta se por acaso vierem mais respostas
        respostas = respostas[:NUM_QUESTOES]

        # --- LÓGICA DO LINK DE REVISÃO ---
        tem_erro = ("?" in inscricao) or ("NAO_LIDO" in inscricao) or ("EM BRANCO" in respostas) or ("NULA(MARCADAS>1)" in respostas)
        
        if tem_erro:
            # Cria um link que pesquisa automaticamente o nome do arquivo no seu Drive
            url_drive = f"https://drive.google.com/drive/search?q={simulado}.tiff"
            link_revisao = f'=HYPERLINK("{url_drive}"; "Ver Cartão")'
        else:
            link_revisao = ""
        # ---------------------------------

        linha = {
            "Simulado": simulado,
            "Inscricao": inscricao,
            "Link_Revisao": link_revisao
        }
        
        # Adiciona as questões (Q1, Q2, etc.) dinamicamente até NUM_QUESTOES
        for idx, resposta in enumerate(respostas):
            linha[f"Q{idx+1}"] = resposta
            
        linhas.append(linha)

    # 4. REMOVED SAVING TO CSV. Only consolidate data in memory.
    if not linhas:
        print("Nenhum dado consolidate.")
        return []
        
    print(f"Dados brutos consolidados em memória ({len(linhas)} simulados).")
    
    # RETORNO IMPORTANTE: O próximo script do Excel vai consumir essa lista!
    return linhas

if __name__ == "__main__":
    # Running this directly now won't save a file, just test memory creation
    data = gerar_planilha_unificada()
    print(f"Retornadas {len(data)} linhas em memória.")