import pandas as pd
from agent.query_engine import _columna_con_nombre, _columna_con_genero, _columna_con_score, _normalizar # Importar helpers
import json
import os
import requests
from typing import Tuple, Dict, Any
import re

# Google AI API
import google.generativeai as genai

# Reemplaza con tu API key de Google AI
GOOGLE_API_KEY = "AIzaSyA9r_1iHXKhkKjuXw4Hi-01wDuR6pL6Q3o"

# RAWG API Configuration
RAWG_API_KEY = "c55b39ab9c9546e4a94da2a1e9a6985f"  # Replace with your RAWG API key
RAWG_BASE_URL = "https://api.rawg.io/api/v1"

# Configura la API key de Google AI
genai.configure(api_key=GOOGLE_API_KEY)

# Selecciona el modelo de Google AI
# Puedes probar con 'gemini-pro' o 'gemini-1.5-flash-latest'
MODEL_NAME = "gemini-1.5-flash-latest"

def _mejorar_normalizacion(texto: str) -> str:
    """Mejora la normalización del texto para búsquedas más efectivas."""
    if not isinstance(texto, str):
        return ""
    
    # Convertir a minúsculas
    texto = texto.lower()
    
    # Eliminar caracteres especiales pero mantener espacios
    texto = re.sub(r'[^\w\s]', ' ', texto)
    
    # Eliminar espacios múltiples
    texto = re.sub(r'\s+', ' ', texto)
    
    # Eliminar espacios al inicio y final
    texto = texto.strip()
    
    return texto

def _extraer_palabras_clave(texto: str) -> list:
    """Extrae palabras clave relevantes del texto."""
    # Palabras comunes a ignorar
    stop_words = {'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas', 'y', 'o', 'de', 'del', 'en', 'con', 'por', 'para', 'que', 'cual', 'cuales', 'como', 'donde', 'cuando', 'quien', 'quienes'}
    
    # Normalizar el texto
    texto_norm = _mejorar_normalizacion(texto)
    
    # Dividir en palabras
    palabras = texto_norm.split()
    
    # Filtrar stop words y palabras muy cortas
    palabras_clave = [palabra for palabra in palabras if palabra not in stop_words and len(palabra) > 2]
    
    return palabras_clave

def buscar_info_relevante(df, pregunta):
    """Busca información relevante en el dataset para la pregunta en múltiples columnas."""
    if df.empty:
        return "El dataset está vacío.\n", pd.DataFrame()

    # Extraer palabras clave de la pregunta
    palabras_clave = _extraer_palabras_clave(pregunta)
    if not palabras_clave:
        return "No se pudieron extraer palabras clave relevantes de la pregunta.\n", pd.DataFrame()

    col_nombre = _columna_con_nombre(df)
    col_score = _columna_con_score(df)
    col_genero = _columna_con_genero(df)

    # Columnas donde buscar
    columnas_busqueda = []
    if col_nombre: columnas_busqueda.append(col_nombre)
    if col_genero: columnas_busqueda.append(col_genero)
    if 'Review' in df.columns: columnas_busqueda.append('Review')
    if 'Console' in df.columns: columnas_busqueda.append('Console')
    if 'Genre' in df.columns: columnas_busqueda.append('Genre')
    
    if not columnas_busqueda:
        return "No se pudo identificar ninguna columna de búsqueda relevante en el dataset.\n", pd.DataFrame()

    # Realizar la búsqueda en las columnas seleccionadas
    mask = pd.Series([False] * len(df), index=df.index)
    
    for col in columnas_busqueda:
        # Convertir la columna a string y manejar NaN
        col_data = df[col].astype(str).fillna('')
        
        # Para cada palabra clave, buscar en la columna
        for palabra in palabras_clave:
            # Buscar coincidencias exactas o parciales
            mask = mask | col_data.str.contains(palabra, case=False, na=False)
            
            # Si es una columna de género, buscar también coincidencias parciales
            if col == col_genero or col == 'Genre':
                mask = mask | col_data.str.contains(palabra, case=False, na=False)

    resultados_df = df[mask].copy()

    # Si la pregunta menciona ranking/score y se encontraron resultados, ordenar por score
    palabras_ranking = ['mejor', 'top', 'ranking', 'puntuacion', 'puntuación', 'score', 'calificacion', 'calificación']
    pregunta_tiene_ranking_kw = any(palabra in _mejorar_normalizacion(pregunta) for palabra in palabras_ranking)
    
    if pregunta_tiene_ranking_kw and col_score and not resultados_df.empty:
        try:
            resultados_df[col_score] = pd.to_numeric(resultados_df[col_score], errors='coerce')
            resultados_df = resultados_df.dropna(subset=[col_score])
            resultados_df = resultados_df.sort_values(by=col_score, ascending=False)
            
            # Si la pregunta menciona un número específico, limitar resultados
            numeros = re.findall(r'\d+', pregunta)
            if numeros:
                n = int(numeros[0])
                resultados_df = resultados_df.head(n)
        except Exception as e:
            print(f"Error al ordenar por score: {e}")
            pass

    if not resultados_df.empty:
        # Limitar a un número razonable de filas
        if len(resultados_df) > 20:
            resultados_df = resultados_df.head(20)

        # Convertir las filas relevantes a un formato de texto más estructurado
        info_texto = "Información relevante del dataset:\n"
        for index, row in resultados_df.iterrows():
            game_info = f"  Juego: {row.get(col_nombre, 'N/A')}"
            if 'Console' in row:
                game_info += f", Consola: {row['Console']}"
            if 'Review' in row:
                game_info += f", Review: {row['Review'][:150]}..."
            if col_score and col_score in row and pd.notna(row[col_score]):
                game_info += f", Puntaje: {row[col_score]}"
            if col_genero and col_genero in row:
                game_info += f", Género: {row[col_genero]}"
            elif 'Genre' in row:
                game_info += f", Género: {row['Genre']}"
            
            info_texto += game_info + "\n"
        return info_texto, resultados_df
    
    return "No se encontró información relevante en el dataset con la búsqueda actual.\n", pd.DataFrame()

