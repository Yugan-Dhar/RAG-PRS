import json

transcript_path = r"C:\Users\yugan.dhar\.gemini\antigravity\brain\e1241215-9e45-40c4-8b90-f79d586f9b16\.system_generated\logs\transcript_full.jsonl"

with open(transcript_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx in [1882, 1279]:
    data = json.loads(lines[idx])
    content = data.get('content', '')
    if '==Start of OCR' in content:
        with open('scripts/ocr_text.txt', 'w', encoding='utf-8') as out:
            out.write(content)
        print(f"Successfully wrote OCR text from line {idx}")
        break
