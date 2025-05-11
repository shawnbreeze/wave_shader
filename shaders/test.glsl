#version 440

layout(std140, binding = 0) uniform Params {
    mat4  qt_Matrix;
    vec2  resolution;  // текущее разрешение контейнера с шейдером
    int   colsUsed; // общее количество "полезных" пикселей в текстуре
};

layout(location = 0) in  vec2 qt_TexCoord0; // получаем
layout(location = 0) out vec4 FragColor; // отдаём

void main() {
    vec2 pixelCoord = qt_TexCoord0.xy * resolution;
    ivec2 pixel = ivec2(floor(pixelCoord));

    int yFlipped = int(resolution.y) - 1 - pixel.y;
    int pixelID = yFlipped * int(resolution.x) + pixel.x;

    // используйте pixelID как нужно
    // например, отладочный цвет:
    float gray = float(pixelID) / (resolution.x * resolution.y);
    gl_FragColor = vec4(vec3(gray), 1.0);
}
