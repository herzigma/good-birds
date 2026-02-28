import argparse
import sys
from pathlib import Path

import click
import rawpy
from PIL import Image
from rich.console import Console
from rich.progress import Progress
from rich.table import Table

from good_birds.burst import group_into_bursts
from good_birds.models import PhotoInfo, ScoredPhoto
from good_birds.rating import is_exiftool_installed, write_rating
from good_birds.scanner import scan_directory
from good_birds.scorer import score_photo

console = Console()

def normalize_scores(burst_photos: list[ScoredPhoto]) -> None:
    """
    Normalize sharpness and exposure scores within a burst 
    so they are on a comparable scale (0.0 to 1.0) before combining.
    """
    if not burst_photos:
        return
        
    sharpness_scores = [p.sharpness_score for p in burst_photos]
    exposure_scores = [p.exposure_score for p in burst_photos]
    
    max_s = max(sharpness_scores) if sharpness_scores else 0
    min_s = min(sharpness_scores) if sharpness_scores else 0
    
    max_e = max(exposure_scores) if exposure_scores else 0
    min_e = min(exposure_scores) if exposure_scores else 0
    
    for p in burst_photos:
        # Normalize sharpness
        if max_s > min_s:
            p.sharpness_score = (p.sharpness_score - min_s) / (max_s - min_s)
        else:
            p.sharpness_score = 1.0  # They are all the same
            
        # Normalize exposure (already bounded 0-1 from our basic metric, but let's stretch it)
        if max_e > min_e:
            p.exposure_score = (p.exposure_score - min_e) / (max_e - min_e)
        else:
            p.exposure_score = 1.0


@click.command()
@click.argument('directory', type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path))
@click.option('--burst-threshold', default=1.0, help='Seconds between shots to group as burst')
@click.option('--sharpness-weight', default=0.7, help='Weight for sharpness score 0-1')
@click.option('--exposure-weight', default=0.3, help='Weight for exposure score 0-1')
@click.option('--center-weight', default=1.5, help='Extra weight for center sharpness')
@click.option('--rating-best', default=5, help='Star rating for best photo')
@click.option('--rating-rest', default=1, help='Star rating for non-best photos')
@click.option('--dry-run', is_flag=True, help='Show results without writing ratings')
@click.option('--verbose', is_flag=True, help='Show detailed scoring info')
def main(
    directory: Path,
    burst_threshold: float,
    sharpness_weight: float,
    exposure_weight: float,
    center_weight: float,
    rating_best: int,
    rating_rest: int,
    dry_run: bool,
    verbose: bool
):
    """Good Birds - Sort and rate bird photography RAW bursts."""
    
    if not dry_run and not is_exiftool_installed():
        console.print("[bold red]Error:[/] exiftool is not installed or not in PATH.")
        console.print("Please install exiftool to write ratings, or use --dry-run.")
        sys.exit(1)
        
    console.print(f"[bold cyan]Scanning directory:[/] {directory}")
    
    # 1. Scan directory
    with console.status("[bold green]Scanning for RAW files..."):
        photos = scan_directory(directory)
        
    if not photos:
        console.print("[yellow]No supported RAW files found in directory.[/]")
        return
        
    console.print(f"Found [bold]{len(photos)}[/] RAW files.")
    
    # 2. Group into bursts
    bursts = group_into_bursts(photos, threshold_seconds=burst_threshold)
    
    # Filter out single-photo bursts if desired, but for now we'll process all
    # Just to apply the rating.
    
    console.print(f"Grouped into [bold]{len(bursts)}[/] bursts.")
    
    # 3. Score photos
    total_photos_to_score = sum(len(b) for b in bursts)
    
    with Progress(console=console) as progress:
        score_task = progress.add_task("[green]Scoring photos...", total=total_photos_to_score)
        
        for burst in bursts:
            for p in burst.photos:
                # We need to extract the preview again to score it 
                # (to avoid holding hundreds of numpy arrays in memory)
                try:
                    with rawpy.imread(str(p.info.path)) as raw:
                        thumb = raw.extract_thumb()
                        if thumb.format == rawpy.ThumbFormat.JPEG:
                            import io
                            preview_img = Image.open(io.BytesIO(thumb.data))
                            
                            s_score, e_score, _ = score_photo(
                                p.info, 
                                preview_img,
                                center_weight=center_weight
                            )
                            p.sharpness_score = s_score
                            p.exposure_score = e_score
                except Exception as e:
                    if verbose:
                        console.print(f"[yellow]Failed to score {p.info.path.name}: {e}[/]")
                        
                progress.advance(score_task)
                
            # Normalize and combine within the burst
            normalize_scores(burst.photos)
            
            for p in burst.photos:
                p.combined_score = (
                    p.sharpness_score * sharpness_weight + 
                    p.exposure_score * exposure_weight
                )
                
            # Pick best
            if burst.photos:
                burst.best_photo = max(burst.photos, key=lambda p: p.combined_score)

    # 4. Write ratings and show summary
    table = Table(title="Burst Summary")
    table.add_column("Burst", justify="right", style="cyan", no_wrap=True)
    table.add_column("Count", justify="right", style="magenta")
    table.add_column("Best Photo", style="green")
    if verbose:
        table.add_column("Sharpness", justify="right")
        table.add_column("Exposure", justify="right")
        table.add_column("Combined", justify="right")

    with Progress(console=console) as progress:
        write_task = progress.add_task("[blue]Writing ratings...", total=total_photos_to_score)
        
        for i, burst in enumerate(bursts, 1):
            best = burst.best_photo
            
            if best:
                if verbose:
                    table.add_row(
                        f"#{i}", 
                        str(len(burst)), 
                        best.info.path.name,
                        f"{best.sharpness_score:.2f}",
                        f"{best.exposure_score:.2f}",
                        f"{best.combined_score:.2f}"
                    )
                else:
                    table.add_row(f"#{i}", str(len(burst)), best.info.path.name)
            
            for p in burst.photos:
                rating = rating_best if p is best else rating_rest
                success = write_rating(p.info.path, rating, dry_run=dry_run)
                if not success and verbose:
                    console.print(f"[red]Failed to write to {p.info.path.name}[/]")
                progress.advance(write_task)

    console.print(table)
    
    if dry_run:
        console.print("[yellow]Dry run completed. No files were modified.[/]")
    else:
        console.print("[green]Processing completed successfully![/]")

if __name__ == "__main__":
    main()
