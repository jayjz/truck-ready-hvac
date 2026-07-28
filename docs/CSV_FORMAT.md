# CSV Format for Pilots

Contractors can feed real data via two simple CSVs. Column names are case-insensitive; extra columns are ignored.

## inventory.csv

| Column          | Required | Type    | Notes                                      |
|-----------------|----------|---------|--------------------------------------------|
| sku             | yes      | string  | Unique part identifier (normalized upper)  |
| name            | yes      | string  | Human-readable description                 |
| quantity        | yes      | int ≥ 0 | Current on-hand count                      |
| reorder_point   | no       | int ≥ 0 | Default 5                                  |
| unit_cost       | no       | float ≥ 0 | Default 0.0                             |
| category        | no       | string  | Default "general"                          |

Example:

```csv
sku,name,quantity,reorder_point,unit_cost,category
CAP-45-5,Dual Run Capacitor 45/5 MFD,6,4,12.50,electrical
CONT-30A,Contactor 30A 1-Pole,5,3,18.00,electrical
FILTER-20x25,Air Filter 20x25x1 MERV 8,18,10,4.25,filtration
LINESET-50,Line Set 50 ft,0,1,185.00,install
```

## jobs.csv

| Column          | Required | Type   | Notes                                              |
|-----------------|----------|--------|----------------------------------------------------|
| job_id          | yes      | string | Unique job identifier                              |
| job_type        | yes      | string | Used for default parts when no explicit BOM given  |
| customer_name   | yes      | string |                                                    |
| scheduled_date  | yes      | string | Free-form date string is accepted                  |
| assigned_tech   | no       | string |                                                    |
| notes           | no       | string |                                                    |
| required_parts  | no       | string | Optional simple BOM (see below)                    |

### required_parts format (optional)

If the column is present and non-empty, each part is written as:

```
SKU:qty[:urgency]
```

Multiple parts separated by `;`.

Examples:

```
CAP-45-5:1:high;CONT-30A:1
LINESET-50:1:critical;PAD-CONC:1:high
```

Urgency values: `critical`, `high`, `medium`, `low` (default `medium`).

If `required_parts` is blank or missing, the loader falls back to `default_parts_for_job_type(job_type)` so a contractor can start with only job type information.

Example jobs.csv:

```csv
job_id,job_type,customer_name,scheduled_date,assigned_tech,notes,required_parts
JOB-1001,Emergency_Repair,Martinez Residence,2026-07-28,TCH-01,No-cool call,
JOB-1003,Heat_Pump_Install,Patel Residence,2026-07-28,TCH-01,3-ton change-out,LINESET-50:1:critical;PAD-CONC:1:high;WHIP-6/3:1:high
```

## Error behavior

- Missing required columns → clear error listing the missing names.
- Invalid row (bad type, negative quantity, empty SKU, etc.) → error includes the 1-based row number and the Pydantic validation detail.
- Empty file or header-only file → treated as zero records (valid but empty).

See `data/samples/` for ready-to-use examples.
