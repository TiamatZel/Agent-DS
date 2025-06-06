import pandas as pd
from agent.query_engine import _columna_con_nombre, _columna_con_genero, _columna_con_score, _normalizar # Importar helpers
import json
import os

# Google AI API
import google.generativeai as genai

# Reemplaza con tu API key de Google AI
GOOGLE_API_KEY = "AIzaSyA9r_1iHXKhkKjuXw4Hi-01wDuR6pL6Q3o"

# Configura la API key de Google AI
genai.configure(api_key=GOOGLE_API_KEY)

# Selecciona el modelo de Google AI
# Puedes probar con 'gemini-pro' o 'gemini-1.5-flash-latest'
MODEL_NAME = "gemini-1.5-flash-latest"

# Procesamiento de lenguaje natural para interpretar preguntas de usuario

def buscar_info_relevante(df, pregunta):
    """Busca información relevante en el dataset para la pregunta en múltiples columnas."""
    pregunta_norm = _normalizar(pregunta)
    if not pregunta_norm: # Si la pregunta normalizada está vacía, no hay nada que buscar
        return "No se encontró información relevante en el dataset.\n", pd.DataFrame()

    col_nombre = _columna_con_nombre(df)

    # Columnas donde buscar (además del nombre)
    columnas_busqueda = []
    if col_nombre: columnas_busqueda.append(col_nombre)
    if 'Review' in df.columns: columnas_busqueda.append('Review')
    if 'Console' in df.columns: columnas_busqueda.append('Console')
    # No incluimos 'Score' directamente en la búsqueda textual para evitar coincidencias no deseadas con números dentro de texto
    # El modelo puede interpretar preguntas sobre scores basándose en otras columnas si son relevantes.

    if not columnas_busqueda:
        return "No se pudo identificar ninguna columna de búsqueda relevante en el dataset.\n", pd.DataFrame()

    # Realizar la búsqueda en las columnas seleccionadas
    # Creamos una máscara booleana combinando la búsqueda en cada columna
    mask = pd.Series([False] * len(df), index=df.index) # Inicializar máscara a False
    for col in columnas_busqueda:
        # Aplicar la normalización y verificar si la pregunta normalizada está contenida en el texto de la columna
        mask = mask | df[col].astype(str).apply(lambda x: pregunta_norm in _normalizar(x))

    resultados_df = df[mask].copy() # Usar .copy() para evitar SettingWithCopyWarning

    if not resultados_df.empty:
        # Limitar a un número razonable de filas para no exceder el contexto del modelo
        if len(resultados_df) > 20: # Aumentado ligeramente el límite
            resultados_df = resultados_df.head(20)

        # Convertir las filas relevantes a un formato de texto más estructurado para el modelo
        info_texto = "Información relevante del dataset:\n"
        for index, row in resultados_df.iterrows():
             # Formatear la información de cada fila
             game_info = f"  Juego: {row.get(col_nombre, 'N/A')}"
             if 'Console' in row:
                 game_info += f", Consola: {row['Console']}"
             if 'Review' in row:
                 game_info += f", Review: {row['Review'][:150]}..." # Limitar longitud de review
             if 'Score' in row:
                 game_info += f", Puntaje: {row['Score']}"
             # Añadir otras columnas relevantes si existen y no están ya incluidas
             for other_col in df.columns:
                 if other_col not in columnas_busqueda and other_col != col_nombre and other_col not in ['Score']:
                      # Solo añadir si el valor no es nulo/vacío y no es un objeto complejo
                      if pd.notna(row[other_col]) and str(row[other_col]).strip() and not isinstance(row[other_col], (list, dict)):
                           game_info += f", {other_col}: {row[other_col]}"

             info_texto += game_info + "\n"
        return info_texto, resultados_df
    return "No se encontró información **directamente** relevante en el dataset con la búsqueda actual.\n", pd.DataFrame()

def preguntar_al_agente(df, pregunta_usuario):
    """Combina la búsqueda en el dataset con la respuesta del modelo preentrenado (Google AI)."""
    if GOOGLE_API_KEY == "TU_API_KEY_AQUI": # Mantener el check por si acaso
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
        # Si hay un error en la validación, continuamos con la pregunta original
        pass

    info_dataset, resultados_df_relevante = buscar_info_relevante(df, pregunta_usuario)

    # Construir el prompt para el modelo
    prompt = f"Eres un asistente experto en videojuegos con acceso a información adicional de un dataset. Responde la siguiente pregunta usando tu conocimiento y la *información del dataset proporcionada*, si es relevante. Si la información del dataset no es suficiente, usa tu conocimiento general. \n\nInformación ADICIONAL del dataset:\n{info_dataset}\n\nPregunta: {pregunta_usuario}\nRespuesta:"

    respuesta_texto = ""
    try:
        # Llamar al modelo de Google AI
        model = genai.GenerativeModel(MODEL_NAME)
        # Usar generate_content que es más flexible que generate_text
        response = model.generate_content(prompt)

        # Verificar si la respuesta contiene contenido y manejar posibles bloqueos
        if hasattr(response, 'text') and response.text:
             respuesta_texto = response.text.strip()
        elif hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
             respuesta_texto = f"El modelo bloqueó la respuesta por: {response.prompt_feedback.block_reason}. Intenta reformular la pregunta."
        else:
             respuesta_texto = "El modelo no pudo generar una respuesta. Intenta de nuevo o con otra pregunta."

    except Exception as e:
        # Manejo de errores de la API de Google AI u otros errores
        respuesta_texto = f"Ocurrió un error al llamar a la API de Google AI: {e}"
    
    return respuesta_texto, resultados_df_relevante

def interpretar_pregunta(pregunta):
    # Esta función ya no se usa directamente en la app, pero la mantenemos por si acaso.
    # La lógica principal de preguntas ahora está en preguntar_al_agente.
    return pregunta