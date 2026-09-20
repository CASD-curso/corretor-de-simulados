"""
Teste B (item 7 do plano): avalia o modelo contra o corredor G2, reservado
desde sortear_amostra.py e nunca visto em treino nem validação -- o teste
mais próximo de "uso real" que existe hoje no projeto.

Compara duas rodadas contra o mesmo corredor G2: o modelo NOVO (cnn_bolhas.pth,
carregado com a arquitetura atual, com Dropout) e o modelo ANTIGO
(cnn_bolhas_old.pth, carregado com CNNBinSemDropout -- réplica da
arquitetura de antes do Dropout, já que o state_dict antigo não bate com
a classe CNNBin atual). Nenhum arquivo .pth é sobrescrito ou renomeado por
este script -- os dois pesos são lidos, cada um com o molde certo, direto
dos nomes fixos abaixo.

Uso, a partir da raiz do repositório:
    python -m corretor.treino.avaliar_teste_b
"""
from pathlib import Path
import shutil

import torch

from corretor import config
from corretor.inferencia.inferir_simulado import PADRAO_ARQUIVO, padrao_da_questao
from corretor.inferencia.modelo_bolhas import obter_device, preprocessar
from corretor.rede.arquitetura_da_rede import CNNBin, CNNBinSemDropout
from corretor.visao.extracao_em_lote import processar_simulados
from collections import defaultdict

# Nomes fixos dos dois arquivos de pesos a comparar -- nenhum dos dois é
# alterado, renomeado ou sobrescrito por este script.
PESOS_NOVO_PATH = config.CNN_BOLHAS_PATH  # PESOS_DIR / "cnn_bolhas.pth"
PESOS_ANTIGO_PATH = config.PESOS_DIR / "cnn_bolhas_old.pth"

GABARITO_TESTE_B_PATH = Path(__file__).resolve().parent / "gabarito_teste_b.txt"

# Pastas isoladas do Teste B -- nunca tocam em data/entrada nem em
# RECORTES_BOLHAS_DIR/RECORTES_INSCRICAO_DIR (usadas pelo fluxo de
# produção e pelo item 7 de preparação do dataset de treino).
ENTRADA_G2_DIR = config.LOCAL_DIR / "teste_b_entrada"
RECORTES_BOLHAS_G2_DIR = config.LOCAL_DIR / "teste_b_recortes" / "bolhas_respostas"
RECORTES_INSCRICAO_G2_DIR = config.LOCAL_DIR / "teste_b_recortes" / "bolhas_inscricao"


def preparar_recortes_g2() -> None:
    """
    Copia as folhas do corredor G2 (Teste B, nunca visto no treino) para
    uma pasta de entrada isolada e extrai as bolhas para uma pasta de
    recortes isolada -- nunca mistura com data/entrada nem com
    RECORTES_BOLHAS_DIR (usados pelo fluxo de produção e pelo item 7).
    """
    if not config.DATASET_NOVO_CORREDORES_DIR.get("G2"):
        raise RuntimeError(
            "DATASET_NOVO_CORREDORES_DIR['G2'] não configurado em config_local.py."
        )

    pasta_g2_origem = config.DATASET_NOVO_CORREDORES_DIR["G2"]
    folhas_g2 = sorted(pasta_g2_origem.glob("*.tif*"))
    if not folhas_g2:
        raise FileNotFoundError(f"Nenhuma folha .tif/.tiff em '{pasta_g2_origem}'.")

    ENTRADA_G2_DIR.mkdir(parents=True, exist_ok=True)
    existentes = list(ENTRADA_G2_DIR.glob("*.tif*"))
    if existentes:
        print(
            f"'{ENTRADA_G2_DIR}' já tem {len(existentes)} arquivo(s) de uma "
            "rodada anterior do Teste B -- reaproveitando, sem copiar de novo."
        )
        return

    for origem in folhas_g2:
        shutil.copy(origem, ENTRADA_G2_DIR / origem.name)

    print(f"{len(folhas_g2)} folha(s) de G2 copiada(s) para '{ENTRADA_G2_DIR}'.")

    processar_simulados(
        pasta_origem=ENTRADA_G2_DIR,
        pasta_bolhas=RECORTES_BOLHAS_G2_DIR,
        pasta_inscricao=RECORTES_INSCRICAO_G2_DIR,
        extrair_respostas=True,
        extrair_inscricao=False,
    )


def calcular_metricas(respostas_por_simulado: dict, gabarito: str) -> dict:
    """
    Compara cada resposta inferida com o gabarito oficial e devolve um
    dict com acurácia geral e acertos por questão -- mesma lógica de
    comparação de gerar_excel_final(), resumida a números.
    """
    if len(gabarito) != config.NUM_QUESTOES:
        raise ValueError(
            f"Gabarito tem {len(gabarito)} letras, mas NUM_QUESTOES é "
            f"{config.NUM_QUESTOES}."
        )

    acertos_por_questao = [0] * config.NUM_QUESTOES
    total_folhas = len(respostas_por_simulado)

    for respostas in respostas_por_simulado.values():
        for i, resposta in enumerate(respostas):
            if resposta == gabarito[i]:
                acertos_por_questao[i] += 1

    total_respostas = total_folhas * config.NUM_QUESTOES
    total_acertos = sum(acertos_por_questao)

    return {
        "total_folhas": total_folhas,
        "acuracia_geral": 100 * total_acertos / total_respostas,
        "acertos_por_questao": acertos_por_questao,
    }


