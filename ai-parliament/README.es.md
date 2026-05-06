# Parlamento de IAs

Bueno, voy a explicar de qué va esto y cómo está montado.

La idea es simple: hay 6 IAs con personalidades distintas (basadas en MBTI) que viven su vida en una pantalla, se pasean, hablan entre ellas, y cuando tú escribes una pregunta, se convocan en el parlamento, debaten, y votan. Todo con un modelo de lenguaje local corriendo en tu propia máquina.

## Por qué hice esto

El objetivo real era experimentar con IAs locales y ver varias cosas:

- Si los modelos eran suficientemente rápidos como para hacer algo en tiempo real o si era desesperante esperar
- Qué calidad de respuestas daban cuando se les daba un rol y un contexto
- Si de verdad "escuchaban" lo que decían las otras IAs o simplemente ignoraban el historial del debate
- Si había demasiado consenso (spoiler: sí, tienden a ponerse de acuerdo mucho)
- Si las personalidades MBTI se notaban en las respuestas o era todo igual

La respuesta corta: funciona, es interesante, pero tiene limitaciones bastante claras que explico más abajo.

## Los 6 agentes

Cada uno tiene un color, una personalidad, y una posición fija en el mapa donde vive.

| Color | Nombre | MBTI | Rol |
|---|---|---|---|
| Azul | Aris | INTP | El Arquitecto — analítico, lógico |
| Amarillo | Nova | ENFP | La Visionaria — creativa, entusiasta |
| Gris | Doctore | ISTJ | El Inspector — datos, evidencia |
| Rojo | Kaito | ENTJ | El Comandante — estratégico, directo |
| Morado | Lyra | INFJ | La Profeta — intuitiva, holística |
| Naranja | Naranjito | ESFP | La Animadora — práctica, social |

El `system_prompt` de cada uno le dice quién es, cómo habla, y qué frases usa. Eso es lo que hace que Aris diga "lógicamente..." y Naranjito diga "¡vamos a lo importante!". Si quieres cambiar la personalidad de alguno, editas ese texto en `config.py`.

## Setup

```bash
# 1. Instalar Ollama desde https://ollama.com
ollama serve                       # déjalo corriendo en otra terminal
ollama pull llama3.2               # el modelo que usan las IAs (~2 GB) (otro modelo con más potencia haría el programa más fluido)
ollama pull nomic-embed-text       # opcional, para memoria semántica (~270 MB)

# 2. Instalar dependencias Python
pip install -r requirements.txt

# 3. Arrancar
python main.py
```

Si tu máquina aguanta modelos más grandes, cambia `OLLAMA_MODEL` en `config.py`. Con `qwen2.5:7b` o `mistral` las respuestas son notablemente mejores en español, aunque más lentas. Por eso uso Ollama porque si no demoraría demasiado.

## Controles

No hay mucho:

| Acción | Tecla |
|---|---|
| Convocar parlamento | Escribe tu pregunta + **ENTER** |
| Activar / desactivar voz | **F2** |
| Interrumpir parlamento | **ESC** |
| Scroll en paneles | **Rueda del ratón** |

## Las fases del parlamento

Cuando escribes una pregunta pasan estas cosas, en orden:

**A. Convocatoria** — Las 6 IAs caminan hacia el círculo central.

**B. Pensamiento interno** — Cada una genera en privado su reflexión sobre la pregunta. Es paralelo, así que los 6 piensan a la vez. No se habla en voz alta y no lo ven las demás.

**C. Debate externo** — Hablan por turnos. Cada IA ve el historial de lo que han dicho las anteriores y puede responder. Esto es secuencial (uno espera al otro), que es lo que hace que sea lento.

**E. Postura final** — Cada una resume su posición definitiva antes de votar. Paralelo.

**F. Votación** — Votan A FAVOR o EN CONTRA. Paralelo.

**G. Resultado** — Un "secretario" (otra llamada al LLM) sintetiza el debate y da el resultado. Aparece en verde en el panel.

**H. Disolución** — Vuelven a sus casas y retoman la vida diaria.

## Cómo está montado el código

```
main.py           → el loop principal de pygame, eventos, dibujado
config.py         → todos los ajustes y los perfiles MBTI de cada agente
agent.py          → cada IA: estado, movimiento, animación, llamadas al LLM
parliament.py     → orquesta las fases A-H
ollama_client.py  → hace las peticiones HTTP a Ollama con reintentos automáticos
ui.py             → paneles laterales, caja de texto, header y footer
memory.py         → guarda los parlamentos en JSON y los recupera por relevancia
tts.py            → voz local con pyttsx3, cola serial para que no se solapen
```

Las llamadas al LLM no bloquean la animación porque cada agente lanza un `threading.Thread` cuando necesita generar texto. El loop de pygame sigue corriendo a 60 FPS mientras Ollama trabaja.

## La memoria entre sesiones

Al terminar cada parlamento, se guarda en `parliament_memory.json` lo que dijo cada agente, cómo votó, y el consenso final. La próxima vez que haya un parlamento sobre un tema parecido, cada IA recibe en su prompt un resumen de lo que dijo antes.

La búsqueda de recuerdos relevantes funciona en tres modos según lo que tengas instalado:

