"""
Monta a planilha intermediaria do item 5 (correcao manual sem quebrar as
estatisticas): duas abas.

  - "Checkup": visao geral do lote, e a secao das folhas descartadas no
    alinhamento -- essas nao tem bolha nenhuma extraida, entao nao entram
    na lista de correcao; so podem ser resolvidas reescaneando ou
    transcrevendo a mao (Inscricao_Manual + Respostas_Manual).
  - "Correcao": uma linha por ITEM pendente (questao ou posicao de
    inscricao), nao por aluno -- com os recortes reais lado a lado pra
    comparacao visual, e um campo de texto livre validado pra digitar a
    correcao.

Essa planilha nao calcula nota nem estatistica. E so o ponto onde a revisao
humana acontece, antes do calculo em corretor.relatorio.gerar_excel.
"""
from pathlib import Path

import xlsxwriter

from corretor.config import (
    NUM_DIGITOS_INSCRICAO,
    NUM_QUESTOES,
    PLANILHA_REVISAO_PATH,
    RECORTES_BOLHAS_DIR,
    RECORTES_INSCRICAO_DIR,
)
from corretor.inferencia.inferir_completo import gerar_planilha_unificada
from corretor.revisao.montar_imagem import montar_tira

TMP_IMG_DIR = Path("/tmp/corretor_revisao_imgs")

CODIGOS_QUESTAO = "A/B/C/D/E/BRANCO/NULA"
CODIGOS_INSCRICAO = "0-9/?"
VALORES_QUESTAO = ["A", "B", "C", "D", "E", "BRANCO", "NULA"]
VALORES_INSCRICAO = [str(d) for d in range(10)] + ["?"]

IMAGEM_CORROMPIDA = "Imagem corrompida (sem preview)"


def _caminho_bolha(simulado, num_questao, letra):
    return RECORTES_BOLHAS_DIR / f"{simulado}_Q{num_questao}_{letra}.png"


def _caminho_digito(simulado, pos, dig):
    return RECORTES_INSCRICAO_DIR / f"{simulado}_inscricao_pos{pos}_dig{dig}.png"


def _motivo_questao(resposta, ilegivel):
    if ilegivel:
        return IMAGEM_CORROMPIDA
    if resposta == "EM BRANCO":
        return "Em branco (abaixo do limiar)"
    if resposta == "NULA(MARCADAS>1)":
        return "Dupla marcação (NULA)"
    return None  # resposta valida, nao precisa de revisao


def _motivo_inscricao(digito, ilegivel):
    if ilegivel:
        return IMAGEM_CORROMPIDA
    if digito == "?":
        return "Em branco ou dupla marcação (ambígua)"
    return None


def _listar_itens_pendentes(linhas, bolhas_ilegiveis, digitos_ilegiveis, falhas_alinhamento):
    """
    Uma entrada por questao/posicao que precisa de revisao -- nunca por
    aluno. Simulados descartados no alinhamento ficam de fora: nao tem
    bolha extraida, entao nao ha nada aqui pra revisar questao por questao.
    """
    itens = []
    for linha in linhas:
        simulado = linha["Simulado"]
        if simulado in falhas_alinhamento:
            continue

        ilegiveis_q = set(bolhas_ilegiveis.get(simulado, []))
        for q in range(1, NUM_QUESTOES + 1):
            campo = f"Q{q}"
            resposta = linha.get(campo, "EM BRANCO")
            motivo = _motivo_questao(resposta, campo in ilegiveis_q)
            if motivo:
                itens.append({
                    "simulado": simulado, "campo": campo, "tipo": "questao",
                    "motivo": motivo, "num_questao": q,
                })

        ilegiveis_pos = set(digitos_ilegiveis.get(simulado, []))
        inscricao = linha.get("Inscricao", "")
        for pos in range(NUM_DIGITOS_INSCRICAO):
            campo = f"pos{pos}"
            digito = inscricao[pos] if pos < len(inscricao) else "?"
            motivo = _motivo_inscricao(digito, campo in ilegiveis_pos)
            if motivo:
                itens.append({
                    "simulado": simulado, "campo": campo, "tipo": "inscricao",
                    "motivo": motivo, "pos": pos,
                })
    return itens


