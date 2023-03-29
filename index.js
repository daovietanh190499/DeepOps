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
        <img :src="'img/' + img" class="item-block-img">
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
    template: `
    <div class="user-row vertical-flex space-between">
        <div class="vertical-flex user-cell center">
            <img src="img/logo.png" class="item-block-img">
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
                    <div class="tag" v-for="server in user.server_list" :style="{'background-color': server_list[server]['color']}">{{server}} <span class="close-tag"><i class="fa fa-close"></i></span></div>
                    <div class="tag add-tag button">Add <span class="close-tag"><i class="fa fa-plus"></i></span></div>
                </div>
                <div class="user-space"></div>
                <div class="item-block-value" style="width: 10%;">
                    <div class="tag" :style="{'background-color': server_list[user.current_server]['color']}">{{user.current_server}}</div>
                </div>
                <div class="user-space"></div>
                <div class="item-block-value" style="width: 15%;">
                    <button class="button-user button" v-if="user.is_accept && user.state=='offline'" @click="$emit('admin_open_spawn')">Start Server</button>
                    <button class="button-user-2 button" v-if="user.is_accept && user.state=='running'" @click="$emit('admin_stop_server')">Stop Server</button>
                    <button class="button-user-1 button" v-if="user.is_accept && user.state=='running'" @click="$emit('admin_open_spawn')">Spawn Page</button>
                    <button class="button-user-3 button" v-if="!user.is_accept" @click="$emit('admin_accept_user')">Accept User</button>
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
                labels: ['2 GB','4 GB','8 GB','16 GB','32 GB','64 GB'],
            },
            drive: {
                labels: ['20 GB', '100 GB', '500 GB', '1 TB', '10 TB', '30 TB'],
            },
            gpu: {
                labels: ['0 GB', '10 GB', '20 GB', '40 GB'],
            }
        },
        serverList: {
            'Lollipop': {
                name: 'Lollipop',
                image: 'lollipop.png',
                docker_image: "daovietanh99/deepops",
                cpu: 2,
                ram: '4 GB',
                drive: '30 TB',
                gpu: '0 GB',
                color: 'violet'
            },
            'Oreo': {
                name: 'Oreo',
                image: 'oreo.png',
                docker_image: "daovietanh99/deepops",
                cpu: 4,
                ram: '8 GB',
                drive: '30 TB',
                gpu: '10 GB',
                color: '#1e88d2'
            },
            'Popeyes': {
                name: 'Popeyes',
                image: 'popeyes.png',
                docker_image: "daovietanh99/deepops",
                cpu: 8,
                ram: '16 GB',
                drive: '30 TB',
                gpu: '20 GB',
                color: "#f27802"
            },
            'Pizza': {
                name: 'Pizza',
                image: 'pizza.png',
                docker_image: "daovietanh99/deepops",
                cpu: 8,
                ram: '32 GB',
                drive: '30 TB',
                gpu: '40 GB',
                color: "#fcca37"
            },
            'Spagetti': {
                name: 'Spagetti',
                image: 'spagetti.png',
                docker_image: "daovietanh99/deepops",
                cpu: 16,
                ram: '64 GB',
                drive: '30 TB',
                gpu: '40 GB',
                color: "#fcb040"
            }
        },
        userList: [
            {
                username: "daovietanh99",
                role: "admin",
                image: "",
                las_activity: 1300,
                server_list: ['Lollipop', 'Oreo', 'Popeyes', 'Pizza', 'Spagetti'],
                current_server: 'Spagetti',
                is_accept: true,
                state: "running"
            },
            {
                username: "daovietanh19",
                role: "admin",
                image: "",
                las_activity: 1300,
                server_list: ['Lollipop', 'Oreo', 'Popeyes', 'Pizza'],
                current_server: 'Pizza',
                is_accept: false,
                state: "offline"
            }
        ],
        menu: "home",
        current_user: "",
        is_admin: false,

        server: "Lollipop",
        current_spawn_user: "",
        current_server_list: ['Lollipop', 'Oreo', 'Popeyes', 'Pizza', 'Spagetti'],
        admin_open_spawn: false,
        state: "offline"
    },
    mounted () {
        this.getCurrentUserState()
    },
    methods: {
        getCurrentUserState() {
            this.current_user = "daovietanh99"
            this.current_spawn_user = this.current_user
            this.admin_open_spawn = false
            this.server = 'Lollipop'
            this.current_server_list = ['Lollipop', 'Oreo', 'Popeyes', 'Pizza', 'Spagetti']
            this.is_admin = true
            this.state = "offline"
        },
        getAllUsers() {
            if(this.is_admin) {

            }
        },
        getAllServer() {

        },
        changeMenu(menu) {
            this.getCurrentUserState()
            this.getAllUsers()
            this.menu = menu
        },
        changeServer(server) {
            if(this.state=="offline") {
                this.server = server
            }
        },
        adminOpenSpawnPage(user) {
            if(this.is_admin) {
                this.getAllServer()
                this.admin_open_spawn = true
                this.current_spawn_user = user.username
                this.state = user.state
                this.server = user.current_server
                this.current_server_list = user.server_list
            }
        },
        adminStopServer(user) {
            if(this.is_admin) {
                this.getAllUsers()
            }
        },
        adminAcceptUser(user) {
            if(this.is_admin) {
                this.getAllUsers()
            }
        },
        startServer() {
            if(this.current_user == this.current_spawn_user || (this.current_user != this.current_spawn_user && this.is_admin)) {
                this.state = "running"
            }
        },
        stopServer() {
            if(this.current_user == this.current_spawn_user || (this.current_user != this.current_spawn_user && this.is_admin)) {
                this.state = "offline"
            }
        },
        accessServer() {
            if(this.current_user == this.current_spawn_user || (this.current_user != this.current_spawn_user && this.is_admin)) {
                this.state = "running"
            }
        }
    }
})