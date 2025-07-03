import sys
import os

# Función para obtener la ruta absoluta del recurso (compatible con PyInstaller)
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

from views.main_view import MainView
from db import connection  # Se asume que en db/connection.py están definidas las funciones set_default_instance(config) y get_db_connection()
from utils.my_sql_detector import get_available_sql_servers, get_default_username

# Importamos funciones de helpers.py (exportación y extracción de datos del Treeview)
from utils.helpers import get_save_path, export_to_excel, obtener_datos_treeview
import logging
import traceback
from pathlib import Path
from sqlalchemy import text
import customtkinter as ctk
from customtkinter import CTkToplevel, CTkComboBox, CTkButton, CTkLabel, CTkEntry, CTkCheckBox


# Configuración básica de logging.
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")


def get_current_instance(engine):
    """
    Retorna el nombre de la instancia a la que se está conectado utilizando @@SERVERNAME.
    """
    with engine.connect() as conn:
        result = conn.execute(text("SELECT @@SERVERNAME AS servername")).fetchone()
        if result is not None:
            result_dict = dict(result._mapping)
            logging.debug("Resultado SELECT @@SERVERNAME: %s", result_dict)
            return result_dict.get("servername")
    return None


class ConnectionConfigDialog:
    """
    Diálogo modal para configurar la conexión.
    """
    def __init__(self, parent):
        self.result = None
        self.top = ctk.CTkToplevel(parent)
        self.top.title("Configuración de Conexión")
        self.top.geometry("500x600")
        self.top.resizable(False, False)
        
        # Server Type (fijo)
        self.server_type_label = ctk.CTkLabel(self.top, text="Server Type:")
        self.server_type_label.pack(pady=(10, 0))
        self.server_type_var = ctk.StringVar(value="Database Engine")
        self.server_type_entry = CTkEntry(self.top, textvariable=self.server_type_var, state="disabled")
        self.server_type_entry.pack(pady=5)
        
        # Server Name (ComboBox)
        self.server_name_label = ctk.CTkLabel(self.top, text="Server Name:")
        self.server_name_label.pack(pady=(10, 0))
        self.available_instances = get_available_sql_servers()
        default_server = self.available_instances[0] if self.available_instances else "Ingrese el servidor..."
        self.server_name_var = ctk.StringVar(value=default_server)
        self.server_name_combobox = CTkComboBox(self.top, variable=self.server_name_var, values=self.available_instances)
        self.server_name_combobox.pack(pady=5)
        
        # Botón para actualizar instancias
        self.refresh_button = CTkButton(self.top, text="Actualizar instancias", command=self.refresh_instances)
        self.refresh_button.pack(pady=(5, 10))
        
        # Authentication
        self.auth_label = ctk.CTkLabel(self.top, text="Authentication:")
        self.auth_label.pack(pady=(10, 0))
        self.auth_var = ctk.StringVar(value="SQL Server Authentication")
        self.auth_combobox = CTkComboBox(
            self.top, 
            variable=self.auth_var,
            values=["Windows Authentication", "SQL Server Authentication"],
            command=self.on_auth_changed
        )
        self.auth_combobox.pack(pady=5)
        
        # Login
        self.login_label = ctk.CTkLabel(self.top, text="Login:")
        self.login_label.pack(pady=(10, 0))
        default_login = get_default_username()
        self.login_var = ctk.StringVar(value=default_login)
        self.login_entry = CTkEntry(self.top, textvariable=self.login_var)
        self.login_entry.pack(pady=5)
        
        # Password
        self.password_label = ctk.CTkLabel(self.top, text="Password:")
        self.password_label.pack(pady=(10, 0))
        self.password_var = ctk.StringVar(value="")
        self.password_entry = CTkEntry(self.top, textvariable=self.password_var, show="*")
        self.password_entry.pack(pady=5)
        
        # CheckBox para mostrar/ocultar contraseña
        self.show_password_var = ctk.BooleanVar(value=False)
        self.show_password_checkbox = CTkCheckBox(
            self.top, 
            text="Mostrar contraseña", 
            variable=self.show_password_var,
            command=self.toggle_password
        )
        self.show_password_checkbox.pack(pady=(0, 10))
        
        self.update_auth_fields()
        
        # Recordar password
        self.remember_var = ctk.BooleanVar(value=False)
        self.remember_checkbox = CTkCheckBox(self.top, text="Recordar password", variable=self.remember_var)
        self.remember_checkbox.pack(pady=10)
        
        # Botones para Guardar y Conectar
        self.button_frame = ctk.CTkFrame(self.top)
        self.button_frame.pack(pady=(15, 10))
        self.submit_btn = CTkButton(self.button_frame, text="Guardar", command=self.on_submit)
        self.submit_btn.grid(row=0, column=0, padx=5)
        self.connect_btn = CTkButton(self.button_frame, text="Conectar", command=self.on_connect)
        self.connect_btn.grid(row=0, column=1, padx=5)
        
        self.top.grab_set()
        parent.wait_window(self.top)

    def toggle_password(self):
        """
        Muestra u oculta la contraseña según el estado del checkbox.
        """
        if self.show_password_var.get():
            self.password_entry.configure(show="")
        else:
            self.password_entry.configure(show="*")
            
    def refresh_instances(self):
        """Actualiza la lista de instancias de SQL Server."""
        self.available_instances = get_available_sql_servers()
        self.server_name_combobox.configure(values=self.available_instances)
        if self.available_instances:
            self.server_name_var.set(self.available_instances[0])
        logging.debug("Instancias actualizadas: %s", self.available_instances)

    def on_auth_changed(self, new_value):
        self.update_auth_fields()

    def update_auth_fields(self):
        """
        Si se utiliza Windows Authentication, deshabilita los campos Login y Password;
        en caso contrario, se habilitan.
        """
        if self.auth_var.get() == "Windows Authentication":
            self.login_entry.configure(state="disabled")
            self.password_entry.configure(state="disabled")
            self.login_var.set(get_default_username())
            self.password_var.set("")
        else:
            self.login_entry.configure(state="normal")
            self.password_entry.configure(state="normal")

    def on_submit(self):
        """Recoge la configuración sin probar la conexión y cierra el diálogo."""
        self.result = self.get_config()
        self.top.destroy()

    def on_connect(self):
        """
        Recoge la configuración, establece la conexión y prueba la conexión.
        Si es exitosa, muestra un MessageBox y cierra el diálogo.
        """
        self.result = self.get_config()
        connection.set_default_instance(self.result)
        logging.debug("Configuración de conexión establecida: %s", self.result)
        try:
            engine = connection.get_db_connection()
            if engine:
                instance_actual = get_current_instance(engine)
                import tkinter.messagebox as messagebox
                messagebox.showinfo("Conexión exitosa", f"Conectado a la instancia:\n{instance_actual}")
                self.top.destroy()
            else:
                raise Exception("El engine retornado es None.")
        except Exception as e:
            import tkinter.messagebox as messagebox
            messagebox.showerror("Error de conexión", f"No se pudo conectar:\n{e}")

    def get_config(self):
        """Retorna la configuración recogida en forma de diccionario."""
        return {
            "server_type": self.server_type_var.get(),
            "server_name": self.server_name_var.get(),
            "auth": self.auth_var.get(),
            "login": self.login_var.get(),
            "password": self.password_var.get(),
            "remember": self.remember_var.get()
        }


