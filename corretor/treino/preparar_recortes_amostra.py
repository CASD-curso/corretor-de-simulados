"""
Passo que faltava entre sortear_amostra.py e gerar_planilha_anotacao.py:
localiza no disco cada folha listada em amostra_sorteada.csv, copia todas
para SIMULADOS_DIR e roda a extração de bolhas (processar_simulados) sobre
elas -- sem isso, RECORTES_BOLHAS_DIR/RECORTES_INSCRICAO_DIR ficam vazias e
gerar_planilha_anotacao.py só consegue inserir imagens quebradas (X
vermelho) na planilha.

Uso, a partir da raiz do repositório:
    python -m corretor.treino.preparar_recortes_amostra
"""
from pathlib import Path
import shutil

from corretor import config
from corretor.revisao.gerar_planilha_anotacao import ler_amostra
from corretor.treino.sortear_amostra import montar_pool_simulados, montar_pool_vestibular
from corretor.visao.extracao_em_lote import processar_simulados


def montar_indice_folhas(pool: list[Path]) -> dict[str, Path]:
    """
    Constrói um dicionário nome_do_arquivo -> caminho completo, a partir de
    um pool de folhas (lista de Path vinda de montar_pool_simulados ou
    montar_pool_vestibular). Usado para localizar, a partir do CSV de
    amostra (que só guarda o nome), onde cada folha sorteada realmente
    está no disco.

    Levanta ValueError se dois arquivos diferentes tiverem o mesmo nome
    (.name) -- ambiguidade que não dá para resolver sozinho, porque não
    saberíamos qual dos dois é a folha que o CSV se refere.
    """
    indice = {}
    for caminho in pool:
        if caminho.name in indice and indice[caminho.name] != caminho:
            raise ValueError(
                f"Nome de arquivo duplicado em pastas diferentes: '{caminho.name}' "
                f"aparece em '{indice[caminho.name]}' e '{caminho}'."
            )
        indice[caminho.name] = caminho
    return indice


def localizar_folhas_da_amostra(
    linhas_csv: list[dict],
    indice_simulados: dict[str, Path],
    indice_vestibular: dict[str, Path],
) -> list[Path]:
    """
    Para cada linha do CSV de amostra (já lida por ler_amostra, com o campo
    'folha' = nome do arquivo e 'contexto' = "simulados" ou "vestibular"),
    localiza o caminho completo no índice correspondente ao contexto.

    Usar o índice certo por contexto (em vez de um índice único combinado)
    evita que uma folha de vestibular seja confundida com uma de simulados
    que, por coincidência, tivesse o mesmo nome -- coleções diferentes,
    então mesmo nome em contextos diferentes não é tratado como duplicata.
    """
    caminhos = []
    for linha in linhas_csv:
        indice = indice_simulados if linha["contexto"] == "simulados" else indice_vestibular
        nome = linha["folha"]
        if nome not in indice:
            raise FileNotFoundError(
                f"Folha '{nome}' (contexto '{linha['contexto']}') não encontrada "
                f"nas pastas configuradas em config_local.py."
            )
        caminhos.append(indice[nome])
    return caminhos


def copiar_folhas_para_entrada(caminhos: list[Path], pasta_destino: Path) -> None:
    """
    Copia cada folha localizada para pasta_destino (SIMULADOS_DIR, a pasta
    que processar_simulados() lê). Cria a pasta se não existir.

    Levanta RuntimeError sem copiar nada, se pasta_destino já tiver
    arquivos .tif/.tiff -- evita misturar uma rodada antiga (outra amostra
    sorteada, ou sobra do fluxo principal de correção) com a rodada atual,
    o que geraria recortes de folhas que não estão listadas na amostra e
    confundiria a planilha de anotação.
    """
    pasta_destino.mkdir(parents=True, exist_ok=True)

    existentes = list(pasta_destino.glob("*.tif*"))
    if existentes:
        raise RuntimeError(
            f"'{pasta_destino}' já contém {len(existentes)} arquivo(s) .tif/.tiff. "
            "Esvazie a pasta antes de rodar (ou mova o que já estava lá), para não "
            "misturar folhas de outra rodada com a amostra atual."
        )

    for origem in caminhos:
        shutil.copy(origem, pasta_destino / origem.name)


def preparar_recortes_amostra() -> None:
    """
    Ponto de entrada: lê amostra_sorteada.csv, localiza cada folha listada
    nas pastas configuradas em config_local.py, copia todas para
    SIMULADOS_DIR e roda a extração de bolhas (processar_simulados) sobre
    elas -- o passo que faltava entre sortear_amostra.py e
    gerar_planilha_anotacao.py, que só consegue montar as imagens da
    planilha se RECORTES_BOLHAS_DIR/RECORTES_INSCRICAO_DIR já tiverem os
    recortes dessas folhas.
    """
    if config.DATASET_NOVO_SIMULADO is None or config.DATASET_NOVO_SIMULADO_EXTRA is None:
        raise RuntimeError(
            "DATASET_NOVO_SIMULADO / DATASET_NOVO_SIMULADO_EXTRA não configurados "
            "em corretor/config_local.py."
        )
    if not config.DATASET_NOVO_CORREDORES_DIR:
        raise RuntimeError(
            "DATASET_NOVO_CORREDORES_DIR não configurado em corretor/config_local.py."
        )

    linhas_csv = ler_amostra(config.AMOSTRA_SORTEADA_CSV_PATH)

    pool_simulados = montar_pool_simulados(
        config.DATASET_NOVO_SIMULADO, config.DATASET_NOVO_SIMULADO_EXTRA
    )
    pool_vestibular = montar_pool_vestibular(
        list(config.DATASET_NOVO_CORREDORES_DIR.values())
    )
    indice_simulados = montar_indice_folhas(pool_simulados)
    indice_vestibular = montar_indice_folhas(pool_vestibular)

    caminhos = localizar_folhas_da_amostra(linhas_csv, indice_simulados, indice_vestibular)
    print(f"{len(caminhos)} folha(s) localizada(s) a partir de {config.AMOSTRA_SORTEADA_CSV_PATH}.")

    copiar_folhas_para_entrada(caminhos, config.SIMULADOS_DIR)
    print(f"Folhas copiadas para '{config.SIMULADOS_DIR}'. Extraindo bolhas...")

    processar_simulados(extrair_respostas=True, extrair_inscricao=True)


if __name__ == "__main__":
    preparar_recortes_amostra()
