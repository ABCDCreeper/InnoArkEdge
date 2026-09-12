<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { NTabs, NTabPane } from 'naive-ui'
import { useEdgeStore } from '../stores/edge'
import WifiPanel from '../components/sensor/WifiPanel.vue'
import BluetoothPanel from '../components/sensor/BluetoothPanel.vue'
import SensorDashboard from '../components/sensor/SensorDashboard.vue'

const edge = useEdgeStore()
const tab = ref('sensors')

onMounted(() => {
  edge.connect()
})
</script>

<template>
  <n-tabs v-model:value="tab" type="line" animated>
    <n-tab-pane name="sensors" tab="传感器">
      <sensor-dashboard />
    </n-tab-pane>
    <n-tab-pane name="wifi" tab="WiFi">
      <wifi-panel />
    </n-tab-pane>
    <n-tab-pane name="bluetooth" tab="蓝牙">
      <bluetooth-panel />
    </n-tab-pane>
  </n-tabs>
</template>