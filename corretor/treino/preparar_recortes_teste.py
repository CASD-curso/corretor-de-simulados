"""
Localiza no disco cada folha listada em amostra_teste.csv (Teste A + Teste
B, sortear_amostra_teste.py), copia para uma pasta de entrada isolada
(nunca mistura com SIMULADOS_DIR de produção nem com a amostra de treino)
e roda a extração de bolhas sobre elas -- pré-requisito para
gerar_planilha_anotacao.py (seção 2.2 do documento de metodologia).

Uso, a partir da raiz do repositório:
    python -m corretor.treino.preparar_recortes_teste
"""
from corretor import config
from corretor.revisao.gerar_planilha_anotacao import ler_amostra
from corretor.treino.sortear_amostra import montar_pool_simulados
from corretor.treino.sortear_amostra_teste import montar_pool_teste_b
from corretor.treino.preparar_recortes_amostra import (
    montar_indice_folhas,
    localizar_folhas_da_amostra,
    copiar_folhas_para_entrada,
)
from corretor.visao.extracao_em_lote import processar_simulados

ENTRADA_TESTE_DIR = config.LOCAL_DIR / "teste_acuracia_entrada"
RECORTES_BOLHAS_TESTE_DIR = config.LOCAL_DIR / "teste_acuracia_recortes" / "bolhas_respostas"
RECORTES_INSCRICAO_TESTE_DIR = config.LOCAL_DIR / "teste_acuracia_recortes" / "bolhas_inscricao"


def preparar_recortes_teste() -> None:
    """
    Ponto de entrada: lê amostra_teste.csv, localiza cada folha listada
    (Teste A vem do mesmo pool de dia a dia do treino; Teste B vem só do
    corredor G2), copia para uma pasta de entrada isolada e roda a
    extração de bolhas sobre elas.
    """
    if config.DATASET_NOVO_SIMULADO is None or config.DATASET_NOVO_SIMULADO_EXTRA is None:
        raise RuntimeError(
            "DATASET_NOVO_SIMULADO / DATASET_NOVO_SIMULADO_EXTRA não configurados "
            "em corretor/config_local.py."
        )
    if not config.DATASET_NOVO_CORREDORES_DIR.get("G2"):
        raise RuntimeError("DATASET_NOVO_CORREDORES_DIR['G2'] não configurado.")

    linhas_csv = ler_amostra(config.AMOSTRA_TESTE_CSV_PATH)

    pool_simulados = montar_pool_simulados(
        config.DATASET_NOVO_SIMULADO, config.DATASET_NOVO_SIMULADO_EXTRA
    )
    pool_g2 = montar_pool_teste_b(config.DATASET_NOVO_CORREDORES_DIR["G2"])
    indice_simulados = montar_indice_folhas(pool_simulados)
    indice_vestibular = montar_indice_folhas(pool_g2)

    caminhos = localizar_folhas_da_amostra(linhas_csv, indice_simulados, indice_vestibular)
    print(f"{len(caminhos)} folha(s) localizada(s) a partir de {config.AMOSTRA_TESTE_CSV_PATH}.")

    copiar_folhas_para_entrada(caminhos, ENTRADA_TESTE_DIR)
    print(f"Folhas copiadas para '{ENTRADA_TESTE_DIR}'. Extraindo bolhas...")

    processar_simulados(
        pasta_origem=ENTRADA_TESTE_DIR,
        pasta_bolhas=RECORTES_BOLHAS_TESTE_DIR,
        pasta_inscricao=RECORTES_INSCRICAO_TESTE_DIR,
        extrair_respostas=True,
        extrair_inscricao=True,
    )


if __name__ == "__main__":
    preparar_recortes_teste()
