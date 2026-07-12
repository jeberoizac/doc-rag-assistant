import streamlit as st
import os, tempfile
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import ChatGoogleGenerativeAI

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# Configuración segura de la API Key para desarrollo local y OCI
if "GEMINI_API_KEY" in st.secrets:
    os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]
elif "GEMINI_API_KEY" not in os.environ:
    st.error("Falta la API Key de Gemini. Por favor, configúrala en tus variables de entorno o st.secrets.")
    st.stop()

st.set_page_config(page_title="Agente RAG Alura", page_icon="🤖")
st.title("🤖 Mi Agente Lector de Documentos")

