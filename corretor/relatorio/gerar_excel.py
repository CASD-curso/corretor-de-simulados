import pandas as pd
import numpy as np
from pathlib import Path

from corretor.config import OUTPUTS_DIR, LOCAL_DIR, ESTRUTURA_MATERIAS, NUM_QUESTOES, NOME_SIMULADO, SIMULADO_ATIVO
from corretor.inferencia.inferir_completo import gerar_planilha_unificada

# Índice (0-idx) da última coluna que uma aba do Excel pode ter: XFD.
ULTIMA_COLUNA_EXCEL = 16383


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
    # Uma entrada por linha (mesma ordem de 'relatorio'): o conjunto de
    # letras (A-E) cujo percentual de marcação supera o da própria
    # alternativa correta daquela questão -- usado depois para pintar de
    # vermelho essas células específicas na aba "Relatório Sintético dos
    # Testes" (pedido do usuário, 23/09/2026). Precisa ser calculado aqui,
    # com os números ainda em float -- depois eles virão formatados como
    # texto ("23.0%"), e comparar strings desse jeito dá resultado errado.
    alertas_por_linha = []
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

        # Só compara quando a resposta correta é uma letra de fato (não
        # 'X' de questão anulada, onde não existe "a alternativa certa"
        # para servir de referência de comparação).
        resp_correta_norm = resp_correta.strip().upper()
        alertas = set()
        if resp_correta_norm in freqs:
            freq_correta = freqs[resp_correta_norm]
            for alt in ['A', 'B', 'C', 'D', 'E']:
                if alt != resp_correta_norm and freqs[alt] > freq_correta:
                    alertas.add(alt)
        alertas_por_linha.append(alertas)

        # Grupos corretas
        total_pct = df_acertos[col_q].mean()
        sup_pct = df_sup[col_q].mean() if not df_sup.empty else 0
        inf_pct = df_inf[col_q].mean() if not df_inf.empty else 0

        # Ponto Bisserial corrigido (item 10): correlaciona o acerto da
        # questão com a nota nas OUTRAS questões, não com o total. O total
        # inclui a própria questão, e isso inflava o índice sempre para
        # cima -- quem acertou a questão ganhava 1 ponto no total só por
        # tê-la acertado. .corr() é Pearson, que dá o mesmo valor que o
        # ponto bisserial quando uma das variáveis só vale 0 ou 1.
        nota_sem_a_questao = notas - df_acertos[col_q]
        if df_acertos[col_q].std() > 0 and nota_sem_a_questao.std() > 0:
            bisserial = df_acertos[col_q].corr(nota_sem_a_questao)
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

        # ---- Modo escuro (pedido do usuário, 23/09/2026): fundo preto e
        # texto branco em todas as abas. pandas.to_excel() só grava os
        # valores, sem formato nenhum -- por isso dá pra "pintar" a
        # coluna inteira depois, com set_column(): o xlsxwriter só aplica
        # o formato da coluna às células que ainda não têm um formato
        # próprio, então não sobrescreve nada que a gente grave explícito
        # em seguida (o cabeçalho em negrito, e o destaque vermelho).
        # Todas as colunas da aba (A até XFD, a última que o Excel
        # permite) recebem o fundo preto, não só as que têm dado -- senão
        # a área vazia em volta da tabela fica branca (26/09/2026). ----
        workbook = writer.book
        fmt_dark = workbook.add_format({"bg_color": "#000000", "font_color": "#FFFFFF"})
        fmt_dark_header = workbook.add_format({
            "bg_color": "#000000", "font_color": "#FFFFFF", "bold": True,
            "border": 1, "border_color": "#FFFFFF",
        })
        # Vermelho de alerta (item 4 do pedido): alternativa incorreta que
        # puxou mais marcação do que a própria alternativa correta.
        fmt_alerta = workbook.add_format({
            "bg_color": "#B00020", "font_color": "#FFFFFF", "bold": True, "border": 1, "border_color": "#FFFFFF",
        })

        abas = {
            "Resultados Brutos": df_bruto,
            "Estatísticas por Aluno": df_estatisticas,
            "Relatório Sintético dos Testes": df_relatorio,
            "Falhas de Leitura": df_falhas,
        }
        for nome_aba, df in abas.items():
            ws = writer.sheets[nome_aba]
            n_colunas = max(len(df.columns) - 1, 0)
            ws.set_column(0, ULTIMA_COLUNA_EXCEL, None, fmt_dark)
            ws.set_column(0, n_colunas, 16, fmt_dark)
            for col_idx, nome_coluna in enumerate(df.columns):
                ws.write(0, col_idx, nome_coluna, fmt_dark_header)

        # ---- Destaque vermelho na aba de Relatório Sintético ----
        ws_relatorio = writer.sheets['Relatório Sintético dos Testes']
        col_idx_por_letra = {letra: idx for idx, letra in enumerate(df_relatorio.columns) if letra in "ABCDE"}
        for i, alertas in enumerate(alertas_por_linha):
            linha_excel = i + 1  # +1 porque a linha 0 é o cabeçalho
            for letra in alertas:
                ws_relatorio.write(linha_excel, col_idx_por_letra[letra], df_relatorio.at[i, letra], fmt_alerta)

    if len(df_falhas) > 0:
        print(f"AVISO: {len(df_falhas)} simulado(s) com falha de leitura — ver aba 'Falhas de Leitura'.")
    print(f"✓ Excel gerado com sucesso: {caminho_saida}")

if __name__ == "__main__":
    gerar_excel_final()
