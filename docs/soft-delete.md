# Soft-delete

- All database models which provide delete interface should implement soft-delete. No data should actually be completely deleted.
- When an item is deleted, it's values should be saved in a NoSQL database before actually removing from the SQL database.
- This is done because this needs to be reported.

## Implementation

Structure of the NoSQL database that stores deleted items:

```json
{
    "id": "id",
    "table": "table_name",
    "record_id": "record_id",
    "values": {
        "column_name": "value"
    },
    "deleted_at": "timestamp",
    "deleted_by_user_id": "user_id",
    "deleted_by_user_name": "user_name"
}
```

- `id` is the primary key of the NoSQL database.
- `table` is the name of the table from which the record was deleted.
- `record_id` is the primary key of the original record.
- `values` is a JSON object that contains the values of the original record. Whole row needs to be dumped here.
- `deleted_at` is the timestamp when the record was deleted.
- `deleted_by_user_id` is the id of the backoffice user who deleted the record.
- `deleted_by_user_name` is the name of the backoffice user who deleted the record.


To Do:

- Override delete method of ViewSet.
- Create producer to send deleted items to Kafka.
- Create a `report` service.
- Create a consumer in `report` service to consume deleted items from Kafka and save them to NoSQL database.

Report Storage Options:
1. ScyllaDB
2. Cassandra
3. DynamoDB
4. PostgreSQL
