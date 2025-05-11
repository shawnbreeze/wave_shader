#version 440

layout(std140, binding = 0) uniform Params {
    mat4  qt_Matrix;         // transformation matrix
    float qt_Opacity;        // opacity
    vec2  resolution;        // screen resolution
    int   texWidth;          // width of the texture
    int   colsUsed;          // totalnumber of working pixels in the texture
    float ampScale;          // Amplitude scale factor
    vec4  waveColor;         // Color of the waveform
    vec4  backColor;         // Background color
    float smoothing;         // Smoothing factor
    float startTime;         // Initial time in seconds
    int   sampleRate;        // Sampling rate (samples per second) - for startTime (sec) to sample conversion
    float scaleFactor;       // Display scale factor (1 - fullwidth view)
    int   samplePerPixel;    // Number of samples per pixel
} u;

layout(binding = 1) uniform sampler2D source;
layout(location = 0) out vec4 FragColor;

const float baseRight = 0.75;       // Right channel base Y coordinate
const float baseLeft  = 0.25;       // Left channel base Y coordinate

// Function to retrieve value from texture based on coordinates
vec4 getWaveValue(float dataIdx) {
    dataIdx = clamp(dataIdx, 0.0, float(u.colsUsed - 1));

    // Determine texture size
    ivec2 texSize = textureSize(source, 0);

    // Compute texture coordinates
    float texX = (mod(dataIdx, float(u.texWidth)) + 1.5);
    float texY = floor(dataIdx / float(u.texWidth)) + 1.5;
    vec2 texCoord = vec2(texX / float(texSize.x), texY / float(texSize.y));

    // Fetch value
    return texture(source, texCoord);
}

// Function to collect extremes using a fixed number of samples
vec4 collectExtremes(float leftIdx, float rightIdx, int maxSamples) {
    float rMin = 1.0, rMax = -1.0;
    float lMin = 1.0, lMax = -1.0;

    // Always check left and right boundaries of the range
    vec4 leftPixel = getWaveValue(leftIdx);
    vec4 rightPixel = getWaveValue(rightIdx);

    rMin = min(leftPixel.r * 2.0 - 1.0, rightPixel.r * 2.0 - 1.0);
    rMax = max(leftPixel.g * 2.0 - 1.0, rightPixel.g * 2.0 - 1.0);
    lMin = min(leftPixel.b * 2.0 - 1.0, rightPixel.b * 2.0 - 1.0);
    lMax = max(leftPixel.a * 2.0 - 1.0, rightPixel.a * 2.0 - 1.0);

    // Fixed number of samples for HLSL compatibility
    float dataRange = rightIdx - leftIdx;
    int steps = min(maxSamples, 32); // Hard limit for HLSL

    if (steps > 2 && dataRange > 2.0) {
        float stepSize = dataRange / float(steps - 1);

        // Use fixed iterations with unroll hint
        #pragma optionNV(unroll all)
        for (int i = 1; i < 16; i++) {
            if (i >= steps - 1) break; // Terminate loop when done

            float pos = leftIdx + stepSize * float(i);
            vec4 pixel = getWaveValue(pos);

            // Decode values
            float r_min = pixel.r * 2.0 - 1.0;
            float r_max = pixel.g * 2.0 - 1.0;
            float l_min = pixel.b * 2.0 - 1.0;
            float l_max = pixel.a * 2.0 - 1.0;

            // Update extremes
            rMin = min(rMin, r_min);
            rMax = max(rMax, r_max);
            lMin = min(lMin, l_min);
            lMax = max(lMax, l_max);
        }
    }

    // Pack extremes into a vector
    return vec4(rMin, rMax, lMin, lMax);
}

