"""
streamlit_app.py — Corrector.IA · versión web

Estructura:
- Sidebar: configuración (API keys + selección de modelo, tipo, intensidad).
- Área principal: subir archivo, ver párrafos, procesar y descargar.

Decisiones de diseño:
- Las API keys viven SOLO en st.session_state (memoria de sesión). Nunca
  se guardan en disco del servidor. Cuando el usuario cierra la pestaña,
  desaparecen. Esto te quita la responsabilidad legal de manejar claves
  ajenas y simplifica todo.
- El procesamiento usa st.empty() + st.progress() para mostrar avance
  sin congelar la UI. Streamlit reejecuta el script entero en cada
  interacción, así que mantenemos el estado clave en session_state.
- La descarga del .txt corregido se hace con st.download_button — el
  archivo nunca toca el disco del servidor, va directo del buffer en
  memoria al navegador del usuario.
"""

from __future__ import annotations

import io
import re
from datetime import datetime

import streamlit as st

import prompts
import providers


# ---------------------------------------------------------------------------
# Configuración de página
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Corrector.IA",
    page_icon="🍔",  # provisional; cuando subas el repo, reemplazarlo por el .ico
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def partir_en_parrafos(texto: str) -> list[str]:
    """Parte el texto en párrafos por línea en blanco; fallback a línea simple."""
    texto = texto.replace("\r\n", "\n").replace("\r", "\n")
    bloques = re.split(r"\n\s*\n+", texto)
    bloques = [b.strip() for b in bloques if b.strip()]
    if len(bloques) > 1:
        return bloques
    return [linea.strip() for linea in texto.split("\n") if linea.strip()]


def init_session_state():
    """Crea las claves del estado de sesión la primera vez."""
    if "api_keys" not in st.session_state:
        st.session_state.api_keys = {p: "" for p in providers.MODELS.keys()}
    if "resultado" not in st.session_state:
        st.session_state.resultado = None  # tuple (nombre_archivo, contenido_str, log_errores)


# ---------------------------------------------------------------------------
# Sidebar — configuración
# ---------------------------------------------------------------------------

def render_sidebar():
    st.sidebar.title("⚙️ Configuración")

    # --- API keys ---
    with st.sidebar.expander("🔑 API keys", expanded=not any(st.session_state.api_keys.values())):
        st.caption(
            "Tus API keys solo viven en esta sesión. "
            "Nada se guarda en el servidor. "
            "Al cerrar esta pestaña se borran."
        )
        for prov in providers.MODELS.keys():
            url = providers.KEY_URLS.get(prov, "")
            label = f"{prov}"
            help_text = f"Obtenla en: {url}" if url else None
            st.session_state.api_keys[prov] = st.text_input(
                label,
                value=st.session_state.api_keys[prov],
                type="password",
                help=help_text,
                key=f"key_{prov}",
                placeholder="Pega aquí tu API key…",
            )

    # --- Selección de proveedor / modelo ---
    st.sidebar.subheader("🤖 Proveedor y modelo")
    provider = st.sidebar.selectbox(
        "Proveedor",
        list(providers.MODELS.keys()),
        index=0,
        help="OpenAI es el más usado. DeepSeek y MiniMax son las opciones más baratas.",
    )
    model = st.sidebar.selectbox(
        "Modelo",
        providers.MODELS[provider],
        index=0,
    )

    # Aviso si falta la API key
    if not st.session_state.api_keys.get(provider, "").strip():
        st.sidebar.warning(f"Falta API key de {provider}. Ábrela arriba en «API keys».")

    # --- Tipo de texto ---
    st.sidebar.subheader("📝 Tipo de texto")
    tipo = st.sidebar.selectbox(
        "Tipo",
        prompts.listar_tipos(),
        index=0,
    )
    st.sidebar.caption(prompts.descripcion(tipo))

    # --- Intensidad ---
    st.sidebar.subheader("🎚️ Intensidad")
    intensidad = st.sidebar.radio(
        "Intensidad",
        options=["minima", "estandar", "agresiva"],
        format_func=lambda x: {
            "minima": "Mínima — solo errores objetivos",
            "estandar": "Estándar — recomendada",
            "agresiva": "Agresiva — reescribe oraciones torpes",
        }[x],
        index=1,
        label_visibility="collapsed",
    )

    # --- Prompt personalizado (si aplica) ---
    custom = ""
    if tipo == "Otro / Personalizado":
        custom = st.sidebar.text_area(
            "Prompt personalizado",
            height=180,
            placeholder="Escribe aquí tu prompt de corrección…",
        )

    return provider, model, tipo, intensidad, custom


