from fastapi import FastAPI, HTTPException
from time import time
import aiohttp
import re

username = "bangingheads"
password = "MySecretPassword"
leaderboard_id = "577426844126909614"
pick_block = "8843040735491922676"

class Auth:
    def __init__(self, username: str, password: str) -> None:
        self.username = username
        self.password = password
        self.access_token = ""
        self.expires_at = 0


    async def get_auth(self) -> str:
        if self.expires_at < time():
            session = aiohttp.ClientSession()
            data = {
                'client_id': 'play-valorant-web-prod',
                'nonce': '1',
                'redirect_uri': 'https://playvalorant.com/opt_in',
                'response_type': 'token id_token',
            }
            await session.post('https://auth.riotgames.com/api/v1/authorization', json=data)

            data = {
                'type': 'auth',
                'username': self.username,
                'password': self.password
            }
            async with session.put('https://auth.riotgames.com/api/v1/authorization', json=data) as r:
                data = await r.json()
            pattern = re.compile('access_token=((?:[a-zA-Z]|\d|\.|-|_)*).*id_token=((?:[a-zA-Z]|\d|\.|-|_)*).*expires_in=(\d*)')
            data = pattern.findall(data['response']['parameters']['uri'])[0]
            self.access_token = data[0]
            expires_in = data[2]
            self.expires_at = int(time()) + int(expires_in)
            await session.close()
            return self.access_token
        else:
            return self.access_token


    async def get_headers(self) -> dict:
        await self.get_auth()
        return {
            'Authorization': f'Bearer {self.access_token}'
        }

app = FastAPI(
    title="Riot Games Third Party Community Pickems API",
    description="Endpoints for getting information about pickems for the Riot Games Third Party Developer Community",
    version="0.0.1",
    contact={
        "name": "BangingHeads",
    },
)
auth: Auth = None
players_by_name = {}

@app.on_event("startup")
async def startup_event():
    global auth
    auth = Auth(username, password)
    await auth.get_auth()

@app.get("/player-by-id/{id}", summary="Get player by player ID")
async def player_by_id(id):
    headers = await auth.get_headers()
    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://pickem.lolesports.com/api/v1/section-picks/players/{id}/pickBlock/{pick_block}', headers=headers) as resp:
            return await resp.json()

@app.get("/leaderboard", summary="Get leaderboard set in config")
async def get_leaderboard():
    global players_by_name
    data = await leaderboard_by_id(leaderboard_id)
    players_by_name = {player['player']['name'].lower(): player['player']['id'] for player in data['standings']}
    return data

@app.get('/leaderboard-by-id/{id}', summary="Get leaderboard by ID")
async def leaderboard_by_id(id):
    headers = await auth.get_headers()
    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://pickem.lolesports.com/api/v1/leaderboards/group-v2/{id}', headers=headers) as resp:
            data = await resp.json()
    return data

@app.get('/player-by-name/{name}', summary="Get player by name that is part of the leaderboard")
async def by_name(name):
    await get_leaderboard()
    if name.lower() in players_by_name:
         return await player_by_id(players_by_name[name.lower()])
    else:
        raise HTTPException(status_code=404, detail="Player not found")