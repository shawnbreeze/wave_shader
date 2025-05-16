#version 440

layout(location = 0) in vec4 qt_Vertex;
layout(location = 1) in vec2 qt_MultiTexCoord0;

layout(std140, binding = 0) uniform Params
{
    mat4  qt_Matrix;        // matrix for the texture
    float qt_Opacity;       // opacity
    vec2  resolution;       // audio texture size
    int   texWidth;         // audio texture width
    int   colsUsedFine;     // number of columns in fine texture
    int   colsUsedCoarse;   // number of columns in coarse texture
    float ampScale;         // amplitude scale
    vec4  waveColor;        // color of the wave
    vec4  backColor;        // background color
    float startTime;        // start time in seconds
    int   sampleRate;       // sample rate of audio
    float scaleFactor;      // scale factor for the texture
    int   sppFine;          // samples per pixel for fine texture
    int   sppCoarse;        // samples per pixel for coarse texture
    float pxPerTexel;       // pixels per texel for fine texture switching
} u;

void main()
{
    gl_Position = u.qt_Matrix * qt_Vertex;
}
