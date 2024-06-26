var slider = Vue.component('slider', {
    props: ["labels", "value", "disabled"],
    methods: {
        change_value(e) {
            this.$emit('change_value', this.labels[e.target.value - 1])
        }
    },
    mounted() {
        
    },
    template: `
    <div class="equipment-slider center">
        <div class="label-slider bottom">
            <div class="label-container space-between">
                <span v-for="label in labels" class="label-slider-label" :style="{width: 100/labels.length + '%'}">
                    {{label}}
                </span>
            </div>
        </div>
        <div class="tick-slider-background"></div>
        <div class="tick-slider-progress" :style="{width: ((labels.indexOf(value) + 1)*100)/labels.length + '%'}"></div>
        <div class="tick-slider-tick-container">
            <span v-for="index in (labels.length + 1)" 
                    :class="{'tick-slider-tick': index <= (labels.indexOf(value) + 1), 'tick-slider-tick-gray': index > (labels.indexOf(value) + 1)}" 
                    :key="index">
            </span>
        </div>
        <input
            :disabled="disabled"
            class="tick-slider-input"
            type="range"
            min="0"
            :max="labels.length"
            step="1"
            :value="labels.indexOf(value) + 1"
            @input="change_value"
        />
    </div>`
})

var itemBlock = Vue.component('item-block', {
    props: ["title", "img", "short_description", "space", "hover_blue", "activate", "button"],
    template: `
    <div class="item-block vertical-flex" 
        @click="$emit('click')"
        :class="{'hover-blue': hover_blue, 'button': button, 'activate': activate}"
        :style="{'margin-right': space ? '1.5rem' : 0}">
        <img :src="'static/img/' + img" class="item-block-img">
        <div class="item-block-metric horizontal-flex">
            <span class="item-block-title">{{title}}</span>
            <span class="item-block-value">{{short_description}}</span>
        </div>
    </div>
    `
})

var specificationItem = Vue.component('specification-item', {
    props: ["item_key", "value"],
    template: `
    <div class="specification-item space-between">
        <div class="specification-key">{{item_key}}:</div>
        <div class="specification-value">{{value}}</div>
    </div>
    `
})

var equipmentMetric = Vue.component('equipment-metric', {
    props: ['item_key', 'value'],
    template: `
    <div class="equipment-metric horizontal-flex">
        <span class="equipment-metric-title">{{item_key}}</span>
        <span class="equipment-metric-value">{{value}}</span>
    </div>
    `
})

var serverLog = Vue.component('server-log', {
    props: ['message', 'reason'],
    template: `
    <div class="list-plan horizontal-flex">
        <div class="input-text"> {{message}}: {{reason}} </div>
    </div>
    `
})

