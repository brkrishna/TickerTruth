# HuggingFace Space Setup with Gradio (Updated)

Since HuggingFace Spaces best supports **Gradio** natively, here's the revised setup. Gradio is actually better for data exploration interfaces.

---

## Step 1: Create the Space

1. Go to https://huggingface.co/new-space
2. **Space name:** `tickertruth-nse-explorer`
3. **License:** CC-BY-4.0
4. **Space SDK:** Select **Gradio** (not Streamlit)
5. Click **Create Space**

---

## Step 2: Clone and Set Up Files

```bash
git clone https://huggingface.co/spaces/YOUR_USERNAME/tickertruth-nse-explorer
cd tickertruth-nse-explorer

# Create directory structure
mkdir -p sample_data
touch app.py requirements.txt README.md
```

---

## Step 3: Create `app.py` (Gradio App)

```python
import gradio as gr
import pandas as pd
import duckdb
from datetime import datetime, timedelta
from pathlib import Path

# Load sample data (cached)
@gr.cache_data
def load_data():
    """Load sample parquet files"""
    data_dir = Path("sample_data")
    return {
        'corporate_actions': pd.read_parquet(data_dir / "corporate_actions.parquet"),
        'symbol_lineage': pd.read_parquet(data_dir / "symbol_lineage.parquet"),
        'security_master': pd.read_parquet(data_dir / "security_master.parquet"),
        'adjustment_factors': pd.read_parquet(data_dir / "adjustment_factors.parquet"),
    }

data = load_data()

# ============================================================================
# USE CASE 1: Fix Broken Backtests
# ============================================================================

def fix_backtests(symbol):
    """Find splits and bonuses for a symbol"""
    df = data['corporate_actions'][
        (data['corporate_actions']['symbol'] == symbol) &
        (data['corporate_actions']['action_type'].isin(['SPLIT', 'BONUS']))
    ][['symbol', 'ex_date', 'action_type', 'value_ratio', 'adjustment_factor']].sort_values('ex_date', ascending=False)
    
    if len(df) == 0:
        return "No splits or bonuses found for this symbol", None
    
    explanation = f"""
### How to Use This Data

**Adjustment Factor Explanation:**
- The adjustment factor tells you how to scale historical prices
- If a stock has multiple splits with factors [0.5, 0.5], cumulative = 0.5 × 0.5 = 0.25
- This means 1 original share = 0.25 current shares
- **To compare historical prices to today: multiply old price × cumulative factor**

**Example:** {symbol} with splits shown above
- If {symbol} closed at ₹2000 before the first split
- Adjusted price for backtesting: 2000 × adjustment_factor = ₹[adjusted amount]
- This makes it comparable to today's prices

**For backtesting:** Apply adjustments to all prices BEFORE the ex_date of each split.
    """
    
    return df, explanation

# ============================================================================
# USE CASE 2: Reconcile Portfolio NAV
# ============================================================================

def reconcile_nav(symbols_str, start_date, end_date):
    """Query dividends for portfolio analysis"""
    symbols = [s.strip().upper() for s in symbols_str.split(',')]
    
    df = data['corporate_actions'][
        (data['corporate_actions']['symbol'].isin(symbols)) &
        (data['corporate_actions']['action_type'] == 'DIVIDEND') &
        (pd.to_datetime(data['corporate_actions']['ex_date']).dt.date >= start_date) &
        (pd.to_datetime(data['corporate_actions']['ex_date']).dt.date <= end_date)
    ][['symbol', 'ex_date', 'dividend_amount', 'frequency']].sort_values('ex_date', ascending=False)
    
    if len(df) == 0:
        return "No dividends found for selected symbols", None
    
    explanation = f"""
### Understanding NAV Impact

**Why does NAV drop on dividend ex-date?**
- Before ex-date: Stock value includes upcoming dividend
- On ex-date: Stock price drops ~dividend amount, shareholder gets cash
- Net NAV stays same (stock − cash = dividend), but composition changes

**For portfolios:** This is **expected**. It's not a loss — it's converting 
retained earnings into cash distributions to shareholders.

**Example Impact Calculation:**
- If you own 100 shares paying ₹10 dividend each
- Portfolio impact: 100 × ₹10 = ₹1,000 cash outflow
- Stock price drops ~₹10/share, so total portfolio value unchanged
- But now you hold ₹1,000 cash + lower-priced stock

**Action:** Reconcile NAV by accounting for dividends as cash distributions.
    """
    
    return df, explanation

# ============================================================================
# USE CASE 3: Track Symbol Renames
# ============================================================================

def track_renames(months_back):
    """Get recent symbol renames"""
    cutoff_date = (datetime.now() - timedelta(days=30 * months_back)).date()
    
    df = data['symbol_lineage'][
        (data['symbol_lineage']['effective_date'] >= cutoff_date) &
        (data['symbol_lineage']['event_type'].isin(['RENAME', 'NAME_CHANGE']))
    ][['old_symbol', 'new_symbol', 'effective_date', 'reason']].sort_values('effective_date', ascending=False)
    
    if len(df) == 0:
        return "No renames found in this period", None
    
    explanation = f"""
### Update Your Data Pipeline

**Why this matters:**
- NSE renames tickers for various reasons (company request, symbol optimization)
- Historical data exists under OLD symbol until the change date
- NEW symbol data starts after the change date
- Your pipeline must map both to the same company for continuous analysis

**Implementation:**
```python
# Build symbol mapping
symbol_map = {{}}
for _, row in df.iterrows():
    security_id = get_security_id(row['new_symbol'])
    symbol_map[security_id] = {{
        'old': row['old_symbol'],
        'new': row['new_symbol'],
        'date': row['effective_date']
    }}

