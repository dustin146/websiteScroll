import cv2
import numpy as np

# Create a 720p canvas (1280x720)
height, width = 720, 1280
overlay = np.zeros((height, width, 4), dtype=np.uint8)

# Create a semi-transparent browser-like frame
# Top bar (40 pixels high)
overlay[0:40, :] = [50, 50, 50, 200]  # Dark gray with alpha

# Add some fake browser buttons
circle_centers = [(20, 20), (50, 20), (80, 20)]  # Traffic light style buttons
colors = [(46, 115, 252, 255), (255, 189, 46, 255), (255, 95, 86, 255)]  # Blue, Yellow, Red

for center, color in zip(circle_centers, colors):
    cv2.circle(overlay, center, 6, color, -1)

# Add a fake address bar
cv2.rectangle(overlay, (140, 8), (width-140, 32), (255, 255, 255, 200), -1)
cv2.rectangle(overlay, (140, 8), (width-140, 32), (200, 200, 200, 255), 1)

# Save the overlay
cv2.imwrite('overlay.png', overlay)
