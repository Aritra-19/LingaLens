# utils/pdf_processor.py
import os
import pytesseract
import cv2
import numpy as np
import fitz  # PyMuPDF
from pdf2image import convert_from_path
import tempfile

class PDFProcessor:
    def __init__(self, tesseract_cmd=None):
        """
        Initialize the PDF processor
        
        Args:
            tesseract_cmd (str): Path to Tesseract executable (optional)
        """
        # Set Tesseract path if provided
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    
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
        # Try direct text extraction first (for searchable PDFs)
        doc = fitz.open(pdf_path)
        text = ""
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text += page.get_text()
        
        # If direct extraction yields little text, try OCR
        if len(text.strip()) < 100:
            pages = convert_from_path(pdf_path)
            text = ""
            
            for i, page in enumerate(pages):
                # Convert PIL Image to numpy array for OpenCV
                img = cv2.cvtColor(np.array(page), cv2.COLOR_RGB2BGR)
                
                # Extract text from the page image
                page_text = self.extract_text_from_image(img)
                text += page_text + "\n\n"
        
        return text

