#version 440 core

layout(std140, binding = 0) uniform Params
{
    mat4  qt_Matrix;          // уже использован в VS
    float qt_Opacity;
    vec2  resolution;         // px
    int   texWidth;           // ширина текстуры (px)
    int   colsUsed;           // реально занятых текселей
    float ampScale;           // масштаб амплитуды (px / 1.0)
    vec4  waveColor;          // цвет линии
    vec4  backColor;          // фон
    float smoothing;          // px
    float startTime;          // сек
    int   sampleRate;         // Гц
    float scaleFactor;        // 1.0 – «вся длина»
    int   samplePerPixel;     // сэмплов на экранный пиксель
} u;

layout(binding = 1) uniform sampler2D source;

const float baseRight = 0.75;
const float baseLeft  = 0.25;

/*--------------------------------------------------------------*/
/*  Вспомогательное: линейный индекс  → (x,y) в текстуре        */
ivec2 lin2xy (int idx, int w)
{
    return ivec2(idx % w, idx / w);
}
/*--------------------------------------------------------------*/

layout(location = 0) out vec4 fragColor;

void main()
{
    /* ===== 1. экранный столбец, которым занимаемся ================ */
    int column = int(gl_FragCoord.x);               // 0 … width-1

    /* ===== 2. сколько тэкселей приходится на 1 столбец? =========== *
     * при scaleFactor>1 => приближение => МЕНЬШЕ тэкселей на px       */
    float samplesPerPixel = float(u.colsUsed) /
                            (u.resolution.x * max(u.scaleFactor, 1e-6));

    /* ===== 3. смещение по времени в тэкселях ======================= */
    int startTexel = int(u.startTime * float(u.sampleRate) /
                         float(u.samplePerPixel));

    /* ===== 4. «плавающий» диапазон для данного столбца ============ */
    float firstF = float(startTexel) + float(column    ) * samplesPerPixel;
    float lastF  = float(startTexel) + float(column + 1) * samplesPerPixel;

    /* округляем вниз / up-cast’ом, чтобы не потерять покрытие */
    int firstT = int(floor(firstF));
    int lastT  = int(floor(lastF));

    /* гарантируем, что диапазон содержит хотя бы ОДИН тэксель */
    if (lastT <= firstT)
        lastT = firstT + 1;

    /* и, разумеется, не выходим за реальное заполнение текстуры */
    if (firstT >= u.colsUsed) {
        discard;                            // столбец полностью вне данных
    }
    lastT = clamp(lastT, firstT + 1, u.colsUsed);

    /* ---------- 2. Считаем экстремумы внутри этого диапазона ----- */
    float rMin=  1e20, rMax=-1e20,
          lMin=  1e20, lMax=-1e20;

    for (int i = firstT ; i < lastT ; ++i) {
        vec4 s = texelFetch(source, lin2xy(i,u.texWidth), 0);
        rMin = min(rMin, s.r);   rMax = max(rMax, s.g);
        lMin = min(lMin, s.b);   lMax = max(lMax, s.a);
    }

    /* ---------- 3. Конвертируем “0…1” → амплитуда –1…+1 ---------- */
    rMin = (rMin - 0.5) * 2.0;
    rMax = (rMax - 0.5) * 2.0;
    lMin = (lMin - 0.5) * 2.0;
    lMax = (lMax - 0.5) * 2.0;

    /* ---------- 4. Вычисляем, перекрывает ли наш фрагмент Y-диапазон */
    float y = gl_FragCoord.y / u.resolution.y;         // 0…1

    float rLow  = baseRight + rMin * u.ampScale;
    float rHigh = baseRight + rMax * u.ampScale;
    float lLow  = baseLeft  + lMin * u.ampScale;
    float lHigh = baseLeft  + lMax * u.ampScale;

    float sm = max(u.smoothing, 0.0) / u.resolution.y; // сглаживание → 0…1

    float rightMask =
          smoothstep(rLow  - sm, rLow , y) *
          smoothstep(rHigh + sm, rHigh, y);

    float leftMask  =
          smoothstep(lLow  - sm, lLow , y) *
          smoothstep(lHigh + sm, lHigh, y);

    float alpha = clamp(max(leftMask, rightMask), 0.0, 1.0);

    /* ---------- 5. Финальный цвет --------------------------------- */
    fragColor   = mix(u.backColor, u.waveColor, alpha);
}
