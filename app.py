from flask import Flask, render_template, request, jsonify, send_from_directory
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

def overlay_frame(frame, overlay):
    # Resize overlay if needed to match frame dimensions
    if overlay.shape[:2] != frame.shape[:2]:
        overlay = cv2.resize(overlay, (frame.shape[1], frame.shape[0]))
    
    # Create a mask for transparent pixels (assuming overlay has alpha channel)
    if overlay.shape[2] == 4:  # If overlay has alpha channel
        alpha = overlay[:, :, 3] / 255.0
        alpha = np.stack([alpha] * 3, axis=-1)
        overlay_rgb = overlay[:, :, :3]
        
        # Blend the images
        blended = overlay_rgb * alpha + frame * (1 - alpha)
        return blended.astype(np.uint8)
    else:
        # If no alpha channel, use simple overlay
        return cv2.addWeighted(frame, 0.8, overlay, 0.2, 0)

def smooth_scroll(page, start_pos, end_pos, steps=20, delay=0.05):
    frames = []
    step_size = (end_pos - start_pos) / steps
    
    for i in range(steps + 1):
        current = start_pos + (step_size * i)
        page.evaluate(f'window.scrollTo(0, {current})')
        time.sleep(delay)  # Add small random delay for natural feel
        frames.append(capture_frame(page))
    
    return frames

def capture_scrolling_video(url):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={'width': 1280, 'height': 720})
        page = context.new_page()
        
        try:
            # Load the overlay image
            overlay_path = os.path.join(ASSETS_DIR, 'overlay.png')
            if os.path.exists(overlay_path):
                overlay = cv2.imread(overlay_path, cv2.IMREAD_UNCHANGED)
            else:
                overlay = None
            
            # Navigate to the URL with a timeout
            page.goto(url, wait_until='networkidle', timeout=30000)
            
            # Get page dimensions
            page_height = page.evaluate('document.documentElement.scrollHeight')
            viewport_height = page.viewport_size['height']
            
            frames = []
            
            # Initial pause at the top
            for _ in range(10):  # Show top of page for ~0.5 seconds
                frame = capture_frame(page)
                if overlay is not None:
                    frame = overlay_frame(frame, overlay)
                frames.append(frame)
                time.sleep(0.05)
            
            # Scroll halfway down
            halfway_point = page_height / 2
            scroll_frames = smooth_scroll(page, 0, halfway_point)
            if overlay is not None:
                scroll_frames = [overlay_frame(frame, overlay) for frame in scroll_frames]
            frames.extend(scroll_frames)
            
            # Pause at halfway point
            for _ in range(20):  # Pause for ~1 second
                frame = capture_frame(page)
                if overlay is not None:
                    frame = overlay_frame(frame, overlay)
                frames.append(frame)
                time.sleep(0.05)
            
            # Scroll back to top
            scroll_frames = smooth_scroll(page, halfway_point, 0)
            if overlay is not None:
                scroll_frames = [overlay_frame(frame, overlay) for frame in scroll_frames]
            frames.extend(scroll_frames)
            
            # Final pause at the top
            for _ in range(10):  # Show top of page for ~0.5 seconds
                frame = capture_frame(page)
                if overlay is not None:
                    frame = overlay_frame(frame, overlay)
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

@app.route('/capture', methods=['POST'])
def capture():
    url = request.json.get('url')
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    try:
        video_path = capture_scrolling_video(url)
        return jsonify({'video_path': video_path})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
