-- Setup do Unity Catalog para o projeto CNPJ v2
-- Idempotente: pode ser executado mais de uma vez.

-- 1. Catálogo do projeto
CREATE CATALOG IF NOT EXISTS cnpj
  COMMENT 'Dados abertos de CNPJ da Receita Federal, pipeline medallion (projeto de portfólio)';

-- 2. Schemas (um por camada)
CREATE SCHEMA IF NOT EXISTS cnpj.landing COMMENT 'Arquivos brutos da Receita (ZIP/CSV), sem transformação';
CREATE SCHEMA IF NOT EXISTS cnpj.bronze  COMMENT 'Tabelas Delta, cópia fiel dos CSVs + metadados de ingestão';
CREATE SCHEMA IF NOT EXISTS cnpj.silver  COMMENT 'Tabelas limpas, tipadas e deduplicadas';
CREATE SCHEMA IF NOT EXISTS cnpj.gold    COMMENT 'Tabelas de negócio e features para o K-means';

-- 3. Volume para receber os arquivos
CREATE VOLUME IF NOT EXISTS cnpj.landing.receita
  COMMENT 'ZIPs baixados de dados.gov.br / Receita Federal';

-- 4. Conferência
SHOW SCHEMAS IN cnpj;