# Fetch continuous price series
def get_prices(security_id, start_date, end_date):
    prices = []
    mapping = symbol_map[security_id]
    
    # Use old symbol until change date
    if start_date < mapping['date']:
        old_prices = fetch_prices(mapping['old'], start_date, mapping['date'])
        prices.append(old_prices)
    
    # Use new symbol from change date onward
    if end_date >= mapping['date']:
        new_prices = fetch_prices(mapping['new'], mapping['date'], end_date)
        prices.append(new_prices)
    
    return pd.concat(prices).sort_index()
```

**Action:** Update your symbol lists and fetch logic to use both old and new symbols.
    """
    
    return df, explanation

# ============================================================================
# USE CASE 4: Understand Delistings
# ============================================================================

def understand_delistings(event_type):
    """Find delistings, mergers, suspensions"""
    df = data['symbol_lineage'][
        data['symbol_lineage']['event_type'] == event_type
    ][['symbol', 'old_symbol', 'new_symbol', 'effective_date', 'reason']].sort_values('effective_date', ascending=False).head(20)
    
    if len(df) == 0:
        return f"No {event_type} events found", None
    
    explanation = f"""
### Understanding {event_type} Events

**What this means:**
- **DELISTING:** Company no longer trades; any backtest after this date is invalid
- **MERGER:** Two companies combined; track surviving company symbol going forward
- **SUSPENSION:** Temporary halt; data exists but may have gaps
- **NAME_CHANGE:** Ticker or company name changed; same company continues

**For research:**
- Delisted stocks can't be traded today
- Merged companies continue under surviving symbol
- Always check the reason (bankruptcy vs. acquisition vs. voluntary delisting)

**Action:** 
- For backtests: Stop including symbol after delisting date
- For historical analysis: Track both old and new symbols if merged
- For compliance: Document delistings in your symbol master
    """
    
    return df, explanation

# ============================================================================
# USE CASE 5: Validate Price Gaps
# ============================================================================

def validate_price_gaps(symbol):
    """Show expected price impacts from corporate actions"""
    df = data['corporate_actions'][
        data['corporate_actions']['symbol'] == symbol
    ][['ex_date', 'action_type', 'value_ratio', 'adjustment_factor']].sort_values('ex_date', ascending=False).head(20)
    
    if len(df) == 0:
        return f"No corporate actions found for {symbol}", None
    
    # Add expected price change
    def calculate_expected_change(row):
        if row['action_type'] == 'SPLIT':
            parts = str(row['value_ratio']).split(':')
            if len(parts) == 2:
                ratio = float(parts[0]) / float(parts[1])
                return f"{-100 * (1 - ratio):.1f}%"
        elif row['action_type'] == 'BONUS':
            parts = str(row['value_ratio']).split(':')
            if len(parts) == 2:
                ratio = float(parts[0]) / float(parts[1])
                return f"{-100 * (1 - ratio):.1f}%"
        elif row['action_type'] == 'DIVIDEND':
            return "~-1 to -2% (depends on dividend yield)"
        return "Variable"
    
    df['expected_impact'] = df.apply(calculate_expected_change, axis=1)
    
    explanation = f"""
### Validating Price Gaps

**How to match price drops to events:**
- If stock drops 20% on a date and there's a 1:5 split, the drop is EXPECTED (drop = -80%)
- If stock drops 5% on dividend ex-date for a ₹5 dividend (1.5% yield), drop is EXPECTED
- If stock drops 20% but there's no announced corporate action, it's a MARKET move

**Corporate Action Price Impact:**
- **SPLIT 1:5** → stock drops ~80% (it's a technical adjustment, not a loss)
- **BONUS 1:1** → stock drops ~50% (you get 2 shares for 1, each at half price)
- **DIVIDEND ₹X** → stock drops ~X/stock_price (shareholder gets cash)

**Action:** When you see a gap, first check if a corporate action explains it.
If not, investigate other news (earnings, market events, etc.).
    """
    
    return df, explanation

# ============================================================================
# USE CASE 6: Calculate Adjustment Factors
# ============================================================================

def calculate_adjustments(symbol):
    """Show cumulative adjustment factors"""
    df = data['adjustment_factors'][
        data['adjustment_factors']['symbol'] == symbol
    ][['ex_date', 'action_type', 'adjustment_factor', 'cumulative_adjustment_factor']].sort_values('ex_date').head(30)
    
    if len(df) == 0:
        return f"No adjustment factors found for {symbol}", None
    
    last_factor = df['cumulative_adjustment_factor'].iloc[-1]
    
    explanation = f"""
### Understanding Cumulative Adjustments

**What is cumulative_adjustment_factor?**
- It shows how many current shares equal 1 original share
- Example: If factor is 0.0834, then 1 original share = 0.0834 current shares
- Or: 1 current share ≈ 12x the original share

**How to normalize historical prices:**
```
historical_price = 100 (₹100 in 2010)
cumulative_factor = {last_factor:.6f}
normalized_price = historical_price × cumulative_factor
normalized_price = ₹{100 * last_factor:.2f}

