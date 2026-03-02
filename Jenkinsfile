pipeline {
    agent any
    
    parameters {
        booleanParam(
            name: 'ROLLBACK_ONLY',
            defaultValue: false,
            description: 'Выполнить только rollback на предыдущую версию (без сборки и тестов)'
        )
    }
    
    environment {
        SERVICE_NAME = 'report-service'
        LAST_SUCCESS_FILE = 'last_successful_build.txt'
        APP_PORT = '8081'
        CONTAINER_PORT = '5000'
        
        // Автоматически находим где лежит Python
        PYTHON_PATH = sh(
            script: 'command -v python3 || command -v python || echo "/usr/bin/python3"',
            returnStdout: true
        ).trim()
        
        PYTHON_DIR = sh(
            script: "dirname ${PYTHON_PATH}",
            returnStdout: true
        ).trim()
        PATH = "${PYTHON_DIR}:/usr/local/bin:/usr/bin:/bin:${env.PATH}"
    }
    
    stages {
        stage('Rollback Only') {
            when {
                expression { params.ROLLBACK_ONLY }
            }
            steps {
                script {
                    echo "🔙 Выполняется rollback на предыдущую версию..."
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
                        script {
                            echo "🧪 Запуск тестов..."
                            runTests()
                        }
                    }
                }
                
                stage('Build') {
                    steps {
                        script {
                            echo "🏗️ Сборка Docker образа..."
                            buildDockerImage()
                        }
                    }
                }
                
                stage('Deploy') {
                    steps {
                        script {
                            echo "🚀 Деплой новой версии..."
                            deployNewVersion()
                        }
                    }
                }
                
                stage('Health Check') {
                    steps {
                        script {
                            echo "🏥 Проверка здоровья приложения..."
                            healthCheck()
                        }
                    }
                }
            }
        }
    }
    
    post {
        success {
            script {
                if (!params.ROLLBACK_ONLY) {
                    echo "✅ Pipeline успешно выполнен! Сохраняем версию..."
                    saveSuccessfulBuild()
                }
            }
        }
        
        failure {
            script {
                echo "❌ Pipeline упал! Выполняем rollback..."
                try {
                    rollbackToPreviousVersion()
                } catch (Exception e) {
                    echo "⚠️ Не удалось выполнить rollback: ${e.message}"
                }
            }
        }
        
        always {
            script {
                echo "📝 Очистка временных файлов..."
                cleanWs()
            }
        }
    }
}

def runTests() {
    sh '''
        echo "========================================="
        echo "🧪 ЗАПУСК ТЕСТОВ"
        echo "========================================="
        
        echo "🔍 Проверка Python:"
        python --version
        which python
        
        echo "\\n📦 Создание виртуального окружения..."
        python -m venv venv
        
        echo "\\n⚡ Активация виртуального окружения..."
        . venv/bin/activate
        
        echo "\\n📥 Установка зависимостей..."
        pip install --upgrade pip
        pip install -r requirements.txt
        
        echo "\\n🧪 Запуск тестов..."
        pytest tests/ -v --tb=short
    '''
}

def buildDockerImage() {
    sh """
        echo "========================================="
        echo "🐳 СБОРКА DOCKER ОБРАЗА"
        echo "========================================="
        
        echo "📋 Проверка Docker:"
        docker --version
        
        echo "\\n🏗️ Сборка образа ${SERVICE_NAME}:${BUILD_NUMBER}..."
        docker build -t ${SERVICE_NAME}:${BUILD_NUMBER} .
        
        echo "\\n✅ Проверка созданного образа:"
        docker images | grep ${SERVICE_NAME} | grep ${BUILD_NUMBER} || {
            echo "❌ Образ не найден после сборки!"
            exit 1
        }
        
        echo "✅ Образ собран: ${SERVICE_NAME}:${BUILD_NUMBER}"
    """
}

def deployNewVersion() {
    sh """
        echo "========================================="
        echo "🚀 ДЕПЛОЙ НОВОЙ ВЕРСИИ"
        echo "========================================="
        
        echo "🛑 Остановка старого контейнера..."
        docker stop ${SERVICE_NAME} || true
        docker rm ${SERVICE_NAME} || true
        
        echo "\\n🚀 Запуск нового контейнера..."
        docker run -d \\
            -p ${APP_PORT}:${CONTAINER_PORT} \\
            --name ${SERVICE_NAME} \\
            --restart unless-stopped \\
            ${SERVICE_NAME}:${BUILD_NUMBER}
        
        echo "\\n✅ Новый контейнер запущен"
        
        echo "\\n🔍 Проверка статуса контейнера..."
        sleep 3
        docker ps | grep ${SERVICE_NAME} || {
            echo "❌ Контейнер не запустился!"
            docker logs ${SERVICE_NAME}
            exit 1
        }
        
        echo "\\n📋 Детали контейнера:"
        docker ps --filter "name=${SERVICE_NAME}" --format "table {{.Names}}\\t{{.Status}}\\t{{.Ports}}"
    """
}

