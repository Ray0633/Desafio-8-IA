import os
import re
from dotenv import load_dotenv
from groq import Groq
import streamlit as st

def load_css(css_file):
    with open(css_file) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

st.set_page_config(
    page_title="Chat con Groq",
    layout="wide",
    initial_sidebar_state="collapsed"
)

load_css('styles.css')

load_dotenv()
api_key = os.getenv("api_key")

# Configuración inicial y estado de la aplicación
api_key_available = bool(api_key)
client_initialized = False

if not api_key_available:
    st.error("No se encontró la API key en el archivo .env. La funcionalidad del chat estará desactivada.")
else:
    try:
        client = Groq(api_key=api_key)
        client_initialized = True
    except Exception as e:
        st.error(f"Error al inicializar el cliente Groq: {str(e)}. La funcionalidad del chat estará desactivada.")

modelos = ["llama-3.3-70b-versatile", "deepseek-r1-distill-llama-70b", "gemma2-9b-it"]

st.markdown("""
    <div class="title-container">
        <h1>Chat con Groq</h1>
    </div>
""", unsafe_allow_html=True)

st.sidebar.title("Configuración")

if "modelo_actual" not in st.session_state:
    st.session_state.modelo_actual = modelos[0]

modelo_elegido = st.sidebar.selectbox("Modelo", modelos, key="modelo_selector")

if modelo_elegido != st.session_state.modelo_actual:
    st.session_state.historial = [{"role": "system", "content": "solo habla español"}]
    st.session_state.modelo_actual = modelo_elegido

temperatura = st.sidebar.slider("Temperatura", 0.0, 1.5, 0.7, 0.1)

if st.sidebar.button("Limpiar chat"):
    st.session_state.historial = [{"role": "system", "content": "solo habla español"}]
    st.rerun()

# Inicialización del historial de chat solo si la configuración es exitosa
if api_key_available and client_initialized:
    if "historial" not in st.session_state:
        st.session_state.historial = [{"role": "system", "content": "solo habla español"}]
else:
    # Si la configuración falla (sin API key o cliente no inicializado),
    # se elimina cualquier historial existente para evitar interacciones inconsistentes.
    if "historial" in st.session_state:
        del st.session_state.historial

def procesar_respuesta(respuesta: str):
    """
    Procesa la respuesta del modelo para extraer el razonamiento (si existe),
    normalizar saltos de línea, eliminar indentación inicial de cada línea,
    y convertir formatos de fórmulas matemáticas.
    """
    razonamiento = None
    # Intenta extraer el contenido entre <think> y </think> como razonamiento.
    # Esto se hace independientemente del modelo.
    coincidencia_think = re.search(r"<think>(.*?)</think>", respuesta, re.DOTALL)
    if coincidencia_think:
        razonamiento = coincidencia_think.group(1).strip()
        # Elimina el bloque <think>...</think> de la respuesta principal.
        respuesta = re.sub(r"<think>.*?</think>", "", respuesta, flags=re.DOTALL).strip()
    
    # Normalizar todos los tipos de saltos de línea a \n.
    respuesta_normalizada = respuesta.replace('\r\n', '\n').replace('\r', '\n')

    lineas = respuesta_normalizada.split('\n')
    respuesta_procesada = []
    
    for linea in lineas:
        # Eliminar solo la indentación inicial (espacios y tabulaciones).
        # Se conserva el resto de espacios para mantener formatos como listas o bloques de código.
        linea_sin_indentacion = linea.lstrip()

        # Convertir fórmulas matemáticas del formato [formula] a $formula$.
        # Esto permite usar una sintaxis más simple para LaTeX en el input.
        linea_con_formulas = re.sub(r'\[(.*?)\]', r'$\1$', linea_sin_indentacion)
        respuesta_procesada.append(linea_con_formulas)
    
    # Unir las líneas procesadas con un solo salto de línea.
    # Esto preserva los párrafos que estaban separados por líneas vacías.
    respuesta_final = '\n'.join(respuesta_procesada)
    
    return razonamiento, respuesta_final

# Solo mostrar y procesar el chat si el cliente está inicializado y la API key está disponible.
if api_key_available and client_initialized:
    # Mostrar mensajes del historial
    # Asegurarse de que el historial exista y esté inicializado antes de iterar
    if "historial" not in st.session_state:
        st.session_state.historial = [{"role": "system", "content": "solo habla español"}]

    for mensaje in st.session_state.historial:
        if mensaje["role"] == "user":
            with st.chat_message("user"):
                st.markdown(mensaje["content"])
        elif mensaje["role"] == "assistant":
            # Se elimina el parámetro modelo_elegido de la llamada, ya no es necesario.
            razonamiento, contenido_limpio = procesar_respuesta(mensaje["content"])
            with st.chat_message("assistant"):
                if razonamiento:
                    with st.expander("Razonamiento"):
                        st.markdown(razonamiento)
                st.markdown(contenido_limpio)
                if "tokens" in mensaje:
                    st.caption(f"Modelo: {modelo_elegido} | Tokens: {mensaje['tokens']['total']}")
                else:
                    st.caption(f"Modelo: {modelo_elegido}")

    entrada_usuario = st.chat_input("Escribe tu mensaje...")

    if entrada_usuario and entrada_usuario.strip():
        # Asegurarse de que el historial exista antes de añadir mensajes
        if "historial" not in st.session_state:
             st.session_state.historial = [{"role": "system", "content": "solo habla español"}]
        st.session_state.historial.append({"role": "user", "content": entrada_usuario})

        with st.spinner("Pensando..."):
            try:
                mensajes_api = [{"role": m["role"], "content": m["content"]} for m in st.session_state.historial]
                chat_completion = client.chat.completions.create(
                    messages=mensajes_api,
                    model=modelo_elegido,
                    temperature=temperatura,
                )

                if chat_completion.choices and chat_completion.choices[0].message and chat_completion.choices[0].message.content:
                    respuesta = chat_completion.choices[0].message.content
                    tokens_info = {
                        "entrada": chat_completion.usage.prompt_tokens,
                        "salida": chat_completion.usage.completion_tokens,
                        "total": chat_completion.usage.prompt_tokens + chat_completion.usage.completion_tokens
                    }
                    st.session_state.historial.append({
                        "role": "assistant",
                        "content": respuesta,
                        "tokens": tokens_info
                    })
                else:
                    st.error("La API devolvió una respuesta inesperada o vacía. Por favor, intenta de nuevo.")
                    # No se elimina el mensaje del usuario del historial (no hay pop())

            except groq.APIConnectionError as e:
                st.error(f"Error de conexión con la API de Groq: {e.__class__.__name__}. Revisa tu conexión o configuración.")
            except groq.APIStatusError as e:
                st.error(f"Error de la API de Groq (código {e.status_code}): {e.message}")
            except groq.APIError as e: # Otros errores de la API de Groq
                st.error(f"Error de la API de Groq: {e.__class__.__name__}. {str(e)}")
            except Exception as e: # Fallback para otros errores
                st.error(f"Ocurrió un error inesperado: {str(e)}")
            # No st.stop() aquí, st.rerun() se encargará de actualizar la UI.

        st.rerun()
else:
    st.warning("La funcionalidad de chat está desactivada debido a problemas de configuración (API key o inicialización del cliente).")
    # Deshabilitar explícitamente el chat_input si es posible o necesario
    st.chat_input("Escribe tu mensaje...", disabled=True)
