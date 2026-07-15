import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import io
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, time as dtime, date
from zoneinfo import ZoneInfo
from bcb import PTAX as BCB_PTAX
import os

# ─────────────────────────────────────────────
# Configuração da página
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="WDO — Mini Contrato Futuro",
    page_icon="📈",
    layout="wide",
)

# ─────────────────────────────────────────────
# CSS customizado — Otimizado para máxima legibilidade
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap');

.stApp { background-color: #0d1117; }
[data-testid="stAppViewContainer"] { background-color: #0d1117; }
[data-testid="stHeader"] { background-color: #0d1117; }
section[data-testid="stSidebar"] { display: none; }

/* Configuração dos Tabs */
.stTabs [data-baseweb="tab-list"] {
    background-color: #161b22;
    border-radius: 8px;
    padding: 4px;
    border: 1px solid #30363d;
    gap: 2px;
}
.stTabs [data-baseweb="tab"] {
    background-color: transparent;
    color: #8b949e;
    border-radius: 5px;
    font-size: 13px;
    padding: 6px 18px;
    border: none;
}
.stTabs [aria-selected="true"] {
    background-color: #21262d !important;
    color: #e6edf3 !important;
    border: 1px solid #30363d !important;
}
.stTabs [data-baseweb="tab-border"] { display: none; }

/* Configuração dos Cards de Métrica */
[data-testid="stMetric"] {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 12px 16px;
}
[data-testid="stMetricLabel"] p { font-size: 11px !important; color: #8b949e !important; font-family: 'JetBrains Mono'; }
[data-testid="stMetricValue"] { font-family: 'JetBrains Mono' !important; color: #e6edf3 !important; font-size: 20px !important; }
[data-testid="stMetricDelta"] { font-family: 'JetBrains Mono' !important; font-size: 12px !important; }

/* ─── CUSTOMIZAÇÃO AVANÇADA DE TABELAS (PANDAS STYLER) ─── */
/* Células comuns das tabelas */
.dataframe td, .rendered_html td {
    padding: 10px 14px !important; /* Mantém o respiro confortável */
    border-bottom: 1px solid #21262d !important;
    color: #e6edf3; /* REMOVIDO o !important para permitir que o Styler mude a cor do texto */
    background-color: #161b22; /* Força o fundo escuro padrão para evitar células brancas */
}
    width: 100% !important;
    border: 1px solid #30363d !important;
    background-color: #161b22 !important;
}

/* Cabeçalho das tabelas */
.dataframe th, .rendered_html th {
    background-color: #21262d !important;
    color: #c9d1d9 !important;
    font-weight: 600 !important;
    text-align: left !important;
    padding: 10px 14px !important; /* Mais respiro interno */
    border-bottom: 2px solid #30363d !important;
    font-size: 12px !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* Células comuns das tabelas */
.dataframe td, .rendered_html td {
    padding: 10px 14px !important; /* Aumenta a altura das linhas para não espremer os números */
    border-bottom: 1px solid #21262d !important;
    color: #e6edf3 !important;
}

/* Efeito de hover discreto para ajudar o olho a seguir a linha */
.dataframe tr:hover, .rendered_html tr:hover {
    background-color: #1f242c !important;
}

/* Estilização para as tabelas interativas padrão do Streamlit (quando usadas) */
[data-testid="stDataFrame"] { 
    background-color: #161b22; 
    border-radius: 8px; 
}
.stDataFrame { 
    border: 1px solid #30363d !important; 
    border-radius: 8px !important; 
}

/* Inputs e Botões */
input[type="number"], input[type="text"] {
    background-color: #21262d !important;
    color: #e6edf3 !important;
    border: 1px solid #30363d !important;
    font-family: 'JetBrains Mono' !important;
}
.stButton > button {
    background-color: #1f6feb !important;
    color: white !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 500 !important;
}
.stButton > button:hover { background-color: #388bfd !important; }

h1, h2, h3, p, label, div { color: #e6edf3; }
.stMarkdown p { color: #8b949e; font-size: 13px; }

[data-testid="stAlert"] { border-radius: 6px; }
[data-testid="stSpinner"] p { color: #58a6ff !important; font-family: 'JetBrains Mono'; }

.wdo-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 0 20px 0;
    border-bottom: 1px solid #30363d;
    margin-bottom: 20px;
}
.wdo-title { font-size: 20px; font-weight: 600; color: #e6edf3; margin: 0; }
.wdo-sub { font-size: 12px; color: #8b949e; font-family: 'JetBrains Mono'; }
.mono { font-family: 'JetBrains Mono'; }

/* Badges */
.tag-ok { background:#1a3a23; color:#3fb950; border:1px solid #238636; border-radius:4px; font-size:11px; padding:2px 8px; font-family:'JetBrains Mono'; }
.tag-err { background:#3d1a1a; color:#f85149; border-radius:4px; font-size:11px; padding:2px 8px; font-family:'JetBrains Mono'; }
.tag-warn { background:#3a2f1a; color:#e3b341; border:1px solid #9e6a03; border-radius:4px; font-size:11px; padding:2px 8px; font-family:'JetBrains Mono'; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Constantes
# ─────────────────────────────────────────────
TICKERS = {
    "cme":     "6L=F",
    "brl_usd": "BRLUSD=X",
    "xauusd":  "GC=F",
    "dxy":     "DX-Y.NYB",
}
URL_OURO_BRL   = "https://www.melhorcambio.com/ouro-hoje"
URL_PLANILHA   = "https://raw.githubusercontent.com/Mvrsant/calculoswdo/main/ddeprofit.xlsx"
PLANILHA_LOCAL = "ddeprofit.xlsx"
URL_VOL_B3     = ("https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/"
                   "market-data/consultas/mercado-de-derivativos/precos-referenciais/"
                   "superficie-de-volatilidade-de-dolar/")
HEADERS        = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
TZ             = ZoneInfo("America/Sao_Paulo")

HORA_FECHAMENTO_WDO = dtime(18, 30)
HORA_DXY_CALCULO   = 8
MINUTO_DXY_CALCULO = 50

GOOGLE_SHEET_ID  = "1x79rVbOFTjFRIlCNDoBc4LcvvDaKJU4y0yWLiDEwxXQ"
GOOGLE_SHEET_GID = "0"
URL_SHEET_CSV = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=csv&gid={GOOGLE_SHEET_GID}"
MINUTOS_TOLERANCIA_SYNC = 20
TTL_PADRAO = 40 * 60

# ─────────────────────────────────────────────
# Inicialização do Session State para o Modo Manual
# ─────────────────────────────────────────────
if "usar_ajuste_manual" not in st.session_state:
    st.session_state.usar_ajuste_manual = False
if "valores_manuais" not in st.session_state:
    st.session_state.valores_manuais = {}

# ─────────────────────────────────────────────
# Utilitários
# ─────────────────────────────────────────────
def agora_br() -> datetime:
    return datetime.now(tz=TZ)

def agora_br_str() -> str:
    return agora_br().strftime("%d/%m/%Y %H:%M:%S")

def apos_fechamento_wdo() -> bool:
    return agora_br().time() >= HORA_FECHAMENTO_WDO

def calcular_vencimento_wdo(data_base: datetime) -> datetime:
    mes = data_base.month + 1 if data_base.month < 12 else 1
    ano = data_base.year  if data_base.month < 12 else data_base.year + 1
    d   = datetime(ano, mes, 1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d

MESES_ABREV = {
    1: "jan", 2: "fev", 3: "mar", 4: "abr", 5: "mai", 6: "jun",
    7: "jul", 8: "ago", 9: "set", 10: "out", 11: "nov", 12: "dez",
}

def formato_vencimento_b3(data_venc: datetime) -> str:
    return f"{MESES_ABREV[data_venc.month]}-{str(data_venc.year)[2:]}"

def parse_numero(valor) -> float | None:
    if valor is None:
        return None
    s = str(valor).strip()
    if s == "" or s.lower() == "nan":
        return None
    try:
        return float(s)
    except ValueError:
        pass
    try:
        return float(s.replace(".", "").replace(",", "."))
    except ValueError:
        return None

# ─────────────────────────────────────────────
# Funções de busca de dados
# ─────────────────────────────────────────────
@st.cache_data(ttl=TTL_PADRAO, show_spinner=False)
def buscar_yfinance(ticker: str, period: str = "5d") -> dict | None:
    try:
        hist = yf.Ticker(ticker).history(period=period)
        if hist.empty:
            return None
        return {
            "open":  round(hist["Open"].iloc[-1],  4),
            "high":  round(hist["High"].iloc[-1],  4),
            "low":   round(hist["Low"].iloc[-1],   4),
            "close": round(hist["Close"].iloc[-1], 4),
            "prev":  round(hist["Close"].iloc[-2], 4) if len(hist) >= 2 else None,
        }
    except Exception as e:
        st.warning(f"yfinance [{ticker}]: {e}")
        return None

@st.cache_data(ttl=TTL_PADRAO, show_spinner=False)
def buscar_variacao_dxy() -> float | None:
    try:
        hist = yf.Ticker(TICKERS["dxy"]).history(period="5d")
        if len(hist) < 2:
            return None
        ant   = hist["Close"].iloc[-2]
        atual = hist["Close"].iloc[-1]
        return round(((atual - ant) / ant) * 100, 4)
    except Exception as e:
        st.warning(f"DXY variação: {e}")
        return None

@st.cache_data(ttl=TTL_PADRAO, show_spinner=False)
def buscar_variacao_dxy_horario(data_ref: date, hora: int = 8, minuto: int = 50) -> dict | None:
    try:
        ticker = yf.Ticker(TICKERS["dxy"])
        diario = ticker.history(period="5d", interval="1d")
        if len(diario) < 2:
            return None
        fechamento_anterior = diario["Close"].iloc[-2]

        intraday = ticker.history(period="2d", interval="1m")
        if intraday.empty:
            return None
        intraday.index = intraday.index.tz_convert(TZ)

        alvo = datetime.combine(data_ref, dtime(hora, minuto), tzinfo=TZ)
        candles_ate_alvo = intraday.loc[
            (intraday.index.date == data_ref) & (intraday.index <= alvo)
        ]
        if candles_ate_alvo.empty:
            return None

        preco_no_horario = candles_ate_alvo["Close"].iloc[-1]
        horario_real = candles_ate_alvo.index[-1]
        variacao = round(((preco_no_horario - fechamento_anterior) / fechamento_anterior) * 100, 4)

        return {
            "preco":               round(preco_no_horario, 4),
            "fechamento_anterior": round(fechamento_anterior, 4),
            "variacao_pct":        variacao,
            "horario_utilizado":   horario_real.strftime("%d/%m/%Y %H:%M"),
        }
    except Exception as e:
        st.warning(f"DXY variação às {hora:02d}:{minuto:02d}: {e}")
        return None

@st.cache_data(ttl=TTL_PADRAO, show_spinner=False)
def buscar_ouro_brl() -> float | None:
    try:
        r    = requests.get(URL_OURO_BRL, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.content, "html.parser")
        val  = soup.find("input", {"id": "comercial"}).get("value")
        return float(val.replace(",", "."))
    except Exception as e:
        st.warning(f"Ouro BRL: {e}")
        return None

@st.cache_data(ttl=TTL_PADRAO, show_spinner=False)
def colorir_bandas(df: pd.DataFrame) -> pd.DataFrame.style:
    def row_style(row):
        # Aplicamos background e color com !important direto no estilo da linha para garantir prioridade
        if "Máxima" in str(row["Tipo"]):
            return ["background-color: #132619 !important; color: #47c867 !important; font-weight: 600 !important;"] * len(row)
        elif "Mínima" in str(row["Tipo"]):
            return ["background-color: #2d1819 !important; color: #ff6b6b !important; font-weight: 600 !important;"] * len(row)
        # Linhas normais recebem o fundo escuro padrão e texto cinza/claro padrão
        return ["background-color: #161b22 !important; color: #e6edf3 !important;"] * len(row)

    return df.style.apply(row_style, axis=1)

@st.cache_data(ttl=TTL_PADRAO, show_spinner=False)
def buscar_planilha_sheets() -> dict | None:
    try:
        df = pd.read_csv(URL_SHEET_CSV)
        if df.empty:
            return None

        linha = df.iloc[0]
        atualizado_em_str = str(linha.get("atualizado_em", ""))

        try:
            atualizado_em = datetime.strptime(atualizado_em_str, "%d/%m/%Y %H:%M:%S").replace(tzinfo=TZ)
            minutos_desde_sync = (agora_br() - atualizado_em).total_seconds() / 60
        except ValueError:
            minutos_desde_sync = None

        hoje = datetime.today()
        venc = calcular_vencimento_wdo(hoje)
        du = len(pd.bdate_range(start=hoje, end=venc))

        usar_ultimo = apos_fechamento_wdo()
        wdo_fut = (parse_numero(linha["WDOFUT_ultimo"]) if usar_ultimo else parse_numero(linha["WDOFUT_fech_anterior"]))
        dolar_spot = (parse_numero(linha["USDBRL_ultimo"]) if usar_ultimo else parse_numero(linha["USDBRL_fech_anterior"]))

        return {
            "wdo_fut":                 wdo_fut,
            "dolar_spot":              dolar_spot,
            "di1_fut":                 parse_numero(linha["DI1FUT_ultimo"]),
            "frp0":                    parse_numero(linha["FRP0_ultimo"]),
            "expiration_date":         venc.strftime("%d/%m/%Y"),
            "business_days_remaining": du,
            "atualizado_em":           atualizado_em_str,
            "minutos_desde_sync":      minutos_desde_sync,
            "coluna_usada":            "Último" if usar_ultimo else "Fechamento Anterior",
            "fonte":                   "google_sheets",
        }
    except Exception as e:
        st.warning(f"Google Sheets: {e}")
        return None

@st.cache_data(ttl=TTL_PADRAO, show_spinner=False)
def buscar_planilha_github() -> dict | None:
    try:
        r = requests.get(URL_PLANILHA, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return None
        with open(PLANILHA_LOCAL, "wb") as f:
            f.write(r.content)

        df   = pd.read_excel(PLANILHA_LOCAL)
        df["Asset"] = df["Asset"].str.strip()

        def val(ativo, col):
            try:
                v = df.loc[df["Asset"] == ativo, col].values[0]
                return float(v) if pd.notna(v) else None
            except Exception:
                return None

        coluna_fechamento = "Último" if apos_fechamento_wdo() else "Fechamento Anterior"
        hoje = datetime.today()
        venc = calcular_vencimento_wdo(hoje)
        du   = len(pd.bdate_range(start=hoje, end=venc))

        return {
            "wdo_fut":                 val("WDOFUT",  coluna_fechamento),
            "dolar_spot":              val("USD/BRL", coluna_fechamento),
            "di1_fut":                 val("DI1FUT",  "Último"),
            "frp0":                    val("FRP0",    "Último"),
            "expiration_date":         venc.strftime("%d/%m/%Y"),
            "business_days_remaining": du,
            "coluna_usada":            coluna_fechamento,
            "fonte":                   "github",
        }
    except Exception as e:
        st.warning(f"Planilha GitHub: {e}")
        return None

def buscar_planilha() -> dict | None:
    dados = buscar_planilha_sheets()
    return dados if dados is not None else buscar_planilha_github()

@st.cache_data(ttl=TTL_PADRAO, show_spinner=False)
def buscar_delta50_b3(vencimento_ref: str) -> float | None:
    try:
        r = requests.get(URL_VOL_B3, headers=HEADERS, timeout=15)
        r.raise_for_status()
        tabelas = pd.read_html(io.StringIO(r.text), decimal=",", thousands=".")
        if not tabelas:
            return None
        df = tabelas[0]
        df.columns = [str(c).strip() for c in df.columns]

        col_venc = df.columns[0]
        linha = df[df[col_venc].astype(str).str.strip().str.lower() == vencimento_ref.lower()]
        if linha.empty or "50" not in df.columns:
            return None

        return float(linha["50"].values[0])
    except Exception as e:
        st.warning(f"Superfície de vol. B3: {e}")
        return None

@st.cache_data(ttl=TTL_PADRAO, show_spinner=False)
def buscar_sup_volb3_fallback() -> float | None:
    try:
        if not os.path.exists(PLANILHA_LOCAL):
            r = requests.get(URL_PLANILHA, headers=HEADERS, timeout=15)
            with open(PLANILHA_LOCAL, "wb") as f:
                f.write(r.content)
        df = pd.read_excel(PLANILHA_LOCAL, sheet_name="base_b3", header=None)
        return float(df.iloc[18, 6])
    except Exception as e:
        st.warning(f"SUP_VOLB3 fallback: {e}")
        return None

@st.cache_data(ttl=300, show_spinner=False)
def buscar_ptax() -> list:
    try:
        ptax     = BCB_PTAX()
        endpoint = ptax.get_endpoint("CotacaoMoedaPeriodo")
        data_c   = datetime.today().date()

        for _ in range(7):
            s   = data_c.strftime("%m.%d.%Y")
            df  = endpoint.query().parameters(moeda="USD", dataInicial=s, dataFinalCotacao=s).collect()
            if not df.empty:
                break
            data_c -= timedelta(days=1)
        else:
            return [None] * 4

        df["dataHoraCotacao"] = pd.to_datetime(df["dataHoraCotacao"])
        df = df[df["dataHoraCotacao"].dt.date == data_c].sort_values("dataHoraCotacao").reset_index(drop=True)

        cotacoes = [
            {"valor": row["cotacaoVenda"],
             "data":  row["dataHoraCotacao"].strftime("%d/%m/%Y"),
             "hora":  row["dataHoraCotacao"].strftime("%H:%M")}
            for _, row in df.iterrows()
        ]
        while len(cotacoes) < 4:
            cotacoes.append(None)
        return cotacoes[:4]
    except Exception as e:
        st.warning(f"PTAX: {e}")
        return [None] * 4

# ─────────────────────────────────────────────
# Funções de cálculo
# ─────────────────────────────────────────────
def calc_abertura_wdo(wdo_fechamento, dxy_var):
    if None in (wdo_fechamento, dxy_var):
        return None
    return round(wdo_fechamento * (1 + dxy_var / 100), 4)

def calc_over(di1_fut, dias_uteis):
    if None in (di1_fut, dias_uteis):
        return None
    return round(((1 + di1_fut) ** (1 / 252) - 1) * dias_uteis, 6)

def calc_preco_justo(dolar_spot, over):
    if None in (dolar_spot, over):
        return None
    return round(dolar_spot * (1 + over / 100), 4)

def calc_paridade_ouro(xauusd, ouro_brl_g):
    if None in (xauusd, ouro_brl_g):
        return None
    return round((ouro_brl_g / (xauusd / 31.1035)) * 1000, 4)

def calc_bandas(wdo_abertura, over, sup_volb3):
    if None in (wdo_abertura, over, sup_volb3):
        return None
    d = (wdo_abertura * over / 100) + sup_volb3
    return {
        "deslocamento":  round(d, 5),
        "1ª Máxima":     round(wdo_abertura + d, 2),
        "1ª Mínima":     round(wdo_abertura - d, 2),
        "2ª Máxima":     round((wdo_abertura + d) * 1.005, 2),
        "2ª Mínima":     round((wdo_abertura - d) * 0.995, 2),
    }

def calc_bandas_ptax(wdo_abertura, over, sup_volb3, ptaxes):
    b = calc_bandas(wdo_abertura, over, sup_volb3)
    if b is None:
        return None
    d   = b["deslocamento"]
    res = {"deslocamento_val": d, "deslocamento_pts": round(d * 1000, 4), "ptaxes": []}
    for p in ptaxes:
        if p is None:
            res["ptaxes"].append(None)
            continue
        base = p["valor"] * 1000
        res["ptaxes"].append({
            "valor":      p["valor"],
            "data":       p["data"],
            "hora":       p["hora"],
            "1ª Máxima":  round(base + d, 2),
            "1ª Mínima":  round(base - d, 2),
            "2ª Máxima":  round((base + d) * 1.005, 2),
            "2ª Mínima":  round((base - d) * 0.995, 2),
        })
    return res

# ─────────────────────────────────────────────
# Helpers de exibição e Nova Regra de Cores Muted (Suave)
# ─────────────────────────────────────────────
def fmt(v, dec=2):
    return f"{v:.{dec}f}" if v is not None else "—"

def status_badge(ok: bool):
    return '<span class="tag-ok">✓ OK</span>' if ok else '<span class="tag-err">✗ Erro</span>'

def status_badge_warn(texto: str):
    return f'<span class="tag-warn">{texto}</span>'

# CORREÇÃO CRÍTICA: Cores muito mais suaves e confortáveis para leitura prolongada (Padrão Pastel Pro)
def colorir_bandas(df: pd.DataFrame) -> pd.DataFrame.style:
    def row_color(row):
        # Cores muted para máximo conforto de leitura no dark mode
        # Verde suave: fundo #132619, texto #47c867
        # Vermelho suave: fundo #2d1819, texto #ff6b6b
        if "Máxima" in str(row["Tipo"]):
            return ["background-color: #132619 !important; color: #47c867 !important; font-weight: 500;"] * len(row)
        elif "Mínima" in str(row["Tipo"]):
            return ["background-color: #2d1819 !important; color: #ff6b6b !important; font-weight: 500;"] * len(row)
        return [""] * len(row)
    return df.style.apply(row_color, axis=1)

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
col_h1, col_h2, col_h3 = st.columns([3, 2, 1])
with col_h1:
    st.markdown("""
    <div style='padding-top:8px'>
        <p class='wdo-title'>📈 WDO — Mini Contrato Futuro de Dólar</p>
        <p class='wdo-sub'> Cálculos para o mini contrato de dólar negociado na BM&F Bovespa </p>
    </div>""", unsafe_allow_html=True)
with col_h3:
    atualizar = st.button("🔄 Atualizar", width="stretch")
    if atualizar:
        st.cache_data.clear()
        st.rerun()

st.markdown("<hr style='border-color:#30363d;margin:0 0 16px 0'>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# CARGA DE DADOS AUTOMÁTICOS
# ─────────────────────────────────────────────
with st.spinner("Buscando dados..."):
    planilha = buscar_planilha()

    hoje_data = agora_br().date()
    venc_dt = calcular_vencimento_wdo(datetime.today())
    venc_ref_b3 = formato_vencimento_b3(venc_dt)
    
    sup_volb3 = buscar_delta50_b3(venc_ref_b3)
    if sup_volb3 is None:
        sup_volb3 = buscar_sup_volb3_fallback()

    xauusd_d = buscar_yfinance(TICKERS["xauusd"])
    xauusd = xauusd_d["close"] if xauusd_d else None
    ouro_brl = buscar_ouro_brl()

    dxy_var = buscar_variacao_dxy()
    dxy_850_dict = buscar_variacao_dxy_horario(hoje_data, HORA_DXY_CALCULO, MINUTO_DXY_CALCULO)
    dxy_var_850 = dxy_850_dict["variacao_pct"] if dxy_850_dict else None

    cme_d = buscar_yfinance(TICKERS["cme"])
    brlusd_d = buscar_yfinance(TICKERS["brl_usd"])
    ptax_cots = buscar_ptax()

# ─── Processamento das Variáveis Base ─────────────────────
if st.session_state.usar_ajuste_manual:
    vm = st.session_state.valores_manuais
    wdo_fut = vm.get("wdo_fut")
    dolar_spot = vm.get("dolar_spot")
    di1_fut = vm.get("di1_fut")
    dxy_var_para_calculo = vm.get("dxy_var")
    du = vm.get("du")
    sup_volb3 = vm.get("sup_volb3")
    venc_str = "Ajustado Manualmente"
else:
    wdo_fut = planilha.get("wdo_fut") if planilha else None
    dolar_spot = planilha.get("dolar_spot") if planilha else None
    di1_fut = planilha.get("di1_fut") if planilha else None
    du = planilha.get("business_days_remaining") if planilha else None
    venc_str = planilha.get("expiration_date") if planilha else "—"
    dxy_var_para_calculo = dxy_var_850 if dxy_var_850 is not None else dxy_var

# Cálculos Derivados
wdo_abertura  = calc_abertura_wdo(wdo_fut, dxy_var_para_calculo)
over          = calc_over(di1_fut, du)
preco_justo   = calc_preco_justo(dolar_spot, over)
paridade_ouro = calc_paridade_ouro(xauusd, ouro_brl)
bandas        = calc_bandas(wdo_abertura, over, sup_volb3)
bandas_ptax   = calc_bandas_ptax(wdo_abertura, over, sup_volb3, ptax_cots)

horario = agora_br_str()

if st.session_state.usar_ajuste_manual:
    st.warning("⚠️ **Modo de Ajuste Manual Ativo!** Todos os cálculos abaixo refletem os valores informados na aba '⚙️ Ajuste Manual'.")

# ─────────────────────────────────────────────
# STATUS DOS DADOS
# ─────────────────────────────────────────────
with st.expander("📡 Status dos dados — " + horario, expanded=False):
    c1, c2, c3, c4, c5 = st.columns(5)
    fonte_planilha = planilha.get("fonte") if planilha else None
    if fonte_planilha == "google_sheets":
        minutos = planilha.get("minutos_desde_sync")
        if minutos is not None and minutos > MINUTOS_TOLERANCIA_SYNC:
            c1.markdown(f"**Planilha (Sheets)** {status_badge_warn(f'⏱ há {int(minutos)} min')}", unsafe_allow_html=True)
        else:
            c1.markdown(f"**Planilha (Sheets)** {status_badge(True)}", unsafe_allow_html=True)
    elif fonte_planilha == "github":
        c1.markdown(f"**Planilha (GitHub fallback)** {status_badge_warn('usando fallback')}", unsafe_allow_html=True)
    else:
        c1.markdown(f"**Planilha** {status_badge(False)}", unsafe_allow_html=True)

    c2.markdown(f"**Delta50 Vol B3** {status_badge(sup_volb3 is not None)}", unsafe_allow_html=True)
    c3.markdown(f"**Ouro BRL** {status_badge(ouro_brl is not None)}", unsafe_allow_html=True)
    c4.markdown(f"**DXY (8:50)** {status_badge(dxy_var_850 is not None)}", unsafe_allow_html=True)
    ptax_ok = any(p is not None for p in ptax_cots)
    c5.markdown(f"**PTAX** {status_badge(ptax_ok)}", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# ABAS
# ─────────────────────────────────────────────
aba1, aba2, aba3, aba4, aba5 = st.tabs([
    "📊 Visão Geral",
    "📈 Abertura & Bandas",
    "💰 PTAX & Bandas PTAX",
    "🔗 Paridades CME/BRL",
    "⚙️ Ajuste Manual",
])

# ══════════════════════════════════════════════
# ABA 1 — VISÃO GERAL
# ══════════════════════════════════════════════
with aba1:
    st.markdown("#### Métricas principais")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Abertura Est.",  fmt(wdo_abertura, 2),
              delta=fmt(wdo_abertura - wdo_fut, 2) if wdo_abertura and wdo_fut else None)
    m2.metric("Preço Justo",    fmt(preco_justo, 4))
    m3.metric("Paridade Ouro",  fmt(paridade_ouro, 4))
    m4.metric(
        "DXY (8:50)",
        f"{fmt(dxy_var_para_calculo, 2)}%" if dxy_var_para_calculo is not None else "—",
        help=(f"Horário usado: {dxy_850_dict['horario_utilizado']} · usado no cálculo") if dxy_850_dict else "Fallback de variação atual em uso."
    )
    m5.metric("DXY (atual)", f"{fmt(dxy_var, 2)}%" if dxy_var is not None else "—", help="Apenas para acompanhamento")

    st.markdown("<hr style='border-color:#30363d'>", unsafe_allow_html=True)

    with st.expander("📄 Dados Atuais do Cálculo", expanded=False):
        labels = {
            "WDO Futuro": wdo_fut,
            "Dólar Spot": dolar_spot,
            "DI1 Futuro (taxa a.a.)": di1_fut,
            "Vencimento WDO": venc_str,
            "Dias Úteis até Vencimento": du,
            "Over": over,
        }
        df_dados = pd.DataFrame([{"Descrição": k, "Valor": str(v)} for k, v in labels.items()])
        st.dataframe(df_dados, hide_index=True, width="stretch")

    with st.expander("🥇 Ouro — valores em USD e BRL", expanded=False):
        c1, c2 = st.columns(2)
        c1.metric("Ouro Spot (USD/oz)", fmt(xauusd,   2))
        c2.metric("Ouro (R$/grama)",    fmt(ouro_brl, 2))

# ══════════════════════════════════════════════
# ABA 2 — ABERTURA & BANDAS
# ══════════════════════════════════════════════
with aba2:
    st.metric("Abertura WDO estimada", fmt(wdo_abertura, 2),
              delta=fmt(wdo_abertura - wdo_fut, 2) if wdo_abertura and wdo_fut else None)
    st.markdown("<hr style='border-color:#30363d'>", unsafe_allow_html=True)
    st.markdown("#### Máximas e Mínimas")

    if bandas:
        df_b = pd.DataFrame({
            "Tipo":        ["1ª Máxima", "1ª Mínima", "2ª Máxima", "2ª Mínima"],
            "Valor (pts)": [bandas["1ª Máxima"], bandas["1ª Mínima"], bandas["2ª Máxima"], bandas["2ª Mínima"]],
            "Distância":   [round(bandas["1ª Máxima"] - wdo_abertura, 2),
                            round(bandas["1ª Mínima"] - wdo_abertura, 2),
                            round(bandas["2ª Máxima"] - wdo_abertura, 2),
                            round(bandas["2ª Mínima"] - wdo_abertura, 2)],
        })
        st.dataframe(colorir_bandas(df_b), hide_index=True, width="stretch")
    else:
        st.warning("Dados insuficientes para calcular as bandas. Verifique os valores de entrada.")

# ══════════════════════════════════════════════
# ABA 3 — PTAX & BANDAS PTAX
# ══════════════════════════════════════════════
with aba3:
    ptax_validas = [p for p in ptax_cots if p is not None]
    qtde         = len(ptax_validas)

    c1, c2 = st.columns([3, 1])
    with c1:
        st.markdown("#### Cotações PTAX do dia")
    with c2:
        st.metric("Disponibilidade", f"{qtde} / 4")

    st.progress(qtde / 4)

    if ptax_validas:
        cols = st.columns(4)
        for i, (col, p) in enumerate(zip(cols, ptax_cots)):
            with col:
                if p:
                    st.metric(f"PTAX {i+1}", f"R$ {p['valor']:.4f}", help=f"Data: {p['data']} · Hora: {p['hora']}")
                else:
                    st.metric(f"PTAX {i+1}", "—")

    st.markdown("<hr style='border-color:#30363d'>", unsafe_allow_html=True)
    st.markdown("#### Bandas PTAX calculadas")

    if bandas_ptax and ptax_validas:
        c1, c2 = st.columns(2)
        c1.metric("Deslocamento (valor)", fmt(bandas_ptax["deslocamento_val"], 5))
        c2.metric("Deslocamento (pontos)", fmt(bandas_ptax["deslocamento_pts"], 4))

        tipos = ["1ª Máxima", "1ª Mínima", "2ª Máxima", "2ª Mínima"]
        dados = {"Tipo": tipos}
        for i, p in enumerate(bandas_ptax["ptaxes"]):
            if p is None:
                continue
            dados[f"PTAX {i+1} ({p['hora']})"] = [p[t] for t in tipos]

        df_pb = pd.DataFrame(dados)
        st.dataframe(colorir_bandas(df_pb), hide_index=True, width="stretch")
    else:
        st.warning("Aguardando cotações PTAX ou dados de cálculo insuficientes.")

# ══════════════════════════════════════════════
# ABA 4 — PARIDADES CME / BRL
# ══════════════════════════════════════════════
with aba4:
    def cme_to_brl(v):
        return round(1 / v * 1000, 2) if v and v != 0 else None

    def inv(v):
        return round(1 / v, 4) if v and v != 0 else None

    col_cme, col_brl = st.columns(2)
    with col_cme:
        st.markdown("#### CME — 6L=F")
        if cme_d:
            cme_open_brl  = cme_to_brl(cme_d["open"])
            cme_high_brl  = cme_to_brl(cme_d["low"])
            cme_low_brl   = cme_to_brl(cme_d["high"])
            cme_close_brl = cme_to_brl(cme_d["close"])
            cme_prev_brl  = cme_to_brl(cme_d["prev"])
            delta_cme     = round(cme_close_brl - cme_prev_brl, 2) if cme_close_brl and cme_prev_brl else None

            df_cme = pd.DataFrame({
                "Campo":        ["Abertura", "Máxima", "Mínima", "Fechamento", "Fech. Anterior"],
                "USD":          [fmt(cme_d["open"],6), fmt(cme_d["high"],6), fmt(cme_d["low"],6), fmt(cme_d["close"],6), fmt(cme_d["prev"],6)],
                "BRL pts":      [fmt(cme_open_brl,2), fmt(cme_high_brl,2), fmt(cme_low_brl,2), fmt(cme_close_brl,2), fmt(cme_prev_brl,2)],
            })
            st.dataframe(df_cme, hide_index=True, width="stretch")
            st.metric("Δ Fechamento", fmt(delta_cme, 2) if delta_cme else "—", delta=fmt(delta_cme, 2) if delta_cme else None)

    with col_brl:
        st.markdown("#### USD/BRL")
        if brlusd_d:
            usd_open  = inv(brlusd_d["open"])
            usd_high  = inv(brlusd_d["low"])
            usd_low   = inv(brlusd_d["high"])
            usd_close = inv(brlusd_d["close"])
            usd_prev  = inv(brlusd_d["prev"])
            delta_usd = round(usd_close - usd_prev, 4) if usd_close and usd_prev else None

            df_brl = pd.DataFrame({
                "Campo":   ["Abertura", "Máxima", "Mínima", "Fechamento", "Fech. Anterior"],
                "BRLUSD":  [fmt(brlusd_d["open"],6), fmt(brlusd_d["high"],6), fmt(brlusd_d["low"],6), fmt(brlusd_d["close"],6), fmt(brlusd_d["prev"],6)],
                "USD/BRL": [fmt(usd_open,4), fmt(usd_high,4), fmt(usd_low,4), fmt(usd_close,4), fmt(usd_prev,4)],
            })
            st.dataframe(df_brl, hide_index=True, width="stretch")
            st.metric("Δ Fechamento", fmt(delta_usd, 4) if delta_usd else "—", delta=fmt(delta_usd, 4) if delta_usd else None)

# ══════════════════════════════════════════════
# ABA 5 — AJUSTE MANUAL
# ══════════════════════════════════════════════
with aba5:
    st.markdown("#### Sobrescrever valores para recalcular")
    st.caption("Ajuste os parâmetros abaixo para sobrescrever globalmente as fontes de dados.")

    init_wdo = float(wdo_fut or 0) if not st.session_state.usar_ajuste_manual else float(st.session_state.valores_manuais.get("wdo_fut", 0))
    init_spot = float(dolar_spot or 0) if not st.session_state.usar_ajuste_manual else float(st.session_state.valores_manuais.get("dolar_spot", 0))
    init_di1 = float(di1_fut or 0) if not st.session_state.usar_ajuste_manual else float(st.session_state.valores_manuais.get("di1_fut", 0))
    init_dxy = float(dxy_var_para_calculo or 0) if not st.session_state.usar_ajuste_manual else float(st.session_state.valores_manuais.get("dxy_var", 0))
    init_du = int(du or 0) if not st.session_state.usar_ajuste_manual else int(st.session_state.valores_manuais.get("du", 0))
    init_sup = float(sup_volb3 or 0) if not st.session_state.usar_ajuste_manual else float(st.session_state.valores_manuais.get("sup_volb3", 0))

    with st.form("form_manual"):
        c1, c2 = st.columns(2)
        with c1:
            m_wdo    = st.number_input("WDO Futuro — Fechamento", value=init_wdo, format="%.2f")
            m_spot   = st.number_input("Dólar Spot",                value=init_spot, format="%.4f")
            m_di1    = st.number_input("DI1 Futuro (taxa a.a.)",    value=init_di1, format="%.5f")
        with c2:
            m_dxy    = st.number_input("Variação DXY (%) — 08:50",  value=init_dxy, format="%.4f")
            m_du     = st.number_input("Dias Úteis até Vencimento", value=init_du, step=1)
            m_sup    = st.number_input("Delta 50 Vol B3",           value=init_sup, format="%.4f")
        
        c_btn1, c_btn2 = st.columns(2)
        with c_btn1:
            submitted = st.form_submit_button("Aplicar Ajustes Manuais", width="stretch")
        with c_btn2:
            clear_manual = st.form_submit_button("🔄 Restaurar Dados Automáticos", width="stretch")

    if submitted:
        st.session_state.usar_ajuste_manual = True
        st.session_state.valores_manuais = {
            "wdo_fut": m_wdo,
            "dolar_spot": m_spot,
            "di1_fut": m_di1,
            "dxy_var": m_dxy,
            "du": m_du,
            "sup_volb3": m_sup
        }
        st.success("✅ Ajustes manuais aplicados com sucesso! Navegue pelas abas para ver os novos dados.")
        st.rerun()

    if clear_manual:
        st.session_state.usar_ajuste_manual = False
        st.session_state.valores_manuais = {}
        st.success("🔄 Dados automáticos restaurados!")
        st.rerun()

# ─────────────────────────────────────────────
# RODAPÉ
# ─────────────────────────────────────────────
st.markdown(f"""
<div style='margin-top:32px;padding-top:12px;border-top:1px solid #30363d;text-align:center'>
    <p style='font-size:11px;color:#6e7681;font-family:JetBrains Mono'>
        Calculadora WDO  · dados atualizados em {horario} (BRT) ·
    </p>
</div>
""", unsafe_allow_html=True)