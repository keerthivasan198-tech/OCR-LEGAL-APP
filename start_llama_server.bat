@echo off
title Qwen 2.5 7B AI Service (llama.cpp)
echo ==================================================
echo Starting Qwen 2.5 7B LLM Service on Port 8080...
echo Model: models\Qwen2.5-7B-Instruct-Q4_K_M.gguf
echo Endpoint: http://localhost:8080/v1
echo ==================================================

"%~dp0bin\llama-cpp\llama-server.exe" -m "%~dp0models\Qwen2.5-7B-Instruct-Q4_K_M.gguf" --port 8080 -c 2048 -t 4 -tb 4 -fa on -np 1
pause
