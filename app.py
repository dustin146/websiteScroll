from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from playwright.sync_api import sync_playwright
import cv2
import numpy as np
from moviepy.editor import ImageSequenceClip, VideoFileClip, AudioFileClip
import time
import os
import random
from typing import List, Tuple, Optional
from dataclasses import dataclass

app = Flask(__name__)

# Constants
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'assets')
CAPTURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'captures')

# Create directories if they don't exist
os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(CAPTURES_DIR, exist_ok=True)

@dataclass
class VideoConfig:
    fps: int = 20
    video_codec: str = 'libx264'
    audio_codec: str = 'aac'
    viewport_width: int = 1280
    viewport_height: int = 720

class VideoProcessor:
    def __init__(self, config: VideoConfig = VideoConfig()):
        self.config = config
    
    def create_video_from_frames(self, frames: List[np.ndarray], output_path: str, audio_path: Optional[str] = None) -> str:
        """Creates a video from frames with optional audio."""
        try:
            # Create base video without audio
            temp_path = f"{output_path}.temp.mp4"
            self._create_base_video(frames, temp_path)
            
            if audio_path and os.path.exists(audio_path):
                try:
                    self._add_audio_to_video(temp_path, audio_path, output_path)
                except Exception as e:
                    print(f"Error adding audio: {str(e)}")
                    os.rename(temp_path, output_path)
            else:
                os.rename(temp_path, output_path)
                
            return output_path
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise e
    
    def _create_base_video(self, frames: List[np.ndarray], output_path: str):
        """Creates a video from frames without audio."""
        frame_clip = ImageSequenceClip([frame[:, :, ::-1] for frame in frames], fps=self.config.fps)
        frame_clip.write_videofile(output_path, codec=self.config.video_codec, audio=False)
        frame_clip.close()
    
    def _add_audio_to_video(self, video_path: str, audio_path: str, output_path: str):
        """Adds audio from audio_path to video at video_path."""
        print(f"Adding audio from {audio_path} to {video_path}")
        video_clip = VideoFileClip(video_path)
        audio_clip = VideoFileClip(audio_path)
        
        if audio_clip.audio is not None:
            if video_clip.duration > audio_clip.duration:
                video_clip = video_clip.set_audio(audio_clip.audio.loop(duration=video_clip.duration))
            else:
                video_clip = video_clip.set_audio(audio_clip.audio)
            
            video_clip.write_videofile(output_path, codec=self.config.video_codec, audio_codec=self.config.audio_codec)
        
        video_clip.close()
        audio_clip.close()
        os.remove(video_path)

