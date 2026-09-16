import csv
import re
from collections import defaultdict
from pathlib import Path

from corretor.config import (
    DIGITOS_INSCRICAO,
    INSCRICOES_CSV_PATH,
    LIMIAR_MAXIMO, LIMIAR_DUPLA,
    NUM_DIGITOS_INSCRICAO,
    RECORTES_INSCRICAO_DIR,
)
from corretor.inferencia.modelo_bolhas import carregar_modelo, obter_device, prob_bolha_preenchida

PADRAO_ARQUIVO = re.compile(r"^(.+)_inscricao_pos(\d+)_dig(\d+)\.png$", re.IGNORECASE)
'''
Exemplo prático:
Se o arquivo se chamar scan01_inscricao_pos1_dig5.png, esse código corta o nome em três pedaços perfeitos para o seu defaultdict organizar:
scan01
1
5
'''


def ler_digito(probs_por_digito, limiar_maximo=LIMIAR_MAXIMO, limiar_dupla=LIMIAR_DUPLA):
    # Ordena as alternativas da menor probabilidade (mais preenchida) para a maior (mais vazia)
    bolhas_ordenadas = sorted(probs_por_digito.items(), key=lambda item: item[1])
    
    melhor_dig, menor_prob = bolhas_ordenadas[0]
    segunda_dig, segunda_prob = bolhas_ordenadas[1]
    
    # 1. Se a melhor opção ainda tiver probabilidade muito alta, está em branco
    if menor_prob > limiar_maximo:
        return "?"
        
    # 2. Se a segunda melhor opção também estiver bem preenchida, é dupla marcação
    elif segunda_prob < limiar_dupla:
        return "?" 
        
    # 3. Caso contrário, retorna o dígito com a menor probabilidade
    else:
        return str(melhor_dig)
    


def inferir_inscricoes(pasta_recortes=None, csv_saida=None, exportar_csv=True):
    """
    Retorna (inscricao_por_simulado, digitos_ilegiveis_por_simulado).

    O segundo dicionário é a auditoria do item 4: para cada simulado, a
    lista de posições do número de inscrição ("pos2", "pos5", ...) cuja
    imagem existia mas falhou ao abrir.
    """
    if pasta_recortes is None:
        pasta_recortes = RECORTES_INSCRICAO_DIR
    if csv_saida is None:
        csv_saida = INSCRICOES_CSV_PATH

    pasta = Path(pasta_recortes)
    if not pasta.exists():
        raise FileNotFoundError(f"Pasta de recortes não encontrada: {pasta}")

    arquivos = sorted(pasta.glob("*.png"))
    if not arquivos:
        raise FileNotFoundError(f"Nenhum PNG em '{pasta}'. Rode a extração primeiro.")

    por_simulado = defaultdict(lambda: defaultdict(dict))
    for arq in arquivos:
        m = PADRAO_ARQUIVO.match(arq.name)
        if not m:
            continue
        nome_sim, pos, dig = m.group(1), int(m.group(2)), int(m.group(3))
        por_simulado[nome_sim][pos][dig] = arq

    device = obter_device()
    print(f"Inferindo inscrições em: {device}")
    modelo = carregar_modelo(device)

    linhas_csv = []
    digitos_ilegiveis = defaultdict(list)

    for nome_sim in sorted(por_simulado.keys()):
        posicoes = por_simulado[nome_sim]
        digitos = []

        for pos in range(NUM_DIGITOS_INSCRICAO):
            probs = {}
            if pos not in posicoes:  # Se a coluna inteira não existir por algum erro no corte, ele marca como ? e pula para a próxima.
                digitos.append("?")
                continue

            posicao_ilegivel = False
            for dig in DIGITOS_INSCRICAO:
                caminho = posicoes[pos].get(dig)
                if caminho is None:
                    probs[dig] = 1.0   # Assume a bolh ausente como bolha em branco
                    continue
                prob, leitura_ok = prob_bolha_preenchida(modelo, caminho, device)
                probs[dig] = prob
                if not leitura_ok:
                    posicao_ilegivel = True

            if posicao_ilegivel:
                digitos_ilegiveis[nome_sim].append(f"pos{pos}")

            digitos.append(ler_digito(probs))

        inscricao = "".join(digitos)
        linhas_csv.append({
            "Simulado": nome_sim,
            "Inscricao": inscricao,
            "Digitos_Ilegiveis": ",".join(digitos_ilegiveis.get(nome_sim, [])),
        })
        print(f"  {nome_sim}: {inscricao}")

    if exportar_csv:
        cabecalho = ["Simulado", "Inscricao", "Digitos_Ilegiveis"]
        csv_saida = Path(csv_saida)
        csv_saida.parent.mkdir(parents=True, exist_ok=True)

        with open(csv_saida, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=cabecalho)
            writer.writeheader()
            writer.writerows(linhas_csv)

        print(f"\n{len(linhas_csv)} inscrição(ões) exportada(s) para '{csv_saida}'.")

    inscricao_por_simulado = {linha["Simulado"]: linha["Inscricao"] for linha in linhas_csv}
    return inscricao_por_simulado, dict(digitos_ilegiveis)


def main():
    print(f"Lendo recortes de: {RECORTES_INSCRICAO_DIR}")
    _, digitos_ilegiveis = inferir_inscricoes()
    if digitos_ilegiveis:
        print(f"\nAVISO: dígitos ilegíveis em {len(digitos_ilegiveis)} simulado(s): {digitos_ilegiveis}")


if __name__ == "__main__":
    main()
