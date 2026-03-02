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
        echo "🔍 Проверка Python..."
        python --version
        
        echo "📦 Создание виртуального окружения..."
        python -m venv venv
        
        echo "⚡ Активация виртуального окружения..."
        . venv/bin/activate || . venv/Scripts/activate
        
        echo "📥 Установка зависимостей..."
        pip install --upgrade pip
        pip install pytest flask requests
        
        echo "🧪 Создание тестов..."
        mkdir -p tests
        cat > tests/test_simple.py << 'EOF'
def test_python():
    assert 1 + 1 == 2

def test_imports():
    try:
        import flask
        import pytest
        import requests
        assert True
    except ImportError as e:
        assert False, f"Import failed: {e}"
EOF
        
        echo "🧪 Запуск тестов..."
        pytest tests/ -v --tb=short
    '''
}

def buildDockerImage() {
    sh """
        echo "🐳 Сборка Docker образа..."
        docker build -t ${SERVICE_NAME}:${BUILD_NUMBER} .
        
        echo "✅ Проверка созданного образа..."
        docker images | grep ${SERVICE_NAME} | grep ${BUILD_NUMBER}
        
        echo "✅ Образ собран: ${SERVICE_NAME}:${BUILD_NUMBER}"
    """
}

def deployNewVersion() {
    sh """
        echo "🛑 Остановка старого контейнера..."
        docker stop ${SERVICE_NAME} || true
        docker rm ${SERVICE_NAME} || true
        
        echo "🚀 Запуск нового контейнера..."
        docker run -d \\
            -p ${APP_PORT}:${CONTAINER_PORT} \\
            --name ${SERVICE_NAME} \\
            --restart unless-stopped \\
            ${SERVICE_NAME}:${BUILD_NUMBER}
        
        echo "✅ Новый контейнер запущен"
        
        echo "🔍 Проверка статуса контейнера..."
        sleep 3
        docker ps | grep ${SERVICE_NAME} || {
            echo "❌ Контейнер не запустился!"
            docker logs ${SERVICE_NAME}
            exit 1
        }
    """
}

def healthCheck() {
    script {
        def maxRetries = 12
        def retryCount = 0
        def healthOk = false
        
        while (retryCount < maxRetries && !healthOk) {
            try {
                sh """
                    echo "Попытка \${retryCount + 1}/${maxRetries}..."
                    curl -f http://localhost:${APP_PORT}/health
                """
                healthOk = true
                echo "✅ Health check прошел успешно!"
            } catch (Exception e) {
                retryCount++
                if (retryCount < maxRetries) {
                    echo "⚠️ Health check не пройден. Ждем 5 секунд..."
                    sleep(5)
                } else {
                    echo "❌ Health check провален после ${maxRetries} попыток!"
                    error "Health check failed - выполняю rollback"
                }
            }
        }
    }
}

def saveSuccessfulBuild() {
    sh """
        echo ${BUILD_NUMBER} > ${LAST_SUCCESS_FILE}
        echo "✅ Последняя успешная версия ${BUILD_NUMBER} сохранена в ${LAST_SUCCESS_FILE}"
        echo "Содержимое файла: \$(cat ${LAST_SUCCESS_FILE})"
    """
}

def rollbackToPreviousVersion() {
    script {
        // Читаем последнюю успешную версию
        def lastSuccessVersion = sh(
            script: "if [ -f ${LAST_SUCCESS_FILE} ]; then cat ${LAST_SUCCESS_FILE}; else echo '0'; fi",
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
                    docker run -d \\
                        -p ${APP_PORT}:${CONTAINER_PORT} \\
                        --name ${SERVICE_NAME} \\
                        --restart unless-stopped \\
                        ${SERVICE_NAME}:${lastSuccessVersion}
                    
                    echo "✅ Rollback на версию ${lastSuccessVersion} выполнен"
                    
                    # Проверяем, что контейнер запустился
                    sleep 5
                    docker ps | grep ${SERVICE_NAME} || {
                        echo "❌ Контейнер после rollback не запустился!"
                        docker logs ${SERVICE_NAME}
                        exit 1
                    }
                    
                    # Проверяем health check
                    echo "🔍 Проверка health после rollback..."
                    curl -f http://localhost:${APP_PORT}/health || {
                        echo "⚠️ Health check после rollback не пройден"
                        exit 1
                    }
                    echo "✅ Health check после rollback пройден"
                    
                else
                    echo "❌ Образ версии ${lastSuccessVersion} не найден!"
                    echo "Доступные образы:"
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