#version 440

layout(std140, binding = 0) uniform Params {
    mat4  qt_Matrix;
    float qt_Opacity;
    vec2  resolution;
    int   texWidth;
    int   colsUsed;
    float ampScale;
    vec4  waveColor;
    vec4  backColor;
    float smoothing;
    float startTime;     // Начальное время в секундах
    int   sampleRate;    // Частота дискретизации (сэмплов в секунду)
    float scaleFactor;   // Масштаб отображения
    int   samplePerPixel; // Количество сэмплов на пиксель
} u;

layout(binding = 1) uniform sampler2D source;
layout(location = 0) out vec4 FragColor;

const float baseRight = 0.75;
const float baseLeft  = 0.25;

// Функция для получения значения из текстуры с учетом координат
vec4 getWaveValue(float dataIdx) {
    dataIdx = clamp(dataIdx, 0.0, float(u.colsUsed - 1));
    
    // Определяем размер текстуры
    ivec2 texSize = textureSize(source, 0);

    // Вычисляем координаты в текстуре
    float texX = (mod(dataIdx, float(u.texWidth)) + 0.5);
    float texY = floor(dataIdx / float(u.texWidth)) + 0.5;
    vec2 texCoord = vec2(texX / float(texSize.x), texY / float(texSize.y));

    // Берём значение 
    return texture(source, texCoord);
}

// Функция для сбора экстремумов с фиксированным количеством семплов
vec4 collectExtremes(float leftIdx, float rightIdx, int maxSamples) {
    float rMin = 1.0, rMax = -1.0;
    float lMin = 1.0, lMax = -1.0;
    
    // Обязательно проверяем левую и правую границы диапазона
    vec4 leftPixel = getWaveValue(leftIdx);
    vec4 rightPixel = getWaveValue(rightIdx);
    
    rMin = min(leftPixel.r * 2.0 - 1.0, rightPixel.r * 2.0 - 1.0);
    rMax = max(leftPixel.g * 2.0 - 1.0, rightPixel.g * 2.0 - 1.0);
    lMin = min(leftPixel.b * 2.0 - 1.0, rightPixel.b * 2.0 - 1.0);
    lMax = max(leftPixel.a * 2.0 - 1.0, rightPixel.a * 2.0 - 1.0);
    
    // Фиксированное количество семплов для HLSL совместимости
    float dataRange = rightIdx - leftIdx;
    int steps = min(maxSamples, 32); // Жестко ограничиваем для HLSL
    
    if (steps > 2 && dataRange > 2.0) {
        float stepSize = dataRange / float(steps - 1);
        
        // Используем фиксированное количество итераций с unroll hint
        #pragma optionNV(unroll all)
        for (int i = 1; i < 16; i++) {
            if (i >= steps - 1) break; // Проверка для завершения цикла
            
            float pos = leftIdx + stepSize * float(i);
            vec4 pixel = getWaveValue(pos);
            
            // Декодируем значения
            float r_min = pixel.r * 2.0 - 1.0;
            float r_max = pixel.g * 2.0 - 1.0;
            float l_min = pixel.b * 2.0 - 1.0;
            float l_max = pixel.a * 2.0 - 1.0;
            
            // Обновляем минимумы и максимумы
            rMin = min(rMin, r_min);
            rMax = max(rMax, r_max);
            lMin = min(lMin, l_min);
            lMax = max(lMax, l_max);
        }
    }
    
    // Собираем экстремумы в вектор
    return vec4(rMin, rMax, lMin, lMax);
}

