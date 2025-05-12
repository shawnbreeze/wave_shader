import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Controls.Fusion // Add import for base style customization

// Set global style for the application
ApplicationWindow {
    id: root
    width: 1200; height: 720; visible: true
    property int colsUsed: cols_Used
    // Fix audioDuration definition to avoid self-reference
    property real audioLength: audioDuration  // Get value from Python context
    
    color: "#121212"  // Set dark background for the window

    // Get values from Python context, avoiding self-references
    property int spx: samplePerPixel
    property int sampleRateValue: sampleRate // Renamed to avoid self-reference
    property real viewStartTime: 0.0  // Current time in sec calculated in QML

    // Properties for navigation and zooming
    property real startPosition: 0.0  // Initial position in range [0,1]
    property real scaleFactor: 1.0    // Scale (1.0 = normal zoom)
    property real visiblePortion: Math.min(1.0, 1.0 / scaleFactor) // Visible portion of waveform

    // Parameters for zooming
    property real minScale: 1.0  // Minimum scale
    property real maxScale: Screen.width > 0 ? Math.max(1.0, (colsUsed / Screen.width)) : 1.0  // Limit Maximum scale
    property real baseZoomSpeed: 1.5 // Base zoom speed multiplier
    property real fineZoomSpeedFactor: 0.5 // Factor for precise zooming with Ctrl key
    property real dynamicZoomFactor: 0.9 // Dynamic acceleration factor based on wheel speed
    property real maxZoomMultiplier: 4.0 // Maximum zoom acceleration multiplier

    /* --- PROPERTIES FOR ANCHORED ZOOMING --- */
    property bool zooming: false          // Flag indicating if zoom animation is active
    property real anchorMouseX: 0.0       // Normalized X-coordinate of the mouse (0-1) at zoom start
    property real anchorCursorPos: 0.0    // Audio position to remain under the cursor

    // Добавляем свойства для обеих текстур
    property int spxFine: fineSamplePerPixel
    property int spxCoarse: coarseSamplePerPixel
    property int colsUsedFine: fineColsUsed
    property int colsUsedCoarse: coarseColsUsed
    property string activeTexture: (scaleFactor > 50) ? "Детальная" : "Грубая"

    function formatTime(seconds) {
        var mins = Math.floor(seconds / 60)
        var secs = Math.floor(seconds % 60)
        var ms = Math.floor((seconds % 1) * 100)
        return mins.toString().padStart(2, "0") + ":" +
               secs.toString().padStart(2, "0") + "." +
               ms.toString().padStart(2, "0")
    }

    Component.onCompleted: {
        console.log("Sample per pixel:", spx)
        console.log("Sample rate:", sampleRateValue)
        console.log("Audio duration:", audioLength)
        console.log("Visible portion:", visiblePortion)
    }

    // Update startTime when startPosition changes
    onStartPositionChanged: {
        // Calculate time based on position and duration
        var newTime = startPosition * audioLength  // Using audioLength
        viewStartTime = newTime
    }

    // Update visiblePortion when scaleFactor changes
    onScaleFactorChanged: {
        visiblePortion = Math.min(1.0, 1.0 / scaleFactor)
        if (zooming) {
            // When zoom animation is active, adjust startPosition so anchorCursorPos remains under anchorMouseX
            startPosition = Math.max(0.0,
                            Math.min(1.0 - visiblePortion,
                                     anchorCursorPos - anchorMouseX * visiblePortion))
        } else {
            var maxPosition = Math.max(0.0, 1.0 - visiblePortion)
            if (startPosition > maxPosition) {
                startPosition = maxPosition
            }
        }
    }

    // X-scrollbar for track navigation
    Rectangle {
        id: navBarBackground
        anchors.top: parent.top
        anchors.topMargin: 10 // Top margin (formerly infoText)
        anchors.left: parent.left
        anchors.right: parent.right
        height: 50
        color: "#202020"

        Row {
            anchors.fill: parent
            spacing: 10

            // Main scrollbar for navigation
            Item {
                id: scrollBarContainer
                width: parent.width
                height: parent.height
                clip: true // Clip contents beyond borders

                // Scrollbar background
                Rectangle {
                    anchors.fill: parent
                    color: "#303030"
                    radius: 3
                    z: 0 // Bottom layer
                }

                /* ---------- mini-wave ---------- */
                Item {
                    id: miniWaveLayer
                    anchors.fill: parent
                    opacity: 0.5          // Overall opacity for the thumbnail
                    z: 1                   // Positioned above background, below ScrollBar
                    layer.enabled: true    // Enable layer for correct alpha

                    ShaderEffect {
                        id: scrollBarWaveformThumbnail
                        anchors.fill: parent

                        /* shader uniforms */
                        property variant   source: waveImg
                        property int       colsUsed: root.colsUsed
                        property vector2d  resolution: Qt.vector2d(width, height)
                        property int       texWidth: waveImg.width
                        property real      ampScale: 0.2  // ~100% height without cropping
                        property real      smoothing: 0
                        property vector4d  waveColor: Qt.vector4d(0.28,0.85,0.59,1.0) // black waveform originally
                        property vector4d  backColor: Qt.vector4d(0, 0, 0, 0)
                        property real      startTime: 0.0
                        property int       sampleRate: root.sampleRateValue
                        // Удаляем дублирующееся свойство, оно определено ниже
                        // property real      scaleFactor: 1.0
                        property int       samplePerPixel: root.spx
                        property variant sourceFine: fineTexture
                        property variant sourceCoarse: coarseTexture
                        property int colsUsedFine: root.colsUsedFine
                        property int colsUsedCoarse: root.colsUsedCoarse
                        property int sppFine: root.spxFine
                        property int sppCoarse: root.spxCoarse
                        property real scaleFactor: 1.0
//                        fragmentShader: "shaders/waveform_t.frag.qsb"
//                        vertexShader:   "shaders/waveform_t.vert.qsb"
                        fragmentShader: "shaders/new_wave.frag.qsb"
                        vertexShader:   "shaders/new_wave.vert.qsb"
                    }
                }

                // Navigation scrollbar
                ScrollBar {
                    id: navigationScrollBar
                    anchors.fill: parent
                    orientation: Qt.Horizontal
                    hoverEnabled: true 
                    z: 2 // Top layer, above thumbnail

                    // Handle size depends on zoom level
                    size: visiblePortion

                    // Initial position
                    position: startPosition

                    // Scrollbar style
                    contentItem: Rectangle {
                        id: scrollBarHandle
                        implicitWidth: 200
                        implicitHeight: 20
                        radius: 3
                        // Base handle color (opaque)
                        color: "#A0A0A0" 
                        // Initial opacity
                        opacity: navigationScrollBar.hovered ? 0.5 : 0.3

                        // Animation for opacity property
                        Behavior on opacity {
                            NumberAnimation {
                                duration: 150
                                easing.type: Easing.InOutCirc
                            }
                        }
                        
                        border.color: "black" // Keep black border if needed
                        border.width: 1

                        // No text inside the handle
                    }

                    /* --- internal helper properties --- */
                    property real _prevPos: position
                    property real _lastDelta: 0

                    // React to scrollbar position changes
                    onPositionChanged: {
                        if (pressed) {  // Move waveform only while dragging
                            root.startPosition = position
                            _lastDelta = position - _prevPos
                            _prevPos   = position
                        }
                    }

                    // On handle release, start inertia animation
                    onPressedChanged: {
                        if (pressed) {  // Drag start
                            _prevPos = position
                            if (scrollAnimation.running) scrollAnimation.stop()
                        } else {  // Drag end – inertia
                            if (Math.abs(_lastDelta) > 0.01) {
                                return;  // If movement > 0.01, it's a drag – do not start animation
                            }
                            
                            var maxPos   = Math.max(0, 1 - root.visiblePortion)
                            var target   = root.startPosition + _lastDelta * 10   // inertia coefficient
                            target       = Math.max(0, Math.min(maxPos, target))

                            if (scrollAnimation.running) scrollAnimation.stop()
                            
                            scrollAnimation.from = root.startPosition
                            scrollAnimation.to   = target
                            scrollAnimation.start()
                        }
                    }

                    // Update scrollbar position on external startPosition change
                    Binding {
                        target: navigationScrollBar
                        property: "position"
                        value: startPosition
                    }
                }
            }
            // Removed element for current position display (timeDisplay)
        }
    }

    // X-scale bar for zooming
    Rectangle {
        id: scaleBarBackground
        anchors.top: navBarBackground.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 0
    }

    // Animation for smooth zoom change
    NumberAnimation {
        id: scaleAnimation
        target: root
        property: "scaleFactor"
        duration: 300 // Animation duration
        easing.type: Easing.OutCubic // Smooth deceleration
        onStopped: {
            root.zooming = false // Reset flag when animation stops
        }
    }

    /* --- inertia animation for scrolling --- */
    NumberAnimation {
        id: scrollAnimation
        target: root
        property: "startPosition"
        duration: 500
        easing.type: Easing.OutCubic
    }

    // Первый Image элемент
    Image {
        id: waveImg
        source: waveTextureUrl  // URL от провайдера
        visible: false
        layer.smooth: false
        smooth: false
        mipmap: false
        cache: true  // Отключаем кэширование, чтобы принудительно перезагружать
        asynchronous: true // Асинхронная загрузка для больших изображений
        
        // Обработка ошибок загрузки
        onStatusChanged: {
            if (status === Image.Ready) {
                console.log("Image loaded successfully: " + width + "x" + height)
            } else if (status === Image.Loading) {
                console.log("Image loading...")
            } else if (status === Image.Error) {
                console.error("Error loading image: " + source)
            }
        }
    }

    // Загружаем обе текстуры
    Image {
        id: fineTexture
        source: fineTextureUrl
        visible: false
        layer.smooth: false
        smooth: false
        mipmap: false
        cache: true
        asynchronous: true
        
        onStatusChanged: {
            if (status === Image.Ready) {
                console.log("Fine texture loaded: " + width + "x" + height)
            } else if (status === Image.Error) {
                console.error("Error loading fine texture")
            }
        }
    }
    
    Image {
        id: coarseTexture
        source: coarseTextureUrl
        visible: false
        layer.smooth: false
        smooth: false
        mipmap: false
        cache: true
        asynchronous: true
        
        onStatusChanged: {
            if (status === Image.Ready) {
                console.log("Coarse texture loaded: " + width + "x" + height)
            } else if (status === Image.Error) {
                console.error("Error loading coarse texture")
            }
        }
    }

    ShaderEffect {
        id: waveShader
//        antialiasing: true
        layer.enabled: true
        layer.samples: 8
        smooth: true
        anchors.top: scaleBarBackground.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 5
        property variant source: waveImg
        property int colsUsed: root.colsUsed
        property vector2d resolution: Qt.vector2d(width, height)
        property int texWidth: waveImg.width
        property var ampScale: 0.23
        property var smoothing: 9999
        property vector4d waveColor: Qt.vector4d(0.28,0.85,0.59,1.0)
        property vector4d backColor: Qt.vector4d(0.0,0.0,0.0,1.0)
        property real startTime: root.viewStartTime
        property int sampleRate: root.sampleRateValue
        // Удаляем дублирующееся свойство, оно определено ниже
        // property real scaleFactor: root.scaleFactor
        property int samplePerPixel: root.spx
        property variant sourceFine: fineTexture
        property variant sourceCoarse: coarseTexture
        property int colsUsedFine: root.colsUsedFine
        property int colsUsedCoarse: root.colsUsedCoarse
        property int sppFine: root.spxFine
        property int sppCoarse: root.spxCoarse
        property real scaleFactor: root.scaleFactor
//        fragmentShader: "shaders/waveform_t.frag.qsb"
//        vertexShader: "shaders/waveform_t.vert.qsb"
        fragmentShader: "shaders/new_wave.frag.qsb"
        vertexShader:   "shaders/new_wave.vert.qsb"
        
        // Debug handler removed
        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.NoButton // Only process wheel events, no clicks
            onWheel: function(wheel) {
                if (scaleAnimation.running) {
                    scaleAnimation.stop()
                }
                var oldScale = root.scaleFactor
                var currentAnimatedPosition = root.startPosition
                var zoomIn = wheel.angleDelta.y > 0
                var wheelIntensity = Math.abs(wheel.angleDelta.y) / 120.0
                var dynamicMultiplier = Math.min(maxZoomMultiplier, 1.0 + 
                                        (Math.pow(wheelIntensity, 1.3) * dynamicZoomFactor))
                var zoomFactor = zoomIn ? 1.0 : 0.9 
                var effectiveSpeed = baseZoomSpeed * dynamicMultiplier * zoomFactor
                if (wheel.modifiers & Qt.ControlModifier) {
                    effectiveSpeed = baseZoomSpeed * fineZoomSpeedFactor
                }
                effectiveSpeed = Math.max(1.05, effectiveSpeed)
                var newScale = zoomIn ? 
                    Math.min(maxScale, oldScale * effectiveSpeed) : 
                    Math.max(minScale, oldScale / effectiveSpeed)
                if (Math.abs(newScale - oldScale) < 0.0001) {
                    wheel.accepted = true
                    return
                }
                var mouseX = wheel.x / width
                var oldVisiblePortion = Math.min(1.0, 1.0 / oldScale)
                var cursorPositionInAudio = currentAnimatedPosition + mouseX * oldVisiblePortion
                var sampleBefore = Math.floor(cursorPositionInAudio * root.audioLength * root.sampleRateValue)
                var newVisiblePortion = Math.min(1.0, 1.0 / newScale)
                var targetNewPosition = cursorPositionInAudio - mouseX * newVisiblePortion
                targetNewPosition = Math.max(0.0, Math.min(1.0 - newVisiblePortion, targetNewPosition))
                var cursorPositionAfterTarget = targetNewPosition + mouseX * newVisiblePortion
                var sampleAfter = Math.floor(cursorPositionAfterTarget * root.audioLength * root.sampleRateValue)
                root.anchorMouseX = mouseX
                root.anchorCursorPos = cursorPositionInAudio
                root.zooming = true
                scaleAnimation.from = oldScale
                scaleAnimation.to = newScale
                scaleAnimation.start()
                wheel.accepted = true
            }
        }
        
        // Display current zoom information
        Text {
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: 10
            color: "white"
            text: "Position: " + root.viewStartTime.toFixed(2) + " sec | Sample index: " + 
                  Math.floor(root.viewStartTime * root.sampleRateValue) + " | Texture index: " + 
                  Math.floor(root.viewStartTime * root.sampleRateValue / 
                  (root.scaleFactor > 50 ? root.spxFine : root.spxCoarse)) + " | Scale: ×" + 
                  root.scaleFactor.toFixed(1) + " | Текущая текстура: " + root.activeTexture;
            font.pixelSize: 15
        }
    }

    // Добавляем отладочное отображение загруженного изображения
    Rectangle {
        id: debugImageContainer
        anchors.right: parent.right
        anchors.top: navBarBackground.bottom
        width: 200
        height: 200
        color: "#191919"
        border.color: "white"
        border.width: 1
        visible: typeof showDebugImage !== 'undefined' && showDebugImage
        
        Text {
            id: debugTitle
            anchors.top: parent.top
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Debug: Image Provider"
            color: "white"
            font.pixelSize: 12
        }
        
        Column {
            anchors.top: debugTitle.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.margins: 5
            
            Text {
                width: parent.width
                text: "Provider ID: " + (typeof providerID !== 'undefined' ? providerID : "unknown")
                color: "white"
                font.pixelSize: 10
                elide: Text.ElideRight
            }
            
            Text {
                width: parent.width
                text: "Created: " + (typeof providerCreationTime !== 'undefined' ? providerCreationTime : "unknown")
                color: "white"
                font.pixelSize: 10
            }
            
            Text {
                width: parent.width
                text: "Image: " + (waveImg.status === Image.Ready ? waveImg.width + "×" + waveImg.height : "not loaded")
                color: waveImg.status === Image.Ready ? "lightgreen" : "red"
                font.pixelSize: 10
            }
            
            Text {
                width: parent.width
                text: "Status: " + (waveImg.status === Image.Ready ? "Ready" : 
                                   waveImg.status === Image.Loading ? "Loading" : "Error")
                color: waveImg.status === Image.Ready ? "lightgreen" : 
                       waveImg.status === Image.Loading ? "yellow" : "red"
                font.pixelSize: 10
            }
        }
        
        // Второй Image элемент с тем же URL
        Image {
            id: debugImage
            source: (root.scaleFactor > 50) ? fineTextureUrl : coarseTextureUrl
            anchors.bottom: parent.bottom
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width - 10
            height: parent.height - 80
            fillMode: Image.PreserveAspectFit
            cache: false
            smooth: false
            
            Text {
                anchors.bottom: parent.bottom
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Зеленая метка в верхнем\nправом углу = ImageProvider"
                color: "lightgreen"
                font.pixelSize: 10
                horizontalAlignment: Text.AlignHCenter
            }
        }
    }
}

