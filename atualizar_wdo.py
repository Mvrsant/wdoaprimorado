import io
import json
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
# CONFIGURAÇÕES E IDs
# ─────────────────────────────────────────────────────────────
SHEET_DESTINO_ID = "1RjX2XNB84PUJmQN8IZYxbh-at5eF_FpcTii_K5NLsxM"   # calculos WDO
SHEET_PONTE_ID   = "1x79rVbOFTjFRIlCNDoBc4LcvvDaKJU4y0yWLiDEwxXQ"   # temporealdde
TAB_DESTINO_NOME = "Planilha1"

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
        if tabelas:
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

def parse_num(v):
    if v is None:
        return None
    s = str(v).strip().replace("%", "")
    if not s or s.lower() == "nan":
        return None
    try:
        return float(s)
    except ValueError:
        pass
    try:
        return float(s.replace(".", "").replace(",", "."))
    except ValueError:
        return None

def main():
    print(f"[{agora_br().strftime('%H:%M:%S')}] Iniciando execução no GitHub Actions...")

    # Autenticação Google via Secret do GitHub
    creds_json = os.environ.get("GCP_SA_KEY")
    if creds_json:
        creds_dict = json.loads(creds_json)
        gc = gspread.service_account_from_dict(creds_dict)
    else:
        gc = gspread.service_account(filename="credentials.json")

    # 1. Leitura da planilha-ponte (dados do DDE)
    wdo_fut, dolar_spot, di1_fut, frp0 = None, None, None, None
    try:
        sh_ponte = gc.open_by_key(SHEET_PONTE_ID)
        ws_ponte = sh_ponte.sheet1
        linha_dde = ws_ponte.row_values(2)
        if len(linha_dde) >= 7:
            usar_ultimo = apos_fechamento_wdo()
            wdo_fut = parse_num(linha_dde[1] if usar_ultimo else linha_dde[2])
            dolar_spot = parse_num(linha_dde[3] if usar_ultimo else linha_dde[4])
            di1_fut = parse_num(linha_dde[5])
            if di1_fut and di1_fut > 1:
                di1_fut = di1_fut / 100
            frp0 = parse_num(linha_dde[6])
            print(f"DDE lido com sucesso: WDO={wdo_fut}, Spot={dolar_spot}, DI1={di1_fut}, FRP0={frp0}")
    except Exception as e:
        print(f"Aviso ao ler planilha ponte: {e}")

    # 2. Busca de dados externos
    hoje = datetime.today()
    venc_dt = calcular_vencimento_wdo(hoje)
    du = len(pd.bdate_range(start=hoje, end=venc_dt))
    venc_str = venc_dt.strftime("%d/%m/%Y")

    dxy_var = buscar_variacao_dxy()
    sup_volb3 = buscar_delta50_b3(venc_dt)
    cme_d = buscar_yfinance(TICKERS["cme"])
    brlusd_d = buscar_yfinance(TICKERS["brl_usd"])
    xauusd_d = buscar_yfinance(TICKERS["xauusd"])
    ouro_brl = buscar_ouro_brl()
    ptax_cots = buscar_ptax()

    # 3. Atualização da Planilha1 (calculos WDO)
    sh_dest = gc.open_by_key(SHEET_DESTINO_ID)
    ws_dest = sh_dest.worksheet(TAB_DESTINO_NOME)

    updates = []

    # Inputs Mercado (B4:B11)
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

    # CME (K5:K8)
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

    # Spot BRL/USD (L13:L16)
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

    # Ouro Spot (J13 e J15)
    if xauusd_d:
        updates.append({"range": "J13", "values": [[xauusd_d["close"]]]})
    if ouro_brl:
        updates.append({"range": "J15", "values": [[ouro_brl]]})

    # Janelas PTAX (B15:C18)
    ptax_linhas = []
    for p in ptax_cots:
        if p:
            ptax_linhas.append([p["hora"], p["valor"]])
        else:
            ptax_linhas.append(["", ""])
    updates.append({"range": "B15:C18", "values": ptax_linhas})

    # Gravação em lote
    ws_dest.batch_update(updates, value_input_option="USER_ENTERED")
    print(f"[{agora_br().strftime('%H:%M:%S')}] Sucesso! Painel calculos WDO atualizado.")

if __name__ == "__main__":
    main()