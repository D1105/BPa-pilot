# Скрипт запуска пилота АвтоИмпорт Pro (Windows PowerShell)

Write-Host "🚗 Запуск АвтоИмпорт Pro..." -ForegroundColor Cyan

# Проверяем наличие .env
if (-not (Test-Path "backend\.env")) {
    Write-Host "⚠️  Создайте файл backend\.env с OPENAI_API_KEY" -ForegroundColor Yellow
    Write-Host "   Пример: OPENAI_API_KEY=sk-your-key-here" -ForegroundColor Gray
}

# Запуск бэкенда
Write-Host "`n📦 Запуск бэкенда..." -ForegroundColor Green
Start-Process -FilePath "pwsh" -ArgumentList "-NoExit", "-Command", "cd backend; python main.py" -WindowStyle Normal

# Ждём запуска бэкенда
Start-Sleep -Seconds 3

# Запуск фронтенда
Write-Host "🎨 Запуск фронтенда..." -ForegroundColor Green
Start-Process -FilePath "pwsh" -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev" -WindowStyle Normal

Write-Host "`n✅ Готово!" -ForegroundColor Green
Write-Host "   Backend: http://localhost:8000" -ForegroundColor Cyan
Write-Host "   Frontend: http://localhost:5173" -ForegroundColor Cyan
Write-Host "   Админка: нажмите [Админ] в футере сайта" -ForegroundColor Gray
