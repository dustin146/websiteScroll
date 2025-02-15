from moviepy.editor import VideoFileClip
import os

video_path = os.path.join('static', 'assets', 'test_video.mp4')
print(f"Video path: {video_path}")
print(f"File exists: {os.path.exists(video_path)}")

try:
    clip = VideoFileClip(video_path)
    print(f"Video loaded successfully")
    print(f"Duration: {clip.duration}")
    print(f"Has audio: {clip.audio is not None}")
    clip.close()
except Exception as e:
    print(f"Error loading video: {str(e)}")