This normalized price is now comparable to today's prices in backtests.
```

**Cascading Adjustments Explained:**
- If stock had: 1:5 bonus (0.2) + 1:2 split (0.5)
- Cumulative = 0.2 × 0.5 = 0.1
- So 1 original share = 0.1 current shares

**Action:** Use cumulative_adjustment_factor for all historical price normalization.
    """
    
    return df, explanation

# ============================================================================
# Build Gradio Interface
# ============================================================================

with gr.Blocks(title="TickerTruth NSE Explorer") as app:
    gr.Markdown("# 🇮🇳 TickerTruth NSE Explorer")
    gr.Markdown("""
    Explore NSE symbol lineage, corporate actions, and adjustment factors.
    Learn how to fix backtests, reconcile portfolios, and track symbol changes.
    
    **Last Updated:** 2026-06-07 | [Full Guide](./huggingface-space-guide.md)
    """)
    
    with gr.Tabs():
        # TAB 1: Fix Broken Backtests
        with gr.Tab("1️⃣ Fix Broken Backtests"):
            symbols = sorted(data['corporate_actions']['symbol'].unique())
            symbol_input = gr.Dropdown(
                choices=symbols,
                value='RELIANCE' if 'RELIANCE' in symbols else symbols[0],
                label="Select a stock"
            )
            btn_1 = gr.Button("Find Splits & Bonuses", variant="primary")
            
            output_table_1 = gr.Dataframe(label="Corporate Actions")
            output_text_1 = gr.Markdown(label="Explanation")
            
            btn_1.click(
                fn=fix_backtests,
                inputs=symbol_input,
                outputs=[output_table_1, output_text_1]
            )
            
            # Auto-run on load
            app.load(fn=fix_backtests, inputs=symbol_input, outputs=[output_table_1, output_text_1])
        
        # TAB 2: Reconcile Portfolio NAV
        with gr.Tab("2️⃣ Reconcile Portfolio NAV"):
            symbols_text = gr.Textbox(
                value="INFY, TCS, WIPRO",
                label="Symbols (comma-separated)",
                placeholder="INFY, TCS, WIPRO"
            )
            start_date = gr.Date(
                value=datetime.now() - timedelta(days=365),
                label="Start Date"
            )
            end_date = gr.Date(
                value=datetime.now(),
                label="End Date"
            )
            btn_2 = gr.Button("Find Dividends", variant="primary")
            
            output_table_2 = gr.Dataframe(label="Dividend Events")
            output_text_2 = gr.Markdown(label="Explanation")
            
            btn_2.click(
                fn=reconcile_nav,
                inputs=[symbols_text, start_date, end_date],
                outputs=[output_table_2, output_text_2]
            )
        
        # TAB 3: Track Symbol Renames
        with gr.Tab("3️⃣ Track Symbol Renames"):
            months_slider = gr.Slider(
                minimum=1,
                maximum=24,
                value=12,
                step=1,
                label="Months Back"
            )
            btn_3 = gr.Button("Find Renames", variant="primary")
            
            output_table_3 = gr.Dataframe(label="Symbol Changes")
            output_text_3 = gr.Markdown(label="Explanation")
            
            btn_3.click(
                fn=track_renames,
                inputs=months_slider,
                outputs=[output_table_3, output_text_3]
            )
            
            app.load(fn=track_renames, inputs=months_slider, outputs=[output_table_3, output_text_3])
        
        # TAB 4: Understand Delistings
        with gr.Tab("4️⃣ Understand Delistings"):
            event_dropdown = gr.Dropdown(
                choices=['DELISTING', 'MERGER', 'SUSPENSION', 'NAME_CHANGE'],
                value='DELISTING',
                label="Event Type"
            )
            btn_4 = gr.Button("Find Events", variant="primary")
            
            output_table_4 = gr.Dataframe(label="Events")
            output_text_4 = gr.Markdown(label="Explanation")
            
            btn_4.click(
                fn=understand_delistings,
                inputs=event_dropdown,
                outputs=[output_table_4, output_text_4]
            )
            
            app.load(fn=understand_delistings, inputs=event_dropdown, outputs=[output_table_4, output_text_4])
        
        # TAB 5: Validate Price Gaps
        with gr.Tab("5️⃣ Validate Price Gaps"):
            symbols_5 = sorted(data['corporate_actions']['symbol'].unique())
            symbol_input_5 = gr.Dropdown(
                choices=symbols_5,
                value='HCLTECH' if 'HCLTECH' in symbols_5 else symbols_5[0],
                label="Select a stock"
            )
            btn_5 = gr.Button("Show Expected Price Impacts", variant="primary")
            
            output_table_5 = gr.Dataframe(label="Corporate Actions")
            output_text_5 = gr.Markdown(label="Explanation")
            
            btn_5.click(
                fn=validate_price_gaps,
                inputs=symbol_input_5,
                outputs=[output_table_5, output_text_5]
            )
            
            app.load(fn=validate_price_gaps, inputs=symbol_input_5, outputs=[output_table_5, output_text_5])
        
        # TAB 6: Calculate Adjustments
        with gr.Tab("6️⃣ Calculate Adjustments"):
            symbols_6 = sorted(data['adjustment_factors']['symbol'].unique())
            symbol_input_6 = gr.Dropdown(
                choices=symbols_6,
                value='TATASTEEL' if 'TATASTEEL' in symbols_6 else symbols_6[0],
                label="Select a stock"
            )
            btn_6 = gr.Button("Show Adjustment Factors", variant="primary")
            
            output_table_6 = gr.Dataframe(label="Adjustment History")
            output_text_6 = gr.Markdown(label="Explanation")
            
            btn_6.click(
                fn=calculate_adjustments,
                inputs=symbol_input_6,
                outputs=[output_table_6, output_text_6]
            )
            
            app.load(fn=calculate_adjustments, inputs=symbol_input_6, outputs=[output_table_6, output_text_6])
    
    # Footer
    gr.Markdown("""
    ---
    📚 **Learn More:** [Full Guide](./huggingface-space-guide.md) | 
    💬 **Feedback:** [Discussions](https://huggingface.co/datasets/tickertruth/nse-india-security-master/discussions) |
    📊 **Dataset:** [HuggingFace](https://huggingface.co/datasets/tickertruth/nse-india-security-master)
    """)

if __name__ == "__main__":
    app.launch()
```

