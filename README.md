# Good Birds 🦅 📸

A blazing fast command-line tool to help bird photographers sort through bursts of RAW photos and automatically pick the sharpest, best-exposed shots.

## Features

- **Blazing Fast**: Uses the embedded JPEG thumbnail inside the RAW file for analysis. No slow RAW decoding required.
- **Smart Burst Detection**: Automatically groups photos taken within 1 second of each other.
- **Sharpness Analytics**: Uses OpenCV Laplacian Variance to detect which photo is actually in focus.
- **Exposure Detection**: Analyzes histograms to severely penalize clipped highlights (blown whites) and crushed shadows.
- **Automatic Rating**: Writes standard XMP star ratings direct to your CR2 files so they show up beautifully in Lightroom, Adobe Bridge, and other EXIF-aware software.
- **Standalone Binary**: Zero dependencies required if you download the Windows executable! ExifTool is bundled automatically inside the app.

## Standalone Executable (Windows)

The released `.exe` bundle for Windows is completely self-contained. **You do not need to install ExifTool or Python.**
ExifTool is bundled directly inside the executable and invoked automatically in the background to safely write ratings. Simply download the `.exe` and run it against your photo directories.

## macOS and Linux

For macOS and Linux users, Good Birds operates natively but requires **ExifTool** to be installed on your system since it cannot be pre-bundled into a single executable as cleanly as on Windows.

1. **Install ExifTool** via your package manager:
   - **macOS**: `brew install exiftool`
   - **Ubuntu/Debian**: `sudo apt install libimage-exiftool-perl`
2. **Run Good Birds** from source or build your own executable (see Development section). The application will automatically detect your system's `exiftool` installation and use it!

## How Ratings Work

Good Birds modifies the **metadata** of your original RAW files directly without altering the image data itself.

### What changes are made to the image files?

The tool uses the industry-standard ExifTool engine to write standard **XMP Star Ratings** (`XMP:Rating`) into the metadata headers of your RAW/CR2 files.
By default:

- The single "best" photo in each burst receives a **5-star** rating.
- All other photos in the burst receive a **1-star** rating.

### Using ratings in your photo editing software

Because Good Birds writes standard XMP ratings, these stars are instantly recognized by almost all professional photo management software:

1. Run `good-birds` on your folder of RAW files.
2. Open that same folder in your editing software (e.g., **Adobe Lightroom Classic**, **Adobe Bridge**, **Capture One**, or **Darktable**).
3. The star ratings will automatically appear under your photo thumbnails.
4. **Filter your view** to show only 5-star photos! You can now instantly review the best, sharpest shots from every burst, and mass-delete the 1-star blurry duplicates if desired.

## Usage

```bash
# Basic usage
good-birds /path/to/your/photos

# Dry run (don't write actual ratings to files, just show what it would do)
good-birds /path/to/your/photos --dry-run --verbose

# Tweak the burst timeframe to 0.5s instead of 1.0s
good-birds /path/to/your/photos --burst-threshold 0.5
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--burst-threshold` | `1.0` | Seconds between shots to still be considered part of the same burst. |
| `--sharpness-weight` | `0.7` | How much relative weight sharpness should get in the combined score. |
| `--exposure-weight` | `0.3` | How much relative weight exposure gets in the combined score. |
| `--center-weight` | `1.5` | Extra score multiplier for sharpness found in the center 50% of the frame. |
| `--rating-best` | `5` | The XMP star rating to write to the best photo in each burst. |
| `--rating-rest` | `1` | The XMP star rating to write to all other photos in the burst. |
| `--dry-run` | `False` | Analyzes and scores photos but skips writing ratings via exiftool. |
| `--verbose` | `False` | Print detailed scoring data for the best photo of every burst in the final table. |

## How it works

1. **Scanning**: Scans the provided directory for RAW files (supports CR2, CR3, NEF, ARW).
2. **Grouping**: Reads the ultra-precise `DateTimeOriginal` and `SubsecTimeOriginal` from the Exif headers. Groups files that have timestamps within the threshold (1s default) of each other.
3. **Extraction**: Uses `rawpy` to lift the embedded preview JPEG out of the RAW file.
4. **Scoring**:
   - **Sharpness**: Converts the image to grayscale and applies a Laplacian operator to find edges, calculating variance. More variance = more micro-contrast edges = sharper image.
   - **Exposure**: Looks at the 8-bit histogram. Applies large penalties for pixels hitting 255 (blown highlights) or 0 (pure black shadows).
5. **Rating**: Combines the normalized scores and picks the top photo per burst. Uses the bundled ExifTool Perl engine to call `exiftool -XMP:Rating=X` and overwrites the metadata in place.

## Development

Requires Python 3.9+. We use `uv` for blazing fast dependency management.

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -e .
pytest
```

## Building

To build the standalone single-file distribution, use PyInstaller.

If building on **Windows**, ensure you have run the `download_exiftool.py` script first to fetch the local ExifTool binary. The PyInstaller script will automatically bundle it. If building on **macOS/Linux**, PyInstaller will skip bundling ExifTool and correctly assume the end-user has installed it via their package manager.

```bash
uv pip install pyinstaller
pyinstaller good-birds.spec
```

The executable will be located in the `dist/` directory.

## License

MIT License. See `LICENSE`.
