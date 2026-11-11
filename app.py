"""Práctica MINEA: estimación nutricional de platos con IA multimodal.

Los alumnos suben la foto de un plato, eligen o escriben una instrucción (prompt) y un
modelo multimodal (Gemini, gratis con una clave de Google AI Studio; o Groq) estima los
alimentos, los gramos y la energía. La app compara la estimación con el valor de
referencia y guarda cada intento para comparar el error entre instrucciones.
"""
import base64
import io
import json
import random
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
import streamlit as st
from PIL import Image

st.set_page_config(page_title="Estimación nutricional con IA · MINEA", page_icon="🍽️", layout="wide")

DIR_EJEMPLOS = Path(__file__).parent / "ejemplos"
# Platos de Nutrition5k (Thames et al., CVPR 2021; CC BY 4.0): cada ingrediente se pesó al servirlo y la
# composición se calculó con la base de datos del USDA. No hay datos de fibra.
EJEMPLOS = {
    "Ensalada de bacalao con maíz": {
        "archivo": "dish_1562613045.jpg",
        "ref": {"kcal": 166, "proteinas_g": 21.5, "hidratos_g": 18.3, "grasas_g": 1.8},
        "ingredientes": [("Bacalao", 96, 81), ("Maíz", 79, 76), ("Brotes de hoja verde", 32, 9)]},
    "Pollo con espinacas y brócoli": {
        "archivo": "dish_1565811025.jpg",
        "ref": {"kcal": 361, "proteinas_g": 65.4, "hidratos_g": 4.4, "grasas_g": 7.7},
        "ingredientes": [("Pollo", 205, 338), ("Brócoli", 52, 18), ("Espinaca cruda", 20, 5)]},
    "Pollo a la plancha con aceitunas y tomate": {
        "archivo": "dish_1564083508.jpg",
        "ref": {"kcal": 276, "proteinas_g": 22.8, "hidratos_g": 6.0, "grasas_g": 18.4},
        "ingredientes": [("Pollo a la plancha", 96, 217), ("Tomate cherry", 92, 17), ("Aceitunas", 37, 43)]},
    "Huevos revueltos con boniato y coles de Bruselas": {
        "archivo": "dish_1562605384.jpg",
        "ref": {"kcal": 306, "proteinas_g": 17.0, "hidratos_g": 18.4, "grasas_g": 18.4},
        "ingredientes": [("Huevos revueltos", 147, 218), ("Boniato", 65, 50), ("Coles de Bruselas", 47, 20),
                         ("Aceite de oliva", 2, 19)]},
    "Ensalada de atún": {
        "archivo": "dish_1565809120.jpg",
        "ref": {"kcal": 366, "proteinas_g": 63.2, "hidratos_g": 22.9, "grasas_g": 1.7},
        "ingredientes": [("Atún", 205, 266), ("Pimiento", 98, 39), ("Tomate cherry", 74, 13), ("Cebolla", 56, 22),
                         ("Zanahoria", 52, 21), ("Zumo de limón", 17, 3)]},
    "Almendras con brócoli y coliflor": {
        "archivo": "dish_1558725286.jpg",
        "ref": {"kcal": 817, "proteinas_g": 33.3, "hidratos_g": 40.7, "grasas_g": 66.0},
        "ingredientes": [("Almendras", 132, 763), ("Brócoli", 97, 34), ("Coliflor", 79, 20)]},
}

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta"
GROQ_URL = "https://api.groq.com/openai/v1"
GROQ_DEFAULT = "meta-llama/llama-4-scout-17b-16e-instruct"
NUTRIENTES = ["kcal", "proteinas_g", "hidratos_g", "grasas_g", "fibra_g"]
NOMBRES = {"kcal": "Energía (kcal)", "proteinas_g": "Proteínas (g)", "hidratos_g": "Hidratos de carbono (g)",
           "grasas_g": "Grasas (g)", "fibra_g": "Fibra (g)"}

