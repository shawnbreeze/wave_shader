#version 440 core
/*  Минимум, необходимый ShaderEffect:
    4-е вершины «квадрата», уже содержащие NDC-координаты –1…+1   */
layout(location = 0) in vec4 qt_Vertex;
layout(location = 1) in vec2 qt_MultiTexCoord0;

layout(std140, binding = 0) uniform Params {
    mat4  qt_Matrix;
} u;

/* Ничего, кроме позиции, не передаём */
void main()
{
    gl_Position = u.qt_Matrix * qt_Vertex;   // honour Qt-Quick трансформации
}
