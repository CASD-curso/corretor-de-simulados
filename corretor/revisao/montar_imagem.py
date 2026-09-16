"""
Monta a tira de recortes (bolhas de questao ou digitos de inscricao) lado a
lado, pra planilha de revisao do item 5. O ponto e permitir comparar as 5
(ou 10) alternativas de uma vez, em vez de uma imagem so -- que nao deixa
decidir nada em caso de dupla marcacao ou marcacao fraca.
"""
from pathlib import Path

from PIL import Image, ImageDraw

DISPLAY_SIZE = 30  # recorte original e 32x32; aqui so arredonda pra baixo
GAP = 4
LABEL_H = 16


def montar_tira(crops_labels):
    """
    crops_labels: lista de tuplas (caminho, label). 'caminho' pode ser um
    Path que nao existe ou uma imagem corrompida -- nesse caso desenha um
    X no lugar do recorte em vez de pular a posicao, pra manter o numero de
    quadros fixo e o rotulo embaixo sempre alinhado com a alternativa certa.
    Retorna um objeto PIL.Image, pronto pra salvar e inserir na planilha.
    """
    n = len(crops_labels)
    largura = n * DISPLAY_SIZE + (n - 1) * GAP
    altura = DISPLAY_SIZE + LABEL_H
    tira = Image.new("RGB", (largura, altura), "white")
    draw = ImageDraw.Draw(tira)

    for i, (caminho, label) in enumerate(crops_labels):
        x = i * (DISPLAY_SIZE + GAP)
        aberto = False
        if caminho is not None and Path(caminho).exists():
            try:
                crop = Image.open(caminho).convert("L").resize((DISPLAY_SIZE, DISPLAY_SIZE))
                tira.paste(crop, (x, 0))
                aberto = True
            except Exception:
                aberto = False
        if not aberto:
            draw.rectangle([x, 0, x + DISPLAY_SIZE - 1, DISPLAY_SIZE - 1], outline="red")
            draw.line([x, 0, x + DISPLAY_SIZE - 1, DISPLAY_SIZE - 1], fill="red")
            draw.line([x, DISPLAY_SIZE - 1, x + DISPLAY_SIZE - 1, 0], fill="red")
        draw.text((x + DISPLAY_SIZE // 2 - 4, DISPLAY_SIZE + 2), str(label), fill="black")

    return tira
