Vue.component('spec-row', {
    props: ['label', 'value'],
    template: `<div class="flex flex-col gap-0.5 border-b border-slate-100 py-2 last:border-0 sm:flex-row sm:justify-between sm:gap-4">
      <span class="shrink-0 font-medium text-slate-500" v-text="label"></span>
      <span class="font-semibold text-slate-800 sm:text-right sm:max-w-[65%] break-words" v-text="value"></span>
    </div>`,
})

Vue.component('user-row', {
    props: ['user'],
    data() {
        return { showRole: false, last_activity: '--' }
    },
    created() {
        const d = (Date.now() - parseFloat(this.user.last_activity)) / 1000
        if (!this.user.last_activity) this.last_activity = '--'
        else if (d < 60) this.last_activity = Math.round(d) + 's ago'
        else if (d < 3600) this.last_activity = Math.round(d / 60) + 'm ago'
        else if (d < 86400) this.last_activity = Math.round(d / 3600) + 'h ago'
        else this.last_activity = Math.round(d / 86400) + 'd ago'
    },
    template: `
    <div class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm mb-3 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:gap-4">
      <div class="flex items-center gap-3 min-w-0 sm:flex-1">
        <img :src="user.image || '/static/img/logo.png'" class="h-10 w-10 shrink-0 rounded-full border object-cover" alt="">
        <div class="min-w-0 flex-1">
          <p class="font-semibold truncate" v-text="user.username"></p>
          <p v-if="user.email" class="text-xs text-slate-500 truncate" v-text="user.email"></p>
          <p class="text-xs text-slate-500 break-words" v-text="user.role + ' · ' + last_activity + (user.group_name ? ' · ' + user.group_name : '')"></p>
        </div>
      </div>
      <div class="flex flex-wrap items-center gap-2 sm:justify-end">
        <span class="text-xs px-2 py-0.5 rounded-full" :class="user.is_accept ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'"
              v-text="user.is_accept ? 'accepted' : 'pending'"></span>
        <div class="relative">
          <button @click="showRole=!showRole" class="px-3 py-1.5 rounded-lg bg-indigo-600 text-white text-xs" v-text="user.role"></button>
          <div v-if="showRole" class="absolute z-10 mt-1 right-0 bg-white border rounded-lg shadow py-1 min-w-[8rem]">
            <button class="block w-full text-left px-3 py-1 text-sm hover:bg-slate-50" @click="$emit('role','admin'); showRole=false">admin</button>
            <button class="block w-full text-left px-3 py-1 text-sm hover:bg-slate-50" @click="$emit('role','normal_user'); showRole=false">normal_user</button>
          </div>
        </div>
        <button v-if="!user.is_accept" @click="$emit('accept')" class="px-3 py-1.5 rounded-lg bg-emerald-600 text-white text-xs">Accept</button>
        <button @click="$emit('delete')" class="px-3 py-1.5 rounded-lg border text-slate-600 text-xs">Delete</button>
      </div>
    </div>`,
})

Vue.component('workspace-card', {
    props: ['ws', 'showOwner', 'disabled'],
    computed: {
        k8sDisplay() {
            if (this.disabled) return 'Loading…'
            return (this.ws.k8s_status && this.ws.k8s_status.display) || this.ws.state
        },
        stateClass() {
            if (this.disabled) return 'bg-slate-100 text-slate-500'
            const d = this.k8sDisplay.toLowerCase()
            if (d === 'running') return 'bg-emerald-100 text-emerald-700'
            if (d === 'terminating') return 'bg-rose-100 text-rose-700'
            if (d === 'scaled down' || d === 'not deployed' || this.ws.state === 'offline') {
                return 'bg-slate-100 text-slate-600'
            }
            return 'bg-amber-100 text-amber-700'
        },
        canStart() {
            return this.ws.state === 'offline'
        },
        canStop() {
            return ['running', 'pending_start', 'pending_stop'].includes(this.ws.state)
        },
        canOpen() {
            return this.ws.state === 'running' && this.k8sDisplay.toLowerCase() === 'running'
        },
        canDelete() {
            return this.ws.state === 'offline'
        },
        serverUrl() {
            return window.location.protocol + '//' + this.ws.hostname
        },
    },
    methods: {
        workspaceDriveSummary(ws) {
            const mounts = ws.drive_mounts || []
            if (mounts.length) {
                return 'Drives: ' + mounts.map((m) => {
                    let s = (m.drive_name || '?') + ' → ' + m.mount_path
                    if (m.sub_path) s += ' (subPath)'
                    return s
                }).join(', ')
            }
            if (ws.drive_name) {
                return 'Drive: ' + ws.drive_name + ' → ' + (ws.mount_path || '/home/coder')
            }
            return 'Drives: none (ephemeral)'
        },
        onCardClick() {
            if (this.disabled) return
            this.$emit('detail', this.ws)
        },
    },
    template: `
    <div class="dohub-workspace-card rounded-2xl border border-slate-200 bg-white p-4 shadow-sm flex flex-col gap-3 transition"
         :class="disabled ? 'opacity-60 pointer-events-none select-none' : 'cursor-pointer hover:border-blue-300 hover:shadow-md'"
         @click="onCardClick">
      <div class="flex justify-between items-start gap-2 min-w-0">
        <div class="min-w-0 flex-1 overflow-hidden">
          <h3 class="font-bold text-slate-900 truncate" v-text="ws.name"></h3>
          <p v-if="showOwner" class="text-xs text-slate-500 truncate mt-0.5" v-text="'@' + ws.owner"></p>
        </div>
        <span class="shrink-0 rounded-full px-2 py-0.5 text-xs font-bold max-w-[40%] text-right leading-tight" :class="stateClass" v-text="k8sDisplay"></span>
      </div>
      <div class="text-xs text-slate-600 space-y-0.5 pointer-events-none min-w-0">
        <p class="dohub-break-long" v-text="ws.cpu + ' vCPU · ' + ws.ram"></p>
        <p class="dohub-break-long" v-text="workspaceDriveSummary(ws)"></p>
        <p class="dohub-break-long" v-text="'GPU: ' + (ws.gpu || 'none')"></p>
        <p class="dohub-break-long font-mono" v-text="ws.docker_repository + ':' + ws.docker_tag"></p>
      </div>
      <div class="dohub-card-actions mt-auto" @click.stop>
        <button v-if="canStart" @click="$emit('start', ws)"
                class="dohub-card-action-main dohub-card-action-main--wide rounded-lg bg-blue-600 text-white">Start</button>
        <button v-if="canStop" @click="$emit('stop', ws)"
                class="dohub-card-action-main rounded-lg bg-rose-600 text-white">Stop</button>
        <button v-if="canOpen" @click="$emit('open', ws)"
                class="dohub-card-action-main rounded-lg border border-blue-600 text-blue-600 bg-white">Open</button>
        <button @click="$emit('export', ws)"
                class="dohub-card-action-icon rounded-lg border bg-white text-slate-700" title="Export"><i class="fa fa-download"></i></button>
        <button v-if="canDelete" @click="$emit('delete', ws)"
                class="dohub-card-action-icon rounded-lg border border-rose-200 bg-white text-rose-600" title="Delete"><i class="fa fa-trash"></i></button>
      </div>
    </div>`,
})

const ENV_TEMPLATE_RE = /<<([a-z]+)(?::(\d+))?>>/gi

function randomToken(len) {
    const chars = 'abcdefghijklmnopqrstuvwxyz0123456789'
    let s = ''
    for (let i = 0; i < len; i++) s += chars[Math.floor(Math.random() * chars.length)]
    return s
}

function randomDigits(len) {
    let s = ''
    for (let i = 0; i < len; i++) s += String(Math.floor(Math.random() * 10))
    return s
}

function expandEnvTemplateString(value, username) {
    if (value == null) return ''
    return String(value).replace(ENV_TEMPLATE_RE, (_, kind, arg) => {
        const n = arg ? parseInt(arg, 10) : 0
        switch ((kind || '').toLowerCase()) {
            case 'rdstring':
                return randomToken(n > 0 ? n : 16)
            case 'rdnum':
                return randomDigits(n > 0 ? n : 6)
            case 'tmsp':
                return new Date().toISOString().replace(/\.\d{3}Z$/, 'Z')
            case 'username':
                return username || ''
            default:
                return `<<${kind}>>`
        }
    })
}

function resolveTemplateEnv(envDefaults, username) {
    const out = {}
    if (!envDefaults) return out
    const defaults = { ...envDefaults }
    if (defaults.PASSWORD_PREFIX && !defaults.PASSWORD) {
        defaults.PASSWORD = `${defaults.PASSWORD_PREFIX}<<rdstring:6>>`
        delete defaults.PASSWORD_PREFIX
    }
    Object.keys(defaults).forEach((k) => {
        if (k === 'PASSWORD_PREFIX') return
        out[k] = expandEnvTemplateString(defaults[k], username)
    })
    return out
}

function defaultDriveMount() {
    return { drive_id: '', mount_path: '/home/coder' }
}

function parseCpuValue(value) {
    const n = Number(value)
    return Number.isFinite(n) && n > 0 ? n : NaN
}

function cpuListIncludes(list, cpu) {
    const n = parseCpuValue(cpu)
    if (Number.isNaN(n)) return false
    return (list || []).some((c) => parseCpuValue(c) === n)
}

function formatPlanTemplateDriveMountsText(mounts) {
    if (!mounts || !mounts.length) return ''
    return mounts
        .map((m) => (typeof m === 'string' ? m : (m.mount_path || m.path || '')))
        .filter(Boolean)
        .join(', ')
}

function parsePlanTemplateDriveMountsText(text) {
    const raw = (text || '').trim()
    if (!raw) return { drive_mounts: [] }
    if (raw.startsWith('[')) {
        try {
            const arr = JSON.parse(raw)
            if (!Array.isArray(arr)) return { error: 'drive_mounts must be a JSON array' }
            const drive_mounts = arr
                .map((item) => {
                    if (typeof item === 'string') return { mount_path: item.trim() }
                    return { mount_path: (item.mount_path || item.path || '').trim() }
                })
                .filter((m) => m.mount_path)
            return { drive_mounts }
        } catch {
            return { error: 'drive_mounts must be valid JSON' }
        }
    }
    const drive_mounts = raw
        .split(/[,;]/)
        .map((p) => p.trim())
        .filter(Boolean)
        .map((mount_path) => ({ mount_path }))
    return { drive_mounts }
}

function defaultPlanTemplateForm() {
    return {
        name: '',
        image: 'logo.png',
        cpu: 2,
        ram: '4G',
        gpu: 'none',
        docker_repository: 'codercom/code-server',
        docker_tag: '4.89.0-ubuntu',
        ports_text: '8080',
        command_text: '',
        drive_mounts_text: '',
        env_defaults_text: '{"SECRET_KEY":"secret-<<rdstring:64>>","PWA_APPNAME":"Workspace"}',
        sort_order: 0,
        is_active: true,
    }
}

function planTemplatePayloadFromForm(form) {
    let env_defaults = {}
    try {
        env_defaults = JSON.parse(form.env_defaults_text || '{}')
    } catch {
        return { error: 'env_defaults must be valid JSON' }
    }
    const mountsParsed = parsePlanTemplateDriveMountsText(form.drive_mounts_text)
    if (mountsParsed.error) return { error: mountsParsed.error }
    return {
        payload: {
            name: form.name,
            image: form.image,
            cpu: form.cpu,
            ram: form.ram,
            gpu: form.gpu,
            docker_repository: (form.docker_repository || '').trim(),
            docker_tag: (form.docker_tag || '').trim(),
            exposed_ports: parsePorts(form.ports_text),
            container_command: parseCommand(form.command_text),
            env_defaults,
            drive_mounts: mountsParsed.drive_mounts,
            sort_order: form.sort_order,
            is_active: form.is_active,
        },
    }
}

function defaultForm() {
    return {
        name: 'My workspace',
        cpu: 2,
        ram: '4G',
        drive_mounts: [],
        gpu: 'none',
        node_hostname: 'auto',
        docker_image_id: '',
        docker_repository: 'codercom/code-server',
        docker_tag: '4.89.0-ubuntu',
        ports_text: '8080',
        command_text: '',
        env_vars: {},
        privileged: false,
    }
}

function parsePorts(text) {
    if (!text || !String(text).trim()) return [8080]
    return String(text).split(/[,\s]+/).map((p) => parseInt(p, 10)).filter((n) => !isNaN(n) && n > 0)
}

function parseCommand(text) {
    if (!text || !String(text).trim()) return []
    const out = []
    let cur = ''
    let quote = null
    const s = String(text).trim()
    for (let i = 0; i < s.length; i++) {
        const ch = s[i]
        if (quote) {
            if (ch === quote) {
                quote = null
            } else if (ch === '\\' && quote === '"' && i + 1 < s.length) {
                cur += s[++i]
            } else {
                cur += ch
            }
        } else if (ch === '"' || ch === "'") {
            quote = ch
        } else if (/\s/.test(ch)) {
            if (cur) {
                out.push(cur)
                cur = ''
            }
        } else {
            cur += ch
        }
    }
    if (cur) out.push(cur)
    return out
}