FORMATO_JSON = """Responde ÚNICAMENTE con un objeto JSON válido, sin texto adicional, con esta estructura:
{
  "alimentos": [
    {"nombre": "...", "gramos": 0, "kcal": 0, "proteinas_g": 0, "hidratos_g": 0, "grasas_g": 0, "fibra_g": 0}
  ],
  "total": {"kcal": 0, "proteinas_g": 0, "hidratos_g": 0, "grasas_g": 0, "fibra_g": 0},
  "confianza": "baja | media | alta",
  "supuestos": ["..."]
}"""

PLANTILLAS = {
    "1 · Básica": "¿Cuántas calorías tiene este plato?",
    "2 · Estructurada": (
        "Actúa como dietista-nutricionista experto en evaluación dietética.\n"
        "Analiza la fotografía de este plato.\n"
        "1. Identifica cada alimento visible.\n"
        "2. Estima los gramos de cada alimento.\n"
        "3. Calcula la energía y los macronutrientes de cada alimento usando valores de tablas de composición "
        "españolas (BEDCA) para el alimento tal como se ve (cocinado, crudo, frito…).\n\n" + FORMATO_JSON),
    "3 · Con contexto": (
        "Actúa como dietista-nutricionista experto en evaluación dietética.\n"
        "Contexto: el plato mide aproximadamente {diametro} cm de diámetro; "
        "úsalo como referencia de tamaño para estimar las porciones.\n"
        "Información adicional sobre el plato: {notas}\n\n"
        "Pasos:\n"
        "1. Identifica cada alimento visible y los ingredientes probables no visibles (aceite de cocinado, "
        "salsas, azúcar).\n"
        "2. Estima los gramos de cada uno comparando con el tamaño del plato.\n"
        "3. Calcula energía, proteínas, hidratos de carbono, grasas y fibra con valores de BEDCA.\n"
        "4. Si no estás seguro de algo, indícalo en «supuestos» y no lo inventes.\n\n" + FORMATO_JSON),
    "4 · Libre": "",
}

DEMO = {
    "alimentos": [
        {"nombre": "arroz blanco cocido", "gramos": 150, "kcal": 195, "proteinas_g": 4, "hidratos_g": 42, "grasas_g": 0.4, "fibra_g": 0.6},
        {"nombre": "pechuga de pollo a la plancha", "gramos": 120, "kcal": 198, "proteinas_g": 37, "hidratos_g": 0, "grasas_g": 4.3, "fibra_g": 0},
        {"nombre": "aceite de oliva (cocinado)", "gramos": 8, "kcal": 72, "proteinas_g": 0, "hidratos_g": 0, "grasas_g": 8, "fibra_g": 0},
        {"nombre": "ensalada (lechuga y tomate)", "gramos": 80, "kcal": 15, "proteinas_g": 0.8, "hidratos_g": 2.6, "grasas_g": 0.2, "fibra_g": 1.2},
    ],
    "confianza": "media",
    "supuestos": ["Respuesta simulada (modo demostración): no se ha analizado la fotografía."],
}


# ------------------------------------------------------------------ utilidades
def secreto(nombre):
    try:
        return st.secrets.get(nombre, "")
    except Exception:
        return ""


def imagen_a_jpeg(archivo, lado_max=1024):
    img = Image.open(archivo).convert("RGB")
    img.thumbnail((lado_max, lado_max))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88)
    return img, buf.getvalue()


