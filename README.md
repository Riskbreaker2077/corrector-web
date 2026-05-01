# Corrector.IA — versión web

Corrector de estilo asistido por IA con interfaz web. Soporta OpenAI, Anthropic
(Claude), Google (Gemini), DeepSeek y MiniMax. Cada usuario mete su propia API
key, que solo vive en su sesión del navegador.

## Ejecutar localmente

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Se abre el navegador en `http://localhost:8501`.

## Desplegar gratis en Streamlit Community Cloud

Esta es la opción para compartir el link con colegas. **Streamlit Cloud es
gratuito para apps públicas** y la cuota es generosa (recursos limitados pero
suficientes para este caso de uso).

### Paso 1 — Subir a GitHub

1. Crea una cuenta en https://github.com si no tienes.
2. Crea un repositorio nuevo, por ejemplo `corrector-ia-web`. Marca **público**
   (Streamlit Cloud gratis solo despliega repos públicos).
3. Sube **estos cuatro archivos** al repo:
   ```
   streamlit_app.py
   providers.py
   prompts.py
   requirements.txt
   .streamlit/config.toml
   ```
   La forma más sencilla si nunca has usado git: en GitHub web, "Add file →
   Upload files", arrastra todo, commit. Para `.streamlit/config.toml`
   asegúrate de mantener la carpeta — GitHub lo respeta si subes el archivo
   con esa ruta.

   **NO subas tus API keys ni nada con `secret`/`key` en el nombre.** El repo
   debe estar limpio.

### Paso 2 — Conectar Streamlit Cloud

1. Entra a https://share.streamlit.io e inicia sesión con tu cuenta de GitHub.
2. Pulsa **"Create app"** o **"New app"**.
3. Conecta tu repositorio. Configuración:
   - **Repository**: tu cuenta/`corrector-ia-web`
   - **Branch**: `main`
   - **Main file path**: `streamlit_app.py`
   - **App URL** (opcional): elige un subdominio, por ejemplo
     `corrector-ia.streamlit.app`. Ese será el link que compartes.
4. Pulsa **Deploy**. Espera 2-4 minutos mientras instala dependencias.
5. Cuando esté listo, te da una URL pública del estilo
   `https://corrector-ia.streamlit.app`. Esa es la que mandas a tus colegas.

### Paso 3 — Mantener actualizado

Cada vez que hagas un commit en GitHub, Streamlit Cloud re-despliega
automáticamente en 1-2 minutos. No tienes que volver a hacer nada.

## Estructura del proyecto

```
corrector-web/
├── streamlit_app.py       # GUI de Streamlit (única página)
├── providers.py           # Capa unificada para OpenAI/Anthropic/Gemini/DeepSeek/MiniMax
├── prompts.py             # Catálogo de prompts por tipo × intensidad
├── requirements.txt       # Dependencias para pip
├── .streamlit/
│   └── config.toml        # Tema y configuración de Streamlit
└── README.md
```

`providers.py` y `prompts.py` son **idénticos a los del programa de escritorio**
— no se cambia ni una línea. Si quieres añadir un proveedor nuevo o un tipo de
texto nuevo, lo haces ahí y la app web lo recoge.

## Privacidad y seguridad

Esta app está pensada para uso de profesores que ya tienen su propia API key.

- Las API keys que el usuario introduce viven solo en `st.session_state`, que
  Streamlit mantiene en memoria del servidor durante la sesión del navegador.
  Cuando el usuario cierra la pestaña, Streamlit elimina la sesión y las keys
  se pierden.
- **El servidor no guarda nada en disco.** No hay base de datos, no hay
  archivos de logs con keys, no hay backups.
- El texto que el usuario sube se procesa en memoria y se descarga al navegador
  como .txt. Tampoco se guarda en disco del servidor.
- El texto sí viaja al proveedor de IA que el usuario elija (OpenAI, Anthropic,
  etc.). Las políticas de privacidad de cada proveedor aplican ahí.

## Limitaciones conocidas

**Procesamiento síncrono.** Streamlit ejecuta el script principal y mantiene
el navegador esperando. Para textos de >50 párrafos con un modelo lento
(claude-opus-4-7, por ejemplo), puede tardar varios minutos. Si el navegador
o un proxy intermedio cortan la conexión por timeout, se pierde el progreso.

Si esto se vuelve un problema en la práctica, las soluciones son:
1. Recomendar al usuario `gpt-4o-mini` o `deepseek-v4-flash` (rápidos y baratos).
2. Procesar en lotes más pequeños (partir el .txt en archivos de 20 párrafos).
3. Migrar a una arquitectura con cola de tareas (Celery/Redis) — esto saca el
   proyecto del free tier de Streamlit Cloud.

**Sin almacenamiento de progreso.** Si el usuario cierra la pestaña a la mitad
del procesamiento, pierde el avance. La versión de escritorio escribía
incrementalmente a disco; aquí no podemos porque no hay disco accesible al
usuario.

**Cuota de Streamlit Cloud.** El free tier tiene límites de RAM y CPU. Para uso
de un grupo pequeño de profesores está bien. Si lo abres a cientos de usuarios
simultáneos, eventualmente la app se ralentizará y necesitarás un plan pagado o
migrar a otro servicio (Railway, Fly.io, Render).
