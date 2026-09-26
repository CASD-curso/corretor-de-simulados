"""
Script avulso, de uso único: imprime as respostas lidas pelo software
(modelo novo) para UMA folha específica do G2, para conferência manual
contra o que o Gonzalez leu olhando o scan direto -- não faz parte do
pipeline, não precisa ser mantido.

Uso, a partir da raiz do repositório:
    python -m corretor.treino.conferir_folha
"""
from pathlib import Path

from corretor import config
from corretor.inferencia.inferir_simulado_e_inscricao import PADRAO_BOLHA, decidir
from corretor.inferencia.modelo_bolhas import carregar_modelo, obter_device, prob_bolha_preenchida

# Nome da folha a conferir -- SEM extensão, igual ao que aparece no nome
# dos arquivos de recorte (ex.: NOME_Q1_A.png).
NOME_FOLHA = "20260901193429379_0001"

RECORTES_BOLHAS_G2_DIR = config.LOCAL_DIR / "teste_b_recortes" / "bolhas_respostas"


def main():
    arquivos = sorted(RECORTES_BOLHAS_G2_DIR.glob(f"{NOME_FOLHA}_Q*_*.png"))
    if not arquivos:
        raise FileNotFoundError(
            f"Nenhum recorte de '{NOME_FOLHA}' em '{RECORTES_BOLHAS_G2_DIR}'. "
            "Rode o Teste B (avaliar_teste_b.py) primeiro."
        )

    por_questao = {}
    for arq in arquivos:
        m = PADRAO_BOLHA.match(arq.name)
        if not m:
            continue
        _, num_q, alt = m.group(1), int(m.group(2)), m.group(3).upper()
        por_questao.setdefault(num_q, {})[alt] = arq

    device = obter_device()
    modelo = carregar_modelo(device)

    respostas = []
    for q in range(1, config.NUM_QUESTOES + 1):
        if q not in por_questao:
            respostas.append("BRANCOM")
            continue
        probs = {}
        for alt in config.ALTERNATIVAS:
            caminho = por_questao[q].get(alt)
            if caminho is None:
                probs[alt] = 1.0
                continue
            prob, _ = prob_bolha_preenchida(modelo, caminho, device)
            probs[alt] = prob
        respostas.append(decidir(probs))

    print(f"Folha: {NOME_FOLHA}")
    print("".join(r if r not in ("BRANCOM", "MULTM") else "?" for r in respostas))
    print()
    for i, r in enumerate(respostas, 1):
        print(f"  Q{i}: {r}")


if __name__ == "__main__":
    main()
