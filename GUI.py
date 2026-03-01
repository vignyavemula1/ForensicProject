from importlib.resources import path
from tkinter import *
from tkinter import filedialog, ttk, messagebox
from PIL import ImageTk, Image, ExifTags, ImageChops
from optparse import OptionParser
from datetime import datetime
from matplotlib import image
from prettytable import PrettyTable
import numpy as np
import random
import sys
import cv2
import re
import os

from pyparsing import Opt

from ForgeryDetection import Detect
import double_jpeg_compression
import noise_variance
import copy_move_cfa
import audio_forensics
import video_forensics


# Global variables
IMG_WIDTH = 400
IMG_HEIGHT = 400
uploaded_image = None
uploaded_audio = None
uploaded_video = None
current_media_type = "image"  # Can be "image", "audio", or "video"

# copy-move parameters
cmd = OptionParser("usage: %prog image_file [options]")
cmd.add_option('', '--imauto',
               help='Automatically search identical regions. (default: %default)', default=1)
cmd.add_option('', '--imblev',
               help='Blur level for degrading image details. (default: %default)', default=8)
cmd.add_option('', '--impalred',
               help='Image palette reduction factor. (default: %default)', default=15)
cmd.add_option(
    '', '--rgsim', help='Region similarity threshold. (default: %default)', default=5)
cmd.add_option(
    '', '--rgsize', help='Region size threshold. (default: %default)', default=1.5)
cmd.add_option(
    '', '--blsim', help='Block similarity threshold. (default: %default)', default=200)
cmd.add_option('', '--blcoldev',
               help='Block color deviation threshold. (default: %default)', default=0.2)
cmd.add_option(
    '', '--blint', help='Block intersection threshold. (default: %default)', default=0.2)
opt, args = cmd.parse_args()
# if not args:
#     cmd.print_help()
#     sys.exit()


def getImage(path, width, height):
    """
    Function to return an image as a PhotoImage object
    :param path: A string representing the path of the image file
    :param width: The width of the image to resize to
    :param height: The height of the image to resize to
    :return: The image represented as a PhotoImage object
    """
    img = Image.open(path)
    img = img.resize((width, height), Image.Resampling.LANCZOS)

    return ImageTk.PhotoImage(img)


def browseFile():
    """
    Function to open a browser for users to select an image
    :return: None
    """
    # Only accept jpg and png files
    filename = filedialog.askopenfilename(title="Select an image", filetypes=[("image", ".jpeg"),("image", ".png"),("image", ".jpg")])

    # No file selected (User closes the browsing window)
    if filename == "":
        return

    global uploaded_image, current_media_type

    uploaded_image = filename
    current_media_type = "image"

    progressBar['value'] = 0   # Reset the progress bar
    # Show only filename, not full path
    display_name = os.path.basename(filename)
    if len(display_name) > 50:
        display_name = display_name[:47] + "..."
    fileLabel.configure(text=display_name)     # Set the filename in the fileLabel

    # Display the input image in imagePanel
    img = getImage(filename, IMG_WIDTH, IMG_HEIGHT)
    imagePanel.configure(image=img)
    imagePanel.image = img

    # Display blank image in resultPanel
    blank_img = getImage("images/output.png", IMG_WIDTH, IMG_HEIGHT)
    resultPanel.configure(image=blank_img)
    resultPanel.image = blank_img

    # Reset the resultLabel
    resultLabel.configure(text="READY TO SCAN", foreground="green")


def browseAudioFile():
    """
    Function to open a browser for users to select an audio file
    :return: None
    """
    filename = filedialog.askopenfilename(
        title="Select an audio file", 
        filetypes=[("Audio", ".wav"), ("Audio", ".mp3"), ("Audio", ".flac"), ("Audio", ".ogg")]
    )

    if filename == "":
        return

    global uploaded_audio, current_media_type

    uploaded_audio = filename
    current_media_type = "audio"

    progressBar['value'] = 0
    # Show only filename, not full path
    display_name = os.path.basename(filename)
    if len(display_name) > 50:
        display_name = display_name[:47] + "..."
    fileLabel.configure(text=display_name)

    # Display audio icon
    audio_img = getImage("images/input.png", IMG_WIDTH, IMG_HEIGHT)
    imagePanel.configure(image=audio_img)
    imagePanel.image = audio_img

    # Display blank image in resultPanel
    blank_img = getImage("images/output.png", IMG_WIDTH, IMG_HEIGHT)
    resultPanel.configure(image=blank_img)
    resultPanel.image = blank_img

    resultLabel.configure(text="AUDIO FILE LOADED - READY TO ANALYZE", foreground="blue")


