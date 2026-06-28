from pathlib import Path

file_path = Path("_agent/references/raw/S04E04.md")

lines = file_path.read_text(encoding="utf-8").splitlines()

cleaned_lines = []

for line in lines:
    if not line.startswith("*") and line != '':
        cleaned_lines.append(line)

cleaned_text = "\n\n".join(cleaned_lines)

file_path.write_text(cleaned_text, encoding="utf-8")

print(f"Cleaned {len(lines)} lines down to {len(cleaned_lines)} lines.")