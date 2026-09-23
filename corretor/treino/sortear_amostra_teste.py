"""
Sorteio da amostra do experimento de acurácia por bolha (item 7, regra de
margem 7.1) -- adapta sortear_amostra.py (usado para o dataset de treino)
para sortear do pool de teste isolado (nunca visto pelo modelo em nenhuma
fase), conforme o desenho da seção 2 do documento de metodologia
(docs/metodologia_teste_acuracia_bolhas.md).

Uso, a partir da raiz do repositório:
    python -m corretor.treino.sortear_amostra_teste
"""
from pathlib import Path

from corretor import config
from corretor.revisao.gerar_planilha_anotacao import ler_amostra
from corretor.treino.sortear_amostra import (
    montar_pool_simulados,
    listar_folhas,
    sortear_folhas,
    montar_amostra,
    salvar_csv,
)


def carregar_folhas_ja_usadas(caminho_csv_treino: Path) -> set[str]:
    """
    Lê o CSV de amostra do treino (sortear_amostra.py) e devolve o
    conjunto de nomes de folha já usados ali, para excluir do pool do
    Teste A -- sem essa exclusão, parte da amostra de teste cairia em
    folhas que o modelo já viu no treino, contaminando a métrica (seção
    2.1 do documento de metodologia).
    """
    linhas = ler_amostra(caminho_csv_treino)
    return {linha["folha"] for linha in linhas}


def filtrar_folhas_novas(pool: list[Path], usadas: set[str]) -> list[Path]:
    """
    Remove do pool as folhas cujo nome já aparece em 'usadas' (o conjunto
    devolvido por carregar_folhas_ja_usadas) -- isola o pool do Teste A
    das folhas já vistas pelo modelo no treino (seção 2.1 do documento de
    metodologia).
    """
    return [folha for folha in pool if folha.name not in usadas]


def montar_pool_teste_a(pasta_215: Path, pasta_extra: Path, caminho_csv_treino: Path) -> list[Path]:
    """
    Monta o pool do Teste A (dia a dia): junta as folhas de 215-simu e
    extra (mesma fonte do treino, seção 7.0) e remove as que já foram
    sorteadas para o treino -- garante que nenhuma folha do Teste A já
    tenha sido vista pelo modelo (seção 2.1 do documento de metodologia).
    """
    pool_bruto = montar_pool_simulados(pasta_215, pasta_extra)
    usadas = carregar_folhas_ja_usadas(caminho_csv_treino)
    return filtrar_folhas_novas(pool_bruto, usadas)


def montar_pool_teste_b(pasta_g2: Path) -> list[Path]:
    """
    Monta o pool do Teste B: todas as folhas do corredor G2, já isolado
    desde o sorteio original de treino (nunca entra no pool de treino,
    seção 7.0) -- aqui não precisa filtrar nada, só listar (seção 2.1 do
    documento de metodologia).
    """
    return listar_folhas(pasta_g2)


if __name__ == "__main__":
    SEED = 29
    NUM_QUESTOES_PROVA = 50
    NUM_DIGITOS_INSCRICAO = 7
    PROPORCAO_INSCRICAO = 0.0  # este sorteio não amostra inscrição, só questões

    if config.DATASET_NOVO_SIMULADO is None or config.DATASET_NOVO_SIMULADO_EXTRA is None:
        raise RuntimeError(
            "DATASET_NOVO_SIMULADO / DATASET_NOVO_SIMULADO_EXTRA não configurados "
            "em corretor/config_local.py."
        )
    if not config.DATASET_NOVO_CORREDORES_DIR.get("G2"):
        raise RuntimeError("DATASET_NOVO_CORREDORES_DIR['G2'] não configurado.")

    pool_teste_a = montar_pool_teste_a(
        config.DATASET_NOVO_SIMULADO,
        config.DATASET_NOVO_SIMULADO_EXTRA,
        config.AMOSTRA_SORTEADA_CSV_PATH,
    )
    pool_teste_b = montar_pool_teste_b(config.DATASET_NOVO_CORREDORES_DIR["G2"])

    folhas_a = sortear_folhas(pool_teste_a, 70, SEED)
    folhas_b = sortear_folhas(pool_teste_b, 30, SEED + 1000)

    amostra = montar_amostra(
        folhas_a, folhas_b, NUM_QUESTOES_PROVA, NUM_DIGITOS_INSCRICAO,
        PROPORCAO_INSCRICAO, SEED + 2000,
    )

    salvar_csv(amostra, config.AMOSTRA_TESTE_CSV_PATH)
