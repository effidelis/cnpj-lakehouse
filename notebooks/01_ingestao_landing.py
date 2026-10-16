# Databricks notebook source
# MAGIC %md
# MAGIC # 01 - Ingestão: Receita Federal → Volume (landing)
# MAGIC
# MAGIC Baixa o recorte de um mês dos dados abertos de CNPJ direto para
# MAGIC `/Volumes/cnpj/landing/receita/<mes>/`, com manifesto (tamanho, data na origem, SHA-256).
# MAGIC
# MAGIC - Idempotente: rodar de novo só baixa o que mudou na origem.
# MAGIC - Arquivos ficam como vieram (ZIP). Descompactar e ler é tarefa do bronze.
# MAGIC - Lógica em `src/receita_download.py`, a mesma usada pelo script de linha de comando.

# COMMAND ----------

# DBTITLE 1,Parâmetros (widgets)
dbutils.widgets.text("mes", "2026-10", "Mês de referência (AAAA-MM)")
dbutils.widgets.text("destino", "/Volumes/cnpj/landing/receita", "Volume de destino")

mes = dbutils.widgets.get("mes")
destino = dbutils.widgets.get("destino")
print(f"mes={mes}  destino={destino}")

# COMMAND ----------

# DBTITLE 1,Importar src
# Torna src/ importável: o notebook roda a partir de notebooks/, a raiz do repo é a pasta acima
import os, sys
raiz_repo = os.path.dirname(os.getcwd())
sys.path.insert(0, os.path.join(raiz_repo, "src"))

import receita_download

# COMMAND ----------

# DBTITLE 1,Baixar recorte para o Volume
manifesto = receita_download.baixar_recorte(mes, destino)

# COMMAND ----------

# DBTITLE 1,Conferir o Volume
# Conferência: o que está no Volume agora
display(dbutils.fs.ls(f"{destino}/{mes}/"))
