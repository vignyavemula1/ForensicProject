# Multimedia Forensics Detection System

## Overview
This comprehensive Multimedia Forensics Detection System provides advanced forensic analysis capabilities for:
- **Images** (JPEG, PNG)
- **Audio** (WAV, MP3, FLAC, OGG)
- **Video** (MP4, AVI, MOV, MKV)

## Features

### Image Forensics
1. **Copy-Move Detection** - Detects duplicated regions within an image
2. **Compression Detection** - Identifies double JPEG compression
3. **Metadata Analysis** - Extracts and analyzes EXIF metadata
4. **Noise Inconsistency** - Detects inconsistent noise patterns
5. **CFA Artifact Detection** - Identifies Color Filter Array artifacts
6. **Error-Level Analysis (ELA)** - Highlights manipulated regions
7. **Image Extraction** - Extracts hidden images through steganography
8. **String Extraction** - Extracts hidden text from image files

### Audio Forensics 🎵
1. **Splicing Detection** - Identifies audio cuts and splices through spectral analysis
2. **Clipping Detection** - Detects audio clipping that may indicate manipulation
3. **Noise Pattern Analysis** - Analyzes consistency of background noise
4. **Resampling Detection** - Identifies if audio has been resampled
5. **Compression Artifacts** - Detects signs of lossy compression
6. **Metadata Extraction** - Extracts detailed audio file metadata

### Video Forensics 🎬
1. **Frame Duplication** - Detects duplicate or frozen frames
2. **Inter-Frame Forgery** - Identifies temporal inconsistencies between frames
3. **Copy-Move Detection** - Detects copied regions within video frames
4. **Double Compression** - Identifies re-encoding artifacts
5. **Noise Consistency** - Analyzes noise patterns across frames
6. **Frame Rate Anomalies** - Detects irregular frame timing
7. **Metadata Analysis** - Extracts comprehensive video metadata

## Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Setup
```bash
# Install required packages
pip install -r requirements.txt
```

### Required Libraries
```
matplotlib>=3.7.0
numpy>=1.24.0
opencv_python>=4.8.0
Pillar>=10.0.0
prettytable>=3.2.0
pyparsing>=3.0.6
scikit_learn>=1.3.0
scipy>=1.10.0
librosa>=0.10.0
soundfile>=0.12.0
mutagen>=1.47.0
ffmpeg-python>=0.2.0
```

## Usage

### GUI Application
```bash
python GUI.py
```

The GUI provides three main upload options:
1. **Upload Image** - For image forensic analysis
2. **Upload Audio** - For audio forensic analysis
3. **Upload Video** - For video forensic analysis

#### Image Analysis Workflow:
1. Click "Upload Image" and select an image file
2. Choose from various detection algorithms:
   - Compression-Detection
   - Metadata-Analysis
   - CFA-artifact
   - Noise-Inconsistency
   - Copy-Move
   - Error-Level Analysis
   - Image-Extraction
   - String Extraction

#### Audio Analysis Workflow:
1. Click "Upload Audio" and select an audio file
2. Click "Audio Forensics" to run comprehensive analysis
3. Results will be saved to `Audio_Analysis.txt`

#### Video Analysis Workflow:
1. Click "Upload Video" and select a video file
2. Click "Video Forensics" to run comprehensive analysis
3. Results will be saved to `Video_Analysis.txt`

### Command-Line Usage

#### Audio Analysis
```bash
python audio_forensics.py path/to/audio/file.wav
```

#### Video Analysis
```bash
python video_forensics.py path/to/video/file.mp4
```

## Input Directories
Organize your test files in the following directories:
- `input/Audio Analysis/` - Audio files for testing
- `input/Video Analysis/` - Video files for testing
- `input/Copy-Move/` - Images for copy-move detection
- `input/Compression Detection/` - Images for compression testing
- `input/Metadata Analysis/` - Files with metadata
- And other existing image analysis directories...