def healthCheck() {
    script {
        def maxRetries = 12
        def retryCount = 0
        def healthOk = false
        
        echo "========================================="
        echo "🏥 HEALTH CHECK"
        echo "========================================="
        
        while (retryCount < maxRetries && !healthOk) {
            try {
                sh """
                    echo "Попытка \$((retryCount + 1))/${maxRetries}..."
                    echo "Проверка http://localhost:${APP_PORT}/health"
                    
                    # Проверяем, что контейнер работает
                    docker ps | grep ${SERVICE_NAME} || {
                        echo "❌ Контейнер не работает!"
                        exit 1
                    }
                    
                    # Пробуем curl
                    curl -f http://localhost:${APP_PORT}/health || {
                        echo "❌ Health check endpoint не отвечает"
                        docker logs --tail 20 ${SERVICE_NAME}
                        exit 1
                    }
                    
                    echo "✅ Health check прошел успешно!"
                """
                healthOk = true
            } catch (Exception e) {
                retryCount++
                if (retryCount < maxRetries) {
                    echo "⚠️ Health check не пройден (${retryCount}/${maxRetries}). Ждем 5 секунд..."
                    sleep(5)
                } else {
                    echo "❌ Health check провален после ${maxRetries} попыток!"
                    sh """
                        echo "\\n📋 Последние логи контейнера:"
                        docker logs --tail 50 ${SERVICE_NAME}
                    """
                    error "Health check failed - выполняю rollback"
                }
            }
        }
    }
}

def saveSuccessfulBuild() {
    sh """
        echo "========================================="
        echo "💾 СОХРАНЕНИЕ ВЕРСИИ"
        echo "========================================="
        
        echo ${BUILD_NUMBER} > ${LAST_SUCCESS_FILE}
        echo "✅ Последняя успешная версия ${BUILD_NUMBER} сохранена в ${LAST_SUCCESS_FILE}"
        echo "Содержимое файла: \$(cat ${LAST_SUCCESS_FILE})"
        
        # Сохраняем копию в отдельное место для надежности
        cp ${LAST_SUCCESS_FILE} ${LAST_SUCCESS_FILE}.backup || true
    """
}

def rollbackToPreviousVersion() {
    script {
        echo "========================================="
        echo "🔄 ROLLBACK"
        echo "========================================="
        
        // Читаем последнюю успешную версию
        def lastSuccessVersion = sh(
            script: """
                if [ -f ${LAST_SUCCESS_FILE} ]; then
                    cat ${LAST_SUCCESS_FILE}
                elif [ -f ${LAST_SUCCESS_FILE}.backup ]; then
                    cat ${LAST_SUCCESS_FILE}.backup
                else
                    echo "0"
                fi
            """,
            returnStdout: true
        ).trim()
        
        echo "📦 Последняя успешная версия: ${lastSuccessVersion}"
        
        if (lastSuccessVersion != "0" && lastSuccessVersion != "unknown" && lastSuccessVersion != "") {
            sh """
                echo "🔄 Выполняем rollback на версию ${lastSuccessVersion}..."
                
                # Проверяем существование образа
                if docker images | grep -q "${SERVICE_NAME}.*${lastSuccessVersion}"; then
                    echo "✅ Образ найден, выполняем откат..."
                    
                    # Останавливаем и удаляем текущий контейнер
                    docker stop ${SERVICE_NAME} || true
                    docker rm ${SERVICE_NAME} || true
                    
                    # Запускаем предыдущую версию
                    echo "🚀 Запуск предыдущей версии..."
                    docker run -d \\
                        -p ${APP_PORT}:${CONTAINER_PORT} \\
                        --name ${SERVICE_NAME} \\
                        --restart unless-stopped \\
                        ${SERVICE_NAME}:${lastSuccessVersion}
                    
                    echo "✅ Rollback на версию ${lastSuccessVersion} выполнен"
                    
                    # Проверяем, что контейнер запустился
                    echo "\\n🔍 Проверка контейнера..."
                    sleep 5
                    docker ps | grep ${SERVICE_NAME} || {
                        echo "❌ Контейнер после rollback не запустился!"
                        docker logs ${SERVICE_NAME}
                        exit 1
                    }
                    
                    # Проверяем health check
                    echo "\\n🔍 Проверка health после rollback..."
                    curl -f http://localhost:${APP_PORT}/health || {
                        echo "⚠️ Health check после rollback не пройден"
                        docker logs --tail 20 ${SERVICE_NAME}
                        exit 1
                    }
                    echo "✅ Health check после rollback пройден"
                    
                else
                    echo "❌ Образ версии ${lastSuccessVersion} не найден!"
                    echo "\\nДоступные образы:"
                    docker images | grep ${SERVICE_NAME} || echo "Нет образов ${SERVICE_NAME}"
                    exit 1
                fi
            """
        } else {
            echo "❌ Нет сохраненной успешной версии для rollback"
            echo "Файл ${LAST_SUCCESS_FILE} не существует или пуст"
        }
    }
}