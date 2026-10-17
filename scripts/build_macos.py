"""Build an Apple Silicon or Intel .app using the current Python architecture.

Run from the repository root: .venv/bin/python scripts/build_macos.py
"""

from pathlib import Path
import argparse
import os
import subprocess
import sys
import tempfile

from PIL import Image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dmg", action="store_true", help="Also create the drag-to-install disk image")
    args = parser.parse_args()
    if sys.platform != "darwin":
        raise SystemExit("Build the macOS application on macOS.")
    root = Path(__file__).resolve().parents[1]
    build = root / "build" / "macos"
    iconset = build / "RealceCoronal.iconset"
    iconset.mkdir(parents=True, exist_ok=True)
    source = root / "assets" / "icon-options" / "03-realce-coronal.png"
    with Image.open(source) as image:
        image = image.convert("RGBA")
        for size in (16, 32, 128, 256, 512):
            for density in (1, 2):
                suffix = "@2x" if density == 2 else ""
                image.resize((size * density, size * density), Image.Resampling.LANCZOS).save(
                    iconset / f"icon_{size}x{size}{suffix}.png")
    icon = build / "RealceCoronal.icns"
    subprocess.run(["/usr/bin/iconutil", "-c", "icns", str(iconset), "-o", str(icon)], check=True)

    # Keep caches and generated spec files inside the ignored build directory.
    environment = os.environ.copy()
    environment["PYINSTALLER_CONFIG_DIR"] = str(build / "cache")
    subprocess.run([
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--windowed", "--onedir", "--name", "Corona Enhance Filters",
        "--icon", str(icon), "--osx-bundle-identifier", "com.fbitto.realcecoronal",
        "--specpath", str(build), "--workpath", str(build / "work"),
        "--distpath", str(root / "dist"),
        "--add-data", f"{source}:assets/icon-options",
        "--collect-all", "watroo",
        "--hidden-import", "PIL.TiffImagePlugin",
        str(root / "main.py"),
    ], cwd=root, env=environment, check=True)
    print(f"Application ready: {root / 'dist' / 'Corona Enhance Filters.app'}")
    if args.dmg:
        app = root / "dist" / "Corona Enhance Filters.app"
        subprocess.run(["/usr/bin/codesign", "--verify", "--deep", "--strict", str(app)], check=True)
        with tempfile.TemporaryDirectory(prefix="dmg-", dir=build) as staging:
            destination = Path(staging)
            subprocess.run(["/usr/bin/ditto", str(app), str(destination / app.name)], check=True)
            (destination / "Applications").symlink_to("/Applications", target_is_directory=True)
            dmg = root / "dist" / "Corona Enhance Filters.dmg"
            subprocess.run([
                "/usr/bin/hdiutil", "create", "-volname", "Corona Enhance Filters",
                "-srcfolder", str(destination), "-format", "UDZO", "-ov", str(dmg),
            ], check=True)
            subprocess.run(["/usr/bin/hdiutil", "verify", str(dmg)], check=True)
        print(f"Installer ready: {dmg}")


if __name__ == "__main__":
    main()