def browseVideoFile():
    """
    Function to open a browser for users to select a video file
    :return: None
    """
    filename = filedialog.askopenfilename(
        title="Select a video file", 
        filetypes=[("Video", ".mp4"), ("Video", ".avi"), ("Video", ".mov"), ("Video", ".mkv")]
    )

    if filename == "":
        return

    global uploaded_video, current_media_type

    uploaded_video = filename
    current_media_type = "video"

    progressBar['value'] = 0
    # Show only filename, not full path
    display_name = os.path.basename(filename)
    if len(display_name) > 50:
        display_name = display_name[:47] + "..."
    fileLabel.configure(text=display_name)

    # Try to display first frame
    try:
        cap = cv2.VideoCapture(filename)
        ret, frame = cap.read()
        if ret:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_pil = Image.fromarray(frame_rgb)
            frame_pil = frame_pil.resize((IMG_WIDTH, IMG_HEIGHT), Image.Resampling.LANCZOS)
            frame_photo = ImageTk.PhotoImage(frame_pil)
            imagePanel.configure(image=frame_photo)
            imagePanel.image = frame_photo
        cap.release()
    except:
        video_img = getImage("images/input.png", IMG_WIDTH, IMG_HEIGHT)
        imagePanel.configure(image=video_img)
        imagePanel.image = video_img

    # Display blank image in resultPanel
    blank_img = getImage("images/output.png", IMG_WIDTH, IMG_HEIGHT)
    resultPanel.configure(image=blank_img)
    resultPanel.image = blank_img

    resultLabel.configure(text="VIDEO FILE LOADED - READY TO ANALYZE", foreground="purple")


def copy_move_forgery():
    # Retrieve the path of the image file
    path = uploaded_image
    eps = 60
    min_samples = 2

    # User has not selected an input image
    if path is None:
        # Show error message
        messagebox.showerror('Error', "Please select image")
        return

    detect = Detect(path)
    key_points, descriptors = detect.siftDetector()
    forgery = detect.locateForgery(eps, min_samples)

    # Set the progress bar to 100%
    progressBar['value'] = 100

    if forgery is None:
        # Retrieve the thumbs up image and display in resultPanel
        img = getImage("images/no_copy_move.png", IMG_WIDTH, IMG_HEIGHT)
        resultPanel.configure(image=img)
        resultPanel.image = img

        # Display results in resultLabel
        resultLabel.configure(text="ORIGINAL IMAGE", foreground="green")
    else:
        # Retrieve the output image and display in resultPanel
        img = getImage("images/copy_move.png", IMG_WIDTH, IMG_HEIGHT)
        resultPanel.configure(image=img)
        resultPanel.image = img

        # Display results in resultLabel
        resultLabel.configure(text="Image Forged", foreground="red")
        # cv2.imshow('Original image', detect.image)
        cv2.imshow('Forgery', forgery)
        wait_time = 1000
        while(cv2.getWindowProperty('Forgery', 0) >= 0) or (cv2.getWindowProperty('Original image', 0) >= 0):
            keyCode = cv2.waitKey(wait_time)
            if (keyCode) == ord('q') or keyCode == ord('Q'):
                cv2.destroyAllWindows()
                break
            elif keyCode == ord('s') or keyCode == ord('S'):
                name = re.findall(r'(.+?)(\.[^.]*$|$)', path)
                date = datetime.today().strftime('%Y_%m_%d_%H_%M_%S')
                new_file_name = name[0][0]+'_'+str(eps)+'_'+str(min_samples)
                new_file_name = new_file_name+'_'+date+name[0][1]

                vaue = cv2.imwrite(new_file_name, forgery)
                print('Image Saved as....', new_file_name)


