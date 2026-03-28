### What kind of dummy data do you need?
Below are ready‑to‑use sample payloads and example responses for the new AI Scheduler API, plus a couple of samples for the WhatsApp/Twilio webhook and realtime events. If you need seed docs for the separate `app/` MongoDB app, tell me and I’ll include those too.

---

### 1) Tenants and professionals (pre‑seeded)
These are available immediately after starting the AI Scheduler:

- Tenants: `demo-salon`, `demo-clinic`
- Professionals per tenant (in‑memory) roughly look like this:
```json
{
  "tenant": "demo-salon",
  "category": "salon",
  "professionals": [
    {
      "name": "Alice",
      "price": 40.0,
      "slots": [
        {"time": "09:00", "status": "available"},
        {"time": "09:30", "status": "available"},
        {"time": "10:00", "status": "available"}
        // ... up to 16:30 (30‑minute steps)
      ]
    },
    {
      "name": "Bob",
      "price": 50.0,
      "slots": [
        {"time": "11:00", "status": "available"},
        {"time": "11:30", "status": "available"}
        // ... up to 18:30
      ]
    }
  ],
  "appointments": [],
  "cancellations": 0,
  "revenue": 0.0
}
```

```json
{
  "tenant": "demo-clinic",
  "category": "clinic",
  "professionals": [
    {
      "name": "Dr. Smith",
      "price": 75.0,
      "slots": [
        {"time": "10:00", "status": "available"},
        {"time": "10:30", "status": "available"}
        // ... up to 17:30
      ]
    },
    {
      "name": "Dr. Lee",
      "price": 80.0,
      "slots": [
        {"time": "09:00", "status": "available"},
        {"time": "09:30", "status": "available"}
        // ... up to 16:30
      ]
    }
  ],
  "appointments": [],
  "cancellations": 0,
  "revenue": 0.0
}
```

---

### 2) Dummy requests and responses (AI Scheduler API)

- List professionals
  - Request:
    ```http
    GET /v1/tenants/demo-salon/professionals
    ```
  - Example response:
    ```json
    [
      {"name": "Alice", "price": 40.0},
      {"name": "Bob", "price": 50.0}
    ]
    ```

- List slots for a professional
  - Request:
    ```http
    GET /v1/tenants/demo-salon/professionals/Alice/slots
    ```
  - Example response:
    ```json
    [
      {"time": "09:00", "status": "available"},
      {"time": "09:30", "status": "available"},
      {"time": "10:00", "status": "available"}
    ]
    ```

- Predict best slots (AI)
  - Request body:
    ```json
    {
      "tenant": "demo-salon",
      "professional": "Alice",
      "top_k": 3
    }
    ```
  - Example response:
    ```json
    {
      "tenant": "demo-salon",
      "professional": "Alice",
      "recommended": ["11:30", "12:00", "15:30"],
      "rationale": "Balanced off‑peak times and even distribution across the day."
    }
    ```

- Create appointment
  - Request body:
    ```json
    {
      "tenant": "demo-salon",
      "customer_name": "John Doe",
      "customer_phone": "+15551234567",
      "professional": "Alice",
      "time": "11:30"
    }
    ```
  - Example response:
    ```json
    {
      "id": "6f4a477f-28a5-4b24-8d32-0ff9a3e34c1e",
      "tenant": "demo-salon",
      "customer_name": "John Doe",
      "customer_phone": "+15551234567",
      "professional": "Alice",
      "time": "11:30",
      "price": 40.0,
      "status": "booked"
    }
    ```

- Cancel appointment
  - Request:
    ```http
    DELETE /v1/tenants/demo-salon/appointments/6f4a477f-28a5-4b24-8d32-0ff9a3e34c1e
    ```
  - Example response:
    ```json
    {
      "id": "6f4a477f-28a5-4b24-8d32-0ff9a3e34c1e",
      "tenant": "demo-salon",
      "customer_name": "John Doe",
      "customer_phone": "+15551234567",
      "professional": "Alice",
      "time": "11:30",
      "price": 40.0,
      "status": "canceled"
    }
    ```

- Admin analytics
  - Request:
    ```http
    GET /v1/tenants/demo-salon/analytics
    ```
  - Example response:
    ```json
    {
      "tenant": "demo-salon",
      "total_appointments": 3,
      "cancellations": 1,
      "revenue": 130.0
    }
    ```

---

### 3) Dummy data for the Twilio/WhatsApp webhook stub
- Endpoint: `POST /v1/integrations/twilio/whatsapp` (form‑urlencoded)
- Example form body you can post with curl:
```bash
curl -X POST http://127.0.0.1:8100/v1/integrations/twilio/whatsapp \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'WaId=demo-user&From=+15551234567&Body=list&tenant=demo-salon'
```
- Example JSON response:
```json
{
  "status": "ok",
  "reply": "Alice, Bob"
}
```
Other `Body` values to try: `book`, `who`, any free text.

---

### 4) WebSocket dummy events
Connect to `ws://127.0.0.1:8100/ws/demo-salon` and you’ll receive events like:

- Appointment created
```json
{
  "type": "appointment_created",
  "tenant": "demo-salon",
  "appointment": {
    "id": "6f4a477f-28a5-4b24-8d32-0ff9a3e34c1e",
    "customer_name": "John Doe",
    "customer_phone": "+15551234567",
    "professional": "Alice",
    "time": "11:30",
    "price": 40.0,
    "status": "booked"
  }
}
```

- Appointment canceled
```json
{
  "type": "appointment_canceled",
  "tenant": "demo-salon",
  "appointment": {
    "id": "6f4a477f-28a5-4b24-8d32-0ff9a3e34c1e",
    "professional": "Alice",
    "time": "11:30"
  }
}
```

- WhatsApp message relay
```json
{
  "type": "whatsapp_message",
  "tenant": "demo-salon",
  "from": "+15551234567",
  "body": "book"
}
```

---

### 5) Optional: Create your own dummy tenant
If you want a custom tenant, you can POST these through code later, but for quick testing here’s a JSON structure compatible with the in‑memory store:
```json
{
  "tenant": "demo-showroom",
  "category": "showroom",
  "professionals": [
    {
      "name": "Advisor A",
      "price": 0.0,
      "slots": [
        {"time": "10:00", "status": "available"},
        {"time": "10:30", "status": "available"},
        {"time": "11:00", "status": "available"}
      ]
    }
  ],
  "appointments": [],
  "cancellations": 0,
  "revenue": 0.0
}
```

If you need this exposed via an endpoint (e.g., `POST /v1/tenants/{tenant}/seed`) I can add a simple route to accept this payload and seed data dynamically.

---

If you tell me which part you want dummy data for (API requests, responses, WebSocket, or the separate Mongo‑backed `app/`), I’ll tailor the samples further or provide Postman collections.