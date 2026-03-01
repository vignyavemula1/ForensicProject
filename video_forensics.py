"""
Video Forensics Detection Module
Implements various techniques to detect video manipulation and forgery
"""

import cv2
import numpy as np
from sklearn.cluster import DBSCAN
import os
from datetime import datetime
import matplotlib.pyplot as plt
from scipy import fftpack
from scipy.stats import entropy
import json
import subprocess
import warnings
warnings.filterwarnings('ignore')


class VideoForensics:
    """Class for video forensics analysis"""
    
    def __init__(self, video_path):
        """Initialize with video file path"""
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.duration = self.frame_count / self.fps if self.fps > 0 else 0
        
    def extract_metadata(self):
        """Extract video metadata"""
        metadata = {
            'File Path': self.video_path,
            'File Name': os.path.basename(self.video_path),
            'File Size': f"{os.path.getsize(self.video_path) / (1024*1024):.2f} MB",
            'Resolution': f"{self.width}x{self.height}",
            'FPS': f"{self.fps:.2f}",
            'Frame Count': self.frame_count,
            'Duration': f"{self.duration:.2f} seconds",
            'Codec': int(self.cap.get(cv2.CAP_PROP_FOURCC))
        }
        
        # Try to extract additional metadata using ffprobe if available
        try:
            metadata.update(self._extract_ffprobe_metadata())
        except:
            pass
        
        return metadata
    
    def _extract_ffprobe_metadata(self):
        """Extract metadata using ffprobe (if available)"""
        try:
            cmd = [
                'ffprobe', 
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                self.video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                extra_metadata = {}
                if 'format' in data:
                    fmt = data['format']
                    if 'bit_rate' in fmt:
                        extra_metadata['Bitrate'] = f"{int(fmt['bit_rate'])/1000:.0f} kbps"
                    if 'format_name' in fmt:
                        extra_metadata['Format'] = fmt['format_name']
                return extra_metadata
        except:
            pass
        return {}
    
    def detect_frame_duplication(self, sample_size=100, threshold=0.95):
        """
        Detect duplicate frames which may indicate manipulation
        Returns: (has_duplicates, duplication_percentage, duplicate_frames)
        """
        try:
            # Sample frames uniformly
            frame_indices = np.linspace(0, self.frame_count-1, min(sample_size, self.frame_count), dtype=int)
            
            frames = []
            frame_hashes = []
            
            for idx in frame_indices:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = self.cap.read()
                if ret:
                    # Convert to grayscale and resize for comparison
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    small = cv2.resize(gray, (32, 32))
                    frames.append(small)
                    # Compute hash
                    frame_hashes.append(small.flatten())
            
            # Compare consecutive frames
            duplicate_count = 0
            duplicate_frames = []
            
            for i in range(len(frame_hashes) - 1):
                # Compute similarity
                correlation = np.corrcoef(frame_hashes[i], frame_hashes[i+1])[0, 1]
                if correlation > threshold:
                    duplicate_count += 1
                    duplicate_frames.append(frame_indices[i+1])
            
            duplication_percentage = (duplicate_count / len(frame_hashes)) * 100 if len(frame_hashes) > 0 else 0
            has_duplicates = duplication_percentage > 25.0  # More than 25% duplicates is suspicious
            
            return has_duplicates, duplication_percentage, duplicate_frames
        except Exception as e:
            print(f"Error in frame duplication detection: {e}")
            return False, 0.0, []
    
    def detect_inter_frame_forgery(self, sample_size=50):
        """
        Detect inter-frame manipulation by analyzing motion vectors
        Returns: (is_forged, forgery_score, suspicious_frames)
        """
        try:
            frame_indices = np.linspace(0, self.frame_count-1, min(sample_size, self.frame_count), dtype=int)
            
            frame_differences = []
            prev_frame = None
            
            for idx in frame_indices:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = self.cap.read()
                if ret:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    
                    if prev_frame is not None:
                        # Calculate frame difference
                        diff = cv2.absdiff(gray, prev_frame)
                        mean_diff = np.mean(diff)
                        frame_differences.append(mean_diff)
                    
                    prev_frame = gray
            
            if len(frame_differences) == 0:
                return False, 0.0, []
            
            # Analyze temporal consistency
            mean_diff = np.mean(frame_differences)
            std_diff = np.std(frame_differences)
            
            # Find abnormal transitions
            threshold = mean_diff + 3 * std_diff
            suspicious_indices = np.where(np.array(frame_differences) > threshold)[0]
            
            forgery_score = (len(suspicious_indices) / len(frame_differences)) * 100
            is_forged = forgery_score > 30.0  # More than 30% suspicious frames
            
            suspicious_frames = [frame_indices[i+1] for i in suspicious_indices if i+1 < len(frame_indices)]
            
            return is_forged, forgery_score, suspicious_frames
        except Exception as e:
            print(f"Error in inter-frame forgery detection: {e}")
            return False, 0.0, []
    
    def detect_copy_move_video(self, sample_frames=20):
        """
        Detect copy-move forgery in video frames using SIFT
        Returns: (has_forgery, forgery_percentage, forged_frames)
        """
        try:
            frame_indices = np.linspace(0, self.frame_count-1, min(sample_frames, self.frame_count), dtype=int)
            
            forged_frame_count = 0
            forged_frames = []
            
            sift = cv2.SIFT_create()
            
            for idx in frame_indices:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = self.cap.read()
                if ret:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    
                    # Detect keypoints and compute descriptors
                    keypoints, descriptors = sift.detectAndCompute(gray, None)
                    
                    if descriptors is not None and len(descriptors) > 10:
                        # Cluster descriptors to find duplicates
                        try:
                            clusters = DBSCAN(eps=40, min_samples=2).fit(descriptors)
                            unique_labels = np.unique(clusters.labels_)
                            
                            # Check if there are multiple clusters (potential copy-move)
                            non_noise_clusters = len(unique_labels[unique_labels != -1])
                            
                            if non_noise_clusters > 0:
                                forged_frame_count += 1
                                forged_frames.append(idx)
                        except:
                            pass
            
            forgery_percentage = (forged_frame_count / len(frame_indices)) * 100 if len(frame_indices) > 0 else 0
            has_forgery = forgery_percentage > 40.0
            
            return has_forgery, forgery_percentage, forged_frames
        except Exception as e:
            print(f"Error in copy-move detection: {e}")
            return False, 0.0, []
    
    def detect_double_compression(self, sample_frames=30):
        """
        Detect double compression artifacts
        Returns: (is_double_compressed, confidence)
        """
        try:
            frame_indices = np.linspace(0, self.frame_count-1, min(sample_frames, self.frame_count), dtype=int)
            
            dct_histograms = []
            
            for idx in frame_indices:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = self.cap.read()
                if ret:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    
                    # Apply DCT
                    dct = fftpack.dct(fftpack.dct(gray.T, norm='ortho').T, norm='ortho')
                    
                    # Histogram of DCT coefficients
                    hist, _ = np.histogram(dct.flatten(), bins=50, range=(-100, 100))
                    dct_histograms.append(hist)
            
            if len(dct_histograms) == 0:
                return False, 0.0
            
            # Analyze DCT coefficient distribution
            mean_hist = np.mean(dct_histograms, axis=0)
            
            # Look for periodic patterns typical of double compression
            # Calculate entropy of histogram
            hist_entropy = entropy(mean_hist + 1e-10)
            
            # Double compression typically shows lower entropy (be more conservative)
            is_double_compressed = hist_entropy < 2.2
            confidence = max(0, (2.8 - hist_entropy) / 2.8) * 100
            
            return is_double_compressed, confidence
        except Exception as e:
            print(f"Error in double compression detection: {e}")
            return False, 0.0
    
    def analyze_noise_consistency(self, sample_frames=20):
        """
        Analyze noise consistency across frames
        Returns: (is_inconsistent, consistency_score)
        """
        try:
            frame_indices = np.linspace(0, self.frame_count-1, min(sample_frames, self.frame_count), dtype=int)
            
            noise_levels = []
            
            for idx in frame_indices:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = self.cap.read()
                if ret:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    
                    # Estimate noise using Laplacian
                    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
                    noise_level = laplacian.var()
                    noise_levels.append(noise_level)
            
            if len(noise_levels) == 0:
                return False, 0.0
            
            # Calculate coefficient of variation
            mean_noise = np.mean(noise_levels)
            std_noise = np.std(noise_levels)
            
            consistency_score = (std_noise / mean_noise) * 100 if mean_noise > 0 else 0
            
            # High variation indicates inconsistency (more than 100% for compressed video)
            is_inconsistent = consistency_score > 100.0
            
            return is_inconsistent, consistency_score
        except Exception as e:
            print(f"Error in noise consistency analysis: {e}")
            return False, 0.0
    
    def detect_frame_rate_anomalies(self):
        """
        Detect frame rate inconsistencies
        Returns: (has_anomalies, anomaly_score)
        """
        try:
            # Check if FPS is standard
            standard_fps = [23.976, 24, 25, 29.97, 30, 50, 59.94, 60]
            
            is_standard = any(abs(self.fps - std_fps) < 0.1 for std_fps in standard_fps)
            
            if not is_standard:
                anomaly_score = 75.0
                has_anomalies = True
            else:
                # Check temporal consistency with CONSECUTIVE frames
                sample_size = min(50, self.frame_count - 1)
                start_frame = np.random.randint(0, max(1, self.frame_count - sample_size - 1))
                
                timestamps = []
                for frame_num in range(start_frame, start_frame + sample_size):
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                    timestamp = self.cap.get(cv2.CAP_PROP_POS_MSEC)
                    timestamps.append(timestamp)
                
                # Calculate inter-frame time differences for CONSECUTIVE frames
                time_diffs = np.diff(timestamps)
                expected_diff = 1000.0 / self.fps  # milliseconds per frame
                
                # Check for anomalies (allow more tolerance)
                anomalies = np.abs(time_diffs - expected_diff) > (expected_diff * 1.5)
                anomaly_score = (np.sum(anomalies) / len(time_diffs)) * 100 if len(time_diffs) > 0 else 0
                
                has_anomalies = anomaly_score > 30.0
            
            return has_anomalies, anomaly_score
        except Exception as e:
            print(f"Error in frame rate anomaly detection: {e}")
            return False, 0.0
    
    def extract_suspicious_frames(self, output_dir='suspicious_frames', max_frames=10):
        """Extract and save suspicious frames"""
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            # Run detection to get suspicious frames
            _, _, inter_frame_suspicious = self.detect_inter_frame_forgery()
            _, _, copy_move_suspicious = self.detect_copy_move_video()
            
            # Combine and get unique frames
            all_suspicious = list(set(inter_frame_suspicious + copy_move_suspicious))
            all_suspicious.sort()
            
            saved_frames = []
            for idx, frame_num in enumerate(all_suspicious[:max_frames]):
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                ret, frame = self.cap.read()
                if ret:
                    filename = f"{output_dir}/frame_{frame_num:06d}.png"
                    cv2.imwrite(filename, frame)
                    saved_frames.append(filename)
            
            return saved_frames
        except Exception as e:
            print(f"Error extracting suspicious frames: {e}")
            return []
    
    def comprehensive_analysis(self):
        """
        Run all detection methods and provide comprehensive report
        Returns: Dictionary with all analysis results
        """
        results = {
            'file_path': self.video_path,
            'file_name': os.path.basename(self.video_path),
            'metadata': self.extract_metadata(),
            'frame_duplication': None,
            'inter_frame_forgery': None,
            'copy_move_detection': None,
            'double_compression': None,
            'noise_consistency': None,
            'frame_rate_anomalies': None,
            'overall_verdict': 'ANALYZING'
        }
        
        # Run all tests
        has_dup, dup_percent, dup_frames = self.detect_frame_duplication()
        results['frame_duplication'] = {
            'has_duplicates': has_dup,
            'percentage': dup_percent,
            'duplicate_frames': dup_frames[:10]  # Limit output
        }
        
        is_inter_forged, inter_score, inter_frames = self.detect_inter_frame_forgery()
        results['inter_frame_forgery'] = {
            'is_forged': is_inter_forged,
            'score': inter_score,
            'suspicious_frames': inter_frames[:10]
        }
        
        has_copy_move, cm_percent, cm_frames = self.detect_copy_move_video()
        results['copy_move_detection'] = {
            'has_forgery': has_copy_move,
            'percentage': cm_percent,
            'forged_frames': cm_frames[:10]
        }
        
        is_double_comp, comp_conf = self.detect_double_compression()
        results['double_compression'] = {
            'is_detected': is_double_comp,
            'confidence': comp_conf
        }
        
        is_noise_incons, noise_score = self.analyze_noise_consistency()
        results['noise_consistency'] = {
            'is_inconsistent': is_noise_incons,
            'score': noise_score
        }
        
        has_fr_anom, fr_score = self.detect_frame_rate_anomalies()
        results['frame_rate_anomalies'] = {
            'has_anomalies': has_fr_anom,
            'score': fr_score
        }
        
        # Overall verdict (need at least 4 indicators for "LIKELY FORGED")
        forgery_indicators = sum([
            has_dup,
            is_inter_forged,
            has_copy_move,
            is_double_comp,
            is_noise_incons,
            has_fr_anom
        ])
        
        if forgery_indicators >= 4:
            results['overall_verdict'] = 'LIKELY FORGED'
        elif forgery_indicators >= 2:
            results['overall_verdict'] = 'SUSPICIOUS'
        else:
            results['overall_verdict'] = 'LIKELY AUTHENTIC'
        
        return results
    
    def __del__(self):
        """Release video capture"""
        if hasattr(self, 'cap'):
            self.cap.release()


def detect_video_forgery(video_path):
    """
    Main function to detect video forgery
    Returns comprehensive analysis results
    """
    forensics = VideoForensics(video_path)
    results = forensics.comprehensive_analysis()
    del forensics
    return results


if __name__ == "__main__":
    # Test the module
    import sys
    if len(sys.argv) > 1:
        video_file = sys.argv[1]
        results = detect_video_forgery(video_file)
        
        print("\n" + "="*60)
        print("VIDEO FORENSICS ANALYSIS REPORT")
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
        
        dup = results['frame_duplication']
        print(f"\n1. Frame Duplication:")
        print(f"   Status: {'DETECTED' if dup['has_duplicates'] else 'NOT DETECTED'}")
        print(f"   Percentage: {dup['percentage']:.2f}%")
        
        inter = results['inter_frame_forgery']
        print(f"\n2. Inter-Frame Forgery:")
        print(f"   Status: {'DETECTED' if inter['is_forged'] else 'NOT DETECTED'}")
        print(f"   Score: {inter['score']:.2f}%")
        
        cm = results['copy_move_detection']
        print(f"\n3. Copy-Move Detection:")
        print(f"   Status: {'DETECTED' if cm['has_forgery'] else 'NOT DETECTED'}")
        print(f"   Percentage: {cm['percentage']:.2f}%")
        
        comp = results['double_compression']
        print(f"\n4. Double Compression:")
        print(f"   Status: {'DETECTED' if comp['is_detected'] else 'NOT DETECTED'}")
        print(f"   Confidence: {comp['confidence']:.2f}%")
        
        noise = results['noise_consistency']
        print(f"\n5. Noise Consistency:")
        print(f"   Status: {'INCONSISTENT' if noise['is_inconsistent'] else 'CONSISTENT'}")
        print(f"   Score: {noise['score']:.2f}")
        
        fr = results['frame_rate_anomalies']
        print(f"\n6. Frame Rate Anomalies:")
        print(f"   Status: {'DETECTED' if fr['has_anomalies'] else 'NOT DETECTED'}")
        print(f"   Score: {fr['score']:.2f}%")
        
        print("\n" + "="*60)
    else:
        print("Usage: python video_forensics.py <video_file>")