def gerar_planilha_revisao(caminho_saida=None):
    if caminho_saida is None:
        caminho_saida = PLANILHA_REVISAO_PATH
    TMP_IMG_DIR.mkdir(parents=True, exist_ok=True)

    linhas, bolhas_ilegiveis, digitos_ilegiveis, falhas_alinhamento = gerar_planilha_unificada()
    itens = _listar_itens_pendentes(linhas, bolhas_ilegiveis, digitos_ilegiveis, falhas_alinhamento)
    simulados_com_pendencia = sorted({it["simulado"] for it in itens})
    simulados_sem_pendencia = len(linhas) - len(simulados_com_pendencia) - len(falhas_alinhamento)

    wb = xlsxwriter.Workbook(str(caminho_saida))

    fmt_titulo = wb.add_format({"bold": True, "font_size": 13})
    fmt_banner = wb.add_format({"bold": True, "bg_color": "#FFF2CC", "border": 1, "valign": "vcenter"})
    fmt_header = wb.add_format({"bold": True, "bg_color": "#D9E1F2", "border": 1, "valign": "vcenter"})
    fmt_celula = wb.add_format({"border": 1, "valign": "vcenter"})
    fmt_wrap = wb.add_format({"border": 1, "valign": "vcenter", "text_wrap": True})
    fmt_link = wb.add_format({"border": 1, "valign": "vcenter", "font_color": "blue", "underline": True})
    fmt_metrica = wb.add_format({"bold": True})
    fmt_input = wb.add_format({"border": 1, "bg_color": "#FFFFFF", "valign": "vcenter"})

    # ================= aba Checkup =================
    ck = wb.add_worksheet("Checkup")
    ck.set_column("A:A", 26)
    ck.set_column("B:D", 30)

    ck.write("A1", "Checkup do lote", fmt_titulo)
    ck.write("A3", "Simulados processados", fmt_metrica)
    ck.write("B3", len(linhas))
    ck.write("A4", "Sem nenhuma pendência", fmt_metrica)
    ck.write("B4", simulados_sem_pendencia)
    ck.write("A5", "Com pendência corrigível (ver aba Correção)", fmt_metrica)
    ck.write("B5", len(simulados_com_pendencia))
    ck.write("A6", "Descartados no alinhamento (não têm bolha extraída)", fmt_metrica)
    ck.write("B6", len(falhas_alinhamento))

    row = 8
    if falhas_alinhamento:
        ck.merge_range(
            row, 0, row, 3,
            "Descartados no alinhamento — reescaneie a folha OU transcreva "
            "manualmente pelo link abaixo (fica pendente até uma das duas opções)",
            fmt_banner,
        )
        row += 1
        for col, titulo in enumerate([
            "Simulado", "Link_Original",
            f"Inscrição_Manual ({NUM_DIGITOS_INSCRICAO} dígitos)",
            "Respostas_Manual (todas as letras em sequência)",
        ]):
            ck.write(row, col, titulo, fmt_header)
        row += 1
        for simulado in sorted(falhas_alinhamento.keys()):
            ck.write(row, 0, simulado, fmt_celula)
            url = f"https://drive.google.com/drive/search?q={simulado}.tiff"
            ck.write_url(row, 1, url, fmt_link, string="Ver scan original")
            ck.write(row, 2, "", fmt_input)
            ck.write(row, 3, "", fmt_input)
            row += 1
        row += 1

    # ================= aba Correcao =================
    cr = wb.add_worksheet("Correção")
    cr.set_column("A:A", 20)
    cr.set_column("B:B", 10)
    cr.set_column("C:C", 30)
    cr.set_column("D:D", 14)
    cr.set_column("E:E", 46)

    n_itens = len(itens)
    primeira_linha = 2  # 0-idx, logo apos o header (sem pular linha)

    if n_itens:
        ultima_linha = primeira_linha + n_itens - 1
        faixa_corrigido = f"D{primeira_linha + 1}:D{ultima_linha + 1}"
        banner_formula = (
            f'=CONCATENATE("Faltam ", COUNTBLANK({faixa_corrigido}), " de {n_itens} revisar   |   '
            f'Questão: {CODIGOS_QUESTAO} — Inscrição: {CODIGOS_INSCRICAO}")'
        )
        cr.merge_range(0, 0, 0, 4, banner_formula, fmt_banner)
    else:
        cr.merge_range(0, 0, 0, 4, "Nenhum item pendente — pode seguir direto para o cálculo.", fmt_banner)
    cr.set_row(0, 22)

    for col, titulo in enumerate(["Simulado", "Campo", "Motivo", "Corrigido", "Alternativas"]):
        cr.write(1, col, titulo, fmt_header)

    linha_por_simulado = {}  # simulado -> primeira linha (0-idx) na aba Correcao

    for i, item in enumerate(itens):
        r = primeira_linha + i
        cr.set_row(r, 40)
        cr.write(r, 0, item["simulado"], fmt_celula)
        cr.write(r, 1, item["campo"], fmt_celula)
        cr.write(r, 2, item["motivo"], fmt_wrap)
        cr.write(r, 3, "", fmt_input)

        if item["tipo"] == "questao":
            valores_aceitos = VALORES_QUESTAO
            if item["motivo"] == IMAGEM_CORROMPIDA:
                url = f"https://drive.google.com/drive/search?q={item['simulado']}.tiff"
                cr.write_url(r, 4, url, fmt_link, string="Sem preview — abrir scan original")
            else:
                crops = [(_caminho_bolha(item["simulado"], item["num_questao"], letra), letra)
                         for letra in "ABCDE"]
                tira = montar_tira(crops)
                img_path = TMP_IMG_DIR / f"item_{i}.png"
                tira.save(img_path)
                cr.insert_image(r, 4, str(img_path), {"x_offset": 4, "y_offset": 2})
        else:
            valores_aceitos = VALORES_INSCRICAO
            if item["motivo"] == IMAGEM_CORROMPIDA:
                url = f"https://drive.google.com/drive/search?q={item['simulado']}.tiff"
                cr.write_url(r, 4, url, fmt_link, string="Sem preview — abrir scan original")
            else:
                crops = [(_caminho_digito(item["simulado"], item["pos"], dig), str(dig))
                         for dig in range(10)]
                tira = montar_tira(crops)
                img_path = TMP_IMG_DIR / f"item_{i}.png"
                tira.save(img_path)
                cr.insert_image(r, 4, str(img_path), {"x_offset": 4, "y_offset": 2})

        cr.data_validation(r, 3, r, 3, {
            "validate": "list",
            "source": valores_aceitos,
            "dropdown": False,
            "error_message": "Digite um dos códigos válidos (ver legenda no topo).",
        })

        linha_por_simulado.setdefault(item["simulado"], r)

    cr.freeze_panes(2, 0)

    # volta pra aba Checkup: lista de pendencias, com link interno pra Correcao
    if simulados_com_pendencia:
        ck.merge_range(row, 0, row, 2, "Simulados com pendência corrigível", fmt_banner)
        row += 1
        for col, titulo in enumerate(["Simulado", "Itens pendentes", "Ir para Correção"]):
            ck.write(row, col, titulo, fmt_header)
        row += 1
        contagem = {}
        for item in itens:
            contagem[item["simulado"]] = contagem.get(item["simulado"], 0) + 1
        for simulado in simulados_com_pendencia:
            ck.write(row, 0, simulado, fmt_celula)
            ck.write(row, 1, contagem[simulado], fmt_celula)
            destino_linha = linha_por_simulado[simulado] + 1  # 1-idx pro Excel
            ck.write_url(row, 2, f"internal:'Correção'!A{destino_linha}", fmt_link, string="Abrir →")
            row += 1

    wb.close()
    print(f"Planilha de revisão gerada: {caminho_saida}")
    print(f"  {len(simulados_com_pendencia)} simulado(s) com pendência corrigível ({n_itens} item(ns) no total).")
    print(f"  {len(falhas_alinhamento)} simulado(s) descartado(s) no alinhamento (aba Checkup).")

    # Devolve tambem 'linhas' -- o resultado cru que essa mesma chamada ja
    # calculou pra montar a planilha. Sem isso, quem for aplicar a revisao
    # depois (aplicar_revisao) precisaria chamar gerar_planilha_unificada()
    # de novo so pra reconstruir o que ja estava aqui, rodando a inferencia
    # (CNN no lote inteiro) uma segunda vez sem necessidade.
    return caminho_saida, linhas


if __name__ == "__main__":
    gerar_planilha_revisao()
