<script setup lang="ts">
import { onMounted, ref, onBeforeUnmount } from 'vue'
import {
  NCard, NGrid, NGridItem, NStatistic, NTag, NSpace, NLog,
} from 'naive-ui'
import { useEdgeStore } from '../../stores/edge'

const edge = useEdgeStore()
const eventLog = ref<string[]>([])
let logTimer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  edge.send('wifi_status')
  edge.send('bt_status')

  logTimer = setInterval(() => {
    const d = edge.sensorData
    const line = `[${new Date().toLocaleTimeString()}] HR:${d.hr} HRV:${d.hrv} 注意力:${(d.attention * 100).toFixed(0)}% 人脸:${d.faceCount}${d.rfidCard ? ` RFID:${d.rfidCard}` : ''}`
    eventLog.value.unshift(line)
    if (eventLog.value.length > 100) eventLog.value.pop()
  }, 5000)
})

onBeforeUnmount(() => {
  if (logTimer) clearInterval(logTimer)
})
</script>

<template>
  <n-grid :cols="4" :x-gap="12" :y-gap="12">
    <n-grid-item span="1">
      <n-card size="small">
        <n-statistic label="心率" :value="edge.sensorData.hr" suffix="bpm" />
      </n-card>
    </n-grid-item>
    <n-grid-item span="1">
      <n-card size="small">
        <n-statistic label="HRV" :value="edge.sensorData.hrv" suffix="ms" :precision="1" />
      </n-card>
    </n-grid-item>
    <n-grid-item span="1">
      <n-card size="small">
        <n-statistic label="注意力" :value="(edge.sensorData.attention * 100).toFixed(0)" suffix="%" />
      </n-card>
    </n-grid-item>
    <n-grid-item span="1">
      <n-card size="small">
        <n-statistic label="人脸数" :value="edge.sensorData.faceCount" />
      </n-card>
    </n-grid-item>
  </n-grid>

  <n-card title="传感器状态" style="margin-top: 12px;">
    <n-space>
      <n-tag :type="['connected', 'demo'].includes(edge.sensorStatus.ble) ? 'success' : 'default'">BLE: {{ edge.sensorStatus.ble }}</n-tag>
      <n-tag :type="['connected', 'demo'].includes(edge.sensorStatus.camera) ? 'success' : 'default'">Camera: {{ edge.sensorStatus.camera }}</n-tag>
      <n-tag :type="['connected', 'demo'].includes(edge.sensorStatus.rfid) ? 'success' : 'default'">RFID: {{ edge.sensorStatus.rfid }}</n-tag>
    </n-space>
  </n-card>

  <n-card title="事件日志" style="margin-top: 12px;">
    <n-log :rows="8" :log="eventLog.join('\n')" />
  </n-card>
</template>