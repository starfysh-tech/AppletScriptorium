# 🐟 Segment Salmon

A high-performance M3U8 downloader that swims upstream to gather video segments with style. Downloads HLS video streams similar to VLC, but with dynamic progress bars and lossless quality preservation.

## ✨ Features

- **🎯 Lossless Quality**: Preserves source quality with FFmpeg stream copy (no re-encoding)
- **📊 Dynamic Progress**: Animated progress bars with download rates, ETA, and spinners
- **⚡ Concurrent Downloads**: Multi-threaded segment downloading with configurable workers
- **🔄 Smart Retry Logic**: Exponential backoff retry system for failed segments
- **⌨️ Graceful Interrupts**: Clean Ctrl+C handling with automatic cleanup
- **🧹 Smart Cleanup**: Removes temporary files and partial downloads automatically
- **📱 Quality Presets**: High/Medium/Low quality options for re-encoding fallback
- **🔍 Master Playlist Support**: Automatically selects highest bandwidth stream

## 🚀 Quick Start

### Single Command Usage

```bash
# Show help menu
./segment-salmon

# Download with automatic quality detection
./segment-salmon 'https://example.com/playlist.m3u8'

# Download to specific directory with custom name
./segment-salmon 'https://example.com/playlist.m3u8' -o ./downloads -n myvideo.mp4

# High-performance download with 8 workers
./segment-salmon 'https://example.com/playlist.m3u8' --workers 8 --quality high
```

## 📦 Dependencies

The shell wrapper automatically handles dependency management:

- **python3** (required) - Install via `brew install python3` or `apt install python3`
- **requests** (auto-installed) - HTTP client library
- **rich** (auto-installed) - Beautiful terminal output
- **ffmpeg** (optional) - For lossless concatenation and MP4 output

## 🛠️ Installation

```bash
git clone <repository-url>
cd segment-salmon
chmod +x segment-salmon
./segment-salmon --help
```

The first run will automatically prompt to install missing Python dependencies.

## 📖 Usage Examples

### Basic Downloads
```bash
# Simple download
./segment-salmon 'https://cdn.example.com/video/playlist.m3u8'

# Custom output location
./segment-salmon 'https://cdn.example.com/video/playlist.m3u8' -o ~/Downloads -n video.mp4
```

### Advanced Options
```bash
# High-performance settings
./segment-salmon 'https://cdn.example.com/video/playlist.m3u8' \
  --workers 10 \
  --timeout 60 \
  --retries 5 \
  --quality high

# Low-bandwidth friendly
./segment-salmon 'https://cdn.example.com/video/playlist.m3u8' \
  --workers 2 \
  --quality medium
```

## 🎛️ Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `-o, --output-dir` | Output directory | Current directory |
| `-n, --name` | Output filename | `video_[timestamp].mp4` |
| `--quality` | Quality preset: high/medium/low | `high` |
| `--workers` | Concurrent downloads | `2` |
| `--timeout` | Request timeout (seconds) | `30` |
| `--retries` | Retry attempts per segment | `3` |
| `-h, --help` | Show help message | - |

## 🎨 Progress Display

The dynamic progress bar shows:
```
⠋ Downloading ━━━━━━━━━━░░░░░░ 67% • 4,987/7,431 segments • 2.4 MB/s • 0:12:34
```

- **Spinner**: Shows active download status
- **Progress Bar**: Visual completion indicator
- **Percentage**: Current progress
- **Counters**: Completed/total segments
- **Speed**: Real-time transfer rate
- **ETA**: Estimated time remaining

## 🔧 Technical Details

### Quality Preservation
1. **Stream Copy**: Attempts lossless concatenation first (`ffmpeg -c copy`)
2. **Fallback Re-encoding**: Uses quality presets if stream copy fails
3. **Format Support**: Outputs MP4 with H.264/AAC when FFmpeg available

### Interrupt Handling
- **Ctrl+C**: Graceful shutdown with cleanup message
- **SIGTERM**: Proper signal handling for system shutdowns
- **Cleanup**: Removes partial downloads and temporary files
- **Exit Codes**: Standard POSIX exit codes (130 for SIGINT)

### Error Recovery
- **Exponential Backoff**: `2^attempt` second delays between retries
- **Failed Segment Tracking**: Continues download despite individual failures
- **Network Resilience**: Handles connection timeouts and HTTP errors

## 🐛 Troubleshooting

### Common Issues

**FFmpeg not found**
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# The script works without FFmpeg but uses basic concatenation
```

**Python dependencies missing**
```bash
# The script will prompt to auto-install, or manually:
pip3 install --user requests rich
```

**Permission denied**
```bash
chmod +x segment-salmon
```

## 📄 License

MIT License - Feel free to swim with the salmon! 🐟

## 🤝 Contributing

Contributions welcome! This salmon loves company upstream.

---

*Built with ❤️ for downloading HLS streams that swim against the current*