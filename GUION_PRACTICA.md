# Práctica 2. Estimación nutricional de platos con IA multimodal

**Máster MINEA · Inteligencia artificial y aprendizaje automático en la nutrición personalizada**

## Objetivos

- Usar un modelo de IA multimodal para estimar la composición de un plato a partir de una fotografía.
- Comprobar cómo cambia la precisión de la estimación al mejorar la instrucción (*prompt*).
- Calcular e interpretar métricas de error de regresión: error absoluto, MAE y error relativo.

## Material

- La aplicación (el enlace lo da la profesora).
- Una clave gratuita de la API de Gemini. Para crearla:
  1. Entra en <https://aistudio.google.com> con una cuenta de Google.
  2. Pulsa «Get API key» y crea una clave.
  3. Pégala en la barra lateral de la app.
- Un plato cuya composición se conozca. Hay dos opciones:
  - **Plato de ejemplo** de la app. Sus ingredientes se pesaron al servirlo y los valores de referencia se rellenan solos.
  - **Plato propio**, pesado en casa o preparado con una receta de cantidades conocidas.
    - Haz la foto desde arriba y con todo el plato visible.
    - No debe aparecer ninguna persona.
    - Calcula los valores de referencia con BEDCA (<https://www.bedca.net>): kcal, proteínas, hidratos de carbono, grasas y fibra.

## Desarrollo (en parejas)

### Ronda 1. Instrucción básica (10 min)
1. Sube la foto, escribe el nombre del plato e introduce los valores de referencia.
2. Elige la plantilla **«1 · Básica»** y deja desactivada la opción «Forzar respuesta en JSON».
3. Pulsa **Analizar plato** y lee la respuesta. ¿Es fácil compararla con tu referencia?

### Ronda 2. Instrucción estructurada (10 min)
1. Elige la plantilla **«2 · Estructurada»**, que define un rol, unos pasos y la salida en JSON.
2. Analiza el mismo plato con **3 repeticiones**. ¿Da siempre la misma estimación?

### Ronda 3. Instrucción propia (15 min)
1. Parte de la plantilla **«3 · Con contexto»** o de la **«4 · Libre»**.
2. Mejora la instrucción. Algunas ideas:
   - Indicar el tamaño real del plato o de un objeto de referencia, como un tenedor.
   - Mencionar los ingredientes que no se ven: aceite de cocinado, salsas, azúcar.
   - Pedir que primero identifique los alimentos y después estime cada porción.
   - Incluir un ejemplo de respuesta correcta.
3. Prueba al menos dos versiones y quédate con la que tenga menor error.

### Puesta en común (15 min)
Compara con el resto de la clase el **MAE por ronda** que aparece en la sección 5 de la app.

## Entregable

1. La tabla descargada de la app (botón «Descargar tabla (CSV)»).
2. Una reflexión breve, de unas 300 palabras, que responda a estas preguntas:
   - ¿Qué cambio en la instrucción redujo más el error?
   - ¿En qué alimentos o nutrientes se equivoca más el modelo? ¿Por qué crees que ocurre?
   - ¿Las repeticiones dieron siempre el mismo resultado? ¿Qué implica esto para usar la herramienta en la consulta?
   - ¿Usarías esta herramienta con pacientes? ¿Con qué precauciones?

## Fórmulas

- **Error** = estimado − referencia. Si es positivo, el modelo sobrestima; si es negativo, infraestima.
- **Error absoluto** = |estimado − referencia|
- **MAE** (error absoluto medio) = media de los errores absolutos de todos los intentos de una ronda.
- **Error relativo (%)** = 100 · |estimado − referencia| / referencia
