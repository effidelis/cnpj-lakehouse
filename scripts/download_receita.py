"""
Linha de comando para baixar o recorte da Receita no PC.

Uso (na raiz do projeto):
    python scripts/download_receita.py --mes 2026-10

A lógica fica em src/receita_download.py (a mesma usada pelo notebook no Databricks).
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from receita_download import baixar_recorte  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mes", required=True, help="pasta de referência, ex.: 2026-10")
    ap.add_argument("--destino", default="data/raw", help="pasta local de saída")
    args = ap.parse_args()
    baixar_recorte(args.mes, args.destino)


if __name__ == "__main__":
    main()
