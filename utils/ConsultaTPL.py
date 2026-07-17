"""
ConsultaTPL.py
Lê o estoque atual do WMS da TPL via API e retorna lista de SKUs com saldo.

Endpoints utilizados:
  POST /api/get/auth  → gera token dinâmico (válido 1h, não pode chamar 2x)
  POST /api/get/stock → retorna saldo de todos os SKUs ativos

Credenciais necessárias (Secrets do GitHub):
  TPL_APIKEY  → fornecido pelo comercial/projetos TPL
  TPL_TOKEN   → fornecido pelo comercial/projetos TPL
  TPL_EMAIL   → e-mail autorizado a utilizar o serviço
  TPL_BASE_URL → ex: https://oms.tpl.com.br/api
"""
import os
import json
import time
import logging
import requests
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger(__name__)

TPL_BASE_URL = os.getenv("TPL_BASE_URL", "https://oms.tpl.com.br/api")
TPL_APIKEY   = os.getenv("TPL_APIKEY")
TPL_TOKEN    = os.getenv("TPL_TOKEN")
TPL_EMAIL    = os.getenv("TPL_EMAIL")

MAX_RETRIES  = 3
RETRY_DELAY  = 10


def autenticar_tpl():
    """
    Gera token dinâmico via get/auth.
    ATENÇÃO: o token é válido por 1h e não pode ser solicitado mais de uma vez
    nesse período (retorna code 400 na segunda tentativa).
    O token é gerado uma vez no início da execução e reutilizado.
    """
    if not all([TPL_APIKEY, TPL_TOKEN, TPL_EMAIL]):
        raise RuntimeError(
            "Credenciais da TPL ausentes. "
            "Confira TPL_APIKEY, TPL_TOKEN e TPL_EMAIL nos Secrets."
        )

    url = f"{TPL_BASE_URL}/get/auth"
    payload = {
        "apikey": TPL_APIKEY,
        "token":  TPL_TOKEN,
        "email":  TPL_EMAIL,
    }

    for tentativa in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                data=json.dumps(payload),
                timeout=30
            )
            data = response.json()

            if response.status_code == 200 and ("token" in data or "auth" in data):
                log.info("TPL: autenticado com sucesso.")
                return data.get("token", data.get("auth"))
            
            code = data.get("code", response.status_code)

            # code 400 = já há um auth em uso (token ainda válido de execução anterior)
            # Isso não deveria acontecer no GitHub Actions (nova execução = novo ambiente)
            # mas tratamos por segurança.
            if code == 400:
                log.warning("TPL: auth code 400 — token ainda em uso. Aguardando 65s...")
                time.sleep(65)
                continue

            log.error(f"TPL: falha na autenticação (code={code}): {data}")
            raise RuntimeError(f"Falha na autenticação TPL: code={code}")

        except requests.exceptions.RequestException as e:
            log.warning(f"TPL: erro de conexão na autenticação (tentativa {tentativa}): {e}")
            if tentativa < MAX_RETRIES:
                time.sleep(RETRY_DELAY)

    raise RuntimeError("TPL: falha definitiva na autenticação após retries.")


def rodarAPITPL():
    """
    Consulta o estoque atual de todos os SKUs ativos na TPL.
    Retorna lista de dicts: [{"sku": ..., "available": balance}, ...]

    O campo 'balance' da TPL representa o saldo atual do período.
    Usamos start=hoje para garantir que o saldo reflita a posição atual.
    """
    from datetime import datetime
    from zoneinfo import ZoneInfo

    auth = autenticar_tpl()
    hoje = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y")

    url = f"{TPL_BASE_URL}/get/stock"
    payload = {
        "auth":   auth,
        "start":  hoje,
        "resume": 1,      # inclui saldo acumulado anterior ao período
        "sku": [{"sku": "*"}]  # todos os SKUs ativos
    }

    for tentativa in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                data=json.dumps(payload),
                timeout=60
            )
            data = response.json()
            code = data.get("code", response.status_code)

            if code == 200:
                estoque = data.get("stock", [])
                resultados = []
                for item in estoque:
                    if item.get("code") != 200:
                        log.warning(f"TPL: SKU {item.get('sku')} retornou code={item.get('code')}. Pulando.")
                        continue
                    # Saldo = balance do período + resume (saldo anterior)
                    balance   = int(item.get("balance", 0) or 0)
                    resume    = item.get("resume", {})
                    saldo_ant = int(resume.get("balance", 0) or 0) if resume else 0
                    saldo_total = balance + saldo_ant

                    resultados.append({
                        "sku":       item["sku"],
                        "available": saldo_total,
                        "blocked":   0,  # TPL não separa por local; avarias tratadas separadamente
                    })

                log.info(f"TPL: {len(resultados)} SKUs recebidos com sucesso.")
                return resultados

            log.warning(f"TPL: get/stock retornou code={code} (tentativa {tentativa})")
            time.sleep(RETRY_DELAY)

        except requests.exceptions.RequestException as e:
            log.warning(f"TPL: erro de conexão em get/stock (tentativa {tentativa}): {e}")
            if tentativa < MAX_RETRIES:
                time.sleep(RETRY_DELAY)

    raise RuntimeError("TPL: falha definitiva em get/stock após retries.")
