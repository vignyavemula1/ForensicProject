import os
import sys
import cv2
from django.shortcuts import render
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from PIL import Image, ExifTags
from .forms import ImageUploadForm, AudioUploadForm, VideoUploadForm
# Project root (where manage.py, ForgeryDetection.py, audio_forensics.py, video_forensics.py live)
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
import double_jpeg_compression
import noise_variance
from ForgeryDetection import Detect

# Optional: audio/video forensics (project root)
try:
    import audio_forensics
except ImportError:
    audio_forensics = None
try:
    import video_forensics
except ImportError:
    video_forensics = None


def home_view(request):
    """Multimedia forensics detector landing: Image, Audio, Video."""
    return render(request, 'forgery/home.html')


def upload_view(request):
    context = {}
    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            image = form.cleaned_data['image']
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            fs = FileSystemStorage(location=upload_dir)
            filename = fs.save(image.name, image)
            file_path = fs.path(filename)

            # Run existing detection scripts
            double_comp = False
            try:
                double_comp = double_jpeg_compression.detect(file_path)
            except Exception:
                double_comp = False

            exif_data = {}
            try:
                img = Image.open(file_path)
                img_exif = img.getexif()
                if img_exif:
                    for k, v in img_exif.items():
                        exif_data[ExifTags.TAGS.get(k, k)] = v
            except Exception:
                exif_data = {}

            noise = False
            try:
                noise = noise_variance.detect(file_path)
            except Exception:
                noise = False

            # Copy-move forgery detection
            forgery_url = None
            try:
                detect = Detect(file_path)
                detect.siftDetector()
                forgery_img = detect.locateForgery()
                if forgery_img is not None:
                    results_dir = os.path.join(settings.MEDIA_ROOT, 'results')
                    os.makedirs(results_dir, exist_ok=True)
                    out_name = f'forgery_{filename}'
                    out_path = os.path.join(results_dir, out_name)
                    cv2.imwrite(out_path, forgery_img)
                    forgery_url = os.path.join(settings.MEDIA_URL, 'results', out_name)
            except Exception:
                forgery_url = None

            upload_url = os.path.join(settings.MEDIA_URL, 'uploads', filename)

            context.update({
                'double_compressed': double_comp,
                'exif': exif_data,
                'noise_forgery': noise,
                'upload_url': upload_url,
                'forgery_url': forgery_url,
                'filename': filename,
            })
            return render(request, 'forgery/result.html', context)
    else:
        form = ImageUploadForm()

    context['form'] = form
    return render(request, 'forgery/upload.html', context)


def audio_upload_view(request):
    """Upload audio and run forgery detection."""
    if not audio_forensics:
        return render(request, 'forgery/audio_result.html', {
            'error': 'Audio forensics module not available. Install dependencies (e.g. librosa, mutagen).'
        })
    if request.method == 'POST':
        form = AudioUploadForm(request.POST, request.FILES)
        if form.is_valid():
            audio = form.cleaned_data['audio']
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads', 'audio')
            os.makedirs(upload_dir, exist_ok=True)
            fs = FileSystemStorage(location=upload_dir)
            filename = fs.save(audio.name, audio)
            file_path = fs.path(filename)
            try:
                results = audio_forensics.detect_audio_forgery(file_path)
            except Exception as e:
                return render(request, 'forgery/audio_result.html', {
                    'error': str(e),
                    'filename': filename,
                })
            # Optional: spectrogram
            spectrogram_url = None
            try:
                af = audio_forensics.AudioForensics(file_path)
                results_dir = os.path.join(settings.MEDIA_ROOT, 'results')
                os.makedirs(results_dir, exist_ok=True)
                spec_name = f'spectrogram_audio_{filename}.png'
                spec_path = os.path.join(results_dir, spec_name)
                af.generate_spectrogram(spec_path)
                spectrogram_url = f'{settings.MEDIA_URL}results/{spec_name}'
            except Exception:
                pass
            upload_url = f'{settings.MEDIA_URL}uploads/audio/{filename}'
            return render(request, 'forgery/audio_result.html', {
                'results': results,
                'filename': filename,
                'upload_url': upload_url,
                'spectrogram_url': spectrogram_url,
            })
    else:
        form = AudioUploadForm()
    return render(request, 'forgery/audio_upload.html', {'form': form})


def video_upload_view(request):
    """Upload video and run forgery detection."""
    if not video_forensics:
        return render(request, 'forgery/video_result.html', {
            'error': 'Video forensics module not available. Install dependencies (e.g. opencv-python).'
        })
    if request.method == 'POST':
        form = VideoUploadForm(request.POST, request.FILES)
        if form.is_valid():
            video = form.cleaned_data['video']
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads', 'video')
            os.makedirs(upload_dir, exist_ok=True)
            fs = FileSystemStorage(location=upload_dir)
            filename = fs.save(video.name, video)
            file_path = fs.path(filename)
            try:
                results = video_forensics.detect_video_forgery(file_path)
            except Exception as e:
                return render(request, 'forgery/video_result.html', {
                    'error': str(e),
                    'filename': filename,
                })
            upload_url = f'{settings.MEDIA_URL}uploads/video/{filename}'
            return render(request, 'forgery/video_result.html', {
                'results': results,
                'filename': filename,
                'upload_url': upload_url,
            })
    else:
        form = VideoUploadForm()
    return render(request, 'forgery/video_upload.html', {'form': form})
