"""Alinhamento perspectivo do gabarito escaneado."""
import itertools

import cv2
import numpy as np
from corretor.config import CONFIG_SIMULADOS, SIMULADO_ATIVO


def _ordenar_cantos(pontos):
    """
    Recebe 4 pontos (cx, cy) em qualquer ordem e devolve
    (superior_esquerdo, superior_direito, inferior_direito, inferior_esquerdo).
    Mesma regra de soma/diferença já usada mais abaixo na função principal.
    """
    pontos = np.array(pontos, dtype="float32")
    somas = pontos.sum(axis=1)
    diferencas = np.diff(pontos, axis=1)
    return (
        pontos[np.argmin(somas)],
        pontos[np.argmin(diferencas)],
        pontos[np.argmax(somas)],
        pontos[np.argmax(diferencas)],
    )


def _distancia(p, q):
    return float(np.linalg.norm(np.array(p) - np.array(q)))


def _pontuacao_retangulo(quatro_pontos):
    """
    Quanto menor, mais os 4 pontos se parecem com um retângulo: soma do
    quanto os dois lados opostos diferem entre si e do quanto as duas
    diagonais diferem entre si. Um retângulo perfeito dá pontuação 0.
    """
    se, sd, id_, ie = _ordenar_cantos(quatro_pontos)

    lado_superior = _distancia(se, sd)
    lado_inferior = _distancia(ie, id_)
    lado_esquerdo = _distancia(se, ie)
    lado_direito = _distancia(sd, id_)
    diagonal_1 = _distancia(se, id_)
    diagonal_2 = _distancia(sd, ie)

    return (
        abs(lado_superior - lado_inferior)
        + abs(lado_esquerdo - lado_direito)
        + abs(diagonal_1 - diagonal_2)
    )


def _escolher_melhor_quadrilatero(candidatos):
    """
    Quando sobram mais de 4 candidatos a marcador (ex.: um borrão na folha
    que também caiu dentro da margem de canto), testa todas as combinações
    de 4 e devolve a que mais se aproxima de um retângulo. Com poucos
    candidatos (a situação real: 5 ou 6, nunca dezenas), o número de
    combinações é pequeno o suficiente para testar todas sem otimização.
    """
    melhor_combinacao = None
    melhor_pontuacao = None
    for combinacao in itertools.combinations(candidatos, 4):
        pontuacao = _pontuacao_retangulo(combinacao)
        if melhor_pontuacao is None or pontuacao < melhor_pontuacao:
            melhor_pontuacao = pontuacao
            melhor_combinacao = combinacao
    return list(melhor_combinacao), melhor_pontuacao


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
    params_alinhamento = config_atual.get(
        "ALINHAMENTO", {"AREA_MINIMA_MARCADOR_FRACAO": 5000 / (2480 * 3508), "MARGEM_FRACAO": 0.30}
    )

    LARGURA_ALINHADA = 800
    ALTURA_ALINHADA = 1130
    # Fração da área total da imagem, não pixels absolutos -- assim o limiar
    # acompanha a resolução real do scan (100/200/300/400/600 dpi, achado de
    # 23/09/2026: um lote a 200 dpi teve 100% das folhas descartadas porque
    # o limiar antigo, fixo em pixels, foi calibrado só para 300 dpi).
    AREA_MINIMA_MARCADOR_FRACAO = params_alinhamento["AREA_MINIMA_MARCADOR_FRACAO"]
    MARGEM_FRACAO = params_alinhamento["MARGEM_FRACAO"]
    # Faixa bem fina na borda externa da folha que é ignorada antes de
    # procurar marcador -- existe pra um borrão ou mancha exatamente na
    # beirada da folha (ex.: sombra do scanner, resto de fita) não entrar
    # nem como candidato. .get() com default: funciona mesmo se algum
    # SIMULADO_ATIVO não tiver essa chave configurada ainda.
    MARGEM_CORTE_BORDA_FRACAO = params_alinhamento.get("MARGEM_CORTE_BORDA_FRACAO", 0.01)

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

    # Apaga (vira fundo) uma faixa fina em toda a borda antes de procurar
    # contorno. Qualquer mancha que esteja só nessa faixa nunca vira
    # candidato a marcador; um marcador real, bem mais para dentro da
    # folha, não é afetado.
    corte_x = int(largura * MARGEM_CORTE_BORDA_FRACAO)
    corte_y = int(altura * MARGEM_CORTE_BORDA_FRACAO)
    if corte_x > 0:
        imagem_binaria[:, :corte_x] = 0
        imagem_binaria[:, largura - corte_x:] = 0
    if corte_y > 0:
        imagem_binaria[:corte_y, :] = 0
        imagem_binaria[altura - corte_y:, :] = 0

    contornos, _ = cv2.findContours(
        imagem_binaria, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    marcadores = []
    margem_x, margem_y = largura * MARGEM_FRACAO, altura * MARGEM_FRACAO
    # Calculado aqui (não antes) porque depende de altura/largura reais desta
    # imagem, lidas linhas acima -- é o que torna o limiar independente do DPI.
    area_minima_marcador = AREA_MINIMA_MARCADOR_FRACAO * altura * largura

    for contorno in contornos:
        area = cv2.contourArea(contorno)
        if area < area_minima_marcador:
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
    elif len(marcadores) > 4:
        # Mais de 4 candidatos: normalmente é um borrão, rasura ou sombra
        # que também caiu dentro da margem de canto e passou no filtro de
        # área. Em vez de descartar a folha, escolhe entre todas as
        # combinações de 4 a que mais forma um retângulo -- os 4 marcadores
        # reais, por construção, formam um retângulo; um borrão extra não
        # tende a completar essa forma tão bem quanto o marcador que ele
        # substituiria.
        n_candidatos = len(marcadores)
        marcadores, pontuacao = _escolher_melhor_quadrilatero(marcadores)
        print(f" -> [{SIMULADO_ATIVO}] {n_candidatos} candidatos a marcador encontrados "
              f"(esperado: 4) -- escolhidos os 4 que formam o retangulo mais regular "
              f"(pontuacao {pontuacao:.1f}, 0 = retangulo perfeito).")
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