# ---------------------------------------------------------------------------
# Área principal
# ---------------------------------------------------------------------------

def render_main(provider, model, tipo, intensidad, custom):
    st.title("🍔 Corrector.IA")
    st.caption(
        "Corrector de estilo asistido por IA. "
        "Sube un archivo .txt, elige el modelo y el tipo de texto, "
        "y obtén una versión corregida descargable."
    )

    # --- Subida de archivo ---
    archivo = st.file_uploader(
        "Sube el archivo .txt a corregir",
        type=["txt"],
        help="Solo archivos de texto plano. Si tu fuente es Word o PDF, exporta primero a .txt.",
    )

    if archivo is None:
        st.info("Sube un archivo para empezar.")
        return

    # Leer y partir en párrafos
    try:
        contenido = archivo.read().decode("utf-8")
    except UnicodeDecodeError:
        st.error(
            "No pude leer el archivo como UTF-8. "
            "Ábrelo en el Bloc de notas, guárdalo como UTF-8 y vuelve a intentar."
        )
        return

    parrafos = partir_en_parrafos(contenido)
    if not parrafos:
        st.warning("El archivo no contiene párrafos procesables.")
        return

    # Información del archivo
    col1, col2, col3 = st.columns(3)
    col1.metric("Archivo", archivo.name)
    col2.metric("Párrafos", len(parrafos))
    col3.metric("Caracteres", f"{len(contenido):,}")

    # Vista previa expandible
    with st.expander("👁️ Vista previa del primer párrafo"):
        st.text(parrafos[0][:500] + ("…" if len(parrafos[0]) > 500 else ""))

    # --- Prompt resultante ---
    prompt_sistema = prompts.construir_prompt(tipo, intensidad, custom)
    with st.expander("🔍 Ver prompt que se enviará al modelo (avanzado)"):
        st.code(prompt_sistema, language="markdown")

    # --- Botón de procesar ---
    api_key = st.session_state.api_keys.get(provider, "").strip()

    boton_disabled = not api_key
    if st.button(
        "▶️ Procesar archivo",
        type="primary",
        disabled=boton_disabled,
        help="Falta API key" if boton_disabled else None,
    ):
        procesar(parrafos, provider, model, api_key, prompt_sistema, archivo.name)

    # --- Resultado ---
    if st.session_state.resultado is not None:
        nombre, contenido_corregido, errores = st.session_state.resultado
        st.success(f"✓ Procesamiento completo: {nombre}")
        if errores:
            st.warning(f"⚠ {len(errores)} párrafo(s) no se pudieron corregir y se conservó el original. Detalles abajo.")

        col_a, col_b = st.columns(2)
        col_a.download_button(
            label="⬇️ Descargar archivo corregido",
            data=contenido_corregido.encode("utf-8"),
            file_name=nombre,
            mime="text/plain",
            type="primary",
        )
        if errores:
            log_text = f"Errores en el procesamiento ({len(errores)}):\n\n"
            log_text += "\n".join(f"Párrafo #{i}: {err}" for i, err in errores)
            col_b.download_button(
                label="⬇️ Descargar log de errores",
                data=log_text.encode("utf-8"),
                file_name=nombre.replace(".txt", ".errores.log"),
                mime="text/plain",
            )

        # Comparación lado a lado de los primeros párrafos
        with st.expander("🔬 Ver comparación original vs corregido"):
            originales = parrafos[:5]  # primeros 5 para no saturar
            corregidos = contenido_corregido.split("\n\n")[:5]
            for i, (orig, corr) in enumerate(zip(originales, corregidos), start=1):
                st.markdown(f"**Párrafo {i}**")
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("*Original*")
                    st.text(orig)
                with c2:
                    st.markdown("*Corregido*")
                    st.text(corr)
                st.divider()
            if len(parrafos) > 5:
                st.caption(f"(Mostrando 5 de {len(parrafos)} párrafos. Descarga el archivo para ver todos.)")


