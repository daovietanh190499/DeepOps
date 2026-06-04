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
        <p class="text-xs text-slate-500" v-text="user.role + ' · ' + last_activity"></p>
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
    props: ['ws', 'showOwner'],
    computed: {
        stateClass() {
            if (this.ws.state === 'running') return 'bg-emerald-100 text-emerald-700'
            if (this.ws.state === 'offline') return 'bg-slate-100 text-slate-600'
            return 'bg-amber-100 text-amber-700'
        },
        canStart() {
            return this.ws.state === 'offline'
        },
        canStop() {
            return ['running', 'pending_start', 'pending_stop'].includes(this.ws.state)
        },
        canOpen() {
            return this.ws.state === 'running'
        },
        canDelete() {
            return this.ws.state === 'offline'
        },
        serverUrl() {
            return window.location.protocol + '//' + this.ws.hostname
        },
    },
    methods: {
        onCardClick() {
            this.$emit('detail', this.ws)
        },
    },
    template: `
    <div class="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm flex flex-col gap-3 cursor-pointer transition hover:border-blue-300 hover:shadow-md"
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
        <span class="shrink-0 rounded-full px-2 py-0.5 text-xs font-bold uppercase" :class="stateClass" v-text="ws.state"></span>
      </div>
      <div class="text-xs text-slate-600 space-y-0.5 pointer-events-none">
        <p v-text="ws.cpu + ' vCPU · ' + ws.ram"></p>
        <p v-text="'Drive: ' + (ws.drive_name || '—') + ' → ' + (ws.mount_path || '/home/coder')"></p>
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

function randomToken(len) {
    const chars = 'abcdefghijklmnopqrstuvwxyz0123456789'
    let s = ''
    for (let i = 0; i < len; i++) s += chars[Math.floor(Math.random() * chars.length)]
    return s
}

const PLAN_TEMPLATES = [
    {
        name: 'Lollipop', image: 'lollipop.png', cpu: 2, ram: '4G', gpu: 'none',
        env_defaults: { PASSWORD: () => 'lollipop-' + randomToken(6), PWA_APPNAME: 'Lollipop' },
    },
    {
        name: 'Oreo', image: 'oreo.png', cpu: 4, ram: '8G', gpu: 'mig-2g.10gb',
        env_defaults: { PASSWORD: () => 'oreo-' + randomToken(6), PWA_APPNAME: 'Oreo' },
    },
    {
        name: 'Popeyes', image: 'popeyes.png', cpu: 8, ram: '16G', gpu: 'mig-3g.20gb',
        env_defaults: { PASSWORD: () => 'popeyes-' + randomToken(6), PWA_APPNAME: 'Popeyes' },
    },
    {
        name: 'Pizza', image: 'pizza.png', cpu: 8, ram: '32G', gpu: 'gpu',
        env_defaults: { PASSWORD: () => 'pizza-' + randomToken(6), PWA_APPNAME: 'Pizza' },
    },
    {
        name: 'Spagetti', image: 'spagetti.png', cpu: 16, ram: '64G', gpu: 'gpu:2',
        env_defaults: { PASSWORD: () => 'spagetti-' + randomToken(6), PWA_APPNAME: 'Spagetti' },
    },
]

function defaultForm() {
    return {
        name: 'My workspace',
        cpu: 2,
        ram: '4G',
        drive_id: '',
        mount_path: '/home/coder',
        gpu: 'none',
        docker_image_id: '',
        docker_repository: 'codercom/code-server',
        docker_tag: '4.89.0-ubuntu',
        ports_text: '8080',
        command_text: '',
        env_vars: {},
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
    return {
        name: form.name,
        cpu: form.cpu,
        ram: form.ram,
        drive_id: form.drive_id || null,
        mount_path: form.mount_path || '/home/coder',
        gpu: form.gpu === 'none' ? '' : form.gpu,
        docker_repository: form.docker_repository,
        docker_tag: form.docker_tag,
        env_vars: { ...form.env_vars },
        exposed_ports: parsePorts(form.ports_text),
        container_command: parseCommand(form.command_text),
    }
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
        equipmentList: {
            cpu: [2, 4, 8, 16, 32],
            ram: ['2G', '4G', '8G', '16G', '32G', '64G'],
            gpu: ['none', 'mig-2g.10gb', 'mig-3g.20gb', 'gpu', 'gpu:2'],
        },
        driveSizeOptions: ['20Gi', '50Gi', '100Gi', '200Gi', '500Gi', '1Ti'],
        myDrives: [],
        adminDrives: [],
        adminDrivePagination: { page: 1, pages: 1, total: 0, per_page: 12 },
        adminDriveFilter: '',
        newDrive: { name: 'My drive', size: '20Gi' },
        driveCreateLoading: false,
        deleteModalDrive: null,
        deleteModalDriveIsAdmin: false,
        deleteDriveConfirmInput: '',
        deleteDriveInProgress: false,
        planTemplates: PLAN_TEMPLATES,
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
        adminWorkspaces: [],
        adminPagination: { page: 1, pages: 1, total: 0, per_page: 12 },
        adminServerFilter: '',
        adminDockerImages: [],
        newImage: { label: '', repository: '', default_tag: 'latest' },
        clusterOverview: null,
        clusterLoading: false,
        joinCommand: '',
        joinCommandRaw: '',
        joinCommandLoading: false,
        joinCommandError: '',
        userList: [],
        is_login: typeof is_login !== 'undefined' ? is_login : 0,
        menu: 'home',
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
    },
    computed: {
        canConfirmDelete() {
            return this.deleteConfirmInput.trim().toLowerCase() === 'delete'
        },
        canConfirmDeleteDrive() {
            return this.deleteDriveConfirmInput.trim().toLowerCase() === 'delete'
        },
        selectedDriveLabel() {
            const d = this.myDrives.find((x) => x.id === this.form.drive_id)
            return d ? d.name + ' (' + d.size + ')' : '—'
        },
        userTabs() {
            return [
                { id: 'home', label: 'Home' },
                { id: 'drives', label: 'Drives' },
                { id: 'servers', label: 'My servers' },
            ]
        },
        adminTabs() {
            return [
                { id: 'admin-overall', label: 'Overall' },
                { id: 'admin-users', label: 'Users' },
                { id: 'admin-drives', label: 'All drives' },
                { id: 'admin-servers', label: 'Servers' },
                { id: 'admin-images', label: 'Images' },
            ]
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
    },
    created() {
        const params = new URLSearchParams(window.location.search)
        this.menu = params.get('tab') || 'home'
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
        async pollStatuses() {
            const m = this.menu
            if (m === 'drives' || m === 'home') await this.loadMyDrives()
            if (m === 'servers' || m === 'home') await this.loadMyWorkspaces()
            if (m === 'admin-drives') await this.loadAdminDrives(this.adminDrivePagination.page)
            if (m === 'admin-servers') await this.loadAdminWorkspaces(this.adminPagination.page)
            if (m === 'admin-overall') await this.loadClusterOverview()
        },
        loginWithGithub() { window.location = 'login' },
        logout() { window.location = 'logout' },
        workspaceUrl(ws) {
            return window.location.protocol + '//' + (ws.hostname || '')
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
        },
        closeWorkspaceModal() {
            this.modalWorkspace = null
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
                await this.refreshLists()
            } finally {
                this.deleteInProgress = false
            }
        },
        exportModalConfig() {
            if (!this.modalWorkspace) return
            downloadJson(this.modalWorkspace, 'dohub-' + this.modalWorkspace.slug + '-config.json')
        },
        changeMenu(menu) {
            this.stopStatusPolling()
            this.menu = menu
            window.history.replaceState({}, '', '/?tab=' + menu)
            if (menu === 'drives') this.loadMyDrives()
            if (menu === 'servers') this.loadMyWorkspaces()
            if (menu === 'admin-overall') this.loadClusterOverview()
            if (menu === 'admin-drives') this.loadAdminDrives(1)
            if (menu === 'admin-servers') this.loadAdminWorkspaces(1)
            if (menu === 'admin-users') this.getAllUsers()
            if (menu === 'admin-images') this.loadAdminDockerImages()
            if (['home', 'drives', 'servers', 'admin-drives', 'admin-servers', 'admin-overall'].includes(menu)) {
                this.startStatusPolling()
            }
        },
        async init() {
            if (!this.is_login) return
            await this.getCurrentUserState()
            await this.loadDockerImages()
            await this.loadMyDrives()
            await this.loadMyWorkspaces()
            if (this.is_admin) {
                await this.getAllUsers()
                await this.loadAdminDockerImages()
            }
            if (this.menu === 'admin-overall') await this.loadClusterOverview()
            if (['home', 'drives', 'servers', 'admin-drives', 'admin-servers', 'admin-overall'].includes(this.menu)) {
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
                this.form.docker_tag = first.default_tag
            }
        },
        onDockerImageChange() {
            const img = this.dockerImages.find((i) => i.id === this.form.docker_image_id)
            if (img) {
                this.form.docker_repository = img.repository
                this.form.docker_tag = img.default_tag
            }
        },
        applyTemplate(t) {
            this.form.cpu = t.cpu
            this.form.ram = t.ram
            this.form.gpu = t.gpu
            this.form.name = t.name + ' workspace'
            const env = resolveEnvDefaults(t.env_defaults)
            this.form.env_vars = { ...this.form.env_vars, ...env }
            const firstKey = Object.keys(env)[0] || 'PASSWORD'
            this.envKey = firstKey
            this.envValue = this.form.env_vars[firstKey] || ''
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
                    return
                }
                this.bulkSummary = formatBulkSummary(data, items.length)
                await this.loadMyWorkspaces()
                await this.loadMyDrives()
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
                    return
                }
                this.driveBulkSummary = formatBulkSummary(data, items.length)
                await this.loadMyDrives()
                if (this.is_admin) await this.loadAdminDrives(this.adminDrivePagination.page)
            } catch (e) {
                this.driveBulkSummary = e.message || String(e)
            } finally {
                this.driveBulkLoading = false
            }
        },
        async loadMyDrives() {
            const res = await fetch('drives')
            if (res.status !== 200) return
            const data = await res.json()
            this.myDrives = data.result || []
            if (!this.form.drive_id && this.myDrives.length) {
                this.form.drive_id = this.myDrives[0].id
            }
        },
        async loadAdminDrives(page) {
            const q = new URLSearchParams({ page: page || 1, per_page: 12, user: this.adminDriveFilter })
            const res = await fetch('admin/drives?' + q)
            if (res.status !== 200) return
            const data = await res.json()
            this.adminDrives = data.result || []
            this.adminDrivePagination = data.pagination || this.adminDrivePagination
        },
        async createDrive() {
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
            await this.loadMyDrives()
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
            await this.loadMyDrives()
            if (this.is_admin) await this.loadAdminDrives(this.adminDrivePagination.page)
        },
        async runWorkspace() {
            if (!this.form.drive_id) {
                this.runError = 'Select a drive to mount'
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
                return
            }
            await this.loadMyWorkspaces()
            this.changeMenu('servers')
        },
        async loadMyWorkspaces() {
            const res = await fetch('workspaces')
            if (res.status !== 200) return
            const data = await res.json()
            this.myWorkspaces = data.result || []
            if (this.modalWorkspace) {
                const updated = this.myWorkspaces.find((w) => w.id === this.modalWorkspace.id)
                if (updated) this.modalWorkspace = { ...updated, env_vars: { ...(updated.env_vars || {}) } }
            }
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
            await fetch('workspaces/' + ws.id + '/stop', { method: 'POST' })
            await this.refreshLists()
        },
        openWorkspace(ws) {
            window.open(this.workspaceUrl(ws), '_blank')
        },
        exportWorkspace(ws) {
            window.location = 'workspaces/' + ws.id + '/export'
        },
        async refreshLists() {
            await this.loadMyWorkspaces()
            if (this.is_admin && this.menu === 'admin-servers') {
                await this.loadAdminWorkspaces(this.adminPagination.page)
            }
        },
        async getAllUsers() {
            const res = await fetch('all_users')
            if (res.status === 200) {
                const data = await res.json()
                this.userList = data.result
            }
        },
        adminAcceptUser(u) {
            fetch('accept_user/' + u.username).then(() => this.getAllUsers())
        },
        adminDeleteUser(u) {
            if (!confirm('Delete user ' + u.username + '?')) return
            fetch('delete_user/' + u.username, { method: 'DELETE' }).then(() => this.getAllUsers())
        },
        adminChangeRole(u, role) {
            fetch('change_role/' + u.username + '/' + role, { method: 'PUT' }).then(() => this.getAllUsers())
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
            this.newImage = { label: '', repository: '', default_tag: 'latest' }
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