void main()
{
    // Убеждаемся, что sampleRate не ноль для избежания деления на ноль
    float effectiveSampleRate = max(1.0, float(u.sampleRate));
    
    // Явно вычисляем начальную позицию в семплах
    float startSampleIndex = u.startTime * effectiveSampleRate;
    
    // Убеждаемся, что samplePerPixel не ноль
    float effectiveSamplePerPixel = max(1.0, float(u.samplePerPixel));
    
    // Переводим в индексы текстуры
    float startTexIndex = startSampleIndex / effectiveSamplePerPixel;
    
    // Для отладки - выводим цветную полосу, если startTexIndex > 0
    // if (startTexIndex > 0.1) {
    //     FragColor = vec4(1.0, 0.0, 0.0, 1.0);  // красная полоса для проверки
    //     return;
    // }
    
    // Масштабный фактор - сколько элементов текстуры приходится на один пиксель экрана
    float scaledPixelWidth = float(u.colsUsed) / (u.resolution.x * max(0.1, u.scaleFactor));
    
    // Текущая X-координата пикселя относительно начала экрана
    float pixelX = gl_FragCoord.x;
    
    // Вычисляем индексы с учетом стартовой позиции и масштаба
    float leftIdx = startTexIndex + (pixelX - 0.5) * scaledPixelWidth;
    float rightIdx = startTexIndex + (pixelX + 0.5) * scaledPixelWidth;
    
    // Проверяем, что индексы в допустимых пределах
    leftIdx = max(0.0, leftIdx);
    rightIdx = min(float(u.colsUsed - 1), rightIdx);
    
    // Инициализируем минимальные и максимальные значения
    float rMin = 1.0, rMax = -1.0;
    float lMin = 1.0, lMax = -1.0;
    
    // Определяем ширину диапазона данных
    float dataRange = rightIdx - leftIdx;
    
    if (dataRange <= 1.0) {
        // Если в диапазон попадает не более 1 сэмпла, используем точное чтение
        vec4 pixel = getWaveValue(leftIdx);
        
        // Декодируем значения
        rMin = pixel.r * 2.0 - 1.0;
        rMax = pixel.g * 2.0 - 1.0;
        lMin = pixel.b * 2.0 - 1.0;
        lMax = pixel.a * 2.0 - 1.0;
    } else {
        // Для большого диапазона используем специальную функцию
        vec4 extremes = collectExtremes(leftIdx, rightIdx, 16);
        rMin = extremes.x;
        rMax = extremes.y;
        lMin = extremes.z;
        lMax = extremes.w;
        
        // Добавляем особый случай для очень широких диапазонов
        if (dataRange > 16.0) {
            // Проверяем дополнительные контрольные точки (1/4, 1/2, 3/4)
            float q1 = leftIdx + dataRange * 0.25;
            float q2 = leftIdx + dataRange * 0.5;
            float q3 = leftIdx + dataRange * 0.75;
            
            vec4 p1 = getWaveValue(q1);
            vec4 p2 = getWaveValue(q2);
            vec4 p3 = getWaveValue(q3);
            
            // Обновляем экстремумы
            rMin = min(rMin, min(p1.r * 2.0 - 1.0, min(p2.r * 2.0 - 1.0, p3.r * 2.0 - 1.0)));
            rMax = max(rMax, max(p1.g * 2.0 - 1.0, max(p2.g * 2.0 - 1.0, p3.g * 2.0 - 1.0)));
            lMin = min(lMin, min(p1.b * 2.0 - 1.0, min(p2.b * 2.0 - 1.0, p3.b * 2.0 - 1.0)));
            lMax = max(lMax, max(p1.a * 2.0 - 1.0, max(p2.a * 2.0 - 1.0, p3.a * 2.0 - 1.0)));
        }
    }
    
    // Вычисляем границы волн
    float rTop = baseRight + (rMax * u.ampScale);
    float rBot = baseRight + (rMin * u.ampScale);
    float lTop = baseLeft  + (lMax * u.ampScale);
    float lBot = baseLeft  + (lMin * u.ampScale);

    // Текущая позиция Y
    float y = gl_FragCoord.y / u.resolution.y;

    // Размер пикселя по вертикали
    float pixelHeight = 1.0 / u.resolution.y;

    // Вычисляем, насколько сильно меняются границы волны по Y при смещении на 1 пиксель по X
    float drTop_dx = abs(dFdx(rTop));
    float drBot_dx = abs(dFdx(rBot));
    float dlTop_dx = abs(dFdx(lTop));
    float dlBot_dx = abs(dFdx(lBot));

    // Берем максимальное из этих изменений как меру "резкости" волны по X
    float max_deriv_x = max(max(drTop_dx, drBot_dx), max(dlTop_dx, dlBot_dx));

    // Адаптивное сглаживание:
    // 1. Базовое сглаживание от пользователя (u.smoothing)
    // 2. Минимальное сглаживание, зависящее от высоты пикселя
    // 3. Динамическое сглаживание, зависящее от резкости волны по X.
    //    Коэффициент 1.0 (или чуть больше, например 1.5-2.0) может быть настроен для лучшего вида.
    float dynamicSmoothing = max_deriv_x * 2;
    float effectiveSmoothing = max(u.smoothing, max(pixelHeight * 0.5, dynamicSmoothing));

    // Используем улучшенную функцию для более стабильного отображения
    float waveR = smoothstep(rBot - effectiveSmoothing, rBot, y) - smoothstep(rTop, rTop + effectiveSmoothing, y);
    float waveL = smoothstep(lBot - effectiveSmoothing, lBot, y) - smoothstep(lTop, lTop + effectiveSmoothing, y);

    // Смешиваем цвета с учётом сглаживания
    FragColor = mix(u.backColor, u.waveColor, clamp(waveR + waveL, 0.0, 1.0));
    
}