# ---------------------------------------------------------------------------
# Procesamiento — corre síncrono pero con UI reactiva
# ---------------------------------------------------------------------------

def procesar(parrafos: list[str], provider: str, model: str,
             api_key: str, prompt_sistema: str, nombre_original: str):
    """
    Procesa todos los párrafos secuencialmente con barra de progreso.

    A diferencia del Tkinter, aquí Streamlit ejecuta esto en el script
    principal: el navegador queda esperando la respuesta. Para textos
    grandes (>50 párrafos con modelos lentos) esto puede tardar minutos
    y el navegador puede cortar la conexión. Si eso pasa, hay que migrar
    a streaming o procesamiento en chunks pequeños.
    """
    resultados: list[str] = []
    errores: list[tuple[int, str]] = []

    progreso = st.progress(0, text="Iniciando…")

    for i, parrafo in enumerate(parrafos, start=1):
        progreso.progress(
            i / len(parrafos),
            text=f"Procesando {i}/{len(parrafos)} con {provider} · {model}…"
        )

        res = providers.call_model(
            provider=provider,
            model=model,
            api_key=api_key,
            system=prompt_sistema,
            user=parrafo,
            temperature=0.3,
        )

        if res.ok and res.text.strip():
            resultados.append(res.text.strip())
        else:
            resultados.append(parrafo)
            errores.append((i, res.error or "respuesta vacía"))

    progreso.empty()

    # Construir nombre de salida sanitizado
    nombre_salida = construir_nombre_salida(nombre_original, provider, model)
    contenido_final = "\n\n".join(resultados)

    # Guardar en session_state para poder mostrar el botón de descarga
    st.session_state.resultado = (nombre_salida, contenido_final, errores)

    # Forzar rerun para mostrar el resultado
    st.rerun()


def construir_nombre_salida(nombre_original: str, provider: str, model: str) -> str:
    """Construye el nombre del archivo de salida, sanitizado para Windows."""
    stem = nombre_original.rsplit(".", 1)[0]
    stem = sanitizar(stem)[:80]
    modelo_safe = sanitizar(model)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{stem}__corregido_{provider}-{modelo_safe}_{ts}.txt"


def sanitizar(texto: str) -> str:
    """Quita caracteres ilegales en nombres de archivo Windows."""
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", texto)
    s = re.sub(r"-{2,}", "-", s)
    s = s.rstrip(". ")
    return s or "archivo"


# ---------------------------------------------------------------------------
# Footer informativo
# ---------------------------------------------------------------------------

def render_footer():
    st.divider()
    st.caption(
        "🔒 **Privacidad**: tus API keys solo viven en esta sesión del navegador. "
        "El servidor de esta app **no las almacena**. "
        "Cuando cierres la pestaña, desaparecen y tendrás que volver a meterlas. "
        "El texto que procesas viaja al proveedor de IA que elijas (OpenAI, Anthropic, etc.) "
        "según las políticas de privacidad de cada uno. "
        "Esta app no guarda copias de tus textos."
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    init_session_state()
    provider, model, tipo, intensidad, custom = render_sidebar()
    render_main(provider, model, tipo, intensidad, custom)
    render_footer()


if __name__ == "__main__":
    main()
