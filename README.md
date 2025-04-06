First Install dependencies by this code:
pip install flask flask-cors pytesseract pillow googletrans==4.0.0-rc1
Then for OCR install tesseract
URL-  https://github.com/UB-Mannheim/tesseract/wiki
After installing tesseract copy the path from our program files [Path is "C:\Program Files\Tesseract-OCR"]
Then search Edit Environment Variables and click environment variables
choose Path 'User variable for KIIT' and click edit option 
Then add the copid path by clicking new button
After that open cmd and check the tesseract version by 'tesseract --version' if it shows error then check the added path in system variables
That's all now go to code and run app.py
in comandline write 'python app.py'
It will run nicely
