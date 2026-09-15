#!/usr/bin/env python3
"""Correcao completa fora do Colab: data/entrada/*.tif -> data/outputs/<nome>.xlsx

Uso, a partir da raiz do repositorio:
    python scripts/rodar_correcao.py

Antes de rodar, data/ precisa conter:
    entrada/*.tif|.tiff    os cartoes escaneados
    simulado_ativo.txt     CASDINHO ou SEMI
    gabarito_atual.txt     as letras do gabarito oficial, sem espacos
    nome_simulado.txt      nome do .xlsx de saida (opcional)

No Colab esse script nao e usado: o notebook Corretor_Simulados.ipynb faz o
mesmo, com os campos preenchidos na interface.
"""
import sys
from pathlib import Path

# Unico sys.path do projeto: coloca a raiz do repositorio no caminho para que
# 'import corretor' funcione ao chamar o script direto. Os modulos nao precisam
# disso porque sempre importam pelo pacote.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from corretor.config import NUM_QUESTOES, OUTPUTS_DIR, SIMULADO_ATIVO, SIMULADOS_DIR
from corretor.relatorio.gerar_excel import gerar_excel_final
from corretor.visao.extracao_em_lote import processar_simulados


def main():
    print("=" * 62)
    print(f"CORRETOR DE SIMULADOS  |  {SIMULADO_ATIVO} ({NUM_QUESTOES} questoes)")
    print("=" * 62)

    tifs = sorted(Path(SIMULADOS_DIR).glob("*.tif*"))
    if not tifs:
        print(f"Nenhum .tif em {SIMULADOS_DIR}. Nada a fazer.")
        return 1
    print(f"Entrada: {len(tifs)} cartao(oes) em {SIMULADOS_DIR}\n")

    print("[1/2] Extraindo bolhas...")
    processar_simulados(extrair_respostas=True, extrair_inscricao=True)

    print("\n[2/2] Inferindo e gerando a planilha...")
    gerar_excel_final()

    print(f"\nSaida em: {OUTPUTS_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
