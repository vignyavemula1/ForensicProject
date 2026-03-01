from django import forms

class ImageUploadForm(forms.Form):
    image = forms.ImageField(label='Select image')

class AudioUploadForm(forms.Form):
    audio = forms.FileField(
        label='Select audio',
        help_text='WAV, MP3, or other supported format'
    )

class VideoUploadForm(forms.Form):
    video = forms.FileField(
        label='Select video',
        help_text='MP4, AVI, or other supported format'
    )
