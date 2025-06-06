import pandas as pd
import os

def cargar_datos(nombre_archivo='videogames.csv'):
    ruta = os.path.join('data', nombre_archivo)
    if not os.path.exists(ruta):
        raise FileNotFoundError(f'No se encontró el archivo {ruta}')
    df = pd.read_csv(ruta)
    # Aquí puedes agregar limpieza de datos si es necesario
    return df 