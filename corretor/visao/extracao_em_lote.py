import json
import os
from pathlib import Path

import cv2
import numpy as np


from corretor.config import (
    ADAPTIVE_THRESH_BLOCK,
    ADAPTIVE_THRESH_C,
    FALHAS_ALINHAMENTO_PATH,
    GRADE_INSCRICAO,
    GRADE_RESPOSTAS,
    NUM_QUESTOES,  # Importado para uso dinâmico nos logs
    PRE_PROC_CLAHE_CLIP,
    PRE_PROC_GAMMA,
    PRE_PROC_USAR_CLAHE,
    RECORTES_BOLHAS_DIR,
    RECORTES_INSCRICAO_DIR,
    SIMULADOS_DIR,
)
from corretor.visao.alinhar_gabarito import alinhar_gabarito


def processar_recorte_adaptativo(img_cinza, target_size=(32, 32)):
    """
    Pipeline: Padding -> (opcional) CLAHE/gamma -> Adaptive Threshold -> Resize.
    Ajustado para bolhas mais claras em scans com baixo contraste.
    """
    img_padded = cv2.copyMakeBorder(img_cinza, 4, 4, 4, 4, cv2.BORDER_CONSTANT, value=255)

    if PRE_PROC_USAR_CLAHE:
        clahe = cv2.createCLAHE(clipLimit=PRE_PROC_CLAHE_CLIP, tileGridSize=(4, 4))
        img_padded = clahe.apply(img_padded)

    if PRE_PROC_GAMMA != 1.0:
        norm = img_padded.astype(np.float32) / 255.0
        img_padded = np.clip(np.power(norm, PRE_PROC_GAMMA) * 255.0, 0, 255).astype(np.uint8)

    binaria = cv2.adaptiveThreshold(
        img_padded,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        ADAPTIVE_THRESH_BLOCK,
        ADAPTIVE_THRESH_C,
    )
    final = cv2.resize(binaria, target_size, interpolation=cv2.INTER_AREA)
    return final


def extrair_bolhas_inscricao(imagem_alinhada_cinza, nome_base, pasta_inscricao):
    """Grade 7x10 de bolhas de inscrição -> PNGs 32x32.

    x_ini/y_ini/passo_x/passo_y vêm do config como float (medidos direto em
    gabaritos reais). Cada borda da célula é arredondada individualmente
    (round()) em vez de multiplicar um passo inteiro truncado -- assim o
    erro de arredondamento não se acumula célula a célula.
    """
    g = GRADE_INSCRICAO
    x_ini, y_ini = g["x_ini"], g["y_ini"]
    passo_x, passo_y = g["passo_x"], g["passo_y"]

    for pos in range(g["qtd_colunas"]):
        x1 = round(x_ini + pos * passo_x)
        x2 = round(x_ini + (pos + 1) * passo_x)
        for dig in range(g["qtd_linhas"]):
            y1 = round(y_ini + dig * passo_y)
            y2 = round(y_ini + (dig + 1) * passo_y)
            bolha_raw = imagem_alinhada_cinza[y1:y2, x1:x2]
            bolha_final = processar_recorte_adaptativo(bolha_raw, target_size=(32, 32))
            nome_arquivo = os.path.join(
                pasta_inscricao, f"{nome_base}_inscricao_pos{pos}_dig{dig}.png"
            )
            # Salvamento seguro para Windows
            sucesso, buffer = cv2.imencode('.png', bolha_final)
            if sucesso:
                buffer.tofile(nome_arquivo)


