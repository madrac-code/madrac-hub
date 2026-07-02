# ────────────────────────────────────────────────────────────────────
# PRUEBA DE PARÁMETROS DE FASTER-WHISPER
# Mide WER (Word Error Rate) con jiwer sobre audios en español
# rioplatense grabados con distintos micrófonos
# ────────────────────────────────────────────────────────────────────

import os
import sys
import json
import time
import tempfile
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
from faster_whisper import WhisperModel
from jiwer import wer, cer


# ─── CONFIGURACIÓN ─────────────────────────────────────────────────

# Textos de referencia (lo que realmente dijo el usuario)
REFERENCIAS = {
    "poner_musica":     "poner música",
    "pausar_musica":    "pausar música",
    "cerrar_musica":    "cerrar música",
    "subir_volumen":    "subir el volumen",
    "abrir_youtube":    "abrir youtube",
    "siguiente_cancion": "siguiente canción",
    "bajar_volumen":    "bajar el volumen",
    "obtener_hora":     "obtener la hora",
}


# ─── GRABACIÓN ─────────────────────────────────────────────────────

def grabar_audio(segundos=5, sample_rate=16000, device=None):
    """Graba audio del micrófono y lo guarda como WAV temporal."""
    print(f"  Grabando {segundos}s...")
    audio = sd.rec(
        int(segundos * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype="int16",
        device=device
    )
    sd.wait()

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    wav.write(tmp.name, sample_rate, audio)
    return tmp.name


def grabar_lote(device=None, label=""):
    """
    Graba todas las frases de referencia.
    Retorna dict: {clave: ruta_wav}
    """
    rutas = {}
    print(f"\n{'='*50}")
    print(f"GRABAR LOTE ({label})")
    print(f"{'='*50}")

    for key, frase in REFERENCIAS.items():
        input(f"  Presioná Enter y decí: '{frase}'")
        ruta = grabar_audio(device=device)
        rutas[key] = ruta
        print(f"  → Guardado: {key}.wav")

    return rutas


def grabar_lote_dispositivos():
    """
    Graba audios de prueba con dos micrófonos distintos.
    Retorna: {"droidcam": {rutas}, "real": {rutas}}
    """
    import sounddevice as sd
    dispositivos = sd.query_devices()
    print("\nDispositivos de entrada disponibles:")
    for i, d in enumerate(dispositivos):
        if d['max_input_channels'] > 0:
            print(f"  {i}: {d['name']}")

    print("\n¿Querés grabar con dos dispositivos diferentes?")
    print("  1 = Sí, DroidCam y micrófono real")
    print("  2 = No, solo con el default")

    opcion = input("Elegí (1/2): ").strip()

    lotes = {}

    if opcion == "1":
        idx_droidcam = input("Índice del micrófono DroidCam: ").strip()
        idx_real = input("Índice del micrófono real: ").strip()

        lotes["droidcam"] = grabar_lote(
            device=int(idx_droidcam),
            label="DroidCam"
        )
        lotes["real"] = grabar_lote(
            device=int(idx_real),
            label="Micrófono Real"
        )
    else:
        lotes["default"] = grabar_lote(label="Default")

    return lotes


# ─── TEST DE UNA COMBINACIÓN ──────────────────────────────────────

def transcribir_con_parametros(audio_path, modelo, beam_size, vad_filter,
                                temperature, condition_on_previous_text,
                                hotwords):
    """
    Transcribe un audio con los parámetros dados.
    Retorna: (texto_transcrito, tiempo_segundos)
    """
    whisper = WhisperModel(modelo, device="cpu", compute_type="int8")

    kwargs = dict(
        language="es",
        beam_size=beam_size,
        vad_filter=vad_filter,
        temperature=temperature,
        condition_on_previous_text=condition_on_previous_text,
    )
    if hotwords:
        kwargs["hotwords"] = hotwords

    inicio = time.time()
    segments, info = whisper.transcribe(audio_path, **kwargs)
    texto = " ".join(s.text for s in segments).strip().lower()
    tiempo = time.time() - inicio

    return texto, tiempo


# ─── BATERÍA DE PRUEBAS ──────────────────────────────────────────

def ejecutar_bateria(audios, referencias):
    """
    Ejecuta todas las combinaciones de parámetros sobre los audios.
    Retorna lista de resultados ordenados por WER.
    """
    MODELOS = ["small", "medium"]
    BEAM_SIZES = [1, 2, 5, 10]
    VAD_FILTERS = [False, True]
    TEMPERATURES = [0.0, 0.2, 0.5]
    CONDITION_ON_PREV = [False, True]
    HOTWORDS_OPCIONES = [
        "",
        "MÚSICA VOLUMEN YOUTUBE ABRIR CERRAR",
        "música volumen youtube abrir cerrar poner pausar siguiente anterior"
    ]

    total = (len(MODELOS) * len(BEAM_SIZES) * len(VAD_FILTERS) *
             len(TEMPERATURES) * len(CONDITION_ON_PREV) *
             len(HOTWORDS_OPCIONES))

    resultados = []
    ejecutadas = 0

    print(f"\n{'='*60}")
    print(f"EJECUTANDO {total} COMBINACIONES...")
    print(f"{'='*60}\n")

    for modelo in MODELOS:
        for beam in BEAM_SIZES:
            for vad in VAD_FILTERS:
                for temp in TEMPERATURES:
                    for cond in CONDITION_ON_PREV:
                        for hw in HOTWORDS_OPCIONES:
                            ejecutadas += 1
                            transcripciones = []
                            errores = []
                            tiempos = []

                            for key, ruta in audios.items():
                                if key not in referencias:
                                    continue
                                ref = referencias[key]

                                texto, tiempo = transcribir_con_parametros(
                                    ruta, modelo, beam, vad, temp, cond, hw
                                )
                                error = wer(ref, texto)
                                errores.append(error)
                                tiempos.append(tiempo)
                                transcripciones.append((ref, texto))

                            if not errores:
                                continue

                            wer_avg = sum(errores) / len(errores)
                            cer_avg = sum(
                                cer(ref, texto)
                                for ref, texto in transcripciones
                            ) / len(transcripciones)
                            tiempo_avg = sum(tiempos) / len(tiempos)

                            resultados.append({
                                "modelo": modelo,
                                "beam_size": beam,
                                "vad_filter": vad,
                                "temperature": temp,
                                "condition_on_prev": cond,
                                "hotwords": hw[:30] if hw else "(none)",
                                "wer": round(wer_avg, 4),
                                "cer": round(cer_avg, 4),
                                "tiempo": round(tiempo_avg, 2),
                            })

                            pct = ejecutadas / total * 100
                            sys.stdout.write(
                                f"\r  [{ejecutadas}/{total}] "
                                f"{pct:5.1f}%  "
                                f"WER={wer_avg:.3f}  "
                                f"modelo={modelo} beam={beam} "
                                f"vad={vad} temp={temp}"
                            )
                            sys.stdout.flush()

    print("\n")
    return resultados


# ─── ANÁLISIS DE RESULTADOS ──────────────────────────────────────

def analizar_resultados(resultados):
    """Muestra tabla comparativa y mejor configuración."""
    print(f"\n{'='*80}")
    print("TOP 10 MEJORES CONFIGURACIONES (menor WER = mejor)")
    print(f"{'='*80}")

    top = sorted(resultados, key=lambda r: r["wer"])[:10]

    print(f"{'#':<4} {'Modelo':<8} {'Beam':<5} {'VAD':<5} "
          f"{'Temp':<5} {'Prev':<5} {'WER':<7} {'T(s)':<6} Hotwords")
    print("-" * 85)

    for i, r in enumerate(top, 1):
        print(
            f"{i:<4} {r['modelo']:<8} {r['beam_size']:<5} "
            f"{r['vad_filter']:<5} {r['temperature']:<5} "
            f"{r['condition_on_prev']:<5} {r['wer']:<7} "
            f"{r['tiempo']:<6} {r['hotwords']}"
        )

    # Mejor configuración
    mejor = min(resultados, key=lambda r: r["wer"])
    print(f"\n{'='*80}")
    print("★ MEJOR CONFIGURACIÓN")
    print(f"{'='*80}")
    print(f"  Modelo:    {mejor['modelo']}")
    print(f"  Beam size: {mejor['beam_size']}")
    print(f"  VAD:       {mejor['vad_filter']}")
    print(f"  Temp:      {mejor['temperature']}")
    print(f"  Prev text: {mejor['condition_on_prev']}")
    print(f"  Hotwords:  {mejor['hotwords']}")
    print(f"  WER:       {mejor['wer']}")
    print(f"  Tiempo:    {mejor['tiempo']}s")

    # Comparación por modelo
    print(f"\n{'='*80}")
    print("PROMEDIO WER POR MODELO")
    print(f"{'='*80}")
    for modelo in ["small", "medium"]:
        wer_modelo = [r["wer"] for r in resultados if r["modelo"] == modelo]
        if wer_modelo:
            print(f"  {modelo:<10} WER promedio: "
                  f"{sum(wer_modelo)/len(wer_modelo):.4f}")

    # Comparación por VAD
    print(f"\n{'='*80}")
    print("PROMEDIO WER POR VAD FILTER")
    print(f"{'='*80}")
    for vad in [False, True]:
        wer_vad = [r["wer"] for r in resultados if r["vad_filter"] == vad]
        if wer_vad:
            print(f"  VAD={str(vad):<6}  WER promedio: "
                  f"{sum(wer_vad)/len(wer_vad):.4f}")

    # Comparación por hotwords
    print(f"\n{'='*80}")
    print("PROMEDIO WER POR HOTWORDS")
    print(f"{'='*80}")
    for hw in ["", "MÚSICA VOLUMEN YOUTUBE ABRIR CERRAR",
               "música volumen youtube abrir cerrar poner pausar "
               "siguiente anterior"]:
        wer_hw = [r["wer"] for r in resultados if r["hotwords"] == hw[:30]]
        if wer_hw:
            label = hw[:30] if hw else "(none)"
            print(f"  {label:<35} WER: "
                  f"{sum(wer_hw)/len(wer_hw):.4f}")

    return mejor


# ─── MAIN ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Test de parámetros Faster-Whisper con WER"
    )
    parser.add_argument("--grabar", action="store_true",
                        help="Grabar audios nuevos")
    parser.add_argument("--dispositivos", action="store_true",
                        help="Grabar con dos micrófonos distintos")
    parser.add_argument("--dir", default=".",
                        help="Directorio con audios .wav pre-grabados")
    parser.add_argument("--guardar", default="resultados_whisper.json",
                        help="Archivo para guardar resultados")
    args = parser.parse_args()

    if args.grabar:
        if args.dispositivos:
            lotes = grabar_lote_dispositivos()
        else:
            lotes = {"default": grabar_lote()}
    else:
        # Cargar audios pre-grabados
        lotes = {}
        disponibles = {}
        for key in REFERENCIAS:
            for ext in ["", "_droidcam", "_real"]:
                ruta = os.path.join(args.dir, f"{key}{ext}.wav")
                if os.path.exists(ruta):
                    disponibles[key] = ruta
                    print(f"  Encontrado: {ruta}")

        if not disponibles:
            print("No hay audios grabados.")
            print("Usá: python prueba_whisper.py --grabar")
            print("  o: python prueba_whisper.py --grabar --dispositivos")
            sys.exit(1)

        lotes = {"grabados": disponibles}

    # Ejecutar batería de pruebas
    todos_resultados = []
    for nombre_lote, audios in lotes.items():
        print(f"\n>>> Probando lote: {nombre_lote}")
        resultados = ejecutar_bateria(audios, REFERENCIAS)
        todos_resultados.extend(resultados)

    # Analizar
    mejor = analizar_resultados(todos_resultados)

    # Guardar resultados
    with open(args.guardar, "w", encoding="utf-8") as f:
        json.dump({
            "mejor": mejor,
            "todos": todos_resultados
        }, f, indent=2, ensure_ascii=False)

    print(f"\nResultados guardados en: {args.guardar}")
