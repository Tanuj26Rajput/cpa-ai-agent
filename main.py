from pathlib import Path
import sys

from workflow.pipeline import run_pipeline


def main():
    args = sys.argv[1:]
    source_type = "local"
    input_location = None

    if args:
        if args[0] in {"local", "gdrive", "email", "auto"}:
            source_type = args[0]
            if len(args) > 1:
                input_location = args[1]
        else:
            input_location = args[0]

    if input_location is None and source_type == "local":
        for candidate in (
            Path("data/order_10283.pdf"),
            Path("data/order_10272.pdf"),
            Path("data/order_10262.pdf"),
            Path("data/invoice_10260.pdf"),
            Path("data/order_10248.pdf"),
            Path("data/order_10264.pdf"),
            Path("data/sample.txt"),
        ):
            if candidate.exists():
                input_location = str(candidate)
                break

    report = run_pipeline(input_location=input_location, source_type=source_type)
    print("\n=== FINAL REPORT ===\n")
    print(report)


if __name__ == "__main__":
    main()
