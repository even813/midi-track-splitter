@echo off
chcp 65001 >nul
title MIDI 钢琴分轨工具
cd /d "%~dp0"
python start.py
pause
