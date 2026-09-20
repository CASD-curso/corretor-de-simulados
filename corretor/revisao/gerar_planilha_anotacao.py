import csv
from pathlib import Path

import xlsxwriter

from corretor.config import (
    AMOSTRA_SORTEADA_CSV_PATH,
    PLANILHA_ANOTACAO_PATH,
    RECORTES_BOLHAS_DIR,
    RECORTES_INSCRICAO_DIR,
)
from corretor.revisao.montar_imagem import montar_tira

TMP_IMG_DIR = Path("/tmp/corretor_anotacao_imgs")


def _caminho_bolha(folha, num_questao, letra):
    """
    Monta o caminho do recorte de uma alternativa específica, seguindo a
    mesma convenção de nome já usada em RECORTES_BOLHAS_DIR (ver
    gerar_planilha_revisao._caminho_bolha): <folha_sem_extensao>_Q<num_questao>_<letra>.png

    'folha' chega com extensão (ex.: "...0065.tiff", como está na coluna
    'folha' do CSV de amostra), mas processar_simulados() grava os recortes
    usando o nome SEM extensão (nome_base = nome do arquivo até o primeiro
    ".") -- Path(folha).stem remove só a última extensão, sem esse risco.
    """
    nome_base = Path(folha).stem
    return RECORTES_BOLHAS_DIR / f"{nome_base}_Q{num_questao}_{letra}.png"


def _caminho_digito(folha, pos, dig):
    """
    Monta o caminho do recorte de um dígito específico da grade de
    inscrição, seguindo a mesma convenção já usada em
    RECORTES_INSCRICAO_DIR (ver gerar_planilha_revisao._caminho_digito):
    <folha_sem_extensao>_inscricao_pos<pos>_dig<dig>.png

    Mesmo motivo de _caminho_bolha: os recortes foram gravados sem a
    extensão de 'folha' no nome.
    """
    nome_base = Path(folha).stem
    return RECORTES_INSCRICAO_DIR / f"{nome_base}_inscricao_pos{pos}_dig{dig}.png"


def ler_amostra(caminho_csv: Path) -> list[dict]:
    """
    Lê o CSV gerado por sortear_amostra.py e devolve as linhas já com os
    campos convertidos de volta para seus tipos originais: 'questoes' de
    texto ("12;47") para list[int]; 'sorteia_inscricao' de texto para bool;
    'posicao_inscricao' de texto para int, ou None quando a folha não
    sorteou inscrição (nesse caso salvar_csv gravou string vazia).
    """
    with open(caminho_csv, newline="", encoding="utf-8") as arquivo:
        leitor = csv.DictReader(arquivo)
        linhas = list(leitor)
    for linha in linhas:
        linha["questoes"] = [int(q) for q in linha["questoes"].split(";")]
        linha["sorteia_inscricao"] = linha["sorteia_inscricao"] == "True"
        linha["posicao_inscricao"] = (
            int(linha["posicao_inscricao"]) if linha["posicao_inscricao"] != "" else None
        )
    return linhas


def _montar_itens(linhas: list[dict]) -> list[dict]:
    """
    Converte as linhas de amostra_sorteada.csv (uma por folha) em itens
    individuais (um por questão sorteada, ou por grupo de inscrição
    sorteado) -- o nível de granularidade que gerar_planilha() espera.
    Cada linha de folha vira 2 itens de questão, mais 1 item de inscrição
    (na posição sorteada por sortear_posicao_inscricao) quando
    sorteia_inscricao for True (seção 7.0 do plano).
    """
    itens = []
    for linha in linhas:
        folha = linha["folha"]
        for num_questao in linha["questoes"]:
            crops = [(_caminho_bolha(folha, num_questao, letra), letra) for letra in "ABCDE"]
            itens.append({
                "rotulo": f"{folha} — Q{num_questao}",
                "crops": crops,
                "valores_aceitos": ["A", "B", "C", "D", "E", "BRANCO", "NULA"],
            })
        if linha["sorteia_inscricao"]:
            pos = linha["posicao_inscricao"]
            crops = [(_caminho_digito(folha, pos, dig), str(dig)) for dig in range(10)]
            itens.append({
                "rotulo": f"{folha} — inscrição pos{pos}",
                "crops": crops,
                "valores_aceitos": [str(d) for d in range(10)],
            })
    return itens


def gerar_planilha(itens: list[dict], caminho_saida: Path) -> None:
    """
    Monta a planilha de anotação: uma linha por item (questão sorteada ou
    grupo de inscrição sorteado), com a tira de recortes lado a lado
    (montar_tira, já existente) e uma célula em branco para o anotador
    marcar qual bolha está preenchida.

    'itens' é uma lista de dicts já resolvidos para o nível de item
    individual (não mais por folha) -- cada um com 'rotulo', 'crops'
    (lista de (caminho, label) pronta para montar_tira) e
    'valores_aceitos' (as letras/dígitos válidos daquele item, para a
    validação da célula).
    """
    wb = xlsxwriter.Workbook(str(caminho_saida))
    ws = wb.add_worksheet("Anotação")
    ws.set_column("A:A", 20)
    ws.set_column("B:B", 30)
    ws.set_column("C:C", 46)

    fmt_header = wb.add_format({"bold": True, "bg_color": "#D9E1F2", "border": 1})
    fmt_celula = wb.add_format({"border": 1, "valign": "vcenter"})
    fmt_input = wb.add_format({"border": 1, "bg_color": "#FFFFFF"})

    for col, titulo in enumerate(["Item", "Marcada", "Recortes"]):
        ws.write(0, col, titulo, fmt_header)

    for i, item in enumerate(itens):
        r = i + 1
        ws.set_row(r, 40)
        ws.write(r, 0, item["rotulo"], fmt_celula)
        ws.write(r, 1, "", fmt_input)

        tira = montar_tira(item["crops"])
        img_path = TMP_IMG_DIR / f"item_{i}.png"
        tira.save(img_path)
        ws.insert_image(r, 2, str(img_path), {"x_offset": 4, "y_offset": 2})

        ws.data_validation(r, 1, r, 1, {
            "validate": "list",
            "source": item["valores_aceitos"],
            "dropdown": False,
        })

    wb.close()


def gerar_planilha_anotacao(caminho_csv: Path, caminho_saida: Path) -> None:
    """
    Ponto de entrada do arquivo: lê a amostra sorteada, monta os itens
    individuais e gera a planilha de anotação pronta para o revisor
    preencher.
    """
    TMP_IMG_DIR.mkdir(parents=True, exist_ok=True)
    linhas = ler_amostra(caminho_csv)
    itens = _montar_itens(linhas)
    gerar_planilha(itens, caminho_saida)


if __name__ == "__main__":
    gerar_planilha_anotacao(AMOSTRA_SORTEADA_CSV_PATH, PLANILHA_ANOTACAO_PATH)
