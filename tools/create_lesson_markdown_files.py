# Each course lesson is divided manually by human, during reading.
# Parts of the lessons are copied into the files created by this tool.

from pathlib import Path

# User-editable configuration.
LESSON_NUMBER = 14
PART_COUNT = 4
OUTPUT_DIR = Path("_agent/references/raw")
OUTPUT_DIR_EXERCISE = Path("_agent/references/exercises")


# Create empty markdown files for one lesson using the configured names.
def create_lesson_markdown_files(lesson_number: int, part_count: int, output_dir: Path, output_dir_exe: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    created_files: list[Path] = []

    for part_number in range(1, part_count + 1):
        file_path = output_dir / f"L{lesson_number}_Part{part_number}.md"
        if not file_path.exists():
            file_path.write_text("", encoding="utf-8")
            created_files.append(file_path)

    exercise_path = output_dir_exe / f"L{lesson_number}_exercise.md"
    if not exercise_path.exists():
        exercise_path.write_text("", encoding="utf-8")
        created_files.append(exercise_path)

    return created_files


# Run the tool with the constants defined above.
def main() -> None:
    created_files = create_lesson_markdown_files(LESSON_NUMBER, PART_COUNT, OUTPUT_DIR, OUTPUT_DIR_EXERCISE)

    if created_files:
        print("Created files:")
        for file_path in created_files:
            print(f"- {file_path}")
    else:
        print("No files were created because they already exist.")


if __name__ == "__main__":
    main()
