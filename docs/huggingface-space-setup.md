# HuggingFace Space Setup Guide: TickerTruth Interactive Explorer

Create an interactive HuggingFace Space for users to explore NSE corporate actions, symbol lineage, and adjustment factors with live queries, sample results, and educational content.

---

## Part 1: Create the Space (5 minutes)

### Step 1: Navigate to HuggingFace Spaces
1. Go to https://huggingface.co/new-space
2. **Space name:** `tickertruth-nse-explorer` (or similar)
3. **License:** CC-BY-4.0 (or your preference)
4. **Space SDK:** `Streamlit` (recommended for data exploration)
5. Click **Create Space**

### Step 2: Clone and Set Up Local
```bash
git clone https://huggingface.co/spaces/YOUR_USERNAME/tickertruth-nse-explorer
cd tickertruth-nse-explorer
```

### Step 3: Minimal File Structure
```
tickertruth-nse-explorer/
├── app.py                      # Main Streamlit app
├── requirements.txt            # Python dependencies
├── sample_data/
│   ├── corporate_actions.parquet    # Sample data (versioned monthly)
│   ├── symbol_lineage.parquet       # Symbol history
│   ├── security_master.parquet      # Current symbols
│   └── adjustment_factors.parquet   # Pre-calculated adjustments
├── queries.py                  # Pre-built query functions
└── README.md                   # Space documentation
```

---

## Part 2: Core Streamlit App (`app.py`)

Create an interactive query builder with 6 pre-built use cases:

