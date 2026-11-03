# Power BI Dashboard Guide - `powerbi/Accident_Dashboard.pbix`

Step-by-step instructions to build the two-page dashboard in **Power BI Desktop** (free, Windows) from the CSVs
produced by `notebooks/03_data_visualization.ipynb`. All files are in `data/powerbi/`.

| File | Grain | Used for |
|---|---|---|
| `fact_accidents.csv` | one row per accident (cleaned 399,581-row stratified sample) | all visuals, slicers, KPIs |
| `by_state.csv` | one row per State | state dimension / table |
| `by_weather.csv` | one row per weather group | weather dimension |
| `by_hour.csv` | one row per hour 0-23 | hour dimension |
| `by_month.csv` | one row per Year-Month | optional pre-aggregated trend |
| `hotspots_top.csv` | top 10 hotspot grid cells (full 7.7M-row data) | hotspot table |
| `map_points_20k.csv` | 20,000 sampled accident points | map visual |

> Counts in `fact_accidents.csv` are from the 5.18% stratified sample. Label the KPI card "Accidents (sample)".
> The hotspot table counts come from the full file.

---

## 1. Load the data

1. Open Power BI Desktop > **Blank report**.
2. **Home > Get data > Text/CSV** > select `data/powerbi/fact_accidents.csv` > **Transform Data** (not Load).
3. Repeat **Home > New Source > Text/CSV** inside Power Query for `by_state.csv`, `by_weather.csv`, `by_hour.csv`,
   `hotspots_top.csv` and `map_points_20k.csv`.

## 2. Power Query (Transform Data)

On **fact_accidents**:

1. Check the column types (click the type icon left of each header):
   * `Start_Time` -> **Date/Time**
   * `Severity`, `Year`, `Month`, `Hour`, `DayOfWeek`, `IsWeekend`, `IsRushHour`, `IsSevere`, `RoadFeatureCount`,
     `Junction`, `Traffic_Signal`, `Crossing`, `Duration_min` -> **Whole Number**
   * `Start_Lat`, `Start_Lng`, `Temperature_F`, `Visibility_mi`, `Precipitation_in`, `Distance_mi` -> **Decimal Number**
   * `State`, `City`, `WeatherGroup`, `DayNight`, `DayName` -> **Text**
2. **Add Column > Custom Column**: name `Date`, formula `= DateTime.Date([Start_Time])`, then set its type to **Date**.
3. Select `Start_Lat` > **Column tools (after load) > Data category = Latitude**; `Start_Lng` > **Longitude**;
   `State` > **State or Province**; `City` > **City** (done in step 5 below, in the Data view).
4. On **map_points_20k** set `Start_Lat`/`Start_Lng` to Decimal Number.
5. **Home > Close & Apply**.

In the **Data view** (table icon, left bar) set the data categories from step 3 (Column tools > Data category) for
both `fact_accidents` and `map_points_20k`.

## 3. Date table and relationships

1. **Modeling > New table**:
   ```DAX
   Calendar = ADDCOLUMNS(
       CALENDAR(DATE(2016,1,1), DATE(2023,3,31)),
       "Year", YEAR([Date]), "Month", MONTH([Date]),
       "MonthName", FORMAT([Date], "MMM"), "YearMonth", FORMAT([Date], "YYYY-MM"))
   ```
   Then **Table tools > Mark as date table** > Date column = `Date`. Select `MonthName` > **Sort by column** > `Month`.
2. Open the **Model view** (left bar) and drag to create these relationships (all *Many-to-one*, single direction):

| From (many) | To (one) |
|---|---|
| `fact_accidents[Date]` | `Calendar[Date]` |
| `fact_accidents[State]` | `by_state[State]` |
| `fact_accidents[WeatherGroup]` | `by_weather[WeatherGroup]` |
| `fact_accidents[Hour]` | `by_hour[Hour]` |

`hotspots_top` and `map_points_20k` stay unrelated (stand-alone visuals).

3. Select `fact_accidents[DayName]` > **Sort by column** > `DayOfWeek`.

## 4. DAX measures

Select `fact_accidents` in the Data pane > **Modeling > New measure**, one at a time:

