import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import io
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, time as dtime
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
# CSS customizado — tema dark estilo terminal
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&display=swap');

.stApp { background-color: #0d1117; }
[data-testid="stAppViewContainer"] { background-color: #0d1117; }
[data-testid="stHeader"] { background-color: #0d1117; }
section[data-testid="stSidebar"] { display: none; }

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

[data-testid="stMetric"] {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 12px 16px;
}
[data-testid="stMetricLabel"] p { font-size: 11px !important; color: #8b949e !important; font-family: 'JetBrains Mono'; }
[data-testid="stMetricValue"] { font-family: 'JetBrains Mono' !important; color: #e6edf3 !important; font-size: 20px !important; }
[data-testid="stMetricDelta"] { font-family: 'JetBrains Mono' !important; font-size: 12px !important; }

[data-testid="stDataFrame"] { background-color: #161b22; border-radius: 8px; }
.stDataFrame { border: 1px solid #30363d !important; border-radius: 8px !important; }

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
.tag-ok { background:#1a3a23; color:#3fb950; border:1px solid #238636; border-radius:4px; font-size:11px; padding:2px 8px; font-family:'JetBrains Mono'; }
.tag-err { background:#3d1a1a; color:#f85149; border-radius:4px; font-size:11px; padding:2px 8px; font-family:'JetBrains Mono'; }
.tag-warn { background:#3a2f1a; color:#e3b341; border:1px solid #9e6a03; border-radius:4px; font-size:11px; padding:2px 8px; font-family:'JetBrains Mono'; }
.banda-row-max { background-color: #1a3a23 !important; color: #3fb950 !important; }
.banda-row-min { background-color: #3d1a1a !important; color: #f85149 !important; }
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
HEADERS        = {"User-Agent": "Mozilla/5.0"}
TZ             = ZoneInfo("America/Sao_Paulo")

# Horário de fechamento do WDO (ajustar se necessário)
HORA_FECHAMENTO_WDO = dtime(18, 0)

# ── Google Sheets (planilha-ponte alimentada pelo sync_dde.py) ──
# Preencher com os valores reais (ver SETUP_GOOGLE_SHEETS.md)
GOOGLE_SHEET_ID  = "1x79rVbOFTjFRIlCNDoBc4LcvvDaKJU4y0yWLiDEwxXQ"
GOOGLE_SHEET_GID = "0"
URL_SHEET_CSV = (
    f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}"
    f"/export?format=csv&gid={GOOGLE_SHEET_GID}"
)
MINUTOS_TOLERANCIA_SYNC = 20  # acima disso, considera dado "desatualizado"

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
    """Formata a data de vencimento como 'jul-26', igual à tabela da B3."""
    return f"{MESES_ABREV[data_venc.month]}-{str(data_venc.year)[2:]}"

def parse_numero(valor) -> float | None:
    """
    Converte um valor numérico vindo do Google Sheets (que pode estar
    formatado no padrão brasileiro, ex: '5,1341' ou '1.234,56') para
    float. Tenta primeiro conversão direta (formato US/decimal com
    ponto); se falhar, converte do formato BR.
    """
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
        # formato BR: remove separador de milhar '.', troca decimal ',' por '.'
        return float(s.replace(".", "").replace(",", "."))
    except ValueError:
        return None

# ─────────────────────────────────────────────
# Funções de busca de dados
# ─────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
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

@st.cache_data(ttl=300, show_spinner=False)
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

@st.cache_data(ttl=600, show_spinner=False)
def buscar_ouro_brl() -> float | None:
    try:
        r    = requests.get(URL_OURO_BRL, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.content, "html.parser")
        val  = soup.find("input", {"id": "comercial"}).get("value")
        return float(val.replace(",", "."))
    except Exception as e:
        st.warning(f"Ouro BRL: {e}")
        return None


# ── NOVO: leitura via Google Sheets (fonte primária) ──────────────
@st.cache_data(ttl=120, show_spinner=False)
def buscar_planilha_sheets() -> dict | None:
    """
    Lê a planilha-ponte no Google Sheets, alimentada pelo sync_dde.py
    rodando localmente na máquina com o Profit/DDE. Retorna None se
    a planilha ainda não tiver sido configurada ou estiver vazia.
    """
    if "COLOQUE_AQUI" in GOOGLE_SHEET_ID:
        return None  # ainda não configurado — ver SETUP_GOOGLE_SHEETS.md

    try:
        df = pd.read_csv(URL_SHEET_CSV)
        if df.empty:
            return None
        linha = df.iloc[0]  # linha 2 da planilha = primeira linha de dados

        atualizado_em_str = str(linha.get("atualizado_em", ""))
        try:
            atualizado_em = datetime.strptime(atualizado_em_str, "%d/%m/%Y %H:%M:%S").replace(tzinfo=TZ)
            minutos_desde_sync = (agora_br() - atualizado_em).total_seconds() / 60
        except ValueError:
            minutos_desde_sync = None

        hoje = datetime.today()
        venc = calcular_vencimento_wdo(hoje)
        du   = len(pd.bdate_range(start=hoje, end=venc))

        return {
            "wdo_fut":                 parse_numero(linha["WDOFUT_ultimo"]),
            "dolar_spot":              parse_numero(linha["USDBRL_ultimo"]),
            "di1_fut":                 parse_numero(linha["DI1FUT_ultimo"]),
            "frp0":                    parse_numero(linha["FRP0_ultimo"]),
            "expiration_date":         venc.strftime("%d/%m/%Y"),
            "business_days_remaining": du,
            "atualizado_em":           atualizado_em_str,
            "minutos_desde_sync":      minutos_desde_sync,
            "fonte":                   "google_sheets",
        }
    except Exception as e:
        st.warning(f"Google Sheets: {e}")
        return None


@st.cache_data(ttl=600, show_spinner=False)
def buscar_planilha_github() -> dict | None:
    """
    Fonte de fallback (arquivo estático no GitHub). Usa 'Último' após
    o fechamento do WDO (fechamento de hoje) e 'Fechamento Anterior'
    durante o pregão (valor provisório).
    """
    try:
        r = requests.get(URL_PLANILHA, timeout=15)
        if r.status_code != 200:
            st.warning(f"Planilha GitHub: status {r.status_code}")
            return None
        with open(PLANILHA_LOCAL, "wb") as f:
            f.write(r.content)

        df   = pd.read_excel(PLANILHA_LOCAL)
        cols = ["Asset", "Fechamento Anterior", "Último"]
        if not all(c in df.columns for c in cols):
            st.warning("Colunas ausentes na planilha.")
            return None
        df["Asset"] = df["Asset"].str.strip()

        def val(ativo, col):
            try:
                v = df.loc[df["Asset"] == ativo, col].values[0]
                v = float(v)
                return v if pd.notna(v) else None
            except Exception:
                return None

        # Coluna a usar: 'Último' pós-fechamento (fechamento de hoje),
        # 'Fechamento Anterior' durante o pregão (valor provisório)
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
    """Tenta primeiro o Google Sheets (dado do dia, via DDE); cai para o GitHub se indisponível."""
    dados = buscar_planilha_sheets()
    if dados is not None:
        return dados
    return buscar_planilha_github()


# ── NOVO: Delta 50% da superfície de volatilidade via scraping ──
@st.cache_data(ttl=600, show_spinner=False)
def buscar_delta50_b3(vencimento_ref: str) -> float | None:
    """
    Faz scraping da tabela pública de superfície de volatilidade de
    dólar na página da B3, sem precisar de Excel/DDE.
    vencimento_ref: formato 'jul-26' (ver formato_vencimento_b3)
    """
    try:
        r = requests.get(URL_VOL_B3, headers=HEADERS, timeout=15)
        r.raise_for_status()
        tabelas = pd.read_html(io.StringIO(r.text), decimal=",", thousands=".")
        #tabelas = pd.read_html(r.text, decimal=",", thousands=".")
        if not tabelas:
            st.warning("Superfície de vol. B3: nenhuma tabela encontrada na página.")
            return None
        df = tabelas[0]
        df.columns = [str(c).strip() for c in df.columns]

        col_venc = df.columns[0]
        linha = df[df[col_venc].astype(str).str.strip().str.lower() == vencimento_ref.lower()]
        if linha.empty:
            st.warning(f"Superfície de vol. B3: vencimento '{vencimento_ref}' não encontrado na tabela.")
            return None

        if "50" not in df.columns:
            st.warning("Superfície de vol. B3: coluna delta 50 não encontrada — conferir cabeçalho da tabela.")
            return None

        return float(linha["50"].values[0])
    except Exception as e:
        st.warning(f"Superfície de vol. B3: {e}")
        return None


@st.cache_data(ttl=600, show_spinner=False)
def buscar_sup_volb3_fallback() -> float | None:
    """Fallback antigo (lê do Excel do GitHub) — usar apenas se o scraping falhar."""
    try:
        if not os.path.exists(PLANILHA_LOCAL):
            r = requests.get(URL_PLANILHA, timeout=15)
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
            df  = (endpoint.query()
                   .parameters(moeda="USD", dataInicial=s, dataFinalCotacao=s)
                   .collect())
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
# Funções de cálculo (não alteradas — over já validado)
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
# Helpers de exibição
# ─────────────────────────────────────────────
def fmt(v, dec=2):
    return f"{v:.{dec}f}" if v is not None else "—"

def delta_color(v):
    if v is None:
        return "off"
    return "normal" if v >= 0 else "inverse"

def status_badge(ok: bool):
    if ok:
        return '<span class="tag-ok">✓ OK</span>'
    return '<span class="tag-err">✗ Erro</span>'

def status_badge_warn(texto: str):
    return f'<span class="tag-warn">{texto}</span>'

def colorir_bandas(df: pd.DataFrame) -> pd.DataFrame.style:
    def row_color(row):
        if "Máxima" in str(row["Tipo"]):
            return ["background-color:#1a3a23;color:#3fb950"] * len(row)
        elif "Mínima" in str(row["Tipo"]):
            return ["background-color:#3d1a1a;color:#f85149"] * len(row)
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
# CARGA DE DADOS (com spinner único)
# ─────────────────────────────────────────────
with st.spinner("Buscando dados..."):
    planilha   = buscar_planilha()

    venc_dt        = calcular_vencimento_wdo(datetime.today())
    venc_ref_b3    = formato_vencimento_b3(venc_dt)
    sup_volb3      = buscar_delta50_b3(venc_ref_b3)
    if sup_volb3 is None:
        sup_volb3 = buscar_sup_volb3_fallback()  # fallback pro Excel antigo

    xauusd_d   = buscar_yfinance(TICKERS["xauusd"])
    xauusd     = xauusd_d["close"] if xauusd_d else None
    ouro_brl   = buscar_ouro_brl()
    dxy_var    = buscar_variacao_dxy()
    cme_d      = buscar_yfinance(TICKERS["cme"])
    brlusd_d   = buscar_yfinance(TICKERS["brl_usd"])
    ptax_cots  = buscar_ptax()

# ─── Cálculos derivados ─────────────────────
wdo_fut    = planilha.get("wdo_fut")   if planilha else None
dolar_spot = planilha.get("dolar_spot") if planilha else None
di1_fut    = planilha.get("di1_fut")   if planilha else None
du         = planilha.get("business_days_remaining") if planilha else None
venc_str   = planilha.get("expiration_date") if planilha else "—"

wdo_abertura  = calc_abertura_wdo(wdo_fut, dxy_var)
over          = calc_over(di1_fut, du)
preco_justo   = calc_preco_justo(dolar_spot, over)
paridade_ouro = calc_paridade_ouro(xauusd, ouro_brl)
bandas        = calc_bandas(wdo_abertura, over, sup_volb3)
bandas_ptax   = calc_bandas_ptax(wdo_abertura, over, sup_volb3, ptax_cots)

horario = agora_br_str()

# ─────────────────────────────────────────────
# STATUS DOS DADOS (mini painel)
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
    c4.markdown(f"**DXY** {status_badge(dxy_var is not None)}", unsafe_allow_html=True)
    ptax_ok = any(p is not None for p in ptax_cots)
    c5.markdown(f"**PTAX** {status_badge(ptax_ok)}", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# ABAS PRINCIPAIS
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
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Abertura Est.",  fmt(wdo_abertura, 2),
              delta=fmt(wdo_abertura - wdo_fut, 2) if wdo_abertura and wdo_fut else None)
    m2.metric("Preço Justo",    fmt(preco_justo, 4))
    m3.metric("Paridade Ouro",  fmt(paridade_ouro, 4))
    m4.metric("Variação DXY",   f"{fmt(dxy_var, 2)}%" if dxy_var else "—")

    st.markdown("<hr style='border-color:#30363d'>", unsafe_allow_html=True)

    with st.expander("📄 Dados da planilha", expanded=False):
        if planilha:
            labels = {
                "wdo_fut":                 "WDO Futuro",
                "dolar_spot":              "Dólar Spot",
                "di1_fut":                 "DI1 Futuro (taxa a.a.)",
                "frp0":                    "FRP0",
                "expiration_date":         "Vencimento WDO",
                "business_days_remaining": "Dias Úteis até Vencimento",
                "atualizado_em":           "Sincronizado em",
                "coluna_usada":            "Coluna usada (fallback GitHub)",
                "fonte":                   "Fonte dos dados",
            }
            rows = [{"Descrição": labels.get(k, k), "Valor": str(v)}
                    for k, v in planilha.items() if k != "minutos_desde_sync"]
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        else:
            st.warning("Dados da planilha não disponíveis.")

    with st.expander("🥇 Ouro — valores em USD e BRL", expanded=False):
        c1, c2 = st.columns(2)
        c1.metric("Ouro Spot (USD/oz)", fmt(xauusd,   2))
        c2.metric("Ouro (R$/grama)",    fmt(ouro_brl, 2))

    with st.expander("📐 Over (DI1 acumulado)", expanded=False):
        st.metric("Over", fmt(over, 6))

    with st.expander("📅 Vencimento do contrato", expanded=False):
        c1, c2 = st.columns(2)
        c1.metric("Próximo vencimento",   venc_str)
        c2.metric("Dias úteis restantes", f"{du} du" if du else "—")

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
            "Valor (pts)": [bandas["1ª Máxima"], bandas["1ª Mínima"],
                            bandas["2ª Máxima"], bandas["2ª Mínima"]],
            "Distância":   [round(bandas["1ª Máxima"] - wdo_abertura, 2),
                            round(bandas["1ª Mínima"] - wdo_abertura, 2),
                            round(bandas["2ª Máxima"] - wdo_abertura, 2),
                            round(bandas["2ª Mínima"] - wdo_abertura, 2)],
        })
        st.dataframe(colorir_bandas(df_b), hide_index=True, width="stretch")
    else:
        st.warning("Dados insuficientes para calcular as bandas. Verifique a aba ⚙️ Ajuste Manual.")

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
    if qtde < 4:
        st.info(f"⏳ {qtde} cotação(ões) disponível(is). Aguardando as próximas...")
    else:
        st.success("✅ Todas as cotações PTAX do dia disponíveis.")

    if ptax_validas:
        cols = st.columns(4)
        for i, (col, p) in enumerate(zip(cols, ptax_cots)):
            with col:
                if p:
                    st.metric(
                        f"PTAX {i+1}",
                        f"R$ {p['valor']:.4f}",
                        help=f"Data: {p['data']} · Hora: {p['hora']}",
                    )
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
        st.warning("Dados insuficientes para as bandas PTAX. Verifique a aba ⚙️ Ajuste Manual.")

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
                "USD":          [fmt(cme_d["open"],6), fmt(cme_d["high"],6),
                                 fmt(cme_d["low"],6),  fmt(cme_d["close"],6), fmt(cme_d["prev"],6)],
                "BRL pts":      [fmt(cme_open_brl,2), fmt(cme_high_brl,2),
                                 fmt(cme_low_brl,2),   fmt(cme_close_brl,2), fmt(cme_prev_brl,2)],
            })
            st.dataframe(df_cme, hide_index=True, width="stretch")
            st.metric("Δ Fechamento", fmt(delta_cme, 2) if delta_cme else "—",
                      delta=fmt(delta_cme, 2) if delta_cme else None)
        else:
            st.warning("Dados CME não disponíveis.")

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
                "BRLUSD":  [fmt(brlusd_d["open"],6), fmt(brlusd_d["high"],6),
                            fmt(brlusd_d["low"],6),   fmt(brlusd_d["close"],6), fmt(brlusd_d["prev"],6)],
                "USD/BRL": [fmt(usd_open,4), fmt(usd_high,4),
                            fmt(usd_low,4),  fmt(usd_close,4), fmt(usd_prev,4)],
            })
            st.dataframe(df_brl, hide_index=True, width="stretch")
            st.metric("Δ Fechamento", fmt(delta_usd, 4) if delta_usd else "—",
                      delta=fmt(delta_usd, 4) if delta_usd else None)
        else:
            st.warning("Dados BRL/USD não disponíveis.")

    st.markdown("<hr style='border-color:#30363d'>", unsafe_allow_html=True)
    st.markdown("#### DXY — Índice do Dólar")
    if brlusd_d:  # reaproveita cache — evita 2ª chamada idêntica a buscar_yfinance(dxy)
        pass
    dxy_d = buscar_yfinance(TICKERS["dxy"])
    if dxy_d:
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Abertura",   fmt(dxy_d["open"],  3))
        c2.metric("Máxima",     fmt(dxy_d["high"],  3))
        c3.metric("Mínima",     fmt(dxy_d["low"],   3))
        c4.metric("Fechamento", fmt(dxy_d["close"], 3))
        c5.metric("Variação",   f"{fmt(dxy_var, 2)}%" if dxy_var else "—")
    else:
        st.warning("Dados DXY não disponíveis.")

# ══════════════════════════════════════════════
# ABA 5 — AJUSTE MANUAL
# ══════════════════════════════════════════════
with aba5:
    st.markdown("#### Sobrescrever valores para recalcular")
    st.caption("Use esta aba se algum dado automático estiver incorreto ou indisponível.")

    with st.form("form_manual"):
        c1, c2 = st.columns(2)
        with c1:
            m_wdo    = st.number_input("WDO Futuro — Fechamento", value=float(wdo_fut or 0), format="%.2f")
            m_spot   = st.number_input("Dólar Spot",                value=float(dolar_spot or 0), format="%.4f")
            m_di1    = st.number_input("DI1 Futuro (taxa a.a.)",    value=float(di1_fut or 0), format="%.5f")
        with c2:
            m_dxy    = st.number_input("Variação DXY (%)",          value=float(dxy_var or 0), format="%.4f")
            m_du     = st.number_input("Dias Úteis até Vencimento", value=int(du or 0), step=1)
            m_sup    = st.number_input("Delta 50 Vol B3",           value=float(sup_volb3 or 0), format="%.4f")
        submitted = st.form_submit_button("Recalcular com valores manuais", width="stretch")

    if submitted:
        m_abertura = calc_abertura_wdo(m_wdo, m_dxy)
        m_over     = calc_over(m_di1, m_du)
        m_pjusto   = calc_preco_justo(m_spot, m_over)
        m_bandas   = calc_bandas(m_abertura, m_over, m_sup)

        st.markdown("#### Resultados (ajuste manual)")
        c1, c2, c3 = st.columns(3)
        c1.metric("Abertura WDO",  fmt(m_abertura, 2))
        c2.metric("Over (DI1)",    fmt(m_over, 6))
        c3.metric("Preço Justo",   fmt(m_pjusto, 4))

        if m_bandas:
            df_mb = pd.DataFrame({
                "Tipo":        ["1ª Máxima", "1ª Mínima", "2ª Máxima", "2ª Mínima"],
                "Valor (pts)": [m_bandas["1ª Máxima"], m_bandas["1ª Mínima"],
                                m_bandas["2ª Máxima"], m_bandas["2ª Mínima"]],
            })
            st.dataframe(colorir_bandas(df_mb), hide_index=True, width="stretch")

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