class WebsiteRecorder:
    def __init__(self, config: VideoConfig = VideoConfig()):
        self.config = config
    
    def capture_frame(self, page) -> np.ndarray:
        """Captures a single frame from the page."""
        screenshot = page.screenshot(full_page=False)
        return cv2.imdecode(np.frombuffer(screenshot, np.uint8), cv2.IMREAD_COLOR)
    
    def add_webcam_overlay(self, frame: np.ndarray, webcam_frame: np.ndarray, position: str = 'bottom-right') -> np.ndarray:
        """Adds circular webcam overlay to the frame."""
        # Make the overlay a square (same width and height) for perfect circle
        target_size = frame.shape[1] // 4  # 1/4 of frame width
        
        # Resize webcam frame to be square while maintaining aspect ratio
        webcam_h, webcam_w = webcam_frame.shape[:2]
        if webcam_w > webcam_h:
            # Width is larger, maintain height aspect
            scale = target_size / webcam_h
            new_width = int(webcam_w * scale)
            resized = cv2.resize(webcam_frame, (new_width, target_size))
            # Crop to square from center
            start_x = (new_width - target_size) // 2
            resized_webcam = resized[:, start_x:start_x+target_size]
        else:
            # Height is larger, maintain width aspect
            scale = target_size / webcam_w
            new_height = int(webcam_h * scale)
            resized = cv2.resize(webcam_frame, (target_size, new_height))
            # Crop to square from center
            start_y = (new_height - target_size) // 2
            resized_webcam = resized[start_y:start_y+target_size, :]
        
        # Create a circular mask
        mask = np.zeros((target_size, target_size), dtype=np.uint8)
        center = (target_size // 2, target_size // 2)
        radius = target_size // 2
        cv2.circle(mask, center, radius, 255, -1)
        
        # Calculate position
        if position == 'bottom-right':
            x = frame.shape[1] - target_size - 20  # 20px padding
            y = frame.shape[0] - target_size - 20
        elif position == 'bottom-left':
            x = 20
            y = frame.shape[0] - target_size - 20
        elif position == 'top-right':
            x = frame.shape[1] - target_size - 20
            y = 20
        else:  # top-left
            x = 20
            y = 20
        
        # Create output frame
        output = frame.copy()
        
        # Apply circular mask
        roi = output[y:y+target_size, x:x+target_size]
        masked_webcam = cv2.bitwise_and(resized_webcam, resized_webcam, mask=mask)
        masked_background = cv2.bitwise_and(roi, roi, mask=cv2.bitwise_not(mask))
        output[y:y+target_size, x:x+target_size] = cv2.add(masked_webcam, masked_background)
        
        return output
    
    def smooth_scroll(self, page, start_y: int, end_y: int, steps: int = 20) -> List[np.ndarray]:
        """Performs a smooth scroll and captures frames."""
        frames = []
        for i in range(steps):
            current_y = start_y + (end_y - start_y) * (i / steps)
            page.evaluate(f'window.scrollTo(0, {current_y})')
            frames.append(self.capture_frame(page))
            time.sleep(0.05)
        return frames
    
    def load_webcam_frames(self, video_path: str) -> List[np.ndarray]:
        """Loads frames from a webcam video file."""
        frames = []
        if video_path and os.path.exists(video_path):
            cap = cv2.VideoCapture(video_path)
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                frames.append(frame)
            cap.release()
        return frames
    
    def capture_scrolling_video(self, url: str, webcam_video_path: Optional[str] = None, position: str = 'bottom-right') -> Tuple[List[np.ndarray], int]:
        """Captures a scrolling video of a website with optional webcam overlay."""
        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(viewport={'width': self.config.viewport_width, 'height': self.config.viewport_height})
            page = context.new_page()
            
            try:
                page.goto(url, wait_until='networkidle')
                page_height = page.evaluate('document.documentElement.scrollHeight')
                
                # Load webcam frames if provided
                webcam_frames = self.load_webcam_frames(webcam_video_path) if webcam_video_path else []
                total_webcam_frames = len(webcam_frames)
                webcam_frame_idx = 0
                
                frames = []
                
                # Initial pause
                for _ in range(10):
                    frame = self.capture_frame(page)
                    if webcam_frames:
                        frame = self.add_webcam_overlay(frame, webcam_frames[webcam_frame_idx % total_webcam_frames], position)
                        webcam_frame_idx += 1
                    frames.append(frame)
                    time.sleep(0.05)
                
                # Scroll down halfway
                halfway_point = page_height / 2
                scroll_frames = self.smooth_scroll(page, 0, halfway_point)
                for frame in scroll_frames:
                    if webcam_frames:
                        frame = self.add_webcam_overlay(frame, webcam_frames[webcam_frame_idx % total_webcam_frames], position)
                        webcam_frame_idx += 1
                    frames.append(frame)
                
                # Pause at halfway
                for _ in range(20):
                    frame = self.capture_frame(page)
                    if webcam_frames:
                        frame = self.add_webcam_overlay(frame, webcam_frames[webcam_frame_idx % total_webcam_frames], position)
                        webcam_frame_idx += 1
                    frames.append(frame)
                    time.sleep(0.05)
                
                # Scroll back to top
                scroll_frames = self.smooth_scroll(page, halfway_point, 0)
                for frame in scroll_frames:
                    if webcam_frames:
                        frame = self.add_webcam_overlay(frame, webcam_frames[webcam_frame_idx % total_webcam_frames], position)
                        webcam_frame_idx += 1
                    frames.append(frame)
                
                # Final pause
                for _ in range(10):
                    frame = self.capture_frame(page)
                    if webcam_frames:
                        frame = self.add_webcam_overlay(frame, webcam_frames[webcam_frame_idx % total_webcam_frames], position)
                        webcam_frame_idx += 1
                    frames.append(frame)
                    time.sleep(0.05)
                
                return frames, webcam_frame_idx
            finally:
                browser.close()

# Flask routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/capture', methods=['POST'])
def capture():
    url = request.json.get('url')
    webcam_video = request.json.get('webcam_video', 'test_video.mp4')
    position = request.json.get('position', 'bottom-right')
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    try:
        # Initialize components
        config = VideoConfig()
        recorder = WebsiteRecorder(config)
        processor = VideoProcessor(config)
        
        # Get absolute path to the webcam video
        webcam_path = os.path.abspath(os.path.join(ASSETS_DIR, webcam_video))
        print(f"Full webcam path: {webcam_path}")
        print(f"File exists: {os.path.exists(webcam_path)}")
        
        # Capture frames
        frames, _ = recorder.capture_scrolling_video(url, webcam_path, position)
        
        # Create video file
        timestamp = int(time.time())
        output_path = os.path.join(CAPTURES_DIR, f'scroll_{timestamp}.mp4')
        
        # Process video
        processor.create_video_from_frames(frames, output_path, webcam_path)
        
        return jsonify({'video_path': f'/static/captures/scroll_{timestamp}.mp4'})
    except Exception as e:
        print(f"Error in capture route: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/upload_webcam', methods=['POST'])
def upload_webcam():
    if 'webcam' not in request.files:
        return jsonify({'error': 'No webcam video provided'}), 400
    
    file = request.files['webcam']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file:
        # Secure the filename
        filename = secure_filename(file.filename)
        # Save to assets directory
        file_path = os.path.join(ASSETS_DIR, filename)
        file.save(file_path)
        return jsonify({'filename': filename})
    
    return jsonify({'error': 'Failed to save file'}), 500

if __name__ == '__main__':
    app.run(debug=True)
