"""
Download dos dados abertos de CNPJ da Receita Federal (WebDAV público) com manifesto.

Usado por:
- scripts/download_receita.py   (linha de comando, no PC)
- notebooks/01_ingestao_landing (Databricks, grava no Volume)

Por que um manifesto:
    A Receita às vezes altera pastas já publicadas. Para cada arquivo guardamos
    tamanho e data de modificação na origem, mais o SHA-256 do que foi baixado.
    Assim dá para detectar republicação e não baixar de novo o que não mudou.

Só usa a biblioteca padrão do Python.
"""
import base64
import hashlib
import json
import shutil
import tempfile
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

MANIFESTO = "_manifesto.json"
_AUTH = "Basic " + base64.b64encode(f"{SHARE_TOKEN}:".encode()).decode()
_CHUNK = 1024 * 1024  # 1 MB


def _request(url, method="GET", headers=None):
    h = {"Authorization": _AUTH, "User-Agent": "cnpj-lakehouse/0.1"}
    h.update(headers or {})
    return urllib.request.urlopen(urllib.request.Request(url, method=method, headers=h), timeout=120)


def listar_pasta(mes):
    """Lista os ZIPs da pasta do mês via WebDAV PROPFIND. Retorna (base_url, {nome: info})."""
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
    raise RuntimeError("Não consegui listar a pasta. Tentativas:\n  " + "\n  ".join(erros))


def _sha256(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(_CHUNK), b""):
            h.update(bloco)
    return h.hexdigest()


def _baixar(url, destino, tamanho, log):
    """Baixa para um arquivo temporário local, valida o tamanho e só então copia para o destino.

    O destino nunca recebe arquivo pela metade (importante quando o destino é um Volume).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir) / destino.name
        baixado, proximo_log = 0, 0
        with _request(url) as r, open(tmp, "wb") as f:
            for bloco in iter(lambda: r.read(_CHUNK), b""):
                f.write(bloco)
                baixado += len(bloco)
                if baixado >= proximo_log:
                    log(f"    {baixado / 1e6:8.1f} / {tamanho / 1e6:.1f} MB")
                    proximo_log += 50 * _CHUNK
        if baixado != tamanho:
            raise RuntimeError(f"{destino.name}: tamanho divergente (baixado {baixado}, esperado {tamanho})")
        sha = _sha256(tmp)
        shutil.copyfile(tmp, destino)
    return sha


def baixar_recorte(mes, destino, arquivos=None, log=print):
    """Baixa os arquivos do mês para `destino/<mes>/` e atualiza o manifesto.

    Idempotente: pula arquivos já baixados cujo tamanho e data na origem não mudaram.
    Retorna o manifesto (dict).
    """
    arquivos = arquivos or RECORTE_A
    pasta = Path(destino) / mes
    pasta.mkdir(parents=True, exist_ok=True)
    manifesto_path = pasta / MANIFESTO
    manifesto = json.loads(manifesto_path.read_text(encoding="utf-8")) if manifesto_path.exists() else {}

    base, origem = listar_pasta(mes)
    log(f"Fonte: {base}/{mes}/  ({len(origem)} arquivos na origem)")

    faltando = [n for n in arquivos if n not in origem]
    if faltando:
        raise RuntimeError(f"Arquivos não encontrados na origem: {faltando}")

    for nome in arquivos:
        info = origem[nome]
        destino_arq = pasta / nome
        reg = manifesto.get(nome, {})
        if (
            destino_arq.exists()
            and reg.get("tamanho_origem") == info["tamanho_origem"]
            and reg.get("modificado_origem") == info["modificado_origem"]
        ):
            log(f"[=] {nome}: já baixado e sem mudança na origem")
            continue
        log(f"[↓] {nome} ({info['tamanho_origem'] / 1e6:.1f} MB)")
        url = f"{base}/{mes}/{urllib.parse.quote(nome)}"
        sha = _baixar(url, destino_arq, info["tamanho_origem"], log)
        manifesto[nome] = {
            **info,
            "sha256": sha,
            "baixado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "mes_referencia": mes,
        }
        # grava a cada arquivo: se cair no meio, o que já veio fica registrado
        manifesto_path.write_text(json.dumps(manifesto, indent=2, ensure_ascii=False), encoding="utf-8")

    total = sum(manifesto[n]["tamanho_origem"] for n in arquivos)
    log(f"Pronto: {len(arquivos)} arquivos, {total / 1e6:.1f} MB em {pasta}")
    return manifesto
