import os
import glob
import json

log_dir = r"C:\Users\yugan.dhar\.gemini\antigravity\brain\e1241215-9e45-40c4-8b90-f79d586f9b16\.system_generated\logs"
out_path = r"scripts\ocr_text.txt"

found = False
for file_path in glob.glob(os.path.join(log_dir, "**", "*.jsonl"), recursive=True):
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if '==Start of OCR' in line:
                try:
                    data = json.loads(line)
                    content = data.get('content', '')
                    if '==Start of OCR' in content:
                        with open(out_path, 'w', encoding='utf-8') as out:
                            out.write(content)
                        print(f"Found in {file_path}")
                        found = True
                        break
                except:
                    pass
    if found:
        break

if not found:
    print("Could not find anywhere")
