"""
Audio Forensics Detection Module
Implements various techniques to detect audio manipulation and forgery
"""

import numpy as np
import librosa
import librosa.display
import matplotlib.pyplot as plt
from scipy import signal
from scipy.io import wavfile
from scipy.stats import kurtosis, skew
import os
from mutagen import File as MutagenFile
from mutagen.easyid3 import EasyID3
from mutagen.wave import WAVE
from mutagen.mp3 import MP3
import warnings
warnings.filterwarnings('ignore')


class AudioForensics:
    """Class for audio forensics analysis"""
    
    def __init__(self, audio_path):
        """Initialize with audio file path"""
        self.audio_path = audio_path
        self.audio_data = None
        self.sample_rate = None
        self.load_audio()
        
    def load_audio(self):
        """Load audio file"""
        try:
            self.audio_data, self.sample_rate = librosa.load(self.audio_path, sr=None)
            return True
        except Exception as e:
            print(f"Error loading audio: {e}")
            return False
    
    def extract_metadata(self):
        """Extract and analyze audio metadata"""
        metadata = {}
        try:
            audio = MutagenFile(self.audio_path)
            if audio is not None:
                # Basic info
                if hasattr(audio.info, 'length'):
                    metadata['Duration'] = f"{audio.info.length:.2f} seconds"
                if hasattr(audio.info, 'sample_rate'):
                    metadata['Sample Rate'] = f"{audio.info.sample_rate} Hz"
                if hasattr(audio.info, 'channels'):
                    metadata['Channels'] = audio.info.channels
                if hasattr(audio.info, 'bitrate'):
                    metadata['Bitrate'] = f"{audio.info.bitrate} bps"
                
                # Tags
                if audio.tags:
                    for key, value in audio.tags.items():
                        metadata[str(key)] = str(value)
            
            # Additional analysis
            metadata['File Size'] = f"{os.path.getsize(self.audio_path) / 1024:.2f} KB"
            metadata['Audio Length'] = f"{len(self.audio_data)} samples"
            
            return metadata
        except Exception as e:
            print(f"Error extracting metadata: {e}")
            return None
    
    def detect_splicing(self, window_size=2048):
        """
        Detect audio splicing by analyzing spectral discontinuities
        Returns: (is_forged, forgery_score, suspicious_regions)
        """
        try:
            # Compute Short-Time Fourier Transform
            stft = librosa.stft(self.audio_data, n_fft=window_size)
            magnitude = np.abs(stft)
            
            # Analyze frame-to-frame spectral differences
            spectral_diff = np.diff(magnitude, axis=1)
            frame_differences = np.mean(np.abs(spectral_diff), axis=0)
            
            # Statistical analysis
            mean_diff = np.mean(frame_differences)
            std_diff = np.std(frame_differences)
            threshold = mean_diff + 3 * std_diff
            
            # Find suspicious regions with abnormal transitions
            suspicious_frames = np.where(frame_differences > threshold)[0]
            
            # Calculate forgery score
            forgery_score = (len(suspicious_frames) / len(frame_differences)) * 100
            
            # Determine if forged (threshold: more than 20% suspicious frames)
            is_forged = forgery_score > 20.0
            
            # Convert frames to time
            suspicious_times = librosa.frames_to_time(suspicious_frames, sr=self.sample_rate)
            
            return is_forged, forgery_score, suspicious_times
        except Exception as e:
            print(f"Error in splicing detection: {e}")
            return False, 0.0, []
    
    def detect_clipping(self):
        """
        Detect audio clipping which may indicate manipulation
        Returns: (has_clipping, clipping_percentage)
        """
        try:
            # Normalize audio data
            audio_normalized = self.audio_data / np.max(np.abs(self.audio_data))
            
            # Count samples near maximum (clipped)
            clipping_threshold = 0.99
            clipped_samples = np.sum(np.abs(audio_normalized) >= clipping_threshold)
            clipping_percentage = (clipped_samples / len(audio_normalized)) * 100
            
            # Threshold for significant clipping (more than 8%)
            has_clipping = clipping_percentage > 8.0
            
            return has_clipping, clipping_percentage
        except Exception as e:
            print(f"Error in clipping detection: {e}")
            return False, 0.0
    
    def analyze_noise_pattern(self, n_segments=10):
        """
        Analyze noise patterns for consistency
        Inconsistent noise may indicate forgery
        Returns: (is_inconsistent, consistency_score)
        """
        try:
            # Divide audio into segments
            segment_length = len(self.audio_data) // n_segments
            noise_features = []
            
            for i in range(n_segments):
                start = i * segment_length
                end = start + segment_length
                segment = self.audio_data[start:end]
                
                # Extract noise floor estimate
                spectral_centroids = librosa.feature.spectral_centroid(y=segment, sr=self.sample_rate)
                zero_crossing = librosa.feature.zero_crossing_rate(segment)
                
                noise_features.append({
                    'centroid_mean': np.mean(spectral_centroids),
                    'centroid_std': np.std(spectral_centroids),
                    'zcr_mean': np.mean(zero_crossing)
                })
            
            # Calculate consistency
            centroid_means = [f['centroid_mean'] for f in noise_features]
            centroid_std = np.std(centroid_means)
            centroid_mean = np.mean(centroid_means)
            
            # Coefficient of variation
            consistency_score = (centroid_std / centroid_mean) * 100 if centroid_mean > 0 else 0
            
            # High variation indicates inconsistency (more than 60%)
            is_inconsistent = consistency_score > 60.0
            
            return is_inconsistent, consistency_score
        except Exception as e:
            print(f"Error in noise pattern analysis: {e}")
            return False, 0.0
    
    def detect_resampling(self):
        """
        Detect if audio has been resampled (potential manipulation)
        Returns: (is_resampled, confidence)
        """
        try:
            # Compute power spectral density
            frequencies, psd = signal.periodogram(self.audio_data, self.sample_rate)
            
            # Check for frequency cutoffs typical of resampling
            # Original audio should have content up to Nyquist frequency
            nyquist = self.sample_rate / 2
            high_freq_threshold = nyquist * 0.85
            
            # Find index of threshold frequency
            threshold_idx = np.argmin(np.abs(frequencies - high_freq_threshold))
            
            # Analyze high frequency content
            high_freq_power = np.mean(psd[threshold_idx:])
            total_power = np.mean(psd[:threshold_idx]) if threshold_idx > 0 else np.mean(psd)
            
            high_freq_ratio = high_freq_power / total_power if total_power > 0 else 0
            
            # Look for sharp cutoff (brick-wall filter effect from resampling)
            # Calculate spectral rolloff
            cumsum_psd = np.cumsum(psd)
            rolloff_point = 0.95 * cumsum_psd[-1]
            rolloff_idx = np.where(cumsum_psd >= rolloff_point)[0]
            if len(rolloff_idx) > 0:
                rolloff_freq = frequencies[rolloff_idx[0]]
                rolloff_ratio = rolloff_freq / nyquist
            else:
                rolloff_ratio = 1.0
            
            # Resampling indicators:
            # 1. Very low high-freq ratio AND
            # 2. Sharp cutoff (rolloff much less than Nyquist)
            has_low_hf = high_freq_ratio < 0.0001
            has_sharp_cutoff = rolloff_ratio < 0.7
            
            is_resampled = has_low_hf and has_sharp_cutoff
            
            # Calculate confidence
            if is_resampled:
                confidence = min(((1 - high_freq_ratio) * (1 - rolloff_ratio)) * 100, 100)
            else:
                confidence = 0
            
            return is_resampled, confidence
        except Exception as e:
            print(f"Error in resampling detection: {e}")
            return False, 0.0
    
    def generate_spectrogram(self, output_path='spectrogram.png'):
        """Generate and save spectrogram visualization"""
        try:
            plt.figure(figsize=(12, 6))
            
            # Compute spectrogram
            D = librosa.amplitude_to_db(np.abs(librosa.stft(self.audio_data)), ref=np.max)
            
            # Display spectrogram
            librosa.display.specshow(D, sr=self.sample_rate, x_axis='time', y_axis='hz')
            plt.colorbar(format='%+2.0f dB')
            plt.title('Spectrogram Analysis')
            plt.tight_layout()
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.close()
            
            return output_path
        except Exception as e:
            print(f"Error generating spectrogram: {e}")
            return None
    
    def analyze_compression(self):
        """
        Analyze audio compression artifacts
        Returns: (has_artifacts, artifact_score)
        """
        try:
            # Extract mel-frequency cepstral coefficients
            mfccs = librosa.feature.mfcc(y=self.audio_data, sr=self.sample_rate, n_mfcc=13)
            
            # Analyze MFCC statistics
            mfcc_var = np.var(mfccs, axis=1)
            mfcc_kurtosis = kurtosis(mfccs, axis=1)
            
            # High kurtosis and low variance can indicate compression artifacts
            avg_kurtosis = np.mean(np.abs(mfcc_kurtosis))
            avg_variance = np.mean(mfcc_var)
            
            # Compression artifact score
            artifact_score = avg_kurtosis / (avg_variance + 1e-6)
            
            # Threshold for detecting significant artifacts (reduced sensitivity)
            has_artifacts = artifact_score > 50.0
            
            return has_artifacts, artifact_score
        except Exception as e:
            print(f"Error in compression analysis: {e}")
            return False, 0.0
    
    def comprehensive_analysis(self):
        """
        Run all detection methods and provide comprehensive report
        Returns: Dictionary with all analysis results
        """
        results = {
            'file_path': self.audio_path,
            'file_name': os.path.basename(self.audio_path),
            'metadata': self.extract_metadata(),
            'splicing_detection': None,
            'clipping_detection': None,
            'noise_analysis': None,
            'resampling_detection': None,
            'compression_analysis': None,
            'overall_verdict': 'ANALYZING'
        }
        
        # Run all tests
        is_spliced, splice_score, splice_times = self.detect_splicing()
        results['splicing_detection'] = {
            'is_forged': is_spliced,
            'score': splice_score,
            'suspicious_times': splice_times.tolist() if len(splice_times) > 0 else []
        }
        
        has_clipping, clip_percent = self.detect_clipping()
        results['clipping_detection'] = {
            'has_clipping': has_clipping,
            'percentage': clip_percent
        }
        
        is_inconsistent, noise_score = self.analyze_noise_pattern()
        results['noise_analysis'] = {
            'is_inconsistent': is_inconsistent,
            'consistency_score': noise_score
        }
        
        is_resampled, resample_conf = self.detect_resampling()
        results['resampling_detection'] = {
            'is_resampled': is_resampled,
            'confidence': resample_conf
        }
        
        has_comp_artifacts, comp_score = self.analyze_compression()
        results['compression_analysis'] = {
            'has_artifacts': has_comp_artifacts,
            'artifact_score': comp_score
        }
        
        # Overall verdict (need at least 3 indicators for "LIKELY FORGED")
        forgery_indicators = sum([
            is_spliced,
            has_clipping,
            is_inconsistent,
            is_resampled
        ])
        
        if forgery_indicators >= 3:
            results['overall_verdict'] = 'LIKELY FORGED'
        elif forgery_indicators == 2:
            results['overall_verdict'] = 'SUSPICIOUS'
        else:
            results['overall_verdict'] = 'LIKELY AUTHENTIC'
        
        return results


