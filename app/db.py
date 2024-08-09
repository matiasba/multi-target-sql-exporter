from sqlalchemy import create_engine, text
import pandas as pd


def execute_query(db_config, query):
    engine = str(db_config['engine']).lower()
    match engine:
        case "mysql":
            driver = "mysql+pymysql"
        case "postgres":
            driver = "postgresql+psycopg2"
        case "oracle":
            driver = "oracle+oracledb"
        case "mssql":
            driver = "mssql+pymssql"
        case _:
            raise Exception(f"unknown or unsupported engine: {engine}")
    engine = create_engine(
        f'{driver}://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}')
    try:
        with engine.connect() as conn, conn.begin():
            df = pd.read_sql(text(query), engine)
    finally:
        engine.dispose()
    return df
