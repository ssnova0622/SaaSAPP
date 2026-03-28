
# Sequence Diagram for `_compute_supplier_deduction` Method

```mermaid
sequenceDiagram
    participant SaleOrderLineMeta as SaleOrderLineMeta
    participant CheckLineStatus as _check_line_matching_status
    participant SupplierIs as _supplier_is
    participant VendorIs as _vendor_is
    participant ContractIs as _contract_is
    participant GetPricingContract as _get_pricing_and_contract_type
    participant CalculateHotel as _calculate_supplier_deduction_for_hotel
    participant IsContractInList as _is_contract_in_list
    
    Note over SaleOrderLineMeta: Method starts with currency_sar parameter
    
    SaleOrderLineMeta->>CheckLineStatus: _check_line_matching_status()
    alt Special conditions check
        CheckLineStatus-->>SaleOrderLineMeta: Returns True/False
        alt Cancellation or special matching status or EMKAN_SKU
            SaleOrderLineMeta->>SaleOrderLineMeta: Set supplier_deduction = 0.0
            SaleOrderLineMeta->>SaleOrderLineMeta: Return early
        end
    end
    
    Note over SaleOrderLineMeta: Determine base cost
    alt matching_status == 'matched'
        alt vendor in ('gds', 'tp', GSA, NDC)
            SaleOrderLineMeta->>SaleOrderLineMeta: cost = converted_actual_net_cost
        else
            SaleOrderLineMeta->>SaleOrderLineMeta: cost = converted_total_actual_cost
        end
    else
        SaleOrderLineMeta->>SaleOrderLineMeta: cost = converted_quote_cost
    end
    
    SaleOrderLineMeta->>SaleOrderLineMeta: cost = abs(cost)
    
    alt Hotel and Offline product matched with Other Vendor and commissionable
        SaleOrderLineMeta->>SaleOrderLineMeta: supplier_deduction = (cost - converted_marketing_comm)
        SaleOrderLineMeta->>SaleOrderLineMeta: Return early
    end
    
    alt line_type in ('flight', 'other') or is_offline_booking
        alt Flight product and chartered flight vendor
            SaleOrderLineMeta->>SaleOrderLineMeta: supplier_deduction = cost - converted_marketing_comm
            SaleOrderLineMeta->>SaleOrderLineMeta: Return early
        end
        
        SaleOrderLineMeta->>SupplierIs: _supplier_is(FLYADEAL)
        SupplierIs-->>SaleOrderLineMeta: Returns True/False
        alt Flyadeal supplier and ticketing office not FLIGHT_ONE
            SaleOrderLineMeta->>SaleOrderLineMeta: supplier_deduction = cost
            SaleOrderLineMeta->>SaleOrderLineMeta: Return early
        end
        
        alt is_domestic_ksa and entity in VATABLE_ENTITIES
            alt vendor in ('gds', 'tp', GSA)
                SaleOrderLineMeta->>SaleOrderLineMeta: supplier_deduction = abs(cost - converted_gds_vat_in_amount)
            else
                SaleOrderLineMeta->>SaleOrderLineMeta: supplier_deduction = abs(cost - (cost / 1.15))
            end
            SaleOrderLineMeta->>SaleOrderLineMeta: Return early
        end
    end
    
    Note over SaleOrderLineMeta: Initialize amount for hotel product calculations
    SaleOrderLineMeta->>SaleOrderLineMeta: amount = 0.0
    
    alt line_type == HOTEL_PRODUCT
        alt No contract_type (old transaction)
            SaleOrderLineMeta->>SupplierIs: Multiple _supplier_is() checks
            SupplierIs-->>SaleOrderLineMeta: Returns True/False
            SaleOrderLineMeta->>ContractIs: Multiple _contract_is() checks
            ContractIs-->>SaleOrderLineMeta: Returns True/False
            SaleOrderLineMeta->>IsContractInList: _is_contract_in_list() checks
            IsContractInList-->>SaleOrderLineMeta: Returns True/False
            
            Note over SaleOrderLineMeta: Apply various supplier-specific rules
            alt Various supplier and contract conditions
                SaleOrderLineMeta->>SaleOrderLineMeta: Adjust amount based on rules
            end
        else
            SaleOrderLineMeta->>GetPricingContract: _get_pricing_and_contract_type()
            GetPricingContract->>VendorIs: _vendor_is(HR)
            VendorIs-->>GetPricingContract: Returns True/False
            alt vendor is HR
                GetPricingContract->>SaleOrderLineMeta: Get contract details and pricing type
            end
            GetPricingContract-->>SaleOrderLineMeta: Return pricing_type, contract_type
            
            SaleOrderLineMeta->>CalculateHotel: _calculate_supplier_deduction_for_hotel(amount, cost, contract_type)
            CalculateHotel-->>SaleOrderLineMeta: Return updated amount
        end
    end
    
    alt line_type in (ACCOMMODATION_PRODUCT)
        SaleOrderLineMeta->>SaleOrderLineMeta: amount -= converted_marketing_comm
    end
    
    SaleOrderLineMeta->>SaleOrderLineMeta: supplier_deduction = cost + amount
    Note over SaleOrderLineMeta: Method completes
```

## Explanation of the Sequence Diagram

The sequence diagram illustrates the flow of the `_compute_supplier_deduction` method, which calculates the supplier deduction amount based on various business rules and conditions. Here's a breakdown of the key steps:

1. **Initial Checks**:
   - The method first checks for special conditions (cancellation, specific matching statuses, or EMKAN_SKU) that would result in zero deduction.
   - If any of these conditions are met, it sets `supplier_deduction = 0.0` and returns early.

2. **Base Cost Determination**:
   - Depending on the matching status and vendor type, it determines the base cost from either `converted_actual_net_cost`, `converted_total_actual_cost`, or `converted_quote_cost`.
   - The cost is then converted to an absolute value.

3. **Special Case Handling**:
   - For hotel/offline products matched with "other" vendor and having commission, it calculates a specific deduction and returns early.
   - For flight products or offline bookings, it applies various rules based on vendor type, domestic status, and VAT considerations.

4. **Hotel Product Processing**:
   - For hotel products, it handles two scenarios:
     - For old transactions without contract_type, it applies various supplier-specific rules.
     - For newer transactions with contract_type, it gets the pricing and contract type and calculates the deduction accordingly.

5. **Accommodation Product Handling**:
   - For accommodation products, it subtracts the marketing commission from the amount.

6. **Final Calculation**:
   - Finally, it sets `supplier_deduction = cost + amount` to determine the final supplier deduction value.

The diagram shows the complex decision tree and the various helper methods called during the calculation process, illustrating how different business rules are applied based on product type, supplier, contract, and other factors.