import csv # csv import might still be needed for other dependencies in DictWriter types, but DictWriter isn't needed here. Removed.
import json
from collections import defaultdict
from pathlib import Path

# REMOVED RESULTADOS_CSV_PATH from import
from corretor.config import SIMULADOS_DIR, NUM_QUESTOES, FALHAS_ALINHAMENTO_PATH
from corretor.inferencia.inferir_simulado_e_inscricao import inferir_inscricoes, inferir_simulados


def _ler_falhas_alinhamento():
    """
    Lê o registro de folhas descartadas na etapa de alinhamento (item 4),
    gravado por corretor.visao.extracao_em_lote.processar_simulados().
    Se o arquivo não existir (ex.: alguém rodou só a inferência sem passar
    pela extração nesta sessão), retorna vazio — não é um erro.
    """
    caminho = Path(FALHAS_ALINHAMENTO_PATH)
    if not caminho.exists():
        return {}
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)


def gerar_planilha_unificada():
    """
    Retorna (linhas, bolhas_ilegiveis, digitos_ilegiveis, falhas_alinhamento).

    Os três últimos são as mesmas auditorias do item 4, sem processar — o
    item 5 (gerar_planilha_revisao) precisa deles "crus" pra saber
    exatamente qual questão/posição de qual simulado tem imagem pra montar,
    não só o texto já concatenado que vai pra coluna Bolhas_Ilegiveis.
    """
    # 1. Obter os dados de inscrição e de alinhamento (cada um vem com sua
    # respectiva auditoria de falha silenciosa — item 4 do plano)
    dados_inscricao, digitos_ilegiveis = inferir_inscricoes(exportar_csv=False)

    # 2. Obter as respostas das questões
    dados_respostas, bolhas_ilegiveis = inferir_simulados(exportar_csv=False)

    # 2b. Obter as folhas descartadas antes mesmo de chegar à inferência
    falhas_alinhamento = _ler_falhas_alinhamento()

    # 3. Consolidar os dados
    linhas = []
    # Pegamos todos os simulados encontrados em qualquer uma das três fontes.
    # Antes, uma folha que falhasse no alinhamento simplesmente não entrava
    # aqui e desaparecia do resultado sem deixar rastro.
    todos_simulados = (
        set(dados_inscricao.keys())
        .union(dados_respostas.keys())
        .union(falhas_alinhamento.keys())
    )

    for simulado in sorted(todos_simulados):
        # Pega a inscrição (ou 'NAO_LIDO' se falhou)
        inscricao = dados_inscricao.get(simulado, "NAO_LIDO")

        # Pega a lista de respostas (ou lista vazia se falhou)
        respostas = dados_respostas.get(simulado, [])

        # TRAVA DE SEGURANÇA: Completa com "BRANCOM"
        while len(respostas) < NUM_QUESTOES:
            respostas.append("BRANCOM")

        # TRAVA DE SEGURANÇA 2: Corta se por acaso vierem mais respostas
        respostas = respostas[:NUM_QUESTOES]

        # --- AUDITORIA DE FALHAS SILENCIOSAS (item 4) ---
        motivo_alinhamento = falhas_alinhamento.get(simulado)
        alinhamento_ok = "Não" if motivo_alinhamento else "Sim"

        partes_ilegiveis = []
        if simulado in digitos_ilegiveis:
            partes_ilegiveis.append("Inscrição:" + ",".join(digitos_ilegiveis[simulado]))
        if simulado in bolhas_ilegiveis:
            partes_ilegiveis.append("Respostas:" + ",".join(bolhas_ilegiveis[simulado]))
        bolhas_ilegiveis_txt = "; ".join(partes_ilegiveis)

        # --- LÓGICA DO LINK DE REVISÃO ---
        tem_erro = (
            ("?" in inscricao)
            or ("NAO_LIDO" in inscricao)
            or ("BRANCOM" in respostas)
            or ("MULTM" in respostas)
            or bool(motivo_alinhamento)
            or bool(bolhas_ilegiveis_txt)
        )

        if tem_erro:
            # Cria um link que pesquisa automaticamente o nome do arquivo no seu Drive
            url_drive = f"https://drive.google.com/drive/search?q={simulado}.tiff"
            link_revisao = f'=HYPERLINK("{url_drive}"; "Ver Cartão")'
        else:
            link_revisao = ""
        # ---------------------------------

        linha = {
            "Simulado": simulado,
            "Inscricao": inscricao,
            "Link_Revisao": link_revisao,
            "Alinhamento_OK": alinhamento_ok,
            "Motivo_Alinhamento": motivo_alinhamento or "",
            "Bolhas_Ilegiveis": bolhas_ilegiveis_txt,
        }

        # Adiciona as questões (Q1, Q2, etc.) dinamicamente até NUM_QUESTOES
        for idx, resposta in enumerate(respostas):
            linha[f"Q{idx+1}"] = resposta

        linhas.append(linha)

    # 4. REMOVED SAVING TO CSV. Only consolidate data in memory.
    if not linhas:
        print("Nenhum dado consolidate.")
        return [], {}, {}, {}

    print(f"Dados brutos consolidados em memória ({len(linhas)} simulados).")

    # RETORNO IMPORTANTE: o próximo script do Excel (ou o checkpoint do item
    # 5) vai consumir essa lista, mais as três auditorias cruas!
    return linhas, bolhas_ilegiveis, digitos_ilegiveis, falhas_alinhamento

if __name__ == "__main__":
    # Running this directly now won't save a file, just test memory creation
    data, _, _, _ = gerar_planilha_unificada()
    print(f"Retornadas {len(data)} linhas em memória.")
