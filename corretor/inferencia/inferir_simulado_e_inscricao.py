"""
Inferência das duas grades do cartão -- respostas (5 alternativas x N
questões) e inscrição (10 dígitos x 7 posições) -- num módulo só (item 13
do plano).

Antes eram dois módulos, inferir_simulado.py e inferir_inscricao.py, com
~80% do código igual: mesmo agrupamento dos PNGs pelo nome do arquivo, mesmo
laço, mesmos limiares, mesma exportação de CSV. Toda correção precisava ser
feita duas vezes. Aqui a regra de decisão e o laço existem uma vez só, e
cada grade entra como parâmetro. É também o ponto único que o item 7.1 vai
trocar pela regra de margem.
"""
import csv
import re
from collections import defaultdict
from pathlib import Path

from corretor.config import (
    ALTERNATIVAS,
    DIGITOS_INSCRICAO,
    INSCRICOES_CSV_PATH,
    LIMIAR_DUPLA,
    LIMIAR_MAXIMO,
    NUM_DIGITOS_INSCRICAO,
    NUM_QUESTOES,
    RECORTES_BOLHAS_DIR,
    RECORTES_INSCRICAO_DIR,
    RESULTADOS_CSV_PATH,
)
from corretor.inferencia.modelo_bolhas import carregar_modelo, obter_device, prob_bolha_preenchida

# Nome dos recortes gravados por corretor.visao.extracao_em_lote.
# Grupos: (1) simulado, (2) posição na grade, (3) chave da bolha.
#   scan01_Q17_C.png               -> ("scan01", "17", "C")
#   scan01_inscricao_pos2_dig5.png -> ("scan01", "2",  "5")
PADRAO_BOLHA = re.compile(r"^(.+)_Q(\d+)_([A-E])\.png$", re.IGNORECASE)
PADRAO_DIGITO = re.compile(r"^(.+)_inscricao_pos(\d+)_dig(\d)\.png$", re.IGNORECASE)


def decidir(probs_por_chave, limiar_maximo=LIMIAR_MAXIMO, limiar_dupla=LIMIAR_DUPLA):
    """Decide qual bolha de um grupo foi marcada.

    Vale tanto para as 5 alternativas de uma questão quanto para os 10
    dígitos de uma posição da inscrição -- antes eram duas funções quase
    idênticas (padrao_da_questao e ler_digito).

    probs_por_chave: {chave: probabilidade de a bolha estar VAZIA}.
    Probabilidade baixa = bolha marcada.

    Devolve a chave da bolha marcada, 'BRANCOM' (nenhuma passou do limiar)
    ou 'MULTM' (a segunda mais marcada também parece marcada). O sufixo M
    indica decisão automática do modelo, ainda sem revisão humana.
    """
    bolhas_ordenadas = sorted(probs_por_chave.items(), key=lambda item: item[1])

    melhor_chave, menor_prob = bolhas_ordenadas[0]
    _, segunda_prob = bolhas_ordenadas[1]

    if menor_prob > limiar_maximo:
        return "BRANCOM"
    elif segunda_prob < limiar_dupla:
        return "MULTM"
    else:
        return melhor_chave


def _agrupar_recortes(pasta, padrao):
    """Organiza os PNGs da pasta como {simulado: {posição: {chave: caminho}}}.

    A chave sai sempre como texto em maiúscula ('C', '5'), para as duas
    grades serem tratadas igual no resto do módulo. Arquivo com nome fora
    do padrão é ignorado.
    """
    pasta = Path(pasta)
    if not pasta.exists():
        raise FileNotFoundError(f"Pasta de recortes não encontrada: {pasta}")

    arquivos = sorted(pasta.glob("*.png"))
    if not arquivos:
        raise FileNotFoundError(f"Nenhum PNG em '{pasta}'. Rode a extração primeiro.")

    por_simulado = defaultdict(lambda: defaultdict(dict))
    for arq in arquivos:
        m = padrao.match(arq.name)
        if not m:
            continue
        nome_sim, posicao, chave = m.group(1), int(m.group(2)), m.group(3).upper()
        por_simulado[nome_sim][posicao][chave] = arq
    return por_simulado


def _inferir_grade(por_simulado, posicoes, chaves, rotulo_posicao, modelo, device):
    """Laço comum às duas grades.

    posicoes: as posições a ler, na ordem (1..N questões, ou 0..6 dígitos).
    chaves: as bolhas de cada posição (A-E, ou 0-9), como texto.
    rotulo_posicao: função que dá o nome da posição no registro de
    ilegíveis ('Q17', 'pos2').

    Devolve ({simulado: [decisão por posição]}, {simulado: [posições com
    imagem que falhou ao abrir]}). Posição sem nenhum recorte vira 'BRANCOM';
    bolha ausente dentro de uma posição conta como vazia (probabilidade 1.0).
    """
    decisoes = {}
    ilegiveis = defaultdict(list)

    for nome_sim in sorted(por_simulado.keys()):
        grade = por_simulado[nome_sim]
        lidas = []

        for posicao in posicoes:
            if posicao not in grade:
                lidas.append("BRANCOM")
                continue

            probs = {}
            posicao_ilegivel = False
            for chave in chaves:
                caminho = grade[posicao].get(chave)
                if caminho is None:
                    probs[chave] = 1.0
                    continue
                prob, leitura_ok = prob_bolha_preenchida(modelo, caminho, device)
                probs[chave] = prob
                if not leitura_ok:
                    posicao_ilegivel = True

            if posicao_ilegivel:
                ilegiveis[nome_sim].append(rotulo_posicao(posicao))

            lidas.append(decidir(probs))

        decisoes[nome_sim] = lidas

    return decisoes, dict(ilegiveis)


