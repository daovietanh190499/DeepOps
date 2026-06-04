def repoScripts = 'charts/jenkins/pipelines'

pipelineJob('codehub-spawn') {
  description('Spawn codehub via DirectPV — POST /start_server/{username}')
  parameters {
    stringParam('USERNAME', '', 'required')
    stringParam('PASSWORD', '', 'required')
    stringParam('CPU', '2', '')
    stringParam('RAM', '4G', '')
    stringParam('GPU', 'none', '')
    stringParam('DOCKER_IMAGE', 'codercom/code-server', '')
    stringParam('IMAGE_TAG', '4.89.0-ubuntu', '')
    stringParam('VOLUME_SIZE', '20Gi', 'DirectPV PVC size')
    stringParam('STORAGE_CLASS', 'directpv-min-io', '')
    stringParam('NAMESPACE', 'dohub', '')
    stringParam('DOMAIN_NAME', 'dohub.com', '')
    stringParam('DEFAULT_PORT', '8080', '')
    stringParam('CODEHUB_CHART_PATH', 'charts/codehub', '')
    booleanParam('SKIP_HELM', false, '')
    booleanParam('CHECKOUT_REPO', true, '')
  }
  definition {
    cpsScm {
      scm {
        git {
          remote { url('https://github.com/daovietanh190499/DeepOps.git') }
          branch('*/main')
        }
      }
      scriptPath("${repoScripts}/codehub-spawn.Jenkinsfile")
    }
  }
}

pipelineJob('codehub-delete') {
  description('Remove codehub — POST /stop_server/{username}')
  parameters {
    stringParam('USERNAME', '', 'required')
    stringParam('NAMESPACE', 'dohub', '')
    booleanParam('SKIP_HELM', false, '')
    booleanParam('WAIT_POD_DELETE', true, '')
    booleanParam('CHECKOUT_REPO', true, '')
  }
  definition {
    cpsScm {
      scm {
        git {
          remote { url('https://github.com/daovietanh190499/DeepOps.git') }
          branch('*/main')
        }
      }
      scriptPath("${repoScripts}/codehub-delete.Jenkinsfile")
    }
  }
}
