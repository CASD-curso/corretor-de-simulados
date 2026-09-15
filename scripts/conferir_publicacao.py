#!/usr/bin/env python3
"""Confere que nada sensivel esta prestes a ir para o GitHub.

Rode SEMPRE antes do primeiro push e antes de qualquer push depois de mexer
em pastas ou no .gitignore:

    python scripts/conferir_publicacao.py

Sai com codigo 0 se estiver tudo certo, 1 se achar problema. O que ele procura
e o que ja deu errado neste projeto uma vez: scan de aluno versionado por
engano, e o .gitignore excluindo os pesos da rede sem ninguem perceber.
"""
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def rastreados():
    r = subprocess.run(["git", "ls-files"], cwd=RAIZ, capture_output=True, text=True)
    if r.returncode != 0:
        print("ERRO: nao e um repositorio git (rode 'git init' antes).")
        sys.exit(1)
    return [l for l in r.stdout.splitlines() if l]


def main():
    arquivos = rastreados()
    if not arquivos:
        print("ERRO: nenhum arquivo rastreado. Rode 'git add -A' antes.")
        return 1

    problemas = []

    scans = [f for f in arquivos if f.lower().endswith((".tif", ".tiff"))]
    if scans:
        problemas.append(
            f"{len(scans)} scan(s) versionado(s) - contem matricula de aluno:\n"
            + "\n".join(f"      {f}" for f in scans[:10]))

    em_data = [f for f in arquivos if f.startswith("data/")]
    if em_data:
        problemas.append(
            f"{len(em_data)} arquivo(s) sob data/, que deveria ser ignorada:\n"
            + "\n".join(f"      {f}" for f in em_data[:10]))

    planilhas = [f for f in arquivos if f.lower().endswith((".xlsx", ".csv"))]
    if planilhas:
        problemas.append(
            "planilha(s) de resultado versionada(s) - contem notas por aluno:\n"
            + "\n".join(f"      {f}" for f in planilhas[:10]))

    # Os pesos PRECISAM estar versionados: sem eles, quem clonar nao roda nada.
    if "pesos/cnn_bolhas.pth" not in arquivos:
        problemas.append(
            "pesos/cnn_bolhas.pth NAO esta versionado. Sem ele o sistema nao roda\n"
            "      apos um clone. Confira se o .gitignore nao tem um '*.pth'.")

    # Montado em pedacos de proposito: escrito literal, este proprio arquivo
    # seria acusado pela busca abaixo.
    agulhas = ("C:" + chr(92) + "Users" + chr(92), "C:" + "/Users/")
    pessoais = []
    for f in arquivos:
        if not f.endswith((".py", ".md", ".txt", ".ipynb")):
            continue
        try:
            texto = (RAIZ / f).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if any(a in texto for a in agulhas):
            pessoais.append(f)
    if pessoais:
        problemas.append(
            "caminho pessoal do Windows dentro de arquivo publico:\n"
            + "\n".join(f"      {f}" for f in pessoais))

    print(f"Arquivos rastreados: {len(arquivos)}")
    print(f"  .py     {sum(1 for f in arquivos if f.endswith('.py'))}")
    print(f"  .png    {sum(1 for f in arquivos if f.endswith('.png'))}  (dataset de treino)")
    print(f"  .pth    {sum(1 for f in arquivos if f.endswith('.pth'))}  (pesos da rede)")
    print()

    if problemas:
        print("=" * 62)
        print(f"NAO PUBLIQUE. {len(problemas)} problema(s):")
        print("=" * 62)
        for i, p in enumerate(problemas, 1):
            print(f"  {i}. {p}")
        return 1

    print("=" * 62)
    print("OK - nada sensivel entre os arquivos rastreados. Pode publicar.")
    print("=" * 62)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
