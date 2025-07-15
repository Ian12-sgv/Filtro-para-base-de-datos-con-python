import re
import pandas as pd
from sqlalchemy import create_engine, text
from tkinter import messagebox
from urllib.parse import quote_plus
from queries.query_cruce import get_query_cruce

# Variable global para el connection string
DEFAULT_CONNECTION_STR = None

# Instancias predefinidas (solo estas se permiten)
PREDEFINED_INSTANCES = {
    "Servidor DOS": {
        "server_name": "SERVERDOS\\SERVERSQL_DOS",
        "login": "sa",
        "password": "j2094l,."
    },
    "Analista Local": {
        "server_name": "DESKTOP-POHBVL8\\ANALISTA",
        "login": "sa",
        "password": "123456"
    }
}

def set_default_instance(alias):
    """
    Configura la cadena de conexión usando un alias predefinido.
    No admite instancias manuales ni detección dinámica.
    """
    global DEFAULT_CONNECTION_STR

    if alias not in PREDEFINED_INSTANCES:
        raise ValueError(f"Alias '{alias}' no reconocido.")

    config = PREDEFINED_INSTANCES[alias]

    password_enc = quote_plus(config['password'])
    DEFAULT_CONNECTION_STR = (
        f"mssql+pyodbc://{config['login']}:{password_enc}@{config['server_name']}/BODEGA_DATOS?driver=SQL+Server"
    )

def get_db_connection(connection_str=None):
    """
    Retorna una instancia de engine para la conexión a la base de datos.
    """
    try:
        connection_str = connection_str or DEFAULT_CONNECTION_STR
        if not connection_str:
            raise ValueError("No se ha configurado el connection string.")
        return create_engine(connection_str, pool_size=10, max_overflow=20)
    except Exception as e:
        messagebox.showerror("Error de conexión", f"No se pudo crear el engine: {e}")
        return None

def ensure_final_where(query_base, final_alias="Final2"):
    """
    Garantiza que la parte final del query cuente con una cláusula WHERE.
    """
    m = re.search(rf"(FROM\s+{final_alias}\b.*)$", query_base, flags=re.IGNORECASE | re.DOTALL)
    if m:
        final_clause = m.group(1)
        if not re.search(r"\bWHERE\b", final_clause, flags=re.IGNORECASE):
            new_final_clause = final_clause + " WHERE 1 = 1"
        else:
            new_final_clause = final_clause
        query_base = query_base[:m.start()] + new_final_clause
    else:
        query_base += " WHERE 1 = 1"
    return query_base

def get_cruce_data(engine, codigo_filter=None, referencia_filter=None,
                   categoria_filter=None, linea_filter=None, fabrica_filter=None,
                   fecha_option=2):
    """
    Ejecuta el query de cruce con filtros y retorna lista de diccionarios.
    """
    conditions = []
    params = {}

    if codigo_filter:
        conditions.append("CodigoBarra = :codigoFilter")
        params["codigoFilter"] = codigo_filter
    if referencia_filter:
        conditions.append("LOWER(LTRIM(RTRIM(Final2.CleanReferencia))) = :referenciaFilter")
        params["referenciaFilter"] = referencia_filter.strip().lower()
    if categoria_filter:
        conditions.append("CategoriaNombre = :categoriaFilter")
        params["categoriaFilter"] = categoria_filter
    if linea_filter:
        conditions.append("Linea = :lineaFilter")
        params["lineaFilter"] = linea_filter
    if fabrica_filter:
        conditions.append("CodigoFabricante = :fabricaFilter")
        params["fabricaFilter"] = fabrica_filter

    params["fechaStart"] = '2023-01-01' if fecha_option == 1 else '2024-01-01'

    base_query = get_query_cruce().strip().rstrip(';')
    base_query = base_query.replace(":fechaStart", f"'{params['fechaStart']}'")
    del params["fechaStart"]

    base_query = ensure_final_where(base_query, "Final2")
    filter_clause = " AND " + " AND ".join(conditions) if conditions else ""
    full_sql = base_query + filter_clause + " ORDER BY FechaLlegada ASC"

    with engine.connect() as conn:
        result = conn.execute(text(full_sql), params).fetchall()
    return [dict(row._mapping) for row in result]

def get_cruce_data_df(engine, codigo_filter=None, referencia_filter=None,
                      categoria_filter=None, linea_filter=None, fabrica_filter=None,
                      fecha_option=2, chunksize=50000):
    """
    Versión para Pandas DataFrame.
    """
    conditions = []
    params = {}

    if codigo_filter:
        conditions.append("CodigoBarra = :codigoFilter")
        params["codigoFilter"] = codigo_filter
    if referencia_filter:
        conditions.append("LOWER(LTRIM(RTRIM(Final2.CleanReferencia))) = :referenciaFilter")
        params["referenciaFilter"] = referencia_filter.strip().lower()
    if categoria_filter:
        conditions.append("CategoriaNombre = :categoriaFilter")
        params["categoriaFilter"] = categoria_filter
    if linea_filter:
        conditions.append("Linea = :lineaFilter")
        params["lineaFilter"] = linea_filter
    if fabrica_filter:
        conditions.append("CodigoFabricante = :fabricaFilter")
        params["fabricaFilter"] = fabrica_filter

    params["fechaStart"] = '2023-01-01' if fecha_option == 1 else '2024-01-01'

    base_query = get_query_cruce().strip().rstrip(';')
    base_query = base_query.replace(":fechaStart", f"'{params['fechaStart']}'")
    del params["fechaStart"]

    base_query = ensure_final_where(base_query, "Final2")
    filter_clause = " AND " + " AND ".join(conditions) if conditions else ""
    full_sql = base_query + filter_clause + " ORDER BY FechaLlegada ASC"

    df_iter = pd.read_sql(full_sql, con=engine, params=params, chunksize=chunksize)
    return pd.concat(df_iter, ignore_index=True)
