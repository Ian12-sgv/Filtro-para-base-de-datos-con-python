import re
import pandas as pd
from sqlalchemy import create_engine, text
from tkinter import messagebox
from urllib.parse import quote_plus
from queries.query_cruce import get_query_cruce

# Variable global para el connection string
DEFAULT_CONNECTION_STR = None

def set_default_instance(config):
    """
    Configura la cadena de conexión a partir del diccionario 'config'.
    """
    global DEFAULT_CONNECTION_STR
    password_enc = quote_plus(config['password'])
    DEFAULT_CONNECTION_STR = (
        f"mssql+pyodbc://{config['login']}:{password_enc}@{config['server_name']}/BODEGA_DATOS?driver=SQL+Server"
    )

def get_db_connection(connection_str=None):
    """
    Retorna una instancia de engine para la conexión a la base de datos.
    Ajusta el pool de conexiones con pool_size y max_overflow.
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
    Garantiza que la parte final del query (a partir de 'FROM final_alias')
    cuente con una cláusula WHERE. Si no la contiene, inyecta "WHERE 1 = 1".
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
    Ejecuta el query base generado por get_query_cruce(), inyectando filtros adicionales.
    Retorna un listado (lista de diccionarios) con los datos obtenidos.
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

    # Seleccionar la fecha de inicio según la opción
    if fecha_option == 1:
        params["fechaStart"] = '2023-01-01'
    else:
        params["fechaStart"] = '2024-01-01'

    # Obtener el query base y quitar el punto y coma final si existe
    base_query = get_query_cruce().strip()
    if base_query.endswith(';'):
        base_query = base_query[:-1]

    # Inyectar el valor de :fechaStart en la parte WITH para evitar discrepancias de estructura
    base_query = base_query.replace(":fechaStart", f"'{params['fechaStart']}'")
    del params["fechaStart"]

    base_query = ensure_final_where(base_query, final_alias="Final2")
    filter_clause = " AND " + " AND ".join(conditions) if conditions else ""
    full_sql = base_query + filter_clause + " ORDER BY FechaLlegada ASC"
    
    full_query = text(full_sql)
    with engine.connect() as conn:
        result = conn.execute(full_query, params).fetchall()
    data = [dict(row._mapping) for row in result]
    return data

def get_cruce_data_df(engine, codigo_filter=None, referencia_filter=None,
                       categoria_filter=None, linea_filter=None, fabrica_filter=None,
                       fecha_option=2, chunksize=50000):
    """
    Versión para exploración interactiva.
    Ejecuta el query con filtros aplicados y devuelve un DataFrame de Pandas.
    Se utiliza 'chunksize' para procesar grandes volúmenes de datos de forma iterativa.
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

    if fecha_option == 1:
        params["fechaStart"] = '2023-01-01'
    else:
        params["fechaStart"] = '2024-01-01'

    base_query = get_query_cruce().strip()
    if base_query.endswith(';'):
        base_query = base_query[:-1]

    base_query = base_query.replace(":fechaStart", f"'{params['fechaStart']}'")
    del params["fechaStart"]

    base_query = ensure_final_where(base_query, final_alias="Final2")
    filter_clause = " AND " + " AND ".join(conditions) if conditions else ""
    full_sql = base_query + filter_clause + " ORDER BY FechaLlegada ASC"

    # Procesamiento en chunks para reducir uso de memoria y gestionar grandes volúmenes
    df_iter = pd.read_sql(full_sql, con=engine, params=params, chunksize=chunksize)
    df = pd.concat(df_iter, ignore_index=True)
    return df
