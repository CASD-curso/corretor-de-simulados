import csv
import re
from collections import defaultdict
from pathlib import Path

from corretor.config import (
    ALTERNATIVAS,
    LIMIAR_MAXIMO,
    LIMIAR_DUPLA,
    NUM_QUESTOES,
    RECORTES_BOLHAS_DIR,
    RESULTADOS_CSV_PATH,
)
from corretor.inferencia.modelo_bolhas import carregar_modelo, obter_device, prob_bolha_preenchida

PADRAO_ARQUIVO = re.compile(r"^(.+)_Q(\d+)_([A-E])\.png$", re.IGNORECASE)


def padrao_da_questao(probs_por_alt, limiar_maximo=LIMIAR_MAXIMO, limiar_dupla=LIMIAR_DUPLA):
    """Retorna a alternativa marcada (A-E), 'EM BRANCO' ou 'NULA(MARCADAS>1)' usando lógica relativa."""
    
    bolhas_ordenadas = sorted(probs_por_alt.items(), key=lambda item: item[1])
    
    melhor_alt, menor_prob = bolhas_ordenadas[0]
    segunda_alt, segunda_prob = bolhas_ordenadas[1]
    
    if menor_prob > limiar_maximo:
        return "EM BRANCO"
    elif segunda_prob < limiar_dupla:
        return "NULA(MARCADAS>1)"
    else:
        return melhor_alt


def inferir_simulados(pasta_recortes=None, csv_saida=None, exportar_csv=True):
    if pasta_recortes is None:
        pasta_recortes = RECORTES_BOLHAS_DIR
    if csv_saida is None:
        csv_saida = RESULTADOS_CSV_PATH

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
        nome_sim, num_q, alt = m.group(1), int(m.group(2)), m.group(3).upper()
        por_simulado[nome_sim][num_q][alt] = arq

    device = obter_device()
    print(f"Inferindo respostas em: {device}")
    modelo = carregar_modelo(device)

    linhas_csv = []

    for nome_sim in sorted(por_simulado.keys()):
        questoes = por_simulado[nome_sim]
        respostas = []

        for q in range(1, NUM_QUESTOES + 1):
            probs = {}
            if q not in questoes:
                respostas.append("EM BRANCO") 
                continue

            for alt in ALTERNATIVAS:
                caminho = questoes[q].get(alt)
                if caminho is None:
                    probs[alt] = 1.0  # Corrigido para 1.0 (bolha em branco)
                    continue
                probs[alt] = prob_bolha_preenchida(modelo, caminho, device)

            respostas.append(padrao_da_questao(probs))

        linha = {
            "Simulado": nome_sim,
            **{f"Q{i}": respostas[i - 1] for i in range(1, NUM_QUESTOES + 1)},
        }
        linhas_csv.append(linha)
        print(f"  {nome_sim}: {NUM_QUESTOES} questões processadas")

    if exportar_csv:
        cabecalho = ["Simulado"] + [f"Q{i}" for i in range(1, NUM_QUESTOES + 1)]
        csv_saida = Path(csv_saida)
        csv_saida.parent.mkdir(parents=True, exist_ok=True)

        with open(csv_saida, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=cabecalho)
            writer.writeheader()
            writer.writerows(linhas_csv)

        print(f"\n{len(linhas_csv)} simulado(s) exportado(s) para '{csv_saida}'.")
    
    return {
        linha["Simulado"]: [linha[f"Q{i}"] for i in range(1, NUM_QUESTOES + 1)]
        for linha in linhas_csv
    }


def main():
    print(f"Lendo recortes de: {RECORTES_BOLHAS_DIR}")
    inferir_simulados()


if __name__ == "__main__":
    main()