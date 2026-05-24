---
title: "Filter / pivot recipes"
---

# Filter / Pivot Recipes — {{ project_name }}

> The processed CSV is **tidy long**: one row per observation, one
> column per variable. The wide views readers expect (year × variable
> matrices, source-comparison columns, geographic roll-ups) are
> generated on demand. This file is the cookbook.
>
> Recipes ship for **{{ consumer_stack }}**. Add more as common
> downstream uses emerge.

## Setup

### Python (pandas)

```python
import pandas as pd

df = pd.read_csv(
    "data/processed/{{ project_slug }}.csv",
    dtype=str,  # safe default — coerce specific columns below
)

# Coerce numeric columns explicitly:
# df["votes"] = pd.to_numeric(df["votes"], errors="coerce")
```

### R (tidyverse)

```r
library(readr); library(dplyr); library(tidyr)

df <- read_csv(
  "data/processed/{{ project_slug }}.csv",
  col_types = cols(.default = col_character())
)

# Coerce numeric columns explicitly:
# df <- df |> mutate(votes = as.integer(votes))
```

---

## Recipe 1 — Single-vintage wide pivot

*"Show me 2024 only, one row per `observation_id`, with the
project's numeric columns side by side."*

### pandas

```python
v2024 = df.query("vintage == '2024'")

wide = v2024.pivot_table(
    index="observation_id",
    columns="source",                 # or whatever the categorical to spread is
    values="<numeric_column>",        # replace with the project's actual measure
    aggfunc="first",                  # or "sum" if rows can repeat
)
```

### tidyverse

```r
wide <- df |>
  filter(vintage == "2024") |>
  pivot_wider(
    id_cols     = observation_id,
    names_from  = source,
    values_from = `<numeric_column>`
  )
```

---

## Recipe 2 — Year × source matrix of counts

*"How many rows from each source, in each vintage?"* This is what
the audit report shows you, but generated on demand for slicing
by reader.

### pandas

```python
counts = (
    df.groupby(["vintage", "source"])
      .size()
      .unstack("source", fill_value=0)
      .sort_index()
)
```

### tidyverse

```r
counts <- df |>
  count(vintage, source) |>
  pivot_wider(names_from = source, values_from = n, values_fill = 0) |>
  arrange(vintage)
```

---

## Recipe 3 — Roll up to a coarser geography

*"Aggregate from precinct to district (or county, or state)."*
Requires a crosswalk under `data/lookups/`. The pattern is the
same regardless of the specific geography — left-join the crosswalk,
group, aggregate.

### pandas

```python
# Suppose data/lookups/precinct_to_district.csv has columns: precinct, district
crosswalk = pd.read_csv("data/lookups/precinct_to_district.csv", dtype=str)

district_totals = (
    df.merge(crosswalk, on="precinct", how="left")
      .groupby(["vintage", "district"])
      ["<numeric_column>"]
      .sum()
      .reset_index()
)
```

### tidyverse

```r
crosswalk <- read_csv("data/lookups/precinct_to_district.csv",
                      col_types = cols(.default = col_character()))

district_totals <- df |>
  left_join(crosswalk, by = "precinct") |>
  group_by(vintage, district) |>
  summarise(total = sum(as.integer(`<numeric_column>`), na.rm = TRUE),
            .groups = "drop")
```

---

## Recipe 4 — Cross-source concept comparison

*"For every observation_id where source A and source B both
report the same `concept`, show both values side by side."*

This is what the `concept` column is for. Sources that name the
same underlying thing differently are harmonized via
`data/lookups/concepts.yaml`; this recipe is the payoff.

### pandas

```python
compare = (
    df.dropna(subset=["concept"])
      .pivot_table(
          index=["vintage", "observation_id", "concept"],
          columns="source",
          values="<value_column>",
          aggfunc="first",
      )
      .reset_index()
)
```

### tidyverse

```r
compare <- df |>
  filter(!is.na(concept)) |>
  pivot_wider(
    id_cols     = c(vintage, observation_id, concept),
    names_from  = source,
    values_from = `<value_column>`
  )
```

---

## Why long-then-pivot, not wide-as-primary

The tidy long format is the project's contract. Wide is a view.
The reasons:

- **New vintages don't change the schema.** A new year of data is
  new rows, not new columns. Wide-as-primary forces a column-add
  every refresh; tidy-long doesn't.
- **The same canonical CSV serves every downstream use.** A
  pandas notebook, an R analysis, a SQL load, a Datasette
  publish — all of them read the same file.
- **Auditing is uniform.** `audit.py` reports null rates per
  column. In wide layouts, "null rate of `votes_2017`" is a
  different question from "null rate of `votes_2018`"; in tidy
  long, "null rate of `votes`" is the question, and any vintage
  imbalance shows up in source coverage.

There are exceptions — see `references/data-modeling.md` ("When
wide-as-primary is OK") in the data-liberation skill. CVR-style
ballot-image data is the canonical case. But the default is long.
