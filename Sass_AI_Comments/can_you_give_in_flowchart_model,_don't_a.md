
# Flowchart for `_compute_supplier_deduction` Method

```mermaid
flowchart TD
    A[Start: _compute_supplier_deduction] --> B{Cancellation or\nspecific SKU?}
    B -->|Yes| C[Set supplier_deduction = 0.0]
    C --> Z[Return]
    
    B -->|No| D{matching_status\n== 'matched'?}
    D -->|Yes| E{vendor in\n'gds', 'tp', GSA, NDC?}
    E -->|Yes| F[cost = converted_actual_net_cost]
    E -->|No| G[cost = converted_total_actual_cost]
    
    D -->|No| H[cost = converted_quote_cost]
    
    F --> I[cost = abs(cost)]
    G --> I
    H --> I
    
    I --> J{matched with 'other' vendor\nand marketing_comm > 0?}
    J -->|Yes| K[supplier_deduction = cost - converted_marketing_comm]
    K --> Z
    
    J -->|No| L{line_type in 'flight', 'other'\nor is_offline_booking?}
    
    L -->|Yes| M{Flight product with\nchartered flight vendor?}
    M -->|Yes| N[supplier_deduction = cost - converted_marketing_comm]
    N --> Z
    
    M -->|No| O{Supplier is FLYADEAL and\nticketing_office != FLIGHT_ONE?}
    O -->|Yes| P[supplier_deduction = cost]
    P --> Z
    
    O -->|No| Q{is_domestic_ksa and\nentity in VATABLE_ENTITIES?}
    Q -->|Yes| R{vendor in 'gds', 'tp', GSA?}
    R -->|Yes| S[supplier_deduction = abs(cost - converted_gds_vat_in_amount)]
    R -->|No| T{commissionable?}
    T -->|Yes| U[supplier_deduction = cost - converted_marketing_comm]
    T -->|No| V[supplier_deduction = cost / 1.15]
    
    Q -->|No| W{is_domestic_uae and\nentity in TJ, ALM_AE?}
    W -->|Yes| X{vendor in 'gds', 'tp'?}
    X -->|Yes| Y[supplier_deduction = abs(cost - converted_gds_vat_in_amount)]
    X -->|No| AA{commissionable?}
    AA -->|Yes| AB[supplier_deduction = cost - converted_marketing_comm]
    AA -->|No| AC[supplier_deduction = cost / 1.05]
    
    W -->|No| AD{commissionable or\nmarketing_comm > 0?}
    AD -->|Yes| AE[supplier_deduction = cost - converted_marketing_comm]
    AD -->|No| AF[supplier_deduction = cost]
    
    S --> Z
    U --> Z
    V --> Z
    Y --> Z
    AB --> Z
    AC --> Z
    AE --> Z
    AF --> Z
    
    L -->|No| AG{cost is zero?}
    AG -->|Yes| AH[supplier_deduction = 0.0]
    AH --> Z
    
    AG -->|No| AI[amount = 0.0]
    
    AI --> AJ{line_type == HOTEL_PRODUCT?}
    AJ -->|Yes| AK{contract_type exists?}
    AK -->|No| AL[Apply supplier-specific rules\nbased on supplier name]
    AK -->|Yes| AM[Get pricing_type and contract_type]
    AM --> AN[Calculate supplier_deduction\nfor hotel based on contract]
    
    AL --> AO[Apply various supplier-specific\nrules and adjust amount]
    AN --> AO
    
    AJ -->|No| AP{line_type == ACCOMMODATION_PRODUCT?}
    AP -->|Yes| AQ[amount -= converted_marketing_comm]
    AP -->|No| AR[No additional adjustments]
    
    AO --> AS[supplier_deduction = cost + amount]
    AQ --> AS
    AR --> AS
    
    AS --> Z[Return]
```

## Key Decision Points in the Flowchart

1. **Initial Checks**:
   - Cancellation status and specific SKUs that result in zero deduction

2. **Cost Determination**:
   - Different cost calculations based on matching status and vendor type
   - Absolute value calculation for cost

3. **Special Case Handling**:
   - Hotel and offline products with "other" vendor and commissionable status
   - Flight products with chartered flight vendor
   - Supplier-specific rules (FLYADEAL)

4. **VAT and Location-based Rules**:
   - Domestic KSA transactions with vatable entities
   - Domestic UAE transactions with specific entities
   - Different calculations based on vendor type and commissionable status

5. **Hotel Product Processing**:
   - Complex supplier-specific rules based on contract types
   - Special handling for various suppliers (EXPEDIA, DOTW, WITHINEARTH, etc.)

6. **Accommodation Product Handling**:
   - Marketing commission deduction

7. **Final Calculation**:
   - Setting the supplier_deduction field with cost plus any adjustments