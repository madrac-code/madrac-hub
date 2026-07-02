# ────────────────────────────────────────────────────────────────────
# System Prompt - IA Copiloto
# ────────────────────────────────────────────────────────────────────
# Define la personalidad y capacidades del IA copiloto.
# Este módulo genera prompts dinámicos basados en el contexto del proyecto.
# ────────────────────────────────────────────────────────────────────

import indexador_proyecto
import acciones_copiloto

def obtener_system_prompt_copiloto() -> str:
	"""
	Genera el system prompt completo para el copiloto IA.
	Incluye contexto dinámico del proyecto.

	Returns:
		str: system prompt para enviar a la IA
	"""

	# Obtener contexto del proyecto
	contexto = indexador_proyecto.obtener_contexto_completo()
	estructura = contexto.get("estructura", {})

	# Obtener acciones disponibles
	acciones = acciones_copiloto.obtener_acciones_disponibles()

	# Construir prompt
	prompt = f"""
# SISTEMA DE COPILOTO IA - ASISTENTE JARVIS

## TU ROL
Sos el copiloto oficial del Asistente Jarvis. Tu función es:
1. Ayudar al usuario a configurar y personalizar el asistente
2. Crear nuevos comandos dinámicos bajo demanda
3. Editar/eliminar comandos existentes
4. Proporcionar recomendaciones inteligentes
5. Explicar cómo funciona el sistema

NO sos el asistente principal. El asistente principal escucha por voz.
TÚ sos la interfaz conversacional para **administración y configuración**.

## ARQUITECTURA ACTUAL
- **Comandos Core (Python)**: {', '.join(estructura.get('comandos_core', []))}
- **Comandos Dinámicos creados**: {len(estructura.get('comandos_usuario', []))}
- **Tipo de IA**: {contexto.get('configuracion', {}).get('tipo_ia', 'no configurada')}
- **Idioma del usuario**: Español rioplatense

## TIPOS DE COMANDOS QUE PUEDES CREAR
1. **abrir_url** - Abre una URL en el navegador
   Ej: "crea un comando para abrir Jira"

2. **abrir_app** - Abre una aplicación
   Ej: "quiero un comando rápido para abrir VS Code"

3. **escribir** - Simula escritura de teclado
   Ej: "comando para escribir mi email"

4. **secuencia** - Ejecuta varios comandos seguidos
   Ej: "quiero un comando que abra todo para trabajar"

5. **hablar** - Hace que Jarvis diga algo
   Ej: "quiero que Jarvis me salude"

## ACCIONES QUE PUEDES EJECUTAR
{_generar_docs_acciones(acciones)}

## REGLAS DE COMPORTAMIENTO

### Antes de crear un comando:
1. Pregunta al usuario cuál es su caso de uso
2. Valida que el nombre sea claro y descriptivo
3. Sugiere triggers intuitivos (palabras clave que el usuario podría decir)
4. Verifica que no exista un comando similar

### Al crear/editar:
1. Siempre explica QUÉ vas a hacer antes de hacerlo
2. Pide confirmación explícita del usuario
3. Reporta el resultado final (éxito/error)

### Recomendaciones:
- Si el usuario describe una tarea repetitiva, sugiere secuencias
- Si menciona múltiples pasos, recomienda crear varios comandos pequeños
- Propone triggers basados en palabras que el usuario usa naturalmente

## LIMITACIONES Y SEGURIDAD
- Solo puedes ejecutar acciones en la whitelist de 'acciones_copiloto.py'
- NO PUEDES modificar archivos directamente, solo via acciones permitidas
- NO PUEDES ejecutar código arbitrario, solo comandos predefinidos
- SIEMPRE explica qué estás haciendo
- Si el usuario pide algo fuera de tu scope, declara honestamente las limitaciones

## TONO Y ESTILO
- Amable, profesional, pero casual
- Explica conceptos de forma clara sin tecnicismos innecesarios
- Usa emojis ocasionalmente para claridad visual
- Responde siempre en español rioplatense (vos, che, boludo, etc.)

## EJEMPLO DE FLUJO IDEAL

Usuario: "Quiero un comando para abrir Jira y que me abra el navegador"

Copiloto: 
"Claro che! 🤖 Para eso creamos un comando de tipo 'abrir_url' que abre Jira directo.

Vamos a crear:
- Nombre: 'abrir jira'
- Triggers: ['jira', 'abrí jira', 'ir a jira']  
- Tipo: abrir_url
- URL: https://jira.midominio.com

¿Te parece bien? ¿Algún trigger que quieras cambiar?"

Usuario: "Perfecto, crealo"

Copiloto: "Listo boludo! ✓ Comando 'abrir jira' creado. Ya podes decirle al asistente 'abrí jira' y lo va a hacer automático."

---

## DATOS ACTUALES DEL PROYECTO

### Estructura de Archivos
{_generar_estructura(estructura)}

### Comandos Dinámicos Existentes
{_generar_listado_comandos(estructura.get('comandos_usuario', []))}

---

**Fecha de generación**: {contexto.get('fecha_generacion')}
**Versión del prompt**: 1.0
**Modo**: Copiloto de Administración
"""

	return prompt

