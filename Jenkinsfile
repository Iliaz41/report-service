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
        // Имя сервиса
        SERVICE_NAME = 'report-service'
        // Файл для хранения последней успешной версии
        LAST_SUCCESS_FILE = 'last_successful_build.txt'
        // Порт для health-check
        APP_PORT = '8081'
        // Внутренний порт контейнера
        CONTAINER_PORT = '5000'
    }
    
    stages {
        // Этап для rollback (выполняется если ROLLBACK_ONLY = true)
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
        
        // Основной pipeline (если ROLLBACK_ONLY = false)
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
                // Если pipeline успешен и это не rollback-only
                if (!params.ROLLBACK_ONLY) {
                    echo "✅ Pipeline успешно выполнен! Сохраняем версию..."
                    saveSuccessfulBuild()
                }
            }
        }
        
        failure {
            script {
                echo "❌ Pipeline упал! Выполняем rollback..."
                // Записываем причину падения
                currentBuild.description = "Pipeline failed - rollback triggered"
                
                // Пытаемся выполнить rollback на последнюю успешную версию
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

// Функции для переиспользования кода

def runTests() {
    sh '''
        echo "Создание виртуального окружения..."
        python -m venv venv
        
        echo "Активация виртуального окружения..."
        # Для Windows
        if [ -f "venv/Scripts/activate" ]; then
            source venv/Scripts/activate
        # Для Linux/Mac
        else
            source venv/bin/activate
        fi
        
        echo "Установка зависимостей..."
        pip install -r requirements.txt
        
        echo "Запуск тестов..."
        pytest tests/ -v
    '''
}

def buildDockerImage() {
    sh """
        docker build -t ${SERVICE_NAME}:${BUILD_NUMBER} .
        echo "✅ Образ собран: ${SERVICE_NAME}:${BUILD_NUMBER}"
    """
}

def deployNewVersion() {
    sh """
        # Остановка и удаление старого контейнера если существует
        if docker ps -a | grep -q ${SERVICE_NAME}; then
            echo "Останавливаем старый контейнер..."
            docker stop ${SERVICE_NAME} || true
            docker rm ${SERVICE_NAME} || true
        fi
        
        # Запуск нового контейнера
        echo "Запускаем новый контейнер..."
        docker run -d \
            -p ${APP_PORT}:${CONTAINER_PORT} \
            --name ${SERVICE_NAME} \
            ${SERVICE_NAME}:${BUILD_NUMBER}
        
        echo "✅ Новый контейнер запущен"
    """
}

def healthCheck() {
    // Ждем немного, чтобы контейнер точно запустился
    sleep(5)
    
    def maxRetries = 12 // Пробуем 12 раз (примерно 1 минута)
    def retryCount = 0
    def healthOk = false
    
    while (retryCount < maxRetries && !healthOk) {
        try {
            sh """
                curl -f http://localhost:${APP_PORT}/health
                echo "✅ Health check прошел успешно"
            """
            healthOk = true
        } catch (Exception e) {
            retryCount++
            if (retryCount < maxRetries) {
                echo "⚠️ Health check не пройден (попытка ${retryCount}/${maxRetries}). Ждем 5 секунд..."
                sleep(5)
            } else {
                echo "❌ Health check провален после ${maxRetries} попыток!"
                throw new Exception("Health check failed")
            }
        }
    }
    
    if (!healthOk) {
        error "Health check не пройден! Выполняется rollback..."
    }
}

def saveSuccessfulBuild() {
    sh """
        echo ${BUILD_NUMBER} > ${LAST_SUCCESS_FILE}
        echo "✅ Последняя успешная версия ${BUILD_NUMBER} сохранена"
    """
}

def rollbackToPreviousVersion() {
    script {
        // Читаем последнюю успешную версию из файла
        def lastSuccessVersion = "unknown"
        
        try {
            lastSuccessVersion = sh(
                script: "cat ${LAST_SUCCESS_FILE} || echo '0'",
                returnStdout: true
            ).trim()
            
            echo "📦 Последняя успешная версия: ${lastSuccessVersion}"
            
            if (lastSuccessVersion != "unknown" && lastSuccessVersion != "0") {
                sh """
                    echo "🔄 Выполняем rollback на версию ${lastSuccessVersion}..."
                    
                    # Проверяем существование образа
                    if docker images | grep -q "${SERVICE_NAME}.*${lastSuccessVersion}"; then
                        # Останавливаем текущий контейнер
                        docker stop ${SERVICE_NAME} || true
                        docker rm ${SERVICE_NAME} || true
                        
                        # Запускаем предыдущую версию
                        docker run -d \
                            -p ${APP_PORT}:${CONTAINER_PORT} \
                            --name ${SERVICE_NAME} \
                            ${SERVICE_NAME}:${lastSuccessVersion}
                        
                        echo "✅ Rollback на версию ${lastSuccessVersion} выполнен"
                        
                        // Проверяем работоспособность после rollback
                        sleep(5)
                        try {
                            sh "curl -f http://localhost:${APP_PORT}/health"
                            echo "✅ Health check после rollback пройден"
                        } catch (Exception e) {
                            echo "⚠️ Внимание! Health check после rollback не пройден"
                        }
                    } else {
                        echo "❌ Образ версии ${lastSuccessVersion} не найден!"
                    }
                """
            } else {
                echo "❌ Нет сохраненной успешной версии для rollback"
            }
        } catch (Exception e) {
            echo "❌ Ошибка при чтении файла с версией: ${e.message}"
        }
    }
}   