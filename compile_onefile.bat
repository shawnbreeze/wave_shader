python -m nuitka --mingw64 ^
--windows-icon-from-ico=icon.ico ^
--plugin-enable=pyside6 ^
--include-data-files=shaders/new_wave.frag.qsb=shaders/new_wave.frag.qsb ^
--include-data-files=shaders/new_wave.vert.qsb=shaders/new_wave.vert.qsb ^
--include-qt-plugins=qml ^
--standalone ^
--onefile ^
--windows-console-mode=attach ^
--jobs=12 ^
test.py