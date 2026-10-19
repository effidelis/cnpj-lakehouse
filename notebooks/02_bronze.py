# Databricks notebook source
# MAGIC %md
# MAGIC # 02 - Bronze: landing → tabelas Delta em `cnpj.bronze`
# MAGIC
# MAGIC Etapa 1 (este trecho): extrai os ZIPs da landing para CSV, uma pasta por tabela,
# MAGIC em `/Volumes/cnpj/landing/receita/<mes>/csv/<tabela>/`.
# MAGIC
# MAGIC - O Spark não lê ZIP; CSV descompactado é divisível e é lido em paralelo.
# MAGIC - Idempotente: só extrai de novo se o ZIP mudou (SHA-256 do manifesto de download).
# MAGIC - Lógica em `src/receita_extracao.py`.
# MAGIC
# MAGIC Etapa 2 (próximos commits): ler os CSVs como texto e gravar as tabelas Delta.

# COMMAND ----------

# DBTITLE 1,Parâmetros (widgets)
dbutils.widgets.text("mes", "2026-10", "Mês de referência (AAAA-MM)")
dbutils.widgets.text("landing", "/Volumes/cnpj/landing/receita", "Volume da landing")

mes = dbutils.widgets.get("mes")
landing = dbutils.widgets.get("landing")
pasta_mes = f"{landing}/{mes}"
print(f"mes={mes}  pasta_mes={pasta_mes}")

# COMMAND ----------

# DBTITLE 1,Importar src
import os, sys
raiz_repo = os.path.dirname(os.getcwd())
sys.path.insert(0, os.path.join(raiz_repo, "src"))

import receita_extracao

# COMMAND ----------

# DBTITLE 1,Extrair ZIPs para CSV
extracao = receita_extracao.extrair_recorte(pasta_mes)

# COMMAND ----------

# DBTITLE 1,Conferir CSVs extraídos
# Tamanho lido do disco (o que realmente está no Volume), comparado com o registrado no manifesto
linhas = []
for nome_zip, r in sorted(extracao.items(), key=lambda kv: kv[1]["tabela"]):
    no_disco = os.path.getsize(f"{pasta_mes}/{r['csv']}")
    linhas.append((r["tabela"], r["csv"], no_disco, no_disco == r["tamanho_csv"]))
display(spark.createDataFrame(linhas, "tabela string, csv string, bytes_no_disco long, bate_com_manifesto boolean"))
