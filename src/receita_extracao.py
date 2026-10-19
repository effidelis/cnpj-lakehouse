"""
Extração dos ZIPs da Receita para CSV, organizados por tabela.

Entrada:  <pasta_mes>/Empresas1.zip, Simples.zip, ...   (landing, como veio da Receita)
Saída:    <pasta_mes>/csv/<tabela>/<NomeDoZip>.csv       (ex.: csv/empresas/Empresas1.csv)

Por que extrair antes do Spark:
    O Spark lê gzip e bzip2, mas não ZIP. CSV descompactado é divisível, então o Spark
    lê cada arquivo em vários pedaços em paralelo (o Simples tem 3,2 GB descompactado).
    Uma pasta por tabela permite ler todos os pedaços de uma vez (Empresas0..9).

Garantias:
    - Streaming: o ZIP é lido em blocos, nunca carregado inteiro na memória.
    - Atômico: escreve em <nome>.parcial e só renomeia no fim. O CSV final nunca fica pela metade.
    - Íntegro: o zipfile confere o CRC ao terminar a leitura; o tamanho também é conferido.
    - Idempotente: pula o que já foi extraído do mesmo ZIP (mesmo SHA-256 do manifesto de download).

Só usa a biblioteca padrão do Python.
"""
import json
import os
import re
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from layout_receita import PREFIXO_ARQUIVO

MANIFESTO_DOWNLOAD = "_manifesto.json"
MANIFESTO_EXTRACAO = "_extracao.json"
_CHUNK = 8 * 1024 * 1024  # 8 MB


def tabela_do_zip(nome_zip):
    """'Estabelecimentos1.zip' -> 'estabelecimentos'."""
    prefixo = re.sub(r"\d*\.zip$", "", nome_zip)
    if prefixo not in PREFIXO_ARQUIVO:
        raise ValueError(f"ZIP sem tabela conhecida: {nome_zip}")
    return PREFIXO_ARQUIVO[prefixo]


def _extrair_um(zip_path, destino_csv, log):
    """Extrai o único arquivo de dentro do ZIP para destino_csv. Retorna o tamanho em bytes."""
    with zipfile.ZipFile(zip_path) as zf:
        membros = [m for m in zf.infolist() if not m.is_dir()]
        if len(membros) != 1:
            raise RuntimeError(f"{zip_path.name}: esperado 1 arquivo, encontrado {len(membros)}")
        membro = membros[0]
        destino_csv.parent.mkdir(parents=True, exist_ok=True)
        parcial = destino_csv.with_name(destino_csv.name + ".parcial")
        with zf.open(membro) as origem, open(parcial, "wb") as saida:
            shutil.copyfileobj(origem, saida, _CHUNK)  # o CRC é conferido ao fim da leitura
        tamanho = parcial.stat().st_size
        if tamanho != membro.file_size:
            raise RuntimeError(f"{zip_path.name}: tamanho divergente ({tamanho} != {membro.file_size})")
        os.replace(parcial, destino_csv)
    log(f"    {membro.filename} -> {destino_csv.relative_to(destino_csv.parents[2])} ({tamanho / 1e6:.1f} MB)")
    return membro.filename, tamanho


def extrair_recorte(pasta_mes, arquivos=None, log=print):
    """Extrai os ZIPs de `pasta_mes` para `pasta_mes/csv/<tabela>/` e atualiza `_extracao.json`.

    `arquivos`: lista de ZIPs a extrair. Padrão: todos os registrados no manifesto de download.
    Retorna o manifesto de extração (dict).
    """
    pasta_mes = Path(pasta_mes)
    download = json.loads((pasta_mes / MANIFESTO_DOWNLOAD).read_text(encoding="utf-8"))
    arquivos = arquivos or sorted(download)
    pasta_csv = pasta_mes / "csv"
    manifesto_path = pasta_csv / MANIFESTO_EXTRACAO
    pasta_csv.mkdir(parents=True, exist_ok=True)
    manifesto = json.loads(manifesto_path.read_text(encoding="utf-8")) if manifesto_path.exists() else {}

    for nome_zip in arquivos:
        sha_zip = download[nome_zip]["sha256"]
        tabela = tabela_do_zip(nome_zip)
        destino_csv = pasta_csv / tabela / nome_zip.replace(".zip", ".csv")
        reg = manifesto.get(nome_zip, {})
        if destino_csv.exists() and reg.get("sha256_zip") == sha_zip and reg.get("tamanho_csv") == destino_csv.stat().st_size:
            log(f"[=] {nome_zip}: já extraído deste mesmo ZIP")
            continue
        log(f"[»] {nome_zip} -> {tabela}/")
        nome_interno, tamanho = _extrair_um(pasta_mes / nome_zip, destino_csv, log)
        manifesto[nome_zip] = {
            "tabela": tabela,
            "csv": str(destino_csv.relative_to(pasta_mes)),
            "nome_interno": nome_interno,
            "tamanho_csv": tamanho,
            "sha256_zip": sha_zip,
            "extraido_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        manifesto_path.write_text(json.dumps(manifesto, indent=2, ensure_ascii=False), encoding="utf-8")

    total = sum(manifesto[n]["tamanho_csv"] for n in arquivos)
    log(f"Pronto: {len(arquivos)} arquivos, {total / 1e9:.2f} GB em {pasta_csv}")
    return manifesto
