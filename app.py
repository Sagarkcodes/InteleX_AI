from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
import PyPDF2
import docx
import random
import re
import spacy

# Load the spacy model for name extraction
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Downloading spaCy model 'en_core_web_sm'...")
    from spacy.cli import download
    download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")


# Create the Flask application instance
app = Flask(__name__)

# Define the folder where we'll save uploaded files
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Check if the 'uploads' folder exists; if not, create it
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Global variables to store data across requests
extracted_resume_text = ""
dominant_trait = ""
user_name = "User"  # Default name
question_list = []

# ----------------------------------------------------
# Big 5 Trait Keyword Dictionary (Simplified Rule-Set)
# ----------------------------------------------------
BIG_FIVE_KEYWORDS = {
    'Openness': ['creative', 'innovative', 'research', 'explore', 'design', 'ideas', 'diverse', 'curious', 'theoretical'],
    'Conscientiousness': ['organized', 'managed', 'structured', 'deadline', 'efficient', 'detail-oriented', 'project', 'plan', 'responsible'],
    'Extraversion': ['communicate', 'team', 'client', 'present', 'lead', 'social', 'public', 'mentored', 'liaison'],
    'Agreeableness': ['cooperative', 'support', 'helpful', 'friendly', 'patient', 'harmony', 'assist', 'volunteer', 'community'],
    'Neuroticism': ['stress', 'pressure', 'challenging', 'cope', 'handle', 'anxiety', 'calm', 'adapt', 'improve']
}

# ----------------------------------------------------
# Our Personality Trait Question Library
# ----------------------------------------------------
QUESTION_LIBRARY = {
    'Extraversion': [
        "Describe a situation where you had to lead or motivate a team.",
        "How do you approach building rapport with new people, like clients or colleagues?",
        "Tell me about a time you had to present an idea to a group."
    ],
    'Openness': [
        "Tell me about a time you had to be creative to solve a problem.",
        "Describe a new skill or hobby you’ve recently explored.",
        "How do you handle situations where you have to think outside the box?"
    ],
    'Conscientiousness': [
        "How do you plan and manage your time to meet a tight deadline?",
        "Describe a process you've put in place to make your work more efficient.",
        "Tell me about a project where your attention to detail was crucial."
    ],
    'Agreeableness': [
        "Describe a time you had a disagreement with a team member and how you handled it.",
        "Tell me about a time you had to support a colleague through a difficult situation.",
        "How do you ensure harmony and cooperation within a team?"
    ],
    'Neuroticism': [
        "Describe a high-pressure situation you've faced and how you managed your emotions.",
        "Tell me about a time you received constructive criticism. How did you react?",
        "How do you handle unexpected setbacks or failures?"
    ]
}

# ----------------------------------------------------
# Helper function for text extraction
# ----------------------------------------------------
def extract_text_from_resume(filepath):
    """Extracts text from PDF or DOCX files."""
    text = ""
    if filepath.lower().endswith('.pdf'):
        try:
            with open(filepath, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages:
                    text += page.extract_text() if page.extract_text() else ''
        except Exception as e:
            text = f"Error reading PDF: {e}"
    elif filepath.lower().endswith('.docx'):
        try:
            document = docx.Document(filepath)
            for paragraph in document.paragraphs:
                text += paragraph.text + '\n'
        except Exception as e:
            text = f"Error reading DOCX: {e}"
    return text

# ----------------------------------------------------
# Function to extract name using simple heuristics
# ----------------------------------------------------
def extract_name(text):
    # Split text into lines to look for the first line, which often contains the name
    lines = text.strip().split('\n')
    if lines:
        first_line = lines[0].strip()
        # Heuristic 1: If the first line is short and has multiple capitalized words
        if len(first_line) < 50 and re.match(r'^[A-Z][a-z]+(\s[A-Z][a-z]+)+$', first_line):
            return first_line
        
        # Heuristic 2: Use spaCy as a fallback
        doc = nlp(text)
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                # Only return a name if it's not a common technical term
                if len(ent.text.split()) > 1 and ent.text not in ['Python', 'Learning', 'Analysis', 'Project', 'Manager']:
                    return ent.text
    return "Candidate" # A more professional default name

# ----------------------------------------------------
# Function to Score Personality from Text
# ----------------------------------------------------
def score_personality_from_resume(text):
    scores = {}
    clean_text = text.lower()
    for trait, keywords in BIG_FIVE_KEYWORDS.items():
        count = 0
        for keyword in keywords:
            count += clean_text.count(keyword)
        scores[trait] = count
    return scores

# ----------------------------------------------------
# Define the home page route
# ----------------------------------------------------
@app.route('/')
def index():
    return render_template('index.html')

# ----------------------------------------------------
# Define the upload route
# ----------------------------------------------------
@app.route('/upload', methods=['POST'])
def upload_file():
    global extracted_resume_text
    global dominant_trait
    global user_name
    global question_list
    
    if 'resume' not in request.files or request.files['resume'].filename == '':
        return 'No file selected', 400
    
    file = request.files['resume']
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(filepath)
    
    extracted_resume_text = extract_text_from_resume(filepath)
    
    # 1. Extract the name from the resume
    name = extract_name(extracted_resume_text)
    if name:
        user_name = name
    
    # 2. Score the personality and find the dominant trait
    scores = score_personality_from_resume(extracted_resume_text)
    if scores:
        dominant_trait = max(scores, key=scores.get)
    else:
        dominant_trait = 'Extraversion'
        
    # 3. Prepare the list of questions for the entire interview
    questions_for_interview = []
    # Always add the introduction question first
    questions_for_interview.append("Please introduce yourself and tell me a bit about your professional journey so far.")
    
    # Add one question for each trait, starting with the dominant one
    ordered_traits = [t for t in BIG_FIVE_KEYWORDS.keys() if t != dominant_trait]
    random.shuffle(ordered_traits)
    ordered_traits = [dominant_trait] + ordered_traits
    
    for trait in ordered_traits:
        questions_for_interview.append(random.choice(QUESTION_LIBRARY.get(trait, ["Tell me about your experience."])))

    question_list = questions_for_interview
    
    print(f"Resume analysis complete. User: {user_name}. Dominant trait: {dominant_trait}. Questions prepared.")
    
    return redirect(url_for('analysis_result'))

# ----------------------------------------------------
# Define the analysis result page
# ----------------------------------------------------
@app.route('/analysis')
def analysis_result():
    return render_template('analysis_result.html')

# ----------------------------------------------------
# Define the Ready for Interview page
# ----------------------------------------------------
@app.route('/ready_for_interview')
def ready_for_interview():
    return render_template('ready_for_interview.html')

# ----------------------------------------------------
# Define the Live Interview page
# ----------------------------------------------------
@app.route('/live_interview')
def live_interview():
    global user_name
    global question_list
    return render_template('live_interview.html', user_name=user_name, total_questions=len(question_list))

# --- API ENDPOINT to get the next question ---
@app.route('/get_question/<int:question_index>')
def get_question(question_index):
    global question_list
    if 0 <= question_index < len(question_list):
        question = question_list[question_index]
        return jsonify({'question_text': question})
    return jsonify({'question_text': 'End of assessment.'})

# ----------------------------------------------------
# This ensures our InteleX app runs when we execute this file
# ----------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True)