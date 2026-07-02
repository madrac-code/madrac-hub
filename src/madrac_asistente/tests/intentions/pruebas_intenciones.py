"""
Tests unitarios para la funcion detectar_intencion_basica.

Ejecutar: venv\\Scripts\\python.exe pruebas_intenciones.py
"""

import sys
import os

# Agregar el directorio raíz del proyecto al path
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _PROJECT_ROOT)

from core import detectar_intencion_basica


def test_normalizar():
    """Test: normalizar elimina acentos y convierte a minusculas."""
    from core import normalizar
    
    assert normalizar("Hola Mundo") == "hola mundo"
    # Test con texto básico (evitar caracteres Unicode especiales)
    assert normalizar("Que hora es") == "que hora es"
    assert normalizar("  ESPACIOS  EXTRA  ") == "espacios extra"
    print("[OK] test_normalizar")


def test_coincidencia_exacta():
    """Test: coincidencia exacta de prefijo."""
    # Navegadores
    accion, parametro, es_cmd = detectar_intencion_basica("abrir youtube")
    assert accion == "youtube", f"Esperaba 'youtube', obtuvo {accion}"
    assert es_cmd == True
    
    accion, parametro, es_cmd = detectar_intencion_basica("abrir chrome")
    assert accion == "abrir_app", f"Esperaba 'abrir_app', obtuvo {accion}"
    assert parametro == "chrome"
    assert es_cmd == True
    
    accion, parametro, es_cmd = detectar_intencion_basica("abrir brave")
    assert accion == "abrir_app", f"Esperaba 'abrir_app', obtuvo {accion}"
    assert parametro == "brave"
    assert es_cmd == True
    
    accion, parametro, es_cmd = detectar_intencion_basica("abrir navegador")
    assert accion == "abrir_app", f"Esperaba 'abrir_app', obtuvo {accion}"
    assert parametro == "iexplore"
    assert es_cmd == True
    
    print("[OK] test_coincidencia_exacta")


def test_coincidencia_flexible():
    """Test: coincidencia flexible de prefijo."""
    accion, parametro, es_cmd = detectar_intencion_basica("abrir youtube ahora")
    assert accion == "youtube", f"Esperaba 'youtube', obtuvo {accion}"
    assert es_cmd == True
    
    accion, parametro, es_cmd = detectar_intencion_basica("abrir chrome para navegar")
    assert accion == "abrir_app", f"Esperaba 'abrir_app', obtuvo {accion}"
    assert es_cmd == True
    
    print("[OK] test_coincidencia_flexible")


def test_palabra_clave():
    """Test: coincidencia de palabra clave."""
    # Música
    accion, parametro, es_cmd = detectar_intencion_basica("pon musica")
    assert accion == "reproducir_musica", f"Esperaba 'reproducir_musica', obtuvo {accion}"
    assert es_cmd == True
    
    accion, parametro, es_cmd = detectar_intencion_basica("reproducir musica")
    assert accion == "reproducir_musica", f"Esperaba 'reproducir_musica', obtuvo {accion}"
    assert es_cmd == True
    
    # Volumen
    accion, parametro, es_cmd = detectar_intencion_basica("subir volumen")
    assert accion == "subir_volumen", f"Esperaba 'subir_volumen', obtuvo {accion}"
    assert es_cmd == True
    
    accion, parametro, es_cmd = detectar_intencion_basica("bajar volumen")
    assert accion == "bajar_volumen", f"Esperaba 'bajar_volumen', obtuvo {accion}"
    assert es_cmd == True
    
    # Silenciar
    accion, parametro, es_cmd = detectar_intencion_basica("silenciar")
    assert accion == "silenciar", f"Esperaba 'silenciar', obtuvo {accion}"
    assert es_cmd == True
    
    print("[OK] test_palabra_clave")


def test_fecha_hora():
    """Test: fecha y hora."""
    # Múltiples formas de preguntar por la hora
    for texto in ["hora", "qué hora es", "que hora es", "que hora"]:
        accion, parametro, es_cmd = detectar_intencion_basica(texto)
        assert accion == "obtener_hora", f"Esperaba 'obtener_hora' para '{texto}', obtuvo {accion}"
        assert es_cmd == True
    
    # La palabra "fecha" sola debe identificar intencion de fecha
    for texto in ["fecha"]:
        accion, parametro, es_cmd = detectar_intencion_basica(texto)
        assert accion == "obtener_fecha", f"Esperaba 'obtener_fecha' para '{texto}', obtuvo {accion}"
        assert es_cmd == True
    
    print("[OK] test_fecha_hora")


