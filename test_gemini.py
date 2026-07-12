import streamlit as st
from langchain_google_genai import ChatGoogleGenerativeAI

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=st.secrets["GEMINI_API_KEY"],
    temperature=0
)

respuesta = llm.invoke("Hola, ¿quién eres?")

print(respuesta.content)



###################### parte 2 #####
# Inicializar el historial de chat en la memoria de Streamlit si no existe
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Función optimizada para procesar el documento UNA sola vez por archivo
@st.cache_resource(show_spinner=False)
def procesar_documento(file_bytes, file_name):
    temp_file_path = f"temp_{file_name}"
    with open(temp_file_path, "wb") as f:
        f.write(file_bytes)
    
    if file_name.endswith(".pdf"):
        loader = PyPDFLoader(temp_file_path)
    else:
        loader = Docx2txtLoader(temp_file_path)
    docs = loader.load()
    
    os.remove(temp_file_path)
    
    # Fragmentación del texto
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(docs)
    
    # Crear Base de Datos Vectorial (Local con FAISS)
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2", model_kwargs={"device": "cpu"})
    vectorstore = FAISS.from_documents(splits, embeddings)
    return vectorstore.as_retriever(search_kwargs={"k": 3})

uploaded_file = st.file_uploader("Sube tu PDF o Word", type=["pdf", "docx"])

if uploaded_file is not None:
    # Carga optimizada usando caché de Streamlit
    with st.spinner("Procesando el documento de manera óptima..."):
        retriever = procesar_documento(uploaded_file.getvalue(), uploaded_file.name)

    # Configurar Google Generative AI (Ideal para OCI y compatible con roles estándar)
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=os.environ["GEMINI_API_KEY"],
        temperature=0.3
    )

    # Función auxiliar para unir los fragmentos de texto recuperados
    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    # Prompt del sistema estructurado de forma estándar
    prompt = ChatPromptTemplate.from_messages([
        ("system", 
         """Eres un asistente experto. Usa los siguientes fragmentos de contexto recuperados del documento 
         para responder la pregunta del usuario. Si no sabes la respuesta o no está en el texto, di amablemente que no encuentras esa información.
         No inventes datos.\n\n
         
         Contexto:\n{context}"),
        MessagesPlaceholder(variable_name="chat_history"""),
        ("human", "{input}")
    ])

    # Construcción limpia de la cadena LCEL
    rag_chain = (
        {
            "context": (lambda x: x["input"]) | retriever | format_docs, 
            "input": lambda x: x["input"],
            "chat_history": lambda x: x["chat_history"]
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    # --- INTERFAZ VISUAL DEL CHAT ---
    # Renderizar el historial acumulado en pantalla
    for message in st.session_state.chat_history:
        if isinstance(message, HumanMessage):
            with st.chat_message("user"):
                st.write(message.content)
        elif isinstance(message, AIMessage):
            with st.chat_message("assistant"):
                st.write(message.content)

    # Capturar la nueva interacción del usuario
    if user_query := st.chat_input("¿Qué deseas preguntar sobre el documento?"):
        with st.chat_message("user"):
            st.write(user_query)
        
        with st.spinner("Pensando..."):
            try:
                # Invocación estructurada pasando el diccionario con las llaves que espera la cadena
                response_text = rag_chain.invoke({
                    "input": user_query,
                    "chat_history": st.session_state.chat_history
                })
            except Exception as e:
                st.error(f"Error al procesar la cadena: {e}")
                response_text = "Lo siento, ocurrió un error interno al procesar tu consulta."
        
        with st.chat_message("assistant"):
            st.write(response_text)
            
        # Guardar la interacción en el estado de la sesión
        st.session_state.chat_history.extend([
            HumanMessage(content=user_query),
            AIMessage(content=response_text)
        ])
else:
    st.info("Por favor, sube un archivo PDF o Word para comenzar a chatear con el agente.")