<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  NCard, NButton, NList, NListItem, NTag, NSpace, NText, NModal,
  NInput, NForm, NFormItem, NRadio, NRadioGroup,
  useMessage,
} from 'naive-ui'
import { useEdgeStore } from '../../stores/edge'

const edge = useEdgeStore()
const message = useMessage()
const loading = ref(false)
const showConnectModal = ref(false)
const selectedSsid = ref('')
const password = ref('')
const mode = ref<'dhcp' | 'static'>('dhcp')
const ip = ref('')
const mask = ref('24')
const gateway = ref('')

async function scan() {
  loading.value = true
  edge.send('wifi_scan')
  setTimeout(() => { loading.value = false }, 2000)
}

async function connect() {
  edge.send('wifi_connect', {
    ssid: selectedSsid.value,
    password: password.value,
    mode: mode.value,
    ip: ip.value || undefined,
    mask: mask.value || undefined,
    gateway: gateway.value || undefined,
  })
  showConnectModal.value = false
  message.success(`正在连接 ${selectedSsid.value}...`)
}

function openConnect(ssid: string) {
  selectedSsid.value = ssid
  password.value = ''
  mode.value = 'dhcp'
  ip.value = ''
  gateway.value = ''
  showConnectModal.value = true
}

function disconnect() {
  edge.send('wifi_disconnect')
  message.info('正在断开 WiFi...')
}

onMounted(() => { edge.send('wifi_status') })
</script>

<template>
  <n-card title="WiFi 网络">
    <template #header-extra>
      <n-space>
        <n-tag v-if="edge.wifiStatus.connected" type="success" size="small">
          {{ edge.wifiStatus.ssid }}
        </n-tag>
        <n-button size="small" @click="scan" :loading="loading" :disabled="loading">
          扫描
        </n-button>
        <n-button v-if="edge.wifiStatus.connected" size="small" type="warning" @click="disconnect">
          断开
        </n-button>
      </n-space>
    </template>

    <n-list v-if="edge.wifiNetworks.length > 0">
      <n-list-item v-for="net in edge.wifiNetworks" :key="net.ssid">
        <n-space align="center" justify="space-between">
          <n-space align="center">
            <n-text strong>{{ net.ssid }}</n-text>
            <n-tag size="tiny" :bordered="false">{{ net.signal }}%</n-tag>
            <n-tag v-if="net.security && net.security !== ''" size="tiny" type="warning" :bordered="false">加密</n-tag>
            <n-tag v-else size="tiny" type="success" :bordered="false">开放</n-tag>
          </n-space>
          <n-button size="tiny" @click="openConnect(net.ssid)">连接</n-button>
        </n-space>
      </n-list-item>
    </n-list>
    <n-text v-else depth="3">点击扫描以发现附近网络</n-text>
  </n-card>

  <n-modal v-model:show="showConnectModal" title="连接 WiFi" preset="card" style="width: 420px;">
    <n-form>
      <n-form-item label="SSID"><n-input :value="selectedSsid" disabled /></n-form-item>
      <n-form-item label="密码"><n-input v-model:value="password" type="password" placeholder="输入 WiFi 密码" /></n-form-item>
      <n-form-item label="IP 模式">
        <n-radio-group v-model:value="mode">
          <n-radio value="dhcp">DHCP（自动）</n-radio>
          <n-radio value="static">手动</n-radio>
        </n-radio-group>
      </n-form-item>
      <template v-if="mode === 'static'">
        <n-form-item label="IP 地址"><n-input v-model:value="ip" placeholder="192.168.1.100" /></n-form-item>
        <n-form-item label="子网掩码"><n-input v-model:value="mask" placeholder="24" /></n-form-item>
        <n-form-item label="网关"><n-input v-model:value="gateway" placeholder="192.168.1.1" /></n-form-item>
      </template>
      <n-button type="primary" block @click="connect">连接</n-button>
    </n-form>
  </n-modal>
</template>