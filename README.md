# cnpj-lakehouse

Lakehouse pipeline for Brazilian company registry (CNPJ) open data from Receita Federal, built on Databricks with Delta Lake and Unity Catalog.

*Pipeline lakehouse com os dados abertos de CNPJ da Receita Federal, no Databricks com Delta Lake e Unity Catalog. (Versão em português abaixo.)*

## Status

Work in progress. Phase 1: ingestion, Delta Lake, medallion layers and Unity Catalog governance.

| Phase | Scope | Status |
|---|---|---|
| 1 | Ingestion to a Unity Catalog Volume, bronze/silver/gold in Delta, grants and lineage | in progress |
| 2 | K-means clustering with MLflow tracking | planned |
| 3 | CI/CD with Databricks Asset Bundles and GitHub Actions | planned |
| 4 | Agent querying the gold layer via MCP (optional) | planned |

## Architecture (Unity Catalog)

```
cnpj                       catalog
├── landing.receita        volume: original ZIP files, one folder per reference month
├── bronze                 Delta tables, raw text columns + ingestion metadata
├── silver                 typed, cleaned, deduplicated
└── gold                   business tables and K-means features
```

## Data source

- Receita Federal open data, monthly full snapshots (~7 GB compressed, 37 files).
- Layout: [`docs/cnpj-metadados.pdf`](docs/cnpj-metadados.pdf), translated to code in [`src/layout_receita.py`](src/layout_receita.py).
- Raw data is never committed (see `.gitignore`).

## Repository layout

```
sql/        Unity Catalog setup (idempotent)
scripts/    download from Receita Federal WebDAV with a manifest (size, source timestamp, SHA-256)
src/        shared Python code (layout, ingestion)
docs/       source documentation
```

---

## Em português

Projeto de portfólio: refaz um projeto antigo (Parquet) com Delta Lake e Unity Catalog, seguindo a arquitetura medallion, e depois aplica K-means sobre a camada gold.

Decisões de destaque:
- Catálogo próprio (`cnpj`) com um schema por camada: isola o projeto e simplifica grants e lineage.
- Arquivos originais guardados num Volume (`landing`) antes de virar tabela: rastreabilidade e reprocessamento.
- Bronze lê tudo como texto, silver converte tipos: erro de conversão não bloqueia a ingestão.
- Manifesto de download com tamanho, data na origem e SHA-256: detecta republicação de arquivos pela Receita.
- CNPJ tratado como texto (CNPJ alfanumérico a partir de julho de 2026).

## License

MIT. Data: public open data from Receita Federal do Brasil.
