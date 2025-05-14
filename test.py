import sys
from pprint import pprint

from PySide6.QtCore import Qt, QUrl, QSize, qInstallMessageHandler, QtMsgType, QDateTime
from PySide6.QtGui import QImage, QColor, QSurfaceFormat
from PySide6.QtQml import QQmlApplicationEngine, QQmlImageProviderBase
from PySide6.QtQuick import QQuickImageProvider, QQuickWindow, QSGRendererInterface
from PySide6.QtWidgets import QApplication
from PySide6.QtQuickControls2 import QQuickStyle
from audio_processing import audio_to_qimage
import wave
import math
from numpy import ceil
import logging  # Добавляем импорт logging

RECOMPILE_SHADERS = False

# setup logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)  # Устанавливаем уровень логирования DEBUG для захвата всех сообщений

# file handler
file_handler = logging.FileHandler('logfile.log', mode='w')  # 'w' для перезаписи файла при каждом запуске
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                                   datefmt='%Y-%m-%d %H:%M:%S')  # Исправлено: levellevel -> levelname
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# console hamndler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)  # Изменяем уровень на DEBUG, чтобы видеть сообщения console.log()
console_formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s',  # Исправлено: levellevel -> levelname
                                      datefmt='%Y-%m-%d %H:%M:%S')  # Исправлено: %М -> %M
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)


# Функция для обработки сообщений от Qt/QML
def qt_message_handler(mode, context, message):
    # Получаем имя файла и номер строки из контекста, если возможно
    # context.file, context.line, context.function
    log_message = f"[QML] {message}"
    if context.file:
        log_message = f"[QML] {os.path.basename(context.file)}:{context.line} - {message}"

    if mode == QtMsgType.QtDebugMsg:
        logger.debug(log_message)
    elif mode == QtMsgType.QtInfoMsg:
        logger.info(log_message)
    elif mode == QtMsgType.QtWarningMsg:
        logger.warning(log_message)
    elif mode == QtMsgType.QtCriticalMsg:
        logger.error(log_message)
    elif mode == QtMsgType.QtFatalMsg:
        logger.critical(log_message)
        sys.exit(-1) # Фатальные ошибки обычно требуют завершения


class WaveImageProvider(QQuickImageProvider):
    def __init__(self):
        super().__init__(QQmlImageProviderBase.Image, 
                         QQmlImageProviderBase.ForceAsynchronousImageLoading)
        self.images = {}  # textures dict
        self.request_count = 0
        self.provider_id = f"WaveImageProvider - {id(self)}"
        self.creation_time = QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss")
        logger.info(f"WaveProvider {id(self)} created")
        
    def set_image(self, key, image):
        self.images[key] = image
        logger.info(f"Set image '{key}': {image.width()}x{image.height()}, format: {image.format()}, isNull: {image.isNull()}")
        if image.isNull():
            logger.warning("WARNING: Null image set in provider!")
        
    def requestImage(self, id, size, requested_size):
        self.request_count += 1
        key = id.split('/')[0] if '/' in id else id
        if key not in self.images or self.images[key].isNull():
            logger.warning(f"Image provider returning empty image for id: {id}")
            empty_img = QImage(16, 16, QImage.Format.Format_RGBA16FPx4_Premultiplied)
            empty_img.fill(QColor(154, 100, 154, 100))
            return empty_img
            
        img_size = QSize(self.images[key].width(), self.images[key].height())
        logger.debug(f"Returning image #{self.request_count}: {img_size.width()}x{img_size.height()} for id: {id}")
        
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
            "request_count": self.request_count,
            "image_keys": list(self.images.keys())
        }


def create_mipmap_textures_dict(audio_file_path, base_spp) -> dict:
    """
    Создает mipmap текстуры для аудиофайла.
    :param audio_file_path: путь к аудиофайлу
    :param screen_width: ширина экрана (в пикселях)
    :return: словарь {spp: {'texture': QImage, 'cols': cols_used}}
    """
    screen_width = QApplication.primaryScreen().size().width()
    mipmaps = {}
    spp = 1
    textures_size = 0
    cols_used = screen_width * 2 + 1
    while cols_used > (screen_width * 2):
        texture, cols_used = audio_to_qimage(audio_file_path, spp)
        mipmaps[spp] = {'texture': texture, 'cols': cols_used}
        textures_size += texture.sizeInBytes()
        spp *= 2
    logger.info(f"Created {len(mipmaps)} mipmaps with total size: {textures_size / (1024 * 1024):.2f} MB")
    return mipmaps


def recompile_shaders():
    import subprocess
    try:
        subprocess.run(['compile_shaders.bat'], shell=True, check=True)
        logger.info("Shaders compiled successfully")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error compiling shaders: {e}")


