import os
import glob
import json

log_dir = r"C:\Users\yugan.dhar\.gemini\antigravity\brain\e1241215-9e45-40c4-8b90-f79d586f9b16\.system_generated\logs"
out_path = r"scripts\ocr_text.txt"

matches = []
for file_path in glob.glob(os.path.join(log_dir, "**", "*.jsonl"), recursive=True):
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line)
                content = data.get('content', '')
                if '==Start of OCR' in content and '==Start of PDF==' in content:
                    # Ignore tool outputs by checking type
                    if data.get('type') in ['USER_INPUT', 'SYSTEM_MESSAGE']:
                        matches.append((data.get('step_index', 999999), content))
            except:
                pass

if matches:
    # Sort by step_index and take the earliest
    matches.sort(key=lambda x: x[0])
    best_content = matches[0][1]
    with open(out_path, 'w', encoding='utf-8') as out:
        out.write(best_content)
    print(f"Successfully extracted OCR text from step {matches[0][0]}")
else:
    print("Could not find true OCR text")
