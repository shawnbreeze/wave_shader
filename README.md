# Wave Shader Audio Visualizer

https://github.com/user-attachments/assets/eb6076f7-a0da-484d-a424-03a275319928

## Overview

Wave Shader Audio Visualizer is a high-performance audio waveform visualization tool built with Python, Qt (PySide6), and GPU-accelerated shaders. It loads stereo `.wav` files, processes audio data into GPU textures, and renders interactive, zoomable waveforms using custom GLSL shaders.

## Features

- **High-Resolution Waveform Rendering:**  
  Visualizes stereo audio with fine and coarse textures for optimal performance and detail.

- **GPU Shader Acceleration:**  
  Uses custom vertex and fragment shaders for smooth, real-time waveform rendering.

- **Interactive Zoom and Navigation:**  
  - Mouse wheel zoom with dynamic acceleration and anchor-point zooming.
  - Scrollbar and buttons for fast navigation through the audio track.

- **Texture Switching:**  
  Automatically switches between high- and low-resolution textures based on zoom level for efficiency.

- **Customizable Appearance:**  
  - Dark theme with customizable waveform and grid colors.
  - Adjustable antialiasing and rendering parameters.

- **Debugging Tools:**  
  - Real-time diagnostic info for image providers and textures.
  - Logging to both file and console for troubleshooting.

- **Shader Recompilation:**  
  Option to recompile shaders before app launch via command-line argument.

## Usage

1. **Install Requirements:**  
   - Python 3.8+  
   - PySide6  
   - NumPy

2. **Run the Application:**  
   ```
   python test.py [options]
   ```

3. **Command-Line Options:**
   - `--opengl`, `--vulkan`, `--d3d11`, `--d3d12`, `--metal`  
     Select graphics API.
   - `--coarse <int>`  
     Set coarse texture multiplier.
   - `--antialiasing <int>`  
     Set antialiasing sample count.
   - `--spp <int>`  
     Set base samples-per-pixel.
   - `--recompile_shaders`  
     Recompile shaders before launch.

## Requirements
- **Operating System:**  
  Windows, macOS, or Linux.
- **Graphics Card:**  
  Discrete OpenGL 4.4+ or Vulkan-compatible GPU (fps drops with integrated GPUs)

## File Structure

- `test.py` — Main application entry point.
- `audio_processing.py` — Audio file loading and conversion to GPU textures.
- `main.qml` — QML UI for waveform display and controls.
- `shaders/` — Custom GLSL shaders for waveform rendering.

## License

MIT License (see `LICENSE` file for details).

