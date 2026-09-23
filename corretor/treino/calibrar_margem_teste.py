"""
Cruza a anotação cega (planilha_anotacao_teste.xlsx, preenchida à mão) com
a probabilidade bruta do modelo (probabilidades_teste.csv) para montar a
matriz de confusão por bolha e calibrar a margem de decisão por varredura
-- seções 4 e 5 do documento de metodologia
(docs/metodologia_teste_acuracia_bolhas.md).

Regras adotadas, decididas com o usuário em 22/09/2026:
- Questões anotadas 'NULA' são excluídas da matriz por completo -- não dá
  para saber, só pela anotação, qual das bolhas marcadas é a real (mesmo
  princípio já usado em aplicar_anotacao.decidir_destinos, para o dataset
  de treino).
- Sob qualquer margem candidata, uma questão decidida como ambígua (EM
  BRANCO, ou o equivalente a NULA da regra de margem -- duas
  probabilidades coladas) não aponta nenhuma bolha como "marcada pelo
  modelo": as 5 entram como predição "vazia". Consistente com o objetivo
  de minimizar falso positivo (seção 5).
- O critério de seleção da margem é só a precisão mínima (seção 5, sem
  teto adicional de taxa de revisão manual -- só entra se a carga no
  operador se mostrar alta na prática).

Uso, a partir da raiz do repositório:
    python -m corretor.treino.calibrar_margem_teste
"""
import csv
import math
from collections import defaultdict
from pathlib import Path

from corretor.revisao.aplicar_anotacao import ler_planilha_anotada
from corretor.treino.gerar_planilha_anotacao_teste import PLANILHA_ANOTACAO_TESTE_PATH
from corretor.treino.inferir_probabilidades_teste import PROBABILIDADES_TESTE_CSV_PATH

MARGENS_CANDIDATAS = [round(0.05 * i, 2) for i in range(1, 13)]  # 0.05 a 0.60
PRECISAO_MINIMA = 0.99
Z_95 = 1.96


def carregar_probabilidades(caminho_csv: Path) -> dict[str, dict[str, float | None]]:
    """
    Lê probabilidades_teste.csv (inferir_probabilidades_teste.py) e agrupa
    as probabilidades por item: cada chave é o rótulo do item (ex.:
    "abc.tif — Q12"), e o valor é um dict recorte -> probabilidade (ex.:
    {"A": 0.02, "B": 0.98, ...}).
    """
    agrupado = defaultdict(dict)
    with open(caminho_csv, newline="", encoding="utf-8") as arquivo:
        leitor = csv.DictReader(arquivo)
        for linha in leitor:
            prob = float(linha["probabilidade"]) if linha["probabilidade"] else None
            agrupado[linha["item"]][linha["recorte"]] = prob
    return dict(agrupado)


def decidir_margem(probs_por_alt: dict[str, float | None], margem: float) -> str | None:
    """
    Decide a resposta de uma questão sob uma margem candidata (seção 7.1):
    ordena as probabilidades, mede a distância entre as duas menores e só
    aponta uma alternativa como marcada quando essa distância excede a
    margem. Caso contrário (colada, seja baixa ou alta) ou se algum
    recorte não teve probabilidade (leitura falhou), devolve None -- nem
    uma das bolhas é predita como marcada nesse item.
    """
    if any(prob is None for prob in probs_por_alt.values()):
        return None
    ordenadas = sorted(probs_por_alt.items(), key=lambda item: item[1])
    melhor_alt, menor_prob = ordenadas[0]
    _, segunda_prob = ordenadas[1]
    if (segunda_prob - menor_prob) > margem:
        return melhor_alt
    return None


def montar_matriz_confusao(
    probabilidades: dict[str, dict[str, float | None]],
    anotacoes: dict[str, str],
    margem: float,
) -> dict[str, int]:
    """
    Percorre todos os itens anotados, decide a resposta de cada um sob a
    margem candidata e soma TP/FP/FN/TN por bolha (seção 4.1). Itens
    anotados 'NULA' são pulados por inteiro (ground truth ambíguo); itens
    sem probabilidade (recorte não leu) também são pulados, e contados à
    parte em 'sem_dado'.
    """
    contagem = {"TP": 0, "FP": 0, "FN": 0, "TN": 0, "nula_excluida": 0, "sem_dado": 0}

    for rotulo, marcada in anotacoes.items():
        if marcada == "NULA":
            contagem["nula_excluida"] += 1
            continue

        probs_item = probabilidades.get(rotulo)
        if probs_item is None or any(p is None for p in probs_item.values()):
            contagem["sem_dado"] += 1
            continue

        predicao = decidir_margem(probs_item, margem)

        for recorte in probs_item:
            real_marcada = recorte == marcada  # marcada == "" ou "BRANCO" -> nunca bate
            predita_marcada = recorte == predicao

            if predita_marcada and real_marcada:
                contagem["TP"] += 1
            elif predita_marcada and not real_marcada:
                contagem["FP"] += 1
            elif not predita_marcada and real_marcada:
                contagem["FN"] += 1
            else:
                contagem["TN"] += 1

    return contagem


