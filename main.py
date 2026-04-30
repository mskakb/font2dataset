# REVIEW: pending

"""Simple example: generate ASCII dataset with default settings."""

from font2dataset.pipeline import PipelineConfig, run_pipeline
from font2dataset.renderer import RenderConfig


def main():
    """Generate a small example dataset (ASCII, default rendering)."""
    config = PipelineConfig(
        charset="ascii",
        font_dir="./fonts",
        output_dir="./output",
        render=RenderConfig(
            image_size=(64, 64),
            font_size=48,
        ),
        workers=2,
    )

    print("Starting example dataset generation...")
    result = run_pipeline(config)

    print(f"\nGeneration complete:")
    print(f"  Total images: {result.total_images}")
    print(f"  Parquet: {result.parquet_path}")
    print(f"  Elapsed: {result.elapsed_seconds:.1f}s")


if __name__ == "__main__":
    main()
