<script setup lang="ts">
import { ref, watch } from 'vue'
import { NCard, NButton, NList, NListItem, NSpace, NText, NTag, useMessage } from 'naive-ui'
import { useEdgeStore } from '../../stores/edge'

const edge = useEdgeStore()
const message = useMessage()
const scanning = ref(false)

// 监听 btStatus 变化，显示配对/连接结果
watch(() => edge.btStatus.connected, (val) => {
  if (val) message.success('蓝牙已连接')
})
watch(() => edge.btStatus.paired, (val) => {
  if (val) message.success('蓝牙已配对')
})

async function scan() {
  scanning.value = true
  edge.send('bt_scan')
  setTimeout(() => { scanning.value = false }, 12000)
}

function pair(addr: string) {
  edge.send('bt_pair', { address: addr })
  message.info(`正在配对 ${addr}，请在手环上确认...`)
}

function connect(addr: string) {
  edge.send('bt_connect', { address: addr })
  message.info(`正在连接 ${addr}...`)
}

function disconnect() {
  edge.send('bt_disconnect')
  message.info('正在断开蓝牙...')
}
</script>

<template>
  <n-card title="蓝牙设备">
    <template #header-extra>
      <n-space>
        <n-tag v-if="edge.btStatus.connected" type="success" size="small">已连接</n-tag>
        <n-tag v-if="edge.btStatus.paired && !edge.btStatus.connected" type="warning" size="small">已配对</n-tag>
        <n-button size="small" @click="scan" :loading="scanning" :disabled="scanning">扫描</n-button>
        <n-button v-if="edge.btStatus.connected" size="small" type="warning" @click="disconnect">断开</n-button>
      </n-space>
    </template>

    <n-list v-if="edge.btDevices.length > 0">
      <n-list-item v-for="dev in edge.btDevices" :key="dev.address">
        <n-space align="center" justify="space-between">
          <div>
            <n-text strong>{{ dev.name || dev.address }}</n-text>
            <br>
            <n-text depth="3" style="font-size: 12px;">{{ dev.address }}</n-text>
          </div>
          <n-space>
            <n-button size="tiny" @click="pair(dev.address)">配对</n-button>
            <n-button size="tiny" type="primary" @click="connect(dev.address)">连接</n-button>
          </n-space>
        </n-space>
      </n-list-item>
    </n-list>
    <n-text v-else depth="3">点击扫描发现附近的蓝牙设备</n-text>
  </n-card>
</template>