@st.cache_data(ttl=3600, show_spinner=False)
def modelos_gemini(clave):
    """Modelos Gemini disponibles para esta clave que aceptan generateContent (se priorizan los Flash)."""
    r = requests.get(f"{GEMINI_URL}/models", headers={"x-goog-api-key": clave}, params={"pageSize": 200}, timeout=20)
    r.raise_for_status()
    nombres = [m["name"].split("/", 1)[1] for m in r.json().get("models", [])
               if "generateContent" in m.get("supportedGenerationMethods", [])
               and m["name"].split("/", 1)[1].startswith("gemini")]
    excluir = ("image", "tts", "audio", "live", "embedding", "thinking", "deep-research", "computer-use",
               "robotics", "agent", "learnlm", "native", "transcribe", "omni", "banana", "antigravity",
               "translate")
    nombres = [n for n in nombres if not any(e in n for e in excluir)]

    def prioridad(n):
        # 0: alias estables (gemini-flash-latest); 1: Flash estable (gemini-2.5-flash); 2: Flash-Lite estable;
        # 3: otros Flash (preview, exp); 4: resto. Dentro de cada grupo, versiones más recientes primero.
        if re.fullmatch(r"gemini-flash(-lite)?-latest", n):
            g = 0
        elif re.fullmatch(r"gemini-\d+(\.\d+)?-flash", n):
            g = 1
        elif re.fullmatch(r"gemini-\d+(\.\d+)?-flash-lite", n):
            g = 2
        elif "flash" in n:
            g = 3
        else:
            g = 4
        version = re.search(r"gemini-(\d+(?:\.\d+)?)", n)
        return (g, -float(version.group(1)) if version else 0, n)

    return sorted(nombres, key=prioridad)


def probar_modelo(clave, modelo):
    """Petición mínima de texto para comprobar que el modelo responde con esta clave.
    Devuelve True si responde (o si solo está saturado en ese momento) y False si no es utilizable."""
    cab = {"x-goog-api-key": clave}
    r = requests.post(f"{GEMINI_URL}/models/{modelo}:generateContent", headers=cab, timeout=30,
                      json={"contents": [{"parts": [{"text": "Responde solo: OK"}]}]})
    if r.status_code == 400 and "interactions api" in r.text.lower():
        r = requests.post(f"{GEMINI_URL}/interactions", headers=cab, timeout=60,
                          json={"model": modelo, "input": "Responde solo: OK"})
    if r.status_code == 200:
        return True
    return r.status_code == 429 and "limit: 0" not in r.text.lower()


@st.cache_data(ttl=3600, show_spinner=False)
def modelos_operativos(clave, maximo=6):
    """Modelos Flash de la lista que responden de verdad con esta clave (se comprueban una vez por hora)."""
    candidatos = [m for m in modelos_gemini(clave) if "flash" in m][:maximo]
    return [m for m in candidatos if probar_modelo(clave, m)]


def modelo_no_compatible(mensaje):
    """Errores que indican que el modelo no admite esta forma de llamada (no son errores del alumno)."""
    m = mensaje.lower()
    return any(t in m for t in ("interactions api", "error 404", "not supported", "is not found", "not found for api",
                                "no longer available", "deprecated", "not available", "shut down", "limit: 0"))


def llamar_gemini(clave, modelo, prompt, jpeg, temperatura, forzar_json):
    """Llama a generateContent; si el modelo solo admite la Interactions API, usa esa interfaz."""
    imagen_b64 = base64.b64encode(jpeg).decode()
    cuerpo = {
        "contents": [{"parts": [{"text": prompt},
                                {"inline_data": {"mime_type": "image/jpeg", "data": imagen_b64}}]}],
        "generationConfig": {"temperature": temperatura},
    }
    if forzar_json:
        cuerpo["generationConfig"]["responseMimeType"] = "application/json"
    r = requests.post(f"{GEMINI_URL}/models/{modelo}:generateContent", headers={"x-goog-api-key": clave},
                      json=cuerpo, timeout=120)
    if r.status_code == 400 and "interactions api" in r.text.lower():
        return llamar_gemini_interactions(clave, modelo, prompt, imagen_b64, temperatura, forzar_json)
    if r.status_code != 200:
        raise RuntimeError(f"Error {r.status_code} de la API de Gemini: {r.text[:500]}")
    datos = r.json()
    try:
        return "".join(p.get("text", "") for p in datos["candidates"][0]["content"]["parts"])
    except (KeyError, IndexError):
        raise RuntimeError(f"Respuesta sin texto (posible bloqueo de seguridad): {json.dumps(datos)[:500]}")


