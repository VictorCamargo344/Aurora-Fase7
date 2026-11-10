####################################################################
# CONFIG — caminhos e constantes compartilhados por todo o sistema.
#   Concentrar os caminhos aqui evita que cada arquivo monte o seu,
# e permite mover pastas mudando uma única linha.
####################################################################

from pathlib import Path

# Raiz do projeto: a pasta acima de src/
RAIZ = Path(__file__).resolve().parent.parent

PASTA_DADOS = RAIZ / "data"
ARQUIVO_BANCO = PASTA_DADOS / "aurora_siger.db"
ARQUIVO_SQL = PASTA_DADOS / "script_banco.sql"
ARQUIVO_CSV = PASTA_DADOS / "dados_aurora_siger.csv"

PASTA_GRAFICOS = RAIZ / "graficos_ou_imagens"
ARQUIVO_CIRCUITO = RAIZ / "circuito_logico.png"

# Linha separadora usada nos títulos das telas
LINHA = "=" * 72
