import argparse
import json
import re
from pathlib import Path

import fitz


SECTION_RE = re.compile(r"^Section\s+((?:2|3)\.\d+):\s+(.+)$", re.IGNORECASE)
REQ_RE = re.compile(r"^((?:2|3)\.\d+\.\d+(?:\.\d+)?)\s+(.+)$")
REF_RE = re.compile(r"^\[Ref.*\]$|^\[Reference:.*\]$", re.IGNORECASE)
ANNEX_RE = re.compile(r"^ANNEXURE", re.IGNORECASE)


def clean_page_text(text: str) -> list[str]:
    lines = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if "ITSAR No:" in line and "Page" in line:
            continue
        if line in {"Chapter 2: Common Security Requirements", "Chapter 3: Specific Security Requirements"}:
            continue
        lines.append(line)
    return lines


def slug_keywords(title: str) -> list[str]:
    title = title.replace("–", " ").replace("-", " ")
    parts = re.split(r"[,/()]", title)
    keywords = []
    for part in parts:
        part = part.strip()
        if len(part) >= 4:
            keywords.append(part)
    acronyms = re.findall(r"\b[A-Z]{2,}\b", title)
    keywords.extend(acronyms)
    seen = set()
    result = []
    for kw in keywords:
        lower = kw.lower()
        if lower not in seen:
            seen.add(lower)
            result.append(kw)
    return result[:5]


def extract_sub_requirements(body_lines: list[str], req_id: str) -> tuple[str, list[dict]]:
    text = "\n".join(body_lines).strip()
    sub_requirements = []

    clause_matches = list(re.finditer(r"(?m)(^|(?<=\n))([a-z])\)\s+", text))
    if not clause_matches:
        return text, sub_requirements

    intro = text[: clause_matches[0].start()].strip()
    for idx, match in enumerate(clause_matches):
        label = match.group(2)
        start = match.end()
        end = clause_matches[idx + 1].start() if idx + 1 < len(clause_matches) else len(text)
        clause_text = text[start:end].strip()
        if clause_text:
            sub_requirements.append(
                {
                    "id": f"{req_id}.{label}",
                    "text": clause_text,
                    "obligation": "SHALL",
                }
            )
    return intro or text, sub_requirements


def parse_pdf(pdf_path: Path) -> dict:
    doc = fitz.open(pdf_path)
    sections = []
    current_section = None
    current_requirement = None
    current_body_lines = []

    def flush_requirement():
        nonlocal current_requirement, current_body_lines, current_section
        if not current_requirement or not current_section:
            return
        body = [line for line in current_body_lines if line != "Requirement:"]
        refs = [line for line in body if REF_RE.match(line)]
        body = [line for line in body if not REF_RE.match(line)]
        text, sub_requirements = extract_sub_requirements(body, current_requirement["id"])
        current_requirement["text"] = re.sub(r"\s+\n", "\n", text).strip()
        current_requirement["keywords"] = slug_keywords(current_requirement["title"])
        if refs:
            current_requirement["cross_references"] = refs
        if sub_requirements:
            current_requirement["sub_requirements"] = sub_requirements
        current_section["requirements"].append(current_requirement)
        current_requirement = None
        current_body_lines = []

    def flush_section():
        nonlocal current_section
        if current_section:
            sections.append(current_section)
            current_section = None

    for page_index in range(17, min(doc.page_count, 77)):
        lines = clean_page_text(doc.load_page(page_index).get_text())
        i = 0
        while i < len(lines):
            line = lines[i]

            if ANNEX_RE.match(line):
                flush_requirement()
                flush_section()
                return {"sections": sections}

            section_match = SECTION_RE.match(line)
            if section_match:
                flush_requirement()
                flush_section()
                current_section = {
                    "id": section_match.group(1),
                    "title": section_match.group(2).strip().title(),
                    "chapter": "CSR" if section_match.group(1).startswith("2.") else "SSR",
                    "requirements": [],
                }
                i += 1
                continue

            req_match = REQ_RE.match(line)
            if req_match and current_section:
                flush_requirement()
                current_requirement = {
                    "id": req_match.group(1),
                    "title": req_match.group(2).strip(),
                    "obligation": "SHALL",
                    "applicable_router_types": [
                        "conventional",
                        "sdn",
                        "cloud_native",
                        "virtual",
                        "cloud_managed",
                    ],
                    "required_capability_flags": [],
                    "evidence_type": "technical",
                    "is_prohibition": False,
                    "compliance_by_undertaking": False,
                }
                i += 1
                continue

            if current_requirement:
                current_body_lines.append(line)

            i += 1

    flush_requirement()
    flush_section()
    return {"sections": sections}


def merge_existing(existing: dict, parsed: dict) -> dict:
    existing_section_map = {section["id"]: section for section in existing.get("sections", [])}
    existing_req_map = {}
    for section in existing.get("sections", []):
        for req in section.get("requirements", []):
            existing_req_map[req["id"]] = req
            for sub in req.get("sub_requirements", []):
                existing_req_map[sub["id"]] = sub

    merged_sections = []
    for parsed_section in parsed["sections"]:
        existing_section = existing_section_map.get(parsed_section["id"], {})
        merged_section = {
            "id": parsed_section["id"],
            "title": existing_section.get("title", parsed_section["title"]),
            "chapter": existing_section.get("chapter", parsed_section["chapter"]),
            "requirements": [],
        }

        for parsed_req in parsed_section.get("requirements", []):
            existing_req = existing_req_map.get(parsed_req["id"], {})
            merged_req = dict(parsed_req)
            for key, value in existing_req.items():
                if key in {"sub_requirements"}:
                    continue
                if value not in (None, "", [], {}):
                    merged_req[key] = value

            parsed_subs = {sub["id"]: sub for sub in parsed_req.get("sub_requirements", [])}
            existing_subs = {
                sub["id"]: sub
                for sub in existing_req.get("sub_requirements", [])
            } if existing_req else {}

            all_sub_ids = list(dict.fromkeys(list(parsed_subs.keys()) + list(existing_subs.keys())))
            if all_sub_ids:
                merged_subs = []
                for sub_id in all_sub_ids:
                    base = dict(parsed_subs.get(sub_id, existing_subs.get(sub_id, {})))
                    existing_sub = existing_subs.get(sub_id, {})
                    for key, value in existing_sub.items():
                        if value not in (None, "", [], {}):
                            base[key] = value
                    merged_subs.append(base)
                merged_req["sub_requirements"] = merged_subs

            merged_section["requirements"].append(merged_req)

        merged_sections.append(merged_section)

    result = dict(existing)
    result["sections"] = merged_sections
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--existing", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    existing_path = Path(args.existing)
    output_path = Path(args.output)

    with open(existing_path, "r", encoding="utf-8") as f:
        existing = json.load(f)

    parsed = parse_pdf(pdf_path)
    merged = merge_existing(existing, parsed)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    total_reqs = 0
    for section in merged["sections"]:
        for req in section.get("requirements", []):
            total_reqs += 1 + len(req.get("sub_requirements", []))
    print(f"Sections: {len(merged['sections'])}")
    print(f"Requirement items: {total_reqs}")


if __name__ == "__main__":
    main()