def metadata_analysis():
    # Retrieve the path of the image file
    path = uploaded_image
    # User has not selected an input image
    if path is None:
        # Show error message
        messagebox.showerror('Error', "Please select image")
        return

    img = Image.open(path)
    img_exif = img.getexif()

    # Set the progress bar to 100%
    progressBar['value'] = 100

    if img_exif is None:
        # print('Sorry, image has no exif data.')
        # Retrieve the output image and display in resultPanel
        img = getImage("images/no_metadata.png", IMG_WIDTH, IMG_HEIGHT)
        resultPanel.configure(image=img)
        resultPanel.image = img

        # Display results in resultLabel
        resultLabel.configure(text="NO Data Found", foreground="red")
    else:
        # Retrieve the thumbs up image and display in resultPanel
        img = getImage("images/metadata.png", IMG_WIDTH, IMG_HEIGHT)
        resultPanel.configure(image=img)
        resultPanel.image = img

        # Display results in resultLabel
        resultLabel.configure(text="Metadata Details", foreground="green")

        # print('image has exif data.')
        with open('Metadata_analysis.txt', 'w') as f:
            for key, val in img_exif.items():
                if key in ExifTags.TAGS:
                    # print(f'{ExifTags.TAGS[key]} : {val}')
                        f.write(f'{ExifTags.TAGS[key]} : {val}\n')
        os.startfile('Metadata_analysis.txt')



def noise_variance_inconsistency():
    # Retrieve the path of the image file
    path = uploaded_image
    # User has not selected an input image
    if path is None:
        # Show error message
        messagebox.showerror('Error', "Please select image")
        return

    noise_forgery = noise_variance.detect(path)

    # Set the progress bar to 100%
    progressBar['value'] = 100

    if(noise_forgery):
        # print('\nNoise variance inconsistency detected')
        # Retrieve the output image and display in resultPanel
        img = getImage("images/varience.png", IMG_WIDTH, IMG_HEIGHT)
        resultPanel.configure(image=img)
        resultPanel.image = img

        # Display results in resultLabel
        resultLabel.configure(text="Noise variance", foreground="red")
    
    else:
        # Retrieve the thumbs up image and display in resultPanel
        img = getImage("images/no_varience.png", IMG_WIDTH, IMG_HEIGHT)
        resultPanel.configure(image=img)
        resultPanel.image = img

        # Display results in resultLabel
        resultLabel.configure(text="No Noise variance", foreground="green")

def cfa_artifact():
    # Retrieve the path of the image file
    path = uploaded_image
    # User has not selected an input image
    if path is None:
        # Show error message
        messagebox.showerror('Error', "Please select image")
        return

    identical_regions_cfa = copy_move_cfa.detect(path, opt, args)
    # identical_regions_cfa = copy_move_cfa.detect(path, opt, args)


    # Set the progress bar to 100%
    progressBar['value'] = 100

    # print('\n' + str(identical_regions_cfa), 'CFA artifacts detected')

    if(identical_regions_cfa):
        # Retrieve the output image and display in resultPanel
        img = getImage("images/cfa.png", IMG_WIDTH, IMG_HEIGHT)
        resultPanel.configure(image=img)
        resultPanel.image = img

        # Display results in resultLabel
        resultLabel.configure(text=f"{str(identical_regions_cfa)}, CFA artifacts detected", foreground="red")

    else:
        # print('\nSingle compressed')
        # Retrieve the thumbs up image and display in resultPanel
        img = getImage("images/no_cfa.png", IMG_WIDTH, IMG_HEIGHT)
        resultPanel.configure(image=img)
        resultPanel.image = img

        # Display results in resultLabel
        resultLabel.configure(text="NO-CFA artifacts detected", foreground="green")


def ela_analysis():
    # Retrieve the path of the image file
    path = uploaded_image
    TEMP = 'temp.jpg'
    SCALE = 10

    # User has not selected an input image
    if path is None:
        # Show error message
        messagebox.showerror('Error', "Please select image")
        return

    original = Image.open(path)
    original.save(TEMP, quality=90)
    temporary = Image.open(TEMP)

    diff = ImageChops.difference(original, temporary)
    d = diff.load()
    WIDTH, HEIGHT = diff.size
    for x in range(WIDTH):
        for y in range(HEIGHT):
            d[x, y] = tuple(k * SCALE for k in d[x, y])

    # Set the progress bar to 100%
    progressBar['value'] = 100
    diff.show()



