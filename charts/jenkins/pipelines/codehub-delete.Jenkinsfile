/**
 * Delete codehub — equivalent to DeepOps API:
 *   POST /stop_server/{username}
 *   → remove_codehub(username)  (helm uninstall {NAMESPACE}-{username})
 */
pipeline {
    agent { label 'jenkins-agent' }

    parameters {
        string(name: 'USERNAME', defaultValue: '', description: '[API] Path param username (required)')
        string(name: 'NAMESPACE', defaultValue: 'dohub', description: '[API] NAMESPACE env — Helm/K8s namespace')
        booleanParam(name: 'SKIP_HELM', defaultValue: false, description: 'Dry-run: print command only')
        booleanParam(name: 'WAIT_POD_DELETE', defaultValue: true, description: 'Wait for pods with user label to terminate')
        booleanParam(name: 'CHECKOUT_REPO', defaultValue: true, description: 'git checkout scm for scripts')
    }

    stages {
        stage('Validate') {
            steps {
                script {
                    if (!params.USERNAME?.trim()) {
                        error('USERNAME is required (same as /stop_server/{username})')
                    }
                }
            }
        }

        stage('Checkout') {
            when { expression { params.CHECKOUT_REPO } }
            steps {
                checkout scm
            }
        }

        stage('Delete codehub') {
            steps {
                withEnv([
                    "USERNAME=${params.USERNAME.trim()}",
                    "NAMESPACE=${params.NAMESPACE}",
                    "SKIP_HELM=${params.SKIP_HELM}",
                ]) {
                    sh '''
                        chmod +x charts/jenkins/scripts/codehub-delete.sh
                        charts/jenkins/scripts/codehub-delete.sh
                    '''
                }
            }
        }

        stage('Wait for pods') {
            when { expression { params.WAIT_POD_DELETE && !params.SKIP_HELM } }
            steps {
                sh '''
                    kubectl wait --for=delete pod \
                      -l "${NAMESPACE}-username=${USERNAME}" \
                      -n "${NAMESPACE}" --timeout=180s 2>/dev/null || true
                    kubectl get pods -n "${NAMESPACE}" -l "${NAMESPACE}-username=${USERNAME}" 2>/dev/null || echo "No pods left."
                '''
            }
        }
    }

    post {
        success {
            echo "Removed codehub release ${params.NAMESPACE}-${params.USERNAME}"
        }
    }
}
