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
        <p v-text="ws.cpu + ' vCPU · ' + ws.ram + ' · ' + ws.drive"></p>
        <p v-text="'GPU: ' + (ws.gpu || 'none')"></p>
        <p class="font-mono truncate" v-text="ws.docker_repository + ':' + ws.docker_tag"></p>
      </div>
      <div class="flex flex-wrap gap-2 mt-auto" @click.stop>
        <button v-if="ws.state==='offline'" @click="$emit('start', ws)" class="flex-1 rounded-lg bg-blue-600 text-white text-xs py-2 font-semibold">Start</button>
        <button v-if="ws.state==='running'" @click="$emit('stop', ws)" class="flex-1 rounded-lg bg-rose-600 text-white text-xs py-2 font-semibold">Stop</button>
        <button v-if="ws.state==='running'" @click="$emit('open', ws)" class="flex-1 rounded-lg border border-blue-600 text-blue-600 text-xs py-2 font-semibold">Open</button>
        <button @click="$emit('export', ws)" class="rounded-lg border px-2 py-2 text-xs" title="Export"><i class="fa fa-download"></i></button>
        <button v-if="ws.state==='offline'" @click="$emit('delete', ws)" class="rounded-lg border border-rose-200 text-rose-600 px-2 py-2 text-xs"><i class="fa fa-trash"></i></button>
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
        name: 'Lollipop', image: 'lollipop.png', cpu: 2, ram: '4G', drive: '20Gi', gpu: 'none',
        env_defaults: { PASSWORD: () => 'lollipop-' + randomToken(6), PWA_APPNAME: 'Lollipop' },
    },
    {
        name: 'Oreo', image: 'oreo.png', cpu: 4, ram: '8G', drive: '50Gi', gpu: 'mig-2g.10gb',
        env_defaults: { PASSWORD: () => 'oreo-' + randomToken(6), PWA_APPNAME: 'Oreo' },
    },
    {
        name: 'Popeyes', image: 'popeyes.png', cpu: 8, ram: '16G', drive: '100Gi', gpu: 'mig-3g.20gb',
        env_defaults: { PASSWORD: () => 'popeyes-' + randomToken(6), PWA_APPNAME: 'Popeyes' },
    },
    {
        name: 'Pizza', image: 'pizza.png', cpu: 8, ram: '32G', drive: '200Gi', gpu: 'gpu',
        env_defaults: { PASSWORD: () => 'pizza-' + randomToken(6), PWA_APPNAME: 'Pizza' },
    },
    {
        name: 'Spagetti', image: 'spagetti.png', cpu: 16, ram: '64G', drive: '500Gi', gpu: 'gpu:2',
        env_defaults: { PASSWORD: () => 'spagetti-' + randomToken(6), PWA_APPNAME: 'Spagetti' },
    },
]

function defaultForm() {
    return {
        name: 'My workspace',
        cpu: 2,
        ram: '4G',
        drive: '20Gi',
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
        drive: form.drive,
        gpu: form.gpu === 'none' ? '' : form.gpu,
        docker_repository: form.docker_repository,
        docker_tag: form.docker_tag,
        env_vars: { ...form.env_vars },
        exposed_ports: parsePorts(form.ports_text),
        container_command: parseCommand(form.command_text),
    }
}

function normalizeBulkItem(raw) {
    const item = { ...raw }
    if (item.gpu === 'none') item.gpu = ''
    if (typeof item.ports === 'string') item.exposed_ports = parsePorts(item.ports)
    else if (item.ports_text) item.exposed_ports = parsePorts(item.ports_text)
    else if (!item.exposed_ports) item.exposed_ports = [8080]
    if (typeof item.command === 'string') item.container_command = parseCommand(item.command)
    else if (item.command_text) item.container_command = parseCommand(item.command_text)
    if (!item.docker_repository && item.image) item.docker_repository = item.image
    return item
}

function parseCsvBulk(text) {
    const lines = text.trim().split(/\r?\n/).filter((l) => l.trim())
    if (lines.length < 2) throw new Error('CSV needs header + at least one row')
    const headers = lines[0].split(',').map((h) => h.trim())
    const items = []
    for (let i = 1; i < lines.length; i++) {
        const cols = lines[i].split(',').map((c) => c.trim().replace(/^"|"$/g, ''))
        const row = {}
        const env_vars = {}
        headers.forEach((h, j) => {
            const val = cols[j] ?? ''
            if (h.startsWith('env_')) env_vars[h.slice(4)] = val
            else if (h === 'env_json') {
                try { Object.assign(env_vars, JSON.parse(val || '{}')) } catch (_) { /* skip */ }
            } else row[h] = val
        })
        if (Object.keys(env_vars).length) row.env_vars = env_vars
        if (row.cpu) row.cpu = parseInt(row.cpu, 10)
        items.push(normalizeBulkItem(row))
    }
    return items
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
            drive: ['20Gi', '50Gi', '100Gi', '200Gi', '500Gi', '1Ti'],
            gpu: ['none', 'mig-2g.10gb', 'mig-3g.20gb', 'gpu', 'gpu:2'],
        },
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
        dockerImages: [],
        myWorkspaces: [],
        adminWorkspaces: [],
        adminPagination: { page: 1, pages: 1, total: 0, per_page: 12 },
        adminServerFilter: '',
        adminDockerImages: [],
        newImage: { label: '', repository: '', default_tag: 'latest' },
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
    },
    computed: {
        canConfirmDelete() {
            return this.deleteConfirmInput.trim().toLowerCase() === 'delete'
        },
        visibleTabs() {
            const tabs = [
                { id: 'home', label: 'Home' },
                { id: 'servers', label: 'My servers' },
            ]
            if (this.is_admin) {
                tabs.push({ id: 'admin-users', label: 'Users' })
                tabs.push({ id: 'admin-servers', label: 'Servers' })
                tabs.push({ id: 'admin-images', label: 'Images' })
            }
            return tabs
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
    methods: {
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
            this.menu = menu
            window.history.replaceState({}, '', '/?tab=' + menu)
            if (menu === 'servers') this.loadMyWorkspaces()
            if (menu === 'admin-servers') this.loadAdminWorkspaces(1)
            if (menu === 'admin-users') this.getAllUsers()
            if (menu === 'admin-images') this.loadAdminDockerImages()
        },
        async init() {
            if (!this.is_login) return
            await this.getCurrentUserState()
            await this.loadDockerImages()
            await this.loadMyWorkspaces()
            if (this.is_admin) {
                await this.getAllUsers()
                await this.loadAdminDockerImages()
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
            this.form.drive = t.drive
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
        onBulkFileSelected(event) {
            const file = event.target.files && event.target.files[0]
            if (!file) return
            const ext = (file.name.split('.').pop() || '').toLowerCase()
            if (ext === 'csv') this.bulkMode = 'csv'
            else if (ext === 'json') this.bulkMode = 'json'
            else {
                this.showToast('Use .json or .csv file')
                event.target.value = ''
                return
            }
            const reader = new FileReader()
            reader.onload = (ev) => {
                this.bulkText = ev.target.result || ''
                this.bulkFileName = file.name
                this.bulkSummary = ''
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
                this.bulkSummary = `Done: ${data.ok} ok, ${data.failed} failed (${items.length} total)`
                await this.loadMyWorkspaces()
            } catch (e) {
                this.bulkSummary = e.message || String(e)
            } finally {
                this.bulkLoading = false
            }
        },
        async runWorkspace() {
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
