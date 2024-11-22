@echo off

rem Init python environment venv

rem Check if venv folder exists

if not exist venv (
    echo Creating virtual environment
    python -m venv venv
)

rem Activate virtual environment
call venv\Scripts\activate

rem Install dependencies
pip install -r requirements.txt