def jpeg_Compression():

    # Retrieve the path of the image file
    path = uploaded_image
    # User has not selected an input image
    if path is None:
        # Show error message
        messagebox.showerror('Error', "Please select image")
        return

    double_compressed = double_jpeg_compression.detect(path)

    # Set the progress bar to 100%
    progressBar['value'] = 100

    if(double_compressed):
        # print('\nDouble compression detected')
        # Retrieve the output image and display in resultPanel
        img = getImage("images/double_compression.png", IMG_WIDTH, IMG_HEIGHT)
        resultPanel.configure(image=img)
        resultPanel.image = img

        # Display results in resultLabel
        resultLabel.configure(text="Double compression", foreground="red")

    else:
        # print('\nSingle compressed')
        # Retrieve the thumbs up image and display in resultPanel
        img = getImage("images/single_compression.png", IMG_WIDTH, IMG_HEIGHT)
        resultPanel.configure(image=img)
        resultPanel.image = img

        # Display results in resultLabel
        resultLabel.configure(text="Single compression", foreground="green")

def image_decode():
    # Retrieve the path of the image file
    path = uploaded_image
    # User has not selected an input image
    if path is None:
        # Show error message
        messagebox.showerror('Error', "Please select image")
        return
    
    # Encrypted image
    img = cv2.imread(path) 
    width = img.shape[0]
    height = img.shape[1]
      
    # img1 and img2 are two blank images
    img1 = np.zeros((width, height, 3), np.uint8)
    img2 = np.zeros((width, height, 3), np.uint8)
      
    for i in range(width):
        for j in range(height):
            for l in range(3):
                v1 = format(img[i][j][l], '08b')
                v2 = v1[:4] + chr(random.randint(0, 1)+48) * 4
                v3 = v1[4:] + chr(random.randint(0, 1)+48) * 4
                  
                # Appending data to img1 and img2
                img1[i][j][l]= int(v2, 2)
                img2[i][j][l]= int(v3, 2)
    
    # Set the progress bar to 100%
    progressBar['value'] = 100

    # These are two images produced from
    # the encrypted image
    # cv2.imwrite('pic2_re.png', img1)
    cv2.imwrite('output.png', img2)
    # Image.show(img2)
    # creating a object
    im = Image.open('output.png')
    im.show()

def string_analysis():
    # Retrieve the path of the image file
    path = uploaded_image
    # User has not selected an input image
    if path is None:
        # Show error message
        messagebox.showerror('Error', "Please select image")
        return
    
    x=PrettyTable()
    x.field_names = ["Bytes", "8-bit", "string"]
    # x.border = False
    with open(path, "rb") as f:
            n = 0
            b = f.read(16)

            while b:
                s1 = " ".join([f"{i:02x}" for i in b])  # hex string
                # insert extra space between groups of 8 hex values
                s1 = s1[0:23] + " " + s1[23:]

                # ascii string; chained comparison
                s2 = "".join([chr(i) if 32 <= i <= 127 else "." for i in b])

                # print(f"{n * 16:08x}  {s1:<48}  |{s2}|")
                x.add_row([f"{n * 16:08x}",f"{s1:<48}",f"{s2}"])

                n += 1
                b = f.read(16)
            
            # Set the progress bar to 100%
            progressBar['value'] = 100

            with open('hex_viewer.txt', 'w') as w:
                w.write(str(x))
                # w.write(f"{os.path.getsize(path):08x}")
            os.startfile('hex_viewer.txt')
            # print(f"{os.path.getsize(filename):08x}")


