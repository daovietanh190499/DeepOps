Vue.component('spec-row', {
    props: ['label', 'value'],
    template: `<div class="flex justify-between gap-4 border-b border-slate-100 py-2 last:border-0">
      <span class="font-medium text-slate-500" v-text="label"></span>
      <span class="font-semibold text-slate-800 text-right truncate" v-text="value"></span>
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
    <div class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm mb-3 flex flex-wrap gap-4 items-center">
      <img :src="user.image || '/static/img/logo.png'" class="h-10 w-10 rounded-full border object-cover" alt="">
      <div class="flex-1 min-w-[8rem]">
        <p class="font-semibold" v-text="user.username"></p>
        <p v-if="user.email" class="text-xs text-slate-500 truncate" v-text="user.email"></p>
        <p class="text-xs text-slate-500" v-text="user.role + ' · ' + last_activity + (user.group_name ? ' · ' + user.group_name : '')"></p>
      </div>
      <span class="text-xs px-2 py-0.5 rounded-full" :class="user.is_accept ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'"
            v-text="user.is_accept ? 'accepted' : 'pending'"></span>
      <div class="relative">
        <button @click="showRole=!showRole" class="px-3 py-1 rounded-lg bg-indigo-600 text-white text-xs" v-text="user.role"></button>
        <div v-if="showRole" class="absolute z-10 mt-1 bg-white border rounded-lg shadow py-1">
          <button class="block w-full text-left px-3 py-1 text-sm hover:bg-slate-50" @click="$emit('role','admin'); showRole=false">admin</button>
          <button class="block w-full text-left px-3 py-1 text-sm hover:bg-slate-50" @click="$emit('role','normal_user'); showRole=false">normal_user</button>
        </div>
      </div>
      <button v-if="!user.is_accept" @click="$emit('accept')" class="px-3 py-1 rounded-lg bg-emerald-600 text-white text-xs">Accept</button>
      <button @click="$emit('delete')" class="px-3 py-1 rounded-lg border text-slate-600 text-xs">Delete</button>
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
                return 'Drives: ' + mounts.map((m) => (m.drive_name || '?') + ' → ' + m.mount_path).join(', ')
            }
            return 'Drive: ' + (ws.drive_name || '—') + ' → ' + (ws.mount_path || '/home/coder')
        },
        onCardClick() {
            if (this.disabled) return
            this.$emit('detail', this.ws)
        },
    },
    template: `
    <div class="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm flex flex-col gap-3 transition"
         :class="disabled ? 'opacity-60 pointer-events-none select-none' : 'cursor-pointer hover:border-blue-300 hover:shadow-md'"
         @click="onCardClick">
      <div class="flex justify-between items-start gap-2">
        <div class="min-w-0 flex-1">
          <h3 class="font-bold text-slate-900 truncate" v-text="ws.name"></h3>
          <p v-if="showOwner" class="text-xs text-slate-500" v-text="'@' + ws.owner"></p>
          <div class="flex items-center gap-1 mt-0.5">
            <p class="text-xs font-mono text-slate-400 truncate flex-1" v-text="ws.hostname"></p>
            <button type="button" @click.stop="$emit('copy', ws)" class="shrink-0 rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-blue-600" title="Copy URL">
              <i class="fa fa-copy text-xs"></i>
            </button>
          </div>
        </div>
        <span class="shrink-0 rounded-full px-2 py-0.5 text-xs font-bold" :class="stateClass" v-text="k8sDisplay"></span>
      </div>
      <div class="text-xs text-slate-600 space-y-0.5 pointer-events-none">
        <p v-text="ws.cpu + ' vCPU · ' + ws.ram"></p>
        <p v-text="workspaceDriveSummary(ws)"></p>
        <p v-text="'GPU: ' + (ws.gpu || 'none')"></p>
        <p class="font-mono truncate" v-text="ws.docker_repository + ':' + ws.docker_tag"></p>
      </div>
      <div class="flex flex-wrap gap-2 mt-auto" @click.stop>
        <button v-if="canStart" @click="$emit('start', ws)" class="flex-1 rounded-lg bg-blue-600 text-white text-xs py-2 font-semibold">Start</button>
        <button v-if="canStop" @click="$emit('stop', ws)" class="flex-1 rounded-lg bg-rose-600 text-white text-xs py-2 font-semibold">Stop</button>
        <button v-if="canOpen" @click="$emit('open', ws)" class="flex-1 rounded-lg border border-blue-600 text-blue-600 text-xs py-2 font-semibold">Open</button>
        <button @click="$emit('export', ws)" class="rounded-lg border px-2 py-2 text-xs" title="Export"><i class="fa fa-download"></i></button>
        <button v-if="canDelete" @click="$emit('delete', ws)" class="rounded-lg border border-rose-200 text-rose-600 px-2 py-2 text-xs"><i class="fa fa-trash"></i></button>
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

function expandEnvTemplateString(value) {
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
            default:
                return `<<${kind}>>`
        }
    })
}

