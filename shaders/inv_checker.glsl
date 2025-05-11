
#version 440

// ---------- стандартный UBO Qt Quick (можно и не приводить, но не мешает)
layout(std140, binding = 0) uniform Params {
    mat4  qt_Matrix;
    float qt_Opacity;
} u;

// ---------- texture property (первая = unit 1)
layout(binding = 1) uniform sampler2D source;

// ---------- varyings с ОБЯЗАТЕЛЬНЫМ layout(location)
layout(location = 0) in  vec2 qt_TexCoord0;   // из вершинного
layout(location = 0) out vec4 FragColor;      // к экрану

void main()
{
    vec4 src = texture(source, qt_TexCoord0);   // исходный цвет
    vec3 inv = vec3(1.0) - src.rgb;             // инверсия RGB
    FragColor = vec4(inv, src.a) * u.qt_Opacity;
}