def audio_analysis():
    """Comprehensive audio forensics analysis"""
    path = uploaded_audio
    
    if path is None:
        messagebox.showerror('Error', "Please select an audio file")
        return
    
    try:
        progressBar['value'] = 25
        
        # Run audio forensics
        results = audio_forensics.detect_audio_forgery(path)
        
        progressBar['value'] = 100
        
        # Create results text file
        with open('Audio_Analysis.txt', 'w') as f:
            f.write("="*60 + "\n")
            f.write("AUDIO FORENSICS ANALYSIS REPORT\n")
            f.write("="*60 + "\n\n")
            f.write(f"File: {results['file_name']}\n")
            f.write(f"Overall Verdict: {results['overall_verdict']}\n\n")
            
            if results['metadata']:
                f.write("-"*60 + "\n")
                f.write("METADATA:\n")
                for key, value in results['metadata'].items():
                    f.write(f"  {key}: {value}\n")
            
            f.write("\n" + "-"*60 + "\n")
            f.write("DETECTION RESULTS:\n\n")
            
            splice = results['splicing_detection']
            f.write("1. Splicing Detection:\n")
            f.write(f"   Status: {'DETECTED' if splice['is_forged'] else 'NOT DETECTED'}\n")
            f.write(f"   Score: {splice['score']:.2f}%\n\n")
            
            clip = results['clipping_detection']
            f.write("2. Clipping Detection:\n")
            f.write(f"   Status: {'DETECTED' if clip['has_clipping'] else 'NOT DETECTED'}\n")
            f.write(f"   Percentage: {clip['percentage']:.2f}%\n\n")
            
            noise = results['noise_analysis']
            f.write("3. Noise Pattern Analysis:\n")
            f.write(f"   Status: {'INCONSISTENT' if noise['is_inconsistent'] else 'CONSISTENT'}\n")
            f.write(f"   Score: {noise['consistency_score']:.2f}\n\n")
            
            resample = results['resampling_detection']
            f.write("4. Resampling Detection:\n")
            f.write(f"   Status: {'DETECTED' if resample['is_resampled'] else 'NOT DETECTED'}\n")
            f.write(f"   Confidence: {resample['confidence']:.2f}%\n\n")
            
            comp = results['compression_analysis']
            f.write("5. Compression Artifacts:\n")
            f.write(f"   Status: {'DETECTED' if comp['has_artifacts'] else 'NOT DETECTED'}\n")
            f.write(f"   Score: {comp['artifact_score']:.2f}\n")
            
            f.write("\n" + "="*60 + "\n")
        
        # Display results
        if results['overall_verdict'] == 'LIKELY FORGED':
            img = getImage("images/varience.png", IMG_WIDTH, IMG_HEIGHT)
            resultPanel.configure(image=img)
            resultPanel.image = img
            resultLabel.configure(text="AUDIO LIKELY FORGED", foreground="red")
        elif results['overall_verdict'] == 'SUSPICIOUS':
            img = getImage("images/cfa.png", IMG_WIDTH, IMG_HEIGHT)
            resultPanel.configure(image=img)
            resultPanel.image = img
            resultLabel.configure(text="AUDIO SUSPICIOUS", foreground="orange")
        else:
            img = getImage("images/no_copy_move.png", IMG_WIDTH, IMG_HEIGHT)
            resultPanel.configure(image=img)
            resultPanel.image = img
            resultLabel.configure(text="AUDIO LIKELY AUTHENTIC", foreground="green")
        
        os.startfile('Audio_Analysis.txt')
        
    except Exception as e:
        messagebox.showerror('Error', f"Audio analysis failed: {str(e)}")
        progressBar['value'] = 0