def get_rawg_genre_info(genre_name: str) -> Dict[str, Any]:
    """Fetch genre information from RAWG API."""
    try:
        # First, search for the genre
        search_url = f"{RAWG_BASE_URL}/genres"
        params = {
            'key': RAWG_API_KEY,
            'search': genre_name,
            'page_size': 1
        }
        response = requests.get(search_url, params=params)
        response.raise_for_status()
        
        data = response.json()
        if data['results']:
            genre_id = data['results'][0]['id']
            
            # Get detailed genre information
            genre_url = f"{RAWG_BASE_URL}/genres/{genre_id}"
            params = {'key': RAWG_API_KEY}
            response = requests.get(genre_url, params=params)
            response.raise_for_status()
            
            return response.json()
        return {}
    except Exception as e:
        print(f"Error fetching RAWG data: {e}")
        return {}

def is_genre_query(pregunta: str) -> bool:
    """Determine if the query is related to game genres."""
    palabras_genero = ['género', 'genero', 'tipo', 'categoría', 'categoria', 'estilo']
    return any(palabra in _normalizar(pregunta) for palabra in palabras_genero)

def preguntar_al_agente(df, pregunta_usuario):
    """Combina la búsqueda en el dataset con la respuesta del modelo preentrenado (Google AI)."""
    if GOOGLE_API_KEY == "TU_API_KEY_AQUI":
        return "Por favor, configura tu API key de Google AI en agent/nlp_agent.py", pd.DataFrame()

    # Primero validamos si la pregunta es sobre videojuegos
    prompt_validacion = f"""Eres un asistente que solo responde preguntas sobre videojuegos. 
    Analiza la siguiente pregunta y responde SOLO con 'SI' si es sobre videojuegos o 'NO' si no lo es.
    No des ninguna otra explicación, solo 'SI' o 'NO'.
    
    Pregunta: {pregunta_usuario}"""

    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt_validacion)
        
        if hasattr(response, 'text') and response.text:
            es_sobre_videojuegos = response.text.strip().upper() == 'SI'
            if not es_sobre_videojuegos:
                return "Lo siento, solo puedo responder preguntas relacionadas con videojuegos. Por favor, haz una pregunta sobre videojuegos.", pd.DataFrame()
    except Exception as e:
        pass

    info_dataset, resultados_df_relevante = buscar_info_relevante(df, pregunta_usuario)
    
    # Check if it's a genre query and fetch RAWG data if needed
    rawg_info = ""
    if is_genre_query(pregunta_usuario):
        # Extract genre name from the question using the model
        prompt_genre = f"""Extrae el nombre del género de videojuegos mencionado en la siguiente pregunta. 
        Responde SOLO con el nombre del género, sin explicaciones adicionales.
        
        Pregunta: {pregunta_usuario}"""
        
        try:
            model = genai.GenerativeModel(MODEL_NAME)
            response = model.generate_content(prompt_genre)
            if hasattr(response, 'text') and response.text:
                genre_name = response.text.strip()
                rawg_data = get_rawg_genre_info(genre_name)
                if rawg_data:
                    rawg_info = f"\nInformación adicional del género desde RAWG:\n"
                    rawg_info += f"Nombre: {rawg_data.get('name', 'N/A')}\n"
                    rawg_info += f"Descripción: {rawg_data.get('description', 'N/A')}\n"
                    if 'games_count' in rawg_data:
                        rawg_info += f"Total de juegos: {rawg_data['games_count']}\n"
        except Exception as e:
            print(f"Error al procesar información de RAWG: {e}")

    # Construir el prompt para el modelo con instrucciones específicas
    prompt = f"""Eres un asistente experto en videojuegos con acceso a información adicional de un dataset y RAWG API. 
    Responde la siguiente pregunta usando tu conocimiento y la *información proporcionada*.
    
    Instrucciones específicas:
    1. Si la pregunta es sobre rankings o mejores juegos, usa la información de puntuaciones del dataset.
    2. Si se menciona un número específico (ej: "top 5"), respeta ese límite en tu respuesta.
    3. Si la pregunta es sobre una saga o serie específica, busca coincidencias en los nombres de los juegos.
    4. Si la pregunta es sobre géneros, combina la información del dataset con la información de RAWG.
    5. Si la información proporcionada no es suficiente, usa tu conocimiento general.
    
    Información del dataset:
    {info_dataset}
    
    {rawg_info}
    
    Pregunta: {pregunta_usuario}
    Respuesta:"""

    respuesta_texto = ""
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)

        if hasattr(response, 'text') and response.text:
            respuesta_texto = response.text.strip()
        elif hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
            respuesta_texto = f"El modelo bloqueó la respuesta por: {response.prompt_feedback.block_reason}. Intenta reformular la pregunta."
        else:
            respuesta_texto = "El modelo no pudo generar una respuesta. Intenta de nuevo o con otra pregunta."

    except Exception as e:
        respuesta_texto = f"Ocurrió un error al llamar a la API de Google AI: {e}"
    
    return respuesta_texto, resultados_df_relevante

def interpretar_pregunta(pregunta):
    # Esta función ya no se usa directamente en la app, pero la mantenemos por si acaso.
    # La lógica principal de preguntas ahora está en preguntar_al_agente.
    return pregunta