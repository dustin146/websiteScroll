# Website Scroll Capture

A web application that captures scrolling videos of websites while adding a video overlay in the corner, similar to Loom. Perfect for creating consistent, branded website walkthroughs and demonstrations.

## Features

- Capture smooth scrolling videos of any website
- Add webcam video overlay in any corner (top-left, top-right, bottom-left, bottom-right)
- Upload and manage multiple webcam videos for different recordings
- Modern, user-friendly interface
- Real-time status updates and error handling
- High-quality video output with configurable settings

## Installation

1. Clone the repository:
```bash
git clone https://github.com/dustin146/websiteScroll.git
cd websiteScroll
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the Flask server:
```bash
python app.py
```

2. Open your browser and navigate to `http://localhost:5000`

3. Enter a website URL and choose your webcam video position

4. Click "Capture Scroll" to start recording

## Requirements

- Python 3.7+
- Flask
- Playwright
- OpenCV
- NumPy

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
