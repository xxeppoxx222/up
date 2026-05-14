@echo off
chcp 65001 >nul
title UMAX - Build Tool
echo ====================================
echo   Building UMAX Tool - EXE
echo ====================================
echo.

pip install pyinstaller -q

pyinstaller --onefile --noconsole --name UMAX ^
  --add-data "auth.py;." ^
  --add-data "theme.py;." ^
  --hidden-import discord ^
  --hidden-import requests ^
  --hidden-import threading ^
  --hidden-import tkinter ^
  --hidden-import PIL ^
  --hidden-import io ^
  --hidden-import json ^
  --hidden-import os ^
  --hidden-import sys ^
  --hidden-import time ^
  --hidden-import webbrowser ^
  --hidden-import subprocess ^
  --hidden-import random ^
  --hidden-import datetime ^
  --hidden-import hashlib ^
  --hidden-import base64 ^
  --hidden-import uuid ^
  --hidden-import re ^
  --hidden-import math ^
  --hidden-import asyncio ^
  main.py

if %errorlevel% equ 0 (
    echo.
    echo ====================================
    echo   SUCCESS! Output: dist\UMAX.exe
    echo ====================================
) else (
    echo.
    echo ====================================
    echo   BUILD FAILED
    echo ====================================
)
pause
