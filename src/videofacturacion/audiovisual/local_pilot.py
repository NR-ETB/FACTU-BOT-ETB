"""Piloto gratuito y local: MP4 de borrador, sin avatar ni APIs de generación."""

import argparse
import json
import os
import platform
import subprocess
import time
import wave
from array import array
from hashlib import sha256
from importlib.resources import files
from pathlib import Path
from uuid import uuid4

from videofacturacion.audiovisual.cards import render_card
from videofacturacion.config import Settings
from videofacturacion.ingestion.reader import parse_file
from videofacturacion.scripts.engine import ScriptEngine


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def run_process(arguments, *, cwd=None, timeout=120) -> str:
    result = subprocess.run(
        [str(arg) for arg in arguments],
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode:
        # No registrar argumentos ni texto de la fuente al fallar una herramienta.
        raise RuntimeError("La herramienta local no completó el procesamiento.")
    return result.stdout.decode("utf-8", errors="replace")


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as audio:
        if audio.getnchannels() != 1 or audio.getsampwidth() != 2:
            raise ValueError("El audio no tiene el formato PCM esperado.")
        duration = audio.getnframes() / audio.getframerate()
        samples = array("h", audio.readframes(audio.getnframes()))
        if duration <= 0 or not any(samples):
            raise ValueError("La narración está vacía o contiene solo silencio.")
        return duration


def validate_video(ffmpeg: str, path: Path) -> float:
    output = run_process(
        [
            ffmpeg,
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-progress",
            "pipe:1",
            "-nostats",
            "-i",
            path,
            "-map",
            "0:v:0",
            "-map",
            "0:a:0",
            "-f",
            "null",
            "-",
        ]
    )
    values = [
        int(line.split("=", 1)[1])
        for line in output.splitlines()
        if line.startswith("out_time_us=") and line.split("=", 1)[1].lstrip("-").isdigit()
    ]
    duration = max(values, default=0) / 1000000
    if duration <= 0 or path.stat().st_size < 1000:
        raise ValueError("El MP4 final no contiene audio y video válidos.")
    return duration


def render_invoice(invoice, target: Path, ffmpeg: str, voice: str) -> dict:
    started = time.perf_counter()
    target.mkdir(parents=True)
    engine = ScriptEngine()
    script = engine.generate(invoice)
    if engine.verify(invoice, script):
        raise ValueError("El guion no superó la verificación contra la fuente.")
    write_json(target / "guion-verificado.json", script)
    (target / "guion.txt").write_text(script["text"], encoding="utf-8")
    manifest = {
        "segments": [
            dict(segment, audio_file=f"audio-{index:03d}.wav")
            for index, segment in enumerate(script["segments"])
        ]
    }
    write_json(target / "synthesis.json", manifest)
    powershell = (
        Path(os.environ.get("SystemRoot", "C:/Windows"))
        / "System32/WindowsPowerShell/v1.0/powershell.exe"
    )
    voice_script = files("videofacturacion.audiovisual") / "speak_windows.ps1"
    voice_result = json.loads(
        run_process(
            [
                powershell,
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                voice_script,
                "-Manifest",
                (target / "synthesis.json").resolve(),
                "-OutputDirectory",
                target.resolve(),
                "-Voice",
                voice,
            ]
        )
    )
    timeline = []
    for index, segment in enumerate(script["segments"]):
        image_path = target / f"scene-{index:03d}.png"
        audio_path = target / f"audio-{index:03d}.wav"
        visual = render_card(invoice, segment, index, len(script["segments"]), image_path)
        speech_seconds = wav_duration(audio_path)
        duration = speech_seconds + 0.4
        clip = target / f"clip-{index:03d}.mp4"
        run_process(
            [
                ffmpeg,
                "-nostdin",
                "-hide_banner",
                "-loglevel",
                "error",
                "-n",
                "-loop",
                "1",
                "-framerate",
                "12",
                "-i",
                image_path,
                "-i",
                audio_path,
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-tune",
                "stillimage",
                "-crf",
                "23",
                "-pix_fmt",
                "yuv420p",
                "-r",
                "12",
                "-c:a",
                "aac",
                "-b:a",
                "96k",
                "-af",
                "apad=pad_dur=0.4",
                "-t",
                f"{duration:.6f}",
                "-movflags",
                "+faststart",
                clip,
            ]
        )
        timeline.append(
            {
                "index": index,
                "kind": segment["kind"],
                "line_id": segment.get("line_id"),
                "amount": segment.get("amount"),
                "text": segment["text"],
                "visual": visual,
                "speech_seconds": round(speech_seconds, 3),
                "scene_seconds": round(duration, 3),
                "image": image_path.name,
                "image_sha256": sha256(image_path.read_bytes()).hexdigest(),
            }
        )
    (target / "concat.txt").write_text(
        "\n".join(f"file 'clip-{index:03d}.mp4'" for index in range(len(timeline))),
        encoding="ascii",
    )
    video = target / "video.mp4"
    run_process(
        [
            ffmpeg,
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-n",
            "-f",
            "concat",
            "-safe",
            "1",
            "-i",
            "concat.txt",
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            "video.mp4",
        ],
        cwd=target,
    )
    duration = validate_video(ffmpeg, video)
    expected = sum(scene["speech_seconds"] for scene in timeline)
    if duration < expected:
        raise ValueError("La duración final no cubre la narración completa.")
    if engine.verify(invoice, script):
        raise ValueError("El guion cambió durante el procesamiento.")
    result = {
        "status": "BORRADOR",
        "audiovisual_review": "PENDIENTE",
        "text_source_validation": "CORRECTA",
        "voice": voice_result,
        "resolution": "1280x720",
        "frames_per_second": 12,
        "avatar": False,
        "total_cop": invoice.header["total_fuente"],
        "script_signature": script["signature"],
        "source_hash": script["source_hash"],
        "timeline": timeline,
        "video": str(video.resolve()),
        "video_sha256": sha256(video.read_bytes()).hexdigest(),
        "video_bytes": video.stat().st_size,
        "duration_seconds": round(duration, 3),
        "render_seconds": round(time.perf_counter() - started, 3),
        "generation_api_calls": 0,
        "generation_api_cost_usd": "0.00",
    }
    write_json(target / "resultado.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, default=Path("tests/fixtures/cinco_clientes.csv"))
    parser.add_argument(
        "--profile", choices=["conceptos_v1", "etb_prueba_v1"], default="conceptos_v1"
    )
    parser.add_argument("--confirm-synthetic", action="store_true", required=True)
    parser.add_argument("--output", type=Path, default=Path("var/piloto-gratuito"))
    parser.add_argument("--voice", default="Microsoft Helena Desktop")
    args = parser.parse_args()
    if platform.system() != "Windows":
        parser.error("Este piloto requiere las voces locales de Windows.")
    import imageio_ffmpeg

    started = time.perf_counter()
    data = args.file.read_bytes()
    parsed = parse_file(data, args.file.name, args.profile, Settings())
    if any(invoice.issues for invoice in parsed.invoices):
        parser.error("La base contiene facturas inválidas; revise los errores en la aplicación.")
    batch_dir = args.output.resolve() / str(uuid4())
    batch_dir.mkdir(parents=True)
    (batch_dir / ("fuente" + args.file.suffix.lower())).write_bytes(data)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    results = []
    for index, invoice in enumerate(parsed.invoices, start=1):
        result = render_invoice(invoice, batch_dir / f"factura-{index:03d}", ffmpeg, args.voice)
        results.append(
            {
                key: result[key]
                for key in (
                    "video",
                    "total_cop",
                    "duration_seconds",
                    "render_seconds",
                    "video_bytes",
                    "status",
                    "audiovisual_review",
                    "text_source_validation",
                    "voice",
                )
            }
        )
        print(
            json.dumps(
                {
                    "event": "local_draft_completed",
                    "index": index,
                    "count": len(parsed.invoices),
                    "render_seconds": result["render_seconds"],
                }
            ),
            flush=True,
        )
    summary = {
        "pilot": "local-gratuito",
        "source_sha256": parsed.file_hash,
        "invoices": len(results),
        "videos": results,
        "generation_api_calls": 0,
        "generation_api_cost_usd": "0.00",
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "environment": {"python": platform.python_version(), "system": platform.system()},
        "limitations": [
            "Voz es-ES, no es-CO",
            "Sin avatar",
            "Revisión audiovisual humana pendiente",
        ],
        "report": str((batch_dir / "piloto.json").resolve()),
    }
    write_json(batch_dir / "piloto.json", summary)
    write_json(args.output.resolve() / "ultimo-piloto.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