```python
import streamlit as st
import pandas as pd
import duckdb
from datetime import datetime, timedelta

# Page config
st.set_page_config(
    page_title="TickerTruth NSE Explorer",
    page_icon="📈",
    layout="wide"
)

st.title("🇮🇳 TickerTruth NSE Explorer")
st.markdown("""
Explore NSE symbol lineage, corporate actions, and adjustment factors.
Learn how to fix backtests, reconcile portfolios, and track symbol changes.
""")

# Load sample data (cached for performance)
@st.cache_data
def load_data():
    """Load sample parquet files"""
    corporate_actions = pd.read_parquet("sample_data/corporate_actions.parquet")
    symbol_lineage = pd.read_parquet("sample_data/symbol_lineage.parquet")
    security_master = pd.read_parquet("sample_data/security_master.parquet")
    adjustment_factors = pd.read_parquet("sample_data/adjustment_factors.parquet")
    return {
        'corporate_actions': corporate_actions,
        'symbol_lineage': symbol_lineage,
        'security_master': security_master,
        'adjustment_factors': adjustment_factors
    }

data = load_data()

# Sidebar: Navigation
with st.sidebar:
    st.markdown("### 📚 Use Cases")
    use_case = st.radio(
        "Select a use case to explore:",
        [
            "1️⃣ Fix Broken Backtests",
            "2️⃣ Reconcile Portfolio NAV",
            "3️⃣ Track Symbol Renames",
            "4️⃣ Understand Delistings",
            "5️⃣ Validate Price Gaps",
            "6️⃣ Calculate Adjustments"
        ]
    )
    st.markdown("---")
    st.markdown("**Last Updated:** 2026-06-07")
    st.markdown("[📖 Full Guide](https://github.com/tickertruth/nse-india-security-master/docs/huggingface-space-guide.md)")
    st.markdown("[💬 Feedback](https://huggingface.co/datasets/tickertruth/nse-india-security-master/discussions)")

# Main content: Use case tabs
if use_case == "1️⃣ Fix Broken Backtests":
    st.header("Fix Broken Backtests with Split Adjustments")
    
    st.markdown("""
    Stock splits cause price discontinuities. This tool shows you how to adjust 
    historical prices to match post-split prices.
    """)
    
    # Input: Symbol selector
    symbols = sorted(data['corporate_actions']['symbol'].unique())
    symbol = st.selectbox(
        "Select a stock:",
        symbols,
        index=symbols.index('RELIANCE') if 'RELIANCE' in symbols else 0
    )
    
    # Query splits for this symbol
    df_splits = data['corporate_actions'][
        (data['corporate_actions']['symbol'] == symbol) &
        (data['corporate_actions']['action_type'].isin(['SPLIT', 'BONUS']))
    ][['symbol', 'ex_date', 'action_type', 'value_ratio', 'adjustment_factor']].sort_values('ex_date', ascending=False)
    
    if len(df_splits) > 0:
        st.subheader(f"Events for {symbol}")
        st.dataframe(df_splits, use_container_width=True)
        
        # Educational explanation
        st.markdown("### How to Use This Data")
        with st.expander("📖 Click to expand explanation"):
            st.markdown(f"""
            **Adjustment Factor Interpretation:**
            - If a stock has **5 splits** with factors [0.5, 0.5, 0.5, 0.5, 0.5], 
              the cumulative adjustment is: 0.5^5 = 0.03125
            - This means 1 original share = 0.03125 current shares
            - To compare historical prices to today: **multiply old price × cumulative factor**
            
            **Example:** {symbol} closed at ₹2000 on 2023-05-30 with a 1:5 split on 2023-05-31
            - Historical price for backtesting: 2000 × 0.2 = ₹400
            - This makes it comparable to post-split prices
            """)
        
        # Download section
        csv = df_splits.to_csv(index=False)
        st.download_button(
            label=f"Download {symbol} splits as CSV",
            data=csv,
            file_name=f"{symbol}_splits.csv",
            mime="text/csv"
        )
    else:
        st.info(f"No splits/bonuses found for {symbol}")

elif use_case == "2️⃣ Reconcile Portfolio NAV":
    st.header("Reconcile Portfolio NAV After Dividends")
    
    st.markdown("""
    Dividend payments cause NAV drops. This tool helps you understand and 
    reconcile dividend impacts on portfolio valuation.
    """)
    
    # Multi-select symbols
    available_symbols = sorted(data['corporate_actions']['symbol'].unique())
    selected_symbols = st.multiselect(
        "Select stocks to analyze (default: top tech stocks):",
        available_symbols,
        default=['INFY', 'TCS', 'WIPRO'] if all(s in available_symbols for s in ['INFY', 'TCS', 'WIPRO']) 
                 else available_symbols[:3]
    )
    
    # Date range
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Start date:",
            datetime.now() - timedelta(days=365)
        )
    with col2:
        end_date = st.date_input(
            "End date:",
            datetime.now()
        )
    
    # Query dividends
    df_divs = data['corporate_actions'][
        (data['corporate_actions']['symbol'].isin(selected_symbols)) &
        (data['corporate_actions']['action_type'] == 'DIVIDEND') &
        (data['corporate_actions']['ex_date'] >= pd.Timestamp(start_date)) &
        (data['corporate_actions']['ex_date'] <= pd.Timestamp(end_date))
    ][['symbol', 'ex_date', 'dividend_amount', 'frequency']].sort_values('ex_date', ascending=False)
    
    if len(df_divs) > 0:
        st.subheader("Dividend Events")
        st.dataframe(df_divs, use_container_width=True)
        
        st.markdown("### Portfolio Impact Calculator")
        col1, col2, col3 = st.columns(3)
        with col1:
            holdings = st.number_input("INFY shares:", value=100)
        with col2:
            infy_div = df_divs[df_divs['symbol'] == 'INFY']['dividend_amount'].sum() if 'INFY' in df_divs['symbol'].values else 0
        with col3:
            st.metric("INFY Dividend Impact", f"₹{holdings * infy_div:,.0f}", delta=f"-{holdings * infy_div:,.0f}")
        
        with st.expander("📖 Understanding NAV Impact"):
            st.markdown("""
            **Why does NAV drop on dividend ex-date?**
            - Before ex-date: Shareholder owns stock worth ₹100 + upcoming ₹5 dividend
            - On ex-date: Stock price drops ~₹5 (the dividend amount), shareholder now owns ₹95 stock + ₹5 cash
            - Net NAV is the same, but composition changed (stock → cash)
            
            **For portfolios:** This is expected and not a loss. It's a conversion of 
            retained earnings into cash distributions.
            """)
    else:
        st.info(f"No dividends found for selected symbols in this date range")

elif use_case == "3️⃣ Track Symbol Renames":
    st.header("Track Symbol Renames and Status Changes")
    
    st.markdown("""
    When NSE renames a ticker, your data pipeline breaks. This tool shows you 
    all symbol changes so you can update your systems.
    """)
    
    # Time range for renames
    months_back = st.slider(
        "Show renames from last N months:",
        min_value=1,
        max_value=24,
        value=12
    )
    
    df_lineage = data['symbol_lineage'][
        data['symbol_lineage']['effective_date'] >= 
        (datetime.now() - timedelta(days=30*months_back)).date()
    ][['old_symbol', 'new_symbol', 'effective_date', 'event_type', 'reason']].sort_values('effective_date', ascending=False)
    
    if len(df_lineage) > 0:
        st.subheader(f"Symbol Changes (Last {months_back} Months)")
        st.dataframe(df_lineage, use_container_width=True)
        
        st.markdown("### Update Your Pipeline")
        with st.expander("📖 Code example"):
            st.code("""
# Build symbol mapping from lineage
symbol_map = {}
for _, row in df_lineage.iterrows():
    old_sym = row['old_symbol']
    new_sym = row['new_symbol']
    date = row['effective_date']
    
    # Map: get security_id from both old and new symbols
    security_id = get_security_id(new_sym)
    symbol_map[security_id] = {
        'old_symbol': old_sym,
        'new_symbol': new_sym,
        'change_date': date
    }

# Use in price fetch
def get_continuous_price_series(security_id, start_date, end_date):
    prices = []
    for date in date_range(start_date, end_date):
        sym = symbol_map[security_id].get_symbol_for_date(date)
        price = fetch_price(sym, date)
        prices.append(price)
    return prices
            """, language="python")
        
        csv = df_lineage.to_csv(index=False)
        st.download_button(
            label="Download symbol changes as CSV",
            data=csv,
            file_name="symbol_changes.csv",
            mime="text/csv"
        )
    else:
        st.info("No symbol changes in this period")

elif use_case == "4️⃣ Understand Delistings":
    st.header("Understand Delistings and Merger Chains")
    
    st.markdown("""
    Track what happened to delisted stocks: merged, defaulted, renamed?
    """)
    
    event_type = st.selectbox(
        "Filter by event type:",
        ['DELISTING', 'MERGER', 'RENAME', 'SUSPENSION']
    )
    
    df_events = data['symbol_lineage'][
        data['symbol_lineage']['event_type'] == event_type
    ][['symbol', 'old_symbol', 'new_symbol', 'effective_date', 'reason']].sort_values('effective_date', ascending=False).head(20)
    
    if len(df_events) > 0:
        st.dataframe(df_events, use_container_width=True)
    else:
        st.info(f"No {event_type} events found")

elif use_case == "5️⃣ Validate Price Gaps":
    st.header("Validate Price Gaps Against Corporate Actions")
    
    st.markdown("""
    See if a price drop matches a corporate action (split, dividend) or 
    if it's a market move.
    """)
    
    symbol = st.selectbox(
        "Select a stock:",
        sorted(data['corporate_actions']['symbol'].unique())
    )
    
    # Show corporate actions + expected price impact
    df_actions = data['corporate_actions'][
        data['corporate_actions']['symbol'] == symbol
    ][['ex_date', 'action_type', 'value_ratio', 'adjustment_factor']].sort_values('ex_date', ascending=False).head(10)
    
    if len(df_actions) > 0:
        st.subheader(f"Expected Price Impacts for {symbol}")
        
        # Add expected price change column
        def expected_change(row):
            if row['action_type'] == 'SPLIT':
                ratio = float(row['value_ratio'].split(':')[0])
                return f"{-100 * (1 - ratio):.1f}%"
            elif row['action_type'] == 'BONUS':
                ratio = float(row['value_ratio'].split(':')[0])
                return f"{-100 * (1 - ratio):.1f}%"
            else:
                return "Variable"
        
        df_actions['expected_price_change'] = df_actions.apply(expected_change, axis=1)
        st.dataframe(df_actions, use_container_width=True)

elif use_case == "6️⃣ Calculate Adjustments":
    st.header("Calculate Correct Adjustment Factors")
    
    st.markdown("""
    Understand cascading adjustments (splits on top of bonuses) and 
    cumulative normalization factors.
    """)
    
    symbol = st.selectbox(
        "Select a stock:",
        sorted(data['adjustment_factors']['symbol'].unique())
    )
    
    df_adj = data['adjustment_factors'][
        data['adjustment_factors']['symbol'] == symbol
    ][['ex_date', 'action_type', 'adjustment_factor', 'cumulative_adjustment_factor']].sort_values('ex_date')
    
    if len(df_adj) > 0:
        st.dataframe(df_adj, use_container_width=True)
        
        st.markdown("### Normalization Formula")
        st.code(f"""
# For {symbol}:
cumulative_factor = {df_adj['cumulative_adjustment_factor'].iloc[-1]:.6f}

# To compare historical price to current:
historical_price = 100  # e.g., ₹100 in 2010
normalized_price = historical_price * {df_adj['cumulative_adjustment_factor'].iloc[-1]:.6f}
# = ₹{100 * df_adj['cumulative_adjustment_factor'].iloc[-1]:.2f}

# This makes 2010 prices comparable to today
        """)

# Footer
st.markdown("---")
st.markdown("""
📚 **Learn More:** [Full Guide](../huggingface-space-guide.md) | 
💬 **Feedback:** [Discussions](https://huggingface.co/datasets/tickertruth/nse-india-security-master/discussions) |
📊 **Dataset:** [HuggingFace](https://huggingface.co/datasets/tickertruth/nse-india-security-master)
""")
```