def video_analysis():
    """Comprehensive video forensics analysis"""
    path = uploaded_video
    
    if path is None:
        messagebox.showerror('Error', "Please select a video file")
        return
    
    try:
        progressBar['value'] = 25
        
        # Run video forensics
        results = video_forensics.detect_video_forgery(path)
        
        progressBar['value'] = 100
        
        # Create results text file
        with open('Video_Analysis.txt', 'w') as f:
            f.write("="*60 + "\n")
            f.write("VIDEO FORENSICS ANALYSIS REPORT\n")
            f.write("="*60 + "\n\n")
            f.write(f"File: {results['file_name']}\n")
            f.write(f"Overall Verdict: {results['overall_verdict']}\n\n")
            
            if results['metadata']:
                f.write("-"*60 + "\n")
                f.write("METADATA:\n")
                for key, value in results['metadata'].items():
                    f.write(f"  {key}: {value}\n")
            
            f.write("\n" + "-"*60 + "\n")
            f.write("DETECTION RESULTS:\n\n")
            
            dup = results['frame_duplication']
            f.write("1. Frame Duplication:\n")
            f.write(f"   Status: {'DETECTED' if dup['has_duplicates'] else 'NOT DETECTED'}\n")
            f.write(f"   Percentage: {dup['percentage']:.2f}%\n\n")
            
            inter = results['inter_frame_forgery']
            f.write("2. Inter-Frame Forgery:\n")
            f.write(f"   Status: {'DETECTED' if inter['is_forged'] else 'NOT DETECTED'}\n")
            f.write(f"   Score: {inter['score']:.2f}%\n\n")
            
            cm = results['copy_move_detection']
            f.write("3. Copy-Move Detection:\n")
            f.write(f"   Status: {'DETECTED' if cm['has_forgery'] else 'NOT DETECTED'}\n")
            f.write(f"   Percentage: {cm['percentage']:.2f}%\n\n")
            
            comp = results['double_compression']
            f.write("4. Double Compression:\n")
            f.write(f"   Status: {'DETECTED' if comp['is_detected'] else 'NOT DETECTED'}\n")
            f.write(f"   Confidence: {comp['confidence']:.2f}%\n\n")
            
            noise = results['noise_consistency']
            f.write("5. Noise Consistency:\n")
            f.write(f"   Status: {'INCONSISTENT' if noise['is_inconsistent'] else 'CONSISTENT'}\n")
            f.write(f"   Score: {noise['score']:.2f}\n\n")
            
            fr = results['frame_rate_anomalies']
            f.write("6. Frame Rate Anomalies:\n")
            f.write(f"   Status: {'DETECTED' if fr['has_anomalies'] else 'NOT DETECTED'}\n")
            f.write(f"   Score: {fr['score']:.2f}%\n")
            
            f.write("\n" + "="*60 + "\n")
        
        # Display results
        if results['overall_verdict'] == 'LIKELY FORGED':
            img = getImage("images/varience.png", IMG_WIDTH, IMG_HEIGHT)
            resultPanel.configure(image=img)
            resultPanel.image = img
            resultLabel.configure(text="VIDEO LIKELY FORGED", foreground="red")
        elif results['overall_verdict'] == 'SUSPICIOUS':
            img = getImage("images/cfa.png", IMG_WIDTH, IMG_HEIGHT)
            resultPanel.configure(image=img)
            resultPanel.image = img
            resultLabel.configure(text="VIDEO SUSPICIOUS", foreground="orange")
        else:
            img = getImage("images/no_copy_move.png", IMG_WIDTH, IMG_HEIGHT)
            resultPanel.configure(image=img)
            resultPanel.image = img
            resultLabel.configure(text="VIDEO LIKELY AUTHENTIC", foreground="green")
        
        os.startfile('Video_Analysis.txt')
        
    except Exception as e:
        messagebox.showerror('Error', f"Video analysis failed: {str(e)}")
        progressBar['value'] = 0


# Initialize the app window
root = Tk()
root.title("Multimedia Forensics Detection System")
root.iconbitmap('images/favicon.ico')

# Ensure the program closes when window is closed
root.protocol("WM_DELETE_WINDOW", root.quit)

# Set window size and make it resizable
root.geometry("1400x900")
root.resizable(True, True)

# Configure grid weights to prevent expansion
root.grid_columnconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=1)
root.grid_columnconfigure(2, weight=1)

# Add the GUI into the Tkinter window
# GUI(parent=root)

# Label for the results of scan
resultLabel = Label(text="MULTIMEDIA FORENSICS DETECTOR", font=("Courier", 32, "bold"))
resultLabel.grid(row=0, column=0, columnspan=3, pady=10)
# resultLabel.grid(row=0, column=1, columnspan=2)

# Get the blank image
input_img = getImage("images/input.png", IMG_WIDTH, IMG_HEIGHT)
middle_img = getImage("images/middle.png", IMG_WIDTH, IMG_HEIGHT)
output_img = getImage("images/output.png", IMG_WIDTH, IMG_HEIGHT)

# Displays the input image
imagePanel = Label(image=input_img)
imagePanel.image = input_img
imagePanel.grid(row=1, column=0, padx=5)

# Label to display the middle image
middle = Label(image=middle_img)
middle.image = middle_img
middle.grid(row=1, column=1, padx=5)

# Label to display the output image
resultPanel = Label(image=output_img)
resultPanel.image = output_img
resultPanel.grid(row=1, column=2, padx=5)

# Label to display the path of the input image
fileLabel = Label(text="No file selected", fg="grey", font=("Times", 12), wraplength=500, justify="center")
fileLabel.grid(row=2, column=0, columnspan=3, pady=5)
# fileLabel.grid(row=2, column=0, columnspan=2)


