import os
from PyPDF2 import PdfReader
import re

curriculum_dir = os.path.join("static", "curiculum")
output_file = "curriculum_data.txt"

def extract_text():
    all_text = []
    
    # Iterate through all pdf files in the static/curiculum directory
    for filename in os.listdir(curriculum_dir):
        if filename.lower().endswith(".pdf"):
            filepath = os.path.join(curriculum_dir, filename)
            print(f"Extracting text from: {filename}")
            
            try:
                reader = PdfReader(filepath)
                file_text = []
                for idx, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if text:
                        file_text.append(text)
                
                # Join page text and prefix with document name for context
                full_doc_text = f"--- ข้อมูลจากเอกสาร {filename} ---\n" + "\n".join(file_text)
                all_text.append(full_doc_text)
            except Exception as e:
                print(f"Error reading {filename}: {e}")
                
    # Process and clean the text slightly before saving
    combined_text = "\n\n".join(all_text)
    
    # Save the huge text block
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(combined_text)
        
    print(f"Successfully extracted text to {output_file}")
    print(f"Total characters: {len(combined_text)}")

if __name__ == "__main__":
    extract_text()