---

## Step 4: `requirements.txt`

```
gradio>=4.0.0
pandas>=2.0.0
pyarrow>=12.0.0
numpy>=1.24.0
```

---

## Step 5: `README.md` for the Space

```markdown
# TickerTruth NSE Explorer

Interactive exploration of NSE symbol lineage and corporate actions data.

## Features

- **Fix Broken Backtests** — Find stock splits and bonuses, apply adjustment factors
- **Reconcile Portfolio NAV** — Analyze dividend impacts on portfolio valuation
- **Track Symbol Renames** — Monitor ticker changes across NSE
- **Understand Delistings** — See merger chains and status changes
- **Validate Price Gaps** — Match price drops to corporate events
- **Calculate Adjustments** — Understand cascading adjustment factors

## Data Source

Sample data extracted monthly from [TickerTruth NSE India Security Master](https://huggingface.co/datasets/tickertruth/nse-india-security-master).

## Usage

1. Select a use case tab
2. Choose a symbol, date range, or filter
3. View results in tabular format
4. Read explanations to understand how to apply the data

## Questions?

- 📖 [Full Exploration Guide](https://github.com/tickertruth/nse-india-security-master/docs/huggingface-space-guide.md)
- 💬 [Dataset Discussions](https://huggingface.co/datasets/tickertruth/nse-india-security-master/discussions)

**Last Updated:** 2026-06-07  
**Data Refresh:** Monthly (15th of each month)
```

