async function captureWebsite() {
    const urlInput = document.getElementById('urlInput');
    const status = document.getElementById('status');
    const video = document.getElementById('captureVideo');
    
    if (!urlInput.value) {
        status.textContent = 'Please enter a valid URL';
        return;
    }

    try {
        status.textContent = 'Capturing website scroll... This may take a few moments.';
        video.style.display = 'none';
        
        const response = await fetch('/capture', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url: urlInput.value })
        });

        const data = await response.json();
        
        if (response.ok) {
            status.textContent = 'Capture complete! Playing video...';
            video.src = data.video_path;
            video.style.display = 'block';
            video.play();
        } else {
            status.textContent = 'Error: ' + data.error;
        }
    } catch (error) {
        status.textContent = 'Error: ' + error.message;
        console.error('Error:', error);
    }
}
