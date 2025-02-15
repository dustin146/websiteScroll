from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from playwright.sync_api import sync_playwright
import cv2
import numpy as np
import time
import os
import random

app = Flask(__name__)

# Ensure the directories exist
CAPTURES_DIR = os.path.join('static', 'captures')
ASSETS_DIR = os.path.join('static', 'assets')
os.makedirs(CAPTURES_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)

def capture_frame(page):
    screenshot = page.screenshot(full_page=False)
    return cv2.imdecode(np.frombuffer(screenshot, np.uint8), cv2.IMREAD_COLOR)

def add_webcam_overlay(frame, webcam_frame, position='bottom-right', size_ratio=0.25):
    """Add webcam overlay to the frame in the specified position"""
    if webcam_frame is None:
        return frame
    
    frame_h, frame_w = frame.shape[:2]
    webcam_h, webcam_w = webcam_frame.shape[:2]
    
    # Calculate new size for webcam frame (25% of main frame by default)
    new_webcam_w = int(frame_w * size_ratio)
    new_webcam_h = int(webcam_h * (new_webcam_w / webcam_w))
    
    # Resize webcam frame
    webcam_resized = cv2.resize(webcam_frame, (new_webcam_w, new_webcam_h))
    
    # Calculate position
    if position == 'bottom-right':
        x = frame_w - new_webcam_w - 20  # 20px padding
        y = frame_h - new_webcam_h - 20
    elif position == 'bottom-left':
        x = 20
        y = frame_h - new_webcam_h - 20
    elif position == 'top-right':
        x = frame_w - new_webcam_w - 20
        y = 20
    else:  # top-left
        x = 20
        y = 20
    
    # Create mask for rounded corners
    mask = np.zeros((new_webcam_h, new_webcam_w), dtype=np.uint8)
    cv2.rectangle(mask, (0, 0), (new_webcam_w, new_webcam_h), 255, -1)
    radius = 15
    cv2.rectangle(mask, (0, 0), (radius*2, radius*2), 0, -1)
    cv2.circle(mask, (radius, radius), radius, 255, -1)
    cv2.rectangle(mask, (new_webcam_w-radius*2, 0), (new_webcam_w, radius*2), 0, -1)
    cv2.circle(mask, (new_webcam_w-radius, radius), radius, 255, -1)
    cv2.rectangle(mask, (0, new_webcam_h-radius*2), (radius*2, new_webcam_h), 0, -1)
    cv2.circle(mask, (radius, new_webcam_h-radius), radius, 255, -1)
    cv2.rectangle(mask, (new_webcam_w-radius*2, new_webcam_h-radius*2), (new_webcam_w, new_webcam_h), 0, -1)
    cv2.circle(mask, (new_webcam_w-radius, new_webcam_h-radius), radius, 255, -1)
    
    # Add slight shadow
    shadow = np.zeros_like(frame)
    shadow[y+5:y+new_webcam_h+5, x+5:x+new_webcam_w+5] = [0, 0, 0]
    frame = cv2.addWeighted(frame, 1, shadow, 0.5, 0)
    
    # Add webcam overlay using the mask
    roi = frame[y:y+new_webcam_h, x:x+new_webcam_w]
    roi_bg = cv2.bitwise_and(roi, roi, mask=cv2.bitwise_not(mask))
    roi_fg = cv2.bitwise_and(webcam_resized, webcam_resized, mask=mask)
    frame[y:y+new_webcam_h, x:x+new_webcam_w] = cv2.add(roi_bg, roi_fg)
    
    return frame

def smooth_scroll(page, start_pos, end_pos, steps=20, delay=0.05):
    frames = []
    step_size = (end_pos - start_pos) / steps
    
    for i in range(steps + 1):
        current = start_pos + (step_size * i)
        page.evaluate(f'window.scrollTo(0, {current})')
        time.sleep(delay)
        frames.append(capture_frame(page))
    
    return frames

def capture_scrolling_video(url, webcam_video_path=None, position='bottom-right'):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={'width': 1280, 'height': 720})
        page = context.new_page()
        
        try:
            # Load the webcam video if provided
            webcam_frames = []
            if webcam_video_path and os.path.exists(webcam_video_path):
                webcam_cap = cv2.VideoCapture(webcam_video_path)
                while True:
                    ret, frame = webcam_cap.read()
                    if not ret:
                        break
                    webcam_frames.append(frame)
                webcam_cap.release()
            
            # Navigate to the URL with a timeout
            page.goto(url, wait_until='networkidle', timeout=30000)
            
            # Get page dimensions
            page_height = page.evaluate('document.documentElement.scrollHeight')
            viewport_height = page.viewport_size['height']
            
            frames = []
            webcam_frame_idx = 0
            total_webcam_frames = len(webcam_frames)
            
            # Initial pause at the top
            for _ in range(10):
                frame = capture_frame(page)
                if webcam_frames:
                    webcam_frame = webcam_frames[webcam_frame_idx % total_webcam_frames]
                    frame = add_webcam_overlay(frame, webcam_frame, position)
                    webcam_frame_idx += 1
                frames.append(frame)
                time.sleep(0.05)
            
            # Scroll halfway down
            halfway_point = page_height / 2
            scroll_frames = smooth_scroll(page, 0, halfway_point)
            for frame in scroll_frames:
                if webcam_frames:
                    webcam_frame = webcam_frames[webcam_frame_idx % total_webcam_frames]
                    frame = add_webcam_overlay(frame, webcam_frame, position)
                    webcam_frame_idx += 1
                frames.append(frame)
            
            # Pause at halfway point
            for _ in range(20):
                frame = capture_frame(page)
                if webcam_frames:
                    webcam_frame = webcam_frames[webcam_frame_idx % total_webcam_frames]
                    frame = add_webcam_overlay(frame, webcam_frame, position)
                    webcam_frame_idx += 1
                frames.append(frame)
                time.sleep(0.05)
            
            # Scroll back to top
            scroll_frames = smooth_scroll(page, halfway_point, 0)
            for frame in scroll_frames:
                if webcam_frames:
                    webcam_frame = webcam_frames[webcam_frame_idx % total_webcam_frames]
                    frame = add_webcam_overlay(frame, webcam_frame, position)
                    webcam_frame_idx += 1
                frames.append(frame)
            
            # Final pause at the top
            for _ in range(10):
                frame = capture_frame(page)
                if webcam_frames:
                    webcam_frame = webcam_frames[webcam_frame_idx % total_webcam_frames]
                    frame = add_webcam_overlay(frame, webcam_frame, position)
                    webcam_frame_idx += 1
                frames.append(frame)
                time.sleep(0.05)
            
            # Create video file
            timestamp = int(time.time())
            output_path = os.path.join(CAPTURES_DIR, f'scroll_{timestamp}.mp4')
            
            if frames:
                height, width = frames[0].shape[:2]
                out = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'mp4v'), 20, (width, height))
                
                for frame in frames:
                    out.write(frame)
                out.release()
                
                return f'/static/captures/scroll_{timestamp}.mp4'
            else:
                raise Exception("No frames were captured")
                
        except Exception as e:
            raise Exception(f"Failed to capture website: {str(e)}")
        finally:
            browser.close()

@app.route('/')
def index():
    return render_template('index.html')

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

@app.route('/capture', methods=['POST'])
def capture():
    url = request.json.get('url')
    webcam_video = request.json.get('webcam_video', 'default_webcam.mp4')
    position = request.json.get('position', 'bottom-right')
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    try:
        video_path = capture_scrolling_video(url, os.path.join(ASSETS_DIR, webcam_video), position)
        return jsonify({'video_path': video_path})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