def extrair_bolhas_respostas(imagem_alinhada_cinza, nome_base, pasta_bolhas):
    """Grade de respostas dinâmica (lida do config) -> PNGs 32x32.

    y_questoes_ini/passo_y são globais; cada bloco tem seu próprio
    x_ini/passo_x. Todos vêm do config como float (medidos direto em
    gabaritos reais) -- cada borda da célula é arredondada individualmente
    (round()), nunca um passo inteiro truncado reaproveitado em todas as
    linhas. Com passo inteiro truncado, o erro se acumulava ao longo de 16
    linhas e chegava a ~20px de desvio na última questão de cada bloco,
    cortando a bolha pela metade -- essa era a causa dos recortes em
    formato de meia-lua na planilha de revisão.
    """
    g = GRADE_RESPOSTAS
    y_questoes_ini = g["y_questoes_ini"]
    passo_y = g["passo_y"]
    alternativas = ["A", "B", "C", "D", "E"]
    num_questao = 1

    for bloco in g["blocos"]:
        x_ini = bloco["x_ini"]
        passo_x = bloco["passo_x"]
        qtd_linhas = bloco["linhas"]

        for linha in range(qtd_linhas):
            y1 = round(y_questoes_ini + linha * passo_y)
            y2 = round(y_questoes_ini + (linha + 1) * passo_y)
            for coluna in range(5):
                x1 = round(x_ini + coluna * passo_x)
                x2 = round(x_ini + (coluna + 1) * passo_x)

                bolha_raw = imagem_alinhada_cinza[y1:y2, x1:x2]
                bolha_final = processar_recorte_adaptativo(bolha_raw, target_size=(32, 32))
                letra = alternativas[coluna]
                nome_arquivo = os.path.join(
                    pasta_bolhas, f"{nome_base}_Q{num_questao}_{letra}.png"
                )
                # Salvamento seguro para Windows
                sucesso, buffer = cv2.imencode('.png', bolha_final)
                if sucesso:
                    buffer.tofile(nome_arquivo)

            num_questao += 1


def processar_simulados(
    pasta_origem=None,
    pasta_bolhas=None,
    pasta_inscricao=None,
    extrair_respostas=True,
    extrair_inscricao=True,
):
    if pasta_origem is None:
        pasta_origem = str(SIMULADOS_DIR)
    if pasta_bolhas is None:
        pasta_bolhas = str(RECORTES_BOLHAS_DIR)
    if pasta_inscricao is None:
        pasta_inscricao = str(RECORTES_INSCRICAO_DIR)

    if extrair_respostas:
        os.makedirs(pasta_bolhas, exist_ok=True)
    if extrair_inscricao:
        os.makedirs(pasta_inscricao, exist_ok=True)

    arquivos = sorted([
        os.path.join(pasta_origem, f)
        for f in os.listdir(pasta_origem)
        if f.lower().endswith((".tif", ".tiff"))
    ])

    if not arquivos:
        print(f"Nenhum arquivo encontrado na pasta '{pasta_origem}'.")
        return

    tipos = []
    if extrair_inscricao:
        tipos.append("inscrição")
    if extrair_respostas:
        tipos.append(f"respostas ({NUM_QUESTOES} questões)")
        
    print(f"Iniciando extração de {len(arquivos)} simulados ({', '.join(tipos)})...")

    # Item 4 do plano: antes, uma folha sem alinhamento só gerava um print e
    # desaparecia do resultado. Agora cada falha fica registrada aqui, com o
    # motivo, e é persistida em disco para gerar_planilha_unificada conseguir
    # ler mesmo numa célula/processo separado do notebook.
    falhas_alinhamento = {}

    for index_arquivo, caminho_imagem in enumerate(arquivos):
        nome_base = os.path.basename(caminho_imagem).split(".")[0]
        print(f"[{index_arquivo + 1}/{len(arquivos)}] Processando: {nome_base}")

        imagem_alinhada_cinza, motivo_falha = alinhar_gabarito(caminho_imagem)
        if imagem_alinhada_cinza is None:
            print(f"  -> ERRO: Não foi possível alinhar ({motivo_falha}). Pulando.")
            falhas_alinhamento[nome_base] = motivo_falha
            continue

        if extrair_inscricao:
            extrair_bolhas_inscricao(imagem_alinhada_cinza, nome_base, pasta_inscricao)

        if extrair_respostas:
            extrair_bolhas_respostas(imagem_alinhada_cinza, nome_base, pasta_bolhas)

    # Persiste o registro de falhas desta rodada (sobrescreve o de rodadas
    # anteriores — o arquivo reflete sempre o último lote extraído).
    caminho_falhas = Path(FALHAS_ALINHAMENTO_PATH)
    caminho_falhas.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho_falhas, "w", encoding="utf-8") as f:
        json.dump(falhas_alinhamento, f, ensure_ascii=False, indent=2)

    if falhas_alinhamento:
        print(f"\n{len(falhas_alinhamento)} folha(s) descartada(s) por falha de alinhamento "
              f"(registradas em '{caminho_falhas}').")
    print("\nProcessamento em lote concluído com sucesso!")
    return falhas_alinhamento


if __name__ == "__main__":
    processar_simulados()