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

if not api_key:
    st.error("No se encontró la API key en el archivo .env")
    st.stop()

try:
    client = Groq(api_key=api_key)
except Exception as e:
    st.error(f"Error al inicializar el cliente: {str(e)}")
    st.stop()

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

if "historial" not in st.session_state:
    st.session_state.historial = [{"role": "system", "content": "solo habla español"}]

def procesar_respuesta(respuesta: str, modelo: str):
    razonamiento = None
    if modelo.startswith("deepseek"):
        coincidencia = re.search(r"<think>(.*?)</think>", respuesta, re.DOTALL)
        if coincidencia:
            razonamiento = coincidencia.group(1).strip()
            respuesta = re.sub(r"<think>.*?</think>", "", respuesta, flags=re.DOTALL).strip()
    
    # Procesar el texto para eliminar indentación excesiva
    lineas = respuesta.split('\n')
    respuesta_procesada = []
    
    for linea in lineas:
        # Eliminar indentación excesiva
        linea = linea.strip()
        if linea:
            # Convertir fórmulas matemáticas
            linea = re.sub(r'\[(.*?)\]', r'$\1$', linea)
            respuesta_procesada.append(linea)
    
    # Unir las líneas con doble salto para mejor legibilidad
    respuesta_final = '\n\n'.join(respuesta_procesada)
    
    return razonamiento, respuesta_final

for mensaje in st.session_state.historial:
    if mensaje["role"] == "user":
        with st.chat_message("user"):
            st.markdown(mensaje["content"])
    elif mensaje["role"] == "assistant":
        razonamiento, contenido_limpio = procesar_respuesta(mensaje["content"], modelo_elegido)
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
    st.session_state.historial.append({"role": "user", "content": entrada_usuario})

    with st.spinner("Pensando..."):
        try:
            mensajes_api = [{"role": m["role"], "content": m["content"]} for m in st.session_state.historial]
            chat_completion = client.chat.completions.create(
                messages=mensajes_api,
                model=modelo_elegido,
                temperature=temperatura,
            )

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

        except Exception as e:
            st.error(f"Error al procesar la respuesta: {str(e)}")
            st.session_state.historial.pop()
            st.stop()

    st.rerun()
