# 📨 Background Job Queue — Architecture & Steps (Using AWS SQS)

This document explains how our background task system works using **AWS SQS**, **Python workers**, **Neo4j**, and **Postgres**. It also outlines the steps required to set it up and run it in production.

---

## 📌 1. Overview

We use **AWS SQS** to run long-running tasks in the background.

The flow:

1. API receives a request (e.g., segmentation job)
2. API creates a job entry in Postgres
3. API sends a message into SQS with the `job_id` + payload
4. Worker (`task.py`) reads messages from SQS
5. Worker calls `segmenter.py` to process the job
6. `segmenter.py` reads data from Neo4j and generates results
7. Worker writes results into Postgres (`job` + `task` tables)
8. Worker deletes the message from SQS after success
9. If job fails → update status and send to DLQ

This ensures tasks run **reliably**, **asynchronously**, and **in order** when needed.

---

## 📌 2. Components

### **🔹 2.1 API Service (Producer)**

Responsible for:

* Creating a "job" entry in Postgres with status `queued`
* Publishing a message to SQS containing:

  ```json
  {
    "job_id": "uuid",
    "task_type": "segment",
    "payload": {...}
  }
  ```

### **🔹 2.2 SQS Queue**

* Use **FIFO queue** (to preserve order if needed)
* Set **MessageGroupId** to group related jobs (e.g., `"segmentation"`)
* Configure:

  * Visibility timeout (longer than job execution time)
  * Dead Letter Queue (for failing jobs)

### **🔹 2.3 Worker (Consumer) — `task.py`**

Continuously polls SQS:

1. Takes one message at a time
2. Marks job as `running`
3. Calls `segmenter.py`
4. On success:

   * Mark job `completed`
   * Insert output into `task` table
   * Delete SQS message

5. On failure:

   * Mark job `failed`
   * Let SQS retry via visibility timeout
   * Eventually message goes to DLQ

### **🔹 2.4 Task Processing — `segmenter.py`**

Contains the core logic:

* Calls Neo4j through:

  * `neo4j/database.py`
  * `neo4j/queries.py`

* Runs the segmentation/processing logic
* Returns results for storage

### **🔹 2.5 Databases**

#### **Neo4j**

* Stores instance/segment graph data
* Used for computation-heavy tasks

#### **Postgres**

Tables needed:

* `job` (tracking overall job status)
* `task` (storing processed results)

---

## 📌 3. Required Steps to Make This System Work

### **STEP 1 — Create an SQS Queue (FIFO Recommended)**

* Enable content-based deduplication (optional)
* Create a Dead Letter Queue (DLQ)

### **STEP 2 — Configure API to enqueue jobs**

* Insert into `job` table
* Send SQS message with `job_id` + payload
* Return `job_id` to frontend

### **STEP 3 — Build Worker (`task.py`)**

* Poll SQS using long polling (20 seconds)
* Process one message at a time
* Mark job status in Postgres
* Handle errors safely
* Delete message after success

### **STEP 4 — Implement `segmenter.py`**

* Define task types (e.g., segmentation)
* Fetch data from Neo4j
* Run computation
* Format output
* Save results via Postgres

### **STEP 5 — Implement Neo4j Layers**

* `queries.py` → Cypher queries
* `database.py` → neo4j-driver wrapper
* Provide clean functions that segmenter calls

### **STEP 6 — Add Postgres Schema**

* `job` table: id, status, timestamps
* `task` table: results linked to job_id

### **STEP 7 — Configure Worker Deployment**

Options:

* systemd service
* Docker container
* ECS / EC2 runner
* Kubernetes CronJob

### **STEP 8 — Add Monitoring**

Recommended:

* SQS queue length
* DLQ message count
* Worker error logs
* Job status dashboard

---

## 📌 4. Job Lifecycle

| Stage         | Description                              |
| ------------- | ---------------------------------------- |
| **queued**    | API received request and job enqueued    |
| **running**   | Worker picked job and started processing |
| **completed** | Worker successfully finished             |
| **failed**    | Worker failed (error recorded)           |
| **retrying**  | SQS is retrying after timeout            |

---

## 📌 5. Minimal Folder Structure

