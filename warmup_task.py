import os
import sys
import base64
import requests
import json
from openai import OpenAI

# ==========================================
# CONFIGURATION
# ==========================================

# 1. OCR CONFIGURATION
OCR_API_URL = "https://bei1zck1d4v0m956.aistudio-app.com/ocr"
ACCESS_TOKEN = "be1c79c680c334a4ef65f3ee9d8c24321a4123f0"

# 2. ERNIE CONFIGURATION (Via OpenAI SDK)
# We use the AI Studio compatible endpoint you found
client = OpenAI(
    api_key=ACCESS_TOKEN,
    base_url="https://aistudio.baidu.com/llm/lmapi/v3",
)

# 3. FILE CONFIGURATION
PDF_PATH = "my_document.pdf" 
OUTPUT_HTML = "index.html"

# ==========================================
# PART 1: CLOUD OCR
# ==========================================

def extract_text_via_api(pdf_path, api_url, token):
    print(f"☁️  Uploading {pdf_path} to PaddleOCR-VL...")

    try:
        with open(pdf_path, "rb") as file:
            file_bytes = file.read()
            file_data = base64.b64encode(file_bytes).decode("ascii")
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return None

    headers = {
        "Authorization": f"token {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "file": file_data,
        "fileType": 0, 
        "useDocOrientationClassify": False,
        "useTextlineOrientation": False
    }

    try:
        print("⏳ Sending request to OCR API...")
        response = requests.post(api_url, json=payload, headers=headers)
        
        if response.status_code != 200:
            print(f"❌ API Error {response.status_code}: {response.text}")
            return None
            
        result_json = response.json()
        
        print("✅ Analysis Complete. Parsing content...")
        
        extracted_text = ""
        
        # 1. Try VL Structure
        if "result" in result_json and "layoutParsingResults" in result_json["result"]:
            parsing_results = result_json["result"]["layoutParsingResults"]
            for page_idx, page in enumerate(parsing_results):
                extracted_text += f"\n<!-- Page {page_idx + 1} -->\n"
                res_list = page.get("prunedResult", {}).get("parsing_res_list", [])
                for block in res_list:
                    content = block.get("block_content", "")
                    extracted_text += content + "\n\n"
                    
        # 2. Fallback to Standard Structure
        elif "result" in result_json and "ocrResults" in result_json["result"]:
             print("⚠️ Note: Using standard OCR fallback parsing.")
             ocr_results = result_json["result"]["ocrResults"]
             for res in ocr_results:
                 pruned = res.get("prunedResult", "")
                 extracted_text += str(pruned) + "\n"
        else:
            print(f"❌ Unexpected JSON structure. Keys found: {list(result_json.keys())}")
            return None
            
        return extracted_text

    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return None

# ==========================================
# PART 2: MARKDOWN
# ==========================================

def convert_to_markdown_structure(raw_text):
    md_content = f"""
# Extracted Document Content
{raw_text}
    """
    return md_content

# ==========================================
# PART 3: ERNIE GEN (Via OpenAI SDK)
# ==========================================

def generate_webpage_with_ernie(markdown_content):
    print("🤖 Preparing content for ERNIE (via OpenAI SDK)...")
    
    # SAFETY: Truncate to 2000 chars
    content_snippet = markdown_content[:2000]
    
    # IMPROVED PROMPT FOR BETTER DESIGN
    prompt = f"""
    You are an expert UI/UX designer and developer participating in a high-stakes Hackathon.
    
    Task: Transform the following raw content (extracted from a PDF) into a STUNNING, modern single-page website.
    
    The goal is to impress judges. The website must NOT look like a simple text dump.
    
    Design Requirements:
    1. **Tech Stack:** Use Tailwind CSS (via CDN) for sophisticated styling.
    2. **Structure:**
       - **Hero Section:** A visually appealing header with a gradient background (e.g., Indigo to Purple), a large white title, and a subtitle.
       - **Content Grid:** Display the extracted content in a responsive grid of "Cards" with white backgrounds, soft shadows (shadow-lg), and hover effects (scale-105).
       - **Typography:** Use a beautiful sans-serif font from Google Fonts (e.g., 'Poppins' or 'Inter').
       - **Navbar & Footer:** Include a sticky navbar with a logo placeholder and a professional footer with copyright info.
    3. **Aesthetics:** - Use a professional color palette (e.g., Slate-900 for text, Indigo-600 for accents).
       - Add generous whitespace (padding/margin).
       - Use rounded corners (rounded-2xl) and subtle borders.
    4. **Icons:** Include the FontAwesome CDN and add relevant icons to section headers to make it visual.
    
    Output Rules:
    - Return ONLY the complete HTML file code.
    - Do NOT include markdown fences (```html).
    - Ensure valid HTML5 structure with all necessary CDNs in the <head>.
    
    Content to transform:
    {content_snippet}
    """

    try:
        print(f"🚀 Sending request to ERNIE...")
        
        # Using standard OpenAI format
        chat_completion = client.chat.completions.create(
            # We use ernie-3.5-8k for speed/reliability. 
            # You can try "ernie-4.0-8k-latest" or "ernie-5.0-thinking-preview" if you want.
            model="ernie-3.5-8k", 
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            stream=False, # Disable streaming for simpler file writing
            temperature=0.7
        )
        
        result = chat_completion.choices[0].message.content
        return result

    except Exception as e:
        print(f"❌ ERNIE Failed: {e}")
        return None

# ==========================================
# MAIN EXECUTION
# ==========================================

if __name__ == "__main__":
    if not os.path.exists(PDF_PATH):
        print(f"❌ Error: File '{PDF_PATH}' not found.")
        sys.exit(1)

    # 1. Extract
    raw_text = extract_text_via_api(PDF_PATH, OCR_API_URL, ACCESS_TOKEN)
    
    if raw_text and len(raw_text) > 0:
        print(f"📝 Extracted {len(raw_text)} characters of text.")
        
        # 2. Format
        md_content = convert_to_markdown_structure(raw_text)
        
        # 3. Generate
        html_code = generate_webpage_with_ernie(md_content)
        
        if html_code:
            # Cleanup markdown fences if ERNIE adds them
            html_code = html_code.replace("```html", "").replace("```", "")
            
            with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
                f.write(html_code)
            
            print(f"🎉 Success! Website generated: {OUTPUT_HTML}")
            print("Action: Open this file in your browser to check it.")
    else:
        print("❌ OCR failed to extract any text.")