<script setup lang="ts">
import { computed } from 'vue'
import { NIcon, NPopover, NSpace, NText, NTag } from 'naive-ui'
import { PulseOutline, EyeOutline, CardOutline } from '@vicons/ionicons5'
import { useEdgeStore } from '../../stores/edge'

const edge = useEdgeStore()

const bleStatus = computed(() => ({
  color: edge.sensorStatus.ble === 'connected' ? '#18a058' : '#d03050',
  icon: PulseOutline,
  label: `${edge.sensorData.hr} bpm`,
}))

const attentionLevel = computed(() => {
  const a = edge.sensorData.attention
  if (a > 0.7) return { color: '#18a058', text: '专注' }
  if (a > 0.3) return { color: '#f0a020', text: '一般' }
  return { color: '#d03050', text: '分散' }
})
</script>

<template>
  <n-space align="center" size="small">
    <n-popover trigger="hover">
      <template #trigger>
        <n-tag :bordered="false" :color="{ text: bleStatus.color, border: 'transparent' }" size="small" style="cursor:pointer;">
          <template #icon>
            <n-icon :color="bleStatus.color"><component :is="bleStatus.icon" /></n-icon>
          </template>
          {{ bleStatus.label }}
        </n-tag>
      </template>
      <n-text>BLE: {{ edge.sensorStatus.ble }} | HRV: {{ edge.sensorData.hrv }}</n-text>
    </n-popover>

    <n-popover trigger="hover">
      <template #trigger>
        <n-tag :bordered="false" :color="{ text: attentionLevel.color, border: 'transparent' }" size="small" style="cursor:pointer;">
          <template #icon>
            <n-icon :color="attentionLevel.color"><eye-outline /></n-icon>
          </template>
          {{ attentionLevel.text }}
        </n-tag>
      </template>
      <n-text>注意力: {{ (edge.sensorData.attention * 100).toFixed(0) }}% | 人脸: {{ edge.sensorData.faceCount }}</n-text>
    </n-popover>

    <n-popover trigger="hover">
      <template #trigger>
        <n-tag :bordered="false" :color="{ text: edge.sensorData.rfidCard ? '#18a058' : '#666', border: 'transparent' }" size="small" style="cursor:pointer;">
          <template #icon>
            <n-icon><card-outline /></n-icon>
          </template>
          {{ edge.sensorData.rfidCard ? '卡片' : '待卡' }}
        </n-tag>
      </template>
      <n-text>{{ edge.sensorData.rfidCard ? `RFID: ${edge.sensorData.rfidCard}` : '等待刷卡...' }}</n-text>
    </n-popover>
  </n-space>
</template>