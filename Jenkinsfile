pipeline {
    agent {
        // Use different agents based on language
        matrix {
            agent {
                docker {
                    image 'python:3.9'
                    args '-u root'
                }
            }
            agent {
                docker {
                    image 'node:16'
                    args '-u root'
                }
            }
            agent {
                docker {
                    image 'maven:3.8.1-openjdk-11'
                    args '-u root'
                }
            }
        }
    }

    environment {
        // Environment variables
        GITHUB_CREDENTIALS = credentials('github-credentials')
        DOCKER_REGISTRY = 'your-docker-registry'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Setup') {
            parallel {
                stage('Python Setup') {
                    steps {
                        script {
                            if (isUnix()) {
                                sh '''
                                    python -m pip install --upgrade pip
                                    pip install -r requirements.txt
                                    pip install pytest pytest-cov allure-pytest
                                '''
                            }
                        }
                    }
                }

                stage('JavaScript Setup') {
                    steps {
                        script {
                            if (isUnix()) {
                                sh '''
                                    npm install
                                    npm install jest supertest
                                '''
                            }
                        }
                    }
                }

                stage('Java Setup') {
                    steps {
                        script {
                            if (isUnix()) {
                                sh '''
                                    mvn clean install -DskipTests
                                '''
                            }
                        }
                    }
                }
            }
        }

        stage('Test') {
            parallel {
                stage('Python Functional Tests') {
                    steps {
                        sh './scripts/run_tests.sh --language python --type functional --env ci'
                    }
                    post {
                        always {
                            junit 'reports/junit-report.xml'
                        }
                    }
                }

                stage('JavaScript Integration Tests') {
                    steps {
                        sh './scripts/run_tests.sh --language javascript --type integration --env ci'
                    }
                    post {
                        always {
                            junit 'reports/junit-report.xml'
                        }
                    }
                }

                stage('Java Security Tests') {
                    steps {
                        sh './scripts/run_tests.sh --language java --type security --env ci'
                    }
                    post {
                        always {
                            junit 'reports/junit-report.xml'
                        }
                    }
                }
            }
        }

        stage('Generate Reports') {
            steps {
                script {
                    sh 'pip install allure-pytest'
                    sh 'allure generate reports/allure-results -o reports/allure-report'
                }
            }
            post {
                success {
                    publishHTML(target: [
                        allowMissing: false,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: 'reports/allure-report',
                        reportFiles: 'index.html',
                        reportName: 'Allure Report'
                    ])
                }
            }
        }

        stage('Release') {
            when {
                buildingTag()
            }
            steps {
                script {
                    // Create release artifacts
                    sh 'tar -czvf api-testing-framework-${TAG_NAME}.tar.gz .'
                    
                    // GitHub Release
                    withCredentials([usernamePassword(credentialsId: 'github-credentials', usernameVariable: 'GITHUB_USER', passwordVariable: 'GITHUB_TOKEN')]) {
                        sh '''
                            curl -H "Authorization: token ${GITHUB_TOKEN}" \
                                 -H "Accept: application/vnd.github.v3+json" \
                                 -d "{
                                     \\"tag_name\\": \\"${TAG_NAME}\\",
                                     \\"target_commitish\\": \\"main\\",
                                     \\"name\\": \\"${TAG_NAME}\\",
                                     \\"body\\": \\"Release ${TAG_NAME}\\",
                                     \\"draft\\": false,
                                     \\"prerelease\\": false
                                 }" \
                                 https://api.github.com/repos/${GITHUB_USER}/api-testing-framework/releases
                        '''
                    }
                }
            }
            post {
                success {
                    archiveArtifacts artifacts: '*.tar.gz', fingerprint: true
                }
            }
        }
    }

    // Post-build actions
    post {
        always {
            // Clean workspace
            cleanWs()
        }
        failure {
            // Send notifications
            mail to: 'damineone@gmail.com',
                 subject: "Failed Pipeline: ${currentBuild.fullDisplayName}",
                 body: "Something is wrong with the pipeline ${env.BUILD_URL}"
        }
    }
}