from flask import Flask, render_template, request, jsonify
import os
from PyPDF2 import PdfReader
import cohere
import logging

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Set your Cohere API key
cohere_client = cohere.Client(api_key="lgPMgk5dOX1OJlISAS8P0cnMoGz9WP0z62rimsZ1")

# Function to read text from a PDF file and chunk it
def read_pdf(file_path, chunk_size=1000):
    with open(file_path, 'rb') as pdf_file:
        pdf_reader = PdfReader(pdf_file)
        chunks = []
        text = ""

        for page in pdf_reader.pages:
            text += page.extract_text()
            while len(text) > chunk_size:
                chunks.append(text[:chunk_size])
                text = text[chunk_size:]

        if text:  # Add any remaining text
            chunks.append(text)
        
        return chunks

# Read and process PDF files into chunks
pdf_texts = {}
pdf_folder = os.path.join(app.root_path, 'pdf_files')
for file in os.listdir(pdf_folder):
    if file.endswith('.pdf'):
        file_path = os.path.join(pdf_folder, file)
        pdf_texts[file] = read_pdf(file_path)

# Function to find relevant chunks based on the user's question
def find_relevant_chunks(question, pdf_texts):
    relevant_chunks = []
    for file, chunks in pdf_texts.items():
        for chunk in chunks:
            if any(word in chunk.lower() for word in question.lower().split()):
                relevant_chunks.append(chunk)
                if len(" ".join(relevant_chunks)) > 3000:  # Ensure it doesn't exceed token limit
                    return relevant_chunks
    return relevant_chunks

# Function to generate AI response using relevant chunks
def generate_ai_response(question):
    relevant_chunks = find_relevant_chunks(question, pdf_texts)
    combined_context = " ".join(relevant_chunks)
    
    prompt = f"Based on the following context, answer this question: {question}\n\nContext: {combined_context}"
    
    try:
        response = cohere_client.generate(
            model='command',
            prompt=prompt,
            max_tokens=150,
            temperature=0.7,
            k=0,
            stop_sequences=[],
            return_likelihoods='NONE'
        )
        return response.generations[0].text.strip()
    except Exception as e:
        app.logger.error(f"Error in generate_ai_response: {str(e)}")
        raise

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chatbot', methods=['POST'])
def chatbot_response():
    try:
        data = request.json
        user_question = data['question']
        app.logger.info(f"Received question: {user_question}")
        
        response = generate_ai_response(user_question)
        app.logger.info(f"Generated response: {response}")
        
        return jsonify({'answer': response})
    except Exception as e:
        app.logger.error(f"Error in chatbot_response: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
