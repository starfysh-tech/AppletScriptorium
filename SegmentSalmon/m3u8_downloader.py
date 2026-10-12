#!/usr/bin/env python3
"""
M3U8 Downloader - Downloads HLS video streams similar to VLC
"""

import os
import sys
import re
import time
import argparse
import shutil
import requests
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import subprocess
import threading
import signal
import atexit
import uuid
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn
from rich.console import Console


class UnsupportedPlaylistError(ValueError):
    pass


class ProgressTracker:
    def __init__(self, total_segments):
        self.total_segments = total_segments
        self.completed = 0
        self.failed = 0
        self.start_time = time.time()
        self.lock = threading.Lock()
        self.bytes_downloaded = 0
        
    def update_progress(self, success=True, bytes_count=0):
        with self.lock:
            if success:
                self.completed += 1
                self.bytes_downloaded += bytes_count
            else:
                self.failed += 1
                
    def get_rate(self):
        elapsed = time.time() - self.start_time
        if elapsed > 0:
            return self.completed / elapsed
        return 0
        
    def get_elapsed_time(self):
        return time.time() - self.start_time
        
    def get_eta(self):
        rate = self.get_rate()
        if rate > 0:
            remaining = self.total_segments - self.completed
            return remaining / rate
        return 0
        
    def format_time(self, seconds):
        """Format time in MM:SS or HH:MM:SS format"""
        if seconds < 0:
            return "00:00"
        
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"