def texto_interaction(datos):
    """Texto generado en una respuesta de la Interactions API (pasos «model_output» o lista «outputs»)."""
    bloques = []
    for paso in datos.get("steps") or []:
        if paso.get("type") == "model_output":
            bloques += [c.get("text", "") for c in paso.get("content") or [] if c.get("type") == "text"]
    if not bloques:
        bloques = [o.get("text", "") for o in datos.get("outputs") or [] if o.get("type") == "text"]
    return "".join(bloques)


def llamar_gemini_interactions(clave, modelo, prompt, imagen_b64, temperatura, forzar_json):
    cuerpo = {
        "model": modelo,
        "input": [{"type": "image", "mime_type": "image/jpeg", "data": imagen_b64},
                  {"type": "text", "text": prompt}],
        "generation_config": {"temperature": temperatura},
    }
    if forzar_json:
        cuerpo["response_format"] = {"type": "text", "mime_type": "application/json"}
    url, cab = f"{GEMINI_URL}/interactions", {"x-goog-api-key": clave}
    r = requests.post(url, headers=cab, json=cuerpo, timeout=180)
    if r.status_code == 400:
        # Si el servicio rechaza algún parámetro opcional, se repite la petición sin él.
        for opcional in ("generation_config", "response_format"):
            if opcional in r.text and opcional in cuerpo:
                cuerpo.pop(opcional)
                r = requests.post(url, headers=cab, json=cuerpo, timeout=180)
                if r.status_code != 400:
                    break
    if r.status_code != 200:
        raise RuntimeError(f"Error {r.status_code} de la API de Gemini (Interactions): {r.text[:500]}")
    texto = texto_interaction(r.json())
    if not texto:
        raise RuntimeError(f"Respuesta sin texto: {r.text[:500]}")
    return texto


def llamar_groq(clave, modelo, prompt, jpeg, temperatura, forzar_json):
    cuerpo = {
        "model": modelo,
        "temperature": temperatura,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(jpeg).decode()}}]}],
    }
    if forzar_json:
        cuerpo["response_format"] = {"type": "json_object"}
    r = requests.post(f"{GROQ_URL}/chat/completions", headers={"Authorization": f"Bearer {clave}"}, json=cuerpo, timeout=120)
    if r.status_code != 200:
        raise RuntimeError(f"Error {r.status_code} de la API de Groq: {r.text[:500]}")
    return r.json()["choices"][0]["message"]["content"]


def respuesta_demo():
    d = json.loads(json.dumps(DEMO))
    for a in d["alimentos"]:  # pequeña variación para simular la variabilidad entre respuestas
        f = random.uniform(0.85, 1.15)
        for k in ["gramos"] + NUTRIENTES:
            a[k] = round(a[k] * f, 1)
    d["total"] = {k: round(sum(a[k] for a in d["alimentos"]), 1) for k in NUTRIENTES}
    return json.dumps(d, ensure_ascii=False, indent=2)


def extraer_json(texto):
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", texto.strip(), flags=re.S)
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", t, flags=re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return None
    return None


def numero(v):
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return None


def totales(d):
    """Totales de energía y nutrientes a partir del JSON (campo total o suma de alimentos)."""
    out = {}
    tot = d.get("total") if isinstance(d.get("total"), dict) else {}
    alimentos = d.get("alimentos") if isinstance(d.get("alimentos"), list) else []
    for k in NUTRIENTES:
        v = numero(tot.get(k)) if tot else None
        if v is None and k == "kcal":
            v = numero(d.get("total_kcal"))
        if v is None and alimentos:
            vals = [numero(a.get(k)) for a in alimentos if isinstance(a, dict)]
            vals = [x for x in vals if x is not None]
            v = sum(vals) if vals else None
        out[k] = v
    return out


