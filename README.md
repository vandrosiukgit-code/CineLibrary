# CineLibrary

Personal Cinematic Knowledge Management System.

## Project location

D:\КИНО\CineLibrary

## Backend setup

Open the project in PyCharm Professional.

Create a Python virtual environment in the project root:

    python -m venv .venv

Activate it in PowerShell:

    .\.venv\Scripts\Activate.ps1

Install dependencies:

    pip install -r backend\requirements.txt

Run the backend from the backend directory:

    uvicorn app.main:app --reload

Backend:
http://127.0.0.1:8000

API documentation:
http://127.0.0.1:8000/docs

## Frontend

The frontend structure is prepared.
React and Vite will be configured in a later development stage.

## Current limitations

This is an initial project skeleton.
No external APIs, AI services or database are connected.
