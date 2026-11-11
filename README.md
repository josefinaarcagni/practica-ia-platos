# Práctica: estimación nutricional de platos con IA multimodal

Aplicación de Streamlit para la sesión de IA y aprendizaje automático del Máster MINEA. Cada alumno sube la foto de un plato y elige o escribe una instrucción (*prompt*). Un modelo multimodal estima los alimentos, los gramos, la energía y los macronutrientes. La app compara esa estimación con el valor de referencia y calcula el error de cada intento y de cada ronda.

## Proveedores de modelo

| Proveedor | Coste | Clave |
|---|---|---|
| **Gemini (Google)**, recomendado | Nivel gratuito para los modelos Flash | <https://aistudio.google.com>, en «Get API key» |
| Groq (Llama 4 Scout con visión) | Nivel gratuito con límites | <https://console.groq.com/keys> |
| Modo demostración | Sin conexión | No necesita clave; devuelve una respuesta simulada |

- La app pide a la API la lista de modelos Gemini disponibles para cada clave y coloca primero los «flash». Así, si Google cambia los nombres de los modelos, no hay que tocar el código.
- Los límites del nivel gratuito cambian con frecuencia y van por proyecto. Consulta los límites vigentes de tu clave en el panel de Google AI Studio antes de la clase.
- En el nivel gratuito, el proveedor puede usar el contenido enviado para mejorar sus servicios. Por eso conviene usar solo fotos de platos, sin personas.

## Ejecutar en local

```bash
cd practica-ia-platos
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py
```

## Publicar en Streamlit Community Cloud (gratis)

1. Sube esta carpeta a un repositorio de GitHub. `.streamlit/secrets.toml` está en `.gitignore`, así que tu clave no se sube.
2. En <https://share.streamlit.io>, pulsa «Create app» y elige el repositorio y `app.py`.
3. Opcional: en «App settings → Secrets», pega `GEMINI_API_KEY = "tu-clave"`. Así el alumnado no necesita crear su propia clave. Ten en cuenta que todos compartirán los límites de tu proyecto; con un grupo grande es mejor que cada alumno use su clave.
4. Copia la URL de la app en la diapositiva «Acceso a la aplicación» de `ML-IA-nutricion.pptx`.

## Qué hace la app

1. **Foto:** se puede subir un archivo o hacerla con la cámara. Se redimensiona a 1024 px antes de enviarla.
2. **Referencia:** kcal y macronutrientes reales del plato (opcional), pesados y calculados con BEDCA.
3. **Instrucción:** hay cuatro plantillas y todas se pueden editar antes de enviar.
   - Básica.
   - Estructurada, que pide la salida en JSON.
   - Con contexto: diámetro del plato e información adicional.
   - Libre.
4. **Resultado:**
   - Tabla de alimentos con sus supuestos y la confianza que declara el modelo.
   - Diferencia con la referencia.
   - Respuesta completa del modelo.
   - Si la respuesta no es JSON (lo normal con la instrucción básica), la app intenta leer la cifra de kcal del texto.
5. **Historial:**
   - Error de cada intento.
   - MAE y error relativo medio por ronda, con su gráfico.
   - Descarga en CSV para entregar.

**Otros ajustes de la barra lateral:**
- **Temperatura:** controla cuánto varían las respuestas.
- **Forzar respuesta en JSON:** pide al servicio que devuelva JSON válido.
- **Repeticiones:** de 1 a 3. Sirve para ver que la misma pregunta puede dar respuestas distintas.
