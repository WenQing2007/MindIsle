"""
backend/voice.py
MindIsle（心屿）语音模块 —— 语音识别（STT）与语音合成（TTS）

方案 B（后端云端 API）：
  - 语音合成 TTS ：edge-tts（微软免费云端中文语音，音色自然）
                   合成生成的 mp3 保存在 audio/tts_cache/ 下，供前端直接播放。
  - 语音识别 STT ：faster-whisper（开源 Whisper，本地推理，中文识别效果好，
                   零 API 密钥，演示时不受网络/免费额度影响）。

可维护性设计：STT 与 TTS 分别封装为独立函数 voice_to_text() / text_to_speech()，
若后续想换成阿里/讯飞等云端免费额度，只需替换这两个函数内部实现，路由层无需改动。
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import tempfile
import time
from typing import Optional

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
TTS_CACHE_DIR = os.path.join(PROJECT_ROOT, "audio", "tts_cache")
os.makedirs(TTS_CACHE_DIR, exist_ok=True)

# faster-whisper 首次使用需从 HuggingFace 下载模型；国内网络访问 huggingface.co
# 常不稳定，这里默认走国内镜像，下载完成后模型会缓存在本地，后续离线可用。
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

# 中文音色：xiaoxiao 晓晓(女) | xiaoyi 晓伊(女) | yunjian 云健(男) | yunxi 云希(男)
DEFAULT_TTS_VOICE = "zh-CN-XiaoxiaoNeural"

# piper-tts 本地中文模型（HHF 镜像可下载，一次缓存离线可用）
_PIPER_MODEL = "zh_CN-huayan-medium"
_PIPER_REPO = "rhasspy/piper-voices"
_PIPER_SUBDIR = "zh/zh_CN/huayan/medium"

# edge-tts 云端失败后的“记忆窗口”：这段时间内直接走本地 piper，不重复等待云端
_EDGE_FAILED_UNTIL = 0.0
_EDGE_FALLBACK_SKIP_SECONDS = 300  # 5 分钟
# 允许播放的音频文件后缀
ALLOWED_AUDIO_EXT = {".mp3", ".wav", ".ogg", ".m4a"}

# 参考文档：
#   edge-tts 中文音色列表可通过 `edge-tts --list-voices` 查询。
#   faster-whisper 模型：base(~140MB)/small(~460MB)/medium 等，中文推荐 small。
_WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL", "small")


# ---------------------------------------------------------------------------
# 语音合成 TTS（edge-tts，免费云端）
# ---------------------------------------------------------------------------
async def _edge_tts_synthesize(text: str, voice: str, out_path: str) -> None:
    import edge_tts

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(out_path)


def _tts_cache_path(text: str, engine_key: str, local: bool = False) -> str:
    """基于文本内容生成稳定的缓存文件名（相同文本不重复合成）。"""
    digest = hashlib.md5(f"{engine_key}|{text}".encode("utf-8")).hexdigest()[:16]
    ext = ".wav" if local else ".mp3"
    return os.path.join(TTS_CACHE_DIR, f"mindisle_{digest}{ext}")


def _ensure_piper_model() -> str:
    """确保 piper 中文语音模型就绪，返回 .onnx 绝对路径。

    优先复用项目 data/piper 下的本地缓存；否则从 HF 镜像下载到 HF 缓存并返回
    实际落盘路径（onnx 与其 .onnx.json 相邻，PiperVoice.load 按 model+'.json'
    自动定位配置）。piper 合成为纯本地推理（onnxruntime），跨平台、无需系统
    语音/COM 会话。
    """
    root = os.path.join(PROJECT_ROOT, "data", "piper")
    sub = _PIPER_SUBDIR
    onnx = os.path.join(root, sub, f"{_PIPER_MODEL}.onnx")
    json_p = os.path.join(root, sub, f"{_PIPER_MODEL}.onnx.json")
    if os.path.exists(onnx) and os.path.exists(json_p):
        return onnx

    from huggingface_hub import hf_hub_download

    ep = os.environ.get("HF_ENDPOINT", "https://hf-mirror.com")
    hf_hub_download(
        _PIPER_REPO, f"{sub}/{_PIPER_MODEL}.onnx.json",
        repo_type="model", endpoint=ep,
    )
    return hf_hub_download(
        _PIPER_REPO, f"{sub}/{_PIPER_MODEL}.onnx",
        repo_type="model", endpoint=ep,
    )


def _tts_local(text: str, out_path: str) -> None:
    """本地 TTS：用 piper-tts（本地 ONNX 神经网络中文语音）在独立子进程中合成 wav。

    piper 是纯本地推理（onnxruntime），不受 Windows 会话/COM 影响；放到独立
    子进程执行，可避免 uvicorn 服务器线程/会话环境下音频数据丢失导致空文件。
    首次合成会自动下载中文模型（一次缓存，离线可用）。输出 wav。
    """
    import base64
    import subprocess
    import sys

    b64 = base64.b64encode(text.encode("utf-8")).decode("ascii")
    CHILD = r"""