def get_connection_config(parent):
    """Muestra el diálogo de configuración y retorna la configuración ingresada."""
    dialog = ConnectionConfigDialog(parent)
    return dialog.result


def export_demo(parent, data=None):
    """
    Función de demostración para exportar datos a Excel.

    Si no se proporciona un conjunto de datos, se utilizan datos de ejemplo.
    Extrae los datos reales del Treeview (en este caso se pasan mediante 'data')
    y abre un diálogo para seleccionar dónde guardar el archivo, notificando al usuario el resultado.

    Args:
        parent: Ventana principal para el diálogo.
        data (opcional): Lista de diccionarios con los datos a exportar.
                         Si es None, se usan datos de ejemplo.
    """
    if data is None:
        data = [
            {"Columna1": "Dato 1", "Columna2": "Dato 2"},
            {"Columna1": "Dato 3", "Columna2": "Dato 4"}
        ]
    else:
        logging.debug("Datos extraídos del Treeview: %s", data)

    output_file = get_save_path(parent)
    if not output_file:
        logging.info("Exportación cancelada. No se ha guardado el archivo.")
        return

    try:
        export_to_excel(data, output_file)
    except Exception as e:
        logging.error("Error al exportar: %s", e)
        import tkinter.messagebox as messagebox
        messagebox.showerror("Error al exportar", f"Se produjo un error:\n{e}")
    else:
        logging.info("Archivo guardado exitosamente en: %s", output_file)
        import tkinter.messagebox as messagebox
        messagebox.showinfo("Exportación exitosa", f"Archivo guardado:\n{output_file}")


def run_view():
    """
    Configura la conexión mediante un diálogo y, a continuación, muestra la vista principal.
    Se añade un botón que, al presionarlo, extrae los datos actuales del Treeview de MainView
    (atributo 'tree_cruce') y los exporta a Excel.
    """
    # Ventana temporal para la configuración de conexión.
    app_temp = ctk.CTk()
    app_temp.withdraw()
    config = get_connection_config(app_temp)
    app_temp.destroy()
    connection.set_default_instance(config)
    logging.debug("Configuración final de conexión: %s", config)
    
    try:
        # Se crea la ventana principal. Asegúrate de que MainView define el widget Treeview como 'tree_cruce'
        main_app = MainView(refresh_callback=lambda: None)
        
        # Se crea un botón adicional para exportar.
        # Se extraen los datos reales usando 'obtener_datos_treeview' aplicado a 'main_app.tree_cruce'
        export_button = ctk.CTkButton(
            main_app,
            text="Exportar a Excel",
            command=lambda: export_demo(main_app, obtener_datos_treeview(main_app.tree_cruce))
        )
        export_button.grid(row=99, column=0, pady=10, sticky="ew")

        
        main_app.mainloop()
    except Exception as e:
        logging.error("Error en la aplicación: %s", e)
        traceback.print_exc()


if __name__ == "__main__":
    run_view()
