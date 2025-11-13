@echo off
echo 민원처리 챗봇 프로젝트를 실행합니다...
echo.

REM Node.js 설치 확인
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Node.js가 설치되어 있지 않습니다.
    echo install-nodejs.bat 파일을 실행하여 Node.js를 설치해주세요.
    pause
    exit /b 1
)

echo Node.js 버전 확인:
node --version
echo.

echo npm 버전 확인:
npm --version
echo.

echo 의존성을 설치합니다...
npm install

if %errorlevel% neq 0 (
    echo 의존성 설치에 실패했습니다.
    pause
    exit /b 1
)

echo.
echo 개발 서버를 시작합니다...
echo 브라우저에서 http://localhost:3000 으로 접속하세요.
echo 서버를 중지하려면 Ctrl+C를 누르세요.
echo.

npm start

pause