---

## Part 3: Dependencies (`requirements.txt`)

```
streamlit>=1.28.0
pandas>=2.0.0
pyarrow>=12.0.0
duckdb>=0.9.0
numpy>=1.24.0
```

---

## Part 4: Sample Data Strategy

### Option A: Embedded Sample Data (Recommended for <50MB)

**Pros:** Simple, no dependencies, fast loads  
**Cons:** Manual updates, large files in git

1. **Extract sample data locally:**
```bash
python -c "
import pandas as pd
import duckdb

# Connect to your production Dolt database
conn = duckdb.connect('dolt://...')

# Sample: Top 50 symbols, last 5 years of corporate actions
top_symbols = conn.execute('''
    SELECT DISTINCT symbol FROM fact_corporate_action_event 
    LIMIT 50
''').fetchall()

symbols_list = [s[0] for s in top_symbols]

# Export to parquet
df = conn.execute(f'''
    SELECT * FROM fact_corporate_action_event 
    WHERE symbol IN ({','.join([f\"'{s}'\" for s in symbols_list])})
      AND ex_date >= CURRENT_DATE - INTERVAL 5 YEARS
''').df()

df.to_parquet('sample_data/corporate_actions.parquet')
print(f'Exported {len(df)} corporate action records')
"
```

2. **Check into Space repo:**
```bash
git add sample_data/*.parquet
git commit -m "chore: refresh sample data for June 2026 release"
git push
```

