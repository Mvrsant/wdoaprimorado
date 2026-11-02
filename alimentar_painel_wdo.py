import io
import os
import gspread
import requests
import pandas as pd
import yfinance as yf
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, time as dtime
from zoneinfo import ZoneInfo
from bcb import PTAX as BCB_PTAX

# ─────────────────────────────────────────────────────────────
# CONFIGURAÇÕES DA PLANILHA GOOGLE
# ─────────────────────────────────────────────────────────────
# ID da sua planilha: calculos WDO
SPREADSHEET_ID = "1RjX2XNB84PUJmQN8IZYxbh-at5eF_FpcTii_K5NLsxM"
TAB_NAME = "Planilha1"
CREDS_JSON = "credentials.json"  # Arquivo de Conta de Serviço do Google Cloud

TZ = ZoneInfo("America/Sao_Paulo")
HORA_FECHAMENTO_WDO = dtime(18, 30)

TICKERS = {
    "cme": "6L=F",
    "brl_usd": "BRLUSD=X",
    "xauusd": "GC=F",
    "dxy": "DX-Y.NYB",
}
URL_OURO_BRL = "https://www.melhorcambio.com/ouro-hoje"
URL_VOL_B3 = (
    "https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/"
    "market-data/consultas/mercado-de-derivativos/precos-referenciais/"
    "superficie-de-volatilidade-de-dolar/"
)
HEADERS = {"User-Agent": "Mozilla/5.0"}

# ─────────────────────────────────────────────────────────────
# FUNÇÕES DE COLETA DE DADOS (REAPROVEITADAS DA SUA ROTINA)
# ─────────────────────────────────────────────────────────────
def agora_br():
    return datetime.now(tz=TZ)

def apos_fechamento_wdo():
    return agora_br().time() >= HORA_FECHAMENTO_WDO