---

## Step 6: Add Sample Data Files

Use the same export script from the previous guide:

```bash
python scripts/export_sample_data.py
# This creates: sample_data/corporate_actions.parquet, etc.

# Then push to HF Space
git add sample_data/ app.py requirements.txt README.md
git commit -m "Initial: TickerTruth NSE Explorer"
git push
```

---

## Gradio vs. Streamlit (Why Gradio is Better for HF Spaces)

| Feature | Gradio | Streamlit |
|---------|--------|-----------|
| **Native HF Support** | ✅ First-class | ⚠️ Community SDK |
| **Deployment Speed** | ⚡ <30s | 🐢 1-2 min |
| **State Management** | Clean | Can be quirky |
| **Live Reload** | ✅ Auto | ⚠️ Manual restart |
| **Mobile-Friendly** | ✅ Yes | ⚠️ Limited |
| **Tabular Data UI** | ⭐ Excellent | Good |
| **Documentation** | ✅ HF integrated | External |

**Recommendation:** Use Gradio for HuggingFace Spaces.

---

## Step 7: Deploy

```bash
cd ~/hf-spaces/tickertruth-nse-explorer
git push

# Space auto-deploys in 1-2 minutes
# Then visit: https://huggingface.co/spaces/YOUR_USERNAME/tickertruth-nse-explorer
```

---

## Monthly Refresh (Same as Before)

Use the GitHub Actions workflow from the previous guide — it works with Gradio too. Just adjust the commit message:

```yaml
- git commit -m "chore: refresh sample data - $(date +%Y-%m-%d)"
```

The sample data files (`sample_data/*.parquet`) are version-agnostic; Gradio and Streamlit both read them the same way.

---

**That's it!** You now have an interactive Gradio-based Space with 6 use cases, running on HuggingFace's native SDK with zero cost and monthly data refresh.