### Option B: Lazy Load from Remote (For >100MB)

**Pros:** Smaller Space repo, always fresh data  
**Cons:** Slower initial load, requires stable remote URL

1. **Upload sample data to Cloudflare R2 or HuggingFace Hub:**
```python
from huggingface_hub import hf_hub_download

@st.cache_data
def load_data():
    # Download from HF Hub on first load, cache locally
    df = pd.read_parquet(
        hf_hub_download(
            repo_id="tickertruth/nse-india-security-master",
            filename="sample_data/corporate_actions.parquet",
            repo_type="dataset"
        )
    )
    return df
```

2. **Or from R2 (low-cost):**
```python
import httpx

@st.cache_data
def load_data():
    df = pd.read_parquet(
        "https://r2.tickertruth.com/samples/corporate_actions.parquet"
    )
    return df
```

---

## Part 5: Monthly Data Refresh Automation

### Option A: GitHub Actions (Free, Simple)

Create `.github/workflows/refresh-space-samples.yml` in your main repo:

```yaml
name: Refresh HF Space Sample Data

on:
  schedule:
    # Run on 15th of each month at 6 AM UTC
    - cron: '0 6 15 * *'
  workflow_dispatch:  # Manual trigger

jobs:
  refresh:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install pandas pyarrow duckdb
      
      - name: Extract sample data from Dolt
        env:
          DOLT_USERNAME: ${{ secrets.DOLT_USERNAME }}
          DOLT_PASSWORD: ${{ secrets.DOLT_PASSWORD }}
        run: |
          python scripts/export_sample_data.py
      
      - name: Commit and push to Space repo
        run: |
          git config user.email "ci@tickertruth.com"
          git config user.name "TickerTruth Bot"
          git add sample_data/*.parquet
          git commit -m "chore: refresh sample data - $(date +%Y-%m-%d)"
          git push https://huggingface.co/spaces/YOUR_USERNAME/tickertruth-nse-explorer
        env:
          HF_TOKEN: ${{ secrets.HF_TOKEN }}
```

