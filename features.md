# Features List - Investiční Kalkulačka

## 1. Finanční Modelování
- **Výpočet Hypotéky:** Standardní anuitní splácení, možnost zadat LTV nebo fixní vlastní kapitál.
- **Cashflow Analýza:** 
  - Měsíční a roční cashflow.
  - Zohlednění daně z příjmu FO (daňový štít úroků).
  - Zapracování neobsazenosti (vacancy rate).
- **Projekce v čase:**
  - Indexace nájmu a nákladů (inflace).
  - Růst hodnoty nemovitosti (apreciace).
  - Vývoj dluhu v čase (amortizace).

## 2. Pokročilé Metriky
- **ROI (Return on Investment):** Celková návratnost vlastního kapitálu.
- **Cash-on-Cash Return:** Roční výnos z nájmu vůči vloženým prostředkům.
- **Net Yield:** Čistý výnos z nemovitosti.
- **IRR (Internal Rate of Return):** Vnitřní výnosové procento zohledňující časovou hodnotu peněz, cashflow i prodejní cenu.

## 3. Porovnání s Alternativní Investicí (ETF)
- **Opportunity Cost:** Porovnání nákupu nemovitosti vs. nájem a investice vlastních prostředků do S&P 500 / IWDA.
- **Dotace Cashflow (DCA):** Pokud je nemovitost v mínusu, model simuluje investování této částky do ETF v alternativním scénáři.
- **Měnové Riziko:** Modelování kurzu CZK/EUR pro ETF investice.

## 4. Optimalizace Strategie
- **Hledání Optima:** Automatický grid-search pro nalezení nejlepší kombinace LTV a Doby držení pro maximalizaci IRR.
- **Heatmapa:** Vizuální zobrazení vlivu páky a času na výnosnost.
- **Aplikace jedním klikem:** Rychlé nastavení nalezených parametrů do kalkulačky.

## 5. Správa Scénářů (New)
- **Ukládání a Načítání:** Možnost uložit si parametry konkrétní nemovitosti (např. "Byt Kladno", "Garsonka Praha").
- **Portfolio Porovnání:** Tabulkové srovnání všech uložených scénářů vedle sebe (IRR, Profit, Cashflow).
- **Perzistence:** Data jsou ukládána do lokálního JSON souboru.
