"""Alinhamento perspectivo do gabarito escaneado."""
import cv2
import numpy as np
from corretor.config import CONFIG_SIMULADOS, SIMULADO_ATIVO

def alinhar_gabarito(caminho_imagem):
    """
    Lê a imagem de forma segura e utiliza os parâmetros de alinhamento
    específicos do SIMULADO_ATIVO definido no config.

    Retorna sempre uma tupla (imagem_alinhada, motivo_falha):
      - sucesso: (array numpy, None)
      - falha:   (None, string curta explicando o motivo)
    O motivo existe para que quem chama consiga registrar a falha em vez de
    só ver o print no console (item 4 do plano de alterações).
    """
    # Pega as configurações do simulado ativo atual (CASDINHO ou SEMI)
    config_atual = CONFIG_SIMULADOS.get(SIMULADO_ATIVO, CONFIG_SIMULADOS["CASDINHO"])
    params_alinhamento = config_atual.get("ALINHAMENTO", {"AREA_MINIMA_MARCADOR": 5000, "MARGEM_FRACAO": 0.30})
    
    LARGURA_ALINHADA = 800
    ALTURA_ALINHADA = 1130
    AREA_MINIMA_MARCADOR = params_alinhamento["AREA_MINIMA_MARCADOR"]
    MARGEM_FRACAO = params_alinhamento["MARGEM_FRACAO"]

    caminho_str = str(caminho_imagem)
    img_array = np.fromfile(caminho_str, np.uint8)

    if img_array.size == 0:
        motivo = "arquivo_vazio_ou_caminho_invalido"
        print(f"ERRO: Arquivo vazio ou caminho inválido: {caminho_str}")
        return None, motivo

    imagem = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    if imagem is None:
        motivo = "falha_ao_decodificar_imagem"
        print(f"ERRO: cv2.imdecode falhou ao decodificar a imagem: {caminho_str}")
        return None, motivo

    imagem_cinza = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
    imagem_blur = cv2.GaussianBlur(imagem_cinza, (5, 5), 0)
    _, imagem_binaria = cv2.threshold(
        imagem_blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )

    altura, largura = imagem_binaria.shape
    contornos, _ = cv2.findContours(
        imagem_binaria, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    marcadores = []
    margem_x, margem_y = largura * MARGEM_FRACAO, altura * MARGEM_FRACAO

    for contorno in contornos:
        area = cv2.contourArea(contorno)
        if area < AREA_MINIMA_MARCADOR:
            continue
        
        # Opcional: filtrar proporção para garantir que são quadrados próximos de marcadores
        x, y, w, h = cv2.boundingRect(contorno)
        
        cx, cy = x + w // 2, y + h // 2

        # Verifica se o marcador está em um dos quatro cantos da folha dentro da margem configurada
        if (cx < margem_x and cy < margem_y) or \
           (cx > largura - margem_x and cy < margem_y) or \
           (cx < margem_x and cy > altura - margem_y) or \
           (cx > largura - margem_x and cy > altura - margem_y):
            marcadores.append((cx, cy))

    # Remove duplicadas mantendo a ordem
    marcadores = list(set(marcadores))

    if len(marcadores) == 4:
        pass
    elif len(marcadores) == 3:
        # Ordenamos os marcadores por Y e depois X para reconstruir o 4º canto geometricamente
        marcadores = sorted(marcadores, key=lambda p: (p[1], p[0]))
        p0, p1, p2 = marcadores[0], marcadores[1], marcadores[2]
        
        dist_01 = np.linalg.norm(np.array(p0) - np.array(p1))
        dist_02 = np.linalg.norm(np.array(p0) - np.array(p2))
        dist_12 = np.linalg.norm(np.array(p1) - np.array(p2))
        
        maior_dist = max(dist_01, dist_02, dist_12)
        
        if maior_dist == dist_12:
            p_faltante = np.array(p1) + np.array(p2) - np.array(p0)
        elif maior_dist == dist_02:
            p_faltante = np.array(p0) + np.array(p2) - np.array(p1)
        else:
            p_faltante = np.array(p0) + np.array(p1) - np.array(p2)
            
        marcadores.append(tuple(p_faltante.astype(int)))
        print(f" -> [{SIMULADO_ATIVO}] 4º canto reconstruído matematicamente com sucesso!")
    else:
        motivo = f"apenas_{len(marcadores)}_cantos_encontrados_minimo_3"
        print(f"AVISO: Apenas {len(marcadores)} cantos encontrados em {caminho_str} (Mínimo requerido: 3).")
        return None, motivo

    pontos_origem = np.array(marcadores, dtype="float32")
    somas = pontos_origem.sum(axis=1)
    diferencas = np.diff(pontos_origem, axis=1)

    pontos_ordenados = np.zeros((4, 2), dtype="float32")
    pontos_ordenados[0] = pontos_origem[np.argmin(somas)]       # Superior esquerdo
    pontos_ordenados[2] = pontos_origem[np.argmax(somas)]       # Inferior direito
    pontos_ordenados[1] = pontos_origem[np.argmin(diferencas)]  # Superior direito
    pontos_ordenados[3] = pontos_origem[np.argmax(diferencas)]  # Inferior esquerdo

    pontos_destino = np.array([
        [0, 0],
        [LARGURA_ALINHADA - 1, 0],
        [LARGURA_ALINHADA - 1, ALTURA_ALINHADA - 1],
        [0, ALTURA_ALINHADA - 1],
    ], dtype="float32")

    matriz_perspectiva = cv2.getPerspectiveTransform(pontos_ordenados, pontos_destino)
    imagem_alinhada = cv2.warpPerspective(
        imagem_cinza, matriz_perspectiva, (LARGURA_ALINHADA, ALTURA_ALINHADA)
    )
    return imagem_alinhada, None