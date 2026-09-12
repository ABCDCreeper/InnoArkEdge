import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

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

export const useEdgeStore = defineStore('edge', () => {
  const connected = ref(false)
  const sensorData = ref<SensorData>({ hr: 0, hrv: 0, attention: 0, faceCount: 0, rfidCard: null })
  const sensorStatus = ref({ ble: 'disconnected', camera: 'disconnected', rfid: 'disconnected' })

  const wifiNetworks = ref<WifiNetwork[]>([])
  const wifiStatus = ref({ connected: false, ssid: '', ip: '' })

  const btDevices = ref<BtDevice[]>([])
  const btStatus = ref({ scanning: false, paired: false, connected: false })

  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null

  function connect() {
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
    if (reconnectTimer) clearTimeout(reconnectTimer)
    ws?.close()
    ws = null
    connected.value = false
  }

  function handleMessage(msg: any) {
    switch (msg.event) {
      case 'sensor_data':
        sensorData.value = { ...sensorData.value, ...msg.payload }
        break
      case 'sensor_status':
        sensorStatus.value = msg.payload
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
    connected, sensorData, sensorStatus,
    wifiNetworks, wifiStatus,
    btDevices, btStatus,
    connect, disconnect, send,
  }
})