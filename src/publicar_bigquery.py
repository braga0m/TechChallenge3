########################################################
#### INSTALL
########################################################
%pip install google-cloud-bigquery pyarrow db-dtypes
dbutils.library.restartPython()


########################################################
#### BIBLIOTECAS
########################################################
from google.cloud import bigquery
from google.oauth2 import service_account

########################################################
#### CONFIGURAÇÕES (edite só aqui)
########################################################
PROJETO_GCP  = "avaliacao-alfabetizacao-inep"
DATASET_GOLD = "ouro_analytics"
LOCALIZACAO  = "southamerica-east1"

CAMINHO_BASE = "/Volumes/workspace/default/inep_avaliacao_alfabetizacao"
CAMINHO_GOLD = f"{CAMINHO_BASE}/gold"
CHAVE_PATH   = f"{CAMINHO_BASE}/avaliacao-alfabetizacao-inep-key.json"

# Tabelas da camada Gold que serão publicadas no BigQuery.
# Para publicar outra tabela, basta adicionar o nome da pasta aqui.
TABELAS = [
    "ouro_modelagem",
    # "escola_unido",
    # "uf_unido",
]

########################################################
#### FUNÇÕES
########################################################
def criar_cliente_bigquery(chave_path: str, projeto: str) -> bigquery.Client:
    """Cria o cliente do BigQuery autenticado com a Service Account."""
    credenciais = service_account.Credentials.from_service_account_file(chave_path)
    return bigquery.Client(credentials=credenciais, project=projeto)


def garantir_dataset(client: bigquery.Client, projeto: str, dataset: str, localizacao: str) -> None:
    """Cria o dataset no BigQuery caso ele ainda não exista."""
    dataset_ref = bigquery.Dataset(f"{projeto}.{dataset}")
    dataset_ref.location = localizacao
    client.create_dataset(dataset_ref, exists_ok=True)
    print(f"Dataset '{dataset}' verificado/criado.")


def publicar_tabela(client: bigquery.Client, tabela: str) -> int:
    """Lê uma tabela Parquet da camada Gold e sobrescreve no BigQuery.
    Retorna o número de linhas publicadas."""
    origem  = f"{CAMINHO_GOLD}/{tabela}/"
    destino = f"{PROJETO_GCP}.{DATASET_GOLD}.{tabela}"

    df_pandas = spark.read.parquet(origem).toPandas()

    job = client.load_table_from_dataframe(
        df_pandas,
        destino,
        job_config=bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE"),
    )
    job.result()  # aguarda a conclusão do envio

    return len(df_pandas)

########################################################
#### EXECUÇÃO
########################################################
client = criar_cliente_bigquery(CHAVE_PATH, PROJETO_GCP)
garantir_dataset(client, PROJETO_GCP, DATASET_GOLD, LOCALIZACAO)

sucessos, falhas = [], []

for tabela in TABELAS:
    try:
        linhas = publicar_tabela(client, tabela)
        sucessos.append(tabela)
        print(f"✅ {tabela}: {linhas:,} linhas publicadas.")
    except Exception as erro:
        falhas.append(tabela)
        print(f"❌ {tabela}: falhou -> {erro}")

print(f"\nResumo: {len(sucessos)} publicada(s), {len(falhas)} com falha.")
if falhas:
    print("Tabelas com falha:", falhas)