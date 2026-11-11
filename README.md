# Estimación nutricional de platos con IA multimodal

**Inteligencia artificial y Machine Learning en la nutrición personalizada**

Aplicación para la práctica de *prompting*. Un modelo de IA multimodal recibe la fotografía de un plato y una instrucción (*prompt*). A partir de ellas estima los alimentos, las porciones, la energía y los macronutrientes. La aplicación compara esa estimación con la composición de referencia y registra el error de cada intento.

## Antes de empezar

**Clave de la API de Gemini** (gratuita):
1. Acceda a <https://aistudio.google.com> con una cuenta de Google.
2. Pulse «Get API key» y cree una clave.
3. Pegue la clave en la barra lateral de la aplicación. La clave no se guarda.

Si no dispone de clave, el **modo demostración** permite recorrer la aplicación con una respuesta simulada.

## Flujo de trabajo

1. **Fotografía.** Hay tres opciones:
   - Un plato de ejemplo.
   - Una imagen propia.
   - Una foto con la cámara.
2. **Referencia.** Indique la composición real del plato:
   - Platos de ejemplo: la composición se rellena sola.
   - Platos propios: pese los ingredientes y calcule los valores con [BEDCA](https://www.bedca.net).
3. **Instrucción.** Elija una plantilla y edítela si lo desea:
   - Básica.
   - Estructurada.
   - Con contexto.
   - Libre.
4. **Resultado.** La aplicación muestra:
   - La estimación por alimento.
   - Los supuestos y la confianza que declara el modelo.
   - La diferencia con la referencia.
5. **Comparación.** Muestra el error de cada intento y el MAE por plantilla. Los intentos erróneos se pueden eliminar. Descargue la tabla en CSV para el entregable.

**Parámetros de la barra lateral**
- **Temperatura:** grado de variabilidad de las respuestas.
- **Forzar respuesta en JSON:** obliga al modelo a devolver datos estructurados.
- **Repeticiones** (en la sección 3): número de veces que se envía la misma petición.

## Platos de ejemplo

Proceden de **Nutrition5k**, un conjunto de datos de Google Research (Thames *et al.*, CVPR 2021) con licencia CC BY 4.0. Cada ingrediente se pesó al servir el plato y la composición se calculó con la base de datos del USDA. No incluyen datos de fibra.

## Privacidad

Utilice solo fotografías de platos, sin personas ni datos personales. En el nivel gratuito, el proveedor puede usar el contenido enviado para mejorar sus servicios.

## Fórmulas

| Medida | Cálculo |
|---|---|
| Error | estimado − referencia (positivo: sobrestima; negativo: infraestima) |
| Error absoluto | \|estimado − referencia\| |
| MAE | media de los errores absolutos de los intentos con una misma plantilla |
| Error relativo (%) | 100 · \|estimado − referencia\| / referencia |