def _exportar_csv(linhas, cabecalho, caminho, descricao):
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=cabecalho)
        writer.writeheader()
        writer.writerows(linhas)
    print(f"\n{len(linhas)} {descricao} exportado(s) para '{caminho}'.")


def inferir_simulados(pasta_recortes=None, csv_saida=None, exportar_csv=True):
    """
    Retorna (respostas_por_simulado, bolhas_ilegiveis_por_simulado).

    respostas_por_simulado: {simulado: ['A', 'BRANCOM', 'MULTM', ...]}, uma
    entrada por questão. bolhas_ilegiveis_por_simulado: auditoria do item
    4 -- as questões ('Q3', 'Q17') em que alguma imagem existia mas falhou
    ao abrir.
    """
    por_simulado = _agrupar_recortes(pasta_recortes or RECORTES_BOLHAS_DIR, PADRAO_BOLHA)

    device = obter_device()
    modelo = carregar_modelo(device)
    print(f"Inferindo respostas em: {device}")

    respostas, ilegiveis = _inferir_grade(
        por_simulado,
        posicoes=range(1, NUM_QUESTOES + 1),
        chaves=ALTERNATIVAS,
        rotulo_posicao=lambda q: f"Q{q}",
        modelo=modelo,
        device=device,
    )
    for nome_sim in respostas:
        print(f"  {nome_sim}: {NUM_QUESTOES} questões processadas")

    if exportar_csv:
        cabecalho = ["Simulado"] + [f"Q{i}" for i in range(1, NUM_QUESTOES + 1)] + ["Bolhas_Ilegiveis"]
        linhas = [
            {
                "Simulado": nome_sim,
                **{f"Q{i}": lidas[i - 1] for i in range(1, NUM_QUESTOES + 1)},
                "Bolhas_Ilegiveis": ",".join(ilegiveis.get(nome_sim, [])),
            }
            for nome_sim, lidas in respostas.items()
        ]
        _exportar_csv(linhas, cabecalho, csv_saida or RESULTADOS_CSV_PATH, "simulado")

    return respostas, ilegiveis


def inferir_inscricoes(pasta_recortes=None, csv_saida=None, exportar_csv=True):
    """
    Retorna (inscricao_por_simulado, digitos_ilegiveis_por_simulado).

    inscricao_por_simulado: {simulado: '2601105'}. Posição em branco ou com
    dupla marcação vira '?' -- a inscrição é um texto de 7 caracteres, e o
    resto do pipeline (planilha de revisão, aplicar_revisao) procura
    exatamente esse '?'. digitos_ilegiveis_por_simulado: auditoria do item
    4 -- as posições ('pos2', 'pos5') cuja imagem falhou ao abrir.
    """
    por_simulado = _agrupar_recortes(pasta_recortes or RECORTES_INSCRICAO_DIR, PADRAO_DIGITO)

    device = obter_device()
    modelo = carregar_modelo(device)
    print(f"Inferindo inscrições em: {device}")

    digitos, ilegiveis = _inferir_grade(
        por_simulado,
        posicoes=range(NUM_DIGITOS_INSCRICAO),
        chaves=[str(d) for d in DIGITOS_INSCRICAO],
        rotulo_posicao=lambda pos: f"pos{pos}",
        modelo=modelo,
        device=device,
    )

    inscricoes = {}
    for nome_sim, lidos in digitos.items():
        inscricoes[nome_sim] = "".join(
            "?" if d in ("BRANCOM", "MULTM") else d for d in lidos
        )
        print(f"  {nome_sim}: {inscricoes[nome_sim]}")

    if exportar_csv:
        linhas = [
            {
                "Simulado": nome_sim,
                "Inscricao": inscricao,
                "Digitos_Ilegiveis": ",".join(ilegiveis.get(nome_sim, [])),
            }
            for nome_sim, inscricao in inscricoes.items()
        ]
        _exportar_csv(linhas, ["Simulado", "Inscricao", "Digitos_Ilegiveis"],
                      csv_saida or INSCRICOES_CSV_PATH, "inscrição(ões)")

    return inscricoes, ilegiveis


def main():
    print(f"Lendo recortes de: {RECORTES_INSCRICAO_DIR}")
    _, digitos_ilegiveis = inferir_inscricoes()
    print(f"\nLendo recortes de: {RECORTES_BOLHAS_DIR}")
    _, bolhas_ilegiveis = inferir_simulados()

    if digitos_ilegiveis:
        print(f"\nAVISO: dígitos ilegíveis em {len(digitos_ilegiveis)} simulado(s): {digitos_ilegiveis}")
    if bolhas_ilegiveis:
        print(f"\nAVISO: bolhas ilegíveis em {len(bolhas_ilegiveis)} simulado(s): {bolhas_ilegiveis}")


if __name__ == "__main__":
    main()
