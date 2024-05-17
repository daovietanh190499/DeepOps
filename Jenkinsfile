def label = 'build-agent'

node(label) {
    stage("Checkout SCM") {
        print "Checkout SCM"
        def repoURL = checkout scm
        print "Checkout ${repoURL}"
        print "Checkout SCM Successfully"
    }
    stage('Read Properties') {
        print "Read properties from Jenkins.properties"
        def props = readProperties file: 'Jenkins.properties'
        props.each { key, value ->
            env[key] = value
            print "${key}=${value}"
        }
        print "Read properties from Jenkins.properties Completed"
    }

    get_environment()

    if (env.BRANCH_NAME == 'staging') {
        sonar_scan()
    } else {
        echo "Skipping SonarQube analysis for branch ${env.BRANCH_NAME}"
    }

    build_image()
    deploy_with_helm_chart()
}

def get_environment() {
    stage("Get Build Environment") {
        print "Get build environment from devops repo"
        dir('devops') {
            git branch: 'main', credentialsId: env.GITHUB_CREDENTIALS_ID, url: env.HELM_CHART_REPO
        }
        print "Get build environment from devops repo Completed"
    }
}

def sonar_scan() {
    stage('SonarQube') {
        print "Run Sonar Scan inside sonar-scan-cli docker container"
        docker.withRegistry("http://${env.DOCKER_REGISTRY_URL}"){
            docker.image(env.SONARQUBE_CLI_DOCKER_IMAGE).inside{
               def scannerHome = tool "${env.SONARQUBE_TOOL_NAME}"
                withSonarQubeEnv(installationName: "${env.SONARQUBE_INSTALLATION_NAME}", credentialsId: "${env.SONARQUBE_CREDENTIALS_ID}") {
                    def scannerProperties = [
                        "sonar.projectKey": "${env.SONARQUBE_PROJECT_KEY}",
                        "jenkins": "${env.JOB_NAME}/${env.BUILD_NUMBER}"
                    ]
                    sh "${scannerHome}/sonar-scanner ${scannerProperties.collect { "-D${it.key}=${it.value}" }.join(' ')}"
                }
            }
        }
        print "Run Sonar Scan inside sonar-scan-cli docker container Completed"
    }
}

def getName(name, branchName) {
    if("development".equals(branchName)) {
        return "${name}-dev"
    } else if("staging".equals(branchName)) {
        return "${name}-staging";
    } else {
        return "${name}"
    }
}

def build_image() {
    stage('Build Image') {
        print "Build Docker image"

        def name = getName(env.RELEASE_NAME, env.BRANCH_NAME)

        sh "cp devops/${env.HELM_CHART_DIRECTORY}/secrets/${env.BRANCH_NAME}/.env .env"

        sh "docker build --rm=false -t ${env.DOCKER_REGISTRY_URL}/${name} -f Dockerfile \
            --build-arg pip_index=${env.PYTHON_INDEX} \
            --build-arg pip_index_host=${env.PYTHON_INDEX_HOST} \
            --build-arg pip_index_url=${env.PYTHON_INDEX_URL} \
            --build-arg use_apt_proxy=${env.USE_APT_REPOSITORY} \
            --build-arg docker_registry_url=${env.DOCKER_REGISTRY_URL} \
            ."
        sh "docker push ${env.DOCKER_REGISTRY_URL}/${name}"
        print "Build Docker image Completed"
    }
}

def deploy_with_helm_chart() {
    stage('Deploy') {
        print "Deploy with Helm chart"

        git branch: 'main', credentialsId: env.GITHUB_CREDENTIALS_ID, url: env.HELM_CHART_REPO
        sh "ls -lart ./*"

        def name = getName(env.RELEASE_NAME, env.BRANCH_NAME)
        def namespace = getName(env.NAMESPACE, env.BRANCH_NAME)
        def values_file = getName('values', env.BRANCH_NAME)

        sh "helm upgrade ${name} ${env.HELM_CHART_DIRECTORY} --install \
            --create-namespace --namespace ${namespace} --reset-values --values ${env.HELM_CHART_DIRECTORY}/${values_file}.yaml"

        sh "kubectl rollout restart deployment.apps/${name} -n ${namespace}"

        sh "kubectl delete replicaset \$(kubectl get replicaset -n ${namespace} -o jsonpath='{.items[?(@.spec.replicas==0)].metadata.name }') -n ${namespace}"

        print "Deploy with Helm chart Completed"
    }
}