```DAX
Total Accidents = COUNTROWS(fact_accidents)

Avg Severity = AVERAGE(fact_accidents[Severity])

High Severity % =
DIVIDE(
    CALCULATE(COUNTROWS(fact_accidents), fact_accidents[Severity] >= 3),
    [Total Accidents])

Severe Accidents = CALCULATE(COUNTROWS(fact_accidents), fact_accidents[Severity] >= 3)

Avg Duration (min) = AVERAGE(fact_accidents[Duration_min])
```

Format: `Avg Severity` -> Decimal, 2 places; `High Severity %` -> **Percentage**, 1 place; `Total Accidents` ->
Whole number with thousands separator.

## 5. Page 1 - "Overview"

Canvas: **View > Page view > Fit to page**; Format page > Canvas settings > 16:9.

| # | Visual (Visualizations pane) | Fields | Position |
|---|---|---|---|
| 1 | **Card** | `Total Accidents` (title "Accidents (sample)") | top row, 1 of 3 |
| 2 | **Card** | `Avg Severity` | top row, 2 of 3 |
| 3 | **Card** | `High Severity %` | top row, 3 of 3 |
| 4 | **Map** (or Azure Map) | Latitude `map_points_20k[Start_Lat]`, Longitude `map_points_20k[Start_Lng]`, Legend `Severity`, Bubble size: none | left, large |
| 5 | **Line chart** | X-axis `Calendar[YearMonth]` (or `Calendar[Date]` hierarchy Year > Month), Y-axis `Total Accidents` | right, middle |
| 6 | **Donut chart** | Legend `fact_accidents[Severity]`, Values `Total Accidents` | right, bottom |
| 7 | **Slicer** | `Calendar[Year]` (style: Tile) | slicer bar, top |
| 8 | **Slicer** | `fact_accidents[State]` (style: Dropdown) | slicer bar |
| 9 | **Slicer** | `fact_accidents[WeatherGroup]` (style: Dropdown) | slicer bar |

Colours: Format visual > Data colors - Severity 1 `#9EC5F4`, 2 `#5598E7`, 3 `#256ABF`, 4 `#0D366B`
(light-to-dark = low-to-high impact, same as the notebooks).

Note: the map uses `map_points_20k`, which is not related to the slicers. To make the map follow the slicers, use
`fact_accidents[Start_Lat]` / `[Start_Lng]` instead (heavier, 399k points; Power BI samples them automatically).

## 6. Page 2 - "Deep dive"

Right-click the page tab > **Duplicate page** is not needed; click **+** to add a new page, rename it "Deep dive".

| # | Visual | Fields | Notes |
|---|---|---|---|
| 1 | **Matrix** | Rows `fact_accidents[DayName]`, Columns `fact_accidents[Hour]`, Values `Total Accidents` | Format > Cell elements > **Background color** ON (gradient light `#F4F8FD` -> dark `#0D366B`) = hour x weekday heatmap |
| 2 | **Clustered bar chart** | Y-axis `fact_accidents[WeatherGroup]`, X-axis `High Severity %` | sort descending by `High Severity %`; add `Total Accidents` to Tooltips |
| 3 | **Table** | `hotspots_top[rank]`, `[label]`, `[accidents]`, `[avg_severity]`, `[severe_pct]` | title "Top 10 hotspot cells (full data)" |
| 4 | **Slicers** | copy the three slicers from page 1 (Ctrl+C / Ctrl+V > **Sync** when asked) | keeps filters in sync across pages |

## 7. Save and export

1. **File > Save as** > `powerbi/Accident_Dashboard.pbix`.
2. For the poster/report: **File > Export > Export to PDF**, or take a screenshot of page 1 and save it as
   `poster/assets/powerbi.png` (PNG, at least 1600 px wide).

## 8. Checks before submitting

* The `Total Accidents` card with no filters must equal the row count of `fact_accidents.csv`
  (`rows_clean` in `reports/metrics/cleaning_log.json`).
* `High Severity %` with no filters must match the overall severe share in `reports/metrics/by_weather.csv`
  (weighted by accidents) and in notebook 02.
* Every row of the hotspot table must match `reports/metrics/hotspots.csv`.