def inferir_com_classe(classe_modelo, caminho_pesos: Path) -> dict:
    """
    Réplica de inferir_simulados() (inferir_simulado.py), mas recebendo a
    CLASSE do modelo e o CAMINHO dos pesos como parâmetro, em vez de usar
    CNNBin + CNN_BOLHAS_PATH fixos -- é o que permite este script carregar
    cnn_bolhas.pth com CNNBin (novo, com Dropout) e cnn_bolhas_old.pth com
    CNNBinSemDropout (antigo, sem Dropout) na mesma execução, sem tocar em
    modelo_bolhas.py nem em inferir_simulado.py.
    """
    if not caminho_pesos.exists():
        raise FileNotFoundError(f"Pesos não encontrados em '{caminho_pesos}'.")

    arquivos = sorted(RECORTES_BOLHAS_G2_DIR.glob("*.png"))
    if not arquivos:
        raise FileNotFoundError(f"Nenhum PNG em '{RECORTES_BOLHAS_G2_DIR}'.")

    por_simulado = defaultdict(lambda: defaultdict(dict))
    for arq in arquivos:
        m = PADRAO_ARQUIVO.match(arq.name)
        if not m:
            continue
        nome_sim, num_q, alt = m.group(1), int(m.group(2)), m.group(3).upper()
        por_simulado[nome_sim][num_q][alt] = arq

    device = obter_device()
    modelo = classe_modelo().to(device)
    modelo.load_state_dict(torch.load(caminho_pesos, map_location=device, weights_only=True))
    modelo.eval()

    respostas_por_simulado = {}
    for nome_sim in sorted(por_simulado.keys()):
        questoes = por_simulado[nome_sim]
        respostas = []

        for q in range(1, config.NUM_QUESTOES + 1):
            if q not in questoes:
                respostas.append("EM BRANCO")
                continue

            probs = {}
            for alt in config.ALTERNATIVAS:
                caminho = questoes[q].get(alt)
                if caminho is None:
                    probs[alt] = 1.0
                    continue
                tensor = preprocessar(caminho)
                if tensor is None:
                    probs[alt] = 1.0
                    continue
                with torch.no_grad():
                    saida = modelo(tensor.unsqueeze(0).to(device))
                    probs[alt] = saida.item()

            respostas.append(padrao_da_questao(probs))

        respostas_por_simulado[nome_sim] = respostas

    return respostas_por_simulado


def rodar_passo(gabarito: str, classe_modelo, caminho_pesos: Path, rotulo: str) -> dict:
    """Roda a inferência sobre os recortes de G2 com o modelo indicado e mede a acurácia."""
    print(f"\nModelo: {rotulo} ({caminho_pesos.name}, classe {classe_modelo.__name__})")
    respostas = inferir_com_classe(classe_modelo, caminho_pesos)
    metricas = calcular_metricas(respostas, gabarito)
    print(
        f"Acurácia: {metricas['acuracia_geral']:.2f}% "
        f"({metricas['total_folhas']} folhas, {config.NUM_QUESTOES} questões cada)"
    )
    return metricas


def main():
    gabarito = GABARITO_TESTE_B_PATH.read_text().strip()

    preparar_recortes_g2()

    print("\n" + "=" * 62)
    print("PASSO 1/2: modelo NOVO")
    print("=" * 62)
    metricas_1 = rodar_passo(gabarito, CNNBin, PESOS_NOVO_PATH, "novo (com Dropout)")

    print("\n" + "=" * 62)
    print("PASSO 2/2: modelo ANTIGO")
    print("=" * 62)
    metricas_2 = rodar_passo(gabarito, CNNBinSemDropout, PESOS_ANTIGO_PATH, "antigo (sem Dropout)")

    print("\n" + "=" * 62)
    print("RESUMO")
    print("=" * 62)
    print(f"Novo:   {metricas_1['acuracia_geral']:.2f}%")
    print(f"Antigo: {metricas_2['acuracia_geral']:.2f}%")

    piores = sorted(
        range(config.NUM_QUESTOES),
        key=lambda i: metricas_1["acertos_por_questao"][i] + metricas_2["acertos_por_questao"][i],
    )[:5]
    print("\n5 questões com mais erro combinado (nos dois passos):")
    for i in piores:
        print(
            f"  Q{i + 1} (gabarito {gabarito[i]}): "
            f"passo1={metricas_1['acertos_por_questao'][i]}/{metricas_1['total_folhas']}  "
            f"passo2={metricas_2['acertos_por_questao'][i]}/{metricas_2['total_folhas']}"
        )


if __name__ == "__main__":
    main()
