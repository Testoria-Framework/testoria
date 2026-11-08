pipeline {
  agent any
  parameters {
    choice(name: 'LANGUAGE', choices: ['all', 'python', 'javascript', 'java', 'specs'], description: 'Suites to run')
    choice(name: 'TEST_TYPE', choices: ['all', 'functional', 'integration', 'security', 'performance'], description: 'Test type')
    string(name: 'API_BASE_URL', defaultValue: '', description: 'Target API (empty = bundled demo API)')
  }
  options { timestamps(); timeout(time: 60, unit: 'MINUTES') }
  stages {
    stage('Install') {
      steps { sh './install.sh --no-path --yes --js --java' }
    }
    stage('Test') {
      steps {
        sh '''
          args="--language ${LANGUAGE} --type ${TEST_TYPE}"
          [ -n "${API_BASE_URL}" ] && args="$args --base-url ${API_BASE_URL}"
          bash scripts/run_tests.sh $args
        '''
      }
    }
  }
  post {
    always {
      junit allowEmptyResults: true, testResults: 'reports/**/*junit*.xml, target/surefire-reports/*.xml'
      archiveArtifacts allowEmptyArchive: true, artifacts: 'reports/**'
    }
  }
}