def kcal_de_texto(texto):
    """Para respuestas en texto libre: busca cifras (o rangos) seguidas de «kcal» o «calorías» y devuelve la mayor,
    que suele ser el total del plato. Los rangos (p. ej., 500-600 kcal) se resumen con su punto medio."""
    patron = r"(\d{1,2}[.\s]\d{3}|\d+(?:[.,]\d+)?)\s*(?:(?:-|–|a)\s*(\d{1,2}[.\s]\d{3}|\d+(?:[.,]\d+)?))?\s*(?:kcal|calor[ií]as)"
    def num(x):
        x = re.sub(r"(?<=\d)[.\s](?=\d{3}$)", "", x)
        return numero(x)
    vals = []
    for a, b in re.findall(patron, texto, flags=re.I):
        va, vb = num(a), num(b) if b else None
        vals.append((va + vb) / 2 if va is not None and vb is not None else va)
    vals = [v for v in vals if v]
    return max(vals) if vals else None


# ------------------------------------------------------------------ estado
if "intentos" not in st.session_state:
    st.session_state.intentos = []

# ------------------------------------------------------------------ barra lateral
with st.sidebar:
    st.header("Configuración")
    proveedor = st.radio("Proveedor del modelo", ["Gemini (Google)", "Groq", "Modo demostración"],
                         help="Gemini tiene un nivel gratuito con una clave de Google AI Studio. "
                              "El modo demostración no usa internet y devuelve una respuesta simulada.")
    clave, modelo = "", ""
    if proveedor == "Gemini (Google)":
        clave = st.text_input("Clave de la API de Gemini", value=secreto("GEMINI_API_KEY"), type="password",
                              help="La clave solo se usa durante esta sesión y no se guarda.")
        with st.expander("Cómo obtener la clave (gratuita)", expanded=not clave):
            st.markdown(
                "1. Acceda a [Google AI Studio](https://aistudio.google.com/apikey) con una cuenta de Google.\n"
                "2. Acepte las condiciones de uso, si se le solicitan.\n"
                "3. Pulse **Create API key** y copie la clave generada.\n"
                "4. Péguela en el campo superior y pulse Intro.\n\n"
                "No se necesita tarjeta de crédito. El nivel gratuito limita el número de peticiones por minuto; "
                "si aparece un error 429, espere un minuto antes de repetir.")
        lista = []
        if clave:
            try:
                with st.spinner("Comprobando los modelos disponibles…"):
                    lista = modelos_operativos(clave)
                if not lista:
                    st.error("Ningún modelo ha respondido con esta clave. Compruebe que la clave es correcta "
                             "o inténtelo de nuevo en unos minutos.")
            except Exception as e:
                msg = str(e)
                if "400" in msg or "403" in msg:
                    st.error("La clave no es válida. Cópiela de nuevo desde Google AI Studio.")
                else:
                    st.error(f"No se pudo conectar con Gemini ({msg[:150]}).")
        descartados = st.session_state.setdefault("modelos_descartados", set())
        lista = [m for m in lista if m not in descartados]
        modelo = st.selectbox("Modelo", lista, disabled=not lista,
                              placeholder="Introduzca la clave para ver los modelos",
                              help="Solo se muestran los modelos que han respondido con esta clave. "
                                   "Se recomienda mantener el modelo propuesto.")
    elif proveedor == "Groq":
        clave = st.text_input("Clave de la API de Groq", value=secreto("GROQ_API_KEY"), type="password",
                              help="La clave solo se usa durante esta sesión y no se guarda.")
        with st.expander("Cómo obtener la clave (gratuita)", expanded=not clave):
            st.markdown(
                "1. Cree una cuenta en [GroqCloud](https://console.groq.com).\n"
                "2. En [API Keys](https://console.groq.com/keys), pulse **Create API Key**.\n"
                "3. Copie la clave (solo se muestra una vez) y péguela en el campo superior.")
        modelo = st.text_input("Modelo", value=GROQ_DEFAULT)
    else:
        modelo = "demo"
    temperatura = st.slider("Temperatura", 0.0, 1.0, 0.2, 0.1,
                            help="Valores bajos dan respuestas más estables; valores altos, más variadas.")
    forzar_json = st.checkbox("Forzar respuesta en JSON", value=False,
                              help="Pide al servicio que devuelva JSON válido. Desactivado con la plantilla básica, "
                                   "para ver la diferencia con una instrucción básica.")
    st.divider()
    st.caption("Use solo fotografías de platos, sin personas ni datos personales. En el nivel gratuito, "
               "el proveedor puede utilizar el contenido enviado para mejorar sus servicios.")


