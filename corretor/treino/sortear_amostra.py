from pathlib import Path
import random
import csv

from corretor import config


def listar_folhas(pasta: Path) -> list[Path]:
    """
    Lista todos os arquivos .tif/.tiff de uma pasta, ordenados por nome.

    O padrão "*.tif*" casa as duas extensões porque o "*" final aceita
    zero ou mais caracteres depois de ".tif" -- necessário porque o
    scanner grava .tif em algumas pastas e .tiff em outras (mesma folha,
    extensão diferente por máquina/scanner).

    Ordenar é o que torna o sorteio reproduzível: random.sample depende da
    ordem da lista de entrada, e a ordem que o sistema de arquivos devolve
    não é garantida — pode variar entre chamadas ou entre máquinas. Sem
    ordenar, a mesma seed produziria sorteios diferentes em execuções
    diferentes.
    """
    if not pasta.is_dir():
        raise FileNotFoundError(f"Pasta não encontrada: {pasta}")
    arquivos = sorted(pasta.glob("*.tif*"))
    return arquivos


def montar_pool_simulados(pasta_215: Path, pasta_extra: Path) -> list[Path]:
    """
    Junta as folhas de simulados num único pool: as pastas 215-simu e
    extra, que juntas somam 345 folhas (seção 7.0 do plano). Não sorteia
    nada aqui — só reúne o universo de onde as 80 folhas serão sorteadas.
    """
    return listar_folhas(pasta_215) + listar_folhas(pasta_extra)


def montar_pool_vestibular(pastas_corredores: list[Path], excluir: str = "G2") -> list[Path]:
    """
    Junta as folhas dos corredores de vestibular num único pool, exceto o
    corredor reservado como Teste B (seção 7.0). O nome do corredor
    excluído é comparado pelo nome da pasta (pasta.name), não pelo
    caminho inteiro, porque o caminho completo varia por máquina.
    """
    pool = []
    for pasta in pastas_corredores:
        if pasta.name == excluir:
            continue
        pool += listar_folhas(pasta)
    return pool


def sortear_folhas(pool: list[Path], quantidade: int, seed: int) -> list[Path]:
    """
    Sorteia, sem repetição, 'quantidade' folhas de um pool, usando uma
    seed fixa. Reproduzível: rodar de novo com o mesmo pool (mesma ordem
    — daí listar_folhas() ordenar) e a mesma seed sempre sorteia as
    mesmas folhas, sem depender de curadoria manual (seção 7.0 do plano).
    """
    if quantidade > len(pool):
        raise ValueError(
            f"Pool tem {len(pool)} folhas, mas foram pedidas {quantidade}."
        )
    gerador = random.Random(seed)
    return gerador.sample(pool, quantidade)


def sortear_questoes(num_questoes_prova: int, quantidade: int, seed: int) -> list[int]:
    """
    Usa uma seed derivada da seed principal, para que o sorteio de questões
    não dependa da ordem em que as folhas foram processadas (cada folha tem
    seu próprio sorteio de questões, independente das outras).
    """
    gerador = random.Random(seed)
    return gerador.sample(range(1, num_questoes_prova + 1), quantidade)


def sortear_posicao_inscricao(num_digitos_inscricao: int, seed: int) -> int:
    """
    Sorteia qual posição (0 a num_digitos_inscricao - 1) do número de
    inscrição vai ser anotada, quando a folha entrar no sorteio de
    inscrição (seção 7.0: 1 grupo de 10 dígitos por folha sorteada, não
    sempre a mesma posição -- senão as outras 6 posições nunca apareceriam
    na amostra de treino).
    """
    gerador = random.Random(seed)
    return gerador.randint(0, num_digitos_inscricao - 1)


