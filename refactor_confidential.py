import os
import re

DIR = r"c:\Users\r.hadjicharalambous\OneDrive - Grant Thornton Cyprus\Desktop\PascalExample"

def process_file(path, func):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    new_content = func(content)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)

def update_generic(text):
    text = text.replace("Pascal Education Group", "Alpha Education Group")
    text = text.replace("Pascal English School", "Alpha English School")
    text = text.replace("Pascal Primary School", "Alpha Primary School")
    text = text.replace("PES Nicosia", "AES Nicosia")
    text = text.replace("PPS Nicosia", "APS Nicosia")
    text = text.replace("PES Limassol", "AES Limassol")
    text = text.replace("PES Larnaca", "AES Larnaca")
    text = text.replace("pes_nicosia", "aes_nicosia")
    text = text.replace("pps_nicosia", "aps_nicosia")
    text = text.replace("pes_limassol", "aes_limassol")
    text = text.replace("pes_larnaca", "aes_larnaca")
    text = text.replace("Pascal ", "Alpha ")
    
    # Also fix app.js missing definitions for correct Cyprus schools if they don't match python
    
    return text

process_file(os.path.join(DIR, "api", "index.py"), update_generic)
process_file(os.path.join(DIR, "public", "index.html"), update_generic)
process_file(os.path.join(DIR, "public", "js", "app.js"), update_generic)

print("Removed confidential names.")