class M3U8Downloader:
    def __init__(self, max_workers=2, timeout=30, retries=3):
        self.max_workers = max_workers
        self.timeout = timeout
        self.retries = retries
        self.quality_preset = 'high'
        self.session = self._create_session()
        self.console = Console()
        self.interrupted = False
        self.cleanup_files = []
        self.segments_dir = None
        self.session_id = str(uuid.uuid4())[:8]  # Short unique ID for this session
        
        # Register cleanup handlers
        atexit.register(self._cleanup_on_exit)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Flag the interrupt; workers and the download loop stop on the flag"""
        self.interrupted = True
        # A second Ctrl+C kills the process if a stalled request blocks shutdown
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        self.console.print("\n[yellow]Download interrupted by user. Stopping...[/yellow]")

    def _cleanup_on_exit(self):
        """Clean up temporary files (concat lists, etc.)"""
        for file_path in self.cleanup_files:
            try:
                file_path.unlink(missing_ok=True)
            except Exception:
                pass  # File might be in use, skip

    def _remove_segments_dir(self):
        """Remove the session segments directory"""
        if self.segments_dir and self.segments_dir.exists():
            shutil.rmtree(self.segments_dir, ignore_errors=True)
            self.console.print(f"[dim]Cleaned up session directory: {self.segments_dir.name}[/dim]")
            self.segments_dir = None
        
    def _create_session(self):
        """Create HTTP session with proper headers"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'VLC/3.0.0 LibVLC/3.0.0',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        return session
        
    def fetch_playlist(self, url):
        """Fetch M3U8 playlist content with retries"""
        attempts = self.retries + 1
        for attempt in range(attempts):
            if self.interrupted:
                raise Exception("interrupted")
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                return response.text
            except requests.RequestException as e:
                if attempt == attempts - 1:
                    raise Exception(f"Failed to fetch playlist after {attempts} attempts: {e}")
                time.sleep(2 ** attempt)
                
    def parse_playlist(self, content, base_url):
        """Parse M3U8 playlist and extract segment URLs"""
        lines = content.strip().split('\n')
        
        if not lines[0].startswith('#EXTM3U'):
            raise ValueError("Not a valid M3U8 playlist")
            
        # Check if this is a master playlist
        if any('#EXT-X-STREAM-INF' in line for line in lines):
            return self._parse_master_playlist(lines, base_url)
        else:
            return self._parse_media_playlist(lines, base_url)
            
    def _parse_master_playlist(self, lines, base_url):
        """Parse master playlist and return best quality stream URL"""
        streams = []

        for i, line in enumerate(lines):
            if line.startswith('#EXT-X-MEDIA') and 'TYPE=AUDIO' in line:
                raise UnsupportedPlaylistError("separate audio renditions (#EXT-X-MEDIA:TYPE=AUDIO) are not supported")
            if line.startswith('#EXT-X-STREAM-INF'):
                # Extract bandwidth
                bandwidth_match = re.search(r'BANDWIDTH=(\d+)', line)
                bandwidth = int(bandwidth_match.group(1)) if bandwidth_match else 0
                
                # Get stream URL from next line
                if i + 1 < len(lines):
                    stream_url = urljoin(base_url, lines[i + 1].strip())
                    streams.append((bandwidth, stream_url))
                    
        if not streams:
            raise ValueError("No streams found in master playlist")
            
        # Return highest bandwidth stream
        best_stream = max(streams, key=lambda x: x[0])[1]
        print(f"Selected stream: {best_stream}")
        return best_stream
        
    def _parse_media_playlist(self, lines, base_url):
        """Parse media playlist and extract segment URLs"""
        segments = []
        
        for line in lines:
            line = line.strip()
            if line.startswith('#EXT-X-KEY') and not re.search(r'[:,]METHOD=NONE(,|$)', line):
                raise UnsupportedPlaylistError("encrypted segments (#EXT-X-KEY) are not supported")
            if line.startswith('#EXT-X-MAP'):
                raise UnsupportedPlaylistError("fMP4 init segments (#EXT-X-MAP) are not supported")
            if line and not line.startswith('#'):
                segment_url = urljoin(base_url, line)
                segments.append(segment_url)
                
        return segments
        
    def download_segment(self, url, output_path, progress_tracker=None):
        """Download a single segment with retries and progress tracking"""
        attempts = self.retries + 1
        for attempt in range(attempts):
            if self.interrupted:
                return False
            bytes_downloaded = 0
            try:
                response = self.session.get(url, timeout=self.timeout, stream=True)
                response.raise_for_status()

                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if self.interrupted:
                            return False
                        if chunk:
                            f.write(chunk)
                            bytes_downloaded += len(chunk)

                if progress_tracker:
                    progress_tracker.update_progress(True, bytes_downloaded)
                return True

            except requests.RequestException:
                if attempt == attempts - 1:
                    if progress_tracker:
                        progress_tracker.update_progress(False)
                    return False
                time.sleep(2 ** attempt)
                
    def download_stream(self, playlist_url, output_dir, output_name=None):
        """Download complete HLS stream"""
        # Create output directory
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"Fetching playlist: {playlist_url}")
        playlist_content = self.fetch_playlist(playlist_url)
        base_url = playlist_url.rsplit('/', 1)[0] + '/'
        
        # Parse playlist
        result = self.parse_playlist(playlist_content, base_url)
        
        # Handle master playlist
        if isinstance(result, str):
            print("Master playlist detected, fetching media playlist...")
            media_playlist_content = self.fetch_playlist(result)
            base_url = result.rsplit('/', 1)[0] + '/'
            segments = self._parse_media_playlist(
                media_playlist_content.strip().split('\n'), base_url
            )
        else:
            segments = result
            
        if not segments:
            raise ValueError("No segments found in playlist")
            
        print(f"Found {len(segments)} segments to download")
        
        # Download segments to unique session directory
        segments_dir = output_dir / f"segments_salmon_{self.session_id}"
        segments_dir.mkdir(exist_ok=True)
        self.segments_dir = segments_dir  # Store for cleanup
        
        self.console.print(f"[dim]Session ID: {self.session_id} - Segments in: {segments_dir.name}[/dim]")
        
        segment_files = []
        progress_tracker = ProgressTracker(len(segments))
        
        def download_worker(args):
            i, segment_url = args
            segment_filename = f"segment_{i:06d}.ts"
            segment_path = segments_dir / segment_filename
            
            if self.download_segment(segment_url, segment_path, progress_tracker):
                return segment_path
            else:
                return None
                
        # Download with rich progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("•"),
            TextColumn("{task.completed}/{task.total} segments"),
            TextColumn("•"),
            TextColumn("[cyan]{task.fields[rate]:.1f} seg/s[/cyan]"),
            TextColumn("•"),
            TextColumn("[green]Elapsed: {task.fields[elapsed]}[/green]"),
            TextColumn("•"),
            TextColumn("[yellow]ETA: {task.fields[eta]}[/yellow]"),
            console=self.console,
            refresh_per_second=5
        ) as progress:
            
            task = progress.add_task("Downloading", total=len(segments), 
                                   rate=0.0, elapsed="00:00", eta="00:00")
            
            executor = ThreadPoolExecutor(max_workers=self.max_workers)
            try:
                futures = {executor.submit(download_worker, (i, url)): i
                          for i, url in enumerate(segments)}

                for future in as_completed(futures):
                    if self.interrupted:
                        self.console.print("\n[yellow]Cancelling remaining downloads...[/yellow]")
                        break

                    result = future.result()
                    if result:
                        segment_files.append((futures[future], result))
                    
                    # Update progress bar with current stats including time indicators
                    with progress_tracker.lock:
                        current_completed = progress_tracker.completed
                        current_failed = progress_tracker.failed
                        current_rate = progress_tracker.get_rate()
                        current_elapsed = progress_tracker.get_elapsed_time()
                        current_eta = progress_tracker.get_eta()
                    
                    description = "Downloading"
                    if current_failed > 0:
                        description = f"Downloading ({current_failed} failed)"
                    
                    progress.update(task, 
                                  completed=current_completed,
                                  total=len(segments),
                                  description=description,
                                  rate=current_rate,
                                  elapsed=progress_tracker.format_time(current_elapsed),
                                  eta=progress_tracker.format_time(current_eta))
            finally:
                executor.shutdown(wait=not self.interrupted, cancel_futures=True)

        if self.interrupted:
            self.console.print("[red]Download was interrupted by user[/red]")
            self._remove_segments_dir()
            return None

        if progress_tracker.failed > 0:
            raise Exception(
                f"{progress_tracker.failed} of {len(segments)} segments failed to download; "
                f"kept downloaded segments in {segments_dir}"
            )

        # Sort segment files by index
        segment_files.sort(key=lambda x: x[0])

        # Generate output filename
        if not output_name:
            output_name = f"video_{int(time.time())}.mp4"

        output_file = output_dir / output_name
        if shutil.which('ffmpeg'):
            output_file = output_file.with_suffix('.mp4')  # ffmpeg always writes MP4

        print(f"Concatenating {len(segment_files)} segments...")
        self._concatenate_segments([path for _, path in segment_files], output_file)
        print(f"Download completed: {output_file}")
        self._remove_segments_dir()
        return output_file

    def _concatenate_segments(self, segment_paths, output_path):
        """Concatenate video segments using FFmpeg for better quality"""
        if shutil.which('ffmpeg'):
            self._ffmpeg_concat(segment_paths, output_path)
            return

        print("FFmpeg not available, using binary concatenation...")
        with open(output_path, 'wb') as output_file:
            for segment_path in segment_paths:
                if segment_path.exists():
                    with open(segment_path, 'rb') as segment_file:
                        output_file.write(segment_file.read())
                        
    def _get_ffmpeg_preset(self):
        """Get FFmpeg preset based on quality setting"""
        presets = {
            'high': 'slow',     # Best quality, slower
            'medium': 'medium', # Balanced
            'low': 'fast'      # Faster, lower quality
        }
        return presets.get(self.quality_preset, 'medium')
        
    def _get_crf_value(self):
        """Get CRF value based on quality setting"""
        crf_values = {
            'high': '18',    # Very high quality
            'medium': '23',  # Good quality  
            'low': '28'      # Lower quality
        }
        return crf_values.get(self.quality_preset, '18')
                        
    def _ffmpeg_concat(self, segment_paths, output_path):
        """Concatenate with FFmpeg, lossless first; raise with FFmpeg's stderr on failure"""
        concat_file = output_path.parent / "concat_list.txt"
        self.cleanup_files.append(concat_file)  # Register for cleanup
        with open(concat_file, 'w') as f:
            for segment_path in segment_paths:
                # ffmpeg concat syntax: close the quote, escaped quote, reopen
                escaped = str(segment_path.absolute()).replace("'", "'\\''")
                f.write(f"file '{escaped}'\n")

        # Try lossless stream copy first (preserves source quality)
        if self._try_stream_copy(concat_file, output_path):
            concat_file.unlink(missing_ok=True)
            return

        # Ctrl+C also kills ffmpeg, which looks like a failed stream copy
        if self.interrupted:
            raise Exception("interrupted")
        # Fallback to re-encoding if stream copy fails
        stderr = self._try_reencoding(concat_file, output_path)
        if stderr is not None:
            raise Exception(f"FFmpeg failed; kept segments in {self.segments_dir}\n{stderr}")

    def _try_stream_copy(self, concat_file, output_path):
        """Try lossless stream copy concatenation"""
        cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0', 
            '-i', str(concat_file),
            '-c', 'copy',  # Stream copy - no re-encoding
            '-movflags', '+faststart',
            str(output_path)
        ]
        
        print("Attempting lossless concatenation (preserving source quality)...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"Lossless concatenation successful: {output_path}")
            return True
        else:
            print("Stream copy failed, will try re-encoding...")
            return False
            
    def _try_reencoding(self, concat_file, output_path):
        """Fallback to re-encoding with quality settings"""
        cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', str(concat_file),
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-preset', self._get_ffmpeg_preset(),
            '-crf', self._get_crf_value(),
            '-movflags', '+faststart',
            str(output_path)
        ]
        
        print(f"Re-encoding with {self.quality_preset} quality settings...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Clean up temp file
        concat_file.unlink(missing_ok=True)
        
        if result.returncode == 0:
            print(f"Re-encoded concatenation successful: {output_path}")
            return None
        return result.stderr


def main():
    parser = argparse.ArgumentParser(description='Download M3U8 HLS streams')
    parser.add_argument('url', help='M3U8 playlist URL')
    parser.add_argument('-o', '--output-dir', default='.', 
                       help='Output directory (default: current directory)')
    parser.add_argument('-n', '--name', help='Output filename (will use .mp4 extension if FFmpeg available)')
    parser.add_argument('--quality', choices=['high', 'medium', 'low'], default='high',
                       help='Video quality preset for FFmpeg (default: high)')
    parser.add_argument('--workers', type=int, default=2, 
                       help='Number of concurrent downloads (default: 2)')
    parser.add_argument('--timeout', type=int, default=30,
                       help='Request timeout in seconds (default: 30)')
    parser.add_argument('--retries', type=int, default=3,
                       help='Number of retries per segment after the first attempt (default: 3)')

    args = parser.parse_args()

    downloader = M3U8Downloader(
        max_workers=args.workers,
        timeout=args.timeout,
        retries=args.retries
    )

    # Set quality preset
    downloader.quality_preset = args.quality

    try:
        downloader.download_stream(
            args.url,
            args.output_dir,
            args.name
        )
    except UnsupportedPlaylistError as e:
        print(f"Error: {e}. Try: ffmpeg -i '{args.url}' -c copy output.mp4")
        sys.exit(1)
    except Exception as e:
        if downloader.interrupted:
            sys.exit(130)
        print(f"Error: {e}")
        sys.exit(1)

    if downloader.interrupted:
        sys.exit(130)


if __name__ == "__main__":
    main()