var userRow = Vue.component('user-row', {
    props: ['user', 'server_list'],
    data() {
        return {
            is_open_dropdown: false,
            is_open_dropdown_role: false,
            filter: "",
            last_activity: "--.--"
        }
    },
    created () {
        let duration = (Date.now() - parseFloat(this.user.last_activity))/1000
        if(duration < 60) {
            this.last_activity = Math.round(duration) + ' seconds'
        } else if(duration < 3600) {
            this.last_activity = Math.round(duration/60) + ' minutes'
        } else if(duration < 3600*24) {
            this.last_activity = Math.round(duration/3600) + ' hours'
        } else {
            this.last_activity = Math.round(duration/(3600*24)) + ' days'
        }
    },
    methods: {
        openServerList() {
            this.is_open_dropdown = !this.is_open_dropdown
        },
        openRoleList() {
            this.is_open_dropdown_role = !this.is_open_dropdown_role
        },
        chooseServer(server) {
            this.is_open_dropdown = false
            if(server) {
                this.$emit('admin_add_server_user', server)
            }
        },
        chooseRole(role) {
            this.is_open_dropdown_role = false
            if(role) {
                this.$emit('admin_change_role_user', role)
            }
        },
        deleteServer(server) {
            this.is_open_dropdown = false
            this.$emit('admin_delete_server_user', server)
        }
    },
    template: `
    <div class="user-row vertical-flex space-between">
        <div class="vertical-flex user-cell center">
            <img :src="(user && user.image && user.image !== '') ? user.image : 'static/img/logo.png'" class="item-block-img">
        </div>
        <div class="horizontal-flex space-between user-cell user-cell-info">
            <div class="vertical-flex space-between row-block-title">
                <div class="item-block-title" style="width: 15%;">{{user.username}}</div>
                <div class="user-space"></div>
                <div class="item-block-title" style="width: 10%;">Role</div>
                <div class="user-space"></div>
                <div class="item-block-title" style="width: 10%">Last Activity</div>
                <div class="user-space"></div>
                <div class="item-block-title" style="width: 40%;">Server List</div>
                <div class="user-space"></div>
                <div class="item-block-title" style="width: 10%;">Server</div>
                <div class="user-space"></div>
                <div class="item-block-title" style="width: 15%;">Running</div>
            </div>
            <div class="vertical-flex">
                <div class="item-block-value" style="width: 15%; font-weight: 700"
                    :style="{'color': user.state == 'running' ? '#00c851' : (user.state == 'offline' ? '#ff4444' : '#ffbb33')}"
                > • {{user.state}} </div>
                <div class="user-space"></div>
                <div class="item-block-value" style="width: 10%;">
                    <div class="dropdown">
                        <div class="tag button" 
                            :style="{'background-color': '#3450ee'}"
                            @click="openRoleList()">
                            {{user.role}}
                        </div>
                        <div class="dropdown-content" v-if="is_open_dropdown_role">
                            <div class="dropdown-items">
                                <a @click="chooseRole('admin')">
                                    admin
                                </a>
                                <a @click="chooseRole('normal_user')">
                                    normal_user
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="user-space"></div>
                <div class="item-block-value" style="width: 10%">{{last_activity}}</div>
                <div class="user-space"></div>
                <div class="item-block-value" style="width: 40%;">
                    <div class="tag" 
                        v-for="server in user.server_list" 
                        :style="{'background-color': server_list[server]['color']}" v-if="user.server_list">
                        {{server}} <span class="close-tag" @click="deleteServer(server)"><i class="fa fa-close"></i></span>
                    </div>
                    <div class="dropdown">
                        <div class="tag add-tag button" 
                            @click="openServerList()">
                            Add <span class="close-tag"><i class="fa fa-plus"></i></span>
                        </div>
                        <div class="dropdown-content" v-if="is_open_dropdown">
                            <input type="text" placeholder="Search.." class="search-dropdown" v-model="filter">
                            <a @click="chooseServer(undefined)"> None </a>
                            <div class="dropdown-items">
                                <a v-for="server in Object.keys(server_list)" 
                                    :style="{'color': server_list[server]['color']}"
                                    @click="chooseServer(server)"
                                    v-if="server.toUpperCase().indexOf(filter.toUpperCase()) > -1"
                                >
                                    {{server}}
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="user-space"></div>
                <div class="item-block-value" style="width: 10%;">
                    <div class="tag" :style="{'background-color': server_list[user.current_server]['color']}" v-if="user.current_server">{{user.current_server}}</div>
                </div>
                <div class="user-space"></div>
                <div class="item-block-value" style="width: 15%;">
                    <button class="button-user button" v-if="user.is_accept && user.state=='offline'" @click="$emit('admin_open_spawn')">Start Server</button>
                    <button class="button-user-2 button" v-if="user.is_accept && user.state=='running'" @click="$emit('admin_stop_server')">Stop Server</button>
                    <button class="button-user-1 button" v-if="user.is_accept && user.state=='running'" @click="$emit('admin_open_spawn')">Spawn Page</button>
                    <button class="button-user-3 button" v-if="!user.is_accept" @click="$emit('admin_accept_user')">Accept User</button>
                    <button class="button-user-2 button" v-if="user.state!='running'" @click="$emit('admin_delete_user')">Delete User</button>
                </div>
            </div>
        </div>
    </div>
    `
})

