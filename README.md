# Website Scroll Capture

This application creates scrolling video captures of websites, similar to Sendspark. It uses Python with Flask for the backend and Playwright for web automation.

## Setup

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Install Playwright browsers:
```bash
playwright install
```

3. Run the application:
```bash
python app.py
```

4. Open your browser and navigate to `http://localhost:5000`

## Usage

1. Enter a website URL in the input field
2. Click "Capture Scroll"
3. Wait for the capture to complete
4. The resulting video will be displayed on the page

## Features

- Smooth scrolling animation
- MP4 video output
- Simple and intuitive interface
- Automatic video generation

## Requirements

See `requirements.txt` for a full list of Python dependencies.
