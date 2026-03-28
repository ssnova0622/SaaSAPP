
# Why Using a Temporary Table Can Be Slow for Large Datasets

You're absolutely right to be concerned about using temporary tables when handling large datasets. The current implementation in `insert_update_order_report_data` uses a three-step process:

1. Create a temporary table with data from both sales and refunds
2. Delete existing records from the main table that match records in the temporary table
3. Insert all records from the temporary table into the main table

This approach has several performance drawbacks:

## Performance Issues with Temporary Tables

1. **Additional I/O Operations**: Creating a temporary table requires writing all the data to disk once, then reading it again for the delete and insert operations.

2. **Multiple Database Operations**: Instead of a single efficient operation, we're performing three separate operations (create, delete, insert).

3. **Increased Memory Usage**: Temporary tables consume additional memory and disk space.

4. **Table Locks**: The delete operation might lock parts of the main table, potentially affecting concurrent operations.

5. **Index Rebuilding**: After bulk deletes, database indexes may need to be rebuilt, adding overhead.

## Better Alternatives

A more efficient approach would be to use PostgreSQL's native `INSERT ... ON CONFLICT` (upsert) functionality:

```sql
INSERT INTO ofh_order_dashboard {orders_fields}
WITH aggregated_data AS (
    {self._from_sale()}
    UNION ALL
    {self._from_refund()}
)
SELECT * FROM aggregated_data
ON CONFLICT (internal_id) DO UPDATE SET
    order_id = EXCLUDED.order_id,
    business_unit = EXCLUDED.business_unit,
    -- other fields...
```

This single operation would:
- Only update records that already exist
- Insert new records that don't exist
- Avoid the overhead of temporary tables
- Utilize database transaction optimizations

## Why the Current Implementation Exists

The temporary table approach was implemented to work around type casting issues between the `internal_id` values in the queries and the database. The previous implementation using `ON CONFLICT` was causing errors because:

1. The `internal_id` field needed a unique constraint
2. There were type mismatches between string and integer representations

If you're dealing with large datasets, it would be worth revisiting the `ON CONFLICT` approach with proper type handling to significantly improve performance.