# Progress bar
progressBar = ttk.Progressbar(length=500)
progressBar.grid(row=3, column=0, columnspan=3, pady=5)
# progressBar.grid(row=3, column=0, columnspan=2)


# Configure the style of the buttons
s = ttk.Style()
s.configure('my.TButton', font=('Times', 12), width=20)
s.configure('audio.TButton', font=('Times', 12), foreground='blue', width=20)
s.configure('video.TButton', font=('Times', 12), foreground='purple', width=20)

# FILE UPLOAD BUTTONS - Row 4
# Button to upload images
uploadButton = ttk.Button(
    text="Upload Image", style="my.TButton", command=browseFile)
uploadButton.grid(row=4, column=0, sticky="nsew", pady=5, padx=5)

# Button to upload audio
uploadAudioButton = ttk.Button(
    text="Upload Audio", style="audio.TButton", command=browseAudioFile)
uploadAudioButton.grid(row=4, column=1, sticky="nsew", pady=5, padx=5)

# Button to upload video
uploadVideoButton = ttk.Button(
    text="Upload Video", style="video.TButton", command=browseVideoFile)
uploadVideoButton.grid(row=4, column=2, sticky="nsew", pady=5, padx=5)

# IMAGE ANALYSIS BUTTONS - Row 5
# Button to run the Compression detection algorithm
compression = ttk.Button(text="Compression-Detection",
                         style="my.TButton", command=jpeg_Compression)
compression.grid(row=5, column=0, pady=5, padx=5, sticky="ew")

# Button to run the Metadata-Analysis detection algorithm
metadata = ttk.Button(text="Metadata-Analysis",
                      style="my.TButton", command=metadata_analysis)
metadata.grid(row=5, column=1, pady=5, padx=5, sticky="ew")

# Button to run the CFA-artifact detection algorithm
artifact = ttk.Button(text="CFA-artifact", style="my.TButton", command=cfa_artifact)
artifact.grid(row=5, column=2, pady=5, padx=5, sticky="ew")

# IMAGE ANALYSIS BUTTONS - Row 6
# Button to run the noise variance inconsistency detection algorithm
noise = ttk.Button(text="Noise-Inconsistency",
                   style="my.TButton", command=noise_variance_inconsistency)
noise.grid(row=6, column=0, pady=5, padx=5, sticky="ew")

# Button to run the Copy-Move  detection algorithm
copy_move = ttk.Button(text="Copy-Move", style="my.TButton", command=copy_move_forgery)
copy_move.grid(row=6, column=1, pady=5, padx=5, sticky="ew")

# Button to run the Error-Level Analysis algorithm
ela = ttk.Button(text="Error-Level Analysis", style="my.TButton", command=ela_analysis)
ela.grid(row=6, column=2, pady=5, padx=5, sticky="ew")

# IMAGE ANALYSIS BUTTONS - Row 7
# Button to run the Image pixel Analysis algorithm
image_stegnography = ttk.Button(text="Image-Extraction", style="my.TButton", command=image_decode)
image_stegnography.grid(row=7, column=0, pady=5, padx=5, sticky="ew")

# Button to run the String Extraction Analysis algorithm
String_analysis = ttk.Button(text="String Extraction", style="my.TButton", command=string_analysis)
String_analysis.grid(row=7, column=1, pady=5, padx=5, sticky="ew")

# MULTIMEDIA ANALYSIS BUTTONS - Row 8
# Button to run audio forensics
audioButton = ttk.Button(text="Audio Forensics", style="audio.TButton", command=audio_analysis)
audioButton.grid(row=8, column=0, columnspan=1, pady=10, padx=5, sticky="ew")

# Button to run video forensics
videoButton = ttk.Button(text="Video Forensics", style="video.TButton", command=video_analysis)
videoButton.grid(row=8, column=1, columnspan=2, pady=10, padx=5, sticky="ew")

# Button to exit the program
style = ttk.Style()
style.configure('W.TButton', font = ('calibri', 10, 'bold'),foreground = 'red')

quitButton = ttk.Button(text="Exit Program", style = 'W.TButton', command=root.quit)
quitButton.grid(row=9, column=0, columnspan=3, pady=10, sticky="e", padx=10)

# Open the GUI
root.mainloop()
