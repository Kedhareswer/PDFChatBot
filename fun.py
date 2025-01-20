import streamlit as st
import torch
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
from langchain.chains.question_answering import load_qa_chain
from langchain.llms import HuggingFaceHub
from transformers import pipeline
import tempfile

class PDFChatbot:
    def __init__(self):
        # Initialize embeddings
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        # Initialize the QA model
        self.qa_model = pipeline(
            "question-answering",
            model="deepset/roberta-base-squad2"
        )
        self.vector_store = None
        self.chain = None

    def process_pdf(self, pdf_file):
        """Process the uploaded PDF file"""
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(pdf_file.getvalue())
            tmp_path = tmp_file.name

        # Load PDF
        loader = PyPDFLoader(tmp_path)
        pages = loader.load_and_split()

        # Split text into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        texts = text_splitter.split_documents(pages)

        # Create vector store
        self.vector_store = FAISS.from_documents(texts, self.embeddings)

    def answer_question(self, question: str, k: int = 4) -> str:
        """Answer a question based on the PDF content"""
        if self.vector_store is None:
            return "Please upload a PDF first."

        # Get relevant documents
        relevant_docs = self.vector_store.similarity_search(question, k=k)
        
        # Combine relevant texts
        combined_text = " ".join([doc.page_content for doc in relevant_docs])
        
        # Get answer using the QA model
        answer = self.qa_model(
            question=question,
            context=combined_text
        )
        
        return answer['answer']
# Add these methods to the PDFChatbot class

    def generate_summary(self, text_length: int = 150) -> str:
        """Generate a summary of the PDF content"""
        summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
        
        # Get all text from vector store
        all_docs = self.vector_store.similarity_search("", k=999)
        full_text = " ".join([doc.page_content for doc in all_docs])
        
        return summarizer(full_text, max_length=text_length, min_length=30)[0]['summary_text']

    def extract_keywords(self, num_keywords: int = 10) -> list:
        """Extract key terms from the PDF"""
        from keybert import KeyBERT
        
        kw_model = KeyBERT()
        all_docs = self.vector_store.similarity_search("", k=999)
        full_text = " ".join([doc.page_content for doc in all_docs])
        
        keywords = kw_model.extract_keywords(full_text, top_n=num_keywords)
        return [kw[0] for kw in keywords]

    def get_confidence_score(self, question: str, answer: str) -> float:
        """Calculate confidence score for the answer"""
        from scipy.special import softmax
        
        relevant_docs = self.vector_store.similarity_search(question, k=1)
        context = relevant_docs[0].page_content
        
        # Use model's confidence score
        result = self.qa_model(question=question, context=context)
        return result['score']

def main():
    st.title("📚 Advanced PDF Chatbot")
    
    # Sidebar for additional features
    with st.sidebar:
        st.header("Features")
        show_summary = st.checkbox("Show Document Summary")
        show_keywords = st.checkbox("Show Keywords")
        show_confidence = st.checkbox("Show Confidence Scores")

    # Main content
    pdf_file = st.file_uploader("Upload your PDF", type='pdf')
    
    if pdf_file:
        with st.spinner("Processing PDF..."):
            st.session_state.chatbot.process_pdf(pdf_file)
        st.success("PDF processed successfully!")
        
        # Show additional features based on sidebar selection
        if show_summary:
            with st.expander("Document Summary"):
                summary = st.session_state.chatbot.generate_summary()
                st.write(summary)
                
        if show_keywords:
            with st.expander("Key Terms"):
                keywords = st.session_state.chatbot.extract_keywords()
                st.write(", ".join(keywords))
        
        # Chat interface
        st.subheader("Ask Questions")
        question = st.text_input("Enter your question:")
        
        if question:
            with st.spinner("Thinking..."):
                answer = st.session_state.chatbot.answer_question(question)
                
                if show_confidence:
                    confidence = st.session_state.chatbot.get_confidence_score(question, answer)
                    st.progress(confidence)
                    st.write(f"Confidence: {confidence:.2%}")
                
                st.write("Answer:", answer)