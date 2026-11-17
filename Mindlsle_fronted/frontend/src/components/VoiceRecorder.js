// 语音录音器：基于 recorder-core（wav 编码，浏览器麦克风 → wav blob）
// 使用方法：
//   const rec = new VoiceRecorder()
//   await rec.start()                 // 请求权限并开始录音（Async）
//   const blob = await rec.stop()     // 停止，返回 wav Blob（未录音返回 null）
import Recorder from 'recorder-core'
import 'recorder-core/recorder.wav.min.js'

class VoiceRecorder {
  constructor() {
    this.record = null
    this.recording = false
  }

  // 开始录音；返回 Promise。成功后 this.recording = true
  start() {
    return new Promise((resolve, reject) => {
      if (this.record) { resolve(); return }
      // 16kHz 单声道 wav，whisper 识别与文件体积都更友好
      this.record = Recorder({ type: 'wav', sampleRate: 16000, bitRate: 16 })
      this.record.open(() => {
        try {
          this.record.start()
          this.recording = true
          resolve()
        } catch (e) {
          reject(e && e.message ? e.message : '录音启动失败')
        }
      }, msg => {
        reject(msg)
      })
    })
  }

  // 停止录音，返回 wav Blob；未在录音返回 null
  stop() {
    return new Promise(resolve => {
      if (!this.record || !this.recording) { resolve(null); return }
      this.record.stop(blob => {
        try { this.record.close() } catch (_e) { /* ignore */ }
        this.record = null
        this.recording = false
        resolve(blob)
      }, () => {
        this.record = null
        this.recording = false
        resolve(null)
      })
    })
  }

  // 取消录音（不产出结果）
  cancel() {
    if (this.record && this.recording) {
      try { this.record.cancel && this.record.cancel() } catch (_e) { /* ignore */ }
      try { this.record.close() } catch (_e) { /* ignore */ }
    }
    this.record = null
    this.recording = false
  }
}

export default VoiceRecorder