def cargar_ejemplo():
    """Al elegir un plato de ejemplo, rellena el nombre y los valores de referencia medidos."""
    nombre = st.session_state.get("ejemplo")
    if nombre in EJEMPLOS:
        st.session_state.nombre_plato = nombre
        for k in NUTRIENTES:
            st.session_state[f"ref_{k}"] = float(EJEMPLOS[nombre]["ref"].get(k, 0.0))


# ------------------------------------------------------------------ cuerpo
st.title("Estimación nutricional de platos con IA multimodal")
st.markdown("Máster MINEA · Práctica de *prompting*. Compare la estimación del modelo con la composición "
            "de referencia y analice cómo cambia el error al modificar la instrucción.")

c1, c2 = st.columns([1, 1.25], gap="large")

with c1:
    st.subheader("1. Fotografía del plato")
    origen = st.radio("Origen", ["Plato de ejemplo", "Subir archivo", "Cámara"], horizontal=True,
                      label_visibility="collapsed")
    archivo, ejemplo = None, None
    if origen == "Plato de ejemplo":
        ejemplo = st.selectbox("Plato", list(EJEMPLOS), index=None, placeholder="Seleccione un plato",
                               key="ejemplo", on_change=cargar_ejemplo)
        if ejemplo:
            archivo = DIR_EJEMPLOS / EJEMPLOS[ejemplo]["archivo"]
    elif origen == "Subir archivo":
        archivo = st.file_uploader("Fotografía (JPG o PNG)", type=["jpg", "jpeg", "png", "webp"])
    else:
        archivo = st.camera_input("Fotografía del plato")
    nombre_plato = st.text_input("Nombre del plato", key="nombre_plato", placeholder="p. ej., lentejas con chorizo")
    jpeg = None
    if archivo:
        img, jpeg = imagen_a_jpeg(archivo)
        st.image(img, width="stretch")
    if ejemplo:
        with st.expander("Composición medida del plato"):
            st.dataframe(pd.DataFrame(EJEMPLOS[ejemplo]["ingredientes"], columns=["Ingrediente", "Gramos", "kcal"]),
                         width="stretch", hide_index=True)
            st.caption("Fuente: Nutrition5k (Thames et al., CVPR 2021), Google Research, licencia CC BY 4.0. "
                       "Ingredientes pesados al servir el plato; composición calculada con la base de datos "
                       "del USDA. Sin datos de fibra.")

    st.subheader("2. Valores de referencia")
    st.caption("Composición real del plato. En los platos propios, pese los ingredientes y calcule los valores "
               "con BEDCA. Deje en 0 los que no conozca.")
    ref = {}
    rc = st.columns(3)
    for i, k in enumerate(NUTRIENTES):
        ref[k] = rc[i % 3].number_input(NOMBRES[k], min_value=0.0, step=1.0, key=f"ref_{k}")

