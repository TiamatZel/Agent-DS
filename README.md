# Video Game Assistant IA

Este proyecto es un asistente virtual inteligente capaz de responder instantáneamente a consultas sobre videojuegos, desde características técnicas hasta datos históricos, usando una base de datos constantemente actualizada.

## Características
- Responde preguntas sobre videojuegos (plataforma, género, desarrollador, año, ventas, etc.).
- Permite búsquedas y comparaciones entre juegos.
- Base de datos actualizable fácilmente.
- Interfaz sencilla (CLI, web o chatbot).

## Estructura del Proyecto
```
/video-game-assistant
│
├── data/                # Dataset descargado de Kaggle
├── agent/               # Lógica del agente
│   ├── data_loader.py   # Carga y limpieza de datos
│   ├── query_engine.py  # Motor de consultas
│   └── nlp_agent.py     # Procesamiento de lenguaje natural
├── app.py               # API o interfaz principal
├── requirements.txt     # Dependencias
└── README.md            # Este archivo
```

## Primeros pasos
1. Descarga el dataset de Kaggle y colócalo en la carpeta `data/`.
2. Instala las dependencias: `pip install -r requirements.txt`
3. Ejecuta la aplicación: `streamlit run app.py`

--- 