import json
from pathlib import Path

transcript_path = r"C:\Users\yugan.dhar\.gemini\antigravity\brain\e1241215-9e45-40c4-8b90-f79d586f9b16\.system_generated\logs\transcript_full.jsonl"
out_path = r"scripts\ocr_text.txt"

found = False
with open(transcript_path, 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        try:
            data = json.loads(line)
            content = data.get('content', '')
            if '==Start of PDF==' in content:
                print(f"Found at line {i}, type {data.get('type')}, length {len(content)}")
                with open(out_path, 'w', encoding='utf-8') as out:
                    out.write(content)
                found = True
        except Exception as e:
            print(f"Error on line {i}: {e}")

if not found:
    print("Could not find ==Start of PDF== in any message")
