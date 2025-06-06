# Motor de consultas para el asistente de videojuegos

import unicodedata
import pandas as pd
import requests
import json
import os

RAWG_API_KEY = "TU_API_KEY_AQUI"  # <--- Pega aquí tu API key de RAWG
RAWG_API_URL = "https://api.rawg.io/api/games"
CACHE_FILE = "cache_generos.json"

def _columna_con_nombre(df):
    posibles = ['name', 'title', 'game', 'nombre', 'gamename', 'game_name', 'game title']
    for col in df.columns:
        if col.strip().lower() in posibles:
            return col
    return df.columns[0]

def _columna_con_genero(df):
    posibles = ['genre', 'genero', 'category', 'categoría']
    for col in df.columns:
        if col.strip().lower() in posibles:
            return col
    return None

def _columna_con_score(df):
    posibles = ['score', 'puntaje', 'calificacion', 'rating']
    for col in df.columns:
        if col.strip().lower() in posibles:
            return col
    return None

def _normalizar(texto):
    if not isinstance(texto, str):
        texto = str(texto)
    texto = texto.lower()
    texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('utf-8')
    return texto

def _agrupar_promediar(df):
    col_nombre = _columna_con_nombre(df)
    col_score = _columna_con_score(df)
    if col_score is None:
        return df.drop_duplicates(subset=[col_nombre])
    agrupado = df.groupby(col_nombre, as_index=False).agg({col_score: 'mean'})
    agrupado[col_score] = agrupado[col_score].round(2)
    return agrupado

def _cargar_cache_generos():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def _guardar_cache_generos(cache):
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def obtener_generos_rawg(nombre_juego):
    cache = _cargar_cache_generos()
    nombre_norm = _normalizar(nombre_juego)
    if nombre_norm in cache:
        return cache[nombre_norm]
    if RAWG_API_KEY == "TU_API_KEY_AQUI":
        return []  # No hay API key
    params = {"key": RAWG_API_KEY, "search": nombre_juego, "page_size": 1}
    try:
        resp = requests.get(RAWG_API_URL, params=params, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data["results"]:
                generos = [g["name"].lower() for g in data["results"][0]["genres"]]
                cache[nombre_norm] = generos
                _guardar_cache_generos(cache)
                return generos
    except Exception:
        pass
    cache[nombre_norm] = []
    _guardar_cache_generos(cache)
    return []

def buscar_juego(df, nombre):
    col = _columna_con_nombre(df)
    nombre_norm = _normalizar(nombre)
    resultados = df[df[col].apply(lambda x: nombre_norm in _normalizar(x))]
    resultados = _agrupar_promediar(resultados)
    return resultados, col

def juegos_por_genero(df, genero):
    col = _columna_con_genero(df)
    genero_norm = _normalizar(genero)
    if col:
        resultados = df[df[col].apply(lambda x: genero_norm in _normalizar(x))]
        resultados = _agrupar_promediar(resultados)
        return resultados, col
    else:
        # Usar RAWG API para inferir género
        col_nombre = _columna_con_nombre(df)
        juegos = []
        for _, row in df.iterrows():
            nombre_juego = row[col_nombre]
            generos = obtener_generos_rawg(nombre_juego)
            if genero_norm in [g.lower() for g in generos]:
                juegos.append(row)
        if juegos:
            resultados = pd.DataFrame(juegos)
            resultados = _agrupar_promediar(resultados)
            return resultados, None
        else:
            return df.iloc[0:0], None 