import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface SensorData {
  hr: number
  hrv: number
  attention: number
  faceCount: number
  rfidCard: string | null
}

export interface WifiNetwork {
  ssid: string
  signal: number
  security: string
}

export interface BtDevice {
  address: string
  name: string
}

let demoInterval: ReturnType<typeof setInterval> | null = null

export const useEdgeStore = defineStore('edge', () => {
  const connected = ref(false)
  const useDemo = ref(true)

  // 初始化为演示数据，避免页面显示全 0
  const sensorData = ref<SensorData>({ hr: 72, hrv: 38.5, attention: 0.65, faceCount: 1, rfidCard: null })
  const sensorStatus = ref({ ble: 'demo', camera: 'demo', rfid: 'demo' })

  const wifiNetworks = ref<WifiNetwork[]>([])
  const wifiStatus = ref({ connected: false, ssid: '', ip: '' })

  const btDevices = ref<BtDevice[]>([])
  const btStatus = ref({ scanning: false, paired: false, connected: false })

  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null

  function startDemo() {
    stopDemo()
    demoInterval = setInterval(() => {
      sensorData.value = {
        hr: Math.round(65 + Math.random() * 25),
        hrv: Math.round((30 + Math.random() * 25) * 10) / 10,
        attention: Math.round((0.3 + Math.random() * 0.5) * 100) / 100,
        faceCount: Math.round(Math.random() * 3),
        rfidCard: Math.random() > 0.85 ? `卡 ${Math.floor(Math.random() * 1000)}` : null,
      }
      sensorStatus.value = {
        ble: Math.random() > 0.1 ? 'demo' : 'disconnected',
        camera: Math.random() > 0.15 ? 'demo' : 'disconnected',
        rfid: Math.random() > 0.05 ? 'demo' : 'disconnected',
      }
    }, 5000)
  }

  function stopDemo() {
    if (demoInterval) {
      clearInterval(demoInterval)
      demoInterval = null
    }
  }

  function connect() {
    startDemo()
    if (ws && ws.readyState === WebSocket.OPEN) return
    ws = new WebSocket(`ws://${location.host}/ws`)

    ws.onopen = () => { connected.value = true }
    ws.onclose = () => {
      connected.value = false
      reconnectTimer = setTimeout(connect, 3000)
    }
    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        handleMessage(msg)
      } catch { /* ignore parse errors */ }
    }
  }

  function disconnect() {
    stopDemo()
    if (reconnectTimer) clearTimeout(reconnectTimer)
    ws?.close()
    ws = null
    connected.value = false
  }

  function handleMessage(msg: any) {
    switch (msg.event) {
      case 'sensor_data':
        if (!useDemo.value) sensorData.value = { ...sensorData.value, ...msg.payload }
        break
      case 'sensor_status':
        if (!useDemo.value) sensorStatus.value = msg.payload
        break
      case 'wifi_networks':
        wifiNetworks.value = msg.payload
        break
      case 'wifi_status':
      case 'wifi_result':
        wifiStatus.value = { ...wifiStatus.value, ...msg.payload }
        break
      case 'bt_devices':
        btDevices.value = msg.payload
        break
      case 'bt_status':
      case 'bt_result':
        btStatus.value = { ...btStatus.value, ...msg.payload }
        break
    }
  }

  function send(cmd: string, payload?: Record<string, any>) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ cmd, payload }))
    }
  }

  return {
    connected, useDemo, sensorData, sensorStatus,
    wifiNetworks, wifiStatus,
    btDevices, btStatus,
    connect, disconnect, send,
  }
})