function resolveTemplateEnv(envDefaults) {
    const out = {}
    if (!envDefaults) return out
    const defaults = { ...envDefaults }
    if (defaults.PASSWORD_PREFIX && !defaults.PASSWORD) {
        defaults.PASSWORD = `${defaults.PASSWORD_PREFIX}<<rdstring:6>>`
        delete defaults.PASSWORD_PREFIX
    }
    Object.keys(defaults).forEach((k) => {
        if (k === 'PASSWORD_PREFIX') return
        out[k] = expandEnvTemplateString(defaults[k])
    })
    return out
}

function defaultDriveMount() {
    return { drive_id: '', mount_path: '/home/coder' }
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
        drive_mounts: [defaultDriveMount()],
        gpu: 'none',
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
    return String(text).trim().split(/\s+/)
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
        if (item.cpu) item.cpu = parseInt(item.cpu, 10)
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

const appVue = new Vue({
    el: '#root',
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
        adminDockerImages: [],
        newImage: { label: '', repository: '', default_tag: 'latest', tags_text: '' },
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
        userList: [],
        adminUserFilter: '',
        adminUserStatus: '',
        adminUserPagination: { page: 1, pages: 1, total: 0, per_page: 10 },
        adminUsersTab: 'users',
        adminServersTab: 'servers',
        adminDrivesTab: 'drives',
        resourceGroups: [],
        showGroupFormModal: false,
        editingGroup: null,
        groupForm: { name: '', max_cpu: 4, max_ram_g: 8, max_drive_size_gi: 50, max_gpu_vram_g: 10, max_servers: 5, max_drives: 3, can_change_privileged: false },
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
        current_user: '',
        is_admin: false,
        runLoading: false,
        runError: '',
        modalWorkspace: null,
        deleteModalWorkspace: null,
        deleteModalIsAdmin: false,
        deleteConfirmInput: '',
        deleteInProgress: false,
        toastMessage: '',
        toastTimer: null,
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
            if (!mounts.length) return '—'
            return mounts.map((m) => {
                const d = this.myDrivesAll.find((x) => x.id === m.drive_id)
                return (d ? this.driveOptionLabel(d) : '?') + ' → ' + (m.mount_path || '/home/coder')
            }).join(', ')
        },
        userTabs() {
            return [
                { id: 'servers', label: 'My servers' },
                { id: 'drives', label: 'My drives' },
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
        filteredPlanTemplates() {
            if (!this.resourceLimits.limited) return this.planTemplates
            const eq = this.resourceLimits.equipment || {}
            const cpus = eq.cpu || []
            const rams = eq.ram || []
            const gpus = eq.gpu || []
            return this.planTemplates.filter((t) =>
                cpus.includes(t.cpu) && rams.includes(t.ram) && gpus.includes(t.gpu),
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
    },
    created() {
        const params = new URLSearchParams(window.location.search)
        const tab = params.get('tab') || 'servers'
        this.menu = tab === 'home' ? 'servers' : tab
        this.init()
    },
    beforeDestroy() {
        this.stopStatusPolling()
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
                this.showToast('URL copied')
            } catch {
                const ta = document.createElement('textarea')
                ta.value = url
                document.body.appendChild(ta)
                ta.select()
                document.execCommand('copy')
                document.body.removeChild(ta)
                this.showToast('URL copied')
            }
        },
        openWorkspaceModal(ws) {
            this.modalWorkspace = { ...ws, env_vars: { ...(ws.env_vars || {}) } }
            this.sshPrivateKeyOnce = ''
            this.sshSyncMessage = ''
            this.sshSyncError = ''
            this.loadWorkspaceSsh(ws)
        },
        closeWorkspaceModal() {
            this.modalWorkspace = null
            this.sshPrivateKeyOnce = ''
            this.sshSyncMessage = ''
            this.sshSyncError = ''
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
            window.history.replaceState({}, '', '/?tab=' + menu)
            if (menu === 'drives') await this.reloadMyDrives(1)
            if (menu === 'servers') await this.reloadMyWorkspaces(1)
            if (menu === 'admin-overall') {
                await this.loadClusterOverview()
                await this.loadDirectpvDiscover()
            }
            if (menu === 'admin-drives') {
                if (this.adminDrivesTab === 'catalog') await this.loadAdminPlatformCatalog()
                else await this.reloadAdminDrives(1)
            }
            if (menu === 'admin-servers') {
                if (this.adminServersTab === 'catalog') await this.loadAdminPlatformCatalog()
                else await this.reloadAdminWorkspaces(1)
            }
            if (menu === 'admin-users') {
                if (this.adminUsersTab === 'groups') await this.loadResourceGroups()
                else await this.loadAdminUsers(1)
            }
            if (menu === 'admin-images') await this.loadAdminDockerImages()
            if (['drives', 'servers', 'admin-drives', 'admin-servers', 'admin-overall'].includes(menu)) {
                this.startStatusPolling()
            }
        },
        async init() {
            if (!this.is_login) return
            await this.getCurrentUserState()
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
            if (this.is_admin) {
                if (this.menu === 'admin-users') {
                    if (this.adminUsersTab === 'groups') await this.loadResourceGroups()
                    else await this.loadAdminUsers(1)
                }
                await this.loadAdminDockerImages()
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
            if (!confirm('Delete option ' + option.value + '?')) return
            const res = await fetch('admin/platform/options/' + option.id, { method: 'DELETE' })
            if (res.status !== 200) {
                this.showToast('Delete failed')
                return
            }
            await this.loadAdminPlatformCatalog()
            this.showToast('Option deleted')
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
                command_text: (template.container_command || []).join(' '),
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
            if (!confirm('Delete template ' + template.name + '?')) return
            const res = await fetch('admin/platform/templates/' + template.id, { method: 'DELETE' })
            if (res.status !== 200) {
                this.showToast('Delete failed')
                return
            }
            await this.loadAdminPlatformCatalog()
            await this.loadPlatformCatalog()
            this.showToast('Template deleted')
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
        clampFormToLimits() {
            const eq = this.resourceLimits.equipment
            if (!eq) return
            if (!eq.cpu.includes(this.form.cpu)) {
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
            if (eq.cpu && !eq.cpu.includes(Number(cpu))) {
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
        syncResourceUsageCounts() {
            if (!this.resourceLimits.limits) return
            this.resourceLimits.limits.server_count = this.myServerPagination.total ?? this.myWorkspaces.length
            this.resourceLimits.limits.drive_count = this.myDrivePagination.total ?? this.myDrives.length
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
                this.form.command_text = t.container_command.join(' ')
            } else {
                this.form.command_text = ''
            }
            const env = resolveTemplateEnv(t.env_defaults)
            this.form.env_vars = { ...this.form.env_vars, ...env }
            const firstKey = Object.keys(env)[0] || ''
            this.envKey = firstKey
            this.envValue = this.form.env_vars[firstKey] || ''
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
                const cmd = t.container_command.join(' ')
                parts.push('cmd ' + (cmd.length > 24 ? cmd.slice(0, 24) + '…' : cmd))
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
            const q = new URLSearchParams({ page: page || 1, per_page: 12, user: this.adminDriveFilter })
            const res = await fetch('admin/drives?' + q)
            if (res.status !== 200) return
            const data = await res.json()
            this.adminDrives = data.result || []
            this.adminDrivePagination = data.pagination || this.adminDrivePagination
        },
        openCreateDriveModal() {
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
        driveSelectableForMount(drive, rowIndex) {
            if ((this.form.drive_mounts[rowIndex] || {}).drive_id === drive.id) return true
            if ((this.form.drive_mounts || []).some((m, i) => i !== rowIndex && m.drive_id === drive.id)) {
                return false
            }
            return true
        },
        drivesForMountRow(rowIndex) {
            return this.myDrivesAll.filter((d) => this.driveSelectableForMount(d, rowIndex))
        },
        addDriveMount() {
            if (!this.form.drive_mounts) this.$set(this.form, 'drive_mounts', [])
            const idx = this.form.drive_mounts.length
            const mountPath = idx === 0 ? '/home/coder' : (idx === 1 ? '/data' : `/mnt/drive${idx + 1}`)
            this.form.drive_mounts.push({ drive_id: '', mount_path: mountPath })
        },
        removeDriveMount(index) {
            if (!this.form.drive_mounts || this.form.drive_mounts.length <= 1) return
            this.form.drive_mounts.splice(index, 1)
        },
        async openCreateServerModal() {
            const limitErr = this.checkServerCountLimit()
            if (limitErr) {
                this.showToast(limitErr)
                return
            }
            await this.loadMyDrivesAll()
            await this.loadDockerImages()
            if (this.selectedDockerTags.length && !this.selectedDockerTags.includes(this.form.docker_tag)) {
                this.form.docker_tag = this.selectedDockerTags[0]
            }
            if (!this.form.drive_mounts || !this.form.drive_mounts.length) {
                this.form.drive_mounts = [defaultDriveMount()]
            }
            this.runError = ''
            this.showCreateServerModal = true
        },
        closeCreateServerModal() {
            this.showCreateServerModal = false
            this.runError = ''
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
            if (!(this.form.drive_mounts || []).some((m) => m.drive_id)) {
                this.runError = 'Select at least one drive to mount'
                return
            }
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
            const res = await fetch('workspaces/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formPayload(this.form)),
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
            this.showToast('Server created')
        },
        async loadMyWorkspaces(page) {
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
            const q = new URLSearchParams({
                page: page || 1,
                per_page: 12,
                user: this.adminServerFilter,
            })
            const res = await fetch('admin/workspaces?' + q)
            if (res.status !== 200) return
            const data = await res.json()
            this.adminWorkspaces = data.result || []
            this.adminPagination = data.pagination || this.adminPagination
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
            const q = new URLSearchParams({
                page: page || 1,
                per_page: 10,
                user: this.adminUserFilter,
            })
            if (this.adminUserStatus) q.set('status', this.adminUserStatus)
            const res = await fetch('all_users?' + q)
            if (res.status !== 200) return
            const data = await res.json()
            this.userList = data.result || []
            this.adminUserPagination = data.pagination || this.adminUserPagination
        },
        adminAcceptUser(u) {
            fetch('accept_user/' + u.username).then(() => this.loadAdminUsers(this.adminUserPagination.page))
        },
        adminDeleteUser(u) {
            if (!confirm('Delete user ' + u.username + '?')) return
            fetch('delete_user/' + u.username, { method: 'DELETE' }).then(() => {
                const page = this.adminUserPagination.page
                const next = this.userList.length <= 1 && page > 1 ? page - 1 : page
                this.loadAdminUsers(next)
            })
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
            else await this.reloadAdminWorkspaces(1)
        },
        async switchAdminDrivesTab(tab) {
            this.adminDrivesTab = tab
            if (tab === 'catalog') await this.loadAdminPlatformCatalog()
            else await this.reloadAdminDrives(1)
        },
        async loadResourceGroups() {
            const res = await fetch('admin/resource_groups')
            if (res.status !== 200) return
            const data = await res.json()
            this.resourceGroups = data.result || []
        },
        openCreateGroupModal() {
            this.editingGroup = null
            this.groupForm = { name: '', max_cpu: 4, max_ram_g: 8, max_drive_size_gi: 50, max_gpu_vram_g: 10, max_servers: 5, max_drives: 3, can_change_privileged: false }
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
        async deleteResourceGroup(g) {
            if (!confirm('Delete group "' + g.name + '"? Members will lose limits.')) return
            const res = await fetch('admin/resource_groups/' + g.id + '/update', { method: 'DELETE' })
            if (res.status !== 200) {
                const data = await res.json().catch(() => ({}))
                this.showToast(data.message || 'Delete failed')
                return
            }
            await this.loadResourceGroups()
            this.showToast('Group deleted')
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
        async loadAdminDockerImages() {
            const res = await fetch('admin/docker_images')
            if (res.status === 200) {
                const data = await res.json()
                this.adminDockerImages = data.result
            }
        },
        async createDockerImage() {
            await fetch('admin/docker_images/create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(this.newImage),
            })
            this.newImage = { label: '', repository: '', default_tag: 'latest', tags_text: '' }
            await this.loadAdminDockerImages()
            await this.loadDockerImages()
        },
        async deleteDockerImage(img) {
            if (!confirm('Delete image ' + img.label + '?')) return
            await fetch('admin/docker_images/' + img.id, { method: 'DELETE' })
            await this.loadAdminDockerImages()
            await this.loadDockerImages()
        },
    },
})
