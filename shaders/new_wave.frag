#version 440 core

layout(std140, binding = 0) uniform Params
{
    mat4  qt_Matrix;
    float qt_Opacity;
    vec2  resolution;
    int   texWidth;
    int   colsUsedFine;
    int   colsUsedCoarse;
    float ampScale;
    vec4  waveColor;
    vec4  backColor;
    float smoothing;
    float startTime;
    int   sampleRate;
    float scaleFactor;
    int   sppFine;
    int   sppCoarse;
} u;

layout(binding = 1) uniform sampler2D sourceFine;
layout(binding = 2) uniform sampler2D sourceCoarse;

const float baseRight = 0.75;
const float baseLeft  = 0.25;

ivec2 lin2xy (int idx, int w)
{
    return ivec2(idx % w, idx / w);
}

layout(location = 0) out vec4 fragColor;

void main()
{
    // Выбираем текстуру и параметры в зависимости от scaleFactor
    bool useFineTexture = (u.scaleFactor > 70.0);
    
    int colsUsed = useFineTexture ? u.colsUsedFine : u.colsUsedCoarse;
    int samplePerPixel = useFineTexture ? u.sppFine : u.sppCoarse;
    
    int column = int(gl_FragCoord.x);

    float samplesPerPixel = float(colsUsed) /
                            (u.resolution.x * max(u.scaleFactor, 1e-6));

    int startTexel = int(u.startTime * float(u.sampleRate) /
                         float(samplePerPixel));

    float firstF = float(startTexel) + float(column    ) * samplesPerPixel;
    float lastF  = float(startTexel) + float(column + 1) * samplesPerPixel;

    int firstT = int(floor(firstF));
    int lastT  = int(floor(lastF));
    if (lastT <= firstT)
        lastT = firstT + 1;
    if (firstT >= colsUsed) {
        discard;
    }
    lastT = clamp(lastT, firstT + 1, colsUsed);

    float rMin=  1e20, rMax=-1e20,
          lMin=  1e20, lMax=-1e20;

    // Выбираем текстуру для чтения данных
    for (int i = firstT ; i < lastT ; ++i) {
        vec4 s;
        if (useFineTexture) {
            s = texelFetch(sourceFine, lin2xy(i,u.texWidth), 0);
        } else {
            s = texelFetch(sourceCoarse, lin2xy(i,u.texWidth), 0);
        }
        rMin = min(rMin, s.r);   rMax = max(rMax, s.g);
        lMin = min(lMin, s.b);   lMax = max(lMax, s.a);
    }

    rMin = (rMin - 0.5) * 2.0;
    rMax = (rMax - 0.5) * 2.0;
    lMin = (lMin - 0.5) * 2.0;
    lMax = (lMax - 0.5) * 2.0;

    float y = gl_FragCoord.y / u.resolution.y;

    float rBot  = baseRight + rMin * u.ampScale;
    float rTop = baseRight + rMax * u.ampScale;
    float lBot  = baseLeft  + lMin * u.ampScale;
    float lTop = baseLeft  + lMax * u.ampScale;

    float waveR = step(rBot, y) - step(rTop, y);
    float waveL = step(lBot, y) - step(lTop, y);

    if (samplesPerPixel <= 50) {
        int nextColumn = column + 1;
        if (nextColumn < int(u.resolution.x)) {
            float nextFirstF = float(startTexel) + float(nextColumn) * samplesPerPixel;
            int nextFirstT = int(floor(nextFirstF));
            if (nextFirstT < colsUsed) {
                vec4 nextS;
                if (useFineTexture) {
                    nextS = texelFetch(sourceFine, lin2xy(nextFirstT, u.texWidth), 0);
                } else {
                    nextS = texelFetch(sourceCoarse, lin2xy(nextFirstT, u.texWidth), 0);
                }
                float nextRMin = (nextS.r - 0.5) * 2.0;
                float nextRMax = (nextS.g - 0.5) * 2.0;
                float nextLMin = (nextS.b - 0.5) * 2.0;
                float nextLMax = (nextS.a - 0.5) * 2.0;
                float nextRBot = baseRight + nextRMin * u.ampScale;
                float nextRTop = baseRight + nextRMax * u.ampScale;
                float nextLBot = baseLeft  + nextLMin * u.ampScale;
                float nextLTop = baseLeft  + nextLMax * u.ampScale;

                float minR = min(rBot, nextRBot);
                float maxR = max(rBot, nextRBot);
                if (y >= minR && y <= maxR) waveR = 1.0;
                float minRT = min(rTop, nextRTop);
                float maxRT = max(rTop, nextRTop);
                if (y >= minRT && y <= maxRT) waveR = 1.0;
                float minL = min(lBot, nextLBot);
                float maxL = max(lBot, nextLBot);
                if (y >= minL && y <= maxL) waveL = 1.0;
                float minLT = min(lTop, nextLTop);
                float maxLT = max(lTop, nextLTop);
                if (y >= minLT && y <= maxLT) waveL = 1.0;
            }
        }
    }

    fragColor = mix(u.backColor, u.waveColor,
                    clamp(waveR + waveL, 0.0, 1.0));
}
