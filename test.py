import sys
import wave
import logging
from PySide6.QtCore import Qt, QUrl, QSize, qInstallMessageHandler, QtMsgType, QDateTime
from PySide6.QtGui import QImage, QColor, QSurfaceFormat
from PySide6.QtQml import QQmlApplicationEngine, QQmlImageProviderBase
from PySide6.QtQuick import QQuickImageProvider, QQuickWindow, QSGRendererInterface
from PySide6.QtWidgets import QApplication
from PySide6.QtQuickControls2 import QQuickStyle
from audio_processing import audio_to_qimage
from pprint import pprint


# setup logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# file handler
file_handler = logging.FileHandler('logfile.log', mode='w')
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                                   datefmt='%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
console_formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s',
                                      datefmt='%Y-%m-%d %H:%M:%S')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)


# function to handle QML messages
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
        super().__init__(QQmlImageProviderBase.ImageType.Image,
                         QQmlImageProviderBase.Flag.ForceAsynchronousImageLoading)
        self.images = {}  # textures dict
        self.request_count = 0
        self.provider_id = f"WaveImageProvider - {id(self)}"
        self.creation_time = QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss")
        logger.debug(f"WaveProvider {id(self)} created")

    def set_image(self, key, image):
        self.images[key] = image
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

    # diagnostic info
    def get_diagnostic_info(self):
        return {
            "provider_id": self.provider_id,
            "creation_time": self.creation_time,
            "request_count": self.request_count,
            "image_keys": list(self.images.keys())
        }


def recompile_shaders():
    import subprocess
    result = subprocess.run(['compile_shaders.bat'], shell=True)
    if result.returncode == 0:
        logger.info("Shaders compiled successfully")
    else:
        logger.error(f"Error compiling shaders: {result.stderr}")
        sys.exit()


class AudioWaveApp:
    def __init__(self, coarse_multiplier=1, antialiasing_samples=0, base_spp=2):
        app = QApplication(sys.argv)
        
        # Set base style for all controls
        QQuickStyle.setStyle("Fusion")
        
        logger.info("App started.")
        self.engine = QQmlApplicationEngine()
        frmt = QSurfaceFormat()
        frmt.setSamples(antialiasing_samples)
        frmt.setSwapInterval(0)  # turn off VSync
        QSurfaceFormat.setDefaultFormat(frmt)

        # create and add image provider
        self.wave_provider = WaveImageProvider()
        self.engine.addImageProvider("wave", self.wave_provider)

        audio_file_path = "Antonio Vivaldi - Allegro - Spring.wav"
        # audio_file_path = "long.wav"

        # Retrieve audio file info before creating texture
        with wave.open(audio_file_path, 'rb') as wav_file:
            n_frames = wav_file.getnframes()
            framerate = wav_file.getframerate()
            channels = wav_file.getnchannels()
            audio_duration = n_frames / float(framerate)

        # init sample_per_pixel (SPP),
        # 1 for maximum detailed waveform and max ZOOM,
        # lower values need more RAM and GPU,
        # 0 for automatic, optimal = 2 TODO: automatic spp setting based on audio n_frames and MAX_TEX_SIDE, returns max value that fits in MAX_TEX_SIDE*MAX_TEX_SIDE size texture
        base_sample_per_pixel = base_spp

        # create 2 textures with different sample_per_pixel values
        # fine texture
        fine_texture, fine_cols_used = audio_to_qimage(audio_file_path, base_sample_per_pixel)
        if fine_texture.isNull():
            logger.error(f"Failed to load fine texture for {audio_file_path}")
        else:
            logger.debug(f"Fine texture loaded: {fine_texture.width()}x{fine_texture.height()}")
        fine_texture_copy = QImage(fine_texture)
        self.wave_provider.set_image("fine", fine_texture_copy)
        
        # coarse texture
        coarse_sample_per_pixel = max(
            base_sample_per_pixel * 16 * coarse_multiplier,
            base_sample_per_pixel * 16 * coarse_multiplier * (n_frames // 8388608)
        )
        logging.debug(f'Selected coarse sample per pixel: {coarse_sample_per_pixel}')
        coarse_texture, coarse_cols_used = audio_to_qimage(audio_file_path, coarse_sample_per_pixel)
        if coarse_texture.isNull():
            logger.error(f"Failed to load coarse texture for {audio_file_path}")
        else:
            logger.debug(f"Coarse texture loaded: {coarse_texture.width()}x{coarse_texture.height()}")
        coarse_texture_copy = QImage(coarse_texture)
        self.wave_provider.set_image("coarse", coarse_texture_copy)

        pixels_per_second = fine_texture.width() / audio_duration if audio_duration > 0 else 0

        # set required context properties
        context = self.engine.rootContext()
        
        # pass audio info
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
        context.setContextProperty("fineTextureSwitchThreshold", 1.0)
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
        context.setContextProperty("antialiasingSamples", antialiasing_samples)

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
    import sys
    argv = sys.argv

    # Set default values
    COARSE_MULTIPLIER = 1
    ANTIALIASING_SAMPLES = 0
    BASE_SPP = 2

    # set Qt messages handler
    qInstallMessageHandler(qt_message_handler)

    os.environ['QSG_RENDER_LOOP'] = 'basic'  # Use basic render loop for debugging
    logger.info(f"QSG_RENDER_LOOP set to: {os.environ.get('QSG_RENDER_LOOP')}")

    # command line arguments processing
    for arg in argv:
        match arg:
            # force graphics API selection
            case '--opengl': QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.OpenGL)
            case '--vulkan': QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.Vulkan)
            case '--d3d11': QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.Direct3D11)
            case '--d3d12': QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.Direct3D12)
            case '--metal': QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.Metal)

            # coarse texture multiplier setting
            case '--coarse':
                try:
                    COARSE_MULTIPLIER = int(argv[argv.index('--coarse') + 1])
                    logger.info(f"COARSE_MULTIPLIER set to: {COARSE_MULTIPLIER}")
                except (IndexError, ValueError):
                    logger.warning('--coarse argument must be followed by an integer value')

            # antialiasing samples setting
            case '--antialiasing':
                try:
                    ANTIALIASING_SAMPLES = int(argv[argv.index('--antialiasing') + 1])
                    logger.info(f"Antialiasing samples set to: {ANTIALIASING_SAMPLES}")
                except (IndexError, ValueError):
                    logger.warning('--antialiasing argument must be followed by an integer value')

            # run shader recompilation before app start
            case '--recompile_shaders':
                recompile_shaders()

            # base SPP setting
            case '--spp':
                try:
                    BASE_SPP = int(argv[argv.index('--spp') + 1])
                    logger.info(f"Base sample per pixel set to: {BASE_SPP}")
                except (IndexError, ValueError):
                    logger.warning('--spp argument must be followed by an integer value')

    logger.info(f"Graphics API set to: {QQuickWindow.graphicsApi()}")

    app = AudioWaveApp(
        coarse_multiplier=COARSE_MULTIPLIER,
        antialiasing_samples=ANTIALIASING_SAMPLES,
        base_spp=BASE_SPP
    )

