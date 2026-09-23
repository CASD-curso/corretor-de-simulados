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
    """Retorna a alternativa marcada (A-E), 'BRANCOM' ou 'MULTM' usando lógica relativa.

    O sufixo M marca que a decisão veio direto do modelo, sem revisão
    humana ainda -- ver corretor.revisao.aplicar_revisao, que grava
    'BRANCO'/'MULT' (sem M) quando o operador confirma manualmente."""

    bolhas_ordenadas = sorted(probs_por_alt.items(), key=lambda item: item[1])

    melhor_alt, menor_prob = bolhas_ordenadas[0]
    segunda_alt, segunda_prob = bolhas_ordenadas[1]

    if menor_prob > limiar_maximo:
        return "BRANCOM"
    elif segunda_prob < limiar_dupla:
        return "MULTM"
    else:
        return melhor_alt


def inferir_simulados(pasta_recortes=None, csv_saida=None, exportar_csv=True):
    """
    Retorna (respostas_por_simulado, bolhas_ilegiveis_por_simulado).

    O segundo dicionário é a auditoria do item 4 do plano: para cada
    simulado, a lista de questões ("Q3", "Q17", ...) em que pelo menos uma
    das 5 imagens de bolha existia mas falhou ao abrir. Antes essa falha só
    fazia a bolha valer 1.0 (vazia) silenciosamente, sem nenhum registro de
    qual questão foi afetada.
    """
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
    bolhas_ilegiveis = defaultdict(list)

    for nome_sim in sorted(por_simulado.keys()):
        questoes = por_simulado[nome_sim]
        respostas = []

        for q in range(1, NUM_QUESTOES + 1):
            probs = {}
            if q not in questoes:
                respostas.append("BRANCOM")
                continue

            questao_ilegivel = False
            for alt in ALTERNATIVAS:
                caminho = questoes[q].get(alt)
                if caminho is None:
                    probs[alt] = 1.0  # Corrigido para 1.0 (bolha em branco)
                    continue
                prob, leitura_ok = prob_bolha_preenchida(modelo, caminho, device)
                probs[alt] = prob
                if not leitura_ok:
                    questao_ilegivel = True

            if questao_ilegivel:
                bolhas_ilegiveis[nome_sim].append(f"Q{q}")

            respostas.append(padrao_da_questao(probs))

        linha = {
            "Simulado": nome_sim,
            **{f"Q{i}": respostas[i - 1] for i in range(1, NUM_QUESTOES + 1)},
            "Bolhas_Ilegiveis": ",".join(bolhas_ilegiveis.get(nome_sim, [])),
        }
        linhas_csv.append(linha)
        print(f"  {nome_sim}: {NUM_QUESTOES} questões processadas")

    if exportar_csv:
        cabecalho = ["Simulado"] + [f"Q{i}" for i in range(1, NUM_QUESTOES + 1)] + ["Bolhas_Ilegiveis"]
        csv_saida = Path(csv_saida)
        csv_saida.parent.mkdir(parents=True, exist_ok=True)

        with open(csv_saida, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=cabecalho)
            writer.writeheader()
            writer.writerows(linhas_csv)

        print(f"\n{len(linhas_csv)} simulado(s) exportado(s) para '{csv_saida}'.")

    respostas_por_simulado = {
        linha["Simulado"]: [linha[f"Q{i}"] for i in range(1, NUM_QUESTOES + 1)]
        for linha in linhas_csv
    }
    return respostas_por_simulado, dict(bolhas_ilegiveis)


def main():
    print(f"Lendo recortes de: {RECORTES_BOLHAS_DIR}")
    _, bolhas_ilegiveis = inferir_simulados()
    if bolhas_ilegiveis:
        print(f"\nAVISO: bolhas ilegíveis em {len(bolhas_ilegiveis)} simulado(s): {bolhas_ilegiveis}")


if __name__ == "__main__":
    main()
