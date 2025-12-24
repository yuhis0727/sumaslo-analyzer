@echo off
setlocal

rem auth
powershell -ExecutionPolicy RemoteSigned -Command "(Get-ECRLoginCommand).Password | docker login --username AWS --password-stdin 533267366734.dkr.ecr.ap-northeast-1.amazonaws.com"

rem build
docker build --platform linux/x86_64 -t my-fastapi-app:latest -f Dockerfile.prod . --no-cache

rem tagging image
docker tag my-fastapi-app:latest 430118844802.dkr.ecr.ap-northeast-1.amazonaws.com/god777:latest

rem push image
docker push 430118844802.dkr.ecr.ap-northeast-1.amazonaws.com/god777:latest