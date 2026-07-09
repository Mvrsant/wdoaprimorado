# WDO — Calculadora de Paridades do Mini Contrato Futuro de Dólar

App em Streamlit para cálculo de abertura estimada, bandas, preço justo
e paridades do WDO (mini dólar futuro, B3).

## Estrutura

```
app.py                      → app Streamlit (deploy — não precisa de credenciais)
sync_dde.py                 → roda LOCALMENTE, sincroniza dados do Profit/DDE com o Google Sheets
requirements.txt            → dependências do app (deploy)
requirements_sync_local.txt → dependências do sync_dde.py (só na máquina local)
SETUP_GOOGLE_SHEETS.md      → passo a passo de configuração do Google Sheets/Service Account
.gitignore                  → garante que credenciais não sejam commitadas
```

## Como rodar

### App (deploy)
```bash
pip install -r requirements.txt
streamlit run app.py
```

### Sincronização local (na máquina com Profit + Excel/DDE)
```bash
pip install -r requirements_sync_local.txt
python sync_dde.py
```
Configurar antes: ver `SETUP_GOOGLE_SHEETS.md`.

## ⚠️ Segurança

- `service_account.json` (credencial do Google) **nunca** deve ser commitado.
  Já está no `.gitignore`.
- Se este repositório for público, mantenha o `SHEET_ID` funcional mas
  lembre que qualquer pessoa com o link do Sheets em modo "leitor" consegue
  ver os dados — avalie se isso é aceitável ou se prefere repositório/planilha
  privados.
- Ao fazer deploy (Streamlit Community Cloud, etc.), o app só *lê* do Sheets
  via CSV público — não precisa de nenhuma credencial no ambiente de deploy.

## Fontes de dados

| Dado                          | Fonte primária          | Fallback                  |
|--------------------------------|--------------------------|----------------------------|
| WDOFUT / USD-BRL / DI1 / FRP0  | Google Sheets (via DDE)  | Planilha estática no GitHub |
| Delta 50 Vol. B3               | Scraping da página B3    | Excel `base_b3` (antigo)   |
| Ouro, DXY, CME, PTAX            | yfinance / BCB / scraping | —                          |
