# Corrector.IA — versión web

Aplicación web que devuelve una **corrección de estilo** de un documento
en **formato crudo** (`.txt` plano, UTF-8). El usuario sube un `.txt`, la
app lo procesa párrafo por párrafo contra un modelo de IA, y entrega como
salida otro `.txt` con la versión corregida.

Pensado para profes de lengua, editores, estudiantes de posgrado y
cualquiera que necesite pulir un texto en español sin perder su voz.

> ⚠️ **Formato de entrada y salida: solo `.txt` plano.** No acepta `.docx`,
> `.pdf`, `.md` ni Markdown enriquecido. Si tu fuente es Word o PDF,
> expórtala primero a `.txt` UTF-8 desde tu editor.

**App en vivo:** https://web-hamburguesa-extra.streamlit.app/

## ¿Qué hace?

Subes un archivo `.txt`, eliges proveedor de IA + modelo + tipo de texto +
intensidad, y la app te devuelve una versión corregida del mismo `.txt`
que puedes descargar.

El procesamiento es **párrafo por párrafo**: la app parte tu texto por líneas
en blanco, envía cada párrafo al modelo con un prompt especializado, y al final
recompone el archivo. Si un párrafo falla (timeout, error de API), conserva el
original y lo registra en un log de errores descargable.

## Cómo funciona (paso a paso)

1. **Subes un `.txt`.** El archivo se lee en memoria y se parte por párrafos
   (líneas en blanco). Si tu fuente es Word o PDF, expórtalo a `.txt` primero.
2. **Abres "API keys" en la barra lateral** y pegas la clave del proveedor
   que vayas a usar. La clave **solo vive en tu sesión del navegador**: ni se
   guarda en disco, ni se envía a ningún sitio más que al proveedor.
3. **Eliges proveedor y modelo.** Por defecto OpenAI con `gpt-5.5`. DeepSeek
   y MiniMax son las opciones más baratas.
4. **Eliges el tipo de texto** (Académico, Tesis/Filosofía, Literario,
   Periodístico, Técnico, Pedagógico, Editorial, Correspondencia, Otro).
5. **Eliges la intensidad** de la intervención:
   - **Mínima** — solo errores objetivos (tildes, signos, concordancia).
   - **Estándar** — lo anterior + ambigüedades, anglicismos, muletillas.
   - **Agresiva** — lo anterior + reescribe oraciones torpes, reordena,
     ajusta ritmo. Conserva la voz del autor.
6. **Pulsa "Procesar archivo".** Verás una barra de progreso
   (`Procesando 3/27 con OpenAI · gpt-5.5…`) y, al terminar, botones para:
   - Descargar el archivo corregido.
   - Descargar el log de errores (si los hubo).
   - Ver una comparación lado a lado de los primeros 5 párrafos.

El archivo de salida se llama
`<original>__corregido_<proveedor>-<modelo>_<timestamp>.txt`.

## Tipos de texto soportados

Cada tipo fija qué se toca y qué se respeta. Esto es importante: un texto
filosófico y uno periodístico no se corrigen igual.

| Tipo | Cuida especialmente | No toca |
|---|---|---|
| Académico (general) | Conectores, gerundios de posterioridad, "el cual/la cual/cuyo" | Tecnicismos, citas, formato APA/Chicago/ISO 690 |
| Tesis doctoral / Filosofía | Distinciones uso/mención, distinciones autor/comentarista, carga argumentativa, latinismos y alemán/griego en cursiva | Traducciones citadas, tecnicismos filosóficos (Bildung, Dasein, phrónesis…) |
| Literario / Narrativo | Voz y ritmo del narrador, rayas de diálogo, tiempos verbales narrativos, repeticiones intencionales | Licencias estilísticas, neologismos, registros coloquiales en diálogos |
| Periodístico | Frases cortas en voz activa, lead claro, atribuciones limpias, cifras consistentes | Declaraciones textuales, nombres y cargos |
| Técnico / Manual | Imperativo claro, terminología consistente, listas paralelas | Nombres de funciones, variables, comandos, rutas, código |
| Pedagógico (bachillerato) | Claridad sin perder rigor, conectores para lector joven, vocabulario técnico introducido | Definiciones formales, citas, ejemplos contextualizados |
| Editorial / Norma estricta | Comillas latinas (« »), raya (—), espacios en abreviaturas, mayúsculas RAE, numeral hasta nueve | Referencias bibliográficas, DOI, URL |
| Correspondencia formal | Saludo/despedida, propósito claro, cortesía sin servilismo | Nombres, cargos, fechas, números de oficio |
| Otro / Personalizado | (Tú defines el prompt en la caja inferior) | (Tú decides) |

