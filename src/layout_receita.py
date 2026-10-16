"""
Layout dos dados abertos de CNPJ (fonte: docs/cnpj-metadados.pdf, Receita Federal).

Os CSVs da Receita não têm cabeçalho, então os nomes das colunas vêm daqui.
A ordem importa: é a posição da coluna no arquivo.

Conferido contra os arquivos de 2026-10 (contagem de colunas bate em 100% das linhas).
Observações que o PDF não deixa claras:
- Códigos (situação, porte, motivo...) vêm sempre com 2 dígitos: "02", não "2".
- Datas vêm como texto AAAAMMDD; existe o valor "0" para data ausente.
- municipio é o código da Receita (4 dígitos), não o código IBGE (7 dígitos).
- CNPJ pode ser alfanumérico desde jul/2026: tratar sempre como texto.
"""

LAYOUT = {
    "empresas": [
        "cnpj_basico",
        "razao_social",
        "natureza_juridica",
        "qualificacao_responsavel",
        "capital_social",          # decimal com vírgula: "1000,00"
        "porte_empresa",           # 00 não informado, 01 micro, 03 pequeno porte, 05 demais
        "ente_federativo_responsavel",
    ],
    "estabelecimentos": [
        "cnpj_basico",
        "cnpj_ordem",
        "cnpj_dv",
        "identificador_matriz_filial",  # 1 matriz, 2 filial
        "nome_fantasia",
        "situacao_cadastral",           # 01 nula, 02 ativa, 03 suspensa, 04 inapta, 08 baixada
        "data_situacao_cadastral",
        "motivo_situacao_cadastral",
        "nome_cidade_exterior",
        "pais",
        "data_inicio_atividade",
        "cnae_fiscal_principal",
        "cnae_fiscal_secundaria",       # lista separada por vírgula
        "tipo_logradouro",
        "logradouro",
        "numero",
        "complemento",
        "bairro",
        "cep",
        "uf",
        "municipio",                    # código da Receita, não IBGE
        "ddd_1",
        "telefone_1",
        "ddd_2",
        "telefone_2",
        "ddd_fax",
        "fax",
        "correio_eletronico",
        "situacao_especial",
        "data_situacao_especial",
    ],
    "socios": [
        "cnpj_basico",
        "identificador_socio",          # 1 PJ, 2 PF, 3 estrangeiro
        "nome_socio_razao_social",
        "cnpj_cpf_socio",               # CPF mascarado pela Receita (LGPD)
        "qualificacao_socio",
        "data_entrada_sociedade",
        "pais",
        "representante_legal",          # CPF mascarado
        "nome_representante",
        "qualificacao_representante_legal",
        "faixa_etaria",                 # 0 não se aplica, 1 (0-12) ... 9 (80+)
    ],
    "simples": [
        "cnpj_basico",
        "opcao_simples",                # S, N, vazio
        "data_opcao_simples",
        "data_exclusao_simples",
        "opcao_mei",                    # S, N, vazio
        "data_opcao_mei",
        "data_exclusao_mei",
    ],
    # Tabelas de domínio: todas com (codigo, descricao)
    "cnaes": ["codigo", "descricao"],
    "motivos": ["codigo", "descricao"],
    "municipios": ["codigo", "descricao"],
    "naturezas": ["codigo", "descricao"],
    "paises": ["codigo", "descricao"],
    "qualificacoes": ["codigo", "descricao"],
}

# Prefixo do nome do ZIP -> tabela. Ex.: "Estabelecimentos1.zip" -> "estabelecimentos"
PREFIXO_ARQUIVO = {
    "Empresas": "empresas",
    "Estabelecimentos": "estabelecimentos",
    "Socios": "socios",
    "Simples": "simples",
    "Cnaes": "cnaes",
    "Motivos": "motivos",
    "Municipios": "municipios",
    "Naturezas": "naturezas",
    "Paises": "paises",
    "Qualificacoes": "qualificacoes",
}
