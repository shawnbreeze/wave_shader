import sys
from PySide6.QtCore import Qt, QUrl, QSize
from PySide6.QtGui import QImage, QColor, QSurfaceFormat
from PySide6.QtQml import QQmlApplicationEngine, QQmlImageProviderBase
from PySide6.QtQuick import QQuickImageProvider, QQuickWindow, QSGRendererInterface
from PySide6.QtWidgets import QApplication
from PySide6.QtQuickControls2 import QQuickStyle
import wave
import math
from numpy import ceil

from audio_processing import audio_to_qimage


class WaveImageProvider(QQuickImageProvider):
    def __init__(self):
        super().__init__(QQmlImageProviderBase.Image, 
                         QQmlImageProviderBase.ForceAsynchronousImageLoading)
        self.images = {}  # Словарь для хранения нескольких текстур
        self.request_count = 0
        self.provider_id = f"WaveProvider-{id(self)}"
        import time
        self.creation_time = time.strftime("%H:%M:%S")
        
    def set_image(self, key, image):
        self.images[key] = image
        print(f"Set image '{key}': {image.width()}x{image.height()}, format: {image.format()}, isNull: {image.isNull()}")
        if image.isNull():
            print("WARNING: Null image set in provider!")
        
    def requestImage(self, id, size, requested_size):
        self.request_count += 1
        key = id.split('/')[0] if '/' in id else id
        if key not in self.images or self.images[key].isNull():
            print(f"Warning: Image provider returning empty image for id: {id}")
            empty_img = QImage(16, 16, QImage.Format.Format_RGBA8888)
            empty_img.fill(QColor(255, 0, 0, 255))
            return empty_img
            
        img_size = QSize(self.images[key].width(), self.images[key].height())
        print(f"Returning image #{self.request_count}: {img_size.width()}x{img_size.height()} for id: {id}")
        
        result_image = QImage(self.images[key])

        if requested_size.width() > 0 and requested_size.height() > 0:
            return result_image.scaled(requested_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        else:
            return result_image

    # Метод для получения диагностической информации
    def get_diagnostic_info(self):
        return {
            "provider_id": self.provider_id,
            "creation_time": self.creation_time,
            "request_count": self.request_count
        }


def calculate_optimal_sample_per_pixel(num_frames, sample_rate, screen_width, min_width=800):
    """
    Calculates the optimal number of samples per pixel to minimize aliasing,
    using more gentle settings to preserve detail.
    
    Args:
        num_frames: Total number of frames in the audio file
        sample_rate: Audio sample rate (samples per second)
        screen_width: Screen width in pixels
        min_width: Minimum width to display the full waveform
        
    Returns:
        Optimal sample_per_pixel value
    """
    # Ideal ratio: one screen pixel corresponds to one texture pixel
    target_width = max(screen_width, min_width)
    
    # Base value – number of frames per pixel
    raw_spp = num_frames / target_width
    
    # Limit the minimum value
    if raw_spp < 1:
        return 1
    
    # Calculate audio duration
    duration = num_frames / sample_rate
    
    # More gentle rounding to power of two using round instead of floor for precision
    log2 = math.log2(raw_spp)
    power_of_two = 2 ** int(round(log2))
    
    # Limit maximum values to preserve detail
    max_allowed_spp = min(512, num_frames // 16)  # No more than 512 and at least 16 points on screen
    
    # New logic with gentler settings depending on duration
    if duration < 10:  # Short files (less than 10 sec)
        result = min(max(1, power_of_two // 2), max_allowed_spp)
    elif duration < 60:  # Files up to a minute
        result = min(max(2, power_of_two // 2), max_allowed_spp)
    elif duration < 300:  # Files up to 5 minutes
        result = min(max(4, power_of_two), max_allowed_spp)
    else:  # Very long files
        result = min(max(8, power_of_two), max_allowed_spp)
    
    # Ensure SPP is not too high relative to data size
    if num_frames / result < 100:
        result = max(1, num_frames // 100)
    
    # Optimal SPP for current screen
    optimal_for_screen = max(1, num_frames // screen_width)
    
    # Use lower SPP if screen can show more detail
    if optimal_for_screen < result and optimal_for_screen >= 1:
        result = optimal_for_screen
        
    # Further reduce SPP if data is sparse
    if num_frames / result < target_width / 2:
        result = max(1, num_frames // target_width)
    
    print(f"Base SPP value: {raw_spp:.2f}, power of two: {power_of_two}, final: {result}")
    
    return result


class AudioWaveApp:
    def __init__(self):
        app = QApplication(sys.argv)
        
        # Set base style for all controls
        QQuickStyle.setStyle("Material")
        
        self.engine = QQmlApplicationEngine()
        frmt = QSurfaceFormat()
        frmt.setSamples(8)
        frmt.setSwapInterval(0)
        # Включаем поддержку mipmaps
        QSurfaceFormat.setDefaultFormat(frmt)

        # Создаем и регистрируем image provider (перерегистрируем с правильными параметрами)
        self.wave_provider = WaveImageProvider()
        self.engine.addImageProvider("wave", self.wave_provider)

        audio_file_path = "bb.wav"
        
        # Retrieve audio file info before creating texture
        with wave.open(audio_file_path, 'rb') as wav_file:
            n_frames = wav_file.getnframes()
            framerate = wav_file.getframerate()
            channels = wav_file.getnchannels()
            audio_duration = n_frames / float(framerate)
        
        # Screen width
        screen = app.primaryScreen()
        screen_width = screen.size().width()
        
        # init sample_per_pixel
        sample_per_pixel = 1
        
        # create 2 textures with different sample_per_pixel values
        # fine texture
        fine_texture = audio_to_qimage(audio_file_path, sample_per_pixel)
        fine_texture_copy = QImage(fine_texture)
        self.wave_provider.set_image("fine", fine_texture_copy)
        
        # coarse texture
        coarse_sample_per_pixel = sample_per_pixel * 16
        coarse_texture = audio_to_qimage(audio_file_path, coarse_sample_per_pixel)
        coarse_texture_copy = QImage(coarse_texture)
        self.wave_provider.set_image("coarse", coarse_texture_copy)
        
        # Расчеты для обеих текстур
        fine_cols_used = int(ceil(n_frames / sample_per_pixel))
        coarse_cols_used = int(ceil(n_frames / coarse_sample_per_pixel))
        
        pixels_per_second = fine_texture.width() / audio_duration if audio_duration > 0 else 0

        # Set context properties
        context = self.engine.rootContext()
        
        # Передаем информацию о обеих текстурах
        context.setContextProperty("sampleRate", framerate)
        context.setContextProperty("audioDuration", audio_duration)
        
        # Детальная текстура
        context.setContextProperty("fineTextureUrl", "image://wave/fine")
        context.setContextProperty("fineSamplePerPixel", sample_per_pixel)
        context.setContextProperty("fineColsUsed", fine_cols_used)
        
        # Грубая текстура
        context.setContextProperty("coarseTextureUrl", "image://wave/coarse")
        context.setContextProperty("coarseSamplePerPixel", coarse_sample_per_pixel)
        context.setContextProperty("coarseColsUsed", coarse_cols_used)
        
        # Для обратной совместимости
        context.setContextProperty("samplePerPixel", sample_per_pixel)
        context.setContextProperty("cols_Used", fine_cols_used)
        context.setContextProperty("waveTextureUrl", "image://wave/fine")
        
        # Другие свойства
        context.setContextProperty("pixelsPerSecond", pixels_per_second)
        context.setContextProperty("waveColor", QColor("white"))
        context.setContextProperty("gridColor", QColor("#808080"))
        
        # Props for debugging provider
        context.setContextProperty("showDebugImage", False)
        context.setContextProperty("providerID", self.wave_provider.provider_id)
        context.setContextProperty("providerCreationTime", self.wave_provider.creation_time)

        # Recompile shaders before loading QML
        import subprocess
        
        try:
            subprocess.run(['compile_shaders.bat'], shell=True, check=True)
            # print("Shaders compiled successfully")
        except subprocess.CalledProcessError:
            print("Error compiling shaders")
            
        # Load QML
        self.engine.addImportPath(":/")
        self.engine.load(QUrl("main.qml"))

        # Check QML load success
        if not self.engine.rootObjects():
            print("Error loading QML file")
            sys.exit(-1)
            
        sys.exit(app.exec())


if __name__ == "__main__":
    import os
    os.environ['QSG_RENDER_LOOP'] = 'basic'  # Use basic render loop for debugging

    # Set environment variables for Vulkan
    os.environ["QT_QUICK_BACKEND"] = "vulkan"  # или "vulkan"
    # os.environ["QSG_INFO"] = "1"
    QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.Vulkan)  # или .OpenGL, .Direct3D11 …

    app = AudioWaveApp()