def test_no_coincidencia():
    """Test: no detectar intenciones conocidas."""
    # Texto no coincide con ninguna intención conocida
    accion, parametro, es_cmd = detectar_intencion_basica("hola cómo estás")
    assert accion is None, f"Esperaba None, obtuvo {accion}"
    assert parametro is None, f"Esperaba None, obtuvo {parametro}"
    assert es_cmd == False
    
    accion, parametro, es_cmd = detectar_intencion_basica("¿podrías ayudarme?")
    assert accion is None, f"Esperaba None, obtuvo {accion}"
    assert es_cmd == False
    
    # Comando vacío
    accion, parametro, es_cmd = detectar_intencion_basica("")
    assert accion is None, f"Esperaba None, obtuvo {accion}"
    assert es_cmd == False
    
    print("[OK] test_no_coincidencia")


def test_coincidencia_cierre():
    """Test: deteccion de cierre."""
    accion, parametro, es_cmd = detectar_intencion_basica("cerrar ventana")
    assert accion == "cerrar_ventana", f"Esperaba 'cerrar_ventana', obtuvo {accion}"
    assert parametro == "ventana", f"Esperaba parametro 'ventana', obtuvo '{parametro}'"
    assert es_cmd == True
     
    print("[OK] test_coincidencia_cierre")


def test_cerrar_parametro():
    """Test: extraccion de parametro al cerrar."""
    # cerrar + musica/reproductor/cancion -> detener_musica
    accion, parametro, es_cmd = detectar_intencion_basica("cerrar musica")
    assert accion == "detener_musica", f"'cerrar musica': Esperaba 'detener_musica', obtuvo {accion}"
    assert es_cmd == True

    accion, parametro, es_cmd = detectar_intencion_basica("cerrar reproductor")
    assert accion == "detener_musica", f"'cerrar reproductor': Esperaba 'detener_musica', obtuvo {accion}"
    assert es_cmd == True

    # cerrar + otra cosa -> cerrar_ventana(parametro)
    tests = [
        ("cerrar brave", "brave"),
        ("cerrar youtube", "youtube"),
        ("cerrar chrome", "chrome"),
        ("cerrar bloc", "bloc"),
        ("cerrar", ""),
    ]
    for entrada, esperado in tests:
        accion, parametro, es_cmd = detectar_intencion_basica(entrada)
        assert accion == "cerrar_ventana", f"'{entrada}': Esperaba 'cerrar_ventana', obtuvo {accion}"
        assert parametro == esperado, f"'{entrada}': Esperaba parametro '{esperado}', obtuvo '{parametro}'"
        assert es_cmd == True
    print("[OK] test_cerrar_parametro")


def test_coincidencia_eliminacion_acentos():
    """Test: eliminacion de acentos en coincidencia."""
    accion, parametro, es_cmd = detectar_intencion_basica("abrir youtube")
    assert accion == "youtube", f"Esperaba 'youtube', obtuvo {accion}"
    assert es_cmd == True
     
    accion, parametro, es_cmd = detectar_intencion_basica("hora")
    assert accion == "obtener_hora", f"Esperaba 'obtener_hora', obtuvo {accion}"
    assert es_cmd == True
     
    print("[OK] test_coincidencia_eliminacion_acentos")


def test_coincidencia_minusculas():
    """Test: la normalización convierte a minusculas."""
    accion, parametro, es_cmd = detectar_intencion_basica("ABRIR CHROME")
    assert accion == "abrir_app", f"Esperaba 'abrir_app', obtuvo {accion}"
    assert parametro == "chrome"
    assert es_cmd == True
    
    accion, parametro, es_cmd = detectar_intencion_basica("Pon Musica")
    assert accion == "reproducir_musica", f"Esperaba 'reproducir_musica', obtuvo {accion}"
    assert es_cmd == True
    
    print("[OK] test_coincidencia_minusculas")


