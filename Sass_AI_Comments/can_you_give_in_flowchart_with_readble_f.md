
```mermaid
flowchart TD
    A[Start: Calculate Supplier Deduction] --> B{Is Cancellation OR\nMatching Status = CANCELLATION OR\nSKU = EMKAN_SKU?}
    B -->|Yes| C[Set supplier_deduction = 0.0]
    B -->|No| D{Matching Status = 'matched'?}
    
    D -->|Yes| E{Vendor is GDS, TP, GSA, or NDC?}
    D -->|No| F[cost = converted_quote_cost]
    
    E -->|Yes| G[cost = converted_actual_net_cost]
    E -->|No| H[cost = converted_total_actual_cost]
    
    G --> I[cost = abs(cost)]
    H --> I
    F --> I
    
    I --> J{Matching Status = 'matched' AND\nVendor = 'other' AND\nconverted_marketing_comm > 0.0?}
    
    J -->|Yes| K[supplier_deduction = cost - converted_marketing_comm]
    J -->|No| L{Line Type is 'flight'/'other' OR\nis_offline_booking?}
    
    L -->|No| M[Continue to hotel product logic]
    L -->|Yes| N{Line Type = FLIGHT_PRODUCT AND\nVendor = CHARTERED_FLIGHT?}
    
    N -->|Yes| O[supplier_deduction = cost - converted_marketing_comm]
    N -->|No| P{Supplier is FLYADEAL AND\nticketing_office_id != FLIGHT_ONE?}
    
    P -->|Yes| Q[supplier_deduction = cost]
    P -->|No| R{is_domestic_ksa AND\nentity in VATABLE_ENTITIES?}
    
    R -->|Yes| S{Vendor in 'gds', 'tp', GSA?}
    R -->|No| T{is_domestic_uae AND\nentity in (TJ, ALM_AE)?}
    
    S -->|Yes| U[supplier_deduction = abs(cost - converted_gds_vat_in_amount)]
    S -->|No| V{commissionable?}
    
    V -->|Yes| W[supplier_deduction = cost - converted_marketing_comm]
    V -->|No| X[supplier_deduction = cost / 1.15]
    
    T -->|Yes| Y{Vendor in 'gds', 'tp'?}
    T -->|No| Z[Continue with other conditions]
    
    Y -->|Yes| AA[supplier_deduction = abs(cost - converted_gds_vat_in_amount)]
    Y -->|No| AB{commissionable?}
    
    AB -->|Yes| AC[supplier_deduction = cost - converted_marketing_comm]
    AB -->|No| AD[supplier_deduction = cost / 1.05]
    
    C --> AE[End]
    K --> AE
    O --> AE
    Q --> AE
    U --> AE
    W --> AE
    X --> AE
    AA --> AE
    AC --> AE
    AD --> AE
    Z --> AE
    M --> AE
```