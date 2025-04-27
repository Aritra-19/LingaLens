#pdftry.py
import os
import pytesseract
import cv2
import numpy as np
import fitz  # PyMuPDF
from pdf2image import convert_from_path
from transformers import MarianMTModel, MarianTokenizer, M2M100ForConditionalGeneration, M2M100Tokenizer
import torch
import warnings

warnings.filterwarnings("ignore")

class PDFTranslationSystem:
    def __init__(self, target_language="hi", tesseract_cmd=None):
        """
        Initialize the PDF translation system
        
        Args:
            target_language (str): Target language code for translation
                Supported languages: 'hi' (Hindi), 'bn' (Bengali), 'or' (Odia), 
                'fr', 'es', 'de', 'it', 'ru', 'zh', 'ar', etc.
            tesseract_cmd (str): Path to Tesseract executable (optional)
        """
        print("Initializing PDF Translation System...")
        
        # Set Tesseract path if provided
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        
        # Ensure Tesseract is available
        try:
            pytesseract.get_tesseract_version()
            print("✓ Tesseract OCR detected")
        except:
            print("⚠️ Tesseract OCR not found. Please install it: https://github.com/tesseract-ocr/tesseract")
        
        # Set up translation model
        self.target_language = target_language
        
        # Marian models for European languages
        self.marian_models = {
            'fr': ('Helsinki-NLP/opus-mt-en-fr', 'Helsinki-NLP/opus-mt-fr-en'),
            'es': ('Helsinki-NLP/opus-mt-en-es', 'Helsinki-NLP/opus-mt-es-en'),
            'de': ('Helsinki-NLP/opus-mt-en-de', 'Helsinki-NLP/opus-mt-de-en'),
            'it': ('Helsinki-NLP/opus-mt-en-it', 'Helsinki-NLP/opus-mt-it-en'),
            'ru': ('Helsinki-NLP/opus-mt-en-ru', 'Helsinki-NLP/opus-mt-ru-en'),
            'zh': ('Helsinki-NLP/opus-mt-en-zh', 'Helsinki-NLP/opus-mt-zh-en'),
            'ar': ('Helsinki-NLP/opus-mt-en-ar', 'Helsinki-NLP/opus-mt-ar-en'),
        }
        
        # Indian languages - using M2M100 model which has better support for Indic languages
        self.indic_languages = ['hi', 'bn', 'or']
        
        # Load appropriate translation model
        if target_language in self.marian_models:
            print(f"Loading Marian translation model for {target_language}...")
            model_name = self.marian_models[target_language][0]
            self.translator_tokenizer = MarianTokenizer.from_pretrained(model_name)
            self.translator_model = MarianMTModel.from_pretrained(model_name)
            self.model_type = "marian"
            print(f"✓ Translation model loaded")
        
        elif target_language in self.indic_languages:
            print(f"Loading M2M100 translation model for {target_language}...")
            self.translator_tokenizer = M2M100Tokenizer.from_pretrained("facebook/m2m100_418M")
            self.translator_model = M2M100ForConditionalGeneration.from_pretrained("facebook/m2m100_418M")
            self.model_type = "m2m100"
            print(f"✓ Translation model loaded")
        
        else:
            print(f"⚠️ Unsupported target language: {target_language}")
            print(f"Supported languages: {list(self.marian_models.keys()) + self.indic_languages}")
            raise ValueError(f"Unsupported language: {target_language}")
    
    def preprocess_image(self, img):
        """
        Preprocess image to improve OCR results
        
        Args:
            img: Image as numpy array
            
        Returns:
            numpy array: Processed image
        """
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply thresholding
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Optional: noise removal
        kernel = np.ones((1, 1), np.uint8)
        img = cv2.dilate(thresh, kernel, iterations=1)
        img = cv2.erode(img, kernel, iterations=1)
        
        return img
    
    def extract_text_from_image(self, img):
        """
        Extract text from an image using OCR
        
        Args:
            img: Image as numpy array
            
        Returns:
            str: Extracted text
        """
        # Preprocess the image
        processed_img = self.preprocess_image(img)
        
        # Perform OCR
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(processed_img, config=custom_config)
        
        return text
    
    def extract_text_from_pdf(self, pdf_path):
        """
        Extract text from a PDF file, trying direct extraction first,
        then falling back to OCR if needed
        
        Args:
            pdf_path (str): Path to the PDF file
            
        Returns:
            str: Extracted text
        """
        print(f"Processing PDF: {pdf_path}")
        
        # Try direct text extraction first (for searchable PDFs)
        doc = fitz.open(pdf_path)
        text = ""
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text += page.get_text()
        
        # If direct extraction yields little text, try OCR
        if len(text.strip()) < 100:
            print("Direct extraction yielded limited text. Attempting OCR...")
            pages = convert_from_path(pdf_path)
            text = ""
            
            for i, page in enumerate(pages):
                print(f"OCR processing page {i+1}/{len(pages)}")
                
                # Convert PIL Image to numpy array for OpenCV
                img = cv2.cvtColor(np.array(page), cv2.COLOR_RGB2BGR)
                
                # Extract text from the page image
                page_text = self.extract_text_from_image(img)
                text += page_text + "\n\n"
        else:
            print(f"Extracted {len(text)} characters using direct extraction")
        
        return text
    
    def translate_text(self, text, source_lang="en"):
        """
        Translate text from source language to target language
        
        Args:
            text (str): Text to translate
            source_lang (str): Source language code (default: English)
            
        Returns:
            str: Translated text
        """
        print(f"Translating text ({len(text)} characters) to {self.target_language}...")
        
        # Handle empty text
        if not text or text.isspace():
            return ""
        
        # Process in chunks to handle large texts
        max_length = 512
        chunks = [text[i:i+max_length] for i in range(0, len(text), max_length)]
        translated_chunks = []
        
        for chunk in chunks:
            if self.model_type == "marian":
                # Tokenize for Marian models
                batch = self.translator_tokenizer([chunk], return_tensors="pt", padding=True, truncation=True, max_length=max_length)
                
                # Generate translation
                with torch.no_grad():
                    translated = self.translator_model.generate(**batch)
                
                # Decode
                translated_text = self.translator_tokenizer.batch_decode(translated, skip_special_tokens=True)[0]
            
            elif self.model_type == "m2m100":
                # For M2M100 model (used for Indic languages)
                self.translator_tokenizer.src_lang = source_lang
                encoded = self.translator_tokenizer(chunk, return_tensors="pt")
                
                with torch.no_grad():
                    generated_tokens = self.translator_model.generate(
                        **encoded,
                        forced_bos_token_id=self.translator_tokenizer.get_lang_id(self.target_language)
                    )
                
                translated_text = self.translator_tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)[0]
            
            translated_chunks.append(translated_text)
        
        return " ".join(translated_chunks)
    
    def translate_pdf(self, pdf_path, output_dir=None):
        """
        Process a PDF file to extract and translate text
        
        Args:
            pdf_path (str): Path to the PDF file
            output_dir (str): Directory to save results (default: "./results")
            
        Returns:
            dict: Result containing original and translated text
        """
        if not os.path.exists(pdf_path):
            raise ValueError(f"PDF file does not exist: {pdf_path}")
        
        if output_dir is None:
            output_dir = "./results"
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Extract text from PDF
        extracted_text = self.extract_text_from_pdf(pdf_path)
        
        # Translate the extracted text
        translated_text = self.translate_text(extracted_text)
        
        # Save results to output directory
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        
        # Save original text
        original_path = os.path.join(output_dir, f"{base_name}_original.txt")
        with open(original_path, 'w', encoding='utf-8') as f:
            f.write(extracted_text)
        
        # Save translated text
        translated_path = os.path.join(output_dir, f"{base_name}_translated_{self.target_language}.txt")
        with open(translated_path, 'w', encoding='utf-8') as f:
            f.write(translated_text)
        
        print(f"PDF processed and translated to {self.target_language}.")
        print(f"Original text saved to: {original_path}")
        print(f"Translated text saved to: {translated_path}")
        
        return {
            "original_text": extracted_text,
            "translated_text": translated_text,
            "original_path": original_path,
            "translated_path": translated_path
        }


def main():
    """
    Main function to demonstrate PDF translation
    """
    # Set the path to Tesseract if needed
    tesseract_path = r"C:/Program Files/Tesseract-OCR/tesseract.exe"  # Change this to your Tesseract path or set to None
    
    # Initialize the translation system with Bengali as the target language
    translator = PDFTranslationSystem(target_language="bn", tesseract_cmd=tesseract_path)
    
    # Path to the PDF file
    pdf_file = "pdf1.pdf"  # Change this to your PDF file
    
    # Translate the PDF
    result = translator.translate_pdf(pdf_file)
    
    # Print a sample of the results
    print("\nSample of original text:")
    print(result["original_text"][:200] + "..." if len(result["original_text"]) > 200 else result["original_text"])
    
    print("\nSample of translated text (Bengali):")
    print(result["translated_text"][:200] + "..." if len(result["translated_text"]) > 200 else result["translated_text"])


if __name__ == "__main__":
    main()