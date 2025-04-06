# app.py
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_cors import CORS
import pytesseract
from PIL import Image
from googletrans import Translator
import os
from werkzeug.utils import secure_filename
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
import json
from bson import json_util
import tempfile
from utils.pdf_processor import PDFProcessor
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app) # Enable CORS for all routes
app.secret_key = os.getenv('SECRET_KEY', 'fallback_secret_key_for_development')  # Required for sessions

# Configure MongoDB connection
mongo_uri = os.getenv('MONGO_URI')
client = MongoClient(mongo_uri)
db = client.lingalens_db  # Database name
users_collection = db.users  # Collection for users

# Configure upload folder
UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), 'lingalens_uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize translator
translator = Translator()

# Initialize PDF processor
# Set the path to Tesseract if needed, otherwise it will use the system's default
tesseract_path = os.getenv('TESSERACT_CMD')  # Change this to your Tesseract path
pdf_processor = PDFProcessor(tesseract_cmd=tesseract_path)

@app.route('/')
def index():
    return render_template('body.html')

@app.route('/converter')
def converter():
    return render_template('index.html')

@app.route('/signup', methods=['POST'])
def signup():
    try:
        data = request.json
        name = data.get('name')
        email = data.get('email')
        phone = data.get('phone')
        password = data.get('password')
        
        # Check if email already exists
        if users_collection.find_one({"email": email}):
            return jsonify({"success": False, "message": "Email already registered!"}), 400
        
        # Create new user with hashed password
        new_user = {
            "name": name,
            "email": email,
            "phone": phone,
            "password": generate_password_hash(password)
        }
        
        # Insert the user into the database
        result = users_collection.insert_one(new_user)
        
        return jsonify({"success": True, "message": "Registration successful!"})
    
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/signin', methods=['POST'])
def signin():
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        
        # Find the user
        user = users_collection.find_one({"email": email})
        
        if user and check_password_hash(user['password'], password):
            # Convert ObjectId to string for JSON serialization
            user_data = json.loads(json_util.dumps(user))
            
            # Store user info in session
            session['user'] = {
                'id': str(user_data['_id']),
                'name': user_data['name'],
                'email': user_data['email']
            }
            
            return jsonify({
                "success": True, 
                "message": "Login successful!",
                "user": {
                    "name": user_data['name'],
                    "email": user_data['email']
                }
            })
        else:
            return jsonify({"success": False, "message": "Invalid email or password!"}), 401
    
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/logout', methods=['POST'])
def logout():
    # Clear the session
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully"})

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/process_image', methods=['POST'])
def process_image():
    try:
        target_language = request.form.get('language', 'en')
        original_text = ""

        # Check if the request contains a file or text
        if 'image' in request.files:
            file = request.files['image']
            
            if file and allowed_file(file.filename):
                # Use a secure temp file
                with tempfile.NamedTemporaryFile(delete=False, dir=app.config['UPLOAD_FOLDER']) as tmp_file:
                    file.save(tmp_file.name)
                    file_path = tmp_file.name
                
                try:
                    # Check if it's a PDF file
                    if file.filename.lower().endswith('.pdf'):
                        # Process PDF file
                        original_text = pdf_processor.extract_text_from_pdf(file_path)
                    else:
                        # Process image file
                        img = Image.open(file_path)
                        if tesseract_path:
                            pytesseract.pytesseract.tesseract_cmd = tesseract_path
                        original_text = pytesseract.image_to_string(img)
                finally:
                    # Always clean up the temp file
                    if os.path.exists(file_path):
                        os.remove(file_path)
            else:
                return jsonify({"error": "Invalid file type"}), 400

        elif 'text' in request.form:
            original_text = request.form.get('text', '')
        else:
            return jsonify({"error": "No image or text provided"}), 400
        
        # Translate the text if we have content
        if original_text.strip():
            try:
                translation = translator.translate(original_text, dest=target_language)
                translated_text = translation.text
            except Exception as trans_error:
                print(f"Translation error: {trans_error}")
                translated_text = "Translation service unavailable"
            
            return jsonify({
                "original_text": original_text,
                "translated_text": translated_text
            })
        else:
            return jsonify({"error": "No text could be extracted or provided"}), 400
        
    except Exception as e:
        print(f"Error in process_image: {e}")
        return jsonify({"error": "An error occurred while processing your request"}), 500

if __name__ == '__main__':
    # For production, use a proper WSGI server instead of the built-in Flask server
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)