def montar_amostra(
    folhas_simulados: list[Path],
    folhas_vestibular: list[Path],
    num_questoes_prova: int,
    num_digitos_inscricao: int,
    proporcao_inscricao: float,
    seed: int,
) -> list[dict]:
    """
    Monta a lista de decisões de amostragem: uma entrada por folha sorteada,
    com o contexto (simulados/vestibular), as 2 questões sorteadas para
    aquela folha, e se ela também sorteia um grupo de inscrição (só uma
    fração das folhas, conforme proporcao_inscricao) -- e, quando sorteia,
    qual das num_digitos_inscricao posições foi escolhida.

    Cada folha usa uma seed derivada (seed + posição na lista) para que o
    sorteio de questões de uma folha não dependa da ordem das outras --
    mesmo princípio de sortear_folhas: reprodutível, sem viés de curadoria.
    """
    todas_folhas = [(f, "simulados") for f in folhas_simulados] + [
        (f, "vestibular") for f in folhas_vestibular
    ]
    amostra = []
    for indice, (folha, contexto) in enumerate(todas_folhas):
        seed_folha = seed + indice
        questoes = sortear_questoes(num_questoes_prova, 2, seed_folha)
        gerador = random.Random(seed_folha)
        sorteia_inscricao = gerador.random() < proporcao_inscricao
        posicao_inscricao = (
            sortear_posicao_inscricao(num_digitos_inscricao, seed_folha)
            if sorteia_inscricao
            else None
        )
        amostra.append({
            "folha": folha.name,
            "contexto": contexto,
            "questoes": questoes,
            "sorteia_inscricao": sorteia_inscricao,
            "posicao_inscricao": posicao_inscricao,
        })
    return amostra


def salvar_csv(amostra: list[dict], caminho_saida: Path) -> None:
    """
    Grava a amostra (lista de dicts de montar_amostra()) num CSV, uma linha
    por folha sorteada. A coluna 'questoes' guarda os 2 números separados
    por ';' (ex.: "12;47") porque CSV não tem um jeito nativo de guardar uma
    lista dentro de uma célula -- juntar num texto com separador é a forma
    usual de contornar isso.
    """
    campos = ["folha", "contexto", "questoes", "sorteia_inscricao", "posicao_inscricao"]
    with open(caminho_saida, "w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=campos)
        escritor.writeheader()
        for entrada in amostra:
            escritor.writerow({
                "folha": entrada["folha"],
                "contexto": entrada["contexto"],
                "questoes": ";".join(str(q) for q in entrada["questoes"]),
                "sorteia_inscricao": entrada["sorteia_inscricao"],
                "posicao_inscricao": entrada["posicao_inscricao"],
            })


if __name__ == "__main__":
    SEED = 20260919
    NUM_QUESTOES_PROVA = 50
    NUM_DIGITOS_INSCRICAO = 7
    PROPORCAO_INSCRICAO = 0.15

    if config.DATASET_NOVO_SIMULADO is None or config.DATASET_NOVO_SIMULADO_EXTRA is None:
        raise RuntimeError(
            "DATASET_NOVO_SIMULADO / DATASET_NOVO_SIMULADO_EXTRA não configurados. "
            "Copie corretor/config_local.exemplo.py para corretor/config_local.py "
            "e preencha com os caminhos da sua máquina."
        )
    if not config.DATASET_NOVO_CORREDORES_DIR:
        raise RuntimeError(
            "DATASET_NOVO_CORREDORES_DIR não configurado em corretor/config_local.py."
        )

    pool_simulados = montar_pool_simulados(
        config.DATASET_NOVO_SIMULADO, config.DATASET_NOVO_SIMULADO_EXTRA
    )
    pool_vestibular = montar_pool_vestibular(
        list(config.DATASET_NOVO_CORREDORES_DIR.values())
    )

    folhas_simulados = sortear_folhas(pool_simulados, 80, SEED)
    folhas_vestibular = sortear_folhas(pool_vestibular, 27, SEED + 1000)

    amostra = montar_amostra(
        folhas_simulados,
        folhas_vestibular,
        NUM_QUESTOES_PROVA,
        NUM_DIGITOS_INSCRICAO,
        PROPORCAO_INSCRICAO,
        SEED + 2000,
    )

    salvar_csv(amostra, config.AMOSTRA_SORTEADA_CSV_PATH)