### Option B: Manual Monthly Refresh (Minimal Overhead)

Every month (after your nightly pipeline runs):

```bash
# 1. Extract and export
python pipelines/run.py --export-space-samples --date 2026-06-15

# 2. Upload to Space
cd ~/hf-spaces/tickertruth-nse-explorer
git pull origin main
cp ~/apps/TickerTruth/sample_data/*.parquet ./sample_data/
git add sample_data/
git commit -m "chore: refresh sample data for June 2026 release"
git push

# 3. Space auto-reloads on push
```

---

## Part 6: Script to Export Sample Data (`scripts/export_sample_data.py`)

```python
import duckdb
import pandas as pd
from pathlib import Path
from datetime import datetime

# Connect to production Dolt database
conn = duckdb.connect('dolt://...')

output_dir = Path("sample_data")
output_dir.mkdir(exist_ok=True)

# Export 1: Corporate actions (top 50 symbols, 5 years)
print("Exporting corporate actions...")
df_ca = conn.execute("""
    SELECT 
        symbol, ex_date, action_type, value_ratio, 
        adjustment_factor, dividend_amount, frequency
    FROM fact_corporate_action_event
    WHERE symbol IN (
        SELECT symbol FROM dim_security_master 
        WHERE trading_status = 'ACTIVE'
        ORDER BY market_cap DESC NULLS LAST
        LIMIT 50
    )
      AND ex_date >= CURRENT_DATE - INTERVAL '5 YEARS'
    ORDER BY ex_date DESC
""").df()
df_ca.to_parquet(output_dir / "corporate_actions.parquet", compression='snappy')
print(f"  ✓ {len(df_ca)} records")

# Export 2: Symbol lineage (renames, delistings)
print("Exporting symbol lineage...")
df_lin = conn.execute("""
    SELECT 
        symbol, old_symbol, new_symbol, effective_date, 
        event_type, reason
    FROM lineage_symbol_event
    WHERE effective_date >= CURRENT_DATE - INTERVAL '10 YEARS'
    ORDER BY effective_date DESC
""").df()
df_lin.to_parquet(output_dir / "symbol_lineage.parquet", compression='snappy')
print(f"  ✓ {len(df_lin)} records")

# Export 3: Security master (current, top 100)
print("Exporting security master...")
df_sm = conn.execute("""
    SELECT 
        symbol, isin, company_name, sector, 
        listing_date, trading_status, market_cap
    FROM dim_security_master
    WHERE trading_status = 'ACTIVE'
    ORDER BY market_cap DESC NULLS LAST
    LIMIT 100
""").df()
df_sm.to_parquet(output_dir / "security_master.parquet", compression='snappy')
print(f"  ✓ {len(df_sm)} records")

# Export 4: Adjustment factors (cumulative)
print("Exporting adjustment factors...")
df_adj = conn.execute("""
    SELECT 
        symbol, ex_date, action_type, 
        adjustment_factor, cumulative_adjustment_factor
    FROM fact_adjustment_factor
    WHERE symbol IN (
        SELECT DISTINCT symbol FROM fact_corporate_action_event
        WHERE ex_date >= CURRENT_DATE - INTERVAL '5 YEARS'
    )
    ORDER BY symbol, ex_date
""").df()
df_adj.to_parquet(output_dir / "adjustment_factors.parquet", compression='snappy')
print(f"  ✓ {len(df_adj)} records")

print(f"\n✅ All samples exported at {datetime.now().isoformat()}")
```

---

## Part 7: README for the Space

```markdown
# TickerTruth NSE Explorer

Interactive exploration of NSE symbol lineage and corporate actions.

## Features

- **Fix Backtests:** Find splits and bonuses, apply adjustment factors
- **Track Renames:** Monitor ticker changes across NSE
- **Understand Delistings:** See merger chains and status changes
- **Reconcile NAV:** Analyze dividend impacts on portfolios
- **Validate Price Gaps:** Match price drops to corporate events
- **Calculate Adjustments:** Understand cascading factors

## Data Source

Sample data is extracted monthly from the full TickerTruth dataset.
See [full dataset](https://huggingface.co/datasets/tickertruth/nse-india-security-master)
for production-grade access with versioning.

## Usage

1. Select a use case in the sidebar
2. Choose a stock or date range
3. View results and download as CSV
4. Read the explanations to understand how to apply the data

## Questions?

- 📖 [Full Guide](https://github.com/tickertruth/nse-india-security-master/docs/huggingface-space-guide.md)
- 💬 [Discussions](https://huggingface.co/datasets/tickertruth/nse-india-security-master/discussions)
- 📊 [Full Dataset](https://huggingface.co/datasets/tickertruth/nse-india-security-master)

---

**Last Updated:** 2026-06-07  
**Data Refresh:** Monthly (15th of each month)
```

