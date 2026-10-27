from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"status": "KITTRA V23 ULTIME LIVE", "solde": 10.91}

@app.get("/etat")
def etat():
    return {"solde": 10.91, "principal": 10.91, "disponible": 10.91, "en_cours": "0.00", "en_trade": False, "mode": "BALEINE", "position": "BNBUSDT", "coffre": {"total": 0}}

@app.get("/ping")
def ping():
    return {"pong": True}
