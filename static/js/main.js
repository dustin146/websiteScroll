async function handleWebcamUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('webcam', file);

    try {
        const response = await fetch('/upload_webcam', {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            const data = await response.json();
            const select = document.getElementById('webcamVideo');
            const option = new Option(file.name, data.filename);
            select.add(option);
            select.value = data.filename;
            updateStatus('Webcam video uploaded successfully!', 'success');
        } else {
            throw new Error('Failed to upload webcam video');
        }
    } catch (error) {
        updateStatus('Error uploading webcam video: ' + error.message, 'error');
    }
}

function updateStatus(message, type = '') {
    const status = document.getElementById('status');
    status.textContent = message;
    status.className = 'status ' + type;
}

async function captureWebsite() {
    const urlInput = document.getElementById('urlInput');
    const webcamSelect = document.getElementById('webcamVideo');
    const positionSelect = document.getElementById('webcamPosition');
    const video = document.getElementById('captureVideo');
    
    if (!urlInput.value) {
        updateStatus('Please enter a valid URL', 'error');
        return;
    }

    try {
        updateStatus('Capturing website scroll... This may take a few moments.');
        video.style.display = 'none';
        
        const response = await fetch('/capture', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                url: urlInput.value,
                webcam_video: webcamSelect.value,
                position: positionSelect.value
            })
        });

        const data = await response.json();
        
        if (response.ok) {
            updateStatus('Capture complete!', 'success');
            video.src = data.video_path;
            video.style.display = 'block';
            video.play();
        } else {
            updateStatus('Error: ' + data.error, 'error');
        }
    } catch (error) {
        updateStatus('Error: ' + error.message, 'error');
        console.error('Error:', error);
    }
}