const appVue = new Vue({
    el: '#root',
    data: {
        equipmentList: {
            cpu: {
                labels: [2,4,8,16,32],
            },
            ram: {
                labels: ['2G','4G','8G','16G','32G','64G'],
            },
            drive: {
                labels: ['20GB', '100GB', '500GB', '1TB', '10TB', '30TB'],
            },
            gpu: {
                labels: ['none', 'mig-2g.10gb', 'mig-3g.20gb', 'gpu', 'gpu:2'],
            }
        },
        serverList: {
            'Lollipop': {
                name: 'Default',
                image: 'logo.png',
                docker_image: "codercom/code-server",
                cpu: 2,
                ram: '2G',
                drive: '20GB',
                gpu: 'none',
                color: "#fcb040"
            }
        },
        userList: [],
        is_login: is_login,

        menu: "home",
        current_user: "",
        is_admin: false,

        server: "Lollipop",
        current_spawn_user: "",
        current_server_list: [],
        admin_open_spawn: false,
        access_password: "",
        state: "offline",
        server_log: {
            message: "Idle",
            reason: "Idling"
        },

        socket_change_state: null
    },
    created () {
        this.getInfo()
        const params = new Proxy(new URLSearchParams(window.location.search), {
            get: (searchParams, prop) => searchParams.get(prop),
        });
        this.menu = params.tab ? params.tab : "home"
    },
    methods: {
        loginWithGithub() {
            window.location = 'login'
        },
        logout() {
            window.location = 'logout'
        },
        async getInfo() {
            await this.getAllServers()
            await this.getCurrentUserState()
            await this.getAllUsers()
        },
        setupSocket() {
            if(this.socket_change_state) {
                this.socket_change_state.close()
            }
            try {
                this.socket_change_state = new WebSocket('wss://' + window.location.hostname + ':3112/state_change/' + this.current_spawn_user)
            } catch {
                this.socket_change_state = null
            }
            this.socket_change_state.onmessage = e => {
                this.state = e.data
                this.socket_change_state.close()
            }
        },
        async getCurrentUserState() {
            if(this.is_login) {
                return fetch('user_state')
                    .then(res => {
                        if(res.status == 200) {
                            return res.json()
                        } else {
                            return null
                        }
                    })
                    .then(res => {
                        if(res) {
                            this.current_user = res['result']['username']
                            this.current_spawn_user = this.current_user
                            this.admin_open_spawn = false
                            this.server = res['result']['current_server']
                            this.current_server_list = res['result']['server_list']
                            this.is_admin = res['result']['role'] == 'admin'
                            this.state = res['result']['state']
                            this.access_password = res['result']['access_password']
                            this.server_log = res['result']['server_log']
                            this.setupSocket()
                        }
                    })
            }
            return
        },
        async getAllUsers() {
            if(this.is_admin) {
                return fetch('all_users')
                    .then(res => {
                        if(res.status == 200) {
                            return res.json()
                        } else {
                            return {'result': []}
                        }
                    })
                    .then(res => {
                        this.userList = res['result']
                    })
            }
            return
        },
        async getAllServers() {
            return fetch('all_servers')
                .then(res => res.json())
                .then(res => {
                    this.serverList = res['result']
                })
        },
        changeMenu(menu) {
            window.location.replace("/?tab=" + menu)
        },
        changeServer(server) {
            if(this.state=="offline") {
                fetch(`change_server/${this.current_spawn_user}/${server}`)
                .then(res => {
                    if(res.status == 200){
                        this.server = server
                    }
                })
            }
        },
        adminOpenSpawnPage(user) {
            if(this.is_admin) {
                this.getAllServers()
                this.admin_open_spawn = true
                this.current_spawn_user = user.username
                this.state = user.state
                this.server = user.current_server
                this.current_server_list = user.server_list
                this.access_password = user.access_password
                this.server_log = user.server_log
            }
        },
        adminStopServer(user) {
            if(this.is_admin) {
                fetch(`stop_server/${user.username}`)
                .then(res => {
                    this.getAllUsers()
                })
            }
        },
        adminAcceptUser(user) {
            if(this.is_admin) {
                fetch('accept_user/' + user['username'])
                .then(res => {
                    this.getAllUsers()
                })
            }
        },
        adminDeleteUser(user) {
            if(this.is_admin) {
                fetch('delete_user/' + user['username'])
                .then(res => {
                    this.getAllUsers()
                })
            }
        },
        adminAddServerUser(user, server) {
            if(this.is_admin) {
                fetch(`add_server_user/${user['username']}/${server}`)
                .then(res => {
                    this.getAllUsers()
                })
            }
        },
        adminDeleteServerUser(user, server) {
            if(this.is_admin) {
                fetch(`delete_server_user/${user['username']}/${server}`)
                .then(res => {
                    this.getAllUsers()
                })
            }
        },
        adminChangeRoleUser(user, role) {
            if(this.is_admin) {
                fetch(`change_role/${user['username']}/${role}`)
                .then(res => {
                    this.getAllUsers()
                })
            }
        },
        startServer() {
            if(this.current_user == this.current_spawn_user || (this.current_user != this.current_spawn_user && this.is_admin)) {
                fetch(`start_server/${this.current_spawn_user}`)
                .then(res => {
                    if(res.status == 200){
                        this.state = "pending_start"
                        this.setupSocket()
                    }
                })
            }
        },
        stopServer() {
            if(this.current_user == this.current_spawn_user || (this.current_user != this.current_spawn_user && this.is_admin)) {
                fetch(`stop_server/${this.current_spawn_user}`)
                .then(res => {
                    if(res.status == 200){
                        this.state = "pending_stop"
                        this.setupSocket()
                    }
                })
            }
        },
        accessServer() {
            if(this.current_user == this.current_spawn_user || (this.current_user != this.current_spawn_user && this.is_admin)) {
                window.location = `${window.location.protocol}//${this.current_spawn_user}.${window.location.host}`
                this.state = "running"
            }
        }
    }
})