## Proveedores y modelos disponibles

| Proveedor | Modelos incluidos | Dónde sacar la API key |
|---|---|---|
| OpenAI | `gpt-5.5`, `gpt-5.4`, `gpt-5.4-mini`, `gpt-4o-mini` | https://platform.openai.com/api-keys |
| Anthropic | `claude-opus-4-7`, `claude-sonnet-4-6`, `claude-haiku-4-5` | https://console.anthropic.com/settings/keys |
| Gemini | `gemini-2.5-pro`, `gemini-2.5-flash` | https://aistudio.google.com/apikey |
| DeepSeek | `deepseek-v4-pro`, `deepseek-v4-flash` | https://platform.deepseek.com/api_keys |
| MiniMax | `MiniMax-M2.7`, `MiniMax-M2.5` | https://platform.minimax.io/user-center/basic-information/interface-key |

**Recomendación rápida:**

- **Presupuesto bajo / textos largos:** `deepseek-v4-flash`, `gpt-4o-mini` o
  `MiniMax-M2.5`.
- **Calidad máxima (cuesta más):** `gpt-5.5`, `claude-opus-4-7`.
- **Balance:** `gpt-5.4` o `claude-sonnet-4-6`.
- **Filosofía/tesis:** Anthropic suele funcionar muy bien para preservar
  distinciones conceptuales.

## Privacidad y seguridad (esto importa)

- **Tu API key** vive solo en `st.session_state`, memoria del servidor de
  Streamlit mientras dura tu pestaña. Cuando cierras, desaparece.
- **Tu texto** se procesa en memoria y se descarga a tu navegador. No se
  guarda en disco del servidor.
- **El servidor no tiene base de datos, ni logs con keys, ni backups.**
- El texto **sí viaja al proveedor de IA que elijas** (OpenAI, Anthropic,
  etc.). Las políticas de privacidad de cada proveedor aplican ahí.

## Limitaciones conocidas

- **Procesamiento síncrono.** Para textos de >50 párrafos con un modelo
  lento, el navegador puede cortar la conexión por timeout. Soluciones:
  usar un modelo rápido (`gpt-4o-mini`, `deepseek-v4-flash`), partir el
  `.txt` en lotes de ~20 párrafos, o migrar a una arquitectura con cola
  de tareas (esto último sale del free tier).
- **Sin almacenamiento de progreso.** Si cierras la pestaña a la mitad,
  pierdes el avance.
- **Free tier de Streamlit Cloud** tiene límites de RAM y CPU. Para uso
  individual o grupo pequeño está bien; para cientos de usuarios
  simultáneos se ralentiza o hay que migrar a un plan pagado.

## Ejecutar localmente

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Se abre en `http://localhost:8501`. Útil si quieres desarrollar, probar
cambios en `prompts.py` o no depender de la app pública.

## Estructura del proyecto

```
corrector-web/
├── streamlit_app.py        # GUI de Streamlit (única página)
├── providers.py            # Capa unificada OpenAI/Anthropic/Gemini/DeepSeek/MiniMax
├── prompts.py              # Catálogo de prompts por tipo × intensidad
├── requirements.txt        # Dependencias (streamlit, openai, anthropic, google-genai)
├── .streamlit/
│   └── config.toml         # Tema y configuración de Streamlit
├── .devcontainer/
│   └── devcontainer.json   # Para abrir en GitHub Codespaces
├── .gitignore
└── README.md
```

`providers.py` y `prompts.py` son la lógica real. `streamlit_app.py` solo
orquesta: lee inputs, llama a `providers.call_model`, muestra resultados.

## Cómo desplegar tu propia copia

La app actual está desplegada en Streamlit Community Cloud (gratis para
apps públicas). Si quieres levantar la tuya:

1. Haz fork de este repo o créalo nuevo y sube los archivos.
2. Entra a https://share.streamlit.io con tu cuenta de GitHub.
3. "New app" → selecciona repo, branch `main`, main file `streamlit_app.py`.
4. Elige un subdominio (ej. `tu-corrector.streamlit.app`).
5. Deploy. Espera 2-4 minutos.

Cada commit en `main` re-despliega automáticamente.

## Licencia

MIT — úsalo, modifícalo, compártelo. Si haces una versión que te funciona
bien, un PR con los prompts mejorados es bienvenido.