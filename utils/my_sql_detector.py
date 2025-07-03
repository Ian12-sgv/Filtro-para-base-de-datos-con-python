# utils/my_sql_detector.py

import subprocess
import getpass

def get_available_sql_servers():
    """
    Usa el comando 'sqlcmd -L' para listar las instancias de SQL Server visibles en la red.
    Devuelve una lista de nombres de instancias.
    """
    try:
        output = subprocess.check_output(["sqlcmd", "-L"], stderr=subprocess.STDOUT, text=True)
        # La salida suele tener un formato similar a:
        # Servers:
        #    DESKTOP-ABC\SQLEXPRESS
        #    SERVER1\INSTANCE1
        # Se filtra quitando la línea de encabezado y espacios en blanco.
        lines = output.splitlines()
        instances = []
        for line in lines:
            line = line.strip()
            if line and not line.lower().startswith("servers"):
                instances.append(line)
        return instances
    except subprocess.CalledProcessError as e:
        print("Error al ejecutar sqlcmd -L:", e.output)
        return []
    except Exception as ex:
        print("Error inesperado al listar instancias:", ex)
        return []

def get_default_username():
    """
    Retorna el nombre de usuario actual del sistema.
    Útil para Windows Authentication.
    """
    return getpass.getuser()
