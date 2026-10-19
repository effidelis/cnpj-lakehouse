"""
Bronze: CSV da Receita -> tabela Delta em `cnpj.bronze.<tabela>`.

Regras do bronze (cópia fiel da fonte, em formato de tabela):
- Todas as colunas como STRING. Nada de conversão de tipo, limpeza ou deduplicação (isso é silver).
  Motivo: zeros à esquerda ("0001"), datas "0", decimal com vírgula e CNPJ alfanumérico
  seriam corrompidos em silêncio por uma conversão automática.
- Nomes das colunas vêm de `layout_receita.LAYOUT` (os CSVs não têm cabeçalho).
- Colunas de controle: _arquivo_origem, _mes_referencia, _ingerido_em.
- Linhas malformadas não derrubam a carga: vão para a coluna `_registro_corrompido` (quarentena)
  e são contadas na conferência.
- Idempotente por mês: regravar um mês substitui só aquele mês (replaceWhere), os outros ficam.

Diferente de receita_download/receita_extracao, este módulo depende do PySpark
(recebe a SparkSession como parâmetro, então dá para testar com um Spark local).
"""
from pyspark.sql import functions as F
from pyspark.sql.types import StringType, StructField, StructType

from layout_receita import LAYOUT

COLUNA_CORROMPIDO = "_registro_corrompido"

OPCOES_CSV = {
    "sep": ";",
    "header": "false",
    "encoding": "ISO-8859-1",   # latin-1: sem isso, "Jurídica" vira lixo
    "quote": '"',
    "escape": '"',
    "mode": "PERMISSIVE",
    "columnNameOfCorruptRecord": COLUNA_CORROMPIDO,
}


def schema_texto(tabela):
    """Schema com todas as colunas do layout como STRING, mais a coluna de quarentena."""
    campos = [StructField(c, StringType(), True) for c in LAYOUT[tabela]]
    return StructType(campos + [StructField(COLUNA_CORROMPIDO, StringType(), True)])


def ler_csv(spark, pasta_csv_tabela, tabela, mes):
    """Lê todos os CSVs da pasta da tabela, como texto, com colunas de controle."""
    return (
        spark.read.options(**OPCOES_CSV)
        .schema(schema_texto(tabela))
        .csv(pasta_csv_tabela)
        .withColumn("_arquivo_origem", F.col("_metadata.file_name"))
        .withColumn("_mes_referencia", F.lit(mes))
        .withColumn("_ingerido_em", F.current_timestamp())
    )


def gravar(spark, df, nome_tabela, mes, comentario):
    """Grava em Delta. Se a tabela já existe, substitui só o mês (idempotente por mês)."""
    if spark.catalog.tableExists(nome_tabela):
        (df.write.format("delta").mode("overwrite")
           .option("replaceWhere", f"_mes_referencia = '{mes}'")
           .saveAsTable(nome_tabela))
    else:
        df.write.format("delta").mode("overwrite").saveAsTable(nome_tabela)
        spark.sql(f"COMMENT ON TABLE {nome_tabela} IS '{comentario}'")


def carregar_tabela(spark, pasta_mes, tabela, mes, catalogo_schema="cnpj.bronze"):
    """Lê `pasta_mes/csv/<tabela>/` e grava em `<catalogo_schema>.<tabela>`. Retorna o nome da tabela."""
    nome = f"{catalogo_schema}.{tabela}"
    df = ler_csv(spark, f"{pasta_mes}/csv/{tabela}", tabela, mes)
    comentario = f"Bronze: cópia fiel (tudo STRING) dos CSVs de {tabela} da Receita Federal, com colunas de controle"
    gravar(spark, df, nome, mes, comentario)
    return nome