function formatCommand(parts) {
    if (!parts || !parts.length) return ''
    return parts.map((part) => {
        const s = String(part)
        if (!s) return ''
        if (/[\s'"]/.test(s)) return "'" + s.replace(/'/g, "'\\''") + "'"
        return s
    }).filter(Boolean).join(' ')
}

function resolveEnvDefaults(envDefaults) {
    const out = {}
    if (!envDefaults) return out
    Object.keys(envDefaults).forEach((k) => {
        const v = envDefaults[k]
        out[k] = typeof v === 'function' ? v() : String(v)
    })
    return out
}

function formPayload(form) {
    const mounts = (form.drive_mounts || []).filter((m) => m.drive_id)
    const primary = mounts[0]
    return {
        name: form.name,
        cpu: form.cpu,
        ram: form.ram,
        node_hostname: form.node_hostname === 'auto' ? '' : (form.node_hostname || ''),
        drive_id: primary ? primary.drive_id : null,
        mount_path: primary ? (primary.mount_path || '/home/coder') : '/home/coder',
        drive_mounts: mounts.map((m) => ({
            drive_id: m.drive_id,
            mount_path: m.mount_path || '/home/coder',
        })),
        gpu: form.gpu === 'none' ? '' : form.gpu,
        docker_repository: form.docker_repository,
        docker_tag: form.docker_tag,
        env_vars: { ...form.env_vars },
        exposed_ports: parsePorts(form.ports_text),
        container_command: parseCommand(form.command_text),
        privileged: !!form.privileged,
    }
}

const LEGACY_GPU_ALIASES = {
    'mig-2g.10gb': '1:10240',
    'mig-3g.20gb': '1:20480',
    'gpu': '1:40960',
    'gpu:2': '2:20480',
}

function normalizeGpuValue(gpu) {
    if (!gpu || gpu === 'none') return 'none'
    return LEGACY_GPU_ALIASES[gpu] || gpu
}

function formatBulkSummary(data, total) {
    let summary = `Done: ${data.ok} ok, ${data.failed} failed (${total} total)`
    const failed = (data.results || []).filter((r) => !r.ok)
    if (failed.length) {
        summary += '\n' + failed.map((r) => `#${r.index + 1}: ${r.error || 'failed'}`).join('\n')
    }
    return summary
}

function normalizeBulkItem(raw) {
    const item = { ...raw }
    if (item.gpu === 'none') item.gpu = ''
    if (item.user_drive_id) item.drive_id = item.user_drive_id
    if (item.drive && !item.drive_id && !item.drive_name && !item.drive_slug) {
        if (/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(String(item.drive))) {
            item.drive_id = item.drive
        } else {
            item.drive_name = String(item.drive)
        }
    }
    if (item.drive_mounts && Array.isArray(item.drive_mounts)) {
        item.drive_mounts = item.drive_mounts.map((m) => {
            const ref = m.drive_id || m.user_drive_id || m.claim_name || m.drive_slug || m.drive_name || m.drive || ''
            return {
                drive_id: ref,
                mount_path: m.mount_path || '/home/coder',
            }
        }).filter((m) => m.drive_id)
        if (item.drive_mounts.length) {
            item.drive_id = item.drive_mounts[0].drive_id
            item.mount_path = item.drive_mounts[0].mount_path
        }
    }
    if (!item.mount_path) item.mount_path = '/home/coder'
    if (typeof item.ports === 'string') item.exposed_ports = parsePorts(item.ports)
    else if (item.ports_text) item.exposed_ports = parsePorts(item.ports_text)
    else if (!item.exposed_ports) item.exposed_ports = [8080]
    if (typeof item.command === 'string') item.container_command = parseCommand(item.command)
    else if (item.command_text) item.container_command = parseCommand(item.command_text)
    if (!item.docker_repository && item.image) item.docker_repository = item.image
    return item
}

function parseCsvRows(text, rowMapper) {
    const lines = text.trim().split(/\r?\n/).filter((l) => l.trim())
    if (lines.length < 2) throw new Error('CSV needs header + at least one row')
    const headers = lines[0].split(',').map((h) => h.trim())
    const items = []
    for (let i = 1; i < lines.length; i++) {
        const cols = lines[i].split(',').map((c) => c.trim().replace(/^"|"$/g, ''))
        const row = {}
        headers.forEach((h, j) => { row[h] = cols[j] ?? '' })
        items.push(rowMapper(row))
    }
    return items
}

function parseCsvBulk(text) {
    return parseCsvRows(text, (row) => {
        const env_vars = {}
        const item = {}
        Object.keys(row).forEach((h) => {
            const val = row[h]
            if (h.startsWith('env_')) env_vars[h.slice(4)] = val
            else if (h === 'env_json') {
                try { Object.assign(env_vars, JSON.parse(val || '{}')) } catch (_) { /* skip */ }
            } else item[h] = val
        })
        if (Object.keys(env_vars).length) item.env_vars = env_vars
        if (item.cpu != null && item.cpu !== '') {
            const cpu = parseCpuValue(item.cpu)
            if (!Number.isNaN(cpu)) item.cpu = cpu
        }
        return normalizeBulkItem(item)
    })
}

function normalizeDriveBulkItem(raw) {
    const item = { ...raw }
    if (!item.size) item.size = '20Gi'
    return item
}

function parseDriveCsvBulk(text) {
    return parseCsvRows(text, (row) => normalizeDriveBulkItem(row))
}

function downloadJson(obj, filename) {
    const blob = new Blob([JSON.stringify(obj, null, 2)], { type: 'application/json' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = filename
    a.click()
    URL.revokeObjectURL(a.href)
}

const DOCKER_IMAGE_BULK_PLACEHOLDER_JSON = '[{"label":"Code Server","repository":"codercom/code-server","default_tag":"4.89.0-ubuntu","tags":["4.89.0-ubuntu","latest"],"is_active":true,"sort_order":0}]'
const DOCKER_IMAGE_BULK_PLACEHOLDER_CSV = 'label,repository,default_tag,tags_text,is_active,sort_order\nCode Server,codercom/code-server,4.89.0-ubuntu,4.89.0-ubuntu;latest,true,0'
const PLAN_TEMPLATE_BULK_PLACEHOLDER_JSON = '[{"name":"Code Server","cpu":2,"ram":"4G","gpu":"none","image":"logo.png","docker_repository":"codercom/code-server","docker_tag":"4.89.0-ubuntu","exposed_ports":[8080],"container_command":[],"env_defaults":{},"drive_mounts":[{"mount_path":"/home/coder"}],"is_active":true,"sort_order":0}]'
const PLAN_TEMPLATE_BULK_PLACEHOLDER_CSV = 'name,cpu,ram,gpu,image,docker_repository,docker_tag,exposed_ports,command_text,drive_mounts_text,env_defaults,is_active,sort_order\nCode Server,2,4G,none,logo.png,codercom/code-server,4.89.0-ubuntu,8080,,/home/coder,{},true,0'

const appVue = new Vue({
    el: '#root',
    mounted() {
        const splash = document.getElementById('dohub-boot-splash')
        if (splash) {
            splash.style.opacity = '0'
            splash.style.transition = 'opacity 180ms ease'
            window.setTimeout(() => splash.remove(), 220)
        }
    },
    data: {
        fullEquipmentList: { cpu: [], ram: [], gpu: [], drive_sizes: [] },
        equipmentList: { cpu: [], ram: [], gpu: [] },
        driveSizeOptions: [],
        adminCatalogOptions: [],
        adminPlanTemplates: [],
        showPlanTemplateModal: false,
        editingPlanTemplate: null,
        planTemplateForm: defaultPlanTemplateForm(),
        planTemplateFormLoading: false,
        newCatalogOption: { category: 'cpu', value: '', vram_g: 0 },
        newPlanTemplate: defaultPlanTemplateForm(),
        myDrives: [],
        myDrivesAll: [],
        myDriveFilter: '',
        myDrivePagination: { page: 1, pages: 1, total: 0, per_page: 12 },
        adminDrives: [],
        adminDrivePagination: { page: 1, pages: 1, total: 0, per_page: 12 },
        adminDriveFilter: '',
        adminDriveNameFilter: '',
        adminDriveGroupFilter: '',
        newDrive: { name: 'My drive', size: '20Gi' },
        showCreateDriveModal: false,
        showBulkCreateDriveModal: false,
        driveCreateLoading: false,
        deleteModalDrive: null,
        deleteModalDriveIsAdmin: false,
        deleteDriveConfirmInput: '',
        deleteDriveInProgress: false,
        planTemplates: [],
        form: defaultForm(),
        envKey: '',
        envValue: '',
        bulkMode: 'json',
        bulkText: '',
        bulkFileName: '',
        bulkAutoStart: true,
        bulkLoading: false,
        bulkSummary: '',
        driveBulkMode: 'json',
        driveBulkText: '',
        driveBulkFileName: '',
        driveBulkLoading: false,
        driveBulkSummary: '',
        dockerImages: [],
        myWorkspaces: [],
        myServerFilter: '',
        myServerPagination: { page: 1, pages: 1, total: 0, per_page: 12 },
        adminWorkspaces: [],
        adminPagination: { page: 1, pages: 1, total: 0, per_page: 12 },
        adminServerFilter: '',
        adminServerNameFilter: '',
        adminServerGroupFilter: '',
        adminDockerImages: [],
        adminImageNameFilter: '',
        adminImageCreatorFilter: '',
        adminImageStatusFilter: 'all',
        myDockerImages: [],
        myImageFilter: '',
        myImagePagination: { page: 1, pages: 1, total: 0, per_page: 12 },
        adminImagePagination: { page: 1, pages: 1, total: 0, per_page: 12 },
        newImage: { label: '', repository: '', default_tag: 'latest', tags_text: '' },
        newUserImage: { label: '', repository: '', default_tag: 'latest', tags_text: '' },
        editingDockerImage: null,
        dockerImageBulkMode: 'json',
        dockerImageBulkText: '',
        dockerImageBulkFileName: '',
        dockerImageBulkLoading: false,
        dockerImageBulkSummary: '',
        showDockerImageBulkModal: false,
        planTemplateBulkMode: 'json',
        planTemplateBulkText: '',
        planTemplateBulkFileName: '',
        planTemplateBulkLoading: false,
        planTemplateBulkSummary: '',
        showPlanTemplateBulkModal: false,
        clusterOverview: null,
        clusterLoading: false,
        joinCommand: '',
        joinCommandRaw: '',
        joinCommandLoading: false,
        joinCommandError: '',
        directpvDiscover: null,
        directpvDiscoverPath: '',
        directpvDiscoverLoading: false,
        directpvDiscoverSaving: false,
        directpvDiscoverError: '',
        directpvDiscoverMessage: '',
        directpvDiscoverRaw: '',
        directpvInitLoading: false,
        directpvInitError: '',
        directpvInitResult: '',
        showDirectpvInitConfirm: false,
        sshGenerateLoading: false,
        sshPrivateKeyOnce: '',
        sshSyncMessage: '',
        sshSyncError: '',
        tunnelPortsText: '',
        tunnelExposeLoading: false,
        tunnelSyncMessage: '',
        tunnelSyncError: '',
        tunnelInfo: {
            enabled: false,
            ports: [],
            ports_text: '',
            wss_url: '',
            path_prefix: '',
            client_command: '',
            port_commands: [],
            curl_example: '',
        },
        modalTab: 'general',
        workspaceLogs: {
            text: '',
            loading: false,
            error: '',
            pods: [],
            selectedPod: '',
            containers: [],
            selectedContainer: '',
        },
        workspaceDescribe: {
            text: '',
            loading: false,
            error: '',
        },
        monitorWindowOptions: [
            { minutes: 5, label: '5 min' },
            { minutes: 15, label: '15 min' },
            { minutes: 30, label: '30 min' },
            { minutes: 60, label: '1 hour' },
            { minutes: 300, label: '5 hours' },
        ],
        workspaceMonitor: {
            points: [],
            loading: false,
            error: '',
            pods: [],
            selectedPod: '',
            hasGpu: false,
            windowMinutes: 300,
            windowLabel: '5 hours',
        },
        workspaceLogsTimer: null,
        workspaceMonitorTimer: null,
        workspaceBackupTimer: null,
        workspaceBackup: {
            loading: false,
            scheduleLoading: false,
            runLoading: false,
            stopLoading: false,
            rcloneSaveLoading: false,
            error: '',
            syncMessage: '',
            syncError: '',
            schedule: '',
            remote: '',
            rcloneConfig: '',
            hasConfig: false,
            folders: [],
            volumeOptions: [],
            enabled: false,
            formDirty: false,
            status: {
                last_run_at: '',
                last_success: null,
                last_message: '',
                running: false,
                trigger: '',
                sidecar_active: false,
                sidecar_ready: false,
            },
        },
        monitorChartInstances: {},
        workspaceLogsAutoScroll: true,
        userList: [],
        adminUserFilter: '',
        adminUserStatus: '',
        adminUserGroupFilter: 'all',
        adminUserPagination: { page: 1, pages: 1, total: 0, per_page: 10 },
        adminUsersTab: 'users',
        adminServersTab: 'servers',
        adminDrivesTab: 'drives',
        resourceGroups: [],
        showGroupFormModal: false,
        editingGroup: null,
        groupForm: { name: '', max_cpu: 4, max_ram_g: 8, max_drive_size_gi: 50, max_gpu_vram_g: 10, max_servers: 5, max_drives: 3, max_images: 10, can_change_privileged: false },
        groupFormLoading: false,
        groupMembersModal: null,
        memberSearchQuery: '',
        memberSearchResults: [],
        memberSearchTimer: null,
        memberBulkEmails: '',
        memberBulkLoading: false,
        memberBulkSummary: '',
        resourceLimits: {
            limited: false,
            limits: null,
            equipment: {
                cpu: [2, 4, 8, 16, 32],
                ram: ['2G', '4G', '8G', '16G', '32G', '64G'],
                gpu: ['none', '1:1024', '1:10240', '1:40960', '2:20480'],
                drive_sizes: ['20Gi', '50Gi', '100Gi', '200Gi', '500Gi', '1Ti'],
            },
        },
        is_login: typeof is_login !== 'undefined' ? is_login : 0,
        menu: 'servers',
        showCreateServerModal: false,
        showBulkCreateServerModal: false,
        editingWorkspace: null,
        k8sNodeOptions: [],
        k8sNodeOptionsError: '',
        current_user: '',
        is_admin: false,
        runLoading: false,
        runError: '',
        modalWorkspace: null,
        deleteModalWorkspace: null,
        deleteModalIsAdmin: false,
        deleteConfirmInput: '',
        deleteInProgress: false,
        deleteModalUser: null,
        deleteUserConfirmInput: '',
        deleteUserInProgress: false,
        deleteModalImage: null,
        deleteImageIsAdmin: false,
        deleteImageInProgress: false,
        deleteYesNoModal: null,
        deleteYesNoInProgress: false,
        bulkSelected: {
            users: {},
            drives: {},
            servers: {},
            images: {},
        },
        bulkLastIndex: {
            users: -1,
            drives: -1,
            servers: -1,
            images: -1,
        },
        bulkActionLoading: false,
        bulkConfirmModal: null,
        toastMessage: '',
        toastTimer: null,
        mobileNavOpen: false,
        statusPollTimer: null,
        listLoading: 0,
        statusPending: {
            myWorkspaces: false,
            myDrives: false,
            adminWorkspaces: false,
            adminDrives: false,
        },
    },
    computed: {
        canConfirmDelete() {
            return this.deleteConfirmInput.trim().toLowerCase() === 'delete'
        },
        canConfirmDeleteDrive() {
            return this.deleteDriveConfirmInput.trim().toLowerCase() === 'delete'
        },
        canConfirmDeleteUser() {
            if (!this.deleteModalUser) return false
            return this.deleteUserConfirmInput.trim() === this.deleteModalUser.username
        },
        canChangePrivileged() {
            return this.is_admin || !!(this.resourceLimits && this.resourceLimits.can_change_privileged)
        },
        selectedDockerTags() {
            const img = this.dockerImages.find((i) => i.id === this.form.docker_image_id)
            if (!img) return []
            if (img.tags && img.tags.length) return img.tags
            return [img.default_tag || 'latest']
        },
        selectedDrivesLabel() {
            const mounts = (this.form.drive_mounts || []).filter((m) => m.drive_id)
            if (!mounts.length) return 'none (ephemeral)'
            return mounts.map((m) => this.driveMountSummary(m)).join(', ')
        },
        userTabs() {
            return [
                { id: 'servers', label: 'My servers' },
                { id: 'drives', label: 'My drives' },
                { id: 'images', label: 'My images' },
            ]
        },
        adminTabs() {
            return [
                { id: 'admin-overall', label: 'Overall' },
                { id: 'admin-users', label: 'Users' },
                { id: 'admin-drives', label: 'Drives' },
                { id: 'admin-servers', label: 'Servers' },
                { id: 'admin-images', label: 'Images' },
            ]
        },
        directpvDiscoverSelectedCount() {
            if (!this.directpvDiscover || !this.directpvDiscover.nodes) return 0
            return this.directpvDiscover.nodes.reduce((sum, node) => {
                const yes = (node.drives || []).filter((d) => d.select === 'yes').length
                return sum + yes
            }, 0)
        },
        directpvColumns() {
            const dp = this.clusterOverview && this.clusterOverview.directpv
            if (dp && dp.columns && dp.columns.length) return dp.columns
            const drives = (dp && dp.drives) || []
            if (!drives.length) return []
            return Object.keys(drives[0]).map((k) => ({ key: k, label: k.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()) }))
        },
        envKeysSorted() {
            return Object.keys(this.form.env_vars || {}).sort()
        },
        modalEnvKeys() {
            if (!this.modalWorkspace || !this.modalWorkspace.env_vars) return []
            return Object.keys(this.modalWorkspace.env_vars).sort()
        },
        modalK8sDisplay() {
            if (!this.modalWorkspace) return ''
            return (this.modalWorkspace.k8s_status && this.modalWorkspace.k8s_status.display)
                || this.modalWorkspace.state
                || ''
        },
        modalDeploymentSummary() {
            const dep = this.modalWorkspace && this.modalWorkspace.k8s_status
                && this.modalWorkspace.k8s_status.deployment
            if (!dep) return '—'
            return `${dep.ready}/${dep.desired} ready · ${dep.available} available`
        },
        modalPods() {
            const pods = this.modalWorkspace && this.modalWorkspace.k8s_status
                && this.modalWorkspace.k8s_status.pods
            return pods || []
        },
        modalPrimaryPod() {
            return this.modalPods.length ? this.modalPods[0] : null
        },
        modalPodDomain() {
            return (this.modalPrimaryPod && this.modalPrimaryPod.pod_domain) || '—'
        },
        modalPodIp() {
            return (this.modalPrimaryPod && this.modalPrimaryPod.pod_ip) || '—'
        },
        modalPodName() {
            return (this.modalPrimaryPod && this.modalPrimaryPod.name) || '—'
        },
        modalServiceDns() {
            const svc = this.modalWorkspace && this.modalWorkspace.k8s_status
                && this.modalWorkspace.k8s_status.service
            return (svc && svc.cluster_dns) || '—'
        },
        filteredPlanTemplates() {
            if (!this.resourceLimits.limited) return this.planTemplates
            const eq = this.resourceLimits.equipment || {}
            const cpus = eq.cpu || []
            const rams = eq.ram || []
            const gpus = eq.gpu || []
            return this.planTemplates.filter((t) =>
                cpuListIncludes(cpus, t.cpu) && rams.includes(t.ram) && gpus.includes(t.gpu),
            )
        },
        canCreateMoreServers() {
            const l = this.resourceLimits.limits
            if (!this.resourceLimits.limited || !l || !l.max_servers) return true
            const count = l.server_count ?? this.myServerPagination.total ?? this.myWorkspaces.length
            return count < l.max_servers
        },
        canCreateMoreDrives() {
            const l = this.resourceLimits.limits
            if (!this.resourceLimits.limited || !l || !l.max_drives) return true
            const count = l.drive_count ?? this.myDrivePagination.total ?? this.myDrives.length
            return count < l.max_drives
        },
        canCreateMoreImages() {
            const l = this.resourceLimits.limits
            if (!this.resourceLimits.limited || !l || !l.max_images) return true
            const count = l.image_count ?? this.myImagePagination.total ?? this.myDockerImages.length
            return count < l.max_images
        },
        dockerImageBulkPlaceholder() {
            return this.dockerImageBulkMode === 'json'
                ? DOCKER_IMAGE_BULK_PLACEHOLDER_JSON
                : DOCKER_IMAGE_BULK_PLACEHOLDER_CSV
        },
        planTemplateBulkPlaceholder() {
            return this.planTemplateBulkMode === 'json'
                ? PLAN_TEMPLATE_BULK_PLACEHOLDER_JSON
                : PLAN_TEMPLATE_BULK_PLACEHOLDER_CSV
        },
    },
    created() {
        const params = new URLSearchParams(window.location.search)
        const tab = params.get('tab') || 'servers'
        this.menu = tab === 'home' ? 'servers' : tab
        this.init()
    },
    beforeDestroy() {
        this.stopStatusPolling()
        this.stopWorkspaceLogsPoll()
    },
    methods: {
        startStatusPolling() {
            this.stopStatusPolling()
            if (!this.is_login) return
            this.statusPollTimer = setInterval(() => this.pollStatuses(), 5000)
        },
        stopStatusPolling() {
            if (this.statusPollTimer) {
                clearInterval(this.statusPollTimer)
                this.statusPollTimer = null
            }
        },
        beginListLoad() {
            this.listLoading += 1
        },
        endListLoad() {
            this.listLoading = Math.max(0, this.listLoading - 1)
        },
        formatContainerCommand(cmd) {
            const text = formatCommand(cmd || [])
            return text || '(default)'
        },
        bulkKey(context, item) {
            if (context === 'users') return item.username
            return String(item.id)
        },
        clearBulkSelection(context) {
            if (context) {
                this.$set(this.bulkSelected, context, {})
                this.bulkLastIndex[context] = -1
                return
            }
            ;['users', 'drives', 'servers', 'images'].forEach((c) => {
                this.$set(this.bulkSelected, c, {})
                this.bulkLastIndex[c] = -1
            })
        },
        bulkIsSelected(context, item) {
            return !!this.bulkSelected[context][this.bulkKey(context, item)]
        },
        bulkSelectedCount(context) {
            return Object.keys(this.bulkSelected[context] || {}).length
        },
        bulkSelectedOnPage(context, items) {
            return (items || []).filter((item) => this.bulkIsSelected(context, item))
        },
        bulkAllOnPageSelected(context, items) {
            const list = items || []
            if (!list.length) return false
            return list.every((item) => this.bulkIsSelected(context, item))
        },
        bulkSomeOnPageSelected(context, items) {
            const list = items || []
            if (!list.length) return false
            const n = list.filter((item) => this.bulkIsSelected(context, item)).length
            return n > 0 && n < list.length
        },
        onBulkSelectToggle(context, items, index, event) {
            if (!items || !items[index]) return
            const key = this.bulkKey(context, items[index])
            const willSelect = !this.bulkSelected[context][key]
            if (event.shiftKey && this.bulkLastIndex[context] >= 0) {
                const from = Math.min(this.bulkLastIndex[context], index)
                const to = Math.max(this.bulkLastIndex[context], index)
                for (let i = from; i <= to; i++) {
                    const k = this.bulkKey(context, items[i])
                    if (willSelect) this.$set(this.bulkSelected[context], k, true)
                    else this.$delete(this.bulkSelected[context], k)
                }
            } else if (willSelect) {
                this.$set(this.bulkSelected[context], key, true)
            } else {
                this.$delete(this.bulkSelected[context], key)
            }
            this.bulkLastIndex[context] = index
        },
        onBulkContextMenu(context, items, index, event) {
            if (event) event.preventDefault()
            this.onBulkSelectToggle(context, items, index, event)
        },
        bulkToggleAllOnPage(context, items, checked) {
            ;(items || []).forEach((item) => {
                const key = this.bulkKey(context, item)
                if (checked) this.$set(this.bulkSelected[context], key, true)
                else this.$delete(this.bulkSelected[context], key)
            })
        },
        openBulkConfirmModal(payload) {
            this.bulkConfirmModal = payload
        },
        closeBulkConfirmModal() {
            this.bulkConfirmModal = null
        },
        async confirmBulkAction() {
            if (!this.bulkConfirmModal || this.bulkActionLoading) return
            const modal = this.bulkConfirmModal
            this.bulkActionLoading = true
            try {
                await modal.run()
                this.closeBulkConfirmModal()
            } finally {
                this.bulkActionLoading = false
            }
        },
        bulkAcceptUsers() {
            const users = this.bulkSelectedOnPage('users', this.userList).filter((u) => !u.is_accept)
            if (!users.length) {
                this.showToast('No pending users selected')
                return
            }
            this.openBulkConfirmModal({
                title: 'Accept users',
                description: `Accept ${users.length} user(s)?`,
                confirmLabel: 'Yes, accept',
                confirmClass: 'bg-emerald-600 hover:bg-emerald-700',
                run: async () => {
                    const results = await Promise.allSettled(
                        users.map((u) => fetch('accept_user/' + encodeURIComponent(u.username))),
                    )
                    const ok = results.filter((r) => r.status === 'fulfilled' && r.value.status === 200).length
                    this.showToast(`Accepted ${ok}/${users.length} user(s)`)
                    this.clearBulkSelection('users')
                    await this.loadAdminUsers(this.adminUserPagination.page)
                },
            })
        },
        bulkDeleteUsers() {
            const users = this.bulkSelectedOnPage('users', this.userList)
            if (!users.length) return
            this.openBulkConfirmModal({
                title: 'Delete users',
                description: `Permanently delete ${users.length} user(s) and all their servers, drives, and images?`,
                confirmLabel: 'Yes, delete',
                run: async () => {
                    const results = await Promise.allSettled(
                        users.map((u) => fetch('delete_user/' + encodeURIComponent(u.username), { method: 'DELETE' })),
                    )
                    const ok = results.filter((r) => r.status === 'fulfilled' && r.value.status === 200).length
                    this.showToast(`Deleted ${ok}/${users.length} user(s)`)
                    this.clearBulkSelection('users')
                    const page = this.adminUserPagination.page
                    const next = this.userList.length <= users.length && page > 1 ? page - 1 : page
                    await this.loadAdminUsers(next)
                },
            })
        },
        bulkAcceptImages() {
            const images = this.bulkSelectedOnPage('images', this.adminDockerImages).filter((img) => !img.is_accepted)
            if (!images.length) {
                this.showToast('No pending images selected')
                return
            }
            this.openBulkConfirmModal({
                title: 'Accept images',
                description: `Accept ${images.length} image(s) for use in servers?`,
                confirmLabel: 'Yes, accept',
                confirmClass: 'bg-emerald-600 hover:bg-emerald-700',
                run: async () => {
                    const results = await Promise.allSettled(
                        images.map((img) => fetch('admin/docker_images/' + img.id, {
                            method: 'PUT',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ is_accepted: true }),
                        })),
                    )
                    const ok = results.filter((r) => r.status === 'fulfilled' && r.value.status === 200).length
                    this.showToast(`Accepted ${ok}/${images.length} image(s)`)
                    this.clearBulkSelection('images')
                    await this.loadAdminDockerImages(this.adminImagePagination.page)
                    await this.loadDockerImages()
                },
            })
        },
        bulkDeleteImages() {
            const images = this.bulkSelectedOnPage('images', this.adminDockerImages)
            if (!images.length) return
            this.openBulkConfirmModal({
                title: 'Delete images',
                description: `Delete ${images.length} image(s)? This cannot be undone.`,
                confirmLabel: 'Yes, delete',
                run: async () => {
                    const results = await Promise.allSettled(
                        images.map((img) => fetch('admin/docker_images/' + img.id, { method: 'DELETE' })),
                    )
                    const ok = results.filter((r) => r.status === 'fulfilled' && r.value.status === 200).length
                    this.showToast(`Deleted ${ok}/${images.length} image(s)`)
                    this.clearBulkSelection('images')
                    await this.loadAdminDockerImages(this.adminImagePagination.page)
                    await this.loadDockerImages()
                },
            })
        },
        bulkDeleteDrives() {
            const drives = this.bulkSelectedOnPage('drives', this.adminDrives)
            if (!drives.length) return
            const inUse = drives.filter((d) => d.in_use).length
            const deletable = drives.filter((d) => !d.in_use)
            if (!deletable.length) {
                this.showToast('Selected drives are in use — stop servers first')
                return
            }
            let desc = `Delete ${deletable.length} drive(s) and their PVCs?`
            if (inUse) desc += ` (${inUse} in-use drive(s) will be skipped.)`
            this.openBulkConfirmModal({
                title: 'Delete drives',
                description: desc,
                confirmLabel: 'Yes, delete',
                run: async () => {
                    const results = await Promise.allSettled(
                        deletable.map((d) => fetch('drives/' + d.id, { method: 'DELETE' })),
                    )
                    const ok = results.filter((r) => r.status === 'fulfilled' && r.value.status === 200).length
                    this.showToast(`Deleted ${ok}/${deletable.length} drive(s)`)
                    this.clearBulkSelection('drives')
                    await this.reloadAdminDrives(this.adminDrivePagination.page)
                },
            })
        },
        bulkStartServers() {
            const servers = this.bulkSelectedOnPage('servers', this.adminWorkspaces).filter((ws) => ws.state === 'offline')
            if (!servers.length) {
                this.showToast('No offline servers selected')
                return
            }
            this.openBulkConfirmModal({
                title: 'Start servers',
                description: `Start ${servers.length} server(s)?`,
                confirmLabel: 'Yes, start',
                confirmClass: 'bg-blue-600 hover:bg-blue-700',
                run: async () => {
                    const results = await Promise.allSettled(
                        servers.map((ws) => fetch('workspaces/' + ws.id + '/start', { method: 'POST' })),
                    )
                    const ok = results.filter((r) => r.status === 'fulfilled' && r.value.status === 200).length
                    this.showToast(`Started ${ok}/${servers.length} server(s)`)
                    this.clearBulkSelection('servers')
                    await this.reloadAdminWorkspaces(this.adminPagination.page)
                    await this.pollStatuses()
                },
            })
        },
        bulkStopServers() {
            const servers = this.bulkSelectedOnPage('servers', this.adminWorkspaces).filter((ws) =>
                ['running', 'pending_start', 'pending_stop'].includes(ws.state),
            )
            if (!servers.length) {
                this.showToast('No running servers selected')
                return
            }
            this.openBulkConfirmModal({
                title: 'Stop servers',
                description: `Stop ${servers.length} server(s)?`,
                confirmLabel: 'Yes, stop',
                confirmClass: 'bg-amber-600 hover:bg-amber-700',
                run: async () => {
                    const results = await Promise.allSettled(
                        servers.map((ws) => fetch('workspaces/' + ws.id + '/stop', { method: 'POST' })),
                    )
                    const ok = results.filter((r) => r.status === 'fulfilled' && r.value.status === 200).length
                    this.showToast(`Stopped ${ok}/${servers.length} server(s)`)
                    this.clearBulkSelection('servers')
                    await this.reloadAdminWorkspaces(this.adminPagination.page)
                    await this.pollStatuses()
                },
            })
        },
        bulkDeleteServers() {
            const servers = this.bulkSelectedOnPage('servers', this.adminWorkspaces)
            const deletable = servers.filter((ws) => ws.state === 'offline')
            if (!deletable.length) {
                this.showToast('Only offline servers can be deleted — stop running servers first')
                return
            }
            let desc = `Delete ${deletable.length} server(s)? This cannot be undone.`
            if (deletable.length < servers.length) {
                desc += ` (${servers.length - deletable.length} non-offline server(s) will be skipped.)`
            }
            this.openBulkConfirmModal({
                title: 'Delete servers',
                description: desc,
                confirmLabel: 'Yes, delete',
                run: async () => {
                    const results = await Promise.allSettled(
                        deletable.map((ws) => fetch('workspaces/' + ws.id, { method: 'DELETE' })),
                    )
                    const ok = results.filter((r) => r.status === 'fulfilled' && r.value.status === 200).length
                    this.showToast(`Deleted ${ok}/${deletable.length} server(s)`)
                    this.clearBulkSelection('servers')
                    await this.reloadAdminWorkspaces(this.adminPagination.page)
                },
            })
        },
        bulkDeleteMyDrives() {
            const drives = this.bulkSelectedOnPage('drives', this.myDrives)
            if (!drives.length) return
            const inUse = drives.filter((d) => d.in_use).length
            const deletable = drives.filter((d) => !d.in_use)
            if (!deletable.length) {
                this.showToast('Selected drives are in use — stop servers first')
                return
            }
            let desc = `Delete ${deletable.length} drive(s) and their PVCs?`
            if (inUse) desc += ` (${inUse} in-use drive(s) will be skipped.)`
            this.openBulkConfirmModal({
                title: 'Delete drives',
                description: desc,
                confirmLabel: 'Yes, delete',
                run: async () => {
                    const results = await Promise.allSettled(
                        deletable.map((d) => fetch('drives/' + d.id, { method: 'DELETE' })),
                    )
                    const ok = results.filter((r) => r.status === 'fulfilled' && r.value.status === 200).length
                    this.showToast(`Deleted ${ok}/${deletable.length} drive(s)`)
                    this.clearBulkSelection('drives')
                    const page = this.myDrivePagination.page
                    const next = this.myDrives.length <= deletable.length && page > 1 ? page - 1 : page
                    await this.reloadMyDrives(next)
                    await this.loadMyDrivesAll()
                },
            })
        },
        bulkStartMyServers() {
            const servers = this.bulkSelectedOnPage('servers', this.myWorkspaces).filter((ws) => ws.state === 'offline')
            if (!servers.length) {
                this.showToast('No offline servers selected')
                return
            }
            this.openBulkConfirmModal({
                title: 'Start servers',
                description: `Start ${servers.length} server(s)?`,
                confirmLabel: 'Yes, start',
                confirmClass: 'bg-blue-600 hover:bg-blue-700',
                run: async () => {
                    const results = await Promise.allSettled(
                        servers.map((ws) => fetch('workspaces/' + ws.id + '/start', { method: 'POST' })),
                    )
                    const ok = results.filter((r) => r.status === 'fulfilled' && r.value.status === 200).length
                    this.showToast(`Started ${ok}/${servers.length} server(s)`)
                    this.clearBulkSelection('servers')
                    await this.reloadServerLists()
                },
            })
        },
        bulkStopMyServers() {
            const servers = this.bulkSelectedOnPage('servers', this.myWorkspaces).filter((ws) =>
                ['running', 'pending_start', 'pending_stop'].includes(ws.state),
            )
            if (!servers.length) {
                this.showToast('No running servers selected')
                return
            }
            this.openBulkConfirmModal({
                title: 'Stop servers',
                description: `Stop ${servers.length} server(s)?`,
                confirmLabel: 'Yes, stop',
                confirmClass: 'bg-amber-600 hover:bg-amber-700',
                run: async () => {
                    const results = await Promise.allSettled(
                        servers.map((ws) => fetch('workspaces/' + ws.id + '/stop', { method: 'POST' })),
                    )
                    const ok = results.filter((r) => r.status === 'fulfilled' && r.value.status === 200).length
                    this.showToast(`Stopped ${ok}/${servers.length} server(s)`)
                    this.clearBulkSelection('servers')
                    await this.reloadServerLists()
                },
            })
        },
        bulkDeleteMyServers() {
            const servers = this.bulkSelectedOnPage('servers', this.myWorkspaces)
            const deletable = servers.filter((ws) => ws.state === 'offline')
            if (!deletable.length) {
                this.showToast('Only offline servers can be deleted — stop running servers first')
                return
            }
            let desc = `Delete ${deletable.length} server(s)? This cannot be undone.`
            if (deletable.length < servers.length) {
                desc += ` (${servers.length - deletable.length} non-offline server(s) will be skipped.)`
            }
            this.openBulkConfirmModal({
                title: 'Delete servers',
                description: desc,
                confirmLabel: 'Yes, delete',
                run: async () => {
                    const results = await Promise.allSettled(
                        deletable.map((ws) => fetch('workspaces/' + ws.id, { method: 'DELETE' })),
                    )
                    const ok = results.filter((r) => r.status === 'fulfilled' && r.value.status === 200).length
                    this.showToast(`Deleted ${ok}/${deletable.length} server(s)`)
                    this.clearBulkSelection('servers')
                    const page = this.myServerPagination.page
                    const next = this.myWorkspaces.length <= deletable.length && page > 1 ? page - 1 : page
                    await this.reloadMyWorkspaces(next)
                },
            })
        },
        bulkDeleteMyImages() {
            const images = this.bulkSelectedOnPage('images', this.myDockerImages)
            if (!images.length) return
            this.openBulkConfirmModal({
                title: 'Delete images',
                description: `Delete ${images.length} image(s)? This cannot be undone.`,
                confirmLabel: 'Yes, delete',
                run: async () => {
                    const results = await Promise.allSettled(
                        images.map((img) => fetch('docker_images/' + img.id, { method: 'DELETE' })),
                    )
                    const ok = results.filter((r) => r.status === 'fulfilled' && r.value.status === 200).length
                    this.showToast(`Deleted ${ok}/${images.length} image(s)`)
                    this.clearBulkSelection('images')
                    const page = this.myImagePagination.page
                    const next = this.myDockerImages.length <= images.length && page > 1 ? page - 1 : page
                    await this.reloadMyImages(next)
                },
            })
        },
        setStatusPending(keys, value) {
            ;(keys || []).forEach((key) => {
                if (key in this.statusPending) this.statusPending[key] = value
            })
        },
        async loadListsThenPoll(loadFn, pollFn, pendingKeysFn) {
            this.beginListLoad()
            try {
                await loadFn()
            } finally {
                this.endListLoad()
            }
            const keys = typeof pendingKeysFn === 'function' ? pendingKeysFn() : (pendingKeysFn || [])
            if (keys.length) this.setStatusPending(keys, true)
            try {
                if (pollFn) await pollFn()
            } finally {
                if (keys.length) this.setStatusPending(keys, false)
            }
        },
        async pollStatuses() {
            if (this.listLoading > 0) return
            const m = this.menu
            const tasks = []
            if (m === 'drives' || m === 'servers') tasks.push(this.pollMyDriveStatuses())
            if (m === 'servers') tasks.push(this.pollMyWorkspaceStatuses())
            if (m === 'admin-drives') tasks.push(this.pollAdminDriveStatuses())
            if (m === 'admin-servers') tasks.push(this.pollAdminWorkspaceStatuses())
            if (m === 'admin-overall') await this.loadClusterOverview()
            await Promise.all(tasks)
        },
        collectIds(items) {
            const seen = {}
            return (items || []).map((item) => item.id).filter((id) => {
                if (!id || seen[id]) return false
                seen[id] = true
                return true
            })
        },
        mergeWorkspaceStatuses(items, statusMap) {
            ;(items || []).forEach((ws) => {
                const st = statusMap[ws.id]
                if (!st) return
                this.$set(ws, 'state', st.state)
                this.$set(ws, 'k8s_status', st.k8s_status)
            })
        },
        mergeDriveStatuses(items, statusMap) {
            ;(items || []).forEach((d) => {
                const st = statusMap[d.id]
                if (!st) return
                ;['status', 'pvc_phase', 'in_use', 'node', 'pv_name'].forEach((k) => {
                    if (st[k] !== undefined) this.$set(d, k, st[k])
                })
            })
        },
        statusMapFromResult(rows) {
            const map = {}
            ;(rows || []).forEach((row) => { if (row.id) map[row.id] = row })
            return map
        },
        async fetchWorkspaceStatuses(path, ids) {
            const res = await fetch(path, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(ids && ids.length ? { ids } : {}),
            })
            if (res.status !== 200) return {}
            const data = await res.json()
            return this.statusMapFromResult(data.result)
        },
        async fetchDriveStatuses(path, ids) {
            const res = await fetch(path, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(ids && ids.length ? { ids } : {}),
            })
            if (res.status !== 200) return {}
            const data = await res.json()
            return this.statusMapFromResult(data.result)
        },
        async pollMyWorkspaceStatuses() {
            const ids = this.collectIds(this.myWorkspaces)
            if (!ids.length) return
            const map = await this.fetchWorkspaceStatuses('workspaces/status', ids)
            this.mergeWorkspaceStatuses(this.myWorkspaces, map)
            if (this.modalWorkspace && map[this.modalWorkspace.id]) {
                this.mergeWorkspaceStatuses([this.modalWorkspace], map)
            }
        },
        async pollAdminWorkspaceStatuses() {
            const ids = this.collectIds(this.adminWorkspaces)
            if (!ids.length) return
            const map = await this.fetchWorkspaceStatuses('admin/workspaces/status', ids)
            this.mergeWorkspaceStatuses(this.adminWorkspaces, map)
        },
        async pollMyDriveStatuses() {
            const ids = this.collectIds([].concat(this.myDrives || [], this.myDrivesAll || []))
            if (!ids.length) return
            const map = await this.fetchDriveStatuses('drives/status', ids)
            this.mergeDriveStatuses(this.myDrives, map)
            this.mergeDriveStatuses(this.myDrivesAll, map)
        },
        async pollAdminDriveStatuses() {
            const ids = this.collectIds(this.adminDrives)
            if (!ids.length) return
            const map = await this.fetchDriveStatuses('admin/drives/status', ids)
            this.mergeDriveStatuses(this.adminDrives, map)
        },
        async reloadMyWorkspaces(page) {
            await this.loadListsThenPoll(
                () => this.loadMyWorkspaces(page),
                () => this.pollMyWorkspaceStatuses(),
                () => (this.myWorkspaces.length ? ['myWorkspaces'] : []),
            )
        },
        async reloadMyDrives(page) {
            await this.loadListsThenPoll(
                () => this.loadMyDrives(page),
                () => this.pollMyDriveStatuses(),
                () => (this.myDrives.length ? ['myDrives'] : []),
            )
        },
        async reloadMyDrivesAll() {
            await this.loadListsThenPoll(
                () => this.loadMyDrivesAll(),
                () => this.pollMyDriveStatuses(),
                () => (this.myDrivesAll.length ? ['myDrives'] : []),
            )
        },
        async reloadAdminWorkspaces(page) {
            await this.loadListsThenPoll(
                () => this.loadAdminWorkspaces(page),
                () => this.pollAdminWorkspaceStatuses(),
                () => (this.adminWorkspaces.length ? ['adminWorkspaces'] : []),
            )
        },
        async reloadAdminDrives(page) {
            await this.loadListsThenPoll(
                () => this.loadAdminDrives(page),
                () => this.pollAdminDriveStatuses(),
                () => (this.adminDrives.length ? ['adminDrives'] : []),
            )
        },
        async reloadDriveLists() {
            await this.loadListsThenPoll(async () => {
                await this.loadMyDrives(this.myDrivePagination.page)
                await this.loadMyDrivesAll()
                if (this.is_admin) await this.loadAdminDrives(this.adminDrivePagination.page)
            }, async () => {
                await this.pollMyDriveStatuses()
                if (this.is_admin) await this.pollAdminDriveStatuses()
            }, () => {
                const keys = []
                if (this.myDrives.length) keys.push('myDrives')
                if (this.is_admin && this.adminDrives.length) keys.push('adminDrives')
                return keys
            })
        },
        async reloadServerLists() {
            await this.loadListsThenPoll(async () => {
                await this.loadMyWorkspaces(this.myServerPagination.page)
                if (this.is_admin && this.menu === 'admin-servers') {
                    await this.loadAdminWorkspaces(this.adminPagination.page)
                }
            }, async () => {
                await this.pollMyWorkspaceStatuses()
                if (this.is_admin && this.menu === 'admin-servers') {
                    await this.pollAdminWorkspaceStatuses()
                }
            }, () => {
                const keys = []
                if (this.myWorkspaces.length) keys.push('myWorkspaces')
                if (this.is_admin && this.menu === 'admin-servers' && this.adminWorkspaces.length) {
                    keys.push('adminWorkspaces')
                }
                return keys
            })
        },
        statusPendingKeysForMenu() {
            const keys = []
            const m = this.menu
            if (m === 'servers' && this.myWorkspaces.length) keys.push('myWorkspaces')
            if (m === 'drives' && this.myDrives.length) keys.push('myDrives')
            if (m === 'admin-drives' && this.adminDrives.length) keys.push('adminDrives')
            if (m === 'admin-servers' && this.adminWorkspaces.length) keys.push('adminWorkspaces')
            return keys
        },
        loginWithGithub() { window.location = 'login' },
        logout() { window.location = 'logout' },
        workspaceUrl(ws) {
            return window.location.protocol + '//' + (ws.hostname || '')
        },
        driveOptionLabel(d) {
            if (!d) return '—'
            const inner = d.size + (d.node ? ', ' + d.node : '')
            let label = d.name + ' (' + inner + ')'
            if (d.workspace_count > 0) {
                label += ' · ' + d.workspace_count + ' server' + (d.workspace_count === 1 ? '' : 's')
            }
            if (d.in_use) label += ' · running'
            return label
        },
        driveDetailLine(d) {
            if (!d) return ''
            let line = d.size
            if (d.node) line += ' · ' + d.node
            if (d.workspace_count > 0) {
                line += ' · ' + d.workspace_count + ' server' + (d.workspace_count === 1 ? '' : 's')
            }
            if (d.in_use) line += ' · running'
            return line
        },
        showToast(msg) {
            this.toastMessage = msg
            if (this.toastTimer) clearTimeout(this.toastTimer)
            this.toastTimer = setTimeout(() => { this.toastMessage = '' }, 2200)
        },
        async copyWorkspaceUrl(ws) {
            const url = this.workspaceUrl(ws)
            try {
                await navigator.clipboard.writeText(url)
                this.showToast('Service URL copied')
            } catch {
                const ta = document.createElement('textarea')
                ta.value = url
                document.body.appendChild(ta)
                ta.select()
                document.execCommand('copy')
                document.body.removeChild(ta)
                this.showToast('Service URL copied')
            }
        },
        async copyWorkspaceDomain(ws) {
            const domain = (ws && ws.hostname) || ''
            if (!domain) return
            try {
                await navigator.clipboard.writeText(domain)
                this.showToast('Service domain copied')
            } catch {
                const ta = document.createElement('textarea')
                ta.value = domain
                document.body.appendChild(ta)
                ta.select()
                document.execCommand('copy')
                document.body.removeChild(ta)
                this.showToast('Service domain copied')
            }
        },
        primaryWorkspacePod(ws) {
            const pods = ws && ws.k8s_status && ws.k8s_status.pods
            return pods && pods.length ? pods[0] : null
        },
        copyPodDomain(ws) {
            const pod = this.primaryWorkspacePod(ws)
            if (pod && pod.pod_domain) this.copyText(pod.pod_domain, 'Pod domain copied')
        },
        copyPodIp(ws) {
            const pod = this.primaryWorkspacePod(ws)
            if (pod && pod.pod_ip) this.copyText(pod.pod_ip, 'Pod IP copied')
        },
        copyPodName(ws) {
            const pod = this.primaryWorkspacePod(ws)
            if (pod && pod.name) this.copyText(pod.name, 'Pod name copied')
        },
        copyServiceDns(ws) {
            const svc = ws && ws.k8s_status && ws.k8s_status.service
            if (svc && svc.cluster_dns) this.copyText(svc.cluster_dns, 'Service DNS copied')
        },
        openWorkspaceModal(ws) {
            this.mobileNavOpen = false
            this.stopWorkspaceLogsPoll()
            this.modalTab = 'general'
            this.workspaceLogs = {
                text: '',
                loading: false,
                error: '',
                pods: [],
                selectedPod: '',
                containers: [],
                selectedContainer: '',
            }
            this.workspaceDescribe = { text: '', loading: false, error: '' }
            this.workspaceMonitor = {
                points: [],
                loading: false,
                error: '',
                pods: [],
                selectedPod: '',
                hasGpu: false,
                windowMinutes: 300,
                windowLabel: '5 hours',
            }
            this.destroyMonitorCharts()
            this.workspaceLogsAutoScroll = true
            this.modalWorkspace = { ...ws, env_vars: { ...(ws.env_vars || {}) } }
            this.sshPrivateKeyOnce = ''
            this.sshSyncMessage = ''
            this.sshSyncError = ''
            this.tunnelPortsText = ''
            this.tunnelExposeLoading = false
            this.tunnelSyncMessage = ''
            this.tunnelSyncError = ''
            this.tunnelInfo = {
                enabled: false,
                ports: [],
                ports_text: '',
                wss_url: '',
                path_prefix: '',
                client_command: '',
                port_commands: [],
                curl_example: '',
            }
            this.loadWorkspaceSsh(ws)
            this.loadWorkspaceTunnel(ws)
            this.workspaceBackup = {
                loading: false,
                scheduleLoading: false,
                runLoading: false,
                stopLoading: false,
                rcloneSaveLoading: false,
                error: '',
                syncMessage: '',
                syncError: '',
                schedule: '',
                remote: '',
                rcloneConfig: '',
                hasConfig: false,
                folders: [],
                volumeOptions: [],
                enabled: false,
                formDirty: false,
                status: {
                    last_run_at: '',
                    last_success: null,
                    last_message: '',
                    running: false,
                    trigger: '',
                    sidecar_active: false,
                    sidecar_ready: false,
                },
            }
        },
        closeWorkspaceModal() {
            this.stopWorkspaceLogsPoll()
            this.stopWorkspaceMonitorPoll()
            this.stopWorkspaceBackupPoll()
            this.destroyMonitorCharts()
            this.modalTab = 'general'
            this.modalWorkspace = null
            this.sshPrivateKeyOnce = ''
            this.sshSyncMessage = ''
            this.sshSyncError = ''
            this.tunnelSyncMessage = ''
            this.tunnelSyncError = ''
        },
        switchModalTab(tab) {
            this.modalTab = tab
            this.stopWorkspaceLogsPoll()
            this.stopWorkspaceMonitorPoll()
            this.stopWorkspaceBackupPoll()
            if (tab === 'logs') {
                this.destroyMonitorCharts()
                this.fetchWorkspaceLogs()
                this.startWorkspaceLogsPoll()
                return
            }
            if (tab === 'monitor') {
                this.fetchWorkspaceMonitor()
                this.startWorkspaceMonitorPoll()
                return
            }
            if (tab === 'backup') {
                this.destroyMonitorCharts()
                this.workspaceBackup.formDirty = false
                this.fetchWorkspaceBackup()
                this.startWorkspaceBackupPoll()
                return
            }
            this.destroyMonitorCharts()
            if (tab === 'describe' && !this.workspaceDescribe.text && !this.workspaceDescribe.loading) {
                this.fetchWorkspaceDescribe()
            }
        },
        startWorkspaceLogsPoll() {
            this.stopWorkspaceLogsPoll()
            this.workspaceLogsTimer = setInterval(() => {
                if (this.modalTab === 'logs' && this.modalWorkspace) {
                    this.fetchWorkspaceLogs(true)
                }
            }, 2000)
        },
        stopWorkspaceLogsPoll() {
            if (this.workspaceLogsTimer) {
                clearInterval(this.workspaceLogsTimer)
                this.workspaceLogsTimer = null
            }
        },
        onWorkspaceLogsScroll(event) {
            const el = event.target
            this.workspaceLogsAutoScroll = el.scrollHeight - el.scrollTop - el.clientHeight < 48
        },
        onWorkspaceLogsPodChange() {
            this.workspaceLogs.selectedContainer = ''
            this.fetchWorkspaceLogs()
        },
        async fetchWorkspaceLogs(silent) {
            if (!this.modalWorkspace) return
            if (!silent) this.workspaceLogs.loading = true
            const ws = this.modalWorkspace
            const params = new URLSearchParams({ tail: '500' })
            if (this.workspaceLogs.selectedPod) params.set('pod', this.workspaceLogs.selectedPod)
            if (this.workspaceLogs.selectedContainer) params.set('container', this.workspaceLogs.selectedContainer)
            try {
                const res = await fetch('workspaces/' + ws.id + '/logs?' + params.toString())
                if (!this.modalWorkspace || this.modalWorkspace.id !== ws.id) return
                const data = await res.json().catch(() => ({}))
                const result = data.result || {}
                if (res.status !== 200) {
                    this.workspaceLogs.error = data.message || 'Failed to load logs'
                    return
                }
                this.workspaceLogs.text = result.logs || ''
                this.workspaceLogs.pods = result.pods || []
                this.workspaceLogs.containers = result.containers || []
                if (result.selected_pod) this.workspaceLogs.selectedPod = result.selected_pod
                if (!this.workspaceLogs.selectedPod && this.workspaceLogs.pods.length) {
                    this.workspaceLogs.selectedPod = this.workspaceLogs.pods[0].name
                }
                this.workspaceLogs.error = result.error || ''
            } catch (e) {
                if (this.modalWorkspace && this.modalWorkspace.id === ws.id) {
                    this.workspaceLogs.error = e.message || 'Failed to load logs'
                }
            } finally {
                if (this.modalWorkspace && this.modalWorkspace.id === ws.id) {
                    this.workspaceLogs.loading = false
                    this.$nextTick(() => {
                        const el = this.$refs.workspaceLogsTerminal
                        if (el && this.workspaceLogsAutoScroll) el.scrollTop = el.scrollHeight
                    })
                }
            }
        },
        async fetchWorkspaceDescribe() {
            if (!this.modalWorkspace) return
            const ws = this.modalWorkspace
            this.workspaceDescribe.loading = true
            this.workspaceDescribe.error = ''
            const params = new URLSearchParams()
            if (this.workspaceLogs.selectedPod) params.set('pod', this.workspaceLogs.selectedPod)
            try {
                const qs = params.toString()
                const res = await fetch('workspaces/' + ws.id + '/describe' + (qs ? '?' + qs : ''))
                if (!this.modalWorkspace || this.modalWorkspace.id !== ws.id) return
                const data = await res.json().catch(() => ({}))
                if (res.status !== 200) {
                    this.workspaceDescribe.error = data.message || 'Failed to load describe output'
                    this.workspaceDescribe.text = ''
                    return
                }
                this.workspaceDescribe.text = (data.result && data.result.text) || ''
            } catch (e) {
                if (this.modalWorkspace && this.modalWorkspace.id === ws.id) {
                    this.workspaceDescribe.error = e.message || 'Failed to load describe output'
                }
            } finally {
                if (this.modalWorkspace && this.modalWorkspace.id === ws.id) {
                    this.workspaceDescribe.loading = false
                }
            }
        },
        startWorkspaceMonitorPoll() {
            this.stopWorkspaceMonitorPoll()
            this.workspaceMonitorTimer = setInterval(() => {
                if (this.modalTab === 'monitor' && this.modalWorkspace) {
                    this.fetchWorkspaceMonitor(true)
                }
            }, 2000)
        },
        stopWorkspaceMonitorPoll() {
            if (this.workspaceMonitorTimer) {
                clearInterval(this.workspaceMonitorTimer)
                this.workspaceMonitorTimer = null
            }
        },
        onWorkspaceMonitorPodChange() {
            this.fetchWorkspaceMonitor()
        },
        onWorkspaceMonitorWindowChange() {
            this.fetchWorkspaceMonitor()
        },
        formatMonitorTime(iso) {
            if (!iso) return ''
            const d = new Date(iso)
            if (Number.isNaN(d.getTime())) return iso
            const mins = this.workspaceMonitor.windowMinutes || 300
            if (mins <= 30) {
                return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
            }
            return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        },
        monitorLatestPoint() {
            const pts = this.workspaceMonitor.points || []
            return pts.length ? pts[pts.length - 1] : null
        },
        formatMonitorCpuSummary(point) {
            if (!point) return '—'
            const used = Number(point.cpu_cores ?? 0)
            const limit = Number(point.cpu_limit_cores ?? 0)
            const pct = point.cpu_pct ?? 0
            return `${used.toFixed(2)} / ${limit.toFixed(2)} cores (${pct}%)`
        },
        formatMonitorMemorySummary(point) {
            if (!point) return '—'
            const used = Number(point.memory_gb ?? 0)
            const limit = Number(point.memory_limit_gb ?? 0)
            const pct = point.memory_pct ?? 0
            return `${used.toFixed(2)} / ${limit.toFixed(2)} GB (${pct}%)`
        },
        formatMonitorGpuUtilSummary(point) {
            if (!point || point.gpu_util_pct == null) return '—'
            return `${Number(point.gpu_util_pct).toFixed(0)}% SM`
        },
        formatMonitorGpuMemSummary(point) {
            if (!point || point.gpu_mem_total_gib == null) return '—'
            const used = Number(point.gpu_mem_used_gib ?? 0)
            const limit = Number(point.gpu_mem_total_gib ?? 0)
            const pct = point.gpu_mem_pct ?? 0
            return `${used.toFixed(2)} / ${limit.toFixed(2)} GiB (${pct}%)`
        },
        destroyMonitorCharts() {
            const keys = ['cpu', 'memory', 'gpuUtil', 'gpuMem']
            keys.forEach((key) => {
                if (this.monitorChartInstances[key]) {
                    this.monitorChartInstances[key].destroy()
                    this.monitorChartInstances[key] = null
                }
            })
        },
        monitorChartOptions(title, color, tooltipLabel) {
            return {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                interaction: { intersect: false, mode: 'index' },
                plugins: {
                    legend: { display: false },
                    title: {
                        display: true,
                        text: title,
                        color: '#334155',
                        font: { size: 12, weight: '600' },
                        padding: { bottom: 8 },
                    },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => {
                                if (typeof tooltipLabel === 'function') {
                                    return tooltipLabel(ctx)
                                }
                                const v = ctx.parsed.y
                                return v == null ? '' : `${ctx.dataset.label}: ${v}%`
                            },
                        },
                    },
                },
                scales: {
                    x: {
                        display: true,
                        ticks: {
                            maxTicksLimit: 8,
                            color: '#94a3b8',
                            font: { size: 10 },
                        },
                        grid: { display: false },
                    },
                    y: {
                        min: 0,
                        max: 100,
                        ticks: {
                            stepSize: 25,
                            color: '#94a3b8',
                            font: { size: 10 },
                            callback: (v) => v + '%',
                        },
                        grid: { color: 'rgba(148, 163, 184, 0.2)' },
                    },
                },
                elements: {
                    line: { borderWidth: 2, tension: 0.15 },
                    point: { radius: 0, hitRadius: 8, hoverRadius: 3 },
                },
            }
        },
        upsertMonitorChart(key, canvasRef, title, borderColor, fillColor, labels, values, tooltipLabel) {
            if (typeof Chart === 'undefined') return
            const canvas = canvasRef
            if (!canvas) return
            const dataset = {
                label: title,
                data: values,
                borderColor: borderColor,
                backgroundColor: fillColor,
                fill: true,
            }
            if (this.monitorChartInstances[key]) {
                const chart = this.monitorChartInstances[key]
                chart.options.plugins.title.text = title
                if (tooltipLabel) {
                    chart.options.plugins.tooltip.callbacks.label = (ctx) => tooltipLabel(ctx)
                }
                chart.data.labels = labels
                chart.data.datasets[0].data = values
                chart.data.datasets[0].label = title
                chart.update('none')
                return
            }
            this.monitorChartInstances[key] = new Chart(canvas, {
                type: 'line',
                data: { labels, datasets: [dataset] },
                options: this.monitorChartOptions(title, borderColor, tooltipLabel),
            })
        },
        renderMonitorCharts() {
            const pts = this.workspaceMonitor.points || []
            const labels = pts.map((p) => this.formatMonitorTime(p.ts))
            const latest = pts.length ? pts[pts.length - 1] : null
            this.$nextTick(() => {
                this.upsertMonitorChart(
                    'cpu',
                    this.$refs.monitorChartCpu,
                    latest ? `CPU · ${this.formatMonitorCpuSummary(latest)}` : 'CPU utilization',
                    'rgb(59, 130, 246)',
                    'rgba(59, 130, 246, 0.28)',
                    labels,
                    pts.map((p) => p.cpu_pct),
                    (ctx) => {
                        const p = pts[ctx.dataIndex]
                        if (!p) return ''
                        return this.formatMonitorCpuSummary(p)
                    },
                )
                this.upsertMonitorChart(
                    'memory',
                    this.$refs.monitorChartMemory,
                    latest ? `RAM · ${this.formatMonitorMemorySummary(latest)}` : 'RAM utilization',
                    'rgb(16, 185, 129)',
                    'rgba(16, 185, 129, 0.28)',
                    labels,
                    pts.map((p) => p.memory_pct),
                    (ctx) => {
                        const p = pts[ctx.dataIndex]
                        if (!p) return ''
                        return this.formatMonitorMemorySummary(p)
                    },
                )
                if (this.workspaceMonitor.hasGpu) {
                    this.upsertMonitorChart(
                        'gpuUtil',
                        this.$refs.monitorChartGpuUtil,
                        latest ? `GPU · ${this.formatMonitorGpuUtilSummary(latest)}` : 'GPU utilization',
                        'rgb(168, 85, 247)',
                        'rgba(168, 85, 247, 0.28)',
                        labels,
                        pts.map((p) => (p.gpu_util_pct == null ? null : p.gpu_util_pct)),
                        (ctx) => {
                            const p = pts[ctx.dataIndex]
                            if (!p || p.gpu_util_pct == null) return ''
                            return this.formatMonitorGpuUtilSummary(p)
                        },
                    )
                    this.upsertMonitorChart(
                        'gpuMem',
                        this.$refs.monitorChartGpuMem,
                        latest ? `GPU memory · ${this.formatMonitorGpuMemSummary(latest)}` : 'GPU memory',
                        'rgb(245, 158, 11)',
                        'rgba(245, 158, 11, 0.28)',
                        labels,
                        pts.map((p) => (p.gpu_mem_pct == null ? null : p.gpu_mem_pct)),
                        (ctx) => {
                            const p = pts[ctx.dataIndex]
                            if (!p || p.gpu_mem_total_gib == null) return ''
                            return this.formatMonitorGpuMemSummary(p)
                        },
                    )
                }
            })
        },
        async fetchWorkspaceMonitor(silent) {
            if (!this.modalWorkspace) return
            if (!silent) this.workspaceMonitor.loading = true
            const ws = this.modalWorkspace
            const params = new URLSearchParams()
            if (this.workspaceMonitor.selectedPod) params.set('pod', this.workspaceMonitor.selectedPod)
            params.set('window', String(this.workspaceMonitor.windowMinutes || 300))
            try {
                const qs = params.toString()
                const res = await fetch('workspaces/' + ws.id + '/monitor' + (qs ? '?' + qs : ''))
                if (!this.modalWorkspace || this.modalWorkspace.id !== ws.id) return
                const data = await res.json().catch(() => ({}))
                const result = data.result || {}
                if (res.status !== 200) {
                    this.workspaceMonitor.error = data.message || 'Failed to load monitor metrics'
                    return
                }
                this.workspaceMonitor.points = result.points || []
                this.workspaceMonitor.pods = result.pods || []
                this.workspaceMonitor.hasGpu = !!result.has_gpu
                if (result.window_minutes) this.workspaceMonitor.windowMinutes = result.window_minutes
                this.workspaceMonitor.windowLabel = result.window_label || this.workspaceMonitor.windowLabel
                if (result.window_options && result.window_options.length) {
                    this.monitorWindowOptions = result.window_options
                }
                if (result.selected_pod) this.workspaceMonitor.selectedPod = result.selected_pod
                if (!this.workspaceMonitor.selectedPod && this.workspaceMonitor.pods.length) {
                    this.workspaceMonitor.selectedPod = this.workspaceMonitor.pods[0].name
                }
                this.workspaceMonitor.error = result.error || ''
                this.renderMonitorCharts()
            } catch (e) {
                if (this.modalWorkspace && this.modalWorkspace.id === ws.id) {
                    this.workspaceMonitor.error = e.message || 'Failed to load monitor metrics'
                }
            } finally {
                if (this.modalWorkspace && this.modalWorkspace.id === ws.id) {
                    this.workspaceMonitor.loading = false
                }
            }
        },
        applySshModalFields(result) {
            if (!this.modalWorkspace || !result) return
            Object.keys(result).forEach((k) => {
                if (k === 'private_key' || k === 'sync') return
                this.$set(this.modalWorkspace, k, result[k])
            })
        },
        async loadWorkspaceSsh(ws) {
            const res = await fetch('workspaces/' + ws.id + '/ssh')
            if (res.status !== 200 || !this.modalWorkspace || this.modalWorkspace.id !== ws.id) return
            const data = await res.json()
            this.applySshModalFields(data.result || {})
        },
        applyTunnelInfo(result) {
            if (!result) return
            this.tunnelInfo = {
                enabled: !!result.enabled,
                ports: result.ports || [],
                ports_text: result.ports_text || '',
                wss_url: result.wss_url || '',
                path_prefix: result.path_prefix || 'port-tunnel',
                client_command: result.client_command || '',
                port_commands: result.port_commands || [],
                curl_example: result.curl_example || '',
            }
            if (result.ports_text !== undefined) {
                this.tunnelPortsText = result.ports_text
            }
        },
        async loadWorkspaceTunnel(ws) {
            const res = await fetch('workspaces/' + ws.id + '/tunnel')
            if (res.status !== 200 || !this.modalWorkspace || this.modalWorkspace.id !== ws.id) return
            const data = await res.json()
            this.applyTunnelInfo(data.result || {})
        },
        async exposeTunnelPorts(ws) {
            this.tunnelExposeLoading = true
            this.tunnelSyncMessage = ''
            this.tunnelSyncError = ''
            try {
                const res = await fetch('workspaces/' + ws.id + '/tunnel/expose', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ports_text: this.tunnelPortsText }),
                })
                const data = await res.json().catch(() => ({}))
                const result = data.result || {}
                this.applyTunnelInfo(result)
                const sync = result.sync || {}
                if (sync.message) this.tunnelSyncMessage = sync.message
                const syncErr = (sync.error || '').trim()
                    || (sync.ok === false ? (sync.helm_logs || '').trim() : '')
                if (syncErr) this.tunnelSyncError = syncErr
                if (res.status !== 200) {
                    this.showToast(data.message || syncErr || 'Expose failed')
                    return
                }
                this.showToast(data.message || (this.tunnelInfo.enabled ? 'Ports exposed' : 'Tunnel cleared'))
                await this.refreshLists()
            } catch (e) {
                this.showToast(e.message || 'Expose failed')
            } finally {
                this.tunnelExposeLoading = false
            }
        },
        async generateSshKeys(ws) {
            this.sshGenerateLoading = true
            this.sshPrivateKeyOnce = ''
            this.sshSyncMessage = ''
            this.sshSyncError = ''
            try {
                const res = await fetch('workspaces/' + ws.id + '/ssh/generate', { method: 'POST' })
                const data = await res.json().catch(() => ({}))
                const result = data.result || {}
                this.applySshModalFields(result)
                if (result.private_key) this.sshPrivateKeyOnce = result.private_key

                const sync = result.sync || {}
                if (sync.message) this.sshSyncMessage = sync.message
                const syncErr = (sync.error || '').trim()
                    || (sync.ok === false ? (sync.helm_logs || sync.apply_logs || '').trim() : '')
                if (syncErr) this.sshSyncError = syncErr

                if (res.status !== 200 || !result.has_key) {
                    this.showToast(data.message || syncErr || 'SSH key generation failed')
                    return
                }
                this.showToast(
                    sync.message
                    || (sync.ok === false ? (data.message || 'Keys saved — check sync status below') : 'SSH keys ready — save the private key')
                )
                await this.refreshLists()
            } catch (e) {
                this.showToast(e.message || 'SSH key generation failed')
            } finally {
                this.sshGenerateLoading = false
            }
        },
        downloadSshKey(ws) {
            window.location = 'workspaces/' + ws.id + '/ssh/download'
        },
        downloadMonitorFile(ws) {
            if (!ws) return
            const params = new URLSearchParams()
            if (this.workspaceMonitor.selectedPod) params.set('pod', this.workspaceMonitor.selectedPod)
            const qs = params.toString()
            window.location = 'workspaces/' + ws.id + '/monitor/download' + (qs ? '?' + qs : '')
        },
        markBackupFormDirty() {
            this.workspaceBackup.formDirty = true
        },
        applyBackupStatus(result) {
            if (!result) return
            this.workspaceBackup.enabled = !!result.enabled
            this.workspaceBackup.hasConfig = !!result.has_config
            if (result.status) {
                this.workspaceBackup.status = { ...this.workspaceBackup.status, ...result.status }
            }
        },
        applyBackupForm(result) {
            if (!result) return
            this.workspaceBackup.schedule = result.schedule || ''
            this.workspaceBackup.remote = result.remote || ''
            this.workspaceBackup.folders = Array.isArray(result.folders) ? [...result.folders] : []
            this.workspaceBackup.volumeOptions = Array.isArray(result.volume_options)
                ? result.volume_options.map((v) => ({ ...v }))
                : []
            if (result.rclone_config !== undefined) {
                this.workspaceBackup.rcloneConfig = result.rclone_config || ''
            }
        },
        applyBackupInfo(result, { updateForm = true, forceForm = false } = {}) {
            if (!result) return
            if (updateForm && (forceForm || !this.workspaceBackup.formDirty)) {
                this.applyBackupForm(result)
            }
            this.applyBackupStatus(result)
        },
        async saveRcloneConfig(ws) {
            if (!ws) return
            this.workspaceBackup.rcloneSaveLoading = true
            try {
                const res = await fetch('workspaces/' + ws.id + '/backup/rclone/save', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        rclone_config: this.workspaceBackup.rcloneConfig,
                        remote: this.workspaceBackup.remote,
                        schedule: this.workspaceBackup.schedule,
                        folders: this.workspaceBackup.folders,
                    }),
                })
                const data = await res.json().catch(() => ({}))
                if (res.status !== 200) {
                    this.showToast(data.message || 'Failed to save config')
                    return
                }
                this.applyBackupInfo(data.result || {}, { updateForm: true, forceForm: true })
                this.workspaceBackup.formDirty = false
                this.showToast(data.message || 'Backup settings saved')
            } catch (e) {
                this.showToast(e.message || 'Failed to save config')
            } finally {
                this.workspaceBackup.rcloneSaveLoading = false
            }
        },
        downloadRcloneConfig(ws) {
            if (!ws) return
            window.location = 'workspaces/' + ws.id + '/backup/rclone/download'
        },
        async loadWorkspaceBackup(ws) {
            const target = ws || this.modalWorkspace
            if (!target) return
            const res = await fetch('workspaces/' + target.id + '/backup')
            if (res.status !== 200 || !this.modalWorkspace || this.modalWorkspace.id !== target.id) return
            const data = await res.json()
            this.applyBackupInfo(data.result || {})
        },
        normalizeBackupMountPath(path) {
            const text = (path || '').trim()
            if (!text) return '/'
            return text.replace(/\/+$/, '') || '/'
        },
        backupVolumeOptionsList() {
            if (this.workspaceBackup.volumeOptions.length) {
                return this.workspaceBackup.volumeOptions
            }
            const mounts = this.modalWorkspace?.drive_mounts || []
            return mounts.map((m) => ({
                drive_id: m.drive_id,
                drive_name: m.drive_name,
                claim_name: m.claim_name,
                mount_path: m.mount_path,
                sub_path: m.sub_path || '',
            }))
        },
        isBackupMountSelected(mountPath) {
            const norm = this.normalizeBackupMountPath(mountPath)
            return this.workspaceBackup.folders.some(
                (f) => this.normalizeBackupMountPath(f) === norm,
            )
        },
        toggleBackupMount(vol) {
            if (!vol || !vol.mount_path) return
            const norm = this.normalizeBackupMountPath(vol.mount_path)
            const idx = this.workspaceBackup.folders.findIndex(
                (f) => this.normalizeBackupMountPath(f) === norm,
            )
            if (idx >= 0) {
                this.workspaceBackup.folders.splice(idx, 1)
            } else {
                this.workspaceBackup.folders.push(vol.mount_path)
            }
            this.markBackupFormDirty()
        },
        startWorkspaceBackupPoll() {
            this.stopWorkspaceBackupPoll()
            this.workspaceBackupTimer = setInterval(() => {
                if (this.modalTab === 'backup' && this.modalWorkspace) {
                    this.fetchWorkspaceBackup(true)
                }
            }, 1000)
        },
        stopWorkspaceBackupPoll() {
            if (this.workspaceBackupTimer) {
                clearInterval(this.workspaceBackupTimer)
                this.workspaceBackupTimer = null
            }
        },
        async fetchWorkspaceBackup(silent) {
            if (!this.modalWorkspace) return
            if (!silent) this.workspaceBackup.loading = true
            const ws = this.modalWorkspace
            try {
                const res = await fetch('workspaces/' + ws.id + '/backup')
                if (!this.modalWorkspace || this.modalWorkspace.id !== ws.id) return
                const data = await res.json().catch(() => ({}))
                if (res.status !== 200) {
                    this.workspaceBackup.error = data.message || 'Failed to load backup status'
                    return
                }
                const result = data.result || {}
                if (silent) {
                    this.applyBackupStatus(result)
                } else {
                    this.applyBackupInfo(result, { updateForm: true })
                }
                this.workspaceBackup.error = ''
            } catch (e) {
                if (this.modalWorkspace && this.modalWorkspace.id === ws.id) {
                    this.workspaceBackup.error = e.message || 'Failed to load backup status'
                }
            } finally {
                if (this.modalWorkspace && this.modalWorkspace.id === ws.id) {
                    this.workspaceBackup.loading = false
                }
            }
        },
        async scheduleWorkspaceBackup(ws) {
            this.workspaceBackup.scheduleLoading = true
            this.workspaceBackup.syncMessage = ''
            this.workspaceBackup.syncError = ''
            try {
                const res = await fetch('workspaces/' + ws.id + '/backup/schedule', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        schedule: this.workspaceBackup.schedule,
                        remote: this.workspaceBackup.remote,
                        folders: this.workspaceBackup.folders,
                        rclone_config: this.workspaceBackup.rcloneConfig,
                    }),
                })
                const data = await res.json().catch(() => ({}))
                const result = data.result || {}
                this.applyBackupInfo(result, { updateForm: true, forceForm: true })
                this.workspaceBackup.formDirty = false
                const sync = result.sync || {}
                if (sync.message) this.workspaceBackup.syncMessage = sync.message
                const syncErr = (sync.error || '').trim()
                    || (sync.ok === false ? (sync.helm_logs || '').trim() : '')
                if (syncErr) this.workspaceBackup.syncError = syncErr
                if (res.status !== 200) {
                    this.showToast(data.message || syncErr || 'Schedule failed')
                    return
                }
                this.showToast(data.message || 'Backup scheduled')
                await this.refreshLists()
            } catch (e) {
                this.showToast(e.message || 'Schedule failed')
            } finally {
                this.workspaceBackup.scheduleLoading = false
            }
        },
        async runWorkspaceBackup(ws) {
            this.workspaceBackup.runLoading = true
            try {
                const res = await fetch('workspaces/' + ws.id + '/backup/run', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        remote: this.workspaceBackup.remote,
                        folders: this.workspaceBackup.folders,
                        rclone_config: this.workspaceBackup.rcloneConfig,
                    }),
                })
                const data = await res.json().catch(() => ({}))
                const result = data.result || {}
                this.applyBackupInfo(result, { updateForm: true, forceForm: true })
                if (res.status !== 200) {
                    this.showToast(data.message || 'Backup failed to start')
                    return
                }
                this.workspaceBackup.status.running = true
                this.workspaceBackup.status.last_success = null
                this.workspaceBackup.status.last_message = 'Backup started'
                this.workspaceBackup.status.trigger = 'manual'
                this.showToast(data.message || 'Backup started')
                await this.fetchWorkspaceBackup(true)
            } catch (e) {
                this.showToast(e.message || 'Backup failed to start')
            } finally {
                this.workspaceBackup.runLoading = false
            }
        },
        async stopWorkspaceBackup(ws) {
            this.workspaceBackup.stopLoading = true
            this.workspaceBackup.syncMessage = ''
            this.workspaceBackup.syncError = ''
            try {
                const res = await fetch('workspaces/' + ws.id + '/backup/stop', { method: 'POST' })
                const data = await res.json().catch(() => ({}))
                const result = data.result || {}
                this.applyBackupInfo(result, { updateForm: true, forceForm: true })
                this.workspaceBackup.formDirty = false
                const sync = result.sync || {}
                if (sync.message) this.workspaceBackup.syncMessage = sync.message
                const syncErr = (sync.error || '').trim()
                    || (sync.ok === false ? (sync.helm_logs || '').trim() : '')
                if (syncErr) this.workspaceBackup.syncError = syncErr
                if (res.status !== 200) {
                    this.showToast(data.message || syncErr || 'Failed to stop backup')
                    return
                }
                this.showToast(data.message || 'Backup stopped')
                await this.refreshLists()
            } catch (e) {
                this.showToast(e.message || 'Failed to stop backup')
            } finally {
                this.workspaceBackup.stopLoading = false
            }
        },
        formatBackupTime(iso) {
            if (!iso) return '—'
            const d = new Date(iso)
            if (Number.isNaN(d.getTime())) return iso
            return d.toLocaleString()
        },
        async copyText(text, msg) {
            if (!text) return
            try {
                await navigator.clipboard.writeText(text)
                this.showToast(msg || 'Copied')
            } catch {
                this.showToast('Copy failed')
            }
        },
        openDeleteModal(ws, isAdmin) {
            this.deleteModalWorkspace = ws
            this.deleteModalIsAdmin = !!isAdmin
            this.deleteConfirmInput = ''
            this.deleteInProgress = false
        },
        closeDeleteModal() {
            this.deleteModalWorkspace = null
            this.deleteConfirmInput = ''
            this.deleteInProgress = false
        },
        async confirmDeleteWorkspace() {
            if (!this.canConfirmDelete || !this.deleteModalWorkspace) return
            const ws = this.deleteModalWorkspace
            this.deleteInProgress = true
            try {
                const res = await fetch('workspaces/' + ws.id, { method: 'DELETE' })
                if (res.status !== 200) {
                    this.showToast('Delete failed')
                    return
                }
                if (this.modalWorkspace && this.modalWorkspace.id === ws.id) {
                    this.closeWorkspaceModal()
                }
                this.closeDeleteModal()
                this.showToast('Server deleted')
                await this.reloadServerLists()
            } finally {
                this.deleteInProgress = false
            }
        },
        exportModalConfig() {
            if (!this.modalWorkspace) return
            downloadJson(this.modalWorkspace, 'dohub-' + this.modalWorkspace.slug + '-config.json')
        },
        async changeMenu(menu) {
            this.stopStatusPolling()
            this.menu = menu
            this.mobileNavOpen = false
            window.history.replaceState({}, '', '/?tab=' + menu)
            if (menu === 'drives') await this.reloadMyDrives(1)
            if (menu === 'servers') await this.reloadMyWorkspaces(1)
            if (menu === 'images') await this.reloadMyImages(1)
            if (menu === 'admin-overall') {
                await this.loadClusterOverview()
                await this.loadDirectpvDiscover()
            }
            if (menu === 'admin-drives') {
                if (this.adminDrivesTab === 'catalog') await this.loadAdminPlatformCatalog()
                else {
                    await this.loadResourceGroups()
                    await this.reloadAdminDrives(1)
                }
            }
            if (menu === 'admin-servers') {
                if (this.adminServersTab === 'catalog') await this.loadAdminPlatformCatalog()
                else {
                    await this.loadResourceGroups()
                    await this.reloadAdminWorkspaces(1)
                }
            }
            if (menu === 'admin-users') {
                await this.loadResourceGroups()
                if (this.adminUsersTab === 'groups') await this.loadResourceGroups()
                else await this.loadAdminUsers(1)
            }
            if (menu === 'admin-images') await this.reloadAdminDockerImages(1)
            if (['drives', 'servers', 'admin-drives', 'admin-servers', 'admin-overall'].includes(menu)) {
                this.startStatusPolling()
            }
        },
        async init() {
            if (!this.is_login) return
            await this.getCurrentUserState()
            if (this.is_admin) {
                // Needed for admin filters (users/drives/servers) on first load.
                await this.loadResourceGroups()
            }
            await this.loadPlatformCatalog()
            await this.loadDockerImages()
            await this.loadListsThenPoll(async () => {
                await this.loadMyDrives(1)
                await this.loadMyDrivesAll()
                await this.loadMyWorkspaces(1)
                if (this.is_admin) {
                    if (this.menu === 'admin-drives' && this.adminDrivesTab !== 'catalog') {
                        await this.loadAdminDrives(1)
                    }
                    if (this.menu === 'admin-servers' && this.adminServersTab !== 'catalog') {
                        await this.loadAdminWorkspaces(1)
                    }
                }
            }, () => this.pollStatuses(), () => this.statusPendingKeysForMenu())
            if (this.menu === 'images') await this.reloadMyImages(1)
            if (this.is_admin) {
                if (this.menu === 'admin-users') {
                    if (this.adminUsersTab === 'groups') await this.loadResourceGroups()
                    else await this.loadAdminUsers(1)
                }
                await this.loadAdminDockerImages(this.adminImagePagination.page)
            }
            if (this.menu === 'admin-overall') {
                await this.loadClusterOverview()
                await this.loadDirectpvDiscover()
            }
            if (['drives', 'servers', 'admin-drives', 'admin-servers', 'admin-overall'].includes(this.menu)) {
                this.startStatusPolling()
            }
        },
        async loadClusterOverview() {
            this.clusterLoading = true
            try {
                const res = await fetch('admin/cluster/overview')
                if (res.status !== 200) return
                const data = await res.json()
                this.clusterOverview = data.result || null
            } finally {
                this.clusterLoading = false
            }
        },
        formatDriveBytes(bytes) {
            const n = Number(bytes)
            if (!n || Number.isNaN(n)) return '—'
            const units = ['B', 'KiB', 'MiB', 'GiB', 'TiB']
            let size = n
            let unit = 0
            while (size >= 1024 && unit < units.length - 1) {
                size /= 1024
                unit += 1
            }
            return (unit === 0 ? size : size.toFixed(1)) + ' ' + units[unit]
        },
        async loadDirectpvDiscover() {
            const res = await fetch('admin/cluster/directpv/discover')
            if (res.status !== 200) return
            const data = await res.json()
            const result = data.result || {}
            this.directpvDiscoverPath = result.path || ''
            if (!result.ok) {
                this.directpvDiscoverError = result.error || 'Failed to load discover file'
                this.directpvDiscover = null
                return
            }
            this.directpvDiscoverError = ''
            this.directpvDiscover = result.data || null
        },
        async runDirectpvDiscover() {
            this.directpvDiscoverLoading = true
            this.directpvDiscoverError = ''
            this.directpvDiscoverMessage = ''
            this.directpvDiscoverRaw = ''
            try {
                const res = await fetch('admin/cluster/directpv/discover/run', { method: 'POST' })
                const data = await res.json().catch(() => ({}))
                const result = data.result || {}
                this.directpvDiscoverRaw = result.raw || ''
                this.directpvDiscoverPath = result.path || this.directpvDiscoverPath
                if (!result.ok) {
                    this.directpvDiscoverError = result.error || data.message || 'Discover failed'
                    return
                }
                this.directpvDiscover = result.data || null
                this.directpvDiscoverMessage = result.message || (result.data ? 'Drives discovered' : 'No drives discovered')
                this.showToast(this.directpvDiscoverMessage)
            } catch (e) {
                this.directpvDiscoverError = e.message || String(e)
            } finally {
                this.directpvDiscoverLoading = false
            }
        },
        async toggleDirectpvDriveSelect(nodeIndex, driveIndex) {
            if (!this.directpvDiscover || !this.directpvDiscover.nodes) return
            const node = this.directpvDiscover.nodes[nodeIndex]
            const drive = node && node.drives && node.drives[driveIndex]
            if (!drive) return
            const prev = drive.select === 'yes' ? 'yes' : 'no'
            const next = prev === 'yes' ? 'no' : 'yes'
            this.$set(drive, 'select', next)
            this.directpvDiscoverSaving = true
            this.directpvDiscoverError = ''
            try {
                const res = await fetch('admin/cluster/directpv/discover/save', {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ data: this.directpvDiscover }),
                })
                const data = await res.json().catch(() => ({}))
                const result = data.result || {}
                if (!result.ok) {
                    this.directpvDiscoverError = result.error || data.message || 'Save failed'
                    this.$set(drive, 'select', prev)
                    this.showToast(this.directpvDiscoverError)
                    return
                }
                if (result.data) this.directpvDiscover = result.data
            } catch (e) {
                this.$set(drive, 'select', prev)
                this.directpvDiscoverError = e.message || String(e)
                this.showToast(this.directpvDiscoverError)
            } finally {
                this.directpvDiscoverSaving = false
            }
        },
        openDirectpvInitConfirm() {
            if (!this.directpvDiscover || !this.directpvDiscoverSelectedCount) {
                this.showToast('Select at least one drive to init')
                return
            }
            this.showDirectpvInitConfirm = true
            this.directpvInitError = ''
            this.directpvInitResult = ''
        },
        closeDirectpvInitConfirm() {
            this.showDirectpvInitConfirm = false
        },
        async confirmDirectpvInit() {
            this.directpvInitLoading = true
            this.directpvInitError = ''
            this.directpvInitResult = ''
            try {
                const res = await fetch('admin/cluster/directpv/init', { method: 'POST' })
                const data = await res.json().catch(() => ({}))
                const result = data.result || {}
                this.directpvInitResult = result.raw || result.message || ''
                if (!result.ok) {
                    this.directpvInitError = result.error || data.message || 'Init failed'
                    this.showToast(this.directpvInitError)
                    return
                }
                this.showDirectpvInitConfirm = false
                this.showToast(result.message || 'DirectPV init completed')
                await this.loadClusterOverview()
            } catch (e) {
                this.directpvInitError = e.message || String(e)
                this.showToast(this.directpvInitError)
            } finally {
                this.directpvInitLoading = false
            }
        },
        async fetchJoinCommand() {
            this.joinCommandLoading = true
            this.joinCommandError = ''
            this.joinCommand = ''
            this.joinCommandRaw = ''
            try {
                const res = await fetch('admin/cluster/join-command', { method: 'POST' })
                const data = await res.json().catch(() => ({}))
                const result = data.result || {}
                this.joinCommandRaw = result.raw || ''
                if (result.ok && result.command) {
                    this.joinCommand = result.command
                } else {
                    this.joinCommandError = result.error || data.message || 'Could not get join command'
                    if (this.joinCommandRaw) this.joinCommandError += ' (see output below)'
                }
            } catch (e) {
                this.joinCommandError = e.message || String(e)
            } finally {
                this.joinCommandLoading = false
            }
        },
        async copyJoinCommand() {
            if (!this.joinCommand) return
            try {
                await navigator.clipboard.writeText(this.joinCommand)
                this.showToast('Join command copied')
            } catch {
                this.showToast('Copy failed')
            }
        },
        async getCurrentUserState() {
            const res = await fetch('user_state')
            if (res.status !== 200) return
            const data = await res.json()
            const u = data.result
            this.current_user = u.username
            this.is_admin = u.role === 'admin'
            this.resourceLimits = u.resource_limits || { limited: false, limits: null, equipment: null, can_change_privileged: false }
            this.refreshEquipmentFromLimits()
        },
        applyPlatformCatalog(catalog) {
            if (!catalog) return
            const eq = catalog.equipment || {}
            this.fullEquipmentList = {
                cpu: eq.cpu || [],
                ram: eq.ram || [],
                gpu: eq.gpu || [],
                drive_sizes: eq.drive_sizes || [],
            }
            this.planTemplates = catalog.templates || []
            this.refreshEquipmentFromLimits()
        },
        refreshEquipmentFromLimits() {
            const base = this.fullEquipmentList
            if (!this.resourceLimits.limited) {
                this.equipmentList = { cpu: base.cpu || [], ram: base.ram || [], gpu: base.gpu || [] }
                this.driveSizeOptions = base.drive_sizes || []
            } else {
                const eq = this.resourceLimits.equipment || {}
                this.equipmentList = {
                    cpu: eq.cpu || base.cpu || [],
                    ram: eq.ram || base.ram || [],
                    gpu: eq.gpu || base.gpu || [],
                }
                this.driveSizeOptions = eq.drive_sizes || base.drive_sizes || []
            }
            this.clampFormToLimits()
            if (this.driveSizeOptions.length && !this.driveSizeOptions.includes(this.newDrive.size)) {
                this.newDrive.size = this.driveSizeOptions[0]
            }
        },
        async loadPlatformCatalog() {
            const res = await fetch('platform/catalog')
            if (res.status !== 200) return
            const data = await res.json()
            this.applyPlatformCatalog(data.result)
        },
        async loadAdminPlatformCatalog() {
            if (!this.is_admin) return
            const res = await fetch('admin/platform/catalog')
            if (res.status !== 200) return
            const data = await res.json()
            const result = data.result || {}
            this.adminCatalogOptions = result.options || []
            this.adminPlanTemplates = result.templates || []
            this.applyPlatformCatalog(result)
        },
        catalogOptionsFor(category) {
            return (this.adminCatalogOptions || [])
                .filter((o) => o.category === category)
                .sort((a, b) => a.sort_order - b.sort_order || a.value.localeCompare(b.value))
        },
        async addCatalogOption() {
            const payload = { ...this.newCatalogOption }
            if (!payload.value || !String(payload.value).trim()) {
                this.showToast('Value required')
                return
            }
            const res = await fetch('admin/platform/options', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            })
            const data = await res.json().catch(() => ({}))
            if (res.status !== 201) {
                this.showToast(data.message || 'Add failed')
                return
            }
            this.newCatalogOption.value = ''
            this.newCatalogOption.vram_g = 0
            await this.loadAdminPlatformCatalog()
            this.showToast('Option added')
        },
        async deleteCatalogOption(option) {
            this.openDeleteYesNoModal({
                kind: 'catalog_option',
                item: option,
                title: 'Delete catalog option',
                description: 'Remove option "' + option.value + '" from the platform catalog?',
            })
        },
        async _executeDeleteCatalogOption(option) {
            const res = await fetch('admin/platform/options/' + option.id, { method: 'DELETE' })
            if (res.status !== 200) {
                this.showToast('Delete failed')
                return false
            }
            await this.loadAdminPlatformCatalog()
            this.showToast('Option deleted')
            return true
        },
        async toggleCatalogOption(option) {
            const res = await fetch('admin/platform/options/' + option.id, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ is_active: !option.is_active }),
            })
            if (res.status !== 200) {
                this.showToast('Update failed')
                return
            }
            await this.loadAdminPlatformCatalog()
        },
        async savePlanTemplate() {
            const built = planTemplatePayloadFromForm(this.newPlanTemplate)
            if (built.error) {
                this.showToast(built.error)
                return
            }
            const res = await fetch('admin/platform/templates', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(built.payload),
            })
            const data = await res.json().catch(() => ({}))
            if (res.status !== 201) {
                this.showToast(data.message || 'Save failed')
                return
            }
            this.newPlanTemplate = defaultPlanTemplateForm()
            await this.loadAdminPlatformCatalog()
            await this.loadPlatformCatalog()
            this.showToast('Template added')
        },
        openEditPlanTemplateModal(template) {
            this.editingPlanTemplate = template
            this.planTemplateForm = {
                name: template.name,
                image: template.image,
                cpu: template.cpu,
                ram: template.ram,
                gpu: template.gpu || 'none',
                docker_repository: template.docker_repository || '',
                docker_tag: template.docker_tag || '',
                ports_text: (template.exposed_ports || [8080]).join(', '),
                command_text: formatCommand(template.container_command || []),
                drive_mounts_text: formatPlanTemplateDriveMountsText(template.drive_mounts),
                env_defaults_text: JSON.stringify(template.env_defaults || {}, null, 2),
                sort_order: template.sort_order || 0,
                is_active: template.is_active !== false,
            }
            this.showPlanTemplateModal = true
        },
        closePlanTemplateModal() {
            this.showPlanTemplateModal = false
            this.editingPlanTemplate = null
            this.planTemplateForm = defaultPlanTemplateForm()
        },
        async savePlanTemplateModal() {
            if (!this.editingPlanTemplate) return
            const built = planTemplatePayloadFromForm(this.planTemplateForm)
            if (built.error) {
                this.showToast(built.error)
                return
            }
            if (!(built.payload.name || '').trim()) {
                this.showToast('Name required')
                return
            }
            this.planTemplateFormLoading = true
            try {
                const res = await fetch('admin/platform/templates/' + this.editingPlanTemplate.id, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(built.payload),
                })
                const data = await res.json().catch(() => ({}))
                if (res.status !== 200) {
                    this.showToast(data.message || 'Save failed')
                    return
                }
                this.closePlanTemplateModal()
                await this.loadAdminPlatformCatalog()
                await this.loadPlatformCatalog()
                this.showToast('Template updated')
            } finally {
                this.planTemplateFormLoading = false
            }
        },
        async deletePlanTemplate(template) {
            this.openDeleteYesNoModal({
                kind: 'plan_template',
                item: template,
                title: 'Delete quick template',
                description: 'Remove template "' + template.name + '" from the catalog?',
            })
        },
        async _executeDeletePlanTemplate(template) {
            const res = await fetch('admin/platform/templates/' + template.id, { method: 'DELETE' })
            if (res.status !== 200) {
                this.showToast('Delete failed')
                return false
            }
            await this.loadAdminPlatformCatalog()
            await this.loadPlatformCatalog()
            this.showToast('Template deleted')
            return true
        },
        async togglePlanTemplate(template) {
            const res = await fetch('admin/platform/templates/' + template.id, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ is_active: !template.is_active }),
            })
            if (res.status !== 200) {
                this.showToast('Update failed')
                return
            }
            await this.loadAdminPlatformCatalog()
            await this.loadPlatformCatalog()
        },
        downloadPlanTemplatesJson() {
            window.location = 'admin/platform/templates/export'
        },
        openPlanTemplateBulkModal() {
            this.showPlanTemplateBulkModal = true
            this.planTemplateBulkMode = 'json'
            this.planTemplateBulkText = ''
            this.planTemplateBulkFileName = ''
            this.planTemplateBulkSummary = ''
        },
        closePlanTemplateBulkModal() {
            this.showPlanTemplateBulkModal = false
            this.planTemplateBulkLoading = false
        },
        onPlanTemplateBulkFileSelected(event) {
            const file = event && event.target && event.target.files && event.target.files[0]
            if (!file) return
            this.planTemplateBulkFileName = file.name || ''
            const reader = new FileReader()
            reader.onload = () => {
                this.planTemplateBulkText = String(reader.result || '')
            }
            reader.readAsText(file)
        },
        parsePlanTemplatesBulk() {
            const text = (this.planTemplateBulkText || '').trim()
            if (!text) return { error: 'paste JSON/CSV or upload a file' }
            if (this.planTemplateBulkMode === 'json') {
                try {
                    const parsed = JSON.parse(text)
                    const items = Array.isArray(parsed) ? parsed : (parsed.items || parsed.templates || parsed.result || [])
                    if (!Array.isArray(items)) return { error: 'JSON must be an array of templates (or {items:[...]})' }
                    return { items }
                } catch {
                    return { error: 'invalid JSON' }
                }
            }
            try {
                const items = parseCsvRows(text, (row) => ({
                    id: row.id || row.template_id || '',
                    name: row.name || '',
                    cpu: row.cpu || 2,
                    ram: row.ram || '4G',
                    gpu: row.gpu || 'none',
                    image: row.image || 'logo.png',
                    docker_repository: row.docker_repository || row.repository || '',
                    docker_tag: row.docker_tag || row.tag || '',
                    exposed_ports: row.exposed_ports || row.ports_text || row.ports || '8080',
                    command_text: row.command_text || row.command || '',
                    drive_mounts_text: row.drive_mounts_text || row.drive_mounts || '',
                    env_defaults: row.env_defaults || row.env_defaults_text || '{}',
                    is_active: (row.is_active || 'true').toString().toLowerCase() !== 'false',
                    sort_order: row.sort_order || 0,
                }))
                return { items }
            } catch (e) {
                return { error: e.message || 'invalid CSV' }
            }
        },
        async importPlanTemplatesBulk() {
            const built = this.parsePlanTemplatesBulk()
            if (built.error) {
                this.planTemplateBulkSummary = built.error
                return
            }
            this.planTemplateBulkLoading = true
            this.planTemplateBulkSummary = ''
            try {
                const res = await fetch('admin/platform/templates/import', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ items: built.items }),
                })
                const data = await res.json().catch(() => ({}))
                const failed = (data.results || []).filter((r) => !r.ok)
                this.planTemplateBulkSummary = `Imported: ${data.ok || 0} ok, ${data.failed || failed.length} failed`
                if (failed.length) {
                    this.planTemplateBulkSummary += '\n' + failed.map((r) => (r.name || '?') + ': ' + (r.error || 'failed')).join('\n')
                }
                await this.loadAdminPlatformCatalog()
                await this.loadPlatformCatalog()
            } finally {
                this.planTemplateBulkLoading = false
            }
        },
        clampFormToLimits() {
            const eq = this.resourceLimits.equipment
            if (!eq) return
            if (!cpuListIncludes(eq.cpu, this.form.cpu)) {
                this.form.cpu = eq.cpu[eq.cpu.length - 1] || this.form.cpu
            }
            if (!eq.ram.includes(this.form.ram)) {
                this.form.ram = eq.ram[eq.ram.length - 1] || this.form.ram
            }
            if (!eq.gpu.includes(this.form.gpu)) {
                this.form.gpu = eq.gpu[0] || 'none'
            }
        },
        checkWorkspaceLimits(cpu, ram, gpu) {
            if (!this.resourceLimits.limited) return null
            const eq = this.resourceLimits.equipment || {}
            const gpuVal = normalizeGpuValue(gpu)
            if (eq.cpu && !cpuListIncludes(eq.cpu, cpu)) {
                return `CPU exceeds group limit (${this.resourceLimits.limits.max_cpu} vCPU)`
            }
            if (eq.ram && !eq.ram.includes(ram)) {
                return `RAM exceeds group limit (${this.resourceLimits.limits.max_ram_g}G)`
            }
            if (eq.gpu && !eq.gpu.includes(gpuVal)) {
                return `GPU exceeds group VRAM limit (${this.resourceLimits.limits.max_gpu_vram_g}G)`
            }
            return null
        },
        checkDriveSizeLimit(size) {
            if (!this.resourceLimits.limited) return null
            const sizes = (this.resourceLimits.equipment || {}).drive_sizes || []
            if (!sizes.includes(size)) {
                return `Drive size exceeds group limit (${this.resourceLimits.limits.max_drive_size_gi}Gi)`
            }
            return null
        },
        checkServerCountLimit() {
            if (!this.resourceLimits.limited || !this.resourceLimits.limits) return null
            const l = this.resourceLimits.limits
            if (!l.max_servers) return null
            const count = l.server_count ?? this.myServerPagination.total ?? this.myWorkspaces.length
            if (count >= l.max_servers) {
                return `Server count exceeds group limit (${l.max_servers} max, you have ${count})`
            }
            return null
        },
        checkDriveCountLimit() {
            if (!this.resourceLimits.limited || !this.resourceLimits.limits) return null
            const l = this.resourceLimits.limits
            if (!l.max_drives) return null
            const count = l.drive_count ?? this.myDrivePagination.total ?? this.myDrives.length
            if (count >= l.max_drives) {
                return `Drive count exceeds group limit (${l.max_drives} max, you have ${count})`
            }
            return null
        },
        checkImageCountLimit() {
            if (!this.resourceLimits.limited || !this.resourceLimits.limits) return null
            const l = this.resourceLimits.limits
            if (!l.max_images) return null
            const count = l.image_count ?? this.myImagePagination.total ?? this.myDockerImages.length
            if (count >= l.max_images) {
                return `Image count exceeds group limit (${l.max_images} max, you have ${count})`
            }
            return null
        },
        syncResourceUsageCounts() {
            if (!this.resourceLimits.limits) return
            this.resourceLimits.limits.server_count = this.myServerPagination.total ?? this.myWorkspaces.length
            this.resourceLimits.limits.drive_count = this.myDrivePagination.total ?? this.myDrives.length
            this.resourceLimits.limits.image_count = this.myImagePagination.total ?? this.myDockerImages.length
        },
        async loadDockerImages() {
            const res = await fetch('docker_images')
            if (res.status !== 200) return
            const data = await res.json()
            this.dockerImages = data.result || []
            if (this.dockerImages.length && !this.form.docker_image_id) {
                const first = this.dockerImages[0]
                this.form.docker_image_id = first.id
                this.form.docker_repository = first.repository
                const tags = (first.tags && first.tags.length) ? first.tags : [first.default_tag || 'latest']
                this.form.docker_tag = tags.includes(first.default_tag) ? first.default_tag : tags[0]
            }
        },
        async loadMyDockerImages(page) {
            this.clearBulkSelection('images')
            const q = new URLSearchParams({
                page: page || this.myImagePagination.page || 1,
                per_page: 12,
            })
            if (this.myImageFilter) q.set('name', this.myImageFilter)
            const res = await fetch('docker_images/mine?' + q)
            if (res.status !== 200) return
            const data = await res.json()
            this.myDockerImages = data.result || []
            this.myImagePagination = data.pagination || this.myImagePagination
            this.syncResourceUsageCounts()
        },
        async reloadMyImages(page) {
            await this.loadMyDockerImages(page || 1)
        },
        async createUserDockerImage() {
            const limitErr = this.checkImageCountLimit()
            if (limitErr) {
                this.showToast(limitErr)
                return
            }
            const tags = String(this.newUserImage.tags_text || '')
                .split(/[,;\s]+/)
                .map((t) => t.trim())
                .filter(Boolean)
            const res = await fetch('docker_images/create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    label: this.newUserImage.label,
                    repository: this.newUserImage.repository,
                    default_tag: this.newUserImage.default_tag || 'latest',
                    tags,
                }),
            })
            if (res.status !== 201) {
                const data = await res.json().catch(() => ({}))
                this.showToast(data.message || 'Failed to submit image')
                return
            }
            this.newUserImage = { label: '', repository: '', default_tag: 'latest', tags_text: '' }
            await this.reloadMyImages(this.myImagePagination.page)
            this.showToast('Image submitted — waiting for admin approval')
        },
        onDockerImageChange() {
            const img = this.dockerImages.find((i) => i.id === this.form.docker_image_id)
            if (img) {
                this.form.docker_repository = img.repository
                const tags = (img.tags && img.tags.length) ? img.tags : [img.default_tag || 'latest']
                this.form.docker_tag = tags.includes(img.default_tag) ? img.default_tag : tags[0]
            }
        },
        applyTemplate(t) {
            const gpu = normalizeGpuValue(t.gpu)
            const err = this.checkWorkspaceLimits(t.cpu, t.ram, gpu)
            if (err) {
                this.showToast(err)
                return
            }
            this.form.cpu = t.cpu
            this.form.ram = t.ram
            this.form.gpu = gpu
            this.form.name = t.name + ' workspace'
            this.applyTemplateDockerSettings(t)
            if (t.container_command && t.container_command.length) {
                this.form.command_text = formatCommand(t.container_command)
            } else {
                this.form.command_text = ''
            }
            const env = resolveTemplateEnv(t.env_defaults, this.current_user)
            this.form.env_vars = { ...this.form.env_vars, ...env }
            const firstKey = Object.keys(env)[0] || ''
            this.envKey = firstKey
            this.envValue = this.form.env_vars[firstKey] || ''
            if (t.drive_mounts && t.drive_mounts.length) {
                this.form.drive_mounts = t.drive_mounts.map((m) => ({
                    drive_id: '',
                    mount_path: m.mount_path || m.path || '/home/coder',
                }))
            } else {
                this.form.drive_mounts = []
            }
        },
        applyTemplateDockerSettings(t) {
            if (t.exposed_ports && t.exposed_ports.length) {
                this.form.ports_text = t.exposed_ports.join(', ')
            }
            const repository = (t.docker_repository || '').trim()
            if (!repository) return
            const img = this.dockerImages.find((i) => i.repository === repository)
            if (img) {
                this.form.docker_image_id = img.id
                this.form.docker_repository = img.repository
                const tags = (img.tags && img.tags.length) ? img.tags : [img.default_tag || 'latest']
                const wanted = (t.docker_tag || img.default_tag || tags[0] || 'latest').trim()
                this.form.docker_tag = tags.includes(wanted) ? wanted : tags[0]
                return
            }
            this.form.docker_image_id = ''
            this.form.docker_repository = repository
            this.form.docker_tag = (t.docker_tag || 'latest').trim()
        },
        templateSummaryLine(t) {
            const parts = [t.cpu + ' vCPU', t.gpu || 'no GPU']
            if (t.docker_repository) {
                parts.push(t.docker_repository + (t.docker_tag ? ':' + t.docker_tag : ''))
            }
            if (t.exposed_ports && t.exposed_ports.length) {
                parts.push('ports ' + t.exposed_ports.join(','))
            }
            if (t.container_command && t.container_command.length) {
                const cmd = formatCommand(t.container_command)
                parts.push('cmd ' + (cmd.length > 24 ? cmd.slice(0, 24) + '…' : cmd))
            }
            if (t.drive_mounts && t.drive_mounts.length) {
                const paths = t.drive_mounts
                    .map((m) => m.mount_path || m.path)
                    .filter(Boolean)
                    .join(', ')
                if (paths) parts.push('mounts ' + paths)
            }
            return parts.join(' · ')
        },
        addEnv() {
            const k = (this.envKey || '').trim()
            if (!k) return
            this.$set(this.form.env_vars, k, this.envValue || '')
        },
        editEnv(key) {
            this.envKey = key
            this.envValue = this.form.env_vars[key] || ''
        },
        removeEnv(key) {
            this.$delete(this.form.env_vars, key)
            if (this.envKey === key) {
                this.envKey = ''
                this.envValue = ''
            }
        },
        exportFormConfig() {
            downloadJson(formPayload(this.form), 'dohub-workspace-config.json')
        },
        onBulkFileSelected(event, target) {
            const kind = target || 'servers'
            const file = event.target.files && event.target.files[0]
            if (!file) return
            const ext = (file.name.split('.').pop() || '').toLowerCase()
            const modeKey = kind === 'drives' ? 'driveBulkMode' : 'bulkMode'
            const textKey = kind === 'drives' ? 'driveBulkText' : 'bulkText'
            const fileKey = kind === 'drives' ? 'driveBulkFileName' : 'bulkFileName'
            const summaryKey = kind === 'drives' ? 'driveBulkSummary' : 'bulkSummary'
            if (ext === 'csv') this[modeKey] = 'csv'
            else if (ext === 'json') this[modeKey] = 'json'
            else {
                this.showToast('Use .json or .csv file')
                event.target.value = ''
                return
            }
            const reader = new FileReader()
            reader.onload = (ev) => {
                this[textKey] = ev.target.result || ''
                this[fileKey] = file.name
                this[summaryKey] = ''
            }
            reader.onerror = () => this.showToast('Could not read file')
            reader.readAsText(file)
            event.target.value = ''
        },
        clearBulk() {
            this.bulkText = ''
            this.bulkFileName = ''
            this.bulkSummary = ''
        },
        clearDriveBulk() {
            this.driveBulkText = ''
            this.driveBulkFileName = ''
            this.driveBulkSummary = ''
        },
        parseBulkItems() {
            const text = (this.bulkText || '').trim()
            if (!text) throw new Error('Upload a file or paste JSON/CSV content')
            if (this.bulkMode === 'json') {
                const parsed = JSON.parse(text)
                const arr = Array.isArray(parsed) ? parsed : [parsed]
                return arr.map(normalizeBulkItem)
            }
            return parseCsvBulk(text)
        },
        async runBulkCreate() {
            this.bulkLoading = true
            this.bulkSummary = ''
            try {
                const items = this.parseBulkItems()
                const res = await fetch('workspaces/bulk_run', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ items, auto_start: this.bulkAutoStart }),
                })
                const data = await res.json().catch(() => ({}))
                if (res.status !== 200) {
                    this.bulkSummary = data.message || 'Bulk create failed'
                    this.showToast(data.message || 'Bulk create failed')
                    return
                }
                this.bulkSummary = formatBulkSummary(data, items.length)
                await this.reloadServerLists()
                this.showToast('Bulk server create finished')
            } catch (e) {
                this.bulkSummary = e.message || String(e)
            } finally {
                this.bulkLoading = false
            }
        },
        parseDriveBulkItems() {
            const text = (this.driveBulkText || '').trim()
            if (!text) throw new Error('Upload a file or paste JSON/CSV content')
            if (this.driveBulkMode === 'json') {
                const parsed = JSON.parse(text)
                const arr = Array.isArray(parsed) ? parsed : [parsed]
                return arr.map(normalizeDriveBulkItem)
            }
            return parseDriveCsvBulk(text)
        },
        async runDriveBulkCreate() {
            this.driveBulkLoading = true
            this.driveBulkSummary = ''
            try {
                const items = this.parseDriveBulkItems()
                const res = await fetch('drives/bulk_create', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ items }),
                })
                const data = await res.json().catch(() => ({}))
                if (res.status !== 200) {
                    this.driveBulkSummary = data.message || 'Bulk create failed'
                    this.showToast(data.message || 'Bulk create failed')
                    return
                }
                this.driveBulkSummary = formatBulkSummary(data, items.length)
                await this.reloadDriveLists()
                this.showToast('Bulk drive create finished')
            } catch (e) {
                this.driveBulkSummary = e.message || String(e)
            } finally {
                this.driveBulkLoading = false
            }
        },
        async loadMyDrives(page) {
            this.clearBulkSelection('drives')
            const q = new URLSearchParams({
                page: page || this.myDrivePagination.page || 1,
                per_page: 12,
                name: this.myDriveFilter,
            })
            const res = await fetch('drives?' + q)
            if (res.status !== 200) return
            const data = await res.json()
            this.myDrives = data.result || []
            this.myDrivePagination = data.pagination || this.myDrivePagination
            this.syncResourceUsageCounts()
        },
        async loadMyDrivesAll() {
            const q = new URLSearchParams({ page: 1, per_page: 500 })
            const res = await fetch('drives?' + q)
            if (res.status !== 200) return
            const data = await res.json()
            this.myDrivesAll = data.result || []
        },
        async loadAdminDrives(page) {
            this.clearBulkSelection('drives')
            const q = new URLSearchParams({ page: page || 1, per_page: 12, user: this.adminDriveFilter })
            if (this.adminDriveNameFilter) q.set('name', this.adminDriveNameFilter)
            if (this.adminDriveGroupFilter && this.adminDriveGroupFilter !== 'all') q.set('group', this.adminDriveGroupFilter)
            const res = await fetch('admin/drives?' + q)
            if (res.status !== 200) return
            const data = await res.json()
            this.adminDrives = data.result || []
            this.adminDrivePagination = data.pagination || this.adminDrivePagination
        },
        reloadAdminDrivesFilters() {
            this.reloadAdminDrives(1)
        },
        openCreateDriveModal() {
            this.mobileNavOpen = false
            const limitErr = this.checkDriveCountLimit()
            if (limitErr) {
                this.showToast(limitErr)
                return
            }
            this.showCreateDriveModal = true
        },
        closeCreateDriveModal() {
            this.showCreateDriveModal = false
        },
        openBulkCreateDriveModal() {
            const limitErr = this.checkDriveCountLimit()
            if (limitErr) {
                this.showToast(limitErr)
                return
            }
            this.showBulkCreateDriveModal = true
        },
        closeBulkCreateDriveModal() {
            this.showBulkCreateDriveModal = false
        },
        async createDrive() {
            const limitErr = this.checkDriveCountLimit() || this.checkDriveSizeLimit(this.newDrive.size)
            if (limitErr) {
                this.showToast(limitErr)
                return
            }
            this.driveCreateLoading = true
            const res = await fetch('drives/create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(this.newDrive),
            })
            this.driveCreateLoading = false
            if (res.status !== 201) {
                const data = await res.json().catch(() => ({}))
                this.showToast(data.message || 'Create failed')
                return
            }
            this.newDrive = { name: 'My drive', size: '20Gi' }
            await this.reloadDriveLists()
            this.closeCreateDriveModal()
            this.showToast('Drive created')
        },
        openDeleteDriveModal(d, isAdmin) {
            this.deleteModalDrive = d
            this.deleteModalDriveIsAdmin = !!isAdmin
            this.deleteDriveConfirmInput = ''
        },
        closeDeleteDriveModal() {
            this.deleteModalDrive = null
            this.deleteDriveConfirmInput = ''
        },
        async confirmDeleteDrive() {
            if (!this.canConfirmDeleteDrive || !this.deleteModalDrive) return
            const d = this.deleteModalDrive
            this.deleteDriveInProgress = true
            const res = await fetch('drives/' + d.id, { method: 'DELETE' })
            this.deleteDriveInProgress = false
            if (res.status !== 200) {
                const data = await res.json().catch(() => ({}))
                this.showToast(data.message || 'Delete failed')
                return
            }
            this.closeDeleteDriveModal()
            this.showToast('Drive deleted')
            await this.reloadDriveLists()
        },
        drivesForMountRow() {
            return this.myDrivesAll
        },
        suggestMountPath(rowIndex) {
            const defaults = ['/home/coder', '/app/data', '/app/logs', '/data']
            if (rowIndex < defaults.length) return defaults[rowIndex]
            return `/mnt/path${rowIndex + 1}`
        },
        addDriveMount() {
            if (!this.form.drive_mounts) this.$set(this.form, 'drive_mounts', [])
            const idx = this.form.drive_mounts.length
            const prev = this.form.drive_mounts[idx - 1]
            const mountPath = this.suggestMountPath(idx)
            this.form.drive_mounts.push({
                drive_id: prev && prev.drive_id ? prev.drive_id : '',
                mount_path: mountPath,
            })
        },
        driveMountSummary(m) {
            if (!m || !m.drive_id) return '—'
            const d = this.myDrivesAll.find((x) => x.id === m.drive_id)
            const name = d ? d.name : '?'
            let line = name + ' → ' + (m.mount_path || '/home/coder')
            const sameDrive = (this.form.drive_mounts || []).filter(
                (row) => row.drive_id === m.drive_id,
            ).length
            if (sameDrive > 1) line += ' (subPath)'
            return line
        },
        removeDriveMount(index) {
            if (!this.form.drive_mounts) return
            this.form.drive_mounts.splice(index, 1)
        },
        resetCreateServerForm() {
            this.form = defaultForm()
            this.envKey = ''
            this.envValue = ''
            this.runError = ''
        },
        async openCreateServerModal() {
            this.mobileNavOpen = false
            const limitErr = this.checkServerCountLimit()
            if (limitErr) {
                this.showToast(limitErr)
                return
            }
            this.resetCreateServerForm()
            await this.loadMyDrivesAll()
            await this.loadDockerImages()
            await this.loadK8sNodeOptions()
            this.editingWorkspace = null
            this.showCreateServerModal = true
        },
        closeCreateServerModal() {
            this.showCreateServerModal = false
            this.runError = ''
            this.editingWorkspace = null
        },
        async loadK8sNodeOptions() {
            this.k8sNodeOptionsError = ''
            try {
                const res = await fetch('k8s/nodes')
                const data = await res.json().catch(() => ({}))
                const result = data.result || {}
                if (res.status !== 200 || result.ok === false) {
                    this.k8sNodeOptionsError = result.error || data.message || 'Failed to load nodes'
                    this.k8sNodeOptions = []
                    return
                }
                this.k8sNodeOptions = Array.isArray(result.nodes) ? result.nodes : []
            } catch (e) {
                this.k8sNodeOptionsError = e.message || 'Failed to load nodes'
                this.k8sNodeOptions = []
            }
        },
        async openEditServerModal(ws) {
            if (!ws || ws.state !== 'offline') {
                this.showToast('Stop server before editing')
                return
            }
            this.mobileNavOpen = false
            this.resetCreateServerForm()
            this.editingWorkspace = ws
            await this.loadMyDrivesAll()
            await this.loadDockerImages()
            await this.loadK8sNodeOptions()
            this.form.name = ws.name || ''
            this.form.cpu = ws.cpu || 2
            this.form.ram = ws.ram || '4G'
            this.form.gpu = ws.gpu || 'none'
            this.form.node_hostname = (ws.node_hostname || '').trim() ? (ws.node_hostname || '') : 'auto'
            // Ensure the Docker image dropdown reflects the existing config.
            this.applyTemplateDockerSettings({
                docker_repository: ws.docker_repository,
                docker_tag: ws.docker_tag,
                exposed_ports: ws.exposed_ports,
            })
            this.form.ports_text = (ws.exposed_ports && ws.exposed_ports.length) ? ws.exposed_ports.join(', ') : '8080'
            this.form.command_text = (ws.container_command && ws.container_command.length)
                ? formatCommand(ws.container_command)
                : ''
            this.form.env_vars = { ...(ws.env_vars || {}) }
            this.form.privileged = !!ws.privileged
            const mounts = Array.isArray(ws.drive_mounts) ? ws.drive_mounts : []
            this.form.drive_mounts = mounts.map((m) => ({ drive_id: m.drive_id || '', mount_path: m.mount_path || '/home/coder' }))
            this.showCreateServerModal = true
        },
        openBulkCreateServerModal() {
            const limitErr = this.checkServerCountLimit()
            if (limitErr) {
                this.showToast(limitErr)
                return
            }
            this.showBulkCreateServerModal = true
        },
        closeBulkCreateServerModal() {
            this.showBulkCreateServerModal = false
        },
        async runWorkspace() {
            const limitErr = this.checkServerCountLimit()
                || this.checkWorkspaceLimits(this.form.cpu, this.form.ram, this.form.gpu)
            if (limitErr) {
                this.runError = limitErr
                this.showToast(limitErr)
                return
            }
            this.runLoading = true
            this.runError = ''
            this.addEnv()
            const payload = formPayload(this.form)
            const isEdit = !!this.editingWorkspace
            const res = await fetch(isEdit ? ('workspaces/' + this.editingWorkspace.id) : 'workspaces/run', {
                method: isEdit ? 'PUT' : 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            })
            const data = await res.json().catch(() => ({}))
            this.runLoading = false
            if (res.status !== 200) {
                this.runError = data.logs || data.message || 'Start failed'
                this.showToast(data.message || 'Start failed')
                return
            }
            await this.reloadServerLists()
            this.closeCreateServerModal()
            this.showToast(isEdit ? 'Server updated' : 'Server created')
        },
        async loadMyWorkspaces(page) {
            this.clearBulkSelection('servers')
            const q = new URLSearchParams({
                page: page || this.myServerPagination.page || 1,
                per_page: 12,
                name: this.myServerFilter,
            })
            const res = await fetch('workspaces?' + q)
            if (res.status !== 200) return
            const data = await res.json()
            this.myWorkspaces = data.result || []
            this.myServerPagination = data.pagination || this.myServerPagination
            this.syncResourceUsageCounts()
        },
        async loadAdminWorkspaces(page) {
            this.clearBulkSelection('servers')
            const q = new URLSearchParams({
                page: page || 1,
                per_page: 12,
                user: this.adminServerFilter,
            })
            if (this.adminServerNameFilter) q.set('name', this.adminServerNameFilter)
            if (this.adminServerGroupFilter && this.adminServerGroupFilter !== 'all') q.set('group', this.adminServerGroupFilter)
            const res = await fetch('admin/workspaces?' + q)
            if (res.status !== 200) return
            const data = await res.json()
            this.adminWorkspaces = data.result || []
            this.adminPagination = data.pagination || this.adminPagination
        },
        reloadAdminWorkspacesFilters() {
            this.reloadAdminWorkspaces(1)
        },
        async startWorkspace(ws) {
            await fetch('workspaces/' + ws.id + '/start', { method: 'POST' })
            await this.refreshLists()
        },
        async stopWorkspace(ws) {
            const res = await fetch('workspaces/' + ws.id + '/stop', { method: 'POST' })
            const data = await res.json().catch(() => ({}))
            if (res.status !== 200) {
                this.showToast(data.message || data.error || data.logs || 'Stop failed')
                return
            }
            this.showToast('Server stopped')
            await this.refreshLists()
        },
        openWorkspace(ws) {
            window.open(this.workspaceUrl(ws), '_blank')
        },
        exportWorkspace(ws) {
            window.location = 'workspaces/' + ws.id + '/export'
        },
        async refreshLists() {
            await this.pollStatuses()
        },
        async loadAdminUsers(page) {
            this.clearBulkSelection('users')
            const q = new URLSearchParams({
                page: page || 1,
                per_page: 10,
                user: this.adminUserFilter,
            })
            if (this.adminUserStatus) q.set('status', this.adminUserStatus)
            if (this.adminUserGroupFilter && this.adminUserGroupFilter !== 'all') q.set('group', this.adminUserGroupFilter)
            const res = await fetch('all_users?' + q)
            if (res.status !== 200) return
            const data = await res.json()
            this.userList = data.result || []
            this.adminUserPagination = data.pagination || this.adminUserPagination
        },
        adminAcceptUser(u) {
            fetch('accept_user/' + u.username).then(() => this.loadAdminUsers(this.adminUserPagination.page))
        },
        openDeleteUserModal(u) {
            this.deleteModalUser = u
            this.deleteUserConfirmInput = ''
            this.deleteUserInProgress = false
        },
        closeDeleteUserModal() {
            this.deleteModalUser = null
            this.deleteUserConfirmInput = ''
            this.deleteUserInProgress = false
        },
        async confirmDeleteUser() {
            if (!this.canConfirmDeleteUser || !this.deleteModalUser) return
            const u = this.deleteModalUser
            this.deleteUserInProgress = true
            try {
                const res = await fetch('delete_user/' + encodeURIComponent(u.username), { method: 'DELETE' })
                if (res.status !== 200) {
                    const data = await res.json().catch(() => ({}))
                    this.showToast(data.message || 'Delete failed')
                    return
                }
                this.closeDeleteUserModal()
                const page = this.adminUserPagination.page
                const next = this.userList.length <= 1 && page > 1 ? page - 1 : page
                await this.loadAdminUsers(next)
                this.showToast('User deleted')
            } finally {
                this.deleteUserInProgress = false
            }
        },
        adminChangeRole(u, role) {
            fetch('change_role/' + u.username + '/' + role, { method: 'PUT' })
                .then(() => this.loadAdminUsers(this.adminUserPagination.page))
        },
        switchAdminUsersTab(tab) {
            this.adminUsersTab = tab
            if (tab === 'groups') this.loadResourceGroups()
            else this.loadAdminUsers(1)
        },
        async switchAdminServersTab(tab) {
            this.adminServersTab = tab
            if (tab === 'catalog') await this.loadAdminPlatformCatalog()
            else {
                await this.loadResourceGroups()
                await this.reloadAdminWorkspaces(1)
            }
        },
        async switchAdminDrivesTab(tab) {
            this.adminDrivesTab = tab
            if (tab === 'catalog') await this.loadAdminPlatformCatalog()
            else {
                await this.loadResourceGroups()
                await this.reloadAdminDrives(1)
            }
        },
        async loadResourceGroups() {
            const res = await fetch('admin/resource_groups')
            if (res.status !== 200) return
            const data = await res.json()
            this.resourceGroups = data.result || []
        },
        openCreateGroupModal() {
            this.editingGroup = null
            this.groupForm = { name: '', max_cpu: 4, max_ram_g: 8, max_drive_size_gi: 50, max_gpu_vram_g: 10, max_servers: 5, max_drives: 3, max_images: 10, can_change_privileged: false }
            this.showGroupFormModal = true
        },
        openEditGroupModal(g) {
            this.editingGroup = g
            this.groupForm = {
                name: g.name,
                max_cpu: g.max_cpu,
                max_ram_g: g.max_ram_g,
                max_drive_size_gi: g.max_drive_size_gi,
                max_gpu_vram_g: g.max_gpu_vram_g,
                max_servers: g.max_servers,
                max_drives: g.max_drives,
                max_images: g.max_images,
                can_change_privileged: !!g.can_change_privileged,
            }
            this.showGroupFormModal = true
        },
        closeGroupFormModal() {
            this.showGroupFormModal = false
            this.editingGroup = null
        },
        async saveResourceGroup() {
            this.groupFormLoading = true
            try {
                const url = this.editingGroup
                    ? 'admin/resource_groups/' + this.editingGroup.id + '/update'
                    : 'admin/resource_groups/create'
                const res = await fetch(url, {
                    method: this.editingGroup ? 'PUT' : 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.groupForm),
                })
                const data = await res.json().catch(() => ({}))
                if (res.status !== 200 && res.status !== 201) {
                    this.showToast(data.message || 'Save failed')
                    return
                }
                this.closeGroupFormModal()
                await this.loadResourceGroups()
                this.showToast('Group saved')
            } finally {
                this.groupFormLoading = false
            }
        },
        deleteResourceGroup(g) {
            this.openDeleteYesNoModal({
                kind: 'group',
                item: g,
                title: 'Delete group',
                description: 'Delete group "' + g.name + '"? Members will lose limits.',
            })
        },
        async _executeDeleteResourceGroup(g) {
            const res = await fetch('admin/resource_groups/' + g.id + '/update', { method: 'DELETE' })
            if (res.status !== 200) {
                const data = await res.json().catch(() => ({}))
                this.showToast(data.message || 'Delete failed')
                return false
            }
            await this.loadResourceGroups()
            this.showToast('Group deleted')
            return true
        },
        openDeleteYesNoModal(payload) {
            this.deleteYesNoModal = payload
            this.deleteYesNoInProgress = false
        },
        closeDeleteYesNoModal() {
            this.deleteYesNoModal = null
            this.deleteYesNoInProgress = false
        },
        async confirmDeleteYesNo() {
            if (!this.deleteYesNoModal || this.deleteYesNoInProgress) return
            const modal = this.deleteYesNoModal
            this.deleteYesNoInProgress = true
            try {
                let ok = false
                if (modal.kind === 'catalog_option') {
                    ok = await this._executeDeleteCatalogOption(modal.item)
                } else if (modal.kind === 'plan_template') {
                    ok = await this._executeDeletePlanTemplate(modal.item)
                } else if (modal.kind === 'group') {
                    ok = await this._executeDeleteResourceGroup(modal.item)
                }
                if (ok) this.closeDeleteYesNoModal()
            } finally {
                this.deleteYesNoInProgress = false
            }
        },
        openDeleteImageModal(img, isAdmin) {
            this.deleteModalImage = img
            this.deleteImageIsAdmin = !!isAdmin
            this.deleteImageInProgress = false
        },
        closeDeleteImageModal() {
            this.deleteModalImage = null
            this.deleteImageIsAdmin = false
            this.deleteImageInProgress = false
        },
        async confirmDeleteImage() {
            if (!this.deleteModalImage || this.deleteImageInProgress) return
            const img = this.deleteModalImage
            const isAdmin = this.deleteImageIsAdmin
            this.deleteImageInProgress = true
            try {
                const url = isAdmin
                    ? 'admin/docker_images/' + img.id
                    : 'docker_images/' + img.id
                const res = await fetch(url, { method: 'DELETE' })
                if (res.status !== 200) {
                    const data = await res.json().catch(() => ({}))
                    this.showToast(data.message || 'Delete failed')
                    return
                }
                this.closeDeleteImageModal()
                if (isAdmin) {
                    await this.loadAdminDockerImages(this.adminImagePagination.page)
                    await this.loadDockerImages()
                } else {
                    const page = this.myImagePagination.page
                    const next = this.myDockerImages.length <= 1 && page > 1 ? page - 1 : page
                    await this.reloadMyImages(next)
                    await this.loadDockerImages()
                }
                this.showToast('Image deleted')
            } finally {
                this.deleteImageInProgress = false
            }
        },
        async openGroupMembersModal(g) {
            const res = await fetch('admin/resource_groups/' + g.id)
            if (res.status !== 200) {
                this.showToast('Could not load members')
                return
            }
            const data = await res.json()
            this.groupMembersModal = data.result || { ...g, members: [] }
            this.memberSearchQuery = ''
            this.memberSearchResults = []
            this.memberBulkEmails = ''
            this.memberBulkSummary = ''
        },
        closeGroupMembersModal() {
            this.groupMembersModal = null
            this.memberSearchQuery = ''
            this.memberSearchResults = []
            if (this.memberSearchTimer) clearTimeout(this.memberSearchTimer)
        },
        onMemberSearchInput() {
            if (this.memberSearchTimer) clearTimeout(this.memberSearchTimer)
            const q = (this.memberSearchQuery || '').trim()
            if (!q || !this.groupMembersModal) {
                this.memberSearchResults = []
                return
            }
            this.memberSearchTimer = setTimeout(() => this.searchGroupMembers(q), 250)
        },
        async searchGroupMembers(q) {
            const params = new URLSearchParams({ q, exclude_group: this.groupMembersModal.id })
            const res = await fetch('admin/users/search?' + params)
            if (res.status !== 200) return
            const data = await res.json()
            this.memberSearchResults = data.result || []
        },
        async addGroupMember(u) {
            if (!this.groupMembersModal) return
            const res = await fetch('admin/resource_groups/' + this.groupMembersModal.id + '/members', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: u.id }),
            })
            const data = await res.json().catch(() => ({}))
            if (res.status !== 200 && res.status !== 201) {
                this.showToast(data.message || 'Add failed')
                return
            }
            this.memberSearchQuery = ''
            this.memberSearchResults = []
            await this.openGroupMembersModal({ id: this.groupMembersModal.id, name: this.groupMembersModal.name })
            await this.loadResourceGroups()
            this.showToast('Added ' + u.username)
        },
        async removeGroupMember(m) {
            if (!this.groupMembersModal) return
            const res = await fetch(
                'admin/resource_groups/' + this.groupMembersModal.id + '/members/' + m.user_id,
                { method: 'DELETE' },
            )
            if (res.status !== 200) {
                const data = await res.json().catch(() => ({}))
                this.showToast(data.message || 'Remove failed')
                return
            }
            await this.openGroupMembersModal({ id: this.groupMembersModal.id, name: this.groupMembersModal.name })
            await this.loadResourceGroups()
            this.showToast('Member removed')
        },
        async bulkAddGroupMembers() {
            if (!this.groupMembersModal) return
            this.memberBulkLoading = true
            this.memberBulkSummary = ''
            try {
                const res = await fetch('admin/resource_groups/' + this.groupMembersModal.id + '/members/bulk', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ emails_text: this.memberBulkEmails }),
                })
                const data = await res.json().catch(() => ({}))
                if (res.status !== 200) {
                    this.memberBulkSummary = data.message || 'Bulk add failed'
                    return
                }
                const failed = (data.results || []).filter((r) => !r.ok)
                this.memberBulkSummary = `Matched ${data.matched}, added ${data.added}, failed ${data.failed}`
                if (failed.length) {
                    this.memberBulkSummary += '\n' + failed.map((r) => r.email + ': ' + (r.error || 'failed')).join('\n')
                }
                await this.openGroupMembersModal({ id: this.groupMembersModal.id, name: this.groupMembersModal.name })
                await this.loadResourceGroups()
                this.showToast('Bulk add finished')
            } finally {
                this.memberBulkLoading = false
            }
        },
        async loadAdminDockerImages(page) {
            this.clearBulkSelection('images')
            const q = new URLSearchParams({
                page: page || this.adminImagePagination.page || 1,
                per_page: 12,
            })
            if (this.adminImageNameFilter) q.set('name', this.adminImageNameFilter)
            if (this.adminImageCreatorFilter) q.set('creator', this.adminImageCreatorFilter)
            if (this.adminImageStatusFilter && this.adminImageStatusFilter !== 'all') {
                q.set('status', this.adminImageStatusFilter)
            }
            const res = await fetch('admin/docker_images?' + q)
            if (res.status === 200) {
                const data = await res.json()
                this.adminDockerImages = data.result || []
                this.adminImagePagination = data.pagination || this.adminImagePagination
            }
        },
        reloadAdminDockerImagesFilters() {
            this.loadAdminDockerImages(1)
        },
        async reloadAdminDockerImages(page) {
            await this.loadAdminDockerImages(page || 1)
        },
        async acceptDockerImage(img) {
            if (!img || !img.id) return
            await fetch('admin/docker_images/' + img.id, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ is_accepted: true }),
            })
            await this.loadAdminDockerImages(this.adminImagePagination.page)
            await this.loadDockerImages()
            this.showToast('Image accepted')
        },
        openEditDockerImage(img) {
            this.editingDockerImage = {
                ...img,
                tags_text: ((img && img.tags) ? img.tags : []).join(', '),
            }
        },
        cancelEditDockerImage() {
            this.editingDockerImage = null
        },
        async saveDockerImage(img) {
            if (!img || !img.id) return
            const tags = String(img.tags_text || '')
                .split(/[,;\s]+/)
                .map((t) => t.trim())
                .filter(Boolean)
            await fetch('admin/docker_images/' + img.id, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    label: img.label,
                    repository: img.repository,
                    default_tag: img.default_tag,
                    tags,
                    tags_text: tags.join(', '),
                    is_active: img.is_active,
                    sort_order: img.sort_order,
                }),
            })
            this.editingDockerImage = null
            await this.loadAdminDockerImages(this.adminImagePagination.page)
            await this.loadDockerImages()
        },
        downloadDockerImagesJson() {
            window.location = 'admin/docker_images/export'
        },
        openDockerImageBulkModal() {
            this.showDockerImageBulkModal = true
            this.dockerImageBulkMode = 'json'
            this.dockerImageBulkText = ''
            this.dockerImageBulkFileName = ''
            this.dockerImageBulkSummary = ''
        },
        closeDockerImageBulkModal() {
            this.showDockerImageBulkModal = false
            this.dockerImageBulkLoading = false
        },
        onDockerImageBulkFileSelected(event) {
            const file = event && event.target && event.target.files && event.target.files[0]
            if (!file) return
            this.dockerImageBulkFileName = file.name || ''
            const reader = new FileReader()
            reader.onload = () => {
                this.dockerImageBulkText = String(reader.result || '')
            }
            reader.readAsText(file)
        },
        parseDockerImagesBulk() {
            const text = (this.dockerImageBulkText || '').trim()
            if (!text) return { error: 'paste JSON/CSV or upload a file' }
            if (this.dockerImageBulkMode === 'json') {
                try {
                    const parsed = JSON.parse(text)
                    const items = Array.isArray(parsed) ? parsed : (parsed.items || parsed.result || [])
                    if (!Array.isArray(items)) return { error: 'JSON must be an array of images (or {items:[...]})' }
                    return { items }
                } catch {
                    return { error: 'invalid JSON' }
                }
            }
            try {
                const items = parseCsvRows(text, (row) => ({
                    id: row.id || row.image_id || '',
                    label: row.label || '',
                    repository: row.repository || row.repo || '',
                    default_tag: row.default_tag || row.tag || 'latest',
                    tags_text: row.tags || row.tags_text || '',
                    sort_order: row.sort_order || 0,
                    is_active: (row.is_active || 'true').toString().toLowerCase() !== 'false',
                }))
                return { items }
            } catch (e) {
                return { error: e.message || 'invalid CSV' }
            }
        },
        async importDockerImagesBulk() {
            const built = this.parseDockerImagesBulk()
            if (built.error) {
                this.dockerImageBulkSummary = built.error
                return
            }
            this.dockerImageBulkLoading = true
            this.dockerImageBulkSummary = ''
            try {
                const res = await fetch('admin/docker_images/import', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ items: built.items }),
                })
                const data = await res.json().catch(() => ({}))
                const failed = (data.results || []).filter((r) => !r.ok)
                this.dockerImageBulkSummary = `Imported: ${data.ok || 0} ok, ${data.failed || failed.length} failed`
                if (failed.length) {
                    this.dockerImageBulkSummary += '\n' + failed.map((r) => (r.label || r.repository || '?') + ': ' + (r.error || 'failed')).join('\n')
                }
                await this.loadAdminDockerImages(this.adminImagePagination.page)
                await this.loadDockerImages()
            } finally {
                this.dockerImageBulkLoading = false
            }
        },
        async createDockerImage() {
            await fetch('admin/docker_images/create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(this.newImage),
            })
            this.newImage = { label: '', repository: '', default_tag: 'latest', tags_text: '' }
            await this.loadAdminDockerImages(this.adminImagePagination.page)
            await this.loadDockerImages()
        },
    },
})