def detect_audio_forgery(audio_path):
    """
    Main function to detect audio forgery
    Returns comprehensive analysis results
    """
    forensics = AudioForensics(audio_path)
    results = forensics.comprehensive_analysis()
    return results


if __name__ == "__main__":
    # Test the module
    import sys
    if len(sys.argv) > 1:
        audio_file = sys.argv[1]
        results = detect_audio_forgery(audio_file)
        
        print("\n" + "="*60)
        print("AUDIO FORENSICS ANALYSIS REPORT")
        print("="*60)
        print(f"\nFile: {results['file_name']}")
        print(f"\nOverall Verdict: {results['overall_verdict']}")
        print("\n" + "-"*60)
        
        if results['metadata']:
            print("\nMETADATA:")
            for key, value in results['metadata'].items():
                print(f"  {key}: {value}")
        
        print("\n" + "-"*60)
        print("\nDETECTION RESULTS:")
        
        splice = results['splicing_detection']
        print(f"\n1. Splicing Detection:")
        print(f"   Status: {'DETECTED' if splice['is_forged'] else 'NOT DETECTED'}")
        print(f"   Score: {splice['score']:.2f}%")
        
        clip = results['clipping_detection']
        print(f"\n2. Clipping Detection:")
        print(f"   Status: {'DETECTED' if clip['has_clipping'] else 'NOT DETECTED'}")
        print(f"   Percentage: {clip['percentage']:.2f}%")
        
        noise = results['noise_analysis']
        print(f"\n3. Noise Pattern Analysis:")
        print(f"   Status: {'INCONSISTENT' if noise['is_inconsistent'] else 'CONSISTENT'}")
        print(f"   Score: {noise['consistency_score']:.2f}")
        
        resample = results['resampling_detection']
        print(f"\n4. Resampling Detection:")
        print(f"   Status: {'DETECTED' if resample['is_resampled'] else 'NOT DETECTED'}")
        print(f"   Confidence: {resample['confidence']:.2f}%")
        
        comp = results['compression_analysis']
        print(f"\n5. Compression Artifacts:")
        print(f"   Status: {'DETECTED' if comp['has_artifacts'] else 'NOT DETECTED'}")
        print(f"   Score: {comp['artifact_score']:.2f}")
        
        print("\n" + "="*60)
    else:
        print("Usage: python audio_forensics.py <audio_file>")
