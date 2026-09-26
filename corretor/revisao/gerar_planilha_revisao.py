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

Inscricao repetida (item 12 do plano): duas ou mais folhas lidas com o
mesmo numero de inscricao aparecem num quadro da aba Checkup, a direita da
lista de pendencias -- o numero repetido na primeira coluna e, na mesma
linha, o link de cada folha no Drive com uma celula "Excluir?". Marcar SIM
tira aquela folha do calculo (e risca os itens dela na aba Correcao). Se nao
for a mesma folha duas vezes, e sim outro aluno com a inscricao lida errado,
o operador corrige o numero na linha "Inscricao" dessa folha na aba Correcao
e confere, na coluna Situacao do quadro, que a repeticao sumiu.

Essa planilha nao calcula nota nem estatistica. E so o ponto onde a revisao
humana acontece, antes do calculo em corretor.relatorio.gerar_excel.

Modo escuro (decisao do usuario, 23/09/2026): fundo preto e texto branco em
toda a planilha, nas duas abas. Duas excecoes deliberadas, para nao perder
sinalizacao util: as celulas de INPUT (onde o operador digita a correcao)
ficam num cinza escuro (#262626) em vez de preto puro, para continuar
visualmente diferentes de uma celula de leitura -- e o banner de alinhamento
mantem uma borda amarela, para nao perder o alerta visual. Se preferir preto
liso em tudo, sem nenhuma excecao, e so pedir.
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

# Índice (0-idx) da última coluna que uma aba do Excel pode ter: XFD.
ULTIMA_COLUNA_EXCEL = 16383

CODIGOS_QUESTAO = "A/B/C/D/E/BRANCO/MULT"
CODIGOS_INSCRICAO = "0-9/?"
VALORES_QUESTAO = ["A", "B", "C", "D", "E", "BRANCO", "MULT"]
VALORES_INSCRICAO = [str(d) for d in range(10)] + ["?"]

IMAGEM_CORROMPIDA = "Imagem corrompida (sem preview)"
INSCRICAO_AMBIGUA = "Em branco ou dupla marcação (ambígua)"

# Item de inscricao repetida na aba Correcao: o campo e a inscricao inteira,
# nao uma posicao, porque quem le errado e a folha toda, nao um digito que o
# modelo marcou como duvidoso.
CAMPO_INSCRICAO_REPETIDA = "Inscricao"
VALOR_EXCLUIR = "SIM"
EXCLUIDO = "EXCLUÍDO"


def _letra(col):
    """Indice de coluna 0-idx -> letra do Excel (0 -> A, 26 -> AA)."""
    letras = ""
    col += 1
    while col:
        col, resto = divmod(col - 1, 26)
        letras = chr(ord("A") + resto) + letras
    return letras


def _caminho_bolha(simulado, num_questao, letra):
    return RECORTES_BOLHAS_DIR / f"{simulado}_Q{num_questao}_{letra}.png"


def _caminho_digito(simulado, pos, dig):
    return RECORTES_INSCRICAO_DIR / f"{simulado}_inscricao_pos{pos}_dig{dig}.png"


def _motivo_questao(resposta, ilegivel):
    if ilegivel:
        return IMAGEM_CORROMPIDA
    if resposta == "BRANCOM":
        return "Em branco (BRANCOM — abaixo do limiar)"
    if resposta == "MULTM":
        return "Dupla marcação (MULTM)"
    return None  # resposta valida, nao precisa de revisao


def _motivo_inscricao(digito, ilegivel):
    if ilegivel:
        return IMAGEM_CORROMPIDA
    if digito == "?":
        return INSCRICAO_AMBIGUA
    return None


def _inscricoes_repetidas(linhas, falhas_alinhamento):
    """
    {inscricao: [simulados]} so para os numeros lidos em mais de uma folha.

    So entra inscricao lida por inteiro (todos os digitos, sem '?'): duas
    folhas com '12?4567' nao sao necessariamente o mesmo numero, e essas ja
    vao para a aba Correcao pela posicao ambigua.
    """
    por_inscricao = {}
    for linha in linhas:
        simulado = linha["Simulado"]
        inscricao = linha.get("Inscricao", "")
        if simulado in falhas_alinhamento:
            continue
        if len(inscricao) != NUM_DIGITOS_INSCRICAO or not inscricao.isdigit():
            continue
        por_inscricao.setdefault(inscricao, []).append(simulado)
    return {insc: sims for insc, sims in sorted(por_inscricao.items()) if len(sims) > 1}


def _listar_itens_pendentes(linhas, bolhas_ilegiveis, digitos_ilegiveis, falhas_alinhamento, repetidas):
    """
    Uma entrada por questao/posicao que precisa de revisao -- nunca por
    aluno. Simulados descartados no alinhamento ficam de fora: nao tem
    bolha extraida, entao nao ha nada aqui pra revisar questao por questao.

    Cada folha com inscricao repetida ganha tambem um item da inscricao
    inteira, onde o operador digita o numero certo se ela foi lida errado.
    """
    repetida_de = {sim: insc for insc, sims in repetidas.items() for sim in sims}
    itens = []
    for linha in linhas:
        simulado = linha["Simulado"]
        if simulado in falhas_alinhamento:
            continue

        ilegiveis_q = set(bolhas_ilegiveis.get(simulado, []))
        for q in range(1, NUM_QUESTOES + 1):
            campo = f"Q{q}"
            resposta = linha.get(campo, "BRANCOM")
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

        if simulado in repetida_de:
            itens.append({
                "simulado": simulado, "campo": CAMPO_INSCRICAO_REPETIDA, "tipo": "repetida",
                "motivo": (f"Inscrição repetida ({repetida_de[simulado]}) — só corrija se "
                           f"esta folha foi lida errado; se ela estiver certa, deixe em branco"),
            })
    return itens


def gerar_planilha_revisao(caminho_saida=None):
    if caminho_saida is None:
        caminho_saida = PLANILHA_REVISAO_PATH
    TMP_IMG_DIR.mkdir(parents=True, exist_ok=True)

    linhas, bolhas_ilegiveis, digitos_ilegiveis, falhas_alinhamento = gerar_planilha_unificada()
    repetidas = _inscricoes_repetidas(linhas, falhas_alinhamento)
    itens = _listar_itens_pendentes(linhas, bolhas_ilegiveis, digitos_ilegiveis, falhas_alinhamento, repetidas)
    simulados_com_pendencia = sorted({it["simulado"] for it in itens})
    simulados_sem_pendencia = len(linhas) - len(simulados_com_pendencia) - len(falhas_alinhamento)

    wb = xlsxwriter.Workbook(str(caminho_saida))

    PRETO = "#000000"
    BRANCO = "#FFFFFF"
    CINZA_INPUT = "#262626"  # exceção deliberada -- ver docstring do módulo

    fmt_titulo = wb.add_format({"bold": True, "font_size": 13, "bg_color": PRETO, "font_color": BRANCO})
    fmt_banner = wb.add_format({
        "bold": True, "bg_color": PRETO, "font_color": BRANCO, "valign": "vcenter",
        "border": 2, "border_color": "#FFC107",  # exceção deliberada -- mantém o alerta visual
    })
    fmt_header = wb.add_format({
        "bold": True, "bg_color": PRETO, "font_color": BRANCO, "border": 1,
        "border_color": BRANCO, "valign": "vcenter",
    })
    fmt_celula = wb.add_format({"border": 1, "border_color": BRANCO, "bg_color": PRETO, "font_color": BRANCO, "valign": "vcenter"})
    fmt_wrap = wb.add_format({
        "border": 1, "border_color": BRANCO, "bg_color": PRETO, "font_color": BRANCO,
        "valign": "vcenter", "text_wrap": True,
    })
    fmt_link = wb.add_format({
        "border": 1, "border_color": BRANCO, "bg_color": PRETO, "font_color": "#4EA8FF", "underline": True, "valign": "vcenter",
    })
    fmt_metrica = wb.add_format({"bold": True, "bg_color": PRETO, "font_color": BRANCO})
    fmt_valor = wb.add_format({"bg_color": PRETO, "font_color": BRANCO})
    fmt_input = wb.add_format({"border": 1, "border_color": BRANCO, "bg_color": CINZA_INPUT, "font_color": BRANCO, "valign": "vcenter"})
    # Fundo das colunas inteiras: vale para toda célula que não recebe um
    # formato próprio -- inclusive a área vazia em volta das tabelas, que
    # antes ficava branca (26/09/2026). Toda chamada de set_column() abaixo
    # repete esse formato: sem ele, a chamada que só ajusta a largura
    # apagaria o fundo preto daquela coluna.
    fmt_fundo = wb.add_format({"bg_color": PRETO, "font_color": BRANCO})
    fmt_banner_wrap = wb.add_format({
        "bold": True, "bg_color": PRETO, "font_color": BRANCO, "valign": "vcenter", "text_wrap": True,
        "border": 2, "border_color": "#FFC107",
    })
    # "@" = formato texto: sem ele o Excel guarda '0123456' como o numero
    # 123456 e perde o zero da frente.
    fmt_input_texto = wb.add_format({
        "border": 1, "border_color": BRANCO, "bg_color": CINZA_INPUT, "font_color": BRANCO,
        "valign": "vcenter", "num_format": "@",
    })
    # Linha de folha excluida no Checkup: cinza e riscada na aba Correcao.
    fmt_excluido = wb.add_format({"font_color": "#666666", "font_strikeout": True})

    # ================= aba Checkup =================
    ck = wb.add_worksheet("Checkup")
    ck.set_column(0, ULTIMA_COLUNA_EXCEL, None, fmt_fundo)
    ck.set_column("A:A", 26, fmt_fundo)
    ck.set_column("B:D", 30, fmt_fundo)

    ck.write("A1", "Checkup do lote", fmt_titulo)
    ck.write("A3", "Simulados processados", fmt_metrica)
    ck.write("B3", len(linhas), fmt_valor)
    ck.write("A4", "Sem nenhuma pendência", fmt_metrica)
    ck.write("B4", simulados_sem_pendencia, fmt_valor)
    ck.write("A5", "Com pendência corrigível (ver aba Correção)", fmt_metrica)
    ck.write("B5", len(simulados_com_pendencia), fmt_valor)
    ck.write("A6", "Descartados no alinhamento (não têm bolha extraída)", fmt_metrica)
    ck.write("B6", len(falhas_alinhamento), fmt_valor)
    ck.write("A7", "Inscrições repetidas (ver quadro à direita)", fmt_metrica)
    ck.write("B7", len(repetidas), fmt_valor)

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

    # Posicao do quadro de inscricoes repetidas no Checkup (0-idx): comeca na
    # mesma linha da lista de pendencias, a partir da coluna E. Precisa ser
    # conhecida antes da aba Correcao, cuja coluna Situacao aponta para ele.
    linha_aviso_rep = row
    col_rep = 4
    max_por_grupo = max((len(sims) for sims in repetidas.values()), default=0)
    col_situacao_rep = col_rep + 1 + 2 * max_por_grupo
    primeira_linha_rep = linha_aviso_rep + 2
    ultima_linha_rep = primeira_linha_rep + len(repetidas) - 1

    # ================= aba Correcao =================
    cr = wb.add_worksheet("Correção")
    cr.set_column(0, ULTIMA_COLUNA_EXCEL, None, fmt_fundo)
    cr.set_column("A:A", 20, fmt_fundo)
    cr.set_column("B:B", 10, fmt_fundo)
    cr.set_column("C:C", 30, fmt_fundo)
    cr.set_column("D:D", 14, fmt_fundo)
    cr.set_column("E:E", 46, fmt_fundo)
    cr.set_column("F:F", 22, fmt_fundo)
    cr.set_column("G:G", 12, fmt_fundo)

    n_itens = len(itens)
    primeira_linha = 2  # 0-idx, logo apos o header (sem pular linha)

    if n_itens:
        ultima_linha = primeira_linha + n_itens - 1
        faixa_campo = f"B{primeira_linha + 1}:B{ultima_linha + 1}"
        faixa_corrigido = f"D{primeira_linha + 1}:D{ultima_linha + 1}"
        faixa_situacao = f"G{primeira_linha + 1}:G{ultima_linha + 1}"
        # Nao contam como "falta revisar": o item de inscricao repetida (em
        # branco e resposta valida -- a folha estava certa) e os itens de
        # folha excluida no Checkup.
        contar = f'"{CAMPO_INSCRICAO_REPETIDA}"'
        banner_formula = (
            f'=CONCATENATE("Faltam ", '
            f'COUNTIFS({faixa_corrigido}, "", {faixa_campo}, "<>"&{contar}, {faixa_situacao}, "<>{EXCLUIDO}"), '
            f'" de ", COUNTIFS({faixa_campo}, "<>"&{contar}, {faixa_situacao}, "<>{EXCLUIDO}"), '
            f'" revisar   |   Questão: {CODIGOS_QUESTAO} — Inscrição: {CODIGOS_INSCRICAO}")'
        )
        cr.merge_range(0, 0, 0, 6, banner_formula, fmt_banner)
        # Linha inteira cinza e riscada quando a folha foi excluida no Checkup.
        cr.conditional_format(primeira_linha, 0, ultima_linha, 6, {
            "type": "formula",
            "criteria": f'=$G{primeira_linha + 1}="{EXCLUIDO}"',
            "format": fmt_excluido,
        })
    else:
        cr.merge_range(0, 0, 0, 6, "Nenhum item pendente — pode seguir direto para o cálculo.", fmt_banner)
    cr.set_row(0, 22)

    for col, titulo in enumerate(["Simulado", "Campo", "Motivo", "Corrigido", "Alternativas", "Scan Original", "Situação"]):
        cr.write(1, col, titulo, fmt_header)

    # Coluna Situacao: EXCLUÍDO quando a folha desta linha tem SIM no quadro
    # de repetidas do Checkup. O quadro alterna colunas (Simulado, Excluir?,
    # Simulado, Excluir?...); comparando a faixa dos nomes com a mesma faixa
    # deslocada uma coluna para a direita, cada nome fica emparelhado com o
    # seu proprio "Excluir?".
    if repetidas:
        def _faixa_ck(col_ini, col_fim):
            return (f"Checkup!${_letra(col_ini)}${primeira_linha_rep + 1}:"
                    f"${_letra(col_fim)}${ultima_linha_rep + 1}")
        faixa_nomes = _faixa_ck(col_rep + 1, col_situacao_rep - 2)
        faixa_excluir = _faixa_ck(col_rep + 2, col_situacao_rep - 1)

    linha_por_simulado = {}  # simulado -> primeira linha (0-idx) na aba Correcao
    linha_repetida_por_simulado = {}  # simulado -> linha (0-idx) do item "Inscricao"

    for i, item in enumerate(itens):
        r = primeira_linha + i
        cr.set_row(r, 40)
        cr.write(r, 0, item["simulado"], fmt_celula)
        cr.write(r, 1, item["campo"], fmt_celula)
        cr.write(r, 2, item["motivo"], fmt_wrap)
        cr.write(r, 3, "", fmt_input)
        # Coluna F fica vazia por padrão -- só as linhas de inscrição
        # ambígua (ver abaixo) recebem o link de scan completo. Precisa
        # de algum conteúdo (mesmo vazio, com formato) pra manter o fundo
        # escuro da linha inteira.
        cr.write(r, 5, "", fmt_celula)
        if repetidas:
            cr.write_formula(
                r, 6,
                f'=IF(SUMPRODUCT(({faixa_nomes}=$A{r + 1})*({faixa_excluir}="{VALOR_EXCLUIR}"))>0,'
                f'"{EXCLUIDO}","")',
                fmt_celula, "",
            )
        else:
            cr.write(r, 6, "", fmt_celula)

        if item["tipo"] == "repetida":
            cr.write(r, 3, "", fmt_input_texto)
            cr.write(r, 4, "", fmt_celula)
            url = f"https://drive.google.com/drive/search?q={item['simulado']}.tiff"
            cr.write_url(r, 5, url, fmt_link, string="Ver folha completa")
            cr.data_validation(r, 3, r, 3, {
                "validate": "length",
                "criteria": "==",
                "value": NUM_DIGITOS_INSCRICAO,
                "error_message": f"Digite a inscrição inteira ({NUM_DIGITOS_INSCRICAO} dígitos).",
            })
            linha_repetida_por_simulado[item["simulado"]] = r
            linha_por_simulado.setdefault(item["simulado"], r)
            continue

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

            # Pedido do usuário (23/09/2026): quando a posição está
            # ambígua (branco OU dupla marcação -- hoje "?" não distingue
            # as duas causas), a tira de dígitos isolados às vezes não é
            # suficiente para o operador decidir -- ele precisa ver a
            # folha inteira. Coluna F entrega esse link, reaproveitando o
            # mesmo padrão de URL já usado para IMAGEM_CORROMPIDA.
            if item["motivo"] == INSCRICAO_AMBIGUA:
                url = f"https://drive.google.com/drive/search?q={item['simulado']}.tiff"
                cr.write_url(r, 5, url, fmt_link, string="Ver folha completa")

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

    # quadro de inscricoes repetidas, a direita da lista de pendencias
    if repetidas:
        ck.set_column(col_rep, col_rep, 20, fmt_fundo)
        for k in range(max_por_grupo):
            ck.set_column(col_rep + 1 + 2 * k, col_rep + 1 + 2 * k, 26, fmt_fundo)
            ck.set_column(col_rep + 2 + 2 * k, col_rep + 2 + 2 * k, 10, fmt_fundo)
        ck.set_column(col_situacao_rep, col_situacao_rep, 18, fmt_fundo)

        ck.merge_range(
            linha_aviso_rep, col_rep, linha_aviso_rep, col_situacao_rep,
            "Inscrições repetidas — abra as folhas pelos links. Se for o mesmo simulado "
            "escaneado duas vezes, marque SIM em \"Excluir?\" na cópia que sobra. Se for "
            "outro aluno com a inscrição lida errado, siga normalmente para a aba Correção, "
            "corrija o número lá e volte aqui para conferir em \"Situação\" que a repetição "
            "foi resolvida.",
            fmt_banner_wrap,
        )
        ck.set_row(linha_aviso_rep, 75)

        titulos = ["Inscrição repetida"]
        for k in range(max_por_grupo):
            titulos += [f"Simulado {k + 1}", "Excluir?"]
        titulos.append("Situação")
        for j, titulo in enumerate(titulos):
            ck.write(linha_aviso_rep + 1, col_rep + j, titulo, fmt_header)

        for g, (inscricao, simulados) in enumerate(repetidas.items()):
            r = primeira_linha_rep + g
            ck.write_string(r, col_rep, inscricao, fmt_celula)
            ainda_repetida = []
            for k in range(max_por_grupo):
                col_nome = col_rep + 1 + 2 * k
                col_excluir = col_nome + 1
                if k >= len(simulados):
                    ck.write(r, col_nome, "", fmt_celula)
                    ck.write(r, col_excluir, "", fmt_celula)
                    continue
                simulado = simulados[k]
                url = f"https://drive.google.com/drive/search?q={simulado}.tiff"
                ck.write_url(r, col_nome, url, fmt_link, string=simulado)
                ck.write(r, col_excluir, "", fmt_input)
                ck.data_validation(r, col_excluir, r, col_excluir, {
                    "validate": "list",
                    "source": [VALOR_EXCLUIR],
                    "error_message": f"Deixe em branco ou escolha {VALOR_EXCLUIR}.",
                })
                # Esta folha ainda conta como repetida se nao foi excluida e
                # a correcao dela na aba Correcao esta vazia ou repete o numero.
                excl = f"{_letra(col_excluir)}{r + 1}"
                corr = f"'Correção'!D{linha_repetida_por_simulado[simulado] + 1}"
                num = f"{_letra(col_rep)}{r + 1}"
                ainda_repetida.append(f'AND({excl}<>"{VALOR_EXCLUIR}",OR({corr}="",{corr}={num}))*1')
            ck.write_formula(
                r, col_situacao_rep,
                f'=IF({"+".join(ainda_repetida)}<=1,"✔ Resolvida","✖ Ainda repetida")',
                fmt_celula, "✖ Ainda repetida",
            )

    wb.close()
    print(f"Planilha de revisão gerada: {caminho_saida}")
    print(f"  {len(simulados_com_pendencia)} simulado(s) com pendência corrigível ({n_itens} item(ns) no total).")
    print(f"  {len(falhas_alinhamento)} simulado(s) descartado(s) no alinhamento (aba Checkup).")
    if repetidas:
        print(f"  {len(repetidas)} inscrição(ões) repetida(s) — ver quadro à direita na aba Checkup.")

    # Devolve tambem 'linhas' -- o resultado cru que essa mesma chamada ja
    # calculou pra montar a planilha. Sem isso, quem for aplicar a revisao
    # depois (aplicar_revisao) precisaria chamar gerar_planilha_unificada()
    # de novo so pra reconstruir o que ja estava aqui, rodando a inferencia
    # (CNN no lote inteiro) uma segunda vez sem necessidade.
    return caminho_saida, linhas


if __name__ == "__main__":
    gerar_planilha_revisao()
