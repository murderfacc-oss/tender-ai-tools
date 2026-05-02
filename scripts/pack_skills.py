"""
Упаковывает скиллы в zip-архивы для загрузки в Cowork.

Использование:
    python scripts/pack_skills.py              # все скиллы
    python scripts/pack_skills.py zhaloba-fas  # конкретный скилл

Zip кладётся рядом со скиллом: project/skills/<имя>-v<версия>.zip
Версия берётся из первой строки ## vX.X в CHANGELOG.md.
"""

import re
import sys
import zipfile
from pathlib import Path

SKILLS_DIR = Path(__file__).parent.parent / "project" / "skills"


def get_version(skill_dir: Path) -> str:
    changelog = skill_dir / "CHANGELOG.md"
    if not changelog.exists():
        return "v0"
    text = changelog.read_text(encoding="utf-8")
    m = re.search(r"##\s+(v[\d.]+)", text)
    return m.group(1) if m else "v0"


def pack_skill(skill_dir: Path) -> Path:
    version = get_version(skill_dir)
    zip_path = SKILLS_DIR / f"{skill_dir.name}-{version}.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in sorted(skill_dir.rglob("*")):
            if file.is_file():
                arcname = file.relative_to(skill_dir)
                zf.write(file, arcname)

    size_kb = zip_path.stat().st_size // 1024
    print(f"  {zip_path.name}  ({size_kb} KB, {len(zf.namelist())} файлов)")
    return zip_path


def main():
    if not SKILLS_DIR.exists():
        print(f"ERROR: папка скиллов не найдена: {SKILLS_DIR}")
        sys.exit(1)

    # Определяем что паковать
    if len(sys.argv) > 1:
        names = sys.argv[1:]
        skill_dirs = [SKILLS_DIR / name for name in names]
        missing = [d for d in skill_dirs if not d.is_dir()]
        if missing:
            print(f"ERROR: скиллы не найдены: {', '.join(str(m) for m in missing)}")
            sys.exit(1)
    else:
        skill_dirs = [d for d in sorted(SKILLS_DIR.iterdir())
                      if d.is_dir() and (d / "SKILL.md").exists()]

    print(f"Паков скиллов: {len(skill_dirs)}\n")
    for skill_dir in skill_dirs:
        pack_skill(skill_dir)

    print("\nГотово. Загружай zip-файлы в Cowork.")


if __name__ == "__main__":
    main()
