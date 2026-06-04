/**
 * Spawn codehub — equivalent to DeepOps API POST /start_server/{username}
 * Uses DirectPV PVC (storageClass directpv-min-io, WaitForFirstConsumer).
 */
pipeline {
    agent { label 'jenkins-agent' }

    parameters {
        string(name: 'USERNAME', defaultValue: '', description: '[API] username (required)')
        string(name: 'PASSWORD', defaultValue: '', description: '[API] access_password (required)')
        string(name: 'CPU', defaultValue: '2', description: '[API] ServerOption.cpu')
        string(name: 'RAM', defaultValue: '4G', description: '[API] ServerOption.ram')
        string(name: 'GPU', defaultValue: 'none', description: '[API] ServerOption.gpu')
        string(name: 'DOCKER_IMAGE', defaultValue: 'codercom/code-server', description: '[API] docker_image')
        string(name: 'IMAGE_TAG', defaultValue: '4.89.0-ubuntu', description: '[API] image tag')
        string(name: 'VOLUME_SIZE', defaultValue: '20Gi', description: '[API] config volumeSize / persistence.size')
        string(name: 'STORAGE_CLASS', defaultValue: 'directpv-min-io', description: '[API] storage.storageClassName')
        string(name: 'NAMESPACE', defaultValue: 'dohub', description: '[API] NAMESPACE')
        string(name: 'DOMAIN_NAME', defaultValue: 'dohub.com', description: '[API] DOMAIN_NAME')
        string(name: 'DEFAULT_PORT', defaultValue: '8080', description: '[API] DEFAULT_PORT')
        string(name: 'CODEHUB_CHART_PATH', defaultValue: 'charts/codehub', description: 'Helm chart path')
        booleanParam(name: 'SKIP_HELM', defaultValue: false, description: 'Dry-run')
        booleanParam(name: 'CHECKOUT_REPO', defaultValue: true, description: 'git checkout scm')
    }

    stages {
        stage('Validate') {
            steps {
                script {
                    if (!params.USERNAME?.trim()) { error('USERNAME is required') }
                    if (!params.PASSWORD?.trim()) { error('PASSWORD is required') }
                }
            }
        }

        stage('Checkout') {
            when { expression { params.CHECKOUT_REPO } }
            steps { checkout scm }
        }

        stage('Spawn codehub') {
            steps {
                script {
                    def chartPath = params.CODEHUB_CHART_PATH.startsWith('/')
                        ? params.CODEHUB_CHART_PATH
                        : "${env.WORKSPACE}/${params.CODEHUB_CHART_PATH}"

                    withEnv([
                        "USERNAME=${params.USERNAME.trim()}",
                        "PASSWORD=${params.PASSWORD}",
                        "CPU=${params.CPU}",
                        "RAM=${params.RAM}",
                        "GPU=${params.GPU}",
                        "DOCKER_IMAGE=${params.DOCKER_IMAGE}",
                        "IMAGE_TAG=${params.IMAGE_TAG}",
                        "VOLUME_SIZE=${params.VOLUME_SIZE}",
                        "STORAGE_CLASS=${params.STORAGE_CLASS}",
                        "NAMESPACE=${params.NAMESPACE}",
                        "DOMAIN_NAME=${params.DOMAIN_NAME}",
                        "DEFAULT_PORT=${params.DEFAULT_PORT}",
                        "CODEHUB_CHART_PATH=${chartPath}",
                        "SKIP_HELM=${params.SKIP_HELM}",
                    ]) {
                        sh '''
                            chmod +x charts/jenkins/scripts/codehub-spawn.sh
                            charts/jenkins/scripts/codehub-spawn.sh
                        '''
                    }
                }
            }
        }
    }

    post {
        success {
            echo "OK: ${params.USERNAME} — PVC ${params.VOLUME_SIZE} (${params.STORAGE_CLASS})"
        }
    }
}