void main()
{
    // Ensure sampleRate is nonzero to avoid division by zero
    float effectiveSampleRate = max(1.0, float(u.sampleRate));

    // Compute start sample index explicitly
    float startSampleIndex = u.startTime * effectiveSampleRate;

    // Ensure samplePerPixel is nonzero
    float effectiveSamplePerPixel = max(1.0, float(u.samplePerPixel));

    // Convert to texture indices
    float startTexIndex = startSampleIndex / effectiveSamplePerPixel;

    // Scaled factor: number of texture elements per screen pixel
    float scaledPixelWidth = float(u.colsUsed) / (u.resolution.x * max(0.1, u.scaleFactor));

    // Current pixel X-coordinate relative to the screen start
    float pixelX = gl_FragCoord.x;

    // Calculate indices accounting for start position and scale
    float leftIdx = startTexIndex + (pixelX - 0.5) * scaledPixelWidth;
    float rightIdx = startTexIndex + (pixelX + 0.5) * scaledPixelWidth;

    // Clamp indices within allowable bounds
    leftIdx = max(0.0, leftIdx);
    rightIdx = min(float(u.colsUsed - 1), rightIdx);

    float rMin = 1.0, rMax = -1.0;
    float lMin = 1.0, lMax = -1.0;

    float dataRange = rightIdx - leftIdx;

    if (dataRange <= 1.0) {
        vec4 pixel = getWaveValue(leftIdx);
        rMin = pixel.r * 2.0 - 1.0;
        rMax = pixel.g * 2.0 - 1.0;
        lMin = pixel.b * 2.0 - 1.0;
        lMax = pixel.a * 2.0 - 1.0;
    } else {
        vec4 extremes = collectExtremes(leftIdx, rightIdx, 16);
        rMin = extremes.x;
        rMax = extremes.y;
        lMin = extremes.z;
        lMax = extremes.w;

        if (dataRange > 16.0) {
            float q1 = leftIdx + dataRange * 0.25;
            float q2 = leftIdx + dataRange * 0.5;
            float q3 = leftIdx + dataRange * 0.75;

            vec4 p1 = getWaveValue(q1);
            vec4 p2 = getWaveValue(q2);
            vec4 p3 = getWaveValue(q3);

            rMin = min(rMin, min(p1.r * 2.0 - 1.0, min(p2.r * 2.0 - 1.0, p3.r * 2.0 - 1.0)));
            rMax = max(rMax, max(p1.g * 2.0 - 1.0, max(p2.g * 2.0 - 1.0, p3.g * 2.0 - 1.0)));
            lMin = min(lMin, min(p1.b * 2.0 - 1.0, min(p2.b * 2.0 - 1.0, p3.b * 2.0 - 1.0)));
            lMax = max(lMax, max(p1.a * 2.0 - 1.0, max(p2.a * 2.0 - 1.0, p3.a * 2.0 - 1.0)));
        }
    }

    float rTop = baseRight + (rMax * u.ampScale);
    float rBot = baseRight + (rMin * u.ampScale);
    float lTop = baseLeft  + (lMax * u.ampScale);
    float lBot = baseLeft  + (lMin * u.ampScale);

    float y = gl_FragCoord.y / u.resolution.y;
    float pixelHeight = 1.0 / u.resolution.y;

    float drTop_dx = abs(dFdx(rTop));
    float drBot_dx = abs(dFdx(rBot));
    float dlTop_dx = abs(dFdx(lTop));
    float dlBot_dx = abs(dFdx(lBot));

    float max_deriv_x = max(max(drTop_dx, drBot_dx), max(dlTop_dx, dlBot_dx));

    float dynamicSmoothing = max_deriv_x * .05;
    float effectiveSmoothing = max(u.smoothing, max(pixelHeight * 0.5, dynamicSmoothing));

    float waveR = smoothstep(rBot - effectiveSmoothing, rBot, y) - smoothstep(rTop, rTop + effectiveSmoothing, y);
    float waveL = smoothstep(lBot - effectiveSmoothing, lBot, y) - smoothstep(lTop, lTop + effectiveSmoothing, y);

    FragColor = mix(u.backColor, u.waveColor, clamp(waveR + waveL, 0.0, 1.0));
}