import request from './request'

// ===== 语音识别 STT：把音频上传后端识别成文字 =====
export function stt(audioBlob, filename = 'record.wav') {
  const form = new FormData()
  form.append('file', audioBlob, filename)
  return request({
    url: '/api/voice/stt',
    method: 'post',
    data: form
  })
}

// ===== 语音合成 TTS：把文本转语音，返回音频 URL =====
export function tts(text, voice) {
  return request({
    url: '/api/voice/tts',
    method: 'post',
    data: { text, voice }
  })
}
