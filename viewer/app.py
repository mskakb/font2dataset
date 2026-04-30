#!/usr/bin/env python3

"""
Web viewer for font2dataset images.

Browse generated character images organized by font and Unicode block.
"""

import argparse
import json
import logging
from pathlib import Path

from flask import Flask, render_template, send_file, jsonify

app = Flask(__name__, template_folder='templates')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global state (set at startup)
metadata_records = []
fonts_set = set()
output_dir = None


def load_metadata(output_dir: str | Path) -> list[dict]:
    """Load metadata.jsonl from output directory."""
    metadata_path = Path(output_dir) / "metadata.jsonl"
    if not metadata_path.exists():
        logger.warning("metadata.jsonl not found at %s", metadata_path)
        return []

    records = []
    with open(metadata_path) as f:
        for line in f:
            if line.strip():
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as e:
                    logger.error("Failed to parse line: %s", e)
                    continue

    logger.info("Loaded %d records from metadata.jsonl", len(records))
    return records


@app.route("/")
def index():
    """Serve the main viewer page."""
    return render_template("index.html")


@app.route("/api/metadata")
def api_metadata():
    """Return all metadata records as JSON."""
    return jsonify(metadata_records)


@app.route("/api/fonts")
def api_fonts():
    """Return sorted list of unique fonts."""
    return jsonify(sorted(list(fonts_set)))


@app.route("/images/<filename>")
def serve_image(filename: str):
    """Serve image files from output/images/."""
    if not output_dir:
        return "Output directory not configured", 400

    image_path = Path(output_dir) / "images" / filename
    if not image_path.exists() or not image_path.is_file():
        return "Image not found", 404

    return send_file(image_path, mimetype="image/png")


def main():
    """Main entry point."""
    global metadata_records, fonts_set, output_dir

    parser = argparse.ArgumentParser(
        description="Web viewer for font2dataset images."
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./output",
        help="Output directory from font2dataset pipeline (default: ./output)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port to run server on (default: 5000)",
    )

    args = parser.parse_args()
    output_dir = str(Path(args.output_dir).resolve())

    # Load metadata at startup
    metadata_records = load_metadata(output_dir)
    fonts_set = {record["font_path"] for record in metadata_records}

    logger.info("Starting viewer on http://localhost:%d", args.port)
    app.run(debug=True, port=args.port, use_reloader=False)


if __name__ == "__main__":
    main()
