# Pickems API
This is a project to proxy auth for pickems for the Riot Games Lol Esports 2021.

It allows you to auth with your own Riot Games account and proxy your auth to allow others to access your leaderboard information.

## Installation
```python
pip install -r requirements.txt
```

## Running
This uses FastAPI, meaning you can use any ASGI server to run it. The requirements include uvicorn.
```python
uvicorn main:app
```
