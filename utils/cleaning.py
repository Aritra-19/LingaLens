# utils/cleaning.py
import cv2
import pytesseract
import re
import numpy as np
import os
from PIL import Image
from langdetect import detect

# Try to import IndicNormalizer, but handle potential import errors
try:
    from indicnlp.normalize import IndicNormalizerFactory
    INDIC_NORMALIZE_AVAILABLE = True
except ImportError:
    print("Warning: indicnlp package not found. Indic language normalization will be unavailable.")
    INDIC_NORMALIZE_AVAILABLE = False

class ImageCleaningSystem:
    def __init__(self, tesseract_cmd=None):
        """
        Initialize the Image Cleaning System for enhanced OCR
        
        Args:
            tesseract_cmd (str): Path to Tesseract executable (optional)
        """
        print("Initializing Image Cleaning System...")
        
        # Set Tesseract path if provided
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        
        # Ensure Tesseract is available
        try:
            pytesseract.get_tesseract_version()
            print("✓ Tesseract OCR detected")
        except:
            print("⚠️ Tesseract OCR not found. Please install it: https://github.com/tesseract-ocr/tesseract")
        
        # Initialize language normalizers if available
        self.normalizers = {}
        if INDIC_NORMALIZE_AVAILABLE:
            normalizer_factory = IndicNormalizerFactory()
            for lang in ['hi', 'bn', 'or']:  # Hindi, Bengali, Odia
                try:
                    self.normalizers[lang] = normalizer_factory.get_normalizer(lang)
                except Exception as e:
                    print(f"Warning: Could not initialize normalizer for {lang}: {e}")
        
        # Default OCR configuration
        self.custom_config = r'--oem 3 --psm 6'
        
        # Language mapping for OCR
        self.lang_map = {
            'en': 'eng',  # English
            'hi': 'hin',  # Hindi
            'bn': 'ben',  # Bengali
            'or': 'ori',  # Odia
            # Add more languages as needed
        }
    
    def pre_process_image(self, image_path):
        """
        Preprocess image to improve OCR results
        
        Args:
            image_path: Path to the image file
            
        Returns:
            numpy array: Processed image
        """
        # Read the image
        if isinstance(image_path, str):
            image = cv2.imread(image_path)
        else:
            # If image_path is already a numpy array
            image = image_path
            
        if image is None:
            raise ValueError("Could not read image")
        
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply adaptive thresholding
        adaptive_thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 31, 11
        )
        
        # Optional: Noise removal
        kernel = np.ones((1, 1), np.uint8)
        opening = cv2.morphologyEx(adaptive_thresh, cv2.MORPH_OPEN, kernel)
        
        # Apply bilateral filter to preserve edges
        smooth = cv2.bilateralFilter(opening, 9, 75, 75)
        
        return smooth
    
    def extract_text(self, image, language='eng'):
        """
        Extract text from a preprocessed image using OCR
        
        Args:
            image: Preprocessed image as numpy array
            language (str): Language for OCR (default: 'eng')
            
        Returns:
            str: Extracted text
        """
        # Perform OCR with the specified language
        custom_config = f'{self.custom_config}'
        text = pytesseract.image_to_string(image, lang=language, config=custom_config)
        
        return text
    
    def detect_language(self, text):
        """
        Detect the language of a text
        
        Args:
            text (str): Text to analyze
            
        Returns:
            str: Detected language code
        """
        try:
            if not text or len(text.strip()) < 10:
                return "unknown"
            
            lang = detect(text)
            
            # Map detected language to our supported languages
            lang_mapping = {
                'en': 'en',  # English
                'hi': 'hi',  # Hindi
                'bn': 'bn',  # Bengali
                'or': 'or',  # Odia
            }
            
            return lang_mapping.get(lang, lang)
        except:
            return "unknown"
    
    def clean_text(self, text, language='en'):
        """
        Clean and normalize extracted text
        
        Args:
            text (str): Text to clean
            language (str): Language code for normalization
            
        Returns:
            str: Cleaned text
        """
        # Skip cleaning if text is empty
        if not text or text.isspace():
            return text
        
        # Basic cleaning operations for all languages
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', text).strip()
        
        # Apply language-specific normalization if available
        if language in self.normalizers and INDIC_NORMALIZE_AVAILABLE:
            try:
                cleaned = self.normalizers[language].normalize(cleaned)
            except Exception as e:
                print(f"Error during normalization: {e}")
        
        return cleaned
    
    def process_image(self, image_path, language='eng'):
        """
        Process an image to extract and clean text
        
        Args:
            image_path (str): Path to the image file
            language (str): Language for OCR
            
        Returns:
            str: Extracted and cleaned text
        """
        print(f"Processing image with language: {language}")
        
        # Preprocess the image
        preprocessed = self.pre_process_image(image_path)
        
        # Extract text using OCR
        text = self.extract_text(preprocessed, language)
        
        # Auto-detect language if set to 'auto'
        if language == 'auto':
            detected_lang = self.detect_language(text)
            print(f"Detected language: {detected_lang}")
            
            # If we detected a different language than the default, re-extract
            if detected_lang != "unknown" and detected_lang != "en":
                ocr_lang = self.lang_map.get(detected_lang, language)
                text = self.extract_text(preprocessed, ocr_lang)
                language = detected_lang
        
        # Clean and normalize the text
        cleaned_text = self.clean_text(text, language)
        
        return cleaned_text

# Example usage
def main():
    """
    Main function to demonstrate image processing
    """
    # Set the path to Tesseract if needed
    tesseract_path = r"C:/Program Files/Tesseract-OCR/tesseract.exe"  # Change this to your Tesseract path
    
    # Initialize the image cleaning system
    cleaner = ImageCleaningSystem(tesseract_cmd=tesseract_path)
    
    # Path to the image file
    image_file = input("Enter image path: ")  
    
    # Process the image
    extracted_text = cleaner.process_image(image_file, language='hin')
    
    print("\nExtracted text:")
    print(extracted_text)

if __name__ == "__main__":
    main()