---

## Part 8: Data Refresh Frequency & Strategy

| Frequency | Effort | Freshness | Cost | Recommendation |
|-----------|--------|-----------|------|-----------------|
| **Weekly** | High | High | Low | Only if data changes weekly (not typical for corporate actions) |
| **Monthly** | Low | Good | Low | ✅ **Recommended** — sync after nightly pipeline run |
| **Quarterly** | Very Low | Fair | Very Low | OK for low-traffic spaces, misses some events |
| **On-Demand** | Manual | Fresh | Low | Good fallback if someone reports stale data |

### Recommended: Monthly, Scheduled

```yaml
# Timing: 15th of each month, 2 hours after nightly pipeline completes
schedule:
  - cron: '0 6 15 * *'
```

**Why monthly?**
- Corporate actions are announced weeks/months in advance → no urgent need for daily updates
- Symbol renames are infrequent → monthly snapshot is sufficient
- Reduces maintenance burden and keeps sample data size manageable
- Aligns with your nightly pipeline refresh

### Fallback: Manual Update

If a user reports stale data:
```bash
# Quick 5-minute refresh
python scripts/export_sample_data.py && \
cd ~/hf-spaces/tickertruth-nse-explorer && \
git pull && git add sample_data/ && \
git commit -m "chore: manual refresh - user report" && \
git push
```

---

## Part 9: Deployment Checklist

- [ ] Create Space at https://huggingface.co/new-space
- [ ] Clone Space repo locally
- [ ] Copy `app.py` and `requirements.txt`
- [ ] Create `sample_data/` with parquet files
- [ ] Test locally: `streamlit run app.py`
- [ ] Push to HF: `git push`
- [ ] Space auto-deploys (1-2 minutes)
- [ ] Set up GitHub Actions for monthly refresh
- [ ] Add link to Space in dataset README
- [ ] Post announcement in discussions

---

## Part 10: Monitoring & Maintenance

### Monthly Checklist (after data refresh)

```bash
# 1. Verify space loaded
curl -s https://huggingface.co/spaces/YOUR_USERNAME/tickertruth-nse-explorer | grep "TickerTruth NSE Explorer" && echo "✓ Space loaded"

# 2. Check sample data file sizes
ls -lh sample_data/*.parquet

# 3. Spot-check a query (manual)
# - Open Space in browser
# - Run "Fix Broken Backtests" with RELIANCE
# - Verify splits appear correctly

# 4. Monitor discussions for feedback
# - Check for "data is stale" complaints
# - Note any missing corporate actions
```

### Troubleshooting

| Issue | Fix |
|-------|-----|
| Space won't load | Check `requirements.txt`, ensure all dependencies are pinned |
| Data loads slowly | Use `@st.cache_data` decorator (included in template) |
| Old data showing | Clear cache: delete `.streamlit/cache` |
| Sample data too large | Reduce symbols (e.g., top 30 instead of 50) or time window |

---

## Cost Estimate

| Item | Cost | Notes |
|------|------|-------|
| HuggingFace Space (free tier) | $0 | Includes 1 Space for free |
| GitHub Actions (free tier) | $0 | ~5 min/month execution |
| Sample data storage (Space) | $0 | <100MB, no charges |
| Optional: R2 storage (if large) | $0.015/GB | Only if >500MB sample data |
| **Total Monthly** | **$0** | Completely free |

---

## Next Steps

1. **Immediate (1 day):** Create Space, push code, verify it loads
2. **First Refresh (after nightly pipeline):** Export sample data, push to Space
3. **Ongoing (15th of each month):** Automated refresh via GitHub Actions

This gives you a free, low-maintenance, interactive demo that educates users on your dataset and drives engagement.