```
/app
  /api
    enqueue.py
  /worker
    task.py
    segmenter.py
  /neo4j
    database.py
    queries.py
  /postgres
    models.py
  /utils
    sqs.py
```

---

## 📌 6. Summary

You need to:

1. Create SQS queue (FIFO) + DLQ
2. Add code in API to enqueue messages
3. Add worker (task.py) to consume messages
4. Implement segmentation logic (segmenter.py)
5. Add Postgres tracking tables
6. Add Neo4j access layer
7. Handle errors and retries
8. Deploy worker as background service

Everything else you already planned is correct — you just needed structure and missing pieces (visibility timeout, DLQ, idempotency).

---

## 📌 7. Current Implementation

The current project structure includes:

* `app/main.py` - Main application entry point
* `app/tasks.py` - Worker implementation
* `app/segmentation.py` - Segmentation logic
* `app/sqs_service.py` - SQS service wrapper
* `app/neo4j_database.py` - Neo4j database connection
* `app/neo4j_queries.py` - Cypher queries
* `app/db/models.py` - Database models
* `app/db/postgres.py` - PostgreSQL connection
* `app/storage.py` - Storage utilities
* `docker-compose.yml` - Docker orchestration
* `Dockerfile` - Container definition
* `start.sh` - Startup script

---

## 📌 8. Getting Started

### Prerequisites

* Python 3.9+
* Docker and Docker Compose
* AWS account with SQS access
* Neo4j database
* PostgreSQL database

### Environment Variables

The application supports multiple environments (dev/prod) with environment-specific configuration.

#### Environment Selector

* `ENVIRONMENT` - Set to `dev` or `prod` to select which environment configuration to use

#### Environment-Specific Variables

All configuration variables support environment-specific versions using `DEV_` or `PROD_` prefixes:

**PostgreSQL:**
* `DEV_POSTGRES_URL` / `PROD_POSTGRES_URL` - PostgreSQL connection string

**Neo4j:**
* `DEV_NEO4J_URI` / `PROD_NEO4J_URI` - Neo4j connection URI
* `DEV_NEO4J_USER` / `PROD_NEO4J_USER` - Neo4j username
* `DEV_NEO4J_PASSWORD` / `PROD_NEO4J_PASSWORD` - Neo4j password

**AWS SQS:**
* `DEV_AWS_REGION` / `PROD_AWS_REGION` - AWS region (e.g., `us-east-1`)
* `DEV_AWS_ACCESS_KEY_ID` / `PROD_AWS_ACCESS_KEY_ID` - AWS access key
* `DEV_AWS_SECRET_ACCESS_KEY` / `PROD_AWS_SECRET_ACCESS_KEY` - AWS secret key
* `DEV_SQS_QUEUE_URL` / `PROD_SQS_QUEUE_URL` - SQS queue URL

**Firebase Storage:**
* `DEV_GOOGLE_APPLICATION_CREDENTIALS` / `PROD_GOOGLE_APPLICATION_CREDENTIALS` - Path to Firebase credentials JSON
* `DEV_FIREBASE_STORAGE_BUCKET` / `PROD_FIREBASE_STORAGE_BUCKET` - Firebase Storage bucket name

**Milvus:**
* `DEV_MILVUS_URI` / `PROD_MILVUS_URI` - Milvus connection URI
* `DEV_MILVUS_TOKEN` / `PROD_MILVUS_TOKEN` - Milvus authentication token
* `DEV_MILVUS_COLLECTION_NAME` / `PROD_MILVUS_COLLECTION_NAME` - Milvus collection name

**Environment-Agnostic:**
* `GEMINI_API_KEY` - Gemini API key (shared across environments)
* `LOG_LEVEL` - Logging level (default: `INFO`)

#### Usage Examples

**Development:**
```bash
ENVIRONMENT=dev
```

**Production:**
```bash
ENVIRONMENT=prod
```

The system will automatically load the corresponding `DEV_*` or `PROD_*` variables based on the `ENVIRONMENT` setting

### Running with Docker

```bash
docker-compose up -d
```

### Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run the worker
python -m app.tasks
```

---

## 📌 9. Next Steps

If you need:

✅ Ready-to-copy folder structure
✅ Sample worker code
✅ Example SQL schema
✅ Complete end-to-end implementation

Feel free to extend this implementation based on your specific requirements.
