from flask import Flask, render_template, request, jsonify
from PyPDF2 import PdfReader
from transformers import pipeline
from googlesearch import search
from newspaper import Article
import nltk
import threading

app = Flask(__name__)

# Download required NLTK data
nltk.download('punkt')

class PDFChatbot:
    def __init__(self):
        # Initialize models
        self.summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
        self.qa_model = pipeline("question-answering", model="deepset/roberta-base-squad2")
        self.pdf_text = ""
        
    def process_pdf(self, pdf_file):
        """Extract text from PDF"""
        reader = PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        self.pdf_text = text
        return text

    def get_summary(self):
        """Generate summary of the PDF content"""
        # Split text into chunks (BART has a max input length)
        max_chunk = 1024
        chunks = [self.pdf_text[i:i+max_chunk] for i in range(0, len(self.pdf_text), max_chunk)]
        
        summaries = []
        for chunk in chunks:
            summary = self.summarizer(chunk, max_length=130, min_length=30, do_sample=False)
            summaries.append(summary[0]['summary_text'])
        
        return " ".join(summaries)

    def search_google(self, query, num_results=3):
        """Search Google for relevant information"""
        search_results = []
        try:
            for url in search(query, num_results=num_results):
                try:
                    article = Article(url)
                    article.download()
                    article.parse()
                    search_results.append({
                        'title': article.title,
                        'text': article.text[:500],  # First 500 characters
                        'url': url
                    })
                except:
                    continue
        except:
            pass
        return search_results

    def answer_question(self, question):
        """Answer questions using both PDF content and Google search"""
        # Get answer from PDF content
        pdf_answer = self.qa_model(question=question, context=self.pdf_text[:512])
        
        # Get additional context from Google
        search_query = f"{question} {' '.join(self.pdf_text.split()[:50])}"  # Use first 50 words for context
        search_results = self.search_google(search_query)
        
        # Combine answers
        response = {
            'pdf_answer': pdf_answer['answer'],
            'confidence': round(pdf_answer['score'] * 100, 2),
            'web_results': search_results
        }
        
        return response

# Initialize chatbot
chatbot = PDFChatbot()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'})
    
    if file and file.filename.endswith('.pdf'):
        try:
            text = chatbot.process_pdf(file)
            summary = chatbot.get_summary()
            return jsonify({
                'success': True,
                'summary': summary,
                'text_length': len(text)
            })
        except Exception as e:
            return jsonify({'error': str(e)})
    
    return jsonify({'error': 'Invalid file type'})

@app.route('/ask', methods=['POST'])
def ask():
    data = request.json
    question = data.get('question')
    
    if not question:
        return jsonify({'error': 'No question provided'})
    
    try:
        response = chatbot.answer_question(question)
        return jsonify(response)
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)