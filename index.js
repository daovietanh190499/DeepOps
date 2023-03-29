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
                short_description: '1x vCPU, 0 GB GPU',
                cpu: 2,
                ram: '4 GB',
                drive: '30 TB',
                gpu: '0 GB'
            },
            'Oreo': {
                name: 'Oreo',
                image: 'oreo.png',
                docker_image: "daovietanh99/deepops",
                short_description: '4x vCPU, 10 GB GPU',
                cpu: 4,
                ram: '8 GB',
                drive: '30 TB',
                gpu: '10 GB'
            },
            'Popeyes': {
                name: 'Popeyes',
                image: 'popeyes.png',
                docker_image: "daovietanh99/deepops",
                short_description: '8x vCPU, 20 GB GPU',
                cpu: 8,
                ram: '16 GB',
                drive: '30 TB',
                gpu: '20 GB'
            },
            'Pizza': {
                name: 'Pizza',
                image: 'pizza.png',
                docker_image: "daovietanh99/deepops",
                short_description: '8x vCPU, 40 GB GPU',
                cpu: 8,
                ram: '32 GB',
                drive: '30 TB',
                gpu: '40 GB'
            },
            'Spagetti': {
                name: 'Spagetti',
                image: 'spagetti.png',
                docker_image: "daovietanh99/deepops",
                short_description: '16x vCPU, 2x 40 GB GPU',
                cpu: 16,
                ram: '64 GB',
                drive: '30 TB',
                gpu: '40 GB'
            }
        },
        menu: "home",
        server: "Lollipop",
        is_admin: true
    },
    mounted () {
        
    },
    methods: {
        changeMenu(menu) {
            this.menu = menu
        },
        changeServer(server) {
            this.server = server
        }
    }
})