import argparse
import os
from pathlib import Path
import fitz  # PyMuPDF
from pypdf import PdfWriter


def format_size(size_bytes: int) -> str:
    """Format byte size into human-readable KB or MB."""
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    return f"{size_bytes / 1024:.2f} KB"


def compress_pdf_basic(
    input_path: str,
    output_path: str,
    image_quality: int = 65,
    max_dpi: int = 150,
) -> tuple[int, int]:
    orig_size = os.path.getsize(input_path)

    # 1. Use PyMuPDF (fitz) to downsample/recompress images, deduplicate objects, and deflate streams
    try:
        doc = fitz.open(input_path)
        if hasattr(doc, "rewrite_images"):
            doc.rewrite_images(
                dpi_threshold=max_dpi + 50,
                dpi_target=max_dpi,
                quality=image_quality,
                lossy=True,
                lossless=True,
                bitonal=True,
                color=True,
                gray=True,
                set_to_gray=False,
            )
        doc.save(
            output_path,
            garbage=4,          # Deduplicate identical objects & remove unused/orphan objects
            deflate=True,       # Compress all uncompressed streams
            deflate_images=True,
            deflate_fonts=True,
            clean=True,         # Clean and sanitize content streams
        )
        doc.close()
    except Exception:
        # 2. Fallback to pypdf + Pillow image recompression & object deduplication
        writer = PdfWriter(clone_from=input_path)
        # Compress content streams and embedded images for all pages added to the writer
        for page in writer.pages:
            for img in page.images:
                img.replace(img.image, quality=image_quality)
            page.compress_content_streams()
        writer.compress_identical_objects(remove_identicals=True, remove_orphans=True)
        with open(output_path, "wb") as f:
            writer.write(f)

    new_size = os.path.getsize(output_path)
    reduction = (1 - new_size / orig_size) * 100 if orig_size > 0 else 0.0
    print(
        f"Saved optimized PDF to {output_path} "
        f"({format_size(orig_size)} -> {format_size(new_size)}, {reduction:.1f}% reduction)"
    )
    return orig_size, new_size


def print_comparison_table(results: list[dict]) -> None:
    if not results:
        return

    header = (
        f"{'PDF FILE':<40} | {'ORIGINAL':>12} | {'COMPRESSED':>12} | "
        f"{'SAVED':>12} | {'REDUCTION':>10}"
    )
    print("\n" + header)
    print("-" * len(header))

    total_orig = 0
    total_comp = 0

    for r in results:
        orig = r["orig_size"]
        comp = r["comp_size"]
        saved = orig - comp
        pct = (saved / orig * 100) if orig > 0 else 0.0
        total_orig += orig
        total_comp += comp
        name = r["name"] if len(r["name"]) <= 40 else r["name"][:37] + "..."
        print(
            f"{name:<40} | {format_size(orig):>12} | {format_size(comp):>12} | "
            f"{format_size(saved):>12} | {pct:>9.1f}%"
        )

    total_saved = total_orig - total_comp
    total_pct = (total_saved / total_orig * 100) if total_orig > 0 else 0.0
    print("-" * len(header))
    print(
        f"{'TOTAL (' + str(len(results)) + ' files)':<40} | "
        f"{format_size(total_orig):>12} | {format_size(total_comp):>12} | "
        f"{format_size(total_saved):>12} | {total_pct:>9.1f}%"
    )


def compress_pdfs_in_folder(
    source_folder: str,
    output_folder: str = None,
    image_quality: int = 65,
    max_dpi: int = 150,
    compare_only: bool = False,
):
    input_dir = Path(source_folder).expanduser().resolve()
    if not input_dir.exists() or not input_dir.is_dir():
        print(f"Source folder {source_folder} does not exist.")
        return

    if output_folder:
        output_dir = Path(output_folder).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
    else:
        output_dir = input_dir

    # Find all source PDFs in the folder (skipping already-generated compressed_*.pdf files)
    pdf_files = sorted(
        p for p in input_dir.glob("*.pdf")
        if not p.name.startswith("compressed_")
    )

    if not pdf_files:
        print(f"No PDF files found in {input_dir}.")
        return

    print(f"Found {len(pdf_files)} PDF file(s) in {input_dir}.")

    comparison_results = []
    for pdf_path in pdf_files:
        # Skip already compressed or output files if in same folder to avoid overwriting issues
        out_path = output_dir / f"compressed_{pdf_path.name}"
        try:
            if compare_only:
                if out_path.exists():
                    orig_size = os.path.getsize(pdf_path)
                    new_size = os.path.getsize(out_path)
                else:
                    print(f"Skipping {pdf_path.name} (no compressed file at {out_path.name})")
                    continue
            else:
                print(f"Compressing {pdf_path.name}...")
                orig_size, new_size = compress_pdf_basic(
                    str(pdf_path),
                    str(out_path),
                    image_quality=image_quality,
                    max_dpi=max_dpi,
                )
            comparison_results.append({
                "name": pdf_path.name,
                "orig_size": orig_size,
                "comp_size": new_size,
            })
        except Exception as e:
            print(f"Error processing {pdf_path.name}: {e}")

    print_comparison_table(comparison_results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compress and compare all PDFs in a source folder.")
    parser.add_argument(
        "source_folder",
        nargs="?",
        type=str,
        help="Path to the source folder containing PDFs",
    )
    parser.add_argument("-o", "--output_folder", type=str, default=None, help="Path to output folder (optional)")
    parser.add_argument("-q", "--quality", type=int, default=65, help="JPEG image quality (1-100, default: 65)")
    parser.add_argument("--dpi", type=int, default=150, help="Target max image DPI (default: 150)")
    parser.add_argument(
        "--compare-only",
        action="store_true",
        help="Only compare existing original vs compressed_*.pdf file sizes without re-compressing",
    )

    args = parser.parse_args()
    source_path = args.source_folder or input("Enter source folder path: ").strip().strip('"')
    compress_pdfs_in_folder(
        source_path,
        args.output_folder,
        args.quality,
        args.dpi,
        compare_only=args.compare_only,
    )