class AudioWaveApp:
    def __init__(self):
        app = QApplication(sys.argv)
        
        # Set base style for all controls
        QQuickStyle.setStyle("Material")
        
        logger.info("App started.")
        self.engine = QQmlApplicationEngine()
        frmt = QSurfaceFormat()
        frmt.setSamples(8)
        frmt.setSwapInterval(0)
        # Включаем поддержку mipmaps
        QSurfaceFormat.setDefaultFormat(frmt)

        # Создаем и регистрируем image provider (перерегистрируем с правильными параметрами)
        self.wave_provider = WaveImageProvider()
        self.engine.addImageProvider("wave", self.wave_provider)

        audio_file_path = "Antonio Vivaldi - Allegro - Spring.wav"
        # sys.exit(0)
        # Retrieve audio file info before creating texture
        with wave.open(audio_file_path, 'rb') as wav_file:
            n_frames = wav_file.getnframes()
            framerate = wav_file.getframerate()
            channels = wav_file.getnchannels()
            audio_duration = n_frames / float(framerate)

        # init sample_per_pixel (SPP), 1 for max detailed waveform, lower values need more RAM and GPU, optimal = 2
        base_sample_per_pixel = 1
        # textures = create_mipmap_textures_dict(audio_file_path, base_sample_per_pixel)
        # sys.exit(0)

        # create 2 textures with different sample_per_pixel values
        # fine texture
        fine_texture, fine_cols_used = audio_to_qimage(audio_file_path, base_sample_per_pixel)
        if fine_texture.isNull():
            logger.error(f"Failed to load fine texture for {audio_file_path}")
        else:
            logger.info(f"Fine texture loaded: {fine_texture.width()}x{fine_texture.height()}")
        fine_texture_copy = QImage(fine_texture)
        self.wave_provider.set_image("fine", fine_texture_copy)
        
        # coarse texture
        coarse_sample_per_pixel = base_sample_per_pixel * 32
        coarse_texture, coarse_cols_used = audio_to_qimage(audio_file_path, coarse_sample_per_pixel)
        if coarse_texture.isNull():
            logger.error(f"Failed to load coarse texture for {audio_file_path}")
        else:
            logger.info(f"Coarse texture loaded: {coarse_texture.width()}x{coarse_texture.height()}")
        coarse_texture_copy = QImage(coarse_texture)
        self.wave_provider.set_image("coarse", coarse_texture_copy)

        pixels_per_second = fine_texture.width() / audio_duration if audio_duration > 0 else 0

        # set context properties
        context = self.engine.rootContext()
        
        # pass audio textures info
        context.setContextProperty("sampleRate", framerate)
        context.setContextProperty("audioDuration", audio_duration)
        
        # high resolution texture
        context.setContextProperty("fineTextureUrl", "image://wave/fine")
        context.setContextProperty("fineSamplePerPixel", base_sample_per_pixel)
        context.setContextProperty("fineColsUsed", fine_cols_used)
        
        # low resolution texture
        context.setContextProperty("coarseTextureUrl", "image://wave/coarse")
        context.setContextProperty("coarseSamplePerPixel", coarse_sample_per_pixel)
        context.setContextProperty("coarseColsUsed", coarse_cols_used)
        
        # more properties
        context.setContextProperty("samplePerPixel", base_sample_per_pixel)
        context.setContextProperty("cols_Used", fine_cols_used)
        context.setContextProperty("waveTextureUrl", "image://wave/fine")

        context.setContextProperty("pixelsPerSecond", pixels_per_second)
        context.setContextProperty("waveColor", QColor("white"))
        context.setContextProperty("gridColor", QColor("#808080"))
        
        # Props for debugging provider
        context.setContextProperty("showDebugImage", False)
        context.setContextProperty("providerID", self.wave_provider.provider_id)
        context.setContextProperty("providerCreationTime", self.wave_provider.creation_time)

        # Recompile shaders before loading QML
        if RECOMPILE_SHADERS:
            recompile_shaders()

        # Load QML
        self.engine.addImportPath(":/")
        self.engine.load(QUrl("main.qml"))

        # Check QML load success
        if not self.engine.rootObjects():
            logger.error("Error loading QML file. Root objects not found.")
            sys.exit(-1)
        else:
            logger.info("QML file loaded successfully.")
            
        sys.exit(app.exec())


if __name__ == "__main__":
    import os
    # Устанавливаем обработчик сообщений Qt перед созданием QApplication или QQmlApplicationEngine
    qInstallMessageHandler(qt_message_handler)

    os.environ['QSG_RENDER_LOOP'] = 'basic'  # Use basic render loop for debugging
    logger.info(f"QSG_RENDER_LOOP set to: {os.environ.get('QSG_RENDER_LOOP')}")

    # Set environment variables
    # os.environ["QSG_INFO"] = "1"
    # logger.info(f"QSG_INFO set to: {os.environ.get('QSG_INFO')}")
    
    # set graphics API
    # QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.OpenGL)
    # QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.Vulkan)
    logger.info(f"Graphics API set to: {QQuickWindow.graphicsApi()}")

    app = AudioWaveApp()