import base64, os, sys, wave
sys.path.insert(0, r"__ROOT__")
from backend.voice import _ensure_piper_model
from piper import PiperVoice
model = _ensure_piper_model()
voice = PiperVoice.load(model)
with wave.open(sys.argv[2], "wb") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(voice.config.sample_rate)
    voice.synthesize_wav(base64.b64decode(sys.argv[1]).decode("utf-8"), wf)
"""
    code = CHILD.replace("__ROOT__", PROJECT_ROOT)
    proc = subprocess.run(
        [sys.executable, "-c", code, b64, out_path],
        capture_output=True, timeout=180, text=True,
    )
    size = os.path.getsize(out_path) if os.path.exists(out_path) else 0
    if proc.returncode != 0 or size < 200:
        raise RuntimeError(
            f"本地语音合成失败(size={size},ret={proc.returncode}): {proc.stderr[:300]!r}"
        )




def text_to_speech(
    text: str,
    voice: str = DEFAULT_TTS_VOICE,
    use_cache: bool = True,
    allow_fallback: bool = True,
) -> dict:
    """把文本合成为中文语音，返回 {url, filename, path}。

    双通道自动降级（满足《需求分析》2.6「语音服务故障自动降级」）：
      1. 首选 edge-tts（微软云端，音色自然，输出 mp3）；
      2. 若云端不可用，自动降级为本地 piper-tts（离线神经网络，输出 wav），
         跨平台、不依赖系统语音，后台/离线均可用。
    若云端失败，会记录短暂的“不可用”标记，避免后续每次调用都等待云端超时。

    :param text:          要朗读的文本
    :param voice:         edge-tts 中文音色名（默认晓晓）
    :param use_cache:     命中缓存时直接复用已合成音频
    :param allow_fallback: 是否允许在云端失败时降级到本地语音
    :return:              形如 {"url": "/api/voice/audio/mindisle_xxx.mp3|wav", ...}
    :raises RuntimeError: 两种通道都失败时抛出
    """
    text = (text or "").strip()
    if not text:
        raise ValueError("TTS 文本不能为空")

    # 1) 首选 edge-tts（云端）—— 仅在非“失败记忆窗口”内尝试
    global _EDGE_FAILED_UNTIL
    if time.time() >= _EDGE_FAILED_UNTIL:
        edge_path = _tts_cache_path(text, voice, local=False)
        if use_cache and os.path.exists(edge_path):
            return _build_result(edge_path)
        try:
            asyncio.run(_edge_tts_synthesize(text, voice, edge_path))
            return _build_result(edge_path)
        except Exception as exc:  # noqa: BLE001
            if os.path.exists(edge_path):  # 清理残缺文件
                try:
                    os.remove(edge_path)
                except OSError:
                    pass
            print(f"[MindIsle·voice] edge-tts 不可用，降级本地语音: {exc}")
            _EDGE_FAILED_UNTIL = time.time() + _EDGE_FALLBACK_SKIP_SECONDS
            if not allow_fallback:
                raise RuntimeError(f"语音合成失败（edge-tts）: {exc}") from exc

    # 2) 降级：本地 piper-tts（离线稳定）
    local_path = _tts_cache_path(text, "local", local=True)
    if use_cache and os.path.exists(local_path):
        return _build_result(local_path)
    try:
        _tts_local(text, local_path)
        return _build_result(local_path)
    except Exception as exc2:  # noqa: BLE001
        if os.path.exists(local_path):
            try:
                os.remove(local_path)
            except OSError:
                pass
        raise RuntimeError(f"语音合成失败（edge-tts 与本地均不可用）: {exc2}") from exc2


AUDIO_MIME = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
    ".m4a": "audio/mp4",
}


def audio_media_type(path: str) -> str:
    """根据文件后缀返回对应 MIME 类型（默认 mp3）。"""
    return AUDIO_MIME.get(os.path.splitext(path)[1].lower(), "audio/mpeg")


def _build_result(path: str) -> dict:
    filename = os.path.basename(path)
    return {
        "url": f"/api/voice/audio/{filename}",
        "filename": filename,
        "path": path,
    }


# ---------------------------------------------------------------------------
# 语音识别 STT（faster-whisper，本地开源，零密钥）
# ---------------------------------------------------------------------------
_whisper_model = None


def _get_whisper_model():
    """懒加载 Whisper 模型，重复调用复用（进程级缓存），避免每次识别重新加载。"""
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel

        # CPU 上用 int8 精度加速；有 GPU 时可自动选用 fp16
        _whisper_model = WhisperModel(_WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
    return _whisper_model


def voice_to_text(audio_path: str, language: str = "zh") -> str:
    """识别音频文件中的语音，返回文本。

    :param audio_path: 音频文件路径（wav/mp3/m4a/ogg 等）
    :param language:   语言（默认 zh 中文；None 表示自动检测）
    :return:           识别出的文本；识别为空时返回空串
    """
    if not audio_path or not os.path.exists(audio_path):
        raise ValueError("音频文件不存在")

    model = _get_whisper_model()
    segments, _info = model.transcribe(audio_path, language=language)
    text = "".join(seg.text for seg in segments).strip()
    return text


def transcribe_upload(upload_bytes: bytes, filename: str = "upload.wav") -> str:
    """把前端上传的音频字节落盘到临时文件后识别，识别完自动清理临时文件。

    :param upload_bytes: 上传的音频原始字节
    :param filename:     上传文件名（用于决定后缀，whisper 按内容自动解析，后缀影响不大）
    :return:             识别文本
    """
    suffix = os.path.splitext(filename or "")[1] or ".wav"
    fd, tmp = tempfile.mkstemp(prefix="mindisle_stt_", suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(upload_bytes)
        return voice_to_text(tmp)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


def is_audio_filename(filename: str) -> bool:
    """校验文件名后缀是否为允许的音频类型（防路径穿越 / 非法访问）。"""
    return os.path.splitext(os.path.basename(filename or ""))[1].lower() in ALLOWED_AUDIO_EXT


if __name__ == "__main__":
    # 自测：TTS → STT 闭环（需联网合成；识别为本地）
    text = "你好，我是心屿，很高兴认识你。今天过得怎么样呢？"
    print("== 1) 语音合成 TTS ==")
    t0 = time.time()
    res = text_to_speech(text)
    print(f"  生成: {res['url']}  ({time.time()-t0:.1f}s, {os.path.getsize(res['path'])} bytes)")
    print("== 2) 语音识别 STT ==")
    t0 = time.time()
    heard = voice_to_text(res["path"])
    print(f"  识别: {heard!r}  ({time.time()-t0:.1f}s)")
    print("== 3) 结果对比 ==")
    print(f"  原文 : {text!r}")
    print(f"  识别 : {heard!r}")