def calcular_metricas(contagem: dict[str, int]) -> dict[str, float]:
    """
    Calcula precisão, revocação (sensibilidade) e acurácia por bolha a
    partir da matriz de confusão (seção 4.2). Precisão e revocação vêm
    0.0 quando o denominador é zero (nenhuma bolha predita/real marcada
    sob essa margem), em vez de lançar erro de divisão por zero.
    """
    tp, fp, fn, tn = contagem["TP"], contagem["FP"], contagem["FN"], contagem["TN"]
    total = tp + fp + fn + tn

    precisao = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    revocacao = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    acuracia = (tp + tn) / total if total > 0 else 0.0

    return {"precisao": precisao, "revocacao": revocacao, "acuracia": acuracia, "total_bolhas": total}


def intervalo_wilson(acertos: int, n: int, z: float = Z_95) -> tuple[float, float]:
    """
    Intervalo de confiança de Wilson (seção 3.5) para uma proporção de
    acertos observada -- usado sempre, nunca o intervalo normal simples
    (Wald), porque a taxa esperada aqui fica perto de um extremo (~99%),
    onde Wald degrada (seção 3.4), mesmo com n na casa das centenas.
    """
    if n == 0:
        return (0.0, 0.0)
    p_chapeu = acertos / n
    z2_n = (z ** 2) / n
    centro = (p_chapeu + z2_n / 2) / (1 + z2_n)
    meia_largura = (z / (1 + z2_n)) * math.sqrt(p_chapeu * (1 - p_chapeu) / n + (z ** 2) / (4 * n ** 2))
    return (max(0.0, centro - meia_largura), min(1.0, centro + meia_largura))


def varrer_margens(
    probabilidades: dict[str, dict[str, float | None]],
    anotacoes: dict[str, str],
) -> list[dict]:
    """
    Roda montar_matriz_confusao + calcular_metricas para cada margem
    candidata (seção 5, protocolo de calibração, passos 2-4) e devolve um
    ponto por margem, pronto para montar a curva precisão-revocação.
    """
    resultados = []
    for margem in MARGENS_CANDIDATAS:
        contagem = montar_matriz_confusao(probabilidades, anotacoes, margem)
        metricas = calcular_metricas(contagem)
        resultados.append({"margem": margem, **contagem, **metricas})
    return resultados


def escolher_margem(resultados: list[dict], precisao_minima: float = PRECISAO_MINIMA) -> dict | None:
    """
    Critério de seleção (seção 5, passo 5): a MENOR margem candidata que
    ainda garante a precisão mínima -- não a mais alta possível, para não
    gerar excesso de EM BRANCO desnecessário. Devolve None se nenhuma
    margem candidata atingir a precisão mínima (a varredura precisa ser
    ampliada, ou a meta revista).
    """
    candidatas = [r for r in resultados if r["precisao"] >= precisao_minima]
    if not candidatas:
        return None
    return min(candidatas, key=lambda r: r["margem"])


def calibrar_margem_teste() -> None:
    """
    Ponto de entrada: lê a anotação cega e as probabilidades, roda a
    varredura de margens, escolhe a margem final e imprime o resultado --
    incluindo o intervalo de Wilson para a acurácia por bolha sob a
    margem escolhida (seção 3.6: leitura correta do IC, nunca "95% de
    chance de p estar no intervalo").
    """
    anotados = ler_planilha_anotada(PLANILHA_ANOTACAO_TESTE_PATH)
    anotacoes = {item["rotulo"]: item["marcada"] for item in anotados}
    probabilidades = carregar_probabilidades(PROBABILIDADES_TESTE_CSV_PATH)

    resultados = varrer_margens(probabilidades, anotacoes)

    print(f"{'Margem':>8} {'Precisão':>10} {'Revocação':>11} {'Acurácia':>10} {'TP':>5} {'FP':>5} {'FN':>5} {'TN':>5}")
    for r in resultados:
        print(
            f"{r['margem']:>8.2f} {r['precisao']:>10.2%} {r['revocacao']:>11.2%} "
            f"{r['acuracia']:>10.2%} {r['TP']:>5} {r['FP']:>5} {r['FN']:>5} {r['TN']:>5}"
        )

    escolhida = escolher_margem(resultados)
    if escolhida is None:
        print(f"\nNenhuma margem candidata atingiu precisão >= {PRECISAO_MINIMA:.0%}.")
        return

    acertos = escolhida["TP"] + escolhida["TN"]
    total = escolhida["total_bolhas"]
    ic_baixo, ic_alto = intervalo_wilson(acertos, total)

    print(f"\nMargem escolhida: {escolhida['margem']:.2f}")
    print(f"Precisão: {escolhida['precisao']:.2%} | Revocação: {escolhida['revocacao']:.2%}")
    print(
        f"Acurácia por bolha: {escolhida['acuracia']:.2%} "
        f"(IC 95% Wilson: [{ic_baixo:.2%}; {ic_alto:.2%}], n={total})"
    )
    print(
        f"Itens excluídos -- NULA na anotação: {resultados[0]['nula_excluida']}, "
        f"sem dado (leitura falhou): {resultados[0]['sem_dado']}"
    )


if __name__ == "__main__":
    calibrar_margem_teste()
