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

var userRow = Vue.component('user-row', {
    props: ['user', 'server_list'],
    data() {
        return {
            is_open_dropdown: false,
            filter: ""
        }
    },
    methods: {
        openServerList() {
            this.is_open_dropdown = !this.is_open_dropdown
        },
        chooseServer(server) {
            this.is_open_dropdown = false
            if(server) {
                this.$emit('admin_add_server_user', server)
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
                <div class="item-block-value" style="width: 15%;">{{user.state}}</div>
                <div class="user-space"></div>
                <div class="item-block-value" style="width: 10%;">{{user.role}}</div>
                <div class="user-space"></div>
                <div class="item-block-value" style="width: 10%">13 seconds ago</div>
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
                docker_image: "daovietanh99/deepops",
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
        state: "offline"
    },
    created () {
        this.getInfo()
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
            await this.getAllUsers()
            await this.getCurrentUserState()
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
            this.getInfo()
            this.menu = menu
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
        startServer() {
            if(this.current_user == this.current_spawn_user || (this.current_user != this.current_spawn_user && this.is_admin)) {
                fetch(`start_server/${this.current_spawn_user}`)
                .then(res => {
                    if(res.status == 200){
                        this.state = "running"
                    }
                })
            }
        },
        stopServer() {
            if(this.current_user == this.current_spawn_user || (this.current_user != this.current_spawn_user && this.is_admin)) {
                fetch(`stop_server/${this.current_spawn_user}`)
                .then(res => {
                    if(res.status == 200){
                        this.state = "offline"
                    }
                })
            }
        },
        accessServer() {
            if(this.current_user == this.current_spawn_user || (this.current_user != this.current_spawn_user && this.is_admin)) {
                this.state = "running"
            }
        }
    }
})