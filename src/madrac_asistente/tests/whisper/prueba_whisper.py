# ────────────────────────────────────────────────────────────────────
# Prueba de parámetros de Faster-Whisper
# Mide WER (jiwer) con distintas configuraciones sobre audios de prueba
# ────────────────────────────────────────────────────────────────────

import os
import sys
import json
import time
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
from faster_whisper import WhisperModel
from jiwer import wer, cer


# ─── CONFIG ────────────────────────────────────────────────────────

# Transcripciones de referencia (lo que realmente dijo el usuario)
REFERENCIAS = {
    "poner_musica": "poner música",
    "pausar_musica": "pausar música",
    "cerrar_musica": "cerrar música",
    "subir_volumen": "subir el volumen",
    "abrir_youtube": "abrir youtube",
    "siguiente_cancion": "siguiente canción",
}

# Parámetros a probar (producto cartesiano)
MODELOS = ["small", "medium"]
BEAM_SIZES = [1, 2, 5, 10]
VAD_FILTERS = [False, True]
TEMPERATURES = [0.0, 0.2, 0.5]
CONDITION_ON_PREVIOUS = [False, True]
HOTWORDS_OPCIONES = [
    "",
    "MÚSICA VOLUMEN YOUTUBE ABRIR CERRAR",
    "música volumen youtube abrir cerrar poner pausar siguiente anterior"
]


# ─── GRABACIÓN ─────────────────────────────────────────────────────

def grabar_audio(segundos=5, sample_rate=16000, nombre_base="test"):
    """
    Graba audio del micrófono default y guarda .wav.
    Retorna la ruta del archivo.
    """
    print(f"Grabando '{nombre_base}' ({segundos}s)...")
    audio = sd.rec(int(segundos * sample_rate), samplerate=sample_rate,
                   channels=1, dtype="int16")
    sd.wait()
    ruta = f"{nombre_base}.wav"
    wav.write(ruta, sample_rate, audio)
    print(f"  Guardado: {ruta}")
    return ruta


def grabar_lote():
    """
    Graba un conjunto de frases de prueba.
    El usuario debe decir cada frase cuando se le indique.
    """
    rutas = {}
    for key, frase in REFERENCIAS.items():
        input(f"Presioná Enter y decí: '{frase}'")
        ruta = grabar_audio(nombre_base=key)
        rutas[key] = ruta
    return rutas


# ─── EVALUACIÓN ────────────────────────────────────────────────────

def evaluar_combinacion(modelo, beam_size, vad_filter, temperature,
                        condition_on_previous_text, hotwords,
                        audio_data):
    """
    Transcribe con los parámetros dados y devuelve (texto, tiempo_seg).
    """
    whisper = WhisperModel(modelo, device="cpu",
                           compute_type="int8")
    inicio = time.time()

    kwargs = dict(
        language="es",
        beam_size=beam_size,
        vad_filter=vad_filter,
        temperature=temperature,
        condition_on_previous_text=condition_on_previous_text,
    )
    if hotwords:
        kwargs["hotwords"] = hotwords

    segments, info = whisper.transcribe(audio_data, **kwargs)
    texto = " ".join(s.text for s in segments).strip().lower()

    elapsed = time.time() - inicio
    return texto, elapsed


def ejecutar_bateria(audios, referencias):
    """
    Ejecuta todas las combinaciones de parámetros sobre los audios.
    Imprime tabla comparativa con WER.
    """
    resultados = []
    total_combinaciones = (
        len(MODELOS) * len(BEAM_SIZES) * len(VAD_FILTERS) *
        len(TEMPERATURES) * len(CONDITION_ON_PREVIOUS) * len(HOTWORDS_OPCIONES)
    )
    ejecutadas = 0

    for modelo in MODELOS:
        for beam in BEAM_SIZES:
            for vad in VAD_FILTERS:
                for temp in TEMPERATURES:
                    for cond in CONDITION_ON_PREVIOUS:
                        for hw in HOTWORDS_OPCIONES:
                            ejecutadas += 1
                            errores = []
                            tiempos = []

                            for key, ruta_wav in audios.items():
                                texto, elapsed = evaluar_combinacion(
                                    modelo, beam, vad, temp, cond, hw, ruta_wav
                                )
                                ref = referencias[key]
                                error = wer(ref, texto)
                                errores.append(error)
                                tiempos.append(elapsed)

                            wer_promedio = sum(errores) / len(errores)
                            tiempo_promedio = sum(tiempos) / len(tiempos)

                            resultados.append({
                                "modelo": modelo,
                                "beam_size": beam,
                                "vad_filter": vad,
                                "temperature": temp,
                                "condition_on_prev": cond,
                                "hotwords": hw[:30] if hw else "(none)",
                                "wer": round(wer_promedio, 4),
                                "tiempo": round(tiempo_promedio, 2),
                            })

                            pct = ejecutadas / total_combinaciones * 100
                            sys.stdout.write(
                                f"\r  [{ejecutadas}/{total_combinaciones}] "
                                f"{pct:.0f}%  WER={wer_promedio:.3f}  "
                                f"modelo={modelo} beam={beam} vad={vad}"
                            )
                            sys.stdout.flush()

    print("\n\n=== RESULTADOS ===")
    print(f"{'Modelo':<8} {'Beam':<5} {'VAD':<5} {'Temp':<5} "
          f"{'CondPrev':<8} {'WER':<6} {'T(s)':<6} Hotwords")
    print("-" * 80)
    mejores = sorted(resultados, key=lambda r: r["wer"])[:10]
    for r in mejores:
        print(f"{r['modelo']:<8} {r['beam_size']:<5} {r['vad_filter']:<5} "
              f"{r['temperature']:<5} {r['condition_on_prev']:<8} "
              f"{r['wer']:<6} {r['tiempo']:<6} {r['hotwords']}")

    mejor = min(resultados, key=lambda r: r["wer"])
    print("\n★ MEJOR CONFIGURACIÓN:")
    print(json.dumps(mejor, indent=2, ensure_ascii=False))
    return mejor


# ─── MAIN ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--grabar", action="store_true",
                        help="Grabar audios de prueba primero")
    parser.add_argument("--dir", default=".",
                        help="Directorio con audios .wav ya grabados")
    args = parser.parse_args()

    if args.grabar:
        print("Grabando audios de prueba...")
        print("(necesitás micrófono conectado)")
        audios = grabar_lote()
    else:
        # Buscar archivos .wav pre-grabados
        disponibles = {}
        for key in REFERENCIAS:
            ruta = os.path.join(args.dir, f"{key}.wav")
            if os.path.exists(ruta):
                disponibles[key] = ruta
                print(f"  Encontrado: {ruta}")
        if not disponibles:
            print("No hay audios. Usá --grabar para grabarlos.")
            sys.exit(1)
        if len(disponibles) < len(REFERENCIAS):
            print(f"  (disponibles {len(disponibles)}/{len(REFERENCIAS)})")
        audios = disponibles

    mejor = ejecutar_bateria(audios, REFERENCIAS)