- **Semántico** — usa embeddings vectoriales (`nomic-embed-text`). Encuentra temas similares aunque usen palabras distintas.
- **Keyword** — Jaccard sobre palabras clave. Más básico pero no necesita nada extra.
- **Recent** — simplemente los últimos N parlamentos. Siempre funciona.

Se detecta automáticamente al arrancar. Si luego instalas `nomic-embed-text`, calcula los embeddings de las entradas antiguas en segundo plano.

## La voz

Cada agente tiene un índice de voz del sistema y una velocidad distinta. Aris habla lento y reflexivo, Naranjito habla rápido. En Windows usa SAPI5 (las voces que tengas instaladas). En macOS usa NSSpeechSynthesizer.

Lo que se habla en voz alta: saludos casuales, intervenciones en el debate, posturas finales, razones del voto.

Lo que no se habla: los pensamientos internos (son privados por diseño) y el consenso del secretario.

La cola de voz es serial, así que aunque los LLMs generen respuestas en paralelo, las voces suenan una detrás de otra sin solaparse.

## Los indicadores visuales

Cada agente tiene un **punto de color** en la esquina inferior izquierda que indica su estado:

- Gris oscuro → quieto en casa
- Verde → paseando
- Amarillo → acercándose a otro agente
- Cian → conversación casual
- Rojo → moviéndose al parlamento
- Morado brillante → pensando internamente
- Amarillo intenso → debatiendo
- Naranja → votando
- Verde claro → volviendo a casa

Cuando está pensando (esperando respuesta del LLM), aparecen **3 puntos amarillos parpadeantes** encima del nombre.

El **anillo pulsante** alrededor del cuerpo aparece cuando está activo en algo: conversación, debate, pensamiento o votación. El color del anillo varía según la fase.

## Inconvenientes que tiene

Esto es importante porque si lo vas a usar conviene saber con qué te vas a encontrar.

**Los modelos tardan mucho.** Ollama corre en local, totalmente gratis, pero en CPU normal cada respuesta puede tardar entre 5 y 20 segundos. Un parlamento completo puede llevarse 2-3 minutos. Si tienes GPU es mucho más rápido. Es la limitación más grande que hay.

**Hay timeouts.** Cuando 6 agentes llaman a Ollama en paralelo, Ollama los procesa de uno en uno internamente. El último de la cola puede esperar 90 segundos solo en la cola, más el tiempo de generación. Si el modelo es lento ese día, se pasa del timeout. Hay reintentos automáticos (hasta 3 intentos con 180 segundos cada uno), pero si Ollama está muy cargado puede fallar igualmente. En las fases anteriores al debate no importa mucho, pero en la postura final hay un fallback que usa lo que el agente dijo en el debate como postura.

**Las voces a veces no suenan.** pyttsx3 con SAPI5 en Windows tiene un bug conocido donde después de la primera locución el motor acumula estado interno y las siguientes fallan silenciosamente. Lo he intentado resolver reinicializando el motor para cada frase, pero en algunos sistemas puede seguir siendo inestable. Si no escuchas nada después del primer agente, es esto.

**Los textos a veces salen cortados.** El modelo genera hasta un límite de tokens. Si una frase es larga y llega al límite, se corta a mitad. Subi los tokens para reducirlo pero no desaparece del todo sin ralentizar mucho más el proceso.

**Demasiado consenso.** Los modelos tienden a llegar a acuerdos. Rara vez hay debates encendidos de verdad. En general todos acaban apoyando alguna versión de la misma idea. Es una limitación del modelo, no del código. Suele ser 5 a favor 1 en contra o al revés.

**Las personalidades se notan poco con modelos pequeños.** Con `llama3.2:3b` las diferencias entre agentes son sutiles. Con modelos más grandes (`qwen2.5:7b`, `mistral`) las personalidades MBTI se notan bastante más en el tono y el tipo de argumentos.

**No hay interacción real entre agentes fuera del parlamento.** En la vida diaria se acercan y se saludan, pero no hay memoria de esas conversaciones ni influyen en el parlamento. Cada agente es independiente salvo por el historial del debate que se inyecta en el prompt.

## Configuración rápida

Todo lo ajustable está en `config.py`:

- `DEBATE_ROUNDS` — rondas de debate (1 por defecto, más rondas = más lento pero más real)
- `MEMORY_RECALL_N` — cuántos parlamentos pasados recibe cada agente en el prompt
- `MEMORY_RECALL_MODE` — `"auto"`, `"semantic"`, `"keyword"` o `"recent"`
- `OLLAMA_MODEL` — el modelo que usan todos los agentes
- `TTS_ENABLED_DEFAULT` — si la voz arranca activada o no

Para empezar la memoria de cero, borra `parliament_memory.json`.

## Ideas que quedaron pendientes

- La interfaz gráfica está muy pixelada, intente resolverla con el Claude pero sigue sin ser nítido.
- Coaliciones visuales: que las IAs se agrupen antes de votar según afinidad
- Modo rebelde: que un agente pueda oponerse al consenso si su convicción es muy fuerte
- Exportar parlamentos a HTML navegable
- Panel que muestre qué recuerdos pasados están influyendo en el parlamento actual