def calcular_vencimento_wdo(data_base):
    mes = data_base.month + 1 if data_base.month < 12 else 1
    ano = data_base.year if data_base.month < 12 else data_base.year + 1
    d = datetime(ano, mes, 1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d

MESES_ABREV = {1: "jan", 2: "fev", 3: "mar", 4: "abr", 5: "mai", 6: "jun",
               7: "jul", 8: "ago", 9: "set", 10: "out", 11: "nov", 12: "dez"}

def buscar_yfinance(ticker):
    try:
        hist = yf.Ticker(ticker).history(period="5d")
        if hist.empty:
            return None
        return {
            "open": round(float(hist["Open"].iloc[-1]), 4),
            "high": round(float(hist["High"].iloc[-1]), 4),
            "low": round(float(hist["Low"].iloc[-1]), 4),
            "close": round(float(hist["Close"].iloc[-1]), 4),
        }
    except Exception as e:
        print(f"Erro yfinance [{ticker}]: {e}")
        return None

def buscar_variacao_dxy():
    try:
        hist = yf.Ticker(TICKERS["dxy"]).history(period="5d")
        if len(hist) < 2:
            return None
        ant = float(hist["Close"].iloc[-2])
        atual = float(hist["Close"].iloc[-1])
        return round(((atual - ant) / ant) * 100, 4)
    except Exception as e:
        print(f"Erro DXY: {e}")
        return None

def buscar_ouro_brl():
    try:
        r = requests.get(URL_OURO_BRL, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.content, "html.parser")
        val = soup.find("input", {"id": "comercial"}).get("value")
        return float(val.replace(",", "."))
    except Exception as e:
        print(f"Erro Ouro BRL: {e}")
        return None

def buscar_delta50_b3(venc_dt):
    try:
        venc_ref = f"{MESES_ABREV[venc_dt.month]}-{str(venc_dt.year)[2:]}"
        r = requests.get(URL_VOL_B3, headers=HEADERS, timeout=15)
        tabelas = pd.read_html(io.StringIO(r.text), decimal=",", thousands=".")
        if not tabelas:
            return None
        df = tabelas[0]
        df.columns = [str(c).strip() for c in df.columns]
        linha = df[df[df.columns[0]].astype(str).str.strip().str.lower() == venc_ref.lower()]
        if not linha.empty and "50" in df.columns:
            return float(linha["50"].values[0])
    except Exception as e:
        print(f"Erro Vol B3: {e}")
    return None

def buscar_ptax():
    try:
        ptax = BCB_PTAX()
        endpoint = ptax.get_endpoint("CotacaoMoedaPeriodo")
        data_c = datetime.today().date()
        for _ in range(7):
            s = data_c.strftime("%m-%d-%Y")
            df = endpoint.query().parameters(moeda="USD", dataInicial=s, dataFinalCotacao=s).collect()
            if not df.empty:
                break
            data_c -= timedelta(days=1)
        else:
            return [None] * 4

        df["dataHoraCotacao"] = pd.to_datetime(df["dataHoraCotacao"])
        df = df[df["dataHoraCotacao"].dt.date == data_c].sort_values("dataHoraCotacao").reset_index(drop=True)
        cotacoes = [
            {"valor": round(float(row["cotacaoVenda"]), 4),
             "hora": row["dataHoraCotacao"].strftime("%H:%M")}
            for _, row in df.iterrows()
        ]
        while len(cotacoes) < 4:
            cotacoes.append(None)
        return cotacoes[:4]
    except Exception as e:
        print(f"Erro PTAX: {e}")
        return [None] * 4

# ─────────────────────────────────────────────────────────────
# SINCRONIZAÇÃO COM O GOOGLE SHEETS
# ─────────────────────────────────────────────────────────────
def atualizar_painel():
    print(f"[{agora_br().strftime('%H:%M:%S')}] Coletando dados de mercado...")

    # 1. Calendário e Vencimentos
    hoje = datetime.today()
    venc_dt = calcular_vencimento_wdo(hoje)
    du = len(pd.bdate_range(start=hoje, end=venc_dt))
    venc_str = venc_dt.strftime("%d/%m/%Y")

    # 2. Cotações Globais e Derivativos
    dxy_var = buscar_variacao_dxy()
    sup_volb3 = buscar_delta50_b3(venc_dt)
    cme_d = buscar_yfinance(TICKERS["cme"])
    brlusd_d = buscar_yfinance(TICKERS["brl_usd"])
    xauusd_d = buscar_yfinance(TICKERS["xauusd"])
    ouro_brl = buscar_ouro_brl()
    ptax_cots = buscar_ptax()

    # 3. Conexão com a planilha Google
    gc = gspread.service_account(filename=CREDS_JSON)
    sh = gc.open_by_key(SPREADSHEET_ID)
    ws = sh.worksheet(TAB_NAME)

    # Lendo dados do DDE (se você já envia para a aba 'sync_dde')
    try:
        ws_dde = sh.worksheet("sync_dde")
        dde_row = ws_dde.row_values(2)
        # Ex: WDOFUT_fech_anterior (col C), USDBRL_fech_anterior (col E), DI1 (col F), FRP0 (col G)
        usar_ultimo = apos_fechamento_wdo()
        wdo_fut = float(dde_row[1].replace(".", "").replace(",", ".")) if usar_ultimo else float(dde_row[2].replace(".", "").replace(",", "."))
        dolar_spot = float(dde_row[3].replace(",", ".")) if usar_ultimo else float(dde_row[4].replace(",", "."))
        di1_fut = float(dde_row[5].replace("%", "").replace(",", ".")) / 100
        frp0 = float(dde_row[6].replace(",", "."))
    except Exception as e:
        print(f"Aviso ao ler sync_dde (usando valores da tela): {e}")
        wdo_fut = None
        dolar_spot = None
        di1_fut = None
        frp0 = None

    updates = []

    # ── Atualiza Parâmetros (B4:B11) ──
    if wdo_fut is not None:
        updates.append({"range": "B4", "values": [[wdo_fut]]})
    if dxy_var is not None:
        updates.append({"range": "B5", "values": [[dxy_var / 100]]})
    if dolar_spot is not None:
        updates.append({"range": "B6", "values": [[dolar_spot]]})
    if di1_fut is not None:
        updates.append({"range": "B7", "values": [[di1_fut]]})
    updates.append({"range": "B8", "values": [[du]]})
    if sup_volb3 is not None:
        updates.append({"range": "B9", "values": [[sup_volb3]]})
    if frp0 is not None:
        updates.append({"range": "B10", "values": [[frp0]]})
    updates.append({"range": "B11", "values": [[venc_str]]})

    # ── Atualiza CME (K5:K8) ──
    if cme_d:
        updates.append({
            "range": "K5:K8",
            "values": [
                [cme_d["open"]],
                [cme_d["high"]],
                [cme_d["low"]],
                [cme_d["close"]],
            ]
        })

    # ── Atualiza Spot BRLUSD (L13:L16) ──
    if brlusd_d:
        updates.append({
            "range": "L13:L16",
            "values": [
                [brlusd_d["open"]],
                [brlusd_d["high"]],
                [brlusd_d["low"]],
                [brlusd_d["close"]],
            ]
        })

    # ── Atualiza Ouro (J13 e J15) ──
    if xauusd_d:
        updates.append({"range": "J13", "values": [[xauusd_d["close"]]]})
    if ouro_brl:
        updates.append({"range": "J15", "values": [[ouro_brl]]})

    # ── Atualiza Janelas PTAX (B15:C18) ──
    ptax_valores = []
    for p in ptax_cots:
        if p:
            ptax_valores.append([p["hora"], p["valor"]])
        else:
            ptax_valores.append(["", ""])
    updates.append({"range": "B15:C18", "values": ptax_valores})

    # Executa a escrita em lote de uma só vez
    ws.batch_update(updates, value_input_option="USER_ENTERED")
    print(f"[{agora_br().strftime('%H:%M:%S')}] Planilha atualizada com sucesso!")

if __name__ == "__main__":
    atualizar_painel( )
