#version 440

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

layout(binding = 1) uniform sampler2D sourceFine;       // fine texture
layout(binding = 2) uniform sampler2D sourceCoarse;     // coarse texture

const float baseRight = 0.75;               // right channel base position
const float baseLeft  = 0.25;               // left channel base position
const float normFactor = 2.0;               // нормализующий множитель (r-0.5)*2.0
const float halfValue = 0.5;                // половина для нормализации

// pre-calculate the division coordinate without modulus
ivec2 lin2xy (int idx, int w)
{
    return ivec2(idx % w, idx / w);
}

// Function for reading data from texture and normalization
vec4 getNormalizedSample(int idx, bool useFine) {
    vec4 s = useFine
           ? texelFetch(sourceFine, lin2xy(idx, u.texWidth), 0)
           : texelFetch(sourceCoarse, lin2xy(idx, u.texWidth), 0);

    // Normalize all components in one call
    return (s - halfValue) * normFactor;
}

layout(location = 0) out vec4 fragColor;

void main()
{
    // dynamic fine texture selection
    float pixelsPerCoarseTexel = (u.resolution.x * u.scaleFactor) / float(u.colsUsedCoarse);
    bool useFineTexture = (pixelsPerCoarseTexel > u.pxPerTexel);
    int colsUsed = useFineTexture ? u.colsUsedFine : u.colsUsedCoarse;
    int samplePerPixel = useFineTexture ? u.sppFine : u.sppCoarse;

    int column = int(gl_FragCoord.x);
    float y = gl_FragCoord.y / u.resolution.y;

    float samplesPerPixel = float(colsUsed) / (u.resolution.x * max(u.scaleFactor, 1e-6));
    bool isHighZoom = (samplesPerPixel < 50.0);

    int startTexel = int(u.startTime * float(u.sampleRate) / float(samplePerPixel));
    float firstF = float(startTexel) + float(column) * samplesPerPixel;
    float lastF  = firstF + samplesPerPixel;

    int firstT = int(floor(firstF));
    int lastT  = int(floor(lastF));
    
    if (lastT <= firstT)
        lastT = firstT + 1;
    if (firstT >= colsUsed) {
        discard;
    }
    lastT = min(lastT, colsUsed);

    // Initialization of minimum and maximum values
    vec4 minMax = vec4(1e20, -1e20, 1e20, -1e20); // rMin, rMax, lMin, lMax

    // Collecting range data without branching within a loop
    for (int i = firstT; i < lastT; ++i) {
        vec4 norm = getNormalizedSample(i, useFineTexture);

        // Updating the minimum and maximum values
        minMax.x = min(minMax.x, norm.x);  // rMin
        minMax.y = max(minMax.y, norm.y);  // rMax
        minMax.z = min(minMax.z, norm.z);  // lMin
        minMax.w = max(minMax.w, norm.w);  // lMax
    }

    // Computation of wave boundaries taking into account the scale
    float rBot = baseRight + minMax.x * u.ampScale;
    float rTop = baseRight + minMax.y * u.ampScale;
    float lBot = baseLeft  + minMax.z * u.ampScale;
    float lTop = baseLeft  + minMax.w * u.ampScale;

    float waveR = step(rBot, y) - step(rTop, y);
    float waveL = step(lBot, y) - step(lTop, y);

    // Optimized line drawing at high zoom level
    if (isHighZoom) {
        int nextColumn = column + 1;
        if (nextColumn < int(u.resolution.x)) {
            float nextFirstF = float(startTexel) + float(nextColumn) * samplesPerPixel;
            int nextFirstT = int(floor(nextFirstF));
            
            if (nextFirstT < colsUsed) {
                // Get the data of the next column in one call
                vec4 nextNorm = getNormalizedSample(nextFirstT, useFineTexture);

                // Calculate the bounds for the next column
                float nextRBot = baseRight + nextNorm.x * u.ampScale;
                float nextRTop = baseRight + nextNorm.y * u.ampScale;
                float nextLBot = baseLeft  + nextNorm.z * u.ampScale;
                float nextLTop = baseLeft  + nextNorm.w * u.ampScale;

                // Check for the right channel (lower and upper limits)
                if ((y >= min(rBot, nextRBot) && y <= max(rBot, nextRBot)) || 
                    (y >= min(rTop, nextRTop) && y <= max(rTop, nextRTop))) {
                    waveR = 1.0;
                }
                
                // Check for the left channel (lower and upper limits)
                if ((y >= min(lBot, nextLBot) && y <= max(lBot, nextLBot)) || 
                    (y >= min(lTop, nextLTop) && y <= max(lTop, nextLTop))) {
                    waveL = 1.0;
                }
            }
        }
    }

    fragColor = mix(u.backColor, u.waveColor, clamp(waveR + waveL, 0.0, 1.0));
}