with c2:
    st.subheader("3. Instrucción (prompt)")
    plantilla = st.selectbox("Plantilla", list(PLANTILLAS), index=1)
    diametro, notas = 26, "ninguna"
    if plantilla.startswith("3"):
        cc = st.columns([1, 2])
        diametro = cc[0].number_input("Diámetro del plato (cm)", 10, 40, 26)
        notas = cc[1].text_input("Información adicional", value="ninguna",
                                 placeholder="p. ej., cocinado con dos cucharadas de aceite")
    base = PLANTILLAS[plantilla].replace("{diametro}", str(diametro)).replace("{notas}", notas or "ninguna")
    prompt = st.text_area("Instrucción (editable)", value=base, height=330,
                          key=f"prompt_{plantilla}_{diametro}_{notas}")
    cc = st.columns([1, 1.4])
    repeticiones = cc[0].number_input("Repeticiones", 1, 3, 1, help="Envía la misma petición varias veces para observar la variabilidad.")
    enviar = cc[1].button("Analizar plato", type="primary", width="stretch",
                          disabled=(jpeg is None and proveedor != "Modo demostración") or not prompt.strip() or not modelo)

# ------------------------------------------------------------------ llamada al modelo
if enviar:
    if proveedor != "Modo demostración" and not clave:
        st.error("Falta la clave de la API. Consulte en la barra lateral cómo obtenerla gratuitamente.")
        st.stop()
    for rep in range(int(repeticiones)):
        with st.spinner(f"Consultando el modelo ({rep + 1}/{int(repeticiones)})…"):
            try:
                if proveedor == "Gemini (Google)":
                    candidatos = [modelo] + [m for m in lista if m != modelo][:4]
                    for i, m in enumerate(candidatos):
                        try:
                            texto = llamar_gemini(clave, m, prompt, jpeg, temperatura, forzar_json)
                            break
                        except RuntimeError as err:
                            if not modelo_no_compatible(str(err)) or i == len(candidatos) - 1:
                                raise
                            st.session_state.modelos_descartados.add(m)
                    if m != modelo:
                        st.info(f"El modelo {modelo} no es compatible con esta aplicación; se ha utilizado {m}.")
                        modelo = m
                elif proveedor == "Groq":
                    texto = llamar_groq(clave, modelo, prompt, jpeg, temperatura, forzar_json)
                else:
                    texto = respuesta_demo()
            except Exception as e:
                msg = str(e)
                if "429" in msg:
                    st.error("Se ha superado el límite de peticiones del nivel gratuito. Espere un minuto o seleccione otro modelo.")
                else:
                    st.error(msg)
                st.stop()
        datos = extraer_json(texto)
        est = totales(datos) if isinstance(datos, dict) else {k: None for k in NUTRIENTES}
        if est["kcal"] is None:
            est["kcal"] = kcal_de_texto(texto)
        st.session_state.contador = st.session_state.get("contador", 0) + 1
        fila = {"intento": st.session_state.contador, "hora": datetime.now().strftime("%H:%M:%S"),
                "plato": nombre_plato or "(sin nombre)",
                "plantilla": plantilla, "modelo": modelo, "temperatura": temperatura,
                "json_valido": isinstance(datos, dict)}
        for k in NUTRIENTES:
            fila[f"{k}_est"] = est[k]
            fila[f"{k}_ref"] = ref[k] or None
        if est["kcal"] is not None and ref["kcal"]:
            fila["error_kcal"] = round(est["kcal"] - ref["kcal"], 1)
            fila["error_abs_kcal"] = abs(fila["error_kcal"])
            fila["error_rel_%"] = round(100 * fila["error_abs_kcal"] / ref["kcal"], 1)
        fila["prompt"] = prompt
        fila["respuesta"] = texto
        st.session_state.intentos.append(fila)
    st.session_state.ultimo = (texto, datos)