## Output
- Analysis results are saved as text files:
  - `Audio_Analysis.txt` - Comprehensive audio forensic report
  - `Video_Analysis.txt` - Comprehensive video forensic report
  - `Metadata_analysis.txt` - Image metadata report
  - `hex_viewer.txt` - String extraction results

## Detection Algorithms

### Audio Forensics Algorithm Details

#### 1. Splicing Detection
- Uses Short-Time Fourier Transform (STFT)
- Analyzes spectral discontinuities
- Identifies suspicious temporal transitions
- Threshold: >5% abnormal frames indicates forgery

#### 2. Clipping Detection
- Identifies samples at or near maximum amplitude
- Calculates clipping percentage
- Threshold: >1% clipping is suspicious

#### 3. Noise Pattern Analysis
- Divides audio into segments
- Analyzes spectral centroids and zero-crossing rates
- Calculates coefficient of variation
- Threshold: >30% variation indicates inconsistency

#### 4. Resampling Detection
- Analyzes power spectral density
- Checks for frequency cutoffs
- Examines high-frequency content
- Low high-frequency ratio suggests resampling

#### 5. Compression Analysis
- Extracts Mel-frequency cepstral coefficients (MFCCs)
- Analyzes statistical properties
- High kurtosis indicates compression artifacts

### Video Forensics Algorithm Details

#### 1. Frame Duplication
- Samples frames uniformly
- Compares consecutive frames using correlation
- Threshold: >10% duplicates is suspicious

#### 2. Inter-Frame Forgery
- Analyzes temporal consistency
- Calculates frame-to-frame differences
- Identifies abnormal transitions
- Threshold: >15% suspicious frames

#### 3. Copy-Move Detection
- Uses SIFT feature detection on frames
- Applies DBSCAN clustering
- Identifies duplicated regions

#### 4. Double Compression
- Applies DCT to frames
- Analyzes coefficient distributions
- Low entropy indicates double compression

#### 5. Noise Consistency
- Estimates noise using Laplacian
- Calculates coefficient of variation
- Threshold: >50% variation is inconsistent

#### 6. Frame Rate Anomalies
- Checks against standard frame rates
- Analyzes temporal consistency
- Identifies timing irregularities

## Verdict Classification

### Overall Verdict Criteria:

**Audio & Video:**
- **LIKELY FORGED** - 2+ or 3+ forgery indicators detected
- **SUSPICIOUS** - 1-2 forgery indicators detected
- **LIKELY AUTHENTIC** - 0-1 forgery indicators detected

## Technical Details

### Audio Processing
- Sample rates: Supports all standard sample rates
- Formats: WAV, MP3, FLAC, OGG
- Analysis window: Configurable (default: 2048 samples)
- Segment analysis: 10 segments for consistency checks

### Video Processing
- Resolutions: Supports all common resolutions
- Formats: MP4, AVI, MOV, MKV
- Frame sampling: Adaptive based on video length
- Analysis methods: SIFT, DCT, correlation analysis

### Image Processing
- Formats: JPEG, PNG
- Algorithms: SIFT, DBSCAN, DCT, ELA
- Block-based analysis for copy-move detection

## Troubleshooting

### Common Issues:

1. **ImportError for librosa/soundfile:**
   ```bash
   pip install librosa soundfile
   ```

2. **Audio analysis errors:**
   - Ensure audio file is not corrupted
   - Check file format is supported
   - Try converting to WAV format

3. **Video analysis slow:**
   - Large videos are automatically sampled
   - Reduce sample size in code if needed
   - Consider processing shorter clips

4. **Missing ffprobe:**
   - Install FFmpeg for enhanced metadata extraction
   - System will work without it but with reduced metadata

## Performance Considerations

- **Audio Analysis:** ~5-30 seconds depending on file length
- **Video Analysis:** ~1-5 minutes depending on file size and length
- **Image Analysis:** <5 seconds for most operations

## Limitations

### Audio:
- Very short clips (<1 second) may not provide enough data
- Heavily compressed files may have limited forensic value

### Video:
- Very large files (>1GB) may require significant processing time
- Low-resolution videos may have reduced detection accuracy