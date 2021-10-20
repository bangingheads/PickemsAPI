from fastapi import FastAPI, HTTPException
from typing import Optional
from time import time
import aiohttp
import re

username = "bangingheads"
password = "MySecretPassword"
leaderboard_id = "577426844126909614"

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
pick_blocks = {}
teams = {}

@app.on_event("startup")
async def startup_event():
    global auth, pick_blocks, teams
    auth = Auth(username, password)
    await auth.get_auth()
    headers = {"x-api-key": "uvuy3Wep82aZ3D21pAH9Z4RygQZjfbzC2QtedVFs"}
    tournament_id = ""
    async with aiohttp.ClientSession() as session:
        # Set pick blocks
        async with session.get('https://pickem.lolesports.com/api/v1/leagues?hl=en-US') as resp:
            data = await resp.json()
            pick_blocks = {pick_block['slug']['slug']: pick_block['id'] for pick_block in data['leagues'][0]['tournament']['pickBlocks']}
            tournament_id = data['leagues'][0]['tournament']['eldsTournamentId']
        # Set Teams
        async with session.get(f'https://esports-api.lolesports.com/persisted/pickem/getMatchesForTournament?hl=en-US&sport=lol&tournamentId={tournament_id}', headers=headers) as resp:
            data = await resp.json()
            events = data['data']['matches']['events']
            teams.update({team['id']: team for event in events for team in event['match']['teams']})
        

@app.get("/player-by-id/{id}", summary="Get player by ID of latest stage")
@app.get("/player-by-id/{id}/{stage}", summary="Get player by player ID by stage")
async def player_by_id(id: str, stage: Optional[str] = None):
    if stage == None:
        stage = list(pick_blocks.keys())[-1]
    headers = await auth.get_headers()
    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://pickem.lolesports.com/api/v1/section-picks/players/{id}/pickBlock/{pick_blocks[stage]}', headers=headers) as resp:
            return await resp.json()

@app.get("/player-by-name/{name}", summary="Get player by name in leaderboard of latest stage")
@app.get("/player-by-name/{name}/{stage}", summary="Get player by name that is part of the leaderboard by stage")
async def by_name(name: str, stage: Optional[str] = None):
    if stage == None:
        stage = list(pick_blocks.keys())[-1]
    await get_leaderboard()
    if name.lower() in players_by_name:
         return await player_by_id(players_by_name[name.lower()], stage)
    else:
        raise HTTPException(status_code=404, detail="Player not found")

@app.get("/leaderboard", summary="Get leaderboard set in config")
async def get_leaderboard():
    global players_by_name
    data = await leaderboard_by_id(leaderboard_id)
    players_by_name = {player['player']['name'].lower(): player['player']['id'] for player in data['standings']}
    return data

@app.get("/leaderboard-by-id/{id}", summary="Get leaderboard by ID")
async def leaderboard_by_id(id):
    headers = await auth.get_headers()
    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://pickem.lolesports.com/api/v1/leaderboards/group-v2/{id}', headers=headers) as resp:
            data = await resp.json()
    return data

@app.get("/stages", summary="Get active stages by name")
def get_stages():
    return list(pick_blocks.keys())

@app.get("/teams", summary="Get all active teams info by ID")
def get_teams():
    return teams