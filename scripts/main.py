import logging
import sys
from pathlib import Path

if __name__ == "__main__" and __package__ is None:
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from scripts.pipeline import (  # noqa: E402
    extract_class_type,
    get_school_type,
    main as pipeline_main,
    normalize_name,
    run_pipeline,
)

__all__ = [
    "extract_class_type",
    "get_school_type",
    "main",
    "normalize_name",
    "run_pipeline",
]


def main(argv: list[str] | None = None):
    return pipeline_main(argv)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s"
    )
    main()
