import os
import zipfile
from pathlib import Path
import argparse


def package_skill(skill_path: Path, output_dir: Path):
    """Zips a skill directory for distribution"""
    if not skill_path.exists() or not skill_path.is_dir():
        print(f"❌ Error: {skill_path} is not a valid directory.")
        return False

    skill_name = skill_path.name
    output_dir.mkdir(exist_ok=True)

    zip_path = output_dir / f"{skill_name}.skill"

    # If the file exists, we'll overwrite it
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(skill_path):
            if "__pycache__" in root or ".git" in root or "dist" in root:
                continue
            for file in files:
                filepath = Path(root) / file
                # Archive name should be relative to the skill's parent so the folder is included
                arcname = filepath.relative_to(skill_path.parent)
                zipf.write(filepath, arcname)

    print(f"✅ Success! Packaged {skill_name} to: {zip_path}")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Package one or more skills into .skill (ZIP) files.")
    parser.add_argument("skill_paths", nargs="+", help="Paths to one or more skill directories")
    parser.add_argument("--out", default="dist", help="Output directory for the packaged skills (default: dist)")

    args = parser.parse_args()

    # If --out is a relative path, make it relative to the current working directory
    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = Path.cwd() / out_dir

    success_count = 0
    for path_str in args.skill_paths:
        skill_path = Path(path_str).resolve()
        if package_skill(skill_path, out_dir):
            success_count += 1

    if success_count > 0:
        print(f"\nSummary: Packaged {success_count} skill(s) into {out_dir}")
    else:
        print("\nNo skills were packaged.")