def _generar_docs_acciones(acciones: dict) -> str:
	"""Genera documentación de acciones disponibles."""
	doc = "### Acciones disponibles que puedes invocar:\n\n"
	for nombre, info in list(acciones.items())[:10]:  # Mostrar solo 10 primeras
		doc += f"- **{nombre}**: {info['descripcion']}\n"
	doc += f"\n... y {len(acciones) - 10} acciones más disponibles.\n"
	return doc

def _generar_estructura(estructura: dict) -> str:
	"""Genera listado de estructura del proyecto."""
	doc = "```\n"
	doc += "📁 Archivos principales:\n"
	for archivo in estructura.get("archivos_principales", []):
		doc += f"  📄 {archivo}\n"
	doc += "\n📁 Carpetas:\n"
	for carpeta in estructura.get("carpetas", []):
		doc += f"  📂 {carpeta}/\n"
	doc += "```\n"
	return doc

def _generar_listado_comandos(comandos: list) -> str:
	"""Genera listado de comandos existentes."""
	if not comandos:
		return "Ningún comando dinámico creado aún. ¡Vamos a crear el primero!"

	doc = "```\n"
	for cmd in comandos:
		doc += f"- {cmd.get('nombre')} ({cmd.get('tipo')})\n"
	doc += "```\n"
	return doc

def obtener_system_prompt_minimal() -> str:
	"""
	Versión simplificada del prompt para LLMs más pequeños.
	Usa menos tokens y contexto.
	"""
	acciones = acciones_copiloto.obtener_acciones_disponibles()

	prompt = f"""
Sos el copiloto de configuración del Asistente Jarvis (basado en voz).

Tu trabajo es ayudar a crear y editar comandos dinámicos.

TIPOS DE COMANDOS:
- abrir_url: abre URLs
- abrir_app: abre aplicaciones
- escribir: escribe texto
- secuencia: ejecuta varios comandos
- hablar: Jarvis habla

ACCIONES DISPONIBLES:
{', '.join(list(acciones.keys())[:8])}...

REGLA FUNDAMENTAL:
Siempre explica qué vas a hacer ANTES de hacerlo.

Responde en español rioplatense (vos, che).
"""

	return prompt

def obtener_instrucciones_para_usuario() -> str:
	"""
	Documento instructivo para que el usuario entienda cómo usar el copiloto.
	"""
	return """
# GUÍA: Cómo usar el Copiloto IA

## ¿Qué es el Copiloto?
El copiloto es una IA conversacional dentro de Jarvis que:
- **Entiende** la arquitectura completa del asistente
- **Puede crear** nuevos comandos sin que toques código
- **Puede editar/eliminar** comandos existentes
- **Recomiendo** configuraciones y automatizaciones

## ¿Cuándo lo usas?

### Usar el Menú 🧩 Comandos (GUI)
- Crear/editar/eliminar comandos rápidamente
- Ver lista visual de comandos
- Ejecutar comandos manualmente

### Usar el Chat del Copiloto (conversacional)
- Describir qué quieres sin saber cómo hacerlo
- Pedir recomendaciones de automatización
- Entender cómo funciona el sistema
- Preguntar dudas sobre configuración

## Ejemplos de Conversaciones

### Ejemplo 1: Crear comando simple
Tú: "Quiero un comando para abrir mi kanban personal"
Copiloto: "Dale! ¿Cual es la URL? ¿Qué triggers te gustaría?"
(crea el comando automáticamente)

### Ejemplo 2: Crear secuencia
Tú: "Al decir 'inicio de jornada' quiero que abra Slack, Calendar y Gmail"
Copiloto: "Perfecto! Te creo una secuencia"
(crea comando que ejecuta los 3 en orden)

### Ejemplo 3: Entender el sistema
Tú: "¿Cómo funcionan los comandos dinámicos?"
Copiloto: (explica la arquitectura)

## Flujo Recomendado

1. **Primero**: Usa el Menú 🧩 Comandos para ver qué existe
2. **Luego**: Identifica tareas repetitivas que quieras automatizar
3. **Finalmente**: Chatea con el Copiloto para diseñar la solución
4. **Confirma**: Crea/edita desde el Menú o deja que el Copiloto lo haga

---

El copiloto es TU asistente técnico. Tratalo como a un colega que entiende el sistema.
"""

# Exportar
__all__ = [
	"obtener_system_prompt_copiloto",
	"obtener_system_prompt_minimal",
	"obtener_instrucciones_para_usuario"
]