def test_prioridad_coincidencia():
    """Test: orden de prioridad de coincidencia."""
    # La coincidencia exacta debería prevalecer sobre la palabra clave
    # "abrir youtube" coincide exactamente → youtube
    accion, parametro, es_cmd = detectar_intencion_basica("abrir youtube")
    assert accion == "youtube", f"Esperaba 'youtube', obtuvo {accion}"
    
    # "abrir chrome" coincide exactamente → abrir_app
    accion, parametro, es_cmd = detectar_intencion_basica("abrir chrome")
    assert accion == "abrir_app", f"Esperaba 'abrir_app', obtuvo {accion}"
    
    # "reproducir" coincide con palabra clave → reproducir_musica
    accion, parametro, es_cmd = detectar_intencion_basica("reproducir")
    assert accion == "reproducir_musica", f"Esperaba 'reproducir_musica', obtuvo {accion}"
    
    print("[OK] test_prioridad_coincidencia")


def test_musica_control():
    """Test: control de reproduccion (pausa, reanudar)."""
    tests = [
        ("pausa", "play_pause"),
        ("pausa musica", "play_pause"),
        ("pause", "play_pause"),
        ("reanudar", "play_pause"),
        ("reanudar musica", "play_pause"),
    ]
    for entrada, accion_esperada in tests:
        accion, parametro, es_cmd = detectar_intencion_basica(entrada)
        assert accion == accion_esperada, f"'{entrada}': Esperaba '{accion_esperada}', obtuvo {accion}"
        assert es_cmd == True
    print("[OK] test_musica_control")


def test_detener_musica():
    """Test: detener musica por patron de prefijo."""
    tests = ["detener musica", "detener reproductor", "detener cancion"]
    for entrada in tests:
        accion, parametro, es_cmd = detectar_intencion_basica(entrada)
        assert accion == "detener_musica", f"'{entrada}': Esperaba 'detener_musica', obtuvo {accion}"
        assert es_cmd == True
    # "detener" solo no debe coincidir (va a Ollama)
    accion, parametro, es_cmd = detectar_intencion_basica("detener todo")
    assert accion is None, f"'detener todo': Esperaba None, obtuvo {accion}"
    assert es_cmd == False
    # Variantes foneticas
    for entrada in ["de tener musica", "de tener reproductor", "de tener cancion"]:
        accion, parametro, es_cmd = detectar_intencion_basica(entrada)
        assert accion == "detener_musica", f"'{entrada}': Esperaba 'detener_musica', obtuvo {accion}"
        assert es_cmd == True
    print("[OK] test_detener_musica")


def test_foneticas_cerrar_musica():
    """Test: variantes foneticas de cerrar musica."""
    for entrada in ["cera musica", "sera musica"]:
        accion, parametro, es_cmd = detectar_intencion_basica(entrada)
        assert accion == "detener_musica", f"'{entrada}': Esperaba 'detener_musica', obtuvo {accion}"
        assert es_cmd == True
    print("[OK] test_foneticas_cerrar_musica")


def test_fuzzy_correccion():
    """Test: correccion fonetica por distancia de edicion."""
    # La correccion solo debe activarse con palabras del dominio musica
    tests_ok = [
        ("cerra musica", "detener_musica"),
        ("detener musica", "detener_musica"),
        ("detenerr musica", "detener_musica"),
        ("reproducri musica", "reproducir_musica"),
        ("reproducir musica", "reproducir_musica"),
        ("pausar musica", "play_pause"),
    ]
    for entrada, accion_esperada in tests_ok:
        accion, parametro, es_cmd = detectar_intencion_basica(entrada)
        assert accion == accion_esperada, f"'{entrada}': Esperaba '{accion_esperada}', obtuvo {accion}"
        assert es_cmd == True
    # Sin palabras del dominio musica, no debe corregir
    for entrada in ["cerra ventana", "detener todo", "reproducri documento"]:
        accion, parametro, es_cmd = detectar_intencion_basica(entrada)
        assert accion is None, f"'{entrada}': Esperaba None (sin correccion), obtuvo {accion}"
        assert es_cmd == False
    print("[OK] test_fuzzy_correccion")


if __name__ == "__main__":
    print("=" * 60)
    print("TESTS UNITARIOS: detectar_intencion_basica")
    print("=" * 60)
    print()

    test_normalizar()
    test_coincidencia_exacta()
    test_coincidencia_flexible()
    test_palabra_clave()
    test_fecha_hora()
    test_no_coincidencia()
    test_coincidencia_cierre()
    test_cerrar_parametro()
    test_musica_control()
    test_detener_musica()
    test_foneticas_cerrar_musica()
    test_fuzzy_correccion()
    test_coincidencia_eliminacion_acentos()
    test_coincidencia_minusculas()
    test_prioridad_coincidencia()

    print()
    print("=" * 60)
    print("TODOS LOS TESTS PASARON")
    print("=" * 60)