# ------------------------------------------------------------------ resultado
if "ultimo" in st.session_state:
    texto, datos = st.session_state.ultimo
    st.divider()
    st.subheader("4. Resultado del último intento")
    r1, r2 = st.columns([1.3, 1], gap="large")
    with r1:
        if isinstance(datos, dict) and isinstance(datos.get("alimentos"), list):
            df = pd.DataFrame(datos["alimentos"])
            st.dataframe(df, width="stretch", hide_index=True)
            if datos.get("supuestos"):
                st.markdown("**Supuestos del modelo:** " + "; ".join(map(str, datos["supuestos"])))
            if datos.get("confianza"):
                st.markdown(f"**Confianza declarada:** {datos['confianza']}")
        else:
            st.info("La respuesta no es un JSON con la estructura esperada (habitual con la instrucción básica). "
                    "Se ha intentado leer la cifra de kcal del texto.")
            st.markdown(texto)
    with r2:
        ult = st.session_state.intentos[-1]
        for k in NUTRIENTES:
            e, rf = ult.get(f"{k}_est"), ult.get(f"{k}_ref")
            if e is None:
                continue
            delta = None if not rf else f"{e - rf:+.0f} frente a la referencia ({100 * (e - rf) / rf:+.0f} %)"
            st.metric(NOMBRES[k], f"{e:.0f}", delta, delta_color="off")
        with st.expander("Respuesta completa del modelo"):
            st.code(texto, language="json" if isinstance(datos, dict) else None)

# ------------------------------------------------------------------ historial
if st.session_state.intentos:
    st.divider()
    st.subheader("5. Comparación de intentos")
    hist = pd.DataFrame(st.session_state.intentos)
    cols = ["intento", "hora", "plato", "plantilla", "modelo", "json_valido", "kcal_est", "kcal_ref",
            "error_kcal", "error_rel_%"]
    tabla = hist[[c for c in cols if c in hist.columns]].copy()
    tabla.insert(0, "eliminar", False)
    editada = st.data_editor(tabla, width="stretch", hide_index=True, key=f"editor_{len(hist)}",
                             disabled=[c for c in tabla.columns if c != "eliminar"],
                             column_config={"eliminar": st.column_config.CheckboxColumn("Eliminar", width="small")})
    b1, b2, b3 = st.columns(3)
    seleccion = editada.loc[editada["eliminar"], "intento"].tolist()
    if b1.button("Eliminar seleccionados", width="stretch", disabled=not seleccion):
        st.session_state.intentos = [f for f in st.session_state.intentos if f["intento"] not in seleccion]
        if not st.session_state.intentos:
            st.session_state.pop("ultimo", None)
        st.rerun()
    if b2.button("Borrar todo", width="stretch"):
        st.session_state.intentos = []
        st.session_state.pop("ultimo", None)
        st.rerun()
    b3.download_button("Descargar tabla (CSV)", hist.to_csv(index=False).encode("utf-8-sig"),
                       file_name="intentos_platos.csv", mime="text/csv", width="stretch")

    con_error = hist.dropna(subset=["error_abs_kcal"]) if "error_abs_kcal" in hist.columns else hist.iloc[0:0]
    if len(con_error):
        s1, s2 = st.columns([1.4, 1], gap="large")
        with s1:
            st.markdown("**Error absoluto (kcal) de cada intento**")
            st.bar_chart(con_error, x="intento", y="error_abs_kcal", color="plantilla",
                         x_label="Intento", y_label="Error absoluto (kcal)")
        with s2:
            st.markdown("**Error medio por plantilla**")
            resumen = (con_error.groupby("plantilla")
                       .agg(intentos=("error_abs_kcal", "size"), MAE_kcal=("error_abs_kcal", "mean"),
                            error_relativo_medio=("error_rel_%", "mean")).round(1))
            st.dataframe(resumen, width="stretch")
    sin_error = len(hist) - len(con_error)
    if sin_error:
        st.caption(f"{sin_error} intento(s) sin error calculado: falta la referencia de kcal o no se encontró "
                   "la cifra de kcal en la respuesta.")
