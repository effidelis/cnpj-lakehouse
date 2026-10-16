"""
Baixa um recorte dos dados abertos de CNPJ da Receita Federal e gera um manifesto.

Uso (na raiz do projeto):
    python scripts/download_receita.py --mes 2026-10

Por que um manifesto:
    A Receita às vezes altera pastas já publicadas. Para cada arquivo guardamos
    tamanho e data de modificação na origem, mais o SHA-256 do que foi baixado.
    Assim dá para detectar republicação e não baixar de novo o que não mudou.

Só usa a biblioteca padrão do Python (sem pip install).
"""
import argparse
import base64
import hashlib
import json
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

HOST = "https://arquivos.receitafederal.gov.br"
SHARE_TOKEN = "YggdBLfdninEJX9"  # token público do compartilhamento (não é credencial)
WEBDAV_BASES = [
    f"{HOST}/public.php/dav/files/{SHARE_TOKEN}",  # Nextcloud novo
    f"{HOST}/public.php/webdav",                    # Nextcloud antigo
]

# Recorte A: 1 arquivo de cada tabela grande + Simples + todas as tabelas de domínio
RECORTE_A = [
    "Empresas1.zip",
    "Estabelecimentos1.zip",
    "Socios1.zip",
    "Simples.zip",
    "Cnaes.zip",
    "Motivos.zip",
    "Municipios.zip",
    "Naturezas.zip",
    "Paises.zip",
    "Qualificacoes.zip",
]

AUTH = "Basic " + base64.b64encode(f"{SHARE_TOKEN}:".encode()).decode()
CHUNK = 1024 * 1024  # 1 MB


def _request(url, method="GET", headers=None):
    h = {"Authorization": AUTH, "User-Agent": "cnpj-lakehouse/0.1"}
    h.update(headers or {})
    return urllib.request.urlopen(urllib.request.Request(url, method=method, headers=h), timeout=120)


def listar_pasta(mes):
    """Lista arquivos da pasta do mês via WebDAV PROPFIND: nome, tamanho, data de modificação."""
    erros = []
    for base in WEBDAV_BASES:
        url = f"{base}/{mes}/"
        try:
            with _request(url, "PROPFIND", {"Depth": "1"}) as r:
                xml = r.read()
        except Exception as e:  # tenta a próxima base
            erros.append(f"{url}: {e}")
            continue
        ns = {"d": "DAV:"}
        arquivos = {}
        for resp in ET.fromstring(xml).findall("d:response", ns):
            href = urllib.parse.unquote(resp.findtext("d:href", "", ns))
            nome = href.rstrip("/").split("/")[-1]
            prop = resp.find("d:propstat/d:prop", ns)
            tamanho = prop.findtext("d:getcontentlength", None, ns)
            if not nome.lower().endswith(".zip") or tamanho is None:
                continue
            arquivos[nome] = {
                "tamanho_origem": int(tamanho),
                "modificado_origem": prop.findtext("d:getlastmodified", None, ns),
            }
        return base, arquivos
    sys.exit("Não consegui listar a pasta. Tentativas:\n  " + "\n  ".join(erros))


def sha256(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(CHUNK), b""):
            h.update(bloco)
    return h.hexdigest()


def baixar(url, destino, tamanho):
    tmp = destino.with_suffix(destino.suffix + ".part")
    baixado = 0
    with _request(url) as r, open(tmp, "wb") as f:
        for bloco in iter(lambda: r.read(CHUNK), b""):
            f.write(bloco)
            baixado += len(bloco)
            print(f"\r    {baixado / 1e6:8.1f} / {tamanho / 1e6:.1f} MB", end="", flush=True)
    print()
    if baixado != tamanho:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"tamanho divergente: baixado {baixado}, esperado {tamanho}")
    tmp.replace(destino)  # só vira o nome final se terminou inteiro


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mes", required=True, help="pasta de referência, ex.: 2026-10")
    ap.add_argument("--destino", default="data/raw", help="pasta local de saída")
    args = ap.parse_args()

    pasta = Path(args.destino) / args.mes
    pasta.mkdir(parents=True, exist_ok=True)
    manifesto_path = pasta / "_manifesto.json"
    anterior = json.loads(manifesto_path.read_text(encoding="utf-8")) if manifesto_path.exists() else {}

    base, origem = listar_pasta(args.mes)
    print(f"Fonte: {base}/{args.mes}/  ({len(origem)} arquivos na origem)")

    faltando = [n for n in RECORTE_A if n not in origem]
    if faltando:
        sys.exit(f"Arquivos do recorte não encontrados na origem: {faltando}")

    manifesto = {}
    for nome in RECORTE_A:
        info = origem[nome]
        destino = pasta / nome
        reg = anterior.get(nome, {})
        inalterado = (
            destino.exists()
            and reg.get("tamanho_origem") == info["tamanho_origem"]
            and reg.get("modificado_origem") == info["modificado_origem"]
        )
        if inalterado:
            print(f"[=] {nome}: já baixado e sem mudança na origem")
            manifesto[nome] = reg
            continue
        print(f"[↓] {nome} ({info['tamanho_origem'] / 1e6:.1f} MB)")
        url = f"{base}/{args.mes}/{urllib.parse.quote(nome)}"
        baixar(url, destino, info["tamanho_origem"])
        manifesto[nome] = {
            **info,
            "sha256": sha256(destino),
            "baixado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "mes_referencia": args.mes,
        }
        manifesto_path.write_text(json.dumps(manifesto | {k: v for k, v in anterior.items() if k not in manifesto}, indent=2, ensure_ascii=False), encoding="utf-8")

    manifesto_path.write_text(json.dumps(manifesto, indent=2, ensure_ascii=False), encoding="utf-8")
    total = sum(v["tamanho_origem"] for v in manifesto.values())
    print(f"\nPronto: {len(manifesto)} arquivos, {total / 1e6:.1f} MB em {pasta}")
    print(f"Manifesto: {manifesto_path}")


if __name__ == "__main__":
    main()
