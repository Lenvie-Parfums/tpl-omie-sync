"""
diagnostico_tpl.py
Consulta o estoque de SKUs específicos na TPL e mostra o retorno bruto.
Uso: python diagnostico_tpl.py
"""
import os
import json
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()

TPL_BASE_URL = os.getenv("TPL_BASE_URL", "https://oms.tpl.com.br/api")
TPL_APIKEY   = os.getenv("TPL_APIKEY")
TPL_TOKEN    = os.getenv("TPL_TOKEN")
TPL_EMAIL    = os.getenv("TPL_EMAIL")

# SKUs pra inspecionar — adicione os que quiser
SKUS_INSPECIONAR = ["107033000", "107033500", "107013000"]

# Autentica
auth_resp = requests.post(
    f"{TPL_BASE_URL}/get/auth",
    headers={"Content-Type": "application/json"},
    data=json.dumps({"apikey": TPL_APIKEY, "token": TPL_TOKEN, "email": TPL_EMAIL}),
    timeout=30
)
auth_data = auth_resp.json()
print("=== GET/AUTH ===")
print(json.dumps(auth_data, indent=2))

token = auth_data.get("token") or auth_data.get("auth")
if not token:
    print("ERRO: token nao obtido")
    exit(1)

hoje = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y")

# Consulta estoque dos SKUs específicos
stock_resp = requests.post(
    f"{TPL_BASE_URL}/get/stock",
    headers={"Content-Type": "application/json"},
    data=json.dumps({
        "auth":   token,
        "start":  hoje,
        "resume": 1,
        "sku":    [{"sku": s} for s in SKUS_INSPECIONAR]
    }),
    timeout=30
)

print("\n=== GET/STOCK (retorno bruto) ===")
print(json.dumps(stock_resp.json(), indent=2))
