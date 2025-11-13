@echo off
echo Node.js 자동 설치를 시작합니다...
echo.

REM Node.js 다운로드 URL (LTS 버전)
set NODEJS_URL=https://nodejs.org/dist/v20.11.0/node-v20.11.0-x64.msi
set INSTALLER_NAME=nodejs-installer.msi

echo Node.js 설치 파일을 다운로드 중입니다...
powershell -Command "& {Invoke-WebRequest -Uri '%NODEJS_URL%' -OutFile '%INSTALLER_NAME%'}"

if exist "%INSTALLER_NAME%" (
    echo 설치 파일 다운로드 완료!
    echo.
    echo Node.js를 설치합니다. 설치 창이 나타날 때까지 잠시 기다려주세요...
    echo.
    
    REM 자동 설치 실행 (무음 설치)
    msiexec /i "%INSTALLER_NAME%" /quiet /norestart
    
    echo.
    echo 설치가 완료되었습니다!
    echo.
    
    REM 설치 파일 삭제
    del "%INSTALLER_NAME%"
    
    echo 터미널을 다시 시작한 후 다음 명령어로 설치를 확인하세요:
    echo node --version
    echo npm --version
    echo.
    echo 그 후 프로젝트 폴더에서 다음 명령어를 실행하세요:
    echo npm install
    echo npm start
    
) else (
    echo 다운로드에 실패했습니다.
    echo 수동으로 설치해주세요: https://nodejs.org/
)

pause
