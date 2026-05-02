"""
Собирает архив tender-ai-tools.zip для передачи партнёру.

Содержимое архива:
  skills/                          — zip-файлы всех скиллов
  mcp/                             — сервер MCP (без .env и тестовых данных)
  README.md                        — обзор проекта
  INSTALL_PROMPT.md                — основной путь: промт для Claude Code
  Установка Tender AI Tools.pptx   — fallback: ручная инструкция (11 слайдов)

Использование:
    python scripts/build_partner_archive.py
    python scripts/build_partner_archive.py --output partner.zip
"""

import argparse
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT    = Path(__file__).parent.parent
MCP_DIR = ROOT.parent / "sabytrade-mcp"

MCP_INCLUDE = {
    "server.py",
    "zakupki_scraper.py",
    "requirements.txt",
    ".env.example",
}


def build_skills(root: Path) -> list[Path]:
    """Запускает pack_skills.py и возвращает пути zip-файлов."""
    print("Собираю скиллы...")
    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "pack_skills.py")],
        capture_output=True,
        cwd=str(root),
    )
    skills_dir = root / "project" / "skills"
    return sorted(skills_dir.glob("*.zip"))


def build_guide(root: Path) -> Path:
    """Генерирует презентацию по установке (PowerPoint, fallback)."""
    guide_path = root / "Установка Tender AI Tools.pptx"
    print("Генерирую презентацию (fallback)...")
    subprocess.run(
        [sys.executable, str(root / "scripts" / "generate_install_pptx.py"),
         "--output", str(guide_path)],
        cwd=str(root),
        check=True,
    )
    return guide_path


def build_prompt(root: Path) -> Path:
    """Генерирует INSTALL_PROMPT.md — основной путь установки."""
    prompt_path = root / "INSTALL_PROMPT.md"
    print("Генерирую INSTALL_PROMPT.md...")
    subprocess.run(
        [sys.executable, str(root / "scripts" / "generate_install_prompt.py"),
         "--output", str(prompt_path)],
        cwd=str(root),
        check=True,
    )
    return prompt_path


def build_archive(output_path: Path, root: Path, mcp_dir: Path):
    skill_zips = build_skills(root)
    prompt_path = build_prompt(root)
    guide_path = build_guide(root)

    print(f"\nСобираю архив: {output_path.name}")

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # скиллы
        for zip_file in skill_zips:
            arcname = f"skills/{zip_file.name}"
            zf.write(zip_file, arcname)
            print(f"  + {arcname}")

        # MCP
        for fname in MCP_INCLUDE:
            src = mcp_dir / fname
            if src.exists():
                arcname = f"mcp/{fname}"
                zf.write(src, arcname)
                print(f"  + {arcname}")
            else:
                print(f"  ? пропущен (не найден): mcp/{fname}")

        # README
        readme = root / "README.md"
        if readme.exists():
            zf.write(readme, "README.md")
            print(f"  + README.md")

        # промт для Claude Code (основной путь)
        if prompt_path.exists():
            zf.write(prompt_path, prompt_path.name)
            print(f"  + {prompt_path.name}")

        # презентация (fallback)
        if guide_path.exists():
            zf.write(guide_path, guide_path.name)
            print(f"  + {guide_path.name}")

    size_kb = output_path.stat().st_size // 1024
    print(f"\nГотово: {output_path}  ({size_kb} KB, {len(zf.namelist())} файлов)")
    print("Отправляй партнёру этот файл.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", "-o", type=Path,
                        default=Path("tender-ai-tools.zip"))
    parser.add_argument("--mcp-dir", type=Path, default=MCP_DIR)
    args = parser.parse_args()

    if not args.mcp_dir.exists():
        print(f"WARN: папка MCP не найдена: {args.mcp_dir}")
        print("Архив будет собран без MCP-сервера.")

    build_archive(
        output_path=ROOT / args.output,
        root=ROOT,
        mcp_dir=args.mcp_dir,
    )


if __name__ == "__main__":
    main()
