pipeline {
    agent any
    
    parameters {
        booleanParam(
            name: 'ROLLBACK_ONLY',
            defaultValue: false,
            description: 'Выполнить только rollback'
        )
    }
    
    environment {
        SERVICE_NAME = 'report-service'
        LAST_SUCCESS_FILE = 'last_successful_build.txt'
        APP_PORT = '8081'
        CONTAINER_PORT = '5000'
        // Явно указываем путь к Python
        PYTHON_PATH = '/usr/bin/python3'
    }
    
    stages {
        stage('Rollback Only') {
            when {
                expression { params.ROLLBACK_ONLY }
            }
            steps {
                script {
                    echo "🔙 Выполняется rollback..."
                    rollbackToPreviousVersion()
                }
            }
        }
        
        stage('Main Pipeline') {
            when {
                expression { !params.ROLLBACK_ONLY }
            }
            stages {
                stage('Test') {
                    steps {
                        echo "🧪 Запуск тестов..."
                        sh '''
                            echo "🔍 Проверка Python:"
                            /usr/bin/python3 --version
                            
                            echo "📥 Установка pytest глобально..."
                            /usr/bin/python3 -m pip install --upgrade pip
                            /usr/bin/python3 -m pip install pytest flask requests
                            
                            echo "📋 Список установленных пакетов:"
                            /usr/bin/python3 -m pip list
                            
                            echo "🧪 Запуск тестов..."
                            cd tests && /usr/bin/python3 -m pytest -v --tb=short
                        '''
                    }
                }
                
                stage('Build') {
                    steps {
                        echo "🏗️ Сборка Docker образа..."
                        sh """
                            docker build -t ${SERVICE_NAME}:${BUILD_NUMBER} .
                            docker images | grep ${SERVICE_NAME}
                        """
                    }
                }
                
                stage('Deploy') {
                    steps {
                        echo "🚀 Деплой..."
                        sh """
                            docker stop ${SERVICE_NAME} || true
                            docker rm ${SERVICE_NAME} || true
                            docker run -d -p ${APP_PORT}:${CONTAINER_PORT} --name ${SERVICE_NAME} ${SERVICE_NAME}:${BUILD_NUMBER}
                            sleep 3
                            docker ps | grep ${SERVICE_NAME}
                        """
                    }
                }
                
                stage('Health Check') {
                    steps {
                        echo "🏥 Проверка здоровья..."
                        sh """
                            for i in 1 2 3 4 5 6 7 8 9 10 11 12; do
                                echo "Попытка \$i/12..."
                                curl -f http://localhost:${APP_PORT}/health && exit 0
                                sleep 5
                            done
                            echo "Health check failed"
                            exit 1
                        """
                    }
                }
            }
        }
    }
    
    post {
        success {
            script {
                if (!params.ROLLBACK_ONLY) {
                    sh "echo ${BUILD_NUMBER} > ${LAST_SUCCESS_FILE}"
                    echo "✅ Версия ${BUILD_NUMBER} сохранена"
                }
            }
        }
        failure {
            script {
                echo "❌ Pipeline упал! Пытаемся откатиться..."
                script {
                    def lastVersion = sh(script: "cat ${LAST_SUCCESS_FILE} 2>/dev/null || echo 0", returnStdout: true).trim()
                    if (lastVersion != "0") {
                        sh """
                            docker stop ${SERVICE_NAME} || true
                            docker rm ${SERVICE_NAME} || true
                            docker run -d -p ${APP_PORT}:${CONTAINER_PORT} --name ${SERVICE_NAME} ${SERVICE_NAME}:${lastVersion}
                            echo "✅ Откат на версию ${lastVersion}"
                        """
                    }
                }
            }
        }
        always {
            cleanWs()
        }
    }
}