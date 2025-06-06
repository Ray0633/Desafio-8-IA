import os
from dotenv import load_dotenv
from groq import Groq
import streamlit as st

load_dotenv()

client = Groq(api_key=os.getenv("api_key"))

modelos = ["llama-3.3-70b-versatile", "deepseek-r1-distill-llama-70b", "gemma2-9b-it"]

st.set_page_config(page_title="Chat con Groq", layout="wide")
st.title("Chatbots con Groq")
st.sidebar.title("Menú")
modelo_elegido = st.sidebar.selectbox("Modelos", modelos)

if "historial" not in st.session_state:
    st.session_state.historial = [{
        "role": "system",
        "content": "solo habla español"
    }]

for mensaje in st.session_state.historial:
    if mensaje["role"] == "user":
        with st.chat_message("🧑‍💻 Usuario"):
            st.markdown(mensaje["content"])
    elif mensaje["role"] == "assistant":
        with st.chat_message("🤖 Asistente"):
            st.markdown(mensaje["content"])

entrada_usuario = st.chat_input("Escribí tu mensaje...")

if entrada_usuario and entrada_usuario.strip():
    st.session_state.historial.append({"role": "user", "content": entrada_usuario})

    chat_completion = client.chat.completions.create(
        messages=st.session_state.historial,
        model=modelo_elegido,
    )

    respuesta = chat_completion.choices[0].message.content
    st.session_state.historial.append({"role": "assistant", "content": respuesta})

    st.rerun()
