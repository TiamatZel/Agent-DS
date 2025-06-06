import streamlit as st
import pandas as pd # Importar pandas para inicializar DataFrame en session_state
from agent.data_loader import cargar_datos
from agent.nlp_agent import preguntar_al_agente
from agent.query_engine import buscar_juego # Eliminar juegos_por_genero de la importación si no se usa aquí

st.title('Video Game Assistant IA')

# Inicializar st.session_state si no existe
if 'df_principal' not in st.session_state:
    st.session_state['df_principal'] = pd.DataFrame() # Inicializar con DataFrame vacío
    st.session_state['df_cargado'] = None # Para guardar el DataFrame completo una vez cargado

# Cargar datos (solo una vez)
if st.session_state['df_cargado'] is None:
    try:
        df_completo = cargar_datos()
        st.session_state['df_cargado'] = df_completo
        st.session_state['df_principal'] = df_completo # Mostrar todo el dataset al inicio
        st.success('Datos cargados correctamente.')
    except Exception as e:
        st.error(f'Error al cargar los datos: {e}')

df = st.session_state['df_cargado'] # Usar el DataFrame cargado para el agente y búsqueda directa

# Interfaz de preguntas en lenguaje natural

def mostrar_agente_nlp(df_completo):
    st.header('Pregunta al Agente IA')
    pregunta = st.text_input('Escribe tu pregunta sobre videojuegos', key='nlp_input') # Usar key única
    
    # Botón para preguntar
    if st.button('Preguntar', key='nlp_button') and pregunta:
        if df_completo is not None:
            with st.spinner('El agente está pensando...'):
                respuesta_texto, resultados_df = preguntar_al_agente(df_completo, pregunta)
                st.write('Respuesta del Agente:')
                st.write(respuesta_texto)
                # Actualizar el DataFrame principal con los resultados relevantes del agente
                st.session_state['df_principal'] = resultados_df
        else:
            st.warning('No se pudieron cargar los datos para consultar al agente.')

# Interfaz de búsqueda directa por nombre
def mostrar_busqueda_directa(df_completo):
    st.header('Buscar Directamente por Nombre') # Título actualizado
    
    # Usamos st.form y st.form_submit_button para el botón de búsqueda
    with st.form(key='direct_search_form'):
        nombre = st.text_input('Buscar por Nombre', key='direct_name_input_form') # Usar key única para el form
        buscar_button = st.form_submit_button('Buscar')

    # La búsqueda se activa solo cuando se presiona el botón
    if buscar_button and nombre:
        if df_completo is not None:
            resultados_df, col_usada = buscar_juego(df_completo, nombre)
            st.caption(f'Buscando por nombre en la columna: {col_usada}')
            st.session_state['df_principal'] = resultados_df # Actualizar la tabla con resultados de búsqueda
        else:
            st.warning('No se pudieron cargar los datos para la búsqueda directa.')
    # Si el campo de nombre está vacío después de presionar buscar, la tabla no se actualiza con un DataFrame vacío aquí.

# Mostrar la interfaz si los datos están cargados
if df is not None:
    mostrar_agente_nlp(df) # Sección del Agente IA
    st.markdown('---') # Separador
    mostrar_busqueda_directa(df) # Sección de Búsqueda Directa por Nombre

    # Mostrar la tabla principal (siempre visible) basándose en st.session_state
    if not st.session_state['df_principal'].empty:
         st.write(f'Mostrando {len(st.session_state['df_principal'])} resultados:')
         st.dataframe(st.session_state['df_principal'])
    elif df is not None: # Si la tabla está vacía pero el dataset completo existe
        st.write('No se encontraron resultados relevantes con la búsqueda actual.')
        # Opcional: mostrar el dataset completo si no hay resultados en la búsqueda actual
        # st.write('Mostrando el dataset completo:')
        # st.dataframe(df)
    else:
        st.write('Cargando datos...') # Mensaje si el df completo aún no está cargado

else:
    st.warning('Esperando a que los datos se carguen correctamente.')

# Eliminamos la sección de búsqueda directa por nombre para simplificar la interfaz.
# La lógica del agente NLP ahora maneja la búsqueda y actualización de la tabla. 